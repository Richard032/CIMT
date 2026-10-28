"""Test evidence boundaries using in-memory pictures and small fake services."""

import base64
import io
import json
import pathlib
import sys
import unittest
from types import SimpleNamespace

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "runtime"))

from PIL import Image
from crashes import CrashRecovery, StartupGuard, TerminationObservation
from errors import InfrastructureError
from redaction import Redactor, ScreenMasker
from screen_capture import ScreenCapture

SECRET_FIELD = {
    "identifier": "Password",
    "value": "private fixture",
    "coordinates": {"x": 10, "y": 10, "width": 20, "height": 20},
}


class CaptureFixture:
    """Supply two UI reads around one screenshot. No image is written to disk."""

    def __init__(self, before, after):
        self.reads = iter([before, after])
        self.mask_calls = 0
        self.redactor = Redactor({"masking": {"rules": [{"element-id": "Password"}]}})
        self.masker = ScreenMasker(self.redactor)
        stream = io.BytesIO()
        Image.new("RGB", (100, 100), "white").save(stream, format="PNG")
        self.image = stream.getvalue()
        self.screen = ScreenCapture(self.call, self.native, lambda: None, self.redactor, self)

    def call(self, name, **arguments):
        if name == "mobile_take_screenshot":
            return {"content": [{"type": "image", "data": base64.b64encode(self.image).decode()}]}
        return {"content": [{"type": "text", "text": json.dumps(next(self.reads))}]}

    def native(self, arguments):
        return {"data": {"device": {"screenSize": {"width": 100, "height": 100}}}}

    def capture(self, elements, image, size):
        self.mask_calls += 1
        return self.masker.capture(elements, image, size)


class CaptureRaceTests(unittest.TestCase):
    def test_appearing_secret_stops_before_image_can_leave_capture(self):
        fixture = CaptureFixture([], [SECRET_FIELD])
        with self.assertRaises(InfrastructureError):
            fixture.screen.snapshot()
        self.assertEqual(fixture.mask_calls, 0)

    def test_disappearing_secret_stops_capture(self):
        fixture = CaptureFixture([SECRET_FIELD], [])
        with self.assertRaises(InfrastructureError):
            fixture.screen.snapshot()
        self.assertEqual(fixture.mask_calls, 0)

    def test_unchanged_secret_is_masked(self):
        fixture = CaptureFixture([SECRET_FIELD], [SECRET_FIELD])
        elements, encoded = fixture.screen.snapshot()
        self.assertEqual(elements[0]["value"], "<masked>")
        with Image.open(io.BytesIO(encoded)) as image:
            self.assertEqual(image.getpixel((15, 15)), (0, 0, 0))

    def test_unchanged_screen_without_secrets_can_be_captured(self):
        fixture = CaptureFixture([], [])
        _, encoded = fixture.screen.snapshot()
        self.assertEqual(fixture.mask_calls, 1)
        self.assertTrue(encoded)


class CrashFixture:
    """A known termination with separately controlled capture and storage errors."""

    def __init__(self, capture_error=False, storage_error=False, crashed=True):
        self.crashed = crashed
        self.capture_error = capture_error
        self.storage_error = storage_error
        self.published_crashes = []
        self.session = SimpleNamespace(
            app_id="com.fixture.app",
            executable="app",
            elements=[],
            image=b"masked",
            history=[],
            result={"crashes": [], "steps": [], "remaining": [], "verdict": "inconclusive"},
        )
        self.recovery = CrashRecovery(self, self, self, Redactor({}), self.publish)

    def observe(self):
        return TerminationObservation(
            "home" if self.crashed else "com.fixture.app",
            self.crashed,
            [{"exceptionType": "fixture"}] if self.crashed else [],
        )

    def snapshot(self):
        if self.capture_error:
            raise InfrastructureError("capture unavailable")
        return [], b"masked"

    def save_step(self, step, elements, image):
        if self.storage_error:
            raise OSError("storage unavailable")
        return {"screenshot": "safe.png"}

    def save_image(self, name, image):
        if self.storage_error:
            raise OSError("storage unavailable")
        return "safe.png"

    def publish(self):
        self.published_crashes.append(len(self.session.result["crashes"]))

    def call(self, name, **arguments):
        pass

    def foreground(self):
        return "home"

    def running(self, app_id, executable):
        return False

    def run_action(self, entry):
        return self.recovery.after_action(self.session, entry, {"action": "tap"}, {}, "point")


class CrashEvidenceTests(unittest.TestCase):
    def test_known_crash_is_published_before_failed_capture(self):
        fixture = CrashFixture(capture_error=True)
        entry = {"step": 1}
        with self.assertRaises(InfrastructureError):
            fixture.run_action(entry)
        self.assertEqual(fixture.published_crashes, [1])
        self.assertEqual(fixture.session.result["verdict"], "failed")
        self.assertIn("evidenceError", entry)

    def test_known_crash_survives_failed_image_storage(self):
        fixture = CrashFixture(storage_error=True)
        with self.assertRaises(OSError):
            fixture.run_action({"step": 1})
        self.assertEqual(len(fixture.session.result["crashes"]), 1)
        self.assertEqual(fixture.published_crashes, [1])

    def test_failed_capture_without_a_crash_does_not_invent_a_finding(self):
        fixture = CrashFixture(capture_error=True, crashed=False)
        with self.assertRaises(InfrastructureError):
            fixture.run_action({"step": 1})
        self.assertEqual(fixture.session.result["crashes"], [])
        self.assertEqual(fixture.session.result["verdict"], "inconclusive")

    def test_startup_crash_is_published_before_failed_storage(self):
        fixture = CrashFixture(storage_error=True)
        guard = StartupGuard(fixture, fixture, fixture.publish)
        with self.assertRaises(OSError):
            guard.check(fixture.session)
        self.assertEqual(fixture.session.result["verdict"], "failed")
        self.assertEqual(fixture.published_crashes, [1, 1])


if __name__ == "__main__":
    unittest.main()
