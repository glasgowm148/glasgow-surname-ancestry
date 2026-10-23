"""Rank paternal links by fixed-1850-cohort connectivity impact.

Run from the repository root: .venv/bin/python research/ancestry-connections/rank_working_joins.py
Use --scope all-unconfident to include older tree attachments.
Use --scope unrated to prioritise individual-rating coverage, including
inherited confident marks that have no reviewed percentage.
Coverage ranks the child-side branch size first; the other modes rank
dependent connected pairs. These are separate measures of research impact.
Impact counts dependent connected pairs, never confidence or new genealogical joins.
Nested link impacts overlap and must not be summed. Counts concern retained profiles,
not independently verified unique people. Selected-only scope is retained; dispatch defaults
to explicit research readiness followed by working impact. Unknown readiness is not a hold.
--preflight adds held evidence for a bounded shortlist (five rows unless --limit is set).
"""
from pathlib import Path
import argparse,json,sys
sys.path.insert(0,str(Path.cwd()))
from tools.branch_connectivity import load_public_nodes,CONFIDENT,paternal_link_impacts


def explicit_research_state(assessment):
    """Use reviewed dispositions only; dates and narrative are not hold signals."""
    state = assessment.get('research_state') or {}
    if not isinstance(state, dict):
        return {'disposition': 'unknown'}
    if state.get('disposition') not in {'ready', 'awaiting_source', 'reviewed_no_change'}:
        return {**state, 'disposition': 'unknown'}
    return dict(state)


def sort_rows(rows, order='actionable', scope='selected'):
    """Keep impact modes explicit; dispatch readiness never changes graph impact."""
    def key(row):
        identity = (row['child'], row['father'])
        if order == 'confident-gain':
            return (-row['confident_pair_gain'], -row['cross_pairs'], *identity)
        if scope == 'unrated':
            impact = (-row['child_side'], -row['cross_pairs'], *identity)
        else:
            impact = (-row['cross_pairs'], *identity)
        if order == 'actionable':
            disposition = row.get('research_state', {}).get('disposition', 'unknown')
            readiness = {'ready': 0, 'unknown': 1, 'awaiting_source': 2,
                         'reviewed_no_change': 2}.get(disposition, 1)
            return (readiness, *impact)
        return impact
    rows.sort(key=key)
    return rows


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope",choices=["selected","all-unconfident","unrated"],default="selected",help="Selected hypotheses, all unconfident attachments, or all individually unrated links")
    parser.add_argument("--sort",choices=["actionable","working-pairs","confident-gain"],default="actionable",help="Explicit research readiness then working impact (default), working impact, or immediate confident-pair gain")
    parser.add_argument("--preflight",action="store_true",help="Include bounded held-evidence packets; defaults to a five-row shortlist")
    parser.add_argument("--limit",type=int,help="Maximum output rows (must be positive)")
    args=parser.parse_args(argv)
    if args.limit is not None and args.limit < 1:parser.error("--limit must be positive")
    root=Path('www');strategy=json.load(open('research/ancestry-connections/strategy.json'));nodes,edges,quality=load_public_nodes(root,set(strategy['variants']));cohort=set(json.load(open('www/data/ancestry-connectivity.json'))['cohorts']['1850']['working']['cohort_ids']);parents={e['child']:e['father'] for e in edges}
    impacts={(r['child'],r['father']):r for r in paternal_link_impacts(nodes,edges,1850,cohort)}
    rows=[]
    assessments=json.load(open('research/relationship_assessments.json'))
    by_assertion={a.get('assertion_id'):a for a in assessments}
    cases={c.get('assertion_id'):c for c in strategy.get('early_connections',[]) if c.get('assertion_id')}
    selected=[]
    for a in assessments:
     if a.get('publication_status')!='approved' or not a.get('working_selection'):continue
     for child,v in a.get('perspectives',{}).items():
      if v.get('relationship')=='father':selected.append((child,next(i for i in a['people'] if i!=child),a))
    if args.scope=='all-unconfident':
     candidates=[(e['child'],e['father'],by_assertion.get(e.get('assertion_id'),{})) for e in edges if e['status'] not in CONFIDENT]
    elif args.scope=='unrated':
     candidates=[(e['child'],e['father'],by_assertion.get(e.get('assertion_id'),{})) for e in edges if e.get('confidence_percent') is None]
    else:candidates=selected
    by_pair={(e['child'],e['father']):e for e in edges}
    for child,father,a in candidates:
     if parents.get(child)!=father or (child,father) not in impacts:continue
     impact=impacts[child,father]
     row={'assertion_id':a.get('assertion_id') or by_pair[child,father].get('assertion_id'),'child':child,'father':father,'child_name':nodes[child]['name'],'father_name':nodes[father]['name'],**{k:impact[k] for k in ('child_side','parent_side','cross_pairs','confident_child_side','confident_parent_side','confident_pair_gain','confident_component_reduction')},'evidence_grade':a.get('evidence_grade'),'source_ids':a.get('source_ids',[]),'links':a.get('analysis_links',[])}
     if args.scope in {'all-unconfident','unrated'}:row.update(status=by_pair[child,father]['status'],confidence_percent=by_pair[child,father].get('confidence_percent'),selected_working_hypothesis=bool(a.get('working_selection')),cohort_year=nodes[child].get('year'),year_basis=nodes[child].get('year_basis'),first_record_year=nodes[child].get('first_record_year'))
     case=cases.get(row['assertion_id'],{})
     row['last_test']=case.get('last_test') or a.get('last_test') or ''
     row['next_test']=case.get('next_test') or a.get('next_test') or ''
     row['research_state']=explicit_research_state(a)
     rows.append(row)
    sort_rows(rows,args.sort,args.scope)
    limit=args.limit if args.limit is not None else (5 if args.preflight else None)
    if limit is not None:rows=rows[:limit]
    if args.preflight:
     from tools.research_preflight import build_preflight,load_preflight_context
     context=load_preflight_context()
     for row in rows:
      row['preflight']=build_preflight(row['child'],row['father'],context=context)
    print(json.dumps(rows,ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()
