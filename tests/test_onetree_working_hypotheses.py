import unittest

from tools.site_sources.onetree.build import apply_working_hypotheses


def people(*ids):
    return [{"id": ident, "name": ident, "parents": []} for ident in ids]


def assessment(child, father, **extra):
    return {"working_selection": True, "publication_status": "approved", "status": "uncertain",
            "allow_new_relationship": True, "assertion_id": "A-1", "basis": "reviewed basis",
            "perspectives": {child: {"relationship": "father"}, father: {"relationship": "son"}}, **extra}


class WorkingHypothesisTests(unittest.TestCase):
    def test_approved_selected_edge_is_added(self):
        model = people("Child-1", "Father-1")
        self.assertEqual(apply_working_hypotheses(model, [assessment("Child-1", "Father-1")]), 1)
        self.assertEqual(model[0]["parents"][0]["id"], "Father-1")
        self.assertEqual(model[0]["parents"][0]["source"], "local_working_hypothesis")

    def test_unselected_and_unapproved_are_ignored(self):
        model = people("Child-1", "Father-1")
        item = assessment("Child-1", "Father-1", working_selection=False)
        self.assertEqual(apply_working_hypotheses(model, [item]), 0)
        item["working_selection"] = True
        item["publication_status"] = "draft"
        self.assertEqual(apply_working_hypotheses(model, [item]), 0)

    def test_competing_father_rejected(self):
        model = people("Child-1", "Father-1", "Father-2")
        model[0]["parents"] = [{"id": "Father-1", "role": "father", "status": "uncertain"}]
        with self.assertRaisesRegex(ValueError, "conflicts with existing father"):
            apply_working_hypotheses(model, [assessment("Child-1", "Father-2")])

    def test_cycle_rejected(self):
        model = people("Child-1", "Father-1")
        model[0]["parents"] = [{"id": "Father-1", "role": "father", "status": "uncertain"}]
        with self.assertRaisesRegex(ValueError, "cycle"):
            apply_working_hypotheses(model, [assessment("Father-1", "Child-1")])

    def test_saved_merged_parent_resolves_without_losing_original(self):
        model = people('Child-1', 'Father-1')
        original = {'id': 'Former-1', 'role': 'father', 'status': 'unknown', 'inModel': False}
        model[0]['parents'] = [original.copy()]
        self.assertEqual(apply_working_hypotheses(model, [assessment('Child-1', 'Father-1')],
                                               {'Former-1': 'Father-1'}), 1)
        self.assertEqual(model[0]['parents'][0]['id'], 'Father-1')
        self.assertEqual(model[0]['parents'][0]['status'], 'uncertain')
        self.assertEqual(model[0]['parentAliasResolutions'][0]['original'], original)

    def test_alias_cannot_replace_a_distinct_person_still_in_model(self):
        model = people('Child-1', 'Father-1', 'Former-1')
        model[0]['parents'] = [{'id': 'Former-1', 'role': 'father'}]
        with self.assertRaisesRegex(ValueError, 'conflicts with existing father'):
            apply_working_hypotheses(model, [assessment('Child-1', 'Father-1')], {'Former-1': 'Father-1'})

    def test_named_merged_parent_can_resolve_export_placeholder(self):
        model = people('Child-1', 'Father-1')
        original = {'id': '', 'name': 'Parent outside current One-Tree export', 'role': 'father'}
        model[0]['parents'] = [original.copy()]
        item = assessment('Child-1', 'Father-1', parent_alias_resolution={
            'original_id': 'Former-1', 'canonical_id': 'Father-1'})
        self.assertEqual(apply_working_hypotheses(model, [item], {'Former-1': 'Father-1'}), 1)
        self.assertEqual(model[0]['parentAliasResolutions'][0]['original'], original)
        self.assertEqual(model[0]['parentAliasResolutions'][0]['original_profile_id'], 'Former-1')

    def test_placeholder_without_saved_alias_stays_unresolved(self):
        model = people('Child-1', 'Father-1')
        model[0]['parents'] = [{'id': '', 'name': 'Parent outside current One-Tree export', 'role': 'father'}]
        with self.assertRaisesRegex(ValueError, 'conflicts with existing father'):
            apply_working_hypotheses(model, [assessment('Child-1', 'Father-1')])

    def test_alias_resolution_keeps_cycle_guard(self):
        model = people('Child-1', 'Father-1')
        model[0]['parents'] = [{'id': 'Former-1', 'role': 'father'}]
        model[1]['parents'] = [{'id': 'Child-1', 'role': 'father'}]
        with self.assertRaisesRegex(ValueError, 'cycle'):
            apply_working_hypotheses(model, [assessment('Child-1', 'Father-1')], {'Former-1': 'Father-1'})

    def test_multiple_selected_fathers_rejected_before_mutation(self):
        model = people("Child-1", "Father-1", "Father-2")
        with self.assertRaisesRegex(ValueError, "multiple selected fathers"):
            apply_working_hypotheses(model, [assessment("Child-1", "Father-1"), assessment("Child-1", "Father-2")])
        self.assertEqual(model[0]["parents"], [])


if __name__ == "__main__":
    unittest.main()
