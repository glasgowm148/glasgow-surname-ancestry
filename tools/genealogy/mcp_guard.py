#!/usr/bin/env python3
"""Small stdio policy boundary around pinned upstream MCPs; no tree writes."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import threading
import time

RUNTIME = Path.home() / 'Library/Application Support/genealogy-tools'
POLICY = json.loads((RUNTIME / 'mcp-policy.json').read_text())
KIND = sys.argv[1]
SPEC = POLICY[KIND]
ALLOWED = set(SPEC['tools'])
PROJECT = Path(__file__).resolve().parents[2]
COLLECTIONS = json.loads((PROJECT / 'tools/genealogy/collections.json').read_text())['collections']
pending = {}
lock = threading.Lock()
last_call = 0


def emit(message):
    with lock:
        print(json.dumps(message, ensure_ascii=False), flush=True)


def reject(request, reason):
    if 'id' in request:
        emit({'jsonrpc': '2.0', 'id': request['id'],
              'error': {'code': -32602, 'message': reason}})


def bounded(args, key, default, ceiling):
    args[key] = max(1, min(int(args.get(key, default)), ceiling))


def check_path(value, root, exact=False):
    path = Path(value).expanduser().resolve()
    approved = Path(root).resolve()
    if (exact and path != approved) or (not exact and path != approved and approved not in path.parents):
        raise ValueError('Only the reviewed working corpus is accessible')
    if not path.exists():
        raise ValueError('Reviewed corpus path does not exist')
    return str(path)


def validate(name, args):
    if name not in ALLOWED:
        raise ValueError('Tool unavailable under project read-only policy')
    if KIND == 'qmd':
        if name == 'query':
            searches = args.get('searches')
            if not searches:
                searches = [{'type': 'lex', 'query': args.pop('query', '')}]
            if not searches or any(s.get('type') != 'lex' for s in searches):
                raise ValueError('This index uses local keyword search only')
            args.pop('query', None)
            args['searches'] = searches[:3]
            args['rerank'] = False
            bounded(args, 'limit', 5, 5)
        elif name == 'get':
            bounded(args, 'maxLines', 60, 80)
    elif KIND == 'pdf':
        for key in ('path', 'paths'):
            if key in args:
                value = args[key]
                args[key] = [check_path(p, SPEC['root']) for p in value] if isinstance(value, list) else check_path(value, SPEC['root'])
        if name in ('pdf_search', 'pdf_corpus_search'):
            args['mode'] = 'keyword'
            bounded(args, 'top_k' if name == 'pdf_corpus_search' else 'max_results', 5, 5)
            bounded(args, 'context_chars', 180, 300)
            args['excerpt_style'] = 'snippet'
        if name == 'pdf_read_pages':
            pages = []
            for part in str(args.get('pages', '')).split(','):
                if re.fullmatch(r'\d+', part):
                    pages.append(int(part))
                elif re.fullmatch(r'\d+-\d+', part):
                    start, end = map(int, part.split('-'))
                    if end < start or end - start > 1:
                        raise ValueError('Read at most two PDF pages per call')
                    pages.extend(range(start, end + 1))
                else:
                    raise ValueError('Specify one or two PDF pages')
            if len(set(pages)) > 2 or not pages or min(pages) < 1:
                raise ValueError('Read at most two PDF pages per call')
    elif KIND == 'gedcom':
        if name == 'load_gedcom':
            args['file_path'] = check_path(args.get('file_path', ''), SPEC['file'], exact=True)
        for key in ('max_results', 'page_size', 'max_paths', 'generations'):
            if key in args:
                bounded(args, key, 5, 5)
    elif KIND == 'research_sources':
        # The only exposed provider is verified Open Archives, with a historical range.
        year = str(args.get('death_year', ''))
        if not re.fullmatch(r'1\d{3}', year) or int(year) > 1900:
            raise ValueError('A historical upper year <=1900 is required')
        bounded(args, 'limit', 5, 5)
    return args


env = {'HOME': SPEC.get('home', str(RUNTIME / 'isolated-home')),
       'PATH': '/opt/homebrew/bin:/usr/bin:/bin', 'LANG': 'en_GB.UTF-8',
       'HF_HUB_OFFLINE': '1', 'HF_HUB_DISABLE_TELEMETRY': '1',
       'DO_NOT_TRACK': '1', 'FASTMCP_CHECK_FOR_UPDATES': 'off'}
env.update(SPEC.get('env', {}))
child = subprocess.Popen(SPEC['command'], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                         stderr=sys.stderr, text=True, env=env, cwd=SPEC['cwd'], bufsize=1)


def output():
    for line in child.stdout:
        try:
            response = json.loads(line)
        except (ValueError, TypeError):
            # Never corrupt stdio with an upstream log line.
            continue
        method, tool_name = pending.pop(response.get('id'), ('', ''))
        result = response.get('result', {})
        if method == 'initialize':
            result['capabilities'] = {'tools': {'listChanged': False}}
            result['instructions'] = 'Read-only reviewed public genealogy corpus. Use bounded excerpts; verify original records.'
        elif method == 'tools/list':
            result['tools'] = [t for t in result.get('tools', []) if t['name'] in ALLOWED]
            for t in result['tools']:
                t['description'] = t.get('description', '')[:1000]
                t['annotations'] = {'readOnlyHint': True, 'destructiveHint': False,
                                    'openWorldHint': KIND == 'research_sources'}
                if KIND == 'qmd' and t['name'] == 'query':
                    t['description'] = 'Search public non-living profile summaries and reviewed case notes with local BM25. Use searches=[{type:"lex",query:"terms"}], rerank=false. At most five results. Results carry original source paths and JSON pointers or verbatim-note line mapping.'
                if KIND == 'research_sources':
                    t['description'] = 'Search public Open Archives historical records. birth_year/death_year are lower/upper RECORD EVENT years, not lifespan filters. Upper year <=1900 is required. At most five results; one call per second.'
        elif method == 'tools/call' and 'result' in response:
            if KIND in ('qmd', 'pdf'):
                original_result = json.dumps(result, ensure_ascii=False)
                provenance = []
                for entry in COLLECTIONS:
                    if entry['staged_name'] in original_result:
                        line_note = '; original line = staged line minus 6' if entry['kind'] == 'note' else '; PDF page numbers match the original exactly'
                        provenance.append(str(PROJECT / entry['source']) + line_note)
                if KIND == 'qmd':
                    source_map = RUNTIME / 'open-profile-sources.json'
                    if source_map.is_file():
                        mapping = json.loads(source_map.read_text())
                        # Generated summaries carry per-excerpt JSON pointers,
                        # not the six-line offset used by verbatim case notes.
                        for filename in set(re.findall(r'open-profiles/([^\s"<>]+\.md)', original_result)):
                            for source in mapping.get(filename, {}).get('sources', []):
                                provenance.append(str(PROJECT / source) + '; generated summary: use the embedded source JSON pointer, never a line offset')
                if provenance:
                    result.setdefault('content', []).insert(0, {'type': 'text', 'text': 'Original sources:\n' + '\n'.join(dict.fromkeys(provenance))})
            cap = SPEC.get('response_bytes', 14000)
            if len(json.dumps(result, ensure_ascii=False).encode()) > cap:
                texts = '\n'.join(c.get('text', '') if c.get('type') == 'text' else c.get('resource', {}).get('text', '')
                                  for c in result.get('content', []) if c.get('type') in ('text', 'resource'))
                excerpt = texts.encode()[:cap - 1500].decode('utf-8', errors='ignore')
                response['result'] = {'content': [{'type': 'text', 'text': excerpt + '\n[Response truncated. Narrow the query or read a smaller original excerpt.]'}],
                                      'isError': result.get('isError', False)}
        emit(response)
    # Close the protocol if startup fails or the upstream exits; never hang
    # an MCP client behind a dead process.
    os._exit(child.wait() or 0)


threading.Thread(target=output, daemon=True).start()
try:
    for line in sys.stdin:
        request = {}
        try:
            request = json.loads(line)
            method = request.get('method', '')
            if method not in ('initialize', 'notifications/initialized', 'notifications/cancelled', 'ping', 'tools/list', 'tools/call'):
                reject(request, 'Only tool queries are exposed by this server')
                continue
            name = ''
            if method == 'tools/call':
                name = request['params']['name']
                request['params']['arguments'] = validate(name, request['params'].get('arguments', {}))
                if KIND == 'research_sources':
                    time.sleep(max(0, 1.0 - (time.monotonic() - last_call)))
                    last_call = time.monotonic()
            if 'id' in request:
                pending[request['id']] = (method, name)
            child.stdin.write(json.dumps(request) + '\n')
            child.stdin.flush()
        except (KeyError, ValueError, TypeError) as exc:
            reject(request, str(exc))
finally:
    child.terminate()
    try:
        child.wait(timeout=5)
    except subprocess.TimeoutExpired:
        child.kill()
