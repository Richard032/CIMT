"""Execution of one exploration objective on one target and device."""

import hashlib
import pathlib
import plistlib
import re
import time
import zipfile
from contextlib import nullcontext
from dataclasses import dataclass, field
from coverage_tracker import CoverageTracker
from crashes import CrashMonitor, CrashRecovery, StartupGuard
from errors import InfrastructureError, ExplorationStalled
from exploration_memory import ExplorationMemory
from evidence import ScenarioEvidence
from check_results import scenario_verdict
from check_recorder import CheckRecorder
from requirement_results import RequirementResults
from decision_recovery import DecisionRecovery

UNFINISHED_OBJECTIVE = "Testing objective has not finished; coverage is not confirmed"


@dataclass
class ScenarioSession:
    """Stores objective data; it does not perform device or AI operations."""

    result: dict
    app_id: str
    executable: str
    elements: list
    image: bytes
    active: str = ""
    history: list = field(default_factory=list)
    coverage: CoverageTracker = field(default_factory=CoverageTracker)
    exploration: ExplorationMemory = field(default_factory=ExplorationMemory)


def application_executable(build, platform):
    """Read the IPA identity without installing or modifying it."""
    if platform != "ios":
        return build["app-id"]
    with zipfile.ZipFile(build["artifact"]) as archive:
        name = next(
            name
            for name in archive.namelist()
            if re.match(r"^Payload/[^/]+\.app/Info.plist$", name)
        )
        info = plistlib.loads(archive.read(name))
    if info["CFBundleIdentifier"] != build["app-id"]:
        raise InfrastructureError("IPA identity differs from build metadata")
    return info["CFBundleExecutable"]


class ScenarioRunner:
    """Orders objective steps. Actions, coverage, evidence, and recovery are separate services."""

    def __init__(
        self,
        inputs,
        config,
        redactor,
        control,
        actions,
        report,
        sleep=time.sleep,
        clock=time.time,
        requirements=None,
        activity=None,
    ):
        self.inputs = inputs
        self.config = config
        self.redactor = redactor
        self.control = control
        self.actions = actions
        self.report = report
        self.sleep = sleep
        self.clock = clock
        self.requirements = requirements or []
        self.activity = activity
        self.decisions = DecisionRecovery(inputs, config, redactor, control, activity)

    def run(self, mobile, build, result, agent, publish):
        """Execute one objective until it completes, is blocked, or reaches a limit."""
        scenario = self._new_result(build)
        result["scenarios"].append(scenario)
        try:
            publish()
            self._run(mobile, build, scenario, agent, publish)
        except ExplorationStalled as error:
            scenario["remaining"].append(str(error))
            if self.activity:
                self.activity.write("Exploration stopped", "blocked", str(error), mobile.device, build["target"])
        finally:
            # Errors and limits must not hide work that still needs testing.
            if scenario["completion"] != "complete":
                self._add_unresolved_work(scenario)
                if not scenario["remaining"]:
                    scenario["remaining"].append(UNFINISHED_OBJECTIVE)
            publish()

    def _run(self, mobile, build, result, agent, publish):
        """Order device and AI operations for the current objective."""
        evidence = self._evidence(mobile, build)
        session, monitor = self._prepare(mobile, build, result, evidence, publish)
        startup = StartupGuard(mobile, evidence, publish)
        recovery = CrashRecovery(mobile, monitor, evidence, self.redactor, publish)
        while True:
            self.control.check()
            with self._operation("Check application startup state", mobile, build["target"]):
                state = startup.check(session)
            if state == "stop":
                return
            if state == "retry":
                continue
            if not self._within_app(session):
                publish()
                return
            action = self._choose(mobile, session, agent, evidence, publish)
            if action["action"] == "done":
                self._complete(session, action)
                if self.activity:
                    self.activity.write("Objective finished", session.result["completion"],
                        "Verdict: " + session.result["verdict"], mobile.device, build["target"])
                publish()
                return
            before = session.elements
            entry, element, point = self._action_context(session, action)
            try:
                self._perform(mobile, session, action, entry, element)
                with self._operation("Observe action result and check crash recovery", mobile, build["target"]):
                    cancelled = recovery.after_action(session, entry, action, element, point)
            except Exception as error:
                # An interruption may arrive after only part of a credential action.
                entry.setdefault("actionError", self.redactor.text(str(error)))
                raise
            finally:
                # Keep the performed action even when evidence or recovery fails.
                session.exploration.record(before, session.elements, action, entry)
                session.result["exploration"] = self.redactor.object(session.exploration.saved())
                self._save_action(session, entry, action)
                publish()
            if cancelled:
                return

    def _operation(self, name, mobile, target):
        return self.activity.operation(name, mobile.device, target) if self.activity else nullcontext()

    def _evidence(self, mobile, build):
        target = build["target"]
        name = "target-" + re.sub(r"[^A-Za-z0-9_.-]", "_", target)[:60]
        folder = mobile.folder / (name + "-" + hashlib.sha256(target.encode()).hexdigest()[:8])
        folder.mkdir(mode=0o700, exist_ok=True)
        return ScenarioEvidence(folder, self.report)

    def _prepare(self, mobile, build, result, evidence, publish):
        executable = application_executable(build, mobile.device["platform"])
        self.control.check()
        mobile.reset(build["artifact"], build["app-id"], build["target"])
        result["reset"] = self._reset_description(mobile.device["platform"])
        monitor = CrashMonitor(mobile, build["app-id"], executable)
        monitor.start(result)
        elements, image = mobile.snapshot()
        screenshot = evidence.save_image("step-0000.png", image)
        result["steps"].append(
            {
                "step": 0,
                "action": "reset/install/launch",
                "observation": result["reset"],
                "screenshot": screenshot,
            }
        )
        return ScenarioSession(result, build["app-id"], executable, elements, image), monitor

    def _new_result(self, build):
        return {
            "target": build["target"],
            "appId": build["app-id"],
            "verdict": "inconclusive",
            "completion": "incomplete",
            "steps": [],
            "remaining": [UNFINISHED_OBJECTIVE],
            "crashes": [],
            "checks": [],
            "requirements": RequirementResults.initial(self.requirements),
            "coverage": {},
            "reset": "not-started",
        }

    @staticmethod
    def _reset_description(platform):
        return (
            "app-container-reinstall-verified; Keychain/backend state needs app hooks"
            if platform == "ios"
            else "install-and-platform-data-clear-verified"
        )

    @staticmethod
    def _within_app(session):
        allowed = [
            session.app_id,
            "com.apple.springboard",
            "com.android.permissioncontroller",
            "com.google.android.permissioncontroller",
            "com.android.packageinstaller",
        ]
        if session.active in allowed:
            return True
        session.result["remaining"].append(
            "Application opened another app; that external workflow was not explored"
        )
        return False

    def _choose(self, mobile, session, agent, evidence, publish):
        session.exploration.observe(session.elements)
        session.coverage.observe(session.elements)
        coverage = session.coverage.snapshot()
        session.result["coverage"] = coverage
        publish()
        with self._operation("Request AI action", mobile, session.result["target"]):
            action = self.decisions.choose(mobile, session, agent, evidence, publish)
        # Save the latest plan before checks or limits can stop this scenario.
        action = dict(action, remaining=self.redactor.object(list(action["remaining"])))
        session.result["remaining"] = list(action["remaining"])
        session.exploration.plan = list(action["remaining"])
        session.result["exploration"] = self.redactor.object(session.exploration.saved())
        if action["action"] != "done" and not session.result["remaining"]:
            session.result["remaining"].append(UNFINISHED_OBJECTIVE)
        # Keep a returned finding even if the run limit expired during the request.
        CheckRecorder(self.redactor, evidence, publish).record(
            session, action.get("checks", []), self.inputs["instructions"]
        )
        self.control.check()
        publish()
        return action

    def _action_context(self, session, action):
        element = next(
            (element for element in session.elements if element.get("ref") == action["ref"]), {}
        )
        point = session.coverage.crash_point(session.result["target"], element, action)
        entry = {
            "step": len(session.result["steps"]),
            "action": self.redactor.records.action(action),
            "observation": action["observation"],
        }
        return entry, element, point

    def _perform(self, mobile, session, action, entry, element):
        try:
            with self._operation("Execute device action: " + action["action"], mobile, session.result["target"]):
                self.actions.execute(mobile, action, session.elements)
            if action["action"] in ["tap", "credential"]:
                session.coverage.activated(element)
        except ValueError as error:
            entry["actionError"] = str(error)
        self.sleep(min(0.4, max(0, self.control.deadline - self.clock())))

    def _save_action(self, session, entry, action):
        session.result["coverage"] = session.coverage.snapshot()
        session.result["steps"].append(self.redactor.records.step(entry))
        result = entry.get("crash", entry.get("actionError", entry.get("observedOutcome", "Action result unavailable")))
        session.history.append(self.redactor.records.action(dict(
            action, result=result, controlLabel=entry.get("controlLabel", ""))))

    @staticmethod
    def _complete(session, action):
        result = session.result
        # The saved list was already redacted when the response was received.
        result["remaining"] = list(action["remaining"])
        result["coverage"] = session.coverage.snapshot()
        ScenarioRunner._add_unresolved_work(result)
        result["interpretation"] = action["observation"]
        complete = action["completion"] == "complete" and not result["remaining"]
        result["completion"] = "complete" if complete else "incomplete"
        result["verdict"] = scenario_verdict(
            result.get("checks", []), bool(result["crashes"]), complete, result["requirements"]
        )

    @staticmethod
    def _add_unresolved_work(result):
        """Include known coverage gaps even when no final AI response was returned."""
        outstanding = result.get("coverage", {}).get("outstandingObservedControls", 0)
        messages = []
        if outstanding:
            messages.append(
                str(outstanding) + " observed control/state combinations were not activated"
            )
        unresolved = RequirementResults.unresolved(result["requirements"])
        if unresolved:
            messages.append(str(unresolved) + " requirements have no decided result")
        for message in messages:
            if message not in result["remaining"]:
                result["remaining"].append(message)
