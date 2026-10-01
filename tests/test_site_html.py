import tempfile
import unittest
from pathlib import Path

from tools.site_html import read_html


class ReadHtmlTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "assets/research/fragments").mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def write_page(self, value):
        path = self.root / "page.html"
        path.write_text(value, encoding="utf-8")
        return path

    def test_expands_fragment_preserving_details_id_and_textarea_content(self):
        (self.root / "assets/research/fragments/a.html").write_text(
            '<details><summary>Updated</summary><p>Expanded content</p></details>', encoding="utf-8")
        page = self.write_page('<details id="outer" data-r-fragment="/assets/research/fragments/a.html"><textarea>original content</textarea></details>')
        result = read_html(page, self.root)
        self.assertIn('id="outer"', result)
        self.assertIn("Expanded content", result)
        self.assertNotIn("original content", result)

    def test_rejects_remote_outside_and_missing_or_malformed_fragments(self):
        for url in ("https://example.test/x.html", "/private/x.html", "/assets/research/fragments/../x.html"):
            with self.subTest(url=url):
                with self.assertRaises(ValueError):
                    read_html(self.write_page(f'<details data-r-fragment="{url}"></details>'), self.root)
        with self.assertRaises((ValueError, FileNotFoundError)):
            read_html(self.write_page('<details data-r-fragment="/assets/research/fragments/missing.html"></details>'), self.root)
        (self.root / "assets/research/fragments/b.html").write_text("<p>no details</p>", encoding="utf-8")
        with self.assertRaises(ValueError):
            read_html(self.write_page('<details data-r-fragment="/assets/research/fragments/b.html"></details>'), self.root)


if __name__ == "__main__":
    unittest.main()
