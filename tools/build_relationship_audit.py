#!/usr/bin/env python3
"""Publish the documented relationship-change audit and its honest limits."""
from pathlib import Path
from html import escape
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from tools.free_space_edition import shell_page


def build(web=ROOT/'www'):
    ledger=json.loads((ROOT/'research/latest-findings.json').read_text())
    audit=json.loads((ROOT/'research/historical-relationship-audit-2026-09-30.json').read_text())
    changes=[(f,c) for f in ledger['findings'] for c in f.get('relationship_changes',[])]
    unmarked=sum(c['before']=='unmarked' for f,c in changes)
    def person(value):
        ident=re.search(r'[A-Za-z]+-\d+',value)
        if not ident:return escape(value)
        ident=ident[0]; url='/people/'+ident.lower()+'.html'
        if not (web/url.lstrip('/')).exists():url='https://www.wikitree.com/wiki/'+ident
        return f'<a href="{url}">{escape(value)}</a>'
    rows=[]
    for f,c in sorted(changes,key=lambda x:x[0]['found_on'],reverse=True):
        before='Unmarked (previously ungraded)' if c['before']=='unmarked' else c['before'].capitalize()
        rows.append(f'<tr><td>{f["found_on"]}</td><td>{person(c["subject"])}</td><td>{escape(c["relationship"].capitalize())}: {person(c["relative"])}</td><td>{before} → Certain</td><td>{escape(c["explanation"])}<p><a href="/latest-findings/#finding-{f["id"]}">Finding and source references →</a></p></td></tr>')
    missing=[]
    for c in audit['confident_status_without_recoverable_prior_grade']:
        missing.append('<li>'+person(c['subject'])+' — '+person(c['relative'])+': '+escape(c.get('evidence',c.get('evidence_basis','Current confidence is recorded; the previous grade is unavailable.')))+'</li>')
    main=f'<main class="r-main" id="main"><header class="r-page-head"><span class="r-kicker">Historical audit · 30 September 2026</span><h1>Relationships that became certain</h1><p>{len(changes)} documented confidence changes: {len(changes)-unmarked} from uncertain or unknown, and {unmarked} from an unmarked prior grade.</p><p><a href="/latest-findings/?status=relationship-certain">Filter the findings →</a></p></header><section><h2>Why the earlier count was incomplete</h2><p>The earlier ledger had three batches covering nine relationships. It omitted five recorded uncertain-to-confident reviews and 24 live changes from unmarked to confident. Those dated reviews are now backfilled. Unmarked means no earlier confidence grade was selected; it is preserved explicitly rather than relabelled uncertain.</p><p>The audit reconciled 58 saved live correction rows, 93 structured relationship assessments and 77 existing family-relationship findings. It inventoried 1,009 findings files and read the relationship-relevant cases, with available repository history from 20 August to 29 September. The recoverable findings history starts on 17 July. This establishes the recorded changes; it cannot recreate missing earlier notes.</p><p>Confident is WikiTree’s non-DNA certainty setting. The table retains supported inference and record-defined identity limits in each source account. It does not claim a fresh original-image inspection for an older citation review.</p></section><section><h2>Recorded confidence changes</h2><div style="overflow:auto;max-width:100%"><table style="width:100%;font-size:14px;border-collapse:collapse"><thead><tr><th>Review date</th><th>Person</th><th>Relationship</th><th>Previous → new grade</th><th>Evidence and scope</th></tr></thead><tbody>'+''.join(rows)+'</tbody></table></div></section><section><h2>Current confident relationships with no recoverable previous grade</h2><p>These five historical cases are visible here but excluded from the change count.</p><ul>'+''.join(missing)+'</ul></section></main>'
    page=shell_page((web/'about/index.html').read_text(),main,'Relationship confidence history','/research/relationship-audit/index.html')
    page=page.replace('</head>','<style>#main table td,#main table th{padding:12px;text-align:left;vertical-align:top;border-bottom:1px solid #d4dece}#main table td:last-child{min-width:300px}#main table td:first-child{white-space:nowrap}</style></head>')
    path=web/'research/relationship-audit/index.html';path.parent.mkdir(parents=True,exist_ok=True);path.write_text(page)
    return {'relationship_audit_rows':len(changes),'exact_prior_transitions':len(changes)-unmarked,'previously_ungraded':unmarked}


if __name__=='__main__':print(build())
