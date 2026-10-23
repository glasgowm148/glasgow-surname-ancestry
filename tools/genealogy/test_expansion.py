#!/usr/bin/env python3
"""Focused checks for eligibility, privacy projection and refresh hooks."""
import ast
import json
from pathlib import Path
import re
import tempfile
import sys
from unittest.mock import patch
import open_profiles as profiles
sys.path.insert(0, str(profiles.ROOT))


def main():
    assert list(profiles.identity_tokens('born before-1701', set())) == []
    assert list(profiles.identity_tokens('Historic-1701', set())) == ['Historic-1701']
    linked = '[John-1](https://www.wikitree.com/wiki/Historic-1) and John-1'
    assert set(profiles.identity_tokens(linked, {'historic-1'})) == {'Historic-1'}
    assert 'John-1' in list(profiles.identity_tokens(linked, set()))
    assert 'John-1' in list(profiles.identity_tokens(linked + '\n\nJohn-1', {'historic-1'}))
    eligible = {'Privacy': 60, 'IsLiving': 0}
    assert profiles.eligibility(eligible) == 'explicit_nonliving'
    assert profiles.eligibility({**eligible, 'IsLiving': 1, 'DeathDate': '1750'}) == 'living'
    assert profiles.eligibility(eligible, {'Privacy': 50, 'IsLiving': 0}) == 'not_open'
    assert profiles.eligibility(eligible, {'Privacy': None}) == 'not_open'
    assert profiles.eligibility({'Privacy': 60, 'BirthDate': '2000'}) == 'living_status_unknown'
    assert profiles.eligibility({'Privacy': 60, 'BirthDate': '1750'}) == 'historical_birth'
    assert profiles.eligibility({'Privacy': 60, 'DeathDate': '2000'}) == 'recorded_death'
    assert profiles.eligibility({'Privacy': 50, 'DeathDate': '1750'}) == 'not_open'
    from tools.public_privacy import PublicPrivacy
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / 'data/exports/one-tree').mkdir(parents=True)
        (root / 'data/wikitree').mkdir(parents=True)
        (root / 'www/data').mkdir(parents=True)
        (root / 'www/people').mkdir(parents=True)
        runtime = root / 'runtime'
        runtime.mkdir()
        def write(relative, data):
            (root / relative).write_text(json.dumps(data))
        write('data/wikitree/live-profile-overrides.json', {'profiles': {}})
        write('data/wikitree/profile-evidence.json', {'profiles': {
            'Historic-1': {'privacy': 60, 'profile_fields': {**eligible, 'Name': 'Historic-1', 'FirstName': 'Historical', 'BirthDate': '1750'}},
            'Private-1': {'privacy': 40, 'profile_fields': {'Privacy': 40, 'Name': 'Private-1', 'DeathDate': '1800'}},
            'Living-1': {'privacy': 60, 'profile_fields': {'Privacy': 60, 'Name': 'Living-1', 'IsLiving': 1}},
        }})
        write('www/data/people-index.json', [
            {'id': 'Historic-1', 'json_url': '/people/historic-1.json'},
            {'id': 'record-janet-broun-dalziel-1716', 'json_url': '/people/record-janet-broun-dalziel-1716.json'}])
        write('www/people/historic-1.json', {'claims': [
            {'claim': 'Recorded in Edinburgh in 1770.', 'status': 'certain'},
            {'claim': 'DNA kit number SECRETKIT'},
            {'claim': 'Private-1 was related to Living-1.'}],
            'research_findings': [{'sections': [
                {'category': 'conclusion', 'markdown': 'Supported historical conclusion.'},
                {'category': 'sources', 'markdown': 'Licensed full record transcription.'},
                {'title': 'Current conclusion', 'category': 'other',
                 'markdown': 'Current 88% assessment, born before-1701. <!-- queue-identity-review-2026 --> [Draft](/people/record-janet-broun-dalziel-1716.html).'},
                {'title': 'Current conclusion — 17 October 2026', 'category': 'conclusion',
                 'markdown': 'Superseded historical assessment.'},
                {'title': 'Earlier Current conclusion', 'category': 'conclusion',
                 'markdown': 'Obsolete conclusion.'},
                {'title': 'Current conclusion', 'category': 'conclusion',
                 'markdown': 'Private-1 remains related.'},
                {'title': 'Current conclusion', 'category': 'conclusion',
                 'markdown': 'Unknown local [draft](/people/record-unknown-person-1750.html).'},
                {'title': 'Current conclusion', 'category': 'conclusion',
                 'markdown': 'DNA kit number ANOTHERSECRET'},
                {'title': 'Current conclusion', 'category': 'conclusion',
                 'markdown': 'The gravestone transcription supports the household.\n\nJohn-1022 remains an unresolved shorthand.\n\n> Copied source QUOTEBODY\n\nLicensed passage LICENSEDBODY\n\nPrivate-1 and Living-1.\n\nThe next safe analytical paragraph.',
                 'raw_transcription': 'RAWBODYSHOULDNEVERAPPEAR'}]}]})
        policy = PublicPrivacy()
        policy.tester_pattern = re.compile(r'(?!)')
        with patch('tools.public_privacy.from_sources', return_value=policy), patch.object(profiles, 'RUNTIME', runtime):
            out = root / 'stage'
            result = profiles.stage(out, root, runtime / 'no-status.json')
            text = (out / 'Historic-1.md').read_text()
            assert result['open_profiles'] == 1
            assert 'Supported historical conclusion' in text and '#/claims/0' in text
            assert 'Current 88% assessment, born before-1701.' in text
            assert 'queue-identity-review' not in text
            assert '#/research_findings/0/sections/2' in text
            assert all(word not in text for word in ('Superseded historical', 'Obsolete conclusion', 'Unknown local', 'ANOTHERSECRET'))
            assert 'The gravestone transcription supports the household.' in text
            assert 'The next safe analytical paragraph.' in text
            assert '#/research_findings/0/sections/8' in text
            assert 'Partial analytical summary; 4 paragraph(s) omitted' in text
            assert '"original_markdown_paragraphs": [1, 6]' in text
            assert all(word not in text for word in ('John-1022', 'QUOTEBODY', 'LICENSEDBODY', 'RAWBODYSHOULDNEVERAPPEAR'))
            assert all(word not in text for word in ('SECRETKIT', 'Private-1', 'Living-1', 'Licensed'))
            # Revoking eligibility removes stale searchable content.
            write('data/wikitree/profile-evidence.json', {'profiles': {}})
            assert profiles.stage(out, root, runtime / 'no-status.json')['open_profiles'] == 0
            assert not list(out.iterdir())
    # Ensure the targeted sync hook is confined to an approved successful write.
    tree = ast.parse((profiles.ROOT / 'tools/sync_catalogue_research.py').read_text())
    guarded = [node for node in ast.walk(tree) if isinstance(node, ast.If)
               and ast.unparse(node.test) == 'args.write and (not missing)']
    assert len(guarded) == 1 and 'refresh_after_batch()' in ast.unparse(guarded[0])
    release = ast.parse((profiles.ROOT / 'tools/publish_research_release.py').read_text())
    function = next(node for node in release.body if isinstance(node, ast.FunctionDef) and node.name == 'publish')
    source = ast.unparse(function)
    assert source.index('build_latest_findings.py') < source.index('refresh_after_batch')
    print('PASS: eligibility, living/restricted/DNA exclusion, JSON provenance, stale removal and approved-batch hook guards')


if __name__ == '__main__':
    main()
