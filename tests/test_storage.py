import tempfile
import unittest
from pathlib import Path

from models.project import new_project
from services.storage import clear_old_cache, delete_old_projects, storage_summary


class StorageTests(unittest.TestCase):
    def _file(self, path: Path, size: int = 10) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"x" * size)
        return path

    def test_clear_old_cache_preserves_current_project_and_referenced_audio(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = new_project("Current")
            current_audio = self._file(root / "audio" / "current.wav", 11)
            self._file(root / "audio" / "old.wav", 12)
            self._file(root / "renders" / project.id / "current.mp4", 13)
            self._file(root / "renders" / "old-project" / "old.mp4", 14)
            self._file(root / "exports" / "old-project" / "final.mp4", 15)
            project.scenes[0].audio_url = str(current_audio)

            removed = clear_old_cache(project.to_dict(), root)

            self.assertTrue(current_audio.exists())
            self.assertTrue((root / "renders" / project.id / "current.mp4").exists())
            self.assertFalse((root / "audio" / "old.wav").exists())
            self.assertFalse((root / "renders" / "old-project").exists())
            self.assertEqual(removed.files, 3)
            self.assertEqual(removed.bytes, 41)

    def test_delete_old_projects_preserves_current_project(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = new_project("Current")
            self._file(root / "projects" / project.id / "current.json")
            self._file(root / "projects" / "old-project" / "old.json")
            self._file(root / "renders" / "old-project" / "old.mp4")
            self._file(root / "exports" / "old-project" / "final.mp4")

            removed = delete_old_projects(project.to_dict(), root)

            self.assertTrue((root / "projects" / project.id / "current.json").exists())
            self.assertFalse((root / "projects" / "old-project").exists())
            self.assertEqual(removed.files, 3)

    def test_summary_counts_only_other_projects_as_old(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = new_project("Current")
            self._file(root / "projects" / project.id / "current.json")
            self._file(root / "projects" / "old-project" / "old.json")
            summary = storage_summary(project.to_dict(), root)
            self.assertEqual(summary["old_projects"], 1)


if __name__ == "__main__":
    unittest.main()
