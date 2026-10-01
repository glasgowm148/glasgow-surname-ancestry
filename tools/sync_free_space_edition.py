#!/usr/bin/env python3
"""Pull public WikiTree sources for comparison, preserve local edits, prepare outgoing diffs.

No credentials and no WikiTree writes. Example:
  python tools/sync_free_space_edition.py --pull --limit 5
  python tools/sync_free_space_edition.py --import-remote 'Space:Glasgow DNA' remote.wiki
  python tools/sync_free_space_edition.py --accept-remote 'Space:Glasgow DNA'
  python tools/sync_free_space_edition.py --prepare
"""
from __future__ import annotations
import argparse,datetime as dt,difflib,json,sys,time
from pathlib import Path
from urllib.parse import quote
import requests
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tools.free_space_edition import EDITION,STATE,digest,public_text,key
from tools.public_privacy import from_sources


def assessment(local,remote,baseline=None):
    if local==remote:return 'Both editions match'
    if baseline is None:return 'First comparison: review differences'
    if local==baseline:return 'WikiTree changed; local transfer ready for review'
    if remote==baseline:return 'Local changes ready for WikiTree review'
    return 'Both editions changed: resolve the conflict'


def fetch_remote(page_id,session=None):
    session=session or requests.Session();page_id=page_id.replace(' ','_')
    r=session.get('https://api.wikitree.com/api.php',params={'action':'getProfile','key':page_id,'fields':'Title,Privacy,Touched','appId':'GlasgowLocalEdition'},timeout=25);r.raise_for_status();item=r.json()[0]
    if item.get('status') not in (0,'0','',None):raise ValueError('WikiTree API: '+str(item.get('status')))
    profile=item.get('profile',{})
    if int(profile.get('Privacy',0))<50:raise ValueError('WikiTree page is not public')
    title=profile.get('Title',{}).get('PrefixedText',page_id)
    r=session.get('https://www.wikitree.com/index.php',params={'title':title.replace(' ','_'),'action':'raw'},timeout=25)
    metadata={'remoteTouched':profile.get('Touched',''),'checkedAt':dt.datetime.now(dt.timezone.utc).isoformat(),'sourceUrl':'https://www.wikitree.com/index.php?title='+quote(title.replace(' ','_'))+'&action=raw'}
    if r.status_code!=200 or not r.text.strip() or r.headers.get('content-type','').lower().startswith('text/html'):
        return None,{**metadata,'status':'WikiTree text unavailable; local edition preserved','error':f'Public source request returned HTTP {r.status_code}; no source was imported.'}
    return r.text,metadata


def compare(page,raw,state,metadata=None):
    policy=from_sources();remote,removed=public_text(raw,policy,page['wikitreeId']);local=(ROOT/page['editionFile']).read_text();previous=state.get('basePublicText')
    return {**state,**(metadata or {}),'status':assessment(local,remote,previous),'remotePublicText':remote,'remotePublicHash':digest(remote),'localHash':digest(local),'checkedAt':dt.datetime.now(dt.timezone.utc).isoformat(),'omittedRemotePassages':removed,'sourceRetrievedAt':dt.datetime.now(dt.timezone.utc).isoformat(),'basePublicText':remote if local==remote else previous,'baseRemoteHash':digest(previous) if previous is not None else None,'error':''}


def prepare(pages,state):
    output=ROOT/'research/free-space-pages/outgoing';output.mkdir(parents=True,exist_ok=True);rows=[]
    for page in pages:
        local=(ROOT/page['editionFile']).read_text();saved=state.get('pages',{}).get(page['wikitreeId'],{});remote=saved.get('remotePublicText')
        replacement=output/(page['slug']+'.wiki');replacement.write_text(local)
        diff=output/(page['slug']+'.diff')
        text='Remote text has not been retrieved. Review the current WikiTree page before saving this local draft.\n' if remote is None else '\n'.join(difflib.unified_diff(remote.splitlines(),local.splitlines(),fromfile='WikiTree',tofile='Local edition',lineterm=''))+'\n'
        diff.write_text(text);rows.append({'wikitreeId':page['wikitreeId'],'status':saved.get('status','Remote text not checked'),'replacement':str(replacement.relative_to(ROOT)),'diff':str(diff.relative_to(ROOT)),'liveSave':False})
    (output/'index.json').write_text(json.dumps({'pages':rows,'scope':'Prepared public-safe replacements only; no live WikiTree edits.'},ensure_ascii=False,indent=2)+'\n')
    return len(rows)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--pull',action='store_true');parser.add_argument('--page',action='append',default=[]);parser.add_argument('--limit',type=int,default=5);parser.add_argument('--all',action='store_true');parser.add_argument('--import-remote',nargs=2,metavar=('WIKITREE_ID','FILE'));parser.add_argument('--accept-remote');parser.add_argument('--prepare',action='store_true');args=parser.parse_args()
    if not EDITION.exists():parser.error('Build the local edition first')
    pages=list(json.loads(EDITION.read_text())['pages'].values());state=json.loads(STATE.read_text()) if STATE.exists() else {'schema_version':1,'pages':{}}
    if args.page:pages=[p for p in pages if key(p['wikitreeId']) in {key(i) for i in args.page}]
    if args.pull:
        session=requests.Session()
        for p in pages if args.all else pages[:args.limit]:
            old=state['pages'].get(p['wikitreeId'],{})
            try:
                raw,metadata=fetch_remote(p['wikitreeId'],session)
                state['pages'][p['wikitreeId']]=compare(p,raw,old,metadata) if raw is not None else {**old,**metadata}
            except (requests.RequestException,ValueError,KeyError) as e:
                state['pages'][p['wikitreeId']]={**old,'status':'Pull failed; local edition preserved','error':str(e)[:250],'checkedAt':dt.datetime.now(dt.timezone.utc).isoformat()}
            print(p['wikitreeId']+': '+state['pages'][p['wikitreeId']]['status']);time.sleep(1)
    if args.import_remote:
        pid,path=args.import_remote;p=next((p for p in pages if key(p['wikitreeId'])==key(pid)),None)
        if not p:parser.error('Unknown local page')
        state['pages'][p['wikitreeId']]=compare(p,Path(path).read_text(),state['pages'].get(p['wikitreeId'],{}),{'sourceUrl':p['viewUrl'],'importMethod':'User supplied current WikiTree source; verify its date before saving.'})
    if args.accept_remote:
        p=next((p for p in pages if key(p['wikitreeId'])==key(args.accept_remote)),None)
        if not p:parser.error('Unknown local page')
        current=state['pages'].get(p['wikitreeId'],{});remote=current.get('remotePublicText')
        if remote is None:parser.error('No retrieved remote text available; local text unchanged')
        destination=ROOT/p['editionFile'];backup=ROOT/'.cache/free-space-reconciliation'/f'{p["slug"]}-{dt.datetime.now().strftime("%Y%m%d%H%M%S%f")}.wiki';backup.parent.mkdir(parents=True,exist_ok=True);backup.write_text(destination.read_text());destination.write_text(remote);current['status']='Both editions match';current['localHash']=digest(remote);current['basePublicText']=remote
    STATE.write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n')
    if args.prepare:print(f'Prepared {prepare(pages,state)} local replacements; no WikiTree writes.')
    if not any((args.pull,args.import_remote,args.accept_remote,args.prepare)):parser.print_help()

if __name__=='__main__':main()
