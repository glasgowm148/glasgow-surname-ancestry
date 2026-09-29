#!/usr/bin/env python3
"""Offline browser regression tests. Requires Playwright and Chromium."""
import hashlib,json,os,time
from pathlib import Path
from playwright.sync_api import sync_playwright
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
PUBLIC_DIR=ROOT/'www'/'onetree'/'glasgow-one-tree-polished-3'
OUT=HERE/'previews';OUT.mkdir(exist_ok=True)
HTML=(PUBLIC_DIR/'index.html').read_text()
def no_overlap(boxes):
 for i,a in enumerate(boxes):
  for b in boxes[i+1:]:
   if a.get('id')==b.get('id'):continue
   if min(a['x']+a['w'],b['x']+b['w'])-max(a['x'],b['x'])>0.25 and min(a['y']+a['h'],b['y']+b['h'])-max(a['y'],b['y'])>0.25:return [a,b]
 return None
report={'errors':[],'overviewStates':0,'familyStates':0,'labelCollisions':[],'cardCollisions':[],'exportRoundTrip':None}
with sync_playwright() as pw:
 browser=pw.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH','/usr/bin/chromium'),headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
 page=browser.new_page(viewport={'width':1600,'height':1080},device_scale_factor=1)
 page.on('pageerror',lambda e:report['errors'].append(str(e)))
 start=time.perf_counter();page.set_content(HTML);page.wait_for_function('!!window.GlasgowTree');report['startupSeconds']=round(time.perf_counter()-start,3)
 report['validation']=page.evaluate('GlasgowTree.validate()');report['audit']=page.evaluate('GlasgowTree.familyAudit()')
 page.wait_for_timeout(200);page.screenshot(path=str(OUT/'whole-tree.png'))
 for width,height in [(1600,1080),(1024,850),(390,844)]:
  page.set_viewport_size({'width':width,'height':height});page.wait_for_timeout(100);page.evaluate('GlasgowTree.home();GlasgowTree.fit()');page.wait_for_timeout(70)
  home=page.evaluate('GlasgowTree.view().cam')
  for mode in ['first','journeys']:
   page.evaluate('(m)=>GlasgowTree.colourMode(m)',mode)
   for scale in [1,2.2,5,12]:
    for dx,dy in [(0,0),(-150,100),(180,-100)]:
     page.evaluate('(c)=>{GlasgowTree.setCamera(c);GlasgowTree.drawNow()}',{'x':home['x']+dx,'y':home['y']+dy,'k':home['k']*scale})
     labels=page.evaluate('GlasgowTree.labels()');bad=no_overlap(labels);report['overviewStates']+=1
     if bad:report['labelCollisions'].append({'width':width,'mode':mode,'scale':scale,'boxes':bad})
  page.evaluate('GlasgowTree.home();GlasgowTree.focusEarly()');page.wait_for_timeout(320)
  if width==390:page.screenshot(path=str(OUT/'early-mobile.png'))
  for pid in ['McCook-217','Glasgow-1026','Graham-38221','Brade-232','Smith-374110','Glasgow-1095','Glasgow-1729','Glasgow-3970','Glasgow-591']:
   for lens in ['descendants','ancestors','close']:
    page.evaluate('([id,lens])=>GlasgowTree.readFamily(id,lens)',[pid,lens]);page.wait_for_timeout(10)
    nodes=page.evaluate('[...GlasgowTree.positions().values()].map(n=>({id:n.id,x:n.x,y:n.y,w:232,h:76}))')
    assert len(nodes)==len({n['id'] for n in nodes})
    bad=no_overlap(nodes);report['familyStates']+=1
    if bad:report['cardCollisions'].append({'width':width,'id':pid,'lens':lens,'boxes':bad})
    if pid=='McCook-217':
     edges=page.evaluate('GlasgowTree.sceneEdges()')
     assert not any(e['type']=='recorded' and {e['a'],e['b']}=={'McCook-217','Glasgow-1026'} for e in edges)
     if lens=='ancestors':assert len(nodes)==1
     else:
      positions={n['id']:n for n in nodes};assert positions['McCook-217']['x']==positions['Glasgow-1026']['x']
   if width==390 and pid=='McCook-217':
    page.evaluate("GlasgowTree.readFamily('McCook-217')");page.wait_for_timeout(300);page.screenshot(path=str(OUT/'ann-mobile.png'))
 # Representative examples and opening the notebook's new ancestry action.
 page.set_viewport_size({'width':1600,'height':1080});page.wait_for_timeout(150)
 page.evaluate("GlasgowTree.readFamily('McCook-217')");page.wait_for_timeout(350);page.screenshot(path=str(OUT/'ann-and-william.png'))
 assert 'JOINED THROUGH A RECORDED SPOUSE' in page.locator('#detail-content').inner_text()
 page.locator('[data-action="ancestors"][data-id="Glasgow-1026"]').click();page.wait_for_timeout(350)
 assert page.evaluate('GlasgowTree.view().readingRoot')=='Glasgow-1026';page.screenshot(path=str(OUT/'william-ancestors.png'))
 page.evaluate('GlasgowTree.home();GlasgowTree.fit()');page.wait_for_timeout(150)
 report['benchmarkMilliseconds']=page.evaluate('GlasgowTree.benchmark()')
 frames=page.evaluate('GlasgowTree.stats().frames');page.wait_for_timeout(400);report['idleFrames']=page.evaluate('GlasgowTree.stats().frames')-frames
 page.locator('[data-view="branches"]').first.click();page.wait_for_timeout(100);page.screenshot(path=str(OUT/'branch-view.png'))
 assert 'McCook-217' not in page.evaluate('GlasgowTree.branchAnchors()')
 assert 'Glasgow-1095' in page.evaluate('GlasgowTree.branchAnchors()')
 page.evaluate('GlasgowTree.traceDNA()');assert 'FT20271' in page.locator('#dna-view').inner_text()
 page.evaluate("window._savedBlobs=[];window._origCreateURL=URL.createObjectURL;URL.createObjectURL=b=>{window._savedBlobs.push(b);return window._origCreateURL(b)};void 0")
 page.evaluate('GlasgowTree.exportHtml()')
 exported=page.evaluate('window._savedBlobs.at(-1).text()');assert len(exported)>4_000_000
 original=page.evaluate('JSON.stringify(GlasgowTree.data)')
 page2=browser.new_page(viewport={'width':1200,'height':900});page2.on('pageerror',lambda e:report['errors'].append('roundtrip: '+str(e)))
 page2.set_content(exported);page2.wait_for_function('!!window.GlasgowTree')
 report['exportRoundTrip']={'modelIdentical':page2.evaluate('JSON.stringify(GlasgowTree.data)')==original,'validation':page2.evaluate('GlasgowTree.validate()'),'annAttachment':page2.evaluate("GlasgowTree.familyAttachment('McCook-217')")}
 # CSV headers explicitly distinguish spouse attachments from parents.
 page.locator('#export-btn').click();page.locator('[data-export="csv"]').click()
 csv_text=page.evaluate('window._savedBlobs.at(-1).text()');header=csv_text.splitlines()[0];assert 'Layout link type' in header
 ann_row=next(row for row in csv_text.splitlines() if row.startswith('"McCook-217"'));assert '"Glasgow-1026","partner"' in ann_row
 report['csvPartnerTyped']=True
 browser.close()
(OUT/'browser-qa.json').write_text(json.dumps(report,indent=2))
print(json.dumps({k:v for k,v in report.items() if k not in ['exportRoundTrip']},indent=2))
assert not report['errors'],report['errors'];assert not report['labelCollisions'],report['labelCollisions'];assert not report['cardCollisions'],report['cardCollisions']
assert report['idleFrames']==0;assert report['exportRoundTrip']['modelIdentical']
print('All browser checks passed.')
