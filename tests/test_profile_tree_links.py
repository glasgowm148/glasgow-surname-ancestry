"""Profile pages link to the person's tree views through the shared profile script."""
import unittest
from pathlib import Path

from tools.atlas_whole_tree import PATCHES
from tools.build_tree_research_status import family_lines

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "tools/site_sources/performance/core.js"


class ProfileTreeLinksTest(unittest.TestCase):
    def test_core_script_builds_links_for_tree_people(self):
        text = CORE.read_text(encoding="utf-8")
        self.assertEqual(text.count("nav.id='profile-tree-links'"), 1)
        for href in ("'/onetree/#view=all&sun='", "'&view=family'", "'&view=family&lens=ancestors'",
                     "'&view=all'", "'&view=lanes'"):
            self.assertIn(href, text)
        self.assertIn("me.tree!==true", text)
        self.assertIn(".dossier-header .dossier-actions", text)

    def test_saved_tree_view_only_restores_the_same_request(self):
        # A link asking for another view (e.g. Whole tree after Descendants) must not be
        # overridden by the camera saved for this tab; reloads and Back still restore it.
        text = CORE.read_text(encoding="utf-8")
        self.assertIn("sameAsk=!asked||askKey(saved?.path)===askKey('#'+asked)", text)
        self.assertIn("if(saved&&sameAsk&&", text)

    def test_atlas_hash_opens_lens_and_timeline(self):
        out = next(new for old, new in PATCHES if old.startswith("if(id&&P.has(id))"))
        self.assertIn("['ancestors','close'].includes(lens)", out)
        self.assertIn("v==='lanes'||v==='all'", out)

    def test_family_lines_counts_distinct_relatives(self):
        model = {"people": [
            {"id": "A", "kind": "person", "parents": []},
            {"id": "B", "kind": "person", "parents": [{"id": "A"}]},
            {"id": "C", "kind": "person", "parents": [{"id": "A"}, {"id": "B"}]},
            {"id": "D", "kind": "person", "parents": [{"id": "C"}, {"id": "X", "withheld": True}]},
            {"id": "E", "kind": "person", "parents": [{"id": "A", "status": "non-biological"}]},
            {"id": "G", "kind": "group", "parents": []},
        ]}
        lines = family_lines(model)
        self.assertEqual(lines["A"], [3, 0])
        self.assertEqual(lines["C"], [1, 2])
        self.assertEqual(lines["D"], [0, 3])
        self.assertNotIn("E", lines)
        self.assertNotIn("G", lines)


if __name__ == "__main__":
    unittest.main()
