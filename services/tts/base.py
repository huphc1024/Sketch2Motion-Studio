"""Abstract TTS provider contract."""

from __future__ import annotations

from abc import ABC, abstractmethod

from .types import ProviderAudio, SynthesisInput, TTSVoice


class TTSProvider(ABC):
    id: str
    name: str
    supported_languages: tuple[str, ...]

    @abstractmethod
    def get_voices(self) -> list[TTSVoice]:
        raise NotImplementedError

    @abstractmethod
    def synthesize(self, input: SynthesisInput) -> ProviderAudio:
        raise NotImplementedError

    def validate(self, input: SynthesisInput) -> None:
        if not input.text.strip():
            raise ValueError("Script is empty.")
        if input.language not in self.supported_languages:
            raise ValueError(f"{self.name} does not support language {input.language!r}.")
