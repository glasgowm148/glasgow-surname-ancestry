"""Withdraw explicitly reviewed canonical records from public chronology.

The private canonical row is retained. Only an exact-URL, single-entry source
can be withdrawn here; mixed sources require a separate reviewed reconciliation.
The source and record URLs retain non-identifying withdrawal notices.
"""
from copy import deepcopy
import json
from pathlib import Path


def withdrawn_source(row, document, public_rows):
    """Validate ownership before replacing a single-entry source with a notice."""
    if row.get('publish_to_record_index') is not False or not row.get('publication_withdrawal_reason'):
        raise ValueError('Withdrawal needs explicit canonical opt-out and a reviewed reason')
    if not row.get('reviewed_on') or not row.get('provenance'):
        raise ValueError('Withdrawal needs reviewed source provenance')
    url = row.get('source_url')
    if not url or document.get('url') != url:
        raise ValueError('Withdrawal source URL mismatch')
    # A register page can contain several distinct entries at the same URL.
    # Require a separate reviewed reconciliation before removing that source.
    if len(public_rows) > 1:
        raise ValueError('Mixed source has unrelated records; review required')
    if public_rows and public_rows[0]['record_id'] != row['record_id']:
        from tools.ingest_canonical_records import same_entry_rows
        if not same_entry_rows(row, public_rows):
            raise ValueError('Withdrawal does not identify the existing public entry')
    ids = {r['record_id'] for r in public_rows}
    ids.add(row['record_id'])
    if any(r.get('source_url') != url for r in public_rows):
        raise ValueError('Withdrawal contains an unrelated public entry')
    if any(r.get('id') not in ids for r in document.get('records', [])):
        raise ValueError('Mixed source has unrelated records; review required')
    for citation in document.get('citations', []):
        if (citation.get('source') or {}).get('url') != url:
            raise ValueError('Mixed source has unrelated citations; review required')
        if any(c.get('provenance') != 'mapped_record' for c in citation.get('claims', [])):
            raise ValueError('Withdrawal would replace non-generated claims; review required')
    result = deepcopy(document)
    result.update(title='Source attribution withdrawn pending review', members=[], citations=[], records=[], events=[],
                  record_count=0, citation_count=0, transcription=None, image=None,
                  date_basis='Withdrawn: no supported historical event date')
    # Prior evidence remains in the research database and the review receipt;
    # public annotations must not retain the withdrawn person/date assertions.
    result['annotations'] = {'publication_withdrawal': {
        'canonical_record_id': row['record_id'], 'reviewed_on': row['reviewed_on'],
        'reason': row['publication_withdrawal_reason']}}
    return result, ids


def apply(root, record_ids=None, *, refresh_sources=True):
    from tools.ingest_canonical_records import (main_body, packed_source_index, records_body,
                                               source_browse_pages, source_page)
    from tools.project_paths import atomic_write_text

    root = Path(root)
    web = root / 'www'
    read = lambda path: json.loads(path.read_text())
    canonical_path = root / 'research/canonical_records.json'
    if not canonical_path.exists():
        return {'withdrawn_records': 0, 'changed_files': 0}
    canonical = read(canonical_path)
    selected = [r for r in canonical if r.get('publish_to_record_index') is False
                and r.get('publication_withdrawal_reason') and (record_ids is None or r['record_id'] in record_ids)]
    if record_ids is not None and set(record_ids) != {r['record_id'] for r in selected}:
        raise ValueError('Select only explicit reviewed canonical withdrawals')
    if not selected:
        return {'withdrawn_records': 0, 'changed_files': 0}
    full = read(web / 'data/records-index.json')
    compact = read(web / 'assets/research/record-index.json')
    sources = read(web / 'assets/v3/source-index.json')
    writes, retired, changed_sources = {}, set(), {}
    # Plan the entire batch before any public write.
    for row in selected:
        public = [r for r in full if r.get('source_url') == row['source_url']]
        docs = [s for s in sources if any(r.get('document_id') == s['id'] for r in public)]
        if not docs:
            docs = [s for s in sources if read(web / f'assets/v3/sources/{s["id"]}.json').get('url') == row['source_url']]
        if len(docs) != 1:
            raise ValueError('Withdrawal needs one exact existing source')
        sid = docs[0]['id']
        document, ids = withdrawn_source(row, read(web / f'assets/v3/sources/{sid}.json'), public)
        retired.update(ids)
        changed_sources[sid] = document
        writes[web / f'assets/v3/sources/{sid}.json'] = document
        page = web / f'sources/{sid}/index.html'
        writes[page] = source_page(page.read_text(), document, existing=True, site_root=web)
        for rid in ids:
            writes[web / f'assets/research/records/{rid}.json'] = {
                'record_id': rid, 'withdrawn': True, 'canonical_record_id': row['record_id'],
                'reason': row['publication_withdrawal_reason'], 'source_url': row['source_url']}
    full = [r for r in full if r['record_id'] not in retired]
    compact = [r for r in compact if r['id'] not in retired]
    for source in sources:
        if source['id'] in changed_sources:
            source.update(title=changed_sources[source['id']]['title'], members=[], records=0, citations=0,
                          **{'from': None, 'to': None, 'image': False, 'transcription': False,
                             'date_basis': 'Withdrawn: no supported historical event date'})
    writes[web / 'data/records-index.json'] = full
    writes[web / 'assets/research/record-index.json'] = compact
    events_path = web / 'assets/research/event-index.json'
    if events_path.exists():
        urls = {row['source_url'] for row in selected}
        writes[events_path] = [event for event in read(events_path)
                              if event.get('source_url') not in urls
                              and event.get('document_id') not in changed_sources]
    writes[web / 'assets/v3/source-index.json'] = sources
    writes[web / 'assets/v3/source-index-packed.json'] = packed_source_index(sources)
    writes[web / 'records/index.html'] = main_body((web / 'records/index.html').read_text(), records_body(full))
    writes.update(source_browse_pages(web, sources))
    if refresh_sources:
        from tools.build_source_collections import ready
        if not ready(web):
            raise ValueError('Maintained Sources collection inputs are incomplete; no withdrawal writes applied')
    changed = 0
    for path, value in writes.items():
        text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, separators=(',', ':')) + '\n'
        if not path.exists() or path.read_text() != text:
            atomic_write_text(path, text)
            changed += 1
    if refresh_sources:
        from tools.build_source_collections import repair
        repair(web)
    return {'withdrawn_records': len(selected), 'changed_files': changed}
