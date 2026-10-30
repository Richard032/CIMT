"""Collects only masked screenshots and UI elements."""

import base64
import io
import json
import time
from PIL import Image
from errors import CaptureChanged, InfrastructureError, LimitReached
from capture_guard import CaptureGuard
from mask_geometry import ScreenSize


class ScreenCapture:
    """Keeps raw pixels in memory until masking has succeeded."""

    MAX_ATTEMPTS = 3
    RETRY_DELAY_SECONDS = 0.25

    def __init__(self, call, native, readiness, redactor, masker, image_reader=None,
                 deadline=None, sleep=time.sleep, clock=time.time, on_retry=None):
        self.call = call
        self.native = native
        self.readiness = readiness
        self.redactor = redactor
        self.masker = masker
        self.image_reader = image_reader or self._image
        self.guard = CaptureGuard(redactor)
        self.deadline = deadline
        self.sleep = sleep
        self.clock = clock
        self.on_retry = on_retry

    def raw_elements(self):
        """Read UI data from the adapter without saving the unredacted response."""
        result = self.call("mobile_list_elements_on_screen", format="json")
        for content in result.get("content", []):
            if content.get("type") == "text":
                text = content.get("text", "")
                start = text.find("[")
                if start >= 0:
                    try:
                        value = json.loads(text[start:])
                    except ValueError:
                        continue
                    if isinstance(value, list) and all(isinstance(item, dict) for item in value):
                        return value
        raise InfrastructureError("No structured UI elements were returned")

    def snapshot(self):
        """Capture a screen only when device readiness and mask positions are verified."""
        for attempt in range(1, self.MAX_ATTEMPTS + 1):
            self._check_deadline()
            try:
                return self._capture_once()
            except CaptureChanged as error:
                # Discard changing frames. Never save or send them without verified masks.
                if attempt == self.MAX_ATTEMPTS:
                    raise InfrastructureError(
                        "No verified screenshot after " + str(attempt)
                        + " capture attempts. Last change: " + str(error)
                    ) from error
                if self.on_retry:
                    self.on_retry(attempt, error)
                self._wait_for_screen()

    def _capture_once(self):
        """Validate and mask one fresh image, with UI checks on both sides."""
        self.readiness()
        size = self._size()
        raw = self.raw_elements()
        image = self.image_reader()
        after = self.raw_elements()
        self.guard.verify(raw, after, size, self._size())
        self.readiness()
        raw = after
        safe, encoded = self.masker.capture(raw, image, size)
        self._add_screen_size(safe, encoded, size)
        return safe, encoded

    def _check_deadline(self):
        if self.deadline is not None and self.clock() >= self.deadline:
            raise LimitReached("Whole-run time limit reached during screenshot capture")

    def _wait_for_screen(self):
        self._check_deadline()
        delay = self.RETRY_DELAY_SECONDS
        if self.deadline is not None:
            delay = min(delay, max(0, self.deadline - self.clock()))
        self.sleep(delay)

    def _size(self):
        value = (
            self.native(["device", "info"]).get("data", {}).get("device", {}).get("screenSize", {})
        )
        size = ScreenSize.read(value)
        return dict(width=size.width, height=size.height)

    def _image(self):
        result = self.call("mobile_take_screenshot")
        image = next(
            (
                base64.b64decode(item["data"])
                for item in result.get("content", [])
                if item.get("type") == "image"
            ),
            None,
        )
        if not image:
            raise InfrastructureError("Step screenshot collection failed")
        return image

    @staticmethod
    def _add_screen_size(elements, encoded, size):
        with Image.open(io.BytesIO(encoded)) as picture:
            elements.append(
                {
                    "type": "CimtScreenInfo",
                    "screenWidth": size["width"],
                    "screenHeight": size["height"],
                    "imageWidth": picture.width,
                    "imageHeight": picture.height,
                }
            )
