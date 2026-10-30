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


def entry_subjects(row):
    """People an entry names: canonical ``profiles`` keys or an index row's ``profile_ids``."""
    value = row.get('profiles') or row.get('profile_ids') or []
    if isinstance(value, dict):
        value = list(value)
    if isinstance(value, str):
        value = value.split('|')
    return frozenset(str(item).strip().casefold() for item in value if str(item).strip())


def entry_key(row):
    """A provider record id names one record; a page URL can hold many entries.

    On a page (any provider key other than a record id), the entry is told
    apart by the people it names, so two baptisms on one register page are two
    records rather than a conflict.
    """
    provider = provider_key(row)
    return provider if provider[0] == 'findmypast' else (*provider, entry_subjects(row))


def same_entry_rows(row, rows):
    """Existing rows that are the same entry as ``row`` (see :func:`entry_key`)."""
    provider = provider_key(row)
    previous = [r for r in rows if provider_key(r) == provider]
    if provider[0] == 'findmypast' or not entry_subjects(row):
        return previous
    matched = [r for r in previous if entry_subjects(r) == entry_subjects(row)]
    if not matched and len(previous) == 1 and not entry_subjects(previous[0]):
        return previous   # an earlier row that names nobody can only be this entry
    return matched


def merge(rows, supplied, key):
    by_id = {r[key]: r for r in supplied}
    if len(by_id) != len(supplied) or len({r[key] for r in rows}) != len(rows):
        raise ValueError(f"Duplicate {key}")
    return [by_id.pop(r[key], r) for r in rows] + list(by_id.values())


def merge_citations(rows, supplied):
    """A shared evidence item may retain a separate citation for each person."""
    def identity(row):
        return row['evidence_id'], row['person']

    by_id = {identity(row): row for row in supplied}
    if len(by_id) != len(supplied) or len({identity(row) for row in rows}) != len(rows):
        raise ValueError('Duplicate (evidence_id, person)')
    return [by_id.pop(identity(row), row) for row in rows] + list(by_id.values())


def main_body(shell, body):
    result, count = re.subn(r'(<main\b[^>]*>)[\s\S]*?(</main>)',
                          lambda m: m[1] + body + m[2], shell, count=1, flags=re.I)
    if count != 1:
        raise ValueError("Maintained page shell has no main container")
    return result


READER = '<div id="v3-reader"'


def ensure_reader(page, doc):
    """Give a source page the standard reader container if it lacks one.

    Every source page carries ``<div id="v3-reader">``, where the reader script
    opens the record and other publishers (``publish_static_sources``) anchor
    their sections; a page made from the canonical block alone had none.
    """
    if READER in page:
        return page
    url = escape(doc.get('url') or '', quote=True)
    title = escape(' '.join((doc.get('title') or 'this source').split()))
    archive = f'<a href="{url}">Open the cited archive</a>' if url else ''
    reader = (f'{READER} aria-live="polite"><p class="r-loading">Opening the record, text and linked people…</p>'
              f'<noscript><p>This reading workspace needs JavaScript. The original citation is still available: '
              f'{title}.</p>{archive}</noscript></div>')
    result, count = re.subn(r'</main>', lambda _: reader + '</main>', page, count=1, flags=re.I)
    if count != 1:
        raise ValueError('Source page has no main container')
    return result


def repair_layout(root=ROOT):
    """Add the standard reader to every source page that lacks it; returns the pages changed."""
    web = Path(root) / 'www'
    changed = []
    for source in sorted((web / 'assets/v3/sources').glob('s-*.json')):
        page = web / 'sources' / source.stem / 'index.html'
        if page.is_file():
            text = page.read_text(encoding='utf-8')
            updated = ensure_reader(text, json.loads(source.read_text(encoding='utf-8')))
            if updated != text:
                page.write_text(updated, encoding='utf-8')
                changed.append(page.relative_to(web).as_posix())
    return changed


def source_page(shell, doc, *, existing=False, site_root=None):
    site_root = Path(site_root) if site_root is not None else None
    canonical_ids = set()
    for citation in doc.get('citations', []):
        for claim in citation.get('claims', []):
            canonical_ids.update(str(item) for item in (claim.get('subject_ids') or []) if item)
    for record in doc.get('records', []):
        profiles = record.get('profiles') or {}
        canonical_ids.update(str(item) for item in profiles if item)
    canonical_by_key = {item.casefold(): item for item in canonical_ids
                        if re.fullmatch(r"[A-Z][A-Za-z'-]+-\d+", item)}
    title = escape(' '.join(doc['title'].split()))
    start, end = '<!-- canonical-record-ingest:start -->', '<!-- canonical-record-ingest:end -->'
    outside = re.sub(re.escape(start) + r'[\s\S]*?' + re.escape(end), '', shell, count=1)
    secondary = '<p class="r-kicker">Source item</p><h2>' in shell
    heading = 'h2' if existing and (start not in shell or secondary or re.search(r'<h1\b', outside, re.I)) else 'h1'
    body = f'<header><p class="r-kicker">Source item</p><{heading}>{title}</{heading}></header>'
    body += f'<p><a href="{escape(doc["url"], quote=True)}">Inspect the provider record</a></p>'
    title_correction = (doc.get('annotations') or {}).get('title_correction')
    if title_correction:
        body += '<p><strong>Source-title correction:</strong> ' + escape(title_correction['reason']) + '</p>'
    body += '<p>Reviewed source details and inspection limits are stated with each maintained record; an entry is not treated as an original image reading unless its assessment says so.</p>'
    for row in doc.get('records', []):
        body += '<article><h2>' + escape(' '.join((row.get('association') or row.get('name') or 'Record association').split())) + '</h2>'
        body += '<p>' + escape(' · '.join(str(row[k]) for k in ('date', 'place', 'country', 'status') if row.get(k))) + '</p>'
        body += '<p>' + escape(row.get('note') or '') + '</p></article>'
    body += '<h2>Linked people and record roles</h2><ul>'
    for row in doc.get('citations', []):
        who = escape(row.get('name') or row.get('person') or 'Unnamed record subject')
        person = str(row.get('person') or '')
        local = site_root / 'people' / f'{person}.html' if site_root and person else None
        if person and local and local.is_file():
            who = f'<a href="/people/{escape(person, quote=True)}.html">{who}</a>'
        elif person:
            target = canonical_by_key.get(person.casefold())
            if target:
                who = f'<a href="https://www.wikitree.com/wiki/{escape(target, quote=True)}">{who}</a>'
        earlier = (title_correction and (row.get('source') or {}).get('title') == title_correction['previous'])
        label = '<strong>Earlier reading, superseded:</strong> ' if earlier else ''
        body += '<li>' + label + who + ': ' + escape(row.get('assertion') or '') + '</li>'
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
    from tools.publish_static_sources import START as static_start, END as static_end, block as static_block
    if static_start in result:
        before, rest = result.split(static_start, 1)
        _, after = rest.split(static_end, 1)
        result = before + static_block(doc) + after
    return ensure_reader(result, doc)


def packed_source_index(sources):
    return {'fields': SOURCE_INDEX_FIELDS, 'rows': [[row.get(k) for k in SOURCE_INDEX_FIELDS] for row in sources]}


def source_browse_pages(web, sources):
    """The complete no-script source index, 100 rows a page, from the source index rows."""
    web = Path(web)
    browse = web / 'sources/browse/index.html'
    if not browse.exists():
        return {}
    shell = browse.read_text()
    header = re.search(r'<main\b[^>]*>\s*(<header\b[\s\S]*?</header>)', shell, re.I)
    if not header:
        raise ValueError('Maintained Sources browse header missing')
    ordered = sorted(sources, key=lambda r: (r.get('from') if r.get('from') is not None else 9999, r['title'].casefold()))
    pages = max(1, (len(ordered) + 99) // 100)
    def route(number):
        return '/sources/browse/' if number == 1 else f'/sources/browse/page-{number}.html'
    writes = {}
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
    # Provider lookup needs every source URL, but keeping every full source
    # document resident makes planning a large corpus unnecessarily costly.
    # Read each document for its URL, retain only lightweight lookup state,
    # then load full documents lazily for selected identities below.
    source_ids = list(dict.fromkeys(s['id'] for s in sources))
    source_id_set = set(source_ids)
    url_ids = {}
    for sid in source_ids:
        doc = read(web / f'assets/v3/sources/{sid}.json')
        if doc.get('url'):
            url_ids.setdefault(provider_key(doc), []).append(sid)
        del doc
    docs = {}
    source_template = next(iter(sorted((web / 'sources').glob('s-*/index.html'))), None)
    if source_template is None:
        raise ValueError('Existing maintained source-reader shell required')
    writes = {}
    new_full, new_compact, selected_docs = [], [], set()
    source_records = {}
    record_aliases = set()
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
        if entry_key(row) in seen_providers:
            raise ValueError(f'{rid}: duplicate selected provider record')
        seen_providers.add(entry_key(row))
        previous_rows = same_entry_rows(row, full)
        if len(previous_rows) > 1:
            raise ValueError(f'{rid}: multiple existing record IDs for this entry; review required')
        if previous_rows:
            rid = previous_rows[0]['record_id']
            if not re.fullmatch(r'[a-zA-Z0-9_-]+', rid):
                raise ValueError('Unsafe existing record ID')
            if rid != row['record_id']:
                aliases = [r for r in full if r['record_id'] == row['record_id']]
                if any(provider_key(r) != provider for r in aliases):
                    raise ValueError('Canonical record alias has a different source URL')
                record_aliases.add(row['record_id'])
        year = row.get('year')
        current_year = date.today().year
        undated = 'year' in row and year is None and row.get('date_status') == 'undated'
        if undated:
            basis = row.get('historical_basis')
            source = basis.get('source_url') if isinstance(basis, dict) else None
            explanation = (basis.get('reason') or basis.get('explanation')) if isinstance(basis, dict) else None
            event = basis.get('latest_event_year') if isinstance(basis, dict) else None
            birth = basis.get('latest_birth_year') if isinstance(basis, dict) else None
            valid_year = lambda value: isinstance(value, int) and not isinstance(value, bool) and 1 <= value <= current_year
            if (not isinstance(source, str) or _safe_url(source) != source
                    or not isinstance(explanation, str) or not explanation.strip()
                    or (event is not None and (not valid_year(event) or event > 1900))
                    or (birth is not None and (not valid_year(birth) or birth >= current_year - 120))
                    or (event is None and birth is None)):
                raise ValueError(f'{rid}: undated record requires a sourced historical event or birth bound and explanation')
            date_label = row.get('date', 'Undated')
            if not isinstance(date_label, str) or not date_label.strip() or any(ord(c) < 32 for c in date_label) or len(date_label) > 120:
                raise ValueError(f'{rid}: invalid undated display label')
            date_label = date_label.strip()
        elif not isinstance(year, int) or isinstance(year, bool) or not 1 <= year <= current_year or row.get('date_status') == 'undated':
            raise ValueError(f'{rid}: explicit historical record year required')
        elif year > 1900:
            basis = row.get('historical_basis') or {}
            latest_birth = basis.get('latest_birth_year') if isinstance(basis, dict) else None
            birth_source = basis.get('source_url') if isinstance(basis, dict) else None
            if (not isinstance(latest_birth, int) or isinstance(latest_birth, bool)
                    or not 1 <= latest_birth < current_year - 120 or latest_birth > year
                    or not birth_source or _safe_url(birth_source) != birth_source):
                raise ValueError(f'{rid}: post-1900 event requires a sourced historical birth bound')
        if not undated:
            date_label = row.get('date') or str(year)
        ids = url_ids.get(provider, [])
        if len(ids) > 1:
            raise ValueError(f'{rid}: ambiguous existing exact-URL source IDs')
        sid = ids[0] if ids else 's-' + sha256(url.encode()).hexdigest()[:16]
        if sid in docs or sid in source_id_set:
            # Exact provider matches are loaded for enrichment. A generated
            # ID may already belong to another source, so read that one row
            # only when needed to preserve the collision guard.
            existing_doc = docs.get(sid)
            if existing_doc is None:
                existing_doc = read(web / f'assets/v3/sources/{sid}.json')
            if provider_key(existing_doc) != provider:
                raise ValueError('Source ID collision')
            docs[sid] = existing_doc
        url_ids[provider] = [sid]
        doc = docs.setdefault(sid, {'id': sid, 'title': row.get('source_title') or row.get('association') or rid,
                                  'url': url, 'reference': row.get('provider_record_id') or rid,
                                  'repository': '', 'grouping_basis': 'exact source URL',
                                  'members': [], 'citations': [], 'records': [], 'events': [],
                                  'transcription': None, 'image': None, 'annotations': {},
                                  'is_collection': False, 'date_basis': 'reviewed undated' if undated else 'reviewed record year'})
        prior_title = row.get('source_title_supersedes')
        if prior_title:
            corrected_title = row.get('source_title')
            reason = row.get('source_title_correction_reason')
            if (not isinstance(prior_title, str) or not corrected_title or not reason
                    or doc['title'] not in {prior_title, corrected_title}):
                raise ValueError(f'{rid}: source-title correction needs the reviewed previous title and reason')
            doc['title'] = corrected_title
            doc.setdefault('annotations', {})['title_correction'] = dict(
                previous=prior_title, corrected=corrected_title, reason=reason)
            for citation in doc.get('citations', []):
                if (citation.get('source') or {}).get('title') == prior_title:
                    prefix = 'Earlier source reading, superseded — '
                    if not str(citation.get('type') or '').startswith(prefix):
                        citation['type'] = prefix + (citation.get('type') or 'Citation')
        if rid != row['record_id']:
            # The exact-entry match above retained a published stable ID.
            # Its earlier canonical ID is an alias, not a second event.
            doc['records'] = [r for r in doc.get('records', []) if r['id'] != row['record_id']]
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
        source_title = row.get('source_title') or label
        # The inspected image does not turn a compiled history into a primary
        # record, nor should ingestion relabel a reviewed manuscript derivative.
        reviewed_quality = row.get('source_quality')
        quality = ('original' if reviewed_quality in {'original', 'original_manuscript', 'original_register'}
                   else 'secondary' if reviewed_quality in {'secondary', 'late_compiled_history'}
                   else 'derivative')
        qualification = '; '.join(p['name'] + ': ' + role for p, role in linked)
        note = ' '.join(filter(None, [row.get('note'), qualification, 'Reviewed ' + row['reviewed_on'] + '; ' + row['provenance']]))
        category = row.get('record_category') or ('Births and baptisms' if '/BAP/' in str(row.get('provider_record_id')) or 'baptis' in label.lower()
                    else 'Deaths and burials' if re.search(r'bur|death|obituar', label, re.I) or '/BUR/' in str(row.get('provider_record_id')) else 'Other records')
        # A subject's surname (Glasgow) is not a Scottish jurisdiction signal.
        # Prefer the reviewed country, then the event place; collection wording
        # is only a fallback when no event place was supplied.
        geography = str(row.get('place') or row.get('association') or '')
        country = str(row.get('country') or '').strip().casefold()
        if not country:
            country = ('united states' if re.search(r'United States|Ohio|Pennsylvania', geography, re.I) else
                       'ireland' if re.search(r'Ireland|Irish|Cork', geography, re.I) else
                       'england' if re.search(r'Birmingham|England', geography, re.I) else
                       'scotland' if re.search(r'Scot|Glasgow|Midcalder|Kirkliston|Leith|Cambusnethan|Kilmarnock', geography, re.I) else 'other')
        # A candidate link is navigation, never identification with the subject.
        slug = linked[0][0]['id'] if linked else ''
        person_url = '/people/' + slug + '.html' if slug else '/sources/' + sid + '/'
        person_label = row.get('person') or label
        if row.get('person') and any('candidate' in role.casefold() for _, role in linked):
            person_label += ' (candidate identity)'
        record = dict(record_id=rid, provider_record_id=row.get('provider_record_id'), catalogue_id=slug, person=person_label,
                      profile_ids=' | '.join(context), year=date_label,
                      filter_year=year, region=country.title(), record_category=category,
                      association=label, note=note, location_id='', record_location=row.get('place') or '',
                      record_precision=row.get('record_precision') or 'Provider transcript place; not geocoded', evidence=row['status'],
                      catalogue_url=person_url, person_url=person_url, place_url='', source_title=source_title,
                      source_url=url, source_type='Reviewed canonical record', source_status=row['status'],
                      supporting_source_title=source_title, supporting_source_url=url, supporting_source_quality=quality,
                      supporting_source_status='explicit', supporting_source_reason=row['status'],
                      country=country, research_date=False, document_id=sid, profile_context=deepcopy(context),
                      provenance=row['provenance'])
        if undated:
            record['date_status'] = 'undated'
            record['historical_basis'] = deepcopy(row['historical_basis'])
        elif year > 1900:
            record['historical_basis'] = deepcopy(row['historical_basis'])
        previous = next((r for r in full if r['record_id'] == rid), None)
        if previous and provider_key(previous) != provider:
            raise ValueError(f'{rid}: existing record has a different source URL')
        new_full.append(record)
        new_compact.append(dict(id=rid, person=person_label, p=slug, year=record['year'], y=year,
                                place=record['record_location'], location_id='', country=country,
                                category=category, association=label + (' — ' + qualification if qualification else ''),
                                status=row['status'], quality=quality, title=source_title,
                                research_date=False, document_id=sid, citation='explicit'))
        source_records.setdefault(sid, []).append(dict(id=rid, person=slug, name=label, year=year, country=country.title(),
                                  date=record['year'], date_status='undated' if undated else 'dated',
                                  place=record['record_location'], association=label, note=note, status=row['status']))
        citations = []
        for person, role in linked or [({}, 'No identified catalogue person')]:
            eid = 'E-' + sha256((rid + '|' + person.get('id', '')).encode()).hexdigest()[:16]
            citations.append(dict(evidence_id=eid, person=person.get('id', ''), name=person.get('name', label),
                                  type=label, date=record['year'], place=record['record_location'],
                                  assertion=role + '. ' + note, status='unassessed', quality=quality,
                                  source={'title': source_title, 'url': url, 'reference': doc['reference']}, claims=[]))
        if linked:
            # A later identity review replaces this entry's generated
            # unassigned citation. Keep its reading as history, rather than
            # displaying a stale "no identified person" claim beside the match.
            unassigned_id = 'E-' + sha256((rid + '|').encode()).hexdigest()[:16]
            previous_citations = doc.get('citations', [])
            superseded = [c for c in previous_citations
                          if c.get('evidence_id') == unassigned_id and not c.get('person')]
            if superseded:
                history = doc.setdefault('annotations', {}).setdefault('superseded_citations', [])
                for citation in superseded:
                    if citation not in history:
                        history.append(deepcopy(citation))
                doc['citations'] = [c for c in previous_citations if c not in superseded]
        doc['citations'] = merge_citations(doc.get('citations', []), citations)
        doc['members'] = list(dict.fromkeys([*doc.get('members', []), *(p['id'] for p, _ in linked)]))
        selected_docs.add(sid)
        writes[web / f'assets/research/records/{rid}.json'] = record
    full = merge([r for r in full if r['record_id'] not in record_aliases], new_full, 'record_id')
    compact = merge([r for r in compact if r['id'] not in record_aliases], new_compact, 'id')
    source_rows = []
    for sid in selected_docs:
        doc = docs[sid]
        doc['records'] = merge(doc.get('records', []), source_records[sid], 'id')
        doc['record_count'], doc['citation_count'] = len(doc['records']), len(doc['citations'])
        years = [r['year'] if isinstance(r.get('year'), int) and not isinstance(r['year'], bool)
                 else int(str(r['date'])[:4])
                 for r in doc['records'] if r.get('date_status') != 'undated'
                 and ((isinstance(r.get('year'), int) and not isinstance(r['year'], bool))
                      or re.match(r'^\d{4}(?!\d)', str(r.get('date', ''))))]
        has_undated = any(r.get('year') is None for r in doc['records'])
        doc['date_basis'] = ('reviewed record years with undated records' if has_undated and years else
                             'reviewed undated' if has_undated else 'reviewed record year')
        old = next((r for r in sources if r['id'] == sid), {})
        # Preserve maintained bounds for ordinary dated sources. When an
        # undated record is present, only actual record years may bound it.
        bounds = years if has_undated else [*years, *([old['from']] if old.get('from') is not None else []),
                                              *([old['to']] if old.get('to') is not None else [])]
        source_rows.append({**old, 'id': sid, 'title': doc['title'], 'members': doc['members'],
                            'records': doc['record_count'], 'citations': doc['citation_count'],
                            'from': min(bounds) if bounds else None,
                            'to': max(bounds) if bounds else None,
                            'image': bool(doc.get('image')), 'transcription': bool(doc.get('transcription')),
                            'basis': doc.get('grouping_basis', 'exact source URL'), 'date_basis': doc.get('date_basis', '')})
        writes[web / f'assets/v3/sources/{sid}.json'] = doc
        page = web / f'sources/{sid}/index.html'
        shell = page.read_text() if page.exists() else source_template.read_text()
        writes[page] = source_page(shell, doc, existing=page.exists(), site_root=web)
    sources = merge(sources, sorted(source_rows, key=lambda r: r['id']), 'id')
    writes[web / 'data/records-index.json'] = full
    writes[web / 'assets/research/record-index.json'] = compact
    writes[web / 'assets/v3/source-index.json'] = sources
    writes[web / 'assets/v3/source-index-packed.json'] = packed_source_index(sources)
    writes[web / 'records/index.html'] = main_body((web / 'records/index.html').read_text(), records_body(full))
    writes.update(source_browse_pages(web, sources))
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
    parser.add_argument('--repair-layout', action='store_true',
                        help='give every source page without the standard reader container one, then stop')
    args = parser.parse_args()
    if args.repair_layout:
        changed = repair_layout(args.root)
        print(json.dumps({'repaired_source_pages': len(changed)}))
        return
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
