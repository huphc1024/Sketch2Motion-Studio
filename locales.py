"""Display strings and localized choice labels for the Gradio interface."""

from typing import Final


ENGLISH: Final[str] = "en"
CHINESE: Final[str] = "zh"

LANGUAGE_CHOICES: Final[list[tuple[str, str]]] = [
    ("English", ENGLISH),
    ("中文", CHINESE),
]

UI_TEXT: Final[dict[str, dict[str, str]]] = {
    ENGLISH: {
        "heading": "## Doodle -> Sketch -> Video",
        "parameters": "Parameters",
        "duration": "Animation duration (s)",
        "delay": "Subpath delay ratio",
        "scale": "Scale factor",
        "drawing_style": "Drawing style",
        "preserve_colors": "Preserve colors",
        "palette_size": "Color palette size",
        "video_format": "Video format",
        "input_image": "Input doodle/photo",
        "sketch_preview": "Sketch preview",
        "video_preview": "Video preview",
        "generate_sketch": "Generate sketch",
        "generate_video": "Generate video",
        "linear": "Linear",
        "smooth": "Smooth",
        "there_and_back": "There and back",
        "wiggle": "Wiggle",
        "landscape": "Landscape 16:9 (1920x1080)",
        "portrait": "Portrait 9:16 (1080x1920)",
    },
    CHINESE: {
        "heading": "## 涂鸦 -> 线稿 -> 视频",
        "parameters": "参数设置",
        "duration": "动画时长（秒）",
        "delay": "子路径延迟比例",
        "scale": "缩放比例",
        "drawing_style": "绘制风格",
        "preserve_colors": "保留颜色",
        "palette_size": "调色板颜色数量",
        "video_format": "视频格式",
        "input_image": "输入涂鸦/照片",
        "sketch_preview": "线稿预览",
        "video_preview": "视频预览",
        "generate_sketch": "生成线稿",
        "generate_video": "生成视频",
        "linear": "线性",
        "smooth": "平滑",
        "there_and_back": "往返",
        "wiggle": "摆动",
        "landscape": "横屏 16:9 (1920x1080)",
        "portrait": "竖屏 9:16 (1080x1920)",
    },
}


def get_ui_text(language: str) -> dict[str, str]:
    """Return UI text for a supported language, defaulting to English."""
    language = {"English": ENGLISH, "中文": CHINESE}.get(language, language)
    return UI_TEXT.get(language, UI_TEXT[ENGLISH])


def drawing_style_choices(language: str) -> list[tuple[str, str]]:
    """Return localized drawing-style labels with stable renderer values."""
    text = get_ui_text(language)
    return [
        (text["linear"], "linear"),
        (text["smooth"], "smooth"),
        (text["there_and_back"], "there_and_back"),
        (text["wiggle"], "wiggle"),
    ]


def video_format_choices(language: str) -> list[tuple[str, str]]:
    """Return localized video-format labels with stable renderer values."""
    text = get_ui_text(language)
    return [
        (text["landscape"], "landscape"),
        (text["portrait"], "portrait"),
    ]


def normalize_drawing_style(value: str) -> str:
    """Accept either a localized label or the stable drawing-style value."""
    for language in UI_TEXT:
        for label, stable_value in drawing_style_choices(language):
            if value in (label, stable_value):
                return stable_value
    return value


def normalize_video_format(value: str) -> str:
    """Accept either a localized label or the stable video-format value."""
    for language in UI_TEXT:
        for label, stable_value in video_format_choices(language):
            if value in (label, stable_value):
                return stable_value
    return value
