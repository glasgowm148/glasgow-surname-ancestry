#!/usr/bin/env python3
"""Exercise stdio servers and enforced corpus/read-only boundaries locally."""
import asyncio
import hashlib
import json
from pathlib import Path
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[2]
RUNTIME = Path.home() / 'Library/Application Support/genealogy-tools'
POLICY = json.loads((RUNTIME / 'mcp-policy.json').read_text())
REPORT = {}


def parsed(result):
    text = '\n'.join(c.text if c.type == 'text' else c.resource.text
                     for c in result.content if c.type in ('text', 'resource'))
    try:
        return json.loads(text)
    except ValueError:
        return text


async def main():
    for kind, spec in POLICY.items():
        params = StdioServerParameters(command='/opt/homebrew/bin/python3',
                                       args=[str(ROOT / 'tools/genealogy/mcp_guard.py'), kind])
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                init = await session.initialize()
                listed = await session.list_tools()
                names = {t.name for t in listed.tools}
                assert names == set(spec['tools']), (kind, names)
                assert not init.capabilities.resources and not init.capabilities.prompts
                REPORT[kind] = {'server': init.serverInfo.model_dump(), 'tools': sorted(names)}
                try:
                    await session.call_tool('save_gedcom', {'file_path': '/tmp/forbidden.ged'})
                    raise AssertionError('Unlisted tool unexpectedly accepted')
                except Exception as error:
                    assert 'unavailable' in str(error), str(error)
                REPORT[kind]['unlisted_write_rejected'] = True
                if kind == 'qmd':
                    hit = parsed(await session.call_tool('query', {'searches': [{'type': 'lex', 'query': 'Currituck William Glasgow-428'}], 'rerank': False, 'limit': 2}))
                    assert 'Glasgow-428' in json.dumps(hit)
                    REPORT[kind]['historical_query'] = 'Currituck William Glasgow-428 -> relevant profile/case, original source mapping retained'
                    expanded = parsed(await session.call_tool('query', {'searches': [{'type': 'lex', 'query': 'Glasgow-1150'}], 'limit': 1}))
                    assert 'open-profiles/Glasgow-1150.md' in json.dumps(expanded)
                    generated = parsed(await session.call_tool('get', {'file': 'qmd://historical-notes/open-profiles/Glasgow-1150.md', 'fromLine': 1, 'maxLines': 25}))
                    assert '#/profiles/Glasgow-1150' in str(generated)
                    assert 'generated summary' in str(generated) and 'staged line minus 6' not in str(generated)
                    REPORT[kind]['expanded_profile_query'] = 'Glasgow-1150 -> generated public summary with original JSON pointers; no false line offset'
                    doc = await session.call_tool('get', {'file': 'qmd://historical-notes/Glasgow-428-findings.md', 'fromLine': 7, 'maxLines': 12})
                    assert 'Currituck' in json.dumps(parsed(doc))
                    try:
                        await session.call_tool('query', {'searches': [{'type': 'vec', 'query': 'private'}]})
                        raise AssertionError('Unexpected semantic search')
                    except Exception as error:
                        assert 'keyword' in str(error)
                elif kind == 'pdf':
                    path = str(next((RUNTIME / 'corpus/pdf').glob('grant*.pdf')))
                    info = parsed(await session.call_tool('pdf_info', {'path': path}))
                    REPORT[kind]['pdf_info'] = info
                    hit = parsed(await session.call_tool('pdf_corpus_search', {'paths': str(RUNTIME / 'corpus/pdf'), 'query': 'Glasgow', 'mode': 'keyword', 'top_k': 2}))
                    assert 'page' in json.dumps(hit) and 'Glasgow' in json.dumps(hit)
                    REPORT[kind]['historical_search'] = hit
                    try:
                        await session.call_tool('pdf_info', {'path': str(ROOT / '.cache/private.pdf')})
                        raise AssertionError('Unexpected private path')
                    except Exception as error:
                        assert 'reviewed' in str(error)
                    REPORT[kind]['private_path_rejected'] = True
                elif kind == 'gedcom':
                    result = parsed(await session.call_tool('load_gedcom', {'file_path': spec['file']}))
                    assert '57' in json.dumps(result), result
                    text = Path(spec['file']).read_text()
                    import re
                    block = next(b for b in re.split(r'(?m)(?=^0 )', text) if b.splitlines() and ' INDI' in b.splitlines()[0] and '1 FAMS ' in b)
                    person_id = block.splitlines()[0].split()[1]
                    relation = parsed(await session.call_tool('get_relationships', {'person_id': person_id}))
                    assert any(k in json.dumps(relation) for k in ('children', 'spouse', 'parents'))
                    REPORT[kind]['historical_relationship_query'] = relation
                    try:
                        await session.call_tool('load_gedcom', {'file_path': str(ROOT / 'archive/dump/GEDs/private.ged')})
                        raise AssertionError('Unexpected unrestricted load')
                    except Exception as error:
                        assert 'reviewed' in str(error)
                    REPORT[kind]['original_load_rejected'] = True
                elif kind == 'research_sources':
                    result = parsed(await session.call_tool('search_open_archives', {'name': 'Coret', 'birth_year': '1700', 'death_year': '1850', 'limit': 1}))
                    assert not result.get('error'), result
                    REPORT[kind]['historical_provider_query'] = result
                    try:
                        await session.call_tool('search_open_archives', {'name': 'private', 'death_year': '2020'})
                        raise AssertionError('Unexpected modern subject')
                    except Exception as error:
                        assert 'historical' in str(error)
    changed = []
    for item in json.loads((RUNTIME / 'tree-baseline.json').read_text()):
        if hashlib.sha256(Path(item['path']).read_bytes()).hexdigest() != item['sha256']:
            changed.append(item['kind'])
    assert not changed, changed
    REPORT['original_trees_unchanged'] = True
    for path, digest in json.loads((RUNTIME / 'existing-config-baseline.json').read_text()).items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest
    REPORT['user_config_auth_unchanged'] = True
    (RUNTIME / 'verification.json').write_text(json.dumps(REPORT, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'verified_servers': list(POLICY), 'original_trees_unchanged': True,
                      'report': str(RUNTIME / 'verification.json')}))


if __name__ == '__main__':
    asyncio.run(main())
