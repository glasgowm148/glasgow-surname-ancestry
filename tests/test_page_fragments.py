import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from tools.page_fragments import optimize_page

class PageFragmentsTests(unittest.TestCase):
    def test_large_details_and_idempotence(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp); html = '<details id="research-note-a"><summary>Sources</summary><p>' + "e" * 60000 + "</p></details>"
            out, stats = optimize_page(html, "people/test.html", root)
            self.assertEqual(stats["extracted"], 1); self.assertIn("data-r-fragment=", out)
            reader = next((root / "people/research-material").glob("*/index.html")); self.assertIn("e" * 60000, reader.read_text())
            again, second = optimize_page(out, "people/test.html", root); self.assertEqual(second["extracted"], 0); self.assertEqual(again, out)

    def test_nested_and_anchors(self):
        with TemporaryDirectory() as tmp:
            inner = '<details id="inner"><summary>Inner</summary><p>' + "x" * 30000 + "</p></details>"
            html = '<details id="outer"><summary>Outer</summary><a id="target"></a>' + inner + "y" * 30000 + "</details>"
            out, stats = optimize_page(html, "x.html", Path(tmp)); self.assertEqual(stats["extracted"], 1); self.assertIn('data-r-fragment-anchors="target inner"', out)

    def test_profile_update_preserves_textarea(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp); value = "complete revised profile " + "z" * 55000
            html = '<section id="wikitree-update" class="profile-update-panel"><textarea>' + value + "</textarea></section>"
            out, stats = optimize_page(html, "people/p.html", root); self.assertEqual(stats["extracted"], 1); self.assertIn('id="wikitree-update"', out)
            fragment = next((root / "assets/research/fragments").glob("*.html")).read_text(); self.assertIn(value, fragment); self.assertNotIn('id="wikitree-update"', fragment)

    def test_duplicate_notes_and_unsafe_path(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp); out, stats = optimize_page('<p id="research-note-a">one</p><p id="research-note-a">two</p>', "x.html", root)
            self.assertEqual(stats["extracted"], 0); self.assertEqual(out.count('id="research-note-a"'), 1)
            with self.assertRaises(ValueError): optimize_page("<p>x</p>", "../outside.html", root)

if __name__ == "__main__": unittest.main()
