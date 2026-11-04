"""Compact rows for the master source list on /sources/ and its category views.

One row per public reference item (the collection index), enriched with the
published record entries that cite it (``data/records-index.json``) and, for
records already in that public index, the reviewed canonical fields (provider,
collection, archive reference, source level and the indexed role). Canonical
rows that are not in the public record index are never read into the output,
so withheld or possibly-living people stay out.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

CATEGORY_ORDER = ['newspapers', 'census', 'births', 'marriages', 'deaths', 'wills-probate', 'land-tax',
                  'church', 'military', 'directories', 'education', 'histories', 'pedigrees', 'other']

PROVIDERS = [
    (r'(^|\.)trees\.ancestry\.|(^|\.)ancestry\.com/family-tree', 'Ancestry trees'),
    (r'(^|\.)ancestry\.', 'Ancestry'), (r'findmypast\.', 'Findmypast'), (r'familysearch\.org', 'FamilySearch'),
    (r'wikitree\.com', 'WikiTree'), (r'findagrave\.com', 'Find a Grave'), (r'scotlandspeople\.gov\.uk', 'ScotlandsPeople'),
    (r'nrscotland\.gov\.uk', 'National Records of Scotland'), (r'irishgenealogy\.ie', 'IrishGenealogy.ie'),
    (r'nationalarchives\.ie', 'National Archives of Ireland'), (r'proni\.gov\.uk', 'PRONI'),
    (r'britishnewspaperarchive\.co\.uk', 'British Newspaper Archive'), (r'newspapers\.com', 'Newspapers.com'),
    (r'paperspast\.natlib\.govt\.nz', 'Papers Past'), (r'bdmhistoricalrecords\.dia\.govt\.nz', 'NZ BDM'),
    (r'myheritage\.', 'MyHeritage'), (r'geni\.com', 'Geni'), (r'archive\.org', 'Internet Archive'),
    (r'books\.google\.', 'Google Books'), (r'gro\.gov\.uk', 'GRO (England & Wales)'),
    (r'nationalarchives\.gov\.uk', 'The National Archives (UK)'), (r'wikipedia\.org', 'Wikipedia'),
]

# Archive references printed in citation titles. Deliberately narrow: a false
# reference is worse than a blank cell.
REFERENCE_PATTERNS = [
    r'\bPRONI\s+[A-Z]{1,5}\s?/\s?[\w./-]*\d[\w./-]*',
    r'\b(?:RG|HO|WO|PROB|IR|ADM|PIN|BT|MH|ASSI)\s?\d{1,3}(?:/[\w]+)*\b',
    r'\bOPR\s+\d+[A-Z]?(?:/\d+)*\b',
    r'\b(?:CH[23]|SC\d{1,3}|GD\d{1,3}|RH\d{1,3}|CS\d{1,3}|NG\d{1,3})/[\d/]+\b',
    r'\b(?:MIC|T|D)/\d[\d/A-Z]*\b',
    r'\bmicrofilm\s+[A-Z]?\d[\d,]*\d(?:,\s*roll\s+\d+)?',
]

DATE_STATUS = {
    'record year': 'Record date', 'record dates': 'Record date', 'source title': 'Year from title',
    'reviewed citation title': 'Year from title', 'multiple census years': 'Several years',
    'multiple record years': 'Several years', 'reviewed undated': 'Undated (reviewed)', 'unknown': 'Unresolved',
}

MAX_PEOPLE = 8

REVIEWED_CATEGORY_PATTERNS = [
    ('newspapers', r'newspaper'), ('census', r'census'), ('births', r'birth|baptis|christen'),
    ('marriages', r'marri|banns|divorce'), ('deaths', r'death|burial'), ('wills-probate', r'will|probate'),
    ('land-tax', r'land|tax|valuation|property'), ('church', r'church|parish'), ('military', r'military'),
    ('directories', r'director'), ('education', r'education|school'), ('pedigrees', r'family hist|pedigree'),
]


def reviewed_categories(web: Path) -> dict:
    """Record types from the reviewed record entries of each ingested source.

    Only categories that map cleanly are returned; a source without one keeps
    the keyword classification.
    """
    records = json.loads((Path(web) / 'data/records-index.json').read_text(encoding='utf-8'))
    found = {}
    for record in records:
        sid = record.get('document_id')
        if not sid:
            continue
        for part in str(record.get('record_category') or '').split('|'):
            part = part.strip().casefold()
            for key, pattern in REVIEWED_CATEGORY_PATTERNS:
                if part and re.search(pattern, part):
                    found.setdefault(sid, set()).add(key)
    return {sid: [c for c in CATEGORY_ORDER if c in keys] for sid, keys in found.items()}


def provider(url, kind):
    host_path = re.sub(r'^https?://(www\.)?', '', str(url or ''), flags=re.I).casefold()
    if not host_path:
        return ''
    for pattern, label in PROVIDERS:
        if re.search(pattern, host_path):
            return label
    host = urlparse(str(url)).netloc.casefold().removeprefix('www.')
    return host.split(')')[0].strip('.') or ''


def findmypast_dataset(url):
    """Findmypast transcript ids start with the dataset code (e.g. SCOT/OPR/BAP)."""
    query = parse_qs(urlparse(str(url)).query)
    ident = unquote((query.get('id') or [''])[0])
    parts = [p for p in ident.split('/') if p and not p.isdigit()]
    return '/'.join(parts[:3])


def references(text):
    found = []
    for pattern in REFERENCE_PATTERNS:
        for match in re.finditer(pattern, text):
            value = ' '.join(match[0].split()).rstrip(' .;:')
            if value and value not in found:
                found.append(value)
    return found[:3]


def level_label(canonical, record, row):
    """Original, transcript, index or family account, from the most specific evidence."""
    level = str((canonical or {}).get('source_level') or '').casefold()
    quality = str((canonical or {}).get('source_quality') or '').casefold()
    rtype = str((canonical or {}).get('record_type') or '').casefold()
    if quality.startswith('original') or quality == 'primary' or (record or {}).get('supporting_source_quality') == 'original':
        return 'Original'
    if 'transcript' in level or 'transcri' in quality:
        return 'Transcript'
    if level == 'index' or 'index' in rtype:
        return 'Index'
    if row.get('original_kind') == 'profile' or quality in {'tree_only', 'family_history'}:
        return 'Family account'
    if quality in {'secondary', 'late_compiled_history'} or row['categories'] == ['histories']:
        return 'Published account'
    if row.get('image'):
        return 'Image'
    return 'Not assessed'


def match_label(role):
    role = str(role or '').casefold()
    if 'candidate' in role or 'possible' in role or 'probable' in role:
        return 'Candidate'
    if 'not ' in role and 'same' in role:
        return 'Different person'
    return 'Linked'


def clean(value):
    return ' '.join(str(value or '').split())


def build_rows(web: Path, rows: list[dict], root: Path) -> dict:
    records = json.loads((web / 'data/records-index.json').read_text(encoding='utf-8'))
    by_doc = {}
    for record in records:
        if record.get('document_id'):
            by_doc.setdefault(record['document_id'], []).append(record)
    public_ids = {r['record_id'] for r in records if r.get('document_id')}
    canonical_path = root / 'research/canonical_records.json'
    canonical = {}
    if canonical_path.exists():
        for row in json.loads(canonical_path.read_text(encoding='utf-8')):
            # Only rows already published to the record index; never the held ones.
            if row.get('record_id') in public_ids and row.get('publish_to_record_index') is True:
                canonical[row['record_id']] = row
    out = []
    for row in rows:
        entries = sorted(by_doc.get(row['id'], []), key=lambda r: (r.get('filter_year') or 9999, r['record_id']))
        first = entries[0] if entries else None
        canon = canonical.get(first['record_id']) if first else None
        years = row.get('years') or []
        year = row.get('year') if row.get('year') is not None else (years[0] if years else None)
        status = DATE_STATUS.get(row.get('year_basis') or 'unknown', 'Unresolved')
        if first and first.get('date_status') == 'undated':
            status = 'Undated (reviewed)'
        date = clean(first.get('year')) if first and first.get('date_status') != 'undated' else ''
        if date and re.fullmatch(r'\d{4}', date):
            date = ''
        members = {p['id'].casefold(): p for p in row.get('people') or []}
        named, linked, pending = [], {}, 0
        for entry in entries:
            canon_entry = canonical.get(entry['record_id']) or {}
            name = clean(canon_entry.get('person') or entry.get('person'))
            role = clean(canon_entry.get('event_role'))
            if not role:
                assoc = clean(entry.get('association'))
                role = assoc.split(' — ', 1)[1].split(';')[0] if ' — ' in assoc else ''
            if name and [name, role] not in named:
                named.append([name, role])
            for ident, context in (entry.get('profile_context') or {}).items():
                person = members.get(ident.casefold())
                context_role = context.get('role', '') if isinstance(context, dict) else ''
                if person:
                    linked.setdefault(person['id'], [clean(person['name']), person.get('url') or '', match_label(context_role), clean(context_role)])
            pending += len(entry.get('pending_profile_ids') or [])
        for person in row.get('people') or []:
            linked.setdefault(person['id'], [clean(person['name']), person.get('url') or '', 'Cited', ''])
        if not named:
            named = [[name, role] for name, _, _, role in list(linked.values())[:MAX_PEOPLE]]
        url = row.get('original_url') or ''
        prov = clean((canon or {}).get('provider')) or provider(url, row.get('original_kind'))
        collection = clean((canon or {}).get('collection'))
        if not collection and prov == 'Findmypast':
            collection = findmypast_dataset(url)
        refs = [clean(canon[k]) for k in ('tna_reference',) if canon and canon.get(k)]
        if not refs:
            refs = references(row.get('title') or '')
        rtype = clean((canon or {}).get('record_type'))
        if not rtype or rtype == 'Previously held source citation':
            rtype = clean(first.get('record_category')) if first else ''
        places = [clean(p) for p in row.get('places') or [] if clean(p)]
        if first and first.get('record_location') and clean(first['record_location']) not in places:
            places.insert(0, clean(first['record_location']))
        item = {
            'i': row['id'], 't': row.get('display_title') or row.get('title') or row['id'],
            'y': year, 'ds': status, 'c': [CATEGORY_ORDER.index(c) for c in row['categories'] if c in CATEGORY_ORDER],
            'co': row.get('countries') or [], 'pv': prov,
        }
        optional = {
            'ys': years if len(years) > 1 else None, 'd': date,
            'pl': places[:3], 'cl': collection, 'rf': ' · '.join(refs), 'lv': level_label(canon, first, row),
            'rt': rtype, 'n': named[:MAX_PEOPLE], 'nn': len(named) if len(named) > MAX_PEOPLE else None,
            'p': list(linked.values())[:MAX_PEOPLE], 'pn': len(linked) if len(linked) > MAX_PEOPLE else None,
            'pp': pending or None, 'u': url, 'k': 'p' if row.get('original_kind') == 'profile' else None,
            'r': len(entries) or None,
        }
        item.update({k: v for k, v in optional.items() if v})
        out.append(item)
    return {'categories': CATEGORY_ORDER, 'rows': out}
