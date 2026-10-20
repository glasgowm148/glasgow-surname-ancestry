import json
import subprocess
import unittest
from copy import deepcopy

from tools.approved_restorations import documentary_renderer
from tools.site_sources.onetree.build import apply_working_hypotheses, apply_working_mothers, apply_recorded_family_restorations, reviewed_family_aliases


def people(*ids):
    return [{"id": ident, "name": ident, "parents": []} for ident in ids]


def assessment(child, father, **extra):
    return {"working_selection": True, "publication_status": "approved", "status": "uncertain",
            "allow_new_relationship": True, "assertion_id": "A-1", "basis": "reviewed basis",
            "perspectives": {child: {"relationship": "father"}, father: {"relationship": "son"}}, **extra}


class WorkingHypothesisTests(unittest.TestCase):
    def local_replacement_case(self):
        model = people('Child-1', 'OldFather-1', 'NewFather-1')
        model[1]['childrenRecorded'] = [{'id': 'Child-1'}, {'id': 'Other-1'}]
        previous = dict(assertion_id='A-old', publication_status='approved', working_selection=True,
                        child='Child-1', father='OldFather-1', status='uncertain',
                        basis='Earlier reviewed comparison', source_ids=['S-old'],
                        probability={'value': .28, 'label': 'Uncertain · 28%'})
        alternative = dict(assertion_id='A-old', people=['Child-1', 'OldFather-1'],
                           publication_status='approved', lifecycle='alternative', status='uncertain',
                           source_ids=['S-old'], previous_working_selection=previous,
                           perspectives={'Child-1': {'relationship': 'father'}})
        selected = assessment('Child-1', 'NewFather-1', people=['Child-1', 'NewFather-1'],
                              status='possible', source_ids=['S-new'], model_note='Revised local family.',
                              working_parent_replacement=dict(previous_parent='OldFather-1',
                                  previous_parent_source='local_working_hypothesis',
                                  alternative_assertion_id='A-old', reason='Better combined identity fit'))
        return model, alternative, selected

    def test_replaces_a_reviewed_local_selection_without_a_captured_father(self):
        model, alternative, selected = self.local_replacement_case()
        self.assertEqual(apply_working_hypotheses(model, [alternative, selected]), 1)
        self.assertEqual([p['id'] for p in model[0]['parents']], ['NewFather-1'])
        self.assertEqual(model[0]['priorWorkingParents'][0]['id'], 'OldFather-1')
        self.assertEqual(model[0]['priorWorkingParents'][0]['reason'], 'Earlier reviewed comparison')
        self.assertEqual(model[0]['priorWorkingParents'][0]['probability']['value'], .28)
        self.assertEqual(model[1]['childrenRecorded'], [{'id': 'Other-1'}])
        self.assertEqual(model[2]['childrenRecorded'][0]['id'], 'Child-1')
        # A repeat build can already contain the selected parent; preserve one history row.
        self.assertEqual(apply_working_hypotheses(model, [alternative, selected]), 1)
        self.assertEqual([p['id'] for p in model[0]['parents']], ['NewFather-1'])
        self.assertEqual(len(model[0]['priorWorkingParents']), 1)
        self.assertEqual(model[0]['note'], 'Revised local family.')

    def test_local_replacement_requires_the_prior_approved_selection(self):
        for key in ['working_selection', 'publication_status', 'assertion_id', 'child',
                    'father', 'status', 'basis', 'source_ids']:
            with self.subTest(key=key):
                model, alternative, selected = self.local_replacement_case()
                alternative['previous_working_selection'].pop(key)
                before = deepcopy(model)
                with self.assertRaisesRegex(ValueError, 'reviewed local selection'):
                    apply_working_hypotheses(model, [alternative, selected])
                self.assertEqual(model, before)

    def test_local_replacement_does_not_override_another_captured_parent(self):
        model, alternative, selected = self.local_replacement_case()
        model[0]['parents'] = [dict(id='OtherFather-1', role='father', status='unmarked')]
        before = deepcopy(model)
        with self.assertRaisesRegex(ValueError, 'captured father'):
            apply_working_hypotheses(model, [alternative, selected])
        self.assertEqual(model, before)

    def test_local_replacement_preserves_a_confident_captured_parent(self):
        model, alternative, selected = self.local_replacement_case()
        model[0]['parents'] = [dict(id='OldFather-1', role='father', status='confident')]
        before = deepcopy(model)
        with self.assertRaisesRegex(ValueError, 'captured father'):
            apply_working_hypotheses(model, [alternative, selected])
        self.assertEqual(model, before)

    def test_local_replacement_requires_retained_sources_and_checks_cycles(self):
        model, alternative, selected = self.local_replacement_case()
        alternative['source_ids'] = ['Unrelated-source']
        before = deepcopy(model)
        with self.assertRaisesRegex(ValueError, 'reviewed local selection'):
            apply_working_hypotheses(model, [alternative, selected])
        self.assertEqual(model, before)
        model, alternative, selected = self.local_replacement_case()
        model[2]['parents'] = [dict(id='Child-1', role='father', status='uncertain')]
        before = deepcopy(model)
        with self.assertRaisesRegex(ValueError, 'paternal cycle'):
            apply_working_hypotheses(model, [alternative, selected])
        self.assertEqual(model, before)

    def test_possible_and_probable_parents_keep_both_reciprocal_grades(self):
        for grade in ['possible', 'probable']:
            with self.subTest(grade=grade):
                model = people('Child-1', 'Father-1', 'Mother-1')
                father = assessment('Child-1', 'Father-1', people=['Child-1', 'Father-1'],
                                    status=grade, source_ids=['S-1'])
                mother = assessment('Child-1', 'Mother-1', people=['Child-1', 'Mother-1'],
                                    status=grade, assertion_id='A-mother', source_ids=['S-1'])
                mother['perspectives']['Child-1']['relationship'] = 'mother'
                self.assertEqual(apply_working_hypotheses(model, [father, mother]), 1)
                self.assertEqual(apply_working_mothers(model, [father, mother]), 1)
                self.assertEqual([(p['role'], p['status']) for p in model[0]['parents']],
                                 [('father', grade), ('mother', grade)])
                for parent in model[1:]:
                    self.assertEqual(parent['childrenRecorded'][0]['status'], grade)
                    self.assertTrue(parent['childrenRecorded'][0]['hypothesis'])
                expression = documentary_renderer("p.parents.map(relationHTML).join('')")
                script = ("const esc=s=>s;const relationHTML=r=>'';const p="
                          + json.dumps(model[0]) + ";console.log(JSON.stringify(" + expression + "));true;")
                rendered = json.loads(subprocess.check_output(['node', '-e', script], text=True))
                for role in ['father', 'mother']:
                    self.assertIn(f'Selected {grade} working {role}.', rendered)

    def test_record_only_person_links_are_labelled_source_account(self):
        page = ">WikiTree ${icon('out')}</a>"
        result = documentary_renderer(page)
        self.assertIn("p.recordUrl&&!p.wikitreeUrl?'Source account':'WikiTree'", result)
        self.assertEqual(documentary_renderer(result), result)

    def test_probable_working_father_keeps_grade_and_reciprocal_link(self):
        model = people('Child-1', 'Father-1')
        proposal = assessment('Child-1', 'Father-1', status='probable', source_ids=['S-1'])
        self.assertEqual(apply_working_hypotheses(model, [proposal]), 1)
        self.assertEqual(model[0]['parents'][0]['status'], 'probable')
        self.assertEqual(model[1]['childrenRecorded'][0]['status'], 'probable')
        expression = documentary_renderer("p.parents.map(relationHTML).join('')")
        script = "const esc=s=>s;const relationHTML=r=>'';const p={parents:[{role:'father',hypothesis:true,status:'probable'}]};console.log(JSON.stringify(" + expression + "));"
        rendered = json.loads(subprocess.check_output(['node', '-e', script], text=True))
        self.assertIn('Selected probable working father.', rendered)
        self.assertNotIn('Selected uncertain', rendered)

    def test_family_aliases_require_saved_canonical_redirects_and_record_review(self):
        a = assessment('Child-1', 'Father-1', people=['Child-1', 'Father-1'], status='proved',
                       source_ids=['S-1'], tree_family_restoration=dict(child='Child-1', father='Father-1',
                       previously_confident=True, profile_aliases={'Alias-1': 'Mother-1'}))
        self.assertEqual(reviewed_family_aliases([a], {'Alias-1': 'Mother-1'}, {'Mother-1'}),
                         {'Alias-1': 'Mother-1'})
        for aliases, public, change in [({}, {'Mother-1'}, {}),
                                       ({'Alias-1': 'Elsewhere-1'}, {'Mother-1'}, {}),
                                       ({'Alias-1': 'Mother-1'}, set(), {}),
                                       ({'Alias-1': 'Mother-1'}, {'Mother-1'}, {'publication_status': 'draft'}),
                                       ({'Alias-1': 'Mother-1'}, {'Mother-1'}, {'source_ids': []})]:
            with self.subTest(aliases=aliases, public=public, change=change):
                with self.assertRaisesRegex(ValueError, 'saved public redirect'):
                    reviewed_family_aliases([dict(a, **change)], aliases, public)

    def maternal_replacement_case(self):
        model = people('Child-1', 'Father-1', 'OldMother-1', 'NewMother-1')
        model[0]['parents'] = [dict(id='Father-1', role='father', status='uncertain', hypothesis=True),
                               dict(id='OldMother-1', role='mother', status='unmarked')]
        model[0]['priorWorkingParents'] = [dict(id='OldFather-1', role='father', status='uncertain')]
        model[2]['childrenRecorded'] = [dict(id='Child-1', status='unmarked'), dict(id='Other-1')]
        model[2]['priorWorkingChildren'] = [dict(id='Earlier-1')]
        alternative = dict(assertion_id='A-old-mother', people=['Child-1', 'OldMother-1'],
                           publication_status='approved', status='uncertain', lifecycle='alternative',
                           source_ids=['S-1'], perspectives={'Child-1': {'relationship': 'mother'}})
        selected = assessment('Child-1', 'NewMother-1', people=['Child-1', 'NewMother-1'],
                              assertion_id='A-new-mother', source_ids=['S-1'],
                              working_parent_replacement=dict(previous_parent='OldMother-1',
                                  alternative_assertion_id='A-old-mother', reason='Preferred sourced family'))
        selected['perspectives']['Child-1']['relationship'] = 'mother'
        return model, alternative, selected

    def test_maternal_replacement_preserves_both_parent_histories(self):
        model, alternative, selected = self.maternal_replacement_case()
        original = deepcopy(model)
        self.assertEqual(apply_working_mothers(model, [alternative, selected]), 1)
        self.assertEqual(model[0]['parents'][0], original[0]['parents'][0])
        self.assertEqual([r['id'] for r in model[0]['parents']], ['Father-1', 'NewMother-1'])
        self.assertEqual(model[0]['priorWorkingParents'], original[0]['priorWorkingParents'] + [original[0]['parents'][1]])
        self.assertEqual(model[2]['childrenRecorded'], [{'id': 'Other-1'}])
        self.assertEqual(model[2]['priorWorkingChildren'], [{'id': 'Earlier-1'}, {'id': 'Child-1', 'status': 'unmarked'}])
        self.assertEqual(model[3]['childrenRecorded'][0]['id'], 'Child-1')

    def test_maternal_selection_is_independent_of_a_paternal_hypothesis(self):
        for father in [[], [dict(id='Father-1', role='father', status='unmarked')]]:
            with self.subTest(father=father):
                model, alternative, selected = self.maternal_replacement_case()
                model[0]['parents'] = deepcopy(father) + [model[0]['parents'][1]]
                self.assertEqual(apply_working_mothers(model, [alternative, selected]), 1)
                self.assertEqual(model[0]['parents'][:-1], father)
                self.assertEqual(model[0]['parents'][-1]['id'], 'NewMother-1')
                self.assertEqual(model[3]['childrenRecorded'][0]['id'], 'Child-1')

    def test_independent_mother_still_requires_reviewed_replacement(self):
        model, alternative, selected = self.maternal_replacement_case()
        model[0]['parents'][0].pop('hypothesis')
        selected.pop('working_parent_replacement')
        before = deepcopy(model)
        with self.assertRaisesRegex(ValueError, 'reviewed replacement'):
            apply_working_mothers(model, [alternative, selected])
        self.assertEqual(model, before)

    def test_maternal_replacement_rejects_unsafe_or_unretained_parents_atomically(self):
        def missing_alternative(m, a, s): a['publication_status'] = 'draft'
        def wrong_role(m, a, s): a['perspectives']['Child-1']['relationship'] = 'father'
        def wrong_pair(m, a, s): a['people'] = ['Child-1', 'Elsewhere-1']
        def confident(m, a, s): m[0]['parents'][1]['status'] = 'confident'
        def withheld(m, a, s): m[0]['parents'][1]['withheld'] = True
        def absent(m, a, s): m[0]['parents'].pop()
        def several(m, a, s): m[0]['parents'].append(dict(id='OtherMother-1', role='mother', status='uncertain'))
        def same_parent(m, a, s): s['working_parent_replacement']['previous_parent'] = 'NewMother-1'
        def no_reason(m, a, s): s['working_parent_replacement'].pop('reason')
        def no_source(m, a, s): a['source_ids'] = []
        def current(m, a, s): a['lifecycle'] = 'current'
        def wrong_grade(m, a, s): a['status'] = 'proved'
        for mutate in [missing_alternative, wrong_role, wrong_pair, confident, withheld, absent,
                       several, same_parent, no_reason, no_source, current, wrong_grade]:
            with self.subTest(mutate=mutate.__name__):
                model, alternative, selected = self.maternal_replacement_case()
                mutate(model, alternative, selected)
                before = deepcopy(model)
                with self.assertRaisesRegex(ValueError, 'captured mother'):
                    apply_working_mothers(model, [alternative, selected])
                self.assertEqual(model, before)

    def test_maternal_replacement_checks_mixed_ancestry_before_mutation(self):
        model, alternative, selected = self.maternal_replacement_case()
        model[3]['parents'] = [dict(id='Child-1', role='father', status='uncertain')]
        before = deepcopy(model)
        with self.assertRaisesRegex(ValueError, 'ancestry cycle'):
            apply_working_mothers(model, [alternative, selected])
        self.assertEqual(model, before)
        model, alternative, selected = self.maternal_replacement_case()
        before = deepcopy(model)
        duplicate = deepcopy(selected); duplicate['assertion_id'] = 'A-second-selection'
        with self.assertRaisesRegex(ValueError, 'unique public family'):
            apply_working_mothers(model, [alternative, selected, duplicate])
        self.assertEqual(model, before)

    def test_maternal_cycle_check_uses_the_replaced_effective_graph(self):
        model = people('Child-1', 'Child-2', 'Father-1', 'OldMother-1', 'NewMother-1')
        model[0]['parents'] = [dict(id='Father-1', role='father', hypothesis=True),
                               dict(id='Child-2', role='mother', status='uncertain')]
        model[1]['parents'] = [dict(id='Father-1', role='father', hypothesis=True),
                               dict(id='OldMother-1', role='mother', status='uncertain')]
        cases = []
        for child, old, new in [('Child-1', 'Child-2', 'NewMother-1'), ('Child-2', 'OldMother-1', 'Child-1')]:
            alt = dict(assertion_id='old-'+child, people=[child, old], publication_status='approved',
                       status='uncertain', lifecycle='alternative', source_ids=['S-1'],
                       perspectives={child: {'relationship': 'mother'}})
            selected = assessment(child, new, people=[child, new], assertion_id='new-'+child,
                                  source_ids=['S-1'], working_parent_replacement=dict(previous_parent=old,
                                  alternative_assertion_id=alt['assertion_id'], reason='Reviewed replacement'))
            selected['perspectives'][child]['relationship'] = 'mother'
            cases += [alt, selected]
        self.assertEqual(apply_working_mothers(model, cases), 2)
        self.assertEqual([r['id'] for r in model[0]['parents'] if r['role'] == 'mother'], ['NewMother-1'])
        self.assertEqual([r['id'] for r in model[1]['parents'] if r['role'] == 'mother'], ['Child-1'])

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
        item['tree_family_restoration']['name_corrections'] = {'Child-1': 'Reviewed Child'}
        self.assertEqual(apply_recorded_family_restorations(model, [item]), ['Child-1', 'Father-1'])
        self.assertEqual(model[0]['name'], 'Reviewed Child')
        self.assertEqual(model[0]['first'], 'Reviewed')
        self.assertEqual(model[1]['childrenRecorded'][0]['name'], 'Reviewed Child')
        self.assertEqual(model[1]['childrenRecorded'][0]['status'], 'proved')
        item['tree_family_restoration']['name_corrections'] = {'Other-1': 'Unreviewed'}
        with self.assertRaisesRegex(ValueError, 'reviewed child or father'):
            apply_recorded_family_restorations(model, [item])
        item['tree_family_restoration'].pop('name_corrections')
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
