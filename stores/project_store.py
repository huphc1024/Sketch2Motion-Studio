"""Pure project-state actions used by the UI and tests."""

from __future__ import annotations

from copy import deepcopy
from typing import Any
from uuid import uuid4

from models.project import Scene, VideoProject, migrate_project, new_scene


class ProjectStore:
    """Immutable-style helpers around serializable project dictionaries."""

    @staticmethod
    def normalize(project: dict[str, Any] | VideoProject) -> dict[str, Any]:
        model = project if isinstance(project, VideoProject) else migrate_project(project)
        return model.to_dict()

    @staticmethod
    def selected_scene(project: dict[str, Any], scene_id: str | None) -> Scene:
        model = migrate_project(project)
        return next((scene for scene in model.scenes if scene.id == scene_id), model.scenes[0])

    @staticmethod
    def add_scene(project: dict[str, Any], after_scene_id: str | None = None) -> tuple[dict[str, Any], str]:
        model = migrate_project(project)
        scene = new_scene(len(model.scenes))
        index = len(model.scenes)
        if after_scene_id:
            current = next((i for i, item in enumerate(model.scenes) if item.id == after_scene_id), None)
            if current is not None:
                index = current + 1
        model.scenes.insert(index, scene)
        ProjectStore._renumber_default_names(model.scenes)
        return model.to_dict(), scene.id

    @staticmethod
    def delete_scene(project: dict[str, Any], scene_id: str) -> tuple[dict[str, Any], str]:
        model = migrate_project(project)
        index = next((i for i, scene in enumerate(model.scenes) if scene.id == scene_id), 0)
        if len(model.scenes) == 1:
            replacement = new_scene()
            model.scenes = [replacement]
            return model.to_dict(), replacement.id
        model.scenes = [scene for scene in model.scenes if scene.id != scene_id]
        ProjectStore._renumber_default_names(model.scenes)
        selected = model.scenes[min(index, len(model.scenes) - 1)].id
        return model.to_dict(), selected

    @staticmethod
    def duplicate_scene(project: dict[str, Any], scene_id: str) -> tuple[dict[str, Any], str]:
        model = migrate_project(project)
        index = next((i for i, scene in enumerate(model.scenes) if scene.id == scene_id), 0)
        duplicate = deepcopy(model.scenes[index])
        duplicate.id = str(uuid4())
        duplicate.name = f"{duplicate.name} copy"
        duplicate.preview_url = None
        model.scenes.insert(index + 1, duplicate)
        return model.to_dict(), duplicate.id

    @staticmethod
    def move_scene(project: dict[str, Any], scene_id: str, target_scene_id: str) -> dict[str, Any]:
        model = migrate_project(project)
        if scene_id == target_scene_id:
            return model.to_dict()
        source = next((scene for scene in model.scenes if scene.id == scene_id), None)
        target = next((scene for scene in model.scenes if scene.id == target_scene_id), None)
        if source is None or target is None:
            return model.to_dict()
        model.scenes.remove(source)
        target_index = model.scenes.index(target)
        model.scenes.insert(target_index, source)
        return model.to_dict()

    @staticmethod
    def update_scene(project: dict[str, Any], scene_id: str, **changes: Any) -> dict[str, Any]:
        model = migrate_project(project)
        scene = next((item for item in model.scenes if item.id == scene_id), None)
        if scene is None:
            return model.to_dict()
        old_script = scene.script
        for key, value in changes.items():
            if key == "transition" and isinstance(value, dict):
                scene.transition.type = str(value.get("type", scene.transition.type))
                scene.transition.duration = max(0.0, float(value.get("duration", scene.transition.duration)))
            elif hasattr(scene, key):
                setattr(scene, key, value)
        if "script" in changes and str(changes["script"]) != old_script and scene.audio_url:
            scene.tts_status = "outdated"
            scene.tts_error = "Script changed — regenerate voice."
        if scene.auto_duration and scene.audio_duration is not None and "transition" in changes:
            scene.duration = max(0.5, scene.audio_duration + scene.transition.duration)
        scene.preview_url = None
        return model.to_dict()

    @staticmethod
    def update_project(project: dict[str, Any], *, title: str | None = None, voice: dict[str, Any] | None = None, video: dict[str, Any] | None = None) -> dict[str, Any]:
        model = migrate_project(project)
        if title is not None:
            model.title = title.strip() or "Untitled video"
        if voice is not None:
            from models.project import VoiceSettings
            model.voice_settings = VoiceSettings.from_dict({**model.to_dict()["voice_settings"], **voice})
            for scene in model.scenes:
                scene.auto_duration = model.voice_settings.auto_duration
        if video is not None:
            from models.project import VideoSettings
            model.video_settings = VideoSettings.from_dict({**model.to_dict()["video_settings"], **video})
        return model.to_dict()

    @staticmethod
    def update_all_scene_visuals(
        project: dict[str, Any], *, preserve_colors: bool, color_count: int, animation_scale: float,
    ) -> dict[str, Any]:
        model = migrate_project(project)
        palette = max(2, min(16, int(color_count)))
        scale = max(0.1, float(animation_scale))
        for scene in model.scenes:
            if scene.preserve_colors != bool(preserve_colors) or scene.color_count != palette:
                scene.svg_path = None
            scene.preserve_colors = bool(preserve_colors)
            scene.color_count = palette
            scene.animation_scale = scale
            scene.preview_url = None
        return model.to_dict()

    @staticmethod
    def _renumber_default_names(scenes: list[Scene]) -> None:
        for index, scene in enumerate(scenes):
            if scene.name.startswith("Scene ") and not scene.name.endswith(" copy"):
                scene.name = f"Scene {index + 1:02d}"
