import contextlib
import io
import json
import os
from pathlib import Path
import runpy
import tempfile
import unittest

from tools.branch_connectivity import load_public_nodes


RANK = runpy.run_path(str(Path(__file__).resolve().parents[1] /
                         'research/ancestry-connections/rank_working_joins.py'))


class UnratedFatherCoverage(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for relative in ('www/data', 'www/people', 'www/assets/research', 'research/ancestry-connections'):
            (self.root / relative).mkdir(parents=True)
        self.index = []
        self.cohorts = None
        self.write('research/ancestry-connections/strategy.json', {'variants': ['Example']})
        self.write('research/relationship_assessments.json', [])
        self.write('research/relationship_probability_estimates.json', {'estimates': []})

    def write(self, path, value):
        (self.root / path).write_text(json.dumps(value))

    def person(self, ident, parents=(), surname='Example', year=1600):
        self.index.append({'id': ident, 'birth_surnames': [surname],
                           'json_url': '/people/' + ident.lower() + '.json'})
        self.write('www/people/' + ident.lower() + '.json', {
            'id': ident, 'name': ident, 'vitals': {'birth': {'date': str(year)}},
            'relationships': {'parents': list(parents)}})

    def father(self, ident, **changes):
        return {**dict(id=ident, name='Named ' + ident, relationship='father', status='uncertain'),
                **changes}

    def finish(self):
        self.write('www/data/people-index.json', self.index)
        self.write('www/data/ancestry-connectivity.json', {'cohorts': self.cohorts or {'1850': {'working': {
            'cohort_ids': [r['id'] for r in self.index if r['birth_surnames'] == ['Example']]}}}})

    def rank(self, *args):
        self.finish()
        previous = Path.cwd()
        try:
            os.chdir(self.root)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                RANK['main'](list(args))
            return json.loads(output.getvalue())
        finally:
            os.chdir(previous)

    def test_external_surname_and_missing_dossier_have_null_graph_impact(self):
        self.person('Child-1', [self.father('Other-1', tree_relationship=True, status='probable')])
        self.person('Other-1', surname='Other')
        self.person('Child-2', [self.father('Missing-1', tree_relationship=True)])
        for order in ('actionable', 'working-pairs', 'confident-gain'):
            with self.subTest(order=order):
                rows = self.rank('--scope', 'unrated', '--sort', order)
                self.assertEqual([(r['child'], r['father']) for r in rows],
                                 [('Child-1', 'Other-1'), ('Child-2', 'Missing-1')])
                for row in rows:
                    self.assertFalse(row['graph_impact_available'])
                    self.assertEqual(row['father_name'], 'Named ' + row['father'])
                    for key in ('child_side', 'parent_side', 'cross_pairs', 'confident_child_side',
                                'confident_parent_side', 'confident_pair_gain', 'confident_component_reduction'):
                        self.assertIsNone(row[key], key)
        retained = []
        default = load_public_nodes(self.root / 'www', {'Example'})
        coverage = load_public_nodes(self.root / 'www', {'Example'}, retained_fathers=retained)
        self.assertEqual(default, coverage, 'coverage collection changed graph or population')
        self.assertEqual(len(retained), 2)

    def test_unselected_and_explicit_alternatives_are_excluded(self):
        self.person('Child-1', [self.father('Selected-1', tree_relationship=True),
                                self.father('Unselected-1'),
                                self.father('Alternative-1', display='alternative')])
        rows = self.rank('--scope', 'unrated')
        self.assertEqual([r['father'] for r in rows], ['Selected-1'])

    def test_approved_working_selection_and_conflicting_selections_reuse_loader(self):
        selected = dict(publication_status='approved', working_selection=True)
        self.person('Child-1', [self.father('Former-1', tree_relationship=True),
                                self.father('Replacement-1', **selected)])
        self.person('Child-2', [self.father('Conflict-1', **selected), self.father('Conflict-2', **selected)])
        rows = self.rank('--scope', 'unrated')
        self.assertEqual([(r['child'], r['father']) for r in rows], [('Child-1', 'Replacement-1')])

    def test_reviewed_external_percentage_excludes_pair_from_unrated(self):
        self.person('Child-1', [self.father('Other-1', tree_relationship=True, status='probable')])
        self.write('www/assets/research/relationship-probabilities.json', {'estimates': [
            dict(subject_id='Child-1', relative_id='Other-1', relationship='father',
                 percent=83, assessment_status='probable', basis='Reviewed pair evidence')]})
        self.assertEqual(self.rank('--scope', 'unrated'), [])

    def test_anonymous_retained_father_is_not_named_coverage(self):
        self.person('Child-1', [self.father('Placeholder-1', name='Unknown Glasgow', tree_relationship=True)])
        self.assertEqual(self.rank('--scope', 'unrated'), [])
        retained = []
        load_public_nodes(self.root / 'www', {'Example'}, retained_fathers=retained)
        self.assertEqual(retained[0]['father'], 'Placeholder-1', 'graph selection still retains placeholder')

    def test_current_database_estimate_closes_private_queue_gap_before_publication(self):
        self.person('Child-1', [self.father('Father-1', tree_relationship=True, status='possible')])
        self.person('Father-1')
        self.write('research/relationship_probability_estimates.json', {'estimates': [dict(
            subject_id='Child-1', relative_id='Father-1', relationship='father', percent=25,
            assessment_status='uncertain', source_ids=['reviewed-source'])]})
        self.assertEqual(self.rank('--scope', 'unrated'), [])
        row, = self.rank('--scope', 'all-unconfident')
        self.assertEqual(row['confidence_percent'], 25)
        self.assertEqual(row['status'], 'uncertain')
        self.assertEqual(row['source_ids'], ['reviewed-source'])
        self.assertIsNone(row['public_confidence_percent'])
        self.assertEqual(row['public_status'], 'possible')
        self.assertEqual(row['cross_pairs'], 1)
        # A review of an alternative father never grades the retained pair.
        self.write('research/relationship_probability_estimates.json', {'estimates': [dict(
            subject_id='Child-1', relative_id='Alternative-1', relationship='father', percent=90)]})
        row, = self.rank('--scope', 'unrated')
        self.assertEqual(row['father'], 'Father-1')
        self.assertIsNone(row['confidence_percent'])

    def test_existing_graph_modes_and_impact_values_are_preserved(self):
        self.person('Child-1', [self.father('Father-1')])
        self.person('Father-1')
        self.person('Child-2', [self.father('Missing-1', tree_relationship=True)])
        self.write('research/relationship_assessments.json', [dict(
            assertion_id='A-selected', publication_status='approved', working_selection=True,
            people=['Child-1', 'Father-1'], perspectives={'Child-1': {'relationship': 'father'}})])
        for scope in ('selected', 'all-unconfident'):
            rows = self.rank('--scope', scope)
            self.assertEqual([(r['child'], r['father']) for r in rows], [('Child-1', 'Father-1')])
            self.assertEqual(rows[0]['cross_pairs'], 1)
            self.assertNotIn('graph_impact_available', rows[0])
        rows = self.rank('--scope', 'unrated')
        self.assertEqual(rows[0]['child'], 'Child-1')
        self.assertTrue(rows[0]['graph_impact_available'])
        self.assertEqual(rows[0]['cross_pairs'], 1)
        self.assertIsNone(rows[1]['cross_pairs'])

    def test_unknown_scope_uses_public_listing_and_real_descendant_reach(self):
        self.person('Root-1')
        self.person('Child-1', [self.father('Root-1')])
        self.person('Child-2', [self.father('Root-1')])
        self.person('Grandchild-1', [self.father('Child-1')])
        self.person('Named-1', [self.father('External-1', tree_relationship=True)])
        self.person('External-1', surname='Other')
        self.person('Anonymous-1', [self.father('Placeholder-1', name='Unknown Glasgow', tree_relationship=True)])
        self.person('AlternativeOnly-1', [self.father('Alternative-1', display='alternative')])
        rows = self.rank('--scope', 'unknown')
        self.assertEqual({r['child'] for r in rows}, {'Root-1', 'Anonymous-1', 'AlternativeOnly-1'})
        root = rows[0]
        self.assertEqual((root['child'], root['known_child_count'], root['known_descendant_count'], root['child_side']),
                         ('Root-1', 2, 3, 4))
        self.assertEqual(root['child_url'], '/people/root-1.html')
        for row in rows:
            self.assertIsNone(row['father'])
            self.assertTrue(row['unknown_father'])
            for key in ('parent_side', 'cross_pairs', 'confident_child_side', 'confident_parent_side',
                        'confident_pair_gain', 'confident_component_reduction'):
                self.assertIsNone(row[key], key)

    def test_unknown_scope_through_limits_descendants_to_saved_early_cohort(self):
        self.person('Root-1', year=1450)
        self.person('Child-1', [self.father('Root-1')], year=1480)
        self.person('Later-1', [self.father('Root-1')], year=1600)
        self.cohorts = {'1500': {'working': {'cohort_ids': ['Root-1', 'Child-1']}},
                        '1850': {'working': {'cohort_ids': ['Root-1', 'Child-1', 'Later-1']}}}
        early = self.rank('--scope', 'unknown', '--through', '1500')[0]
        full = self.rank('--scope', 'unknown')[0]
        self.assertEqual((early['known_child_count'], early['known_descendant_count'], early['earliest_cohort_cutoff']), (1, 1, 1500))
        self.assertEqual(full['known_descendant_count'], 2)

    def test_documentary_origin_root_keeps_route_and_missing_account_is_not_unknown(self):
        self.person('Child-1', [self.father('record-origin-1447')], year=1475)
        self.write('www/data/ancestry-documentary-people.json', {'people': [
            dict(id='record-origin-1447', name='Origin 1447', publication_status='approved',
                 url='/free-space/origin-1447/', first_record_year=1447, source_ids=['S1'])]})
        rows = self.rank('--scope', 'unknown')
        self.assertEqual(len(rows), 1)
        origin = rows[0]
        self.assertEqual(origin['child'], 'record-origin-1447')
        self.assertEqual(origin['child_url'], '/free-space/origin-1447/')
        self.assertIsNone(origin['unknown_father'])
        self.assertEqual(origin['father_listing_status'], 'unavailable')
        self.assertFalse(origin['cohort_member'])
        self.assertIn('outside measured population', origin['population_basis'])
        self.assertEqual((origin['known_child_count'], origin['known_descendant_count'], origin['child_side']), (1, 1, 1))

    def test_unknown_readiness_uses_explicit_person_plan_without_parent_assertion(self):
        self.person('Root-1')
        self.person('Child-1', [self.father('Root-1')])
        self.person('Other-1')
        path = self.root / 'research/Root-1'; path.mkdir()
        self.write('research/Root-1/research_plan.json', {
            'research_state': {'disposition': 'awaiting_source', 'resume_when': 'New parent clause'},
            'last_test': 'Held record exhausted', 'next_test': 'Read new deed'})
        rows = self.rank('--scope', 'unknown')
        self.assertEqual([r['child'] for r in rows], ['Other-1', 'Root-1'])
        held = rows[1]
        self.assertEqual(held['research_state']['disposition'], 'awaiting_source')
        self.assertEqual((held['last_test'], held['next_test']), ('Held record exhausted', 'Read new deed'))
        self.assertIsNone(held['father'])
        self.assertIsNone(held['assertion_id'])
        self.assertEqual(self.rank('--scope', 'unknown', '--sort', 'working-pairs')[0]['child'], 'Root-1')


if __name__ == '__main__':
    unittest.main()
