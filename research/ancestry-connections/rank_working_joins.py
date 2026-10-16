"""Rank existing selected father hypotheses by fixed-1850-cohort connectivity impact.

Run from the repository root: .venv/bin/python research/ancestry-connections/rank_working_joins.py
Impact counts dependent connected pairs, never confidence or new genealogical joins.
"""
from collections import defaultdict
from pathlib import Path
import json,sys
sys.path.insert(0,str(Path.cwd()))
from tools.branch_connectivity import load_public_nodes
root=Path('www');strategy=json.load(open('research/ancestry-connections/strategy.json'));nodes,edges,quality=load_public_nodes(root,set(strategy['variants']));cohort=set(json.load(open('www/data/ancestry-connectivity.json'))['cohorts']['1850']['working']['cohort_ids']);parents={e['child']:e['father'] for e in edges};eligible=set(cohort);stack=list(cohort)
while stack:
 father=parents.get(stack.pop())
 if father in nodes and father not in eligible:
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
for a in json.load(open('research/relationship_assessments.json')):
 if a.get('publication_status')!='approved' or not a.get('working_selection'):continue
 for child,v in a.get('perspectives',{}).items():
  if v.get('relationship')!='father':continue
  father=next(i for i in a['people'] if i!=child)
  if parents.get(child)!=father:continue
  c=side(child,{child,father});p=side(father,{child,father});assert not c&p
  n,m=len(c&cohort),len(p&cohort)
  rows.append({'assertion_id':a['assertion_id'],'child':child,'father':father,'child_name':nodes[child]['name'],'father_name':nodes[father]['name'],'child_side':n,'parent_side':m,'cross_pairs':n*m,'evidence_grade':a.get('evidence_grade'),'source_ids':a.get('source_ids',[]),'links':a.get('analysis_links',[])})
rows.sort(key=lambda r:(-r['cross_pairs'],r['child'],r['father']))
print(json.dumps(rows,ensure_ascii=False,indent=2))
