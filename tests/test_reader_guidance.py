"""Reader wording must preserve research content, links and reading tools."""
import unittest

from bs4 import BeautifulSoup
from tools import repair_reader_guidance as guidance


class ReaderGuidanceTests(unittest.TestCase):
    def test_interface_labels_preserve_record_text_and_identifiers(self):
        original = ('<h2 id="overview">Current position</h2>'
                    '<p>Original quotation: Family Atlas. Parentage is uncertain.</p>'
                    '<table><tr><td>1841</td><td>Probable identification</td></tr></table>'
                    '<a href="/people/glasgow-951.html#sources">Source library</a>'
                    '<details id="archive-tools"><summary>Original record</summary>'
                    '<pre>Family Atlas; source ref. ABC/123</pre></details>')
        revised = guidance.public_labels(original)
        self.assertIn('<h2 id="overview">Biography and research notes</h2>', revised)
        before, after = [BeautifulSoup(value, 'html.parser') for value in (original, revised)]
        for selector in ('p', 'table', 'details'):
            self.assertEqual(str(before.select_one(selector)), str(after.select_one(selector)))
        self.assertEqual(before.a['href'], after.a['href'])
        self.assertEqual(revised, guidance.public_labels(revised))

    def test_home_reading_route_is_idempotent_and_keeps_the_map_and_tree(self):
        page = (guidance.WEB / 'index.html').read_text()
        revised = guidance.home_page(page)
        self.assertEqual(revised, guidance.home_page(revised))
        soup = BeautifulSoup(revised, 'html.parser')
        self.assertEqual(1, len(soup.select('.reader-start')))
        self.assertEqual(1, len(soup.select('#study-map')))
        self.assertEqual(1, len(soup.select('#r-home-canopy')))
        self.assertEqual(1, len(soup.select('script[src*="branches-directory.js"]')))
        self.assertLess(revised.index('class="reader-start"'), revised.index('id="study-map"'))
        self.assertLess(revised.index('id="study-map"'), revised.index('id="research-example"'))

    def test_earlier_sourced_argument_survives_case_section_import(self):
        from tools.build_research_catalog import _load_research_findings
        sections = [section for finding in _load_research_findings(['Glasgow-4070'])
                    for section in finding['sections']]
        prior = next(section for section in sections if section['title'].startswith('Prior relationship assessment'))
        self.assertEqual('assessment', prior['category'])
        self.assertIn('https://law.justia.com/cases/new-york/appellate-division/1905/107-ad-245.html', prior['markdown'])
        self.assertIn('https://www.wikitree.com/wiki/Glasgow-951', prior['markdown'])


if __name__ == '__main__':
    unittest.main()
