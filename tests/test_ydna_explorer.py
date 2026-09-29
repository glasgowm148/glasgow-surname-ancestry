"""Contracts for the public aggregate Y-DNA summary."""
from __future__ import annotations

from pathlib import Path
import unittest

from tools import repair_public_dna
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


class YdnaExplorerTests(unittest.TestCase):
    def test_public_summary_keeps_historical_links_and_uncertainty(self) -> None:
        page = PUBLIC.read_text(encoding="utf-8")
        self.assertIn("Historical branch summary", page)
        self.assertIn('href="/timeline"', page)
        self.assertIn('href="/privacy/"', page)
        for profile in ("Glasgo-21", "Glasgow-1144", "Glasgow-1143", "Glasgow-822", "Glasgow-591", "Glasgow-2738", "Glasgow-951", "Glasgow-12"):
            self.assertIn(f'href="/people/{profile}/"', page)
        for wording in (
            "do not prove a historical pedigree",
            "remain research leads",
            "not been independently established",
            "withheld pending publication approval",
        ):
            self.assertIn(wording, page)

    def test_public_routes_do_not_embed_or_offer_tester_level_assets(self) -> None:
        for path in (PUBLIC, LEGACY_STORY):
            page = path.read_text(encoding="utf-8")
            self.assertNotIn('id="research-data"', page)
            self.assertNotIn("application/json", page)
            self.assertNotIn("comparison matrix", page)
        self.assertIn('name="robots" content="noindex, noarchive"', LEGACY_STORY.read_text(encoding="utf-8"))
        self.assertIn('href="https://glasgow.phenotype.dev/ydna/"', LEGACY_STORY.read_text(encoding="utf-8"))
        self.assertEqual("[]\n", (ROOT / "www" / repair_public_dna.DNA_INDEX).read_text(encoding="utf-8"))
        for relative in repair_public_dna.WITHHELD_ASSETS:
            self.assertFalse((ROOT / "www" / relative).exists(), relative)

    def test_renderer_discards_private_fixture_fields(self) -> None:
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
