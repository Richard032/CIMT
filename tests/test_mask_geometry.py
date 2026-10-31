"""Coordinate tests use small numbers, without images or physical devices."""

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "runtime"))
from errors import InfrastructureError
from mask_geometry import MaskGeometry, MaskRectangle, ScreenSize


def element(x=10, y=10, width=10, height=10):
    return {"coordinates": dict(x=x, y=y, width=width, height=height)}


class MaskGeometryTests(unittest.TestCase):
    def setUp(self):
        self.geometry = MaskGeometry(dict(width=100, height=100), (100, 100))

    def test_mask_has_two_pixel_border(self):
        self.assertEqual(self.geometry.pixels(element()), (8, 8, 22, 22))

    def test_fractional_edges_round_outward(self):
        self.assertEqual(
            self.geometry.pixels(element(x=10.9, y=10.2, width=3, height=3)), (8, 8, 16, 16)
        )

    def test_double_pixel_density_scales_the_bounds(self):
        geometry = MaskGeometry(dict(width=100, height=100), (200, 200))
        self.assertEqual(geometry.pixels(element()), (18, 18, 42, 42))

    def test_downscaled_image_still_has_a_full_pixel_border(self):
        geometry = MaskGeometry(dict(width=1000, height=1000), (100, 100))
        self.assertEqual(
            geometry.pixels(element(x=100.5, y=100.5, width=1, height=1)), (8, 8, 13, 13)
        )

    def test_partly_visible_rectangle_is_clipped(self):
        self.assertEqual(self.geometry.pixels(element(x=-5)), (0, 8, 7, 22))

    def test_extreme_partial_rectangle_is_clipped_before_pixel_scaling(self):
        self.assertEqual(self.geometry.pixels(element(x=-1e308, width=1.1e308)), (0, 8, 99, 22))

    def test_mask_at_screen_edge_is_clipped(self):
        self.assertEqual(self.geometry.pixels(element(x=95, width=5)), (93, 8, 99, 22))

    def test_completely_offscreen_rectangle_has_no_pixels(self):
        self.assertIsNone(self.geometry.pixels(element(x=101)))

    def test_missing_rectangle_stops(self):
        with self.assertRaises(InfrastructureError):
            self.geometry.pixels({})

    def test_zero_width_stops(self):
        with self.assertRaises(InfrastructureError):
            self.geometry.pixels(element(width=0))

    def test_negative_height_stops(self):
        with self.assertRaises(InfrastructureError):
            self.geometry.pixels(element(height=-1))

    def test_nan_coordinate_stops(self):
        with self.assertRaises(InfrastructureError):
            self.geometry.pixels(element(x=float("nan")))

    def test_infinite_width_stops(self):
        with self.assertRaises(InfrastructureError):
            self.geometry.pixels(element(width=float("inf")))

    def test_overflowed_edge_stops(self):
        with self.assertRaises(InfrastructureError):
            MaskRectangle.read(element(x=1e308, width=1e308))

    def test_boolean_coordinate_stops(self):
        with self.assertRaises(InfrastructureError):
            self.geometry.pixels(element(x=True))

    def test_nan_screen_size_stops(self):
        with self.assertRaises(InfrastructureError):
            ScreenSize.read(dict(width=float("nan"), height=100))

    def test_missing_screen_size_stops(self):
        with self.assertRaises(InfrastructureError):
            ScreenSize.read({})

    def test_rotated_frame_stops(self):
        with self.assertRaises(InfrastructureError):
            MaskGeometry(dict(width=100, height=200), (200, 100))

    def test_distortion_over_five_percent_stops(self):
        with self.assertRaises(InfrastructureError):
            MaskGeometry(dict(width=100, height=100), (100, 106))

    def test_observed_simulator_rounding_is_accepted_without_platform_metadata(self):
        geometry = MaskGeometry(dict(width=393, height=852), (1178, 2556))
        self.assertEqual((0, 0, 1177, 2555), geometry.pixels(element(x=0, y=0, width=393, height=852)))

    def test_positive_five_percent_boundary_is_accepted(self):
        MaskGeometry(dict(width=100, height=100), (105, 100))

    def test_negative_five_percent_boundary_is_accepted(self):
        MaskGeometry(dict(width=100, height=100), (95, 100))

    def test_above_positive_five_percent_boundary_is_rejected(self):
        with self.assertRaises(InfrastructureError):
            MaskGeometry(dict(width=100, height=100), (106, 100))

    def test_below_negative_five_percent_boundary_is_rejected(self):
        with self.assertRaises(InfrastructureError):
            MaskGeometry(dict(width=100, height=100), (94, 100))

    def test_uniform_downscale_uses_the_same_relative_tolerance(self):
        MaskGeometry(dict(width=1000, height=1000), (105, 100))

    def test_accepted_distortion_expands_the_mask_for_both_scales(self):
        geometry = MaskGeometry(dict(width=100, height=100), (105, 100))
        self.assertEqual((3, 3, 28, 27), geometry.pixels(element()))

    def test_large_aspect_mismatch_is_not_hidden_by_small_point_dimensions(self):
        with self.assertRaises(InfrastructureError):
            MaskGeometry(dict(width=1, height=1), (100, 150))

    def test_non_finite_scale_stops(self):
        with self.assertRaises(InfrastructureError):
            MaskGeometry(dict(width=1e-308, height=1e-308), (100, 100))


if __name__ == "__main__":
    unittest.main()
