"""Collects only masked screenshots and UI elements."""

import base64
import io
import json
from PIL import Image
from errors import InfrastructureError


class ScreenCapture:
    """Keeps raw pixels in memory until masking has succeeded."""

    def __init__(self, call, native, readiness, redactor, masker):
        self.call = call
        self.native = native
        self.readiness = readiness
        self.redactor = redactor
        self.masker = masker

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
                    if isinstance(value, list):
                        return value
        raise InfrastructureError("No structured UI elements were returned")

    def snapshot(self):
        """Capture a screen only when device readiness and mask positions are verified."""
        self.readiness()
        raw = self.raw_elements()
        image = self._image()
        size = (
            self.native(["device", "info"]).get("data", {}).get("device", {}).get("screenSize", {})
        )
        raw = self._verify_mask_geometry(raw)
        safe, encoded = self.masker.capture(raw, image, size)
        self._add_screen_size(safe, encoded, size)
        return safe, encoded

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

    def _verify_mask_geometry(self, before):
        if not any(self.redactor.sensitive(element) for element in before):
            return before
        after = self.raw_elements()
        if self._mask_regions(before) != self._mask_regions(after):
            raise InfrastructureError("Required mask geometry changed during screenshot capture")
        return after

    def _mask_regions(self, elements):
        return [
            (element.get("identifier"), element.get("coordinates"))
            for element in elements
            if self.redactor.sensitive(element)
        ]

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
