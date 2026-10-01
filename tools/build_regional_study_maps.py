#!/usr/bin/env python3
"""Publish region-specific copies of the Families & places concentration map."""
from collections import Counter, defaultdict
import copy
import csv
from html import escape
import json
import math
from pathlib import Path
import re
import runpy
import unicodedata
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / 'www'
BOUNDARIES = ROOT / 'tools/branch_territories'
REGION_NAMES = {
    'early-ireland': {'Ireland'},
    'scottish-families': {'Scotland'},
    'english-welsh-families': {'England', 'Wales'},
    'north-american-families': {'United States', 'Canada'},
    'australasian-families': {'Australia', 'New Zealand'},
}
COUNTRY_NAMES = {'us': 'United States', 'ca': 'Canada', 'au': 'Australia', 'nz': 'New Zealand'}
CORE_COUNTRIES = {'Ireland', 'United Kingdom', 'United States of America', 'Canada', 'Australia', 'New Zealand'}
COUNTRY_ONLY_LOCATIONS = {'england', 'wales', 'scotland', 'ireland', 'united kingdom', 'united states', 'usa', 'canada', 'australia', 'new zealand',
                          'england united kingdom', 'scotland united kingdom', 'wales united kingdom', 'ireland united kingdom', 'england uk'}
MAP_FRAMES = {
    'early-ireland': (-8.4, 53.8, -4.8, 55.7),
    'scottish-families': (-6.1, 54.9, -1.8, 57.1),
    'english-welsh-families': (-6.5, 49.8, 2.1, 55.9),
    'north-american-families': (-131, 24, -51, 57),
    'australasian-families': (110, -48, 187, -9),
    'other-family-places': (-95, -40, 105, 60),
}
MAP_RE = r'<section\b(?=[^>]*\bid="study-map")[^>]*>.*?</section>'
CONTROLS = 'Hover or tap an area for details. Use + and −, scroll or pinch to zoom; drag to move the map.'
COUNTY_ATTRIBUTION = ('Historic county outlines show representative study areas, not family lands. Boundaries: '
                      '<a href="https://www.county-borders.co.uk/">Historic County Borders Project</a>.')
WORLD_ATTRIBUTION = ('Administrative outlines show representative study areas, not family lands. Boundaries: '
                     '<a href="https://www.naturalearthdata.com/">Natural Earth</a> (public domain).')


def norm(text):
    text = ''.join(c for c in unicodedata.normalize('NFKD', text or '') if not unicodedata.combining(c))
    return re.sub(r'[^a-z0-9]+', ' ', text.lower()).strip()


def row_in_region(row, region):
    if region in REGION_NAMES:
        return row['region'] in REGION_NAMES[region]
    return row['region'] not in set().union(*REGION_NAMES.values()) | {'Scotland / England', 'United Kingdom', 'At Sea'}


def row_is_lead(row):
    return 'one-tree' in row.get('family_group', '').lower() or 'profile lead' in row.get('family_group', '').lower()


def assign_area(row, areas, inside):
    """Use named administrative areas; country-centre pins never locate them."""
    precision = row.get('record_precision', '').lower()
    if any(term in precision for term in ('inferred', 'holding', 'non-geographic')):
        return None
    text = norm(row.get('record_location', ''))
    if text in COUNTRY_ONLY_LOCATIONS and areas and areas[0]['properties']['kind'] != 'country':
        return None
    candidates = [f for f in areas if f['properties'].get('country') not in COUNTRY_NAMES
                  or row['region'] == COUNTRY_NAMES[f['properties']['country']]]
    # Administrative names usually follow the town. Prefer the last mention,
    # then the longest name: Washington, Louisiana is Louisiana, while West
    # Virginia wins over the shorter Virginia match at the same ending.
    named = []
    for feature in candidates:
        p = feature['properties']
        name = norm(re.sub(r' (District|City|Territory)$', '', p['name']))
        for match in re.finditer(r'(?<!\w)' + re.escape(name) + r'(?!\w)', text):
            named.append((match.end(), len(name), p['id']))
        abbreviation = p.get('abbreviation', '')
        if p['country'] in {'us', 'ca', 'au'} and len(abbreviation) in {2, 3}:
            for match in re.finditer(r'\b' + re.escape(abbreviation) + r'\b', row.get('record_location', '')):
                # Measure offsets in the same normalized string as full names.
                end = len(norm(row['record_location'][:match.end()]))
                named.append((end, len(abbreviation), p['id']))
    if named:
        return max(named)[2]
    # Geocoded localities can be placed inside a county; fallback points and
    # country-only entries cannot create an artificial concentration.
    if any(term in precision for term in ('country', 'fallback', 'state-level', 'province-level')):
        return None
    try:
        lon, lat = float(row['longitude']), float(row['latitude'])
    except (ValueError, KeyError):
        return None
    for feature in candidates:
        if inside(lon, lat, feature['geometry']):
            return feature['properties']['id']
    return None


def coverage_territories(region, boundaries, rows, groups, branches, inside):
    areas = [f for f in boundaries if f['properties']['region'] == region
             and not (region == 'other-family-places' and f['properties']['name'] in CORE_COUNTRIES)]
    by_area = defaultdict(list)
    for row in rows:
        if row_in_region(row, region):
            area = assign_area(row, areas, inside)
            if area:
                by_area[area].append(row)
    memberships = defaultdict(set)
    eligible = {g['id']: g for g in groups if region in g['regions']}
    for branch in branches:
        if branch['id'] in eligible:
            for member in branch.get('members', []):
                memberships[member.lower()].add(branch['id'])
    territories, additions = [], []
    for feature in areas:
        associated = by_area[feature['properties']['id']]
        if not associated:
            continue
        feature = copy.deepcopy(feature)
        p = feature['properties']
        people = {r.get('profile_id') or r['person'] for r in associated}
        documented = {r.get('profile_id') or r['person'] for r in associated if not row_is_lead(r)}
        lead_count = len(people - documented)
        sourced = sum(bool(r.get('source_url')) and not row_is_lead(r) for r in associated)
        area_id = 'records-' + p['id']
        matches = Counter(g for row in associated for g in memberships[row.get('profile_id', '').lower()])
        linked = sorted(matches, key=lambda g: (-matches[g], eligible[g]['label']))[:3]
        named = any(norm(p['name']) in norm(' '.join(r.get(k, '') for k in ('record_location', 'region', 'association', 'note'))) for r in associated)
        # A county found spatially need not be written in the searchable record.
        # Use its family links then, rather than inventing a county search term.
        studies = linked
        if named or not linked:
            query = p['name'] if named else associated[0]['person']
            additions.append({'id': area_id, 'url': '/records/?' + urlencode({'branch': region, 'q': query}),
                              'label': 'Records in ' + p['name'] if named else query + '’s records',
                              'status': 'Regional record coverage', 'tier': 'study', 'regions': [region]})
            studies = [area_id] + linked
        p.update(label=p['name'], studies=studies, parishes=[p['name']],
                 boundary_label=p['kind'].capitalize() + ' outline',
                 why=f'{len(people):,} people have records naming or located within this {p["kind"]}.',
                 metrics={'people': len(people), 'documented': len(documented), 'leads': lead_count, 'sourced': sourced,
                          'records': len(associated), 'evidence_text':
                          f'{len(documented):,} people with documentary records · {lead_count:,} unreviewed profile leads · {len(associated):,} record associations'})
        territories.append(feature)
    territories.sort(key=lambda f: (-f['properties']['metrics']['documented'], -f['properties']['metrics']['sourced'],
                                   -f['properties']['metrics']['people'], f['properties']['label']))
    territories = territories[:10]
    for rank, feature in enumerate(territories, 1):
        feature['properties']['priority'] = rank
    return territories, groups + additions


def fit_frame(bounds):
    """Use a consistent map aspect without stretching geographic outlines."""
    west, south, east, north = bounds
    lat = (south + north) / 2
    desired = (north - south) * 1.5 / math.cos(math.radians(lat))
    if east - west < desired:
        centre = (east + west) / 2
        west, east = centre - desired / 2, centre + desired / 2
    else:
        desired = (east - west) * math.cos(math.radians(lat)) / 1.5
        south, north = lat - desired / 2, lat + desired / 2
    return west, south, east, north


def write(path, text, changed):
    if not path.exists() or path.read_text() != text:
        path.write_text(text)
        changed['regional_study_maps'] += 1


def repair(directory=None, renderer=None):
    helper = runpy.run_path(str(ROOT / 'tools/build_branches_directory.py'))
    renderer = renderer or helper['render_study_map']
    directory = directory or json.loads((WEB / 'assets/research/branches-directory.json').read_text())
    boundaries = json.loads((BOUNDARIES / 'regional-boundaries.geojson').read_text())['features']
    branches = json.loads((WEB / 'assets/research/branches.json').read_text())
    with (WEB / 'map/data/records.csv').open(encoding='utf-8-sig', newline='') as source:
        rows = list(csv.DictReader(source))
    local = helper['rank_territories'](json.loads((BOUNDARIES / 'territories.geojson').read_text())['features'])
    changed, metadata = Counter(), {}
    for region in directory['regions']:
        rid = region['id']
        counties = [f for f in boundaries if f['properties']['region'] == rid]
        if rid in {'early-ireland', 'scottish-families'}:
            country = 'ie' if rid == 'early-ireland' else 'sct'
            territories = copy.deepcopy([f for f in local if f['properties']['country'] == country])
            for rank, feature in enumerate(territories, 1):
                feature['properties']['priority'] = rank
            groups = directory['groups']
            intro = f'Explore the main maintained study areas in {region["label"]}, ranked by research notes, sources and recorded people. ' + CONTROLS
            attribution = helper['DEFAULT_MAP_ATTRIBUTION']
            method = 'Maintained parish studies ranked by research notes, source material and documented people.'
        else:
            territories, groups = coverage_territories(rid, boundaries, rows, directory['groups'], branches, helper['_inside'])
            intro = 'Explore this region’s leading study areas. Documentary records are ranked ahead of profile leads awaiting review. ' + CONTROLS
            attribution = COUNTY_ATTRIBUTION if rid == 'english-welsh-families' else WORLD_ATTRIBUTION
            method = 'Explicit administrative names retained even when their coordinates are country-centre fallbacks; fallback coordinates and inferred locations never assign an area. Other localities use geocoded containment. Documentary coverage ranked before unreviewed profile leads.'
        if not territories:
            raise ValueError(f'No mapped study areas for {rid}')
        section = renderer(groups, territories, counties, bbox=fit_frame(MAP_FRAMES[rid]),
                           label=region['label'], intro=intro, attribution=attribution, region_id=rid, overseas=False)
        section = section.replace('<span class="r-kicker">Priority studies</span>', '<span class="r-kicker">Regional study areas</span>', 1)
        path = WEB / region['url'].strip('/') / 'index.html'
        page = re.sub(MAP_RE, '', path.read_text(), count=1, flags=re.S)
        page, count = re.subn(r'(<main\b[^>]*>.*?<header\b[^>]*>.*?</header>)',
                             lambda match: match[1] + section, page, count=1, flags=re.S)
        if count != 1:
            raise ValueError(f'Regional page header missing: {rid}')
        for asset, tag in [
            ('css', '<link rel="stylesheet" href="/assets/research/branches-directory.css?v=14">'),
            ('js', '<script defer src="/assets/research/branches-directory.js?v=7"></script>'),
        ]:
            pattern = r'<(?:link|script)\b[^>]*(?:href|src)="/assets/research/branches-directory\.' + asset + r'(?:\?[^\"]*)?"[^>]*>(?:</script>)?'
            page = re.sub(pattern, '', page)
            page = page.replace('</head>' if asset == 'css' else '</body>', tag + ('</head>' if asset == 'css' else '</body>'), 1)
        write(path, page, changed)
        metadata[rid] = {'label': region['label'], 'method': method, 'source': '/map/data/records.csv',
                         'areas': [f['properties'] for f in territories]}
    write(WEB / 'assets/research/regional-study-maps.json', json.dumps(metadata, ensure_ascii=False, indent=2) + '\n', changed)
    return changed


if __name__ == '__main__':
    print(dict(repair()))
