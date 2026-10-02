"""Sitemap coverage must follow public publication boundaries and clean routes."""
import json
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

from tools.site_sitemap import build_sitemap, safe_route, sitemap_entries


class SitemapTests(unittest.TestCase):
    def test_public_reader_coverage_clean_routes_and_privacy(self):
        with tempfile.TemporaryDirectory() as directory:
            site = Path(directory)

            def page(route, head=""):
                path = site / route
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(f'<!doctype html><html><head>{head}</head><body><main>Public text</main></body></html>')

            def index(route, rows):
                path = site / route
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(rows))

            for route in ("index.html", "catalogue.html", "catalogue/index.html", "research/index.html",
                          "free-space/index.html", "free-space/approved-study/index.html",
                          "latest-findings/index.html", "latest-findings/page/2/index.html",
                          "branches/public-family/index.html", "sources/index.html",
                          "sources/s-1234567890abcdef/index.html", "people/public-1.html",
                          "people/living-1.html", "people/private-1.html", "people/unlisted-1.html",
                          "places/public-place.html", "catalogue/browse/page-2.html",
                          "assets/research/fragments/abcdef0123456789.html",
                          "research/private/notes.html", "research/fragments/part.html",
                          "archive/research.html", "data/hidden.html"):
                page(route)
            page("research/noindex/index.html", '<meta name="robots" content="noindex, follow">')
            page("compare/index.html")
            page("compare/advanced.html", '<link rel="canonical" href="https://glasgow.phenotype.dev/compare">')
            page("research/dated/index.html", '<meta property="article:modified_time" content="2026-01-02T12:00:00Z">')
            page("research/future/index.html", '<meta property="article:modified_time" content="2099-01-02">')
            index("data/people-index.json", [
                {"html_url": "/people/public-1.html"},
                {"html_url": "/people/living-1.html", "living": True},
                {"html_url": "/people/private-1.html", "privacy": 40},
            ])
            index("data/places-index.json", [{"url": "/places/public-place.html"}])
            index("assets/research/branches.json", [{"url": "/branches/public-family/"}])
            index("assets/research/free-space-index.json", [{"url": "/free-space/approved-study/"},
                  {"url": "/assets/research/fragments/abcdef0123456789.html"},
                  {"url": "/../outside.html"}, {"url": "https://other.test/private.html"}])
            index("assets/v3/source-index.json", [{"id": "s-1234567890abcdef"}])
            entries = sitemap_entries(site)
            for route in ("/", "/catalogue/", "/research/", "/sources/", "/free-space/",
                          "/free-space/approved-study/", "/latest-findings/page/2/",
                          "/people/public-1.html", "/places/public-place.html",
                          "/branches/public-family/", "/sources/s-1234567890abcdef/",
                          "/catalogue/browse/page-2.html"):
                self.assertIn(route, entries)
            for fragment in ("living-1", "private-1", "unlisted-1", "noindex", "fragments", "archive", "outside", "hidden", "private/notes"):
                self.assertFalse(any(fragment in route for route in entries))
            self.assertNotIn("/catalogue.html", entries)
            self.assertIn("/compare/", entries)
            self.assertNotIn("/compare/advanced.html", entries)
            self.assertEqual(entries["/research/dated/"], "2026-01-02")
            self.assertIsNone(entries["/research/future/"])
            self.assertIsNone(entries["/"])
            self.assertEqual(build_sitemap(site)["sitemap_urls"], len(entries))
            first = (site / "sitemap.xml").read_bytes()
            build_sitemap(site)
            self.assertEqual(first, (site / "sitemap.xml").read_bytes())
            parsed = ET.fromstring(first)
            urls = [node.text for node in parsed.findall("{*}url/{*}loc")]
            self.assertEqual(len(urls), len(set(urls)))
            self.assertFalse(any(url.endswith("index.html") for url in urls))

    def test_external_symlink_and_nonreader_artifacts_are_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            site = root / "www"
            site.mkdir()
            external = root / "outside.html"
            external.write_text("<html>private</html>")
            (site / "escaped.html").symlink_to(external)
            for route in ("/escaped.html", "/../outside.html", "/data.csv", "/release.tar.gz",
                          "/.cache/notes.html", "/private/notes.html", "https://other.test/reader/"):
                self.assertIsNone(safe_route(route, site))


if __name__ == "__main__":
    unittest.main()
