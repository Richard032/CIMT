"""Read foreground apps, processes and crash information."""

import json
import pathlib
import re
import subprocess
import time
from errors import DeviceActionError, LimitReached
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

    def sample_memory(self, app_id):
        """Read PSS and RSS for the main process of the tested Android app."""
        if self.device['platform'] != 'android':
            raise DeviceActionError('Memory sampling is available on Android only')
        if not re.fullmatch(r'[A-Za-z0-9_.]+', app_id):
            raise DeviceActionError('Memory sampling requires a valid installed Android app ID')
        try:
            serial = DeviceTarget(self.device, self.run_command).adb_serial()
            remaining = self.context['deadline'] - time.time()
            if remaining <= 0:
                raise LimitReached('Whole-run time limit reached')
            result = self.run_command(['adb', '-s', serial, 'shell', 'dumpsys', 'meminfo', '-s', app_id],
                                      capture_output=True, text=True, timeout=min(15, remaining))
        except (OSError, subprocess.TimeoutExpired):
            raise DeviceActionError('Android memory query did not complete') from None
        if result.returncode == 0:
            records = re.split(r'(?m)^\*\* MEMINFO in pid (\d+) \[([^\]\n]+)\] \*\*[^\n]*', result.stdout)
            for pid, package, section in zip(records[1::3], records[2::3], records[3::3]):
                if package != app_id:
                    continue
                totals = re.search(r'TOTAL PSS:\s*(\d+)\s+TOTAL RSS:\s*(\d+)', section)
                if totals:
                    return int(pid), int(totals[1]), int(totals[2])
        raise DeviceActionError('No PSS and RSS sample was returned for the tested Android app')

    def crashes(self):
        """Read native crash metadata without deleting device diagnostics."""
        return self.native(["device", "crashes", "list"], timeout=30).get("data", [])
