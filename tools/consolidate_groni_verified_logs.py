#!/usr/bin/env python3
"""Consolidate read-only GRONI verification into live-log inputs for the site builder.

This writes no WikiTree data and must run only after verify_groni_live_ledger.py.
"""
import argparse, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IDX = ROOT / 'surname-research/indexes'
CREATION_SOURCES = (
    IDX/'groni-created-profiles-2026-09-23.json',
    IDX/'groni-birth-creation-log-2026-09-23.json',
    IDX/'groni-extra-birth-creation-log-2026-09-23.json',
    IDX/'groni-four-more-birth-creation-log-2026-09-23.json',
    Path('/tmp/groni_marriage_creation_log.json'),
    Path('/tmp/groni_death_final_creation_log.json'),
    Path('/tmp/groni_james_1869_creation_log.json'),
)

def entries(path):
    try: data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError): return []
    out = []
    for key in ('created', 'saved', 'verified'):
        if isinstance(data.get(key), list): out.extend(data[key])
    return out

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--ledger', default=str(IDX/'groni-live-registration-ledger-2026-09-23.json')); a = ap.parse_args()
    ledger = json.loads(Path(a.ledger).read_text()); created = {}
    for path in CREATION_SOURCES:
        for x in entries(path):
            reg = x.get('registration') or x.get('registration_number'); wid = x.get('id') or x.get('wikitree_id')
            if reg and wid: created.setdefault(reg, wid)
    logs = {'created': [], 'attached': []}
    for row in ledger.get('rows', []):
        if row.get('status') != 'verified': continue
        reg = row.get('registration_number','').strip(); matches = row.get('live_matches') or []
        if not matches: continue
        wid = created.get(reg) if created.get(reg) in matches else matches[0]
        item = {'registration': reg, 'id': wid, 'source_id': reg, 'verified_live': True, 'verification': 'verify_groni_live_ledger.py'}
        (logs['created'] if created.get(reg) == wid else logs['attached']).append(item)
    for key, filename, action in (('created','groni-live-creation-log-2026-09-23.json','verified_live_creation'), ('attached','groni-live-edit-log-2026-09-23.json','verified_live_attachment')):
        rows = [{**x, 'action': action} for x in logs[key]]
        (IDX/filename).write_text(json.dumps({'generated':'2026-09-23','source_ledger':str(Path(a.ledger).resolve()),'verified_live':True,key:rows}, indent=2, ensure_ascii=False)+'\n')
    print(json.dumps({'verified_rows': sum(len(v) for v in logs.values()), 'created':len(logs['created']), 'attached':len(logs['attached'])}, indent=2))

if __name__ == '__main__': main()
