import io
import sys
import subprocess
from PIL import Image
from xml.etree import ElementTree as ET

if sys.platform == "win32":
    executable_path = "potrace.exe"
else:
    executable_path = "potrace"

NS = "http://www.w3.org/2000/svg"


def _trace_mask(mask: Image.Image) -> bytes:
    buf = io.BytesIO()
    mask.save(buf, format="BMP")
    proc = subprocess.run(
        [executable_path, "-s", "--group", "-o", "-"],
        input=buf.getvalue(),
        stdout=subprocess.PIPE,
        check=True,
    )
    return proc.stdout


def sketch2svg_color(img_path: str, output_path: str = "", num_colors: int = 8, min_coverage: float = 0.002):
    """
    Quantize the image into `num_colors` colors, trace each color layer with
    potrace, and merge all layers into a single colored SVG.
    """
    print(f"Processing image (color): {img_path}", file=sys.stderr)
    im = Image.open(img_path).convert("RGB")

    pal = im.quantize(colors=num_colors, method=Image.Quantize.MAXCOVERAGE, kmeans=3)
    palette = pal.getpalette()
    w, h = im.size
    total = w * h

    ET.register_namespace("", NS)
    root = None

    counts = {idx: cnt for cnt, idx in pal.getcolors(maxcolors=num_colors + 1)}
    order = sorted(counts, key=lambda i: counts[i], reverse=True)
    background_idx = order[0]  # most common color = canvas background

    for idx in order:
        if idx == background_idx:
            continue
        if counts[idx] / total < min_coverage:
            continue
        r, g, b = palette[idx * 3: idx * 3 + 3]
        mask = pal.point(lambda p, i=idx: 0 if p == i else 255, mode="L").convert("1")
        svg_bytes = _trace_mask(mask)
        layer_root = ET.fromstring(svg_bytes)
        color = f"#{r:02x}{g:02x}{b:02x}"
        if root is None:
            root = ET.Element(f"{{{NS}}}svg", dict(layer_root.attrib))
        for gel in layer_root:
            if gel.tag == f"{{{NS}}}g":
                gel.set("fill", color)
                gel.attrib.pop("stroke", None)
                root.append(gel)

    if root is None:
        raise RuntimeError("No traceable color layers found in image.")

    br, bg_, bb = palette[background_idx * 3: background_idx * 3 + 3]
    bg_color = f"#{br:02x}{bg_:02x}{bb:02x}"
    with open(output_path.rsplit(".", 1)[0] + ".bg" if output_path else img_path.rsplit(".", 1)[0] + "_color.bg", "w") as f:
        f.write(bg_color)

    if not output_path:
        output_path = img_path.rsplit(".", 1)[0] + "_color.svg"
    buf = io.BytesIO()
    ET.ElementTree(root).write(buf, encoding="utf-8", xml_declaration=True)
    with open(output_path, "wb") as f:
        f.write(buf.getvalue())

    print(f"Color SVG saved to: {output_path}", file=sys.stderr)
    return output_path, output_path


if __name__ == "__main__":
    sketch2svg_color(sys.argv[1], num_colors=int(sys.argv[2]) if len(sys.argv) > 2 else 8)
