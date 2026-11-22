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

    def test_legacy_lookup_follows_public_record_and_drops_a_withdrawn_alias(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            web = root / 'www'
            older, current = '1' * 16, 'ancestry-123-456'
            source = 's-' + '3' * 16
            url = 'https://example.org/public-register'

            def put(path, value):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(value))

            put(root / details.RETIRED_URLS, {'record_lookups': {
                'published_on': '2026-11-14', 'bundle_sha256': 'a' * 64,
                'records': {older: [current, source, url]},
            }})
            row = {'record_id': current, 'document_id': source, 'source_url': url, 'note': 'Reviewed entry'}
            full = web / 'data/records-index.json'
            compact = web / 'assets/research/record-index.json'
            source_json = web / f'assets/v3/sources/{source}.json'
            put(full, [row])
            put(compact, [{'id': current, 'document_id': source}])
            doc = {'id': source, 'url': url, 'records': [{'id': older}]}
            put(source_json, doc)
            put(web / f'assets/research/records/{current}.json', dict(row, local_generator_detail='Ignored'))
            alias = web / f'assets/research/records/{older}.json'

            self.assertEqual(details.repair_legacy_lookups(web), {'legacy_record_lookups': 1})
            output = json.loads(alias.read_text())
            self.assertEqual(output['record_id'], older)
            self.assertEqual(output['canonical_record_id'], current)
            self.assertEqual(output['superseded_by'], current)
            self.assertEqual(output['note'], row['note'])
            self.assertNotIn('local_generator_detail', output)
            self.assertEqual(json.loads(full.read_text()), [row])
            self.assertEqual(json.loads(compact.read_text()), [{'id': current, 'document_id': source}])
            self.assertEqual(details.repair_legacy_lookups(web), {})

            put(source_json, dict(doc, annotations={'publication_withdrawal': {'reason': 'Scope'}}))
            self.assertEqual(details.repair_legacy_lookups(web), {'removed_legacy_record_lookups': 1})
            self.assertFalse(alias.exists())
            put(source_json, doc)
            put(compact, [])
            put(alias, dict(row, record_id=older))
            self.assertEqual(details.repair_legacy_lookups(web), {'removed_legacy_record_lookups': 1})
            self.assertFalse(alias.exists())

            put(compact, [{'id': current, 'document_id': source}])
            notice = {'record_id': older, 'withdrawn': True, 'reason': 'Scope'}
            put(alias, notice)
            self.assertEqual(details.repair_legacy_lookups(web), {})
            self.assertEqual(json.loads(alias.read_text()), notice)


if __name__ == '__main__':
    unittest.main()
