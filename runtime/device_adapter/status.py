"""Read foreground apps, processes and crash information."""

import json
import pathlib
from .target import DeviceTarget


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
                ["adb", "-s", DeviceTarget(self.device, self.run_command).adb_serial(), "shell", "pidof", app_id],
                capture_output=True,
                timeout=15,
            )
            return r.returncode == 0 and bool(r.stdout.strip())
        target = DeviceTarget(self.device, self.run_command)
        if target.is_ios_simulator:
            return target.simulator_running(app_id)
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
