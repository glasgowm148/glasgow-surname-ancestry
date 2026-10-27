from pathlib import Path
import json
import re
import tempfile
import unittest

from unittest.mock import patch

from tests._generated_data import requires_generated_data

from bs4 import BeautifulSoup
from tests._site_html import read_html


ROOT = Path(__file__).resolve().parents[1]


class PersonDossierPresentationTests(unittest.TestCase):
    def test_timeline_uses_reviewed_vital_without_changing_captured_events(self):
        from copy import deepcopy
        from tools import repair_person_hierarchy as renderer
        model = {'events': [
            {'id': 'death', 'p': 'person-1', 'kind': 'personal', 'basis': 'imported_vital',
             'event_type': 'death', 'date': '1753-03-23', 'year': 1753, 'label': 'Death'},
            {'id': 'relative-death', 'kind': 'collateral', 'event_type': 'death',
             'date': '1800-01-01', 'year': 1800, 'label': 'Relative death'}]}
        original = deepcopy(model)
        death = {'date': '1753-03-15', 'display_date': '15 March 1753 (reported)',
                 'source_url': 'https://example.org/original', 'note': 'Derived from Thursday last.',
                 'provenance': {'assessment_id': 'reviewed-death'}}
        with patch.object(renderer, '_editorial', return_value={}):
            html = renderer._timeline_html('Person-1', model, [], {}, vitals={'death': death})
            unknown = renderer._timeline_html('Person-1', model, [], {},
                vitals={'death': {**death, 'date': None, 'display_date': None}})
        self.assertIn('15 March 1753 (reported)', html)
        self.assertIn('Derived from Thursday last.', html)
        self.assertIn('https://example.org/original', html)
        self.assertNotIn('23 March 1753', html)
        self.assertIn('1 January 1800', html)
        self.assertIn('Undated', unknown)
        self.assertNotIn('23 March 1753', unknown)
        self.assertEqual(model, original)

    def page(self, slug):
        return BeautifulSoup(read_html(ROOT / "www/people" / f"{slug}.html"), "html.parser")

    @requires_generated_data
    def test_evidence_questions_keep_reading_inset(self):
        """The dossier override must not reset expanded evidence cards to edge-to-edge text."""
        stylesheet = (ROOT / "www/assets/repair/person-hierarchy.css").read_text(encoding="utf-8")
        self.assertIn(".person-hierarchy .question{background:#fffefa;border:0;border-bottom:1px solid #d7dfd1;border-radius:0;padding:17px 18px", stylesheet)
        self.assertIn(".person-hierarchy .question{margin:10px 0", stylesheet)
        self.assertIn(".person-hierarchy .question{padding:16px}", stylesheet)

    def test_wikitree_panel_keeps_current_capture_and_diff(self):
        import tools.repair_person_hierarchy as renderer

        update = {
            "profile_id": "Glasgow-1",
            "profile_url": "https://www.wikitree.com/wiki/Glasgow-1",
            "summary": "Add the sourced correction.",
            "significance": 90,
            "remote_captured_at": "2026-09-30T16:50:00Z",
            "remote_revision": "20260930165000",
            "remote_wikitext": "old line\nkeep",
            "proposed_wikitext": "new line\nkeep",
            "pending": True,
        }
        soup = BeautifulSoup(renderer._profile_update_panel(update), "html.parser")
        self.assertIsNotNone(soup.select_one("#wikitree-update"))
        self.assertEqual("old line\nkeep", soup.select_one("#profile-update-current").get_text())
        self.assertEqual("new line\nkeep", soup.select_one("#profile-update-draft").get_text())
        self.assertIsNotNone(soup.select_one(".profile-update-diff"))
        self.assertIn("2026-09-30T16:50:00Z", soup.select_one(".workbench-audit").get_text())

    def test_completed_wikitree_comparison_is_not_marked_pending(self):
        import tools.repair_person_hierarchy as renderer

        update = {
            "profile_id": "Glasgow-1",
            "profile_url": "https://www.wikitree.com/wiki/Glasgow-1",
            "summary": "The prepared amendment is already on WikiTree; no pending biography change.",
            "significance": 90,
            "remote_captured_at": "2026-09-30T16:50:00Z",
            "remote_revision": "20260930165000",
            "remote_wikitext": "same",
            "draft_wikitext": "same",
            "pending": False,
        }
        soup = BeautifulSoup(renderer._profile_update_panel(update), "html.parser")
        self.assertIn("WikiTree profile and prepared draft", soup.get_text())
        self.assertNotIn("Needs updated on WikiTree", soup.get_text())
        self.assertIsNotNone(soup.select_one("#profile-update-current"))

    def test_dossier_comparison_fallback_preserves_capture(self):
        import tools.repair_person_hierarchy as renderer

        dossier = {
            "id": "Glasgow-1",
            "wikitree_comparison": {
                "profile_id": "Glasgow-1",
                "remote_wikitext": "current",
                "draft_wikitext": "draft",
                "pending": False,
            },
        }
        with patch.object(renderer, "_PROFILE_UPDATE_CACHE", {}):
            result = renderer._profile_update_data("Glasgow-1", dossier)
        self.assertEqual("current", result["remote_wikitext"])
        self.assertEqual("draft", result["proposed_wikitext"])
        self.assertFalse(result["pending"])

    def test_completed_comparison_uses_captured_biography_as_draft(self):
        from tools.sync_catalogue_research import completed_comparisons
        from tools.public_privacy import PublicPrivacy

        result = completed_comparisons(
            {"profiles": {"Glasgow-1": {
                "profile_url": "https://www.wikitree.com/wiki/Glasgow-1",
                "captured_at": "2026-09-30T16:50:00Z",
                "last_updated": "20260930165000",
                "biography_wikitext": "current biography",
            }}},
            {"completed_live_profiles": ["Glasgow-1"], "entries": {}},
            PublicPrivacy({}),
        )
        self.assertEqual("current biography", result["Glasgow-1"]["remote_wikitext"])
        self.assertEqual("current biography", result["Glasgow-1"]["draft_wikitext"])
        self.assertFalse(result["Glasgow-1"]["pending"])

    def test_completed_comparison_withholds_private_paragraphs(self):
        from tools.public_privacy import PublicPrivacy
        from tools.sync_catalogue_research import completed_comparisons

        biography = "Historical source and family.\n\nPrivate relative [[Example-200]]."
        evidence = {"profiles": {"Example-100": {"privacy": 60, "biography_wikitext": biography}}}
        policy = PublicPrivacy({"Example-200": {"birth_date": "1950-01-01"}})
        result = completed_comparisons(evidence, {"completed_live_profiles": ["Example-100"]}, policy)
        expected = "Historical source and family.\n\nPrivate family details withheld."
        self.assertEqual(expected, result["Example-100"]["remote_wikitext"])
        self.assertEqual(expected, result["Example-100"]["draft_wikitext"])
        self.assertEqual(biography, evidence["profiles"]["Example-100"]["biography_wikitext"])

    def test_completed_comparison_omits_restricted_or_living_subjects(self):
        from tools.public_privacy import PublicPrivacy
        from tools.sync_catalogue_research import completed_comparisons

        evidence = {"profiles": {
            "Example-100": {"privacy": 35, "biography_wikitext": "Restricted biography"},
            "Example-200": {"privacy": 60, "biography_wikitext": "Living biography"},
        }}
        policy = PublicPrivacy({"Example-200": {"birth_date": "1950-01-01"}})
        result = completed_comparisons(evidence, {"completed_live_profiles": list(evidence["profiles"])}, policy)
        self.assertEqual({}, result)

    def test_biography_sections_are_visible_navigable_and_label_their_own_tables(self):
        """Authored narrative belongs in the reading flow, including its evidence table."""
        from tools.repair_person_hierarchy import render_person_dossier
        editorial = {
            "opening": "A maintained assessment.",
            "biography_sections": [{
                "id": "early-records",
                "title": "Early records",
                "markdown": "[See these records](#early-records)\n\n| Year | Finding |\n| --- | --- |\n| 1841 | Present in parish |",
            }],
        }
        dossier = {"id": "Example-1", "name": "Example Person", "vitals": {}}
        with (
            patch("tools.repair_person_hierarchy._profile_data", return_value=(dossier, {}, {})),
            patch("tools.repair_person_hierarchy._editorial", return_value=editorial),
            patch("tools.repair_person_hierarchy._record_rows", return_value=[]),
            patch("tools.repair_person_hierarchy._record_source_map", return_value=({}, [])),
            patch("tools.repair_person_hierarchy._current_vitals", return_value={}),
            patch("tools.repair_person_hierarchy._family_html", return_value=""),
            patch("tools.repair_person_hierarchy._parent_comparison_html", return_value=""),
            patch("tools.repair_person_hierarchy._evidence_questions", return_value=""),
            patch("tools.repair_person_hierarchy._timeline_html", return_value=""),
            patch("tools.repair_person_hierarchy._research_html", return_value=""),
            patch("tools.repair_person_hierarchy._sources_html", return_value=""),
            patch("tools.repair_person_hierarchy._archive_html", return_value=""),
        ):
            soup = BeautifulSoup(render_person_dossier("Example-1"), "html.parser")
        section = soup.select_one(".biography-section#early-records")
        self.assertIsNotNone(section)
        self.assertNotEqual("details", section.name)
        self.assertEqual("Early records", section.select_one("h2").get_text(strip=True))
        self.assertTrue(soup.select_one('.dossier-nav a[href="#early-records"]'))
        self.assertTrue(soup.select_one('.dossier-toc a[href="#early-records"]'))
        self.assertTrue(section.select_one('.biography-content a[href="#early-records"]'))
        table = section.select_one("table.biography-table")
        self.assertEqual(["Year", "Finding"], [node.get_text(strip=True) for node in table.select("thead th")])
        self.assertEqual("Year", table.select_one("tbody td").get("data-label"))
        self.assertEqual("Finding", table.select("tbody td")[1].get("data-label"))
        self.assertTrue(table.select_one("caption"))

    def test_biography_figures_reserve_their_size(self):
        """Width and height come from the figure itself, so a lazy image cannot shift the page."""
        import struct
        import tools.repair_person_hierarchy as renderer

        png = b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + b"IHDR" + struct.pack(">II", 640, 480) + b"\x08\x02\x00\x00\x00"
        svg = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 360 555" role="img"><title>T</title></svg>'
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            figures = root / "research/Example-1/figures"
            figures.mkdir(parents=True)
            (figures / "map.png").write_bytes(png)
            (figures / "map-mobile.svg").write_bytes(svg)
            (figures / "odd.webp").write_bytes(b"RIFF-not-parsed")
            with patch.object(renderer, "ROOT", root), patch.object(renderer, "WEB", root / "www"):
                soup = BeautifulSoup(renderer._biography_figure_html("Example-1", {"file": "map.png", "mobile_file": "map-mobile.svg", "alt": "Map"}), "html.parser")
                unknown = BeautifulSoup(renderer._biography_figure_html("Example-1", {"file": "odd.webp", "alt": "Odd"}), "html.parser")
        self.assertEqual(("640", "480"), (soup.img["width"], soup.img["height"]))
        self.assertEqual(("360", "555"), (soup.source["width"], soup.source["height"]))
        self.assertNotIn("width", unknown.img.attrs)

    def test_biography_figures_copy_local_assets_and_reject_invalid_files(self):
        """Figure markers render authored local evidence while unsafe or absent files stay empty."""
        import tools.repair_person_hierarchy as renderer

        payload = b"example-image-bytes"
        editorial = {
            "opening": "A maintained assessment.",
            "biography_sections": [{
                "id": "early-records",
                "title": "Early records",
                "markdown": "Before the table.\n\n{{figure:map.png}}\n\nAfter the figures.",
                "figures": [
                    {"file": "map.png", "mobile_file": "map-mobile.png", "alt": "Map of the sample parish", "caption": "A **local** map."},
                    {"file": "../secret.png", "alt": "Should be rejected", "caption": "Unsafe"},
                    {"file": "https://example.test/remote.png", "alt": "Should be rejected"},
                    {"file": "missing.png", "alt": "Should be rejected"},
                ],
            }],
        }
        dossier = {"id": "Example-1", "name": "Example Person", "vitals": {}}
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "research/Example-1/figures/map.png"
            source.parent.mkdir(parents=True)
            source.write_bytes(payload)
            source.with_name("map-mobile.png").write_bytes(b"narrow-image-bytes")
            web = root / "www"
            with (
                patch.object(renderer, "ROOT", root),
                patch.object(renderer, "WEB", web),
                patch("tools.repair_person_hierarchy._profile_data", return_value=(dossier, {}, {})),
                patch("tools.repair_person_hierarchy._editorial", return_value=editorial),
                patch("tools.repair_person_hierarchy._record_rows", return_value=[]),
                patch("tools.repair_person_hierarchy._record_source_map", return_value=({}, [])),
                patch("tools.repair_person_hierarchy._current_vitals", return_value={}),
                patch("tools.repair_person_hierarchy._family_html", return_value=""),
                patch("tools.repair_person_hierarchy._parent_comparison_html", return_value=""),
                patch("tools.repair_person_hierarchy._evidence_questions", return_value=""),
                patch("tools.repair_person_hierarchy._timeline_html", return_value=""),
                patch("tools.repair_person_hierarchy._research_html", return_value=""),
                patch("tools.repair_person_hierarchy._sources_html", return_value=""),
                patch("tools.repair_person_hierarchy._archive_html", return_value=""),
            ):
                soup = BeautifulSoup(renderer.render_person_dossier("Example-1"), "html.parser")
            figure = soup.select_one(".biography-section#early-records .biography-figure")
            self.assertIsNotNone(figure)
            self.assertEqual("Map of the sample parish", figure.img["alt"])
            self.assertIn("local", figure.select_one("figcaption").get_text())
            self.assertEqual(payload, (web / "assets/research/figures/example-1/map.png").read_bytes())
            self.assertEqual(b"narrow-image-bytes", (web / "assets/research/figures/example-1/map-mobile.png").read_bytes())
            self.assertEqual("(max-width:680px)", figure.select_one("picture source")["media"])
            self.assertEqual("Before the table.", figure.find_previous_sibling("p").get_text())
            self.assertEqual("After the figures.", figure.find_next_sibling("p").get_text())
            self.assertEqual(1, len(soup.select(".biography-figure")))
            self.assertNotIn("broken", soup.get_text().casefold())

    def test_opt_in_disclosure_preserves_authored_body_and_table(self):
        from tools.repair_person_hierarchy import render_person_dossier
        editorial = {"opening":"Assessment", "reading_mode":"authored", "reading_guide":{"mode":"summary-disclosures","hypothesis":"Hypothesis","current_answer":"Answer","groups":[{"id":"g","title":"Group","purpose":"Purpose","section_ids":["early"]}]}, "biography_sections":[{"id":"early","title":"Early","markdown":"Question\n\n| Year | Finding |\n| --- | --- |\n| 1841 | Present |","reading_summary":{"question":"What?","finding":"Present.","purpose":"Context."}}]}
        dossier={"id":"Example-1","name":"Example","vitals":{}}
        with patch("tools.repair_person_hierarchy._profile_data",return_value=(dossier,{},{})), patch("tools.repair_person_hierarchy._editorial",return_value=editorial), patch("tools.repair_person_hierarchy._record_rows",return_value=[]), patch("tools.repair_person_hierarchy._record_source_map",return_value=({},[])), patch("tools.repair_person_hierarchy._current_vitals",return_value={}), patch("tools.repair_person_hierarchy._family_html",return_value=""), patch("tools.repair_person_hierarchy._parent_comparison_html",return_value=""), patch("tools.repair_person_hierarchy._evidence_questions",return_value=""), patch("tools.repair_person_hierarchy._timeline_html",return_value=""), patch("tools.repair_person_hierarchy._research_html",return_value=""), patch("tools.repair_person_hierarchy._sources_html",return_value=""), patch("tools.repair_person_hierarchy._archive_html",return_value=""):
            soup=BeautifulSoup(render_person_dossier("Example-1"),"html.parser")
        self.assertEqual(1,len(soup.select(".biography-disclosure"))); self.assertIn("Present",soup.select_one(".biography-content").get_text()); self.assertIsNotNone(soup.select_one("table.biography-table"))

    def test_invalid_reading_guide_falls_back_without_crashing(self):
        from tools.repair_person_hierarchy import render_person_dossier
        dossier={"id":"Example-1","name":"Example","vitals":{}}
        for guide in ({"mode":"summary-disclosures","groups":[None]}, {"mode":"summary-disclosures","groups":[{"id":"g","title":"G","purpose":"P","section_ids":[{}]}]}):
            editorial={"opening":"Assessment","reading_mode":"authored","reading_guide":guide,"biography_sections":[{"id":"early","title":"Early","markdown":"Body"}]}
            with patch("tools.repair_person_hierarchy._profile_data",return_value=(dossier,{},{})), patch("tools.repair_person_hierarchy._editorial",return_value=editorial), patch("tools.repair_person_hierarchy._record_rows",return_value=[]), patch("tools.repair_person_hierarchy._record_source_map",return_value=({},[])), patch("tools.repair_person_hierarchy._current_vitals",return_value={}), patch("tools.repair_person_hierarchy._family_html",return_value=""), patch("tools.repair_person_hierarchy._parent_comparison_html",return_value=""), patch("tools.repair_person_hierarchy._evidence_questions",return_value=""), patch("tools.repair_person_hierarchy._timeline_html",return_value=""), patch("tools.repair_person_hierarchy._research_html",return_value=""), patch("tools.repair_person_hierarchy._sources_html",return_value=""), patch("tools.repair_person_hierarchy._archive_html",return_value=""):
                soup=BeautifulSoup(render_person_dossier("Example-1"),"html.parser")
            self.assertFalse(soup.select(".biography-disclosure")); self.assertIn("Body",soup.get_text())

    def test_compact_account_preserves_grouped_and_new_evidence(self):
        """New research stays reachable without invalidating the compact reading."""
        from tools.repair_person_hierarchy import render_person_dossier
        editorial = {
            "opening": "Current answer", "reading_mode": "authored",
            "reading_guide": {"mode": "compact-account", "hypothesis": "Hypothesis", "current_answer": "Answer",
                "account_sections": [{"id": "short-account", "title": "Family", "markdown": "Main evidence [original](https://example.test/original)."}],
                "groups": [{"id": "g", "title": "Household", "purpose": "Original records", "section_ids": ["early"]}]},
            "biography_sections": [{"id": ident, "title": ident.title(), "markdown": f"{ident} evidence\n\n| Year | Finding |\n| --- | --- |\n| 1841 | Present |",
                "reading_summary": {"question": "What?", "finding": "Present.", "purpose": "Context."}} for ident in ("early", "new")],
        }
        editorial["biography_sections"][1]["reading_summary"] = "A newly found record, with an unresolved identity."
        dossier = {"id": "Example-1", "name": "Example", "vitals": {}}
        with patch("tools.repair_person_hierarchy._profile_data", return_value=(dossier, {}, {})), patch("tools.repair_person_hierarchy._editorial", return_value=editorial), patch("tools.repair_person_hierarchy._record_rows", return_value=[]), patch("tools.repair_person_hierarchy._record_source_map", return_value=({}, [])), patch("tools.repair_person_hierarchy._current_vitals", return_value={}), patch("tools.repair_person_hierarchy._family_html", return_value=""), patch("tools.repair_person_hierarchy._parent_comparison_html", return_value=""), patch("tools.repair_person_hierarchy._evidence_questions", return_value=""), patch("tools.repair_person_hierarchy._timeline_html", return_value=""), patch("tools.repair_person_hierarchy._research_html", return_value=""), patch("tools.repair_person_hierarchy._sources_html", return_value=""), patch("tools.repair_person_hierarchy._archive_html", return_value=""):
            soup = BeautifulSoup(render_person_dossier("Example-1"), "html.parser")
        self.assertIsNone(soup.select_one("#short-account").find_parent("details"))
        self.assertIsNotNone(soup.select_one('#short-account a[href="https://example.test/original"]'))
        for ident in ("early", "new"):
            section = soup.select_one("#" + ident)
            self.assertTrue(section.find_parent("details"))
            self.assertFalse(section.select_one("details").has_attr("open"))
            self.assertIsNotNone(section.select_one("table.biography-table"))
        self.assertIsNotNone(soup.select_one("#reading-group-additional-evidence #new"))
        self.assertEqual(["#overview", "#short-account", "#full-research", "#archive-tools"], [a["href"] for a in soup.select(".dossier-toc a")])

    @requires_generated_data
    def test_acceptance_page_has_one_current_view_and_complete_documentary_list(self):
        soup = self.page("glasgow-951")
        main = soup.select_one("main")
        authored = json.loads((ROOT / "research/Glasgow-951/presentation.json").read_text())["biography_sections"]
        headings = [section.select_one("h2").get_text(" ", strip=True) for section in main.select(".dossier-reading > .dossier-section")]
        self.assertEqual(
            ["What we know", "Mary and the six children", "A life in records", "A small Antrim neighbourhood", "Why the 1888 death is probable", "The case for John Glasgow", "The Irish–Canadian family", "DNA and the Larne hypotheses", "What could change the answer?", "Connected pages", "Source notebook", "Sources"],
            headings,
        )
        for section in authored:
            visible = main.select_one("#" + section["id"])
            self.assertIsNotNone(visible)
            self.assertIsNotNone(visible.find_parent("details"))
            self.assertFalse(visible.find_parent("details").has_attr("open"))
            self.assertIsNone(visible.select_one(".biography-disclosure"))
        self.assertEqual(0, sum(text.casefold() == "current conclusion" for text in headings))
        records = main.select_one("#timeline")
        collateral = BeautifulSoup("".join(str(row) for row in main.select('.timeline-row[data-group="Collateral records"]')), "html.parser")
        historical = main.select("#timeline .timeline-row")
        source_rows = json.loads((ROOT / "www/people/glasgow-951.json").read_text())["presentation"]["record_associations"]
        historical_ids = {row["record_id"] for row in source_rows if not row["record_id"].startswith("correspondence")}
        self.assertTrue(historical_ids.issubset({row.get("id", "").removeprefix("timeline-") for row in historical}))
        self.assertNotIn("Y-DNA", records.get_text() + collateral.get_text())
        self.assertIn("reported autosomal connection", main.get_text())
        self.assertIn("Unnamed Glasgow child baptism", records.get_text())
        self.assertIn("Daniel Glasgow will", collateral.get_text())
        self.assertIn("Daniel Neely Glasgow and Mary Jane Boyd marriage", collateral.get_text())
        for ident in ("family", "evidence", "parent-candidates", "timeline", "research"):
            self.assertEqual("archive-tools", main.select_one("#" + ident).find_parent(id="archive-tools")["id"])
        self.assertFalse(main.select("#next-research .candidate-score"))

    @requires_generated_data
    def test_family_diagram_retains_each_child_account_and_uncertainty(self):
        """Visual connections preserve the table's facts, profile links and limits."""
        from tools.repair_person_hierarchy import _biography_sections_html
        source = json.loads((ROOT / "research/Glasgow-951/presentation.json").read_text())
        section = next(item for item in source["reading_guide"]["account_sections"] if item["id"] == "family-account")
        original = BeautifulSoup(_biography_sections_html("Glasgow-951", {"biography_sections": [section]}, set())[0][2], "html.parser")
        diagram = self.page("glasgow-951").select_one("#family-account .account-family-map")
        rows = original.select("tbody tr")
        children = diagram.select(".family-children > li")
        self.assertEqual(6, len(children))
        for row, child in zip(rows, children):
            self.assertEqual(row.get_text(" ", strip=True), child.get_text(" ", strip=True))
            self.assertEqual([a["href"] for a in row.select("a")], [a["href"] for a in child.select("a")])
        self.assertIn("three were at home in 1851", diagram.figcaption.get_text())
        self.assertIn("Michigan identification is unproved", diagram.get_text())
        self.assertNotIn("Glasgow-4090", diagram.get_text())
        trail = self.page("glasgow-951").select_one("#record-trail")
        self.assertEqual(["1834", "1836", "1851", "1871", "1888"], [n.get_text() for n in trail.select(".trail-year")])
        self.assertIn("probable, not proved", trail.get_text())
        self.assertIn("relationship is unknown", trail.get_text())
        self.assertTrue(all(node.select_one("a[href]") for node in trail.select("li")))

    @requires_generated_data
    def test_important_arguments_are_visible_outside_the_source_notebook(self):
        """The default account must explain the research, rather than hide its findings."""
        soup = self.page("glasgow-951")
        account = soup.select(".account-section")
        self.assertTrue(account)
        for section in account:
            self.assertIsNone(section.find_parent("details"))
            self.assertFalse(section.select("details"))
            self.assertNotIn("{{visuals}}", section.get_text())
        self.assertEqual(1, len(soup.select(".supporting-research details")))
        self.assertEqual(17, len(soup.select("#source-notebook .biography-section")))
        self.assertTrue(soup.select_one('#places-account img[src$="/places.svg"]'))
        self.assertEqual(3, len(soup.select("#parents-account .visual-chain li")))
        self.assertEqual(3, len(soup.select("#parents-account .visual-cards li")))
        self.assertEqual(4, len(soup.select("#death-account .visual-chain li")))
        self.assertIn("1811", soup.select_one("#death-account .visual-cards").get_text())
        self.assertIn("1804", soup.select_one("#death-account .visual-cards").get_text())
        connections = soup.select_one("#connections-account")
        self.assertIn("historical men were not themselves tested", soup.select_one("#dna-account").get_text())
        self.assertIn("Alexander is not connected to them by these records", connections.get_text())
        for node in soup.select("#parents-account .visual-chain li, #death-account .visual-chain li"):
            self.assertTrue(node.select_one("a[href]"))

    @requires_generated_data
    def test_guided_account_exposes_source_readings_with_provenance(self):
        """A reader can inspect each claim and distinguish a record from an inference."""
        soup = self.page("glasgow-951")
        steps = soup.select(".account-journey a")
        self.assertEqual(["#family-account", "#places-account", "#parents-account"], [a["href"] for a in steps])
        snippets = soup.select(".account-section .source-snippet")
        self.assertEqual(6, len(snippets))
        for snippet in snippets:
            ident = snippet["data-excerpt"]
            original = soup.select_one("#excerpt-" + ident)
            self.assertIsNotNone(original)
            self.assertEqual(original.select_one(".record-stage img")["src"], snippet.img["src"])
            self.assertEqual(original.select_one(".record-provenance a")["href"], snippet.select_one(".snippet-source a")["href"])
            self.assertIsNone(snippet.find_parent("details"))
            self.assertTrue(snippet.select_one(".snippet-label").get_text())
            self.assertTrue(snippet.select_one(".snippet-reading").get_text())
            self.assertFalse(snippet.select("[id]"))
        death = soup.select_one("#death-account")
        self.assertIn("upper row", death.select_one('[data-excerpt="robert1866-marriage"]').get_text())
        self.assertIn("lower row", death.select_one('[data-excerpt="ann1876-marriage"]').get_text())
        self.assertIn("does not establish the deceased’s identity", death.get_text())
        self.assertIn("Mary Glasgow", death.select_one('[data-excerpt="alex1888-informant"] blockquote').get_text())
        self.assertIn("The 1888 informant reads Mary Glasgow, daughter", death.get_text())
        self.assertIn("names no relatives or Irish birthplace", soup.select_one('[data-excerpt="nancy1891-death"] .snippet-reading').get_text())
        for section in soup.select(".account-section"):
            self.assertNotIn("{{snippets:", section.get_text())
        self.assertEqual(6, len(soup.select(".account-transition")))

    def test_source_snippets_cannot_preview_withheld_records(self):
        from tools.repair_person_hierarchy import _account_snippets
        block = {"id": "test", "items": [{"excerpt_id": "withheld", "title": "Record", "quote": "A name", "quote_label": "Transcribed fields", "reading": "An interpretation"}]}
        with patch("tools.repair_person_hierarchy._record_excerpt_html", return_value='<p class="record-withheld">Record withheld</p>'):
            rendered = _account_snippets('<p>{{snippets:test}}</p>', [block], "Example-1")
        self.assertNotIn("A name", rendered)
        self.assertNotIn("source-snippet", rendered)
        self.assertNotIn("{{snippets:", rendered)

    @requires_generated_data
    def test_estate_diagram_distinguishes_recorded_kin_words_from_sibling_inference(self):
        soup = self.page("glasgow-951")
        diagram = soup.select_one("#parents-account .visual-kinship")
        self.assertEqual(["niece", "nephew"], [q.get_text() for q in diagram.select("q")])
        parents = diagram.select(".kin-parent")
        self.assertIn("Jane Glascaw", parents[0].get_text())
        self.assertIn("Betty Glascaw", parents[1].get_text())
        self.assertTrue(all(p.select_one('a[href*="Baptisms_1834"]') for p in parents))
        note = diagram.select_one(".visual-note").get_text()
        self.assertIn("probably Nancy’s sisters", note)
        self.assertIn("do not state full siblinghood", note)
        self.assertIn("named transcriptions", note)
        account = soup.select_one("#parents-account .biography-content")
        self.assertLess(str(account).index('visual-kinship'), str(account).index('visual-chain'))
        self.assertEqual(3, len(account.select(".theory-test")))
        self.assertNotIn("{{visuals", account.get_text())
        self.assertIsNone(diagram.find_parent("details"))

    @requires_generated_data
    def test_census_strip_keeps_household_order_separate_from_a_pedigree(self):
        diagram = self.page("glasgow-951").select_one("#places-account .visual-households")
        self.assertEqual(["House 34", "House 35", "House 36", "House 37"], [label.get_text() for label in diagram.select(".evidence-state")])
        self.assertEqual("The Watters household", diagram.select("li h3")[2].get_text())
        self.assertIn("Brothers explicitly recorded", diagram.select("li")[0].get_text())
        self.assertIn("does not call Alexander their brother", diagram.select_one(".visual-note").get_text())
        self.assertIn("not a property map or pedigree", diagram.figcaption.get_text())
        self.assertIsNone(diagram.find_parent("details"))

    @requires_generated_data
    def test_folded_studies_have_visible_material_findings_and_qualifications(self):
        """Important unresolved identities and adverse evidence cannot live only in a notebook."""
        soup = self.page("glasgow-951")
        expected = {
            "family-account": ["baggage agent", "County Antrim", "names neither Alexander nor Mary", "Samuel Elder", "Samuel Glasgow", "no father named", "no death or burial has been found"],
            "places-account": ["Archibald", "Cath Quinn", "CR5/32A/1", "has not been inspected"],
            "death-account": ["Glenleslie", "72", "118", "1882", "weaker but not excluded", "The 1888 informant reads Mary Glasgow, daughter"],
            "parents-account": ["1829", "59", "land section supplies no occupier names", "Plantation measure", "14–15", "7–8"],
            "connections-account": ["express agent of Rochester", "James Glasco", "Eliza Jane", "Thomasina Montgomery", "John Black", "Mary Anne", "1875", "1900–09", "neither the fractions nor the common name"],
            "dna-account": ["genetic distance 3 at Y-111", "FT6135", "Untested", "two missing relationships", "1760", "1762", "only 12", "John Glasgow, farmer"],
            "next-checks-account": ["Ann McClelland", "644/2/849", "28 April 1894", "uninspected", "independent evidence"],
        }
        for ident, phrases in expected.items():
            section = soup.select_one("#" + ident)
            self.assertIsNone(section.find_parent("details"))
            self.assertFalse(section.select("details"))
            text = section.get_text(" ", strip=True).casefold()
            for phrase in phrases:
                self.assertIn(phrase.casefold(), text, (ident, phrase))
        paths = soup.select("#family-account .evidence-path")
        self.assertEqual(3, len(paths))
        self.assertTrue(all(path.select_one('.path-continuation[data-state]') for path in paths))
        guide = json.loads((ROOT / "research/Glasgow-951/presentation.json").read_text())["reading_guide"]
        source_ids = {section["id"] for section in json.loads((ROOT / "research/Glasgow-951/presentation.json").read_text())["biography_sections"]}
        self.assertEqual(source_ids, set(guide["visible_coverage"]))
        self.assertTrue(all(soup.select_one('#' + ident + '.account-section') for ids in guide["visible_coverage"].values() for ident in ids))

    @requires_generated_data
    def test_property_shares_compare_equal_units_without_counting_children(self):
        diagram = self.page("glasgow-951").select_one(".visual-shares")
        self.assertEqual([18, 18], [len(strip.select('.share-unit')) for strip in diagram.select('.share-strip')])
        self.assertEqual([3, 4], [len(strip.select('.share-filled')) for strip in diagram.select('.share-strip')])
        self.assertEqual(["3 of 18 equal parts", "4 of 18 equal parts"], [strip["aria-label"] for strip in diagram.select('.share-strip')])
        self.assertIn("no complete child count follows", self.page("glasgow-951").select_one('#connections-account').get_text())

    @requires_generated_data
    def test_relationship_qualifiers_and_links_are_preserved(self):
        soup = self.page("glasgow-951")
        family = soup.select_one("#family")
        james = family.select("a[href='/people/glasgow-973.html'], a[href='/people/glasgow-3939.html']")
        self.assertEqual(2, len(james))
        unknown = family.select_one("a[href='/people/glasgow-3940.html']")
        self.assertIsNotNone(unknown)
        unknown_row = unknown.find_parent("tr")
        self.assertIn("entry 106", unknown_row.get_text().casefold())
        self.assertEqual("Documented child", unknown_row.select_one(".status-label").get_text())
        self.assertTrue(unknown_row.select_one("a[href^='#source-']"))
        self.assertIn("superseded", family.get_text().casefold())
        self.assertIn("Rosanna (surname unknown)", family.get_text())
        self.assertIn("Thomas Glasgow", family.get_text())
        self.assertIn("Daniel Glasgow", family.get_text())
        for link in soup.select("a[href]"):
            self.assertNotIn("/people/people/", link["href"])

    @requires_generated_data
    def test_sources_backlink_and_archive_boundary(self):
        soup = self.page("glasgow-951")
        from tools.repair_person_hierarchy import _record_rows
        self.assertEqual(len(_record_rows("Glasgow-951")), len(soup.select("#sources .source-register > li")))
        self.assertTrue(any("Correspondence summary" in item.get_text() for item in soup.select("#sources .source-register > li")))
        self.assertTrue(all(item.select_one(".source-links") for item in soup.select("#sources .source-register > li")))
        reading = soup.select_one(".dossier-reading")
        archive = reading.select_one("#archive-tools")
        archive_text = archive.get_text() if archive else ""
        archive.decompose()
        # The restored comparison deliberately exposes native WikiTree text;
        # it is an editing tool, separate from the prose research account.
        for panel in reading.select("#wikitree-update"):
            panel.decompose()
        visible_text = reading.get_text(" ", strip=True)
        self.assertNotIn("[[Glasgow-", visible_text)
        self.assertNotIn("<ref", visible_text)
        self.assertIn("[[", archive_text)

    @requires_generated_data
    def test_record_level_explanations_and_thomas_bridge_are_specific(self):
        soup = self.page("glasgow-951")
        identity = soup.select_one("#question-identity")
        reasons = [row.select("td")[2].get_text(" ", strip=True) for row in identity.select("tbody tr")]
        self.assertGreaterEqual(len(set(reasons)), 4)
        limitations = " ".join(row.select("td")[3].get_text(" ", strip=True) for row in identity.select("tbody tr"))
        self.assertNotIn("Original census record", limitations)
        self.assertIn("tenancy continuity", identity.get_text().casefold())
        thomas = soup.select_one("#question-thomas-network")
        titles = [row.select_one("strong").get_text(" ", strip=True) for row in thomas.select("tbody tr")]
        self.assertIn("Daniel Glasgow will, proved 1871", titles)
        self.assertIn("Daniel Neely Glasgow and Mary Jane Boyd marriage", titles)
        self.assertIn("does not state how Alexander is related", thomas.get_text())

    @requires_generated_data
    def test_dates_relationships_and_actions_use_shared_maintained_model(self):
        target = self.page("glasgow-951")
        child = self.page("glasgow-3167")
        james = self.page("glasgow-3939")
        self.assertIn("after 17 February 1892", target.select_one("#family").get_text())
        self.assertIn("before 1841", target.select_one("#family").get_text())
        self.assertIn("before 1841", james.select_one(".dossier-life").get_text())
        target_row = target.select_one("#family a[href='/people/glasgow-3167.html']").find_parent("tr")
        child_row = child.select_one("#family a[href='/people/glasgow-951.html']").find_parent("tr")
        self.assertIn("Documented daughter", target_row.get_text())
        self.assertIn("Documented father", child_row.get_text())
        for soup in (target, child, james):
            for action in soup.select(".dossier-actions a"):
                self.assertFalse(action.get("href", "").endswith(".json"))
                self.assertNotIn("network.json", action.get("href", ""))

    @requires_generated_data
    def test_resolved_research_is_not_rendered_as_missing(self):
        for slug in ("glasgow-951", "glasgow-3167", "glasgow-987", "glasgow-1367"):
            text = self.page(slug).select_one("#overview").get_text(" ", strip=True)
            self.assertNotIn("No maintained assessment is recorded", text)
        for slug in ("glasgow-3939", "mccaughan-222"):
            text = self.page(slug).select_one("#overview").get_text(" ", strip=True)
            self.assertNotIn("assessment status", text.casefold())
            self.assertNotIn("not yet mapped", text.casefold())

    @requires_generated_data
    def test_reciprocal_roles_dates_and_current_corrections(self):
        target = self.page("glasgow-951")
        child = self.page("glasgow-3167")
        target_row = target.select_one("#family a[href='/people/glasgow-3167.html']").find_parent("tr")
        child_row = child.select_one("#family a[href='/people/glasgow-951.html']").find_parent("tr")
        self.assertIn("Documented daughter", target_row.get_text())
        self.assertIn("Documented father", child_row.get_text())
        self.assertIn("after 17 February 1892", target.get_text())
        self.assertIn("before 1841", target.get_text())
        self.assertIn("Superseded acreage near-equality interpretation", target.select_one("#archive-tools").get_text())
        self.assertNotIn("64-to-63-acre comparison", target.select_one("#evidence").get_text())
        children = target.select("#family .relation-group:nth-of-type(2) tbody tr")
        years = [next(iter(re.findall(r"\b(\d{4})\b", row.select_one("td").get_text(" ", strip=True))), "9999") for row in children]
        self.assertEqual(sorted(years), years)

    @requires_generated_data
    def test_linked_current_accounts_and_source_backlinks(self):
        pages = {slug: self.page(slug) for slug in ("glasgow-3167", "glasgow-987", "glasgow-1367", "glasgow-3939", "mccaughan-222")}
        self.assertIn("1871 Lisnagaver bride", pages["glasgow-3167"].select_one("#overview").get_text())
        self.assertIn("named Alexander Glasgow, farmer, as her father", pages["glasgow-3167"].select_one("#overview").get_text())
        self.assertIn("Daniel Glasgow will", pages["glasgow-987"].get_text())
        self.assertIn("Daniel Neely Glasgow and Mary Jane Boyd marriage", pages["glasgow-987"].get_text())
        self.assertIn("working profile scope", pages["glasgow-1367"].select_one("#overview").get_text())
        for soup in pages.values():
            self.assertEqual(1, len(soup.select('link[href^="/assets/repair/person-hierarchy.css"]')))
            anchors = {f"#{node.get('id')}" for node in soup.select("[id]") if node.get("id")}
            for link in soup.select("a[href^='#']"):
                target = link.get("href")
                if target and target != "#":
                    self.assertIn(target, anchors, (soup.select_one("h1").get_text(strip=True), target))

    @requires_generated_data
    def test_source_specific_semantics_are_not_generic_fillers(self):
        soup = self.page("glasgow-951")
        identity = soup.select_one("#question-identity")
        rows = identity.select("tbody tr")
        reasons = [row.select("td")[2].get_text(" ", strip=True) for row in rows]
        self.assertGreaterEqual(len(set(reasons)), 4)
        self.assertNotIn("Original census record", " ".join(row.select("td")[3].get_text(" ", strip=True) for row in rows))
        thomas = soup.select_one("#question-thomas-network")
        titles = [row.select_one("strong").get_text(" ", strip=True) for row in thomas.select("tbody tr")]
        self.assertIn("Daniel Glasgow will, proved 1871", titles)
        self.assertIn("Daniel Neely Glasgow and Mary Jane Boyd marriage", titles)
        self.assertTrue(soup.select_one("#source-will-daniel-1871 a[href^='#record-will-daniel-1871']"))

    @requires_generated_data
    def test_source_urls_and_wikitree_export_are_preserved(self):
        soup = self.page("glasgow-951")
        self.assertTrue(soup.select_one("#source-baptism-james-1837"))
        self.assertTrue(soup.select_one("#source-baptism-unnamed-1838"))
        self.assertTrue(soup.select_one("#source-will-daniel-1871"))
        self.assertTrue(soup.select_one("#source-marriage-daniel-neely-1888"))
        archive = soup.select_one("#archive-tools")
        reading_copy = soup.select_one(".dossier-reading")
        archive_copy = archive.get_text(" ", strip=True)
        reading_copy_copy = BeautifulSoup(str(reading_copy), "html.parser")
        reading_copy_copy.select_one("#archive-tools").decompose()
        for panel in reading_copy_copy.select("#wikitree-update"):
            panel.decompose()
        self.assertNotIn("[[Glasgow-", reading_copy_copy.get_text())
        self.assertNotIn("<ref", reading_copy_copy.get_text())
        dossier = json.loads((ROOT / "www/people/glasgow-951.json").read_text())
        draft = (dossier.get("wikitree_update") or {}).get("draft_wikitext") or ""
        textarea = soup.select_one("#profile-update-draft") or archive.select_one("textarea")
        if draft:
            self.assertEqual(draft, textarea.get_text())
        self.assertIn("p29041.htm#i290407", str(archive))
        self.assertIn("Baptisms_1834.html", str(archive))

    @requires_generated_data
    def test_sparse_and_linked_pages_use_the_same_safe_shell(self):
        for slug in ("glasgow-973", "glasgow-3940"):
            soup = self.page(slug)
            self.assertIsNotNone(soup.select_one(".dossier-header"))
            self.assertIsNotNone(soup.select_one("#overview"))
            self.assertIn("g-unified", soup.body.get("class", []))
            self.assertIsNotNone(soup.select_one("#g-navigation.g-rail"))
            self.assertIsNotNone(
                soup.select_one('.g-nav-link[href="/catalogue/"][aria-current="page"]')
            )
            self.assertIsNotNone(
                soup.select_one(
                    'link[href^="assets/unified/site.css"], '
                    'link[href^="/assets/unified/site.css"]'
                )
            )
            self.assertFalse("/people/people/" in str(soup))
            for section in soup.select(".dossier-section"):
                self.assertTrue(section.get_text(" ", strip=True))

    @requires_generated_data
    def test_samuel_original_records_preserve_unexplained_surname_conflict(self):
        soup = self.page("glasgow-3167")
        archive = soup.select_one("#archive-tools")
        archive.extract()
        # The WikiTree editing panel quotes the live WikiTree biography (which
        # the prepared draft corrects); it is not the page's research account.
        for panel in soup.select("#wikitree-update"):
            panel.decompose()
        current = soup.get_text(" ", strip=True)
        self.assertIn("Samuel Glasgow", current)
        self.assertIn("Samuel Elder civil birth return", current)
        self.assertIn("original register records Samuel Elder", current)
        self.assertIn("original 1911 form independently records the child as Samuel Glasgow", current)
        self.assertIn("unexplained conflict between original records", current)
        self.assertIn("does not identify Samuel's father", current)
        self.assertIn("records no Glasgow name", current)
        self.assertNotIn("Glasgow was his middle name", current)
        presentation = (ROOT / "research/Glasgow-3167/presentation.json").read_text(encoding="utf-8")
        self.assertIn("birth-samuel-1908", presentation)

    @requires_generated_data
    def test_jane_elder_birth_resolves_identity_and_census_age_conflict(self):
        soup = self.page("glasgow-3167")
        current = soup.get_text(" ", strip=True)
        self.assertIn("Jane Matilda Elder civil birth return", current)
        self.assertIn("16 September 1878", current)
        self.assertIn("maiden surname is entered as Glass", current)
        self.assertIn("identify the later Jane M. Elder", current)
        self.assertIn("1911 age is too low", current)
        self.assertTrue(soup.select_one("#source-birth-jane-elder-1878"))

    @requires_generated_data
    def test_claim_level_correction_does_not_mark_archive_sections_superseded(self):
        for slug, correction_id in (("glasgow-951", "correction-acreage-subdivision"), ("glasgow-1367", "correction-acreage-near-match")):
            soup = self.page(slug)
            correction = soup.select_one(f"#{correction_id}")
            self.assertIsNotNone(correction)
            self.assertIn("Rejected interpretation", correction.get_text())
            self.assertIn("Operative correction", correction.get_text())
            self.assertIn("Unaffected", correction.get_text())
            self.assertNotIn("superseded", correction.find_parent("details").select_one("summary").get_text().casefold())
        self.assertNotIn("64-to-63-acre comparison", self.page("glasgow-951").select_one("#evidence").get_text())

    @requires_generated_data
    def test_reviewed_relationships_are_reciprocal_and_record_backed(self):
        thomas = self.page("glasgow-987")
        daniel = thomas.select_one("#family a[href='/people/glasgow-3896.html']").find_parent("tr")
        neely = thomas.select_one("#family a[href='/people/glasgow-2413.html']").find_parent("tr")
        sarah = thomas.select_one("#family a[href='/people/glasgow-3975.html']").find_parent("tr")
        self.assertIn("Documented sibling", daniel.get_text())
        self.assertIn("will", daniel.get_text().casefold())
        self.assertIn("Documented son", neely.get_text())
        self.assertIn("marriage", neely.get_text().casefold())
        self.assertIn("Documented daughter", sarah.get_text())
        self.assertIn("1885", sarah.get_text())
        self.assertTrue(thomas.select_one("#source-marriage-sarah-1885"))
        mary = self.page("glasgow-3167")
        spouse = mary.select_one("#family a[href='/people/elder-7251.html'], #family a[href='https://www.wikitree.com/wiki/Elder-7251']").find_parent("tr")
        self.assertIn("Documented spouse", spouse.get_text())
        self.assertIn("source-marriage-mary-1871", str(spouse))
        reverse = self.page("glasgow-3896").select_one("#family a[href='/people/glasgow-987.html']").find_parent("tr")
        self.assertIn("Documented sibling", reverse.get_text())

    @requires_generated_data
    def test_shared_canonical_records_populate_sparse_source_registers(self):
        mccaughan = self.page("mccaughan-222")
        james = self.page("glasgow-3939")
        self.assertTrue(mccaughan.select_one("#source-death-mary-1892"))
        self.assertIn("Mary Glasgow civil death register", mccaughan.select_one("#sources").get_text())
        self.assertTrue(james.select_one("#source-baptism-james-1837"))
        self.assertIn("Rasharkin entry 75", james.select_one("#sources").get_text())
        for soup in (mccaughan, james):
            for link in soup.select(".source-links a[href^='#']"):
                self.assertIsNotNone(soup.select_one(link["href"]))

    @requires_generated_data
    def test_existing_letter_generates_remaining_examination_task(self):
        soup = self.page("glasgow-951")
        research = soup.select_one("#research").get_text(" ", strip=True)
        letter = next(
            item for item in json.loads((ROOT / "research/Glasgow-951/presentation.json").read_text(encoding="utf-8"))["completed_searches"]
            if item["search"] == "John Glasgow family Bible and 1847 letter"
        )
        self.assertIn("inspected with the letter", letter["result"])
        self.assertIn("retrieval task is complete", letter["result"])
        self.assertIn(letter["search"], research)
        self.assertIn(letter["result"], research)
        self.assertNotRegex(research, r"\b(?:obtain|acquire)\b.{0,120}\b(?:letter|20 March 1847)\b")
        self.assertNotIn("Obtain and read the original 20 March 1847", research)

    @requires_generated_data
    def test_identity_limitations_do_not_require_modern_profile_ids(self):
        for slug in ("glasgow-3939", "mccaughan-222"):
            soup = self.page(slug)
            limitations = " ".join(cell.get_text(" ", strip=True) for cell in soup.select(".question td:nth-child(4)"))
            self.assertNotIn("profile identifier", limitations.casefold())
            self.assertNotIn("WikiTree profile", limitations)
        self.assertNotIn("One-Tree export profile fields", self.page("glasgow-3939").get_text())

    @requires_generated_data
    def test_person_specific_record_roles_and_no_duplicate_occurrence(self):
        alexander = self.page("glasgow-951")
        mary = self.page("mccaughan-222")
        alexander_death = alexander.select_one("#timeline-death-alexander-1888")
        self.assertEqual("Subject", alexander_death.select_one(".timeline-role").get_text(strip=True))
        mary_death = mary.select_one("#timeline-death-mary-1892")
        self.assertEqual("Subject", mary_death.select_one(".timeline-role").get_text(strip=True))
        self.assertEqual(1, len(mary.select("#timeline-death-mary-1892")))
        self.assertEqual(1, len(mary.select("#source-death-mary-1892")))
        collateral = alexander.select_one("#timeline-death-mary-1892")
        self.assertEqual("Collateral records", collateral["data-group"])
        self.assertIn("Record of the presumed spouse's death", collateral.get_text())
        self.assertNotIn("Subject", collateral.get_text())

    @requires_generated_data
    def test_ranges_sort_by_normalised_start_year(self):
        soup = self.page("glasgow-951")
        records = soup.select_one("#timeline")
        titles = [row.select_one("h3").get_text(" ", strip=True) for row in records.select(".timeline-row")]
        self.assertLess(titles.index("Griffith's Valuation: Alexander at Lisnagaver"), titles.index("Lisnagaver household 35 census return"))
        self.assertLess(titles.index("Lisnagaver household 35 census return"), titles.index("PRONI valuation revision books, Lisnagaver lot 25"))

    @requires_generated_data
    def test_robert_scope_remains_explicitly_unresolved(self):
        soup = self.page("glasgow-1367")
        text = soup.select_one("#overview").get_text(" ", strip=True)
        self.assertIn("working profile scope", text)
        self.assertIn("No record yet bridges those identities", text)
        self.assertIn("proves that the 1834 Lisnagaver, 1825 Doonbought and 1851 Glenleslie entries concern one man", soup.get_text(" ", strip=True))


if __name__ == "__main__":
    unittest.main()
