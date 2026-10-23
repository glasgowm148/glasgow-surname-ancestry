"""Dispatch evidence gates must not invent genealogical conclusions."""
import unittest
import tempfile
import json
from pathlib import Path

from tools.research_preflight import build_preflight, findings_sections, record_needs_review, related_parent_account


def pair():
    return {'people': ['Glasgow-1', 'Glasgow-2'], 'publication_status': 'approved',
            'assertion_id': 'A', 'source_ids': [],
            'perspectives': {'Glasgow-1': {'relationship': 'father'}}}


def record():
    return {'record_id': 'new-record', 'provider_record_id': 'SCOT/OPR/BAP/123',
            'source_url': 'https://www.findmypast.co.uk/transcript?id=SCOT%2FOPR%2FBAP%2F123&tab=this',
            'status': 'Inspected provider transcript; original uninspected',
            'publish_to_record_index': True,
            'profiles': {'Glasgow-1': {'role': 'indexed child; compatible existing profile'},
                         'Glasgow-2': {'role': 'Named father John; current adult-profile identification retained without regrading'}}}


class ResearchPreflightTests(unittest.TestCase):
    def test_only_exact_current_conclusion_and_next_test(self):
        sections = findings_sections('## Current conclusion\nCurrent\n## Current conclusion — old\nSuperseded\n## Next useful test\nRead bond\n')
        assert sections['current_conclusion'][0]['value'] == 'Current'
        assert sections['next_questions'][0]['value'] == 'Read bond'
        assert 'Superseded' not in str(sections)
        assert findings_sections('## Current conclusion\n' + 'x' * 30, 10)['truncated']


    def test_new_explicit_source_requires_review_but_alias_does_not(self):
        r, a = record(), pair()
        for role in ['Named daughter Nancy', 'Recorded son John']:
            r['profiles']['Glasgow-1']['role'] = role
            assert record_needs_review(r, 'Glasgow-1', 'Glasgow-2', [a])
        r['profiles']['Glasgow-2']['role'] = 'Named father John; later adult identity unresolved'
        assert record_needs_review(r, 'Glasgow-1', 'Glasgow-2', [a])
        a['source_ids'] = ['https://www.findmypast.co.uk/transcript?id=SCOT/OPR/BAP/123']
        assert not record_needs_review(r, 'Glasgow-1', 'Glasgow-2', [a])
        a['source_ids'] = ['SCOT/OPR/BAP/999']
        a['assessment_history'] = [{'source_ids': ['SCOT/OPR/BAP/123']}]
        a['next_test'] = 'SCOT/OPR/BAP/123'
        assert record_needs_review(r, 'Glasgow-1', 'Glasgow-2', [a])
        r['relationship_review'] = {'assessments': [{'subject': 'Glasgow-1', 'assertion_id': 'OTHER'}]}
        assert record_needs_review(r, 'Glasgow-1', 'Glasgow-2', [a])
        r['relationship_review']['assessments'][0]['assertion_id'] = 'A'
        assert not record_needs_review(r, 'Glasgow-1', 'Glasgow-2', [a])


    def test_comparison_or_uninspected_record_is_not_parent_evidence(self):
        for field, value in [('role', 'Comparison with recorded father; candidate only'),
                             ('role', 'Possible father'), ('role', 'Father not named'), ('role', 'Father-in-law'), ('role', 'Father not established')]:
            r = record()
            r['profiles']['Glasgow-2'][field] = value
            assert not record_needs_review(r, 'Glasgow-1', None, [pair()])
        r = record()
        r['status'] = 'Original uninspected'
        assert not record_needs_review(r, 'Glasgow-1', None, [pair()])
        r = record()
        r['publish_to_record_index'] = False
        assert not record_needs_review(r, 'Glasgow-1', None, [pair()])


    def test_inventory_bounds_and_narrowing(self):
        with tempfile.TemporaryDirectory() as directory:
            self._inventory_bounds(Path(directory))


    def _inventory_bounds(self, tmp_path):
        metadata = tmp_path / 'data/wikitree'
        metadata.mkdir(parents=True)
        (metadata / 'profile-evidence.json').write_text(json.dumps({'profiles': {'Glasgow-1': {'privacy': 60, 'profile_fields': {'Name': 'Glasgow-1', 'IsLiving': 0}}}}))
        (metadata / 'live-profile-overrides.json').write_text('{}')
        research = tmp_path / 'research'
        (research / 'Glasgow-1').mkdir(parents=True)
        (research / 'Glasgow-1/findings.md').write_text('## Current conclusion\nKnown\n')
        (research / 'Glasgow-1/presentation.json').write_text(json.dumps({'research_tasks': ['read original'], 'completed_searches': ['index'], 'unrelated': 'omit'}))
        (research / 'relationship_assessments.json').write_text(json.dumps([pair()]))
        (research / 'canonical_records.json').write_text(json.dumps([record() for _ in range(6)]))
        result = build_preflight('Glasgow-1', 'Glasgow-2', root=tmp_path)
        assert len(result['source_inventory']['items']) == 5
        assert result['source_inventory']['truncated']
        assert result['source_inventory']['items'][0]['pointer'] == '/0'
        assert result['linked_parent_record_needs_review']
        assert result['presentation']['value']['completed_searches'] == ['index']
        assert 'unrelated' not in str(result['presentation'])
        assert not build_preflight('Glasgow-1', 'Glasgow-3', root=tmp_path)['linked_parent_record_needs_review']


    def test_unknown_privacy_withholds_packet(self):
        with tempfile.TemporaryDirectory() as directory:
            result = build_preflight('Glasgow-1', root=Path(directory))
            assert result['internal_only'] and result['withheld']
            assert 'findings' not in result

    def test_parent_account_is_bounded_and_independently_eligible(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / 'research/Glasgow-2'
            path.mkdir(parents=True)
            (path / 'findings.md').write_text('## Current conclusion\nInspected parent source\n## Next questions\n' + 'q' * 4000)
            parent_record = {'record_id': 'parent-only', 'status': 'Inspected original', 'profiles': {'Glasgow-2': {}}}
            context = {'rows': {'Glasgow-2': {'Privacy': 60, 'IsLiving': 0}}, 'checked': {},
                       'records': [record(), parent_record, parent_record, parent_record, parent_record]}
            result = related_parent_account('Glasgow-1', 'Glasgow-2', root=root, context=context)
            assert result['available'] and result['findings']['truncated']
            assert result['parent_only_sources']['total'] == 4
            assert len(result['parent_only_sources']['items']) == 3
            assert result['parent_only_sources']['items'][0]['pointer'] == '/1'
            assert sum(len(s['value']) for k in ('current_conclusion', 'next_questions') for s in result['findings'][k]) <= 3000
            context['rows']['Glasgow-2']['IsLiving'] = 1
            withheld = related_parent_account('Glasgow-1', 'Glasgow-2', root=root, context=context)
            assert withheld['withheld'] and 'findings' not in withheld
            unavailable = related_parent_account('Glasgow-1', 'record-only-parent', root=root, context=context)
            assert not unavailable['available'] and 'findings' not in unavailable

    def test_existing_reviewed_andrew_fixture(self):
        root = Path(__file__).resolve().parents[1]
        result = build_preflight('Glasgow-1333', 'Glasgow-81', root=root)
        assert result['findings']['current_conclusion']
        assert any(r['record_id'] == 'fmp-record-r-686351978' for r in result['source_inventory']['items'])
        # Existing canonical relationship_review acknowledges the exact approved pair.
        assert not result['linked_parent_record_needs_review']


if __name__ == "__main__":
    unittest.main()
