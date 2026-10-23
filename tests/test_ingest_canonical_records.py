"""Guarded record/source ingest preserves identities and unrelated publications."""
import json
from datetime import date
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from tools.ingest_canonical_records import apply, plan, publish_reviewed
from tools.source_collection_index import build_index


class CanonicalRecordIngestTest(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.web = self.root / 'www'
        self.url = 'https://www.findmypast.co.uk/transcript?id=R_123'
        self.canonical = {
            'record_id': 'new-canonical-id', 'provider_record_id': 'R_123',
            'association': 'Unnamed Glasgow child — Scotland parish baptism',
            'year': 1784, 'date': '1784', 'place': 'Glasgow',
            'source_url': self.url + '&tab=this', 'status': 'Inspected transcript; identity unresolved',
            'reviewed_on': '2026-10-22', 'provenance': 'research/reviewed.json',
            'profiles': {'Glasgow-32': {'role': 'Compatible candidate only; record role not assigned',
                                       'timeline_group': 'Records for identity comparison'}},
        }
        self.put('research/canonical_records.json', [self.canonical])
        self.put('www/data/catalogue-search-index.json', [
            {'id': 'glasgow-32', 'name': 'Agnes Glasgow', 'profile_ids': ['Glasgow-32']}])
        self.put('www/people/glasgow-32.html', '<html>Original person, unchanged</html>')
        self.unrelated = {'record_id': 'unrelated', 'source_url': 'https://example.org/old', 'person': 'Keep me'}
        self.put('www/data/records-index.json', [self.unrelated, {'record_id': 'stable-record', 'source_url': self.url}])
        self.put('www/assets/research/record-index.json', [{'id': 'unrelated'}, {'id': 'stable-record'}])
        self.source = {'id': 's-0123456789abcdef', 'title': 'Maintained title', 'url': self.url,
                       'reference': 'Original reference', 'grouping_basis': 'exact source URL',
                       'members': [], 'records': [], 'citations': [], 'events': [],
                       'transcription': 'Preserved original reading', 'image': None}
        self.put('www/assets/v3/source-index.json', [
            {'id': self.source['id'], 'title': self.source['title'], 'members': [], 'records': 0, 'citations': 0}])
        self.put('www/assets/v3/sources/' + self.source['id'] + '.json', self.source)
        self.shell = '<html><head><title>Maintained</title></head><body><nav>Keep navigation</nav><main id="main">Original reading</main><footer>Keep footer</footer></body></html>'
        self.put('www/sources/' + self.source['id'] + '/index.html', self.shell)
        self.put('www/records/index.html', self.shell)
        self.put('www/sources/browse/index.html', self.shell.replace('Original reading', '<header>Maintained browse header</header>Old rows'))

    def put(self, relative, value):
        p = self.root / relative
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(value if isinstance(value, str) else json.dumps(value))

    def test_preserves_stable_ids_unrelated_rows_and_candidate_qualification(self):
        writes = plan(self.root, ['new-canonical-id'])
        rows = writes[self.web / 'data/records-index.json']
        self.assertEqual(rows[0], self.unrelated)
        self.assertEqual([r['record_id'] for r in rows], ['unrelated', 'stable-record'])
        record = rows[1]
        self.assertEqual(record['document_id'], self.source['id'])
        self.assertEqual(record['profile_context'], self.canonical['profiles'])
        self.assertIn('Compatible candidate only', record['note'])
        self.assertNotEqual(record['person'], 'Agnes Glasgow')
        source = writes[self.web / 'assets/v3/sources' / (self.source['id'] + '.json')]
        self.assertEqual(source['transcription'], 'Preserved original reading')
        self.assertEqual(source['title'], 'Maintained title')
        self.assertEqual(source['citations'][0]['status'], 'unassessed')
        page = writes[self.web / 'sources' / self.source['id'] / 'index.html']
        self.assertIn('Original reading', page)
        self.assertIn('Keep navigation', page)
        self.assertIn('Keep footer', page)
        self.assertIn('Compatible candidate only', page)
        self.assertFalse(any(p.parent == self.web / 'people' for p in writes))
        packed = writes[self.web / 'assets/v3/source-index-packed.json']
        self.assertEqual(packed['rows'][0][0], self.source['id'])
        browse = writes[self.web / 'sources/browse/index.html']
        self.assertIn(self.source['id'], browse)
        self.assertIn('Keep navigation', browse)
        self.assertIn('Maintained browse header', browse)

    def test_second_apply_is_idempotent(self):
        first = apply(self.root, ['new-canonical-id'], refresh_sources=False)
        self.assertGreater(first['changed_files'], 0)
        self.assertEqual(apply(self.root, ['new-canonical-id'], refresh_sources=False)['changed_files'], 0)

    def test_reviewed_original_and_history_quality_survive_all_public_views(self):
        for reviewed, expected in [('original_manuscript', 'original'),
                                   ('original_register', 'original'),
                                   ('late_compiled_history', 'secondary'),
                                   ('derivative_transcription', 'derivative')]:
            with self.subTest(reviewed=reviewed):
                self.canonical.update(source_quality=reviewed, source_title='Exact archival citation')
                self.put('research/canonical_records.json', [self.canonical])
                writes = plan(self.root, ['new-canonical-id'])
                record = writes[self.web / 'data/records-index.json'][1]
                compact = writes[self.web / 'assets/research/record-index.json'][1]
                source = writes[self.web / 'assets/v3/sources' / (self.source['id'] + '.json')]
                self.assertEqual(record['supporting_source_quality'], expected)
                self.assertEqual(compact['quality'], expected)
                self.assertEqual(source['citations'][0]['quality'], expected)
                self.assertEqual(record['source_title'], 'Exact archival citation')
                self.assertEqual(compact['title'], 'Exact archival citation')
                self.assertEqual(source['citations'][0]['source']['title'], 'Exact archival citation')
                self.assertEqual(source['title'], 'Maintained title')

    def test_new_source_uses_the_citation_title_not_the_family_assessment(self):
        self.canonical.update(source_title='Exact archival citation', source_url='https://example.org/new')
        self.canonical.pop('provider_record_id')
        self.put('research/canonical_records.json', [self.canonical])
        writes = plan(self.root, ['new-canonical-id'])
        record = writes[self.web / 'data/records-index.json'][-1]
        source = writes[self.web / 'assets/v3/sources' / (record['document_id'] + '.json')]
        self.assertEqual(source['title'], 'Exact archival citation')

    def test_reviewed_will_category_reaches_full_and_compact_indexes(self):
        self.canonical.update(record_category='Wills and probate',
                              association='James Glasgow, nephew in a will abstract')
        self.put('research/canonical_records.json', [self.canonical])
        writes = plan(self.root, ['new-canonical-id'])
        record = writes[self.web / 'data/records-index.json'][1]
        compact = writes[self.web / 'assets/research/record-index.json'][1]
        self.assertEqual(record['record_category'], 'Wills and probate')
        self.assertEqual(compact['category'], 'Wills and probate')

    def test_anonymous_record_does_not_invent_person(self):
        self.canonical['profiles'] = {}
        self.put('research/canonical_records.json', [self.canonical])
        record = plan(self.root, ['new-canonical-id'])[self.web / 'data/records-index.json'][1]
        self.assertEqual(record['catalogue_id'], '')
        self.assertTrue(record['person_url'].startswith('/sources/'))

    def test_unreviewed_or_nonpublic_context_aborts_before_writes(self):
        self.canonical.pop('reviewed_on')
        self.put('research/canonical_records.json', [self.canonical])
        with self.assertRaises(ValueError):
            plan(self.root, ['new-canonical-id'])
        self.assertEqual((self.web / 'records/index.html').read_text(), self.shell)

    def test_duplicate_existing_provider_identity_fails_closed(self):
        self.put('www/data/records-index.json', [
            {'record_id': 'one', 'source_url': self.url},
            {'record_id': 'two', 'source_url': self.url + '&tab=this'}])
        with self.assertRaisesRegex(ValueError, 'multiple existing record IDs'):
            plan(self.root, ['new-canonical-id'])

    def test_unrelated_source_rows_and_details_survive(self):
        old = {'id': 's-1111111111111111', 'title': 'Unrelated source', 'members': ['another-person'],
               'records': 7, 'citations': 9, 'from': 1700, 'custom': 'retain'}
        source = {**old, 'url': 'https://example.org/old-source', 'records': [], 'citations': []}
        self.put('www/assets/v3/source-index.json', [old, {'id': self.source['id'], 'title': self.source['title']}])
        self.put('www/assets/v3/sources/' + old['id'] + '.json', source)
        writes = plan(self.root, ['new-canonical-id'])
        self.assertEqual(writes[self.web / 'assets/v3/source-index.json'][0], old)
        self.assertNotIn(self.web / 'assets/v3/sources' / (old['id'] + '.json'), writes)

    def test_provider_id_must_agree_with_url(self):
        self.canonical['provider_record_id'] = 'R_other'
        self.put('research/canonical_records.json', [self.canonical])
        with self.assertRaisesRegex(ValueError, 'disagrees'):
            plan(self.root, ['new-canonical-id'])

    def test_collection_uses_record_year_and_jurisdiction_not_collection_span(self):
        self.source['title'] = 'Scotland, Parish Births & Baptisms 1564-1929'
        self.put('www/assets/v3/sources/' + self.source['id'] + '.json', self.source)
        self.canonical['place'] = 'Birmingham, England'
        self.put('research/canonical_records.json', [self.canonical])
        apply(self.root, ['new-canonical-id'], refresh_sources=False)
        row = build_index(self.web)[0]
        self.assertEqual(row['year'], 1784)
        self.assertEqual(row['years'], [1784])
        self.assertEqual(row['countries'], ['England'])
        self.assertEqual(row['year_basis'], 'record year')

    def test_source_reader_append_uses_secondary_heading(self):
        writes = plan(self.root, ['new-canonical-id'])
        page = writes[self.web / 'sources' / self.source['id'] / 'index.html']
        self.assertIn('<h2>Maintained title</h2>', page)
        self.assertNotIn('<h1>Maintained title</h1>', page)

    def test_glasgow_surname_does_not_override_reviewed_event_country(self):
        for country, place, label in (
                ('United States', 'Wayne County, Ohio', 'Alexander Glasgow — Ohio Obituary Index'),
                ('Ireland', 'Cork, Ireland', 'Alexander Glasgow — Irish Deaths 1864 - 1958')):
            with self.subTest(country=country):
                self.canonical.update(country=country, place=place, association=label)
                self.put('research/canonical_records.json', [self.canonical])
                record = plan(self.root, ['new-canonical-id'])[self.web / 'data/records-index.json'][1]
                self.assertEqual(record['country'], country.casefold())
                self.assertEqual(record['region'], country)
                self.assertEqual(record['record_category'], 'Deaths and burials')

    def test_event_place_precedes_collection_country_without_reviewed_country(self):
        self.canonical.update(place='Cork, Ireland', association='Alexander Glasgow — Scotland collection')
        self.put('research/canonical_records.json', [self.canonical])
        record = plan(self.root, ['new-canonical-id'])[self.web / 'data/records-index.json'][1]
        self.assertEqual(record['country'], 'ireland')

    def test_reviewed_override_can_withhold_structured_year_and_country(self):
        apply(self.root, ['new-canonical-id'], refresh_sources=False)
        override = {'sources': [{'id': self.source['id'],
                                'title_sha256': sha256(self.source['title'].encode()).hexdigest(),
                                'years': [], 'countries': []}]}
        original_read, original_exists = Path.read_text, Path.exists
        def read(path, *args, **kwargs):
            return json.dumps(override) if path.name == 'census-reference-overrides.json' else original_read(path, *args, **kwargs)
        def exists(path):
            return path.name == 'census-reference-overrides.json' or original_exists(path)
        with patch.object(Path, 'read_text', read), patch.object(Path, 'exists', exists):
            row = build_index(self.web)[0]
        self.assertIsNone(row['year'])
        self.assertEqual(row['years'], [])
        self.assertEqual(row['countries'], [])
        self.assertEqual(row['year_basis'], 'reviewed citation title')

    def test_replay_requires_explicit_boolean_opt_in(self):
        ignored = {**self.canonical, 'record_id': 'ignored', 'publish_to_record_index': 'true'}
        self.canonical['publish_to_record_index'] = True
        self.put('research/canonical_records.json', [ignored, self.canonical])
        result = publish_reviewed(self.root)
        self.assertEqual(result['selected_records'], 1)
        rows = json.loads((self.web / 'data/records-index.json').read_text())
        self.assertNotIn('ignored', [row['record_id'] for row in rows])
        self.assertEqual(publish_reviewed(self.root)['changed_files'], 0)

    def test_no_opt_ins_does_not_require_or_mutate_generated_site(self):
        self.put('research/canonical_records.json', [{'record_id': 'old-unreviewed-record'}])
        before = (self.web / 'records/index.html').read_text()
        with patch('tools.ingest_canonical_records.apply') as mutation:
            self.assertEqual(publish_reviewed(self.root), {'selected_records': 0, 'changed_files': 0})
        mutation.assert_not_called()
        self.assertEqual((self.web / 'records/index.html').read_text(), before)

    def test_opt_in_does_not_bypass_review_guard(self):
        self.canonical['publish_to_record_index'] = True
        self.canonical.pop('reviewed_on')
        self.put('research/canonical_records.json', [self.canonical])
        before = (self.web / 'data/records-index.json').read_text()
        with self.assertRaises(ValueError):
            publish_reviewed(self.root)
        self.assertEqual((self.web / 'data/records-index.json').read_text(), before)


    def test_later_event_for_sourced_historical_person_is_allowed(self):
        self.canonical.update(year=1901, date='1901', historical_basis={
            'latest_birth_year': 1799, 'source_url': 'https://example.org/birth-1799'})
        self.put('research/canonical_records.json', [self.canonical])
        record = plan(self.root, ['new-canonical-id'])[self.web / 'data/records-index.json'][1]
        self.assertEqual(record['filter_year'], 1901)
        self.assertEqual(record['historical_basis'], self.canonical['historical_basis'])

    def test_later_event_requires_independent_sourced_historical_bound(self):
        for basis in (None, {'latest_birth_year': 1799},
                      {'latest_birth_year': 1799, 'source_url': 'file:///private/capture'},
                      {'latest_birth_year': date.today().year - 120, 'source_url': 'https://example.org/birth'},
                      {'latest_birth_year': 1910, 'source_url': 'https://example.org/birth'},
                      {'latest_birth_year': True, 'source_url': 'https://example.org/birth'}):
            with self.subTest(basis=basis):
                self.canonical.update(year=1901, historical_basis=basis)
                self.put('research/canonical_records.json', [self.canonical])
                with self.assertRaisesRegex(ValueError, 'sourced historical birth bound'):
                    plan(self.root, ['new-canonical-id'])

    def test_later_event_never_bypasses_living_or_future_guards(self):
        self.canonical.update(year=1901, historical_basis={
            'latest_birth_year': 1799, 'source_url': 'https://example.org/birth'})
        for change in ({'living': True}, {'likely_living': True}, {'private': True},
                       {'year': date.today().year + 1}):
            with self.subTest(change=change):
                self.put('research/canonical_records.json', [{**self.canonical, **change}])
                with self.assertRaises(ValueError):
                    plan(self.root, ['new-canonical-id'])


if __name__ == '__main__':
    unittest.main()
