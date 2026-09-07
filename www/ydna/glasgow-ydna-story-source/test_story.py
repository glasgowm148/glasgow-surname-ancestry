"""Narrative edition checks. Requires playwright and a Chromium installation.

The environment may block URL/file navigation. The HTML is injected unchanged;
all interactions, calculations and exports run in the browser. This does not
claim a separate local-file or hosted deployment test.
"""
import json, os, shutil, re
from pathlib import Path
from collections import Counter
from playwright.sync_api import sync_playwright
R=Path(__file__).resolve().parent
O=R/'test-output-story';O.mkdir(exist_ok=True)
report={'browser':'Chromium','load':'Document injection; file and URL navigation blocked by environment policy', 'checks':[], 'responsive':[], 'errors':[]}
def check(ok,name):
 report['checks'].append({'test':name,'passed':bool(ok)})
 if not ok: print('FAILED',name)
def nav(page,view):
 # Exercise the same navigation handler as the actual link, even at narrow widths.
 page.evaluate('(v)=>document.querySelector(`.main-nav a[data-view="${v}"]`).click()',view)
def data(page):return page.evaluate('JSON.parse(document.getElementById("research-data").textContent)')
with sync_playwright() as p:
 b=p.chromium.launch(executable_path=os.environ.get('CHROMIUM_EXECUTABLE') or shutil.which('chromium'),args=['--no-sandbox'])
 page=b.new_page(viewport={'width':1440,'height':1000},device_scale_factor=1)
 page.set_default_timeout(5000)
 page.on('pageerror',lambda e:report['errors'].append(str(e)))
 page.set_content((R/'index.html').read_text(),wait_until='domcontentloaded')
 check(page.evaluate('glasgowYDNA.getActiveView()')=='overview','Story opens first')
 check(page.locator('h1:visible').count()==1,'One visible page heading')
 check(page.locator('.story-chapter').count()==5,'Five continuous story chapters')
 check(page.evaluate('glasgowYDNA.counts.roots===8 && glasgowYDNA.counts.matches===17 && glasgowYDNA.counts.core===7'),'Counts retain 8 root groups, 17 matches, 7 core Big Y tests')
 check(page.evaluate('glasgowYDNA.counts.integratedEvidenceTables===13'),'All 13 retained detailed tables are registered contextually')
 check(page.evaluate('document.documentElement.dataset.theme')=='light','Reading theme defaults to light')
 ids=page.locator('[id]').evaluate_all('(els)=>els.map(e=>e.id)')
 check(len(ids)==len(set(ids)),'No duplicate HTML IDs')
 bad=page.evaluate('''()=>Array.from(document.querySelectorAll('[aria-controls]')).filter(e=>e.getAttribute('aria-controls').split(/\\s+/).some(id=>!document.getElementById(id))).map(e=>e.outerHTML)''')
 check(not bad,'Every aria-controls target exists')
 page.locator('.hero-cta a').first.click();page.wait_for_timeout(100)
 box=page.locator('#story-arrival').bounding_box()
 check(page.evaluate('glasgowYDNA.getActiveView()')=='overview' and box['y']>=135 and box['y']<350,'Chapter jump stays in story and clears sticky headers')
 for branch,needle in [('churnside','second view'),('glasgow','path towards'),('wright','geographic anchor')]:
  page.click('[data-story-branch="'+branch+'"]')
  check(needle in page.locator('#story-fork-reading').inner_text(),f'Branch explanation: {branch}')
  check(page.locator('[data-story-branch][aria-pressed="true"]').count()==1,f'One selected branch: {branch}')
 for mode,count in [('shared',3),('signature',3),('james',1)]:
  page.click('[data-inherit="'+mode+'"]')
  check(page.locator('.inherit-son.highlighted').count()==count,f'Inheritance layer {mode} highlights correct son-lines')
  check(len(page.locator('#inheritance-reading').inner_text())>180,f'Inheritance layer {mode} has full explanation')
 page.locator('[data-inherit="shared"]').focus();page.keyboard.press('Space')
 check(page.locator('[data-inherit="shared"]').get_attribute('aria-pressed')=='true','Inheritance buttons keyboard-operable')
 for a,bid,expected in [('B580327','churnside','R-FT4811'),('brown','999763','R-FT4811'),('churnside','brown','R-FTA30932'),('B580327','farrier-a',None)]:
  check(page.evaluate('([a,b])=>glasgowYDNA.sharedBranch(a,b)',[a,bid])==expected,f'Shared branch {a} / {bid}: {expected}')
 nav(page,'origins')
 for mode,needle in [('norman','Anglo-Norman'),('early','already in Britain'),('norse','Norse-era crossing'),('multiple','separate movements')]:
  page.click('[data-route-model="'+mode+'"]')
  check(needle in page.locator('#route-model-reading').inner_text(),f'Route model opens: {mode}')
  check(page.locator('[data-route-model][aria-pressed="true"]').count()==1,f'One selected route model: {mode}')
  check('Best next comparison:' in page.locator('#route-model-reading').inner_text(),f'Route {mode} gives a discriminating next comparison')
 check(page.locator('#origins .medieval-child').count()==3,'Three medieval child lines displayed')
 check(page.locator('#origin-clock-rows .clock-row').count()==7,'Seven source date rows')
 check(page.locator('#origin-clock-rows .clock-range').count()==5,'Five date ranges; no fabricated intervals for two plain labels')
 for stage in ['north-sea','early-medieval','britain','scotland','ulster','atlantic']:
  page.click('[data-origin-stage="'+stage+'"]')
  check(page.evaluate('glasgowYDNA.getOriginStage()')==stage,f'Deep chapter opens: {stage}')
  check(len(page.locator('#origin-stage-panel').inner_text())>700,f'Deep chapter {stage} explains the evidence')
 page.click('[data-origin-step="-1"]');check(page.evaluate('glasgowYDNA.getOriginStage()')=='ulster','Historical chapter paging')
 nav(page,'compare')
 page.select_option('#kit-a','B580327');page.select_option('#kit-b','1002232')
 check(page.locator('.comparison-metric .metric-value').nth(0).inner_text()=='3 steps','Alexander–James J GD 3')
 check(page.locator('.comparison-metric .metric-value').nth(3).inner_text()=='7 vs 1 states','Directional counts A vs B')
 page.click('#swap-kits')
 check(page.locator('.comparison-metric .metric-value').nth(3).inner_text()=='1 vs 7 states','Swapping reverses directional counts')
 page.select_option('#kit-a','200475');page.select_option('#kit-b','999763')
 check(page.locator('.comparison-metric .metric-value').nth(0).inner_text()=='0 steps','True zero remains distinct from missing')
 check('SNP resolves James' in page.locator('#comparison-output').inner_text(),'Exact STR match explains complementary SNP resolution')
 page.select_option('#kit-a','henry-bigy');page.select_option('#kit-b','farrier-a')
 check(page.locator('.comparison-metric .metric-value').nth(0).inner_text()=='Not supplied','Unmeasured pair kept missing')
 values=page.evaluate('''()=>{const D=JSON.parse(document.getElementById('research-data').textContent),fails=[];for(const [pair,v] of Object.entries(D.pairs)){const [a,b]=pair.split('|');for(const [el,id] of [[document.getElementById('kit-a'),a],[document.getElementById('kit-b'),b]]){el.value=id;el.dispatchEvent(new Event('change',{bubbles:true}))}const text=document.querySelector('.comparison-metric .metric-value').textContent;if(text!==v.gd+' '+(v.gd===1?'step':'steps'))fails.push([pair,text,v.gd])}return {n:Object.keys(D.pairs).length,fails}}''')
 check(not values['fails'],f'All {values["n"]} supplied pairwise distances render correctly')
 nav(page,'roots')
 for f,n in [('linked',4),('candidate',4),('all',8)]:
  page.select_option('#root-filter',f);check(page.locator('#root-grid .root-card').count()==n,f'Root filter {f}: {n}')
 page.fill('#root-search','B580327');check(page.locator('#root-grid .root-card').count()==1,'Search by kit number')
 page.fill('#root-search','unfindable-blah');check(page.locator('#root-grid .empty-state').count()==1,'Root search empty state')
 page.fill('#root-search','');page.click('[data-roster="matches"]')
 for f,n in [('all',17),('core',6),('other-bigy',3),('str-only',8)]:
  page.select_option('#match-filter',f);check(page.locator('#matches-table tbody tr').count()==n,f'Match filter {f}: {n}')
 page.select_option('#match-filter','all');page.fill('#match-search','farrier')
 check(page.locator('#matches-table tbody tr').count()==3,'All three Farrier/Ferrier matches remain searchable')
 page.fill('#match-search','');page.click('#match-sort')
 check(page.locator('#matches-table tbody tr td').first.inner_text()=='10','Reverse sorting retained')
 nav(page,'snp-splits');before=json.dumps(data(page),sort_keys=True)
 for mode,needle in [('unknown','incomplete'),('positive','simplest'),('negative','reversion'),('mixed','discrepancy')]:
  page.select_option('#ft6135-scenario',mode);check(needle in page.locator('#ft6135-result').inner_text(),f'FT6135 scenario {mode} retains interpretation')
 check(before==json.dumps(data(page),sort_keys=True),'Scenario controls never alter the stored research data')
 nav(page,'str-network')
 for i in range(8):
  check(page.locator('#mst-network .net-node').count()==7 and page.locator('#mst-network .net-line').count()==6,f'Network arrangement {i+1}: seven tests, six edges')
  page.click('#tree-next')
 check(page.locator('#network-index').inner_text()=='1 / 8','Eight network alternatives cycle correctly')
 page.click('#distance-matrix [data-preset="B580327,1002232"]')
 check(page.evaluate('glasgowYDNA.getActiveView()')=='compare' and page.evaluate('glasgowYDNA.getSelection().b')=='1002232','Matrix cell selects and opens exact pair')
 nav(page,'mutation-tree');page.wait_for_timeout(80)
 check(page.locator('#branch-connectors path').count()>=10,'Genetic branch connectors render')
 page.click('[data-subview="pedigree"]');check(page.locator('#pedigree-pane').is_visible(),'Pedigree detail opens')
 page.click('[data-subview="snp"]');check(page.locator('#snp-pane').is_visible(),'DNA tree restored')
 nav(page,'next-steps')
 for goal,needle in [('alexander','1002232'),('surname','254947'),('family','FT6135'),('origins','FT4811')]:
 page.select_option('#research-goal',goal);check(needle in page.locator('.action-card').first.inner_text(),f'Goal {goal} yields appropriate priority')
 check(page.locator('.retained-table').count()==12,'Twelve retained tables render beside their subject; matches use the active table')
 check(page.locator('.retained-table tbody tr').count()==61,'All 61 non-match retained rows render contextually')
 check(page.locator('#matches-table tbody tr').count()==17,'All 17 match rows render in the active matches table')
 for host,view in [('family-str-evidence','mutation-tree'),('str-source-matrix','str-network'),('sapp-group-evidence','sapp-model'),('vcf-call-evidence','snp-splits'),('line-status-evidence','next-steps')]:
  check(page.locator('#'+host).evaluate('(e,v)=>e.closest(".view").id===v',view),f'{host} belongs to {view}')
 check('Not the current priority ranking.' in page.locator('.archival-detail').inner_text(),'Original fixed ranking is visibly superseded')
 nav(page,'sources')
 with page.expect_download() as d:page.locator('#sources [data-download="json"]').click()
 d.value.save_as(O/'export.json')
 check(json.loads((O/'export.json').read_text())['metadata']['revision']=='story-documentary-refresh-2026-09-07','JSON export contains documentary-refresh edition metadata')
 nav(page,'str-network')
 with page.expect_download() as d:page.locator('[data-download="matrix"]').click()
 d.value.save_as(O/'matrix.csv')
 check(len((O/'matrix.csv').read_text().splitlines())==8,'Matrix CSV export has header and seven rows')
 # Exercise all ten views at seven screen widths and two themes.
 views=['overview','origins','compare','mutation-tree','str-network','snp-splits','sapp-model','roots','next-steps','sources']
 for theme in ['light','dark']:
  if page.evaluate('document.documentElement.dataset.theme')!=theme:page.click('#theme-button')
  check(page.evaluate('document.documentElement.dataset.theme')==theme,f'Theme switches to {theme}')
  for width in [320,360,390,768,1024,1440,1920]:
   page.set_viewport_size({'width':width,'height':900 if width>768 else 844})
   for view in views:
    nav(page,view)
    dimensions=page.evaluate('({window:innerWidth,document:document.documentElement.scrollWidth,body:document.body.scrollWidth})')
    ok=dimensions['document']<=width+1 and dimensions['body']<=width+1
    report['responsive'].append({'theme':theme,'width':width,'view':view,'passed':ok,**dimensions})
    if not ok: print('OVERFLOW',theme,width,view,dimensions)
 # Check actual mobile menu and selection rather than only dispatching links.
 page.set_viewport_size({'width':390,'height':844});nav(page,'overview')
 page.click('#menu-button');check(page.locator('#menu-button').get_attribute('aria-expanded')=='true','Mobile menu opens')
 page.locator('.main-nav [data-view="origins"]').click();check(page.locator('#menu-button').get_attribute('aria-expanded')=='false','Navigation closes mobile menu')
 page.click('#menu-button');page.keyboard.press('Escape');check(page.locator('#menu-button').get_attribute('aria-expanded')=='false','Escape closes mobile menu')
 check(not report['errors'],'No uncaught JavaScript errors')
 b.close()
report['summary']={'checks':len(report['checks']), 'failed_checks':sum(not x['passed'] for x in report['checks']), 'responsive_cases':len(report['responsive']), 'failed_layout_cases':sum(not x['passed'] for x in report['responsive'])}
(R/'story-test-report.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report['summary'],indent=2))
if report['summary']['failed_checks'] or report['summary']['failed_layout_cases'] or report['errors']:raise SystemExit(1)
