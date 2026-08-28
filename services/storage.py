"""Safe storage accounting and cleanup for generated Sketch2Motion data."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from models.project import migrate_project


GENERATED_ROOT = Path(__file__).resolve().parent.parent / "generated"


@dataclass(frozen=True, slots=True)
class StorageStats:
    files: int = 0
    bytes: int = 0

    def __add__(self, other: "StorageStats") -> "StorageStats":
        return StorageStats(self.files + other.files, self.bytes + other.bytes)


def storage_summary(project: dict[str, Any], root: str | Path = GENERATED_ROOT) -> dict[str, StorageStats | int]:
    model = migrate_project(project)
    base = Path(root)
    project_root = base / "projects"
    old_projects = sum(1 for path in _children(project_root) if path.is_dir() and path.name != model.id)
    return {
        "audio": _stats(base / "audio"),
        "renders": _stats(base / "renders"),
        "exports": _stats(base / "exports"),
        "projects": _stats(project_root),
        "old_projects": old_projects,
    }


def clear_old_cache(project: dict[str, Any], root: str | Path = GENERATED_ROOT) -> StorageStats:
    """Delete shared stale audio and render/export data for non-current projects."""
    model = migrate_project(project)
    base = Path(root)
    audio_root = base / "audio"
    protected_audio = {
        _resolved(Path(scene.audio_url))
        for scene in model.scenes
        if scene.audio_url and _is_within(Path(scene.audio_url), audio_root)
    }
    targets: list[Path] = [
        path for path in _files(audio_root)
        if _resolved(path) not in protected_audio
    ]
    for category in ("renders", "exports"):
        category_root = base / category
        targets.extend(path for path in _children(category_root) if path.name != model.id)
    return _delete_targets(targets, base)


def delete_old_projects(project: dict[str, Any], root: str | Path = GENERATED_ROOT) -> StorageStats:
    """Delete every saved project except the project currently open in the editor."""
    model = migrate_project(project)
    base = Path(root)
    targets: list[Path] = []
    for category in ("projects", "renders", "exports"):
        category_root = base / category
        targets.extend(path for path in _children(category_root) if path.name != model.id)
    return _delete_targets(targets, base)


def format_storage_summary(project: dict[str, Any], root: str | Path = GENERATED_ROOT) -> str:
    summary = storage_summary(project, root)
    audio = summary["audio"]
    renders = summary["renders"]
    exports = summary["exports"]
    projects = summary["projects"]
    assert isinstance(audio, StorageStats)
    assert isinstance(renders, StorageStats)
    assert isinstance(exports, StorageStats)
    assert isinstance(projects, StorageStats)
    cache = audio + renders + exports
    return (
        f"Cache: **{cache.files} files · {_format_bytes(cache.bytes)}**  \n"
        f"Projects: **{summary['old_projects']} old · {_format_bytes(projects.bytes)} total**"
    )


def _delete_targets(targets: Iterable[Path], root: Path) -> StorageStats:
    base = _resolved(root)
    removed = StorageStats()
    for target in dict.fromkeys(targets):
        resolved = _resolved(target)
        if resolved == base or not _is_within(resolved, base):
            raise ValueError(f"Refusing to delete unsafe path: {target}")
        if not target.exists():
            continue
        removed += _stats(target)
        if target.is_dir():
            shutil.rmtree(target)
        else:
            target.unlink()
    return removed


def _stats(path: Path) -> StorageStats:
    if not path.exists():
        return StorageStats()
    if path.is_file():
        try:
            return StorageStats(1, path.stat().st_size)
        except OSError:
            return StorageStats()
    result = StorageStats()
    for file_path in _files(path):
        try:
            result += StorageStats(1, file_path.stat().st_size)
        except OSError:
            continue
    return result


def _children(path: Path) -> list[Path]:
    try:
        return list(path.iterdir())
    except OSError:
        return []


def _files(path: Path) -> list[Path]:
    try:
        return [candidate for candidate in path.rglob("*") if candidate.is_file()]
    except OSError:
        return []


def _resolved(path: Path) -> Path:
    return path.expanduser().resolve(strict=False)


def _is_within(path: Path, parent: Path) -> bool:
    try:
        _resolved(path).relative_to(_resolved(parent))
        return True
    except ValueError:
        return False


def _format_bytes(value: int) -> str:
    size = float(max(0, value))
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"
