#!/usr/bin/env python3
"""Publish a small public-safe summary of verified GRONI family links."""
import json, html
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IDX = ROOT / 'surname-research/indexes'
OUT = ROOT / 'www/records'
CONNECTIONS = IDX / 'groni-family-connection-log-2026-09-23.json'
CREATION = IDX / 'groni-relative-creation-log-2026-09-24.json'

def read(path):
    if not path.exists(): return {}
    return json.loads(path.read_text())

def link(pid):
    if not pid: return 'Unresolved parent'
    return f'<a href="https://www.wikitree.com/wiki/{html.escape(pid)}">{html.escape(pid)}</a>'

def main():
    c = read(CONNECTIONS); n = read(CREATION)
    rows=[]; holds=[]
    seen=set()
    for x in c.get('connected', []):
        key=(x.get('child'),x.get('who'),x.get('parent'))
        if key in seen: continue
        seen.add(key); rows.append({'kind':'parent-child','parent':x.get('parent'),'role':x.get('who'),'children':[x.get('child')],
                     'source_refs':[x.get('source_ref','')],'evidence':x.get('evidence',''),'status':'verified'})
    for x in n.get('created_spouses', []):
        if x.get('relative') and x.get('subject'):
            rows.append({'kind':'spouse','subject':x['subject'],'related':x['relative'],
                         'source_refs':[x.get('registration','')],'status':'verified'})
    extra = n.get('additional_mother', [])
    if isinstance(extra, dict): extra = [extra]
    for x in n.get('created_mothers', []) + extra:
        mother = x.get('mother_id') or x.get('mother')
        if mother:
            rows.append({'kind':'mother-profile','parent':mother,
                         'children':x.get('children') or [x.get('child')],
                         'source_refs':x.get('source_refs') or [x.get('source_ref','')],
                         'status':'verified'})
    for x in c.get('held', []) + c.get('errors', []) + n.get('holds', []):
        holds.append({'group':x.get('group') or x.get('group_key') or x.get('subject') or x.get('registration',''),
                      'profiles':x.get('profiles',[]),
                      'reason':x.get('reason') or x.get('error') or 'held for review'})
    counts={'parent_child_links':sum(x['kind']=='parent-child' for x in rows),
            'spouse_links':sum(x['kind']=='spouse' for x in rows),
            'new_mother_profiles':sum(x['kind']=='mother-profile' for x in rows),
            'holds':len(holds)}
    payload={'generated':'2026-09-24','source_logs':[str(CONNECTIONS.relative_to(ROOT)),str(CREATION.relative_to(ROOT))],
             'counts':counts,'verified_links':rows,'unresolved_holds':holds,'merges':n.get('merges',[])}
    (OUT/'data').mkdir(parents=True,exist_ok=True)
    (OUT/'data/groni-family-links-2026-09-24.json').write_text(json.dumps(payload,indent=2,ensure_ascii=False)+'\n')
    body=['<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>GRONI family links · Glasgow Surname Project</title><link rel="stylesheet" href="../people/catalogue.css"></head><body><header><a class="brand" href="../catalogue">Glasgow Surname Project</a><nav><a href="./">Records</a><a href="groni-civil-registration-coverage-2026-09-23.html">GRONI coverage</a></nav></header><main><p class="kicker">Ireland · civil indexes</p><h1>GRONI family links</h1>',
          f'<p class="lede">{counts["parent_child_links"]} child–parent links, {counts["spouse_links"]} spouse links, {counts["new_mother_profiles"]} new mother profiles, and {counts["holds"]} unresolved groups. Links were made on WikiTree from the supplied index table and compatible family evidence.</p>',
          '<p>Registration references are from the <a href="https://geni.nidirect.gov.uk/search/birth">GRONI birth index</a> and <a href="https://geni.nidirect.gov.uk/search/marriage">marriage index</a>. The dated merge notes retain conflicts from other cited records.</p>',
          '<h2>Parents and children</h2><ul>']
    for r in rows:
        if r['kind'] != 'parent-child': continue
        who=f"{link(r['parent'])} ({html.escape(r['role'] or 'parent')}) → {link(r['children'][0])}"
        note=f" — {html.escape(r['evidence'])}" if r['evidence'] else ''
        body.append(f"<li>{who} <small>{html.escape('; '.join(r['source_refs']))}</small>{note}</li>")
    body += ['</ul><h2>Spouses</h2><ul>']
    for r in rows:
        if r['kind'] != 'spouse': continue
        body.append(f"<li>{link(r['subject'])} and {link(r['related'])} <small>{html.escape('; '.join(r['source_refs']))}</small></li>")
    body += ['</ul><h2>New mother profiles</h2><ul>']
    for r in rows:
        if r['kind'] != 'mother-profile': continue
        body.append(f"<li>{link(r['parent'])}: {', '.join(link(x) for x in r['children'] if x)} <small>{html.escape('; '.join(r['source_refs']))}</small></li>")
    body += ['</ul><h2>Duplicates consolidated</h2><ul>']
    for merge in n.get('merges',[]):
        body.append(f"<li>{link(merge['old'])} → {link(merge['survivor'])}. {html.escape(merge.get('note',''))}</li>")
    body += ['</ul><h2>Unresolved identity groups</h2><ul>']
    for x in holds:
        profiles=', '.join(link(pid) for pid in x['profiles'])
        body.append(f"<li><strong>{html.escape(x['group'])}</strong>: {profiles}. {html.escape(x['reason'])}</li>")
    body += ['</ul><p><a href="data/groni-family-links-2026-09-24.json">Download link data</a>. This local catalogue page is pending live deployment.</p></main></body></html>']
    (OUT/'groni-family-links-2026-09-24.html').write_text('\n'.join(body))
    print(json.dumps(payload['counts']))
if __name__=='__main__': main()
