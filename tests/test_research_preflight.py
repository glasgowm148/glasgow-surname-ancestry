"""Dispatch evidence gates must not invent genealogical conclusions."""
import unittest
import tempfile
import json
import hashlib
from pathlib import Path

from tools.research_preflight import build_preflight, findings_sections, record_needs_review, related_parent_account, _safe_research_path


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

    def test_parent_biography_faris_quote_has_capture_pointer_and_pending_draft(self):
        result = build_preflight('Glasgow-2003', 'Glasgow-12')
        parent = result['related_parent_account']['biographical_kinship_leads']
        captured = [x for x in parent['items'] if x.get('source_kind') == 'captured_biography']
        pending = [x for x in parent['items'] if x.get('source_kind') == 'pending_draft']
        assert any(x.get('pointer') == '/profiles/Glasgow-12/biography_wikitext'
                   and 'at least two children of Robert Glasgow' in x['excerpt']
                   and 'Nancy (Glasgow) McClelland' in x['excerpt'] for x in captured)
        assert pending and all(x.get('path', '').startswith('research/Glasgow-12/') for x in pending)
        assert result['findings']['current_conclusion']

    def test_biography_kinship_leads_are_private_bounded_and_independently_eligible(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'data/wikitree').mkdir(parents=True)
            (root / 'research/Glasgow-1').mkdir(parents=True)
            (root / 'research/Glasgow-2').mkdir(parents=True)
            child_text = ('In this account Nancy was the daughter of Robert Glasgow.\n\n' +
                          'Glasgow-1 was a parent in an unrelated note.\n\n' +
                          '\n\n'.join(f'Nancy was a child of Robert Glasgow in account {i}.' for i in range(4)))
            parent_text = ('Nancy McClelland was one of Robert’s children.\n\n' +
                           '\n\n'.join(f'Robert’s daughter Nancy appears in paragraph {i}.' for i in range(4)))
            evidence = {'profiles': {
                'Glasgow-1': {'privacy': 60, 'profile_fields': {'Name': 'Nancy McClelland', 'IsLiving': 0}, 'biography_wikitext': child_text},
                'Glasgow-2': {'privacy': 60, 'profile_fields': {'Name': 'Robert Glasgow', 'IsLiving': 0}, 'biography_wikitext': parent_text},
            }}
            evidence_path = root / 'data/wikitree/profile-evidence.json'
            evidence_path.write_text(json.dumps(evidence))
            child_draft = root / 'research/Glasgow-1/review.wiki'
            parent_draft = root / 'research/Glasgow-2/review.wiki'
            child_draft.write_text(child_text)
            parent_draft.write_text(parent_text)
            integration = {'profile_updates': {'Glasgow-1': {'draft_path': 'research/Glasgow-1/review.wiki'},
                                                'Glasgow-2': {'draft_path': 'research/Glasgow-2/review.wiki'}}}
            integration_path = root / 'research/queue-review-2026-10-17/catalogue-integration.json'
            integration_path.parent.mkdir(parents=True, exist_ok=True)
            integration_path.write_text(json.dumps(integration))
            (root / 'research/Glasgow-1/findings.md').write_text('## Current conclusion\nExisting conclusion\n')
            before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in (evidence_path, child_draft, parent_draft)}
            context = {'rows': {'Glasgow-1': {'Privacy': 60, 'IsLiving': 0, 'Name': 'Nancy McClelland'},
                                'Glasgow-2': {'Privacy': 60, 'IsLiving': 0, 'Name': 'Robert Glasgow'}},
                       'origins': {}, 'checked': {}, 'assessments': [], 'records': []}
            packet = build_preflight('Glasgow-1', 'Glasgow-2', root=root, context=context)
            leads = packet['biographical_kinship_leads']
            assert packet['findings']['current_conclusion'][0]['value'] == 'Existing conclusion'
            assert leads['total_matches'] >= 4 and leads['truncated'] and len(leads['items']) == 3
            assert sum(len(x.get('excerpt', '')) for x in leads['items']) <= 2400
            assert all('unrelated note' not in x['excerpt'] for x in leads['items'])
            parent_leads = packet['related_parent_account']['biographical_kinship_leads']
            quote = next(x for x in parent_leads['items'] if x.get('source_kind') == 'captured_biography')
            assert quote['pointer'] == '/profiles/Glasgow-2/biography_wikitext'
            assert 'Nancy McClelland was one of Robert’s children' in quote['excerpt']
            assert quote['line'] == 1 and quote['char_offset'] == 0 and quote['source_context']
            assert all(hashlib.sha256(p.read_bytes()).hexdigest() == digest for p, digest in before.items())

            # A living parent is independently withheld, even though the child account is eligible.
            context['rows']['Glasgow-2']['IsLiving'] = 1
            withheld = related_parent_account('Glasgow-1', 'Glasgow-2', root=root, context=context)
            assert withheld['withheld'] and 'biographical_kinship_leads' not in withheld
            assert 'Robert’s daughter' not in json.dumps(withheld)
            from tools.research_preflight import biography_kinship_leads
            helper_withheld = biography_kinship_leads('Glasgow-2', 'Glasgow-1', root=root, context=context)
            assert helper_withheld['withheld'] and not helper_withheld['items']

    def test_pending_biography_path_traversal_and_symlink_are_denied(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'data/wikitree').mkdir(parents=True)
            (root / 'research/Glasgow-1').mkdir(parents=True)
            outside = root / 'secret.wiki'
            outside.write_text('Nancy was a daughter of Robert SECRET.')
            (root / 'data/wikitree/profile-evidence.json').write_text(json.dumps({'profiles': {
                'Glasgow-1': {'profile_fields': {'Name': 'Nancy'}, 'biography_wikitext': 'Nancy was a child of Robert.'}}}))
            integration_path = root / 'research/queue-review-2026-10-17/catalogue-integration.json'
            integration_path.parent.mkdir(parents=True, exist_ok=True)
            integration_path.write_text(json.dumps({'profile_updates': {'Glasgow-1': {'draft_path': '../secret.wiki'}}}))
            context = {'rows': {'Glasgow-1': {'Privacy': 60, 'IsLiving': 0, 'Name': 'Nancy'},
                                'Glasgow-2': {'Privacy': 60, 'IsLiving': 0, 'Name': 'Robert'}},
                       'checked': {}, 'assessments': [], 'records': []}
            from tools.research_preflight import biography_kinship_leads
            result = biography_kinship_leads('Glasgow-1', 'Glasgow-2', root=root, context=context)
            assert 'SECRET' not in json.dumps(result)
            assert result['sources']['pending_draft'] == 'withheld'
            research_link = root / 'research/Glasgow-1/linked.wiki'
            research_link.symlink_to(outside)
            assert _safe_research_path(root, 'research/Glasgow-1/linked.wiki') is None
            assert _safe_research_path(root, 'research/Glasgow-1') is None

    def test_long_paragraph_window_centers_on_late_kinship_match_and_prioritizes_id(self):
        from tools.research_preflight import _kinship_excerpts
        text = 'An unrelated son. ' + 'unrelated padding ' * 200 + 'Nancy is the daughter of Glasgow-12.'
        found = _kinship_excerpts(text, account_id='Glasgow-1', counterpart_id='Glasgow-12',
                                  source_kind='captured_biography', source_path='capture.json',
                                  counterpart_names={'Robert'}, max_excerpts=3, max_chars=2400)
        item = found['items'][0]
        assert 'daughter of Glasgow-12' in item['excerpt']
        assert item['excerpt'].index('Nancy') < 800
        assert text[item['char_offset']:item['char_offset'] + len(item['excerpt'])] == item['excerpt']
        assert item['char_offset'] + item['excerpt'].index('Nancy') > 2400
        ranked = _kinship_excerpts('Robert is Nancy’s father.\n\nNancy’s father is Glasgow-12.',
                                   account_id='Glasgow-1', counterpart_id='Glasgow-12',
                                   source_kind='pending_draft', source_path='research/Glasgow-1/draft.wiki',
                                   counterpart_names={'Robert'}, max_excerpts=1, max_chars=100)
        assert ranked['items'][0]['match_kind'] == 'counterpart_id'
        assert 'Glasgow-12' in ranked['items'][0]['excerpt']


if __name__ == "__main__":
    unittest.main()
