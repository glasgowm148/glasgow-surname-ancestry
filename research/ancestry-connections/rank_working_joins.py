"""Rank paternal links by fixed-1850-cohort connectivity impact.

Run from the repository root: .venv/bin/python research/ancestry-connections/rank_working_joins.py
Use --scope all-unconfident to include older tree attachments.
Impact counts dependent connected pairs, never confidence or new genealogical joins.
Nested link impacts overlap and must not be summed. Counts concern retained profiles,
not independently verified unique people. The existing selected-only default is retained.
"""
from collections import defaultdict
from pathlib import Path
import argparse,json,sys
sys.path.insert(0,str(Path.cwd()))
from tools.branch_connectivity import load_public_nodes,CONFIDENT
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument("--scope",choices=["selected","all-unconfident"],default="selected",help="Include older tree attachments as well as selected hypotheses")
args=parser.parse_args()
root=Path('www');strategy=json.load(open('research/ancestry-connections/strategy.json'));nodes,edges,quality=load_public_nodes(root,set(strategy['variants']));cohort=set(json.load(open('www/data/ancestry-connectivity.json'))['cohorts']['1850']['working']['cohort_ids']);parents={e['child']:e['father'] for e in edges};eligible=set(cohort);stack=list(cohort)
while stack:
 father=parents.get(stack.pop())
 if father in nodes and father not in eligible and (nodes[father].get('birth_year') is None or nodes[father]['birth_year']<=1850):
  eligible.add(father);stack.append(father)
graph=defaultdict(set)
for child,father in parents.items():
 if child in eligible and father in eligible:graph[child].add(father);graph[father].add(child)
def side(start,cut):
 seen={start};stack=[start]
 while stack:
  n=stack.pop()
  for other in graph[n]:
   if {n,other}==cut or other in seen:continue
   seen.add(other);stack.append(other)
 return seen
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
else:candidates=selected
by_pair={(e['child'],e['father']):e for e in edges}
for child,father,a in candidates:
 if parents.get(child)!=father or child not in eligible:continue
 c=side(child,{child,father});p=side(father,{child,father});assert not c&p
 n,m=len(c&cohort),len(p&cohort)
 row={'assertion_id':a.get('assertion_id') or by_pair[child,father].get('assertion_id'),'child':child,'father':father,'child_name':nodes[child]['name'],'father_name':nodes[father]['name'],'child_side':n,'parent_side':m,'cross_pairs':n*m,'evidence_grade':a.get('evidence_grade'),'source_ids':a.get('source_ids',[]),'links':a.get('analysis_links',[])}
 if args.scope=='all-unconfident':row.update(status=by_pair[child,father]['status'],selected_working_hypothesis=bool(a.get('working_selection')),cohort_year=nodes[child].get('year'),year_basis=nodes[child].get('year_basis'),first_record_year=nodes[child].get('first_record_year'))
 rows.append(row)
rows.sort(key=lambda r:(-r['cross_pairs'],r['child'],r['father']))
print(json.dumps(rows,ensure_ascii=False,indent=2))
