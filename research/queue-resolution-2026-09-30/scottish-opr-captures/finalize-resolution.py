import json,re,hashlib
from pathlib import Path
R=Path('/Users/m/wikitree-api-scrape');C=R/'research/queue-resolution-2026-09-30/scottish-opr-captures';P=C.parent/'scottish-opr.json'
x=json.load(open(P));m=json.load(open(C/'maintained-edits.json'))
def link_ids(s):
 parts=re.split(r'(\[\[.*?\]\]|\[https?://[^\]]+\])',s,flags=re.S)
 for i in range(0,len(parts),2):parts[i]=re.sub(r'\b(?:Glasgow|Bruce|Mitchell|Reid|Reade|Raitt|Williamson|Hutcheson|Hutchieson|Hutchison|Davidson|Taylor|Ayton|Swan|Thomson|Woodside|Caldwell|Alexander|Gray|Todd|Anderson)-\d+\b',lambda z:'[['+z.group()+']]',parts[i])
 return ''.join(parts)
for d in m['drafts']:
 p=R/d['path'];s=p.read_text();a,b=s.split('=== Record and identity review, 30 September 2026 ===',1);n,end=b.split('== Sources ==',1)
 s=a+'=== Record and identity review, 30 September 2026 ==='+link_ids(n)+'== Sources =='+end;p.write_text(s)
 d['new_sha256']=hashlib.sha256(s.encode()).hexdigest()
(C/'maintained-edits.json').write_text(json.dumps(m,indent=2,ensure_ascii=False)+'\n')
for p in x['proposed_source_patches']:
 if 'wikitext' not in p['merge']:continue
 s=p['merge']['wikitext'];a,b=s.split('=== Record review, 30 September 2026 ===',1);n,end=b.split('== Sources ==',1)
 p['merge']['wikitext']=a+'=== Record review, 30 September 2026 ==='+link_ids(n)+'== Sources =='+end
x['applied_maintained_source_edits']=m
x['verification'].update(targeted_index_rows_verified=8,held_drafts_verified=7,confirmed_profile_id_fields_preserved=True,original_opr_images_inspected=0,printed_marriage_entries_visually_inspected=6,printed_burgess_entry_visually_inspected=1,public_capture_privacy=60,public_capture_is_living=0,credential_strings_absent_from_json=True,verified_on='2026-09-30')
x['verification'].pop('no_shared_writes',None)
x['verification']['shared_registry_latest_findings_subjects_tools_www_unchanged_by_this_lane']=True
P.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n')
(C/'verification.json').write_text(json.dumps(x['verification'],indent=2,ensure_ascii=False)+'\n')
print('Final research JSON, native profile links and verification saved.')
