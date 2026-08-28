"""Multi-scene Manim + FFmpeg rendering pipeline."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any, Callable

from models.project import Scene, VideoSettings, migrate_project
from sketch2svg import sketch2svg
from sketch2svg_color import sketch2svg_color


ROOT = Path(__file__).resolve().parent.parent
GENERATED = ROOT / "generated"


class RenderError(RuntimeError):
    pass


def ensure_scene_svg(project_id: str, scene: Scene) -> str:
    if scene.svg_path and Path(scene.svg_path).is_file():
        return scene.svg_path
    if not scene.image or not Path(scene.image).is_file():
        raise RenderError(f"{scene.name} has no valid image.")
    asset_dir = GENERATED / "projects" / project_id / "assets"
    asset_dir.mkdir(parents=True, exist_ok=True)
    output = asset_dir / f"{scene.id}{'_color' if scene.preserve_colors else ''}.svg"
    if scene.preserve_colors:
        _, svg_path = sketch2svg_color(scene.image, str(output), num_colors=scene.color_count)
    else:
        _, svg_path = sketch2svg(scene.image, str(output))
    return str(Path(svg_path).resolve())


def render_scene_animation(project_id: str, scene: Scene, settings: VideoSettings, *, quality: str = "l") -> str:
    svg_path = ensure_scene_svg(project_id, scene)
    width, height = settings.dimensions
    render_dir = GENERATED / "renders" / project_id / scene.id
    media_dir = render_dir / "manim"
    render_dir.mkdir(parents=True, exist_ok=True)
    scene_file = ROOT / ("svg2mp4_color.py" if scene.preserve_colors else "svg2mp4.py")
    scene_class = "DrawSVGColor" if scene.preserve_colors else "DrawSVG"
    output_name = f"animation-{width}x{height}-{settings.fps}"
    env = os.environ.copy()
    env.update({
        "SKETCH2MOTION_SVG": svg_path,
        "SKETCH2MOTION_DURATION": str(max(0.5, scene.duration - scene.transition.duration)),
        "SKETCH2MOTION_DELAY": str(scene.animation_delay),
        "SKETCH2MOTION_SCALE": str(scene.animation_scale),
        "SKETCH2MOTION_DRAW": scene.animation_preset,
        "SKETCH2MOTION_HOLD": "0.1",
        "SKETCH2MOTION_WIDTH": str(width),
        "SKETCH2MOTION_HEIGHT": str(height),
    })
    command = [
        os.sys.executable, "-m", "manim", f"-q{quality}", "--disable_caching",
        "--media_dir", str(media_dir), "--output_file", output_name,
        "--resolution", f"{width},{height}", "--frame_rate", str(settings.fps),
        str(scene_file), scene_class,
    ]
    _run(command, env=env, label=f"render {scene.name}")
    candidates = list((media_dir / "videos").rglob(f"{output_name}.mp4"))
    if not candidates:
        raise RenderError(f"Manim did not produce a video for {scene.name}.")
    return str(max(candidates, key=lambda path: path.stat().st_mtime).resolve())


def compose_scene_video(project_id: str, scene: Scene, settings: VideoSettings, *, volume: int = 100, quality: str = "l") -> str:
    raw_video = render_scene_animation(project_id, scene, settings, quality=quality)
    width, height = settings.dimensions
    duration = max(0.5, scene.duration)
    transition = min(scene.transition.duration, max(0.0, duration - 0.1))
    output_dir = GENERATED / "renders" / project_id / scene.id
    output = output_dir / f"scene-{width}x{height}-{settings.fps}.mp4"

    video_filters = [
        f"fps={settings.fps}",
        f"scale={width}:{height}:force_original_aspect_ratio=decrease",
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=white",
        f"tpad=stop_mode=clone:stop_duration={duration:.6f}",
        f"trim=duration={duration:.6f}",
        "setpts=PTS-STARTPTS",
    ]
    if transition > 0 and scene.transition.type != "none":
        video_filters.append(f"fade=t=out:st={duration - transition:.6f}:d={transition:.6f}:color=black")

    command = ["ffmpeg", "-y", "-i", raw_video]
    audio_filter: str
    if scene.audio_url and Path(scene.audio_url).is_file():
        command.extend(["-i", scene.audio_url])
        audio_filter = (
            f"[1:a]adelay=150|150,volume={max(0, min(100, volume)) / 100:.4f},"
            f"apad,atrim=duration={duration:.6f},asetpts=PTS-STARTPTS[a]"
        )
    else:
        command.extend(["-f", "lavfi", "-t", f"{duration:.6f}", "-i", "anullsrc=r=48000:cl=stereo"])
        audio_filter = f"[1:a]atrim=duration={duration:.6f},asetpts=PTS-STARTPTS[a]"
    filter_complex = f"[0:v]{','.join(video_filters)}[v];{audio_filter}"
    command.extend([
        "-filter_complex", filter_complex, "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
        "-r", str(settings.fps), "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-t", f"{duration:.6f}", "-movflags", "+faststart", str(output),
    ])
    _run(command, label=f"compose {scene.name}")
    return str(output.resolve())


def export_project(project: dict[str, Any], progress: Callable[[int, int, str], None] | None = None, *, quality: str = "l") -> str:
    model = migrate_project(project)
    settings = model.video_settings
    scene_videos: list[str] = []
    total = len(model.scenes)
    for index, scene in enumerate(model.scenes, start=1):
        if progress:
            progress(index - 1, total, f"Rendering {scene.name}")
        scene_videos.append(compose_scene_video(
            model.id, scene, settings, volume=model.voice_settings.volume, quality=quality
        ))

    export_dir = GENERATED / "exports" / model.id
    export_dir.mkdir(parents=True, exist_ok=True)
    concat_file = export_dir / "timeline.txt"
    lines = [f"file '{Path(path).as_posix().replace("'", "'\\''")}'" for path in scene_videos]
    concat_file.write_text("\n".join(lines), encoding="utf-8")
    output = export_dir / "final.mp4"
    if progress:
        progress(total, total, "Encoding final MP4")
    _run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(output),
    ], label="export project")
    return str(output.resolve())


def _run(command: list[str], *, env: dict[str, str] | None = None, label: str) -> None:
    try:
        subprocess.run(command, cwd=str(ROOT), env=env, check=True, capture_output=True, text=True)
    except FileNotFoundError as error:
        raise RenderError(f"Required command is missing while trying to {label}: {command[0]}") from error
    except subprocess.CalledProcessError as error:
        detail = (error.stderr or error.stdout or "").strip()[-2000:]
        raise RenderError(f"Failed to {label}: {detail}") from error
