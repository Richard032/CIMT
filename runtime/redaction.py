"""Redaction of configured secrets and sensitive screen regions."""

import io
import json
from PIL import Image, ImageDraw
from errors import InfrastructureError


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

    def text(self, text):
        """Remove known secret values before text is saved or reported."""
        text = str(text)
        for secret in sorted(self.secrets, key=len, reverse=True):
            text = text.replace(secret, "<redacted>")
        return text

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
        value = json.dumps(element)
        return any(secret in value for secret in self.secrets)


class ScreenMasker:
    """Masks sensitive pixels and UI values before evidence can leave memory."""

    def __init__(self, redactor):
        self.redactor = redactor

    def capture(self, raw_elements, image_bytes, size):
        """Return safe UI data and a masked PNG; raw pixels stay in memory."""
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        scale = self._scale(image, size)
        draw = ImageDraw.Draw(image)
        safe = [self._element(element, draw, image, scale) for element in raw_elements]
        output = io.BytesIO()
        image.save(output, format="PNG")
        return safe, output.getvalue()

    @staticmethod
    def _scale(image, size):
        width, height = size["width"], size["height"]
        if width <= 0 or height <= 0:
            raise InfrastructureError("Screen coordinate size is unavailable")
        sx, sy = image.width / width, image.height / height
        if abs(sx / sy - 1) > 0.03:
            raise InfrastructureError("Screen/image coordinate mapping is ambiguous")
        return sx, sy

    def _element(self, element, draw, image, scale):
        item = self.redactor.object(element)
        if self.redactor.sensitive(element):
            self._draw_mask(element, draw, image, scale)
            for key in ["text", "label", "name", "value"]:
                if key in item:
                    item[key] = "<masked>"
        return item

    @staticmethod
    def _draw_mask(element, draw, image, scale):
        try:
            rect = element.get("coordinates", {})
            x, y, width, height = [float(rect[key]) for key in ["x", "y", "width", "height"]]
            if width <= 0 or height <= 0:
                raise ValueError()
        except (KeyError, TypeError, ValueError):
            raise InfrastructureError("Required element mask has no reliable bounds") from None
        sx, sy = scale
        # Add a small border so edge pixels do not reveal a character.
        draw.rectangle(
            (
                max(0, (x - 2) * sx),
                max(0, (y - 2) * sy),
                min(image.width, (x + width + 2) * sx),
                min(image.height, (y + height + 2) * sy),
            ),
            fill="black",
        )
