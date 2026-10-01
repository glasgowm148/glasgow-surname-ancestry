"""Research decisions must agree in every current human/machine view."""
from copy import deepcopy
import json
from pathlib import Path
import unittest

from bs4 import BeautifulSoup
from tests._site_html import read_html

from tools.publish_resolved_dossiers import resolve
from tools.repair_person_hierarchy import _current_vitals
from tools import evidence_labels

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / 'www'


def load(path):
    return json.loads(path.read_text())


class ResolvedPublicModelTests(unittest.TestCase):
    def test_all_approved_pairs_agree_across_outputs_and_preserve_history(self):
        for assessment in load(ROOT / 'research/relationship_assessments.json'):
            if assessment.get('publication_status') != 'approved':
                continue
            aid = assessment['assertion_id']
            for profile, perspective in assessment['perspectives'].items():
                with self.subTest(profile=profile, assertion=aid):
                    if not (WEB / f'people/{profile.lower()}.json').exists():
                        # An external WikiTree relative need not have a local dossier.
                        other = next(p for p in assessment['people'] if p != profile)
                        related = load(WEB / f'people/{other.lower()}.json')
                        external = next(r for rows in related['relationships'].values() for r in rows if r['id'] == profile)
                        self.assertEqual(f'https://www.wikitree.com/wiki/{profile}', external['wikitree_url'])
                        continue
                    dossier = load(WEB / f'people/{profile.lower()}.json')
                    network = load(WEB / f'people/{profile.lower()}.network.json')
                    page = BeautifulSoup(read_html(WEB / f'people/{profile.lower()}.html'), 'html.parser')
                    embedded = json.loads(page.select_one('pre.archive-json').text)
                    self.assertEqual(dossier['relationships'], dossier['presentation']['relationships'])
                    self.assertEqual(dossier['relationships'], embedded['relationships'])
                    self.assertEqual(dossier['claims'], embedded['claims'])
                    row = next(r for rows in dossier['relationships'].values() for r in rows if r.get('claim_id') == aid)
                    self.assertEqual(row, next(r for r in network['relationships'] if r.get('claim_id') == aid))
                    self.assertEqual(row['status'], assessment['status'])
                    self.assertEqual(row['relationship'], perspective['relationship'])
                    self.assertEqual(row['reason'], perspective.get('reason') or assessment['reason'])
                    self.assertEqual(row['source_ids'], assessment['source_ids'])
                    claim = next(c for c in dossier['claims'] if c['id'] == aid)
                    self.assertEqual(claim, next(c for c in network['claims'] if c['id'] == aid))
                    for key in ('status', 'reason', 'source_ids', 'relationship', 'status_label'):
                        self.assertEqual(claim[key], row[key])
                    html_row = page.select_one(f'#family tr[data-claim-id="{aid}"]')
                    self.assertIsNotNone(html_row)
                    # Pages show the curated label in the canonical vocabulary (tools/evidence_labels.py).
                    self.assertEqual(evidence_labels.normalise_status_label(row["status"], row["status_label"]), html_row.select_one('.status-label').text)
                    self.assertIn(row['reason'], html_row.text)
                    record_ids = {r['record_id'] for r in dossier['presentation']['record_associations']}
                    self.assertTrue(set(row['source_ids']).issubset(record_ids))
                    if row['source_ids']:
                        self.assertTrue(html_row.select('a[href^="#source-"]'))
                    else:
                        # An approved publication can be a caution about an
                        # unassessed tree link. It must not claim documentary
                        # proof or manufacture a source anchor.
                        self.assertNotEqual('proved', row['status'])
                        self.assertTrue(row['reason'])
                    for link in html_row.select('a[href^="#"]'):
                        self.assertIsNotNone(page.find(id=link['href'][1:]))
                    for old_id in claim['historical_claim_ids']:
                        old = next(c for c in dossier['claims'] if c['id'] == old_id)
                        self.assertEqual('historical', old['lifecycle'])
                        self.assertEqual(aid, old['superseded_by'])
                        self.assertTrue(any(c['id'] == old_id for c in dossier['imported']['sections']['claims']))

    def test_identity_qualified_vitals_are_not_overridden_by_display_data(self):
        for profile in ('glasgow-1367', 'glasgow-3939', 'glasgow-3940', 'glasgow-951', 'mccaughan-222'):
            dossier = load(WEB / f'people/{profile}.json')
            network = load(WEB / f'people/{profile}.network.json')
            page = BeautifulSoup(read_html(WEB / f'people/{profile}.html'), 'html.parser')
            embedded = json.loads(page.select_one('pre.archive-json').text)
            for representation in (dossier['presentation'], network, embedded):
                self.assertEqual(dossier['vitals'], representation['vitals'])
            self.assertEqual(dossier['vitals'], _current_vitals(profile, dossier,
                {'vitals': {'birth': {'place': 'Stale import'}}}, {'vitals': {'birth': {'place': 'Formatting override'}}}))
            for vital in dossier['vitals'].values():
                if vital.get('qualifier'):
                    self.assertIn(vital['qualifier'], page.select_one('.dossier-life').text)
        robert = load(WEB / 'people/glasgow-1367.json')
        for vital in robert['vitals'].values():
            self.assertIsNone(vital['date'])
            self.assertIsNone(vital['place'])
            self.assertEqual('identity-dependent', vital['status'])
            self.assertTrue(vital['provenance']['assessment_id'])
            self.assertTrue(vital['alternatives'])
            self.assertTrue(all(a.get('qualifier') and a.get('provenance') for a in vital['alternatives']))
        self.assertEqual({'County Antrim, Ireland', 'County Tyrone, Ireland'},
                         {a['place'] for a in robert['vitals']['birth']['alternatives']})
        self.assertEqual('County Tyrone, Ireland', robert['imported']['sections']['vitals']['birth']['place'])

    def test_generic_shared_resolution_is_scoped_idempotent_and_revocable(self):
        original = {'id': 'Person-1', 'relationships': {'parents': [
            {'id': 'Person-2', 'claim_id': 'old', 'status': 'unknown'},
            {'id': 'Person-3', 'claim_id': 'other', 'status': 'unknown'}]},
            'claims': [{'id': 'old', 'status': 'unknown'}, {'id': 'other', 'status': 'unknown'}]}
        review = {'people': ['Person-1', 'Person-2'], 'publication_status': 'approved',
                  'assertion_id': 'new', 'status': 'proved', 'source_ids': ['record-1'],
                  'basis': 'Reviewed record', 'perspectives': {
                      'Person-1': {'relationship': 'father', 'reason': 'The record names the father.'},
                      'Person-2': {'relationship': 'daughter', 'reason': 'The record names the daughter.'}}}
        untouched = deepcopy(original)
        result = resolve(original, [], [review])
        self.assertEqual(original, untouched)
        self.assertEqual(result, resolve(result, [], [review]))
        self.assertEqual(original, resolve(result, [], []))
        self.assertEqual('unknown', result['relationships']['parents'][1]['status'])
        self.assertEqual(original, resolve(original, [], [{**review, 'publication_status': 'draft'}]))
        with self.assertRaisesRegex(ValueError, 'assertion_id'):
            resolve(original, [], [{k: v for k, v in review.items() if k != 'assertion_id'}])

    def test_standalone_publication_updates_derived_mirrors_not_only_html_build(self):
        original = {'id': 'Example-1', 'vitals': {'birth': {'place': 'Import'}}, 'relationships': {},
                    'presentation': {'vitals': {'birth': {'place': 'Display only'}}, 'opening': 'Keep the layout'}}
        review = {'id': 'review', 'subject': 'Example-1', 'status': 'approved',
                  'vitals': {'birth': {'place': None, 'date': None, 'status': 'identity-dependent'}}}
        current = resolve(original, [review])
        self.assertEqual(current['vitals'], current['presentation']['vitals'])
        self.assertEqual('Keep the layout', current['presentation']['opening'])


if __name__ == '__main__':
    unittest.main()
