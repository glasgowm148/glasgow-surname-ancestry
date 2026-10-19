#!/usr/bin/env python3
"""Synchronize GRONI birth profiles and the local public coverage ledger.

The operation is deliberately idempotent: registration numbers are the key,
existing findings and catalogue decisions are preserved, and the browser
logs are retained as source inputs.
"""
from __future__ import annotations
import argparse, csv, json, shutil
from datetime import date
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MASTER = Path(os.environ.get('GLASGOW_CIVIL_RECORDS_CSV', Path.home() / 'Downloads/glasgow_civil_records_master.csv'))
CASES = ROOT/'data/wikitree/research-catalogue-cases.json'
RESEARCH = ROOT/'research'
INDEX = ROOT/'surname-research/indexes'

def read_log(path):
    if not path.exists(): return []
    value = json.loads(path.read_text())
    return value.get('created', [])

def finding(row, item):
    wid, first, reg = item['id'], item.get('first') or row.get('forename',''), item['registration']
    d = row.get('event_date','') or row.get('event_date_iso','')
    district = row.get('district','')
    return f'''<!-- generated: groni-birth-creation-sync -->
# {first} Glasgow ({wid}): civil birth index

Last updated: {date.today().isoformat()}

## Current conclusion

[{first} Glasgow ({wid})](https://www.wikitree.com/wiki/{wid}) was born on {d}; the birth was registered in {district}, Ireland.

## Source findings

- [GRONI civil birth index](https://geni.nidirect.gov.uk/search/birth), `{reg}`. The supplied index records the birth date and registration district; the certificate was not inspected.
'''

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--write', action='store_true')
    ap.add_argument('--master', default=str(MASTER))
    args = ap.parse_args()
    logs = [Path('/tmp/groni_birth_creation_log.json'), Path('/tmp/groni_extra_birth_creation_log.json'), Path('/tmp/groni_four_more_birth_creation_log.json')]
    items = {}
    for path in logs:
        for item in read_log(path):
            if item.get('registration') and item.get('id'):
                items[item['registration']] = item
    with Path(args.master).open(newline='') as f:
        rows = {r['registration_number'].strip(): r for r in csv.DictReader(f)}
    actions=[]
    if args.write:
        INDEX.mkdir(parents=True, exist_ok=True)
        for src, name in zip(logs, ('groni-birth-creation-log-2026-09-23.json','groni-extra-birth-creation-log-2026-09-23.json','groni-four-more-birth-creation-log-2026-09-23.json')):
            if src.exists():
                dst=INDEX/name
                if not dst.exists() or dst.read_bytes()!=src.read_bytes(): shutil.copyfile(src,dst); actions.append('copied '+name)
        # Keep the canonical combined log used by the coverage builder.
        combined={'created': list(sorted(items.values(), key=lambda x:x['registration'])), 'source_logs':[x.name for x in logs], 'updated':date.today().isoformat()}
        (INDEX/'groni-birth-creation-log-2026-09-23.json').write_text(json.dumps(combined,indent=2,ensure_ascii=False)+'\n')
        for reg,item in items.items():
            wid=item['id']; dest=RESEARCH/wid; fp=dest/'findings.md'
            if not fp.exists() and reg in rows:
                dest.mkdir(parents=True, exist_ok=True); fp.write_text(finding(rows[reg],item)); actions.append('created research/'+wid+'/findings.md')
        manifest=json.loads(CASES.read_text()); cases=manifest.setdefault('cases',{})
        for item in items.values():
            wid=item['id']
            if wid not in cases:
                cases[wid]={'status':'pending','profile_id':wid,'reason':'GRONI birth profile created; public metadata capture is pending before catalogue inclusion.'}
        CASES.write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n')
        # The builder consumes the canonical combined log and writes maintained
        # and public row-level ledgers. It is intentionally the only site step.
        import subprocess
        subprocess.run([str(ROOT/'.venv/bin/python'), str(ROOT/'tools/build_groni_civil_coverage.py')], check=True)
    print(json.dumps({'profiles':len(items),'actions':actions,'write':args.write},indent=2))

if __name__=='__main__': main()
