"""JSON project persistence with schema migration."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from models.project import VideoProject, migrate_project


PROJECT_ROOT = Path("generated/projects")


def save_project(project: dict[str, Any] | VideoProject, output_path: str | Path | None = None) -> str:
    model = project if isinstance(project, VideoProject) else migrate_project(project)
    if output_path is None:
        directory = PROJECT_ROOT / model.id
        directory.mkdir(parents=True, exist_ok=True)
        safe_title = re.sub(r"[^A-Za-z0-9._-]+", "-", model.title).strip("-") or "project"
        output = directory / f"{safe_title}.json"
    else:
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(f"{output.suffix}.tmp")
    temporary.write_text(json.dumps(model.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(output)
    return str(output.resolve())


def load_project(path: str | Path) -> VideoProject:
    source = Path(path)
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"Could not load project file: {error}") from error
    return migrate_project(payload)
