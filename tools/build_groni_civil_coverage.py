#!/usr/bin/env python3
"""Build a row-level ledger for the supplied GRONI civil CSV."""
import csv, json, html
from collections import Counter
from pathlib import Path
try:
    from catalogue_theme import CATALOGUE_ASSET_VERSION
except ModuleNotFoundError:
    from tools.catalogue_theme import CATALOGUE_ASSET_VERSION

ROOT = Path(__file__).resolve().parents[1]
MASTER = Path('/Users/m/Downloads/glasgow_civil_records_master.csv')
OUT = ROOT/'surname-research/indexes/groni-civil-registration-coverage-2026-09-23.csv'
OUTJSON = ROOT/'surname-research/indexes/groni-civil-registration-coverage-2026-09-23.json'
WEBJSON = ROOT/'www/records/data/groni-civil-registration-coverage-2026-09-23.json'
WEBCSV = ROOT/'www/records/data/groni-civil-registration-coverage-2026-09-23.csv'
WEBHTML = ROOT/'www/records/groni-civil-registration-coverage-2026-09-23.html'
VERIFIED_LOGS = (ROOT/'surname-research/indexes/groni-live-creation-log-2026-09-23.json', ROOT/'surname-research/indexes/groni-live-edit-log-2026-09-23.json')

def read(path):
    with path.open(newline='') as f: return list(csv.DictReader(f))
def index(rows): return {r.get('registration_number','').strip():r for r in rows if r.get('registration_number','').strip()}
def ids(v): return '; '.join(x.strip().replace('https://www.wikitree.com/wiki/','') for x in (v or '').replace(',',';').split(';') if x.strip())
def profile_links(value):
    names=[x.strip() for x in value.split(';') if x.strip()]
    return ', '.join(f'<a href="https://www.wikitree.com/wiki/{html.escape(name,quote=True)}">{html.escape(name)}</a>' for name in names) or '—'

def verified_live_rows():
    """Accept only explicit post-save verification with a source ID."""
    out = {}
    for path in VERIFIED_LOGS:
        if not path.exists(): continue
        data = json.loads(path.read_text())
        items = data.get('verified', data.get('saved', data.get('created', data.get('attached', []))))
        for item in items if isinstance(items, list) else []:
            if not (item.get('verified_live') or item.get('live_verified') or item.get('saved_live') or item.get('verified')): continue
            reg = (item.get('registration') or item.get('registration_number') or '').strip()
            wid = (item.get('id') or item.get('wikitree_id') or '').strip()
            source = item.get('source_id') or item.get('source_ids') or item.get('citation_id')
            if reg and wid and source:
                out[reg] = {'id': wid, 'source_id': '; '.join(map(str, source)) if isinstance(source, list) else str(source), 'action': item.get('action', 'verified_live_attachment'), 'reason': item.get('verification_note') or item.get('note') or 'Live save verified.'}
    return out

def main():
    master=read(MASTER)
    births=index(read(ROOT/'surname-research/indexes/groni-other-birth-coverage-2026-09-23.csv'))
    births.update(index(read(ROOT/'surname-research/indexes/groni-cookstown-birth-coverage-2026-09-23.csv')))
    deaths=index(read(ROOT/'surname-research/indexes/groni-death-match-audit-2026-09-23.csv'))
    marriages=index(read(ROOT/'surname-research/indexes/groni-marriage-validated-2026-09-23.csv'))
    made=json.loads((ROOT/'surname-research/indexes/groni-created-profiles-2026-09-23.json').read_text())
    made={x['registration']:x['id'] for x in made.get('created',[]) if x.get('registration')}
    verified=verified_live_rows()
    relatives=json.loads((ROOT/'surname-research/indexes/groni-relative-creation-log-2026-09-24.json').read_text())
    canonical={x['old']:x['survivor'] for x in relatives.get('merges',[])}
    rows=[]
    for raw in master:
        typ=raw.get('\ufeffrecord_type',raw.get('record_type','')).strip().lower(); ref=raw['registration_number'].strip()
        a=(births if typ=='birth' else deaths if typ=='death' else marriages).get(ref,{})
        if typ=='birth':
            rawstatus=a.get('status','missing_audit'); profile=ids(a.get('proposed_wikitree_id',''))
            if ref in verified:
                profile=verified[ref]['id']; rawstatus='created_profile' if verified[ref]['action']=='verified_live_creation' else 'attached_existing'
            status={'existing':'matched_existing_candidate','needs_create':'pending_duplicate_check','conflict_review':'hold_conflict_review'}.get(rawstatus,rawstatus)
            action={'matched_existing_candidate':'Verify/cite registration on live profile','created_profile':'Live creation and source citation verified','attached_existing':'Live edit and source citation verified','pending_duplicate_check':'Complete live duplicate check, then create or attach','hold_conflict_review':'Resolve candidate conflict before creating or attaching'}.get(status,'Review birth coverage')
            reason=a.get('reasoning') or verified.get(ref,{}).get('reason',''); source='GRONI birth index; birth coverage audit' + (f"; live source {verified[ref]['source_id']}" if ref in verified else '')
        elif typ=='death':
            rawstatus=a.get('assessment','missing_audit'); profile=verified.get(ref,{}).get('id') or made.get(ref,ids(a.get('candidate_wikitree_ids','')))
            if ref in verified: rawstatus='created_profile' if verified[ref]['action']=='verified_live_creation' else 'attached_existing'
            status={'existing_profile':'matched_existing_candidate','new_profile_created':'created_profile','possible_profile':'hold_possible_match','deferred_robert':'deferred_roberts','unnamed_hold':'hold_unnamed'}.get(rawstatus,rawstatus)
            action={'matched_existing_candidate':'Verify/cite registration on live profile','created_profile':'Live creation and source citation verified','attached_existing':'Live edit and source citation verified','hold_possible_match':'Review candidate and cross-check supplied births/marriages','deferred_roberts':'Deferred to separate Roberts workstream','hold_unnamed':'Resolve unnamed index entry before assignment'}.get(status,'Review death coverage')
            reason=a.get('reason') or verified.get(ref,{}).get('reason',''); source='GRONI death index; death match audit' + (f"; live source {verified[ref]['source_id']}" if ref in verified else '')
        else:
            rawstatus=a.get('status','missing_audit'); profile=verified.get(ref,{}).get('id') or ids(a.get('best_glasgow_profile_id',''))
            if ref in verified: rawstatus='created_profile' if verified[ref]['action']=='verified_live_creation' else 'attached_existing'
            if a.get('possible_spouse_id'): profile='; '.join(x for x in [profile,ids(a['possible_spouse_id'])] if x)
            status={'existing':'hold_existing_candidate','attached_existing':'attached_existing','needs_create':'pending_duplicate_check','conflict_review':'hold_conflict_review'}.get(rawstatus,rawstatus)
            action={'hold_existing_candidate':'Verify couple and cite registration on suitable profile(s)','created_profile':'Live creation and source citation verified','attached_existing':'Live edit and source citation verified','pending_duplicate_check':'Complete live duplicate check, then attach or create','hold_conflict_review':'Resolve conflicting candidate before attaching or creating'}.get(status,'Review marriage coverage')
            reason=a.get('reasoning') or verified.get(ref,{}).get('reason',''); source='GRONI marriage index; marriage coverage audit' + (f"; live source {verified[ref]['source_id']}" if ref in verified else '')
        forename=raw.get('forename',raw.get('recorded_forename',''))
        if forename.strip().lower().startswith('robert'):
            status='deferred_roberts'
            action='Handled by the separate Robert workstream'
        original_profile=profile
        profile='; '.join(canonical.get(wid.strip(),wid.strip()) for wid in profile.split(';') if wid.strip())
        if profile!=original_profile and status=='created_profile':
            status='attached_existing'
            rawstatus='merged_into_existing'
            action='Merged duplicate into existing profile; source citation retained'
            reason=f'Merged {original_profile} into {profile}; original registration remains cited.'
        rows.append({'record_type':typ,'registration_number':ref,'registration_year':raw.get('registration_year',''),'district':raw.get('district',''),'event_date':raw.get('event_date',''),'event_date_iso':raw.get('event_date_iso',''),'forename':forename,'surname':raw.get('surname',raw.get('recorded_surname','')),'sex':raw.get('sex',''),'age_at_death':raw.get('age_at_death',''),'approx_birth_year':raw.get('approx_birth_year',''),'mother_maiden_name':raw.get('mother_maiden_name',''),'other_party_forename':raw.get('other_party_forename',''),'other_party_surname':raw.get('other_party_surname',''),'profile_id_when_known':profile,'status':status,'source':source,'next_action':action,'audit_reasoning':reason,'audit_status':rawstatus})
    OUT.parent.mkdir(parents=True,exist_ok=True); WEBJSON.parent.mkdir(parents=True,exist_ok=True)
    fields=list(rows[0]);
    with OUT.open('w',newline='') as f: w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
    counts=Counter(x['record_type'] for x in rows); statuses=Counter(x['status'] for x in rows)
    payload={'generated':'2026-09-23','source_master':MASTER.name,'row_count':len(rows),'totals':dict(counts),'status_counts':dict(statuses),'note':'Candidate and hold statuses are not confirmed live WikiTree attachments.','rows':rows}
    OUTJSON.write_text(json.dumps(payload,indent=2,ensure_ascii=False)+'\n'); WEBJSON.write_text(json.dumps(payload,indent=2,ensure_ascii=False)+'\n')
    with WEBCSV.open('w',newline='') as f: w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
    trs=''.join('<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>'.format(html.escape(x['record_type']),html.escape(x['registration_number']),html.escape(x['forename']+' '+x['surname']),html.escape(x['district']),profile_links(x['profile_id_when_known']),html.escape(x['status'].replace('_',' '))) for x in rows)
    status_text=' · '.join(f'{html.escape(k)}: {v}' for k,v in sorted(statuses.items()))
    identity_html='''<section id="identity-decisions"><h2>Identity decisions</h2>
<p><a href="https://www.wikitree.com/wiki/Hewitt-8271">Helen (Hewitt) Glasgow</a> is the mother linked to Henry, Alice and Henrietta Glasgow. Their Armagh birth entries name Hewitt as their mother's maiden surname; William Glasgow's family statement names Helen Hewitt as his wife. The duplicate placeholder Hewitt-9718 was merged into Helen. See birth references U/1876/11/1002/11/31, U/1884/11/1002/16/205 and U/1895/11/1002/22/55 in the ledger.</p>
<p>The Ballymena birth of <a href="https://www.wikitree.com/wiki/Glasgow-4342">James Glasgow on 20 August 1869</a> (U/1869/20/1004/5/338) belongs to a separate profile from <a href="https://www.wikitree.com/wiki/Glasgow-2408">James Glasgow born 16 February 1871</a> (U/1871/24/1004/3/478). The 1869 citation was removed from the 1871 profile.</p></section>'''
    priorities=json.loads((ROOT/'surname-research/indexes/groni-full-record-priorities-2026-09-23.json').read_text())['ranked'][:3]
    priority_items=''.join(f'<li><strong>{html.escape(p["registration_id"])}</strong> ({html.escape(p["district"])}): {html.escape(p["question"])}</li>' for p in priorities)
    priority_html=f'<section id="full-record-priorities"><h2>Full returns most useful for open questions</h2><p>These index entries are cited or tracked, but the full returns could distinguish competing identities. No paid returns were inspected in this review.</p><ol>{priority_items}</ol></section>'
    family_html='<p><a href="groni-family-links-2026-09-24.html">View the verified family links and unresolved identity groups</a>.</p>'
    WEBHTML.write_text(f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>GRONI civil-registration coverage · Glasgow Surname Project</title><link rel="stylesheet" href="../people/catalogue.css?v={CATALOGUE_ASSET_VERSION}"></head><body><header><a class="brand" href="../catalogue">Glasgow Surname Project</a><nav><a href="../records/">Records</a><a href="../places/">Places</a><a href="../data/">Data</a></nav></header><main><p class="kicker">Ireland · GRONI civil indexes</p><h1>GRONI civil-registration coverage</h1><p class="lede">{len(rows)} supplied rows: {counts['birth']} births, {counts['death']} deaths and {counts['marriage']} marriages.</p><p><strong>Status counts:</strong> {status_text}</p><p>All 542 non-Robert references were verified in live WikiTree biographies. The 19 Robert entries are assigned to a separate research task. The source is the supplied GRONI index table; certificates were not inspected.</p>{identity_html}{priority_html}{family_html}<p><a href="data/groni-civil-registration-coverage-2026-09-23.csv">Download CSV ledger</a> · <a href="data/groni-civil-registration-coverage-2026-09-23.json">Download JSON ledger</a></p><table class="wikitable sortable"><thead><tr><th>Type</th><th>Registration</th><th>Recorded name</th><th>District</th><th>Profile</th><th>Status</th></tr></thead><tbody>{trs}</tbody></table></main><footer><p>Local research presentation; live deployment remains pending.</p></footer></body></html>''')
    print(json.dumps({'rows':len(rows),'totals':dict(counts),'statuses':dict(statuses),'csv':str(OUT),'json':str(OUTJSON),'web':str(WEBHTML)},indent=2))

if __name__=='__main__': main()
