"""Typed, serializable project and scene models.

The UI stores plain dictionaries in ``gr.State``.  These dataclasses are the
validation boundary used by stores, persistence, TTS, and rendering services.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal
from uuid import uuid4


TTSStatus = Literal["idle", "generating", "ready", "outdated", "error"]
AspectRatio = Literal["9:16", "16:9", "1:1"]
Resolution = Literal["720p", "1080p"]


@dataclass(slots=True)
class Transition:
    type: str = "fade"
    duration: float = 0.3

    @classmethod
    def from_dict(cls, value: Any) -> "Transition":
        value = value if isinstance(value, dict) else {}
        return cls(
            type=str(value.get("type") or "fade"),
            duration=max(0.0, float(value.get("duration", 0.3))),
        )


@dataclass(slots=True)
class Scene:
    id: str
    name: str
    image: str | None = None
    image_prompt: str = ""
    svg_path: str | None = None
    preserve_colors: bool = False
    color_count: int = 8
    script: str = ""
    audio_url: str | None = None
    audio_duration: float | None = None
    audio_hash: str | None = None
    duration: float = 5.0
    auto_duration: bool = True
    animation_preset: str = "smooth"
    animation_delay: float = 0.1
    animation_scale: float = 2.0
    transition: Transition = field(default_factory=Transition)
    tts_status: TTSStatus = "idle"
    tts_error: str | None = None
    preview_url: str | None = None

    @classmethod
    def from_dict(cls, value: Any, index: int = 0) -> "Scene":
        value = value if isinstance(value, dict) else {}
        status = str(value.get("tts_status") or value.get("ttsStatus") or "idle")
        if status not in {"idle", "generating", "ready", "outdated", "error"}:
            status = "idle"
        audio_duration = value.get("audio_duration", value.get("audioDuration"))
        return cls(
            id=str(value.get("id") or uuid4()),
            name=str(value.get("name") or f"Scene {index + 1:02d}"),
            image=_optional_str(value.get("image")),
            image_prompt=str(value.get("image_prompt", value.get("imagePrompt", "")) or ""),
            svg_path=_optional_str(value.get("svg_path", value.get("svgPath"))),
            preserve_colors=bool(value.get("preserve_colors", value.get("preserveColors", False))),
            color_count=max(2, min(16, int(value.get("color_count", value.get("colorCount", 8))))),
            script=str(value.get("script") or ""),
            audio_url=_optional_str(value.get("audio_url", value.get("audioUrl"))),
            audio_duration=float(audio_duration) if audio_duration is not None else None,
            audio_hash=_optional_str(value.get("audio_hash", value.get("audioHash"))),
            duration=max(0.5, float(value.get("duration", 5.0))),
            auto_duration=bool(value.get("auto_duration", value.get("autoDuration", True))),
            animation_preset=str(value.get("animation_preset", value.get("animationPreset", "smooth"))),
            animation_delay=max(0.0, float(value.get("animation_delay", value.get("animationDelay", 0.1)))),
            animation_scale=max(0.1, float(value.get("animation_scale", value.get("animationScale", 2.0)))),
            transition=Transition.from_dict(value.get("transition")),
            tts_status=status,  # type: ignore[arg-type]
            tts_error=_optional_str(value.get("tts_error", value.get("ttsError"))),
            preview_url=_optional_str(value.get("preview_url", value.get("previewUrl"))),
        )

    def apply_audio(self, audio_url: str, audio_duration: float, audio_hash: str) -> None:
        self.audio_url = audio_url
        self.audio_duration = max(0.0, audio_duration)
        self.audio_hash = audio_hash
        self.tts_status = "ready"
        self.tts_error = None
        if self.auto_duration:
            self.duration = max(0.5, self.audio_duration + self.transition.duration)


@dataclass(slots=True)
class VoiceSettings:
    language: Literal["vi", "en", "none"] = "vi"
    provider: str = "vieneu"
    voice_id: str = "default"
    speed: float = 1.0
    pitch: float = 1.0
    volume: int = 100
    auto_duration: bool = True

    @classmethod
    def from_dict(cls, value: Any) -> "VoiceSettings":
        value = value if isinstance(value, dict) else {}
        language = str(value.get("language") or "vi")
        if language not in {"vi", "en", "none"}:
            language = "vi"
        return cls(
            language=language,  # type: ignore[arg-type]
            provider=str(value.get("provider") or ("none" if language == "none" else "vieneu")),
            voice_id=str(value.get("voice_id", value.get("voiceId", "default")) or "default"),
            speed=max(0.75, min(1.5, float(value.get("speed", 1.0)))),
            pitch=max(0.5, min(2.0, float(value.get("pitch", 1.0)))),
            volume=max(0, min(100, int(value.get("volume", 100)))),
            auto_duration=bool(value.get("auto_duration", value.get("autoDuration", True))),
        )


@dataclass(slots=True)
class VideoSettings:
    aspect_ratio: AspectRatio = "16:9"
    fps: Literal[30, 60] = 30
    resolution: Resolution = "1080p"

    @classmethod
    def from_dict(cls, value: Any) -> "VideoSettings":
        value = value if isinstance(value, dict) else {}
        aspect = str(value.get("aspect_ratio", value.get("aspectRatio", "16:9")))
        if aspect not in {"9:16", "16:9", "1:1"}:
            aspect = "16:9"
        fps = 60 if int(value.get("fps", 30)) == 60 else 30
        resolution = "720p" if value.get("resolution") == "720p" else "1080p"
        return cls(aspect_ratio=aspect, fps=fps, resolution=resolution)  # type: ignore[arg-type]

    @property
    def dimensions(self) -> tuple[int, int]:
        long_edge = 1920 if self.resolution == "1080p" else 1280
        short_edge = 1080 if self.resolution == "1080p" else 720
        if self.aspect_ratio == "9:16":
            return short_edge, long_edge
        if self.aspect_ratio == "1:1":
            edge = 1080 if self.resolution == "1080p" else 720
            return edge, edge
        return long_edge, short_edge


@dataclass(slots=True)
class VideoProject:
    id: str
    title: str
    scenes: list[Scene]
    voice_settings: VoiceSettings = field(default_factory=VoiceSettings)
    video_settings: VideoSettings = field(default_factory=VideoSettings)
    schema_version: int = 2

    @classmethod
    def from_dict(cls, value: Any) -> "VideoProject":
        return migrate_project(value)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def new_scene(index: int = 0, *, name: str | None = None) -> Scene:
    return Scene(id=str(uuid4()), name=name or f"Scene {index + 1:02d}")


def new_project(title: str = "Untitled video") -> VideoProject:
    return VideoProject(id=str(uuid4()), title=title, scenes=[new_scene()])


def migrate_project(value: Any) -> VideoProject:
    """Load v2 data and migrate the original one-image project shape."""
    if not isinstance(value, dict):
        return new_project()

    raw_scenes = value.get("scenes")
    if not isinstance(raw_scenes, list) or not raw_scenes:
        legacy_scene = {
            "name": "Scene 01",
            "image": value.get("image") or value.get("input_image"),
            "svg_path": value.get("svg_path"),
            "preserve_colors": value.get("preserve_colors", False),
            "duration": value.get("duration", value.get("manim_dur", 5.0)),
            "animation_preset": value.get("animation_preset", value.get("draw_type", "smooth")),
        }
        raw_scenes = [legacy_scene]

    scenes = [Scene.from_dict(scene, index) for index, scene in enumerate(raw_scenes)]
    return VideoProject(
        id=str(value.get("id") or uuid4()),
        title=str(value.get("title") or "Untitled video"),
        scenes=scenes,
        voice_settings=VoiceSettings.from_dict(value.get("voice_settings", value.get("voiceSettings"))),
        video_settings=VideoSettings.from_dict(value.get("video_settings", value.get("videoSettings"))),
        schema_version=2,
    )


def _optional_str(value: Any) -> str | None:
    return str(value) if value not in (None, "") else None
