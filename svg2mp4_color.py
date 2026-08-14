from manim import LaggedStart, SVGMobject, FullScreenRectangle
from manim import Scene, config, WHITE, BLACK, ORIGIN
from manim import linear, smooth, there_and_back, wiggle
import sys

svg_file = sys.argv[-5] if sys.argv[-5].endswith(".svg") else "sketch.svg"
duration = float(sys.argv[-4]) if sys.argv[-4].replace('.', '', 1).isdigit() else 10.0
delay = float(sys.argv[-3]) if sys.argv[-3].replace('.', '', 1).isdigit() else 0.1
scale = float(sys.argv[-2]) if sys.argv[-2].replace('.', '', 1).isdigit() else 2.0
draw_type = sys.argv[-1] if sys.argv[-1] in ["linear", "smooth", "there_and_back", "wiggle"] else "smooth"

draw_dict = {
    "linear": linear,
    "smooth": smooth,
    "there_and_back": there_and_back,
    "wiggle": wiggle}

config.background_color = BLACK

import os
bg_file = svg_file.rsplit(".", 1)[0] + ".bg"
bg_color = open(bg_file).read().strip() if os.path.exists(bg_file) else WHITE

class DrawSVGColor(Scene):
    def construct(self):
        bg = FullScreenRectangle(
                fill_color=bg_color, fill_opacity=1, stroke_opacity=0
        )
        self.add(bg)

        paths = SVGMobject(svg_file)
        paths.scale(scale)
        paths.move_to(ORIGIN)

        targets = []
        for subpath in paths:
            color = subpath.get_fill_color()
            targets.append(color)
            subpath.set_fill(color, opacity=0).set_stroke(opacity=0)

        animations = [
            subpath.animate.set_fill(color, 1)
            for subpath, color in zip(paths, targets)
        ]

        self.play(
            LaggedStart(
                *animations,
                lag_ratio=delay,
                run_time=duration,
                rate_func=draw_dict.get(draw_type, smooth)
            )
        )
        self.wait(0.5)
