"""Broken internal links fixed at their builders (site audit I2 H5, lane I8)."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import build_statistics_page, build_study_pages
from tools.public_privacy import WITHHELD, WITHHELD_TEXT, PublicPrivacy, safe_href


class StudyPagePersonLinkTests(unittest.TestCase):
    def test_person_links_only_people_with_a_page(self):
        registry = {'glasgow-1': {'name': 'John Glasgow', 'life': '1800 – 1870'},
                    'record-x-1': {'name': 'Isobel Glasgow'}}
        with tempfile.TemporaryDirectory() as tmp:
            web = Path(tmp)
            (web / 'people').mkdir()
            (web / 'people' / 'glasgow-1.html').write_text('<html></html>')
            with patch.object(build_study_pages, 'WEB', web):
                linked = build_study_pages.person('glasgow-1', registry, True)
                plain = build_study_pages.person('record-x-1', registry)
        self.assertIn('<a href="/people/glasgow-1.html">John Glasgow</a>', linked)
        self.assertIn('1800 – 1870', linked)
        self.assertNotIn('<a ', plain)
        self.assertIn('Isobel Glasgow', plain)


class StatisticsLinkTests(unittest.TestCase):
    def test_catalogue_pane_links_become_root_absolute(self):
        pane = ('<a href="catalogue.html?first=John">John</a><a href="people/glasgow-1.html">A</a>'
                '<a href="places/larne.html">Larne</a><a href="/catalogue.html#x">x</a><a href="/catalogue/">all</a>')
        out = build_statistics_page.rebase_catalogue_links(pane)
        self.assertIn('href="/catalogue/?first=John"', out)
        self.assertIn('href="/people/glasgow-1.html"', out)
        self.assertIn('href="/places/larne.html"', out)
        self.assertIn('href="/catalogue/#x"', out)
        self.assertNotIn('catalogue.html', out)
        self.assertEqual(out, build_statistics_page.rebase_catalogue_links(out))


class PrivacyPlaceholderLinkTests(unittest.TestCase):
    def setUp(self):
        self.policy = PublicPrivacy({'Example-200': {'birth_date': '2000-01-01'}})

    def test_link_values_are_blanked_not_replaced_with_the_placeholder(self):
        row = {'id': 'Example-200', 'catalogue_id': 'example-200', 'slug': 'example-200',
               'html_url': '/people/example-200.html', 'json_url': '/people/example-200.json',
               'network_url': '/people/example-200.network.json', 'canonical_url': 'https://x/people/example-200.html',
               'selection_id': 'example-200', 'mother_id': 'Example-200', 'name': 'Ann Example'}
        self.assertEqual(WITHHELD, self.policy.project(row))
        # A public subject's links to private relatives are blanked independently.
        row.update(id='Historical-1', catalogue_id='historical-1', slug='historical-1')
        projected = self.policy.project(row)
        for key in row:
            if key in ('id', 'catalogue_id', 'slug', 'name'):
                self.assertEqual(row[key], projected[key], key)
            else:
                self.assertEqual('', projected[key], key)
        self.assertNotIn(WITHHELD_TEXT, str(projected))

    def test_prose_keeps_the_placeholder(self):
        self.assertEqual(WITHHELD_TEXT, self.policy.project('Daughter of Example-200 and her husband.'))

    def test_safe_href(self):
        self.assertEqual('/people/a-1.html', safe_href('/people/a-1.html'))
        for value in ('', None, WITHHELD_TEXT, '/people/private family details withheld..html'):
            self.assertEqual('', safe_href(value))


if __name__ == '__main__':
    unittest.main()
