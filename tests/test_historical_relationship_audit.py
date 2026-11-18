import json
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import build_relationship_audit

ROOT=Path(__file__).resolve().parents[1]


class RelationshipAuditTests(unittest.TestCase):
    def test_backfills_retain_actual_prior_grade_and_source_pairs(self):
        ledger=json.loads((ROOT/'research/latest-findings.json').read_text())['findings']
        reviewed=[f for f in ledger if f['id'].startswith('certainty-review-')]
        self.assertEqual(29,len(reviewed))
        self.assertEqual(24,sum(c['before']=='unmarked' for f in reviewed for c in f['relationship_changes']))
        self.assertEqual(5,sum(c['before']=='uncertain' for f in reviewed for c in f['relationship_changes']))
        pairs=[]
        for f in reviewed:
            c=f['relationship_changes'][0]
            self.assertTrue(c['previous_status_provenance'])
            self.assertTrue(f['sources'])
            pairs.append((c['subject'],c['relative']))
        self.assertEqual(len(pairs),len(set(pairs)))

    def test_audit_counts_and_links_only_promotions_to_certain(self):
        change = {'before': 'unmarked', 'after': 'certain', 'relationship': 'father',
                  'subject': 'Child Example-1', 'relative': 'Parent Example-2',
                  'explanation': 'The source supports the exact relationship.', 'probability_percent': 96}
        finding = {'id': 'mixed-grades', 'found_on': '2026-11-01', 'finding': 'Three links reviewed.',
                   'relationship_changes': [
                       change,
                       dict(change, before='certain', previous_probability_percent=95,
                            subject='Already certain Example-3'),
                       dict(change, after='probable', subject='Still probable Example-4'),
                   ]}
        with tempfile.TemporaryDirectory() as directory:
            web = Path(directory)
            (web / 'about').mkdir()
            (web / 'about/index.html').write_text('<html><head><title>About</title></head><body><main></main></body></html>')
            with patch('tools.build_relationship_audit.research_data.latest_findings', return_value={'findings': [finding]}):
                result = build_relationship_audit.build(web)
            self.assertEqual({'relationship_audit_rows': 1, 'exact_prior_transitions': 0,
                              'previously_ungraded': 1}, result)
            page = (web / 'research/relationship-audit/index.html').read_text()
            self.assertIn('Unmarked (previously ungraded) → Certain (96%)', page)
            self.assertIn('/latest-findings/page/1/#finding-mixed-grades', page)
            self.assertNotIn('Already certain Example-3', page)
            self.assertNotIn('Still probable Example-4', page)

    def test_audit_assessment_pointers_match_actual_people(self):
        audit=json.loads((ROOT/'research/historical-relationship-audit-2026-09-30.json').read_text())
        assessed=json.loads((ROOT/'research/relationship_assessments.json').read_text())
        for row in audit['additional_exact_uncertain_to_confident']+audit['unmarked_to_confident']:
            ids={re.search(r'[A-Za-z]+-\d+',row[key])[0] for key in ['subject','relative']}
            pointers=[s for s in row['source_refs'] if s.startswith('research/relationship_assessments.json#/')]
            self.assertTrue(pointers)
            for pointer in pointers:self.assertEqual(ids,set(assessed[int(pointer.rsplit('/',1)[1])]['people']))
