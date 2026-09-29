#!/usr/bin/env python3
"""Integrate live GRONI-created profiles into maintained research and the site.

Safe to rerun: rows, findings, manifest entries and moved drafts are keyed by
registration/profile ID and are never duplicated or overwritten.
"""
from __future__ import annotations
import argparse, csv, json, re, shutil
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG = ROOT/'surname-research/indexes/groni-created-profiles-2026-09-23.json'
AUDIT = ROOT/'surname-research/indexes/groni-death-match-audit-2026-09-23.csv'
CASES = ROOT/'data/wikitree/research-catalogue-cases.json'
NEW = ROOT/'surname-research/new-people'; RESEARCH = ROOT/'research'
# These three matching birth/death profiles were created before the browser
# creation log began.  Keep them in the same idempotent local audit path.
PRELOG_CREATED = [
    {'registration':'D/1885/11/1002/13/159', 'id':'Glasgow-4182', 'first':'Henry'},
    {'registration':'D/1884/11/1002/13/63', 'id':'Glasgow-4183', 'first':'Alice'},
    {'registration':'D/1895/11/1002/17/72', 'id':'Glasgow-4184', 'first':'Henrietta'},
]
HOLD_ROWS = {
    'D/1890/23/1004/9/446': ('Glasgow-2995;Glasgow-2975', 'Existing Ballymena James profiles remain compatible; hold the death identity.'),
    'D/1893/170/1020/14/497': ('Glasgow-3033', 'Existing Londonderry Elizabeth profile remains compatible; hold the death identity.'),
    'D/1869/183/1022/2/430': ('Smith-228705', 'Existing Magherafelt Ellen profile remains compatible; hold the death identity.'),
    'D/1879/191/1023/9/27': ('Glasgow-3395;Murray-33072;Anderson-57123', 'Existing Newry Margaret profiles remain compatible; hold the death identity.'),
    'D/1898/201/1024/25/189': ('Glasgow-1422', 'Existing Newtownards Nannie profile remains compatible; hold the death identity.'),
    'D/1871/209/1025/2/489': ('Glasgow-3140', 'Existing Omagh John profile remains compatible; hold the death identity.'),
    'D/1865/24/1004/1/118': ('Glasgow-3988', 'Existing Antrim Elizabeth/Eliza has compatible age and no death; hold.'),
    'D/1890/19/1004/9/138': ('Coburn-2653', 'Existing Agnes (Coburn) Glasgow has compatible age and no death; hold.'),
    'D/1881/20/1004/11/324': ('Thomson-10728;Glasgow-3022;McConnachie-196', 'Creation review found same-age Jane/Janet profiles with blank deaths; hold.'),
    'D/1876/23/1004/5/50': ('Baigrie-43', 'Ann (Baigrie) Glasgow is age-compatible with Nancy and has no death; hold.'),
    'D/1897/20/1004/20/403': ('Glasgow-1363', 'Existing Antrim Margaret has compatible age and no death; hold.'),
    'D/1876/22/1004/3/301': ('Glasgow-1798', 'Existing Margaret has a compatible birth year and no death; hold.'),
    'D/1890/27/1005/13/100': ('Glasgow-2011', 'Existing Jane has a compatible birth year and no death; hold.'),
    'D/1874/49/1007/17/123': ('Glasgow-1387', 'Existing Antrim William has a compatible age and no death; hold.'),
    'D/1874/52/1007/12/431': ('Glasgow-1403', 'Existing Antrim Mary has a compatible age and no death; hold.'),
    'D/1879/49/1007/25/179': ('Glasgow-1363', 'Existing Margaret Glasgow-1363 remains age-compatible; hold this Belfast death.'),
    'D/1900/48/1007/54/58': ('Glasgow-1798', 'Existing Margaret Glasgow-1798 remains age-compatible; hold this Belfast death.'),
    'D/1876/50/1007/30/176': ('Glasgow-1688', 'Existing infant Margaret has a compatible birth date and no death; hold.'),
    'D/1875/98/1009/2/344': ('Glasgow-3126;Glasgow-3196', 'Existing Ireland-born James profiles remain compatible; hold.'),
    'D/1878/99/1009/8/93': ('Glasgow-1305;Glasgow-3541;Gemmill-363;Cunningham-20927', 'Creation review found age-compatible Jane/Janet/Jean profiles with blank deaths; hold.'),
    'D/1865/99/1009/1/329': ('Glasgow-2981', 'Existing Antrim James has compatible age and no death; hold.'),
    'D/1892/99/1009/14/60': ('Baigrie-43', 'Ann (Baigrie) Glasgow is age-compatible and has no death; hold.'),
    'D/1884/99/1009/10/353': ('Neill-1934', 'Existing Ireland-born Jane (Neill) Glasgow remains compatible; hold.'),
    'D/1865/98/1009/1/167': ('Neill-1934', 'Existing Ireland-born Jane (Neill) Glasgow remains compatible; hold.'),
    'D/1864/100/1009/1/6': ('Glasgow-3157', 'Existing Armagh William has a compatible birth year and no death; hold.'),
    'D/1887/100/1009/8/224': ('Glasgow-3438', 'Existing Armagh Sarah has a compatible birth year and no death; hold.'),
    'D/1884/183/1022/7/459': ('Glasgow-2885', 'Existing Ireland-born Ellen has compatible age and no death; hold.'),
    'D/1867/183/1022/2/51': ('Glasgow-1390', 'Existing Antrim William has compatible age and no death; hold.'),
    'D/1879/183/1022/6/164': ('Black-21414', 'Existing Tyrone Mary Jane (Black) Glasgow is age-compatible with Maria; hold.'),
}
COMPLETED_EXISTING = {'D/1866/99/1009/2/55': 'McGowan-3525', 'D/1870/183/1022/3/118': 'Glasgow-3889', 'D/1887/31/1005/7/245': 'Glasgow-4005'}

def registration(text):
    m = re.search(r'D/\d{4}/\d+/\d+/\d+/\d+', text)
    return m.group(0) if m else None

def merge_redirect(old, new):
    """Move an initially-created Unknown directory to its canonical ID."""
    source, target = RESEARCH / old, RESEARCH / new
    if source.exists():
        target.mkdir(exist_ok=True)
        for child in source.iterdir():
            destination = target / child.name
            if destination.exists():
                if child.is_file() and destination.is_file():
                    text = child.read_text(errors='ignore').replace(old, new)
                    old_text = destination.read_text(errors='ignore')
                    if old_text != text:
                        destination.write_text(text)
                continue
            shutil.move(str(child), str(destination))
        source.rmdir()
    for finding in target.glob('*.md'):
        text = finding.read_text()
        replaced = text.replace(old, new)
        if replaced != text:
            finding.write_text(replaced)

def generated_finding(item, work):
    first, wid, reg = item['first'], item['id'], item['registration']
    birth = work.get('birthDate', '')
    exact_birth = work.get('birthDateStatus') == 'certain'
    birth_ref = re.search(r'U/\d{4}/\d+/\d+/\d+/\d+', work.get('bio', ''))
    mother = re.search(r"mother's maiden surname was ([A-Za-z'-]+)", work.get('bio', ''))
    birth_district = work.get('birthLocation', '').replace(', Ireland', '')
    death_district = work.get('deathLocation', '').replace(', Ireland', '')
    date_label = lambda value: date.fromisoformat(value).strftime('%-d %B %Y')
    death = date_label(work['deathDate'])
    if exact_birth and birth_ref:
        places = (f'Both events were registered in {death_district}.'
                  if birth_district == death_district else
                  f'The birth was registered in {birth_district} and the death in {death_district}.')
        conclusion = (f'[{first} Glasgow ({wid})](https://www.wikitree.com/wiki/{wid}) was born on '
                      f'{date_label(birth)} and died on {death}. {places}')
        identity = ('The matching name and registration district, together with the age at death, '
                    'support treating the birth and death entries as the same child.')
        if mother:
            identity += f" The birth index gives the mother's maiden surname as {mother.group(1)}."
    else:
        conclusion = (f'[{first} Glasgow ({wid})](https://www.wikitree.com/wiki/{wid}) died on '
                      f'{death}; the death was registered in {death_district}. The reported age '
                      f'suggests birth about {birth}.')
        identity = ''
    conclusion += ' The exact place of death is unknown.'
    if work.get('lnab') == 'Unknown':
        identity += ' The death index lists Glasgow as her surname but does not give her birth surname.'
    identity_section = f'\n## Identity/relationship assessment\n\n{identity.strip()}\n' if identity else ''
    return f'''<!-- generated: groni-live-creation-sync -->
# {first} Glasgow ({wid}): civil indexes

Last updated: {date.today().isoformat()}

## Current conclusion

{conclusion}

## Source findings

- [GRONI civil death index](https://geni.nidirect.gov.uk/search/death), `{reg}`.
{('- [GRONI civil birth index](https://geni.nidirect.gov.uk/search/birth), `' + birth_ref.group(0) + '`.') if birth_ref else ''}
{identity_section}
'''

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--log',default=str(LOG)); ap.add_argument('--write',action='store_true'); a=ap.parse_args()
    log=json.loads(Path(a.log).read_text()); created=[*PRELOG_CREATED, *log.get('created',[])]
    work={x['registration']:x for x in log.get('created',[])}
    drafts={registration(p.read_text(errors='ignore')):p for p in NEW.glob('*.md') if registration(p.read_text(errors='ignore'))}
    rows=list(csv.DictReader(AUDIT.open(newline=''))); fields=rows[0].keys() if rows else []
    byreg={r['registration_number']:r for r in rows}
    actions=[]
    for item in created:
        reg=item.get('registration'); wid=item.get('id');
        if not reg or not wid: continue
        redirected_from=item.get('redirected_from')
        if a.write and redirected_from:
            merge_redirect(redirected_from, wid)
        r=byreg.get(reg)
        if r:
            r['assessment']='new_profile_created'
            r['candidate_wikitree_ids']=wid
            r['reason']='Live profile created from reviewed GRONI death-index evidence.'
            r['live_duplicate_review']=f'Created {wid} ({item.get("url", "")})'
        src=drafts.get(reg); dest=RESEARCH/wid; finding=dest/'findings.md'
        if a.write and src and src.parent == NEW:
            dest.mkdir(exist_ok=True)
            target=dest/src.name
            if not target.exists(): shutil.move(str(src),str(target)); actions.append(f'moved {src.name} -> research/{wid}/')
        # Findings may have acquired later birth, marriage or family research.
        # A rerun must not replace those additions with the original death draft.
        if a.write and not finding.exists() and reg in work:
            dest.mkdir(exist_ok=True)
            finding.write_text(generated_finding(item, work[reg])); actions.append(f'updated research/{wid}/findings.md')
    for reg, (ids, reason) in HOLD_ROWS.items():
        if reg in byreg:
            byreg[reg].update(assessment='possible_profile', candidate_wikitree_ids=ids, reason=reason)
    for reg, wid in COMPLETED_EXISTING.items():
        if reg in byreg:
            reason = ('Birth 3 October 1887 in the Ballymoney district and Aiken/Eakin mother '
                      'match John Garvin Glasgow-4005; exact death applied live.'
                      if wid == 'Glasgow-4005' else
                      'Exact death date updated live from the reviewed GRONI index.')
            byreg[reg].update(assessment='existing_profile', candidate_wikitree_ids=wid,
                              reason=reason,
                              live_duplicate_review=f'Exact death date applied to {wid}.')
    if a.write:
        with AUDIT.open('w',newline='') as f: csv.DictWriter(f,fieldnames=fields).writeheader(); csv.DictWriter(f,fieldnames=fields).writerows(rows)
        manifest=json.loads(CASES.read_text()); cases=manifest.setdefault('cases',{})
        for item in created:
            wid=item.get('id');
            if wid:
                old=item.get('redirected_from')
                if old:
                    cases.pop(old, None)
                note='Live profile created from reviewed GRONI death-index evidence; public metadata capture is pending before catalogue inclusion.'
                if old:
                    note=f'Canonical profile after WikiTree redirected {old}; '+note
                cases[wid] = {'status':'pending','profile_id':wid,'reason':note}
        CASES.write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n')
        meta_path=AUDIT.with_suffix('.json')
        meta=json.loads(meta_path.read_text())
        counts={}
        for row in rows:
            counts[row['assessment']]=counts.get(row['assessment'],0)+1
        meta['counts']=counts
        meta['live_creation_sync']={
            'updated':date.today().isoformat(),
            'created_profile_ids':sorted({x.get('id') for x in created if x.get('id')}),
            'catalogue_metadata_status':'pending public WikiTree captures',
        }
        meta_path.write_text(json.dumps(meta,indent=2,ensure_ascii=False)+'\n')
        # Preserve the existing live-review JSON; add a small idempotent audit note.
        review=ROOT/'surname-research/indexes/groni-live-duplicate-review-2026-09-23.json'; data=json.loads(review.read_text())
        data['local_creation_sync']={'updated':date.today().isoformat(),'profile_ids':sorted({x.get('id') for x in created if x.get('id')}),'redirects':{x['redirected_from']:x['id'] for x in created if x.get('redirected_from')}}
        review.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({'created':len(created),'actions':actions,'write':a.write},indent=2))
if __name__=='__main__': main()
