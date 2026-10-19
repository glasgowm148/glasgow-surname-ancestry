"""Reader wording and guide links for every printed evidence label (S3-06)."""
from tests._generated_data import requires_generated_data
from pathlib import Path
import re
import tempfile
import unittest

from bs4 import BeautifulSoup

from tools import evidence_labels as ev

ROOT = Path(__file__).resolve().parents[1]
STRONG = {"state-proved", "state-strongly-supported"}

# The source-quality and record-link texts seen on place pages on 7 October 2026
# (102 distinct texts): five quality labels plus the curated record texts.
QUALITY_TEXTS = {"Unclassified", "Index or transcription", "Original record", "Tree/profile only", "Secondary source"}


class DescribeTests(unittest.TestCase):
    def test_every_state_alias_and_quality_has_a_guide_entry(self):
        entries = ev.guide_entries()
        values = [*ev.STATES, *ev.ALIASES, *ev.TREE_DATA_STATUS, *ev.RECORD_QUALITY, *ev.RECORD_EVIDENCE,
                  *(state["label"] for state in ev.STATES.values())]
        for value in values:
            with self.subTest(value=value):
                info = ev.describe(value)
                self.assertIn(info["anchor"], entries)
                self.assertEqual(f"/evidence/#{info['anchor']}", info["url"])
                self.assertTrue(info["text"] and info["meaning"])
                self.assertTrue(info["mapped"])

    def test_standard_keys_print_their_standard_label(self):
        self.assertEqual("Documented", ev.describe("proved")["text"])
        self.assertEqual("state-strongly-supported", ev.describe("strongly_supported")["anchor"])
        self.assertEqual("Tree-marked DNA confirmed", ev.describe("30")["text"])
        self.assertEqual("Unclassified", ev.describe("unknown")["text"])
        self.assertEqual("quality-unknown", ev.describe("unknown")["anchor"])
        self.assertEqual("Original record", ev.describe("original", "quality")["text"])
        self.assertEqual("Unassessed tree link", ev.describe("unknown", "state")["text"])
        self.assertEqual("tone-hypothesis", ev.describe("hypothesis", "tone")["anchor"])
        # Curated dossier text keeps its qualifier.
        self.assertEqual("Probable; 1892 citation", ev.describe("Probable; 1892 citation")["text"])

    def test_place_badge_texts_map_without_upgrading(self):
        self.assertFalse(set(ev.BADGE_TEXT_MAP) & ev.UNMAPPED_BADGE_TEXTS)
        self.assertEqual(102, len(set(ev.BADGE_TEXT_MAP) | ev.UNMAPPED_BADGE_TEXTS | QUALITY_TEXTS))
        entries = ev.guide_entries()
        for text, (anchor, _shown) in ev.BADGE_TEXT_MAP.items():
            with self.subTest(text=text):
                info = ev.describe(text)
                self.assertTrue(info["mapped"])
                self.assertIn(anchor, entries)
                lowered = text.casefold()
                if not lowered.startswith(("documented", "proved")):
                    self.assertNotIn(info["anchor"], STRONG, "a weaker text must not be filed as documented")
                elif re.search(r"\b(?:probable|possible|candidate|working|hypothesis)\b", lowered.split(" /")[0]):
                    self.fail("a documented text with a weaker main clause needs the owner's decision")
                if lowered.startswith("proved"):
                    self.assertTrue(info["text"].startswith("Documented"))
        self.assertEqual("Profile lead · One-Tree", ev.describe("One-Tree profile lead")["text"])
        self.assertEqual("Probable · Highly probable same Irish cleric", ev.describe("Highly probable same Irish cleric")["text"])

    def test_unmapped_wording_is_shown_as_written(self):
        for text in sorted(ev.UNMAPPED_BADGE_TEXTS) + ["A brand-new wording"]:
            with self.subTest(text=text):
                info = ev.describe(text)
                self.assertFalse(info["mapped"])
                self.assertEqual(text, info["text"])
                self.assertEqual(ev.OTHER_WORDING_ANCHOR, info["anchor"])

    def test_label_html_links_to_the_guide_entry(self):
        html = ev.label_html("One-Tree profile lead")
        soup = BeautifulSoup(html, "html.parser")
        span = soup.select_one("span.evidence-badge.evidence-one-tree-profile-lead")
        link = span.select_one("a.ev-label-link")
        self.assertEqual("/evidence/#link-profile-lead", link["href"])
        self.assertEqual("Profile lead · One-Tree", link.get_text())
        self.assertEqual(ev.RECORD_EVIDENCE["Profile lead"], link["title"])
        self.assertIn('href="/evidence/"', ev.guide_link_html())
        self.assertIn(ev.GUIDE_LINK_TEXT, ev.guide_link_html())

    def test_catalogue_badge_helper_uses_the_shared_function(self):
        from tools.build_research_catalog import _evidence_badge
        self.assertEqual(ev.label_html("One-Tree profile lead"), _evidence_badge("One-Tree profile lead"))
        unknown = BeautifulSoup(_evidence_badge("unknown", "Source unclassified"), "html.parser").a
        self.assertEqual(("Unclassified", "/evidence/#quality-unknown"), (unknown.get_text(), unknown["href"]))
        raw = BeautifulSoup(_evidence_badge("Probate index"), "html.parser").a
        self.assertEqual(("Probate index", "/evidence/#other-wording"), (raw.get_text(), raw["href"]))
        self.assertIn("evidence-unknown", _evidence_badge(""))


class RelabelBuiltPagesTests(unittest.TestCase):
    def test_repair_of_built_badges_matches_the_builder(self):
        from tools.relabel_evidence_badges import relabel
        for stored, shown in (("One-Tree profile lead", "One-Tree profile lead"), ("unknown", "Unclassified"),
                              ("original", "Original record"), ("Probate index", "Probate index"),
                              ("Proved son", "Proved son"), ("Documented", "Documented")):
            with self.subTest(stored=stored):
                status = re.sub(r"[^a-z0-9]+", "-", stored.casefold()).strip("-")
                old = f'<div class="badge-row"><span class="evidence-badge evidence-{status}">{shown}</span></div>'
                new, count = relabel(old)
                self.assertEqual(1, count)
                self.assertEqual(f'<div class="badge-row">{ev.label_html(stored)}</div>', new)
                self.assertEqual((new, 0), relabel(new))


class GuidePageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from tools import build_evidence_page as builder
        cls.builder = builder
        cls.soup = BeautifulSoup(builder.render('<html><head><title>About</title></head><body><main>About</main></body></html>'), "html.parser")
        cls.main = cls.soup.select_one("main")

    def test_internal_keys_are_not_visible(self):
        text = self.main.get_text(" ", strip=True)
        for key in [*ev.STATES, *ev.RECORD_QUALITY]:
            if "_" in key:
                self.assertNotIn(key, text)
        self.assertFalse(self.main.select(".ev-key"))
        self.assertEqual("strongly_supported", self.main.select_one("#state-strongly-supported")["data-key"])

    def test_every_label_has_meaning_basis_and_example(self):
        for anchor in ev.guide_entries():
            with self.subTest(anchor=anchor):
                self.assertIsNotNone(self.soup.find(id=anchor))
        for key in ev.STATES:
            entry = self.main.select_one(f"#{ev.anchor_for_state(key)}")
            terms = [dt.get_text(strip=True) for dt in entry.select("dt")]
            self.assertEqual(["Usually rests on", "Example"], terms, key)
            self.assertIn(ev.STATES[key]["label"], entry.h3.get_text())
        for anchor, example in ev.GUIDE_EXAMPLES.items():
            self.assertIsNotNone(self.soup.find(id=anchor), anchor)
            if example:
                link = self.main.select_one(f'#{anchor} a[href="{example[1]}"]')
                self.assertIsNotNone(link, anchor)

    @requires_generated_data
    def test_published_guide_examples_have_local_destinations(self):
        for example in ev.GUIDE_EXAMPLES.values():
            if example:
                self.assertTrue((ROOT / "www" / example[1].lstrip("/")).exists(), example[1])

    def test_other_wording_table_lists_the_mapping(self):
        rows = self.main.select(f"#{ev.OTHER_WORDING_ANCHOR} tbody tr")
        self.assertGreater(len(rows), 50)
        cells = {row.td.get_text(): row.select("td")[1].a["href"] for row in rows}
        self.assertEqual("#link-profile-lead", cells["One-Tree profile lead"])

    def test_stylesheet_is_maintained_and_installed_idempotently(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "evidence.css"
            self.assertTrue(self.builder.install_css(target))
            self.assertFalse(self.builder.install_css(target))
            self.assertIn(".ev-label-link", target.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
