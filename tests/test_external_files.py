"""External-file transfers use temporary containers and fake device commands."""

import hashlib
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "runtime"))
from device_adapter.external_files import ExternalFiles
from device_adapter.app_lifecycle import AppLifecycle
from errors import DeviceCommandTimeout, InfrastructureError, LimitReached


class ExternalFileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "test.xpa"
        self.source.write_bytes(b"synthetic binary fixture\x00\xff")
        self.container = self.root / "app-data"
        self.container.mkdir()
        self.calls = []
        self.commands = SimpleNamespace(
            device={"platform": "ios", "type": "simulator", "id": "chosen-simulator"},
            context={"externalFiles": [{"source": str(self.source), "platform": "ios", "destination": "Documents/test.xpa"}], "deadline": time.time() + 60},
            env={}, run_command=self.run_command,
        )

    def run_command(self, args, **kwargs):
        self.calls.append(args)
        return subprocess.CompletedProcess(args, 0, str(self.container), "")

    def test_simulator_receives_exact_binary_before_app_launch(self):
        ExternalFiles(self.commands).copy("test.app")
        self.assertEqual(self.source.read_bytes(), (self.container / "Documents/test.xpa").read_bytes())
        self.assertEqual(self.calls[0][3:5], ["chosen-simulator", "test.app"])

    def test_nested_destination_with_spaces_is_supported(self):
        self.commands.context["externalFiles"][0]["destination"] = "Documents/test files/seat memory.xpa"
        ExternalFiles(self.commands).copy("test.app")
        self.assertEqual(self.source.read_bytes(), (self.container / "Documents/test files/seat memory.xpa").read_bytes())

    def test_missing_file_stops_before_any_device_command(self):
        self.source.unlink()
        with self.assertRaises(InfrastructureError):
            ExternalFiles(self.commands).copy("test.app")
        self.assertEqual([], self.calls)

    def test_other_platform_files_are_not_copied(self):
        self.commands.context["externalFiles"][0]["platform"] = "android"
        ExternalFiles(self.commands).copy("test.app")
        self.assertEqual([], self.calls)

    def test_existing_config_without_files_does_nothing(self):
        self.commands.context = {}
        ExternalFiles(self.commands).copy("test.app")
        self.assertEqual([], self.calls)

    def test_container_traversal_is_rejected(self):
        for path in ["../escape.xpa", "/escape.xpa", "Documents/../escape.xpa", "Documents/./xpa", "C:/xpa", "Documents/", "Documents/\n.xpa"]:
            with self.subTest(path=path):
                self.commands.context["externalFiles"][0]["destination"] = path
                with self.assertRaises(InfrastructureError):
                    ExternalFiles(self.commands).copy("test.app")
        self.assertEqual([], self.calls)

    def test_symlink_cannot_redirect_copy_outside_the_container(self):
        outside = self.root / "outside"
        outside.mkdir()
        (self.container / "Documents").symlink_to(outside, target_is_directory=True)
        with self.assertRaises(InfrastructureError):
            ExternalFiles(self.commands).copy("test.app")
        self.assertEqual([], list(outside.iterdir()))

    def test_corrupted_copy_is_rejected(self):
        def corrupt(source, destination):
            Path(destination).write_bytes(b"corrupted")
        with patch("device_adapter.external_files.shutil.copyfile", side_effect=corrupt):
            with self.assertRaisesRegex(InfrastructureError, "verification failed"):
                ExternalFiles(self.commands).copy("test.app")

    def test_failed_command_does_not_expose_output_contents(self):
        self.commands.run_command = lambda *args, **kwargs: subprocess.CompletedProcess(args, 1, "private fixture text", "private details")
        with self.assertRaises(InfrastructureError) as raised:
            ExternalFiles(self.commands).copy("test.app")
        self.assertNotIn("private", str(raised.exception))

    def test_cancellation_stops_before_commands(self):
        def cancel():
            raise LimitReached("cancelled")
        with self.assertRaises(LimitReached):
            ExternalFiles(self.commands, cancel).copy("test.app")
        self.assertEqual([], self.calls)

    def test_timeout_prevents_transfer(self):
        def timeout(args, **kwargs):
            raise subprocess.TimeoutExpired(args, 1)
        self.commands.run_command = timeout
        with self.assertRaises(DeviceCommandTimeout):
            ExternalFiles(self.commands).copy("test.app")

    def test_android_upload_uses_selected_device_and_literal_path(self):
        self.commands.device = {"platform": "android", "id": "phone-serial", "type": "real"}
        entry = self.commands.context["externalFiles"][0]
        entry.update(platform="android", destination="files/seat ' name.xpa")
        requests = []
        def run(args, **kwargs):
            requests.append((args, kwargs))
            return subprocess.CompletedProcess(args, 0, hashlib.sha256(self.source.read_bytes()).hexdigest() + "  fixture", "")
        self.commands.run_command = run
        ExternalFiles(self.commands).copy("test.app")
        self.assertTrue(all(request[0][0:3] == ["adb", "-s", "phone-serial"] for request in requests))
        self.assertEqual(self.source.read_bytes(), requests[1][1]["input"])
        self.assertEqual(entry["destination"], shlex.split(requests[-1][0][-1])[-1])
        self.assertEqual("run-as", shlex.split(requests[-1][0][-1])[0])

    def test_android_hash_mismatch_is_rejected(self):
        self.commands.device = {"platform": "android", "id": "phone-serial"}
        self.commands.context["externalFiles"][0]["platform"] = "android"
        self.commands.run_command = lambda args, **kwargs: subprocess.CompletedProcess(args, 0, "wronghash", "")
        with self.assertRaisesRegex(InfrastructureError, "verification failed"):
            ExternalFiles(self.commands).copy("test.app")

    def test_physical_ios_copy_is_verified_and_temporary_data_removed(self):
        self.commands.device["type"] = "real"
        received = []
        def run(args, **kwargs):
            self.calls.append(args)
            if args[4] == "from":
                target = Path(args[args.index("--destination") + 1])
                target.write_bytes(self.source.read_bytes())
                received.append(target)
            return subprocess.CompletedProcess(args, 0, "", "")
        self.commands.run_command = run
        ExternalFiles(self.commands).copy("test.app")
        self.assertEqual(2, len(self.calls))
        self.assertTrue(all("appDataContainer" in call and "test.app" in call for call in self.calls))
        self.assertFalse(received[0].parent.exists())

    def test_reinstall_seeds_again_after_hooks_and_before_launch(self):
        present = False
        events = []
        def native(args):
            return {"data": [{"packageName": "test.app"}] if present else []}
        def call(name, **kwargs):
            nonlocal present
            if name == "mobile_uninstall_app":
                present = False
                shutil.rmtree(self.container)
                self.container.mkdir()
            if name == "mobile_install_app":
                present = True
            if name == "mobile_launch_app":
                self.assertEqual(self.source.read_bytes(), (self.container / "Documents/test.xpa").read_bytes())
            events.append(name)
        def run(args, **kwargs):
            events.append("copy" if args[0] == "xcrun" else "hook")
            return subprocess.CompletedProcess(args, 0, str(self.container), "")
        self.commands.native = native
        self.commands.run_command = run
        self.commands.context["config"] = {"reset": {"command": ["test-hook"]}}
        lifecycle = AppLifecycle(self.commands, call)
        lifecycle.reset("fixture.app", "test.app", "Debug")
        lifecycle.reset("fixture.app", "test.app", "Debug")
        self.assertEqual(2, events.count("copy"))
        self.assertLess(events.index("hook"), events.index("copy"))
        self.assertLess(events.index("copy"), events.index("mobile_launch_app"))

    def test_transfer_failure_prevents_launch(self):
        present = False
        calls = []
        def call(name, **kwargs):
            nonlocal present
            calls.append(name)
            if name == "mobile_install_app": present = True
        self.commands.native = lambda args: {"data": [{"packageName": "test.app"}] if present else []}
        self.commands.context["config"] = {}
        self.commands.run_command = lambda args, **kwargs: subprocess.CompletedProcess(args, 1, "", "")
        with self.assertRaises(InfrastructureError):
            AppLifecycle(self.commands, call).reset("fixture.app", "test.app", "Debug")
        self.assertNotIn("mobile_launch_app", calls)


if __name__ == "__main__":
    unittest.main()
