"""Research decisions must agree in every current human/machine view."""
from copy import deepcopy
from functools import lru_cache
import json
import re
from pathlib import Path
import unittest

from bs4 import BeautifulSoup
from tests._site_html import read_html
from tests._generated_data import requires_generated_data

from tools.publish_resolved_dossiers import resolve
from tools.repair_person_hierarchy import _current_vitals
from tools import evidence_labels
from tools.relationship_probability import percentage_text

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / 'www'


@lru_cache(maxsize=None)
def load(path):
    return json.loads(path.read_text())


@lru_cache(maxsize=None)
def page_for(profile):
    return BeautifulSoup(read_html(WEB / f'people/{profile.lower()}.html'), 'html.parser')


class ResolvedPublicModelTests(unittest.TestCase):
    @requires_generated_data
    def test_all_approved_pairs_agree_across_outputs_and_preserve_history(self):
        assessments = load(ROOT / 'research/relationship_assessments.json')
        by_id = {a['assertion_id']: a for a in assessments if a.get('assertion_id')}
        canonical_ids = {record['record_id'] for record in load(ROOT / 'research/canonical_records.json')}
        for assessment in assessments:
            if assessment.get('publication_status') != 'approved':
                continue
            aid = assessment['assertion_id']
            self.assertTrue(set(assessment['source_ids']).issubset(canonical_ids), aid)
            for profile, perspective in assessment['perspectives'].items():
                with self.subTest(profile=profile, assertion=aid):
                    if not (WEB / f'people/{profile.lower()}.json').exists():
                        # An external WikiTree relative need not have a local dossier.
                        other = next(p for p in assessment['people'] if p != profile)
                        related = load(WEB / f'people/{other.lower()}.json')
                        external = next(r for rows in related['relationships'].values() for r in rows if r['id'] == profile)
                        account = assessment.get('profile_urls', {}).get(profile)
                        if account:
                            self.assertEqual(account['url'], external['url'])
                            self.assertIsNone(external['wikitree_url'])
                        else:
                            self.assertEqual(f'https://www.wikitree.com/wiki/{profile}', external['wikitree_url'])
                        continue
                    dossier = load(WEB / f'people/{profile.lower()}.json')
                    network = load(WEB / f'people/{profile.lower()}.network.json')
                    page = page_for(profile)
                    embedded = json.loads(page.select_one('pre.archive-json').text)
                    self.assertEqual(dossier['relationships'], dossier['presentation']['relationships'])
                    self.assertEqual(dossier['relationships'], embedded['relationships'])
                    self.assertEqual(dossier['claims'], embedded['claims'])
                    claim = next(c for c in dossier['claims'] if c['id'] == aid)
                    if claim.get('lifecycle') == 'historical':
                        # Approval records the publication decision; a later
                        # approved assessment may explicitly replace its scope.
                        self.assertEqual(claim, next(c for c in network['claims'] if c['id'] == aid))
                        replacement = next(c for c in dossier['claims'] if c['id'] == claim['superseded_by'])
                        self.assertEqual('current', replacement['lifecycle'])
                        self.assertIn(aid, replacement['historical_claim_ids'])
                        self.assertFalse(any(r.get('claim_id') == aid for rows in dossier['relationships'].values() for r in rows))
                        continue
                    group, row = next((group, r) for group, rows in dossier['relationships'].items() for r in rows if r.get('claim_id') == aid)
                    self.assertEqual(row, next(r for r in network['relationships'] if r.get('claim_id') == aid))
                    self.assertEqual(row['status'], assessment['status'])
                    self.assertEqual(row['relationship'], perspective['relationship'])
                    self.assertEqual(row['reason'], perspective.get('reason') or assessment['reason'])
                    self.assertEqual(row['source_ids'], assessment['source_ids'])
                    self.assertEqual(claim, next(c for c in network['claims'] if c['id'] == aid))
                    for key in ('status', 'reason', 'source_ids', 'relationship', 'status_label'):
                        self.assertEqual(claim[key], row[key])
                    html_row = page.select_one(f'#family tr[data-claim-id="{aid}"]')
                    self.assertIsNotNone(html_row)
                    # Inactive hypotheses must remain visibly separate, with
                    # their actual grade and percentage still inspectable.
                    label = evidence_labels.normalise_status_label(row["status"], row["status_label"])
                    inactive = (row.get('display') in {'alternative', 'historical', 'superseded'}
                                or row.get('lifecycle') in {'alternative', 'historical', 'superseded'})
                    family_group = html_row.find_parent(attrs={'data-group': True})
                    self.assertIsNotNone(family_group)
                    self.assertEqual(inactive, family_group['data-group'].startswith('alternative-'))
                    if inactive:
                        label = f'Earlier or alternative {row["relationship"]} · {evidence_labels.label(row["status"])}'
                    if group == 'parents':
                        label = re.sub(r'\s*·\s*\d+%$', '', label)
                        label += ' · ' + percentage_text(row['probability'])
                    self.assertEqual(label, html_row.select_one('.status-label').text)
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
                        if old_id in by_id:
                            previous = by_id[old_id]
                            self.assertEqual(previous['perspectives'][profile].get('reason') or previous['reason'], old['reason'])
                        else:
                            self.assertTrue(any(c['id'] == old_id for c in dossier['imported']['sections']['claims']))

    @requires_generated_data
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
        unreviewed = resolve(original, [], [])  # Derived probability metadata also exists without a review.
        result = resolve(original, [], [review])
        self.assertEqual(original, untouched)
        self.assertEqual(result, resolve(result, [], [review]))
        self.assertEqual(unreviewed, resolve(result, [], []))
        self.assertEqual('unknown', result['relationships']['parents'][1]['status'])
        self.assertEqual(unreviewed, resolve(original, [], [{**review, 'publication_status': 'draft'}]))
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
