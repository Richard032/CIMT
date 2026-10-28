"""Capture checks compare observable frame data without any image or API call."""

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "runtime"))
from capture_guard import CaptureGuard
from errors import InfrastructureError
from redaction import Redactor

SIZE = dict(width=100, height=100)


def field(identifier="Password", x=10):
    return dict(identifier=identifier, coordinates=dict(x=x, y=10, width=10, height=10))


class CaptureGuardTests(unittest.TestCase):
    def setUp(self):
        self.guard = CaptureGuard(Redactor({"masking": {"rules": [{"element-id": "Password"}]}}))

    def test_size_change_stops_even_without_sensitive_fields(self):
        with self.assertRaises(InfrastructureError):
            self.guard.verify([], [], SIZE, dict(width=200, height=100))

    def test_element_reordering_does_not_change_the_mask(self):
        first, second = field(x=10), field(x=30)
        self.guard.verify([first, second], [second, first], SIZE, SIZE)

    def test_an_added_duplicate_region_is_still_a_change(self):
        with self.assertRaises(InfrastructureError):
            self.guard.verify([field()], [field(), field()], SIZE, SIZE)

    def test_equivalent_numeric_coordinates_match(self):
        self.guard.verify([field(x="10")], [field(x=10)], SIZE, SIZE)

    def test_unchanged_invalid_bounds_still_stop(self):
        with self.assertRaises(InfrastructureError):
            self.guard.verify([field(x=float("nan"))], [field(x=float("nan"))], SIZE, SIZE)


if __name__ == "__main__":
    unittest.main()
