import unittest
from copy import deepcopy
from tools.relationship_update_changes import normalise_change, pending_changes


class RelationshipChangeTests(unittest.TestCase):
    def setUp(self):
        self.captures = {'Child-1': {'profile_fields': {'Father': 2, 'DataStatus': {'Father': ''}}},
                         'Father-2': {'profile_fields': {'Id': 2}}}
        self.review = {'assertion_id': 'A', 'people': ['Child-1', 'Father-2'],
                       'publication_status': 'approved', 'status': 'proved',
                       'record_scope': 'The recorded child, not the possible later emigrant',
                       'perspectives': {'Child-1': {'relationship': 'father'}}}
        self.change = {'subject_id': 'Child-1', 'relative_id': 'Father-2', 'relationship': 'father',
                       'before': 'unmarked', 'after': 'certain', 'assertion_id': 'A',
                       'previous_status_provenance': ['Saved unmarked flag and cited baptism']}
        self.findings = [{'id': 'batch', 'relationship_changes': [self.change]}]

    def derive(self, spec=None):
        return pending_changes('Child-1', spec or {}, self.captures, [self.review], self.findings)

    def test_explicit_new_grades_and_scope(self):
        for status, band in [('proved', 'confident'), ('probable', 'probable'),
                             ('possible', 'possible'), ('uncertain', 'uncertain')]:
            row = normalise_change({'action': 'add', 'relationship': 'father', 'status': status})
            self.assertEqual(row['confidence_band'], band)
        row = self.derive()[0]
        self.assertEqual((row['action'], row['confidence_band']), ('regrade', 'confident'))
        self.assertEqual(row['scope'], self.review['record_scope'])
        self.assertEqual(row['before'], 'unmarked')

    def test_no_flags_without_prior_assessment_or_current_parent(self):
        self.change['previous_status_provenance'] = []
        self.assertEqual(self.derive(), [])
        self.change['previous_status_provenance'] = ['Saved flag']
        self.captures['Child-1']['profile_fields']['Father'] = 9
        self.assertEqual(self.derive(), [])

    def test_already_applied_or_unapproved_is_not_new_work(self):
        self.captures['Child-1']['profile_fields']['DataStatus']['Father'] = '20'
        self.assertEqual(self.derive(), [])
        self.captures['Child-1']['profile_fields']['DataStatus']['Father'] = ''
        self.review['publication_status'] = 'withheld'
        self.assertEqual(self.derive(), [])

    def test_new_parent_suppresses_old_parent_regrade(self):
        spec = {'relationship_changes': [{'action': 'replace', 'relationship': 'father',
                                         'relative_id': 'Other-3', 'status': 'probable'}]}
        self.assertEqual(len(self.derive(spec)), 1)
        self.assertEqual(self.derive(spec)[0]['relative_id'], 'Other-3')

    def test_no_mutation_and_rebuild_is_stable(self):
        before = deepcopy((self.captures, self.review, self.findings))
        self.assertEqual(self.derive(), self.derive())
        self.assertEqual(before, (self.captures, self.review, self.findings))


if __name__ == '__main__':
    unittest.main()
