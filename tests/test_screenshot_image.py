"""Image tests keep all input pixels in memory and use invented metadata."""

import io
import pathlib
import sys
import unittest
from PIL import Image, PngImagePlugin

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "runtime"))
from errors import InfrastructureError
from screenshot_image import ScreenshotImage


def encoded(image, format="PNG", **options):
    output = io.BytesIO()
    image.save(output, format=format, **options)
    return output.getvalue()


class ScreenshotImageTests(unittest.TestCase):
    def test_opaque_pixels_are_preserved(self):
        result = ScreenshotImage.decode(encoded(Image.new("RGB", (20, 20), "red")))
        self.assertEqual(result.getpixel((10, 10)), (255, 0, 0))

    def test_transparent_hidden_rgb_does_not_become_visible(self):
        result = ScreenshotImage.decode(encoded(Image.new("RGBA", (20, 20), (255, 0, 0, 0))))
        self.assertEqual(result.getpixel((10, 10)), (0, 0, 0))
        self.assertEqual(result.mode, "RGB")

    def test_partial_transparency_is_flattened(self):
        result = ScreenshotImage.decode(encoded(Image.new("RGBA", (20, 20), (255, 0, 0, 128))))
        self.assertEqual(result.getpixel((10, 10)), (128, 0, 0))

    def test_source_metadata_is_not_copied_to_output(self):
        metadata = PngImagePlugin.PngInfo()
        metadata.add_text("Comment", "synthetic private metadata")
        source = encoded(
            Image.new("RGB", (20, 20)),
            pnginfo=metadata,
            dpi=(144, 144),
            icc_profile=b"synthetic profile",
        )
        image = ScreenshotImage.decode(source)
        with Image.open(io.BytesIO(ScreenshotImage.encode(image))) as output:
            self.assertEqual(output.info, {})

    def test_orientation_metadata_cannot_change_mask_coordinates(self):
        exif = Image.Exif()
        exif[274] = 6
        source = encoded(Image.new("RGB", (20, 20)), exif=exif)
        with self.assertRaises(InfrastructureError):
            ScreenshotImage.decode(source)

    def test_lossy_jpeg_is_rejected(self):
        with self.assertRaises(InfrastructureError):
            ScreenshotImage.decode(encoded(Image.new("RGB", (20, 20)), "JPEG"))

    def test_multiple_frames_are_rejected(self):
        source = encoded(
            Image.new("RGB", (20, 20), "white"),
            save_all=True,
            append_images=[Image.new("RGB", (20, 20), "black")],
        )
        with self.assertRaises(InfrastructureError):
            ScreenshotImage.decode(source)

    def test_invalid_image_is_rejected(self):
        with self.assertRaises(InfrastructureError):
            ScreenshotImage.decode(b"invalid screenshot")


if __name__ == "__main__":
    unittest.main()
