"""Built-in voice metadata for the default VieNeu v3 Turbo model."""

from __future__ import annotations

from services.tts.types import TTSVoice


V3_TURBO_VOICE_DATA: tuple[tuple[str, str, str], ...] = (
    ("Adam", "Adam — Nam · Nam · Giọng đọc tự nhiên", "Nam, giọng Nam, tự nhiên"),
    ("Phạm Tuyên", "Phạm Tuyên — Nam · Bắc · Phong cách tự nhiên", "Nam, giọng Bắc, tự nhiên"),
    ("Minh Đức", "Minh Đức — Nam · Bắc · Phong cách tin tức", "Nam, giọng Bắc, tin tức"),
    ("Thanh Bình", "Thanh Bình — Nam · Bắc · Phong cách kể chuyện", "Nam, giọng Bắc, kể chuyện"),
    ("Ngọc Huyền", "Ngọc Huyền — Nữ · Bắc · Giọng đọc tự nhiên", "Nữ, giọng Bắc, tự nhiên"),
    ("Trúc Ly", "Trúc Ly — Nữ · Bắc · Phong cách tự nhiên", "Nữ, giọng Bắc, tự nhiên"),
    ("Đoan Trang", "Đoan Trang — Nữ · Bắc · Phong cách tự nhiên", "Nữ, giọng Bắc, tự nhiên"),
    ("Ngọc Linh", "Ngọc Linh — Nữ · Bắc · Phong cách kể chuyện", "Nữ, giọng Bắc, kể chuyện"),
    ("Mai Anh", "Mai Anh — Nữ · Bắc · Phong cách tin tức", "Nữ, giọng Bắc, tin tức"),
    ("Quỳnh Anh", "Quỳnh Anh — Nữ · Bắc · Phong cách đọc truyện", "Nữ, giọng Bắc, đọc truyện"),
    ("Quang Sơn", "Quang Sơn — Nam · Trung · Phong cách tự nhiên", "Nam, giọng Trung, tự nhiên"),
    ("Ngọc Trân", "Ngọc Trân — Nữ · Trung · Phong cách tự nhiên", "Nữ, giọng Trung, tự nhiên"),
    ("Xuân Vĩnh", "Xuân Vĩnh — Nam · Nam · Phong cách tự nhiên", "Nam, giọng Nam, tự nhiên"),
    ("Thái Sơn", "Thái Sơn — Nam · Nam · Phong cách kể chuyện", "Nam, giọng Nam, kể chuyện"),
    ("Minh Triết", "Minh Triết — Nam · Nam · Phong cách tin tức", "Nam, giọng Nam, tin tức"),
    ("Đức Trí", "Đức Trí — Nam · Nam · Phong cách đọc truyện", "Nam, giọng Nam, đọc truyện"),
    ("Thục Đoan", "Thục Đoan — Nữ · Nam · Phong cách kể chuyện", "Nữ, giọng Nam, kể chuyện"),
    ("Thùy Dung", "Thùy Dung — Nữ · Nam · Phong cách tin tức", "Nữ, giọng Nam, tin tức"),
    ("Mỹ Duyên", "Mỹ Duyên — Nữ · Nam · Phong cách đọc truyện", "Nữ, giọng Nam, đọc truyện"),
    ("Kim Thanh", "Kim Thanh — Nữ · Nam · Phong cách đọc truyện", "Nữ, giọng Nam, đọc truyện"),
)


def v3_turbo_voices() -> list[TTSVoice]:
    """Return fresh value objects so callers can safely modify the list."""
    return [TTSVoice(voice_id, label, "vi", description) for voice_id, label, description in V3_TURBO_VOICE_DATA]


def v3_turbo_voice_payload() -> list[dict[str, str]]:
    """Return the bridge/API representation of the built-in voices."""
    return [
        {"id": voice_id, "name": label, "language": "vi", "description": description}
        for voice_id, label, description in V3_TURBO_VOICE_DATA
    ]
