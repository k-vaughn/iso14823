"""Locate country graphics for a pictogram code.

Canonical layout, at the repository root::

    graphics/<country>/<service>-<pictogram>.png

``de/12-112.png`` is the German rendering of pictogram code 12-112.
The page displays PNG, SVG, or WebP. An EMF with the same stem is an
optional original and is linked beside the image.
"""

from __future__ import annotations

import re
from pathlib import Path

WEB_SUFFIXES = {".svg", ".png", ".webp", ".jpg", ".jpeg", ".gif"}
MASTER_SUFFIXES = {".emf", ".wmf"}
KNOWN_SUFFIXES = WEB_SUFFIXES | MASTER_SUFFIXES
GRAPHIC_RE = re.compile(
    r"([A-Za-z]{2})/(\d{2}-\d{3})\.(emf|wmf|svg|png|webp|jpg|jpeg|gif)\Z",
    re.IGNORECASE,
)


def graphics_root(root: Path) -> Path:
    return root / "graphics"


def sign_graphics(root: Path, sign_id: str) -> dict[str, list[Path]]:
    """Return country code -> files for a three-digit pictogram such as ``12-112``."""
    if not re.fullmatch(r"\d{2}-\d{3}", sign_id):
        return {}
    base = graphics_root(root)
    if not base.is_dir():
        return {}
    found: dict[str, list[Path]] = {}
    stem = sign_id.lower()
    for folder in base.iterdir():
        if not folder.is_dir():
            continue
        code = folder.name.lower()
        if not re.fullmatch(r"[a-z]{2}", code):
            continue
        matches = [
            path
            for path in folder.iterdir()
            if path.is_file()
            and path.stem.lower() == stem
            and path.suffix.lower() in KNOWN_SUFFIXES
        ]
        if matches:
            found[code] = sorted(matches, key=lambda path: (path.suffix.lower(), path.name.lower()))
    return found


def relative_graphic(root: Path, path: Path) -> str:
    """Path from ``docs/signs/`` to a file under ``graphics/`` (``../graphics/...``)."""
    relative = path.resolve().relative_to(graphics_root(root).resolve())
    return "../graphics/" + relative.as_posix()


def web_files(paths: list[Path]) -> list[Path]:
    return [path for path in paths if path.suffix.lower() in WEB_SUFFIXES]


def master_files(paths: list[Path]) -> list[Path]:
    return [path for path in paths if path.suffix.lower() in MASTER_SUFFIXES]
