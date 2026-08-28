import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from services.tooling import resolve_potrace


class ToolingTests(unittest.TestCase):
    def test_configured_potrace_path_has_priority(self):
        with tempfile.TemporaryDirectory() as directory:
            executable = Path(directory) / "potrace.exe"
            executable.touch()
            with patch.dict(os.environ, {"POTRACE_PATH": str(executable)}):
                self.assertEqual(resolve_potrace(), str(executable.resolve()))

    def test_missing_potrace_has_actionable_install_hint(self):
        with patch.dict(os.environ, {"POTRACE_PATH": ""}), patch(
            "services.tooling.ROOT", Path("Z:/definitely-missing-sketch2motion")
        ), patch("services.tooling.shutil.which", return_value=None):
            with self.assertRaisesRegex(FileNotFoundError, "install_potrace.ps1"):
                resolve_potrace()


if __name__ == "__main__":
    unittest.main()
