import tempfile
import unittest
from pathlib import Path

from models.project import migrate_project, new_project
from services.media_import import import_images_and_scripts, parse_srt_scripts


SRT = """1
00:00:00,000 --> 00:00:02,000
Xin chào mọi người.

2
00:00:02,000 --> 00:00:04,000
Đây là <b>cảnh thứ hai</b>.
"""


class MediaImportTests(unittest.TestCase):
    def _file(self, root: Path, name: str, content: str = "image") -> Path:
        path = root / name
        path.write_text(content, encoding="utf-8")
        return path

    def test_srt_text_is_parsed_in_caption_order(self):
        with tempfile.TemporaryDirectory() as directory:
            source = self._file(Path(directory), "caption.srt", SRT)
            self.assertEqual(
                parse_srt_scripts(source),
                ["Xin chào mọi người.", "Đây là cảnh thứ hai."],
            )

    def test_images_are_sorted_naturally_and_scripts_are_assigned_by_index(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            image_10 = self._file(root, "image10.png")
            image_2 = self._file(root, "image2.png")
            image_1 = self._file(root, "image1.png")
            srt = self._file(root, "caption.srt", SRT)

            result = import_images_and_scripts(
                new_project().to_dict(), [image_10, image_2, image_1], srt,
            )
            project = migrate_project(result.project)

            self.assertEqual(
                [Path(scene.image).name for scene in project.scenes],
                ["image1.png", "image2.png", "image10.png"],
            )
            self.assertEqual(
                [scene.script for scene in project.scenes],
                ["Xin chào mọi người.", "Đây là cảnh thứ hai.", ""],
            )
            self.assertTrue(project.voice_settings.auto_duration)
            self.assertTrue(all(scene.auto_duration for scene in project.scenes))

    def test_extra_captions_are_kept_in_the_final_scene(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            image = self._file(root, "image1.png")
            srt = self._file(root, "caption.srt", SRT)
            result = import_images_and_scripts(new_project().to_dict(), [image], srt)
            project = migrate_project(result.project)
            self.assertEqual(result.overflow_count, 1)
            self.assertIn("Xin chào mọi người.", project.scenes[0].script)
            self.assertIn("Đây là cảnh thứ hai.", project.scenes[0].script)


if __name__ == "__main__":
    unittest.main()
