#!/usr/bin/env python3
"""Write ``data/registry.json`` from the Annex I workbook."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from annex import load_workbook

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WORKBOOK = ROOT / "ISO-TC 204-WG 10_N1308_ISO 14823-1 Annex I (EXCEL table).xlsx"
DEFAULT_OUTPUT = ROOT / "data" / "registry.json"


def dump(document: dict) -> str:
    return json.dumps(document, ensure_ascii=False, indent=2) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workbook", type=Path, default=DEFAULT_WORKBOOK)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit 1 when data/registry.json does not match the workbook",
    )
    args = parser.parse_args(argv)
    document = load_workbook(args.workbook)
    text = dump(document)
    warnings = document.get("warnings") or {}
    if args.check:
        current = args.output.read_text(encoding="utf-8") if args.output.is_file() else ""
        if current != text:
            print(
                f"{args.output.relative_to(ROOT)} is out of date. "
                "Run python3 scripts/import_annex.py",
                file=sys.stderr,
            )
            return 1
        print(f"OK: {len(document['signs'])} register entries match the workbook")
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text, encoding="utf-8")
    print(f"Wrote {len(document['signs'])} entries to {args.output.relative_to(ROOT)}")
    for label, items in warnings.items():
        if items:
            print(f"{label}:")
            for item in items:
                print(f"  {item}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
