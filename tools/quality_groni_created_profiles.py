#!/usr/bin/env python3
"""Read-only quality sweep for profiles named by GRONI creation logs."""
import json, re, time
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from wikitree_family_export import post_wikitree

ROOT=Path(__file__).resolve().parents[1]; IDX=ROOT/'surname-research/indexes'; OUT=Path('/tmp/groni-created-profile-quality-flags.json')
FILES=('groni-created-profiles-2026-09-23.json','groni-birth-creation-log-2026-09-23.json','groni-extra-birth-creation-log-2026-09-23.json','groni-four-more-birth-creation-log-2026-09-23.json')
def ids():
 out=set()
 def walk(x):
  if isinstance(x,dict):
   for k in ('id','profile','wikitree_id'):
    v=x.get(k)
    if isinstance(v,str) and re.fullmatch(r'[A-Za-z]+-\d+',v): out.add(v)
   for v in x.values(): walk(v)
  elif isinstance(x,list):
   for v in x: walk(v)
 for f in FILES: walk(json.loads((IDX/f).read_text()))
 return sorted(out)
def main():
 wids=ids(); people={}
 for i in range(0,len(wids),25):
  data=post_wikitree({'action':'getPeople','keys':','.join(wids[i:i+25]),'fields':'Name,Bio,BirthDate,DeathDate,BirthLocation,DeathLocation','bioFormat':'wiki'})
  people.update({p.get('Name'):p for p in (data.get('people') or {}).values() if p.get('Name')}); time.sleep(1)
 flags=[]
 for wid in wids:
  p=people.get(wid) or {}; bio=p.get('Bio') or p.get('bio') or ''; low=bio.lower(); found=[]
  for label,pat in [('provisional boilerplate',r'provisionally'),('index does not establish',r'index does not establish'),('possible match boilerplate',r'possible match') ,('male maiden-name disclaimer',r'(?:male|man)[^\n]{0,100}maiden name|maiden name[^\n]{0,100}(?:male|man)')]:
   if re.search(pat,low): found.append(label)
  for label,key in [('missing birth location','BirthLocation'),('missing death location','DeathLocation')]:
   if not p.get(key): found.append(label)
  if re.search(r'\b(?:19|18)\d{2}-\d{2}-\d{2}\b',bio): found.append('ISO date in biography')
  if found: flags.append({'id':wid,'name':p.get('Name',wid),'flags':found,'birth':p.get('BirthDate',''),'death':p.get('DeathDate',''),'birth_location':p.get('BirthLocation',''),'death_location':p.get('DeathLocation','')})
 OUT.write_text(json.dumps({'read_only':True,'profile_count':len(wids),'returned_count':len(people),'flag_count':len(flags),'flags':flags},indent=2,ensure_ascii=False)+'\n'); print(json.dumps({'profile_count':len(wids),'returned_count':len(people),'flag_count':len(flags),'ids':[x['id'] for x in flags]},indent=2))
if __name__=='__main__': main()
