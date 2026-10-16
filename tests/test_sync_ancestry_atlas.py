import unittest
from copy import deepcopy

from tools.approved_restorations import documentary_renderer
from tools.sync_ancestry_atlas import overlay_model


class AtlasWorkingTests(unittest.TestCase):
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
