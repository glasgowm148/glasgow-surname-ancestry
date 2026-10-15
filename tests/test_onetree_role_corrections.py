import unittest
from copy import deepcopy
from tools.site_sources.onetree.build import apply_reviewed_parent_replacements


class ReviewedParentCorrectionTests(unittest.TestCase):
    def fixture(self):
        people = [dict(id='Child-1',name='Child',parents=[dict(id='Sibling-1',role='father')]),
                  dict(id='Sibling-1',name='Sibling',parents=[dict(id='Father-1',role='father')],
                       childrenRecorded=[dict(id='Child-1'),dict(id='OtherChild-1')]),
                  dict(id='Father-1',name='Father',parents=[])]
        sibling = dict(assertion_id='sibling',people=['Child-1','Sibling-1'],publication_status='approved',
                       source_ids=['will'],role_correction={'Child-1':{'from':['father'],'to':'sibling'}})
        parent = dict(assertion_id='father',publication_status='approved',status='strongly_supported',
                      source_ids=['roll','will'],basis='Combined father and sister statements',
                      perspectives={'Child-1':{'relationship':'father'}},tree_parent_replacement=dict(
                          child='Child-1',father='Father-1',previous_parent='Sibling-1',
                          role_correction_assertion='sibling',reason='Sibling was previously shown as father'))
        return people,[sibling,parent]

    def test_supported_replacement_preserves_previous_role(self):
        people,reviews=self.fixture();old=deepcopy(people[0]['parents'])
        self.assertEqual(apply_reviewed_parent_replacements(people,reviews),['Child-1','Father-1','Sibling-1'])
        self.assertEqual(people[0]['parents'][0]['id'],'Father-1')
        self.assertEqual(people[0]['parents'][0]['status'],'strongly_supported')
        self.assertEqual(people[0]['priorParentRoles'],old)
        self.assertEqual(people[1]['childrenRecorded'],[{'id':'OtherChild-1'}])
        self.assertEqual(people[2]['childrenRecorded'][0]['id'],'Child-1')

    def test_missing_sibling_evidence_is_rejected(self):
        people,reviews=self.fixture();reviews[0]['source_ids']=[]
        with self.assertRaisesRegex(ValueError,'requires an approved father'):
            apply_reviewed_parent_replacements(people,reviews)

    def test_another_attached_father_is_not_silently_replaced(self):
        people,reviews=self.fixture();people[0]['parents'].append(dict(id='Other-1',role='father'))
        with self.assertRaisesRegex(ValueError,'conflicts with another attached father'):
            apply_reviewed_parent_replacements(people,reviews)

    def test_cycle_is_rejected_before_mutation(self):
        people,reviews=self.fixture();people[2]['parents']=[dict(id='Child-1',role='father')]
        old=deepcopy(people)
        with self.assertRaisesRegex(ValueError,'cycle'):
            apply_reviewed_parent_replacements(people,reviews)
        self.assertEqual(people,old)
