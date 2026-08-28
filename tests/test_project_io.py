import tempfile
import unittest
from pathlib import Path

from models.project import new_project
from services.project_io import load_project, save_project


class ProjectIOTests(unittest.TestCase):
    def test_round_trip_keeps_scene_scripts_and_settings(self):
        with tempfile.TemporaryDirectory() as directory:
            project = new_project("Demo")
            project.scenes[0].script = "Xin chào"
            project.video_settings.aspect_ratio = "9:16"
            path = save_project(project, Path(directory) / "project.json")
            loaded = load_project(path)
            self.assertEqual(loaded.title, "Demo")
            self.assertEqual(loaded.scenes[0].script, "Xin chào")
            self.assertEqual(loaded.video_settings.aspect_ratio, "9:16")


if __name__ == "__main__":
    unittest.main()
