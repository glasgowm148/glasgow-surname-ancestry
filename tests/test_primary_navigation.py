import importlib.util
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "www"
SPEC = importlib.util.spec_from_file_location(
    "repair_primary_navigation", ROOT / "tools/repair_primary_navigation.py"
)
NAVIGATION = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(NAVIGATION)


class PrimaryNavigationTests(unittest.TestCase):
    expected = (
        ("/", "Home"),
        ("/catalogue/", "People"),
        ("/branches/", "Families &amp; places"),
        ("/onetree/", "Family tree"),
        ("/ydna/", "Y-DNA"),
        ("/sources/", "Records &amp; sources"),
        ("/research/", "Research"),
        ("/latest-findings/", "Latest findings"),
        ("/about/", "About"),
    )

    def test_renderer_has_the_canonical_links_and_current_section(self):
        nav = NAVIGATION.render_primary_navigation(Path("compare/index.html"))
        self.assertEqual(9, nav.count('class="g-nav-link"'))
        self.assertEqual(1, nav.count('aria-current="page"'))
        self.assertIn('href="/research/" aria-current="page"', nav)
        for href, label in self.expected:
            self.assertIn(f'href="{href}"', nav)
            self.assertIn(f'<span>{label}</span>', nav)
        self.assertNotIn('href="/statistics/"', nav)
        self.assertNotIn('href="/resources/"', nav)
        # Statistics belongs with the other "about the data" pages (S1-07).
        statistics = NAVIGATION.render_primary_navigation(Path("statistics/index.html"))
        self.assertIn('href="/about/" aria-current="page"', statistics)
        self.assertIn('<a href="/statistics/" aria-current="location">Statistics</a>', statistics)

    def test_sample_rails_have_exactly_the_canonical_links(self):
        for relative in (
            "index.html", "catalogue/index.html", "branches/index.html",
            "onetree/index.html", "research/index.html", "statistics/index.html",
            "resources/index.html", "people/glasgow-951.html",
            "latest-findings/index.html",
        ):
            page = (WEB / relative).read_text(encoding="utf-8")
            nav = NAVIGATION.NAV.search(page)
            self.assertIsNotNone(nav, relative)
            links = re.findall(r'<a\b(?=[^>]*\bclass="[^"]*\bg-nav-link\b)[^>]*>', nav.group(0))
            self.assertEqual(9, len(links), relative)
            self.assertEqual(1, sum('aria-current="page"' in link for link in links), relative)
            self.assertEqual(
                list(self.expected),
                [(re.search(r'href="([^"]+)"', link).group(1),
                  re.search(r'<span>(.*?)</span>', nav.group(0)[nav.group(0).find(link):]).group(1))
                 for link in links],
                relative,
            )

    def test_records_and_transcriptions_have_their_own_section(self):
        for relative in ('sources/index.html', 'records/index.html', 'research/transcriptions/index.html'):
            nav = NAVIGATION.render_primary_navigation(Path(relative))
            self.assertIn('href="/sources/" aria-current="page"', nav, relative)
            self.assertEqual(1, nav.count('aria-current="page"'))

    def test_tree_tabs_retain_label_and_order_with_old_and_current_markup(self):
        for label in ('Atlas views', 'Family tree views'):
            page = '<span>THE COMPLETE CANOPY</span>' + f'<div role="tablist" aria-label="{label}">' + ''.join(
                f'<button data-view="{view}" role="tab">{text}</button>'
                for view, text in (('branches', 'Branch cards'), ('lanes', 'Timeline'),
                                   ('all', 'Canopy'), ('dna', 'Y-DNA'))
            ) + '</div>'
            revised = NAVIGATION.reorder_atlas_views(page)
            self.assertEqual(['all', 'branches', 'lanes', 'dna'],
                             re.findall(r'data-view="([^"]+)"', revised))
            self.assertIn('>Whole tree<', revised)
            self.assertNotIn('>Canopy<', revised)
            self.assertIn('THE WHOLE TREE', revised)
            self.assertEqual(revised, NAVIGATION.reorder_atlas_views(revised))

    def test_older_research_restoration_keeps_current_tree_controls(self):
        from tools import approved_restorations
        relative = 'onetree/index.html'
        original = ('<html><head></head><body><div aria-label="Atlas views">'
                    '<button data-view="lanes">Timeline</button>'
                    '<button data-view="all">Canopy</button>'
                    '<button data-view="branches">Branch cards</button>'
                    '<button data-view="dna">Y-DNA</button></div></body></html>')
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(approved_restorations, 'entries', return_value={relative: {'kind': 'atlas-renderer'}}), \
                patch.object(approved_restorations, 'source', return_value=original):
            web = Path(directory)
            (web / relative).parent.mkdir(parents=True)
            (web / relative).write_text(original)
            approved_restorations.restore_atlas(web)
            restored = (web / relative).read_text()
            self.assertEqual(['all', 'branches', 'lanes', 'dna'],
                             re.findall(r'data-view="([^"]+)"', restored))
            self.assertIn('>Whole tree<', restored)
            self.assertEqual((0, 0, 0), approved_restorations.restore_atlas(web))


if __name__ == "__main__":
    unittest.main()
