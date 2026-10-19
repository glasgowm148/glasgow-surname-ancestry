import importlib.util
import json
from pathlib import Path
import unittest

from tests._generated_data import requires_generated_data

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]


def module():
    spec = importlib.util.spec_from_file_location('build_branches_directory', ROOT / 'tools/build_branches_directory.py')
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


class BranchesDirectoryTests(unittest.TestCase):
    @requires_generated_data
    def test_generated_directory_contract(self):
        directory = json.loads((ROOT / 'www/assets/research/branches-directory.json').read_text())
        groups = directory['groups']
        branches = json.loads((ROOT / 'www/assets/research/branches.json').read_text())
        self.assertEqual({branch['id'] for branch in branches if branch['kind'] != 'region'},
                         {group['id'] for group in groups})
        self.assertEqual(len(groups), len({group['id'] for group in groups}))
        self.assertEqual({'family', 'research', 'place'}, {group['kind'] for group in groups})
        self.assertTrue(all(group['precision'] for group in groups))
        self.assertTrue(all((group['lat'] is None and group['lon'] is None) == (group['precision'] == 'none') for group in groups))
        self.assertEqual(6, len(directory['regions']))

    @requires_generated_data
    def test_static_page_has_unique_study_cards_and_map_assets(self):
        soup = BeautifulSoup((ROOT / 'www/branches/index.html').read_text(), 'html.parser')
        cards = soup.select('.bd-card[data-group-id]')
        self.assertEqual(len(cards), len({card['data-group-id'] for card in cards}))
        self.assertIsNone(soup.select_one('#r-branch-results'))
        self.assertIsNotNone(soup.select_one('link[href^="/assets/research/branches-directory.css?v="]'))
        self.assertIsNotNone(soup.select_one('script[src^="/assets/research/branches-directory.js?v="]'))

    @requires_generated_data
    def test_priority_map_territories_link_to_existing_studies(self):
        soup = BeautifulSoup((ROOT / 'www/branches/index.html').read_text(), 'html.parser')
        shapes = soup.select('#study-map a.bd-territory[data-territory]')
        items = soup.select('#study-map .bd-priority-item')
        self.assertTrue(5 <= len(shapes) <= 10)
        self.assertEqual([s['data-territory'] for s in shapes], [i['data-territory'] for i in items])
        self.assertEqual([str(n) for n in range(1, len(shapes) + 1)], [s.select_one('text').get_text() for s in shapes])
        for shape in shapes:
            self.assertTrue(shape.select_one('path')['d'].startswith('M'))
            href = shape['href']
            self.assertTrue(href.startswith('/branches/'))
            self.assertTrue((ROOT / 'www' / href.strip('/') / 'index.html').exists(), href)
        self.assertGreater(len(soup.select('#study-map .bd-base path')), 20)
        self.assertIn('Historic County Borders Project', soup.select_one('#study-map figcaption').get_text())

    def test_precision_ranking_prefers_record_stated_location(self):
        helper = module()
        place, lat, lon, precision, label = helper.group_location([
            {'record_location': 'County Antrim', 'record_precision': 'County-level representative point', 'latitude': '54', 'longitude': '-6', 'year': '1800'},
            {'record_location': 'Larne', 'record_precision': 'Record-stated place', 'latitude': '54.85', 'longitude': '-5.82', 'year': '1810'},
        ])
        self.assertEqual(('Larne', 54.85, -5.82, 'exact', 'Record-stated place'), (place, lat, lon, precision, label))


if __name__ == '__main__':
    unittest.main()
