#!/usr/bin/env python3
"""Prepare small, reusable regional-map outlines from public boundary data.

Uses the existing Townlands.ie counties and Historic County Borders Project
inputs, plus Natural Earth states/provinces (50m), New Zealand regions (10m)
and countries (50m). Raw archives stay in data/reference; only simplified
geometry and attribution metadata are maintained under tools/branch_territories.
Run with --download to fetch missing Natural Earth archives.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'data/reference/boundaries/raw'
OUT = ROOT / 'tools/branch_territories'
SCOTTISH_CODES = set('ABN ANG ARG AYS BNF BRW BTE CTN CLM CRT DMF DUN ELT FFE INS KNC KNR KCB LNK MLT MOY NRN ORN PBS PRT RNF RSS RXB SKK SHT STL SRL WLT WGT'.split())
IRISH_CODES = set('ANM ARH DWN FRM LDR TYN'.split())
NATURAL_EARTH = {
    'ne_50m_admin_1_states_provinces': '50m',
    'ne_10m_admin_1_states_provinces': '10m',
    'ne_50m_admin_0_countries': '50m',
}


def convert(path, output, *args):
    subprocess.run(['npx', '--yes', '--', 'mapshaper', str(path), *args,
                    '-o', str(output), 'format=geojson', '-quiet'], check=True, cwd=ROOT)
    return json.loads(output.read_text())['features']


def main(download=False):
    RAW.mkdir(parents=True, exist_ok=True)
    sources = []
    for name, scale in NATURAL_EARTH.items():
        url = f'https://naturalearth.s3.amazonaws.com/{scale}_cultural/{name}.zip'
        archive = RAW / (name + '.zip')
        if not archive.exists() and download:
            urllib.request.urlretrieve(url, archive)
        if not archive.exists():
            raise FileNotFoundError(f'{archive}: use --download to fetch missing inputs')
        folder = RAW / name
        if not (folder / (name + '.shp')).exists():
            with zipfile.ZipFile(archive) as zipped:
                zipped.extractall(folder)
        sources.append({'url': url, 'licence': 'public domain',
                        'sha256': hashlib.sha256(archive.read_bytes()).hexdigest()})
    uk = convert(RAW / 'hcbp/UKDefinitionA.shp', RAW / 'regional_uk_counties.geojson',
                 '-each', 'name=NAME, code=HCS_CODE', '-filter-fields', 'name,code',
                 '-simplify', 'interval=1800', 'keep-shapes')
    admin = convert(RAW / 'ne_50m_admin_1_states_provinces/ne_50m_admin_1_states_provinces.shp', RAW / 'regional_admin1.geojson',
                    '-filter', 'admin=="United States of America" || admin=="Canada" || admin=="Australia"',
                    '-filter-fields', 'name,admin,iso_3166_2', '-simplify', 'interval=6000', 'keep-shapes')
    nz = convert(RAW / 'ne_10m_admin_1_states_provinces/ne_10m_admin_1_states_provinces.shp', RAW / 'regional_nz.geojson',
                 '-filter', 'admin=="New Zealand"', '-filter-fields', 'name,admin,iso_3166_2',
                 '-simplify', 'interval=3000', 'keep-shapes')
    countries = convert(RAW / 'ne_50m_admin_0_countries/ne_50m_admin_0_countries.shp', RAW / 'regional_countries.geojson',
                        '-filter-fields', 'ADMIN,ISO_A3', '-simplify', 'interval=12000', 'keep-shapes')
    ireland = convert(RAW / 'counties.geojson', RAW / 'regional_irish_counties.geojson',
                      '-each', 'name=NAME_EN||NAME_TAG', '-filter-fields', 'name',
                      '-simplify', 'interval=1800', 'keep-shapes')
    features = []

    def add(feature, **properties):
        if feature.get('geometry'):
            geometry = feature['geometry']
            # Keep Pacific islands next to their country instead of drawing
            # a ring across the entire map at the antimeridian.
            if properties.get('country') in {'nz', 'us'}:
                polygons = [geometry['coordinates']] if geometry['type'] == 'Polygon' else geometry['coordinates']
                for polygon in polygons:
                    for ring in polygon:
                        for point in ring:
                            if properties['country'] == 'nz' and point[0] < 0:
                                point[0] += 360
                            elif properties['country'] == 'us' and point[0] > 0:
                                point[0] -= 360
            features.append({'type': 'Feature', 'geometry': geometry, 'properties': properties})

    for feature in uk:
        p = feature['properties']
        if p['code'] in IRISH_CODES:
            continue  # the all-island Irish input supplies these counties
        region = 'scottish-families' if p['code'] in SCOTTISH_CODES else 'english-welsh-families'
        add(feature, id='hcbp-' + p['code'], name=p['name'], region=region,
            country='sct' if region == 'scottish-families' else 'gb', kind='county', source='hcbp')
    for feature in ireland:
        p = feature['properties']
        add(feature, id='ie-' + p['name'].lower().replace(' ', '-'), name=p['name'],
            region='early-ireland', country='ie', kind='county', source='townlands')
    for feature in admin + nz:
        p = feature['properties']
        code = p['iso_3166_2'] or p['name']
        country = {'United States of America': 'us', 'Canada': 'ca', 'Australia': 'au', 'New Zealand': 'nz'}[p['admin']]
        add(feature, id='ne-' + code.lower(), name=p['name'], admin=p['admin'], abbreviation=code.split('-')[-1],
            region='north-american-families' if country in {'us', 'ca'} else 'australasian-families',
            country=country, kind='province' if country == 'ca' else 'region' if country == 'nz' else 'state', source='naturalearth')
    for feature in countries:
        p = feature['properties']
        add(feature, id='country-' + p['ADMIN'].lower().replace(' ', '-'), name=p['ADMIN'],
            region='other-family-places', country='world', kind='country', source='naturalearth')
    payload = {'type': 'FeatureCollection', 'features': features}
    (OUT / 'regional-boundaries.geojson').write_text(json.dumps(payload, ensure_ascii=False, separators=(',', ':')) + '\n')
    sources += [
        {'url': 'https://www.townlands.ie/static/downloads/counties.geojson.zip', 'licence': 'ODbL', 'use': 'Irish counties'},
        {'url': 'https://www.county-borders.co.uk/UKDefinitionA_WG84_Simplified.zip', 'use': 'Historic County Borders Project counties'},
    ]
    (OUT / 'regional-boundaries-sources.json').write_text(json.dumps({'sources': sources, 'simplification_metres': {
        'historic_counties': 1800, 'states_provinces': 6000, 'new_zealand_regions': 3000, 'countries': 12000}}, indent=2) + '\n')
    print({'regional_boundary_features': len(features)})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--download', action='store_true')
    main(parser.parse_args().download)
