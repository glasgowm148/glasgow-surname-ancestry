"""Rank paternal links by fixed-1850-cohort connectivity impact.

Run from the repository root: .venv/bin/python research/ancestry-connections/rank_working_joins.py
Use --scope all-unconfident to include older tree attachments.
Use --scope unrated to prioritise individual-rating coverage, including
inherited confident marks that have no reviewed percentage.
Coverage also includes retained named fathers outside the surname graph;
their graph impact is unavailable (null), rather than zero.
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
from tools.branch_connectivity import load_public_nodes,CONFIDENT,paternal_link_impacts,is_named_father_name


def explicit_research_state(assessment):
    """Use reviewed dispositions only; dates and narrative are not hold signals."""
    state = assessment.get('research_state') or {}
    if not isinstance(state, dict):
        state = {}
    if state.get('disposition') in {'ready', 'awaiting_source', 'reviewed_no_change'}:
        return dict(state)
    test = assessment.get('evidence_test') or {}
    if isinstance(test, dict) and test.get('held_evidence_review_exhausted') is True:
        return {**state, 'disposition': 'awaiting_source',
                'source': 'evidence_test.held_evidence_review_exhausted',
                **{key: test[key] for key in ('summary', 'resume_when') if key in test}}
    return {**state, 'disposition': 'unknown'}


def dispatch_context(assessment, estimate=None, case=None):
    """Prefer assertion reviews; legacy pair estimates supply missing workflow fields."""
    estimate, case = estimate or {}, case or {}
    state = explicit_research_state(assessment)
    if state['disposition'] == 'unknown':
        state = explicit_research_state({'research_state': estimate.get('research_state')})
    return {'research_state': state,
            **{key: case.get(key) or assessment.get(key) or estimate.get(key) or ''
               for key in ('last_test', 'next_test')}}


def sort_rows(rows, order='actionable', scope='selected'):
    """Keep impact modes explicit; dispatch readiness never changes graph impact."""
    def key(row):
        descending = lambda value: -value if value is not None else float('inf')
        identity = (row['child'], row['father'])
        if order == 'confident-gain':
            return (descending(row['confident_pair_gain']), descending(row['cross_pairs']), *identity)
        if scope == 'unrated':
            impact = (descending(row['child_side']), descending(row['cross_pairs']), *identity)
        else:
            impact = (descending(row['cross_pairs']), *identity)
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
    retained=[]
    root=Path('www');strategy=json.loads(Path('research/ancestry-connections/strategy.json').read_text());nodes,edges,quality=load_public_nodes(root,set(strategy['variants']),retained_fathers=retained if args.scope=='unrated' else None);cohort=set(json.loads(Path('www/data/ancestry-connectivity.json').read_text())['cohorts']['1850']['working']['cohort_ids']);parents={e['child']:e['father'] for e in edges}
    impacts={(r['child'],r['father']):r for r in paternal_link_impacts(nodes,edges,1850,cohort)}
    rows=[]
    assessments=json.loads(Path('research/relationship_assessments.json').read_text())
    by_assertion={a.get('assertion_id'):a for a in assessments}
    estimate_data=json.loads(Path('research/relationship_probability_estimates.json').read_text())
    estimates={(e['subject_id'],e['relative_id']):e for e in estimate_data.get('estimates',[])
               if e.get('relationship')=='father'}
    cases={c.get('assertion_id'):c for c in strategy.get('early_connections',[]) if c.get('assertion_id')}
    selected=[]
    for a in assessments:
     if a.get('publication_status')!='approved' or not a.get('working_selection'):continue
     for child,v in a.get('perspectives',{}).items():
      if v.get('relationship')=='father':selected.append((child,next(i for i in a['people'] if i!=child),a))
    if args.scope=='all-unconfident':
     candidates=[(e['child'],e['father'],by_assertion.get(e.get('assertion_id'),{})) for e in edges if e['status'] not in CONFIDENT]
    elif args.scope=='unrated':
     candidates=[(e['child'],e['father'],by_assertion.get(e.get('assertion_id'),{})) for e in retained if e['child'] in cohort and e.get('confidence_percent') is None and is_named_father_name(e.get('father_name'))]
    else:candidates=selected
    by_pair={(e['child'],e['father']):e for e in edges}
    if args.scope=='unrated':by_pair.update({(e['child'],e['father']):e for e in retained})
    for child,father,a in candidates:
     if args.scope!='unrated' and (parents.get(child)!=father or (child,father) not in impacts):continue
     impact=impacts.get((child,father),{})
     pair=by_pair[child,father]
     row={'assertion_id':a.get('assertion_id') or pair.get('assertion_id'),'child':child,'father':father,'child_name':nodes[child]['name'],'father_name':nodes.get(father,{}).get('name') or pair.get('father_name') or father,**{k:impact.get(k) for k in ('child_side','parent_side','cross_pairs','confident_child_side','confident_parent_side','confident_pair_gain','confident_component_reduction')},'evidence_grade':a.get('evidence_grade'),'source_ids':a.get('source_ids',[]),'links':a.get('analysis_links',[])}
     if args.scope=='unrated':row['graph_impact_available']=bool(impact)
     if args.scope in {'all-unconfident','unrated'}:row.update(status=by_pair[child,father]['status'],confidence_percent=by_pair[child,father].get('confidence_percent'),selected_working_hypothesis=bool(a.get('working_selection')),cohort_year=nodes[child].get('year'),year_basis=nodes[child].get('year_basis'),first_record_year=nodes[child].get('first_record_year'))
     case=cases.get(row['assertion_id'],{})
     row.update(dispatch_context(a,estimates.get((child,father)),case))
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
