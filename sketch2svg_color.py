import io
import subprocess
import sys
from collections import Counter
from pathlib import Path
from xml.etree import ElementTree as ET

from PIL import Image

from services.tooling import resolve_potrace

SVG_NS = "http://www.w3.org/2000/svg"
BACKGROUND_LAYER_ID = "sketch2motion-background"


def _trace_mask(mask: Image.Image) -> bytes:
    buffer = io.BytesIO()
    mask.save(buffer, format="BMP")
    result = subprocess.run(
        [resolve_potrace(), "-s", "--group", "-o", "-"],
        input=buffer.getvalue(),
        stdout=subprocess.PIPE,
        check=True,
    )
    return result.stdout


def _load_rgb_image(img_path: str) -> Image.Image:
    with Image.open(img_path) as source:
        if source.mode in {"RGBA", "LA"} or "transparency" in source.info:
            # Transparent drawing canvases should not become black after alpha is dropped.
            rgba = source.convert("RGBA")
            canvas = Image.new("RGBA", rgba.size, "white")
            return Image.alpha_composite(canvas, rgba).convert("RGB")
        return source.convert("RGB")


def _background_index(palette_image: Image.Image) -> int:
    width, height = palette_image.size
    corners = (
        (0, 0),
        (width - 1, 0),
        (0, height - 1),
        (width - 1, height - 1),
    )
    return Counter(palette_image.getpixel(point) for point in corners).most_common(1)[0][0]


def _color_hex(palette: list[int], index: int) -> str:
    red, green, blue = palette[index * 3 : index * 3 + 3]
    return f"#{red:02x}{green:02x}{blue:02x}"


def _output_path(img_path: str, output_path: str) -> Path:
    if output_path:
        path = Path(output_path)
        return path if path.suffix.lower() == ".svg" else path.with_suffix(".svg")
    source = Path(img_path)
    return source.with_name(f"{source.stem}_color.svg")


def sketch2svg_color(
    img_path: str,
    output_path: str = "",
    num_colors: int = 8,
    min_coverage: float = 0.0,
):
    """Convert an image into a self-contained, layered color SVG.

    The background is embedded as an SVG rectangle and metadata. All remaining
    quantized colors are traced, so selecting a background color never removes
    a dominant foreground object from the final image.
    """
    if not 1 <= num_colors <= 256:
        raise ValueError("num_colors must be between 1 and 256")
    if not 0 <= min_coverage < 1:
        raise ValueError("min_coverage must be in the range [0, 1)")

    print(f"Processing image (color): {img_path}", file=sys.stderr)
    image = _load_rgb_image(img_path)
    palette_image = image.quantize(
        colors=num_colors,
        method=Image.Quantize.MAXCOVERAGE,
        kmeans=3,
    )
    palette = palette_image.getpalette()
    width, height = image.size
    total_pixels = width * height
    counts = {
        index: count
        for count, index in palette_image.getcolors(maxcolors=256)
    }
    order = sorted(counts, key=lambda index: counts[index], reverse=True)
    background_idx = _background_index(palette_image)
    background_color = _color_hex(palette, background_idx)

    ET.register_namespace("", SVG_NS)
    root = ET.Element(
        f"{{{SVG_NS}}}svg",
        {
            "version": "1.1",
            "width": f"{width}pt",
            "height": f"{height}pt",
            "viewBox": f"0 0 {width} {height}",
            "data-background-color": background_color,
        },
    )
    ET.SubElement(
        root,
        f"{{{SVG_NS}}}rect",
        {
            "id": BACKGROUND_LAYER_ID,
            "x": "0",
            "y": "0",
            "width": str(width),
            "height": str(height),
            "fill": background_color,
        },
    )

    for index in order:
        if index == background_idx or counts[index] / total_pixels < min_coverage:
            continue

        mask = palette_image.point(
            lambda pixel, color_index=index: 0 if pixel == color_index else 255,
            mode="L",
        ).convert("1")
        traced_root = ET.fromstring(_trace_mask(mask))
        color = _color_hex(palette, index)
        for group in traced_root:
            if group.tag == f"{{{SVG_NS}}}g":
                group.set("fill", color)
                group.attrib.pop("stroke", None)
                root.append(group)

    output = _output_path(img_path, output_path)
    ET.ElementTree(root).write(output, encoding="utf-8", xml_declaration=True)
    print(f"Color SVG saved to: {output}", file=sys.stderr)
    return str(output), str(output)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("Usage: python sketch2svg_color.py INPUT_IMAGE [NUM_COLORS]")
    sketch2svg_color(
        sys.argv[1],
        num_colors=int(sys.argv[2]) if len(sys.argv) > 2 else 8,
    )
