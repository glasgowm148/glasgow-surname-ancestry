"""Project approved chronology location corrections without rebuilding the catalogue.

The chronology registry owns decisions, matching fingerprints, stable record IDs,
prior map points and replacement text. This module projects only those records.
Run after ordinary dossier/catalogue publication, before targeted reader/index
refreshes. --restore restores the fields captured by this projection.
"""
from __future__ import annotations

import argparse
import csv
import io
from copy import deepcopy
from hashlib import sha1
import json
from pathlib import Path
import re
import tempfile

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / 'research/ancestry-connections/documentary-people.json'
MARKER = 'location_review'


def fingerprint(row):
    return {k: str(row.get(k, '')) for k in ('year', 'record_location', 'association')}


def load_projections(path=REGISTRY):
    registry = json.loads(Path(path).read_text())
    rows = []
    ids = set()
    selectors = set()
    for review in registry.get('chronology', []):
        p = review.get('map_projection')
        if not p:
            continue
        rid = p.get('record_id', '')
        if (review.get('publication_status') != 'approved' or not review.get('source_ids')
                or not review.get('assessment_id') or not review.get('id')
                or not re.fullmatch(r'[a-f0-9]{16}', rid) or rid in ids):
            raise ValueError('Map projection requires approved unique stable record ID and sources')
        ids.add(rid)
        allowed = p.get('match_fingerprints', [])
        if not allowed or any(set(f) != {'year', 'record_location', 'association'} for f in allowed):
            raise ValueError('Stable record ID requires exact record fingerprints')
        fields = p.get('record_fields') or {}
        if not fields.get('record_location') or not fields.get('association'):
            raise ValueError('A location correction cannot blank its recorded location')
        if len(review['source_ids']) != len(set(review['source_ids'])) or fields.get('canonical_source_ids') != review['source_ids']:
            raise ValueError('Map projection must reuse its exact canonical source IDs once')
        for value in allowed:
            selector = (review['id'].casefold(), tuple(sorted(value.items())))
            if selector in selectors: raise ValueError('Duplicate map record fingerprint')
            selectors.add(selector)
        if fingerprint(fields) not in allowed:
            raise ValueError('Corrected record fingerprint is not approved')
        point = p.get('point') or {}
        if (not isinstance(fields.get('filter_year'), (int, float))
                or not isinstance(point.get('lat'), (int, float))
                or not isinstance(point.get('lon'), (int, float))
                or not -90 <= point['lat'] <= 90 or not -180 <= point['lon'] <= 180
                or fields.get('location_id') not in point.get('location_ids', [])):
            raise ValueError('Location correction needs bounded coordinates, event year and matching location ID')
        rows.append(review)
    return rows


def stable_record_id(row, catalogue_id, ordinal, projections):
    """Use an approved exact-fingerprint override; otherwise preserve legacy hash."""
    matches = [r for r in projections
               if r['id'].casefold() == catalogue_id.casefold()
               and fingerprint(row) in r['map_projection']['match_fingerprints']]
    if len(matches) > 1:
        raise ValueError('Ambiguous stable record-ID override')
    if matches:
        return matches[0]['map_projection']['record_id']
    return sha1(f"{catalogue_id}|{ordinal}|{row.get('year')}|{row.get('record_location')}|{row.get('association')}".encode()).hexdigest()[:16]


def project_fields(row, fields, assessment_id, restore=False):
    """Retain only changed fields, including field absence, for exact rollback."""
    history = row.get(MARKER)
    if history and history.get('assessment_id') != assessment_id:
        raise ValueError('Refusing to overwrite a different location review')
    if restore:
        for key, prior in (history or {}).get('original_fields', {}).items():
            if prior['present']:
                row[key] = deepcopy(prior['value'])
            else:
                row.pop(key, None)
        row.pop(MARKER, None)
        return
    originals = deepcopy((history or {}).get('original_fields', {}))
    for key, value in fields.items():
        if row.get(key) != value or key not in row:
            originals.setdefault(key, {'present': key in row, 'value': deepcopy(row.get(key))})
            row[key] = deepcopy(value)
    if originals:
        row[MARKER] = {'assessment_id': assessment_id, 'original_fields': originals}


def project_points(points, review, restore=False):
    p = review['map_projection']; rid = p['record_id']; slug = review['id'].casefold()
    occurrences = [(point, item) for point in points for item in point.get('items', []) if item[0] == rid]
    if len(occurrences) != 1 or occurrences[0][1][1] != slug:
        raise ValueError('Expected one map item for the reviewed record/person')
    previous = p['previous_point']
    target = previous if restore else p['point']
    item = deepcopy(previous['items'][0] if restore else [rid, slug, p['record_fields']['filter_year'], False])
    old_point = occurrences[0][0]
    old_point['items'] = [i for i in old_point['items'] if i[0] != rid]
    # Reuse existing parish point; only remove an empty point belonging to this record.
    points[:] = [point for point in points if point is not old_point or point['items']]
    destination = next((point for point in points
                        if point.get('lat') == target['lat'] and point.get('lon') == target['lon']
                        and point.get('name') == target['name']), None)
    if destination is None:
        destination = {k: deepcopy(v) for k, v in target.items() if k != 'items'}
        destination['items'] = []
        points.append(destination)
    destination['items'].append(item)


def project_person(row, review, restore=False):
    p = review['map_projection']; aid = review['assessment_id']
    fields = {}
    if 'death_place' in row: fields['death_place'] = review['vitals']['death']['place']
    for key in ('search', 'meta', 'place'):
        if isinstance(row.get(key), str):
            revised = row[key]
            for old in p.get('previous_place_labels', [p['previous_point']['name']]):
                revised = revised.replace(old, review['vitals']['death']['place'])
            if revised != row[key]: fields[key] = revised
    for key, value in p.get('person_fields', {}).items():
        if key in row:
            fields[key] = value
    # Do not descend into imported/original/history sections.
    if isinstance(row.get('identity'), dict):
        identity = deepcopy(row['identity'])
        identity['locations'] = p['person_fields']['locations']
        fields['identity'] = identity
    if isinstance(row.get('vitals'), dict):
        vitals = deepcopy(row['vitals'])
        death = vitals.setdefault('death', {})
        for key in ('place', 'place_status', 'qualifier'):
            if key in review['vitals']['death']:
                death[key] = review['vitals']['death'][key]
        fields['vitals'] = vitals
    if isinstance(row.get('events'), list):
        events = deepcopy(row['events'])
        for event in events:
            if event.get('id') == 'death' or event.get('event_type') == 'death':
                event['place'] = review['vitals']['death']['place']
                event['note'] = review['vitals']['death']['qualifier']
        fields['events'] = events
    if isinstance(row.get('records'), list):
        records = deepcopy(row['records'])
        for record in records:
            if record.get('record_id') == p['record_id']:
                project_fields(record, p['record_fields'], aid, restore)
        fields['records'] = records
    project_fields(row, fields, aid, restore)


def project_csv(text, key, value, fields, original_row=None):
    """Replace one logical CSV row, preserving all unrelated bytes and quoting."""
    lines=text.splitlines(keepends=True)
    reader=csv.reader(lines)
    header=next(reader); header[0]=header[0].lstrip('\ufeff')
    previous=reader.line_num; matches=[]
    for values in reader:
        end=reader.line_num; row=dict(zip(header,values))
        if row.get(key)==value: matches.append((previous,end,row))
        previous=end
    if len(matches)!=1: raise ValueError('CSV projection needs exactly one matching row')
    start,end,row=matches[0]; before=''.join(lines[start:end])
    if original_row is not None:
        replacement=original_row
    else:
        projected=dict(row)
        for field,val in fields.items():
            if field in projected:
                projected[field]=' | '.join(map(str,val)) if isinstance(val,list) else str(val)
        if projected==row: return text,before
        out=io.StringIO(newline='')
        csv.writer(out,lineterminator='\r\n' if before.endswith('\r\n') else '\n').writerow([projected.get(h,'') for h in header])
        replacement=out.getvalue()
    return ''.join(lines[:start])+replacement+''.join(lines[end:]),before


def rewrite_main(page, body):
    match = re.search(r'(<main\b[^>]*>)[\s\S]*?(</main>)', page)
    if not match:
        raise ValueError('Place page has no maintained main shell')
    return page[:match.start()] + match[1] + body + match[2] + page[match.end():]


def render_place_main(records, people, location_id):
    """Call only the existing place writer for one location, in a temp directory."""
    try:
        from tools import build_research_catalog as catalogue
    except ModuleNotFoundError:
        import build_research_catalog as catalogue
    selected = [deepcopy(r) for r in records if r.get('location_id') == location_id]
    ids = {r['catalogue_id'] for r in selected}
    selected_people = [deepcopy(p) for p in people if p.get('catalogue_id', p.get('id')) in ids]
    with tempfile.TemporaryDirectory() as directory:
        out = Path(directory); (out/'places').mkdir(); (out/'data').mkdir()
        previous = catalogue.PLACES_DIR, catalogue.DATA_DIR
        catalogue.PLACES_DIR, catalogue.DATA_DIR = out/'places', out/'data'
        try:
            slug = catalogue._slug(location_id)
            catalogue._write_place_pages(selected, selected_people, {location_id:slug})
            page=(out/'places'/f'{slug}.html').read_text()
            match=re.search(r'<main\b[^>]*>([\s\S]*?)</main>',page)
            if not match: raise ValueError('Place writer produced no main')
            return re.sub(r'((?:href|src)=")\.\./', r'\1/', match[1])
        finally:
            catalogue.PLACES_DIR, catalogue.DATA_DIR = previous


def project(web, registry=REGISTRY, restore=False, write=False):
    """Prepare all changes first; write only after scope and cardinality validation."""
    web = Path(web); reviews = load_projections(registry); staged = {}; counts = {}
    def read(rel):
        path = web / rel
        if path not in staged:
            staged[path] = path.read_text()
        text = staged[path]
        if path.suffix == '.js': text = text.split('=', 1)[1].strip().rstrip(';')
        return json.loads(text)
    def put(rel, data):
        path = web / rel
        text = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
        if path.suffix == '.js': text = path.read_text().split('=', 1)[0] + '=' + text + ';'
        staged[path] = text + '\n'
    def optional(rel):
        return (web / rel).exists()
    for review in reviews:
        p = review['map_projection']; aid = review['assessment_id']; rid = p['record_id']; slug = review['id'].casefold()
        for rel in ('data/records-index.json', 'assets/research/record-index.json'):
            rows = read(rel); matches = [r for r in rows if (r.get('record_id') or r.get('id')) == rid]
            if len(matches) != 1:
                raise ValueError(f'{rel}: expected one canonical record row for {rid}')
            record = matches[0]
            if (record.get('catalogue_id') or record.get('p')) != slug:
                raise ValueError('Record ID belongs to another person')
            fields = dict(p['record_fields'] if rel.startswith('data/') else p['compact_fields'])
            if 'document_id' in record: fields['document_id'] = None
            project_fields(record, fields, aid, restore); put(rel, rows)
        rel = f'assets/research/records/{rid}.json'
        row = read(rel)
        csv_backups=deepcopy(row.get(MARKER,{}).get('csv_original_rows',{}))
        if row.get('record_id') != rid or row.get('catalogue_id') != slug:
            raise ValueError('Full record identity mismatch')
        fields = dict(p['record_fields'])
        if 'document_id' in row: fields['document_id'] = None
        project_fields(row, fields, aid, restore); put(rel, row)
        rel = 'assets/research/map-points.json'; points = read(rel)
        project_points(points, review, restore); put(rel, points)
        resolver_slug = re.sub(r'[^a-z0-9]+', '-', row.get('person', '').casefold()).strip('-')
        for rel in ('data/people.json', 'data/catalogue-search-index.json', 'data/people-index.json',
                    'data/people-index.js', f'data/resolve/{resolver_slug}.json',
                    'assets/research/search-index.json', 'assets/research/search-people.json'):
            if not optional(rel): continue
            data = read(rel); rows = data.get('people', data.get('candidates', [])) if isinstance(data, dict) else data
            matches = [r for r in rows if (r.get('catalogue_id') or r.get('id', '')).casefold() == slug]
            if len(matches) != 1: raise ValueError(f'{rel}: expected one reviewed person')
            project_person(matches[0], review, restore); put(rel, data)
        for rel in (f'people/{slug}.json', f'assets/research/people/{slug}.json'):
            if not optional(rel): continue
            row = read(rel)
            if row.get('id','').casefold() != slug: raise ValueError('Person file identity mismatch')
            project_person(row, review, restore); put(rel, row)
        for rel in ('assets/research/event-index.json', f'assets/v3/events/{slug}.json'):
            if not optional(rel): continue
            events=read(rel)
            for event in events:
                if event.get('p') == slug and (event.get('id') == 'death' or event.get('event_type') == 'death'):
                    project_fields(event, {'place':review['vitals']['death']['place'],
                        'note':review['vitals']['death']['qualifier']}, aid, restore)
            put(rel,events)
        # Place membership is small and explicit; unrelated rows retain their fields/order.
        for rel in ('assets/research/place-index.json', 'data/places-index.json'):
            if not optional(rel): continue
            places = read(rel)
            for place in places:
                if place.get('id') not in (p['previous_location_id'], p['record_fields']['location_id']): continue
                if restore:
                    project_fields(place, {}, aid, True)
                    continue
                canonical = read('assets/research/record-index.json')
                selected = [r for r in canonical if r.get('location_id') == place['id']]
                # Some historical compact rows omit location_id; use the retained
                # membership for unmodified records in that one location.
                retained = [r for r in canonical if r['id'] in place.get('record_ids', []) and r['id'] != rid]
                by_id = {r['id']:r for r in [*retained,*selected]}
                if place['id'] == p['previous_location_id']: by_id.pop(rid, None)
                records = list(by_id); members = list(dict.fromkeys(r['p'] for r in by_id.values()))
                fields = dict(records=len(records), people=len(members))
                if 'record_ids' in place: fields['record_ids'] = records
                if 'members' in place: fields['members'] = members
                years = [r['y'] for r in by_id.values() if isinstance(r.get('y'), (int,float))]
                fields.update(year_from=min(years) if years else None, year_to=max(years) if years else None)
                project_fields(place, fields, aid)
            put(rel, places)
        # Download mirrors use the same one-row projection; their original raw
        # rows live in the existing record's reversible location history.
        full_rel=f'assets/research/records/{rid}.json'
        full_record=read(full_rel)
        for csv_rel in ('data/records.csv','data/records.csv.txt','data/people.csv','data/people.csv.txt'):
            if not optional(csv_rel): continue
            path=web/csv_rel; text=path.read_bytes().decode('utf-8')
            if restore and csv_rel not in csv_backups: continue
            record_csv='records.csv' in csv_rel
            revised,original=project_csv(text,'record_id' if record_csv else 'catalogue_id',rid if record_csv else slug,
                p['record_fields'] if record_csv else p['person_fields'],csv_backups.get(csv_rel) if restore else None)
            if not restore and revised!=text: csv_backups.setdefault(csv_rel,original)
            staged[path]=revised
        if not restore and csv_backups:
            full_record.setdefault(MARKER,{'assessment_id':aid,'original_fields':{}})['csv_original_rows']=csv_backups
            put(full_rel,full_record)
        # Re-render just the destination place from projected data, preserving its shell.
        target_slug = p['record_fields']['location_id'].replace('_', '-')
        destination_rel = f'places/{target_slug}.html'
        if optional(destination_rel) and optional('data/people.json'):
            destination_path=web/destination_rel
            destination=destination_path.read_text()
            tag='<!-- reviewed-location-destination:'
            saved=re.search(re.escape(tag)+r'([0-9a-f]+) -->',destination)
            if restore:
                if saved: staged[destination_path]=bytes.fromhex(saved[1]).decode()
            else:
                original=bytes.fromhex(saved[1]).decode() if saved else destination
                body=render_place_main(read('data/records-index.json'),read('data/people.json')['people'],p['record_fields']['location_id'])
                fresh=rewrite_main(original,body)
                staged[destination_path]=fresh.replace('</main>','</main>'+tag+original.encode().hex()+' -->',1)
        # Existing routes are preserved. The old route explicitly explains reassignment.
        rel = p['previous_place_route'].lstrip('/'); page_path = web / rel
        if page_path.exists():
            page = page_path.read_text(); start='<!-- reviewed-location-original:'; end=' -->'
            if restore:
                found=re.search(re.escape(start)+r'([0-9a-f]+)'+re.escape(end), page)
                if found: staged[page_path]=bytes.fromhex(found[1]).decode()
            else:
                if start not in page:
                    original=page.encode().hex()
                    page=rewrite_main(page, p['reassignment_html'])
                    page=page.replace('</main>', '</main>'+start+original+end, 1)
                staged[page_path]=page
        counts[review['id']] = rid
    changed = {path: text for path,text in staged.items() if path.read_bytes().decode('utf-8') != text}
    if write:
        for path,text in changed.items(): path.write_bytes(text.encode('utf-8'))
    return {'records': counts, 'changed': [str(p.relative_to(web)) for p in changed], 'write':write, 'restore':restore}


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--www', type=Path, default=ROOT/'www')
    parser.add_argument('--registry', type=Path, default=REGISTRY)
    parser.add_argument('--write', action='store_true')
    parser.add_argument('--restore', action='store_true')
    args=parser.parse_args()
    print(json.dumps(project(args.www,args.registry,args.restore,args.write),indent=2))
