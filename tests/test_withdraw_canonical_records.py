import unittest

from tools.withdraw_canonical_records import withdrawn_source


class WithdrawCanonicalRecordsTests(unittest.TestCase):
    def setUp(self):
        self.row = {'record_id': 'fixture-entry', 'source_url': 'https://example.org/index/1',
                    'publish_to_record_index': False, 'publication_withdrawal_reason': 'Date borrowed from another entry',
                    'reviewed_on': '2026-11-16', 'provenance': 'Reviewed fictional index'}
        self.public = [{'record_id': 'stable-id', 'source_url': self.row['source_url']}]
        self.document = {'url': self.row['source_url'], 'records': [{'id': 'stable-id'}],
                         'citations': [{'source': {'url': self.row['source_url']},
                                        'claims': [{'provenance': 'mapped_record'}]}], 'members': ['fictional-person']}

    def test_exact_entry_becomes_notice_without_person_or_dates(self):
        doc, ids = withdrawn_source(self.row, self.document, self.public)
        self.assertEqual(ids, {'fixture-entry', 'stable-id'})
        self.assertEqual(doc['members'], [])
        self.assertEqual(doc['citations'], [])
        self.assertEqual(doc['records'], [])
        self.assertEqual(doc['record_count'], 0)
        self.assertEqual(self.document['members'], ['fictional-person'])

    def test_mixed_source_and_non_generated_claims_are_rejected(self):
        self.document['records'].append({'id': 'unrelated'})
        with self.assertRaisesRegex(ValueError, 'unrelated records'):
            withdrawn_source(self.row, self.document, self.public)
        self.document['records'].pop()
        self.document['citations'][0]['claims'][0]['provenance'] = 'handwritten'
        with self.assertRaisesRegex(ValueError, 'non-generated'):
            withdrawn_source(self.row, self.document, self.public)

    def test_shared_page_url_does_not_authorize_withdrawing_other_entries(self):
        self.public.append({'record_id': 'another-entry', 'source_url': self.row['source_url']})
        self.document['records'].append({'id': 'another-entry'})
        with self.assertRaisesRegex(ValueError, 'unrelated records'):
            withdrawn_source(self.row, self.document, self.public)

    def test_single_unrelated_entry_is_not_a_stable_record_alias(self):
        self.row['profiles'] = {'Fixture-1': {'role': 'Child'}}
        self.public[0]['profile_ids'] = ['Fixture-2']
        with self.assertRaisesRegex(ValueError, 'does not identify'):
            withdrawn_source(self.row, self.document, self.public)

    def test_opt_out_reason_and_exact_url_are_required(self):
        self.row['publish_to_record_index'] = True
        with self.assertRaisesRegex(ValueError, 'opt-out'):
            withdrawn_source(self.row, self.document, self.public)
        self.row['publish_to_record_index'] = False
        self.document['url'] = 'https://example.org/another-source'
        with self.assertRaisesRegex(ValueError, 'URL mismatch'):
            withdrawn_source(self.row, self.document, self.public)

    def test_withdrawal_replaces_stale_source_page_body(self):
        from tools.ingest_canonical_records import source_page
        doc, _ = withdrawn_source(self.row, self.document, self.public)
        doc.update(id='s-fixture', title='Attribution withdrawn')
        shell = '<html><head><title>Old source</title></head><body><main><h1>Fictional child, 1797</h1></main></body></html>'
        result = source_page(shell, doc, existing=True)
        self.assertNotIn('Fictional child, 1797', result)
        self.assertIn('Date borrowed from another entry', result)
