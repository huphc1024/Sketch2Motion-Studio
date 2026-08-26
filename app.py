import os
import sys
import asyncio
import subprocess
from fractions import Fraction
from pathlib import Path
from typing import Optional

import gradio as gr
from locales import (
    ENGLISH,
    LANGUAGE_CHOICES,
    drawing_style_choices,
    get_ui_text,
    normalize_drawing_style,
    normalize_video_format,
    video_format_choices,
)
from sketch2svg import sketch2svg  # must return (sketch_preview_path, svg_path)
from sketch2svg_color import sketch2svg_color


# ----- Video format options -----
LANDSCAPE_FORMAT = "landscape"
PORTRAIT_FORMAT = "portrait"
VIDEO_FORMATS = {
    LANDSCAPE_FORMAT: (1920, 1080),
    PORTRAIT_FORMAT: (1080, 1920),
}
LEGACY_VIDEO_FORMATS = {
    "Landscape 16:9 (1920x1080)": LANDSCAPE_FORMAT,
    "Portrait 9:16 (1080x1920)": PORTRAIT_FORMAT,
}
DEFAULT_VIDEO_FORMAT = LANDSCAPE_FORMAT


# ----- Async/subprocess compatibility on Windows -----
if sys.platform == "win32":
    # Use selector loop for asyncio + subprocess compatibility on Windows
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


# ----- Utilities -----
def _check_cmd_available(cmd: str, ver:str) -> None:
    """Ensure an external command (e.g., ffmpeg, manim) is available."""
    try:
        subprocess.run([cmd, f"{ver}"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    except Exception as e:
        raise RuntimeError(f"Required command not available: {cmd!r}. Error: {e}") from e


def _check_manim_available() -> None:
    """Ensure Manim is installed in the Python environment running the app."""
    try:
        subprocess.run(
            [sys.executable, "-m", "manim", "--version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
    except Exception as e:
        raise RuntimeError(f"Manim is not available: {e}") from e



def _run(
    cmd: list[str],
    cwd: Optional[Path] = None,
    env: Optional[dict[str, str]] = None,
) -> None:
    """Run a subprocess command with unified error handling."""
    try:
        subprocess.run(cmd, check=True, cwd=str(cwd) if cwd else None, env=env)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\nExit code: {e.returncode}") from e


def _video_frame_rate(video_path: Path) -> Fraction:
    """Return the video's average frame rate as an FFmpeg-compatible fraction."""
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=avg_frame_rate",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(video_path),
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        frame_rate = Fraction(result.stdout.strip())
    except (subprocess.CalledProcessError, ValueError, ZeroDivisionError) as e:
        raise RuntimeError(f"Could not determine frame rate for {video_path}") from e

    if frame_rate <= 0:
        raise RuntimeError(f"Video has no usable frame rate: {video_path}")
    return frame_rate


def _video_resolution(video_format: str) -> tuple[int, int]:
    """Resolve a UI format label to the width and height passed to Manim."""
    video_format = normalize_video_format(video_format)
    video_format = LEGACY_VIDEO_FORMATS.get(video_format, video_format)
    try:
        return VIDEO_FORMATS[video_format]
    except (KeyError, TypeError) as e:
        valid_formats = ", ".join(VIDEO_FORMATS)
        raise ValueError(
            f"Unsupported video format {video_format!r}; choose one of: {valid_formats}"
        ) from e


# ----- Video processing -----
def prepend_last_frame(input_video: str, output_video: str, freeze_sec: float = 1.0) -> None:
    """
    Prepend the last frame of a video as a short still segment.
    Args:
        input_video: path to input video.
        output_video: path to final output video.
        freeze_sec: duration (seconds) of the prepended still segment.
    """
    _check_cmd_available("ffmpeg", "-version")
    _check_cmd_available("ffprobe", "-version")

    in_path = Path(input_video)
    out_path = Path(output_video)
    base = in_path.with_suffix("")
    frame_rate = _video_frame_rate(in_path)
    frame_rate_arg = str(frame_rate)

    last_frame_img = base.parent / f"{base.name}_last_frame.png"

    try:
        # Reverse a short tail so the first output frame is the actual final frame.
        tail_sec = max(0.1, 2 / float(frame_rate))
        _run([
            "ffmpeg", "-y", "-sseof", f"-{tail_sec:.6f}", "-i", str(in_path),
            "-vf", "reverse", "-vframes", "1", "-update", "1", str(last_frame_img)
        ])

        # Render both segments at the source frame rate. Stream-copying a default
        # 25 fps still with a 60 fps Manim video produces invalid timing metadata.
        _run([
            "ffmpeg", "-y",
            "-loop", "1", "-framerate", frame_rate_arg,
            "-t", f"{freeze_sec}", "-i", str(last_frame_img),
            "-i", str(in_path),
            "-filter_complex",
            (
                "[0:v]scale=trunc(iw/2)*2:trunc(ih/2)*2,setsar=1,"
                "setpts=PTS-STARTPTS[still];"
                "[1:v]scale=trunc(iw/2)*2:trunc(ih/2)*2,setsar=1,"
                "setpts=PTS-STARTPTS[source];"
                "[still][source]concat=n=2:v=1:a=0[video]"
            ),
            "-map", "[video]", "-r", frame_rate_arg,
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-movflags", "+faststart", str(out_path)
        ])
    finally:
        # Best-effort cleanup for temporary artifacts
        for f in (last_frame_img,):
            try:
                if f.exists():
                    f.unlink()
            except Exception:
                pass


def convert_svg_to_mp4(
    svg_path: str,
    manim_dur: float = 10.0,
    manim_delay: float = 0.1,
    manim_scale: float = 2.0,
    manim_draw: str = "smooth",
    color_mode: bool = False,
    video_format: str = DEFAULT_VIDEO_FORMAT,
) -> Optional[str]:
    """
    Render an SVG into an animated MP4 using Manim, then prepend the last frame for a short still.
    ``video_format`` selects the output pixel dimensions. Returns the final video path, or None
    on failure.
    """
    if not svg_path:
        print("No SVG path provided.", file=sys.stderr)
        return None

    video_width, video_height = _video_resolution(video_format)
    _check_manim_available()
    _check_cmd_available("ffmpeg", "-version")

    svg_p = Path(svg_path)
    if not svg_p.exists():
        print(f"SVG not found: {svg_p}", file=sys.stderr)
        return None

    media_dir = Path("media")
    manim_scene_file = Path(__file__).with_name("svg2mp4.py")
    scene_class = "DrawSVG"
    render_env = os.environ.copy()
    render_env.update(
        {
            "SKETCH2MOTION_WIDTH": str(video_width),
            "SKETCH2MOTION_HEIGHT": str(video_height),
        }
    )
    if color_mode:
        manim_scene_file = Path(__file__).with_name("svg2mp4_color.py")
        scene_class = "DrawSVGColor"
        render_env.update(
            {
                "SKETCH2MOTION_SVG": str(svg_p),
                "SKETCH2MOTION_DURATION": str(manim_dur),
                "SKETCH2MOTION_DELAY": str(manim_delay),
                "SKETCH2MOTION_SCALE": str(manim_scale),
                "SKETCH2MOTION_DRAW": manim_draw,
            }
        )

    filename = svg_p.stem
    cmd = [
        sys.executable,
        "-m",
        "manim",
        "-qh",  # fast rendering; consider -ql for even faster development quality
        "--disable_caching",
        "--media_dir", str(media_dir),
        "--output_file", filename,
        "--resolution", f"{video_width},{video_height}",
        str(manim_scene_file),
        scene_class,
    ]
    if not color_mode:
        cmd.extend(
            [
                str(svg_p),
                f"{manim_dur}",
                f"{manim_delay}",
                f"{manim_scale}",
                f"{manim_draw}",
            ]
        )

    try:
        _run(cmd, env=render_env)

        # Locate the video created by this render. The resolution directory changes
        # with the selected format, and an older landscape file may have the same name.
        candidates = list((media_dir / "videos").rglob(f"{filename}.mp4"))
        if not candidates:
            print("Rendered video not found under media/videos/*", file=sys.stderr)
            return None
        video_path = max(candidates, key=lambda candidate: candidate.stat().st_mtime)

        out_path = video_path.with_name(f"{video_path.stem}-final.mp4")
        prepend_last_frame(str(video_path), str(out_path), freeze_sec=1.0)
        print(f"[OK] Video created: {out_path}", file=sys.stderr)
        return str(out_path)
    except Exception as e:
        print(f"Error during conversion: {e}", file=sys.stderr)
        return None


# ----- Gradio UI -----
with gr.Blocks(title="Sketch to Motion | 涂鸦转动画") as demo:
    language_selector = gr.Dropdown(
        choices=LANGUAGE_CHOICES,
        value=ENGLISH,
        label="Language / 语言",
        interactive=True,
    )
    heading = gr.Markdown(get_ui_text(ENGLISH)["heading"])

    with gr.Accordion(get_ui_text(ENGLISH)["parameters"], open=True) as parameters:
        with gr.Row():
            manim_dur = gr.Slider(
                minimum=0.5, maximum=20.0, step=0.5, value=10.0,
                label=get_ui_text(ENGLISH)["duration"], interactive=True
            )
            manim_delay = gr.Slider(
                minimum=0.05, maximum=1.0, step=0.05, value=0.1,
                label=get_ui_text(ENGLISH)["delay"], interactive=True
            )
            manim_scale = gr.Slider(
                minimum=0.1, maximum=5.0, step=0.1, value=2.0,
                label=get_ui_text(ENGLISH)["scale"], interactive=True
            )
            manim_drawtype = gr.Dropdown(
                choices=drawing_style_choices(ENGLISH),
                value="smooth",
                label=get_ui_text(ENGLISH)["drawing_style"],
                interactive=True
            )
        with gr.Row():
            color_mode = gr.Checkbox(
                label=get_ui_text(ENGLISH)["preserve_colors"],
                value=False,
                interactive=True,
            )
            color_count = gr.Slider(
                minimum=2,
                maximum=16,
                step=1,
                value=8,
                label=get_ui_text(ENGLISH)["palette_size"],
                interactive=True,
            )
            video_format = gr.Dropdown(
                choices=video_format_choices(ENGLISH),
                value=DEFAULT_VIDEO_FORMAT,
                label=get_ui_text(ENGLISH)["video_format"],
                interactive=True,
            )

    with gr.Row():
        input_img = gr.Image(label=get_ui_text(ENGLISH)["input_image"], type="filepath")
        sketch_preview = gr.Image(label=get_ui_text(ENGLISH)["sketch_preview"], type="filepath")
        video_preview = gr.Video(label=get_ui_text(ENGLISH)["video_preview"], autoplay=True)

    with gr.Row():
        btn_sketch = gr.Button(get_ui_text(ENGLISH)["generate_sketch"])
        btn_video = gr.Button(get_ui_text(ENGLISH)["generate_video"])
        useless = gr.Button("(╯°□°）╯︵ ┻━┻")  # Just for fun, no functionality


    svg_path_state = gr.State(value="")
    color_mode_state = gr.State(value=False)

    def _generate_sketch(image_path, preserve_colors, colors):
        if preserve_colors:
            preview_path, svg_path = sketch2svg_color(image_path, num_colors=int(colors))
        else:
            preview_path, svg_path = sketch2svg(image_path)
        return preview_path, svg_path, preserve_colors

    btn_sketch.click(
        fn=_generate_sketch,
        inputs=[input_img, color_mode, color_count],
        outputs=[sketch_preview, svg_path_state, color_mode_state],
    )

    def _guard_convert(
        svg_path,
        preserve_colors,
        dur,
        delay,
        scale,
        drawtype,
        output_format=DEFAULT_VIDEO_FORMAT,
    ):
        """Guard against empty SVG path before conversion."""
        if not svg_path:
            return None
        return convert_svg_to_mp4(
            svg_path,
            dur,
            delay,
            scale,
            normalize_drawing_style(drawtype),
            preserve_colors,
            normalize_video_format(output_format),
        )

    btn_video.click(
        fn=_guard_convert,
        inputs=[
            svg_path_state,
            color_mode_state,
            manim_dur,
            manim_delay,
            manim_scale,
            manim_drawtype,
            video_format,
        ],
        outputs=video_preview
    )

    def _update_interface(language: str, drawtype: str, output_format: str):
        """Update labels and choices without changing the current workflow state."""
        text = get_ui_text(language)
        return (
            gr.update(value=text["heading"]),
            gr.update(label=text["parameters"]),
            gr.update(label=text["duration"]),
            gr.update(label=text["delay"]),
            gr.update(label=text["scale"]),
            gr.update(
                choices=drawing_style_choices(language),
                value=drawtype,
                label=text["drawing_style"],
            ),
            gr.update(label=text["preserve_colors"]),
            gr.update(label=text["palette_size"]),
            gr.update(
                choices=video_format_choices(language),
                value=output_format,
                label=text["video_format"],
            ),
            gr.update(label=text["input_image"]),
            gr.update(label=text["sketch_preview"]),
            gr.update(label=text["video_preview"]),
            gr.update(value=text["generate_sketch"]),
            gr.update(value=text["generate_video"]),
        )

    language_selector.change(
        fn=_update_interface,
        inputs=[language_selector, manim_drawtype, video_format],
        outputs=[
            heading,
            parameters,
            manim_dur,
            manim_delay,
            manim_scale,
            manim_drawtype,
            color_mode,
            color_count,
            video_format,
            input_img,
            sketch_preview,
            video_preview,
            btn_sketch,
            btn_video,
        ],
    )

# Consider configuring the port via environment variable in production
demo.launch(server_port=7880)
