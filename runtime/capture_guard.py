"""Check observable device changes around a screenshot before releasing pixels."""

from errors import InfrastructureError
from mask_geometry import MaskRectangle, ScreenSize


class CaptureGuard:
    def __init__(self, redactor):
        self.redactor = redactor

    def verify(self, before, after, size_before, size_after):
        if ScreenSize.read(size_before) != ScreenSize.read(size_after):
            raise InfrastructureError("Screen coordinate size changed during screenshot capture")
        if self._regions(before) != self._regions(after):
            raise InfrastructureError("Required mask geometry changed during screenshot capture")

    def _regions(self, elements):
        regions = []
        for element in elements:
            if self.redactor.sensitive(element):
                rect = MaskRectangle.read(element)
                regions.append(
                    (str(element.get("identifier", "")), rect.x, rect.y, rect.width, rect.height)
                )
        # Adapter ordering is not a geometry change. Duplicate regions still count separately.
        return sorted(regions)
