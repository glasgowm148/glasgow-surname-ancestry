#!/usr/bin/env python3
"""Read-only audit of existing GRONI birth attachments."""
import csv,json,re,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from wikitree_family_export import post_wikitree
MASTER={r['registration_number']:r for r in csv.DictReader(open('/Users/m/Downloads/glasgow_civil_records_master.csv',newline=''))}
def main():
  patches=json.load(open('/tmp/groni-existing-combined-live-patches.json'))['patches']
  extras=[]
  for f in ['/tmp/groni-supplemental-existing-notes.json','/tmp/groni-six-provisional-birth-attach-notes.json']:
    d=json.load(open(f)); extras += d.get('items',d.get('notes',[]))
  pairs={}
  for p in patches:
    for reg in re.findall(r'\bU/\d{4}/[A-Za-z0-9]+/\d+/\d+/\d+',p.get('wikitext','')): pairs.setdefault((p['profile_id'],reg),p['profile_id'])
  for x in extras:
    if x.get('type','birth')=='birth' and x.get('profile_id') and x.get('registration'): pairs[(x['profile_id'],x['registration'])]=x['profile_id']
  cache={}; flags=[]
  for (wid,reg) in sorted(pairs):
    row=MASTER.get(reg)
    if not row: continue
    try:
      prof=cache.setdefault(wid,post_wikitree({'action':'getProfile','key':wid,'fields':'Id,Name,BirthDate,Bio,Mother,Parents'}).get('profile') or {})
      expected=row['event_date_iso']; actual=str(prof.get('BirthDate') or '')
      bio=prof.get('bio') or ''; dates=re.findall(r'\b(?:\d{1,2}\s+\w+\s+\d{4}|\d{4}-\d{2}-\d{2})\b',bio)
      if actual and actual[:10] not in ('',expected) and actual[:10].replace('-00','')!=expected[:7]: flags.append({'profile_id':wid,'registration':reg,'kind':'structured_birth_date_conflict','index_date':expected,'profile_birth_date':actual})
      if expected[:4] not in bio and not any(expected[:4] in d for d in dates): flags.append({'profile_id':wid,'registration':reg,'kind':'birth_year_absent_from_biography','index_date':expected})
      mother=prof.get('Mother')
      if mother and str(mother).isdigit() and int(mother):
        mid='Unknown-'+str(mother)
        mp=post_wikitree({'action':'getProfile','key':mid,'fields':'Name,LastNameCurrent,LastNameAtBirth'}).get('profile') or {}
        surnames={str(mp.get(k) or '').lower() for k in ('LastNameAtBirth','LastNameCurrent')}
        maiden=row.get('mother_maiden_name','').strip().lower()
        if maiden and surnames and maiden not in surnames: flags.append({'profile_id':wid,'registration':reg,'kind':'mother_maiden_surname_conflict','index_mother_maiden':row['mother_maiden_name'],'known_mother':mp.get('Name'),'known_mother_surnames':sorted(surnames)})
    except Exception as e: flags.append({'profile_id':wid,'registration':reg,'kind':'api_error','error':str(e)})
  out={'source':'/tmp/apply_civil_existing.py birth patches and supplements','pairs':len(pairs),'flags':flags,'summary':{'red_flags':len(flags)}}
  Path('/tmp/groni-birth-attachment-redflags.json').write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n'); print(json.dumps(out['summary']))
if __name__=='__main__': main()
