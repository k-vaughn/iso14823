## Related issue

Fixes #

## Change

- [ ] Registry change (pictogram entry, status, or country graphic)
- [ ] Documentation-only change

## Checklist

- [ ] `VERSION` is updated (SemVer bump for a registry change, or `doc-only: YYYY-MM-DD` for documentation)
- [ ] `python3 scripts/versioning.py validate --releases RELEASES` passes
- [ ] `python3 scripts/import_annex.py` was run if the workbook changed
- [ ] `python3 scripts/build_pages.py` was run and the generated pages are included
- [ ] New graphics follow `graphics/<country>/<service>-<pictogram>.png`
