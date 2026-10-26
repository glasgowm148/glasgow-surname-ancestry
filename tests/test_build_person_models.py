"""Research-person models follow their dossiers (fictional data)."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tools import build_person_models as models


class PersonModels(unittest.TestCase):
    def test_stage_one_fields_follow_the_inputs_and_the_rest_is_kept(self):
        with TemporaryDirectory() as directory:
            web = Path(directory)
            def put(relative, value):
                path = web / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(value))
            put('people/harrow-1.json', {
                'name': 'Ada Harrow', 'identity': {'gender': 'Female'}, 'open_questions': [],
                'evidence': [{'id': 'E-aaaaaaaaaaaa'}, {'id': 'E-bbbbbbbbbbbb'}], 'claims': [{'id': 'C-1'}],
                'relationships': {'parents': [{'id': 'Harrow-2', 'name': 'Ben'}, {'id': 'Elsewhere-9', 'name': 'Cy'}]}})
            put('people/harrow-2.json', {'name': 'Ben Harrow'})
            put('assets/v3/sources/s-1.json', {'id': 's-1', 'citations': [{'person': 'harrow-1', 'evidence_id': 'E-aaaaaaaaaaaa'}]})
            put('data/records-index.json', [{'record_id': 'r2', 'catalogue_id': 'harrow-1'}, {'record_id': 'r1', 'catalogue_id': 'harrow-1'}])
            put('assets/research/branches.json', [
                {'id': 'family-harrow-2', 'label': 'Ben', 'url': '/branches/family-harrow-2/', 'kind': 'family', 'members': ['harrow-1']},
                {'id': 'region-x', 'kind': 'region', 'members': ['harrow-1']}])
            put('assets/research/people/harrow-1.json', {'id': 'Harrow-1', 'name': 'Ada Harow', 'vitals': {'birth': '1801'},
                                                        'events': [{'id': 'birth'}], 'evidence_count': 1})
            put('assets/research/people/harrow-3.json', {'redirect_to': '/assets/research/people/harrow-1.json'})
            changed, counts = models.build(web)
            model = changed['harrow-1']
            self.assertEqual(model['name'], 'Ada Harrow')
            self.assertEqual((model['evidence_count'], model['claims_count']), (2, 1))
            self.assertEqual(model['evidence_documents'], {'E-aaaaaaaaaaaa': 's-1'})
            self.assertEqual(model['source_documents'], ['s-1'])
            self.assertEqual(model['record_ids'], ['r1', 'r2'])
            self.assertEqual([b['id'] for b in model['branches']], ['family-harrow-2'])
            self.assertEqual([r['external'] for r in model['relationships']['parents']], [False, True])
            self.assertEqual((model['vitals'], model['events']), ({'birth': '1801'}, [{'id': 'birth'}]))   # kept
            self.assertNotIn('harrow-3', changed)
            models.main(['--web', str(web)])
            self.assertEqual(models.build(web)[0], {})


if __name__ == '__main__':
    unittest.main()
