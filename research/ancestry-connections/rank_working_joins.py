"""Rank paternal links by fixed-1850-cohort connectivity impact.

Run from the repository root: .venv/bin/python research/ancestry-connections/rank_working_joins.py
Use --scope all-unconfident to include older tree attachments.
Use --scope unrated to prioritise individual-rating coverage, including
inherited confident marks that have no reviewed percentage.
Coverage also includes retained named fathers outside the surname graph;
their graph impact is unavailable (null), rather than zero.
Use --scope unknown for subjects with no retained named father, ranked by
known cohort descendants; --through selects an earlier saved cohort.
Reachable documentary roots are extra connector rows, labelled outside the
measured population; unavailable accounts are not classified as Unknown.
Default research dispatch prioritises Uncertain/Possible links, then child-side
branch size within explicit readiness. Completed/held tests stay behind available work.
Coverage ranks child-side size; explicit impact sorts rank connected pairs.
Impact counts dependent connected pairs, never confidence or new genealogical joins.
Nested link impacts overlap and must not be summed. Counts concern retained profiles,
not independently verified unique people. Selected-only scope is retained; dispatch defaults
to uncertainty, readiness and branch impact. Unknown readiness is not a hold.
--preflight adds held evidence for a bounded shortlist (five rows unless --limit is set).
"""
from pathlib import Path
import argparse,json,sys
from collections import defaultdict
from urllib.parse import urlsplit
sys.path.insert(0,str(Path.cwd()))
from tools.branch_connectivity import load_public_nodes,CONFIDENT,paternal_link_impacts,is_named_father_name,has_named_father


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


def dispatch_context(assessment, estimate=None, case=None, *, plan=None, father=None):
    """Use pair reviews first, then a plan explicitly bound to this father."""
    estimate, case = estimate or {}, case or {}
    state = explicit_research_state(assessment)
    if state['disposition'] == 'unknown':
        state = explicit_research_state({'research_state': estimate.get('research_state')})
    plan_source = {}
    if state['disposition'] == 'unknown' and plan:
        planned = explicit_research_state(plan)
        # Do not let an old child review hold a replacement father. Unbound
        # plans can describe Unknown investigations, not named parent pairs.
        if planned['disposition'] != 'unknown' and planned.get('father_id') == father:
            state = planned
            plan_source = plan
    return {'research_state': state,
            **{key: state.get(key) or plan_source.get(key) or case.get(key)
               or assessment.get(key) or estimate.get(key) or ''
               for key in ('last_test', 'next_test')}}


def person_plan(project_root, ident):
    path = project_root / 'research' / ident / 'research_plan.json'
    if not path.is_file():
        return {}
    plan = json.loads(path.read_text())
    return plan if plan.get('profile_id', plan.get('case_id', ident)) == ident else {}


def sort_rows(rows, order='actionable', scope='selected'):
    """Keep impact modes explicit; dispatch readiness never changes graph impact."""
    def key(row):
        descending = lambda value: -value if value is not None else float('inf')
        identity = (row['child'], row['father'] or '')
        if scope == 'unknown':
            impact = (-row['known_descendant_count'], -row['known_child_count'],
                      row['earliest_cohort_cutoff'] or float('inf'),
                      row.get('cohort_year') or float('inf'), *identity)
            if order != 'actionable':return impact
        elif order == 'confident-gain':
            return (descending(row['confident_pair_gain']), descending(row['cross_pairs']), *identity)
        elif scope == 'unrated':
            impact = (descending(row['child_side']), descending(row['cross_pairs']), *identity)
        elif order == 'actionable':
            impact = (descending(row.get('child_side')), descending(row.get('confident_pair_gain')),
                      descending(row['cross_pairs']), row.get('cohort_year') or float('inf'), *identity)
        else:
            impact = (descending(row['cross_pairs']), *identity)
        if order == 'actionable':
            disposition = row.get('research_state', {}).get('disposition', 'unknown')
            readiness = {'ready': 0, 'unknown': 1, 'awaiting_source': 2,
                         'reviewed_no_change': 2}.get(disposition, 1)
            if scope not in {'unknown', 'unrated'}:
                percent = row.get('confidence_percent')
                uncertain = (percent < 60 if isinstance(percent, (int, float)) else
                             (row.get('status') or row.get('public_status')) in {'uncertain', 'possible'})
                return (readiness == 2, not uncertain, readiness, *impact)
            return (readiness, *impact)
        return impact
    rows.sort(key=key)
    return rows


def unknown_father_rows(root, nodes, edges, cohorts, through):
    """Reuse public father listings; rank known descendants, not hypothetical joins."""
    cohort = set(cohorts[str(through)]['working']['cohort_ids'])
    parents = {e['child']: e['father'] for e in edges}
    eligible, pending = set(cohort), list(cohort)
    while pending:
        father = parents.get(pending.pop())
        if father in nodes and father not in eligible and not (
                nodes[father].get('birth_year') is not None and nodes[father]['birth_year'] > through):
            eligible.add(father); pending.append(father)
    children = defaultdict(set)
    for edge in edges:
        if {edge['child'], edge['father']} <= eligible:
            children[edge['father']].add(edge['child'])
    rows = []
    for ident in sorted(eligible):
        node = nodes[ident]
        # Outside-cohort documentary connectors are included only at roots.
        if ident not in cohort and ident in parents:continue
        route = str(node.get('url') or '')
        parsed = urlsplit(route)
        safe = parsed.path.startswith('/') and not parsed.scheme and not parsed.netloc and '..' not in Path(parsed.path).parts
        path = root / parsed.path.lstrip('/') if safe else None
        dossier_path = path.with_suffix('.json') if path is not None and path.suffix == '.html' else None
        dossier = json.loads(dossier_path.read_text()) if dossier_path is not None and dossier_path.is_file() else None
        if dossier is not None and has_named_father(dossier):continue
        descendants, stack = set(), list(children[ident])
        while stack:
            child = stack.pop()
            if child not in descendants and child != ident:
                descendants.add(child); stack.extend(children[child])
        measured = descendants & cohort
        earliest = next((int(c) for c in sorted(cohorts, key=int)
                         if ident in cohorts[c]['working']['cohort_ids'] or
                         measured.intersection(cohorts[c]['working']['cohort_ids'])), None)
        # Per-person plans can hold an Unknown investigation without inventing
        # a selected father assertion or reinterpreting prose/dates as a hold.
        plan = person_plan(root.parent, ident)
        rows.append(dict(child=ident, father=None, child_name=node['name'], father_name=None,
            child_url=route if safe else None, assertion_id=None, confidence_percent=None,
            status='unknown_father' if dossier is not None else 'account_unavailable',
            unknown_father=True if dossier is not None else None,
            father_listing_status='unknown' if dossier is not None else 'unavailable',
            account_available=dossier is not None, earliest_cohort_cutoff=earliest,
            cohort_member=ident in cohort, cohort_year=node.get('year'),
            population_basis='measured cohort person' if ident in cohort else 'documentary connector outside measured population',
            year_basis=node.get('year_basis'), first_record_year=node.get('first_record_year'),
            known_child_count=len(children[ident]), known_cohort_child_count=len(children[ident] & cohort),
            known_descendant_count=len(measured), child_side=len(measured) + int(ident in cohort),
            reach_basis='Distinct cohort descendants in the retained working graph; not a proposed father impact.',
            parent_side=None, cross_pairs=None, confident_child_side=None,
            confident_parent_side=None, confident_pair_gain=None, confident_component_reduction=None,
            graph_impact_available=False, evidence_grade=None, source_ids=[], links=[],
            **dispatch_context(dossier or {}, plan=plan)))
    return rows


def print_rows(rows, args):
    sort_rows(rows,args.sort,args.scope)
    limit=args.limit if args.limit is not None else (5 if args.preflight else None)
    if limit is not None:rows=rows[:limit]
    if args.preflight:
     import re
     from tools.research_preflight import build_preflight,load_preflight_context
     context=load_preflight_context()
     for row in rows:
      if row.get('cohort_member') is False or row['child'].startswith('record-') or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]*-\d+',row['child']):
       row['preflight']={'available':False,'profile_id':row['child'],'father_id':row['father'],
                         'reason':'Documentary account has no eligible WikiTree profile ID; use its public account route.',
                         'url':row.get('child_url')}
      else:row['preflight']=build_preflight(row['child'],row['father'],context=context)
    print(json.dumps(rows,ensure_ascii=False,indent=2))


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope",choices=["selected","all-unconfident","unrated","unknown"],default="selected",help="Selected hypotheses, all unconfident attachments, unrated named fathers, or no retained named father")
    parser.add_argument('--through',type=int,default=1850,help='Saved cohort cutoff (default:1850)')
    parser.add_argument("--sort",choices=["actionable","working-pairs","confident-gain"],default="actionable",help="Uncertain/Possible links and branch size, respecting source holds (default); or explicit working/confident pair impact")
    parser.add_argument("--preflight",action="store_true",help="Include bounded held-evidence packets; defaults to a five-row shortlist")
    parser.add_argument("--limit",type=int,help="Maximum output rows (must be positive)")
    args=parser.parse_args(argv)
    if args.limit is not None and args.limit < 1:parser.error("--limit must be positive")
    retained=[]
    root=Path('www');strategy=json.loads(Path('research/ancestry-connections/strategy.json').read_text());nodes,edges,quality=load_public_nodes(root,set(strategy['variants']),retained_fathers=retained if args.scope=='unrated' else None);cohorts=json.loads(Path('www/data/ancestry-connectivity.json').read_text())['cohorts'];parents={e['child']:e['father'] for e in edges}
    if str(args.through) not in cohorts:parser.error('--through must name a saved cohort cutoff')
    cohort=set(cohorts[str(args.through)]['working']['cohort_ids'])
    if args.scope=='unknown':
     print_rows(unknown_father_rows(root,nodes,edges,cohorts,args.through),args)
     return
    impacts={(r['child'],r['father']):r for r in paternal_link_impacts(nodes,edges,args.through,cohort)}
    rows=[]
    assessments=json.loads(Path('research/relationship_assessments.json').read_text())
    by_assertion={a.get('assertion_id'):a for a in assessments}
    estimate_data=json.loads(Path('research/relationship_probability_estimates.json').read_text())
    estimates={(e['subject_id'],e['relative_id']):e for e in estimate_data.get('estimates',[])
               if e.get('relationship')=='father'}
    # Dispatch uses current database-derived reviews, even before their public
    # projection has been rebuilt/approved. Do not change the public graph,
    # selections or impact counts to close this private queue's coverage gaps.
    def reviewed_percent(pair):
     estimate=estimates.get((pair['child'],pair['father']),{})
     return estimate.get('percent') if estimate.get('percent') is not None else pair.get('confidence_percent')
    cases={c.get('assertion_id'):c for c in strategy.get('early_connections',[]) if c.get('assertion_id')}
    selected=[]
    for a in assessments:
     if a.get('publication_status')!='approved' or not a.get('working_selection'):continue
     for child,v in a.get('perspectives',{}).items():
      if v.get('relationship')=='father':selected.append((child,next(i for i in a['people'] if i!=child),a))
    if args.scope=='all-unconfident':
     candidates=[(e['child'],e['father'],by_assertion.get(e.get('assertion_id'),{})) for e in edges if e['status'] not in CONFIDENT]
    elif args.scope=='unrated':
     candidates=[(e['child'],e['father'],by_assertion.get(e.get('assertion_id'),{})) for e in retained if e['child'] in cohort and reviewed_percent(e) is None and is_named_father_name(e.get('father_name'))]
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
     estimate=estimates.get((child,father),{})
     row['confidence_percent']=reviewed_percent(pair)
     if estimate.get('percent') is not None:
      row['status']=estimate.get('assessment_status') or row.get('status')
      row['assertion_id']=row.get('assertion_id') or estimate.get('assertion_id')
      row['source_ids']=estimate.get('source_ids') or row['source_ids']
     row['public_confidence_percent']=pair.get('confidence_percent')
     row['public_status']=pair.get('status')
     case=cases.get(row['assertion_id'],{})
     row.update(dispatch_context(a,estimates.get((child,father)),case,
                                 plan=person_plan(root.parent,child),father=father))
     rows.append(row)
    print_rows(rows,args)


if __name__ == '__main__':
    main()
