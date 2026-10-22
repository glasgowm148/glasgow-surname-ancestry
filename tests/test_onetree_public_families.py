import json
import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from tools.site_sources.onetree.build import apply_public_families, apply_working_hypotheses


class PublicFamiliesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.site = Path(self.tmp.name)
        (self.site / 'people').mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def run_sync(self, people, families, ambiguous=(), years=None, assessments=None, add_only=False):
        for person in people:
            person.setdefault('name', person['id'])
        nodes = {}
        edges = []
        for ident, parents in families.items():
            year = (years or {}).get(ident, 1600)
            nodes[ident] = dict(id=ident, name=ident, url='/people/'+ident.lower()+'.html',
                gender='Male', birth_year=year, death_year=None, birth_status='uncertain',
                year=year, year_basis='birth', year_status='uncertain', first_record_year=None)
            dossier = dict(id=ident, name=ident, vitals={'birth': {'date': str(year), 'place': 'Scotland'}},
                           relationships={'parents': parents})
            (self.site / 'people' / (ident.lower()+'.json')).write_text(json.dumps(dossier))
            edges += [dict(child=ident, father=r['id'], status=r.get('status', 'unknown'))
                      for r in parents if r.get('relationship') == 'father' and ident not in ambiguous]
        with patch('tools.branch_connectivity.load_public_nodes', return_value=(nodes, edges, {'multiple_fathers': list(ambiguous)})):
            return apply_public_families(people, self.site, assessments=assessments, add_only=add_only)

    def selected_father(self):
        return dict(assertion_id='A-selected', publication_status='approved',
                    working_selection=True, allow_new_relationship=True, status='possible',
                    basis='Reviewed local household', source_ids=['Baptism-1'],
                    perspectives={'Child-1': {'relationship': 'father'},
                                  'Father-1': {'relationship': 'son'}})

    def test_reviewed_mother_fills_export_placeholder_but_preserves_private_parent(self):
        assessment = dict(assertion_id='A-mother', publication_status='approved',
                          allow_new_relationship=True, source_ids=['Baptism-1'],
                          basis='Named mother in baptism', people=['Child-1', 'Mother-1'],
                          perspectives={'Child-1': {'relationship': 'mother'}})
        families = {'Child-1': [dict(id='Mother-1', relationship='mother', status='proved',
                                     assertion_id='A-mother')], 'Mother-1': []}
        placeholder = dict(id='', role='mother', status='unmarked',
                           name='Parent outside current One-Tree export', inModel=False)
        people = [dict(id='Child-1', parents=[copy.deepcopy(placeholder)])]
        self.run_sync(people, families, assessments=[assessment])
        self.assertEqual(people[0]['parents'][0]['id'], 'Mother-1')
        self.assertEqual(len(people[0]['parents']), 1)
        for protected in [dict(placeholder, withheld=True),
                          dict(placeholder, id='Other-1'),
                          dict(placeholder, status='non-biological')]:
            people = [dict(id='Child-1', parents=[copy.deepcopy(protected)])]
            self.run_sync(people, families, assessments=[assessment])
            self.assertEqual(people[0]['parents'], [protected])
        people = [dict(id='Child-1', parents=[copy.deepcopy(placeholder)])]
        self.run_sync(people, families, assessments=[dict(assessment, allow_new_relationship=False)])
        self.assertEqual(people[0]['parents'], [placeholder])

    def test_missing_historical_endpoints_are_seeded_before_working_validation(self):
        people = []
        families = {'Child-1': [dict(id='Father-1', relationship='father', status='possible')],
                    'Father-1': []}
        seeded = self.run_sync(people, families, add_only=True)
        self.assertEqual(seeded['publicFamilyNewIds'], ['Child-1', 'Father-1'])
        self.assertTrue(all(p['parents'] == [] for p in people))
        self.assertEqual(apply_working_hypotheses(people, [self.selected_father()]), 1)
        self.run_sync(people, families)
        child = next(p for p in people if p['id'] == 'Child-1')
        self.assertEqual(child['parents'][0]['id'], 'Father-1')
        self.assertTrue(child['parents'][0]['hypothesis'])

    def test_seeding_does_not_hide_a_conflicting_existing_father(self):
        people = [dict(id='Child-1', parents=[dict(id='Old-1', role='father', status='unmarked')]),
                  dict(id='Old-1', parents=[])]
        previous = copy.deepcopy(people[0]['parents'])
        self.run_sync(people, {'Child-1': [], 'Father-1': []}, add_only=True)
        self.assertEqual(people[0]['parents'], previous)
        with self.assertRaisesRegex(ValueError, 'conflicts with existing father'):
            apply_working_hypotheses(people, [self.selected_father()])

    def test_seeded_child_keeps_published_mother_through_full_sync(self):
        people = []
        families = {'Child-1': [
            dict(id='Father-1', relationship='father', status='possible'),
            dict(id='Mother-1', relationship='mother', status='unmarked')],
            'Father-1': []}
        self.run_sync(people, families, add_only=True)
        child = next(p for p in people if p['id'] == 'Child-1')
        self.assertEqual([(p['id'], p['role']) for p in child['parents']],
                         [('Mother-1', 'mother')])
        self.assertFalse(child['parents'][0]['inModel'])
        apply_working_hypotheses(people, [self.selected_father()])
        self.run_sync(people, families)
        self.assertEqual([(p['id'], p['role']) for p in child['parents']],
                         [('Mother-1', 'mother'), ('Father-1', 'father')])
        before = copy.deepcopy(people)
        self.run_sync(people, families)
        self.assertEqual(people, before)

    def test_seeding_keeps_the_historical_cutoff(self):
        people = []
        self.run_sync(people, {'Child-1': [], 'Father-1': []},
                      years={'Child-1': 1900, 'Father-1': 1800}, add_only=True)
        self.assertEqual([p['id'] for p in people], ['Father-1'])
        with self.assertRaisesRegex(ValueError, 'endpoint outside'):
            apply_working_hypotheses(people, [self.selected_father()])

    def test_reviewed_later_child_is_visible_without_changing_birth_or_importing_peers(self):
        people = []
        assessment = dict(assertion_id='A-later', publication_status='approved',
                          status='proved', source_ids=['Family-biography'],
                          probability={'value': .97},
                          perspectives={'Child-1': {'relationship': 'father'}})
        self.run_sync(people, {
            'Child-1': [dict(id='Father-1', relationship='father', status='proved',
                             assertion_id='A-later')],
            'Father-1': [], 'Unreviewed-1': []},
            years={'Child-1': 1900, 'Father-1': 1850, 'Unreviewed-1': 1900},
            assessments=[assessment])
        by_id = {p['id']: p for p in people}
        self.assertEqual(set(by_id), {'Child-1', 'Father-1'})
        self.assertEqual(by_id['Child-1']['born'], 1900)
        self.assertEqual(by_id['Child-1']['parents'][0]['id'], 'Father-1')
        self.assertEqual(by_id['Father-1']['childrenRecorded'][0]['id'], 'Child-1')

    def test_tentative_working_father_preserves_selected_provenance(self):
        for grade in ['possible', 'probable']:
            with self.subTest(grade=grade):
                father = dict(id='Father-1', role='father', status=grade, hypothesis=True,
                              assertion_id='A-selected', reason='Reviewed holding and witness')
                people = [dict(id='Child-1', parents=[father]),
                          dict(id='Father-1', parents=[], childrenRecorded=[])]
                self.run_sync(people, {'Child-1': [
                    dict(id='Father-1', relationship='father', status=grade)
                ]})
                self.assertEqual(people[0]['parents'], [father])

    def test_record_parent_scope_survives_both_directions_and_repeat_sync(self):
        people = [dict(id='Child-1', parents=[
            dict(id='Father-1', role='father', status='proved'),
            dict(id='Mother-1', role='mother', status='unmarked')]),
            dict(id='Father-1', parents=[], childrenRecorded=[{'id': 'Other-1'}]),
            dict(id='Mother-1', parents=[], childrenRecorded=[{'id': 'Other-2'}])]
        scope = 'Scottish baptism only; American adult identity unproved'
        families, assessments = {'Child-1': []}, []
        for role in ['father', 'mother']:
            ident = role.title()+'-1'
            families['Child-1'].append(dict(id=ident, relationship=role, status='proved',
                assertion_id=role, status_label=f'Documented {role} in baptism; American identity unproved'))
            assessments.append(dict(assertion_id=role, publication_status='approved',
                people=['Child-1', ident], record_scope=scope,
                perspectives={'Child-1': {'relationship': role}}))
        self.run_sync(people, families, assessments=assessments)
        for row in people[0]['parents']:
            self.assertEqual(row['status'], 'proved')
            self.assertEqual(row['recordScope'], scope)
            self.assertIn('American identity unproved', row['statusLabel'])
        for parent, other in zip(people[1:], ['Other-1', 'Other-2']):
            self.assertEqual(parent['childrenRecorded'][0], {'id': other})
            child = parent['childrenRecorded'][1]
            self.assertEqual(child['recordScope'], scope)
            self.assertEqual(child['status'], 'proved')
            self.assertIn('Documented child', child['statusLabel'])
            self.assertIn('American identity unproved', child['statusLabel'])
        before = copy.deepcopy(people)
        self.run_sync(people, families, assessments=assessments)
        self.assertEqual(people, before)

    def test_working_father_grade_disagreement_is_rejected(self):
        for selected, published in [('probable', 'uncertain'), ('uncertain', 'probable')]:
            with self.subTest(selected=selected, published=published):
                people = [dict(id='Child-1', parents=[dict(
                    id='Father-1', role='father', status=selected, hypothesis=True)]),
                    dict(id='Father-1', parents=[], childrenRecorded=[])]
                with self.assertRaisesRegex(ValueError, 'Working father disagrees'):
                    self.run_sync(people, {'Child-1': [
                        dict(id='Father-1', relationship='father', status=published)
                    ]})

    def test_reviewed_mother_updates_beside_an_unchanged_working_father(self):
        father = dict(id='Father-1', role='father', status='uncertain', hypothesis=True)
        people = [dict(id='Child-1', parents=[father, dict(id='Mother-1', role='mother', status='unmarked')]),
                  dict(id='Father-1', parents=[], childrenRecorded=[]),
                  dict(id='Mother-1', parents=[], childrenRecorded=[{'id': 'Other-1'}], note='Retain account')]
        assessment = dict(assertion_id='A-mother', people=['Child-1', 'Mother-1'], publication_status='approved',
                          perspectives={'Child-1': {'relationship': 'mother'}})
        result = self.run_sync(people, {'Child-1': [
            dict(id='Father-1', relationship='father', status='uncertain'),
            dict(id='Mother-1', relationship='mother', status='probable', assertion_id='A-mother')
        ]}, assessments=[assessment])
        self.assertEqual(people[0]['parents'][0], father)
        self.assertEqual(people[0]['parents'][1]['status'], 'probable')
        self.assertEqual(people[2]['note'], 'Retain account')
        self.assertEqual(people[2]['childrenRecorded'][0], {'id': 'Other-1'})
        self.assertEqual(people[2]['childrenRecorded'][1]['status'], 'probable')
        self.assertEqual(result['publicMotherGradeScope'], {'Child-1': ['Mother-1']})
        self.assertEqual(result['publicMotherGradeSyncIds'], ['Child-1'])

    def test_maternal_grade_sync_cannot_select_or_invent_a_mother(self):
        for changes, publication in [({}, 'draft'), ({'id': 'Other-1'}, 'approved'),
                                     ({'current': False}, 'approved'), ({'withheld': True}, 'approved'),
                                     ({'status': 'unknown'}, 'approved')]:
            with self.subTest(changes=changes, publication=publication):
                mother = dict(id='Mother-1', role='mother', status='uncertain')
                people = [dict(id='Child-1', parents=[mother]),
                          dict(id='Mother-1', parents=[], childrenRecorded=[])]
                row = dict(id='Mother-1', relationship='mother', status='probable', assertion_id='A-mother')
                row.update(changes)
                assessment = dict(assertion_id='A-mother', people=['Child-1', row['id']],
                                  publication_status=publication,
                                  perspectives={'Child-1': {'relationship': 'mother'}})
                result = self.run_sync(people, {'Child-1': [row]}, assessments=[assessment])
                self.assertEqual(people[0]['parents'], [mother])
                self.assertEqual(result['publicMotherGradeScope'], {})

    def test_reviewed_mother_addition_requires_explicit_sourced_approval(self):
        for approved in [False, True]:
            with self.subTest(approved=approved):
                father = dict(id='Father-1', role='father', status='proved')
                people = [dict(id='Child-1', parents=[father]),
                          dict(id='Mother-1', parents=[], childrenRecorded=[])]
                assessment = dict(assertion_id='A-mother', publication_status='approved',
                    people=['Child-1', 'Mother-1'], allow_new_relationship=approved,
                    source_ids=['Marriage-1', 'Baptism-1'], basis='Reviewed household sequence',
                    perspectives={'Child-1': {'relationship': 'mother'}})
                self.run_sync(people, {'Child-1': [
                    dict(id='Father-1', relationship='father', status='proved'),
                    dict(id='Mother-1', relationship='mother', status='probable', assertion_id='A-mother')
                ]}, assessments=[assessment])
                self.assertEqual(people[0]['parents'][0], father)
                mothers = [r for r in people[0]['parents'] if r['role'] == 'mother']
                self.assertEqual(len(mothers), int(approved))
                if approved:
                    self.assertEqual(mothers[0]['status'], 'probable')
                    self.assertEqual(people[1]['childrenRecorded'][0]['id'], 'Child-1')
                    self.assertEqual(people[1]['childrenRecorded'][0]['status'], 'probable')

    def test_reviewed_mother_addition_rejects_an_ancestry_cycle(self):
        people = [dict(id='Child-1', parents=[]), dict(id='Mother-1', parents=[
            dict(id='Child-1', role='mother', status='proved')])]
        assessment = dict(assertion_id='A-mother', publication_status='approved',
            people=['Child-1', 'Mother-1'], allow_new_relationship=True,
            source_ids=['S-1'], basis='Reviewed household',
            perspectives={'Child-1': {'relationship': 'mother'}})
        with self.assertRaisesRegex(ValueError, 'ancestry cycle'):
            self.run_sync(people, {'Child-1': [dict(id='Mother-1', relationship='mother',
                status='probable', assertion_id='A-mother')]}, assessments=[assessment])

    def test_replaces_old_parent_and_preserves_recorded_grade_and_mother(self):
        mother = {'id': 'Mother-1', 'role': 'mother', 'status': 'uncertain'}
        people = [dict(id='Child-1', parents=[dict(id='Old-1', role='father', status='uncertain'), mother], childrenRecorded=[]),
                  dict(id='Old-1', parents=[], childrenRecorded=[{'id': 'Child-1'}, {'id': 'Other-1'}]),
                  dict(id='Father-1', parents=[], childrenRecorded=[])]
        result = self.run_sync(people, {'Child-1': [{'id': 'Father-1', 'relationship': 'father', 'status': 'unknown', 'tree_status': 'uncertain'}], 'Father-1': []})
        child = people[0]
        self.assertEqual([(r['id'],r['status']) for r in child['parents'] if r['role']=='father'], [('Father-1','uncertain')])
        self.assertEqual(child['parents'][0]['id'], mother['id'])
        self.assertEqual(people[1]['childrenRecorded'], [{'id':'Other-1'}])
        self.assertEqual(people[2]['childrenRecorded'][0]['id'], 'Child-1')
        self.assertIn('Child-1', result['publicFamilySyncIds'])

    def test_adds_missing_published_child_and_records_proved_father(self):
        people = [dict(id='Father-1', parents=[], childrenRecorded=[])]
        result = self.run_sync(people, {'Child-1': [{'id':'Father-1','relationship':'father','status':'proved','reason':'Named in a testament'}], 'Father-1': []})
        self.assertEqual(result['publicFamilyNewIds'], ['Child-1'])
        child = next(p for p in people if p['id']=='Child-1')
        self.assertEqual(child['parents'][0]['status'], 'proved')
        self.assertEqual(child['parents'][0]['reason'], 'Named in a testament')
        self.assertTrue(child['parents'][0]['inModel'])

    def test_pending_creation_node_keeps_catalogue_account_and_father_on_repeat(self):
        people = [dict(id='Father-1', parents=[], childrenRecorded=[])]
        nodes = {'Father-1': dict(id='Father-1', name='Recorded father', url='/people/father-1.html',
            gender='Male', birth_year=1685, death_year=None, birth_status='uncertain', year=1746,
            year_basis='birth', year_status='uncertain', first_record_year=None),
            'record-sarah': dict(id='record-sarah', name='Recorded daughter', url='/people/record-sarah.html',
            gender='Female', birth_year=None, death_year=None, birth_status='unknown', year=1746,
            year_basis='record date', year_status='record date', first_record_year=1746)}
        dossiers = {
            'Father-1': dict(id='Father-1', name='Recorded father', pending_profile_creation=False,
                vitals={'birth': {'date':'1685','place':'Recorded locality'}}, relationships={'parents': []}),
            'record-sarah': dict(id='record-sarah', name='Recorded daughter', pending_profile_creation=True,
                vitals={'birth': {'date':'','place':'Recorded locality'}}, relationships={'parents': [
                    {'id':'Father-1','relationship':'father','status':'proved'}]})}
        for ident, dossier in dossiers.items():
            (self.site / 'people' / (ident.lower()+'.json')).write_text(json.dumps(dossier))
        edges = [dict(child='record-sarah', father='Father-1', status='proved')]
        with patch('tools.branch_connectivity.load_public_nodes', return_value=(nodes, edges, {'multiple_fathers': []})):
            result = apply_public_families(people, self.site)
            before = copy.deepcopy(people)
            apply_public_families(people, self.site)
        child = next(p for p in people if p['id'] == 'record-sarah')
        father = next(p for p in people if p['id'] == 'Father-1')
        self.assertEqual(child['recordUrl'], '/people/record-sarah.html')
        self.assertEqual(child['wikitreeUrl'], '')
        self.assertEqual(child['parents'][0]['id'], 'Father-1')
        self.assertEqual(father['id'], 'Father-1')
        self.assertEqual(people, before)

    def test_holds_competing_fathers_without_selecting_a_candidate(self):
        people = [dict(id='Child-1', parents=[dict(id='Father-1',role='father',status='unmarked')], childrenRecorded=[]),
                  dict(id='Father-1',parents=[],childrenRecorded=[{'id':'Child-1'}]),
                  dict(id='Other-1',parents=[],childrenRecorded=[])]
        result = self.run_sync(people, {'Child-1':[{'id':i,'relationship':'father','status':'uncertain'} for i in ['Father-1','Other-1']], 'Father-1':[], 'Other-1':[]}, ambiguous=['Child-1'])
        self.assertFalse(people[0]['parents'])
        self.assertEqual(len(people[0]['publicFatherAlternatives']), 2)
        self.assertEqual(result['publicFatherHoldIds'], ['Child-1'])

    def test_retains_selected_hypothesis_provenance(self):
        father = dict(id='Father-1',role='father',status='uncertain',hypothesis=True,assertion_id='A-selected',reason='Prior selected model')
        people = [dict(id='Child-1',parents=[father],childrenRecorded=[]), dict(id='Father-1',parents=[],childrenRecorded=[])]
        result = self.run_sync(people, {'Child-1':[{'id':'Father-1','relationship':'father','status':'uncertain'}], 'Father-1':[]})
        self.assertEqual(people[0]['parents'][0]['assertion_id'], 'A-selected')
        self.assertEqual(people[0]['parents'][0]['reason'], 'Prior selected model')
        self.assertNotIn('Child-1', result['publicFamilySyncIds'])

    def test_later_profiles_are_outside_the_historical_sync(self):
        people = [dict(id='Early-1',parents=[],childrenRecorded=[])]
        result = self.run_sync(people, {'Early-1':[], 'Later-1':[]}, years={'Later-1':1950})
        self.assertNotIn('Later-1', [p['id'] for p in people])
        self.assertEqual(result['publicFamilyScopeIds'], ['Early-1'])

    def test_unknown_assessment_without_a_tree_flag_remains_unknown(self):
        people = [dict(id='Child-1',parents=[],childrenRecorded=[]),dict(id='Father-1',parents=[],childrenRecorded=[])]
        self.run_sync(people, {'Child-1':[{'id':'Father-1','relationship':'father','status':'unknown'}], 'Father-1':[]})
        self.assertEqual(people[0]['parents'][0]['status'],'unknown')

    def test_withheld_parent_cannot_publish_an_identifier_or_source_url(self):
        people = [dict(id='Child-1',parents=[],childrenRecorded=[])]
        self.run_sync(people, {'Child-1':[{'relationship':'father','id':'Private-1','withheld':True,'url':'/private/capture'}]})
        rendered = json.dumps(people)
        self.assertNotIn('Private-1', rendered)
        self.assertNotIn('/private/capture', rendered)
        self.assertTrue(people[0]['parents'][0]['withheld'])
