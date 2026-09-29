#!/usr/bin/env python3
"""Reconcile the death match audit with verified live WikiTree citations."""
import csv
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IDX = ROOT / 'surname-research/indexes'
SOURCE = IDX / 'groni-death-match-audit-2026-09-23.csv'
META = SOURCE.with_suffix('.json')
LEDGER = IDX / 'groni-live-registration-ledger-2026-09-23.json'
CREATED = IDX / 'groni-live-creation-log-2026-09-23.json'
FIELDS_LOG = Path('/tmp/groni-missing-death-fields-live-log.json')
CONFLICT_REASONS = {
    'D/1883/11/1002/12/140': 'Cited as an Armagh John lead. A different Armagh John is documented dying on 27 December 1882; this index alone does not identify Elizabeth Fee’s husband.',
    'D/1865/24/1004/1/82': 'Cited on Glasgow-1390 as one of two death leads. The competing 1866 Magherafelt entry better fits his c.1839 birth; a full return could distinguish the men.',
    'D/1867/183/1022/2/51': 'Cited on Glasgow-1390 as the closer age fit, alongside the competing 1865 Ballymena entry. Neither is assigned as his death from the index alone.',
    'D/1884/99/1009/10/328': 'Cited on Glasgow-1802 as a Cookstown lead. The competing 1896 Omagh entry is closer to his documented 1865 birth; a full return could distinguish the men.',
    'D/1896/212/1025/20/338': 'Cited on Glasgow-1802 as the closer age fit, alongside the competing 1884 Cookstown entry. Neither is assigned as his death from the index alone.',
    'D/1871/209/1025/2/489': 'Cited on Glasgow-3140 as an age-compatible Omagh lead. His Armagh family context and the separate 1882 Armagh index entry leave his death unresolved.',
}

ledger = {r['registration_number']: r for r in json.loads(LEDGER.read_text())['rows'] if r['record_type'] == 'death'}
created = {r['registration']: r['id'] for r in json.loads(CREATED.read_text())['created'] if r['registration'].startswith('D/')}
fields = {r['registration']: r for r in json.loads(FIELDS_LOG.read_text())['saved']}
assert len(fields) == 16
with SOURCE.open(newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    headers = list(reader.fieldnames)
    rows = list(reader)
if 'live_cited_profile_ids' not in headers:
    headers.append('live_cited_profile_ids')

for row in rows:
    reg = row['registration_number']
    if row['forename_as_supplied'].lower().startswith('robert'):
        row['assessment'] = 'deferred_robert'
        row['live_cited_profile_ids'] = ''
        continue
    live = ledger[reg]
    if live['status'] != 'verified' or not live['live_matches']:
        raise ValueError(f'Unverified non-Robert death: {reg}')
    row['live_cited_profile_ids'] = ';'.join(live['live_matches'])
    if reg in created:
        row['assessment'] = 'new_profile_created'
        row['candidate_wikitree_ids'] = created[reg]
    elif reg in fields:
        item = fields[reg]
        row['assessment'] = 'existing_profile'
        row['candidate_wikitree_ids'] = item['id']
        row['reason'] = (f"Best fitting existing profile {item['id']}; the cited index death is entered as "
                         f"{item['death_date']} at {item['death_location']}.")
    elif row['assessment'] in ('possible_profile', 'unnamed_hold'):
        row['assessment'] = 'lead_attached'
    elif row['assessment'] == 'new_profile_created':
        row['assessment'] = 'existing_profile'
    if reg in CONFLICT_REASONS:
        row['assessment'] = 'lead_attached'
        row['reason'] = CONFLICT_REASONS[reg]

with SOURCE.open('w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=headers)
    writer.writeheader()
    writer.writerows(rows)
meta = json.loads(META.read_text())
meta['counts'] = dict(Counter(r['assessment'] for r in rows))
meta['live_verification'] = {'date': '2026-09-23', 'non_robert_death_references_cited': 147,
                             'structured_death_fields_added_after_review': len(fields)}
META.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + '\n')
print(json.dumps(meta['counts'], indent=2))
