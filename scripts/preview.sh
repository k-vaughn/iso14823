#!/bin/sh
# Rebuild the register pages and open the local Zensical preview.
set -eu
cd "$(dirname "$0")/.."
python3 scripts/import_annex.py
python3 scripts/build_pages.py
exec zensical serve "$@"
