"""Small platform differences behind the shared mobile-device workflow."""

import re
from errors import InfrastructureError


class DeviceTarget:
    """Keeps native helper identity separate from platform command identity."""

    def __init__(self, device, run_command):
        self.device = device
        self.run_command = run_command

    @property
    def is_ios_simulator(self):
        return self.device.get("type", "real") == "simulator" and self.device["platform"] == "ios"

    def adb_serial(self):
        if self.device.get("type") != "emulator":
            return self.device["id"]
        if self.device["id"].startswith("emulator-"):
            return self.device["id"]
        # Some helper versions identify an emulator by AVD name instead of ADB serial.
        result = self.run_command(["adb", "devices"], capture_output=True, text=True, timeout=15)
        if result.returncode:
            raise InfrastructureError("Android emulator serial lookup failed")
        for line in result.stdout.splitlines():
            columns = line.split()
            if len(columns) == 2 and columns[0].startswith("emulator-") and columns[1] == "device":
                name = self.run_command(["adb", "-s", columns[0], "emu", "avd", "name"], capture_output=True, text=True, timeout=15)
                if name.returncode == 0 and name.stdout.splitlines()[:1] == [self.device["id"]]:
                    return columns[0]
        raise InfrastructureError("Selected Android emulator has no online ADB serial")

    def verify_simulator(self):
        result = self.run_command(["xcrun", "simctl", "getenv", self.device["id"], "SIMULATOR_UDID"],
                                  capture_output=True, text=True, timeout=15)
        if result.returncode or result.stdout.strip() != self.device["id"]:
            raise InfrastructureError("iOS Simulator is not booted and ready")

    def simulator_running(self, app_id):
        result = self.run_command(["xcrun", "simctl", "spawn", self.device["id"], "launchctl", "list"],
                                  capture_output=True, text=True, timeout=15)
        if result.returncode:
            raise InfrastructureError("iOS Simulator process query failed")
        # Require a live PID and an exact bundle identifier, not a substring match.
        return bool(re.search(r"^\s*\d+\s+\S+\s+UIKitApplication:" + re.escape(app_id) + r"\[", result.stdout, re.M))
