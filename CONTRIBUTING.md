# Contributions

Changes are reviewed by the maintenance agency for the ISO 14823 graphic data dictionary and published from this repository. By contributing, you agree that your material may be distributed with the project under [CC BY 4.0](LICENSE.md).

## What to edit

| Change | Edit | Then run |
| --- | --- | --- |
| Sign text from the annex workbook | The workbook, then `python3 scripts/import_annex.py` | `python3 scripts/build_pages.py` |
| A country graphic | `graphics/<country>/<service>-<pictogram>.png` | `python3 scripts/build_pages.py` |
| Wording of the home page, styles, or scripts | Those files | `python3 scripts/build_pages.py` when pages are affected |

Generated pages under `docs/signs/`, `docs/categories/`, and `docs/find.md` are rebuilt from `data/registry.json`. Edit the register or the workbook, then regenerate. See [GRAPHICS.md](GRAPHICS.md) for file names. The United Kingdom directory is `gb`, and the Russia & Belarus column is `ru`.

## VERSION

Every pull request sets the root [`VERSION`](VERSION) file. The `validate-version` check compares it with [`RELEASES`](RELEASES) on the base branch.

See the next registry version:

```bash
python3 scripts/versioning.py suggest --releases RELEASES
```

Registry change (a pictogram entry, a status, or a country graphic). The version must be greater than every SemVer already in `RELEASES`:

```text
version: 0.1.0-alpha.2
```

A full release, which becomes the DRAFT baseline, has no pre-release label. Suggest one with `--full`.

Documentation-only change (home-page wording, styles, or scripts that do not change a sign). Keep the current SemVer and add a date that is not earlier than the latest `RELEASES` date:

```text
version: 0.1.0-alpha.1
doc-only: 2026-11-12
```

Check locally:

```bash
python3 scripts/versioning.py validate --releases RELEASES
python3 scripts/import_annex.py --check
python3 scripts/build_pages.py --check
```

Release automation runs on `k-vaughn/iso14823` after a merge to `main`. It appends `RELEASES`, tags the commit, and deploys that version with mike. Forks do not publish releases.
