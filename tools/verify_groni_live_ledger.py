#!/usr/bin/env python3
"""Read-only GRONI crosswalk ledger and live WikiTree biography check.

Produces one JSON row per civil-registration CSV row. Robert rows are marked
excluded because that workstream is maintained separately. No WikiTree writes.
"""
from __future__ import annotations
import argparse, csv, json, os, re, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from wikitree_family_export import post_wikitree
CSV = ROOT / 'surname-research/indexes/groni-civil-registration-coverage-2026-09-23.csv'
IDX = ROOT / 'surname-research/indexes'
REF = re.compile(r'(?<![A-Z0-9])([UMD]/\d{4}/[A-Z0-9]+(?:/\d+){3,})(?![A-Z0-9])', re.I)
WID = re.compile(r'\b(?:[A-Za-z]+-\d+|Unknown-\d+)\b')

def load_ids():
    out = {}
    def add(reg, value):
        if not reg or not value: return
        vals = value if isinstance(value, list) else re.split(r'[;,\s]+', str(value))
        for v in vals:
            if WID.fullmatch(v): out.setdefault(reg, set()).add(v)
    for r in csv.DictReader(CSV.open(newline='')):
        add(r['registration_number'], r.get('profile_id_when_known'))
    paths = list(IDX.glob('*groni*.json'))
    paths += [p for p in Path('/tmp').rglob('*.json') if re.search(r'(groni|creation|decision|existing.?edit)', p.name, re.I)]
    paths += list(Path('/tmp/groni-death-live-patches').glob('*.json'))
    for path in paths:
        try: data = json.loads(path.read_text())
        except Exception: continue
        def walk(x, reg=None):
            if isinstance(x, dict):
                nr = x.get('registration_number') or x.get('registration') or reg
                for k in ('profile_id_when_known','best_glasgow_profile_id','proposed_wikitree_id','id','profile_id','profile','target','wikitree_id','candidate_wikitree_ids','possible_spouse_id'):
                    add(nr, x.get(k))
                for key in ('registration_numbers','registrations'):
                    for source_id in x.get(key,[]) if isinstance(x.get(key),list) else []:
                        add(source_id,x.get('profile_id') or x.get('profile') or x.get('target') or x.get('id'))
                for v in x.values(): walk(v, nr)
            elif isinstance(x, list):
                for v in x: walk(v, reg)
        walk(data)
    return out

def get_profiles(wids, delay):
    cache = {}
    for start in range(0, len(wids), 25):
        batch = wids[start:start+25]
        try:
            data = post_wikitree({'action':'getPeople','keys':','.join(batch),'fields':'Name,Bio','bioFormat':'wiki'})
            people = data.get('people') or {}
            for p in people.values():
                if isinstance(p, dict) and p.get('Name'):
                    name = p['Name']; cache[name] = (name, p.get('Bio') or p.get('bio') or '')
            for wid in batch:
                if wid not in cache: cache[wid] = (wid, '', 'not returned by getPeople')
        except Exception as e:
            for wid in batch: cache[wid] = (wid, '', str(e))
        if delay: time.sleep(delay)
    return cache

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--output', default=str(IDX/'groni-live-registration-ledger-2026-09-23.json')); ap.add_argument('--delay', type=float, default=1.0); ap.add_argument('--app-id', default=os.getenv('WIKITREE_APP_ID',''))
    a = ap.parse_args(); rows = list(csv.DictReader(CSV.open(newline=''))); ids = load_ids(); ledger=[]
    all_ids=sorted({wid for r in rows if r.get('forename','').strip().lower()!='robert' for wid in ids.get(r['registration_number'],set())})
    cache=get_profiles(all_ids,a.delay)
    for r in rows:
        reg=r['registration_number']; excluded=r.get('forename','').strip().lower()=='robert'
        if excluded: ledger.append({**r,'mapped_ids':[],'status':'excluded_robert'}); continue
        mapped=sorted(ids.get(reg,set()))
        item={**r,'mapped_ids':mapped,'status':'unmapped' if not mapped else 'not_checked','live_matches':[],'live_errors':[]}
        for wid in mapped:
            got=cache[wid]; name,bio=got[0],got[1]
            if len(got)>2: item['live_errors'].append({'id':wid,'error':got[2]}); continue
            refs=set(x.upper() for x in REF.findall(bio))
            if reg.upper() in refs: item['live_matches'].append(name)
        if item['live_matches']: item['status']='verified'
        elif mapped and item['live_errors']: item['status']='api_error'
        elif mapped: item['status']='missing_live_reference'
        ledger.append(item)
    result={'source':str(CSV.relative_to(ROOT)),'generated':'2026-09-23','read_only':True,'rows':ledger,'summary':{}}
    from collections import Counter
    result['summary']=dict(Counter(x['status'] for x in ledger)); result['summary']['unique_profiles_checked']=len(cache)
    Path(a.output).write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({'summary':result['summary'],'unmapped':[x['registration_number'] for x in ledger if x['status']=='unmapped']},indent=2))
if __name__=='__main__': main()
