"""Decide which sign pages differ from the last full registry release.

The comparison follows the ISO 24315 vocabulary site: a full release is a
``registry`` line in RELEASES whose SemVer has no pre-release label. Sign
pages whose register entry or country graphic differs from that release
receive the DRAFT watermark. With no full release yet, every sign page is
a draft, because the maintenance agency has not approved a baseline.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from annex import content_signature
from graphics import GRAPHIC_RE

ROOT = Path(__file__).resolve().parents[1]


def _versioning():
    scripts = Path(__file__).resolve().parent
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    import versioning

    return versioning


def _git(root: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True)


@dataclass(frozen=True)
class DraftState:
    ids: frozenset[str]
    mode: str  # "unreleased" or "diff"
    baseline_version: str | None = None
    baseline_rev: str | None = None


def approved_baseline(root: Path | None = None) -> tuple[str | None, str | None]:
    """Return ``(version, git revision)`` for the latest full registry release."""
    root = root or ROOT
    versioning = _versioning()
    version = versioning.latest_full_registry_version(
        versioning.parse_releases(root / "RELEASES")
    )
    if not version:
        return None, None
    tag = versioning.registry_tag(version)
    probe = _git(root, ["rev-parse", "--verify", "--quiet", f"{tag}^{{commit}}"])
    if probe.returncode == 0 and probe.stdout.strip():
        return version, probe.stdout.strip()

    history = _git(root, ["log", "--format=%H", "--", "RELEASES"])
    if history.returncode != 0:
        print("Could not read git history for RELEASES; treating every sign as draft.", file=sys.stderr)
        return version, None
    needle = None
    revisions = [line for line in history.stdout.splitlines() if line.strip()]
    for rev in reversed(revisions):
        show = _git(root, ["show", f"{rev}:RELEASES"])
        if show.returncode != 0:
            continue
        for line in show.stdout.splitlines():
            parts = line.split()
            if len(parts) == 3 and parts[0] == version and parts[2] == "registry":
                needle = rev
                break
        if needle:
            break
    if not needle:
        print(
            f"Full release {version} is not in git history; treating every sign as draft.",
            file=sys.stderr,
        )
    return version, needle


def _blob(root: Path, path: Path) -> str:
    result = _git(root, ["hash-object", str(path)])
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def graphic_index_from_tree(root: Path) -> dict[str, tuple[tuple[str, str, str], ...]]:
    index: dict[str, list[tuple[str, str, str]]] = {}
    base = root / "graphics"
    if not base.is_dir():
        return {}
    for path in base.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(base).as_posix()
        match = GRAPHIC_RE.fullmatch(relative)
        if not match:
            continue
        sign_id = match.group(2)
        blob = _blob(root, path)
        index.setdefault(sign_id, []).append((match.group(1).lower(), path.name, blob))
    return {sign_id: tuple(sorted(items)) for sign_id, items in index.items()}


def graphic_index_at_rev(root: Path, rev: str) -> dict[str, tuple[tuple[str, str, str], ...]]:
    listing = _git(root, ["ls-tree", "-r", rev, "graphics"])
    if listing.returncode != 0:
        return {}
    index: dict[str, list[tuple[str, str, str]]] = {}
    for line in listing.stdout.splitlines():
        # <mode> <type> <blob>\tgraphics/de/12-112.emf
        if "\t" not in line:
            continue
        meta, rel = line.split("\t", 1)
        blob = meta.split()[-1]
        match = GRAPHIC_RE.fullmatch(rel.removeprefix("graphics/"))
        if not match:
            continue
        sign_id = match.group(2)
        filename = rel.rsplit("/", 1)[-1]
        index.setdefault(sign_id, []).append((match.group(1).lower(), filename, blob))
    return {sign_id: tuple(sorted(items)) for sign_id, items in index.items()}


def changed_ids(
    current: list[dict],
    baseline: list[dict] | None,
    current_graphics: dict[str, tuple] | None = None,
    baseline_graphics: dict[str, tuple] | None = None,
) -> set[str]:
    """Ids whose entry or graphics differ from ``baseline``.

    ``baseline is None`` means there is no approved full release.
    """
    if baseline is None:
        return {sign["id"] for sign in current}
    previous = {sign["id"]: content_signature(sign) for sign in baseline}
    current_graphics = current_graphics or {}
    baseline_graphics = baseline_graphics or {}
    changed: set[str] = set()
    for sign in current:
        sign_id = sign["id"]
        if content_signature(sign) != previous.get(sign_id):
            changed.add(sign_id)
        elif current_graphics.get(sign_id, ()) != baseline_graphics.get(sign_id, ()):
            changed.add(sign_id)
    return changed


def _signs_at_rev(root: Path, rev: str) -> list[dict] | None:
    show = _git(root, ["show", f"{rev}:data/registry.json"])
    if show.returncode != 0:
        return None
    try:
        document = json.loads(show.stdout)
    except json.JSONDecodeError:
        return None
    signs = document.get("signs")
    if not isinstance(signs, list):
        return None
    return signs


def draft_state(root: Path | None = None, signs: list[dict] | None = None) -> DraftState:
    root = root or ROOT
    if signs is None:
        document = json.loads((root / "data" / "registry.json").read_text(encoding="utf-8"))
        signs = document["signs"]
    version, rev = approved_baseline(root)
    if not version or not rev:
        return DraftState(ids=frozenset(sign["id"] for sign in signs), mode="unreleased")
    baseline = _signs_at_rev(root, rev)
    if baseline is None:
        print(f"No data/registry.json at {rev}; treating every sign as draft.", file=sys.stderr)
        return DraftState(
            ids=frozenset(sign["id"] for sign in signs),
            mode="unreleased",
            baseline_version=version,
            baseline_rev=rev,
        )
    changed = changed_ids(
        signs,
        baseline,
        graphic_index_from_tree(root),
        graphic_index_at_rev(root, rev),
    )
    return DraftState(
        ids=frozenset(changed),
        mode="diff",
        baseline_version=version,
        baseline_rev=rev,
    )
