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
        self.write('research/ancestry-connections/strategy.json', {'variants': ['Example']})
        self.write('research/relationship_assessments.json', [])
        self.write('research/relationship_probability_estimates.json', {'estimates': []})

    def write(self, path, value):
        (self.root / path).write_text(json.dumps(value))

    def person(self, ident, parents=(), surname='Example'):
        self.index.append({'id': ident, 'birth_surnames': [surname],
                           'json_url': '/people/' + ident.lower() + '.json'})
        self.write('www/people/' + ident.lower() + '.json', {
            'id': ident, 'name': ident, 'vitals': {'birth': {'date': '1600'}},
            'relationships': {'parents': list(parents)}})

    def father(self, ident, **changes):
        return {**dict(id=ident, name='Named ' + ident, relationship='father', status='uncertain'),
                **changes}

    def finish(self):
        self.write('www/data/people-index.json', self.index)
        self.write('www/data/ancestry-connectivity.json', {'cohorts': {'1850': {'working': {
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


if __name__ == '__main__':
    unittest.main()
