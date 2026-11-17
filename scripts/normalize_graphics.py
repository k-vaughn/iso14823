"""Crop country PNGs that are a spreadsheet cell with a small sign inside.

China's extracts, and a few others, are a 794 by 1123 cell. The sign is
about 80 pixels in the middle. The sign card scales the whole file, so the
sign looks tiny next to a German file that is already cropped to the drawing.

Images that already fill their canvas are left unchanged.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.graphics import graphics_root  # noqa: E402

# A file is a cell extract when the drawing covers less than this fraction.
MAX_FILL = 0.5
WHITE = 248


def content_box(image, threshold: int = WHITE):
    rgba = image.convert("RGBA")
    width, height = rgba.size
    pixels = rgba.load()
    min_x, min_y, max_x, max_y = width, height, -1, -1
    for y in range(height):
        for x in range(width):
            red, green, blue, alpha = pixels[x, y]
            if alpha < 16:
                continue
            if red >= threshold and green >= threshold and blue >= threshold:
                continue
            if x < min_x:
                min_x = x
            if y < min_y:
                min_y = y
            if x > max_x:
                max_x = x
            if y > max_y:
                max_y = y
    if max_x < 0:
        return None
    return (min_x, min_y, max_x + 1, max_y + 1)


def normalize(path: Path, dry_run: bool) -> str | None:
    from PIL import Image

    with Image.open(path) as image:
        box = content_box(image)
        if box is None:
            return None
        width, height = image.size
        ink_w = box[2] - box[0]
        ink_h = box[3] - box[1]
        if ink_w * ink_h >= width * height * MAX_FILL:
            return None
        # Keep one pixel of the anti-aliased edge.
        left = max(0, box[0] - 1)
        top = max(0, box[1] - 1)
        right = min(width, box[2] + 1)
        bottom = min(height, box[3] + 1)
        cropped = image.crop((left, top, right, bottom))
        if not dry_run:
            if cropped.mode == "RGBA" and cropped.getchannel("A").getextrema() == (255, 255):
                cropped = cropped.convert("RGB")
            cropped.save(path, format="PNG", optimize=True)
    return f"{width}x{height} -> {right - left}x{bottom - top}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    root = graphics_root(ROOT)
    changed = 0
    for path in sorted(root.rglob("*.png")):
        result = normalize(path, args.dry_run)
        if result is None:
            continue
        changed += 1
        print(f"{path.relative_to(root).as_posix()} {result}")
    print(f"{changed} file(s)")


if __name__ == "__main__":
    main()
