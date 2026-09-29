"""Reviewed baptism relationships and complete, subordinate candidate scoring."""
import json
from pathlib import Path
import unittest
from urllib.parse import urlsplit

from bs4 import BeautifulSoup
from tools.repair_person_hierarchy import _assessed_relation, _editorial, _profile_data

ROOT = Path(__file__).resolve().parents[1]


class DossierParentsTests(unittest.TestCase):
    def page(self, profile):
        return BeautifulSoup((ROOT / 'www/people' / f'{profile.lower()}.html').read_text(), 'html.parser')

    def test_baptism_basis_is_shared_for_each_named_parent(self):
        for child, record in [('Glasgow-3939', 'baptism-james-1837'), ('Glasgow-3940', 'baptism-unnamed-1838')]:
            for parent, role in [('Glasgow-951', 'father'), ('McCaughan-222', 'mother')]:
                forward = _assessed_relation(parent, {'id': child}, 'children')
                reverse = _assessed_relation(child, {'id': parent}, 'parents')
                self.assertEqual('proved', forward['status'])
                self.assertEqual(forward['status'], reverse['status'])
                self.assertEqual([record], forward['source_ids'])
                self.assertEqual(forward['source_ids'], reverse['source_ids'])
                self.assertEqual(role, reverse['relationship'])
                for viewed, relative in [(parent, child), (child, parent)]:
                    soup = self.page(viewed)
                    row = soup.select_one(f'#family a[href="/people/{relative.lower()}.html"]').find_parent('tr')
                    self.assertIn('Documented', row.select_one('.status-label').text)
                    self.assertIn('Entry ', row.text)
                    link = row.select_one('a[href^="#source-"]')
                    self.assertIsNotNone(soup.select_one(link['href']))
        self.assertEqual('child', _assessed_relation('Glasgow-951', {'id': 'Glasgow-3940'}, 'children')['relationship'])

    def test_missing_name_and_death_remain_separate_from_confirmed_parents(self):
        unknown = self.page('Glasgow-3940')
        self.assertIn('neither a forename nor exact', unknown.select_one('#overview').text)
        self.assertIn('inferred boundary', unknown.select_one('.dossier-life').text)
        self.assertIn('No death or burial', self.page('Glasgow-3939').select_one('#question-death-boundary').text)
        later = _assessed_relation('Glasgow-951', {'id': 'Glasgow-973', 'status': 'strongly_supported'}, 'children')
        self.assertEqual('proved', later['status'])
        self.assertEqual('proved', _assessed_relation('Glasgow-973', {'id': 'McCaughan-222'}, 'parents')['status'])
        self.assertIn('Michigan', later['reason'])
        self.assertIsNone(unknown.select_one('#parent-candidates'))

    def test_wife_is_documented_and_recorded_name_variants_are_visible(self):
        for viewed, relative in [('Glasgow-951', 'McCaughan-222'), ('McCaughan-222', 'Glasgow-951')]:
            relation = _assessed_relation(viewed, {'id': relative}, 'spouses')
            self.assertEqual('proved', relation['status'])
            row = self.page(viewed).select_one(f'#family a[href="/people/{relative.lower()}.html"]').find_parent('tr')
            self.assertIn('Documented', row.select_one('.status-label').text)
        mary = self.page('McCaughan-222')
        recorded_names = next(fact for fact in mary.select('.dossier-fact') if 'Recorded names' in fact.text)
        for variant in ('Mary McAughin', 'Molly McAughern', 'Mary McCaughan'):
            self.assertIn(variant, recorded_names.text)

    def test_possible_father_cards_are_profiled_scored_and_readable(self):
        profile = 'Glasgow-951'
        dossier, _, _ = _profile_data(profile)
        editorial = _editorial(profile)
        inventory = json.loads((ROOT / 'research/Glasgow-951/parent_candidates.json').read_text())
        self.assertEqual([c['id'] for c in inventory], [c['id'] for c in editorial['parent_candidates']])
        expected = [item for item in editorial['parent_candidates'] if item.get('father_profile_id')]
        section = self.page(profile).select_one('#parent-candidates')
        # Authored biographies keep the candidate audit as a supporting register
        # beneath the narrative instead of a second top-level section.
        self.assertTrue(editorial.get('biography_sections'))
        self.assertEqual('details', section.name)
        self.assertIn('supporting-register', section['class'])
        self.assertEqual('Detailed candidate research and score audit', section.find('summary', recursive=False).text)
        self.assertEqual(len(expected), len(section.select('.parent-candidate')))
        scores = {item['id']: item for item in dossier['potential_parentage']['candidates']}
        for item in expected:
            node = section.select_one('#candidate-' + item['id'])
            self.assertEqual(item['state'], node['data-state'])
            self.assertEqual(item['father_profile_id'], node['data-score-profile'])
            for point in item['supports'] + item['objections']:
                self.assertIn(point, node.get_text())
            self.assertTrue(node.select_one(f'a.candidate-name[href="https://www.wikitree.com/wiki/{item["father_profile_id"]}"]'))
            self.assertIn('birth', node.select_one('.candidate-identity small').text.casefold())
            if 'score_profile_id' in item and item['score_profile_id'] is None:
                # Record-named placeholders are deliberately left unscored.
                self.assertNotIn(item['father_profile_id'], scores)
                self.assertIn('—/100', node.select_one('summary').text)
                self.assertIn(item['score_note'], node.select_one('.candidate-score')['title'])
            else:
                self.assertIn(f'{scores[item["father_profile_id"]]["score"]}/100', node.select_one('summary').text)
            self.assertTrue(node.select('.candidate-support li'))
            self.assertTrue(node.select('.candidate-objection li'))
        excluded = section.select_one('#candidate-excluded-james-1702')
        self.assertIn('Excluded', excluded.select_one('summary').text)
        self.assertIn('researched 1799 birth makes him only about twelve', excluded.text)
        self.assertIn('not probabilities', section.text)
        james = section.select_one('#candidate-larne-james-3986')
        james_item = next(item for item in inventory if item['id'] == 'larne-james-3986')
        self.assertIn(james_item['verdict_label'], james.select_one('summary').text)
        self.assertIn(f'{scores["Glasgow-3986"]["score"]}/100', james.select_one('summary').text)
        self.assertFalse(section.select('[data-score-profile^="Unknown-"]'))
        self.assertNotIn('Collateral comparisons', section.text)

    def test_candidate_links_resolve_and_scores_stay_out_of_record_timeline(self):
        soup = self.page('Glasgow-951')
        for link in soup.select('#parent-candidates a[href]'):
            url = urlsplit(link['href'])
            if url.scheme or url.netloc:
                continue
            target = ROOT / 'www' / url.path.lstrip('/') if url.path else ROOT / 'www/people/glasgow-951.html'
            self.assertTrue(target.exists(), link['href'])
            if url.fragment:
                self.assertIsNotNone(BeautifulSoup(target.read_text(), 'html.parser').find(id=url.fragment), link['href'])
        self.assertFalse(soup.select('#timeline .candidate-score'))
        self.assertFalse(soup.select('#parent-candidates [data-score-id]'))
        self.assertEqual(1, len(soup.select('#record-will-daniel-1871-thomas-network')))


if __name__ == '__main__':
    unittest.main()
