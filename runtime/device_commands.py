"""Read-only native device queries and readiness checks."""

import json
import os
import pathlib
import re
import subprocess
import time
from errors import InfrastructureError, LimitReached


class NativeDevice:
    """Runs the native helper with one fixed device and run-specific home."""

    def __init__(self, binary, device, context, redactor, run_command=subprocess.run):
        self.binary = binary
        self.device = device
        self.context = context
        self.run_command = run_command
        self.redactor = redactor
        self.env = dict(os.environ, MOBILECLI_HOME=context["nativeHome"])
        self.env.pop("OPENAI_API_KEY", None)

    def native(self, arguments, timeout=30):
        """Call the native helper for this fixed device within the run deadline."""
        result = self._run(arguments, timeout, text=True)
        try:
            return json.loads(result.stdout)
        except ValueError:
            raise InfrastructureError("Device command returned invalid JSON") from None

    def screenshot(self):
        """Read lossless pixels in memory. Never create a raw screenshot file."""
        return self._run(["screenshot", "--format", "png", "--output", "-"], 30, text=False).stdout

    def _run(self, arguments, timeout, text):
        remaining = self.context["deadline"] - time.time()
        if remaining <= 0:
            raise LimitReached("Whole-run time limit reached")
        try:
            r = self.run_command(
                [self.binary] + arguments + ["--device", self.device["id"]],
                capture_output=True,
                text=text,
                env=self.env,
                timeout=min(timeout, remaining),
            )
        except subprocess.TimeoutExpired:
            raise InfrastructureError("Device command timed out") from None
        if r.returncode != 0:
            error = r.stderr.decode(errors="replace") if isinstance(r.stderr, bytes) else r.stderr
            raise InfrastructureError(self.redactor.text(error[-1000:] or "Device command failed"))
        return r


class DeviceReadiness:
    """Checks device locks before CIMT can perform an app action."""

    def __init__(self, commands, folder):
        self.commands = commands
        self.device = commands.device
        self.context = commands.context
        self.folder = folder
        self.run_command = commands.run_command

    def readiness(self):
        """Check the platform lock state before any app interaction."""
        if self.device["platform"] == "ios":
            self._iphone()
        else:
            self._android()

    def _iphone(self):
        path = pathlib.Path(self.context["work"]) / ("lock-" + self.folder.name + ".json")
        try:
            self.run_command(
                [
                    "xcrun",
                    "devicectl",
                    "device",
                    "info",
                    "lockState",
                    "--device",
                    self.device["id"],
                    "--timeout",
                    "15",
                    "--json-output",
                    str(path),
                ],
                capture_output=True,
                check=True,
                timeout=20,
            )
            if json.loads(path.read_text()).get("result", {}).get("passcodeRequired") is not False:
                raise LimitReached("iPhone is locked; application interaction was not started")
        except (OSError, subprocess.SubprocessError, ValueError):
            raise InfrastructureError("iPhone readiness could not be verified") from None
        finally:
            path.unlink(missing_ok=True)

    def _android(self):
        result = self.run_command(
            ["adb", "-s", self.device["id"], "shell", "dumpsys", "window", "policy"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        states = re.findall("^\\s*showing=(true|false)\\s*$", result.stdout, re.M)
        if result.returncode or len(states) != 1:
            raise InfrastructureError("Android lock readiness could not be verified")
        if states[0] != "false":
            raise LimitReached("Android phone is locked; application interaction was not started")


class DeviceStatus:
    """Queries foreground apps, running processes, and native crash listings."""

    def __init__(self, commands, folder):
        self.device = commands.device
        self.context = commands.context
        self.folder = folder
        self.native = commands.native
        self.run_command = commands.run_command

    def foreground(self):
        """Read the identifier of the current foreground app."""
        return self.native(["apps", "foreground"]).get("data", {}).get("packageName")

    def running(self, app_id, executable):
        """Check whether the tested app process still exists."""
        if self.device["platform"] == "android":
            r = self.run_command(
                ["adb", "-s", self.device["id"], "shell", "pidof", app_id],
                capture_output=True,
                timeout=15,
            )
            return r.returncode == 0 and bool(r.stdout.strip())
        path = pathlib.Path(self.context["work"]) / ("processes-" + self.folder.name + ".json")
        try:
            self.run_command(
                [
                    "xcrun",
                    "devicectl",
                    "device",
                    "info",
                    "processes",
                    "--device",
                    self.device["id"],
                    "--timeout",
                    "15",
                    "--json-output",
                    str(path),
                ],
                capture_output=True,
                check=True,
                timeout=20,
            )
            data = json.loads(path.read_text()).get("result", {})
            return executable in json.dumps(data)
        finally:
            path.unlink(missing_ok=True)

    def crashes(self):
        """Read native crash metadata without deleting device diagnostics."""
        return self.native(["device", "crashes", "list"], timeout=30).get("data", [])
