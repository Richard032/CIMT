"""Check the lossless capture command without running a device helper."""

import pathlib
import subprocess
import sys
import time
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "runtime"))
from device_commands import NativeDevice
from errors import InfrastructureError
from redaction import Redactor


class RecordingCommand:
    def __init__(self, exit_code=0):
        self.exit_code = exit_code
        self.calls = []

    def __call__(self, arguments, **options):
        self.calls.append((arguments, options))
        return subprocess.CompletedProcess(
            arguments, self.exit_code, b"png fixture", b"synthetic secret"
        )


class NativeScreenshotTests(unittest.TestCase):
    def device(self, command):
        return NativeDevice(
            "helper",
            {"id": "phone-a"},
            {"nativeHome": "/unused", "deadline": time.time() + 30},
            Redactor({"credentials": {"test": {"password": "synthetic secret"}}}),
            command,
        )

    def test_capture_requests_png_to_stdout_for_the_fixed_device(self):
        command = RecordingCommand()
        self.assertEqual(self.device(command).screenshot(), b"png fixture")
        arguments, options = command.calls[0]
        self.assertEqual(
            arguments,
            ["helper", "screenshot", "--format", "png", "--output", "-", "--device", "phone-a"],
        )
        self.assertFalse(options["text"])
        self.assertTrue(options["capture_output"])

    def test_capture_failure_redacts_binary_stderr(self):
        with self.assertRaises(InfrastructureError) as raised:
            self.device(RecordingCommand(exit_code=1)).screenshot()
        self.assertNotIn("synthetic secret", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
