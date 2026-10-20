#!/usr/bin/env python3
"""Reproducible browser gates; --fixture-smoke needs no private/generated datasets."""
from __future__ import annotations
import argparse
from functools import partial
from contextlib import contextmanager
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import threading

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
# A local Chrome is used when present; GLASGOW_BROWSER_EXECUTABLE selects another
# Chromium build, otherwise Playwright's managed browser is launched.
CHROME = Path(os.environ.get('GLASGOW_BROWSER_EXECUTABLE', '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'))
AXE = ROOT/'tests/vendor/axe-core-4.x/axe.min.js'
OBSERVERS = """window.auditTasks=[];window.auditCLS=0;
new PerformanceObserver(l=>{for(const e of l.getEntries())auditTasks.push(e.duration)}).observe({type:'longtask',buffered:true});
new PerformanceObserver(l=>{for(const e of l.getEntries())if(!e.hadRecentInput)auditCLS+=e.value}).observe({type:'layout-shift',buffered:true});"""


def fixture(site):
    from tools.catalogue_search_index import build
    from tools.catalogue_search_markup import hero_html, search_panel_html
    from tools.build_latest_findings import repair
    for folder in ['data','people','catalogue','about','latest-findings']:
        (site/folder).mkdir(parents=True, exist_ok=True)
    people = []
    for i in range(80):
        people.append({'id':f'example-{i}', 'name':f'Example Glasgow {i}',
                       'profile_ids':[f'Glasgow-{i+1}'], 'first_names':['Example'],
                       'last_names_at_birth':['Glasgow'], 'last_names_current':['Glasgow'],
                       'gender':'Male' if i%2 else 'Female', 'birth':'1800', 'birth_year':1800,
                       'birth_location':'Yorkshire', 'locations':['Yorkshire'], 'date_years':[1800],
                       'biography_text':'An inspected parish register.', 'has_profile':True,
                       'father':[{'id':'Glasgow-1000','name':'Father Glasgow','certainty':'confident'}],
                       'missing_mother':True, 'field_statuses':{'birth':'certain'}})
    (site/'data/catalogue-search-index.json').write_text(json.dumps(people))
    build(site)
    for source,dest in [('catalogue_search.js','people/search.js'),('catalogue-light.css','people/catalogue.css')]:
        shutil.copy(ROOT/'tools'/source, site/dest)
    template='<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Fixture</title></head><body><main>BODY</main></body></html>'
    body=hero_html(len(people))+search_panel_html('','','')+'<div id="catalogue-results" class="catalogue-results"></div>'
    html=template.replace('BODY',body).replace('</head>','<link rel="stylesheet" href="/people/catalogue.css"></head>').replace('</body>','<script src="/people/search.js"></script></body>')
    (site/'catalogue/index.html').write_text(html)
    (site/'people/glasgow-1.html').write_text(template.replace('BODY','<h1>Example Glasgow</h1>'))
    (site/'about/index.html').write_text(template.replace('BODY','<h1>About</h1>'))
    rows=[{'id':f'fixture-{i:03}', 'found_on':'2026-09-30','kind':'vital','status':'confirmed',
           'finding':f'Register entry {i} records a historical birth.', 'qualification':'',
           'people':[{'id':'Glasgow-1','name':'Example Glasgow','url':'https://www.wikitree.com/wiki/Glasgow-1'}],
           'sources':[{'title':'Inspected register','url':'https://example.org/register'}],
           'detail_url':'/people/glasgow-1.html'} for i in range(60)]
    ledger=site.parent/'ledger.json';ledger.write_text(json.dumps({'findings':rows}));repair(site,ledger)


class Quiet(SimpleHTTPRequestHandler):
    def log_message(self,*args):pass


@contextmanager
def serve(site):
    """Serve a built site on a free local port for the duration of the check."""
    server=ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=str(site)))
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:yield f'http://127.0.0.1:{server.server_port}'
    finally:server.shutdown();server.server_close();thread.join()


def check(base, fixture_mode=False):
    failures=[];measurements=[];errors=[]
    def require(value, message):
        if not value: failures.append(message)
    routes=['/catalogue/','/latest-findings/','/latest-findings/page/2/']
    if not fixture_mode:routes+=['/people/glasgow-951.html','/onetree/','/branches/',
                                '/records/','/places/','/compare.html?a=Gray-16804&b=Gray-25428']
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True, **({'executable_path':str(CHROME)} if CHROME.exists() else {}))
        for width in [320,390,1440]:
            context=browser.new_context(viewport={'width':width,'height':900})
            context.add_init_script(OBSERVERS)
            page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
            for route in routes:
                response=page.goto(base+route,wait_until='networkidle',timeout=60_000)
                require(response.status==200,f'{width} {route}: HTTP {response.status}')
                html_bytes=len(response.body())
                require(html_bytes<=500_000,f'{width} {route}: initial HTML exceeds 500 KB')
                if route=='/catalogue/':page.wait_for_function('window.GlasgowSearchMetrics',timeout=30_000)
                if route=='/onetree/':page.wait_for_function('window.GlasgowTree',timeout=30_000)
                if route.startswith('/compare.html'):
                    require(page.locator('#compare-status').inner_text()=='Comparing John Gray and John Gray',
                            'Reviewed Gray candidates did not compare')
                    require(page.locator('.compare-card').count()==3,'Comparison results are incomplete')
                metrics=page.evaluate("""()=>({width:innerWidth,scroll:document.documentElement.scrollWidth,dom:document.querySelectorAll('*').length,
                    cls:auditCLS,blocking:auditTasks.reduce((s,d)=>s+Math.max(0,d-50),0),maxTask:Math.max(0,...auditTasks),
                    ready:window.GlasgowSearchMetrics?.readyMs, data:performance.getEntriesByType('resource').filter(e=>/catalogue-search-/.test(e.name)).map(e=>({url:e.name,bytes:e.decodedBodySize}))})""")
                measurements.append({'width':width,'route':route,'htmlBytes':html_bytes,**metrics})
                require(metrics['scroll']<=width+1,f'{width} {route}: horizontal overflow {metrics["scroll"]}')
                require(metrics['dom']<6000,f'{width} {route}: initial DOM exceeds 6,000 elements')
                require(metrics['cls']<=.1,f'{width} {route}: CLS {metrics["cls"]:.3f} exceeds .1')
                require(metrics['blocking']<=500,f'{width} {route}: blocking time {metrics["blocking"]:.0f}ms exceeds 500ms')
                if route=='/catalogue/':
                    require(not any('catalogue-search-index.json' in e['url'] for e in metrics['data']), 'Catalogue fetched legacy full index')
                    require(sum(e['bytes'] for e in metrics['data'])<=6_000_000,'Initial catalogue payload exceeds 6 MB')
                    require(metrics['ready']<8000,'Catalogue search readiness exceeds 8s on unthrottled local preview')
                    require(not page.locator('#catalogue-filter-toggle-name').is_hidden(), 'Name filter is inaccessible')
                    page.locator('#catalogue-filter-toggle-name').click()
                    require(page.locator('#catalogue-filter-panel-name').is_visible(),'Name panel did not open')
                    page.keyboard.press('Escape')
                    page.locator('#catalogue-query').fill('Example' if fixture_mode else 'Alexander')
                    page.locator('#catalogue-search').evaluate('(f)=>f.requestSubmit()')
                    page.wait_for_function("document.querySelector('#catalogue-results-count').dataset.state==='ready'")
                    require(page.locator('.catalogue-results-table tbody tr').count()>0,'Search produced no expected results')
                page.add_script_tag(path=str(AXE))
                violations=page.evaluate("async()=> (await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21a','wcag21aa']}})).violations.filter(v=>['critical','serious'].includes(v.impact)).map(v=>({rule:v.id,count:v.nodes.length,targets:v.nodes.slice(0,2).map(n=>n.target)}))")
                require(not violations,f'{width} {route}: accessibility {violations}')
                if not fixture_mode and width==390 and route.startswith('/compare.html'):
                    screenshot=ROOT/'output/playwright/site-quality-compare-mobile.png'
                    screenshot.parent.mkdir(parents=True,exist_ok=True)
                    page.screenshot(path=str(screenshot))
            context.close()
        nojs=browser.new_context(java_script_enabled=False)
        page=nojs.new_page();page.goto(base+'/latest-findings/')
        require(page.locator('#lf-rows tr').count()==50,'No-JS findings root must contain 50 real rows')
        page.locator('#lf-next').click();require('/page/2/' in page.url,'No-JS pagination did not navigate')
        require(page.locator('#lf-rows tr').count()>0,'No-JS second page is empty')
        nojs.close();browser.close()
    require(not errors,'Browser errors: '+ '; '.join(sorted(set(errors))))
    return {'base':base,'measurements':measurements,'failures':failures}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url',help='check a running server instead of serving the built www/ folder')
    parser.add_argument('--fixture-smoke',action='store_true')
    args=parser.parse_args()
    if args.fixture_smoke:
        with tempfile.TemporaryDirectory() as directory:
            site=Path(directory)/'www';fixture(site)
            with serve(site) as base:result=check(base,True)
    elif args.base_url:
        result=check(args.base_url.rstrip('/'))
    else:
        if not (ROOT/'www/catalogue/index.html').is_file():
            parser.error('www/ has no built site; build it first or pass --base-url')
        with serve(ROOT/'www') as base:result=check(base)
    report=ROOT/'artifacts'/('site-quality-fixture-report.json' if args.fixture_smoke else 'site-quality-report.json');report.parent.mkdir(exist_ok=True)
    report.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'pages':len(result['measurements']),'failures':result['failures'],'report':str(report)}))
    return bool(result['failures'])


if __name__=='__main__':raise SystemExit(main())
