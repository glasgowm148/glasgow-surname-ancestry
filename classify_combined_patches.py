import json, concurrent.futures, re
from pathlib import Path
from src.wikitree_family_export import post_wikitree
path=Path('/tmp/groni-existing-combined-live-patches.json'); d=json.loads(path.read_text())
ps=d['patches']
def get(p):
    try:
        r=post_wikitree({'action':'getProfile','key':p['profile_id'],'fields':'Id,Name,Manager,Managers'}).get('profile',{})
        return p['profile_id'],r
    except Exception as e:return p['profile_id'],{'error':str(e)}
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex: got=dict(ex.map(get,ps))
managed=other=unknown=0
for p in ps:
    r=got.get(p['profile_id'],{})
    vals=[]
    for k in ('Manager','Managers'):
        v=r.get(k)
        if isinstance(v,list): vals += [str(x) for x in v]
        elif v: vals.append(str(v))
    s=' '.join(vals)
    if '24779879' in s or 'Glasgow-933' in s: cls='managed'; managed+=1
    elif 'error' in r: cls='unknown'; unknown+=1
    else: cls='other'; other+=1
    p['manager_status']=cls
    p['manager_field']=vals
    # Concise normalized source language requested by parent.
    w=p['wikitext'].replace('; indexed details supplied 23 September 2026','')
    w=w.replace('indexed details supplied 23 September 2026','')
    w=re.sub(r'\n(== Sources ==)',r'\n\n\1',w,count=1)
    p['wikitext']=w
d['summary']['manager_managed']=managed; d['summary']['manager_other']=other; d['summary']['manager_unknown']=unknown
path.write_text(json.dumps(d,indent=2))
print(json.dumps({**d['summary']}))
