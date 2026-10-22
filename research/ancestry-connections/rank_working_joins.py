"""Rank paternal links by fixed-1850-cohort connectivity impact.

Run from the repository root: .venv/bin/python research/ancestry-connections/rank_working_joins.py
Use --scope all-unconfident to include older tree attachments.
Use --scope unrated to prioritise individual-rating coverage, including
inherited confident marks that have no reviewed percentage.
Coverage ranks the child-side branch size first; the other modes rank
dependent connected pairs. These are separate measures of research impact.
Impact counts dependent connected pairs, never confidence or new genealogical joins.
Nested link impacts overlap and must not be summed. Counts concern retained profiles,
not independently verified unique people. The existing selected-only default is retained.
"""
from pathlib import Path
import argparse,json,sys
sys.path.insert(0,str(Path.cwd()))
from tools.branch_connectivity import load_public_nodes,CONFIDENT,paternal_link_impacts
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument("--scope",choices=["selected","all-unconfident","unrated"],default="selected",help="Selected hypotheses, all unconfident attachments, or all individually unrated links")
parser.add_argument("--sort",choices=["working-pairs","confident-gain"],default="working-pairs",help="All dependent working pairs, or immediate confident-pair gain from upgrading this link alone")
args=parser.parse_args()
root=Path('www');strategy=json.load(open('research/ancestry-connections/strategy.json'));nodes,edges,quality=load_public_nodes(root,set(strategy['variants']));cohort=set(json.load(open('www/data/ancestry-connectivity.json'))['cohorts']['1850']['working']['cohort_ids']);parents={e['child']:e['father'] for e in edges}
impacts={(r['child'],r['father']):r for r in paternal_link_impacts(nodes,edges,1850,cohort)}
rows=[]
assessments=json.load(open('research/relationship_assessments.json'))
by_assertion={a.get('assertion_id'):a for a in assessments}
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
 rows.append(row)
if args.sort=='confident-gain':
 rows.sort(key=lambda r:(-r['confident_pair_gain'],-r['cross_pairs'],r['child'],r['father']))
elif args.scope=='unrated':
 rows.sort(key=lambda r:(-r['child_side'],-r['cross_pairs'],r['child'],r['father']))
else:rows.sort(key=lambda r:(-r['cross_pairs'],r['child'],r['father']))
print(json.dumps(rows,ensure_ascii=False,indent=2))
