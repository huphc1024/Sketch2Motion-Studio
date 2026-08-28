"""Create scenes from naturally sorted images and optional SRT scripts."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from models.project import migrate_project, new_scene


@dataclass(frozen=True, slots=True)
class ImportResult:
    project: dict[str, Any]
    selected_scene_id: str
    image_count: int
    caption_count: int
    overflow_count: int


def parse_srt_scripts(path: str | Path) -> list[str]:
    """Return caption text in SRT order; timestamps are intentionally ignored."""
    source = Path(path)
    try:
        content = source.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        content = source.read_text(encoding="cp1258")
    except OSError as error:
        raise ValueError(f"Could not read SRT file: {error}") from error

    scripts: list[str] = []
    for block in re.split(r"\r?\n\s*\r?\n", content.strip()):
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        timing_index = next((index for index, line in enumerate(lines) if "-->" in line), None)
        if timing_index is None:
            continue
        text = " ".join(lines[timing_index + 1:])
        text = re.sub(r"<[^>]+>|\{\\[^}]+\}", "", text).strip()
        if text:
            scripts.append(text)
    if not scripts:
        raise ValueError("The SRT file does not contain any valid caption text.")
    return scripts


def import_images_and_scripts(
    project: dict[str, Any],
    image_paths: Sequence[str | Path] | str | Path | None,
    srt_path: str | Path | None = None,
) -> ImportResult:
    """Replace the timeline with one scene per image and assign SRT text by index."""
    model = migrate_project(project)
    images = _image_paths(image_paths)
    if not images:
        raise ValueError("Select at least one image before importing scenes.")
    scripts = parse_srt_scripts(srt_path) if srt_path else []

    scenes = []
    for index, image in enumerate(images):
        scene = new_scene(index, name=f"Scene {index + 1:02d} · {image.stem}")
        scene.image = str(image.resolve())
        scene.script = scripts[index] if index < len(scripts) else ""
        scene.auto_duration = True
        scenes.append(scene)

    overflow = max(0, len(scripts) - len(scenes))
    if overflow:
        remaining = scripts[len(scenes):]
        scenes[-1].script = "\n".join([scenes[-1].script, *remaining]).strip()

    model.scenes = scenes
    model.voice_settings.auto_duration = True
    return ImportResult(model.to_dict(), scenes[0].id, len(images), len(scripts), overflow)


def _image_paths(value: Sequence[str | Path] | str | Path | None) -> list[Path]:
    raw = [value] if isinstance(value, (str, Path)) else list(value or [])
    images = [Path(item) for item in raw if item and Path(item).is_file()]
    return sorted(images, key=lambda path: _natural_key(path.name))


def _natural_key(value: str) -> list[int | str]:
    return [int(part) if part.isdigit() else part.casefold() for part in re.split(r"(\d+)", value)]
