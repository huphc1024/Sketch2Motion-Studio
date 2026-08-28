"""HTTP client for a local VieNeu audio bridge.

VieNeu's official remote mode returns model speech tokens and expects its SDK
to decode them.  To keep the heavy model/codec outside the Gradio frontend, this
provider talks to a small local bridge that returns a WAV/MP3 response (or JSON
containing base64 audio / a local audio URL).  Its URL and endpoint are fully
configurable and no VieNeu model is loaded in the web process.
"""

from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

from services.tts.base import TTSProvider
from services.tts.types import ProviderAudio, SynthesisInput, TTSVoice
from services.tts.vieneu_voices import v3_turbo_voices


class VieNeuProvider(TTSProvider):
    id = "vieneu"
    name = "VieNeu TTS"
    supported_languages = ("vi",)

    def __init__(self, base_url: str | None = None, timeout: float | None = None) -> None:
        self.base_url = (base_url or os.getenv("VIENEU_TTS_URL") or "http://127.0.0.1:8001").rstrip("/")
        self.synthesize_path = os.getenv("VIENEU_TTS_SYNTHESIZE_PATH", "/synthesize")
        self.voices_path = os.getenv("VIENEU_TTS_VOICES_PATH", "/voices")
        self.timeout = timeout or float(os.getenv("VIENEU_TTS_TIMEOUT", "180"))

    def get_voices(self) -> list[TTSVoice]:
        configured = os.getenv("VIENEU_TTS_VOICES")
        if configured:
            try:
                return self._parse_voices(json.loads(configured))
            except (json.JSONDecodeError, TypeError, ValueError):
                pass
        try:
            payload = self._request_json("GET", self.voices_path)
            voices = self._parse_voices(payload)
            if voices:
                return voices
        except RuntimeError:
            pass
        # The bundled local bridge defaults to VieNeu v3 Turbo. Keep its full
        # catalog visible while the lazy-loaded model is still offline.
        return v3_turbo_voices()

    def synthesize(self, input: SynthesisInput) -> ProviderAudio:
        self.validate(input)
        payload = {
            "text": input.text.strip(),
            "voiceId": input.voice_id,
            "voice_id": input.voice_id,
            "language": input.language,
            "speed": input.speed,
            "pitch": input.pitch,
        }
        url = urljoin(f"{self.base_url}/", self.synthesize_path.lstrip("/"))
        request = Request(
            url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Accept": "audio/wav, audio/mpeg, application/json", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                content = response.read()
                content_type = response.headers.get_content_type()
        except HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")[:500]
            if error.code in {500, 507} and "memory" in detail.lower():
                raise RuntimeError("VieNeu ran out of GPU memory. Reduce model load or keep TTS concurrency at 1.") from error
            raise RuntimeError(f"VieNeu returned HTTP {error.code}: {detail or error.reason}") from error
        except (URLError, TimeoutError, OSError) as error:
            raise RuntimeError(
                f"Cannot reach VieNeu at {self.base_url}. Start the service or update VIENEU_TTS_URL. ({error})"
            ) from error

        if content_type.startswith("audio/"):
            suffix = ".mp3" if content_type in {"audio/mpeg", "audio/mp3"} else ".wav"
            return ProviderAudio(content=content, suffix=suffix, content_type=content_type)

        try:
            body = json.loads(content.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise RuntimeError("VieNeu returned neither valid audio nor JSON.") from error
        return self._audio_from_json(body)

    def _request_json(self, method: str, path: str):
        request = Request(urljoin(f"{self.base_url}/", path.lstrip("/")), method=method)
        try:
            with urlopen(request, timeout=min(self.timeout, 10)) as response:
                return json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError) as error:
            raise RuntimeError(f"Could not load VieNeu voices: {error}") from error

    def _audio_from_json(self, body: object) -> ProviderAudio:
        if not isinstance(body, dict):
            raise RuntimeError("VieNeu JSON response must be an object.")
        encoded = body.get("audio") or body.get("audioBase64") or body.get("audio_base64")
        if encoded:
            try:
                content = base64.b64decode(str(encoded), validate=True)
            except ValueError as error:
                raise RuntimeError("VieNeu returned invalid base64 audio.") from error
            fmt = str(body.get("format") or "wav").lower()
            suffix = ".mp3" if fmt == "mp3" else ".wav"
            return ProviderAudio(content, suffix, "audio/mpeg" if suffix == ".mp3" else "audio/wav")

        audio_url = body.get("audioUrl") or body.get("audio_url") or body.get("path")
        if not audio_url:
            raise RuntimeError("VieNeu JSON response does not contain audioUrl or base64 audio.")
        value = str(audio_url)
        parsed = urlparse(value)
        if parsed.scheme in {"http", "https"}:
            request = Request(value, headers={"Accept": "audio/*"})
            try:
                with urlopen(request, timeout=self.timeout) as response:
                    content = response.read()
                    content_type = response.headers.get_content_type()
            except (HTTPError, URLError, TimeoutError, OSError) as error:
                raise RuntimeError(f"Could not download generated VieNeu audio: {error}") from error
            suffix = ".mp3" if content_type in {"audio/mpeg", "audio/mp3"} else ".wav"
            return ProviderAudio(content, suffix, content_type)

        path = Path(value)
        if not path.is_file():
            raise RuntimeError(f"VieNeu returned a missing audio path: {path}")
        suffix = ".mp3" if path.suffix.lower() == ".mp3" else ".wav"
        return ProviderAudio(path.read_bytes(), suffix, "audio/mpeg" if suffix == ".mp3" else "audio/wav")

    @staticmethod
    def _parse_voices(payload: object) -> list[TTSVoice]:
        if isinstance(payload, dict):
            payload = payload.get("voices") or payload.get("data") or []
        voices: list[TTSVoice] = []
        seen: set[str] = set()
        if not isinstance(payload, list):
            return voices
        for item in payload:
            if isinstance(item, dict):
                voice_id = str(item.get("id") or item.get("voiceId") or item.get("name") or "")
                if voice_id and voice_id not in seen:
                    seen.add(voice_id)
                    voices.append(TTSVoice(
                        id=voice_id,
                        name=str(item.get("displayName") or item.get("display_name") or item.get("name") or voice_id),
                        language="vi",
                        description=str(item.get("description") or ""),
                        supports_pitch=bool(item.get("supportsPitch", False)),
                    ))
            elif isinstance(item, (list, tuple)) and len(item) >= 2:
                voice_id = str(item[1])
                if voice_id and voice_id not in seen:
                    seen.add(voice_id)
                    voices.append(TTSVoice(id=voice_id, name=str(item[0]), language="vi"))
            elif isinstance(item, str) and item not in seen:
                seen.add(item)
                voices.append(TTSVoice(id=item, name=item, language="vi"))
        return voices
