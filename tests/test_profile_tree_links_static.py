from pathlib import Path
import re
import tempfile
import unittest

from bs4 import BeautifulSoup

from tests._generated_data import requires_generated_data
from tools import profile_tree_links as links

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "tools/site_sources/performance/core.js"


def page(person='{"id": "Glasgow-1", "name": "Ada Glasgow", "url": "/people/glasgow-1.html", "tree": true}'):
    return ("<!doctype html><html><head><title>T</title></head>"
            f"<body class=\"person-hierarchy\" data-g-person='{person}'><main><header class=\"dossier-header\">"
            '<div class="dossier-identity"><h1>Ada</h1><div class="dossier-actions"><a href="https://www.wikitree.com/wiki/Glasgow-1">View on WikiTree</a>'
            '<a href="#family-account">Explore family</a></div></div></header></main></body></html>')


class StaticProfileTreeLinkTests(unittest.TestCase):
    def views(self, html):
        return [a["data-view"] for a in BeautifulSoup(html, "html.parser").select("#profile-tree-links a")]

    def test_views_follow_the_tree_counts_like_core_js(self):
        self.assertEqual(["sun", "down", "all", "time"], self.views(links.nav_html("Glasgow-1", "Ada", {"Glasgow-1": [1200, 3]})))
        self.assertEqual(["down", "all", "time"], self.views(links.nav_html("Glasgow-1", "Ada", {"Glasgow-1": [0, 3]})))
        self.assertEqual(["all", "time"], self.views(links.nav_html("Glasgow-1", "Ada", {})))
        self.assertEqual(["sun", "down", "all", "time"], self.views(links.nav_html("Glasgow-1", "Ada", None)))
        sun = BeautifulSoup(links.nav_html("Glasgow-1", "Ada", {"Glasgow-1": [1200, 3]}), "html.parser").select_one("a.ptl-sun")
        self.assertEqual("1,200 descendants", sun.small.text)
        one = BeautifulSoup(links.nav_html("Glasgow-1", "Ada", {"Glasgow-1": [1, 0]}), "html.parser").select_one("a.ptl-sun")
        self.assertEqual("1 descendant", one.small.text)
        self.assertEqual("/onetree/#view=all&sun=Glasgow-1", sun["href"])

    def test_names_and_identifiers_are_escaped_and_encoded(self):
        nav = BeautifulSoup(links.nav_html("O'Neill-2", 'A & "B" <c>', None), "html.parser").nav
        self.assertEqual('Family tree views for A & "B" <c>', nav["aria-label"])
        self.assertEqual("/onetree/#person=O'Neill-2&view=all", nav.select_one('a[data-view="all"]')["href"])
        self.assertIsNone(nav.select_one("c"))

    def test_row_goes_after_the_actions_once_and_only_for_tree_people(self):
        lines = {"Glasgow-1": [5, 0]}
        once = links.add_to_page(page(), lines)
        self.assertEqual(once, links.add_to_page(once, lines))
        soup = BeautifulSoup(once, "html.parser")
        self.assertEqual("profile-tree-links", soup.select_one(".dossier-actions").find_next_sibling()["id"])
        self.assertEqual(1, len(soup.select("#profile-tree-links")))
        self.assertEqual(1, len(soup.select("head style#profile-tree-links-css")))
        refreshed = BeautifulSoup(links.add_to_page(once, {"Glasgow-1": [7, 0]}), "html.parser")
        self.assertEqual("7 descendants", refreshed.select_one("a.ptl-sun small").text)
        outside = page('{"id": "record-x", "name": "X", "url": "/people/record-x.html", "tree": false}')
        self.assertEqual(outside, links.add_to_page(outside, lines))
        self.assertNotIn("profile-tree-links", links.add_to_page(page().replace("dossier-actions", "other"), lines))

    def test_icons_and_stylesheet_match_core_js(self):
        core = CORE.read_text(encoding="utf-8")
        for key, svg in links.ICONS.items():
            self.assertIn(f"{key}:'{svg}'", core)
        start = core.index("st.textContent=\n") + len("st.textContent=\n")
        stylesheet = "".join(re.findall(r"'([^']*)'", core[start:core.index("document.head.append(st)}", start)]))
        self.assertTrue(links.CSS.startswith(stylesheet))
        self.assertIn("document.getElementById('profile-tree-links'))return", core)

    def test_apply_updates_built_pages_in_place(self):
        with tempfile.TemporaryDirectory() as directory:
            web = Path(directory)
            (web / "people").mkdir()
            (web / "people/glasgow-1.html").write_text(page())
            self.assertEqual({"pages": 1, "changed": 1}, links.apply(web, write=False))
            self.assertEqual({"pages": 1, "changed": 1}, links.apply(web))
            self.assertEqual({"pages": 1, "changed": 0}, links.apply(web))
            self.assertIn('id="profile-tree-links"', (web / "people/glasgow-1.html").read_text())

    @requires_generated_data
    def test_built_tree_pages_carry_the_row(self):
        result = links.apply(write=False)
        self.assertGreater(result["pages"], 0)
        self.assertEqual(0, result["changed"], "run tools/profile_tree_links.py")


if __name__ == "__main__":
    unittest.main()
