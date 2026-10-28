"""Redaction of configured secrets and sensitive screen regions."""

import json
import re
from PIL import ImageDraw
from record_redaction import RecordRedactor
from mask_geometry import MaskGeometry
from screenshot_image import ScreenshotImage


class Redactor:
    """Finds secret text and identifies UI elements that need a mask."""

    def __init__(self, config):
        self.secrets = set()

        def visit(value, sensitive=False):
            if isinstance(value, dict):
                for key, item in value.items():
                    visit(
                        item,
                        sensitive
                        or key == "credentials"
                        or any(x in key.lower() for x in ["pass", "secret", "token", "key"]),
                    )
            elif isinstance(value, list):
                for item in value:
                    visit(item, sensitive)
            elif sensitive and str(value):
                self.secrets.add(str(value))

        visit(config)
        self.ids = {rule["element-id"] for rule in config.get("masking", {}).get("rules", [])}
        self.records = RecordRedactor(self)
        # Match once so replacements cannot damage each other or an existing marker.
        spellings = set()
        for secret in self.secrets:
            spellings.update(self._spellings(secret))
        if spellings:
            spellings.add("<redacted>")
        choices = [re.escape(secret) for secret in sorted(spellings, key=len, reverse=True)]
        self.pattern = re.compile("|".join(choices)) if choices else None

    @staticmethod
    def _spellings(secret):
        escaped = json.dumps(secret)[1:-1]
        return [
            secret,
            escaped,
            json.dumps(secret, ensure_ascii=False)[1:-1],
            re.sub(r"\\u[0-9a-fA-F]{4}", lambda match: "\\u" + match[0][2:].upper(), escaped),
        ]

    def text(self, text):
        """Remove known secret values before text is saved or reported."""
        text = str(text)
        return self.pattern.sub("<redacted>", text) if self.pattern else text

    def object(self, value):
        """Copy nested data while removing secret values from its strings."""
        if isinstance(value, dict):
            return {key: self.object(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self.object(item) for item in value]
        return self.text(value) if isinstance(value, str) else value

    def sensitive(self, element):
        """Decide whether an element needs masking before its image is used."""
        if element.get("identifier") in self.ids:
            return True
        if any(
            x in (element.get("identifier", "") + element.get("type", "")).lower()
            for x in ["password", "securetext", "token", "secret"]
        ):
            return True
        return self.contains_secret(element)

    def contains_secret(self, value):
        """Inspect original strings. JSON escaping must not hide a required pixel mask."""
        if isinstance(value, dict):
            return any(self.contains_secret(item) for item in value.values())
        if isinstance(value, list):
            return any(self.contains_secret(item) for item in value)
        return isinstance(value, str) and any(secret in value for secret in self.secrets)


class ScreenMasker:
    """Masks sensitive pixels and UI values before evidence can leave memory."""

    def __init__(self, redactor):
        self.redactor = redactor

    def capture(self, raw_elements, image_bytes, size):
        """Return safe UI data and a masked PNG; raw pixels stay in memory."""
        image = ScreenshotImage.decode(image_bytes)
        geometry = MaskGeometry(size, image.size)
        draw = ImageDraw.Draw(image)
        masks = self._regions(raw_elements, geometry)
        for mask in masks:
            draw.rectangle(mask, fill="black")
        safe = [self._element(element, geometry, masks) for element in raw_elements]
        return safe, ScreenshotImage.encode(image)

    def _regions(self, elements, geometry):
        masks = []
        for element in elements:
            if self.redactor.sensitive(element):
                pixels = geometry.pixels(element)
                if pixels is not None:
                    masks.append(pixels)
        return masks

    def _element(self, element, geometry, masks):
        item = self.redactor.records.element(element)
        # A container mask also hides the text of overlapping child elements.
        if self.redactor.sensitive(element) or geometry.touches_mask(element, masks):
            item = self._mask_text(item)
        return item

    @staticmethod
    def _mask_text(value):
        if isinstance(value, dict):
            return {
                key: (
                    "<masked>"
                    if key in ["text", "label", "name", "value"]
                    else ScreenMasker._mask_text(item)
                )
                for key, item in value.items()
            }
        if isinstance(value, list):
            return [ScreenMasker._mask_text(item) for item in value]
        return value
