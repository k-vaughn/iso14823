# Registry for ITS Graphics (RITSG)

Public register of the pictograms in ISO 14823-1 Annex I, the graphic data dictionary for intelligent transport systems.

The site is a [Zensical](https://zensical.org/) project. Each pictogram code has its own page. Search finds a sign by code (`12-112`, `12112`) or by keyword (`stop`). Country graphics live under [`graphics/`](GRAPHICS.md) as `<country>/<service>-<pictogram>.png`.

Versions are recorded in [`VERSION`](VERSION) and [`RELEASES`](RELEASES). Pull requests are checked against `RELEASES` before merge. A merge publishes the site with mike, and sign pages that differ from the last full release show the DRAFT watermark used on the ISO 24315 vocabulary.

## Build

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 scripts/import_annex.py
python3 scripts/build_pages.py
zensical serve
```

`import_annex.py` reads the Annex I workbook into `data/registry.json`. `build_pages.py` writes `docs/signs/`, `docs/categories/`, and `docs/find.md`.

## Checks

```bash
python3 -m unittest discover -s tests -v
python3 scripts/versioning.py validate --releases RELEASES
python3 scripts/import_annex.py --check
python3 scripts/build_pages.py --check
```
