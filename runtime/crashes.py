"""Crash observations and recovery rules for one scenario."""

import json
import re
from dataclasses import dataclass
from errors import InfrastructureError


class CrashCounter:
    def __init__(self):
        self.point, self.count = None, 0

    def record(self, point, crashed):
        """Count repeated crashes at one point; clear them only after success there."""
        if crashed:
            self.count = self.count + 1 if point == self.point else 1
            self.point = point
        elif point == self.point:
            self.point, self.count = None, 0
        return self.count


def records(value):
    if isinstance(value, list):
        return [x for x in value if isinstance(x, dict)]
    if isinstance(value, dict):
        for key in ["crashes", "reports", "items"]:
            if isinstance(value.get(key), list):
                return records(value[key])
    return []


def record_key(row):
    return str(row.get("id", row.get("name", row.get("path", json.dumps(row, sort_keys=True)))))


@dataclass
class TerminationObservation:
    foreground: str
    died: bool
    diagnostics: list


class CrashMonitor:
    """Finds new app crash records and checks unexpected process termination."""

    def __init__(self, mobile, app_id, executable):
        self.mobile = mobile
        self.app_id = app_id
        self.executable = executable
        self.baseline = set()

    def start(self, scenario):
        """Remember existing diagnostics so old crashes are not reported as new."""
        try:
            self.baseline = {record_key(row) for row in records(self.mobile.crashes())}
        except InfrastructureError:
            scenario["diagnostics"] = (
                "Native crash listing unavailable; process/foreground checks remain active"
            )

    def observe(self):
        """Combine foreground, process, and new crash evidence for this action."""
        foreground = self.mobile.foreground()
        died = foreground != self.app_id and not self.mobile.running(self.app_id, self.executable)
        return TerminationObservation(foreground, died, self._new_records())

    def _new_records(self):
        fresh = []
        try:
            for row in records(self.mobile.crashes()):
                key = record_key(row)
                belongs_to_app = self.app_id in json.dumps(row) or self.executable in json.dumps(
                    row
                )
                if key not in self.baseline and belongs_to_app:
                    fresh.append(row)
                    self.baseline.add(key)
        except InfrastructureError:
            pass
        return fresh


class StartupGuard:
    """Stops an objective after three matching startup terminations."""

    def __init__(self, mobile, evidence, publish):
        self.mobile = mobile
        self.evidence = evidence
        self.publish = publish
        self.failures = 0

    def check(self, session):
        """Retry a failed launch or stop this objective after three failures."""
        session.active = self.mobile.foreground()
        if session.active == session.app_id or self.mobile.running(
            session.app_id, session.executable
        ):
            self.failures = 0
            return "ready"
        self.failures += 1
        self._record(session)
        if self.failures >= 3:
            session.result["remaining"].append(
                "Scenario cancelled after three matching startup terminations"
            )
            return "stop"
        self.mobile.call("mobile_launch_app", packageName=session.app_id)
        session.elements, session.image = self.mobile.snapshot()
        return "retry"

    def _record(self, session):
        session.result["crashes"].append(
            {
                "kind": "unexpected startup termination / suspected crash",
                "matchingAttempt": self.failures,
            }
        )
        session.result["verdict"] = "failed"
        step = {"action": "startup/relaunch check"}
        session.result["steps"].append(step)
        # Save the known failure before attempting image storage.
        self.publish()
        try:
            step["screenshot"] = self.evidence.save_image(
                "startup-crash-" + str(self.failures) + ".png", session.image
            )
        except Exception as error:
            step["evidenceError"] = type(error).__name__
            self.publish()
            raise


class CrashRecovery:
    """Records terminations and decides whether to relaunch or cancel the objective."""

    def __init__(self, mobile, monitor, evidence, redactor, publish):
        self.mobile = mobile
        self.monitor = monitor
        self.evidence = evidence
        self.redactor = redactor
        self.counter = CrashCounter()
        self.publish = publish

    def after_action(self, session, entry, action, element, point):
        """Save the observed result and apply the crash recovery rule."""
        observation = self.monitor.observe()
        crashed = self._is_crash(observation, element)
        cancelled = False
        if crashed:
            cancelled = self._record_crash(session, entry, action, point, observation)
            self.publish()
        else:
            self._record_success(point)
        self._capture(session, entry)
        if cancelled:
            return True
        if crashed:
            self._relaunch(session)
            entry["recovery"] = "relaunch succeeded"
        elif observation.foreground != session.app_id:
            entry["navigation"] = (
                "Explicit exit or background/external navigation; no matching crash diagnostic"
            )
            self._relaunch(session)
        return False

    def _capture(self, session, entry):
        try:
            session.elements, session.image = self.mobile.snapshot()
            entry.update(self.evidence.save_step(entry["step"], session.elements, session.image))
        except Exception as error:
            entry["evidenceError"] = self.redactor.text(str(error))
            raise

    @staticmethod
    def _is_crash(observation, element):
        label = " ".join(str(element.get(key, "")) for key in ["text", "label", "identifier"])
        explicit_exit = bool(re.search(r"\b(quit|exit|close app|beenden)\b", label, re.I))
        return bool(observation.diagnostics) or observation.died and not explicit_exit

    def _record_crash(self, session, entry, action, point, observation):
        count = self.counter.record(point + ":" + self._signature(observation.diagnostics), True)
        crash = self._crash_record(session, entry, action, point, observation, count)
        session.result["crashes"].append(crash)
        session.result["verdict"] = "failed"
        entry.update(crash=crash["kind"], matchingAttempt=count)
        if count >= 3:
            session.result["remaining"].append(
                "Scenario cancelled after three matching crashing attempts"
            )
            return True
        return False

    def _crash_record(self, session, entry, action, point, observation, count):
        return {
            "step": entry["step"],
            "kind": (
                "confirmed crash report"
                if observation.diagnostics
                else "unexpected termination / suspected crash"
            ),
            "point": point,
            "matchingAttempt": count,
            "diagnostics": self.redactor.object(observation.diagnostics),
            "reproductionSteps": self.redactor.object(session.history + [action]),
        }

    @staticmethod
    def _signature(diagnostics):
        if not diagnostics:
            return "unknown"
        keys = ["exceptionType", "exceptionCode", "terminationReason", "signature"]
        signature = json.dumps(
            {key: value for key, value in diagnostics[0].items() if key in keys}, sort_keys=True
        )
        return re.sub(r"0x[0-9a-fA-F]+", "<address>", signature)

    def _record_success(self, point):
        # Unrelated navigation must not clear retries at a known crash point.
        if self.counter.point and self.counter.point.startswith(point + ":"):
            self.counter.record(self.counter.point, False)

    def _relaunch(self, session):
        self.mobile.call("mobile_launch_app", packageName=session.app_id)
        session.elements, session.image = self.mobile.snapshot()
