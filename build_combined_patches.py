import json, concurrent.futures, re
from pathlib import Path
from src.wikitree_family_export import post_wikitree

b=json.loads(Path('/tmp/groni-existing-birth-patches.json').read_text())['patches']
m=json.loads(Path('/tmp/groni-existing-marriage-patches.json').read_text())
by={}
for x in b: by.setdefault(x['id'],{'birth':[],'marriage':[]})['birth'].append(x)
for x in m: by.setdefault(x['profile_id'],{'birth':[],'marriage':[]})['marriage'].append(x)
ids=list(by)
def get(i):
    try:return i,post_wikitree({'action':'getProfile','key':i,'fields':'Id,Name,BirthDate,BirthLocation,Bio'})['profile']
    except Exception as e:return i,{'error':str(e)}
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex: profiles=dict(ex.map(get,ids))
out=[]; conflicts=[]
for i in ids:
 p=profiles.get(i,{})
 if 'error' in p: conflicts.append({'profile_id':i,'reason':p['error']}); continue
 bio=p.get('bio','') or ''
 notes=[]
 for x in by[i]['birth']:
  if x['registration_number'] not in bio: notes.append(x['text'])
 for x in by[i]['marriage']:
  if x['registration_number'] not in bio: notes.append(x['append_text'])
 if not notes: continue
 # Insert notes immediately before Sources, keeping all existing text intact.
 ins='\n'.join(notes)+'\n'
 if re.search(r'^==\s*Sources\s*==',bio,re.M): new=re.sub(r'(?m)^==\s*Sources\s*==',ins+'== Sources ==',bio,count=1)
 else: new=bio.rstrip()+'\n\n'+ins
 patch={'profile_id':i,'numeric_id':p.get('Id'),'name':p.get('Name'), 'wikitext':new,
        'birth_notes':len(by[i]['birth']),'marriage_notes':len(by[i]['marriage']),
        'manager_status':'not_checked','structured_birth_date':p.get('BirthDate',''),'structured_birth_location':p.get('BirthLocation','')}
 # Only request structured birth updates for blank or year-only values, and never overwrite a conflicting date.
 dates={x['date'] for x in by[i]['birth']}
 if len(dates)==1 and dates:
  d=next(iter(dates)); cur=p.get('BirthDate','') or ''
  if not cur or (len(cur)==4 and d.startswith(cur)):
   patch['set_birth_date']=d
  elif cur!=d: conflicts.append({'profile_id':i,'reason':'birth-date-conflict','current':cur,'indexed':sorted(dates)})
 out.append(patch)
result={'patches':out,'conflicts':conflicts,'summary':{'profiles_considered':len(ids),'profiles_with_edits':len(out),'birth_note_rows':sum(len(v['birth']) for v in by.values()),'marriage_note_rows':sum(len(v['marriage']) for v in by.values()),'conflicts':len(conflicts)}}
Path('/tmp/groni-existing-combined-live-patches.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result['summary']))
