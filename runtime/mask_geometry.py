"""Validate device bounds and map them to complete screenshot pixels."""

import math
from dataclasses import dataclass
from errors import InfrastructureError


def finite_number(value):
    """Reject missing, boolean, and non-finite coordinates without exposing their values."""
    try:
        if isinstance(value, bool):
            raise ValueError()
        number = float(value)
        if not math.isfinite(number):
            raise ValueError()
        return number
    except (TypeError, ValueError, OverflowError):
        raise InfrastructureError("Required mask geometry is not finite numeric data") from None


@dataclass(frozen=True)
class ScreenSize:
    width: float
    height: float

    @staticmethod
    def read(value):
        if not isinstance(value, dict):
            raise InfrastructureError("Screen coordinate size is unavailable")
        width, height = finite_number(value.get("width")), finite_number(value.get("height"))
        if width <= 0 or height <= 0:
            raise InfrastructureError("Screen coordinate size is unavailable")
        return ScreenSize(width, height)


@dataclass(frozen=True)
class MaskRectangle:
    x: float
    y: float
    width: float
    height: float

    @staticmethod
    def read(element):
        rect = element.get("coordinates")
        if not isinstance(rect, dict):
            raise InfrastructureError("Required element mask has no reliable bounds")
        values = [finite_number(rect.get(key)) for key in ["x", "y", "width", "height"]]
        result = MaskRectangle(*values)
        if result.width <= 0 or result.height <= 0:
            raise InfrastructureError("Required element mask has no reliable bounds")
        finite_number(result.x + result.width)
        finite_number(result.y + result.height)
        return result


class MaskGeometry:
    """Owns the coordinate transform, clipping, and outward rounding only."""

    def __init__(self, size, image_size):
        self.screen = ScreenSize.read(size)
        self.width, self.height = image_size
        if self.width <= 0 or self.height <= 0:
            raise InfrastructureError("Screenshot dimensions are unavailable")
        self.sx = finite_number(self.width / self.screen.width)
        self.sy = finite_number(self.height / self.screen.height)
        # Allow at most one pixel of rounding, not an arbitrary percentage of the screen.
        if abs(self.sx - self.sy) * max(self.screen.width, self.screen.height) > 1 + 1e-9:
            raise InfrastructureError("Screen/image coordinate mapping is ambiguous")

    def pixels(self, element):
        rect = MaskRectangle.read(element)
        if (
            rect.x >= self.screen.width
            or rect.y >= self.screen.height
            or rect.x + rect.width <= 0
            or rect.y + rect.height <= 0
        ):
            # A valid offscreen field has no visible pixels. Its UI text is still hidden.
            return None
        # Round away from the text and add two image pixels on every side.
        left, top = max(0, rect.x), max(0, rect.y)
        right = min(self.screen.width, rect.x + rect.width)
        bottom = min(self.screen.height, rect.y + rect.height)
        return (
            max(0, math.floor(left * self.sx) - 2),
            max(0, math.floor(top * self.sy) - 2),
            min(self.width - 1, math.ceil(right * self.sx) + 2),
            min(self.height - 1, math.ceil(bottom * self.sy) + 2),
        )

    def touches_mask(self, element, masks):
        if not masks:
            return False
        try:
            rect = MaskRectangle.read(element)
        except InfrastructureError:
            # Without bounds, do not risk returning text from inside a masked container.
            return True
        left, top = rect.x * self.sx, rect.y * self.sy
        right, bottom = (rect.x + rect.width) * self.sx, (rect.y + rect.height) * self.sy
        return any(
            left <= mask[2] and right >= mask[0] and top <= mask[3] and bottom >= mask[1]
            for mask in masks
        )
