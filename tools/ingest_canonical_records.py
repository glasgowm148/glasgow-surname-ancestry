#!/usr/bin/env python3
"""Merge explicitly selected reviewed canonical records into public indexes.

Dry-run by default. Does not change people, dates, relationships or map points.
Existing source IDs are reused by provider identity; unrelated rows survive.
Finalization replays only canonical rows with publish_to_record_index=true.
Standalone replay (including Sources collections): --reviewed --apply. Explicit
--record-id/--source-file batches remain useful for review before opting in.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import date
from hashlib import sha256
from html import escape
import json
from pathlib import Path
import re
from urllib.parse import parse_qs, urlsplit

from tools.project_paths import ROOT, atomic_write_text
from tools.records_page import records_body
from tools.source_collection_index import _safe_url
from tools.repair_sources_page import SOURCE_INDEX_FIELDS, source_row


def read(path):
    return json.loads(path.read_text())


def provider_key(row):
    """Findmypast tab/parameter variations identify the same provider record."""
    url = row.get('source_url') or row.get('url') or ''
    parsed = urlsplit(url)
    if parsed.hostname and re.fullmatch(r'(?:www\.)?findmypast\.(?:co\.uk|com|ie|com\.au)', parsed.hostname):
        ident = (parse_qs(parsed.query).get('id') or [row.get('provider_record_id')])[0]
        if ident:
            return ('findmypast', ident)
    return ('url', url)


def merge(rows, supplied, key):
    by_id = {r[key]: r for r in supplied}
    if len(by_id) != len(supplied) or len({r[key] for r in rows}) != len(rows):
        raise ValueError(f"Duplicate {key}")
    return [by_id.pop(r[key], r) for r in rows] + list(by_id.values())


def main_body(shell, body):
    result, count = re.subn(r'(<main\b[^>]*>)[\s\S]*?(</main>)',
                          lambda m: m[1] + body + m[2], shell, count=1, flags=re.I)
    if count != 1:
        raise ValueError("Maintained page shell has no main container")
    return result


def source_page(shell, doc, *, existing=False):
    title = escape(doc['title'])
    start, end = '<!-- canonical-record-ingest:start -->', '<!-- canonical-record-ingest:end -->'
    outside = re.sub(re.escape(start) + r'[\s\S]*?' + re.escape(end), '', shell, count=1)
    secondary = '<p class="r-kicker">Source item</p><h2>' in shell
    heading = 'h2' if existing and (start not in shell or secondary or re.search(r'<h1\b', outside, re.I)) else 'h1'
    body = f'<header><p class="r-kicker">Source item</p><{heading}>{title}</{heading}></header>'
    body += f'<p><a href="{escape(doc["url"], quote=True)}">Inspect the provider record</a></p>'
    body += '<p>Reviewed provider transcript; the original register has not been inspected unless the assessment explicitly states otherwise.</p>'
    for row in doc.get('records', []):
        body += '<article><h2>' + escape(row.get('association') or row.get('name') or 'Record association') + '</h2>'
        body += '<p>' + escape(' · '.join(str(row.get(k) or '') for k in ('date', 'place', 'status'))) + '</p>'
        body += '<p>' + escape(row.get('note') or '') + '</p></article>'
    body += '<h2>Linked people and record roles</h2><ul>'
    for row in doc.get('citations', []):
        who = escape(row.get('name') or row.get('person') or 'Unnamed record subject')
        if row.get('person'):
            who = f'<a href="/people/{escape(row["person"], quote=True)}.html">{who}</a>'
        body += '<li>' + who + ': ' + escape(row.get('assertion') or '') + '</li>'
    body += '</ul>'
    body = start + '<section aria-label="Reviewed canonical records">' + body + '</section>' + end
    if start in shell:
        result = re.sub(re.escape(start) + r'[\s\S]*?' + re.escape(end), lambda _: body, shell, count=1)
    elif existing:
        result = re.sub(r'</main>', lambda _: body + '</main>', shell, count=1, flags=re.I)
    else:
        result = main_body(shell, body)
    result = re.sub(r'<title>.*?</title>', lambda _: '<title>' + title + ' · Source library</title>', result, count=1, flags=re.S)
    result = re.sub(r'(<link\b[^>]*rel=["\']canonical["\'][^>]*href=)["\'][^"\']*["\']',
                    lambda m: m[1] + '"https://glasgow.phenotype.dev/sources/' + doc['id'] + '/"', result)
    result = re.sub(r'data-v3-source="[^"]*"', 'data-v3-source="' + doc['id'] + '"', result)
    result = re.sub(r'data-g-path="[^"]*"', 'data-g-path="/sources/' + doc['id'] + '/"', result, count=1)
    return result


def plan(root: Path, record_ids: list[str]):
    """Validate the complete batch before returning any proposed writes."""
    root = Path(root)
    web = root / 'www'
    canonical = read(root / 'research/canonical_records.json')
    lookup = {r['record_id']: r for r in canonical}
    if len(lookup) != len(canonical) or len(set(record_ids)) != len(record_ids):
        raise ValueError('Duplicate canonical or selected record IDs')
    if not record_ids or set(record_ids) - lookup.keys():
        raise ValueError('Select existing canonical record IDs explicitly')
    public = read(web / 'data/catalogue-search-index.json')
    destinations = {str(key).casefold(): p for p in public
                    for key in [p['id'], *p.get('profile_ids', [])]}
    full = read(web / 'data/records-index.json')
    compact = read(web / 'assets/research/record-index.json')
    sources = read(web / 'assets/v3/source-index.json')
    docs = {s['id']: read(web / f'assets/v3/sources/{s["id"]}.json') for s in sources}
    url_ids = {}
    for sid, doc in docs.items():
        if doc.get('url'):
            url_ids.setdefault(provider_key(doc), []).append(sid)
    source_template = next(iter(sorted((web / 'sources').glob('s-*/index.html'))), None)
    if source_template is None:
        raise ValueError('Existing maintained source-reader shell required')
    writes = {}
    new_full, new_compact, selected_docs = [], [], set()
    source_records = {}
    seen_providers = set()
    for rid in record_ids:
        row = lookup[rid]
        if not re.fullmatch(r'[a-zA-Z0-9_-]+', rid):
            raise ValueError('Unsafe record ID')
        if not row.get('reviewed_on') or not row.get('provenance') or not row.get('status'):
            raise ValueError(f'{rid}: reviewed date, provenance and assessment required')
        date.fromisoformat(row['reviewed_on'])
        if row.get('private') or row.get('living') or row.get('likely_living'):
            raise ValueError(f'{rid}: non-public subject')
        url = row.get('source_url')
        if not url or _safe_url(url) != url:
            raise ValueError(f'{rid}: safe public provider URL required')
        provider = provider_key(row)
        if provider[0] == 'findmypast' and row.get('provider_record_id') and row['provider_record_id'] != provider[1]:
            raise ValueError(f'{rid}: provider ID disagrees with transcript URL')
        if provider in seen_providers:
            raise ValueError(f'{rid}: duplicate selected provider record')
        seen_providers.add(provider)
        previous_rows = [r for r in full if provider_key(r) == provider]
        if len(previous_rows) > 1:
            raise ValueError(f'{rid}: multiple existing record IDs for provider; review required')
        if previous_rows:
            rid = previous_rows[0]['record_id']
            if not re.fullmatch(r'[a-zA-Z0-9_-]+', rid):
                raise ValueError('Unsafe existing record ID')
        year = row.get('year')
        if not isinstance(year, int) or isinstance(year, bool) or not 1 <= year <= 1900:
            raise ValueError(f'{rid}: explicit historical record year required')
        ids = url_ids.get(provider, [])
        if len(ids) > 1:
            raise ValueError(f'{rid}: ambiguous existing exact-URL source IDs')
        sid = ids[0] if ids else 's-' + sha256(url.encode()).hexdigest()[:16]
        if sid in docs and provider_key(docs[sid]) != provider:
            raise ValueError('Source ID collision')
        url_ids[provider] = [sid]
        doc = docs.setdefault(sid, {'id': sid, 'title': row.get('association') or rid,
                                  'url': url, 'reference': row.get('provider_record_id') or rid,
                                  'repository': '', 'grouping_basis': 'exact source URL',
                                  'members': [], 'citations': [], 'records': [], 'events': [],
                                  'transcription': None, 'image': None, 'annotations': {},
                                  'is_collection': False, 'date_basis': 'reviewed record year'})
        context = row.get('profiles') or {}
        linked = []
        for ident, assessment in context.items():
            person = destinations.get(ident.casefold())
            if not person or not (web / f'people/{person["id"]}.html').is_file():
                raise ValueError(f'{rid}: profile destination is not public: {ident}')
            role = assessment.get('role') if isinstance(assessment, dict) else ''
            if not role:
                raise ValueError(f'{rid}: explicit per-profile role required')
            linked.append((person, role))
        label = row.get('association') or rid
        qualification = '; '.join(p['name'] + ': ' + role for p, role in linked)
        note = ' '.join(filter(None, [row.get('note'), qualification, 'Reviewed ' + row['reviewed_on'] + '; ' + row['provenance']]))
        category = ('Births and baptisms' if '/BAP/' in str(row.get('provider_record_id')) or 'baptis' in label.lower()
                    else 'Deaths and burials' if 'bur' in label.lower() or '/BUR/' in str(row.get('provider_record_id')) else 'Other records')
        geography = ' '.join(str(row.get(k) or '') for k in ('place', 'association', 'provider_record_id'))
        country = ('england' if re.search(r'Birmingham|England', geography, re.I) else
                   'scotland' if re.search(r'Scot|Glasgow|Midcalder|Kirkliston|Leith|Cambusnethan|Kilmarnock', geography, re.I) else 'other')
        # A candidate link is navigation, never identification with the subject.
        slug = linked[0][0]['id'] if linked else ''
        person_url = '/people/' + slug + '.html' if slug else '/sources/' + sid + '/'
        person_label = row.get('person') or label
        if row.get('person') and any('candidate' in role.casefold() for _, role in linked):
            person_label += ' (candidate identity)'
        record = dict(record_id=rid, provider_record_id=row.get('provider_record_id'), catalogue_id=slug, person=person_label,
                      profile_ids=' | '.join(context), year=row.get('date') or str(year),
                      filter_year=year, region=country.title(), record_category=category,
                      association=label, note=note, location_id='', record_location=row.get('place') or '',
                      record_precision='Provider transcript place; not geocoded', evidence=row['status'],
                      catalogue_url=person_url, person_url=person_url, place_url='', source_title=label,
                      source_url=url, source_type='Reviewed canonical record', source_status=row['status'],
                      supporting_source_title=label, supporting_source_url=url, supporting_source_quality='derivative',
                      supporting_source_status='explicit', supporting_source_reason=row['status'],
                      country=country, research_date=False, document_id=sid, profile_context=deepcopy(context),
                      provenance=row['provenance'])
        previous = next((r for r in full if r['record_id'] == rid), None)
        if previous and provider_key(previous) != provider:
            raise ValueError(f'{rid}: existing record has a different source URL')
        new_full.append(record)
        new_compact.append(dict(id=rid, person=person_label, p=slug, year=record['year'], y=year,
                                place=record['record_location'], location_id='', country=country,
                                category=category, association=label + (' — ' + qualification if qualification else ''),
                                status=row['status'], quality='derivative', title=label,
                                research_date=False, document_id=sid, citation='explicit'))
        source_records.setdefault(sid, []).append(dict(id=rid, person=slug, name=label, year=year, country=country.title(),
                                  date=record['year'], place=record['record_location'],
                                  association=label, note=note, status=row['status']))
        citations = []
        for person, role in linked or [({}, 'No identified catalogue person')]:
            eid = 'E-' + sha256((rid + '|' + person.get('id', '')).encode()).hexdigest()[:16]
            citations.append(dict(evidence_id=eid, person=person.get('id', ''), name=person.get('name', label),
                                  type=label, date=record['year'], place=record['record_location'],
                                  assertion=role + '. ' + note, status='unassessed', quality='derivative',
                                  source={'title': label, 'url': url, 'reference': doc['reference']}, claims=[]))
        doc['citations'] = merge(doc.get('citations', []), citations, 'evidence_id')
        doc['members'] = list(dict.fromkeys([*doc.get('members', []), *(p['id'] for p, _ in linked)]))
        selected_docs.add(sid)
        writes[web / f'assets/research/records/{rid}.json'] = record
    full = merge(full, new_full, 'record_id')
    compact = merge(compact, new_compact, 'id')
    source_rows = []
    for sid in selected_docs:
        doc = docs[sid]
        doc['records'] = merge(doc.get('records', []), source_records[sid], 'id')
        doc['record_count'], doc['citation_count'] = len(doc['records']), len(doc['citations'])
        years = [r['year'] if isinstance(r.get('year'), int) else int(str(r['date'])[:4])
                 for r in doc['records'] if isinstance(r.get('year'), int) or re.match(r'^\d{4}', str(r.get('date', '')))]
        old = next((r for r in sources if r['id'] == sid), {})
        source_rows.append({**old, 'id': sid, 'title': doc['title'], 'members': doc['members'],
                            'records': doc['record_count'], 'citations': doc['citation_count'],
                            'from': min([*years, *([old['from']] if old.get('from') else [])]),
                            'to': max([*years, *([old['to']] if old.get('to') else [])]),
                            'image': bool(doc.get('image')), 'transcription': bool(doc.get('transcription')),
                            'basis': doc.get('grouping_basis', 'exact source URL'), 'date_basis': doc.get('date_basis', '')})
        writes[web / f'assets/v3/sources/{sid}.json'] = doc
        page = web / f'sources/{sid}/index.html'
        shell = page.read_text() if page.exists() else source_template.read_text()
        writes[page] = source_page(shell, doc, existing=page.exists())
    sources = merge(sources, sorted(source_rows, key=lambda r: r['id']), 'id')
    writes[web / 'data/records-index.json'] = full
    writes[web / 'assets/research/record-index.json'] = compact
    writes[web / 'assets/v3/source-index.json'] = sources
    writes[web / 'assets/v3/source-index-packed.json'] = {
        'fields': SOURCE_INDEX_FIELDS, 'rows': [[row.get(k) for k in SOURCE_INDEX_FIELDS] for row in sources]}
    writes[web / 'records/index.html'] = main_body((web / 'records/index.html').read_text(), records_body(full))
    browse = web / 'sources/browse/index.html'
    if browse.exists():
        shell = browse.read_text()
        header = re.search(r'<main\b[^>]*>\s*(<header\b[\s\S]*?</header>)', shell, re.I)
        if not header:
            raise ValueError('Maintained Sources browse header missing')
        ordered = sorted(sources, key=lambda r: (r.get('from') if r.get('from') is not None else 9999, r['title'].casefold()))
        pages = max(1, (len(ordered) + 99) // 100)
        def route(number):
            return '/sources/browse/' if number == 1 else f'/sources/browse/page-{number}.html'
        for number in range(1, pages + 1):
            path = browse if number == 1 else browse.parent / f'page-{number}.html'
            current = path.read_text() if path.exists() else shell
            previous = f'<a href="{route(number-1)}">← Previous</a>' if number > 1 else '<span></span>'
            following = f'<a href="{route(number+1)}">Next →</a>' if number < pages else '<span></span>'
            nav = f'<nav class="r-pagination" aria-label="Source index pages">{previous}<span>Page {number} of {pages} · {len(ordered):,} references</span>{following}</nav>'
            body = header[1] + nav + ''.join(source_row(r) for r in ordered[(number-1)*100:number*100]) + nav
            rendered = main_body(current, body)
            if not path.exists():
                rendered = re.sub(r'(<link\b[^>]*rel=["\']canonical["\'][^>]*href=)["\'][^"\']*["\']',
                                  lambda m: m[1] + '"https://glasgow.phenotype.dev' + route(number) + '"', rendered)
                rendered = re.sub(r'data-g-path="[^"]*"', 'data-g-path="' + route(number) + '"', rendered, count=1)
            writes[path] = rendered
    return writes


def apply(root, record_ids, *, refresh_sources=True):
    writes = plan(root, record_ids)
    if refresh_sources:
        from tools.build_source_collections import ready
        if not ready(Path(root) / 'www'):
            raise ValueError('Maintained Sources collection inputs are incomplete; no writes applied')
    changed = 0
    for path, value in writes.items():
        content = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, separators=(',', ':')) + '\n'
        if not path.exists() or path.read_text() != content:
            path.parent.mkdir(parents=True, exist_ok=True)
            atomic_write_text(path, content)
            changed += 1
    if refresh_sources:
        from tools.build_source_collections import repair
        repair(Path(root) / 'www')
    return {'selected_records': len(record_ids), 'changed_files': changed}


def reviewed_record_ids(root=ROOT):
    path = Path(root) / 'research/canonical_records.json'
    if not path.exists():
        return []
    rows = read(path)
    return [row['record_id'] for row in rows if row.get('publish_to_record_index') is True]


def publish_reviewed(root=ROOT):
    """Replay only explicit public-record opt-ins after broader generators."""
    ids = reviewed_record_ids(root)
    if not ids:
        return {'selected_records': 0, 'changed_files': 0}
    # The finalizer rebuilds Sources collections immediately afterwards.
    return apply(Path(root), ids, refresh_sources=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--record-id', action='append', default=[])
    parser.add_argument('--source-file', type=Path, help='Reviewed canonical provenance file; select its exact rows')
    parser.add_argument('--reviewed', action='store_true', help='Replay only publish_to_record_index=true rows (also run by finalization)')
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    if args.reviewed and (args.record_id or args.source_file):
        parser.error('--reviewed cannot be combined with explicit record selection')
    ids = args.record_id
    if args.reviewed:
        ids = reviewed_record_ids(args.root)
    if args.source_file:
        source = args.source_file.resolve().relative_to(args.root.resolve()).as_posix()
        ids += [r['record_id'] for r in read(args.root / 'research/canonical_records.json') if r.get('provenance') == source]
    if args.reviewed and not ids:
        print(json.dumps({'selected_records': 0, 'changed_files': 0} if args.apply else {'selected_records': 0, 'planned_files': 0}))
    else:
        result = apply(args.root, ids) if args.apply else {'selected_records': len(ids), 'planned_files': len(plan(args.root, ids))}
        print(json.dumps(result))


if __name__ == '__main__':
    main()
