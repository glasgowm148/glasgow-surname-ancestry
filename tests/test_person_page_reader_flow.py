"""Person pages: opening sentence, research in the reading flow, note links (site audit I1)."""
from pathlib import Path
import json
import tempfile
import unittest
from unittest.mock import patch

from bs4 import BeautifulSoup

import tools.repair_person_hierarchy as renderer
from tools import dossier_resolution
from tools.catalogue_location_search import biography_text


def _site(root: Path, people: dict[str, str]) -> Path:
    """A minimal public site: people-index plus the listed person pages."""
    web = root / "www"
    (web / "people").mkdir(parents=True)
    (web / "data").mkdir(parents=True)
    (web / "assets").mkdir(parents=True)
    (web / "assets/scan.jpg").write_text("x")
    rows = []
    for ident, slug in people.items():
        (web / "people" / f"{slug}.html").write_text("<html></html>")
        rows.append({"id": ident, "html_url": f"/people/{slug}.html", "alternate_ids": []})
    (web / "data/people-index.json").write_text(json.dumps(rows))
    return web


class SiteCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.web = _site(Path(self.tmp.name), {"Glasgow-1": "glasgow-1", "Glasgow-2": "glasgow-2", "Smith-5": "smith-5"})
        self.patches = [patch.object(renderer, "WEB", self.web), patch.object(renderer, "_PERSON_PAGES", None)]
        for item in self.patches:
            item.start()

    def tearDown(self):
        for item in reversed(self.patches):
            item.stop()
        self.tmp.cleanup()


class NoteLinkTests(SiteCase):
    def render(self, markdown, base="/research/Glasgow-1/"):
        return BeautifulSoup(renderer._safe_markdown_html(markdown, base), "html.parser")

    def test_unpublished_files_render_as_text_and_findings_links_go_to_the_person(self):
        soup = self.render("See [the scan](sources/proni_1.jpg), [James](../Glasgow-2/findings.md), "
                           "[audit](/surname-research/x.md), [image](/assets/scan.jpg) and [web](https://example.org/a).")
        hrefs = {a.get_text(): a["href"] for a in soup.select("a")}
        self.assertEqual({"James": "/people/glasgow-2.html", "image": "/assets/scan.jpg", "web": "https://example.org/a"}, hrefs)
        self.assertIn("the scan", soup.get_text())
        self.assertIn("audit", soup.get_text())
        self.assertNotIn("/research/", str(soup))

    def test_people_without_a_page_are_text_and_ids_with_a_page_are_linked(self):
        soup = self.render("[[Glasgow-2|James Glasgow]], [[Mcaughin-2|Mary]], Smith-5, `Glasgow-2`, Weir-9 and Glasgow-1.")
        links = [(a.get_text(), a["href"]) for a in soup.select("a")]
        self.assertIn(("James Glasgow", "/people/glasgow-2.html"), links)
        self.assertIn(("Smith-5", "/people/smith-5.html"), links)
        self.assertIn(("Glasgow-2", "/people/glasgow-2.html"), links)
        self.assertNotIn("Mary", [label for label, _ in links])
        self.assertNotIn("Weir-9", [label for label, _ in links])
        # The page's own ID is not linked to itself.
        self.assertNotIn("Glasgow-1", [label for label, _ in links])
        self.assertNotIn("[[", soup.get_text())

    def test_html_comments_never_reach_the_page(self):
        self.assertNotIn("nir-2026", renderer._safe_markdown_html("Text <!-- nir-2026-10-06-x --> here.", "/research/Glasgow-1/"))


class OpeningTests(SiteCase):
    def test_tree_introduction_says_only_what_the_tree_records(self):
        dossier = {
            "name": "Alice Glasgow",
            "relationships": {
                "parents": [{"id": "Glasgow-2", "name": "James Glasgow"}, {"id": "Doe-1", "name": "Jane Doe"}],
                "spouses": [{"id": "Smith-5", "name": "Tom Smith"}, {"id": "X-1", "name": "Old Link", "status": "superseded"}],
                "children": [{"id": "A-1", "name": "A"}, {"id": "B-1", "name": "B"}, {"id": "C-1", "name": "C", "display": "proposed"}],
            },
        }
        html = renderer._tree_introduction_html(dossier, {"date": "c. 1854", "status": "estimated"},
                                                {"date": "1901-03-02", "status": "exact"}, "Maine, United States", "")
        soup = BeautifulSoup(html, "html.parser")
        self.assertEqual("Alice Glasgow was born about 1854 in Maine, United States, and died on 2 March 1901. "
                         "This page lists James Glasgow and Jane Doe as parents, Tom Smith as spouse and two children.",
                         soup.get_text())
        self.assertEqual({"/people/glasgow-2.html", "/people/smith-5.html"}, {a["href"] for a in soup.select("a")})

    def test_date_phrases(self):
        cases = {
            ("1856", "uncertain"): "about 1856", ("before 1760", "uncertain"): "before 1760",
            ("1991-01", "exact"): "in January 1991", ("c. 1726 (estimated)", "estimated"): "about 1726",
            ("1871-09-16", "exact"): "on 16 September 1871", ("1767-04-10 / 1774-03-25", "uncertain"): "",
        }
        for (value, status), expected in cases.items():
            self.assertEqual(expected, renderer._date_phrase({"date": value, "status": status}), value)
        self.assertEqual("No birth or death date is recorded for Ann.", renderer._tree_introduction_html({"name": "Ann"}, {}, {}, "", ""))


class ResolutionTests(unittest.TestCase):
    def test_no_placeholder_positions_and_plain_conflict_wording(self):
        tree_only = dossier_resolution.resolve_presentation("X-1", {"evidence": [{"id": "e"}]}, {})
        self.assertEqual("unmapped", tree_only["resolution"]["state"])
        self.assertEqual("", tree_only["position"]["answer"])
        nothing = dossier_resolution.resolve_presentation("X-1", {}, {})
        self.assertEqual("", nothing["position"]["answer"])
        conflict = dossier_resolution.resolve_presentation("X-1", {"research_findings": [{"sections": [
            {"title": "Current conclusion", "category": "conclusion", "markdown": "One."},
            {"title": "Current answer", "category": "conclusion", "markdown": "Two."}]}]}, {})
        self.assertEqual("conflict", conflict["resolution"]["state"])
        self.assertEqual(dossier_resolution.CONFLICT_ANSWER, conflict["position"]["answer"])

    def test_opening_skips_labels_and_keeps_wiki_links_as_names(self):
        markdown = "Collateral update, 13 August 2026\n\nJohn was called senior because [[Glasgow-3913|John Glasgow]] was younger.\n\nMore."
        result = dossier_resolution.resolve_presentation("X-1", {"research_findings": [{"sections": [
            {"title": "Current conclusion", "category": "conclusion", "markdown": markdown}]}]}, {})
        self.assertEqual("John was called senior because John Glasgow was younger.", result["opening"])
        self.assertIn("[[Glasgow-3913|John Glasgow]]", result["opening_markdown"])

    def test_search_ignores_generated_sentences(self):
        for answer in dossier_resolution.GENERATED_ANSWERS:
            self.assertEqual("", biography_text({"presentation": {"position": {"answer": answer}}}))
        self.assertIn("Farmer at Ballykeel", biography_text({"presentation": {"position": {"answer": "Farmer at Ballykeel."}}}))


def _findings(*sections, updated="2026-10-07"):
    return [{"profile_id": "Glasgow-1", "updated": updated, "source_path": "research/Glasgow-1/findings.md",
             "sections": [{"title": title, "category": category, "markdown": markdown} for title, category, markdown in sections]}]


class FindingsSectionTests(SiteCase):
    def test_order_anchors_and_visibility(self):
        dossier = {"research_findings": _findings(
            ("Current conclusion", "conclusion", "Opening paragraph.\n\nSecond paragraph."),
            ("Next records", "actions", "Check the will."),
            ("Source findings", "sources", "First source."),
            ("Current conclusion — newspaper review, 5 October 2026", "conclusion", "Older addition."),
            ("Source findings", "sources", "Second source " + "x" * 5000),
            ("Current conclusion — Findmypast evidence fmp-glasgow-e98494418156, 6 October 2026", "conclusion", "Newer addition."),
            ("Relationship assessment", "assessment", "Assessed."),
            ("Superseded reading of 1834", "notes", "Old reading."),
            ("Miscellany", "notes", "Other."),
        )}
        entries = renderer._finding_entries("Glasgow-1", dossier)
        anchors = [entry["anchor"] for entry in entries]
        self.assertEqual(len(anchors), len(set(anchors)))
        first = renderer._research_note_anchor("/research/Glasgow-1/findings.md", "Source findings")
        self.assertIn(first, anchors)
        self.assertIn(first + "-2", anchors)
        html = renderer._research_findings_html("Glasgow-1", dossier, {"opening_markdown": "Opening paragraph."}, entries)
        soup = BeautifulSoup(html, "html.parser")
        self.assertEqual(["Summary of the research", "Later additions", "What the records show", "Identity and family", "Other research notes", "Still open"],
                         [h.get_text() for h in soup.select("h3.finding-group-title")])
        titles = [node.get_text() for node in soup.select(".finding-title")]
        self.assertEqual("Findmypast evidence, 6 October 2026", titles[1])
        self.assertEqual("Newspaper review, 5 October 2026", titles[2])
        self.assertNotIn("Superseded reading of 1834", titles)
        self.assertNotIn("fmp-glasgow", html)
        self.assertIn("last revised on 7 October 2026", soup.get_text())
        # The opening paragraph is on the page once, at the top; the rest is here.
        summary = soup.select_one('details[data-category="summary"]')
        self.assertNotIn("Opening paragraph.", summary.get_text())
        self.assertIn("Second paragraph.", summary.get_text())
        long_section = soup.find(id=first + "-2")
        self.assertNotIn("open", long_section.attrs)
        self.assertTrue(long_section.select_one("summary small").get_text().startswith("Second source"))
        self.assertTrue(all("open" in node.attrs for node in soup.select("details.research-finding") if node is not long_section))
        archive = BeautifulSoup(renderer._archive_html("Glasgow-1", dossier, {}, findings_shown=True), "html.parser")
        self.assertEqual(["Replaced interpretation: Superseded reading of 1834"],
                         [node.summary.get_text() for node in archive.select('details[id^="research-note-"]')])
        self.assertIn("Check the will.", archive.select_one(".archive-original-set").get_text())

    def test_summary_given_at_the_top_leaves_a_note_not_an_empty_box(self):
        # An editor's comment beside the conclusion must not count as remaining text.
        dossier = {"research_findings": _findings(
            ("Current conclusion", "conclusion", "<!-- site-audit: overall conclusion -->\nOpening paragraph."),
            ("Source findings", "sources", "First source."),
        )}
        entries = renderer._finding_entries("Glasgow-1", dossier)
        html = renderer._research_findings_html("Glasgow-1", dossier, {"opening_markdown": "Opening paragraph."}, entries)
        summary = BeautifulSoup(html, "html.parser").select_one('details[data-category="summary"]')
        self.assertIn("given in full at the top of the page", summary.get_text())


class PageOrderTests(SiteCase):
    def render(self, dossier, editorial, update_panel=""):
        with (
            patch.object(renderer, "_profile_data", return_value=(dossier, {}, {})),
            patch.object(renderer, "_editorial", return_value=editorial),
            patch.object(renderer, "_record_rows", return_value=[]),
            patch.object(renderer, "_record_source_map", return_value=({}, [])),
            patch.object(renderer, "_current_vitals", return_value=dossier.get("vitals") or {}),
            patch.object(renderer, "_parent_comparison_html", return_value=""),
            patch.object(renderer, "_evidence_questions", return_value=""),
            patch.object(renderer, "_timeline_html", return_value=""),
            patch.object(renderer, "_research_html", return_value=""),
            patch.object(renderer, "_profile_update_data", return_value=None),
            patch.object(renderer, "_profile_update_panel", return_value=update_panel),
            patch.object(renderer, "_person_links", return_value={}),
        ):
            return BeautifulSoup(renderer.render_person_dossier("Glasgow-1"), "html.parser")

    def test_tree_only_page_opens_with_an_introduction(self):
        dossier = {"id": "Glasgow-1", "name": "Ann Glasgow", "vitals": {"birth": {"date": "1801", "status": "exact", "place": "Ayr"}},
                   "relationships": {}, "research_findings": []}
        editorial = dossier_resolution.resolve_presentation("Glasgow-1", {**dossier, "evidence": [{"id": "e"}]}, {})
        soup = self.render(dossier, editorial)
        overview = soup.select_one("#overview").get_text(" ", strip=True)
        self.assertIn("Ann Glasgow was born in 1801 in Ayr.", overview)
        self.assertIn("no separate research has been written for this person yet", overview)
        for phrase in ("maintained", "publication-safe", "resolved for publication", "Assessment status"):
            self.assertNotIn(phrase, overview)
        self.assertEqual("About Ann", soup.select_one("#overview h2").get_text())
        self.assertIn("WikiTree profile · Glasgow-1", soup.select_one(".kicker").get_text())
        self.assertIn("No family members are recorded", soup.select_one("#family").get_text())
        self.assertNotIn("Explore family", [a.get_text() for a in soup.select(".dossier-actions a")])

    def test_notes_without_summary_and_research_before_editors_panel(self):
        dossier = {"id": "Glasgow-1", "name": "Ann Glasgow", "vitals": {}, "relationships": {},
                   "research_findings": _findings(("Source findings", "sources", "A record names [[Glasgow-2|James]]."))}
        editorial = dossier_resolution.resolve_presentation("Glasgow-1", dossier, {})
        panel = '<section id="wikitree-update" class="profile-update-panel"><h2>Suggested update to the WikiTree profile</h2></section>'
        soup = self.render(dossier, editorial, panel)
        self.assertIn("Research notes are recorded below; an overall summary has not been written yet.", soup.select_one("#overview").get_text())
        order = [child.get("id") for child in soup.select_one(".dossier-reading").find_all(recursive=False)]
        self.assertLess(order.index("research-findings"), order.index("family"))
        self.assertLess(order.index("family"), order.index("wikitree-update"))
        self.assertEqual(order.index("wikitree-update") + 1, order.index("archive-tools"))
        self.assertTrue(soup.select('#research-findings details[id^="research-note-"]'))
        self.assertFalse(soup.select('#archive-tools details[id^="research-note-"]'))
        self.assertEqual("/people/glasgow-2.html", soup.select_one("#research-findings .finding-body a")["href"])


class EditorsPanelTests(unittest.TestCase):
    def test_panel_has_reader_heading_and_purpose_without_score(self):
        update = {"profile_id": "Glasgow-1", "profile_url": "https://www.wikitree.com/wiki/Glasgow-1", "summary": "Add the correction.",
                  "significance": 72, "remote_captured_at": "2026-09-17T11:06:14+00:00", "remote_revision": "1",
                  "remote_wikitext": "old", "proposed_wikitext": "new", "pending": True}
        soup = BeautifulSoup(renderer._profile_update_panel(update), "html.parser")
        self.assertEqual("Suggested update to the WikiTree profile", soup.select_one("#wikitree-update h2").get_text())
        self.assertTrue(soup.select_one(".panel-purpose"))
        self.assertNotIn("Significance", soup.get_text())
        self.assertNotIn("Paste-ready", soup.get_text())


if __name__ == "__main__":
    unittest.main()


class WithheldUpdateTests(unittest.TestCase):
    """A queued WikiTree update whose text names a withheld person is kept off the page."""

    class _Policy:
        @staticmethod
        def contains_private_id(text):
            return "Living-1" in text

    def test_update_naming_a_withheld_person_is_not_rendered(self):
        queued = {"Glasgow-1": {"profile_id": "Glasgow-1", "summary": "Add the lease.",
                                "remote_wikitext": "Source to be added by [[Living-1|A Relative]].",
                                "proposed_wikitext": "Biography."},
                  "Glasgow-2": {"profile_id": "Glasgow-2", "summary": "Add the will.",
                                "remote_wikitext": "Biography.", "proposed_wikitext": "Biography with the will."}}
        with patch.object(renderer, "_PRIVACY_POLICY", self._Policy()), patch.object(renderer, "_PROFILE_UPDATE_CACHE", queued):
            self.assertIsNone(renderer._profile_update_data("Glasgow-1", {}))
            self.assertEqual("Add the will.", renderer._profile_update_data("Glasgow-2", {})["summary"])
            self.assertEqual("", renderer._profile_update_panel(renderer._profile_update_data("Glasgow-1", {})))
