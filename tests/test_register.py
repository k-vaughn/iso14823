"""Register import, version rules, draft comparison, and page rendering."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import annex  # noqa: E402
import drafts  # noqa: E402
import graphics  # noqa: E402
import pages  # noqa: E402
import versioning  # noqa: E402

WORKBOOK = ROOT / "ISO-TC 204-WG 10_N1308_ISO 14823-1 Annex I (EXCEL table).xlsx"


class AnnexTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.document = annex.load_workbook(WORKBOOK)
        cls.by_id = {sign["id"]: sign for sign in cls.document["signs"]}

    def test_counts_and_unique_ids(self):
        signs = self.document["signs"]
        self.assertEqual(len(signs), 668)
        self.assertEqual(len(self.by_id), 668)
        self.assertTrue(self.document["warnings"]["rows_without_code"])

    def test_stop_sign(self):
        stop = self.by_id["12-112"]
        self.assertEqual(stop["name"], "STOP")
        self.assertEqual(stop["status"], "C")
        self.assertEqual(stop["registered"], "2017")
        self.assertEqual(stop["vienna"], "B, 2a")
        self.assertIn("stopping", stop["definition"])
        self.assertEqual(annex.five_digit("12", "112"), "12112")

    def test_deprecated_stop_ahead(self):
        sign = self.by_id["12-113"]
        self.assertEqual(sign["status"], "D")
        self.assertEqual(sign["retired"], "2023")
        self.assertIn("41", sign["notes"])

    def test_duplicate_stub_dropped_and_range_kept(self):
        self.assertEqual(self.by_id["41-191"]["name"], "With toll")
        block = self.by_id["13-701-710"]
        self.assertEqual(block["kind"], "range")
        self.assertEqual(block["status"], "C")
        self.assertTrue(any("41-191" in item for item in self.document["warnings"]["skipped_stubs"]))

    def test_service_category_typos_are_recorded(self):
        self.assertEqual(self.by_id["32-117-999"].get("service_category_as_written"), "31")
        self.assertNotIn("service_category_as_written", self.by_id["11-137-147"])

    def test_country_codes_follow_iso3166(self):
        codes = [item[0] for item in annex.COUNTRIES]
        self.assertIn("gb", codes)
        self.assertNotIn("uk", codes)
        self.assertIn("ru", codes)
        self.assertEqual(annex.country_by_code()["ru"][1], "Russia & Belarus")

    def test_signature_ignores_worksheet_row(self):
        sign = dict(self.by_id["12-112"])
        moved = dict(sign)
        moved["row"] = sign["row"] + 9
        self.assertEqual(annex.content_signature(sign), annex.content_signature(moved))


class VersioningTests(unittest.TestCase):
    def test_ordering_and_suggestion(self):
        self.assertLess(versioning.SemVer.parse("0.1.0-alpha.1"), versioning.SemVer.parse("0.1.0-alpha.2"))
        self.assertLess(versioning.SemVer.parse("0.1.0-alpha.2"), versioning.SemVer.parse("0.1.0"))
        self.assertEqual(versioning.suggest_next_semver("0.1.0-alpha.1"), "0.1.0-alpha.2")
        self.assertEqual(versioning.suggest_next_semver("0.1.0-alpha.1", prerelease=False), "0.1.0")

    def test_validate_rejects_a_version_that_does_not_move_forward(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            releases = folder / "RELEASES"
            version = folder / "VERSION"
            releases.write_text("0.1.0-alpha.1 2026-11-12 registry\n", encoding="utf-8")
            version.write_text("version: 0.1.0-alpha.1\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                versioning.validate(version, releases)
            version.write_text("version: 0.1.0-alpha.1\ndoc-only: 2026-11-11\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                versioning.validate(version, releases)
            version.write_text("version: 0.1.0-alpha.1\ndoc-only: 2026-11-12\n", encoding="utf-8")
            self.assertTrue(versioning.validate(version, releases).is_doc_only)

    def test_full_release_is_the_draft_baseline(self):
        records = versioning.parse_releases(ROOT / "RELEASES")
        self.assertIsNone(versioning.latest_full_registry_version(records))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "RELEASES"
            path.write_text(
                "0.1.0-alpha.2 2026-11-12 registry\n0.1.0 2026-12-01 registry\n",
                encoding="utf-8",
            )
            self.assertEqual(
                versioning.latest_full_registry_version(versioning.parse_releases(path)),
                "0.1.0",
            )

    def test_repository_version_is_valid(self):
        versioning.validate(ROOT / "VERSION", ROOT / "RELEASES")


class DraftTests(unittest.TestCase):
    def test_no_baseline_marks_every_sign(self):
        signs = [{"id": "12-112", "name": "STOP"}, {"id": "12-113", "name": "Ahead"}]
        self.assertEqual(drafts.changed_ids(signs, None), {"12-112", "12-113"})

    def test_only_the_changed_entry_is_marked(self):
        baseline = [
            {"id": "12-112", "name": "STOP", "status": "C"},
            {"id": "12-113", "name": "Ahead", "status": "D"},
        ]
        current = [
            {"id": "12-112", "name": "STOP", "status": "C"},
            {"id": "12-113", "name": "Stop ahead", "status": "D"},
        ]
        self.assertEqual(drafts.changed_ids(current, baseline), {"12-113"})

    def test_a_new_graphic_marks_the_page_without_an_entry_edit(self):
        signs = [{"id": "12-112", "name": "STOP"}]
        changed = drafts.changed_ids(
            signs,
            signs,
            current_graphics={"12-112": (("de", "12-112.emf", "abc"),)},
            baseline_graphics={},
        )
        self.assertEqual(changed, {"12-112"})


class PageTests(unittest.TestCase):
    def test_stop_page_has_the_watermark_and_the_entry(self):
        sign = annex.load_workbook(WORKBOOK)["signs"]
        stop = next(item for item in sign if item["id"] == "12-112")
        text = pages.render_sign(
            stop,
            draft=True,
            draft_mode="unreleased",
            baseline_version=None,
            files_by_country={},
            root=ROOT,
            known_ids={"12-112", "12-113"},
        )
        self.assertIn('class="draft4-watermark"', text)
        self.assertIn("# 12-112 · STOP", text)
        self.assertIn("B, 2a", text)
        self.assertIn("not yet part of a full release", text)
        self.assertNotIn("draft4-watermark", pages.render_sign(
            stop,
            draft=False,
            draft_mode="diff",
            baseline_version="0.1.0",
            files_by_country={},
            root=ROOT,
            known_ids={"12-112"},
        ))

    def test_find_defaults_to_current(self):
        text = pages.render_find(
            {"categories": [], "countries": [], "signs": []},
            "released",
        )
        self.assertIn('<option value="C" selected>Current</option>', text)

    def test_category_hides_deprecated_until_the_switch_is_off(self):
        service = {"code": "12", "name": "Regulatory", "summary": "Rules of the road."}
        signs = [
            {
                "id": "12-112",
                "name": "STOP",
                "status": "C",
                "kind": "sign",
                "definition": "Stop.",
            },
            {
                "id": "12-113",
                "name": "Former sign",
                "status": "D",
                "kind": "sign",
                "definition": "No longer used.",
            },
        ]
        text = pages.render_category(service, signs, set(), "released")
        self.assertIn('<input type="checkbox" checked>', text)
        self.assertIn(">Hide deprecated</span>", text)
        self.assertIn('<tr class="is-deprecated">', text)
        self.assertIn(">12-112</a>", text)
        self.assertIn(">12-113</a>", text)

    def test_notes_link_a_service_category(self):
        linked = pages._linkify_html("Moved to 41", set(), {"41"})
        self.assertIn('href="../categories/41/"', linked)
        self.assertIn(">41</a>", linked)

    def test_graphic_lookup(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = root / "graphics" / "de"
            folder.mkdir(parents=True)
            (folder / "12-112.EMF").write_bytes(b"emf")
            (folder / "12-112.png").write_bytes(b"png")
            found = graphics.sign_graphics(root, "12-112")
            self.assertEqual(sorted(path.suffix.lower() for path in found["de"]), [".emf", ".png"])
            self.assertEqual(len(graphics.web_files(found["de"])), 1)
            self.assertTrue(graphics.relative_graphic(root, found["de"][0]).startswith("../graphics/de/"))


if __name__ == "__main__":
    unittest.main()
