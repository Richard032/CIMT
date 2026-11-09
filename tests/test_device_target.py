"""Check platform differences without using a real or virtual device."""

import pathlib
import plistlib
import tempfile
import zipfile
import subprocess
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "runtime"))
from device_adapter.target import DeviceTarget
from errors import InfrastructureError
from device_adapter.readiness import DeviceReadiness
from scenario import application_executable


class DeviceTargetTests(unittest.TestCase):
    def test_simulator_zip_keeps_the_actual_app_identity(self):
        with tempfile.TemporaryDirectory() as folder:
            path = pathlib.Path(folder) / "simulator-app.zip"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("Example.app/Info.plist", plistlib.dumps({
                    "CFBundleIdentifier": "com.example.app", "CFBundleExecutable": "Example"
                }))
            self.assertEqual("Example", application_executable({"artifact": str(path), "app-id": "com.example.app"}, "ios"))
            with self.assertRaises(InfrastructureError):
                application_executable({"artifact": str(path), "app-id": "com.example.other"}, "ios")

    def test_physical_android_keeps_its_serial(self):
        target = DeviceTarget({"platform": "android", "id": "phone-a"}, None)
        self.assertEqual("phone-a", target.adb_serial())

    def test_emulator_name_resolves_to_its_matching_adb_serial(self):
        def command(args, **options):
            output = "List of devices attached\nemulator-5554\tdevice\n" if args == ["adb", "devices"] else "CIMT\nOK\n"
            return subprocess.CompletedProcess(args, 0, output, "")
        target = DeviceTarget({"platform": "android", "type": "emulator", "id": "CIMT"}, command)
        self.assertEqual("emulator-5554", target.adb_serial())

    def test_unmatched_emulator_is_rejected(self):
        def command(args, **options):
            return subprocess.CompletedProcess(args, 0, "", "")
        target = DeviceTarget({"platform": "android", "type": "emulator", "id": "missing"}, command)
        with self.assertRaises(InfrastructureError):
            target.adb_serial()

    def test_booted_simulator_is_ready(self):
        calls = []
        def command(args, **options):
            calls.append(args)
            return subprocess.CompletedProcess(args, 0, "sim-a\n", "")
        target = DeviceTarget({"platform": "ios", "type": "simulator", "id": "sim-a"}, command)
        self.assertTrue(target.is_ios_simulator)
        target.verify_simulator()
        self.assertEqual(["xcrun", "simctl", "getenv", "sim-a", "SIMULATOR_UDID"], calls[0])

    def test_shared_readiness_uses_simctl_for_a_simulator(self):
        calls = []
        def command(args, **options):
            calls.append(args)
            return subprocess.CompletedProcess(args, 0, "sim-a\n", "")
        class Commands:
            device = {"platform": "ios", "type": "simulator", "id": "sim-a"}
            context = {}
            run_command = staticmethod(command)
        DeviceReadiness(Commands(), pathlib.Path("device-1")).readiness()
        self.assertEqual("simctl", calls[0][1])
        self.assertNotIn("devicectl", calls[0])

    def test_unbooted_simulator_is_rejected(self):
        def command(args, **options):
            return subprocess.CompletedProcess(args, 1, "", "not booted")
        with self.assertRaises(InfrastructureError):
            DeviceTarget({"platform": "ios", "type": "simulator", "id": "sim"}, command).verify_simulator()

    def test_process_match_requires_exact_identifier_and_live_pid(self):
        def command(args, **options):
            return subprocess.CompletedProcess(args, 0, "123\t0\tUIKitApplication:com.example.app[abcd]\n-\t0\tUIKitApplication:com.example.dead[abcd]\n", "")
        target = DeviceTarget({"platform": "ios", "type": "simulator", "id": "sim"}, command)
        self.assertTrue(target.simulator_running("com.example.app"))
        self.assertFalse(target.simulator_running("com.example.ap"))
        self.assertFalse(target.simulator_running("com.example.dead"))


if __name__ == "__main__":
    unittest.main()
