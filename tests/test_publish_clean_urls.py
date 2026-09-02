"""Clean deployment routes must not break direct local HTML use."""

import tempfile
import unittest
from pathlib import Path

from tools.publish_clean_urls import publish_clean_urls


class PublishCleanUrlsTest(unittest.TestCase):
    def test_legacy_html_remains_portable(self):
        with tempfile.TemporaryDirectory() as directory:
            web = Path(directory)
            source = web / "catalogue.html"
            original = '<html><head></head><body><a href="index.html">Home</a></body></html>'
            source.write_text(original, encoding="utf-8")

            publish_clean_urls(web)

            self.assertEqual(source.read_text(encoding="utf-8"), original)
            clean = (web / "catalogue" / "index.html").read_text(encoding="utf-8")
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


if __name__ == "__main__":
    unittest.main()
