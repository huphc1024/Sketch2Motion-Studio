"""Discovery helpers for native command-line tools used by Sketch2Motion."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def resolve_potrace() -> str:
    """Return a usable Potrace executable or raise an actionable error."""
    executable_name = "potrace.exe" if sys.platform == "win32" else "potrace"
    configured = os.getenv("POTRACE_PATH", "").strip()
    candidates = [
        Path(configured).expanduser() if configured else None,
        ROOT / "tools" / "potrace" / executable_name,
    ]
    for candidate in candidates:
        if candidate and candidate.is_file():
            return str(candidate.resolve())

    system_executable = shutil.which(executable_name) or shutil.which("potrace")
    if system_executable:
        return system_executable

    install_hint = (
        r"Run: powershell -ExecutionPolicy Bypass -File .\scripts\install_potrace.ps1"
        if sys.platform == "win32"
        else "Install Potrace with your package manager (for example: sudo apt install potrace)."
    )
    raise FileNotFoundError(f"Potrace is required to generate SVG sketches. {install_hint}")
