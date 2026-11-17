#!/usr/bin/env python3
"""VERSION / RELEASES helpers for the ITS graphics register.

VERSION file format (repo root):
  version: 1.2.3
  doc-only: 2026-07-27   # optional

RELEASES file format (repo root), one record per line:
  <semver> <YYYY-MM-DD> <registry|doc-only>

A ``registry`` release changes pictogram entries. A ``doc-only`` release
keeps that version number and records a documentation date.
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import sys
from dataclasses import dataclass
from functools import total_ordering
from pathlib import Path
from typing import Iterable, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
VERSION_PATH = ROOT / "VERSION"
RELEASES_PATH = ROOT / "RELEASES"

SEMVER_RE = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)"
    r"(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))"
    r"?(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
)
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
RELEASE_KINDS = ("registry", "doc-only")


def _ident_key(part: str) -> Tuple:
    if part.isdigit():
        return (0, int(part))
    return (1, part)


@total_ordering
@dataclass(frozen=True)
class SemVer:
    major: int
    minor: int
    patch: int
    prerelease: Tuple[str, ...] = ()
    build: str = ""

    @classmethod
    def parse(cls, value: str) -> "SemVer":
        text = value.strip()
        if text.startswith(("v", "V")) and SEMVER_RE.match(text[1:]):
            text = text[1:]
        match = SEMVER_RE.match(text)
        if not match:
            raise ValueError(f"Invalid SemVer: {value!r}")
        pre = tuple(match.group(4).split(".")) if match.group(4) else ()
        build = match.group(5) or ""
        return cls(int(match.group(1)), int(match.group(2)), int(match.group(3)), pre, build)

    @property
    def text(self) -> str:
        base = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            base += "-" + ".".join(self.prerelease)
        if self.build:
            base += "+" + self.build
        return base

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SemVer):
            return NotImplemented
        return (self.major, self.minor, self.patch, self.prerelease) == (
            other.major,
            other.minor,
            other.patch,
            other.prerelease,
        )

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, SemVer):
            return NotImplemented
        core = (self.major, self.minor, self.patch)
        other_core = (other.major, other.minor, other.patch)
        if core != other_core:
            return core < other_core
        if self.prerelease and not other.prerelease:
            return True
        if not self.prerelease and other.prerelease:
            return False
        for left, right in zip(self.prerelease, other.prerelease):
            if left == right:
                continue
            return _ident_key(left) < _ident_key(right)
        return len(self.prerelease) < len(other.prerelease)


@dataclass(frozen=True)
class VersionFile:
    version: str
    doc_only: Optional[dt.date] = None

    @property
    def is_doc_only(self) -> bool:
        return self.doc_only is not None

    @property
    def semver(self) -> SemVer:
        return SemVer.parse(self.version)

    @property
    def is_prerelease(self) -> bool:
        return bool(self.semver.prerelease)

    @property
    def release_type(self) -> str:
        return "doc-only" if self.is_doc_only else "registry"


@dataclass(frozen=True)
class ReleaseRecord:
    version: str
    date: dt.date
    kind: str


def normalize_semver(value: str) -> str:
    return SemVer.parse(value).text


def parse_version_file(path: Path = VERSION_PATH) -> VersionFile:
    if not path.is_file():
        raise ValueError(f"VERSION file not found: {path}")
    version: Optional[str] = None
    doc_only: Optional[dt.date] = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            raise ValueError(f"Invalid VERSION line (expected key: value): {raw!r}")
        key, val = line.split(":", 1)
        key = key.strip().lower()
        val = val.strip()
        if key == "version":
            version = normalize_semver(val)
        elif key == "doc-only":
            if not DATE_RE.match(val):
                raise ValueError(f"Invalid doc-only date (YYYY-MM-DD): {val!r}")
            doc_only = dt.date.fromisoformat(val)
        else:
            raise ValueError(f"Unknown VERSION key: {key!r}")
    if not version:
        raise ValueError("VERSION must contain a 'version:' line")
    return VersionFile(version=version, doc_only=doc_only)


def parse_releases(path: Path = RELEASES_PATH) -> list[ReleaseRecord]:
    if not path.is_file():
        return []
    records: list[ReleaseRecord] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) != 3:
            raise ValueError(
                "Invalid RELEASES line "
                "(expected '<semver> <YYYY-MM-DD> <registry|doc-only>'): "
                f"{raw!r}"
            )
        version, date_s, kind = parts
        version = normalize_semver(version)
        if not DATE_RE.match(date_s):
            raise ValueError(f"Invalid RELEASES date: {date_s!r}")
        if kind not in RELEASE_KINDS:
            raise ValueError(f"Invalid RELEASES type: {kind!r}")
        records.append(
            ReleaseRecord(version=version, date=dt.date.fromisoformat(date_s), kind=kind)
        )
    return records


def latest_semver(records: Iterable[ReleaseRecord]) -> Optional[str]:
    best: Optional[SemVer] = None
    best_text: Optional[str] = None
    for rec in records:
        current = SemVer.parse(rec.version)
        if best is None or current > best:
            best = current
            best_text = normalize_semver(rec.version)
    return best_text


def latest_full_registry_version(records: Iterable[ReleaseRecord]) -> Optional[str]:
    """Latest registry release with no pre-release label."""
    best: Optional[SemVer] = None
    best_text: Optional[str] = None
    for rec in records:
        if rec.kind != "registry":
            continue
        version = SemVer.parse(rec.version)
        if version.prerelease:
            continue
        if best is None or version > best:
            best = version
            best_text = normalize_semver(rec.version)
    return best_text


def max_release_date(records: Iterable[ReleaseRecord]) -> Optional[dt.date]:
    dates = [rec.date for rec in records]
    return max(dates) if dates else None


def suggest_next_semver(latest: Optional[str], *, prerelease: bool = True) -> str:
    if not latest:
        return "0.0.1-alpha.1" if prerelease else "0.0.1"
    current = SemVer.parse(latest)
    if prerelease:
        if current.prerelease:
            pre = list(current.prerelease)
            if pre and pre[-1].isdigit():
                pre[-1] = str(int(pre[-1]) + 1)
            else:
                pre.append("1")
            return SemVer(current.major, current.minor, current.patch, tuple(pre)).text
        return SemVer(current.major, current.minor, current.patch + 1, ("alpha", "1")).text
    if current.prerelease:
        return SemVer(current.major, current.minor, current.patch).text
    return SemVer(current.major, current.minor, current.patch + 1).text


def validate(
    version_path: Path = VERSION_PATH, releases_path: Path = RELEASES_PATH
) -> VersionFile:
    version_file = parse_version_file(version_path)
    records = parse_releases(releases_path)
    latest = latest_semver(records)
    max_date = max_release_date(records)

    if version_file.is_doc_only:
        assert version_file.doc_only is not None
        if latest is None:
            raise ValueError("doc-only releases require a prior registry SemVer in RELEASES")
        if normalize_semver(version_file.version) != normalize_semver(latest):
            raise ValueError(
                f"doc-only PR must keep version: {latest} "
                f"(VERSION has {version_file.version}). "
                "Do not bump SemVer for documentation-only changes."
            )
        if max_date is not None and version_file.doc_only < max_date:
            raise ValueError(
                f"doc-only date {version_file.doc_only.isoformat()} must be >= latest "
                f"RELEASES date {max_date.isoformat()}"
            )
        print(
            f"OK: doc-only release for registry {version_file.version} "
            f"on {version_file.doc_only.isoformat()}"
        )
        return version_file

    if latest is not None and not (version_file.semver > SemVer.parse(latest)):
        suggested = suggest_next_semver(latest, prerelease=True)
        raise ValueError(
            f"VERSION {version_file.version} must be > latest release {latest} "
            f"(from the PR base RELEASES). Suggested next line:\n"
            f"  version: {suggested}"
        )
    kind = "pre-release" if version_file.is_prerelease else "full release"
    print(
        f"OK: registry {kind} {version_file.version} "
        f"(latest on base was {latest or 'none'})"
    )
    return version_file


def append_release(
    version_file: VersionFile,
    releases_path: Path = RELEASES_PATH,
    release_date: Optional[dt.date] = None,
) -> ReleaseRecord:
    release_date = release_date or (
        version_file.doc_only if version_file.is_doc_only else dt.date.today()
    )
    assert release_date is not None
    record = ReleaseRecord(
        version=normalize_semver(version_file.version),
        date=release_date,
        kind=version_file.release_type,
    )
    line = f"{record.version} {record.date.isoformat()} {record.kind}\n"
    if releases_path.is_file():
        existing = releases_path.read_text(encoding="utf-8")
    else:
        existing = "# version date type\n# type is 'registry' or 'doc-only'\n"
    if existing and not existing.endswith("\n"):
        existing += "\n"
    releases_path.write_text(existing + line, encoding="utf-8")
    print(f"Appended to RELEASES: {line.strip()}")
    return record


def already_recorded(version_file: VersionFile, records: list[ReleaseRecord]) -> bool:
    for record in reversed(records):
        if record.version != normalize_semver(version_file.version):
            continue
        if record.kind != version_file.release_type:
            continue
        if version_file.is_doc_only:
            if version_file.doc_only and record.date == version_file.doc_only:
                return True
        else:
            return True
    return False


def choose_doc_tag(doc_date: dt.date, existing_tags: Iterable[str]) -> str:
    tags = set(existing_tags)
    base = f"docs-{doc_date.isoformat()}"
    if base not in tags:
        return base
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")
    return f"docs-{stamp}"


def registry_tag(version: str) -> str:
    return f"v{normalize_semver(version)}"


def _tag_for(version_file: VersionFile, existing_tags: Iterable[str]) -> str:
    if version_file.is_doc_only:
        assert version_file.doc_only is not None
        return choose_doc_tag(version_file.doc_only, existing_tags)
    return registry_tag(version_file.version)


def _emit_outputs(
    version_file: VersionFile,
    *,
    tag: str,
    prerelease: bool,
    changed: bool,
    publish: bool = True,
) -> None:
    lines = [
        f"kind={version_file.release_type}",
        f"version={version_file.version}",
        f"tag={tag}",
        f"prerelease={'true' if prerelease else 'false'}",
        f"changed={'true' if changed else 'false'}",
        f"publish={'true' if publish else 'false'}",
    ]
    for line in lines:
        print(line)
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with Path(output).open("a", encoding="utf-8") as handle:
            for line in lines:
                handle.write(line + "\n")


def cmd_validate(args: argparse.Namespace) -> int:
    try:
        releases = Path(args.releases) if args.releases else RELEASES_PATH
        validate(version_path=VERSION_PATH, releases_path=releases)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


def cmd_suggest(args: argparse.Namespace) -> int:
    try:
        releases = Path(args.releases) if args.releases else RELEASES_PATH
        latest = latest_semver(parse_releases(releases))
        print(suggest_next_semver(latest, prerelease=not args.full))
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


def cmd_apply(args: argparse.Namespace) -> int:
    """Append RELEASES when needed and print the tag the workflow should publish."""
    try:
        version_file = parse_version_file()
        records = parse_releases()
        existing = [tag.strip() for tag in (args.existing_tags or "").split(",") if tag.strip()]
        tag = _tag_for(version_file, existing)
        prerelease = (not version_file.is_doc_only) and version_file.is_prerelease
        if already_recorded(version_file, records):
            print("RELEASES already has this version; ensuring the release can be published.")
            _emit_outputs(
                version_file, tag=tag, prerelease=prerelease, changed=False, publish=True
            )
            return 0
        validate()
        release_date = version_file.doc_only if version_file.is_doc_only else dt.date.today()
        append_release(version_file, release_date=release_date)
        _emit_outputs(version_file, tag=tag, prerelease=prerelease, changed=True, publish=True)
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


def cmd_print_tag(args: argparse.Namespace) -> int:
    version_file = parse_version_file()
    if version_file.is_doc_only:
        assert version_file.doc_only is not None
        existing = [tag.strip() for tag in (args.existing_tags or "").split(",") if tag.strip()]
        print(choose_doc_tag(version_file.doc_only, existing))
    else:
        print(registry_tag(version_file.version))
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    validate_parser = sub.add_parser("validate", help="Validate VERSION against RELEASES")
    validate_parser.add_argument("--releases", default="", help="RELEASES file to compare against")
    validate_parser.set_defaults(func=cmd_validate)

    suggest_parser = sub.add_parser("suggest", help="Print the next suggested SemVer")
    suggest_parser.add_argument("--releases", default="")
    suggest_parser.add_argument("--full", action="store_true", help="Suggest a full release")
    suggest_parser.set_defaults(func=cmd_suggest)

    apply_parser = sub.add_parser("apply", help="Append RELEASES and print release outputs")
    apply_parser.add_argument("--existing-tags", default="")
    apply_parser.set_defaults(func=cmd_apply)

    tag_parser = sub.add_parser("print-tag", help="Print the git tag for the current VERSION")
    tag_parser.add_argument("--existing-tags", default="")
    tag_parser.set_defaults(func=cmd_print_tag)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
