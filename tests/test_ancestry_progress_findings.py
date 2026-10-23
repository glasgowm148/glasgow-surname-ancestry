import json
from pathlib import Path
import subprocess
import unittest

from tools.build_ancestry_progress import individual_finding_rows


class IndividualFindingTests(unittest.TestCase):
    def rows(self, history, value=95, **extra):
        nodes = {key: dict(name=key, url=f'/people/{key.lower()}.html')
                 for key in ['Glasgow-875', 'Glasgow-653', 'record-son']}
        child = extra.pop('child', 'Glasgow-875')
        identity_hold_ids = extra.pop('identity_hold_ids', ())
        assertion = dict(assertion_id='selected', publication_status='approved',
                         status='strongly_supported', assessment_date='2026-10-22',
                         probability={'value': value / 100}, assessment_history=history,
                         **extra)
        edges = [dict(child=child, father='Glasgow-653', assertion_id='selected', confidence_percent=value)]
        return individual_finding_rows(nodes, edges, {'selected': assertion},
                                       {'1850': {'working': {'cohort_ids': ['Glasgow-875']}}},
                                       {'Glasgow-875'}, identity_hold_ids)

    def test_exact_pair_change_date_and_preserved_prior(self):
        history = [{'status': 'unmarked', 'probability_percent': None},
                   {'status': 'probable', 'probability_percent': 71, 'assessment_date': '2026-10-22'}]
        rows = self.rows(history)
        self.assertEqual([(r['kind'], r['before_percent'], r['after_percent']) for r in rows],
                         [('first', None, 71), ('change', 71, 95)])
        self.assertEqual(rows[-1]['date'], '2026-10-22')
        self.assertEqual(rows[-1]['father']['id'], 'Glasgow-653')
        self.assertEqual(rows[-1]['previous_assessment']['status'], 'probable')
        self.assertEqual(rows[-1]['cohorts'], ['1850'])
        self.assertTrue(rows[-1]['baseline'])
        self.assertIn('wikitree_url', rows[-1]['child'])

    def test_decrease_and_within_band_are_changes(self):
        for before, after in [(95, 71), (71, 74)]:
            row = next(r for r in self.rows([{'percent': before}], after) if r['kind'] == 'change')
            self.assertEqual((row['kind'], row['before_percent'], row['after_percent']), ('change', before, after))

    def test_nested_probability_and_no_invented_date(self):
        rows = self.rows([{'probability': {'value': .71}}])
        self.assertIsNone(rows[1]['date'])
        self.assertEqual(rows[0]['before_percent'], 71)

    def test_new_record_person_has_local_link_and_identity_hold(self):
        row = self.rows([], 97, child='record-son', identity_hold_ids={'record-son'}, provenance={'new_local_documentary_person': True})[0]
        self.assertEqual(row['kind'], 'new')
        self.assertNotIn('wikitree_url', row['child'])
        self.assertTrue(row['identity_hold'])
        self.assertEqual(row['cohorts'], [])
        self.assertFalse(row['baseline'])

    def test_creation_ready_record_person_is_not_held(self):
        row = self.rows([], 97, child='record-son', provenance={'new_local_documentary_person': True})[0]
        self.assertFalse(row['identity_hold'])
        self.assertNotIn('wikitree_url', row['child'])

    def test_explicit_new_father_for_existing_person_is_not_first_grading(self):
        row = self.rows([{'status': 'unknown', 'probability_percent': None}], 42,
                        provenance={'new_father_attachment': True})[-1]
        self.assertEqual(row['kind'], 'new')
        self.assertIsNone(row['before_percent'])
        self.assertEqual(row['after_percent'], 42)
        self.assertIn('wikitree_url', row['child'])

    def test_replaced_parent_percent_is_not_previous_pair_rating(self):
        row = self.rows([{'relative_id': 'Other-1', 'percent': 71}])[-1]
        self.assertEqual(row['kind'], 'new')
        self.assertIsNone(row['before_percent'])

    def test_javascript_filters_changes_and_selected_baseline(self):
        script = """
const {individualFindings:f} = require('./tools/ancestry_progress.js');
const rows=[{kind:'change',baseline:true,cohorts:['1850']},{kind:'first',baseline:true,cohorts:['1850']},{kind:'change',baseline:false,cohorts:['1900']}];
process.stdout.write(JSON.stringify([f(rows,'change','fixed').length,f(rows,'all','1850').length,f(rows,'change','1850',true).length]));
"""
        result = subprocess.run(['node', '-e', script], check=True, capture_output=True, text=True)
        self.assertEqual(json.loads(result.stdout), [1, 2, 2])

    def test_real_william_selected_assessment(self):
        assessments = json.loads(Path('research/relationship_assessments.json').read_text())
        assertion = next(a for a in assessments if a['assertion_id'] == 'C-coverage-20261022c-glasgow-875-father')
        rows = self.rows(assertion['assessment_history'])
        self.assertEqual((rows[-1]['before_percent'], rows[-1]['after_percent']), (71, 95))


if __name__ == '__main__':
    unittest.main()
