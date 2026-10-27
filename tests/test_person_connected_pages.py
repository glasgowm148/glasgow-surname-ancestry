"""Person pages, second pass (site audit I7): connected pages, labels, anchors, breadcrumb, date note."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from bs4 import BeautifulSoup

import tools.repair_person_hierarchy as renderer
from tools import dossier_resolution


def _findings(*sections, updated="2026-10-07"):
    return [{"profile_id": "Glasgow-1", "updated": updated, "source_path": "research/Glasgow-1/findings.md",
             "sections": [{"title": title, "category": category, "markdown": markdown} for title, category, markdown in sections]}]


def _links(**values):
    base = {"studies": [], "places": [], "sources": [], "sources_total": 0, "findings": [], "research": [], "mentioned_by": []}
    base.update(values)
    return base


SMALL = _links(
    studies=[{"title": "Family group: Ann Glasgow · c. 1800", "url": "/branches/family-glasgow-1/"}],
    places=[{"title": "Lisnagaver townland", "url": "/places/lisnagaver.html"}],
    sources=[{"title": "1851 census", "url": "/sources/s-1/"}], sources_total=1,
    findings=[{"date": "2026-10-06", "title": "A finding.", "url": "/latest-findings/#finding-a"}],
)


def _mentions(count, name="John Glasgow", ident="Glasgow-9", sections=1):
    rows = []
    for number in range(count):
        for section in range(sections):
            rows.append({"id": f"{ident}{number}", "name": name, "section": f"Source findings {section}",
                         "url": f"/people/{ident.casefold()}{number}.html#research-note-{number:04d}{section}"})
    return rows


class ConnectedPagesTests(unittest.TestCase):
    def render(self, links, **kwargs):
        with patch.object(renderer, "_person_links", return_value=links):
            html = renderer._connected_pages_html("Glasgow-1", {"id": "Glasgow-1", "name": "Ann Glasgow"}, **kwargs)
        return html, BeautifulSoup(html, "html.parser")

    def test_nothing_when_the_index_has_nothing(self):
        self.assertEqual("", self.render(_links())[0])
        self.assertEqual("", self.render({})[0])

    def test_small_block_is_open_with_neutral_labels(self):
        _, soup = self.render(SMALL)
        block = soup.select_one("section#connected-pages")
        self.assertEqual("Connected pages", block.h2.get_text())
        groups = block.select("details.connected-group")
        self.assertEqual(["studies", "places", "sources", "findings"], [group["data-group"] for group in groups])
        self.assertTrue(all("open" in group.attrs for group in groups))
        self.assertEqual("Family and study pages 1 page", groups[0].summary.get_text(" ", strip=True))
        # Family-group pages come from member lists: no caution note.
        self.assertIsNone(groups[0].select_one(".connected-note"))
        self.assertEqual("/places/lisnagaver.html", groups[1].a["href"])
        self.assertEqual("6 October 2026", groups[3].time.get_text())
        self.assertEqual("2026-10-06", groups[3].time["datetime"])
        self.assertIn("Ann Glasgow", block.select_one(".connected-intro").get_text())

    def test_study_pages_get_a_caution_and_sources_a_total(self):
        links = _links(studies=[{"title": "Larne & Kilwaughter", "url": "/branches/larne-kilwaughter/"}],
                       sources=[{"title": f"Source {n}", "url": f"/sources/s-{n}/"} for n in range(10)], sources_total=48)
        _, soup = self.render(links, has_sources=True)
        studies, sources = soup.select("details.connected-group")
        self.assertIn("without placing them in that family", studies.select_one(".connected-note").get_text())
        self.assertEqual("Sources 48 source pages", sources.summary.get_text(" ", strip=True))
        note = sources.select_one(".connected-note")
        self.assertIn("The first 10 of 48 source pages are listed here.", note.get_text())
        self.assertEqual("#sources", note.a["href"])
        more = sources.select_one("details.connected-more")
        self.assertEqual("Show 5 more source pages", more.summary.get_text())
        self.assertEqual(10, len(sources.select("a[href^='/sources/']")))
        _, soup = self.render(links, has_sources=False)
        self.assertIsNone(soup.select_one(".connected-note a"))

    def test_one_extra_item_is_shown_rather_than_hidden(self):
        links = _links(sources=[{"title": f"Source {n}", "url": f"/sources/s-{n}/"} for n in range(6)], sources_total=6)
        _, soup = self.render(links)
        self.assertIsNone(soup.select_one("details.connected-more"))
        self.assertEqual(6, len(soup.select(".connected-list li")))

    def test_mentions_are_grouped_by_person_and_large_blocks_collapse(self):
        rows = _mentions(1, sections=3) + _mentions(1, ident="Glasgow-8") + _mentions(14, name="Mary Hill", ident="Hill-")
        _, soup = self.render(_links(mentioned_by=rows, **{k: v for k, v in SMALL.items() if k != "mentioned_by"}))
        groups = soup.select("details.connected-group")
        self.assertTrue(all("open" not in group.attrs for group in groups))
        self.assertIn("Open a group", soup.select_one(".connected-intro").get_text())
        mentions = soup.select_one('details[data-group="mentioned_by"]')
        self.assertEqual("Mentioned in other people's research 16 people", mentions.summary.get_text(" ", strip=True))
        links = mentions.select(".connected-list a")
        self.assertEqual(16, len(links))
        first = links[0]
        # Three sections: one link to the research section, the section titles as its tooltip.
        self.assertEqual("/people/glasgow-90.html#research-findings", first["href"])
        self.assertEqual("John Glasgow (Glasgow-90)", first.get_text())
        self.assertIn("Source findings 0; Source findings 1", first["title"])
        self.assertEqual("3 sections of notes", first.find_next_sibling("small").get_text())
        single = mentions.find("a", string="John Glasgow (Glasgow-80)")
        self.assertEqual("/people/glasgow-80.html#research-note-00000", single["href"])
        self.assertEqual("Show 8 more people", mentions.select_one("details.connected-more summary").get_text())


class RenderedPageTests(unittest.TestCase):
    def render(self, dossier, links):
        editorial = dossier_resolution.resolve_presentation("Glasgow-1", dossier, {})
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
            patch.object(renderer, "_profile_update_panel", return_value=""),
            patch.object(renderer, "_person_links", return_value=links),
        ):
            return BeautifulSoup(renderer.render_person_dossier("Glasgow-1"), "html.parser")

    def test_block_sits_after_the_overview_with_a_menu_entry_and_no_in_page_crumb(self):
        dossier = {"id": "Glasgow-1", "name": "Ann Glasgow", "vitals": {}, "relationships": {},
                   "research_findings": _findings(("Source findings", "sources", "A record."))}
        soup = self.render(dossier, SMALL)
        order = [child.get("id") for child in soup.select_one(".dossier-reading").find_all(recursive=False)]
        self.assertEqual(order.index("overview") + 1, order.index("connected-pages"))
        self.assertIn("#connected-pages", [a["href"] for a in soup.select(".dossier-nav a")])
        self.assertIn("#connected-pages", [a["href"] for a in soup.select(".dossier-toc a")])
        self.assertIsNone(soup.select_one("nav.crumb"))

    def test_no_block_and_no_menu_entry_without_links(self):
        dossier = {"id": "Glasgow-1", "name": "Ann Glasgow", "vitals": {}, "relationships": {}, "research_findings": []}
        soup = self.render(dossier, _links())
        self.assertIsNone(soup.select_one("#connected-pages"))
        self.assertNotIn("#connected-pages", [a["href"] for a in soup.select(".dossier-nav a")])

    def test_old_fragment_ids_still_land(self):
        dossier = {"id": "Glasgow-1", "name": "Ann Glasgow", "vitals": {}, "relationships": {},
                   "research_findings": _findings(("Source findings", "sources", "A record."))}
        soup = self.render(dossier, _links())
        self.assertEqual("research-findings", soup.find(id="research").find_parent("section")["id"])
        self.assertEqual("family", soup.find(id="imported-identity").find_parent("section")["id"])
        self.assertEqual(1, len(soup.select("#research")))

    def test_headline_note_when_the_research_recommends_other_dates(self):
        correction = "**Birth: before about 1679** (a boundary, not an estimate).\n\nThese are proposals."
        dossier = {"id": "Glasgow-1", "name": "Ann Glasgow", "relationships": {},
                   "vitals": {"birth": {"date": "c. 1675", "status": "estimated"}},
                   "research_findings": _findings(("Recommended correction — vital dates, 6 October 2026", "actions", correction))}
        soup = self.render(dossier, _links())
        note = soup.select_one(".dossier-header .dossier-date-note")
        self.assertEqual("The research recommends recording the birth as “before about 1679”. See the recommended correction.",
                         note.get_text(" ", strip=True).replace(" .", "."))
        self.assertEqual(soup.select_one(".research-finding")["id"], note.a["href"].lstrip("#"))


class LegacyAnchorTests(unittest.TestCase):
    def test_alias_goes_inside_the_successor_and_after_a_summary(self):
        html = ('<section id="overview"></section><section id="research-findings"><h2>R</h2></section>'
                '<details id="family" class="supporting-register"><summary>Family</summary><div>x</div></details>')
        soup = BeautifulSoup(renderer._with_legacy_anchors(html), "html.parser")
        self.assertEqual("research-findings", soup.find(id="research").parent["id"])
        alias = soup.find(id="imported-identity")
        self.assertEqual("family", alias.parent["id"])
        self.assertEqual("summary", alias.find_previous_sibling().name)

    def test_existing_ids_are_left_alone_and_overview_is_the_fallback(self):
        html = '<section id="overview"></section><section id="research"></section>'
        out = renderer._with_legacy_anchors(html)
        self.assertEqual(1, out.count('id="research"'))
        self.assertEqual("overview", BeautifulSoup(out, "html.parser").find(id="imported-identity").parent["id"])


class FindingLabelTests(unittest.TestCase):
    def test_own_heading_becomes_the_label_and_shared_titles_get_their_date(self):
        dossier = {"research_findings": _findings(
            ("Source findings", "sources", "| Source | Finding |\n|---|---|\n| A | checked 30 September 2026 |"),
            ("Source findings", "sources", "<!-- batch -->\n### Montgreenan entail litigation — 6 October 2026\n\nThe case."),
            ("Source findings", "sources", "A letter of 21 August 1775 names him."),
            ("Source findings", "sources", "Another record, read 2026-10-05."),
        )}
        entries = renderer._finding_entries("Glasgow-1", dossier)
        soup = BeautifulSoup(renderer._research_findings_html("Glasgow-1", dossier, {}, entries), "html.parser")
        cards = soup.select("details.research-finding")
        self.assertEqual([entry["anchor"] for entry in entries], [card["id"] for card in cards])
        titles = [card.select_one(".finding-title").get_text() for card in cards]
        self.assertEqual(["Source findings, 30 September 2026", "Montgreenan entail litigation — 6 October 2026",
                          "Source findings", "Source findings, 5 October 2026"], titles)
        self.assertEqual("Source findings", cards[1].select_one(".finding-kicker").get_text())
        self.assertIsNone(cards[0].select_one(".finding-kicker"))
        # The heading is not repeated inside the body.
        self.assertNotIn("Montgreenan", cards[1].select_one(".finding-body").get_text())
        self.assertIn("The case.", cards[1].select_one(".finding-body").get_text())

    def test_heading_matching_the_title_is_not_repeated_as_kicker(self):
        label, kicker, body = renderer._finding_labels([{"anchor": "a", "title": "Next questions", "markdown": "### Next questions\nCheck."}])["a"]
        self.assertEqual(("Next questions", "", "Check."), (label, kicker, body))


class DateNoteTests(unittest.TestCase):
    def entry(self, title, markdown):
        return {"title": title, "markdown": markdown, "anchor": "research-note-x", "archival": False}

    def test_only_recommended_corrections_that_differ(self):
        vitals = {"birth": {"date": "c. 1675"}, "death": {"date": "1742"}}
        self.assertEqual("", renderer._recommended_date_note([self.entry("Source findings", "**Birth: 1679**")], vitals))
        self.assertEqual("", renderer._recommended_date_note([self.entry("Recommended correction — vital dates", "**Death: 1742**")], vitals))
        self.assertEqual("", renderer._recommended_date_note([self.entry("Recommended correction — vital dates", "**Birth: about 1675**")], vitals))
        note = renderer._recommended_date_note([self.entry("Recommended correction — vital dates", "**Birth: before about 1679**\n\n**Death: after 1850.**")], vitals)
        self.assertIn("the birth as “before about 1679” and the death as “after 1850”", note)
        self.assertIn('href="#research-note-x"', note)


class FamilyLabelTests(unittest.TestCase):
    def test_saved_confidence_is_visible_without_inventing_a_percentage(self):
        dossier = {"id": "Glasgow-1", "name": "Ann", "relationships": {"parents": [{
            "id": "Glasgow-2", "name": "James Glasgow", "relationship": "father",
            "status": "unknown", "tree_status": "confident"}]}}
        with patch.object(renderer, "_shared_relationship_assessment", return_value=None):
            html = renderer._family_html("Glasgow-1", dossier, {}, {}, {}, {})
        text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
        self.assertIn("WikiTree: Confident · Not individually rated", text)
        self.assertNotIn("90%", text)

    def test_status_cell_links_to_the_evidence_guide(self):
        dossier = {"id": "Glasgow-1", "name": "Ann", "relationships": {"parents": [{"id": "Glasgow-2", "name": "James Glasgow", "status": "documented"}]}}
        with patch.object(renderer, "_shared_relationship_assessment", return_value=None):
            html = renderer._family_html("Glasgow-1", dossier, {}, {}, {}, {})
        label = BeautifulSoup(html, "html.parser").select_one("tr[data-state] .status-label")
        self.assertTrue(label.a["href"].startswith("/evidence/#"))
        self.assertIn("ev-label-link", label.a["class"])


class TopBarTests(unittest.TestCase):
    def test_one_breadcrumb_home_people_name(self):
        soup = BeautifulSoup('<div class="g-bar"><div class="g-crumbs"><a href="/">Glasgow archive</a><i>/</i><strong>Old</strong></div></div>', "html.parser")
        renderer._set_top_bar_crumbs(soup, "Glasgow-1", "Ann & Glasgow")
        crumbs = soup.select_one(".g-crumbs")
        self.assertEqual("Home/People/Ann & Glasgow", crumbs.get_text())
        self.assertEqual(["/", "/catalogue/"], [a["href"] for a in crumbs.select("a")])


class RepairIndexTests(unittest.TestCase):
    def test_full_pass_refreshes_the_link_index_first(self):
        with tempfile.TemporaryDirectory() as tmp:
            web = Path(tmp)
            (web / "people").mkdir()
            calls = []
            with (
                patch.object(renderer, "WEB", web),
                patch.object(renderer, "publish", side_effect=lambda site, **_: calls.append("publish")),
                patch.object(renderer, "_refresh_reviewed_parentage", return_value=None),
                patch("tools.build_backlinks.write_index", side_effect=lambda site: calls.append(("index", site))),
                patch("tools.catalogue_location_search.refresh_search_indexes", return_value=0),
            ):
                renderer.repair()
                self.assertEqual([("index", web), "publish"], calls)
                calls.clear()
                renderer.repair(["Glasgow-1"])
                self.assertEqual(["publish"], calls)


if __name__ == "__main__":
    unittest.main()
