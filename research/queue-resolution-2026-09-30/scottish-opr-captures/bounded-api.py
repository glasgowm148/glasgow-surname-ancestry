import ast,json,urllib.request,urllib.parse,time
from pathlib import Path
ROOT=Path('/Users/m/wikitree-api-scrape'); OUT=ROOT/'research/queue-resolution-2026-09-30/scottish-opr-captures'
s=ast.parse((ROOT/'src/wikitree_family_export.py').read_text());v={}
for n in s.body:
 if isinstance(n,ast.Assign):
  for t in n.targets:
   if isinstance(t,ast.Name) and t.id in ['WIKITREE_API_URL','WIKITREE_REQUEST_HEADERS']:v[t.id]=ast.literal_eval(n.value)
def api(d):
 time.sleep(1.1)
 return json.load(urllib.request.urlopen(urllib.request.Request(v['WIKITREE_API_URL'],headers=v['WIKITREE_REQUEST_HEADERS'],data=urllib.parse.urlencode({'appId':'GlasgowSurnameResearch',**d}).encode()),timeout=40))[0]
def search(first,last,year=None):
 params={'FirstName':first,'LastName':last}
 if year:params.update(BirthDate=f'{year-25}-00-00',dateSpread='20',dateInclude='neither')
 pages=[];rows=[];start=0
 while True:
  r=api({'action':'searchPerson',**params,'limit':'100','start':str(start),'sort':'birth'})
  ps=r.get('matches',[]);pages.append({'start':start,'status':r.get('status'),'total':r.get('total'),'returned':len(ps)})
  rows.extend(p for p in ps if p.get('Privacy')==60 and not p.get('IsLiving') and (not p.get('BirthDate') or p['BirthDate'][:4]=='0000' or int(p['BirthDate'][:4])<=1700))
  start+=100
  if start>=int(r.get('total') or 0) or not ps:break
 result={'searched_on':'2026-09-30','params':params,'pages':pages,'public_historical_matches':rows}
 OUT.joinpath(first+'_'+last+str(year or '')+'.json').write_text(json.dumps(result))
 print(first,last,len(rows),[(p.get('Name'),p.get('FirstName'),p.get('BirthDate')) for p in rows],flush=True)
 return rows
