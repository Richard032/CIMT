"""Execution of one exploration objective on one target and device."""

import hashlib
import pathlib
import plistlib
import re
import time
import zipfile
from dataclasses import dataclass, field
from coverage_tracker import CoverageTracker
from crashes import CrashMonitor, CrashRecovery, StartupGuard
from errors import InfrastructureError
from evidence import ScenarioEvidence
from check_results import scenario_verdict
from check_recorder import CheckRecorder
from requirement_results import RequirementResults


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

    def run(self, mobile, build, result, agent, publish):
        """Execute one objective until it completes, is blocked, or reaches a limit."""
        evidence = self._evidence(mobile, build)
        session, monitor = self._prepare(mobile, build, result, evidence, publish)
        startup = StartupGuard(mobile, evidence, publish)
        recovery = CrashRecovery(mobile, monitor, evidence, self.redactor, publish)
        while True:
            self.control.check()
            state = startup.check(session)
            if state == "stop":
                return
            if state == "retry":
                continue
            if not self._within_app(session):
                publish()
                return
            action = self._choose(session, agent, evidence, publish)
            if action["action"] == "done":
                self._complete(session, action)
                publish()
                return
            entry, element, point = self._perform(mobile, session, action)
            try:
                cancelled = recovery.after_action(session, entry, action, element, point)
            finally:
                # Keep the performed action even when evidence or recovery fails.
                self._save_action(session, entry, action)
                publish()
            if cancelled:
                return

    def _evidence(self, mobile, build):
        target = build["target"]
        name = "target-" + re.sub(r"[^A-Za-z0-9_.-]", "_", target)[:60]
        folder = mobile.folder / (name + "-" + hashlib.sha256(target.encode()).hexdigest()[:8])
        folder.mkdir(mode=0o700, exist_ok=True)
        return ScenarioEvidence(folder, self.report)

    def _prepare(self, mobile, build, device_result, evidence, publish):
        result = self._new_result(build)
        device_result["scenarios"].append(result)
        publish()
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
            "remaining": [],
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

    def _choose(self, session, agent, evidence, publish):
        session.coverage.observe(session.elements)
        coverage = session.coverage.snapshot()
        session.result["coverage"] = coverage
        publish()
        action = agent.choose(
            self.inputs["instructions"],
            self.inputs.get("requirements", ""),
            self.inputs.get("setup", ""),
            session.elements,
            session.image,
            session.history,
            list(self.config.get("credentials", {})),
            coverage,
            session.result["requirements"],
        )
        # Keep a returned finding even if the run limit expired during the request.
        CheckRecorder(self.redactor, evidence, publish).record(
            session, action.get("checks", []), self.inputs["instructions"]
        )
        self.control.check()
        publish()
        return action

    def _perform(self, mobile, session, action):
        element = next(
            (element for element in session.elements if element.get("ref") == action["ref"]), {}
        )
        point = session.coverage.crash_point(session.result["target"], element, action)
        entry = {
            "step": len(session.result["steps"]),
            "action": self.redactor.object(action),
            "observation": action["observation"],
        }
        try:
            self.actions.execute(mobile, action, session.elements)
            if action["action"] in ["tap", "credential"]:
                session.coverage.activated(element)
        except ValueError as error:
            entry["actionError"] = str(error)
        self.sleep(min(0.4, max(0, self.control.deadline - self.clock())))
        return entry, element, point

    def _save_action(self, session, entry, action):
        session.result["steps"].append(self.redactor.object(entry))
        result = entry.get("crash", entry.get("actionError", "action completed"))
        session.history.append(self.redactor.object(dict(action, result=result)))

    @staticmethod
    def _complete(session, action):
        result = session.result
        result["remaining"] = action["remaining"]
        outstanding = session.coverage.outstanding()
        if outstanding:
            result["remaining"].append(
                str(len(outstanding)) + " observed control/state combinations were not activated"
            )
        unresolved = RequirementResults.unresolved(result["requirements"])
        if unresolved:
            result["remaining"].append(str(unresolved) + " requirements have no decided result")
        result["interpretation"] = action["observation"]
        complete = action["completion"] == "complete" and not result["remaining"]
        result["completion"] = "complete" if complete else "incomplete"
        result["verdict"] = scenario_verdict(
            result.get("checks", []), bool(result["crashes"]), complete, result["requirements"]
        )
