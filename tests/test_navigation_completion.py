import importlib.util
from pathlib import Path
import re
import unittest

from tests._generated_data import requires_generated_data


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "repair_primary_navigation", ROOT / "tools/repair_primary_navigation.py"
)
NAV = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(NAV)


class NavigationCompletionTests(unittest.TestCase):
    def test_first_paint_submenus_have_required_routes_and_order(self):
        catalogue = NAV.render_primary_navigation(Path("catalogue/index.html"))
        self.assertNotIn('href="/catalogue/#catalogue-filters"', catalogue)
        self.assertIn('href="/catalogue/?missingProfile=1#catalogue-filters"', catalogue)

        branches = NAV.render_primary_navigation(Path("branches/index.html"))
        self.assertEqual(
            ["All families", "Family studies", "Scottish families", "Irish families"],
            re.findall(r'<a href="[^"]+"[^>]*>(.*?)</a>', NAV.render_section_submenu(Path("branches/index.html"), "/branches/")),
        )

        tree = NAV.render_section_submenu(Path("onetree/index.html"), "/onetree/")
        self.assertEqual(
            ["Whole tree", "Branch cards", "Timeline", "Y-DNA", "Map"],
            re.findall(r'<a href="[^"]+"[^>]*>(.*?)</a>', tree),
        )

    def test_first_paint_submenu_is_adjacent_to_selected_primary_link(self):
        nav = NAV.render_primary_navigation(Path("changes/index.html"))
        selected_start = nav.index('<a class="g-nav-link" href="/about/" aria-current="page"')
        submenu_start = nav.index('class="g-section-subnav"')
        self.assertIn('</a><div class="g-section-subnav"', nav[selected_start:submenu_start + 32])

    @requires_generated_data
    def test_about_shell_repair_is_idempotent_and_preserves_page_content(self):
        for route, marker in (
            ("changes/index.html", "Catalogue change log"),
            ("feedback/index.html", "Report a correction"),
            ("privacy/index.html", "Privacy and publication policy"),
        ):
            original = (ROOT / "www" / route).read_text(encoding="utf-8")
            repaired = NAV.repair_about_shell_page(original, Path(route))
            self.assertIn('id="g-navigation"', repaired)
            self.assertIn('class="g-footer"', repaired)
            self.assertIn(marker, repaired)
            self.assertIn('href="/about/"', repaired)
            if 'id="g-navigation"' not in original:
                self.assertNotIn('<base href=', repaired)
            if route != 'privacy/index.html':
                self.assertIn('href="/people/catalogue.css', repaired)
            else:
                self.assertIn('.privacy-main', repaired)
            if route.startswith('feedback/'):
                self.assertIn('id="feedback-template"', repaired)
            self.assertEqual(repaired, NAV.repair_about_shell_page(repaired, Path(route)))

    def test_js_contract_covers_anchor_history_and_single_findings_rail(self):
        js = (ROOT / "tools" / "section_submenus.js").read_text(encoding="utf-8")
        self.assertIn("root === '/latest-findings/'", js)
        # Changes and Feedback stay under About (AGENTS.md); site audit S1-07
        # adds the evidence guide, statistics and privacy to the same section.
        self.assertIn("evidence|resources|coverage|statistics|data|changes|privacy|feedback|status", js)
        about_start = js.index("if (root === '/about/') return [")
        about_end = js.index("      ];", about_start)
        about_fallback = js[about_start:about_end]
        self.assertEqual(
            ["/about/", "/evidence/", "/coverage/", "/statistics/", "/data/", "/resources/",
             "/changes/", "/privacy/", "/feedback/"],
            re.findall(r"make\('([^']+)'", about_fallback),
        )
        first_paint = [href for href, _ in NAV.SECTION_SUBMENU_ITEMS["/about/"]]
        self.assertEqual(first_paint, re.findall(r"make\('([^']+)'", about_fallback))
        self.assertIn("location.hash = url.hash", js)
        self.assertIn("addEventListener('popstate', schedule)", js)
        self.assertIn("document.body.classList.remove('g-nav-open')", js)

    @requires_generated_data
    def test_reader_shell_preserves_place_main_assets_and_resolves_base_links(self):
        route = Path("places/corvanaghan.html")
        original = (ROOT / "www" / route).read_text(encoding="utf-8")
        repaired = NAV.repair_reader_shell_page(original, route)
        self.assertIn('id="g-navigation"', repaired)
        self.assertIn('<main', repaired)
        self.assertIn('class="place-hero-grid"', repaired)
        self.assertIn('/people/catalogue.css', repaired)
        self.assertIn('application/ld+json', repaired)
        self.assertNotIn('<base ', repaired)
        self.assertNotIn('href="../', repaired)
        self.assertIn('href="/map/', repaired)
        self.assertEqual(repaired, NAV.repair_reader_shell_page(repaired, route))

    @requires_generated_data
    def test_reader_shell_covers_clean_and_legacy_about_research_routes(self):
        for route in (
            "status/index.html", "status.html", "compare/index.html", "compare.html",
            "candidate-matches/index.html", "candidate-matches.html", "changes.html", "feedback.html",
        ):
            original = (ROOT / "www" / route).read_text(encoding="utf-8")
            repaired = NAV.repair_reader_shell_page(original, Path(route))
            self.assertIn('id="g-navigation"', repaired, route)
            self.assertIn('class="g-footer"', repaired, route)
            self.assertIn('<main', repaired, route)
            # A page that already has the maintained rail is intentionally
            # left untouched, including any page-specific base handling.
            if 'id="g-navigation"' not in original:
                self.assertNotIn('<base ', repaired, route)

    @requires_generated_data
    def test_reader_shell_preserves_catalogue_form_and_filter_controls(self):
        for route in ("catalogue.html", "catalogue/advanced.html"):
            original = (ROOT / "www" / route).read_text(encoding="utf-8")
            repaired = NAV.repair_reader_shell_page(original, Path(route))
            self.assertIn('id="g-navigation"', repaired, route)
            self.assertIn('id="catalogue-filters"', repaired, route)
            self.assertIn('<form', repaired, route)
            if 'id="g-navigation"' not in original:
                self.assertNotIn('<base ', repaired, route)
            self.assertEqual(repaired, NAV.repair_reader_shell_page(repaired, Path(route)))

    def test_existing_catalogue_reader_corrects_page_kind_without_rebuilding_shell(self):
        original = '<html><body class="g-unified g-kind-about v3-site custom"><aside id="g-navigation">Preserved rail</aside><main><form id="catalogue-filters">Filters</form></main></body></html>'
        for route in ('catalogue.html','catalogue/index.html','catalogue/advanced.html'):
            corrected = NAV.repair_reader_shell_page(original, Path(route))
            self.assertIn('g-kind-catalogue', corrected)
            self.assertNotIn('g-kind-about', corrected)
            self.assertEqual(original.replace('g-unified g-kind-about v3-site custom','g-unified v3-site custom g-kind-catalogue'), corrected)
            self.assertEqual(corrected, NAV.repair_reader_shell_page(corrected, Path(route)))

    @requires_generated_data
    def test_reader_shell_covers_public_people_readers_and_skips_merges(self):
        for route, section in (
            ("people/index.html", 'g-kind-catalogue'),
            ("people/clusters/descendants-of-hugh-glasgow-c-1706.html", 'g-kind-branches'),
            ("people/by-name/a.html", 'g-kind-catalogue'),
            ("people/early-bearers/index.html", 'g-kind-catalogue'),
        ):
            original = (ROOT / "www" / route).read_text(encoding="utf-8")
            repaired = NAV.repair_reader_shell_page(original, Path(route))
            self.assertIn('id="g-navigation"', repaired, route)
            self.assertIn(section, repaired, route)
            self.assertIn('<main', repaired, route)
            self.assertIn('/people/catalogue.css', repaired, route)
            if 'id="g-navigation"' not in original:
                self.assertNotIn('<base ', repaired, route)
            self.assertEqual(repaired, NAV.repair_reader_shell_page(repaired, Path(route)))

        merged = (ROOT / "www/people/glasgow-3983.html").read_text(encoding="utf-8")
        self.assertEqual(merged, NAV.repair_reader_shell_page(merged, Path("people/glasgow-3983.html")))

    def test_maintained_shell_css_prevents_rail_and_feedback_clipping(self):
        css = (ROOT / "tools/section_submenus.css").read_text(encoding="utf-8")
        self.assertIn('.v3-site .g-rail .g-nav{flex:0 0 auto;overflow:visible}', css)
        self.assertIn('overflow-y:auto', css)
        self.assertIn('data-g-path="/feedback/index.html"', css)
        self.assertIn('min-height:260px', css)


if __name__ == "__main__":
    unittest.main()
