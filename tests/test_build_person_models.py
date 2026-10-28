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
            put('assets/research/event-index.json', [{'p': 'harrow-1', 'id': 'birth', 'kind': 'personal'},
                                                     {'p': 'harrow-1', 'id': 'E-1', 'kind': 'mention'}])
            changed, counts = models.build(web)
            model = changed['harrow-1']
            self.assertEqual(model['name'], 'Ada Harrow')
            self.assertEqual((model['evidence_count'], model['claims_count']), (2, 1))
            self.assertEqual(model['evidence_documents'], {'E-aaaaaaaaaaaa': 's-1'})
            self.assertEqual(model['source_documents'], ['s-1'])
            self.assertEqual(model['record_ids'], ['r1', 'r2'])
            self.assertEqual([b['id'] for b in model['branches']], ['family-harrow-2'])
            self.assertEqual([r['external'] for r in model['relationships']['parents']], [False, True])
            self.assertEqual(model['vitals'], {'birth': '1801'})                                          # kept
            self.assertEqual([e['id'] for e in model['events']], ['birth'])                            # from the index
            self.assertEqual([e['id'] for e in model['mentions']], ['E-1'])
            self.assertNotIn('harrow-3', changed)
            models.main(['--web', str(web)])
            self.assertEqual(models.build(web)[0], {})

    def test_stage_three_vitals_and_new_models(self):
        with TemporaryDirectory() as directory:
            web = Path(directory)
            def put(relative, value):
                path = web / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(value))
            put('people/harrow-1.json', {'id': 'Harrow-1', 'name': 'Ada Harrow', 'vitals': {
                'birth': {'date': '1801-03-02', 'place': 'Perth, Perthshire, Scotland', 'status': 'exact'},
                'death': {'date': '1870', 'place': 'Ayr', 'status': 'uncertain', 'provenance': {'reviewed': '2026-01-01'}}}})
            put('people/harrow-4.json', {'id': 'Harrow-4', 'name': 'Dot Harrow', 'vitals': {'birth': {'date': '1830'}}})
            put('people/harrow-5.json', {'id': 'Harrow-5', 'name': 'Ed Harrow', 'likely_living': True})
            put('assets/research/atlas-import.json', {'people': [{'id': 'Harrow-4', 'kind': 'person'}]})
            put('assets/research/people/harrow-1.json', {'id': 'Harrow-1', 'vitals': {
                'birth': {'date': '1801', 'place': 'Perth', 'status': 'uncertain', 'display_date': '1801',
                          'country': 'other', 'basis': 'imported_vital'},
                'death': {'date': '1870', 'place': 'Ayr', 'status': 'uncertain'}},
                'original_vitals': {'birth': {'date': '1801'}}, 'review': {'title': 'Current conclusion'}, 'dna': [{'id': 'x'}]})
            changed, counts = models.build(web)
            model = changed['harrow-1']
            self.assertEqual(model['vitals']['birth'], {'date': '1801-03-02', 'place': 'Perth, Perthshire, Scotland',
                                                        'status': 'exact', 'display_date': '2 March 1801',
                                                        'country': 'scotland', 'basis': 'imported_vital'})
            self.assertEqual(model['vitals']['death']['provenance'], {'reviewed': '2026-01-01'})   # the dossier's own form
            self.assertNotIn('country', model['vitals']['death'])
            for kept in ('original_vitals', 'review', 'dna'):
                self.assertEqual(model[kept], {'original_vitals': {'birth': {'date': '1801'}},
                                               'review': {'title': 'Current conclusion'}, 'dna': [{'id': 'x'}]}[kept])
            created = changed['harrow-4']
            self.assertEqual((created['id'], created['catalogue_id'], created['atlas']), ('Harrow-4', 'harrow-4', True))
            self.assertEqual(created['vitals'], {'birth': {'date': '1830'}})
            self.assertEqual(created['url'], '/people/harrow-4.html')
            self.assertNotIn('harrow-5', changed)                                                    # likely living
            self.assertEqual(counts['models created'], 1)
            models.main(['--web', str(web)])
            self.assertEqual(models.build(web)[0], {})


if __name__ == '__main__':
    unittest.main()
