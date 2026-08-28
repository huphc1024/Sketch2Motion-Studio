"""TTS registry, deterministic cache, validation, and sequential queue."""

from __future__ import annotations

import hashlib
import json
import subprocess
import wave
from pathlib import Path
from threading import Lock
from typing import Iterable, Iterator

from .base import TTSProvider
from .providers import VieNeuProvider
from .types import SynthesisInput, TTSResult, TTSVoice


class TTSService:
    def __init__(self, cache_dir: str | Path = "generated/audio") -> None:
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.providers: dict[str, TTSProvider] = {}
        self._queue_lock = Lock()

    def register(self, provider: TTSProvider) -> None:
        self.providers[provider.id] = provider

    def get_provider(self, provider_id: str) -> TTSProvider:
        try:
            return self.providers[provider_id]
        except KeyError as error:
            raise ValueError(f"Unknown TTS provider: {provider_id}") from error

    def get_voices(self, provider_id: str, language: str) -> list[TTSVoice]:
        if language == "none":
            return []
        provider = self.get_provider(provider_id)
        if language not in provider.supported_languages:
            return []
        return [voice for voice in provider.get_voices() if voice.language == language]

    def cache_key(self, provider_id: str, input: SynthesisInput) -> str:
        canonical = json.dumps(
            {
                "provider": provider_id,
                "voiceId": input.voice_id,
                "language": input.language,
                "speed": round(input.speed, 4),
                "pitch": round(input.pitch, 4),
                "text": input.text.strip(),
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def synthesize(self, provider_id: str, input: SynthesisInput) -> TTSResult:
        provider = self.get_provider(provider_id)
        provider.validate(input)
        key = self.cache_key(provider_id, input)
        cached = next((path for path in self.cache_dir.glob(f"{key}.*") if path.suffix in {".wav", ".mp3"}), None)
        if cached:
            return TTSResult(str(cached.resolve()), audio_duration(cached), key, cached=True)

        with self._queue_lock:
            cached = next((path for path in self.cache_dir.glob(f"{key}.*") if path.suffix in {".wav", ".mp3"}), None)
            if cached:
                return TTSResult(str(cached.resolve()), audio_duration(cached), key, cached=True)
            audio = provider.synthesize(input)
            if not audio.content:
                raise RuntimeError(f"{provider.name} returned empty audio.")
            suffix = audio.suffix if audio.suffix in {".wav", ".mp3"} else ".wav"
            output = self.cache_dir / f"{key}{suffix}"
            temporary = output.with_suffix(f"{suffix}.part")
            temporary.write_bytes(audio.content)
            try:
                duration = audio_duration(temporary, format_hint=suffix)
                temporary.replace(output)
            except Exception:
                temporary.unlink(missing_ok=True)
                raise
            return TTSResult(str(output.resolve()), duration, key, cached=False)

    def synthesize_queue(self, provider_id: str, inputs: Iterable[SynthesisInput]) -> Iterator[TTSResult]:
        """Generate serially; the lock also enforces concurrency=1 across UI jobs."""
        for input in inputs:
            yield self.synthesize(provider_id, input)


def audio_duration(path: str | Path, format_hint: str | None = None) -> float:
    path = Path(path)
    if (format_hint or path.suffix).lower() == ".wav":
        try:
            with wave.open(str(path), "rb") as stream:
                if stream.getframerate() <= 0:
                    raise ValueError("Invalid WAV sample rate.")
                duration = stream.getnframes() / stream.getframerate()
                if duration <= 0:
                    raise ValueError("WAV contains no audio frames.")
                return duration
        except (wave.Error, EOFError):
            pass
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
            check=True,
            capture_output=True,
            text=True,
        )
        duration = float(result.stdout.strip())
    except (OSError, subprocess.CalledProcessError, ValueError) as error:
        raise ValueError(f"Invalid audio file returned by TTS: {path}") from error
    if duration <= 0:
        raise ValueError("Generated audio has zero duration.")
    return duration


default_tts_service = TTSService()
default_tts_service.register(VieNeuProvider())
