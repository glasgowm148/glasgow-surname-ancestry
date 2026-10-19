"""Contracts for the public aggregate Y-DNA summary."""
from __future__ import annotations

from pathlib import Path
import json
import unittest
from unittest.mock import patch

from bs4 import BeautifulSoup
from tools import repair_public_dna
from tools.public_ydna_research import approved_document, approved_inputs, PRIVATE, STUDY, LINES
from tools.site_sources.ydna_story import build as ydna_build


ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "www/ydna/index.html"
LEGACY_STORY = ROOT / "www/ydna/glasgow-ydna-story-source/index.html"


def private_fixture() -> dict[str, object]:
    """Synthetic private study input: it must never be emitted by the renderer."""
    return {
        "metadata": {"referenceKit": "private-reference"},
        "kits": [{"id": "private-test-a"}, {"id": "private-test-b"}],
        "pairs": {"private-test-a|private-test-b": {"gd": 3}},
        "audit": {"ids": ["private-test-a", "private-test-b"]},
        "roots": [{
            "kitIds": ["private-test-a"],
            "name": "Example Glasgow",
            "years": "c.1800",
            "profile": "Glasgow-999",
            "haplo": "R-FT20271",
            "route": "Antrim to Scotland",
        }],
    }


requires_approved_study = unittest.skipUnless(
    all((PRIVATE / relative).is_file() for relative in (STUDY, LINES)),
    "requires local approved private Y-DNA inputs",
)


class YdnaExplorerTests(unittest.TestCase):
    @requires_approved_study
    def test_public_summary_keeps_historical_links_and_uncertainty(self) -> None:
        page = PUBLIC.read_text(encoding="utf-8")
        # The original curated explorer now has exact publication approval.
        # Keep the older aggregate-only contract on unapproved input below.
        self.assertTrue(approved_document("ydna/index.html", page))
        self.assertEqual(approved_inputs()[STUDY],
                         json.loads(BeautifulSoup(page, "html.parser").select_one("#research-data").text))
        main = BeautifulSoup(page, "html.parser").select_one("main")
        self.assertTrue(main.select_one("h1").get_text(strip=True))
        self.assertTrue(main.select('a[href^="/timeline/"]'))
        self.assertIn("unproved", main.get_text(" ", strip=True).casefold())
        summary = ydna_build.render(private_fixture(), canonical="https://example.test/ydna/")
        self.assertIn("Historical branch summary", summary)
        self.assertIn('href="/timeline"', summary)
        self.assertIn('href="/privacy/"', summary)
        # All retained historic roots remain available to the aggregate renderer.
        fixture = private_fixture()
        fixture["roots"] = approved_inputs()[STUDY]["roots"]
        summary = ydna_build.render(fixture, canonical="https://example.test/ydna/")
        for profile in (root["profile"] for root in fixture["roots"] if root.get("profile")):
            self.assertIn(f'href="/people/{profile}/"', summary)
        for wording in (
            "do not prove a historical pedigree",
            "remain research leads",
            "not been independently established",
            "withheld pending publication approval",
        ):
            self.assertIn(wording, summary)

    @requires_approved_study
    def test_public_routes_do_not_embed_or_offer_tester_level_assets(self) -> None:
        for path in (PUBLIC, LEGACY_STORY):
            page = path.read_text(encoding="utf-8")
            self.assertTrue(approved_document(str(path.relative_to(ROOT / "www")), page))
        legacy = BeautifulSoup(LEGACY_STORY.read_text(encoding="utf-8"), "html.parser")
        self.assertEqual("noindex, noarchive", legacy.select_one('meta[name="robots"]')["content"])
        self.assertEqual("https://glasgow.phenotype.dev/ydna/", legacy.select_one('link[rel="canonical"]')["href"])
        for relative in (repair_public_dna.DNA_INDEX, *repair_public_dna.WITHHELD_ASSETS):
            path = ROOT / "www" / relative
            if path.exists():
                self.assertTrue(approved_document(relative, path.read_text(encoding="utf-8")), relative)
        self.assertEqual([], repair_public_dna.audit(ROOT / "www", repair_public_dna.PRIVATE_ROOT))

    @patch("tools.public_ydna_research.approved_inputs", return_value=None)
    def test_renderer_discards_private_fixture_fields(self, _approved_inputs) -> None:
        page = ydna_build.render(private_fixture(), canonical="https://example.test/ydna/")
        for private_value in ("private-reference", "private-test-a", "private-test-b", '"pairs"', '"kits"'):
            self.assertNotIn(private_value, page)
        self.assertIn("Example Glasgow", page)
        self.assertIn('href="/people/Glasgow-999/"', page)
        self.assertIn("R-FT20271", page)

    def test_deep_timeline_remains_available_from_the_summary(self) -> None:
        timeline = (ROOT / "www/timeline/index.html").read_text(encoding="utf-8")
        self.assertIn("Y-DNA Timeline", timeline)
        self.assertIn("R-FT20271", timeline)


if __name__ == "__main__":
    unittest.main()
