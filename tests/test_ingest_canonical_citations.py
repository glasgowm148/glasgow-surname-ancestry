"""Shared evidence retains distinct per-person citation contexts."""
from copy import deepcopy
import unittest

from tools.ingest_canonical_records import merge, merge_citations, plan
from tests import test_ingest_canonical_records as fixtures


class CitationIdentityTests(unittest.TestCase):
    def test_ingest_plan_accepts_shared_existing_evidence(self):
        fixture = fixtures.CanonicalRecordIngestTest()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        source_path = fixture.web / 'assets/v3/sources' / (fixture.source['id'] + '.json')
        incoming = plan(fixture.root, ['new-canonical-id'])[source_path]['citations'][0]
        other = {**incoming, 'person': 'glasgow-12', 'assertion': 'Preserved other context'}
        fixture.source['citations'] = [{**incoming, 'assertion': 'Old context'}, other]
        fixture.put(str(source_path.relative_to(fixture.root)), fixture.source)
        citations = plan(fixture.root, ['new-canonical-id'])[source_path]['citations']
        self.assertEqual(citations, [incoming, other])

    def test_shared_evidence_updates_matching_person_and_appends_new_context(self):
        rows = [
            {'evidence_id': 'E-shared', 'person': 'glasgow-649', 'assertion': 'First context'},
            {'evidence_id': 'E-shared', 'person': 'glasgow-12', 'assertion': 'Second context'},
            {'evidence_id': 'E-other', 'person': 'glasgow-649', 'claims': ['keep']},
            {'evidence_id': 'E-other', 'person': 'glasgow-1543', 'claims': ['also keep']},
        ]
        supplied = [
            {'evidence_id': 'E-shared', 'person': 'glasgow-1543', 'assertion': 'Third context'},
            {'evidence_id': 'E-shared', 'person': 'glasgow-12', 'assertion': 'Updated context'},
        ]
        before = deepcopy((rows, supplied))
        expected = [rows[0], supplied[1], rows[2], rows[3], supplied[0]]
        self.assertEqual(merge_citations(rows, supplied), expected)
        self.assertEqual((rows, supplied), before)
        self.assertEqual(merge_citations(expected, supplied), expected)

    def test_duplicate_pair_in_existing_or_incoming_citations_is_rejected(self):
        citation = {'evidence_id': 'E-shared', 'person': 'glasgow-649'}
        for existing, incoming in [([citation, dict(citation)], []),
                                   ([], [citation, dict(citation)])]:
            with self.subTest(existing=bool(existing)):
                with self.assertRaisesRegex(ValueError, 'Duplicate .*evidence_id, person'):
                    merge_citations(existing, incoming)

    def test_other_merge_keys_remain_strict(self):
        for key in ['record_id', 'id']:
            row = {key: 'shared'}
            for existing, incoming in [([row, dict(row)], []), ([], [row, dict(row)])]:
                with self.subTest(key=key, existing=bool(existing)):
                    with self.assertRaisesRegex(ValueError, f'Duplicate {key}'):
                        merge(existing, incoming, key)


if __name__ == '__main__':
    unittest.main()
