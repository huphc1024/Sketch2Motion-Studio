import argparse
import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Render a color SVG drawing animation.")
    parser.add_argument("svg", type=Path, help="Color SVG created by sketch2svg_color.py")
    parser.add_argument("--duration", type=float, default=5.0)
    parser.add_argument("--delay", type=float, default=0.05)
    parser.add_argument("--scale", type=float, default=3.55)
    parser.add_argument(
        "--draw",
        choices=["linear", "smooth", "there_and_back", "wiggle"],
        default="smooth",
    )
    parser.add_argument("--quality", choices=["l", "m", "h", "p", "k"], default="h")
    parser.add_argument("--output-file", default=None)
    args = parser.parse_args()

    if not args.svg.is_file():
        parser.error(f"SVG file not found: {args.svg}")

    env = os.environ.copy()
    env.update(
        {
            "SKETCH2MOTION_SVG": str(args.svg),
            "SKETCH2MOTION_DURATION": str(args.duration),
            "SKETCH2MOTION_DELAY": str(args.delay),
            "SKETCH2MOTION_SCALE": str(args.scale),
            "SKETCH2MOTION_DRAW": args.draw,
        }
    )
    scene_file = Path(__file__).with_name("svg2mp4_color.py")
    output_file = args.output_file or args.svg.stem
    command = [
        sys.executable,
        "-m",
        "manim",
        f"-q{args.quality}",
        "--disable_caching",
        "--output_file",
        output_file,
        str(scene_file),
        "DrawSVGColor",
    ]
    return subprocess.run(command, env=env, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
