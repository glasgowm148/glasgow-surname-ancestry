"""Integrate reviewed lane conclusions; retain original assessments and event scope."""
import json,re,sys
from collections import Counter
from copy import deepcopy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];BATCH=Path(__file__).resolve().parent;DATE='2026-09-30'
def load(p):return json.loads((ROOT/p).read_text())
def save(p,d):(ROOT/p).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def normalize(lane,items):
 out=[]
 for item in items:
  row=deepcopy(item);row['id']=item.get('id',item.get('queue_id'));row['status']=item.get('new_status',item.get('status'))
  if row['status']=='duplicate_workitem':row['status']='superseded'
  row['assessment']=item.get('identity_assessment',item.get('identity_argument',item.get('argument',item.get('assessment'))))
  row['canonical_groups']=item.get('canonical_groups') or [item.get('canonical_group',item.get('canonical_person_event_group',item.get('canonical_event_group',row['id'])))]
  row['report']='research/queue-resolution-2026-09-30/'+lane+'.json'
  row['exclusions']=item.get('new_exclusions',item.get('concrete_exclusions',item.get('exclusions',[])))
  if row['id']=='draft-1648-scotland-edinburgh-john-glasgow':
   row.update(status='compatible_candidate',profile_ids=item['corrected_subject_candidates'],name='John Gray, Edinburgh apprentice, 1648',assessment='The inspected Gray heading corrects the former Glasgow attribution. John Gray is expressly son of deceased Thomas Gray, maltman and burgess of Glasgow. Gray-42340, Gray-16804, Gray-25428 and Gray-32315 remain compatible candidates, with different strengths. Gray-44891 is a qualified father lead; its identity is unproved. Neither this profile identity nor a Glasgow father-confidence upgrade is proved.')
  assert row['id'] and row['assessment'],row
  out.append(row)
 return out
opr=load('research/queue-resolution-2026-09-30/scottish-opr.json')
older=load('research/queue-resolution-2026-09-30/older-records.json')
irish=load('research/queue-resolution-2026-09-30/irish-collateral.json')
irish_groups={}
for group in irish.get('canonical_groups',[]):
 for qid in group['queue_ids']:irish_groups.setdefault(qid,[]).append(group['canonical_group'])
for item in irish.get('entries',[]):
 item['canonical_groups']=irish_groups.get(item['queue_id'],[item['queue_id']])
 if item['queue_id']=='subject-rasharkin-john-elder-marriages-john-elder':
  item['status']='partly_matched';item['canonical_groups']=['irish:john-elder-1842','irish:john-elder-1886','irish:john-elder-1912']
rows=normalize('scottish-opr',opr['items'])+normalize('older-records',older['rows'])+normalize('irish-collateral',irish.get('items',irish.get('rows',irish.get('entries'))))
assert len({r['id'] for r in rows})==len(rows),'Overlapping lane ownership'
registry=load('research/research-queue-matches.json');baseline=load('research/queue-resolution-2026-09-30/baseline.json')
reviews=baseline.get('reviews',baseline)
required={k for k,v in reviews.items() if v.get('status') in ('compatible_candidate','no_compatible_profile','unnamed_record','partly_matched')}
assert required<={r['id'] for r in rows},required-{r['id'] for r in rows}
for row in rows:
 previous=registry['reviews'][row['id']]
 history=deepcopy(previous.get('review_history',[]))
 if not history:history.append({k:deepcopy(v) for k,v in previous.items() if k!='review_history'})
 previous.update(status=row['status'],profile_ids=list(dict.fromkeys(row['profile_ids'])),assessment=row['assessment'],reviewed_on=DATE,
                 canonical_groups=row['canonical_groups'],source_refs=list(dict.fromkeys(previous.get('source_refs',[])+[row['report']])),
                 review_history=history)
 if row.get('name'):previous['current_name']=row['name']
 if row.get('actual_searches'):previous['searches_performed']=row['actual_searches']
registry['summary']=dict(Counter(r['status'] for r in registry['reviews'].values()));save('research/research-queue-matches.json',registry)
subjects=load('research/latest-findings-subjects/subjects.json');lookup={r['id']:r for r in rows}
labels={'matched':'MATCHED — existing profile','already_linked':'MATCHED — existing profile','partly_matched':'PARTLY MATCHED — separate record identities','compatible_candidate':'HOLD — compatible profile linked','no_compatible_profile':'DRAFT — no compatible profile found','unnamed_record':'UNNAMED — original needed'}
for group in subjects['groups']:
 for person in group['people']:
  qid='subject-'+group['slug']+'-'+person['anchor'];row=lookup.get(qid)
  if not row:continue
  person['status']=labels[row['status']];person['identity_note']=row['assessment']
  reasons={c['id']:c['reason'] for c in person.get('candidates',[])}
  person['candidates']=[dict(id=pid,reason=reasons.get(pid,row['assessment'])) for pid in row['profile_ids']]
  checks=[f'Further source and existing-profile review completed {DATE}; retain compatible candidates unless a concrete conflict excludes them.']
  checks += [e.get('reason',e.get('argument',str(e))) if isinstance(e,dict) else str(e) for e in row['exclusions']]
  person['duplicate_check']=list(dict.fromkeys(person.get('duplicate_check',[])+checks))
  person['canonical_groups']=row['canonical_groups']
  mappings=row.get('record_mappings',row.get('record_matches',[]))
  if mappings:person['record_matches']=deepcopy(mappings)
  else:
   person['record_matches']=[dict(finding_id=f['finding_id'],status=row['status'],profile_ids=row['profile_ids'],assessment=row['assessment']) for f in person['facts']]
  # Retain the original complete biography/source block; replace only review notes.
  person['wikitext']=re.sub(r'== Research Notes ==.*?(?=== Sources ==)',lambda m:'== Research Notes ==\n'+row['assessment']+'\n'+('Candidate profiles: '+', '.join('[['+p+']]' for p in row['profile_ids'])+'.\n' if row['profile_ids'] else '')+person['next_test']+'\n\n',person['wikitext'],flags=re.S)
# Exact reviewed JSON-pointer proposals supersede aggregate generic matching.
def merge_patch(data,patch):
 pointer=patch['pointer'];target=data
 for key in pointer.strip('/').split('/'):
  key=key.replace('~1','/').replace('~0','~');target=target[int(key)] if isinstance(target,list) else target[key]
 if patch.get('subject_name'):assert target['name']==patch['subject_name']
 target.update(deepcopy(patch['merge']))
for patch in opr.get('proposed_source_patches',[]):
 if patch['path']=='research/latest-findings-subjects/subjects.json':merge_patch(subjects,patch)
for patch in irish.get('source_input_patches',[]):
 if patch['target']!='research/latest-findings-subjects/subjects.json':continue
 select=patch['selector'];person=next(p for g in subjects['groups'] if g['slug']==select['group_slug'] for p in g['people'] if p['anchor']==select['person_anchor'])
 changes=deepcopy(patch['replace']);changes.pop('profile_ids',None)
 if 'next_question' in changes:changes['next_test']=changes.pop('next_question')
 person.update(changes)
 if patch.get('paste_ready_full_wikitext'):person['wikitext']=patch['paste_ready_full_wikitext']
# Read maintained complete older drafts after source corrections.
for slug in ('glasgow-mathy-burgesses-1554','norfolk-daniel-1729-1730','old-monkland-thomson-sneddon-1860'):
 group=next(g for g in subjects['groups'] if g['slug']==slug)
 for person in group['people']:
  p=ROOT/'research/latest-findings-subjects'/slug/(person['anchor']+'.md')
  if not p.exists():continue
  text=p.read_text();match=re.search(r'```wikitext\s*\n(.*?)\n```',text,re.S)
  if match:person['wikitext']=match[1]
# Refresh the older record facts and field summaries, not just the handoff prose.
norfolk=next(g for g in subjects['groups'] if g['slug']=='norfolk-daniel-1729-1730')
for person in norfolk['people']:
 for fact in person['facts']:
  if fact['finding_id']=='princess-anne-daniel-glasco-deed-1729':
   fact['finding']='Daniel Glasco, Norfolk planter, conveyed 100 acres to Richard Linton with the consent of Mary, explicitly his wife. The court endorsement says Daniel personally acknowledged the deed on 3 September 1729, establishing survival to that date.'
   fact['qualification']='Inspected original deed endorsement. No father is stated; profile identification and the earlier William title recital remain qualified. Registration alone is not used as a life boundary.'
  elif fact['finding_id']=='norfolk-daneill-glasco-witness-1729-30':
   fact['sources']=[dict(title='McIntosh, Norfolk County will abstracts, printed p. 122 (PDF image p. 122), Richard Johnson will',url=older['source_ledger']['will1730']['url'])]
 if person['anchor']=='daniel-glasco':person['minimum_fields']='Daniel, recorded Glasco/Glascow; male Norfolk planter; born before 1729, exact date and birthplace unknown; alive on 3 September 1729 by personal court acknowledgment. The 26 February 1729/30 will witness is probably the same man; no survival-to-probate inference. Wife Mary explicitly named; parents unknown. Glasgow-3322 remains a candidate.'
 elif person['anchor']=='mary':person['minimum_fields']='Mary; maiden surname unknown; expressly Daniel Glasco’s consenting wife in the 1729 deed. Birth date, birthplace, parents and death unknown. Gammon-934 is a candidate only.'
sneddon=next(g for g in subjects['groups'] if g['slug']=='old-monkland-thomson-sneddon-1860')
for person in sneddon['people']:
 for fact in person['facts']:
  fact['finding']='The 9 November 1860 Old Monkland marriage index records Mary Thomson, 37, and William Sneddon, 45, a widowed collier. Her parents are Robert Thomson and Mary Glasgon Thomson; his parents are Robert Sneddon and Mary Gray Sneddon.'
  fact['qualification']='FamilySearch index inspected after sign-in; original image requires a centre or affiliate library and remains uninspected. These indexes describe one event, not independent marriages. The linked mother, bride and groom profiles remain candidates; no Irish origin, Nancy relationship or profile parentage is proved.'
  fact['sources'] += [dict(title='Indexed father Robert Sneddon',url='https://www.familysearch.org/ark:/61903/1:1:6TLK-6T16'),dict(title='Indexed mother Mary Gray Sneddon',url='https://www.familysearch.org/ark:/61903/1:1:6TLK-6T1F')]
 if person['anchor']=='william-sneddon':person['minimum_fields']='William Sneddon; male, estimated birth about 1814/15 from indexed age 45; birthplace unknown. Widowed collier marrying Mary Thomson on 9 November 1860. Indexed parents Robert Sneddon and Mary Gray; earlier wife and death unknown. Sneddon-710 remains a candidate with an age discrepancy.'
 elif person['anchor']=='mary-thomson':person['minimum_fields']='Mary Thomson; female, estimated birth about 1822/23 from indexed age 37; birthplace unknown; marrying William Sneddon on 9 November 1860. Indexed father Robert Thomson and mother Mary Glasgon Thomson. Thomson-3009 remains a disputed candidate; death unknown.'
 else:person['minimum_fields']='Mary, recorded Glasgon Thomson; female; exact birth, birthplace, parents and death unknown. Named mother of Mary Thomson and wife of Robert Thomson in the daughter’s 1860 index. No Irish birthplace or Nancy relationship is proved. All compatible candidates remain qualified.'
# Newly documented spouse shares the existing family study, with a complete draft.
mathy=next(r for r in older['rows'] if r['id']=='subject-glasgow-mathy-burgesses-1554-david-mathy')
companion=mathy['companion_subject'];group=next(g for g in subjects['groups'] if g['slug']=='glasgow-mathy-burgesses-1554')
source=older['source_ledger']['mathy1551'];fact=dict(finding_id='david-mathy-margaret-androsoune-spouse-1551-20260930',finding='The 3 February 1550/51 barn purchase expressly names David Mathy and Mergaret Androsoune as spouses.',qualification='Inspected printed protocol abstract; original manuscript uninspected. Purchaser/witness continuity and existing-profile identities remain qualified.',sources=[dict(title=source['title']+'; printed p. 27 (PDF p. 60)',url=source['url'])])
primary=next(p for p in group['people'] if p['anchor']=='david-mathy')
primary['facts']=[f for f in primary['facts'] if f['finding_id']!=fact['finding_id']]+[deepcopy(fact)]
primary['minimum_fields']='Recorded name David Mathy; adult purchaser in Glasgow on 3 February 1550/51 and probably the 1554 burgess witness. Age, birthplace, parents and death are unknown. Wife Mergaret Androsoune is expressly named in the purchase.'
newperson=dict(anchor='margaret-androsoune',name=companion['name'],status=labels[companion['status']],identity_note=companion['public_paragraph'],minimum_fields='; '.join(str(k).replace('_',' ').capitalize()+': '+str(v) for k,v in companion['minimum_fields'].items()),facts=[deepcopy(fact)],candidates=[dict(id=pid,reason=companion['public_paragraph']) for pid in companion['profile_ids']],duplicate_check=[companion['search_scope']['method']],next_test='Seek a record connecting Anderson-3241 to this named spouse; preserve the compatible candidate while identity remains qualified.',wikitext=companion['wikitext'],draft_sources=['research/latest-findings-subjects/glasgow-mathy-burgesses-1554/margaret-androsoune.md'],record_matches=[dict(finding_id=fact['finding_id'],status=companion['status'],profile_ids=companion['profile_ids'],assessment=companion['public_paragraph'])])
group['people']=[p for p in group['people'] if p['anchor']!='margaret-androsoune']+[newperson]
qid='subject-glasgow-mathy-burgesses-1554-margaret-androsoune'
registry['reviews'][qid]=dict(id=qid,status=companion['status'],profile_ids=companion['profile_ids'],assessment=companion['public_paragraph'],reviewed_on=DATE,canonical_groups=['mathy-household-1551'],source_refs=['research/queue-resolution-2026-09-30/older-records.json'])
# Group this documented couple without asserting their uncertain profile identities.
registry['reviews']['subject-glasgow-mathy-burgesses-1554-david-mathy']['canonical_groups']=['mathy-household-1551']
registry['summary']=dict(Counter(r['status'] for r in registry['reviews'].values()));save('research/research-queue-matches.json',registry)
path=ROOT/newperson['draft_sources'][0];path.write_text('# HOLD — Mergaret Androsoune\n\n'+newperson['minimum_fields']+'\n\n'+newperson['identity_note']+'\n\n## Complete sourced draft\n\n```wikitext\n'+companion['wikitext']+'```\n')
# Remove residence-as-birthplace wording from public record-field summaries.
for group in subjects['groups']:
 for person in group['people']:
  person['minimum_fields']=re.sub(r'uncertain birth location .*? from the cited own/family event, not a natal-place record','birthplace unknown; cited locations describe recorded events',person['minimum_fields'])
for group in subjects['groups']:
 for person in group['people']:
  for match in person.get('record_matches',[]):match.setdefault('assessment',person['identity_note'])
  for fact in person['facts']:
   fact['sources']=list({source['url']:source for source in fact['sources']}.values())
subjects['reviewed_on']=DATE
save('research/latest-findings-subjects/subjects.json',subjects)
summary=dict(reviewed_unresolved=len(required),lane_rows=len(rows),original_worklist=registry['baseline_items'],total_reviews=len(registry['reviews']),current_match_counts=registry['summary'],father_upgrades=0,confirmed_adult_identity_upgrades=0)
save('research/queue-resolution-2026-09-30/integration-summary.json',summary)
print(json.dumps(summary,indent=2))
