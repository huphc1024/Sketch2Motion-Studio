"""Types shared by every TTS provider."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TTSVoice:
    id: str
    name: str
    language: str
    description: str = ""
    supports_pitch: bool = False


@dataclass(frozen=True, slots=True)
class SynthesisInput:
    text: str
    voice_id: str
    language: str
    speed: float = 1.0
    pitch: float = 1.0


@dataclass(frozen=True, slots=True)
class ProviderAudio:
    content: bytes
    suffix: str = ".wav"
    content_type: str = "audio/wav"


@dataclass(frozen=True, slots=True)
class TTSResult:
    audio_url: str
    duration: float
    cache_key: str
    cached: bool = False
