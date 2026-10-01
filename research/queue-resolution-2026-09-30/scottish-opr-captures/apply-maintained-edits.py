import json,re,hashlib
from pathlib import Path
R=Path('/Users/m/wikitree-api-scrape');C=R/'research/queue-resolution-2026-09-30/scottish-opr-captures'
x=json.load(open(R/'research/queue-resolution-2026-09-30/scottish-opr.json'))
mp='surname-research/indexes/scotlandspeople-opr-marriages-to-1700.json';source=json.load(open(R/mp))
selected={4,8,11,14,32,39,41,44};groups={int(g['finding_ids'][0].rsplit('-',1)[1]):g for g in x['groups'] if g['finding_ids'][0].startswith('opr-marriage-')}
manifest={'reviewed_on':'2026-09-30','source':'research/queue-resolution-2026-09-30/scottish-opr.json','original_register_images_inspected':False,'printed_transcription_pages_inspected':True,'index_path':mp,'index_rows':sorted(selected),'prior_index_rows':{},'drafts':[],'remaining_integration':'Root applies event-scoped registry/latest-findings/subject patches and rebuilds affected public surfaces.'}
for p in x['proposed_source_patches']:
 if p['path']!=mp:continue
 i=int(p['pointer'].rsplit('/',1)[1]);n=i+1
 if n not in selected:continue
 row=source['rows'][i];g=groups[n];manifest['prior_index_rows'][str(n)]=dict(row)
 row.setdefault('assessment_history',[]).append({'reviewed_at':'2026-09-30','assessment':row['assessment'],'source_basis':'Supplied official index and initial compatible-candidate audit, before supplementary printed-register review.'})
 row.update(p['merge'])
 row['queue_resolution_source']='research/queue-resolution-2026-09-30/scottish-opr.json'
 if n!=41 and n!=32:
  old=row.get('new_information');prefix=old+' ' if isinstance(old,str) else ''
  row['new_information']=prefix+'Printed register identifies the spouse as '+row['recorded_spouse_occupation']+' and supplies a marriage date; original parish image remains unchecked.'
  row['record_status']='supplied official index; supplementary printed-register transcription visually inspected 30 September 2026; original parish image uninspected'
 if n==44:
  row['primary_identity_status']='no_compatible_profile';row['spouse_identity_status']='compatible_candidate'
 if n==8:
  row['new_information']+=' A 1670 printed burgess abstract supplies a probable occupational continuation and apprenticeship master, not a father.'
source['reviewed_at']='2026-09-30'
(R/mp).write_text(json.dumps(source,indent=2,ensure_ascii=False)+'\n')
files={4:'1684_Scotland_Edinburgh_Marion_Glasgow.md',8:'1671_Scotland_Edinburgh_Eupham_Glasgow.md',11:'1675_Scotland_Edinburgh_Jean_Glasgow.md',14:'1651_Scotland_Edinburgh_Alisone_Glasgow.md',39:'1659_Scotland_Edinburgh_Marione_Glasgow.md',41:'1679_Scotland_Carstairs_Thomas_Glasgow.md',44:'1672_Scotland_Edinburgh_Alison_Glasgow.md'}
url='https://electricscotland.com/history/records/scottishrecordso16scotuoft.pdf'
burl='https://www.tradeshouselibrary.org/uploads/4/7/7/2/47723681/roll_of_edinburgh_burgesses_1406_to_1700.pdf'
for n,name in files.items():
 path=R/'surname-research/new-people'/name;old=path.read_text();(C/('prior-draft-'+name)).write_text(old);g=groups[n];row=source['rows'][n-1]
 notes=[]
 for f in g['new_concrete_findings']:
  if f.get('field')=='recorded_spouse_occupation':
   ss=g['sources'][f['source_ref']];pp=ss['printed_pages'][1];pdf=ss['pdf_pages'][1]
   notes.append(f"The printed Edinburgh register records the marriage of {row['forename'].title()} Glasgow and {f['person']}, {f['value']}, on {row['date']}.<ref>Henry Paton, ed., ''Register of Marriages for the Parish of Edinburgh, 1595–1700'' (Scottish Record Society, 1905), printed pp. 267 and {pp}, PDF pp. 277 and {pdf}, [{url}#page={pdf} scanned edition]. Printed page images inspected 30 September 2026; original parish image uninspected. The unnumbered Prefatory Note, PDF p. 9, describes the dates in register volumes I–II (1595–1694) as marriage dates.</ref>")
  if f['id']=='alexander-hutcheson-tailor-burgess-1670':
   notes.append(f"An Edinburgh tailor named Alexander Hutcheson became a burgess on 22 June 1670 as apprentice to the late Alexander Thomsone, tailor; his apprenticeship date was 31 January 1655. This is a probable continuation of the groom's occupation, while identification remains unproved. Thomsone was his master, not a recorded father.<ref>Charles B. Boog Watson, ed., ''Roll of Edinburgh Burgesses and Guild-Brethren, 1406–1700'' (Scottish Record Society, 1929), printed p. 265, PDF p. 275, [{burl}#page=275 scanned edition]. Printed abstract inspected 30 September 2026; original burgess record unchecked.</ref>")
 if n==8:
  notes.append('The Channelkirk occurrence on 17 September 1671 remains a separate event provisionally associated with the Edinburgh marriage. The Edinburgh occupation is not a quoted Channelkirk fact. [[Glasgow-3358|Eupham Glasgow]] and [[Glasgow-1167|Eupham Glasgow]] remain possible identities with different baptism/parentage questions. [[Hutcheson-361|Rev Alexander Hutcheson]] is a weaker surname-search lead whose ministerial career conflicts with the recorded tailor occupation; no identification is asserted. The later families of [[Hutchieson-4]] and [[Hutchison-313]] exclude those additional leads.')
 elif n==44:
  notes.append("No compatible profile for Alison herself was found in the recorded searches. [[Williamson-14321|John Williamson]], indexed in 1657, remains a young possible identity for her husband. His father [[Williamson-14320|John Williamson]] is excluded because a continuing Kirkcaldy household with Christian Turpie is indexed in 1674, 1677 and 1680. This is a competing named household across the 1672 marriage, rather than rejection simply because another wife was recorded.<ref>National Records of Scotland, ''Old Parish Registers: Births'', Kirkcaldy, references 442/10 160 (22 September 1674, William, FR172), 442/10 182 (20 November 1677, unnamed), and 442/10 198 (30 May 1680, William, FR210), naming John Williamson and Christian Turpie/Turpy; index citations read in [https://www.wikitree.com/wiki/Williamson-14324 William Williamson], [https://www.wikitree.com/wiki/Williamson-14325 unnamed Williamson] and [https://www.wikitree.com/wiki/Williamson-14326 William Williamson], 30 September 2026. Original parish images uninspected.</ref>")
 elif n==41:
  notes.append("[[Glasgow-1449|Thomas Glasgow]] is excluded from this 1679 adult event by his represented later family: attached father [[Glasgow-1382|Thomas Glasgow]] is dated about 1766–1851, and attached mother [[Davidson-14073|Christine Davidson]] is documented as Nathaniel Glasgow's mother in 1774. This conclusion concerns the currently represented family and does not depend on treating Thomas's before-1787 birth bound as an exact date.<ref>Public biographies and family links of [https://www.wikitree.com/wiki/Glasgow-1449 Thomas Glasgow], [https://www.wikitree.com/wiki/Glasgow-1382 Thomas Glasgow] and [https://www.wikitree.com/wiki/Davidson-14073 Christine Davidson], inspected 30 September 2026. Davidson's biography cites FamilySearch [https://www.familysearch.org/ark:/61903/1:1:X1RG-M2G record X1RG-M2G], Nathaniel christened 2 January 1774 to Thomas Glasgow and Christine Davidson. Underlying parish image uninspected.</ref>")
 else:
  notes.append(g['conclusion'])
 if n not in [8,44]:
  if g['primary_profile_ids']:notes.append('Compatible Glasgow candidates remain '+', '.join('[['+p+']]' for p in g['primary_profile_ids'])+'. Their childhood parentage is not transferred into this adult event.')
  else:notes.append('No compatible Glasgow profile was found in the recorded search scope; the held draft does not clear creation or a parent attachment.')
  if g['spouse_profile_ids']:notes.append('Possible husband profiles remain '+', '.join('[['+p+']]' for p in g['spouse_profile_ids'])+'; none is established as this husband.')
 if n==39:notes.append('The additional surname-search leads [[Raitt-2]] (1806 marriage) and [[Raitt-360]] (born 1866, 1904 marriage) are excluded by their much later life events.')
 note='=== Record and identity review, 30 September 2026 ===\n'+'\n\n'.join(notes)+'\n\n'
 new=old.replace('== Sources ==',note+'== Sources ==',1)
 new=re.sub(r'(?<=\*\*Current identity review, 30 September 2026:\*\* ).*?(?=\n\n)',g['conclusion'],new,count=1,flags=re.S)
 if n==8:new=new.replace("**probably**","'''probably'''")
 if n==41:
  new=new.replace('- **Duplicate audit:** bounded local and live exact-name search found no compatible adult.','- **Duplicate audit:** the earlier bounded audit found no compatible adult. The 30 September review retains the linked possibilities below and excludes Glasgow-1449 for a concrete later-family conflict.')
  new=new.replace('No compatible WikiTree profile was found in the bounded audit.','The earlier bounded audit found no compatible WikiTree profile. The current review retains the candidates below; none is confirmed as this adult.')
 path.write_text(new)
 manifest['drafts'].append({'path':str(path.relative_to(R)),'prior_copy':str((C/('prior-draft-'+name)).relative_to(R)),'prior_sha256':hashlib.sha256(old.encode()).hexdigest(),'new_sha256':hashlib.sha256(new.encode()).hexdigest(),'event_ids':g['finding_ids']+(['opr-marriage-32'] if n==8 else [])})
(C/'maintained-edits.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n')
print('Updated',len(selected),'index rows and',len(files),'held drafts; confirmed profile_ids preserved.')
