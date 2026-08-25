import os
import sys
import tempfile
from pathlib import Path
from typing import Optional
from xml.etree import ElementTree as ET

from manim import BLACK, ORIGIN, WHITE, FullScreenRectangle, LaggedStart, SVGMobject
from manim import Scene, config, linear, smooth, there_and_back, wiggle

from sketch2svg_color import BACKGROUND_LAYER_ID, SVG_NS


def _float_arg(value: str, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _scene_arguments() -> tuple[str, float, float, float, str]:
    args = sys.argv[1:]
    legacy_args = args[-5:] if len(args) >= 5 and args[-5].endswith(".svg") else []
    svg_path = os.environ.get("SKETCH2MOTION_SVG") or (
        legacy_args[0] if legacy_args else "sketch.svg"
    )
    duration = _float_arg(
        os.environ.get("SKETCH2MOTION_DURATION") or (legacy_args[1] if legacy_args else ""),
        10.0,
    )
    delay = _float_arg(
        os.environ.get("SKETCH2MOTION_DELAY") or (legacy_args[2] if legacy_args else ""),
        0.1,
    )
    scale = _float_arg(
        os.environ.get("SKETCH2MOTION_SCALE") or (legacy_args[3] if legacy_args else ""),
        2.0,
    )
    draw_type = os.environ.get("SKETCH2MOTION_DRAW") or (
        legacy_args[4] if legacy_args else "smooth"
    )
    return svg_path, duration, delay, scale, draw_type


def _background_color(svg_path: str) -> str:
    try:
        root = ET.parse(svg_path).getroot()
        return root.get("data-background-color", WHITE)
    except (ET.ParseError, OSError):
        legacy_background = Path(svg_path).with_suffix(".bg")
        if legacy_background.exists():
            return legacy_background.read_text(encoding="utf-8").strip()
        return WHITE


def _foreground_svg(svg_path: str) -> tuple[str, Optional[Path]]:
    """Return a temporary SVG with the static background removed for animation."""
    try:
        tree = ET.parse(svg_path)
    except (ET.ParseError, OSError):
        return svg_path, None

    root = tree.getroot()
    background = root.find(f"{{{SVG_NS}}}rect[@id='{BACKGROUND_LAYER_ID}']")
    if background is None:
        return svg_path, None

    root.remove(background)
    with tempfile.NamedTemporaryFile(prefix="sketch2motion-", suffix=".svg", delete=False) as file:
        tree.write(file, encoding="utf-8", xml_declaration=True)
        return file.name, Path(file.name)


svg_file, duration, delay, scale, draw_type = _scene_arguments()
draw_dict = {
    "linear": linear,
    "smooth": smooth,
    "there_and_back": there_and_back,
    "wiggle": wiggle,
}
config.background_color = BLACK


def _configure_frame_aspect() -> None:
    """Match Manim's logical frame to the requested output pixel aspect ratio."""
    try:
        width = float(os.environ.get("SKETCH2MOTION_WIDTH", config.pixel_width))
        height = float(os.environ.get("SKETCH2MOTION_HEIGHT", config.pixel_height))
        if width > 0 and height > 0:
            config.frame_height = 8.0
            config.frame_width = config.frame_height * width / height
    except (TypeError, ValueError, ZeroDivisionError):
        pass


_configure_frame_aspect()


class DrawSVGColor(Scene):
    def construct(self):
        self.add(
            FullScreenRectangle(
                fill_color=_background_color(svg_file),
                fill_opacity=1,
                stroke_opacity=0,
            )
        )

        foreground_svg, temporary_file = _foreground_svg(svg_file)
        try:
            paths = SVGMobject(foreground_svg)
        finally:
            if temporary_file is not None:
                temporary_file.unlink(missing_ok=True)

        paths.scale(scale)
        paths.move_to(ORIGIN)
        target_colors = [subpath.get_fill_color() for subpath in paths]
        for subpath, color in zip(paths, target_colors):
            subpath.set_fill(color, opacity=0).set_stroke(opacity=0)

        if target_colors:
            self.play(
                LaggedStart(
                    *[
                        subpath.animate.set_fill(color, opacity=1)
                        for subpath, color in zip(paths, target_colors)
                    ],
                    lag_ratio=delay,
                    run_time=duration,
                    rate_func=draw_dict.get(draw_type, smooth),
                )
            )
        self.wait(0.5)
