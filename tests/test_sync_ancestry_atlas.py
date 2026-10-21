import unittest
from copy import deepcopy

from tools.approved_restorations import documentary_renderer
from tools.sync_ancestry_atlas import overlay_model


class AtlasWorkingTests(unittest.TestCase):
    def test_existing_record_account_gets_real_urls_without_changing_dates(self):
        old = {'meta': {}, 'landmarks': [], 'sections': [], 'people': [
            {'id': '@smaller-families', 'kind': 'group'},
            {'id': 'Father-1', 'kind': 'person', 'parents': [], 'childrenRecorded': []},
            {'id': 'record-daughter', 'kind': 'person', 'born': 1742, 'parents': []}]}
        fresh = deepcopy(old)
        fresh['meta'].update(date='2026-10-17', publicFamilyScopeIds=['record-daughter'],
                             publicFamilyRelatedIds=['Father-1'])
        fresh['people'][2].update(born=1743, recordUrl='/people/record-daughter.html',
                                 catalogueUrl='/people/record-daughter.html', wikitreeUrl='',
                                 parents=[{'id': 'Father-1', 'role': 'father', 'status': 'proved'}])
        result = overlay_model(old, fresh)
        child = next(p for p in result['people'] if p['id'] == 'record-daughter')
        self.assertEqual(child['recordUrl'], '/people/record-daughter.html')
        self.assertEqual(child['wikitreeUrl'], '')
        self.assertEqual(child['born'], 1742)
        self.assertEqual(child['edge']['parent'], 'Father-1')
        self.assertEqual(overlay_model(result, fresh), result)

    def test_reviewed_family_alias_uses_canonical_account_without_merging_facts(self):
        old = {'meta': {}, 'landmarks': [], 'sections': [], 'people': [
            {'id': '@smaller-families', 'kind': 'group'},
            {'id': 'Father-1', 'kind': 'person', 'partners': [
                {'id': 'Alias-1', 'role': 'spouse', 'name': 'Superseded name'}]},
            {'id': 'Child-1', 'kind': 'person', 'parents': [
                {'id': 'Alias-1', 'role': 'mother', 'status': 'uncertain'}], 'edge': {'parent': 'Alias-1'}},
            {'id': 'Alias-1', 'kind': 'person', 'name': 'Superseded name', 'born': 1540}]}
        fresh = deepcopy(old)
        fresh['people'] = [p for p in fresh['people'] if p['id'] != 'Alias-1']
        fresh['people'].append(dict(id='Mother-1', kind='person', name='Canonical mother', born=1560,
                                   parents=[], partners=[{'id': 'Father-1'}], edge={'parent': '@smaller-families'}))
        fresh['meta'].update(date='2026-10-17', reviewedFamilyAliases={'Alias-1': 'Mother-1'})
        result = overlay_model(old, fresh)
        people = {p['id']: p for p in result['people']}
        self.assertNotIn('Alias-1', people)
        self.assertEqual(people['Mother-1']['born'], 1560)
        self.assertEqual(people['Child-1']['parents'][0]['id'], 'Mother-1')
        self.assertEqual(people['Child-1']['parents'][0]['status'], 'uncertain')
        self.assertEqual(people['Child-1']['edge']['parent'], 'Mother-1')
        self.assertEqual(people['Father-1']['partners'][0]['previous_profile_id'], 'Alias-1')
        self.assertEqual(result, overlay_model(result, fresh))
        invalid = deepcopy(fresh); invalid['meta']['reviewedFamilyAliases'] = {'Alias-1': 'Absent-1'}
        with self.assertRaisesRegex(ValueError, 'canonical public model targets'):
            overlay_model(old, invalid)

    def test_scoped_recorded_mother_missing_from_main_is_restored(self):
        old = {'meta': {}, 'landmarks': [], 'sections': [], 'people': [
            {'id': '@smaller-families', 'kind': 'group'},
            {'id': 'Child-1', 'kind': 'person', 'parents': [
                {'id': 'Father-1', 'role': 'father', 'status': 'confident'}]},
            {'id': 'Father-1', 'kind': 'person', 'childrenRecorded': [{'id': 'Child-1'}]}]}
        fresh = deepcopy(old)
        fresh['meta'].update(date='2026-10-17', publicFamilyScopeIds=['Child-1'],
                             publicFamilyRelatedIds=['Father-1', 'Mother-1'],
                             publicMotherGradeScope={'Child-1': ['Mother-1']})
        fresh['people'][1]['parents'].append(dict(id='Mother-1', role='mother', status='proved'))
        fresh['people'].append(dict(id='Mother-1', kind='person', parents=[], name='Recorded mother',
                                   childrenRecorded=[{'id': 'Child-1'}], edge={'parent': '@smaller-families'}))
        out = overlay_model(old, fresh)
        people = {p['id']: p for p in out['people']}
        self.assertCountEqual(people['Child-1']['parents'], fresh['people'][1]['parents'])
        self.assertEqual(people['Mother-1']['childrenRecorded'], [{'id': 'Child-1'}])
        self.assertEqual(overlay_model(out, fresh), out)
        # A reviewed grade for another captured mother cannot replace a
        # different mother retained in the main model.
        old['people'][1]['parents'].append(dict(id='OtherMother-1', role='mother', status='confident'))
        protected = overlay_model(old, fresh)
        self.assertEqual(protected['people'][1]['parents'][0]['id'], 'OtherMother-1')
        self.assertNotIn('Mother-1', {p['id'] for p in protected['people']})

    def test_scoped_mother_fills_only_an_unidentified_export_placeholder(self):
        placeholder = dict(id='', name='Parent outside current One-Tree export',
                           role='mother', status='unmarked')
        old = {'meta': {}, 'landmarks': [], 'sections': [], 'people': [
            {'id': '@smaller-families', 'kind': 'group'},
            {'id': 'Child-1', 'kind': 'person', 'parents': [deepcopy(placeholder)]}]}
        fresh = deepcopy(old)
        mother = dict(id='Mother-1', role='mother', status='proved')
        fresh['meta'].update(date='2026-10-21', publicFamilyScopeIds=['Child-1'],
                             publicMotherGradeScope={'Child-1': ['Mother-1']})
        fresh['people'][1]['parents'] = [mother]
        fresh['people'].append(dict(id='Mother-1', kind='person', parents=[],
                                   childrenRecorded=[{'id': 'Child-1'}]))
        out = overlay_model(old, fresh)
        self.assertEqual(next(p for p in out['people'] if p['id'] == 'Child-1')['parents'], [mother])
        self.assertIn('Mother-1', {p['id'] for p in out['people']})
        self.assertEqual(overlay_model(out, fresh), out)
        for protected in [dict(placeholder, withheld=True),
                          dict(placeholder, id='Other-1'),
                          dict(placeholder, status='non-biological')]:
            old['people'][1]['parents'] = [protected]
            out = overlay_model(old, fresh)
            self.assertEqual(next(p for p in out['people'] if p['id'] == 'Child-1')['parents'], [protected])

    def test_maternal_replacement_keeps_reciprocal_history_in_main_atlas(self):
        old = {'meta': {}, 'landmarks': [], 'sections': [], 'dna': {'approved': ['retain']}, 'people': [
            {'id': 'Child-1', 'kind': 'person', 'parents': [
                {'id': 'OldFather-1', 'role': 'father', 'status': 'uncertain'},
                {'id': 'OldMother-1', 'role': 'mother', 'status': 'unmarked'}]},
            {'id': 'OldFather-1', 'kind': 'person', 'childrenRecorded': [{'id': 'Child-1'}]},
            {'id': 'OldMother-1', 'kind': 'person', 'note': 'Approved mother account',
             'childrenRecorded': [{'id': 'Child-1'}, {'id': 'Other-1'}]},
            {'id': 'NewFather-1', 'kind': 'person', 'childrenRecorded': []},
            {'id': 'NewMother-1', 'kind': 'person', 'childrenRecorded': []}]}
        fresh = deepcopy(old)
        fresh['meta'].update(date='2026-10-17', workingParentAlternativeIds=['OldFather-1', 'OldMother-1'],
                             workingMotherIds=['NewMother-1'])
        fresh['people'][0].update(parents=[
            dict(id='NewFather-1', role='father', status='uncertain', hypothesis=True),
            dict(id='NewMother-1', role='mother', status='uncertain', hypothesis=True)],
            edge=dict(parent='NewFather-1', type='hypothesis'),
            priorWorkingParents=deepcopy(old['people'][0]['parents']))
        fresh['people'][1].update(childrenRecorded=[], priorWorkingChildren=[{'id': 'Child-1'}])
        fresh['people'][2].update(childrenRecorded=[{'id': 'Other-1'}], priorWorkingChildren=[{'id': 'Child-1'}],
                                  note='Short import')
        fresh['people'][3]['childrenRecorded'] = [{'id': 'Child-1'}]
        fresh['people'][4]['childrenRecorded'] = [{'id': 'Child-1'}]
        out = overlay_model(old, fresh)
        people = {p['id']: p for p in out['people']}
        self.assertEqual(people['Child-1']['parents'], fresh['people'][0]['parents'])
        self.assertEqual(people['Child-1']['priorWorkingParents'], old['people'][0]['parents'])
        self.assertEqual(people['OldMother-1']['childrenRecorded'], [{'id': 'Other-1'}])
        self.assertEqual(people['OldMother-1']['priorWorkingChildren'], [{'id': 'Child-1'}])
        self.assertEqual(people['OldMother-1']['note'], 'Approved mother account')
        self.assertEqual(people['OldFather-1']['priorWorkingChildren'], [{'id': 'Child-1'}])
        self.assertEqual(people['NewMother-1']['childrenRecorded'], [{'id': 'Child-1'}])
        self.assertEqual(out['dna'], old['dna'])
        self.assertEqual(overlay_model(out, fresh), out)

    def test_existing_mother_grade_is_scoped_reciprocal_and_reversible(self):
        old = {'meta': {}, 'landmarks': [], 'sections': [], 'people': [
            {'id': '@smaller-families', 'kind': 'group'},
            {'id': 'Child-1', 'kind': 'person', 'parents': [
                {'id': 'Father-1', 'role': 'father', 'status': 'confident'},
                {'id': 'Mother-1', 'role': 'mother', 'status': 'unmarked'}]},
            {'id': 'Father-1', 'kind': 'person', 'childrenRecorded': [{'id': 'Child-1'}]},
            {'id': 'Mother-1', 'kind': 'person', 'born': 1700, 'note': 'Approved account',
             'childrenRecorded': [{'id': 'Other-1'}]},
            {'id': 'Child-2', 'kind': 'person', 'parents': [
                {'id': 'Mother-2', 'role': 'mother', 'status': 'unmarked'}]},
            {'id': 'Mother-2', 'kind': 'person', 'childrenRecorded': [{'id': 'Child-2'}]}]}
        fresh = deepcopy(old)
        fresh['meta'].update(date='2026-10-17', publicFamilyScopeIds=['Child-1', 'Child-2'],
                             publicFamilyRelatedIds=['Father-1', 'Mother-1'],
                             publicMotherGradeScope={'Child-1': ['Mother-1']})
        fresh['people'][1]['parents'][1]['status'] = 'probable'
        fresh['people'][3].update(born=1710, note='Short import')
        fresh['people'][3]['childrenRecorded'].append({'id': 'Child-1', 'status': 'probable'})
        fresh['people'][4]['parents'][0]['status'] = 'proved'  # Outside the reviewed scope.
        out = overlay_model(old, fresh)
        self.assertEqual(next(r for r in out['people'][1]['parents'] if r['role'] == 'mother')['status'], 'probable')
        self.assertEqual(out['people'][4]['parents'][0]['status'], 'unmarked')
        self.assertEqual((out['people'][3]['born'], out['people'][3]['note']), (1700, 'Approved account'))
        self.assertEqual(out['people'][3]['childrenRecorded'][-1]['status'], 'probable')
        self.assertEqual(overlay_model(out, fresh), out)
        fresh['meta']['publicMotherGradeScope'] = {}
        fresh['people'][1]['parents'][1]['status'] = 'unmarked'
        fresh['people'][3]['childrenRecorded'][-1]['status'] = 'unmarked'
        reverted = overlay_model(out, fresh)
        self.assertEqual(next(r for r in reverted['people'][1]['parents'] if r['role'] == 'mother')['status'], 'unmarked')
        self.assertEqual(reverted['people'][3]['childrenRecorded'][-1]['status'], 'unmarked')

    def test_reviewed_birthplace_can_be_cleared_without_changing_map_context(self):
        old = {'meta': {}, 'landmarks': [], 'sections': [], 'people': [
            {'id': '@root', 'kind': 'group'},
            {'id': 'Parent-1', 'kind': 'person', 'name': 'Approved name',
             'birthplace': 'Unsupported birthplace', 'locationLabel': 'Documented residence',
             'childrenRecorded': []}]}
        fresh = deepcopy(old)
        fresh['meta'].update(date='2026-10-16', reviewedChronologyDisplay={
            'Parent-1': {'birthplace': None, 'locationLabel': 'Unreviewed map label'}})
        out = overlay_model(old, fresh)
        self.assertIsNone(out['people'][1]['birthplace'])
        self.assertEqual(out['people'][1]['locationLabel'], 'Documented residence')
        self.assertEqual(old['people'][1]['birthplace'], 'Unsupported birthplace')
        self.assertEqual(overlay_model(out, fresh), out)

    def test_reviewed_parent_chronology_can_clear_an_unsupported_birth(self):
        old = {'meta': {}, 'landmarks': [], 'sections': [], 'people': [
            {'id': '@root', 'kind': 'group'},
            {'id': 'Child-1', 'kind': 'person', 'parents': [], 'edge': {'parent': '@root'}},
            {'id': 'Mother-1', 'kind': 'person', 'name': 'Approved name', 'born': 1766,
             'birthDisplay': 'c. 1766', 'died': 1784, 'birthplace': 'Approved place',
             'note': 'Approved account', 'childrenRecorded': []}]}
        fresh = deepcopy(old)
        fresh['meta'].update(date='2026-10-16', workingMotherIds=['Mother-1'])
        fresh['people'][1].update(parents=[{'id': 'Mother-1', 'role': 'mother'}],
                                  edge={'parent': 'Mother-1', 'type': 'hypothesis'})
        fresh['people'][2].update(born=None, birthDisplay='Unknown', birthplace='Unreviewed place')
        self.assertEqual(overlay_model(old, fresh)['people'][2]['born'], 1766)
        fresh['meta']['reviewedChronologyDisplay'] = {
            'Mother-1': {'born': None, 'birthDisplay': 'Unknown', 'name': 'Unreviewed name'}}
        out = overlay_model(old, fresh)
        mother = out['people'][2]
        self.assertIsNone(mother['born'])
        self.assertEqual(mother['birthDisplay'], 'Unknown')
        self.assertEqual((mother['name'], mother['birthplace'], mother['note'], mother['died']),
                         ('Approved name', 'Approved place', 'Approved account', 1784))
        self.assertEqual(old['people'][2]['born'], 1766)
        self.assertEqual(overlay_model(out, fresh), out)

    def test_retained_only_parent_archives_both_replaced_children_and_reverts(self):
        old = {'meta': {}, 'landmarks': [], 'sections': [], 'people': [
            {'id': '@root', 'kind': 'group'},
            {'id': 'Old-1', 'kind': 'person', 'note': 'Approved parent account', 'born': 1690,
             'childrenRecorded': [{'id': 'Child-1'}, {'id': 'Child-2'}, {'id': 'Other-1'}]},
            {'id': 'New-1', 'kind': 'person', 'childrenRecorded': []},
            *[{'id': i, 'kind': 'person', 'parents': [{'id': 'Old-1', 'role': 'father'}],
               'edge': {'parent': 'Old-1'}} for i in ['Child-1', 'Child-2']]]}
        fresh = deepcopy(old)
        old['people'][3].update(born=1758, birthplace='Approved region', researchUrl='/evidence/')
        fresh['people'][3].update(born=1760, birthplace='Unreviewed export town')
        fresh['people'] = [p for p in fresh['people'] if p['id'] != 'Old-1']
        fresh['meta'].update(date='2026-10-16', workingParentAlternativeIds=['Old-1'])
        for p in fresh['people']:
            if p['id'].startswith('Child-'):
                p.update(priorWorkingParents=deepcopy(p['parents']),
                    parents=[{'id': 'New-1', 'role': 'father', 'status': 'uncertain'}],
                    edge={'parent': 'New-1', 'type': 'hypothesis'})
        fresh['people'][1]['childrenRecorded'] = [{'id': i} for i in ['Child-1', 'Child-2']]
        result = overlay_model(old, fresh)
        child = next(p for p in result['people'] if p['id'] == 'Child-1')
        self.assertEqual((child['born'], child['birthplace'], child['researchUrl']),
                         (1758, 'Approved region', '/evidence/'))
        prior = next(p for p in result['people'] if p['id'] == 'Old-1')
        self.assertEqual(prior['childrenRecorded'], [{'id': 'Other-1'}])
        self.assertCountEqual(prior['priorWorkingChildren'], [{'id': 'Child-1'}, {'id': 'Child-2'}])
        self.assertEqual((prior['note'], prior['born']), ('Approved parent account', 1690))
        self.assertEqual(result, overlay_model(result, fresh))
        fresh['meta']['workingParentAlternativeIds'] = []
        for p in fresh['people']:
            if p['id'].startswith('Child-'):
                p.pop('priorWorkingParents')
                p.update(parents=[{'id': 'Old-1', 'role': 'father'}], edge={'parent': 'Old-1'})
            elif p['id'] == 'New-1':
                p['childrenRecorded'] = []
        reverted = next(p for p in overlay_model(result, fresh)['people'] if p['id'] == 'Old-1')
        self.assertEqual({k: v for k, v in reverted.items() if k != 'childrenRecorded'},
                         {k: v for k, v in old['people'][1].items() if k != 'childrenRecorded'})
        self.assertCountEqual(reverted['childrenRecorded'], old['people'][1]['childrenRecorded'])

    def test_working_mother_is_reciprocal_and_can_be_withdrawn_independently(self):
        old = {'meta': {}, 'landmarks': [], 'sections': [], 'people': [
            {'id': '@root', 'kind': 'group'},
            {'id': 'Child-1', 'kind': 'person', 'parents': [], 'edge': {'parent': '@root'}},
            {'id': 'Father-1', 'kind': 'person', 'childrenRecorded': []},
            {'id': 'Mother-1', 'kind': 'person', 'note': 'Approved account', 'childrenRecorded': [{'id': 'Other-1'}]}]}
        fresh = deepcopy(old);fresh['meta'].update(date='2026-10-16', workingMotherIds=['Mother-1'], maternalHypotheses=1)
        fresh['people'][1].update(parents=[{'id': 'Father-1', 'role': 'father'}, {'id': 'Mother-1', 'role': 'mother'}],
                                  edge={'parent': 'Father-1', 'type': 'hypothesis'})
        fresh['people'][2]['childrenRecorded'] = [{'id': 'Child-1'}]
        fresh['people'][3]['childrenRecorded'].append({'id': 'Child-1', 'status': 'uncertain'})
        result = overlay_model(old, fresh)
        self.assertEqual(result['people'][3]['note'], 'Approved account')
        self.assertEqual(result['people'][3]['childrenRecorded'], fresh['people'][3]['childrenRecorded'])
        fresh['meta'].update(workingMotherIds=[], maternalHypotheses=0)
        fresh['people'][1]['parents'].pop();fresh['people'][3]['childrenRecorded'].pop()
        reverted = overlay_model(result, fresh)
        self.assertEqual(reverted['people'][3]['childrenRecorded'], [{'id': 'Other-1'}])
        self.assertEqual(reverted['people'][1]['parents'], [{'id': 'Father-1', 'role': 'father'}])

    def test_selected_replacement_preserves_parent_accounts_and_reverts(self):
        old={'meta':{},'landmarks':[],'sections':[],'people':[
            {'id':'@root','kind':'group'},
            {'id':'Child-1','kind':'person','parents':[{'id':'Old-1','role':'father'}],'edge':{'parent':'Old-1'}},
            {'id':'Old-1','kind':'person','note':'Approved old account','childrenRecorded':[{'id':'Child-1'},{'id':'Other-1'}]},
            {'id':'New-1','kind':'person','note':'Approved new account','childrenRecorded':[]}]}
        fresh=deepcopy(old);fresh['meta'].update(date='2026-10-16',workingParentAlternativeIds=['Old-1'])
        fresh['people'][1].update(parents=[{'id':'New-1','role':'father'}],edge={'parent':'New-1','type':'hypothesis'})
        fresh['people'][2].update(note='Short import',childrenRecorded=[{'id':'Other-1'}],priorWorkingChildren=[{'id':'Child-1'}])
        fresh['people'][3]['childrenRecorded']=[{'id':'Child-1'}]
        result=overlay_model(old,fresh)
        self.assertEqual(result['people'][2]['note'],'Approved old account')
        self.assertEqual(result['people'][3]['note'],'Approved new account')
        self.assertEqual(result['people'][2]['childrenRecorded'],[{'id':'Other-1'}])
        self.assertEqual(result,overlay_model(result,fresh))
        fresh=deepcopy(old);fresh['meta']['date']='2026-10-16'
        reverted=overlay_model(result,fresh)
        for actual,expected in zip(reverted['people'],old['people']):
            self.assertEqual({k:v for k,v in actual.items() if k!='childrenRecorded'},
                             {k:v for k,v in expected.items() if k!='childrenRecorded'})
            self.assertCountEqual(actual.get('childrenRecorded',[]),expected.get('childrenRecorded',[]))

    def test_recorded_family_can_add_missing_father_without_replacing_other_profiles(self):
        old = {'meta': {}, 'landmarks': [], 'sections': [], 'people': [
            {'id': '@root', 'kind': 'group'},
            {'id': 'Child-1', 'kind': 'person', 'parents': [], 'edge': {'parent': '@root'}},
            {'id': 'Other-1', 'kind': 'person', 'note': 'Approved account'}]}
        fresh = deepcopy(old)
        fresh['meta'].update(date='2026-10-16', reviewedFamilyRestorationIds=['Child-1', 'Father-1'])
        fresh['people'][1].update(parents=[{'id': 'Father-1', 'role': 'father', 'status': 'proved'}],
                                  edge={'parent': 'Father-1', 'type': 'recorded'})
        fresh['people'].append({'id': 'Father-1', 'kind': 'person', 'edge': {'parent': '@root'}})
        result = overlay_model(old, fresh)
        self.assertEqual(result['people'][1]['edge']['parent'], 'Father-1')
        self.assertEqual(result['people'][2], old['people'][2])
        self.assertEqual(result['meta']['hypotheses'], 0)
        self.assertEqual(result, overlay_model(result, fresh))

    def test_reciprocal_working_children_preserve_parent_facts_and_revoke_cleanly(self):
        old={'meta':{},'landmarks':[],'sections':[],'people':[
            {'id':'Father-1','kind':'person','note':'Approved detailed biography','born':1500,
             'childrenRecorded':[{'id':'Other-1','name':'Other child'}]},
            {'id':'Child-1','kind':'person','parents':[],'edge':{'parent':'@root'}},
            {'id':'@root','kind':'group'}]}
        fresh=deepcopy(old);fresh['meta']['date']='2026-10-16'
        fresh['people'][0].update(note='Shorter import',born=1510,childrenRecorded=[{'id':'Child-1','status':'uncertain'}])
        fresh['people'][1].update(parents=[{'id':'Father-1','status':'uncertain'}],edge={'parent':'Father-1','type':'hypothesis'})
        result=overlay_model(old,fresh);father=result['people'][0]
        self.assertEqual((father['note'],father['born']),('Approved detailed biography',1500))
        self.assertEqual([r['id'] for r in father['childrenRecorded']],['Other-1','Child-1'])
        fresh['people'][1]=deepcopy(old['people'][1]);fresh['people'][0]['childrenRecorded']=[]
        restored=overlay_model(result,fresh)['people'][0]
        self.assertEqual(restored,old['people'][0])

    def test_confident_role_correction_reaches_primary_view_and_can_be_withdrawn(self):
        old = {'meta': {}, 'dna': [], 'landmarks': [], 'sections': [],
               'people': [{'id':'Child-1','kind':'person','parents':[], 'edge':{'parent':'Sibling-1'}},
                          {'id':'Sibling-1','kind':'person'}, {'id':'Father-1','kind':'person'}]}
        fresh=deepcopy(old);fresh['meta'].update(date='2026-10-16',reviewedParentReplacementIds=['Child-1'])
        fresh['people'][0].update(parents=[{'id':'Father-1','status':'strongly_supported'}],
                                   edge={'parent':'Father-1','type':'recorded'})
        result=overlay_model(old,fresh)
        self.assertEqual(result['people'][0]['edge']['parent'],'Father-1')
        self.assertEqual(result['meta']['reviewedParentReplacementIds'],['Child-1'])
        fresh['meta']['reviewedParentReplacementIds']=[];fresh['people'][0]=deepcopy(old['people'][0])
        self.assertEqual(overlay_model(result,fresh)['people'][0],old['people'][0])

    def test_overlay_preserves_approved_features_and_updates_subjects(self):
        old = {'meta': {}, 'dna': [{'id': 'Child-1', 'approved': True}],
               'landmarks': ['Child-1'], 'sections': [{'id': 'Child-1'}],
               'people': [{'id': '@root', 'kind': 'group'},
                          {'id': 'Child-1', 'kind': 'person', 'parents': [], 'edge': {'parent': '@root'}},
                          {'id': 'Other-1', 'kind': 'person', 'note': 'retained'}]}
        fresh = deepcopy(old)
        fresh['meta']['date'] = '2026-10-15'
        fresh['people'][1].update(parents=[{'id': 'record-father', 'status': 'uncertain'}],
                                   edge={'parent': 'record-father', 'type': 'hypothesis'})
        fresh['people'].append({'id': 'record-father', 'kind': 'person', 'documentary': True,
                                'born': None, 'died': None, 'edge': {'parent': '@root'}})
        fresh['sections'].append({'id': 'record-father'})
        result = overlay_model(old, fresh)
        self.assertEqual(result['dna'], old['dna'])
        self.assertTrue(set(old['landmarks']) <= set(result['landmarks']))
        self.assertEqual(result['people'][2], old['people'][2])
        self.assertEqual(result['meta']['hypotheses'], 1)
        self.assertEqual(result, overlay_model(result, fresh))
        # Withdrawing a selected hypothesis restores the current public parent fields.
        fresh['people'][1] = deepcopy(old['people'][1])
        self.assertEqual(overlay_model(result, fresh)['people'][1]['parents'], [])

    def test_renderer_transform_preserves_other_functions(self):
        source = "const wiki=id=>'https://www.wikitree.com/wiki/'+encodeURIComponent(id);\nconst catalogue=p=>p.catalogueId===null?'x':'/people/'+encodeURIComponent(p.catalogueId||p.id.toLowerCase())+'.html';\nfunction renderDNA(){return 'approved controls'}"
        output = documentary_renderer(source)
        self.assertIn('p?.recordUrl', output)
        self.assertIn("function renderDNA(){return 'approved controls'}", output)
        self.assertEqual(output, documentary_renderer(output))


class AtlasPublishedFamilyTests(unittest.TestCase):
    def test_published_family_updates_father_but_retains_approved_account_and_mother(self):
        old = {'meta': {}, 'landmarks': [], 'sections': [], 'dna': [{'approved': True}], 'people': [
            {'id': '@root', 'kind': 'group'}, {'id': '@smaller-families', 'kind': 'group'},
            {'id': 'Child-1', 'kind': 'person', 'name':'Approved name', 'note':'Approved annotation',
             'born':1600,'parents':[{'id':'Old-1','role':'father','status':'unmarked'}, {'id':'Mother-1','role':'mother','status':'uncertain'}],
             'edge':{'parent':'Old-1','role':'father'},'childrenRecorded':[]},
            {'id':'Old-1','kind':'person','childrenRecorded':[{'id':'Child-1'},{'id':'Other-1'}]},
            {'id':'Father-1','kind':'person','childrenRecorded':[]},
            {'id':'Mother-1','kind':'person','childrenRecorded':[]}]}
        fresh = deepcopy(old);fresh['meta'].update(date='2026-10-16',publicFamilyScopeIds=['Child-1'],publicFamilyRelatedIds=['Old-1','Father-1'])
        fresh['people'][2].update(name='Different export name',note='',born=1601,
            parents=[{'id':'Father-1','role':'father','status':'proved'}],
            edge={'parent':'Father-1','role':'father','status':'proved','type':'recorded'})
        fresh['people'][3]['childrenRecorded']=[{'id':'Other-1'}]
        fresh['people'][4]['childrenRecorded']=[{'id':'Child-1','status':'proved'}]
        out=overlay_model(old,fresh);p={p['id']:p for p in out['people']}
        self.assertEqual(out['dna'],old['dna'])
        self.assertEqual([p['Child-1'][k] for k in ['name','note','born']],['Approved name','Approved annotation',1600])
        self.assertEqual(p['Child-1']['edge']['parent'],'Father-1')
        self.assertEqual(p['Child-1']['parents'][0]['id'],'Mother-1')
        self.assertEqual(p['Old-1']['childrenRecorded'],[{'id':'Other-1'}])
        self.assertEqual(p['Father-1']['childrenRecorded'][0]['id'],'Child-1')
        self.assertEqual(overlay_model(out,fresh),out)
