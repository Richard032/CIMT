"""Decode screenshots into a clean canvas without hidden image data."""

import io
from PIL import Image
from errors import InfrastructureError


class ScreenshotImage:
    @staticmethod
    def decode(encoded):
        try:
            with Image.open(io.BytesIO(encoded)) as source:
                if source.format != "PNG" or getattr(source, "n_frames", 1) != 1:
                    raise InfrastructureError("Masking requires a single-frame lossless PNG")
                if source.getexif().get(274, 1) != 1:
                    raise InfrastructureError("Screenshot orientation does not match its pixels")
                source.load()
                # A fresh opaque canvas discards metadata and hidden transparent RGB values.
                canvas = Image.new("RGBA", source.size, (0, 0, 0, 255))
                canvas.alpha_composite(source.convert("RGBA"))
                return canvas.convert("RGB")
        except (OSError, TypeError, ValueError):
            raise InfrastructureError("Screenshot image could not be verified") from None

    @staticmethod
    def encode(image):
        output = io.BytesIO()
        image.save(output, format="PNG")
        return output.getvalue()
