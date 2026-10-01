"""Publish newly inspected record facts, keeping candidate identity qualified."""
import json,re
from pathlib import Path
from copy import deepcopy
ROOT=Path(__file__).resolve().parents[2]
def load(p):return json.loads((ROOT/p).read_text())
def save(p,d):(ROOT/p).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
ledger=load('research/latest-findings.json');byid={f['id']:f for f in ledger['findings']};subjects=load('research/latest-findings-subjects/subjects.json');people={ (g['slug'],p['anchor']):p for g in subjects['groups'] for p in g['people']};new=[]
def public_person(slug,anchor):
 p=people[(slug,anchor)];route='/research/subjects/'+slug+'/#'+anchor
 out=dict(name=p['name'],url=route,role='Sourced record subject; identity remains qualified')
 if p.get('candidates'):
  pid=p['candidates'][0]['id'];local='/people/'+pid.lower()+'.html'
  out.update(id=pid,url=local if (ROOT/'www'/local.lstrip('/')).exists() else 'https://www.wikitree.com/wiki/'+pid,draft_url=route,role='Compatible candidate; identity qualified')
 if p['status'].startswith('MATCHED'):out['role']='Matched existing profile'
 return out

def add(ident,kind,finding,qualification,refs,sources,detail=None,status='qualified',named=None):
 out=dict(id=ident,found_on='2026-09-30',kind=kind,finding=finding,status=status,qualification=qualification,
          people=named if named is not None else [public_person(*ref) for ref in refs],sources=[dict(title=s['title']+('; '+s['page_reference'] if s.get('page_reference') else '')+('; '+s['entry_image_ref'] if s.get('entry_image_ref') else ''),url=s['url']) for s in sources],
          detail_url=detail or '/research/subjects/'+refs[0][0]+'/#'+refs[0][1],provenance=['research/queue-resolution-2026-09-30/'])
 assert out['people'] and out['sources'];new.append(out)
# Keep old discoveries dated as originally recorded; refresh their current reading and source basis.
for (slug,anchor),p in people.items():
 for fact in p['facts']:
  existing=byid.get(fact['finding_id'])
  if not existing:continue
  # Facts are shared by several people, so one reviewed wording is enough.
  existing.update(finding=fact['finding'],qualification=fact.get('qualification',existing.get('qualification','')))
  if fact.get('sources'):existing['sources']=[dict(title=s['title'],url=s['url']) for s in fact['sources']]
  matches={m['finding_id']:m for m in p.get('record_matches',[])};match=matches.get(fact['finding_id'])
  route='/research/subjects/'+slug+'/#'+anchor
  for named in existing.get('people',[]):
   if named.get('draft_url',named.get('url'))!=route:continue
   ids=match.get('profile_ids',[]) if match else [c['id'] for c in p.get('candidates',[])]
   named.update(public_person(slug,anchor))
   if not ids:named.pop('id',None);named.pop('draft_url',None);named['url']=route
   else:
    pid=ids[0];local='/people/'+pid.lower()+'.html';named.update(id=pid,url=local if (ROOT/'www'/local.lstrip('/')).exists() else 'https://www.wikitree.com/wiki/'+pid,draft_url=route,role='Matched existing profile' if match and match['status'] in ('matched','already_linked') else 'Compatible candidate; identity qualified')
  if match:existing.setdefault('profile_match_reviews',{})[anchor]=dict(reviewed_on='2026-09-30',status=match['status'],profile_ids=ids,assessment=match.get('assessment',p['identity_note']))
# The former John Glasgow assertion is superseded, without rewriting discovery history.
old=byid['john-edinburgh-apprentice-thomas-1648']
old.update(finding='The 12 January 1648 apprentice was John Gray, son of deceased Thomas Gray, maltman and burgess of Glasgow. The previous John Glasgow reading is superseded by the inspected Gray heading.',
           status='qualified',qualification='Surname attribution corrected on 30 September 2026 after inspection of printed p. 75 (PDF p. 86). Gray-42340 is only a compatible identity. No Glasgow father relationship is proved.',
           people=[dict(name='John Gray',url='/people/record-john-glasgow-edinburgh-1648.html',role='Corrected record subject; stable former URL retained')],
           sources=[dict(title='Grant, Edinburgh apprenticeship register, printed p. 75 (PDF p. 86), Gray heading',url='https://archive.org/download/scottishrecordso28scotuoft/page/n86.jpg')])
old.pop('relationship_changes',None)
new.append(dict(id='john-gray-apprentice-surname-correction-20260930',found_on='2026-09-30',kind='record',
 finding='The printed Gray heading corrects the former John Glasgow attribution of the 1648 apprenticeship. The entry names John Gray’s deceased father Thomas Gray, maltman and burgess of Glasgow, and master William Blackwood.',
 status='confirmed',qualification='The original manuscript was not inspected. The printed record establishes the named father, while identification with Gray-42340 remains qualified. The former Glasgow profile candidates and Thomas Glasgow father hypothesis are withdrawn.',
 people=[dict(name='John Gray',id='Gray-42340',url='https://www.wikitree.com/wiki/Gray-42340',draft_url='/people/record-john-glasgow-edinburgh-1648.html',role='Compatible candidate; corrected record surname')],
 sources=deepcopy(old['sources']),detail_url='/people/record-john-glasgow-edinburgh-1648.html',provenance=['research/queue-resolution-2026-09-30/older-records.json']))
# Six newly read trades, bundled with their printed marriage-date clarification.
opr=load('research/queue-resolution-2026-09-30/scottish-opr.json')
for group in opr['groups']:
 facts=[f for f in group['new_concrete_findings'] if f.get('field')=='recorded_spouse_occupation']
 if not facts:continue
 fact=facts[0];fids=set(group['finding_ids']);refs=[key for key,p in people.items() if any(f['finding_id'] in fids for f in p['facts'])]
 detail=None;named=None
 if not refs:
  detail='/branches/scottish-families/#opr-marriage-identity-'+group['queue_ids'][0].removeprefix('opr-')
  def candidate(name,ids):
   pid=ids[0] if ids else None;out=dict(name=name,url=detail,role='Compatible candidate; identity qualified')
   if pid:out.update(id=pid,url='https://www.wikitree.com/wiki/'+pid,draft_url=detail)
   return out
  named=[candidate('Eupham Glasgow',group['primary_profile_ids']),candidate('Alexander Hutcheson',group['spouse_profile_ids'])]
 add(fact['id'],'biographical',fact['fact']+' The inspected edition presents this as a marriage date.',
     'Visually inspected historical printed transcription and editorial preface; original parish manuscript uninspected. Adult profile identifications remain qualified and each event is kept separate.',refs,group['sources'][1:],status='confirmed',detail=detail,named=named)
 for extra in group['new_concrete_findings']:
  if extra.get('id')=='alexander-hutcheson-tailor-burgess-1670':
   add(extra['id'],'biographical',extra['fact'], 'The identification with Eupham Glasgow’s 1671 groom is probable. Alexander Thomsone is the apprenticeship master, not a father; no parentage upgrade is claimed.',refs,[group['sources'][3]],detail=detail,named=named[-1:] if named else None)
# New older-record facts.
older=load('research/queue-resolution-2026-09-30/older-records.json');sources=older['source_ledger']
add('david-mathy-margaret-androsoune-spouse-1551-20260930','relationship','A property entry dated 3 February 1550/51 names David Mathy and Mergaret Androsoune as spouses, purchasing a barn at Powdrait. David Mathy also appears as a witness on 4 July 1554.',
    'The named couple is explicit in the inspected printed abstract. Identity of the purchaser with the 1554 Glasgow burgess is probable; Matthew-330 and Anderson-3241 remain weak compatible profile candidates.',
    [('glasgow-mathy-burgesses-1554','david-mathy'),('glasgow-mathy-burgesses-1554','margaret-androsoune')],[sources['mathy1551'],sources['mathy1554b']])
add('norfolk-daniel-court-appearance-1729-20260930','vital','Daniel Glasco personally acknowledged his deed in court on 3 September 1729, establishing that he was alive that day. A 1730 will witness abstract names Daneill Glasco with Richard Linton and John Moy.',
    'The deed’s personal appearance, rather than registration alone, supplies the life boundary. The witness network supports comparison, but identity with Glasgow-3322 and continuity with the 1693 Daniel/Mary couple remain qualified. McIntosh’s will abstract is printed p. 122, not p. 112.',
    [('norfolk-daniel-1729-1730','daniel-glasco'),('norfolk-daniel-1729-1730','richard-linton')],[sources['deed1729'],sources['will1730']])
add('sneddon-1860-indexed-groom-parents-20260930','relationship','The 9 November 1860 Old Monkland marriage index names William Sneddon’s parents as Robert Sneddon and Mary Gray Sneddon. William is indexed as a 45-year-old widowed collier.',
    'The FamilySearch index was inspected after sign-in; its original image requires a FamilySearch centre or affiliate library and was not inspected. Sneddon-710 remains a candidate with an age discrepancy. No existing-profile father-confidence upgrade is claimed.',
    [('old-monkland-thomson-sneddon-1860','william-sneddon')],[dict(title='FamilySearch Scotland marriages index, William Sneddon, 1860',url='https://www.familysearch.org/ark:/61903/1:1:6TLK-6T18'),dict(title='Indexed father Robert Sneddon',url='https://www.familysearch.org/ark:/61903/1:1:6TLK-6T16'),dict(title='Indexed mother Mary Gray Sneddon',url='https://www.familysearch.org/ark:/61903/1:1:6TLK-6T1F')])
# Original Irish census and civil entries, source corrections and household identities.
irish=load('research/queue-resolution-2026-09-30/irish-collateral.json')
for f in irish['new_latest_findings']:
 kind='vital' if 'date-correction' in f['id'] else 'relationship' if any(word in f['id'] for word in ('children','calderwood','family','sarah')) else 'record'
 add(f['id'],kind,f['finding'],f['qualification'],f['subject_refs'],f['sources'])
for f in new:
 if f['id'] in byid:byid[f['id']].update(f)
 else:ledger['findings'].append(f);byid[f['id']]=f
save('research/latest-findings.json',ledger)
save('research/queue-resolution-2026-09-30/new-finding-ids.json',[f['id'] for f in new])
print(json.dumps({'new_batch_entries':len(new),'latest_findings_total':len(ledger['findings']),'ids':[f['id'] for f in new]},indent=2))
