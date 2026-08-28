"""Master-timeline calculations shared by preview and export."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from models.project import migrate_project


VOICE_DELAY = 0.15


@dataclass(frozen=True, slots=True)
class TimelineEntry:
    scene_id: str
    name: str
    start: float
    end: float
    voice_start: float | None
    voice_end: float | None
    transition_start: float | None


def build_master_timeline(project: dict[str, Any]) -> list[TimelineEntry]:
    model = migrate_project(project)
    cursor = 0.0
    entries: list[TimelineEntry] = []
    for scene in model.scenes:
        duration = max(0.5, scene.duration)
        has_voice = model.voice_settings.language != "none" and scene.audio_url is not None
        voice_start = cursor + VOICE_DELAY if has_voice else None
        voice_end = min(cursor + duration, voice_start + (scene.audio_duration or 0.0)) if voice_start is not None else None
        transition_start = cursor + max(0.0, duration - scene.transition.duration) if scene.transition.duration else None
        entries.append(TimelineEntry(
            scene_id=scene.id,
            name=scene.name,
            start=cursor,
            end=cursor + duration,
            voice_start=voice_start,
            voice_end=voice_end,
            transition_start=transition_start,
        ))
        cursor += duration
    return entries


def timeline_markdown(project: dict[str, Any]) -> str:
    entries = build_master_timeline(project)
    if not entries:
        return "No scenes."
    lines = ["| Scene | Timeline | Voice |", "|---|---:|---:|"]
    for entry in entries:
        voice = "—" if entry.voice_start is None else f"{entry.voice_start:.2f}–{entry.voice_end:.2f}s"
        lines.append(f"| {entry.name} | {entry.start:.2f}–{entry.end:.2f}s | {voice} |")
    lines.append(f"\n**Total: {entries[-1].end:.2f}s**")
    return "\n".join(lines)
