import json
from pathlib import Path
import subprocess
import unittest

from tools.build_ancestry_progress import individual_finding_rows, pending_father_changes, named_father_review_counts


class IndividualFindingTests(unittest.TestCase):
    def rows(self, history, value=95, **extra):
        nodes = {key: dict(name=key, url=f'/people/{key.lower()}.html')
                 for key in ['Glasgow-875', 'Glasgow-653', 'record-son']}
        child = extra.pop('child', 'Glasgow-875')
        identity_hold_ids = extra.pop('identity_hold_ids', ())
        father_changes = extra.pop('father_changes', None)
        assertion = dict(assertion_id='selected', publication_status='approved',
                         status='strongly_supported', assessment_date='2026-10-22',
                         probability={'value': value / 100}, assessment_history=history,
                         **extra)
        edges = [dict(child=child, father='Glasgow-653', assertion_id='selected', confidence_percent=value)]
        return individual_finding_rows(nodes, edges, {'selected': assertion},
                                       {'1850': {'working': {'cohort_ids': ['Glasgow-875']}}},
                                       {'Glasgow-875'}, identity_hold_ids, father_changes)

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
        self.assertIsNone(rows[0]['research_event'])
        self.assertEqual(rows[-1]['research_event']['type'], 'confidence_change')
        self.assertEqual(rows[-1]['research_event']['date'], '2026-10-22')

    def test_first_grade_for_newly_indexed_documentary_person_is_not_improvement(self):
        rows=self.rows([],child='record-son',provenance={'new_local_documentary_person':True})
        self.assertEqual(rows[0]['kind'],'new')
        self.assertIsNone(rows[0]['research_event'])

    def test_attachment_uses_checked_attachment_date_not_later_first_rating(self):
        rows=self.rows([],provenance={'new_father_attachment':True,'new_father_attachment_reviewed':'2026-10-16'})
        self.assertEqual(rows[0]['research_event']['type'],'father_attachment')
        self.assertEqual(rows[0]['research_event']['date'],'2026-10-16')

    def test_first_percentage_counts_when_saved_qualitative_confidence_changed(self):
        for before, expected in [('uncertain', 'confidence_change'), ('confident', None), ('unmarked', None)]:
            row = self.rows([{'status': before, 'source_basis': 'Saved prior public assessment'}])[0]
            self.assertIsNone(row['before_percent'])
            self.assertEqual((row['research_event'] or {}).get('type'), expected)
            if expected:
                self.assertEqual(row['research_event']['before_grade'], 'uncertain')

    def test_catalogue_add_and_replace_are_findings_without_attachment_flag(self):
        for action in ['add', 'replace']:
            changes = pending_father_changes([dict(map_key='Glasgow-875', needs_wikitree_update=True,
                wikitree_update_relationship_changes=[dict(action=action,relationship='father',relative_id='Glasgow-653',
                    assertion_id='selected',previous_status='uncertain',previous_relative_id='Other-1')])])
            row = self.rows([], father_changes=changes)[0]
            self.assertEqual(row['kind'], 'new')
            self.assertEqual(row['research_event']['type'], 'father_attachment' if action=='add' else 'father_replacement')
            self.assertEqual(row['research_event']['before_grade'], 'unknown' if action=='add' else 'uncertain')

    def test_catalogue_prior_grade_provenance_can_supply_unmeasured_before_state(self):
        changes = {('glasgow-875','glasgow-653','selected'):
                   dict(action='regrade',previous_status='uncertain',previous_status_provenance='Saved prior profile assessment')}
        row=self.rows([],father_changes=changes)[0]
        self.assertEqual(row['research_event']['before_grade'],'uncertain')
        self.assertIsNone(row['before_percent'])

    def test_record_subject_matches_public_id_rather_than_unprefixed_map_key(self):
        changes=pending_father_changes([dict(id='record-son',map_key='son',needs_wikitree_update=True,
            wikitree_update_relationship_changes=[dict(action='add',relationship='father',relative_id='Glasgow-653',assertion_id='selected')])])
        row=self.rows([],child='record-son',father_changes=changes)[0]
        self.assertEqual(row['research_event']['type'],'father_attachment')

    def test_text_prior_provenance_does_not_invent_an_earlier_grade(self):
        row=self.rows([],provenance={'prior_assessment':'Prior report; no structured assessment'})[0]
        self.assertIsNone(row['previous_assessment'])
        self.assertIsNone(row['research_event'])

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

    def test_selected_former_alternative_keeps_prior_pair_rating(self):
        prior = dict(status='uncertain', probability_percent=18,
                     assessment_date='2026-10-22', lifecycle='alternative',
                     working_selection=False, relative_id='Glasgow-653')
        for after in [18, 38]:
            rows = self.rows([prior], after, provenance={'new_father_attachment': True})
            self.assertEqual(len(rows), 1)
            self.assertEqual((rows[0]['kind'], rows[0]['before_percent'], rows[0]['after_percent']),
                             ('new', 18, after))
            self.assertEqual(rows[0]['previous_assessment']['lifecycle'], 'alternative')

    def test_existing_selected_percentage_change_is_not_new(self):
        prior = dict(probability_percent=71, working_selection=True)
        row = next(row for row in self.rows([prior], provenance={'new_father_attachment': True})
                   if row['after_percent'] == 95)
        self.assertEqual((row['kind'], row['before_percent'], row['after_percent']),
                         ('change', 71, 95))

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


class NamedFatherReviewCoverageTests(unittest.TestCase):
    def test_external_named_fathers_count_without_changing_graph_metrics(self):
        # The loader supplies retained selections before graph boundaries; no graph is needed.
        retained = [dict(child='rated', father='outside', father_name='Named External', confidence_percent=83),
                    dict(child='ungraded', father='missing', father_name='Named Missing'),
                    dict(child='later', father='other', father_name='Named Later', confidence_percent=91),
                    dict(child='anonymous', father='placeholder', father_name='Unknown Glasgow', confidence_percent=90)]
        self.assertEqual(named_father_review_counts(['rated', 'ungraded', 'anonymous'], retained),
                         dict(named_count=2, rated_count=1, unrated_count=1, coverage_percent=50.0))
        self.assertEqual(named_father_review_counts([], retained)['coverage_percent'], None)


if __name__ == '__main__':
    unittest.main()
