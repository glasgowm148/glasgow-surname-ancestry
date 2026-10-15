import unittest
from copy import deepcopy

from tools.approved_restorations import documentary_renderer
from tools.sync_ancestry_atlas import overlay_model


class AtlasWorkingTests(unittest.TestCase):
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
