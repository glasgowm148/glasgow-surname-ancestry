"""Record detail files are produced from the indexes (fictional data)."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tools import build_record_details as details


class RecordDetails(unittest.TestCase):
    def test_files_follow_the_index_and_keep_their_own_fields(self):
        with TemporaryDirectory() as directory:
            web = Path(directory)
            def put(relative, value):
                path = web / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(value))
            put('data/records-index.json', [
                {'record_id': 'r1', 'catalogue_id': 'harrow-1', 'supporting_source_title': 'Newer register'},
                {'record_id': 'r2', 'catalogue_id': 'harrow-2', 'supporting_source_title': 'Census'}])
            put('assets/research/record-index.json', [{'id': 'r1', 'country': 'scotland', 'research_date': True},
                                                      {'id': 'r2', 'country': 'oceania'}])
            put('assets/v3/sources/s-1.json', {'id': 's-1', 'records': [{'id': 'r1'}]})
            put('assets/research/records/r1.json', {'record_id': 'r1', 'supporting_source_title': 'Old register',
                                                    'reviewed_location_original': {'kept': True}})
            put('assets/research/records/r9.json', {'record_id': 'r9', 'note': 'no longer indexed'})
            changed, counts = details.build(web)
            self.assertEqual(changed['r1'], {'reviewed_location_original': {'kept': True}, 'record_id': 'r1',
                                             'catalogue_id': 'harrow-1', 'supporting_source_title': 'Newer register',
                                             'country': 'scotland', 'document_id': 's-1',
                                             'person_url': '/people/harrow-1.html', 'research_date': True})
            self.assertEqual(changed['r2']['country'], 'oceania')
            self.assertNotIn('r9', changed)
            self.assertEqual(dict(counts), {'record files updated': 1, 'new record files': 1})
            details.main(['--web', str(web)])
            self.assertEqual(details.build(web)[0], {})


if __name__ == '__main__':
    unittest.main()
