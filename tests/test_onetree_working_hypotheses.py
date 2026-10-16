import json
import subprocess
import unittest

from tools.approved_restorations import documentary_renderer
from tools.site_sources.onetree.build import apply_working_hypotheses, apply_working_mothers, apply_recorded_family_restorations


def people(*ids):
    return [{"id": ident, "name": ident, "parents": []} for ident in ids]


def assessment(child, father, **extra):
    return {"working_selection": True, "publication_status": "approved", "status": "uncertain",
            "allow_new_relationship": True, "assertion_id": "A-1", "basis": "reviewed basis",
            "perspectives": {child: {"relationship": "father"}, father: {"relationship": "son"}}, **extra}


class WorkingHypothesisTests(unittest.TestCase):
    def test_parent_explanations_name_the_actual_parent_role(self):
        expression = documentary_renderer("p.parents.map(relationHTML).join('')")
        script = "const esc=s=>s;const relationHTML=r=>'';const p={parents:[{role:'father',hypothesis:true},{role:'mother',hypothesis:true}]};console.log(JSON.stringify(" + expression + "));"
        rendered = json.loads(subprocess.check_output(['node', '-e', script], text=True))
        self.assertEqual(rendered.count('Selected uncertain working father.'), 1)
        self.assertEqual(rendered.count('Selected uncertain working mother.'), 1)
        self.assertEqual(documentary_renderer(expression), expression)
        old_page = "const catalogue=p=>p.catalogueUrl|| (" + expression.replace("${esc(r.role||'parent')}", 'father')
        self.assertIn("${esc(r.role||'parent')}", documentary_renderer(old_page))

    def test_maternal_selection_preserves_the_father_and_reciprocal_children(self):
        model = people('Child-1', 'Father-1', 'Mother-1')
        apply_working_hypotheses(model, [assessment('Child-1', 'Father-1')])
        model[2]['childrenRecorded'] = [{'id': 'Other-1'}]
        a = assessment('Child-1', 'Mother-1', source_ids=['S-1'], people=['Child-1', 'Mother-1'])
        a['perspectives']['Child-1']['relationship'] = 'mother'
        self.assertEqual(apply_working_hypotheses(people('Child-1', 'Father-1', 'Mother-1'), [a]), 0)
        self.assertEqual(apply_working_mothers(model, [a]), 1)
        self.assertEqual([(r['role'], r['id']) for r in model[0]['parents']], [('father', 'Father-1'), ('mother', 'Mother-1')])
        self.assertEqual([r['id'] for r in model[2]['childrenRecorded']], ['Other-1', 'Child-1'])
        with self.assertRaisesRegex(ValueError, 'empty maternal field'):
            apply_working_mothers(model, [a])

    def test_maternal_selection_rejects_missing_sources_and_cycles(self):
        model = people('Child-1', 'Father-1', 'Mother-1')
        apply_working_hypotheses(model, [assessment('Child-1', 'Father-1')])
        a = assessment('Child-1', 'Mother-1', people=['Child-1', 'Mother-1'])
        a['perspectives']['Child-1']['relationship'] = 'mother'
        with self.assertRaisesRegex(ValueError, 'sourced claim'):
            apply_working_mothers(model, [a])
        a['source_ids'] = ['S-1'];model[2]['parents'] = [{'id': 'Child-1', 'role': 'mother'}]
        with self.assertRaisesRegex(ValueError, 'ancestry cycle'):
            apply_working_mothers(model, [a])
        self.assertEqual(len(model[0]['parents']), 1)

    def test_selected_parent_replacement_retains_alternative_and_mother(self):
        model = people('Child-1', 'Old-1', 'New-1', 'Mother-1')
        mother={'id':'Mother-1','role':'mother','status':'uncertain'}
        model[0]['parents']=[{'id':'Old-1','role':'father','status':'uncertain'},mother.copy()]
        model[1]['childrenRecorded']=[{'id':'Child-1'},{'id':'Other-1'}]
        proposal=assessment('Child-1','New-1',source_ids=['S-1'],model_note='Possible duplicate; mother independently unproved.',
            working_parent_replacement={'previous_parent':'Old-1','alternative_assertion_id':'A-old','reason':'Preferred local generation'})
        alternative={'assertion_id':'A-old','people':['Child-1','Old-1'],'publication_status':'approved',
                     'status':'uncertain','lifecycle':'alternative','source_ids':['S-1'],
                     'perspectives':{'Child-1':{'relationship':'father'}}}
        with self.assertRaisesRegex(ValueError,'retained uncertain alternative'):
            apply_working_hypotheses(model,[proposal])
        self.assertEqual(apply_working_hypotheses(model,[alternative,proposal]),1)
        self.assertIn(mother,model[0]['parents'])
        self.assertEqual(model[0]['priorWorkingParents'][0]['id'],'Old-1')
        self.assertEqual([r['id'] for r in model[1]['childrenRecorded']],['Other-1'])
        self.assertEqual(model[1]['priorWorkingChildren'][0]['id'],'Child-1')
        self.assertIn('Possible duplicate',model[0]['note'])
        model[0]['parents']=[{'id':'Old-1','role':'father','status':'confident'}]
        with self.assertRaisesRegex(ValueError,'retained uncertain alternative'):
            apply_working_hypotheses(model,[alternative,proposal])

    def test_replacement_of_captured_parent_outside_model_preserves_capture(self):
        model = people('Child-1', 'New-1')
        original = {'id': 'Old-1', 'role': 'father', 'status': 'uncertain', 'inModel': False}
        model[0]['parents'] = [original.copy()]
        proposal = assessment('Child-1', 'New-1', source_ids=['S-1'],
            working_parent_replacement={'previous_parent': 'Old-1',
                'alternative_assertion_id': 'A-old', 'reason': 'Preferred reviewed family'})
        alternative = {'assertion_id': 'A-old', 'people': ['Child-1', 'Old-1'],
            'publication_status': 'approved', 'status': 'uncertain', 'lifecycle': 'alternative',
            'source_ids': ['S-1'], 'perspectives': {'Child-1': {'relationship': 'father'}}}
        self.assertEqual(apply_working_hypotheses(model, [alternative, proposal]), 1)
        self.assertEqual(model[0]['priorWorkingParents'], [original])
        self.assertEqual(model[0]['parents'][0]['id'], 'New-1')
        self.assertEqual(model[1]['childrenRecorded'][0]['id'], 'Child-1')
        self.assertEqual({p['id'] for p in model}, {'Child-1', 'New-1'})
        model[0]['parents'] = [{**original, 'withheld': True}]
        with self.assertRaisesRegex(ValueError, 'retained uncertain alternative'):
            apply_working_hypotheses(model, [alternative, proposal])

    def test_recorded_family_restoration_requires_captured_father_and_prior_grade(self):
        model = people('Child-1', 'Father-1')
        model[0]['parents'] = [{'id': 'Father-1', 'role': 'father', 'status': 'confident'}]
        item = {'assertion_id': 'A-recorded', 'publication_status': 'approved', 'status': 'proved',
                'basis': 'Existing reviewed record', 'source_ids': ['S-record'],
                'perspectives': {'Child-1': {'relationship': 'father'}},
                'tree_family_restoration': {'child': 'Child-1', 'father': 'Father-1', 'previously_confident': True}}
        self.assertEqual(apply_recorded_family_restorations(model, [item]), ['Child-1', 'Father-1'])
        self.assertEqual(model[1]['childrenRecorded'][0]['status'], 'proved')
        item['tree_family_restoration']['previously_confident'] = False
        with self.assertRaisesRegex(ValueError, 'already-confident'):
            apply_recorded_family_restorations(model, [item])
        item['tree_family_restoration']['previously_confident'] = True
        model[0]['parents'][0]['id'] = 'Other-1'
        with self.assertRaisesRegex(ValueError, 'captured father'):
            apply_recorded_family_restorations(model, [item])

    def test_approved_selected_edge_is_added(self):
        model = people("Child-1", "Father-1")
        self.assertEqual(apply_working_hypotheses(model, [assessment("Child-1", "Father-1")]), 1)
        self.assertEqual(model[0]["parents"][0]["id"], "Father-1")
        self.assertEqual(model[0]["parents"][0]["source"], "local_working_hypothesis")
        self.assertEqual(model[1]['childrenRecorded'][0]['id'], 'Child-1')
        self.assertEqual(model[1]['childrenRecorded'][0]['status'], 'uncertain')

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
