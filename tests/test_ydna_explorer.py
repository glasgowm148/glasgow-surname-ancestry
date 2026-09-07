#!/usr/bin/env python3
"""Static contract tests for the public Y-DNA explorer."""

import json
import re
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "www" / "ydna" / "index.html"
SOURCE = ROOT / "www" / "ydna" / "glasgow-ydna-story-source"


def page_data(page: str) -> dict:
    match = re.search(r'<script id="research-data" type="application/json">(.*?)</script>', page, re.S)
    if not match:
        raise AssertionError("embedded Y-DNA research data not found")
    return json.loads(match.group(1))


class YdnaExplorerTests(unittest.TestCase):
    def test_explorer_keeps_story_tools_and_contextual_evidence(self) -> None:
        page = PUBLIC.read_text(encoding="utf-8")
        data = page_data(page)

        self.assertEqual(len(data["roots"]), 8)
        self.assertEqual(len(data["kits"]), 21)
        self.assertEqual(len(data["pairs"]), 64)
        self.assertEqual(len(data["matches"]), 17)
        self.assertEqual(len(data["originalTables"]), 11)
        self.assertEqual(sum(len(tables) for tables in data["originalTables"].values()), 13)
        self.assertEqual(
            sum(len(table) - 1 for tables in data["originalTables"].values() for table in tables),
            78,
        )

        for section in (
            "overview", "origins", "compare", "mutation-tree", "str-network",
            "snp-splits", "sapp-model", "roots", "next-steps", "sources",
        ):
            self.assertIn(f'id="{section}"', page)
        self.assertNotIn('id="evidence-dossier"', page)
        self.assertNotIn('id="dossier-search"', page)
        for host in (
            "family-str-evidence", "family-inheritance-evidence",
            "str-source-matrix", "str-direction-evidence",
            "sapp-group-evidence", "sapp-placement-evidence",
            "ft6135-scenarios-evidence", "vcf-call-evidence",
            "variant-direction-evidence", "yfull-evidence",
            "line-status-evidence", "archived-priorities",
        ):
            self.assertIn(f'id="{host}"', page)
        for feature in (
            "Evidence beneath this pedigree", "Branch-weighted marker reading",
            "SAPP group audit", "Full directional comparison audit",
            "What each unresolved line still needs", "Previous fixed ordering — superseded",
            "Not the current priority ranking.", "Previous page snapshot",
        ):
            self.assertIn(feature, page)

        for evidence in (
            "DYS19=15 · DYS456=16 · DYS712=19", "FT25406 → FT20271", "FTE32242",
            "FT6135", "11816547", "26534797", "Node 16", "Node 17",
            "Wm Farrier and Susanna Abell line", "Henry Ferrier, born c.1758",
            "829 populated reference DYS/FTY fields", "43290879-Nebraska-204066-0005.jpg",
        ):
            self.assertIn(evidence, page)

        for kit in (
            "325862", "B835762", "254947", "N18544", "959947", "B696189",
            "1002232", "B580327", "200475", "999763", "478604", "794462",
        ):
            self.assertIn(kit, page)
        for profile in ("Glasgow-951", "Glasgow-2738", "Glasgow-591", "Glasgow-12"):
            self.assertIn(profile, page)

        self.assertEqual(data["pairs"]["200475|999763"]["gd"], 0)
        self.assertEqual(data["pairs"]["1002232|B580327"]["gd"], 3)
        self.assertEqual(data["audit"]["mstCount"], 8)
        self.assertEqual(data["audit"]["fourPointViolations"], 4)
        self.assertEqual(data["metadata"]["revision"], "story-documentary-refresh-2026-09-07")

        for documentary_check in (
            "1194 Yorkshire Pipe Roll", "half a mark", "pledge or surety",
            "Roger de Glasgu", "John Glasgw in Stirling in 1475–1479/80",
            "Farrier/Ferrier", "medieval de Ferrers", "Duffield-471",
            "placement evidence", "John de Glasgow alias Smith",
            "Robert Watson → Agnes",
        ):
            self.assertIn(documentary_check, page)
        self.assertIn("Space:John_de_Glasgow_alias_Smith_/_John_Glasgow_of_Saltmarket%27", page)
        self.assertIn("association is therefore a lead to verify", page)
        self.assertNotIn("Glasgow and Duffield share this younger part of the tree", page)

        for living_name in (
            "Karl Glasgow", "Rod Dale Glasgow", "Gerald Neumann Glasgow", "Craig Linn Glasgow",
            "Nathan Jacobs", "David Lee Glasgow", "Christopher Dale Glasgow", "Robert Brown",
            "Brian Wilson", "Jerry Glasgo", "John Edward Farrier", "Jason Phillips",
            "Michael B Glasgow", "Jack Glasgow", "Roger Allan Glasgow",
            "Christopher Stephen FARRIER", "J P FARRIER",
        ):
            self.assertNotIn(living_name, page)

    def test_source_build_and_public_routes_are_preserved(self) -> None:
        public = PUBLIC.read_text(encoding="utf-8")
        source_page = (SOURCE / "index.html").read_text(encoding="utf-8")
        old_snapshot = (SOURCE / "reference" / "original-upload.html").read_text(encoding="utf-8")

        self.assertIn('<base href="../">', public)
        self.assertIn("data-clean-index-redirect", public)
        self.assertIn("data-local-file-links", public)
        self.assertIn('<base href="../../">', source_page)
        self.assertNotIn("data-clean-index-redirect", source_page)
        self.assertIn("See which paternal roots actually share mutations.", old_snapshot)
        for token in ("__CSS__", "__JS__", "__DATA__", "__SITE_BASE__", "__ROUTE_REDIRECT__"):
            self.assertNotIn(token, public)
            self.assertNotIn(token, source_page)

    def test_home_and_discovery_links_exist(self) -> None:
        home = (ROOT / "www" / "index.html").read_text(encoding="utf-8")
        self.assertIn('href="ydna.html"', home)
        self.assertIn('href="catalogue.html"', home)
        ydna_legacy = (ROOT / "www" / "ydna.html").read_text(encoding="utf-8")
        self.assertIn("location.protocol==='file:'?'ydna/index.html':'/ydna'", ydna_legacy)
        self.assertNotIn('http-equiv="refresh"', ydna_legacy)
        self.assertIn("/ydna", (ROOT / "www" / "sitemap.xml").read_text(encoding="utf-8"))
        self.assertIn("/ydna", (ROOT / "www" / "llms.txt").read_text(encoding="utf-8"))

    def test_deep_timeline_preserves_unplaced_match_boundary(self) -> None:
        timeline = (ROOT / "www" / "timeline" / "index.html").read_text(encoding="utf-8")
        self.assertIn("three Farrier/Ferrier Y-111 lines at GD 4, 4 and 5", timeline)
        self.assertIn("not drawn inside FT20271", timeline)
        self.assertIn("R-FTA30932, a different named branch", timeline)


if __name__ == "__main__":
    unittest.main()
