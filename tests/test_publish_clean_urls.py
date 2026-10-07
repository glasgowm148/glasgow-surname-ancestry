"""Clean deployment routes must not break direct local HTML use."""

import tempfile
import unittest
from pathlib import Path

from tools.publish_clean_urls import publish_clean_urls


class PublishCleanUrlsTest(unittest.TestCase):
    def test_normalized_redirect_is_replaced_and_existing_readers_keep_their_route(self):
        with tempfile.TemporaryDirectory() as directory:
            web = Path(directory)
            inherited = '<script data-clean-index-redirect="">location.replace("/")</script>'
            (web / 'catalogue.html').write_text('<html><head>' + inherited + '</head></html>')
            reader = web / 'people/research-material/person-123/index.html'
            reader.parent.mkdir(parents=True)
            reader.write_text('<html><head>' + inherited + '</head><main>Complete evidence</main></html>')
            publish_clean_urls(web)
            page = (web / 'catalogue/index.html').read_text()
            self.assertIn('location.replace("/catalogue"+location.search+location.hash)', page)
            self.assertEqual(page.count('data-clean-index-redirect'), 1)
            self.assertNotIn('data-clean-index-redirect', reader.read_text())
            self.assertIn('Complete evidence', reader.read_text())

    def test_legacy_html_remains_portable(self):
        with tempfile.TemporaryDirectory() as directory:
            web = Path(directory)
            source = web / "catalogue.html"
            original = '<html><head></head><body><a href="index.html">Home</a></body></html>'
            source.write_text(original, encoding="utf-8")

            publish_clean_urls(web)

            # The legacy copy keeps its portable links and gains only a
            # canonical link to the clean route (site audit S1-06).
            canonical = '<link rel="canonical" href="https://glasgow.phenotype.dev/catalogue/">'
            self.assertEqual(source.read_text(encoding="utf-8"), original.replace("</head>", canonical + "</head>"))
            publish_clean_urls(web)
            self.assertEqual(source.read_text(encoding="utf-8").count('rel="canonical"'), 1)
            clean = (web / "catalogue" / "index.html").read_text(encoding="utf-8")
            self.assertEqual(clean.count(canonical), 1)
            self.assertIn('<base href="../">', clean)
            self.assertIn('location.protocol!=="file:"', clean)
            self.assertIn('data-local-file-links', clean)
            self.assertIn('href="index.html"', clean)
            self.assertIn("/catalogue.html  /catalogue  301", (web / "_redirects").read_text(encoding="utf-8"))

    def test_root_index_stays_open_and_keeps_local_links_under_file_scheme(self):
        with tempfile.TemporaryDirectory() as directory:
            web = Path(directory)
            home = web / "index.html"
            home.write_text(
                '<html><head><script data-clean-index-redirect>location.replace("/")</script></head>'
                '<body><a href="catalogue.html">Catalogue</a></body></html>',
                encoding="utf-8",
            )

            publish_clean_urls(web)

            output = home.read_text(encoding="utf-8")
            self.assertIn('location.protocol!=="file:"', output)
            self.assertIn('href="catalogue.html"', output)

    def test_comparison_rebuild_refreshes_content_inside_shared_navigation(self):
        with tempfile.TemporaryDirectory() as directory:
            web = Path(directory)
            (web / "compare").mkdir()
            (web / "compare" / "advanced.html").write_text(
                '<html><head><title>Old comparison</title></head>'
                '<body data-g-path="/compare/advanced.html"><aside class="g-rail">'
                '<nav class="g-nav">Old navigation</nav></aside>'
                '<main>Old comparison controls</main>'
                '<script src="/data/compare-index.js?v=old"></script>'
                '<script src="/people/compare.js?v=old" defer></script></body></html>',
                encoding="utf-8",
            )
            source = web / "compare.html"
            for generation in ("first", "updated"):
                source.write_text(
                    '<html><head><title>Compare people</title></head><body>'
                    f'<main><input id="compare-a"><input id="compare-b">{generation}'
                    '<div id="compare-results"></div></main>'
                    '<footer><p>Shared places do not prove kinship.</p></footer>'
                    f'<script src="data/compare-index.js?v={generation}"></script>'
                    f'<script src="people/compare.js?v={generation}" defer></script>'
                    '</body></html>', encoding="utf-8",
                )
                publish_clean_urls(web)
                output = (web / "compare" / "index.html").read_text(encoding="utf-8")
                self.assertEqual(output.count('class="g-rail"'), 1)
                self.assertEqual(output.count('class="g-nav"'), 1)
                self.assertIn('href="/research/" aria-current="page"', output)
                self.assertIn('data-g-path="/compare/"', output)
                self.assertIn('<title>Compare people</title>', output)
                self.assertIn(f'id="compare-b">{generation}', output)
                self.assertIn('id="compare-results"', output)
                self.assertIn('Shared places do not prove kinship.', output)
                self.assertIn(f'src="/data/compare-index.js?v={generation}"', output)
                self.assertIn(f'src="/people/compare.js?v={generation}" defer', output)
                self.assertIn('<base href="../">', output)
                self.assertNotIn('Old comparison', output)
                publish_clean_urls(web)
                self.assertEqual(
                    (web / "compare" / "index.html").read_text(encoding="utf-8"), output
                )


if __name__ == "__main__":
    unittest.main()
