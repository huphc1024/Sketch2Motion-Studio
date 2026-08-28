import os
import sys

from manim import BLACK, ORIGIN, WHITE, FullScreenRectangle, LaggedStart, SVGMobject
from manim import Scene, config, linear, smooth, there_and_back, wiggle


def _float_arg(value: str | None, default: float) -> float:
    try:
        return float(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def _scene_arguments() -> tuple[str, float, float, float, str, float]:
    args = sys.argv[1:]
    legacy = args[-5:] if len(args) >= 5 and args[-5].lower().endswith(".svg") else []
    svg_path = os.getenv("SKETCH2MOTION_SVG") or (legacy[0] if legacy else "sketch.svg")
    duration = _float_arg(os.getenv("SKETCH2MOTION_DURATION") or (legacy[1] if legacy else None), 10.0)
    delay = _float_arg(os.getenv("SKETCH2MOTION_DELAY") or (legacy[2] if legacy else None), 0.1)
    scale = _float_arg(os.getenv("SKETCH2MOTION_SCALE") or (legacy[3] if legacy else None), 2.0)
    draw = os.getenv("SKETCH2MOTION_DRAW") or (legacy[4] if legacy else "smooth")
    hold = max(0.0, _float_arg(os.getenv("SKETCH2MOTION_HOLD"), 0.5))
    return svg_path, max(0.05, duration), max(0.0, delay), max(0.1, scale), draw, hold


svg_file, duration, delay, scale, draw_type, hold_duration = _scene_arguments()

# Define the drawing functions
draw_dict = {
    "linear": linear,
    "smooth": smooth,
    "there_and_back": there_and_back,
    "wiggle": wiggle}

config.background_color = BLACK  # we’ll cover it anyway


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

class DrawSVG(Scene):
    def construct(self):
        bg = FullScreenRectangle(
                fill_color=WHITE, fill_opacity=1, stroke_opacity=0
        )
        self.add(bg)

        paths = SVGMobject(svg_file)
        paths.set_fill(BLACK, opacity=1).set_stroke(opacity=0)

        # calculate the bounding box of the SVG object, and move it to the center
        paths.scale(scale)
        paths.move_to(ORIGIN)

        # set all subpaths to transparent
        for subpath in paths:
            subpath.set_fill(BLACK, opacity=0)

        #paths= sorted(paths, key=lambda p: p.get_width()*p.get_height())
        animations = [subpath.animate.set_fill(BLACK, 1) for subpath in paths]

        # draw the SVG object
        self.play(
            LaggedStart(
                *animations,
                lag_ratio=delay, 
                run_time=duration,
                rate_func= draw_dict.get(draw_type, smooth)
            )
        )
        if hold_duration:
            self.wait(hold_duration)

# manim -pql svg2mp4.py DrawSVG

