#!/usr/bin/env python3
"""Create a minimal historical GEDCOM working copy from a validated local export.

Original trees remain untouched. An explicit birth <=1850 and death <=1900
are required. Notes, media, sources, submitters, addresses and restricted
records are omitted. This is a tree lead, not primary evidence.
"""
import hashlib
import json
from pathlib import Path
import re

runtime = Path.home() / 'Library/Application Support/genealogy-tools'
baseline = json.loads((runtime / 'tree-baseline.json').read_text())
source = max((x for x in baseline if x['kind'] == 'gedcom'), key=lambda x: x['size'])
raw = Path(source['path']).read_bytes()
if hashlib.sha256(raw).hexdigest() != source['sha256']:
    raise SystemExit('Source changed since reviewed header/hash inventory')
text = raw.decode('utf-8-sig', errors='strict')
blocks = re.split(r'(?m)(?=^0 )', text)
people = {}
family_blocks = []
for block in blocks:
    lines = block.strip().splitlines()
    if not lines:
        continue
    match = re.fullmatch(r'0 (@[^@]+@) INDI', lines[0])
    if re.fullmatch(r'0 @[^@]+@ FAM', lines[0]):
        family_blocks.append(lines)
    if not match or re.search(r'(?m)^\d+ (RESN|_PRIV|_LIVING)\b', block):
        continue
    dates = {}
    safe = [lines[0]]
    event = None
    for line in lines[1:]:
        item = re.fullmatch(r'(\d+) (\S+)(?: (.*))?', line)
        if not item:
            continue
        level, tag, value = int(item[1]), item[2], item[3] or ''
        if level == 1:
            event = tag
            if tag in ('NAME', 'SEX', 'BIRT', 'DEAT', 'FAMC', 'FAMS'):
                safe.append(line)
        elif level == 2 and event in ('BIRT', 'DEAT') and tag in ('DATE', 'PLAC'):
            safe.append(line)
            if tag == 'DATE':
                years = re.findall(r'(?<!\d)(1\d{3})(?!\d)', value)
                if years and not re.search(r'\b(?:AFT|BEF|ABT|EST|CAL)\b', value):
                    dates[event] = max(map(int, years))
    if dates.get('BIRT', 9999) <= 1850 and dates.get('DEAT', 9999) <= 1900:
        people[match[1]] = safe
families = {}
for lines in family_blocks:
    members = [line for line in lines[1:] if re.fullmatch(r'1 (HUSB|WIFE|CHIL) @[^@]+@', line) and line.split()[-1] in people]
    if len(members) >= 2:
        families[lines[0].split()[1]] = [lines[0], *members]
for lines in people.values():
    lines[:] = [line for line in lines if not re.match(r'1 FAM[CS] ', line) or line.split()[-1] in families]
output = ['0 HEAD', '1 SOUR HistoricalWorkingSubset', '1 GEDC', '2 VERS 5.5.1', '2 FORM LINEAGE-LINKED', '1 CHAR UTF-8']
for lines in [*people.values(), *families.values()]:
    output.extend(lines)
output.append('0 TRLR')
directory = runtime / 'corpus/tree'
directory.mkdir(parents=True, exist_ok=True)
target = directory / 'historical.ged'
if target.exists():
    target.chmod(0o600)
target.write_text('\n'.join(output) + '\n')
target.chmod(0o444)
metadata = {'source': source['path'], 'source_sha256': source['sha256'],
            'copy_sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
            'people': len(people), 'families': len(families),
            'status': 'Legacy tree lead; relationships not independently verified',
            'privacy': 'Explicit historical dates; minimal fields; restricted records omitted'}
manifest = runtime / 'historical-tree-provenance.json'
manifest.write_text(json.dumps(metadata, indent=2) + '\n')
manifest.chmod(0o600)
print(json.dumps({k: metadata[k] for k in ('people', 'families', 'copy_sha256', 'status')}))
