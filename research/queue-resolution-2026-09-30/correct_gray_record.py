"""Reconcile one verified surname-heading error; preserve public IDs/bookmarks."""
import csv, io, json, sys
from copy import deepcopy
from pathlib import Path
from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
from catalogue_machine_data import resolver_candidates, _normal_match_text
ID='record-john-glasgow-edinburgh-1648'; RID='ae5d63e3be969a94'; MAP='john-glasgow-edinburgh-1648'
SOURCE='https://archive.org/download/scottishrecordso28scotuoft/page/n86.jpg'
TITLE='Register of Apprentices of the City of Edinburgh, 1583–1666, printed p. 75 (PDF p. 86): John Gray, 12 January 1648'
ASSOCIATION='John Gray, son of late Thomas Gray, maltman and burgess of Glasgow, apprenticed to William Blackwood, merchant, 12 January 1648'
NOTE='The entry is under the printed Gray heading, not Glasgow. Thomas G. is the deceased father, a maltman and burgess of Glasgow. John’s age and residence are unrecorded. The former Glasgow attribution is corrected on 30 September 2026; Gray-42340 is a compatible candidate, not a confirmed identity.'
STATUS='Printed p. 75 visually inspected on 30 September 2026 (Internet Archive leaf n86/PDF p. 86): the bold heading is Gray. The original manuscript apprenticeship register was not inspected. Earlier Glasgow attribution superseded.'
changes={}
BACKUP=ROOT/'research/queue-resolution-2026-09-30/gray-backup'
def put(path,data):
 p=ROOT/path
 encoded=(json.dumps(data,ensure_ascii=False,indent=2)+'\n').encode() if not isinstance(data,bytes) else data
 if p.exists() and p.read_bytes()==encoded:return
 if p.exists():
  b=BACKUP/path;b.parent.mkdir(parents=True,exist_ok=True)
  if not b.exists():b.write_bytes(p.read_bytes())
 p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(encoded);changes[str(path)]=len(encoded)
def txt(s):
 return s.replace('John Glasgow','John Gray').replace('printed Glasgow heading','printed Gray heading').replace('explicit Glasgow heading','explicit Gray heading')
def identity(d):
 return any(d.get(k) in (ID,RID,MAP) for k in ('id','catalogue_id','selection_id','slug','record_id','supplement_id','map_key','person_id')) or d.get('reference')==RID

def rewrite(value,inside=False):
 if isinstance(value,dict):
  active=inside or identity(value)
  # Research prose includes the dated superseded surname and must retain it.
  # The normal targeted sync reloads this from the maintained findings file.
  out={k:deepcopy(v) if k=='research_findings' else rewrite(v,active) for k,v in value.items()}
  if active:
   if 'profile_work_candidate_count' in out:out['profile_work_candidate_count']=4
   if 'uncertain_identity' in out:out['uncertain_identity']=True
   if out.get('source_title'):out.update(source_title=TITLE,source_url=SOURCE,source_status=STATUS)
   if 'association' in out:out['association']=ASSOCIATION
   if 'note' in out and (out.get('record_id')==RID or 'source_title' in out):out['note']=NOTE
   if out.get('reference')==RID:out.update(title=TITLE,url=SOURCE)
   if out.get('record_type','').startswith('Apprenticeship entry for John'):out.update(record_type=ASSOCIATION,assertion=NOTE)
   if out.get('type')=='recorded_occurrence':out.update(claim='John Gray was recorded in the Edinburgh apprenticeship register on 12 January 1648.',notes=ASSOCIATION)
  return out
 if isinstance(value,list):
  active=inside or ID in [v for v in value if isinstance(v,str)] or RID in [v for v in value if isinstance(v,str)]
  return [rewrite(v,active) for v in value]
 return txt(value) if inside and isinstance(value,str) else value

# Durable source inputs.
p=Path('www/map/data/records.csv');s=(ROOT/p).read_text(encoding='utf-8-sig');reader=csv.DictReader(io.StringIO(s));fields=reader.fieldnames;rows=list(reader)
found=[r for r in rows if r.get('supplement_id')==MAP];assert len(found)==1
r=found[0];r.update(person='John Gray',association=ASSOCIATION,note=NOTE,source_title=TITLE,source_url=SOURCE,source_status=STATUS)
out=io.StringIO();w=csv.DictWriter(out,fieldnames=fields);w.writeheader();w.writerows(rows);put(p,out.getvalue().encode('utf-8-sig'))
p=Path('data/wikitree/research-catalogue-cases.json');d=json.loads((ROOT/p).read_text());case=next(c for c in d['cases'].values() if c.get('profile_id')==ID);case['record']=deepcopy(r);case['reason']='The inspected Gray heading supersedes the earlier Glasgow attribution. Keep the stable record dossier and its sourced father statement visible; Gray-42340 is only a compatible profile candidate.';put(p,d)
p=Path('data/wikitree/catalogue-profile-audit.json');d=json.loads((ROOT/p).read_text());a=d['entries'][ID];a.update(name='John Gray',identity_note=NOTE,recommended_action='hold',confirmed_profile_id='',search_terms=['John Gray','John Grey'],reviewed_at='2026-09-30',candidates=[{'profile_id':pid,'name':'John Gray','url':'https://www.wikitree.com/wiki/'+pid,'reason':'Compatible candidate of differing strength; the inspected case findings retain the chronology, locality and father qualifications.'} for pid in ('Gray-42340','Gray-16804','Gray-25428','Gray-32315')]);put(p,d)

# Generated data: limit all mutations to this exact subject/record.
for p in sorted((ROOT/'www').rglob('*.json')):
 if 'resolve' in p.parts:continue
 s=p.read_text()
 if ID not in s and RID not in s:continue
 original=json.loads(s);updated=rewrite(original)
 if p.name=='registry-packed.json':
  fields=updated['fields']
  for row in updated['rows']:
   if ID in row:
    record=dict(zip(fields,row));record=rewrite(record)
    row[:]=[record.get(k) for k in fields]
 if str(p.relative_to(ROOT))=='www/assets/v3/search-people.json':
  for row in updated:
   if row[0]==ID:row[:]=[ID,'John Gray','/people/'+ID+'.html','Birth unrecorded – Death unrecorded · '+ID,'John Gray '+ID+' Edinburgh Scotland 1648 apprenticeship']
 if str(p.relative_to(ROOT))=='www/assets/v3/people-quick.json':
  for row in updated:
   if row[0]==ID:row[:]=[ID,'John Gray','Birth unrecorded – Death unrecorded','Edinburgh, Scotland',ID]
 if updated!=original:put(p.relative_to(ROOT),updated)
# JS mirrors with exact JSON assignment wrappers.
for rel in ('www/data/people-index.js','www/data/compare-index.js'):
 p=ROOT/rel;s=p.read_text();prefix,body=s.split('=',1);d,end=json.JSONDecoder().raw_decode(body);tail=body[end:];updated=rewrite(d)
 if updated!=d:put(Path(rel),(prefix+'='+json.dumps(updated,ensure_ascii=False,separators=(',',':'))+tail).encode())
# Remove the misattributed person from Glasgow name resolver responses.
for p in sorted((ROOT/'www/data/resolve').glob('*.json')):
 s=p.read_text()
 if ID not in s:continue
 d=json.loads(s);original=deepcopy(d);d['candidates']=[c for c in d['candidates'] if c.get('id')!=ID];d['candidate_count']=len(d['candidates'])
 if d!=original:put(p.relative_to(ROOT),d)
index=json.loads((ROOT/'www/data/people-index.json').read_text())
for saved in sorted((BACKUP/'www/data/resolve').glob('*.json')):
 p=ROOT/'www/data/resolve'/saved.name
 if not p.exists():continue
 d=json.loads(p.read_text())
 d['candidate_count']=sum(_normal_match_text(row['name'])==_normal_match_text(d['query']['name']) for row in index)
 put(p.relative_to(ROOT),d)
put(Path('www/data/resolve/john-gray.json'),dict(schema_version='1.0',query={'name':'John Gray'},candidate_count=sum(_normal_match_text(row['name'])==_normal_match_text('John Gray') for row in index),candidates=resolver_candidates(index,'John Gray'),scoring='Name candidates only; not a confirmed genealogical identity.'))
# Exact linked rows on generated readers. The dossier itself is refreshed below.
for p in sorted((ROOT/'www').rglob('*.html')):
 if p.name=='index.html' and p.parent.name=='latest-findings':continue
 if p==ROOT/f'www/people/{ID}.html':continue
 s=p.read_text()
 if ID not in s:continue
 soup=BeautifulSoup(s,'html.parser');changed=False
 for a in soup.select('a[href]'):
  if ID+'.html' in a['href'] and 'John Glasgow' in a.get_text():
   for node in list(a.find_all(string=True)):
    if 'John Glasgow' in node:node.replace_with(txt(str(node)));changed=True
   tr=a.find_parent('tr')
   if tr:
    for node in list(tr.find_all(string=True)):
     if 'John Glasgow' in node or 'printed Glasgow heading' in node:node.replace_with(txt(str(node)))
 if changed:put(p.relative_to(ROOT),str(soup).encode())
print(json.dumps({'changed':len(changes),'paths':list(changes)},indent=2))
