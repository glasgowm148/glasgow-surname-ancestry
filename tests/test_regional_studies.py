"""Local-study navigation follows geography, even when members emigrate."""
import importlib.util
import json
from pathlib import Path
import unittest

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {
    'early-ireland': {'lisnagaver-rasharkin', 'larne-kilwaughter'},
    'scottish-families': {'early-scottish-records'},
    'north-american-families': set(),
    'australasian-families': set(),
    'english-welsh-families': set(),
    'other-family-places': set(),
}


class RegionalStudyTests(unittest.TestCase):
    def test_emigration_does_not_change_local_study_region(self):
        spec = importlib.util.spec_from_file_location('experience', ROOT / 'tools/repair_site_experience.py')
        helper = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(helper)
        countries = {'ireland', 'scotland', 'america', 'oceania', 'england', 'other'}
        for region, studies in EXPECTED.items():
            for study in studies:
                with self.subTest(study=study):
                    self.assertEqual([region], helper.branch_topic_ids({'id': study, 'kind': 'place'}, countries))
        # Families still appear in every region represented by their records.
        self.assertEqual(list(EXPECTED), helper.branch_topic_ids({'id': 'family-example', 'kind': 'family'}, countries))

    def test_all_regional_pages_show_only_geographic_local_studies(self):
        branches = json.loads((ROOT / 'www/assets/research/branches.json').read_text())
        for region, studies in EXPECTED.items():
            with self.subTest(region=region):
                soup = BeautifulSoup((ROOT / f'www/branches/{region}/index.html').read_text(), 'html.parser')
                headings = soup.find_all('h2', string='Choose a local study')
                self.assertEqual(1 if studies else 0, len(headings))
                if studies:
                    self.assertEqual({f'/branches/{study}/' for study in studies},
                                     {a['href'] for a in headings[0].parent.select('a')})
                self.assertEqual(studies, {b['id'] for b in branches if b['kind'] == 'place' and region in b['topic_ids']})

    def test_directory_filters_and_family_navigation_use_same_geography(self):
        directory = json.loads((ROOT / 'www/assets/research/branches-directory.json').read_text())
        for group in directory['groups']:
            if group['kind'] == 'place':
                region = next(region for region, studies in EXPECTED.items() if group['id'] in studies)
                self.assertEqual([region], group['regions'])
                self.assertEqual(region, group['region'])
        branches = json.loads((ROOT / 'www/assets/research/branches.json').read_text())
        places = [b for b in branches if b['kind'] == 'place']
        study_urls = {b['url'] for b in places}
        checked = 0
        for branch in branches:
            soup = BeautifulSoup((ROOT / f'www/branches/{branch["id"]}/index.html').read_text(), 'html.parser')
            navigation = soup.select_one('nav[aria-label="Related regions and local studies"]')
            if navigation is None:
                continue
            with self.subTest(branch=branch['id']):
                expected = {p['url'] for p in places if p['id'] != branch['id'] and set(p['topic_ids']) & set(branch['topic_ids'])}
                self.assertEqual(expected, {a['href'] for a in navigation.select('a')} & study_urls)
            checked += 1
        self.assertGreater(checked, 300)


if __name__ == '__main__':
    unittest.main()
