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

    def _mother_fixture(self):
        people = [dict(id='Child-1', name='Child', parents=[dict(id='Martha-1', role='mother')]),
                  dict(id='Martha-1', name='Martha', parents=[], childrenRecorded=[dict(id='Child-1')]),
                  dict(id='Mary-1', name='Mary', parents=[], childrenRecorded=[])]
        correction = dict(assertion_id='stepmother', people=['Child-1', 'Martha-1'],
                          publication_status='approved', source_ids=['correction'],
                          role_correction={'Child-1': {'from': ['mother'], 'to': 'stepmother'}})
        parent = dict(assertion_id='mother', publication_status='approved', status='proved',
                      source_ids=['family'], basis='Named child group',
                      perspectives={'Child-1': {'relationship': 'mother'}},
                      tree_parent_replacement=dict(child='Child-1', mother='Mary-1', role='mother',
                          previous_parent='Martha-1', role_correction_assertion='stepmother',
                          reason='Mary is the named biological mother'))
        return people, [correction, parent]

    def test_supported_mother_replacement_retains_stepmother_history(self):
        people, reviews = self._mother_fixture()
        changed = apply_reviewed_parent_replacements(people, reviews)
        self.assertEqual(changed, ['Child-1', 'Martha-1', 'Mary-1'])
        self.assertEqual(people[0]['parents'][0]['id'], 'Mary-1')
        self.assertEqual(people[0]['parents'][0]['role'], 'mother')
        self.assertEqual(people[0]['priorParentRoles'][0]['id'], 'Martha-1')
        self.assertEqual(people[1]['priorChildRoles'][0]['id'], 'Child-1')
        self.assertEqual(people[1]['childrenRecorded'], [])
        self.assertEqual(people[2]['childrenRecorded'][0]['id'], 'Child-1')

    def test_mother_replacement_is_idempotent(self):
        people, reviews = self._mother_fixture(); apply_reviewed_parent_replacements(people, reviews)
        once = deepcopy(people); apply_reviewed_parent_replacements(people, reviews)
        self.assertEqual(people, once)

    def test_mother_cycle_rolls_back(self):
        people, reviews = self._mother_fixture(); people[2]['parents'] = [dict(id='Child-1', role='father')]
        old = deepcopy(people)
        with self.assertRaisesRegex(ValueError, 'cycle'):
            apply_reviewed_parent_replacements(people, reviews)
        self.assertEqual(people, old)

    def test_competing_mother_rolls_back(self):
        people, reviews = self._mother_fixture(); people[0]['parents'].append(dict(id='Other-1', role='mother'))
        old = deepcopy(people)
        with self.assertRaises(ValueError): apply_reviewed_parent_replacements(people, reviews)
        self.assertEqual(people, old)

    def test_wrong_correction_endpoints_and_missing_source_rejected(self):
        people, reviews = self._mother_fixture(); reviews[0]['people'].append('Extra-1')
        with self.assertRaises(ValueError): apply_reviewed_parent_replacements(people, reviews)
        people, reviews = self._mother_fixture(); reviews[0]['source_ids'] = []
        with self.assertRaises(ValueError): apply_reviewed_parent_replacements(people, reviews)

    def test_duplicate_mother_replacements_roll_back(self):
        people, reviews = self._mother_fixture(); duplicate = deepcopy(reviews[1]); duplicate['assertion_id'] = 'mother-2'
        reviews.append(duplicate); old = deepcopy(people)
        with self.assertRaisesRegex(ValueError, 'same child and role'):
            apply_reviewed_parent_replacements(people, reviews)
        self.assertEqual(people, old)
