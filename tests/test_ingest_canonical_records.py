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

    def test_search_result_does_not_claim_transcript_locality(self):
        self.canonical.update(
            status='Search result only; transcript uninspected',
            record_precision='Search-result locality; transcript uninspected',
        )
        self.put('research/canonical_records.json', [self.canonical])
        writes = plan(self.root, ['new-canonical-id'])
        record = next(r for r in writes[self.web / 'data/records-index.json']
                      if r['record_id'] == 'stable-record')
        self.assertEqual(record['record_precision'],
                         'Search-result locality; transcript uninspected')
        page = writes[self.web / 'sources' / self.source['id'] / 'index.html']
        self.assertIn('Search result only; transcript uninspected', page)
        self.assertIn('Original reading', page)

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

    def test_explicit_title_correction_keeps_identity_and_labels_earlier_reading(self):
        self.canonical.update(source_title='Corrected archival title',
                              source_title_supersedes='Maintained title',
                              source_title_correction_reason='Both originals confirm the corrected name.')
        self.put('research/canonical_records.json', [self.canonical])
        self.source['records'] = [dict(id='new-canonical-id', year=1784, date='1784')]
        self.source['citations'] = [dict(evidence_id='earlier-citation', person='glasgow-32',
                                       assertion='Earlier contributor reading.',
                                       source={'title': 'Maintained title'})]
        self.put('www/assets/v3/sources/' + self.source['id'] + '.json', self.source)
        self.put('www/sources/' + self.source['id'] + '/index.html', self.shell.replace(
            '</main>', '<!-- static-source-evidence:start -->Stale evidence<!-- static-source-evidence:end --></main>'))
        writes = plan(self.root, ['new-canonical-id'])
        source = writes[self.web / 'assets/v3/sources' / (self.source['id'] + '.json')]
        self.assertEqual(source['title'], 'Corrected archival title')
        self.assertEqual([r['id'] for r in source['records']], ['stable-record'])
        self.assertEqual(source['transcription'], 'Preserved original reading')
        self.assertTrue(source['citations'][0]['type'].startswith('Earlier source reading, superseded'))
        page = writes[self.web / 'sources' / self.source['id'] / 'index.html']
        self.assertIn('Earlier reading, superseded:', page)
        self.assertIn('Earlier contributor reading.', page)
        self.assertNotIn('Stale evidence', page)
        self.assertIn('Earlier source reading, superseded', page)
        apply(self.root, ['new-canonical-id'], refresh_sources=False)
        self.assertEqual(apply(self.root, ['new-canonical-id'], refresh_sources=False)['changed_files'], 0)

    def test_title_correction_rejects_unexpected_maintained_title_before_writing(self):
        self.canonical.update(source_title='Corrected title', source_title_supersedes='Different old title',
                              source_title_correction_reason='Reviewed correction.')
        self.put('research/canonical_records.json', [self.canonical])
        path = self.web / 'assets/v3/sources' / (self.source['id'] + '.json')
        before = path.read_bytes()
        with self.assertRaisesRegex(ValueError, 'source-title correction'):
            apply(self.root, ['new-canonical-id'], refresh_sources=False)
        self.assertEqual(path.read_bytes(), before)

    def test_retained_record_identity_replaces_its_earlier_canonical_alias(self):
        url = 'https://example.org/register/page1'
        self.canonical['source_url'] = url
        self.canonical.pop('provider_record_id')
        self.put('research/canonical_records.json', [self.canonical])
        self.source['url'] = url
        self.put('www/assets/v3/sources/' + self.source['id'] + '.json', self.source)
        self.put('www/data/records-index.json', [self.unrelated,
            dict(record_id='stable-record', source_url=url, profile_ids='Glasgow-32'),
            dict(record_id='new-canonical-id', source_url=url, profile_ids='Glasgow-99')])
        self.put('www/assets/research/record-index.json', [dict(id='stable-record'), dict(id='new-canonical-id')])
        writes = plan(self.root, ['new-canonical-id'])
        self.assertEqual([r['record_id'] for r in writes[self.web / 'data/records-index.json']], ['unrelated', 'stable-record'])
        self.assertEqual([r['id'] for r in writes[self.web / 'assets/research/record-index.json']], ['stable-record'])

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

    def use_register_page(self, existing):
        page = 'https://example.org/register/Baptisms_1834.html'
        self.canonical.update(source_url=page, provider_record_id=None)
        self.put('research/canonical_records.json', [self.canonical])
        self.put('www/data/records-index.json', [{'source_url': page, **row} for row in existing])
        return page

    def test_entries_on_one_register_page_are_told_apart_by_the_people_named(self):
        self.use_register_page([{'record_id': 'other-baptism', 'profile_ids': 'Glasgow-951 | McCaughan-222'},
                                {'record_id': 'same-entry', 'profile_ids': 'Glasgow-32'},
                                {'record_id': 'third-baptism', 'profile_ids': ['Glasgow-973']}])
        rows = plan(self.root, ['new-canonical-id'])[self.web / 'data/records-index.json']
        self.assertEqual([r['record_id'] for r in rows], ['other-baptism', 'same-entry', 'third-baptism'])
        self.assertEqual(rows[1]['profile_context'], self.canonical['profiles'])

    def test_a_new_entry_on_a_known_page_becomes_its_own_record(self):
        self.use_register_page([{'record_id': 'other-baptism', 'profile_ids': 'Glasgow-951'}])
        rows = plan(self.root, ['new-canonical-id'])[self.web / 'data/records-index.json']
        self.assertEqual([r['record_id'] for r in rows], ['other-baptism', 'new-canonical-id'])

    def test_two_existing_rows_for_the_same_entry_still_fail_closed(self):
        self.use_register_page([{'record_id': 'one', 'profile_ids': 'Glasgow-32'},
                                {'record_id': 'two', 'profile_ids': ['Glasgow-32']}])
        with self.assertRaisesRegex(ValueError, 'multiple existing record IDs'):
            plan(self.root, ['new-canonical-id'])

    def test_a_new_source_page_keeps_the_standard_reader_container(self):
        self.put('www/assets/v3/source-index.json', [])
        rows = plan(self.root, ['new-canonical-id'])
        page = next(text for path, text in rows.items() if path.name == 'index.html' and 'sources/s-' in path.as_posix())
        self.assertEqual(page.count('<div id="v3-reader"'), 1)
        self.assertLess(page.index('canonical-record-ingest:end'), page.index('<div id="v3-reader"'))

    def test_repair_layout_adds_the_reader_once_to_pages_without_it(self):
        from tools.ingest_canonical_records import repair_layout
        self.put('www/sources/' + self.source['id'] + '/index.html', '<html><main id="main">Old</main></html>')
        self.assertEqual(repair_layout(self.root), ['sources/' + self.source['id'] + '/index.html'])
        self.assertEqual(repair_layout(self.root), [])
        text = (self.web / 'sources' / self.source['id'] / 'index.html').read_text()
        self.assertIn('Open the cited archive', text)

    def test_duplicate_existing_source_url_ids_remain_ambiguous(self):
        duplicate_id = 's-2222222222222222'
        self.put('www/assets/v3/source-index.json', [
            {'id': self.source['id'], 'title': self.source['title']},
            {'id': duplicate_id, 'title': 'Duplicate provider source'}])
        self.put('www/assets/v3/sources/' + duplicate_id + '.json', {
            **self.source, 'id': duplicate_id, 'title': 'Duplicate provider source'})
        with self.assertRaisesRegex(ValueError, 'ambiguous existing exact-URL source IDs'):
            plan(self.root, ['new-canonical-id'])

    def test_generated_source_id_collision_is_checked_lazily(self):
        url = 'https://example.org/new-reviewed-source'
        sid = 's-' + sha256(url.encode()).hexdigest()[:16]
        self.canonical.update(source_url=url)
        self.canonical.pop('provider_record_id')
        self.put('research/canonical_records.json', [self.canonical])
        self.put('www/assets/v3/source-index.json', [{'id': sid, 'title': 'Unrelated collision'}])
        self.put('www/assets/v3/sources/' + sid + '.json', {
            'id': sid, 'title': 'Unrelated collision', 'url': 'https://example.org/old-source',
            'records': [], 'citations': [], 'members': []})
        with self.assertRaisesRegex(ValueError, 'Source ID collision'):
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

    def test_wholly_dated_source_preserves_maintained_source_bounds(self):
        self.put('www/assets/v3/source-index.json', [
            {'id': self.source['id'], 'title': self.source['title'], 'members': [],
             'records': 0, 'citations': 0, 'from': 1700, 'to': 1800}])
        source = plan(self.root, ['new-canonical-id'])[self.web / 'assets/v3/source-index.json'][0]
        self.assertEqual((source['from'], source['to']), (1700, 1800))

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

    def undated(self):
        self.canonical.update(year=None, date_status='undated', date='Undated',
                              historical_basis={'latest_event_year': 1784,
                                                'source_url': 'https://example.org/event-1784',
                                                'reason': 'A separately dated public parish entry bounds this occurrence.'})
        self.put('research/canonical_records.json', [self.canonical])

    def test_reviewed_undated_publish_replay_keeps_null_years_and_source_ids(self):
        self.undated()
        self.canonical['publish_to_record_index'] = True
        self.canonical['source_title'] = 'Scotland, Parish Births & Baptisms 1564-1929'
        self.put('research/canonical_records.json', [self.canonical])
        result = publish_reviewed(self.root)
        self.assertEqual(result['selected_records'], 1)
        record = json.loads((self.web / 'data/records-index.json').read_text())[1]
        compact = json.loads((self.web / 'assets/research/record-index.json').read_text())[1]
        self.assertEqual(record['record_id'], 'stable-record')
        self.assertEqual(record['document_id'], self.source['id'])
        self.assertEqual((record['year'], record['filter_year'], compact['y']), ('Undated', None, None))
        self.assertEqual(compact['year'], 'Undated')
        self.assertEqual(record['date_status'], 'undated')
        source = json.loads((self.web / 'assets/v3/source-index.json').read_text())[0]
        doc = json.loads((self.web / 'assets/v3/sources' / (self.source['id'] + '.json')).read_text())
        self.assertEqual((source['from'], source['to'], source['date_basis']), (None, None, 'reviewed undated'))
        self.assertIsNone(doc['records'][0]['year'])
        collection = build_index(self.web)[0]
        self.assertIsNone(collection['year'])
        self.assertEqual(collection['years'], [])
        self.assertEqual(collection['year_basis'], 'reviewed undated')
        self.assertEqual(publish_reviewed(self.root)['changed_files'], 0)

    def test_undated_label_and_sourced_birth_bound(self):
        self.undated()
        self.canonical['date'] = 'Undated parish occurrence'
        self.canonical['historical_basis'] = {'latest_birth_year': 1780,
                                              'source_url': 'https://example.org/birth-1780',
                                              'explanation': 'The named person has an independently indexed 1780 birth.'}
        self.put('research/canonical_records.json', [self.canonical])
        record = plan(self.root, ['new-canonical-id'])[self.web / 'data/records-index.json'][1]
        self.assertEqual(record['year'], 'Undated parish occurrence')
        self.assertIsNone(record['filter_year'])

    def test_undated_census_collection_title_cannot_supply_event_year(self):
        self.undated()
        self.source['title'] = 'Scotland Census 1881 collection'
        self.put('www/assets/v3/sources/' + self.source['id'] + '.json', self.source)
        apply(self.root, ['new-canonical-id'], refresh_sources=False)
        collection = build_index(self.web)[0]
        self.assertEqual(collection['year_basis'], 'reviewed undated')
        self.assertIsNone(collection['year'])
        self.assertEqual(collection['years'], [])

    def test_mixed_source_retains_only_actual_dated_record_year(self):
        self.undated()
        self.source['records'] = [{'id': 'older', 'year': 1790, 'date': '1790', 'country': 'Scotland'}]
        self.put('www/assets/v3/sources/' + self.source['id'] + '.json', self.source)
        writes = plan(self.root, ['new-canonical-id'])
        source = writes[self.web / 'assets/v3/source-index.json'][0]
        doc = writes[self.web / 'assets/v3/sources' / (self.source['id'] + '.json')]
        self.assertEqual((source['from'], source['to']), (1790, 1790))
        self.assertEqual(doc['date_basis'], 'reviewed record years with undated records')
        apply(self.root, ['new-canonical-id'], refresh_sources=False)
        collection = build_index(self.web)[0]
        self.assertEqual((collection['year'], collection['years']), (1790, [1790]))

    def test_undated_requires_explicit_safe_historical_bound(self):
        self.undated()
        good = dict(self.canonical)
        invalid = [
            {'year': None, 'date_status': None}, {'year': None, 'date_status': 'undated', 'historical_basis': None},
            {'year': None, 'date_status': 'undated', 'historical_basis': {'latest_event_year': 1901, 'source_url': 'https://example.org/x', 'reason': 'Bound'}},
            {'year': None, 'date_status': 'undated', 'historical_basis': {'latest_event_year': True, 'source_url': 'https://example.org/x', 'reason': 'Bound'}},
            {'year': None, 'date_status': 'undated', 'historical_basis': {'latest_birth_year': date.today().year - 120, 'source_url': 'https://example.org/x', 'reason': 'Bound'}},
            {'year': None, 'date_status': 'undated', 'historical_basis': {'latest_event_year': 1784, 'source_url': 'file:///private/capture', 'reason': 'Bound'}},
            {'year': None, 'date_status': 'undated', 'historical_basis': {'latest_event_year': 1784, 'source_url': 'https://example.org/x', 'reason': '  '}},
            {'year': False}, {'year': date.today().year + 1},
        ]
        for change in invalid:
            with self.subTest(change=change):
                self.put('research/canonical_records.json', [{**good, **change}])
                with self.assertRaises(ValueError):
                    plan(self.root, ['new-canonical-id'])


if __name__ == '__main__':
    unittest.main()
