"""Focused acceptance coverage for the person-dossier cleanup."""
from pathlib import Path
import json
import re
import unittest

from bs4 import BeautifulSoup

from tools.repair_person_hierarchy import _date_sort_key


ROOT = Path(__file__).resolve().parents[1]
SLUGS = (
    "glasgow-951",
    "glasgow-1367",
    "glasgow-3939",
    "glasgow-987",
    "glasgow-3167",
    "mccaughan-222",
)


class DossierCleanupTests(unittest.TestCase):
    def page(self, slug):
        path = ROOT / "www" / "people" / f"{slug}.html"
        return BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")

    def text(self, node):
        return node.get_text(" ", strip=True)

    def test_acceptance_pages_keep_collapsed_evidence_and_family_structure(self):
        for slug in SLUGS:
            with self.subTest(slug=slug):
                soup = self.page(slug)
                questions = soup.select("#evidence article.question")
                self.assertTrue(questions)
                for question in questions:
                    details = question.select_one("details.question-details")
                    self.assertIsNotNone(details)
                    self.assertNotIn("open", details.attrs)
                groups = soup.select("#family details.relation-group")
                self.assertTrue(groups)
                self.assertTrue(all("open" not in group.attrs for group in groups))

    def test_local_source_related_and_parent_links_resolve_in_main(self):
        for slug in SLUGS:
            with self.subTest(slug=slug):
                soup = self.page(slug)
                main = soup.select_one("main")
                targets = {node["id"] for node in soup.select("[id]")}
                links = main.select(".source-links a[href^='#'], .related-links a[href^='#'], .parent-comparison a[href^='#']")
                self.assertTrue(links)
                for link in links:
                    self.assertIn(link["href"][1:], targets, link)

    def test_historical_timeline_is_one_date_sorted_sequence_with_groups(self):
        for slug in SLUGS:
            with self.subTest(slug=slug):
                soup = self.page(slug)
                rows = soup.select("#timeline .timeline-row")
                self.assertTrue(rows)
                self.assertTrue(all(row.get("data-group") for row in rows))
                keys = [_date_sort_key(row.select_one("time").get_text(" ", strip=True)) for row in rows]
                self.assertEqual(keys, sorted(keys))

    def test_same_year_month_dates_sort_chronologically(self):
        dates = ("9 October 1843", "17 January 1843", "9 February 1843")
        self.assertEqual(
            ["17 January 1843", "9 February 1843", "9 October 1843"],
            sorted(dates, key=_date_sort_key),
        )

    def test_public_presentation_exports_the_same_scoped_facts_and_basis(self):
        from tools.repair_person_hierarchy import _current_vitals, _profile_data, _assessed_relation
        for slug in SLUGS:
            dossier = json.loads((ROOT / "www/people" / f"{slug}.json").read_text())
            profile = dossier["id"]
            _, model, _ = _profile_data(profile)
            presentation = dossier["presentation"]
            self.assertEqual(_current_vitals(profile, dossier, model), presentation["vitals"])
            for group, rows in presentation["relationships"].items():
                original = dossier["relationships"][group]
                self.assertEqual([_assessed_relation(profile, row, group) for row in original], rows)
        robert = json.loads((ROOT / "www/people/glasgow-1367.json").read_text())["presentation"]
        self.assertEqual("conflict", robert["resolution"]["state"])
        self.assertEqual("identity-dependent", robert["vitals"]["birth"]["status"])

    def test_james_birth_adult_identity_and_death_boundary_are_separate(self):
        soup = self.page("glasgow-3939")
        identity_node = soup.select_one("#question-identity")
        parents_node = soup.select_one("#question-parents")
        death_node = soup.select_one("#question-death-boundary")
        self.assertIsNotNone(identity_node)
        self.assertIsNotNone(parents_node)
        self.assertIsNotNone(death_node)
        identity = self.text(identity_node)
        parents = self.text(parents_node)
        death = self.text(death_node)
        self.assertRegex(identity, r"17 January 1837")
        self.assertRegex(identity, r"9 February(?: 1837)?")
        self.assertIn("not competing birth dates", identity.casefold())
        self.assertIn("adults", parents.casefold())
        self.assertIn("later", parents.casefold())
        self.assertIn("before 1841", death.casefold())
        self.assertIn("inferred", death.casefold())
        self.assertIn("no death or burial", death.casefold())

    def test_thomas_network_evidence_is_canonical_and_legacy_deep_links_remain(self):
        soup = self.page("glasgow-951")
        network = soup.select_one("#question-thomas-network")
        self.assertIsNotNone(network)
        for record_id in ("will-daniel-1871", "marriage-daniel-neely-1888"):
            canonical = f"record-{record_id}-thomas-network"
            legacy = f"record-{record_id}-parents"
            self.assertEqual(1, len(network.select(f"#{canonical}")))
            self.assertEqual(1, len(soup.select(f"#{canonical}")))
            redirect = soup.select_one(f"#{legacy} a")
            self.assertIsNotNone(redirect)
            self.assertEqual(f"#{canonical}", redirect.get("href"))

    def test_robert_keeps_conflict_qualified_vitals_and_open_father_hypothesis(self):
        soup = self.page("glasgow-1367")
        visible = self.text(soup.select_one(".person-dossier-readable"))
        self.assertIn("conflict", visible.casefold())
        self.assertNotRegex(visible, r"\bsettled\s+Tyrone\b")
        father = self.page("glasgow-951").select_one("#family a[href='/people/glasgow-1367.html']").find_parent("tr")
        self.assertIn("Open father hypothesis", self.text(father))
        self.assertNotIn("non-biological", self.text(father).casefold())

    def test_mary_thomas_samuel_and_letter_regressions(self):
        mary = self.page("mccaughan-222")
        alexander = self.page("glasgow-951")
        self.assertEqual("Subject", self.text(mary.select_one("#timeline-death-mary-1892 .timeline-role")))
        collateral = alexander.select_one("#timeline-death-mary-1892")
        self.assertIsNotNone(collateral)
        self.assertNotIn("Subject", self.text(collateral))

        thomas = self.page("glasgow-987")
        timeline_ids = [row.get("id") for row in thomas.select("#timeline .timeline-row")]
        self.assertLess(timeline_ids.index("timeline-census-thomas-1851"), timeline_ids.index("timeline-administration-thomas-1870"))
        self.assertLess(timeline_ids.index("timeline-administration-thomas-1870"), timeline_ids.index("timeline-marriage-sarah-1885"))

        mary_elder = self.page("glasgow-3167")
        visible = self.text(mary_elder.select_one(".person-dossier-readable"))
        self.assertIn("Samuel Elder civil birth return", visible)
        self.assertIn("original register records Samuel Elder", visible)
        self.assertIn("unexplained conflict between original records", visible)
        self.assertIn("does not identify Samuel's father", visible)
        self.assertNotIn("Glasgow was his middle name", visible)

        research = self.text(alexander.select_one("#research"))
        self.assertIn("already-held 20 March 1847 John Glasgow letter", research)
        self.assertNotRegex(research, r"\b(?:obtain|acquire)\b.{0,120}\b(?:letter|20 March 1847)\b")

    def test_hash_handler_walks_all_ancestor_disclosures(self):
        source = (ROOT / "tools" / "repair_person_hierarchy.py").read_text(encoding="utf-8")
        self.assertIn("function openHash()", source)
        self.assertTrue('node=node.parentElement' in source)
        self.assertTrue('if(node.tagName==="DETAILS")node.open=true' in source)
        self.assertIn('window.addEventListener("hashchange",openHash)', source)


if __name__ == "__main__":
    unittest.main()
