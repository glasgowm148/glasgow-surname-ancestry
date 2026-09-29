"""One scoped father hypothesis across human and machine destinations."""
from copy import deepcopy
import json
from pathlib import Path
import unittest
from urllib.parse import urlsplit

from bs4 import BeautifulSoup
from tools.publish_resolved_dossiers import resolve
from tools import evidence_labels

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / 'www'
ASSERTION = 'C-robert-alexander-father-hypothesis'


def load(path):
    return json.loads(path.read_text())


class RobertHypothesisExportsTests(unittest.TestCase):
    def test_meaning_agrees_across_html_dossier_and_network(self):
        assessment = next(a for a in load(ROOT / 'research/relationship_assessments.json')
                          if a.get('assertion_id') == ASSERTION)
        for profile, target, group, old in (
            ('Glasgow-951', 'Glasgow-1367', 'parents', 'C-b48375a01529'),
            ('Glasgow-1367', 'Glasgow-951', 'children', 'C-ad51f3d1462c'),
        ):
            dossier = load(WEB / f'people/{profile.lower()}.json')
            network = load(WEB / f'people/{profile.lower()}.network.json')
            html = BeautifulSoup((WEB / f'people/{profile.lower()}.html').read_text(), 'html.parser')
            row = next(r for r in dossier['relationships'][group] if r['id'] == target)
            network_row = next(r for r in network['relationships'] if r['id'] == target)
            self.assertEqual(row, network_row)
            self.assertEqual('possible', row['status'])
            self.assertEqual('open', row['hypothesis_status'])
            self.assertEqual('current', row['lifecycle'])
            self.assertEqual(ASSERTION, row['claim_id'])
            self.assertEqual(assessment['reason'], row['reason'])
            self.assertEqual(assessment['source_ids'], row['source_ids'])
            self.assertIn('no ages, wife or kinship', row['limitations'])
            node = html.select_one(f'#family tr[data-claim-id="{ASSERTION}"]')
            # Pages show the curated label in the canonical vocabulary (tools/evidence_labels.py).
            self.assertEqual(evidence_labels.normalise_status_label(row["status"], row["status_label"]), node.select_one('.status-label').text)
            self.assertIn(row['reason'], node.text)
            for document in (dossier, network):
                claim = next(c for c in document['claims'] if c['id'] == ASSERTION)
                self.assertEqual('current', claim['lifecycle'])
                self.assertEqual(assessment['limitations'], claim['limitations'])
                historical = next(c for c in document['claims'] if c['id'] == old)
                self.assertEqual('historical', historical['lifecycle'])
                self.assertEqual('superseded', historical['status'])
                self.assertEqual(ASSERTION, historical['superseded_by'])
                self.assertTrue(any(r['claim_id'] == old for r in document['relationship_history']))
                self.assertIn('imported', document)
            imported = next(c for c in dossier['imported']['sections']['claims'] if c['id'] == old)
            self.assertNotEqual(ASSERTION, imported['id'])
            record_ids = {r['record_id'] for r in dossier['presentation']['record_associations']}
            self.assertTrue(set(row['source_ids']).issubset(record_ids))
            for link in row['analysis_links']:
                url = urlsplit(link['href'])
                page = BeautifulSoup((WEB / url.path.lstrip('/')).read_text(), 'html.parser')
                self.assertIsNotNone(page.find(id=url.fragment))
                self.assertTrue(node.select(f'a[href="{link["href"]}"]'))

    def test_current_comparison_and_identity_scope_do_not_restore_the_couple(self):
        dossier = load(WEB / 'people/glasgow-951.json')
        parents = dossier['relationships']['parents']
        catherine = next(r for r in parents if r['id'] == 'Unknown-540856')
        self.assertEqual('unknown', catherine['status'])
        self.assertEqual('alternative', catherine['display'])
        self.assertNotIn('hypothesis_status', catherine)
        candidates = {c['id']: c for c in dossier['presentation']['parent_candidates']}
        active = candidates['unidentified-lisnagaver-robert']
        claim = next(c for c in dossier['claims'] if c['id'] == ASSERTION)
        self.assertEqual(ASSERTION, active['assertion_id'])
        self.assertEqual(claim['hypothesis_status'], active['state'])
        self.assertEqual(claim['claim'], active['assessment'])
        self.assertEqual(claim['limitations'], active['objections'])
        self.assertEqual('superseded', candidates['retired-robert-catherine-attachment']['state'])
        old_reasoning = next(c for c in dossier['claims'] if c['id'] == 'C-d7cae2ea03a1')
        self.assertEqual('historical', old_reasoning['lifecycle'])
        self.assertIn('Coltrim', old_reasoning['notes'])  # Original text preserved.
        robert = load(WEB / 'people/glasgow-1367.json')['presentation']
        self.assertEqual('conflict', robert['resolution']['state'])
        self.assertEqual('identity-dependent', robert['vitals']['birth']['status'])
        self.assertIn('transfer to Lisnagaver unproved', robert['vitals']['birth']['qualifier'])

    def test_resolution_is_idempotent_and_not_a_global_status_replacement(self):
        shared = load(ROOT / 'research/relationship_assessments.json')
        reviews = load(WEB / 'assets/research/assessments.json')['assessments']
        for slug in ('glasgow-951', 'glasgow-1367'):
            dossier = load(WEB / f'people/{slug}.json')
            before = deepcopy(dossier)
            current = resolve(dossier, reviews, shared)
            self.assertEqual(before, dossier)
            self.assertEqual(current, resolve(current, reviews, shared))
            self.assertEqual(before['imported'], current['imported'])
        other = {'id': 'Other-1', 'relationships': {'parents': [{'id': 'Other-2', 'status': 'superseded'}]}, 'claims': []}
        self.assertEqual(other, resolve(other, [], shared))


if __name__ == '__main__':
    unittest.main()
