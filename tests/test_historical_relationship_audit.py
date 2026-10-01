import json
import re
import unittest
from pathlib import Path

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

    def test_audit_assessment_pointers_match_actual_people(self):
        audit=json.loads((ROOT/'research/historical-relationship-audit-2026-09-30.json').read_text())
        assessed=json.loads((ROOT/'research/relationship_assessments.json').read_text())
        for row in audit['additional_exact_uncertain_to_confident']+audit['unmarked_to_confident']:
            ids={re.search(r'[A-Za-z]+-\d+',row[key])[0] for key in ['subject','relative']}
            pointers=[s for s in row['source_refs'] if s.startswith('research/relationship_assessments.json#/')]
            self.assertTrue(pointers)
            for pointer in pointers:self.assertEqual(ids,set(assessed[int(pointer.rsplit('/',1)[1])]['people']))
