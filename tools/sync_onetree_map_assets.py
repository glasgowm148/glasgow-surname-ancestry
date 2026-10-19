#!/usr/bin/env python3
"""Fill missing modern-map profile leads from the maintained CSV, locally.

Run after sync_onetree_ireland_uk_to_1900.py and public_privacy.py. Existing
reviewed associations and supplied coordinates stay intact. No geocoding occurs.
"""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path

try:
    from tools.build_research_catalog import _catalogue_record_types, _source_for_record, SITE_URL
    from tools.project_record_locations import stable_record_id
    from tools.project_paths import merged_map_profiles
    from tools.public_privacy import from_sources, likely_living, PROFILE_TOKEN, WITHHELD_TEXT, valid_map_item
except ModuleNotFoundError:
    from build_research_catalog import _catalogue_record_types, _source_for_record, SITE_URL
    from project_record_locations import stable_record_id
    from project_paths import merged_map_profiles
    from public_privacy import from_sources, likely_living, PROFILE_TOKEN, WITHHELD_TEXT, valid_map_item

ROOT = Path(__file__).resolve().parents[1]
COUNTRIES = {'Scotland': 'scotland', 'Ireland': 'ireland', 'England': 'england',
             'Wales': 'england', 'United Kingdom': 'england', 'United States': 'america',
             'Canada': 'canada', 'Australia': 'oceania', 'New Zealand': 'oceania'}


def merge_points(rows):
    """The viewer selects points by coordinates; keep coincident items together."""
    groups = {}
    for point in rows:
        key = (point['lat'], point['lon'], point['country'])
        if key not in groups:
            groups[key] = point
            continue
        existing = groups[key]
        existing['items'] = list({tuple(item): item for item in existing['items'] + point['items']}.values())
        for field in ('source_places', 'location_ids'):
            existing[field] = list(dict.fromkeys(existing.get(field, []) + point.get(field, [])))
        precisions = list(dict.fromkeys(existing.get('source_precisions', [existing['precision']])
                                        + point.get('source_precisions', [point['precision']])))
        if len(precisions) > 1:
            existing['source_precisions'] = precisions
            existing['precision'] = 'Mixed supplied precisions: ' + '; '.join(precisions)
    return list(groups.values())


def sync(web=ROOT / 'www', *, profiles=None, policy=None):
    web = Path(web)
    if profiles is None:
        profiles, _ = merged_map_profiles()
    policy = policy or from_sources(profiles=profiles)
    read = lambda relative: json.loads((web / relative).read_text())
    changed = 0
    pending = {}

    def write(relative, value):
        path = web / relative
        text = json.dumps(value, ensure_ascii=False, separators=(',', ':')) + '\n'
        if not path.exists() or path.read_text() != text:
            pending[path] = text

    people = read('data/catalogue-search-index.json')
    destinations = {ident.casefold(): person for person in people
                    for ident in person.get('profile_ids', [])
                    if not policy.contains_private_id(ident)}
    public_ids = {person['id'] for person in people}
    owners = {}
    bulk = web / 'data/people.json'
    if bulk.exists():
        for person in json.loads(bulk.read_text())['people']:
            slug = person.get('catalogue_id')
            if slug not in public_ids or policy.private_subject(person):
                continue
            ids = ' | '.join(person.get('profile_ids', []))
            for record in person.get('records', []):
                rid = record.get('record_id')
                if not rid:
                    continue
                if rid in owners and owners[rid]['catalogue_id'] != slug:
                    raise ValueError('Record has multiple canonical public owners')
                owners[rid] = {**record, 'catalogue_id': slug, 'person': person['name'],
                               'profile_ids': ids, 'catalogue_url': f'{SITE_URL}/people/{slug}.html',
                               'person_url': f'/people/{slug}.html', 'record_id': rid}

    def recover(record, rid, identity_key):
        owner = owners.get(rid)
        if not owner or record.get(identity_key) in public_ids:
            return record
        if record.get(identity_key) not in ('', None, WITHHELD_TEXT) and not record.get('withheld'):
            return record
        restored = dict(record)
        if record.get('withheld'):
            restored = dict(owner)
        restored.update({identity_key: owner['catalogue_id'], 'person': owner['person']})
        if identity_key == 'catalogue_id':
            restored.update(profile_ids=owner['profile_ids'], catalogue_url=owner['catalogue_url'],
                            person_url=owner['person_url'])
        return restored

    records_path = web / 'data/records-index.json'
    record_details = dict(owners)
    if records_path.exists():
        records = json.loads(records_path.read_text())
        records = [recover(r, r['record_id'], 'catalogue_id') for r in records]
        write('data/records-index.json', records)
        record_details.update({r['record_id']: {**owners.get(r['record_id'], {}), **r} for r in records})
    compact = read('assets/research/record-index.json')
    compact = [recover(r, r['id'], 'p') for r in compact]
    for record in compact:
        rid = record['id']
        if rid in owners and not (web / f'assets/research/records/{rid}.json').exists():
            detail = dict(record_details[rid])
            detail.update(person_url=owners[rid]['person_url'], country=record.get('country', 'other'))
            write(f'assets/research/records/{rid}.json', detail)
    removed = {r['id'] for r in compact if policy.private_subject(r)
               or (r.get('p') in ('', WITHHELD_TEXT) and r.get('title') == WITHHELD_TEXT)}
    for path in (web / 'assets/research/records').glob('*.json'):
        detail = json.loads(path.read_text())
        restored = recover(detail, path.stem, 'catalogue_id')
        if restored != detail:
            detail = restored
            write(path.relative_to(web).as_posix(), detail)
        if detail.get('withheld') or policy.private_subject(detail):
            removed.add(path.stem)
    compact = [r for r in compact if r['id'] not in removed]
    indexed = {r['id']: r['p'] for r in compact}
    point_files = ('assets/research/map-points.json', 'assets/v3/map-country-associations.json')
    points = {relative: read(relative) for relative in point_files}
    for relative, rows in points.items():
        for point in rows:
            point['items'] = [item for item in point.get('items', [])
                              if valid_map_item(item) and item[0] not in removed
                              and indexed.get(item[0]) == item[1]
                              and not policy.contains_private_id(item[1])]
        points[relative] = [point for point in rows if point['items']]
    mapped = {item[1] for rows in points.values() for point in rows for item in point['items']}
    records_by_person = {}
    for record in compact:
        records_by_person.setdefault(record['p'], []).append(record)
    with (web / 'map/data/records.csv').open(encoding='utf-8-sig', newline='') as handle:
        source = list(csv.DictReader(handle))
    added = []
    for row in source:
        if not row.get('family_group', '').endswith('One-Tree profile leads'):
            continue
        if 'non-geographic' in row.get('record_precision', '').casefold():
            continue
        ids = PROFILE_TOKEN.findall(row.get('profile_id', ''))
        if len(ids) != 1 or ids[0].casefold() not in destinations:
            continue
        ident = ids[0]
        profile = profiles.get(ident)
        if not profile or likely_living(profile) or policy.contains_private_id(ident):
            continue
        person = destinations[ident.casefold()]
        slug = person['id']
        if slug in mapped or not (web / 'people' / (slug + '.html')).is_file():
            continue
        try:
            lat, lon = float(row['latitude']), float(row['longitude'])
        except (ValueError, KeyError):
            continue
        if not (math.isfinite(lat) and math.isfinite(lon) and -90 <= lat <= 90 and -180 <= lon <= 180):
            raise ValueError('Map coordinate outside valid bounds')
        # Reuse a current reviewed record rather than replacing its assessment.
        existing = records_by_person.get(slug, [])
        matching = [r for r in existing if r.get('location_id') == row.get('location_id')]
        if existing and not matching:
            continue
        year = float(row['filter_year']) if row.get('filter_year') else None
        country = COUNTRIES.get(row.get('region'), 'other')
        if matching:
            rid = matching[0]['id']
        else:
            rid = stable_record_id(row, slug, 1, [])
            if any(r['id'] == rid for r in compact):
                raise ValueError('Duplicate generated map record ID')
            record = {**row, **_source_for_record(row, slug), 'record_id': rid,
                      'catalogue_id': slug, 'person': person['name'], 'profile_ids': ident,
                      'person_url': f'/people/{slug}.html', 'catalogue_url': f'/people/{slug}.html',
                      'filter_year': year, 'country': country, 'research_date': False,
                      'record_category': ' | '.join(_catalogue_record_types({'records': [row]})) or 'Other records',
                      'supporting_source_quality': 'unknown', 'supporting_source_status': 'unresolved',
                      'supporting_source_reason': 'Profile export lead; no independent citation reviewed.',
                      'document_id': None}
            write(f'assets/research/records/{rid}.json', record)
            compact.append({'id': rid, 'person': person['name'], 'p': slug, 'year': row['year'],
                            'y': year, 'place': row['record_location'], 'location_id': row['location_id'],
                            'country': country, 'category': record['record_category'],
                            'association': row['association'], 'status': row['evidence'], 'quality': 'unknown',
                            'title': record['source_title'], 'research_date': False,
                            'document_id': None, 'citation': 'unresolved'})
        precision = row['record_precision']
        broad = 'country' in precision.casefold()
        relative = point_files[1 if broad else 0]
        points[relative].append({'lat': lat, 'lon': lon, 'name': row['record_location'],
                                 'country': country, 'precision': precision,
                                 'items': [[rid, slug, year, False]],
                                 'source_places': [row['record_location']], 'location_ids': [row['location_id']],
                                 'level': 'country' if broad else 'locality',
                                 'precision_level': 'country' if broad else 'representative'})
        mapped.add(slug)
        added.append(slug)
    write('assets/research/record-index.json', compact)
    for relative, rows in points.items():
        write(relative, merge_points(rows))
    # Validate the whole batch before replacing any output.
    for path, text in pending.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        changed += 1
    for rid in removed:
        path = web / f'assets/research/records/{rid}.json'
        if path.is_file():
            path.unlink()
            changed += 1
    return {'files': changed, 'added_profile_leads': len(added), 'removed_private_records': len(removed)}


if __name__ == '__main__':
    print(sync())
