import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from xml.etree import ElementTree as ET

from PIL import Image, ImageDraw

from sketch2svg_color import BACKGROUND_LAYER_ID, SVG_NS, _load_rgb_image, sketch2svg_color


TRACE_SVG = b'''<svg xmlns="http://www.w3.org/2000/svg" width="100pt" height="100pt" viewBox="0 0 100 100"><g transform="translate(0,100) scale(1,-1)"><path d="M0 0h100v100h-100z" /></g></svg>'''


class ColorPipelineTests(unittest.TestCase):
    def test_dominant_subject_is_preserved_by_background_layer(self):
        with tempfile.TemporaryDirectory() as directory:
            directory_path = Path(directory)
            input_path = directory_path / "dominant-subject.png"
            output_path = directory_path / "result.svg"
            image = Image.new("RGB", (100, 100), "white")
            ImageDraw.Draw(image).rectangle((0, 0, 59, 99), fill="red")
            image.save(input_path)

            with patch("sketch2svg_color._trace_mask", return_value=TRACE_SVG):
                sketch2svg_color(str(input_path), str(output_path), num_colors=2)

            root = ET.parse(output_path).getroot()
            background = root.find(f"{{{SVG_NS}}}rect[@id='{BACKGROUND_LAYER_ID}']")
            self.assertIsNotNone(background)
            self.assertEqual(background.get("fill"), "#ff0000")
            self.assertEqual(root.get("data-background-color"), "#ff0000")
            self.assertIn("#ffffff", [group.get("fill") for group in root.findall(f"{{{SVG_NS}}}g")])
            self.assertFalse(output_path.with_suffix(".bg").exists())

    def test_transparent_pixels_are_composited_on_white(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "transparent.png"
            image = Image.new("RGBA", (4, 4), (0, 0, 0, 0))
            image.putpixel((1, 1), (0, 102, 255, 255))
            image.save(path)

            rgb = _load_rgb_image(str(path))
            self.assertEqual(rgb.getpixel((0, 0)), (255, 255, 255))
            self.assertEqual(rgb.getpixel((1, 1)), (0, 102, 255))

    def test_rejects_invalid_color_count(self):
        with self.assertRaises(ValueError):
            sketch2svg_color("unused.png", num_colors=0)


if __name__ == "__main__":
    unittest.main()
