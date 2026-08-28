"""Provider-neutral text-to-speech facade."""

from .service import TTSService, default_tts_service
from .types import SynthesisInput, TTSResult, TTSVoice

__all__ = ["SynthesisInput", "TTSResult", "TTSService", "TTSVoice", "default_tts_service"]
