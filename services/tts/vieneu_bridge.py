"""Optional VieNeu SDK bridge for Sketch2Motion.

Install ``requirements-vieneu.txt`` in a separate environment, then run:

    python -m services.tts.vieneu_bridge

The bridge deliberately lives outside the main Gradio process so model memory
is isolated and the editor can keep TTS concurrency at one.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path
from threading import RLock
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from starlette.background import BackgroundTask

from services.tts.vieneu_voices import v3_turbo_voice_payload


app = FastAPI(title="Sketch2Motion VieNeu Bridge", version="1.0")
_model: Any = None
_model_lock = RLock()


class SynthesizePayload(BaseModel):
    text: str = Field(min_length=1)
    voiceId: str = "default"
    language: str = "vi"
    speed: float = Field(default=1.0, ge=0.75, le=1.5)
    pitch: float = Field(default=1.0, ge=0.5, le=2.0)


def _load_model():
    global _model
    if _model is not None:
        return _model
    with _model_lock:
        if _model is not None:
            return _model
        try:
            from vieneu import Vieneu
        except ImportError as error:
            raise RuntimeError(
                "VieNeu SDK is not installed. Install requirements-vieneu.txt in this bridge environment."
            ) from error
        mode = os.getenv("VIENEU_MODE", "v3turbo").strip().lower()
        kwargs: dict[str, Any] = {}
        if mode == "remote":
            kwargs.update({
                "mode": "remote",
                "api_base": os.getenv("VIENEU_REMOTE_API_BASE", "http://127.0.0.1:23333/v1"),
                "model_name": os.getenv("VIENEU_MODEL", "pnnbao-ump/VieNeu-TTS"),
            })
        elif mode == "v3turbo":
            kwargs.update({
                "mode": "v3turbo",
                "backbone_repo": os.getenv("VIENEU_MODEL", "pnnbao-ump/VieNeu-TTS-v3-Turbo"),
                "device": os.getenv("VIENEU_DEVICE", "cpu"),
                "backend": os.getenv("VIENEU_BACKEND", "auto"),
                "precision": os.getenv("VIENEU_PRECISION", "int8"),
            })
            threads = os.getenv("VIENEU_THREADS")
            if threads:
                kwargs["threads"] = max(1, int(threads))
        else:
            kwargs["mode"] = mode
            model = os.getenv("VIENEU_MODEL")
            device = os.getenv("VIENEU_DEVICE")
            if model:
                kwargs["backbone_repo"] = model
            if device:
                kwargs["backbone_device"] = device
        _model = Vieneu(**kwargs)
        return _model


@app.get("/health")
def health():
    return {
        "status": "ok",
        "modelLoaded": _model is not None,
        "mode": os.getenv("VIENEU_MODE", "v3turbo"),
        "builtInVoiceCount": len(v3_turbo_voice_payload()),
    }


def _normalize_voices(available: Any) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    seen: set[str] = set()
    if isinstance(available, dict):
        available = available.get("voices") or available.get("data") or list(available)
    if not isinstance(available, (list, tuple)):
        return result
    for item in available:
        description = ""
        if isinstance(item, dict):
            voice_id = str(item.get("id") or item.get("voiceId") or item.get("name") or "")
            name = str(item.get("displayName") or item.get("description") or item.get("name") or voice_id)
            description = str(item.get("description") or "")
        elif isinstance(item, (list, tuple)) and len(item) >= 2:
            name, voice_id = str(item[0]), str(item[1])
        else:
            voice_id = name = str(item)
        if voice_id and voice_id not in seen:
            seen.add(voice_id)
            result.append({"id": voice_id, "name": name, "language": "vi", "description": description})
    return result


@app.get("/voices")
def voices():
    try:
        tts = _load_model()
        available = tts.list_preset_voices()
    except Exception as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    return {"voices": _normalize_voices(available)}


@app.post("/synthesize")
def synthesize(payload: SynthesizePayload):
    if payload.language != "vi":
        raise HTTPException(status_code=400, detail="This bridge exposes VieNeu for Vietnamese only.")
    output_dir = Path(tempfile.gettempdir()) / "sketch2motion-vieneu"
    output_dir.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(prefix="voice-", suffix=".wav", dir=output_dir, delete=False)
    output = Path(handle.name)
    handle.close()
    try:
        with _model_lock:
            tts = _load_model()
            kwargs: dict[str, Any] = {"text": payload.text.strip()}
            if payload.voiceId not in {"", "default"}:
                if os.getenv("VIENEU_MODE", "v3turbo").strip().lower() == "v3turbo":
                    kwargs["voice"] = payload.voiceId
                else:
                    kwargs["voice"] = tts.get_preset_voice(payload.voiceId)
            audio = tts.infer(**kwargs)
            tts.save(audio, str(output))
        if abs(payload.speed - 1.0) > 0.001:
            adjusted = output.with_name(f"{output.stem}-speed.wav")
            subprocess.run(
                ["ffmpeg", "-y", "-i", str(output), "-filter:a", f"atempo={payload.speed:.4f}", str(adjusted)],
                check=True,
                capture_output=True,
            )
            adjusted.replace(output)
    except Exception as error:
        output.unlink(missing_ok=True)
        detail = str(error)
        status = 507 if "memory" in detail.lower() or "cuda out" in detail.lower() else 503
        raise HTTPException(status_code=status, detail=detail) from error
    if not output.is_file() or output.stat().st_size < 44:
        output.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail="VieNeu produced an invalid WAV file.")
    return FileResponse(
        output,
        media_type="audio/wav",
        filename="voice.wav",
        background=BackgroundTask(output.unlink, missing_ok=True),
    )


if __name__ == "__main__":
    uvicorn.run(
        app,
        host=os.getenv("VIENEU_BRIDGE_HOST", "127.0.0.1"),
        port=int(os.getenv("VIENEU_BRIDGE_PORT", "8001")),
    )
