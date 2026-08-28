"""HTML scene timeline renderer."""

from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Any
from urllib.parse import quote

from models.project import migrate_project


STATUS_LABELS = {
    "idle": "Voice idle",
    "generating": "Generating…",
    "ready": "Voice ready",
    "outdated": "Voice outdated",
    "error": "Voice error",
}


def render_timeline(project: dict[str, Any], selected_scene_id: str | None) -> str:
    model = migrate_project(project)
    cards: list[str] = []
    for index, scene in enumerate(model.scenes):
        selected = " is-selected" if scene.id == selected_scene_id else ""
        image = scene.image or ""
        thumbnail = (
            f'<img src="/gradio_api/file={quote(image)}" alt="" />'
            if image and Path(image).exists()
            else '<div class="scene-placeholder">✦</div>'
        )
        status = STATUS_LABELS.get(scene.tts_status, scene.tts_status)
        cards.append(
            f'''<article class="scene-card{selected}" draggable="true" data-scene-id="{escape(scene.id)}">
                <button class="scene-select" data-action="select" title="Select scene">
                  <span class="scene-index">{index + 1:02d}</span>
                  <span class="scene-thumb">{thumbnail}</span>
                  <span class="scene-meta"><strong>{escape(scene.name)}</strong><em>{scene.duration:.1f}s</em></span>
                  <small class="status-{escape(scene.tts_status)}">● {escape(status)}</small>
                </button>
                <span class="scene-actions">
                  <button data-action="duplicate" title="Duplicate">⧉</button>
                  <button data-action="delete" title="Delete">×</button>
                </span>
              </article>'''
        )
    cards.append(
        '<button class="scene-add" data-action="add"><span>＋</span><strong>Add scene</strong></button>'
    )
    return '<div id="scene-timeline" class="scene-timeline">' + "".join(cards) + "</div>"
