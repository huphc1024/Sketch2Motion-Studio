import os

from manim import LaggedStart, SVGMobject, FullScreenRectangle
from manim import Scene, config, WHITE, BLACK, ORIGIN
from manim import linear, smooth, there_and_back, wiggle
import sys

svg_file = sys.argv[-5] if sys.argv[-5].endswith(".svg") else "sketch.svg"
duration = float(sys.argv[-4]) if sys.argv[-4].replace('.', '', 1).isdigit() else 10.0
delay = float(sys.argv[-3]) if sys.argv[-3].replace('.', '', 1).isdigit() else 0.1
scale = float(sys.argv[-2]) if sys.argv[-2].replace('.', '', 1).isdigit() else 2.0
draw_type = sys.argv[-1] if sys.argv[-1] in ["linear", "smooth", "there_and_back", "wiggle"] else "smooth"

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
        self.wait(1)

# manim -pql svg2mp4.py DrawSVG

