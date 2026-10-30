"""Check observable device changes around a screenshot before releasing pixels."""

from errors import CaptureChanged
from mask_geometry import MaskRectangle, ScreenSize
import json


class CaptureGuard:
    def __init__(self, redactor):
        self.redactor = redactor

    def verify(self, before, after, size_before, size_after):
        first_size, last_size = ScreenSize.read(size_before), ScreenSize.read(size_after)
        if first_size != last_size:
            raise CaptureChanged("Screen coordinate size changed during screenshot capture: "
                + str(first_size.width) + "x" + str(first_size.height) + " -> "
                + str(last_size.width) + "x" + str(last_size.height))
        first, last = self._regions(before), self._regions(after)
        if first != last:
            raise CaptureChanged("Required mask geometry changed during screenshot capture. "
                + self._describe("Before", first) + "; " + self._describe("After", last))

    def _describe(self, label, regions):
        # Coordinates explain the rejected capture. Never include UI text or image pixels.
        sample = [(self.redactor.text(name), x, y, width, height) for name, x, y, width, height in regions[:10]]
        return label + " regions=" + str(len(regions)) + " (identifier,x,y,width,height; first 10): " + json.dumps(sample)

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
