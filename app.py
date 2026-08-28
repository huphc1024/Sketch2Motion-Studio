"""Sketch2Motion multi-scene editor and backend API."""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any, Iterator

import gradio as gr
import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from components.timeline import render_timeline
from models.project import Scene, migrate_project, new_project
from services.project_io import load_project, save_project
from services.rendering import compose_scene_video, ensure_scene_svg, export_project
from services.timeline import timeline_markdown
from services.tts import SynthesisInput, default_tts_service
from services.tts.vieneu_voices import v3_turbo_voices
from stores.project_store import ProjectStore


ROOT = Path(__file__).resolve().parent
GENERATED = ROOT / "generated"
GENERATED.mkdir(parents=True, exist_ok=True)

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


CSS = r"""
:root { --accent: #635bff; --accent-soft: #eeecff; --border: #e5e7eb; --ink: #18181b; --muted: #71717a; }
.gradio-container { max-width: 100% !important; background: #f7f8fa !important; color: var(--ink); }
.gradio-container, .app-header, .panel, .timeline-panel, .scene-card, .compact-status { transition: background-color .18s ease, border-color .18s ease, color .18s ease; }
.app-shell { max-width: 1800px; margin: auto; }
.app-header { background: white; border: 1px solid var(--border); border-radius: 12px; padding: 12px 18px; margin-bottom: 12px; }
.app-header h1 { font-size: 19px !important; margin: 0 !important; letter-spacing: -.02em; }
.panel { background: white; border: 1px solid var(--border); border-radius: 12px; padding: 14px; }
.canvas-panel { min-height: 650px; }
.canvas-panel video, .canvas-panel img { border-radius: 10px; background: #111827; }
.section-kicker { color: var(--muted); font-size: 11px; font-weight: 700; letter-spacing: .12em; text-transform: uppercase; }
button.primary { background: var(--accent) !important; border-color: var(--accent) !important; color: white !important; }
.timeline-panel { margin-top: 12px; background: white; border: 1px solid var(--border); border-radius: 12px; padding: 14px; }
.scene-timeline { display: flex; gap: 10px; overflow-x: auto; padding: 2px 2px 10px; min-height: 158px; align-items: stretch; }
.scene-card { position: relative; width: 190px; min-width: 190px; border: 2px solid transparent; border-radius: 10px; background: #fafafa; overflow: hidden; transition: .16s ease; }
.scene-card:hover { border-color: #c7c3ff; transform: translateY(-1px); }
.scene-card.is-selected { border-color: var(--accent); box-shadow: 0 0 0 3px var(--accent-soft); background: white; }
.scene-card.dragging { opacity: .45; }
.scene-select { appearance: none; border: 0; width: 100%; padding: 8px; text-align: left; background: transparent; color: inherit; cursor: pointer; }
.scene-index { position: absolute; top: 12px; left: 12px; z-index: 2; padding: 2px 6px; border-radius: 6px; background: rgba(17,24,39,.78); color: white; font-size: 11px; font-weight: 700; }
.scene-thumb { display: block; height: 82px; border-radius: 7px; overflow: hidden; background: #eef0f4; }
.scene-thumb img { width: 100%; height: 100%; object-fit: cover; }
.scene-placeholder { height: 100%; display: grid; place-items: center; color: #a1a1aa; font-size: 26px; }
.scene-meta { display: flex; justify-content: space-between; gap: 8px; margin-top: 8px; font-size: 12px; }
.scene-meta strong { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.scene-meta em { font-style: normal; color: var(--muted); }
.scene-select small { display: block; margin-top: 5px; font-size: 10px; color: var(--muted); }
.status-ready { color: #16803c !important; } .status-error, .status-outdated { color: #c2410c !important; } .status-generating { color: var(--accent) !important; }
.scene-actions { position: absolute; right: 8px; top: 8px; z-index: 3; display: flex; gap: 4px; }
.scene-actions button { width: 25px; height: 25px; padding: 0; border: 0; border-radius: 6px; color: white; background: rgba(17,24,39,.72); cursor: pointer; }
.scene-add { min-width: 145px; border: 1px dashed #bbb7ff; border-radius: 10px; background: #faf9ff; color: var(--accent); display: grid; place-content: center; gap: 6px; cursor: pointer; }
.scene-add span { font-size: 26px; }.scene-add strong { font-size: 12px; }
#timeline-event { position: fixed !important; left: -10000px !important; width: 1px !important; height: 1px !important; overflow: hidden !important; }
.compact-status { min-height: 36px; padding: 8px 10px; border-radius: 8px; background: #f7f7f8; color: var(--muted); font-size: 12px; }
.dark .gradio-container { --accent-soft: #28244f; --border: #2d313b; --ink: #f4f4f5; --muted: #a1a1aa; background: #0f1115 !important; color: var(--ink); }
.dark .app-header, .dark .panel, .dark .timeline-panel { background: #17191f; border-color: var(--border); }
.dark .scene-card { background: #1d2027; color: var(--ink); }
.dark .scene-card:hover { border-color: #7770ff; }
.dark .scene-card.is-selected { background: #20232c; border-color: #8b85ff; box-shadow: 0 0 0 3px #28244f; }
.dark .scene-thumb { background: #252a34; }
.dark .scene-add { background: #1b1930; border-color: #625bd6; color: #aaa6ff; }
.dark .compact-status { background: #20232b; color: #b8bbc4; }
.dark .canvas-panel video, .dark .canvas-panel img { background: #090a0d; }
@media(max-width: 1100px) { .editor-row { flex-direction: column !important; } .canvas-panel { min-height: auto; } }
"""


TIMELINE_JS = r"""
() => {
  const applyTheme = (dark) => {
    document.body.classList.toggle('dark', dark);
    document.body.style.background = dark ? '#0f1115' : '#f7f8fa';
    const button = document.querySelector('#theme-toggle button, button#theme-toggle');
    if (button) {
      button.textContent = dark ? '☀ Light' : '🌙 Dark';
      button.setAttribute('aria-label', dark ? 'Switch to light theme' : 'Switch to dark theme');
    }
  };
  const savedTheme = localStorage.getItem('sketch2motion-theme');
  applyTheme(savedTheme === 'dark');
  const bindTheme = () => {
    const button = document.querySelector('#theme-toggle button, button#theme-toggle');
    if (!button || button.dataset.themeBound) return;
    button.dataset.themeBound = '1';
    applyTheme(document.body.classList.contains('dark'));
    button.addEventListener('click', (event) => {
      event.preventDefault();
      const dark = !document.body.classList.contains('dark');
      localStorage.setItem('sketch2motion-theme', dark ? 'dark' : 'light');
      applyTheme(dark);
    });
  };
  const emit = (payload) => {
    const root = document.querySelector('#timeline-event');
    const input = root && root.querySelector('textarea, input');
    if (!input) return;
    const value = JSON.stringify({...payload, nonce: Date.now()});
    const setter = Object.getOwnPropertyDescriptor(Object.getPrototypeOf(input), 'value')?.set;
    if (setter) setter.call(input, value); else input.value = value;
    input.dispatchEvent(new Event('input', {bubbles: true}));
    input.dispatchEvent(new Event('change', {bubbles: true}));
  };
  const bind = () => {
    const timeline = document.querySelector('#scene-timeline');
    if (!timeline || timeline.dataset.bound) return;
    timeline.dataset.bound = '1';
    let dragged = null;
    let pointerScene = null, pointerStartX = 0, pointerMoved = false, suppressClick = false;
    timeline.addEventListener('click', (event) => {
      if (suppressClick) { suppressClick = false; event.preventDefault(); return; }
      const button = event.target.closest('[data-action]');
      if (!button) return;
      event.preventDefault();
      const card = button.closest('[data-scene-id]');
      emit({action: button.dataset.action, sceneId: card?.dataset.sceneId || null});
    });
    timeline.addEventListener('dragstart', (event) => {
      const card = event.target.closest('[data-scene-id]');
      if (!card) return;
      dragged = card.dataset.sceneId; card.classList.add('dragging'); event.dataTransfer.effectAllowed = 'move';
    });
    timeline.addEventListener('dragend', (event) => { event.target.closest('[data-scene-id]')?.classList.remove('dragging'); dragged = null; });
    timeline.addEventListener('dragover', (event) => event.preventDefault());
    timeline.addEventListener('drop', (event) => {
      event.preventDefault();
      const target = event.target.closest('[data-scene-id]')?.dataset.sceneId;
      if (dragged && target && dragged !== target) emit({action: 'move', sceneId: dragged, targetSceneId: target});
    });
    timeline.addEventListener('pointerdown', (event) => {
      const card = event.target.closest('[data-scene-id]');
      if (!card || event.button !== 0) return;
      pointerScene = card.dataset.sceneId; pointerStartX = event.clientX; pointerMoved = false;
    });
    timeline.addEventListener('pointermove', (event) => {
      if (pointerScene && Math.abs(event.clientX - pointerStartX) > 14) pointerMoved = true;
    });
    timeline.addEventListener('pointerup', (event) => {
      if (!pointerScene) return;
      const target = event.target.closest('[data-scene-id]')?.dataset.sceneId;
      if (pointerMoved && target && target !== pointerScene) {
        suppressClick = true;
        emit({action: 'move', sceneId: pointerScene, targetSceneId: target});
      }
      pointerScene = null; pointerMoved = false;
    });
  };
  const initialize = () => { bindTheme(); bind(); };
  initialize(); new MutationObserver(initialize).observe(document.body, {childList: true, subtree: true});
}
"""


def _scene(project: dict[str, Any], selected_scene_id: str | None) -> Scene:
    return ProjectStore.selected_scene(project, selected_scene_id)


def _script_stats(script: str, speed: float = 1.0) -> str:
    characters = len(script or "")
    words = len((script or "").split())
    seconds = words / (2.45 * max(0.75, speed)) if words else 0.0
    return f"**{characters} characters** · ~{seconds:.1f} seconds"


def _voice_status(scene: Scene) -> str:
    labels = {
        "idle": "Voice idle — generate audio when the script is ready.",
        "generating": "⏳ Generating audio…",
        "ready": f"✓ Voice ready · {scene.audio_duration or 0:.2f}s",
        "outdated": "⚠ Voice outdated — the script changed; regenerate required.",
        "error": f"⚠ Voice error: {scene.tts_error or 'Unknown error'}",
    }
    return labels.get(scene.tts_status, scene.tts_status)


def _voice_choices(project: dict[str, Any]) -> list[tuple[str, str]]:
    current = migrate_project(project).voice_settings.voice_id or "default"
    choices = [(item.name, item.id) for item in v3_turbo_voices()]
    if current not in {voice_id for _, voice_id in choices}:
        choices.insert(0, (current if current != "default" else "VieNeu default (automatic)", current))
    return choices


def _full_refresh(project: dict[str, Any], selected_scene_id: str | None):
    model = migrate_project(project)
    selected = next((item for item in model.scenes if item.id == selected_scene_id), model.scenes[0])
    voice = model.voice_settings
    video = model.video_settings
    return (
        model.to_dict(), selected.id, render_timeline(model.to_dict(), selected.id), model.title,
        selected.name, selected.image, selected.svg_path or selected.image, selected.image_prompt,
        selected.preserve_colors, selected.color_count, selected.script, _script_stats(selected.script, voice.speed),
        selected.audio_url, _voice_status(selected), selected.duration, selected.auto_duration,
        selected.animation_preset, selected.animation_delay, selected.animation_scale,
        selected.transition.type, selected.transition.duration,
        voice.language, voice.provider, gr.update(choices=_voice_choices(model.to_dict()), value=voice.voice_id),
        voice.speed, voice.pitch, voice.volume, voice.auto_duration,
        video.aspect_ratio, video.fps, video.resolution,
    )


def _timeline_event(raw_event: str, project: dict[str, Any], selected_scene_id: str):
    try:
        event = json.loads(raw_event or "{}")
    except json.JSONDecodeError:
        return _full_refresh(project, selected_scene_id)
    action = event.get("action")
    scene_id = event.get("sceneId") or selected_scene_id
    if action == "select":
        selected_scene_id = scene_id
    elif action == "add":
        project, selected_scene_id = ProjectStore.add_scene(project, selected_scene_id)
    elif action == "duplicate":
        project, selected_scene_id = ProjectStore.duplicate_scene(project, scene_id)
    elif action == "delete":
        project, selected_scene_id = ProjectStore.delete_scene(project, scene_id)
    elif action == "move":
        project = ProjectStore.move_scene(project, scene_id, event.get("targetSceneId"))
        selected_scene_id = scene_id
    return _full_refresh(project, selected_scene_id)


def _button_action(action: str, project: dict[str, Any], selected_scene_id: str):
    return _timeline_event(json.dumps({"action": action, "sceneId": selected_scene_id}), project, selected_scene_id)


def _sync_scene(
    project: dict[str, Any], selected_scene_id: str, name: str, image: str | None,
    image_prompt: str, preserve_colors: bool, color_count: int, script: str,
    duration: float, auto_duration: bool, animation: str, delay: float, scale: float,
    transition_type: str, transition_duration: float,
):
    current = _scene(project, selected_scene_id)
    changes: dict[str, Any] = {
        "name": (name or current.name).strip(), "image": image, "image_prompt": image_prompt or "",
        "preserve_colors": bool(preserve_colors), "color_count": int(color_count), "script": script or "",
        "duration": max(0.5, float(duration)), "auto_duration": bool(auto_duration),
        "animation_preset": animation, "animation_delay": float(delay), "animation_scale": float(scale),
        "transition": {"type": transition_type, "duration": float(transition_duration)},
    }
    if image != current.image or bool(preserve_colors) != current.preserve_colors or int(color_count) != current.color_count:
        changes["svg_path"] = None
    project = ProjectStore.update_scene(project, selected_scene_id, **changes)
    scene = _scene(project, selected_scene_id)
    if scene.auto_duration and scene.audio_duration is not None:
        project = ProjectStore.update_scene(project, selected_scene_id, duration=max(0.5, scene.audio_duration + scene.transition.duration))
        scene = _scene(project, selected_scene_id)
    return project, render_timeline(project, selected_scene_id), _script_stats(scene.script), _voice_status(scene)


def _update_title(project: dict[str, Any], title: str):
    return ProjectStore.update_project(project, title=title)


def _new_project():
    project = new_project().to_dict()
    return _full_refresh(project, project["scenes"][0]["id"])


def _update_voice_settings(project, selected_scene_id, language, provider, voice_id, speed, pitch, volume, auto_duration):
    notice = "VieNeu Local v3 Turbo · 20 built-in Vietnamese voices."
    if language == "none":
        provider, voice_id = "none", "none"
        notice = "No Voice mode — scene durations are manual."
    elif language == "en":
        provider, voice_id = "none", "none"
        notice = "No English TTS provider is installed. Add one through the provider interface; VieNeu is not used as a fake English voice."
    elif provider == "none":
        provider, voice_id = "vieneu", "default"
    project = ProjectStore.update_project(project, voice={
        "language": language, "provider": provider, "voice_id": voice_id,
        "speed": speed, "pitch": pitch, "volume": volume, "auto_duration": auto_duration,
    })
    choices = [("No voice", "none")] if provider == "none" else _voice_choices(project)
    return project, render_timeline(project, selected_scene_id), gr.update(value=provider), gr.update(choices=choices, value=voice_id), notice


def _update_video_settings(project, aspect_ratio, fps, resolution):
    return ProjectStore.update_project(project, video={"aspect_ratio": aspect_ratio, "fps": fps, "resolution": resolution})


def _refresh_voices(project):
    settings = migrate_project(project).voice_settings
    if settings.provider == "none" or settings.language != "vi":
        return gr.update(choices=[("No compatible provider", "none")], value="none"), "No compatible provider for this language."
    voices = default_tts_service.get_voices(settings.provider, settings.language)
    choices = [(item.name, item.id) for item in voices]
    return gr.update(choices=choices, value=choices[0][1] if choices else None), f"{len(choices)} voice(s) available."


def _generate_sketch(project, selected_scene_id):
    model = migrate_project(project)
    scene = next(item for item in model.scenes if item.id == selected_scene_id)
    try:
        svg_path = ensure_scene_svg(model.id, scene)
        project = ProjectStore.update_scene(project, selected_scene_id, svg_path=svg_path)
        return project, svg_path, render_timeline(project, selected_scene_id), "✓ Sketch ready."
    except Exception as error:
        return project, None, render_timeline(project, selected_scene_id), f"⚠ {error}"


def _synthesis_input(project: dict[str, Any], scene: Scene, text: str | None = None) -> tuple[str, SynthesisInput]:
    settings = migrate_project(project).voice_settings
    if settings.language == "none" or settings.provider == "none":
        raise ValueError("No compatible TTS provider is selected.")
    return settings.provider, SynthesisInput(
        text=(text if text is not None else scene.script).strip(), voice_id=settings.voice_id,
        language=settings.language, speed=settings.speed, pitch=settings.pitch,
    )


def _generate_scene_voice(project, selected_scene_id) -> Iterator[tuple[Any, ...]]:
    model = migrate_project(project)
    scene = next(item for item in model.scenes if item.id == selected_scene_id)
    scene.tts_status, scene.tts_error = "generating", None
    project = model.to_dict()
    yield project, render_timeline(project, selected_scene_id), scene.audio_url, _voice_status(scene), scene.duration
    try:
        provider, request = _synthesis_input(project, scene)
        result = default_tts_service.synthesize(provider, request)
        scene.apply_audio(result.audio_url, result.duration, result.cache_key)
    except Exception as error:
        scene.tts_status, scene.tts_error = "error", str(error)
    project = model.to_dict()
    yield project, render_timeline(project, selected_scene_id), scene.audio_url, _voice_status(scene), scene.duration


def _generate_all_voices(project, selected_scene_id) -> Iterator[tuple[Any, ...]]:
    model = migrate_project(project)
    total = len(model.scenes)
    if model.voice_settings.language == "none" or model.voice_settings.provider == "none":
        scene = next(item for item in model.scenes if item.id == selected_scene_id)
        yield model.to_dict(), render_timeline(model.to_dict(), selected_scene_id), "No compatible TTS provider selected.", scene.audio_url, _voice_status(scene), scene.duration
        return
    for index, scene in enumerate(model.scenes, start=1):
        scene.tts_status, scene.tts_error = "generating", None
        project = model.to_dict()
        selected = next(item for item in model.scenes if item.id == selected_scene_id)
        yield project, render_timeline(project, selected_scene_id), f"Generating voices: {index - 1} / {total}\n\n**{scene.name} generating…**", selected.audio_url, _voice_status(selected), selected.duration
        try:
            provider, request = _synthesis_input(project, scene)
            result = default_tts_service.synthesize(provider, request)
            scene.apply_audio(result.audio_url, result.duration, result.cache_key)
        except Exception as error:
            scene.tts_status, scene.tts_error = "error", str(error)
        project = model.to_dict()
        selected = next(item for item in model.scenes if item.id == selected_scene_id)
        message = f"Generating voices: {index} / {total}\n\n✓ {scene.name}" if scene.tts_status == "ready" else f"Generating voices: {index} / {total}\n\n⚠ {scene.name}: {scene.tts_error}"
        yield project, render_timeline(project, selected_scene_id), message, selected.audio_url, _voice_status(selected), selected.duration


def _preview_voice(project):
    scene = migrate_project(project).scenes[0]
    try:
        provider, request = _synthesis_input(project, scene, "Xin chào, đây là giọng đọc thử của Sketch2Motion.")
        result = default_tts_service.synthesize(provider, request)
        return result.audio_url, "✓ Voice preview ready (cache reused when settings are unchanged)."
    except Exception as error:
        return None, f"⚠ {error}"


def _preview_scene(project, selected_scene_id):
    model = migrate_project(project)
    scene = next(item for item in model.scenes if item.id == selected_scene_id)
    try:
        video = compose_scene_video(
            model.id, scene, model.video_settings,
            volume=0 if model.voice_settings.language == "none" else model.voice_settings.volume, quality="l",
        )
        scene.preview_url = video
        if not scene.svg_path:
            scene.svg_path = ensure_scene_svg(model.id, scene)
        project = model.to_dict()
        return project, render_timeline(project, selected_scene_id), video, f"✓ {scene.name} preview is synchronized to {scene.duration:.2f}s."
    except Exception as error:
        return project, render_timeline(project, selected_scene_id), None, f"⚠ {error}"


def _preview_project(project):
    try:
        video = export_project(project, quality="l")
        return video, f"✓ Full preview ready.\n\n{timeline_markdown(project)}"
    except Exception as error:
        return None, f"⚠ {error}"


def _save_project(project):
    try:
        path = save_project(project)
        return path, f"✓ Project saved to `{path}`"
    except Exception as error:
        return None, f"⚠ {error}"


def _load_project(file_path):
    try:
        model = load_project(file_path)
        return (*_full_refresh(model.to_dict(), model.scenes[0].id), f"✓ Loaded {model.title}")
    except Exception as error:
        fallback = new_project().to_dict()
        return (*_full_refresh(fallback, fallback["scenes"][0]["id"]), f"⚠ {error}")


def build_demo() -> gr.Blocks:
    initial = new_project("My Sketch2Motion video")
    initial_project, initial_scene_id = initial.to_dict(), initial.scenes[0].id

    with gr.Blocks(
        title="Sketch2Motion Studio",
        theme=gr.themes.Soft(primary_hue="indigo", neutral_hue="slate"),
        css=CSS,
        js=TIMELINE_JS,
    ) as demo:
        project_state, selected_scene_state = gr.State(initial_project), gr.State(initial_scene_id)
        with gr.Column(elem_classes="app-shell"):
            with gr.Row(elem_classes="app-header"):
                with gr.Column(scale=4, min_width=330):
                    gr.Markdown("# Sketch2Motion Studio\nMulti-scene drawing videos with per-scene voice over")
                gr.Button("🌙 Dark", size="sm", scale=1, elem_id="theme-toggle")
                new_project_btn = gr.Button("New project", size="sm", scale=1)
                save_btn = gr.Button("Save project", size="sm", scale=1)
                export_btn = gr.Button("Export MP4", variant="primary", size="sm", elem_classes="primary", scale=1)

            with gr.Row(elem_classes="editor-row"):
                with gr.Column(scale=2, min_width=245, elem_classes="panel"):
                    gr.Markdown("<span class='section-kicker'>Project</span>")
                    project_title = gr.Textbox(label="Project title", value=initial.title)
                    gr.Markdown("### Voice Over")
                    language = gr.Dropdown([("Vietnamese", "vi"), ("English", "en"), ("No Voice", "none")], value="vi", label="Language")
                    provider = gr.Dropdown([("VieNeu Local · v3 Turbo", "vieneu"), ("No provider", "none")], value="vieneu", label="Provider")
                    voice = gr.Dropdown(_voice_choices(initial.to_dict()), value="default", label="Voice")
                    refresh_voices_btn = gr.Button("Refresh voices", size="sm")
                    speed = gr.Slider(0.75, 1.5, value=1.0, step=0.05, label="Speed")
                    pitch = gr.Slider(0.5, 2.0, value=1.0, step=0.05, label="Pitch (when supported)")
                    volume = gr.Slider(0, 100, value=100, step=1, label="Volume %")
                    global_auto_duration = gr.Checkbox(value=True, label="Auto duration from voice")
                    voice_provider_status = gr.Markdown("VieNeu Local v3 Turbo · 20 built-in Vietnamese voices.", elem_classes="compact-status")
                    preview_voice_btn = gr.Button("Preview voice")
                    voice_sample = gr.Audio(label="Voice sample", type="filepath")
                    generate_all_btn = gr.Button("Generate All Voices", variant="primary", elem_classes="primary")
                    batch_status = gr.Markdown("Ready · queue concurrency: 1", elem_classes="compact-status")
                    gr.Markdown("### Video Settings")
                    aspect_ratio = gr.Dropdown(["9:16", "16:9", "1:1"], value="16:9", label="Aspect ratio")
                    fps = gr.Dropdown([30, 60], value=30, label="FPS")
                    resolution = gr.Dropdown(["720p", "1080p"], value="1080p", label="Resolution")
                    load_file = gr.File(label="Load project JSON", type="filepath", file_types=[".json"])
                    saved_file = gr.File(label="Saved project", interactive=False)

                with gr.Column(scale=5, min_width=500, elem_classes=["panel", "canvas-panel"]):
                    gr.Markdown("<span class='section-kicker'>Canvas / Preview</span>")
                    with gr.Tabs():
                        with gr.Tab("Scene"):
                            with gr.Row():
                                sketch_preview = gr.Image(label="Sketch / SVG", type="filepath", height=360)
                                scene_video = gr.Video(label="Synchronized scene preview", autoplay=False, height=360)
                            with gr.Row():
                                generate_sketch_btn = gr.Button("Generate sketch")
                                preview_scene_btn = gr.Button("Preview scene", variant="primary", elem_classes="primary")
                        with gr.Tab("Full project"):
                            full_video = gr.Video(label="Master timeline preview", autoplay=False, height=430)
                            preview_project_btn = gr.Button("Preview full project", variant="primary", elem_classes="primary")
                    render_status = gr.Markdown("Select a scene to begin.", elem_classes="compact-status")

                with gr.Column(scale=3, min_width=310, elem_classes="panel"):
                    gr.Markdown("<span class='section-kicker'>Scene Properties</span>")
                    scene_name = gr.Textbox(label="Scene name", value=initial.scenes[0].name)
                    image = gr.Image(label="Image", type="filepath")
                    image_prompt = gr.Textbox(label="Image prompt / notes", placeholder="Optional prompt for a future image provider")
                    with gr.Row():
                        preserve_colors = gr.Checkbox(label="Preserve colors", value=False)
                        color_count = gr.Slider(2, 16, step=1, value=8, label="Palette")
                    script = gr.Textbox(label="Script / Voice Over", lines=7, placeholder="Write this scene's narration…")
                    script_stats = gr.Markdown(_script_stats(""))
                    generate_voice_btn = gr.Button("Generate Voice", variant="primary", elem_classes="primary")
                    scene_audio = gr.Audio(label="Scene voice", type="filepath")
                    voice_status = gr.Markdown(_voice_status(initial.scenes[0]), elem_classes="compact-status")
                    with gr.Accordion("Animation", open=True):
                        animation = gr.Dropdown([("Linear", "linear"), ("Smooth", "smooth"), ("There and back", "there_and_back"), ("Wiggle", "wiggle")], value="smooth", label="Preset")
                        delay = gr.Slider(0.0, 1.0, value=0.1, step=0.05, label="Subpath delay")
                        scale = gr.Slider(0.1, 5.0, value=2.0, step=0.1, label="Scale")
                    with gr.Accordion("Duration & Transition", open=True):
                        duration = gr.Number(value=5.0, minimum=0.5, label="Scene duration (seconds)")
                        scene_auto_duration = gr.Checkbox(value=True, label="Auto from voice")
                        transition_type = gr.Dropdown([("Fade", "fade"), ("None", "none")], value="fade", label="Transition")
                        transition_duration = gr.Slider(0, 2.0, value=0.3, step=0.05, label="Transition duration")

            with gr.Column(elem_classes="timeline-panel"):
                with gr.Row():
                    gr.Markdown("<span class='section-kicker'>Scene Timeline · drag cards to reorder</span>")
                    add_scene_btn = gr.Button("＋ Add", size="sm")
                    duplicate_scene_btn = gr.Button("⧉ Duplicate", size="sm")
                    delete_scene_btn = gr.Button("Delete", size="sm")
                timeline_html = gr.HTML(render_timeline(initial_project, initial_scene_id))
                timeline_event = gr.Textbox(elem_id="timeline-event", container=False, show_label=False)

        refresh_outputs = [
            project_state, selected_scene_state, timeline_html, project_title,
            scene_name, image, sketch_preview, image_prompt, preserve_colors, color_count,
            script, script_stats, scene_audio, voice_status, duration, scene_auto_duration,
            animation, delay, scale, transition_type, transition_duration,
            language, provider, voice, speed, pitch, volume, global_auto_duration,
            aspect_ratio, fps, resolution,
        ]
        timeline_event.change(_timeline_event, [timeline_event, project_state, selected_scene_state], refresh_outputs)
        add_scene_btn.click(lambda p, s: _button_action("add", p, s), [project_state, selected_scene_state], refresh_outputs)
        duplicate_scene_btn.click(lambda p, s: _button_action("duplicate", p, s), [project_state, selected_scene_state], refresh_outputs)
        delete_scene_btn.click(lambda p, s: _button_action("delete", p, s), [project_state, selected_scene_state], refresh_outputs)
        new_project_btn.click(_new_project, outputs=refresh_outputs)

        scene_inputs = [project_state, selected_scene_state, scene_name, image, image_prompt, preserve_colors, color_count, script, duration, scene_auto_duration, animation, delay, scale, transition_type, transition_duration]
        scene_outputs = [project_state, timeline_html, script_stats, voice_status]
        for component in [scene_name, image, image_prompt, preserve_colors, color_count, script, duration, scene_auto_duration, animation, delay, scale, transition_type, transition_duration]:
            component.change(_sync_scene, scene_inputs, scene_outputs)

        project_title.change(_update_title, [project_state, project_title], project_state)
        voice_inputs = [project_state, selected_scene_state, language, provider, voice, speed, pitch, volume, global_auto_duration]
        voice_outputs = [project_state, timeline_html, provider, voice, voice_provider_status]
        for component in [language, provider, voice, speed, pitch, volume, global_auto_duration]:
            component.change(_update_voice_settings, voice_inputs, voice_outputs)
        refresh_voices_btn.click(_refresh_voices, project_state, [voice, voice_provider_status])
        preview_voice_btn.click(_preview_voice, project_state, [voice_sample, voice_provider_status])

        video_inputs = [project_state, aspect_ratio, fps, resolution]
        for component in [aspect_ratio, fps, resolution]:
            component.change(_update_video_settings, video_inputs, project_state)

        generate_sketch_btn.click(_generate_sketch, [project_state, selected_scene_state], [project_state, sketch_preview, timeline_html, render_status])
        generate_voice_btn.click(_generate_scene_voice, [project_state, selected_scene_state], [project_state, timeline_html, scene_audio, voice_status, duration])
        generate_all_btn.click(_generate_all_voices, [project_state, selected_scene_state], [project_state, timeline_html, batch_status, scene_audio, voice_status, duration])
        preview_scene_btn.click(_preview_scene, [project_state, selected_scene_state], [project_state, timeline_html, scene_video, render_status])
        preview_project_btn.click(_preview_project, project_state, [full_video, render_status])
        export_btn.click(_preview_project, project_state, [full_video, render_status])
        save_btn.click(_save_project, project_state, [saved_file, render_status])
        load_file.upload(_load_project, load_file, [*refresh_outputs, render_status])
    return demo


class TTSGeneratePayload(BaseModel):
    provider: str = "vieneu"
    text: str = Field(min_length=1)
    language: str = "vi"
    voiceId: str = "default"
    speed: float = Field(default=1.0, ge=0.75, le=1.5)
    pitch: float = Field(default=1.0, ge=0.5, le=2.0)


def create_app() -> FastAPI:
    api = FastAPI(title="Sketch2Motion API", version="2.0")

    @api.get("/", include_in_schema=False)
    def studio_redirect():
        return RedirectResponse(url="/studio/")

    @api.get("/api/health")
    def health():
        return {"status": "ok", "ttsProviders": list(default_tts_service.providers)}

    @api.get("/api/tts/voices")
    def voices(provider: str = Query("vieneu"), language: str = Query("vi")):
        try:
            result = default_tts_service.get_voices(provider, language)
        except Exception as error:
            raise HTTPException(status_code=503, detail=str(error)) from error
        return {"voices": [{"id": item.id, "name": item.name, "language": item.language, "description": item.description} for item in result]}

    @api.post("/api/tts/generate")
    def generate_tts(payload: TTSGeneratePayload):
        try:
            result = default_tts_service.synthesize(payload.provider, SynthesisInput(
                text=payload.text, voice_id=payload.voiceId, language=payload.language,
                speed=payload.speed, pitch=payload.pitch,
            ))
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        except Exception as error:
            raise HTTPException(status_code=503, detail=str(error)) from error
        filename = Path(result.audio_url).name
        return {"audioUrl": f"/generated/audio/{filename}", "duration": result.duration, "cacheKey": result.cache_key, "cached": result.cached}

    api.mount("/generated", StaticFiles(directory=str(GENERATED)), name="generated")
    return gr.mount_gradio_app(api, build_demo(), path="/studio")


app = create_app()


if __name__ == "__main__":
    uvicorn.run(app, host=os.getenv("SKETCH2MOTION_HOST", "127.0.0.1"), port=int(os.getenv("SKETCH2MOTION_PORT", "7880")))
