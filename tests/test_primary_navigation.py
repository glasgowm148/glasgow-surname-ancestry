import importlib.util
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "www"
SPEC = importlib.util.spec_from_file_location(
    "repair_primary_navigation", ROOT / "tools/repair_primary_navigation.py"
)
NAVIGATION = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(NAVIGATION)


class PrimaryNavigationTests(unittest.TestCase):
    expected = (
        ("/", "Overview"),
        ("/catalogue/", "People"),
        ("/branches/", "Families &amp; places"),
        ("/onetree/", "Atlas"),
        ("/ydna/", "Y-DNA"),
        ("/research/", "Research"),
        ("/about/", "About"),
    )

    def test_renderer_has_the_canonical_seven_and_current_section(self):
        nav = NAVIGATION.render_primary_navigation(Path("statistics/index.html"))
        self.assertEqual(7, nav.count('class="g-nav-link"'))
        self.assertEqual(1, nav.count('aria-current="page"'))
        self.assertIn('href="/research/" aria-current="page"', nav)
        for href, label in self.expected:
            self.assertIn(f'href="{href}"', nav)
            self.assertIn(f'<span>{label}</span>', nav)
        self.assertNotIn('href="/statistics/"', nav)
        self.assertNotIn('href="/resources/"', nav)

    def test_sample_rails_have_exactly_the_canonical_seven(self):
        for relative in (
            "index.html", "catalogue/index.html", "branches/index.html",
            "onetree/index.html", "research/index.html", "statistics/index.html",
            "resources/index.html", "people/glasgow-951.html",
        ):
            page = (WEB / relative).read_text(encoding="utf-8")
            nav = NAVIGATION.NAV.search(page)
            self.assertIsNotNone(nav, relative)
            links = re.findall(r'<a\b(?=[^>]*\bclass="[^"]*\bg-nav-link\b)[^>]*>', nav.group(0))
            self.assertEqual(7, len(links), relative)
            self.assertEqual(1, sum('aria-current="page"' in link for link in links), relative)
            self.assertEqual(
                list(self.expected),
                [(re.search(r'href="([^"]+)"', link).group(1),
                  re.search(r'<span>(.*?)</span>', nav.group(0)[nav.group(0).find(link):]).group(1))
                 for link in links],
                relative,
            )


if __name__ == "__main__":
    unittest.main()
