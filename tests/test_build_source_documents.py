"""Source library documents are produced from the dossiers (fictional data)."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tools import build_source_documents as sources


def evidence(eid, url=None, title='Parish register', claim_ids=()):
    return {'id': eid, 'record_type': 'extracted citation', 'date': '1801', 'place': None, 'assertion': 'Cited.',
            'evidence_status': 'unassessed', 'source_quality': 'derivative', 'independence_group': 'SRC-1',
            'source': {'title': title, 'url': url, 'repository': None, 'reference': None}, 'claim_ids': list(claim_ids)}


class SourceDocuments(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.web = Path(self.tmp.name)
        url = 'https://example.org/register/1801'
        self.put('people/harrow-1.json', {'name': 'Ada Harrow', 'claims': [{'id': 'C-1', 'claim': 'Ada was baptised.'}],
                                          'evidence': [evidence('E-aaaaaaaaaaaa', url, claim_ids=['C-1']),
                                                       evidence('E-bbbbbbbbbbbb', None, 'Family bible')]})
        self.put('people/harrow-2.json', {'name': 'Ben Harrow', 'evidence': [evidence('E-cccccccccccc', url)]})
        self.put('people/harrow-9.json', {'name': 'Living', 'likely_living': True, 'evidence': [evidence('E-dddddddddddd', url)]})
        record_citation = {'person': '', 'evidence_id': 'E-1111111111111111', 'type': 'Baptism', 'source': {'url': url}}
        stale = {'person': 'harrow-1', 'evidence_id': 'E-eeeeeeeeeeee', 'type': 'extracted citation', 'source': {'url': url}}
        self.put('assets/v3/sources/s-0000000000000001.json', {
            'id': 's-0000000000000001', 'title': 'Register 1801', 'url': url, 'grouping_basis': 'exact source URL',
            'reference': 'kept', 'members': ['harrow-1'], 'citations': [stale, record_citation], 'records': [{'year': 1801}]})
        self.put('assets/v3/source-index.json', [{'id': 's-0000000000000001', 'title': 'Register 1801', 'from': 1801, 'to': 1801}])

    def tearDown(self):
        self.tmp.cleanup()

    def put(self, relative, value):
        path = self.web / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value))

    def test_documents_follow_the_dossiers_and_keep_ids_and_record_citations(self):
        changed, rows, counts = sources.build(self.web)
        doc = changed['s-0000000000000001']
        ids = [c['evidence_id'] for c in doc['citations']]
        self.assertEqual(ids, ['E-aaaaaaaaaaaa', 'E-cccccccccccc', 'E-1111111111111111'])   # stale dropped, record kept
        self.assertEqual(doc['citations'][0]['claims'], [{'id': 'C-1', 'claim': 'Ada was baptised.'}])
        self.assertEqual(doc['members'], ['harrow-1', 'harrow-2'])
        self.assertEqual(doc['reference'], 'kept')
        self.assertNotIn('harrow-9', json.dumps(changed))                                     # withheld dossier
        new = [d for sid, d in changed.items() if sid != 's-0000000000000001']
        self.assertEqual([d['title'] for d in new], ['Family bible'])
        self.assertEqual(counts['new sources'], 1)
        self.assertEqual({r['id'] for r in rows}, set(changed))

    def test_a_second_run_changes_nothing(self):
        changed, rows, _ = sources.build(self.web)
        for sid, doc in changed.items():
            self.put(f'assets/v3/sources/{sid}.json', doc)
        self.put('assets/v3/source-index.json', rows)
        self.assertEqual(sources.build(self.web)[0], {})


if __name__ == '__main__':
    unittest.main()
