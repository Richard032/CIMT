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
from errors import InfrastructureError, LimitReached
from redaction import Redactor, ScreenMasker
from screen_capture import ScreenCapture

SECRET_FIELD = {
    "identifier": "Password",
    "value": "private fixture",
    "coordinates": {"x": 10, "y": 10, "width": 20, "height": 20},
}


class CaptureFixture:
    """Supply UI reads around fresh screenshots. No image is written to disk."""

    def __init__(self, before, after):
        self.reads = iter([before, after] * ScreenCapture.MAX_ATTEMPTS)
        self.mask_calls = 0
        self.image_calls = 0
        self.redactor = Redactor({"masking": {"rules": [{"element-id": "Password"}]}})
        self.masker = ScreenMasker(self.redactor)
        stream = io.BytesIO()
        Image.new("RGB", (100, 100), "white").save(stream, format="PNG")
        self.image = stream.getvalue()
        self.screen = ScreenCapture(self.call, self.native, lambda: None, self.redactor, self,
            sleep=lambda _: None)

    def call(self, name, **arguments):
        if name == "mobile_take_screenshot":
            self.image_calls += 1
            return {"content": [{"type": "image", "data": base64.b64encode(self.image).decode()}]}
        return {"content": [{"type": "text", "text": json.dumps(next(self.reads))}]}

    def native(self, arguments):
        return {"data": {"device": {"screenSize": {"width": 100, "height": 100}}}}

    def capture(self, elements, image, size):
        self.mask_calls += 1
        return self.masker.capture(elements, image, size)


class CaptureRaceTests(unittest.TestCase):
    def test_injected_lossless_reader_bypasses_the_adapter_image_tool(self):
        fixture = CaptureFixture([SECRET_FIELD], [SECRET_FIELD])

        def call(name, **arguments):
            self.assertEqual(name, "mobile_list_elements_on_screen")
            return fixture.call(name, **arguments)

        screen = ScreenCapture(
            call,
            fixture.native,
            lambda: None,
            fixture.redactor,
            fixture,
            image_reader=lambda: fixture.image,
        )
        _, encoded = screen.snapshot()
        with Image.open(io.BytesIO(encoded)) as image:
            self.assertEqual(image.getpixel((15, 15)), (0, 0, 0))

    def test_generic_tolerance_keeps_secret_pixels_masked(self):
        fixture = CaptureFixture([SECRET_FIELD], [SECRET_FIELD])
        output = io.BytesIO()
        Image.new("RGB", (1178, 2556), "white").save(output, format="PNG")
        fixture.image = output.getvalue()
        fixture.screen.native = lambda _: {"data": {"device": {
            "screenSize": {"width": 393, "height": 852}
        }}}
        elements, encoded = fixture.screen.snapshot()
        self.assertEqual(elements[0]["value"], "<masked>")
        with Image.open(io.BytesIO(encoded)) as image:
            self.assertEqual(image.getpixel((30, 30)), (0, 0, 0))
            self.assertEqual(image.getpixel((89, 89)), (0, 0, 0))
            self.assertEqual(image.getpixel((100, 100)), (255, 255, 255))

    def test_size_change_stops_before_pixels_are_released(self):
        fixture = CaptureFixture([], [])
        sizes = iter([100, 200] * ScreenCapture.MAX_ATTEMPTS)

        def native(arguments):
            return {"data": {"device": {"screenSize": {"width": next(sizes), "height": 100}}}}

        screen = ScreenCapture(fixture.call, native, lambda: None, fixture.redactor, fixture,
            sleep=lambda _: None)
        with self.assertRaises(InfrastructureError):
            screen.snapshot()
        self.assertEqual(fixture.mask_calls, 0)

    def test_appearing_secret_stops_before_image_can_leave_capture(self):
        fixture = CaptureFixture([], [SECRET_FIELD])
        with self.assertRaisesRegex(InfrastructureError, "No verified screenshot after 3"):
            fixture.screen.snapshot()
        self.assertEqual(fixture.mask_calls, 0)
        self.assertEqual(fixture.image_calls, 3)

    def test_disappearing_secret_stops_capture(self):
        fixture = CaptureFixture([SECRET_FIELD], [])
        with self.assertRaises(InfrastructureError):
            fixture.screen.snapshot()
        self.assertEqual(fixture.mask_calls, 0)

    def test_permission_dialog_is_captured_after_the_transition_settles(self):
        dialog = {"type": "Alert", "label": "Allow Bluetooth?"}
        fixture = CaptureFixture([SECRET_FIELD], [dialog])
        fixture.reads = iter([[SECRET_FIELD], [dialog], [dialog], [dialog]])
        retries = []
        fixture.screen.on_retry = lambda attempt, error: retries.append(attempt)
        elements, encoded = fixture.screen.snapshot()
        self.assertEqual(elements[0], dialog)
        self.assertTrue(encoded)
        self.assertEqual(retries, [1])
        self.assertEqual(fixture.image_calls, 2)
        self.assertEqual(fixture.mask_calls, 1)

    def test_retry_masks_a_sensitive_field_that_appeared(self):
        fixture = CaptureFixture([], [SECRET_FIELD])
        fixture.reads = iter([[], [SECRET_FIELD], [SECRET_FIELD], [SECRET_FIELD]])
        elements, encoded = fixture.screen.snapshot()
        self.assertEqual(elements[0]["value"], "<masked>")
        with Image.open(io.BytesIO(encoded)) as image:
            self.assertEqual(image.getpixel((15, 15)), (0, 0, 0))
        self.assertEqual(fixture.mask_calls, 1)

    def test_retry_returns_the_fresh_image_instead_of_the_rejected_frame(self):
        fixture = CaptureFixture([], [SECRET_FIELD])
        fixture.reads = iter([[], [SECRET_FIELD], [], []])
        stream = io.BytesIO()
        Image.new("RGB", (100, 100), "red").save(stream, format="PNG")
        frames = iter([stream.getvalue(), fixture.image])
        fixture.screen.image_reader = lambda: next(frames)
        _, encoded = fixture.screen.snapshot()
        with Image.open(io.BytesIO(encoded)) as image:
            self.assertEqual(image.getpixel((70, 70)), (255, 255, 255))

    def test_invalid_required_bounds_are_not_retried(self):
        invalid = dict(SECRET_FIELD, coordinates=None)
        fixture = CaptureFixture([invalid], [invalid])
        retries = []
        fixture.screen.on_retry = lambda *args: retries.append(args)
        with self.assertRaisesRegex(InfrastructureError, "no reliable bounds"):
            fixture.screen.snapshot()
        self.assertFalse(retries)
        self.assertEqual(fixture.image_calls, 1)
        self.assertEqual(fixture.mask_calls, 0)

    def test_run_deadline_stops_before_another_capture(self):
        fixture = CaptureFixture([], [SECRET_FIELD])
        now = [0]
        waits = []
        fixture.screen.clock = lambda: now[0]
        fixture.screen.deadline = 0.1

        def wait(seconds):
            waits.append(seconds)
            now[0] += seconds

        fixture.screen.sleep = wait
        with self.assertRaisesRegex(LimitReached, "Whole-run time limit"):
            fixture.screen.snapshot()
        self.assertEqual(waits, [0.1])
        self.assertEqual(fixture.image_calls, 1)
        self.assertEqual(fixture.mask_calls, 0)

    def test_device_lock_is_not_retried(self):
        fixture = CaptureFixture([], [])

        def locked():
            raise LimitReached("iPhone is locked")

        fixture.screen.readiness = locked
        with self.assertRaisesRegex(LimitReached, "locked"):
            fixture.screen.snapshot()
        self.assertEqual(fixture.image_calls, 0)

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

    def test_container_mask_hides_child_ui_text(self):
        child = {
            "identifier": "Child",
            "text": "unknown private text",
            "coordinates": {"x": 12, "y": 12, "width": 10, "height": 10},
        }
        fixture = CaptureFixture([SECRET_FIELD, child], [SECRET_FIELD, child])
        elements, _ = fixture.screen.snapshot()
        self.assertEqual(elements[1]["text"], "<masked>")

    def test_offscreen_sensitive_field_keeps_text_hidden_without_a_pixel_mask(self):
        item = dict(SECRET_FIELD, coordinates=dict(x=120, y=10, width=20, height=20))
        fixture = CaptureFixture([item], [item])
        elements, encoded = fixture.screen.snapshot()
        self.assertEqual(elements[0]["value"], "<masked>")
        with Image.open(io.BytesIO(encoded)) as image:
            self.assertEqual(image.getpixel((15, 15)), (255, 255, 255))

    def test_text_outside_the_mask_is_still_available(self):
        label = {
            "identifier": "Public",
            "text": "Public text",
            "coordinates": {"x": 70, "y": 70, "width": 10, "height": 10},
        }
        fixture = CaptureFixture([SECRET_FIELD, label], [SECRET_FIELD, label])
        elements, _ = fixture.screen.snapshot()
        self.assertEqual(elements[1]["text"], "Public text")

    def test_ui_text_without_bounds_is_hidden_when_masks_are_present(self):
        label = {"identifier": "Unknown", "text": "unknown private text"}
        fixture = CaptureFixture([SECRET_FIELD, label], [SECRET_FIELD, label])
        elements, _ = fixture.screen.snapshot()
        self.assertEqual(elements[1]["text"], "<masked>")


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
