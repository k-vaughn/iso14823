#!/usr/bin/env python3
"""Generate the sign, category, and find pages from ``data/registry.json``."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

from drafts import draft_state
from graphics import sign_graphics
from pages import render_category, render_find, render_sign, search_document, update_counts

ROOT = Path(__file__).resolve().parents[1]
INDEX_PATH = ROOT / "docs" / "index.md"


def publish_graphics() -> None:
    """Copy ``graphics/`` into ``docs/graphics`` so Zensical can publish it.

    Zensical does not follow a symlink that points outside ``docs/``. The copy
    is gitignored; ``graphics/`` stays the source of truth.
    """
    source = ROOT / "graphics"
    dest = ROOT / "docs" / "graphics"
    if dest.is_symlink() or dest.is_file():
        dest.unlink()
    elif dest.exists():
        shutil.rmtree(dest)
    if not source.is_dir():
        dest.mkdir(parents=True)
        return
    shutil.copytree(
        source,
        dest,
        ignore=shutil.ignore_patterns(".gitkeep", "README.md", ".DS_Store"),
    )


def generated_files(document: dict) -> dict[Path, str]:
    signs = document["signs"]
    state = draft_state(ROOT, signs)
    known_ids = {sign["id"] for sign in signs}
    graphics = {sign["id"]: sign_graphics(ROOT, sign["id"]) for sign in signs}
    files: dict[Path, str] = {}
    for sign in signs:
        files[Path("docs/signs") / f"{sign['id']}.md"] = render_sign(
            sign,
            draft=sign["id"] in state.ids,
            draft_mode=state.mode,
            baseline_version=state.baseline_version,
            files_by_country=graphics[sign["id"]],
            root=ROOT,
            known_ids=known_ids,
        )
    by_service: dict[str, list[dict]] = {}
    for sign in signs:
        by_service.setdefault(sign["service_category"], []).append(sign)
    for service in document["service_categories"]:
        files[Path("docs/categories") / f"{service['code']}.md"] = render_category(
            service,
            by_service.get(service["code"], []),
            set(state.ids),
            state.mode,
        )
    payload = search_document(document, set(state.ids), graphics)
    files[Path("docs/find.md")] = render_find(payload, state.mode)
    if INDEX_PATH.is_file():
        files[Path("docs/index.md")] = update_counts(
            INDEX_PATH.read_text(encoding="utf-8"), signs
        )
    return files


def _tracked_generated(root: Path) -> set[Path]:
    found: set[Path] = set()
    for folder in (root / "docs" / "signs", root / "docs" / "categories"):
        if folder.is_dir():
            found.update(path.relative_to(root) for path in folder.glob("*.md"))
    find_page = root / "docs" / "find.md"
    if find_page.is_file():
        found.add(find_page.relative_to(root))
    index = root / "docs" / "index.md"
    if index.is_file():
        found.add(index.relative_to(root))
    return found


def main(argv: list[str] | None = None) -> int:
    check = "--check" in (argv if argv is not None else sys.argv[1:])
    registry_path = ROOT / "data" / "registry.json"
    if not registry_path.is_file():
        print("data/registry.json is missing. Run python3 scripts/import_annex.py", file=sys.stderr)
        return 1
    document = json.loads(registry_path.read_text(encoding="utf-8"))
    files = generated_files(document)
    if Path("docs/index.md") not in files:
        print("docs/index.md is missing", file=sys.stderr)
        return 1
    if check:
        mismatches: list[str] = []
        for relative, text in files.items():
            path = ROOT / relative
            current = path.read_text(encoding="utf-8") if path.is_file() else None
            if current != text:
                mismatches.append(str(relative))
        extras = sorted(str(path) for path in _tracked_generated(ROOT) - set(files))
        if mismatches or extras:
            print("Generated pages are out of date. Run python3 scripts/build_pages.py", file=sys.stderr)
            for item in mismatches[:30]:
                print(f"  differs: {item}", file=sys.stderr)
            for item in extras[:30]:
                print(f"  extra: {item}", file=sys.stderr)
            return 1
        print(f"OK: {len(files)} pages match data/registry.json")
        return 0

    publish_graphics()
    for relative, text in files.items():
        path = ROOT / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    expected = set(files)
    for relative in _tracked_generated(ROOT) - expected:
        (ROOT / relative).unlink()
    print(f"Wrote {len(files)} pages")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
