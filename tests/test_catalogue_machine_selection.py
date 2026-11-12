import unittest
from unittest.mock import patch

from tools import catalogue_machine_data as machine


class SelectedDossierTests(unittest.TestCase):
    def test_public_review_state_excludes_private_fields_and_unreviewed_plans(self):
        plans = {
            'Fable-1': {'research_state': {
                'reviewed': '2026-10-26', 'disposition': 'reviewed_no_change',
                'last_test': 'Census already checked.', 'next_test': 'Inspect the lease.',
                'resume_when': 'The original lease is available.',
                'private_capture': 'Do not export', 'credentials': 'Do not export'}},
            'Fable-2': {'research_state': {'next_test': 'Unreviewed lead'}},
            'Private-1': {'research_state': {'reviewed': '2026-10-26', 'next_test': 'Private'}},
        }
        with patch.object(machine, '_research_plans', return_value=plans):
            result = machine.public_research_states({'Fable-1', 'Fable-2'})
        self.assertEqual(set(result), {'Fable-1'})
        self.assertEqual(result['Fable-1']['next_test'], 'Inspect the lease.')
        self.assertNotIn('private_capture', result['Fable-1'])
        self.assertNotIn('credentials', result['Fable-1'])

    def test_selected_child_retains_unselected_parent_context(self):
        child = dict(catalogue_id='fable-1', profile_ids=['Fable-1'], name='Ada Fable',
                     father=[{'id': 'Fable-2'}], records=[], wikitree_evidence=[])
        father = dict(catalogue_id='fable-2', profile_ids=['Fable-2'], name='Rowan Fable',
                      records=[], wikitree_evidence=[])
        with patch.object(machine, '_relationship_assessments', return_value=[]), \
                patch.object(machine, '_research_plans', return_value={}):
            dossiers, index = machine.build_machine_models([child, father], catalogue_ids={'fable-1'})
        self.assertEqual({'fable-1'}, set(dossiers))
        self.assertEqual(['fable-1'], [row['catalogue_id'] for row in index])
        relation = dossiers['fable-1']['relationships']['parents'][0]
        self.assertEqual(('Rowan Fable', '/people/fable-2.json'), (relation['name'], relation['json_url']))
        self.assertEqual(index[0], machine.build_compact_person_index(child, dossiers['fable-1']))
