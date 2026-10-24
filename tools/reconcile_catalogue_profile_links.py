#!/usr/bin/env python3
"""Project explicitly reviewed record-person links locally; dry run by default.

No identity inference or genealogy adoption. All selected subjects are preflighted
before writes. Original documentary accounts survive in superseded aliases.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import csv
from collections import Counter
from html import escape
import io
import json
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[1]
GENEALOGY = {'parents', 'father', 'mother', 'spouses', 'partners', 'children', 'siblings', 'childrenRecorded'}
IDENTITIES = {'id', 'catalogue_id', 'selection_id', 'slug', 'catalogueId'}
ROLE_REFS = {'person', 'p', 'subject', 'catalogue_id', 'catalogueId'}
LIST_REFS = {'members', 'subjects', 'subject_ids'}


def provider_keys(value):
    """Only structured source URLs constitute provider-record identity proof."""
    result = set()
    if isinstance(value, dict):
        for key, item in value.items():
            if key in {'url', 'source_url'} and isinstance(item, str):
                url = urlsplit(item)
                record = parse_qs(url.query).get('id', [])
                if url.hostname and 'findmypast.' in url.hostname:
                    if record:
                        result.add(('findmypast', record[0]))
            elif key not in {'imported', 'history', 'superseded_documentary_account'}:
                result.update(provider_keys(item))
    elif isinstance(value, list):
        for item in value:
            result.update(provider_keys(item))
    return result


def record_identity(record):
    """Stable documentary identity; retirement metadata cannot create an event."""
    providers = provider_keys(record)
    if providers:
        return ('provider', tuple(sorted(providers)), record.get('association', ''), str(record.get('year', record.get('date', ''))))
    if record.get('record_id') or record.get('id'):
        return ('record', record.get('record_id') or record['id'])
    return ('source', record.get('source_url'), record.get('source_title'), record.get('association'), str(record.get('year', record.get('date', ''))))


def retire_creation_status(value, profile, reviewed):
    if isinstance(value, dict) and isinstance(value.get('source_status'), str):
        value['source_status'] = value['source_status'].replace(
            'scoped integration new_person READY',
            f'scoped integration existing_profile; reconciled {profile} {reviewed}')
    return value


def exact_subject(row, old):
    return isinstance(row, dict) and (any(row.get(key) == old for key in IDENTITIES) or
        row.get('catalogueUrl') in {f'/people/{old}.html', f'https://glasgow.phenotype.dev/people/{old}.html'})


def genealogy_references(value, old):
    """Check identifiers inside explicit genealogy fields, never narrative names."""
    if isinstance(value, str):
        return value == old
    if isinstance(value, list):
        return any(genealogy_references(v, old) for v in value)
    if isinstance(value, dict):
        return any(value.get(k) == old for k in IDENTITIES | {'profile_id', 'target'}) or any(
            genealogy_references(v, old) for k, v in value.items() if k in GENEALOGY)
    return False


def check_edges(value, old, owned=False):
    if isinstance(value, dict):
        owned = owned or exact_subject(value, old)
        for key, item in value.items():
            if key in {'imported', 'history', 'superseded_documentary_account'}:
                continue
            if key in GENEALOGY and (genealogy_references(item, old) or (owned and item)):
                raise ValueError(f'{old}: unexplained genealogical edges in {key}; review required')
            if key in {'relationships', 'edges'} and isinstance(item, list):
                for edge in item:
                    if isinstance(edge, dict) and any(edge.get(k) == old for k in ('source', 'target', 'from', 'to')):
                        if edge.get('type', edge.get('kind', '')) not in {'record', 'documentary', 'source_association'}:
                            raise ValueError(f'{old}: unexplained genealogical edge; review required')
            check_edges(item, old, owned)
    elif isinstance(value, list):
        for item in value:
            check_edges(item, old, owned)


def rewire_documentary(value, old, slug, profile, *, participant=False, reviewed=''):
    """Exact role references only. Narrative claims and imported history stay verbatim."""
    if isinstance(value, list):
        return [rewire_documentary(v, old, slug, profile, participant=participant, reviewed=reviewed) for v in value]
    if not isinstance(value, dict):
        return value
    result = deepcopy(value)
    for key, item in result.items():
        if key in {'imported', 'history', 'superseded_documentary_account'}:
            continue
        if key in ROLE_REFS and item == old:
            result[key] = slug
        elif key == 'id' and participant and item == old:
            result[key] = slug
        elif key in LIST_REFS and isinstance(item, list):
            result[key] = list(dict.fromkeys(slug if x == old else x for x in item))
        elif key in {'url', 'html_url', 'catalogue_url'} and isinstance(item, str):
            parsed = urlsplit(item)
            if parsed.path == f'/people/{old}.html' and (not parsed.netloc or parsed.netloc == 'glasgow.phenotype.dev'):
                result[key] = parsed._replace(path=f'/people/{slug}.html').geturl()
        elif key == 'claims' and isinstance(item, list):
            result[key] = [rewire_documentary(c, old, slug, profile, reviewed=reviewed) if c.get('type') == 'recorded_occurrence' else c for c in item]
        elif isinstance(item, (dict, list)):
            result[key] = rewire_documentary(item, old, slug, profile, participant=key == 'participants', reviewed=reviewed)
    if value.get('catalogue_id') == old and 'profile_ids' in result:
        result['profile_ids'] = [profile] if isinstance(result['profile_ids'], list) else profile
    if reviewed and (any(value.get(key) == old for key in ROLE_REFS) or value.get('supplement_id') == old.removeprefix('record-')):
        retire_creation_status(result, profile, reviewed)
    if isinstance(value.get('members'), list) and value['members'] != result.get('members') and 'count' in value:
        result['count'] = len(result['members'])
    return result


def plan(root: Path, catalogue_ids: list[str]) -> dict[str, bytes]:
    root = Path(root)
    web = root / 'www'
    if not catalogue_ids or len(set(catalogue_ids)) != len(catalogue_ids) or any(not x.startswith('record-') or '/' in x or '..' in x for x in catalogue_ids):
        raise ValueError('Select unique explicit record-* catalogue IDs')
    links = json.loads((root / 'data/wikitree/catalogue-profile-links.json').read_text())['entries']
    people = json.loads((web / 'data/people.json').read_text())
    atlas_path = web / 'assets/research/atlas-model.json'
    atlas = json.loads(atlas_path.read_text()) if atlas_path.exists() else None
    selected = []
    for old in catalogue_ids:
        link = links.get(old) or {}
        profile = link.get('profile_id', '')
        if not profile or not link.get('matched_at') or not link.get('evidence_note'):
            raise ValueError(f'{old}: reviewed profile link, date and evidence note required')
        slug = profile.lower()
        target_path = web / f'people/{slug}.json'
        if not target_path.is_file() or not (web / f'people/{slug}.html').is_file():
            raise ValueError(f'{old}: existing public canonical target required')
        target = json.loads(target_path.read_text())
        if target.get('id') != profile or target.get('status') == 'superseded':
            raise ValueError(f'{old}: invalid canonical target identity')
        previous = json.loads((web / f'people/{old}.json').read_text())
        if previous.get('status') == 'superseded':
            if previous.get('id') != profile:
                raise ValueError(f'{old}: existing alias has conflicting target')
        elif not provider_keys(previous) & provider_keys(target):
            raise ValueError(f'{old}: missing shared provider-record proof')
        for collection in [people, previous if previous.get('status') != 'superseded' else {}, atlas]:
            check_edges(collection, old)
        if not any(p.get('catalogue_id') == slug for p in people['people']):
            raise ValueError(f'{old}: canonical public person row missing')
        selected.append((old, profile, slug, link, previous))

    changes = {}
    def put(path, value):
        path = Path(path)
        if not isinstance(value, bytes) and path.exists():
            latest = changes.get(str(path.relative_to(root)), path.read_bytes())
            if json.loads(latest) == value:
                return  # Keep byte formatting and untouched unrelated shards.
        raw = value if isinstance(value, bytes) else (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode()
        if not path.exists() or path.read_bytes() != raw:
            changes[str(path.relative_to(root))] = raw
    def read(path):
        return json.loads(changes.get(str(path.relative_to(root)), path.read_bytes()))

    for old, profile, slug, link, previous in selected:
        current = next(p for p in people['people'] if p.get('catalogue_id') == slug)
        old_rows = [p for p in people['people'] if exact_subject(p, old)]
        existing = {record_identity(r) for r in current.get('records', [])}
        for old_row in old_rows:
            for record in old_row.get('records', []):
                record = retire_creation_status(rewire_documentary(record, old, slug, profile), profile, link['matched_at'])
                record['profile_id'] = profile
                record.setdefault('retired_catalogue_id', old)
                key = record_identity(record)
                if key not in existing:
                    current.setdefault('records', []).append(record)
                    existing.add(key)
        people['people'] = [p for p in people['people'] if not exact_subject(p, old)]
        people['count'] = len(people['people'])

        # Filter person-only registries; documentary records use the separate role projection.
        registry_paths = ['data/people-index.json', 'data/catalogue-search-index.json',
                          'assets/research/registry.json', 'assets/research/search-people.json',
                          'assets/research/search-index.json', 'assets/unified/search-people.json']
        registry_paths += [str(p.relative_to(web)) for p in (web / 'data/resolve').glob('*.json')]
        registry_paths += [str(p.relative_to(web)) for p in (web / 'data/chunks').glob('people-*.json')]
        for relative in registry_paths:
            path = web / relative
            if not path.exists():
                continue
            # Most resolver shards do not mention this exact documentary ID.
            # Avoid parsing or normalising unrelated generated snapshots.
            raw = changes.get(str(path.relative_to(root)), path.read_bytes())
            if old.encode() not in raw:
                continue
            data = read(path)
            if isinstance(data, list):
                filtered = [r for r in data if not exact_subject(r, old)]
                data = [rewire_documentary(r, old, slug, profile) if isinstance(r, dict) and r.get('kind') == 'record' else r for r in filtered]
            elif isinstance(data, dict):
                for key in ('candidates', 'people', 'rows', 'items'):
                    if isinstance(data.get(key), list):
                        before_count = len(data[key])
                        data[key] = [r for r in data[key] if not exact_subject(r, old)]
                        if key == 'candidates' and len(data[key]) != before_count:
                            data['candidate_count'] = len(data[key])
                        if key == 'items' and len(data[key]) != before_count and 'count' in data:
                            data['count'] = len(data[key])
            put(path, data)
        compare_path = web / 'data/compare-index.js'
        if compare_path.exists():
            prefix = 'window.glasgowCompareIndex='
            original = changes.get(str(compare_path.relative_to(root)), compare_path.read_bytes()).decode()
            if not original.startswith(prefix):
                raise ValueError('Unsupported compare index schema')
            rows, end = json.JSONDecoder().raw_decode(original[len(prefix):])
            tail = original[len(prefix) + end:]
            filtered = [row for row in rows if not exact_subject(row, old)]
            dossier_prefix = 'window.glasgowCompareDossiers='
            changed = len(filtered) != len(rows)
            if dossier_prefix in tail:
                start = tail.index(dossier_prefix) + len(dossier_prefix)
                dossiers, end = json.JSONDecoder().raw_decode(tail[start:])
                if old in dossiers:
                    del dossiers[old]
                    tail = tail[:start] + json.dumps(dossiers, ensure_ascii=False, separators=(',', ':')) + tail[start + end:]
                    changed = True
            if changed:
                put(compare_path, (prefix + json.dumps(filtered, ensure_ascii=False, separators=(',', ':')) + tail).encode())

        # Browser registries have explicit column schemas. Preserve unmatched
        # compact rows verbatim; do not interpret their search prose as identity.
        for relative, columns in (
            ('assets/v3/registry-packed.json', None),
            ('assets/v3/search-people.json', ('id', 'name', 'url', 'meta', 'search')),
            ('assets/v3/people-quick.json', ('id', 'name', 'life', 'place', 'slug')),
        ):
            path = web / relative
            if not path.exists():
                continue
            data = read(path)
            fields = data['fields'] if columns is None else columns
            packed_rows = data['rows'] if columns is None else data
            filtered = []
            for raw in packed_rows:
                if not isinstance(raw, list):
                    raise ValueError(f'Unsupported browser registry schema: {relative}')
                row = dict(zip(fields, raw))
                if exact_subject(row, old):
                    continue
                if row.get('kind') == 'record':
                    row = rewire_documentary(row, old, slug, profile)
                    raw = [row.get(key) for key in fields[:len(raw)]] + raw[len(fields):]
                filtered.append(raw)
            if columns is None:
                data['rows'] = filtered
            else:
                data = filtered
            put(path, data)

        record_paths = ['data/records-index.json', 'assets/research/record-index.json', 'assets/v3/source-index.json']
        record_paths.append('assets/unified/search-records.json')
        record_paths += [str(p.relative_to(web)) for p in (web / 'data/chunks').glob('records-*.json')]
        record_paths += [str(p.relative_to(web)) for p in (web / 'data/chunks').glob('families-*.json')]
        source_index = web / 'assets/v3/source-index.json'
        if source_index.exists():
            for item in read(source_index):
                if old in item.get('members', []):
                    record_paths.append(f'assets/v3/sources/{item["id"]}.json')
                    # Existing source readers retain their prose and shell;
                    # only explicit links to the retired account change.
                    source_page = web / f'sources/{item["id"]}/index.html'
                    if source_page.exists():
                        from bs4 import BeautifulSoup
                        source_soup = BeautifulSoup(changes.get(str(source_page.relative_to(root)), source_page.read_bytes()), 'html.parser')
                        changed = False
                        for tag in source_soup.select('[href]'):
                            if tag['href'] in {f'/people/{old}.html', f'https://glasgow.phenotype.dev/people/{old}.html'}:
                                tag['href'] = tag['href'].replace(f'/people/{old}.html', f'/people/{slug}.html')
                                changed = True
                        if changed:
                            put(source_page, str(source_soup).encode())
        for relative in record_paths:
            path = web / relative
            if path.exists():
                put(path, rewire_documentary(read(path), old, slug, profile, reviewed=link['matched_at']))

        # Legacy repair wrappers feed later search/route generators. Supersede
        # their imported vitals rather than migrating those estimates as facts.
        wrapper_path = web / f'assets/research/people/{old}.json'
        wrapper = read(wrapper_path) if wrapper_path.exists() else {}
        if wrapper and wrapper.get('status') != 'superseded':
            check_edges(wrapper, old)
            put(wrapper_path, {
                'schema_version': wrapper.get('schema_version', '3.0'),
                'id': profile, 'catalogue_id': slug, 'name': current['name'],
                'status': 'superseded', 'superseded_catalogue_id': old,
                'url': f'/people/{slug}.html', 'source_json': f'/people/{slug}.json',
                'redirect_to': f'/assets/research/people/{slug}.json',
                'reason': link['evidence_note'], 'superseded_documentary_account': wrapper,
            })
        original_wrapper = wrapper.get('superseded_documentary_account', wrapper)
        record_ids = list(original_wrapper.get('record_ids', []))
        # A retired wrapper may have lost its record_ids while the compact
        # index still owns a direct record reader. Include canonical rows too
        # so a resumed repair finds readers after the index was rewired.
        compact_records = web / 'assets/research/record-index.json'
        if compact_records.exists():
            record_ids.extend(row['id'] for row in read(compact_records)
                              if row.get('p') in {old, slug} and row.get('id'))
        seen_record_ids = set()
        for record_id in record_ids:
            if not isinstance(record_id, str) or '/' in record_id or '..' in record_id:
                raise ValueError(f'{old}: unsafe legacy record wrapper ID')
            if record_id in seen_record_ids:
                continue
            seen_record_ids.add(record_id)
            path = web / f'assets/research/records/{record_id}.json'
            if path.exists():
                put(path, rewire_documentary(read(path), old, slug, profile, reviewed=link['matched_at']))

        def project_events(events):
            result = []
            def event_key(event):
                return (event.get('p', event.get('person')), event.get('id'), event.get('source_url'), event.get('role'))
            canonical_keys = {event_key(event) for event in events if event.get('p') == slug or event.get('person') == slug}
            converted_keys = set()
            for event in events:
                if event.get('p') == old or event.get('person') == old:
                    if event.get('basis') == 'imported_vital':
                        continue  # Retained in superseded wrapper history only.
                    if event.get('basis') != 'source_association':
                        raise ValueError(f'{old}: unexplained non-documentary legacy event')
                    event = rewire_documentary(event, old, slug, profile)
                    key = event_key(event)
                    if key in canonical_keys or key in converted_keys:
                        continue
                    converted_keys.add(key)
                result.append(event)
            return result

        def documentary_event_key(event):
            providers = provider_keys(event)
            source = tuple(sorted(providers)) if providers else event.get('source_url') or event.get('id')
            return (source, event.get('kind'), event.get('role'), event.get('date', event.get('year')))

        target_wrapper_path = web / f'assets/research/people/{slug}.json'
        if original_wrapper and target_wrapper_path.exists():
            target_wrapper = read(target_wrapper_path)
            for field in ('events', 'mentions', 'family_events', 'research_events', 'unresolved_events'):
                rows = [event for event in original_wrapper.get(field, []) if event.get('basis') == 'source_association']
                for event in project_events(rows):
                    destination = 'mentions' if event.get('kind') == 'mention' else field
                    existing_keys = {documentary_event_key(retained) for retained in target_wrapper.get(destination, [])}
                    if documentary_event_key(event) not in existing_keys:
                        target_wrapper.setdefault(destination, []).append(event)
            put(target_wrapper_path, target_wrapper)
        event_index = web / 'assets/research/event-index.json'
        if event_index.exists():
            put(event_index, project_events(read(event_index)))
        old_events = web / f'assets/v3/events/{old}.json'
        if old_events.exists():
            documentary = project_events(read(old_events))
            put(old_events, documentary)
            target_events = web / f'assets/v3/events/{slug}.json'
            if target_events.exists():
                retained = read(target_events)
                existing_keys = {documentary_event_key(event) for event in retained}
                additions = [event for event in documentary if documentary_event_key(event) not in existing_keys]
                if additions:
                    put(target_events, retained + additions)
            elif documentary:
                put(target_events, documentary)

        branches_path = web / 'assets/research/branches.json'
        if branches_path.exists():
            branches = read(branches_path)
            for branch in branches:
                if old in branch.get('members', []) and branch.get('kind') == 'family':
                    raise ValueError(f'{old}: unexplained genealogical branch membership')
            put(branches_path, rewire_documentary(branches, old, slug, profile))
        search_path = web / 'assets/research/search-index.json'
        if search_path.exists():
            search_rows = read(search_path)
            for row in search_rows:
                if row.get('kind') == 'record' and isinstance(row.get('search'), str):
                    # Generated token text only; historical assertions are untouched.
                    row['search'] = ' '.join(slug if word == old else word for word in row['search'].split())
            put(search_path, search_rows)

        relationship_path = web / 'assets/v3/relationships.json'
        if relationship_path.exists():
            graph = read(relationship_path)
            for edge in graph.get('edges', []):
                if edge.get('a') == old or edge.get('b') == old:
                    raise ValueError(f'{old}: unexplained legacy relationship edge')
            graph.get('nodes', {}).pop(old, None)
            put(relationship_path, graph)
        routing_path = web / 'assets/v3/relationship-routing.json'
        if routing_path.exists():
            routing = read(routing_path)
            nodes = routing['nodes']
            removed = {i for i, node in enumerate(nodes) if old in node[:2]}
            for edge in routing['edges']:
                if edge[1] in removed or edge[2] in removed:
                    raise ValueError(f'{old}: unexplained legacy routing edge')
            if removed:
                index_map = {before: after for after, before in enumerate(i for i in range(len(nodes)) if i not in removed)}
                routing['nodes'] = [node for i, node in enumerate(nodes) if i not in removed]
                for edge in routing['edges']:
                    edge[1], edge[2] = index_map[edge[1]], index_map[edge[2]]
                put(routing_path, routing)
        routes_path = web / 'assets/unified/routes.js'
        if routes_path.exists():
            prefix = 'window.GlasgowRoutes='
            original = changes.get(str(routes_path.relative_to(root)), routes_path.read_bytes()).decode()
            if not original.startswith(prefix):
                raise ValueError('Unsupported unified route schema')
            routes, end = json.JSONDecoder().raw_decode(original[len(prefix):])
            if routes.get(old) == old:
                routes[old] = slug
                put(routes_path, (prefix + json.dumps(routes, ensure_ascii=False, separators=(',', ':')) + original[len(prefix) + end:]).encode())
            elif old in routes and routes[old] != slug:
                raise ValueError(f'{old}: conflicting existing unified route target')
        collection_path = web / 'assets/sources/collection-index.json'
        if collection_path.exists():
            collections = read(collection_path)
            if not isinstance(collections, list):
                raise ValueError('Unsupported source collection index schema')
            for collection in collections:
                collection['members'] = list(dict.fromkeys(
                    slug if member == old else member for member in collection.get('members', [])))
                # This explicitly named list is source participant context,
                # not a genealogical person registry or historical claim.
                if 'people' in collection:
                    collection['people'] = rewire_documentary(
                        collection['people'], old, slug, profile, participant=True)
            put(collection_path, collections)
        for relative in ('map/data/records.csv', 'data/records.csv', 'data/people.csv', 'data/source-gaps.csv', 'data/source-review.csv'):
            path = web / relative
            if not path.exists():
                continue
            text = changes.get(str(path.relative_to(root)), path.read_bytes()).decode('utf-8-sig')
            reader = csv.DictReader(io.StringIO(text)); fields = reader.fieldnames
            rows = []
            for row in reader:
                if relative.endswith('people.csv') and exact_subject(row, old):
                    continue
                if row.get('supplement_id') == old.removeprefix('record-'):
                    if row.get('profile_id') not in ('', profile, None):
                        raise ValueError(f'{old}: conflicting record profile_id')
                    row['profile_id'] = profile
                    retire_creation_status(row, profile, link['matched_at'])
                row = rewire_documentary(row, old, slug, profile, reviewed=link['matched_at'])
                rows.append(row)
            out = io.StringIO(newline=''); writer = csv.DictWriter(out, fieldnames=fields, lineterminator='\r\n')
            writer.writeheader();writer.writerows(rows)
            bom = b'\xef\xbb\xbf' if path.read_bytes().startswith(b'\xef\xbb\xbf') else b''
            put(path, bom + out.getvalue().encode())

        if atlas is not None:
            atlas['people'] = [p for p in atlas['people'] if not exact_subject(p, old)]
            atlas = rewire_documentary(atlas, old, slug, profile)
        if previous.get('status') == 'superseded':
            continue  # Existing public aliases and their history are authoritative.
        alias = dict(schema_version='1.0', id=profile, catalogue_id=slug, name=current['name'],
                     status='superseded', superseded_catalogue_id=old, reason=link['evidence_note'],
                     canonical_url=f'/people/{slug}.html', json_url=f'/people/{slug}.json',
                     network_url=f'/people/{slug}.network.json', wikitree_url=f'https://www.wikitree.com/wiki/{profile}',
                     redirect_to=f'/people/{slug}.json')
        # Preserve former estimates/claims/history outside the active identity schema.
        history = previous.get('superseded_documentary_account') if previous.get('status') == 'superseded' else deepcopy(previous)
        if history:
            alias['superseded_documentary_account'] = history
        put(web / f'people/{old}.json', alias)
        put(web / f'people/{old}.network.json', dict(schema_version='1.0', status='superseded',
             redirect_to=f'/people/{slug}.network.json', person={'id': profile, 'name': current['name']}, relationships=[]))
        from bs4 import BeautifulSoup
        page = web / f'people/{old}.html'
        soup = BeautifulSoup(page.read_text(), 'html.parser')
        main = soup.find('main')
        if main is None:
            raise ValueError(f'{old}: existing reader shell has no main')
        main.clear()
        main.append(BeautifulSoup(f'<article><h1>{escape(current["name"])}</h1><p>This record is already represented by {escape(profile)}.</p><p><a href="/people/{slug}.html">Read the canonical biography, sources and identity questions</a></p></article>', 'html.parser'))
        for tag in soup.select('link[rel="canonical"]'):
            tag['href'] = f'https://glasgow.phenotype.dev/people/{slug}.html'
        put(page, str(soup).encode())
    put(web / 'data/people.json', people)
    coverage_path = web / 'assets/research/coverage.json'
    if coverage_path.exists():
        coverage = read(coverage_path)
        for key in ('catalogue_only', 'atlas_only', 'composite_entries'):
            if isinstance(coverage.get(key), list):
                coverage[key] = [identifier for identifier in coverage[key] if identifier not in catalogue_ids]
        coverage['catalogue'] = len(people['people'])
        event_index = web / 'assets/research/event-index.json'
        if event_index.exists():
            coverage['typed_events'] = dict(Counter(event.get('kind', 'unresolved') for event in read(event_index)))
        put(coverage_path, coverage)
    if atlas is not None:
        put(atlas_path, atlas)
        from tools.site_payloads import pack_model
        put(web / 'assets/research/atlas-model-packed.json', pack_model(atlas))
    full = web / 'data/catalogue-search-index.json'
    if full.exists():
        search = read(full)
        for _, _, slug, _, _ in selected:
            current = next(p for p in people['people'] if p.get('catalogue_id') == slug)
            for row in search:
                if row.get('id') == slug and 'record_count' in row:
                    row['record_count'] = len(current.get('records', []))
        put(full, search)
        put(web / 'data/people-index.js', ('window.glasgowPeopleIndex=' + json.dumps(read(full), ensure_ascii=False, separators=(',', ':')) + ';\n').encode())
    source_index = web / 'assets/v3/source-index.json'
    packed_index = web / 'assets/v3/source-index-packed.json'
    if source_index.exists() and packed_index.exists():
        packed = read(packed_index)
        packed['rows'] = [[row.get(key) for key in packed['fields']] for row in read(source_index)]
        put(packed_index, packed)
    for relative in ('data/people.csv', 'data/records.csv', 'data/source-gaps.csv', 'data/source-review.csv'):
        mirror = web / (relative + '.txt')
        original = web / relative
        if mirror.exists() and original.exists():
            put(mirror, changes.get(str(original.relative_to(root)), original.read_bytes()))
    # Final byte comparison also ensures a repeat plan is empty.
    return {p: raw for p, raw in changes.items() if not (root / p).exists() or (root / p).read_bytes() != raw}


def apply(root: Path, catalogue_ids: list[str], *, refresh=True):
    changes = plan(root, catalogue_ids)
    for relative, content in changes.items():
        path = Path(root) / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(path.name + '.reconcile-tmp')
        temporary.write_bytes(content); temporary.replace(path)
    if changes and refresh:
        from tools.catalogue_search_index import refresh as refresh_search
        from tools import sync_catalogue_research
        refresh_search(Path(root) / 'www')
        previous_web = sync_catalogue_research.WEB
        try:
            sync_catalogue_research.WEB = Path(root) / 'www'
            sync_catalogue_research.refresh_catalogue_summaries(json.loads((Path(root) / 'www/data/catalogue-search-index.json').read_text()))
        finally:
            sync_catalogue_research.WEB = previous_web
    return changes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--catalogue-id', action='append', required=True)
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args()
    changes = apply(args.root, args.catalogue_id) if args.write else plan(args.root, args.catalogue_id)
    print(json.dumps({'mode': 'apply' if args.write else 'dry_run', 'files': sorted(changes)}, indent=2))


if __name__ == '__main__':
    import sys
    sys.path.insert(0, str(ROOT))
    main()
