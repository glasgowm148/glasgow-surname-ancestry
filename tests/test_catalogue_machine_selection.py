import unittest
from unittest.mock import patch

from tools import catalogue_machine_data as machine


class SelectedDossierTests(unittest.TestCase):
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
