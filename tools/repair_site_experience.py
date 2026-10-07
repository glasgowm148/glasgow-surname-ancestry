#!/usr/bin/env python3
"""Targeted presentation repairs, without rebuilding the research catalogue."""
from collections import Counter, defaultdict
from html import escape, unescape
import json
from pathlib import Path
import re
import runpy

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / 'www'
TOPICS = (
    ('early-ireland', 'Ireland & Ulster', {'ireland'}, 'Start with the early Irish records, then explore the households of Lisnagaver, Rasharkin, Larne and Kilwaughter. Follow each local study into its people, original records and open questions.'),
    ('scottish-families', 'Scotland', {'scotland'}, 'Explore the early Scottish bearers, Edinburgh testaments and later family groups. Follow the spouses, children and neighbours named by the documents.'),
    ('north-american-families', 'United States & Canada', {'america', 'canada'}, 'Browse the families recorded in North America, from early Atlantic households to later generations. Each family page brings together its named places, relatives and available records.'),
    ('australasian-families', 'Australia & New Zealand', {'oceania', 'australia', 'nz'}, 'Find the families with records in Australia and New Zealand, then follow their connections to the households and places represented elsewhere in the catalogue.'),
    ('english-welsh-families', 'England & Wales', {'england', 'wales'}, 'Explore English and Welsh households through their named family members and the places recorded in their lives.'),
    ('other-family-places', 'Other places & unresolved locations', {'other'}, 'Browse families connected with other countries or with places still to be identified. Their people and records remain available while locations are researched.'),
)

# A local study belongs to its geographic subject. Overseas records of its
# members describe migration, not additional locations of the study itself.
LOCALITY_TOPICS = {
    'lisnagaver-rasharkin': ['early-ireland'],
    'larne-kilwaughter': ['early-ireland'],
    'early-scottish-records': ['scottish-families'],
}
BRANCH_NAV_RE = r'<nav\b(?=[^>]*\bclass="experience-branch-nav")(?=[^>]*\baria-label="Related regions and local studies")[^>]*>.*?</nav>'


def branch_topic_ids(branch, countries):
    if branch['kind'] == 'place':
        return list(LOCALITY_TOPICS[branch['id']])
    return [id for id, _, keys, _ in TOPICS if keys & countries]


def branch_navigation(branch, branches, hubs):
    parents = [h for h in hubs if h['id'] in branch['topic_ids']]
    localities = [b for b in branches if b['kind'] == 'place' and b['id'] != branch['id'] and set(b['topic_ids']) & set(branch['topic_ids'])]
    links = '<a href="/branches/">All families &amp; places</a>' + ''.join(f'<a href="{h["url"]}">{escape(h["label"])}</a>' for h in parents)
    navigation = f'<nav class="experience-branch-nav" aria-label="Related regions and local studies"><p>Explore the wider records</p><div class="r-actions">{links}</div>'
    if localities:
        navigation += '<p>Other local studies in these regions</p><div class="r-actions">' + ''.join(f'<a href="{b["url"]}">{escape(b["label"])}</a>' for b in localities) + '</div>'
    return navigation + '</nav>'


def repair_local_study_navigation(changed):
    """Refresh study links without rebuilding biographies or memberships."""
    path = WEB / 'assets/research/branches.json'
    branches = json.loads(path.read_text())
    for branch in branches:
        if branch['kind'] == 'place':
            branch['topic_ids'] = branch_topic_ids(branch, set())
    hubs = [b for b in branches if b['kind'] == 'region']
    for branch in branches:
        relative = f'branches/{branch["id"]}/index.html'
        page = (WEB / relative).read_text()
        if branch['kind'] == 'region':
            local = [b for b in branches if b['kind'] == 'place' and branch['id'] in b['topic_ids']]
            section = '<section><h2>Choose a local study</h2>' + cards(local) + '</section>' if local else ''
            page = re.sub(r'<section><h2>Choose a local study</h2>.*?</section>', lambda _: section, page, count=1, flags=re.S)
        else:
            page = re.sub(BRANCH_NAV_RE, lambda _: branch_navigation(branch, branches, hubs), page, count=1, flags=re.S)
        update(relative, page, changed)
    update('assets/research/branches.json', json.dumps(branches, ensure_ascii=False, separators=(',', ':')) + '\n', changed)
    directory_path = WEB / 'assets/research/branches-directory.json'
    directory = json.loads(directory_path.read_text())
    for group in directory['groups']:
        if group['kind'] == 'place':
            group['regions'] = list(LOCALITY_TOPICS[group['id']])
            group['region'] = group['regions'][0]
    update('assets/research/branches-directory.json', json.dumps(directory, ensure_ascii=False, indent=2) + '\n', changed)


# Local studies are evidence-defined, not exported-tree branches.  The former
# Larne list followed uncertain father links through Glenleslie into Rasharkin;
# these reviewed memberships keep only locally documented people and members of
# specifically established local households.
LOCALITY_MEMBERS = {
    'lisnagaver-rasharkin': {
        'glasgow-951', 'mccaughan-222', 'glasgow-3939', 'glasgow-3940',
        'glasgow-938', 'glasgow-3167', 'glasgow-973', 'glasgow-438',
        'glasgow-867', 'garvin-1831', 'glasgow-1371', 'glasgow-2406',
        'glasgow-2908', 'glasgow-987', 'mccracken-5681', 'glasgow-3896',
        'glasgow-2413', 'boyd-18548', 'glasgow-2414', 'glasgow-2415',
        'glasgow-1360', 'glasgow-1361', 'glasgow-1362', 'glasgow-1363',
        'glasgow-1034', 'glasgow-3975', 'dunseeth-1', 'mccracken-5690',
    },
    'larne-kilwaughter': {
        'glasgow-3970', 'glasgow-3961', 'glasgow-3913', 'glasgow-1081',
        'glasgow-1499', 'glasgow-1504', 'murray-20395',
        'glasgow-3325', 'glasgow-3326', 'glasgow-3327', 'glasgow-3328',
        'glasgow-1505', 'glasgow-1506', 'glasgow-1507',
        'glasgow-1508', 'glasgow-1510', 'glasgow-1509', 'glasgow-3324',
        'glasgow-3986', 'glasgow-3991', 'glasgow-3992',
        'glasgow-4180', 'glasgow-4181', 'glasgow-3989', 'stewart-72380',
        'unknown-763421', 'glasgow-4013', 'glasgow-1143', 'wilson-78088',
        'glasgow-1144', 'crosier-512', 'glasgow-1500', 'glasgow-1501',
        'glasgow-2304', 'glasgow-1146', 'glasgow-1983', 'glasgow-1982',
    },
}

LOCAL_FAMILIES = {
    'lisnagaver-rasharkin': [
        dict(status='Documented family', title='Alexander Glasgow and Mary McCaughan', place='Gortereagh, Lisnagaver and Gortahar · 1837–1892', members=['glasgow-951', 'mccaughan-222', 'glasgow-3939', 'glasgow-3940', 'glasgow-938', 'glasgow-3167', 'glasgow-973', 'glasgow-438'], evidence='Baptisms, the complete 1851 household and later marriages document the couple and six children. A tested descendant belongs to R-FT20271, shared with the James J Glasgow line.', boundary='Alexander’s parents, the named ancestor shared with James J, and his exact relationship to Thomas and Daniel remain unresolved. The 1888 death remains probable, with age and informant identity unresolved.'),
        dict(status='Documented household', title='John Glasgow and Margaret Garvin', place='Lisnagaver and Rasharkin · 1846–1918', members=['glasgow-867', 'garvin-1831', 'glasgow-1371', 'glasgow-2406', 'glasgow-2908'], evidence='The 1846 marriage, 1851 household and family memorial establish the couple, their children and John’s brother Samuel.', boundary='The older father John is named but not securely identified with an existing profile.'),
        dict(status='Proved sibling network', title='Thomas and Daniel Glasgow', place='Lisnagaver and Kilrea · by 1871', members=['glasgow-987', 'glasgow-3896', 'glasgow-2413'], evidence='Daniel’s will calls Thomas his late brother and Daniel Neely Glasgow his nephew; the nephew’s marriage names Thomas as father.', boundary='The records do not name the brothers’ parents or prove Alexander was their brother.'),
        dict(status='Documented family', title='Daniel Neely Glasgow and Mary Jane Boyd', place='Tamlaght and Lisnagaver connections · 1888–1901', members=['glasgow-2413', 'boyd-18548', 'glasgow-2414', 'glasgow-2415'], evidence='The marriage and original birth returns document the couple and daughters Sarah Taylor and Elizabeth Boyd Glasgow.', boundary='Their later migration evidence does not resolve the older Glasgow parentage question.'),
        dict(status='Documented continuation', title='Mary Ann Glasgow and Robert Elder', place='Lisnagaver and Gortahar · 1871 onward', members=['glasgow-3167'], evidence='Mary’s marriage names Alexander Glasgow as her father and the later Gortahar records continue the Elder household.', boundary='Only catalogue people with public dossiers are linked here; unresolved later children remain research subjects.'),
    ],
    'larne-kilwaughter': [
        dict(status='Two uncertain parent links', title='James, Hugh and the 1843 bride Mary', place='Larne settlement and property · 1843', members=['glasgow-3991', 'glasgow-4180', 'glasgow-4181', 'glasgow-3989'], evidence='The marriage settlement names Mary and the estate of deceased Hugh. The live working chain places Hugh under James and Mary under Hugh, with both father links explicitly uncertain.', boundary='No inspected record states either new relationship. Hugh’s residence is not given. The bride may be William’s daughter Mary-3989; their 1843/1844 death-year conflict remains unresolved.'),
        dict(status='Documented locality cluster', title='The 1653 and 1669 households', place='Larne, Glenarm and Kilwaughter Demesne', members=['glasgow-3970', 'glasgow-3961', 'glasgow-1081', 'glasgow-3913'], evidence='A 1653 deposition places Robert Glaskow at Larne; the 1669 hearth-money roll records Elizabeth at Glenarm and James and John at Kilwaughter.', boundary='These are separate record occurrences, not a proved founding family.'),
        dict(status='Register-supported household', title='Hugh Glasgow of New Town, Larne', place='New Town of Larne · early eighteenth century', members=['glasgow-1499', 'glasgow-1506', 'glasgow-1507', 'glasgow-1508', 'glasgow-1510'], evidence='The maintained church chronology identifies Hugh’s household and named children.', boundary='The surviving evidence is derivative and does not establish Hugh’s parents or the disputed James identity.'),
        dict(status='Strongly supported family', title='James Glasgow and Sarah Murray', place='Larne and Kilwaughter · eighteenth century', members=['glasgow-1504', 'murray-20395', 'glasgow-3325', 'glasgow-3326', 'glasgow-3327', 'glasgow-3328'], evidence='The congregation-register chronology supports the marriage and four named children.', boundary='Their parentage remains unknown; locality and repeated names do not attach them to the 1653 household.'),
        dict(status='Strongly supported family', title='Robert Glasgow and Rachel Wilson', place='Kilwaughter · 1710s–1770s', members=['glasgow-1143', 'wilson-78088', 'glasgow-1144', 'glasgow-1500', 'glasgow-1501'], evidence='Register and equity evidence reconstructs Robert and Rachel’s household. The original 20 December 1764 Ballykeel memorial expressly names James as Robert’s son; the sourced reading follows below.', boundary='No inspected record proves descent from Robert Glaskow at Larne in 1653.'),
        dict(status='Strongly supported continuation', title='James Glasgow and Mary Crosier', place='Kilwaughter to Newberry, South Carolina', members=['glasgow-1144', 'crosier-512', 'glasgow-2304', 'glasgow-1146', 'glasgow-1983', 'glasgow-1982'], evidence='The maintained family evidence strongly supports the couple and four named sons.', boundary='Their later American branch does not prove the ancestry of the older Larne households.'),
    ],
}

# Locality-specific display overrides are reserved for cases where maintained
# evidence is newer than the catalogue source. Current members render directly
# from the corrected catalogue identities.
LOCAL_MEMBER_LABELS = {}
LOCALITY_PERSON_OVERRIDES = {}
CSS = """
/* Site experience: readable controls, complete coverage and regional browsing. */
body.g-kind-dna{overflow:visible!important}
.v3-site.g-kind-dna #g-page,.v3-site.g-kind-dna .app-layout{overflow:visible}
.v3-site.g-kind-dna #sidebar{top:var(--g-bar)!important;background:#e6edde;border-bottom:2px solid #78906a;box-shadow:0 5px 14px #233b2017;z-index:45}
.v3-site.g-kind-dna #sidebar .main-nav{gap:5px;padding:9px 0;min-height:64px;scroll-padding-inline:12px}
.v3-site.g-kind-dna #sidebar .main-nav a{min-height:44px;padding:10px 13px;font-size:12px;font-weight:600;color:#36512e;border:1px solid transparent;border-radius:6px}
.v3-site.g-kind-dna #sidebar .main-nav a:hover{background:#d4dfca;border-color:#9daf8e}
.v3-site.g-kind-dna #sidebar .main-nav a[aria-current="page"]{background:#35542e;color:#fff;border-color:#35542e;box-shadow:0 2px 5px #233b2020}
.v3-site.g-kind-dna #sidebar .main-nav a:focus-visible{outline:3px solid #8b682d;outline-offset:-3px}
.v3-site.g-kind-dna #sidebar .main-nav .experience-ydna-destination{border-color:#adbea0;background:#f4f6ed}
.v3-site.g-kind-dna .chapter-jumps{top:calc(var(--g-bar) + 66px)}
.v3-site.g-kind-dna .story-chapter{scroll-margin-top:calc(var(--g-bar) + 130px)}
.v3-site .repair-canopy-core{padding:8px;box-sizing:border-box}
.v3-site .repair-canopy-core strong{white-space:nowrap;font-size:20px;line-height:1.2}
.v3-site .repair-canopy-stage{display:grid;grid-template-rows:minmax(0,1fr) auto;color:inherit;text-decoration:none;cursor:pointer}
.v3-site .repair-canopy-stage canvas{min-height:0;cursor:pointer}
.v3-site .repair-canopy-stage:focus-visible{outline:3px solid #59794d;outline-offset:5px}
.v3-site .repair-home-group-links{position:static;inset:auto;display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:6px;padding-top:12px;pointer-events:none}
.v3-site .repair-home-group-label{position:static;min-width:0;max-width:none;padding:7px 8px;border-left:3px solid var(--group-colour);pointer-events:none;box-sizing:border-box}
.v3-site .repair-home-group-label strong,.v3-site .repair-home-group-label small{display:block;white-space:normal;overflow-wrap:anywhere}
.v3-site .repair-home-group-label strong{font-size:13px}
.v3-site .repair-home-group-label small{font-size:10px}
.v3-site .catalogue-search-footer{padding-top:18px}
.v3-site .catalogue-filter-chips{padding-top:8px;gap:10px}
.v3-site .catalogue-filter-chips>label{display:flex;align-items:center;gap:8px;padding:11px 13px!important;min-height:44px;box-sizing:border-box;line-height:1.5}
.v3-site .catalogue-filter-chips>label>input{flex:0 0 auto;margin:0!important}
.v3-site .catalogue-advanced>summary{cursor:pointer;min-height:68px;align-items:center}
.v3-site .catalogue-advanced>summary::after{content:'';display:block;flex:0 0 28px;width:28px;height:28px;padding:0;box-sizing:border-box;line-height:1;background:linear-gradient(currentColor,currentColor) center/12px 2px no-repeat,linear-gradient(currentColor,currentColor) center/2px 12px no-repeat}
.v3-site .catalogue-advanced[open]>summary::after{content:'';background:linear-gradient(currentColor,currentColor) center/12px 2px no-repeat}
.v3-site .catalogue-advanced-body{padding-top:20px;gap:22px}
.v3-site .catalogue-filter-section{padding:18px!important}
.v3-site .catalogue-filter-section>:not(legend){padding-top:8px}
.v3-site .catalogue-primary-search>*,.v3-site .catalogue-query-stack,.v3-site .catalogue-query-control,.v3-site .catalogue-exact-name>span{min-width:0;max-width:100%}
.v3-site .catalogue-query-stack{grid-template-columns:minmax(0,1fr)}
.v3-site #g-page:has(.r-context:not([hidden]))>.v3-view-nav{display:flex}
.v3-site .r-context{border-left:5px solid #54754b;background:#e7eedf}
.v3-site .r-context-top{padding:15px 24px;gap:18px;flex-wrap:wrap}
.v3-site .r-context-title{max-width:none;flex:1 1 260px;gap:6px 12px}
.v3-site .r-context-title strong{font-size:18px}
.v3-site .r-context-title .r-scope-label{font-weight:700;color:#355132}
.experience-selection-id{font-size:12px;color:#47613f}
.experience-scope-help{flex-basis:100%;font-size:12px;color:#48623f}
.v3-site .r-context-controls{flex-direction:row;align-items:center;flex-wrap:wrap}
.v3-site .r-context-clear{padding:10px 15px;border:1px solid #365630;border-radius:6px;background:#365630;color:#fff;font-size:13px!important;font-weight:600;min-height:40px;white-space:normal}
.v3-site .r-context-clear:hover{background:#254321}
.v3-site.g-kind-tree .topbar{flex-wrap:wrap;gap:10px}
.v3-site.g-kind-tree .topbar .top-actions{flex:1 1 350px;min-width:0}
.v3-site.g-kind-tree .topbar .search-wrap{flex:1 1 auto;min-width:0}
.v3-site.g-kind-tree .topbar .global-search{width:100%;height:42px;min-width:0;box-sizing:border-box;gap:9px;padding:0 12px}
.v3-site.g-kind-tree .topbar .global-search input#search{flex:1 1 0;width:0;min-width:0;max-width:100%;height:100%;min-height:0;border:0!important;background:transparent!important;box-shadow:none;padding:0;font-size:13px}
.v3-site.g-kind-tree .topbar .global-search>.ico{flex:none}
.v3-site.g-kind-tree .topbar .global-search input#search::placeholder{font-size:12px}
.v3-site .catalogue-exact-name small{white-space:normal;overflow-wrap:anywhere}
.experience-topic-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,240px),1fr));gap:16px;margin:20px 0 30px}
.experience-topic{display:block;padding:22px;border:1px solid #cdd6c4;border-radius:12px;background:linear-gradient(135deg,#f6f5e8,#edf2e5);text-decoration:none;color:#294b37}
.experience-topic h3{margin:0 0 8px;font:500 25px/1.2 var(--g-serif)}
section.experience-topic > .r-kicker{display:block;margin-bottom:12px}
section.experience-topic > h2{margin:0 0 20px}
.experience-topic p{margin:0 0 12px;line-height:1.65;color:#52634f}
.experience-topic small{display:block;font-size:12px;color:#516446}
.experience-topic:focus-visible,.experience-topic:hover{outline:2px solid #708764;outline-offset:3px}
.experience-branch-nav{margin:20px 0 28px;padding:18px 20px;border:1px solid #d2dbc9;border-radius:10px;background:#f0f3e9}
.experience-branch-nav p{margin:0 0 8px;color:#55664c}
.experience-branch-nav .r-actions{display:flex;flex-wrap:wrap;gap:10px 20px}
.experience-branch-nav a{display:inline-block;padding:5px 0}
.local-family-overview{margin:34px 0}.local-family-overview>header{max-width:76ch;margin-bottom:17px}.local-family-overview>header h2{margin:5px 0 8px}.local-family-overview>header p{margin:0;color:#536451;line-height:1.6}.local-family-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}.local-family-card{padding:18px;border:1px solid #ccd8c5;border-radius:9px;background:#fbfcf7}.local-family-status{display:inline-block;padding:4px 7px;border-radius:999px;background:#e3eee0;color:#315d3b;font:700 9px var(--g-sans);letter-spacing:.07em;text-transform:uppercase}.local-family-card h3{margin:10px 0 4px;font:600 22px/1.2 var(--g-serif);color:#294b37}.local-family-place{margin:0 0 12px;color:#687767;font:600 11px/1.45 var(--g-sans)}.local-family-members{display:flex;flex-wrap:wrap;gap:6px;margin:0 0 13px}.local-family-members a{padding:5px 8px;border:1px solid #ccdac7;border-radius:5px;background:#f0f4eb;color:#315641;font-size:11px;text-decoration:none}.local-family-members a:hover{border-color:#789270;background:#e6eee0}.local-family-basis,.local-family-boundary{margin:8px 0;font-size:13px;line-height:1.55}.local-family-basis strong{color:#2f6846}.local-family-boundary{padding-top:8px;border-top:1px solid #e1e5da;color:#685c3e}.local-family-scope{padding:13px 15px;border-left:4px solid #b39049;background:#f8f3e4;color:#5e5337;font-size:13px;line-height:1.55}
#r-map-coverage{display:flex;flex-wrap:wrap;gap:8px 20px;align-items:center;padding:16px 20px;margin:0 0 16px;border:1px solid #ccd7c1;background:#eef3e7;border-radius:10px}
#r-map-coverage span{flex:1 1 380px;font-size:13px;line-height:1.6}
.experience-map-key{display:flex;flex-wrap:wrap;gap:10px 24px;margin:0 0 14px;font-size:13px;color:#4a6045}
.experience-map-key span{display:flex;align-items:center;gap:8px}
.experience-map-key i{display:inline-block;width:14px;height:14px;border-radius:50%;background:#526e48}
.experience-map-key i.country{width:22px;border-radius:4px;background:#f3eddf;border:2px dashed #7b6844}
.experience-map-key a,#r-map-coverage a{color:#35583d;text-underline-offset:3px}
.v3-country-total>span:last-child{font-size:12px;text-decoration:underline;margin-top:8px}
.repair-home-routes a{padding:14px 15px;border:1px solid #d6ddcf;border-radius:7px;background:#fbfaf4;font-size:15px;transition:border-color .16s ease,background .16s ease,transform .16s ease}.repair-home-routes a small{margin-top:4px}.repair-home-routes a:hover{border-color:#92a58f;background:#f0f3e9;text-decoration:none;transform:translateY(-1px)}
@media(max-width:700px){.experience-topic{padding:18px}.local-family-grid{grid-template-columns:1fr}.local-family-card{padding:16px}.v3-site .catalogue-primary-search{grid-template-columns:minmax(0,1fr)}.v3-site .catalogue-advanced-body{padding-top:18px}.v3-site .catalogue-filter-section{padding:15px!important}.v3-site .catalogue-hero{margin-bottom:12px}.v3-site .catalogue-search-heading{display:grid!important;grid-template-columns:minmax(0,1fr) auto;align-items:center!important;gap:10px!important;padding:16px!important}.v3-site .catalogue-search-heading .kicker,.v3-site .catalogue-search-heading h2{position:absolute!important;width:1px!important;height:1px!important;padding:0!important;margin:-1px!important;overflow:hidden!important;clip:rect(0,0,0,0)!important;white-space:nowrap!important;border:0!important}.v3-site .catalogue-search-heading>div>small{display:block;font-size:.79rem;line-height:1.45}.v3-site .catalogue-results-summary{justify-self:end;margin:0}.v3-site .catalogue-primary-search{padding-top:18px!important}.repair-home-routes{gap:10px!important}.repair-home-routes a{padding:12px;font-size:14px}.v3-site.g-kind-dna #sidebar .main-nav{display:flex!important;grid-template-columns:none!important;flex-wrap:nowrap!important;overflow-x:auto!important;overscroll-behavior-inline:contain;scrollbar-width:thin;padding:7px 10px!important;scroll-padding-inline:10px}.v3-site.g-kind-dna #sidebar .main-nav a{flex:0 0 auto;min-width:112px;min-height:38px!important;padding:7px 12px!important;font-size:10px!important;white-space:nowrap}}
.v3-site.g-kind-tree .content-view{max-height:none}
/* Accessibility: retain regional colour hints while darkening preview label text. */
.repair-home-group-label strong{color:color-mix(in srgb,var(--group-colour,#31583d) 75%,#263f35)}
/* Accessibility: WCAG AA text contrast for small muted labels (same hues, darker). */
body .g-footer a,body .g-footer-links a{color:#536746}
body .g-bar-menu,body .repair-menu-label{color:#536746}
body .v3-feature-timeline time{color:#4c5f43}
body .v3-country-total small{color:#536746}
body .v3-local-mark{color:#74511f}
body .repair-question-trails-head>p{color:#4c5f43}
body .g-eyebrow,body .g-guide-step p,body .g-note-panel .g-eyebrow,body .g-page table th,body .g-page table td{color:#536746}
body .legend,body .legend button{color:#536746}
"""


def update(relative, text, changed):
    path = WEB / relative
    if not path.exists() or path.read_text(encoding='utf-8') != text:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding='utf-8')
        changed['site_experience'] += 1


def patch(text, old, new):
    if new in text:
        return text
    if old not in text:
        raise ValueError(f'Presentation source changed near {old[:90]!r}')
    return text.replace(old, new, 1)


def repair_ydna_navigation(changed):
    navigation = runpy.run_path(str(ROOT / 'tools/repair_dna_navigation.py'))
    changed.update(navigation['repair']())


def repair_map(changed):
    js = (WEB / 'assets/research/map.js').read_text()
    replacements = [
        ('let width=900,height=610,dpr=1,points=[]', 'let recordLookup=new Map();let width=900,height=610,dpr=1,points=[]', ()),
        ("const key=Math.floor(s.x/cell)+':'+Math.floor(s.y/cell)", "const key=p.broad?'country:'+p.key:'local:'+Math.floor(s.x/cell)+':'+Math.floor(s.y/cell)", ()),
        ('g={x:0,y:0,rows:[],count:0,country:p.country}', 'g={x:0,y:0,rows:[],count:0,country:p.country,broad:!!p.broad}', ()),
        ('if(Math.hypot(a.x-b.x,a.y-b.y)<a.r+b.r+4)', 'if(!a.broad&&!b.broad&&Math.hypot(a.x-b.x,a.y-b.y)<a.r+b.r+4)', ()),
        ('for(const g of clusters){const countries=', "const countryBoxes=[];for(const g of clusters){if(g.broad){const text=g.count.toLocaleString();ctx.font='600 12px sans-serif';const w=Math.max(62,ctx.measureText(text).width+22),origin={x:g.x,y:g.y};while(countryBoxes.some(b=>Math.abs(b.x-g.x)<(b.w+w)/2+10&&Math.abs(b.y-g.y)<56))g.y-=56;countryBoxes.push({x:g.x,y:g.y,w});g.r=w/2;ctx.strokeStyle='#796446';ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(origin.x,origin.y);ctx.lineTo(g.x,g.y);ctx.stroke();ctx.fillStyle='#faf4e5';ctx.lineWidth=1.8;ctx.setLineDash([4,3]);ctx.beginPath();ctx.roundRect(g.x-w/2,g.y-17,w,34,5);ctx.fill();ctx.stroke();ctx.setLineDash([]);ctx.fillStyle='#59482e';ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillText(text,g.x,g.y);ctx.font='10px sans-serif';ctx.fillText(g.rows[0].name.split(' \\u00b7 ')[0],g.x,g.y+26);continue}const countries=", ()),
        ('if(g.rows.length!==1)continue;', 'if(g.broad||g.rows.length!==1)continue;', ()),
        ("+' associations in view'", "+' associations in view (including country summaries)'", ("+' associations in view (including fallback summaries)'",)),
        ('if(focus){const m=merc(p.lat,p.lon);', 'if(focus&&!p.broad){const m=merc(p.lat,p.lon);', ()),
        ('tooltip.textContent=g.rows.length===1?', "tooltip.textContent=g.broad?'Country summary: '+g.count.toLocaleString()+' associations awaiting local coordinates':g.rows.length===1?", ("tooltip.textContent=g.broad?(g.rows[0].stateFallback?'State-level fallback: ':'Country summary: ')+g.count.toLocaleString()+' associations awaiting local coordinates':g.rows.length===1?",)),
        ("R.norm(p.name+' '+(p.source_places||[]).join(' ')+' '+x[1]+' '+(names.get(x[1])||''))", "R.norm([recordLookup.get(x[0])?.place,x[1],recordLookup.get(x[0])?.person,R.palette[p.country]?.label,names.get(x[1])||''].join(' '))", ()),
        ("+' mapped source associations · '+filtered.length.toLocaleString()+' representative points'", "+' associations shown · '+filtered.filter(p=>!p.broad).length.toLocaleString()+' local points · '+filtered.filter(p=>p.broad).length+' country summaries'", ("+' associations shown · '+filtered.filter(p=>!p.broad).length.toLocaleString()+' local points · '+filtered.filter(p=>p.broad).length+' fallback summaries'",)),
        ("const [ps,world,britishIsles]=await Promise.all([R.json('/assets/research/map-points.json'),R.json('/assets/research/world.json'),R.json('/assets/repair/british-isles-50m.json')]);points=ps.map((p,i)=>({...p,key:'loc-'+p.lat+'-'+p.lon}));", "const [ps,world,britishIsles,broad,records]=await Promise.all([R.json('/assets/research/map-points.json'),R.json('/assets/research/world.json'),R.json('/assets/repair/british-isles-50m.json'),R.json('/assets/v3/map-country-associations.json'),R.json('/assets/research/record-index.json')]);recordLookup=new Map(records.map(r=>[r.id,r]));points=[...ps,...broad.map(p=>({...p,broad:true}))].map(p=>({...p,key:(p.broad?'country-':'loc-')+p.lat+'-'+p.lon}));", ("points=[...ps,...splitUnitedStatesFallbacks(broad,recordLookup).map(p=>({...p,broad:true}))].map(p=>({...p,key:(p.broad?'fallback-':'loc-')+p.lat+'-'+p.lon}));",)),
    ]
    for old, new, compatible in replacements:
        if 'clusteredFallbackRendering' in js and old in (
            "const key=Math.floor(s.x/cell)+':'+Math.floor(s.y/cell)",
            'g={x:0,y:0,rows:[],count:0,country:p.country}',
            'if(Math.hypot(a.x-b.x,a.y-b.y)<a.r+b.r+4)',
            'for(const g of clusters){const countries=',
            'if(g.rows.length!==1)continue;',
            'tooltip.textContent=g.rows.length===1?',
        ):
            continue
        if new not in js and not any(fragment in js for fragment in compatible):
            js = patch(js, old, new)
    update('assets/research/map.js', js, changed)
    update('assets/v3/map-summary.js', (ROOT / 'tools/site_map_summary.js').read_text(), changed)
    page = (WEB / 'map/index.html').read_text()
    page = page.replace('Specific representative locations. Country-only associations are listed separately, not pinned here.', 'Local record locations and dashed country summaries. Country summaries are not precise event locations.')
    page = page.replace('<span class="r-kicker">Beyond the pins</span><h2>Known only to a country</h2><p>These associations do not have a sufficiently specific local point. They remain searchable without becoming apparent town-level locations.</p>', '<span class="r-kicker">Complete catalogue coverage</span><h2>Every record counts</h2><p>Country totals include local pins, country summaries and records without coordinates. A country summary means local coordinates are missing; the record may still name a town or parish.</p>')
    if 'id="r-map-coverage"' not in page:
        page = page.replace('<div class="r-map-layout">', '<div id="r-map-coverage" role="status">Counting all matching records...</div><div class="experience-map-key"><span><i></i>Local representative point</span><span><i class="country"></i>Country summary: local coordinates pending</span><a href="#v3-country-summary">Country totals, including unplaced records</a></div><div class="r-map-layout">', 1)
    update('map/index.html', page, changed)


def description(branch, people, records):
    root = people.get(branch.get('root'), {})
    name = root.get('name') or branch['label']
    life = root.get('life', '').replace('Not recorded', '').strip(' -\u2013')
    text = f'Browse the relationships attached to {name}' + (f' ({life})' if life else '') + '.'
    if root.get('spouses'):
        text += ' The catalogue names ' + ', '.join(root['spouses'][:2]) + ' as ' + ('partners.' if len(root['spouses']) > 1 else 'a partner.')
    places = Counter(r['place'] for r in records if r.get('place') and not re.search(r'unknown|not recorded|unspecified', r['place'], re.I))
    if places:
        text += ' Associated records name ' + '; '.join(p for p, _ in places.most_common(3)) + '.'
    elif root.get('birthPlace'):
        text += ' The entry records a birthplace of ' + root['birthPlace'] + '.'
    else:
        text += f"Explore the {branch['count']} linked catalogue entries and their recorded relationships."
    return text


def cards(rows, *, descriptions=True):
    return '<div class="experience-topic-grid">' + ''.join(
        f'<a class="experience-topic" href="{escape(b["url"])}"><h3>{escape(b["label"])}</h3>'
        + (f'<p>{escape(b["description"])}</p>' if descriptions else '')
        + f'<small>{b["count"]:,} people &middot; {b["record_count"]:,} record associations</small></a>' for b in rows
    ) + '</div>'


def local_family_section(branch_id, people):
    rendered = []
    for family in LOCAL_FAMILIES.get(branch_id, []):
        members = []
        for slug in family['members']:
            person = people.get(slug)
            if person:
                label = LOCAL_MEMBER_LABELS.get(slug, person['name'])
                members.append(f'<a href="{escape(person["url"], quote=True)}">{escape(label)}</a>')
        rendered.append(
            '<article class="local-family-card">'
            f'<span class="local-family-status">{escape(family["status"])}</span>'
            f'<h3>{escape(family["title"])}</h3><p class="local-family-place">{escape(family["place"])}</p>'
            f'<div class="local-family-members">{"".join(members)}</div>'
            f'<p class="local-family-basis"><strong>Established by:</strong> {escape(family["evidence"])}</p>'
            f'<p class="local-family-boundary"><strong>Still open:</strong> {escape(family["boundary"])}</p></article>'
        )
    scope = ('Membership is based on documented Larne, Glenarm or Kilwaughter evidence and specifically supported family links. '
             'No record joins Alexander of Lisnagaver (Glasgow-951) to this family. The only connection is indirect: his line shares the Y-DNA branch FT20271 with the line of James J Glasgow, which is attached to Kilwaughter through two unproved generations, and the same branch also contains Scottish and Moneymore lines. His probable father, John Glasgow, farmer, has no recorded parent, so no Larne or Kilwaughter man is a documented ancestor of the Rasharkin households, and the DNA connection does not place Rasharkin people in this locality group.'
             if branch_id == 'larne-kilwaughter' else
             'Families are grouped by records from Lisnagaver, Rasharkin and their immediate Bann Valley network. Proved households are kept distinct where the relationship between them is still unknown.')
    synthesis = ''
    if branch_id == 'larne-kilwaughter':
        try:
            from repair_person_hierarchy import _safe_markdown_html
        except ModuleNotFoundError:
            from tools.repair_person_hierarchy import _safe_markdown_html
        source = ROOT / 'research/larne-proof-2026-09-21/public-synthesis.md'
        synthesis = ('<div class="local-family-research" id="larne-original-evidence">'
                     + _safe_markdown_html(source.read_text(), '/branches/larne-kilwaughter/')
                     + '</div>')
    return (f'<section id="local-family-overview" class="local-family-overview"><header><span class="r-kicker">Families in the area</span>'
            f'<h2>Established families and record-defined households</h2><p>{escape(scope)}</p>'
            '<p><a href="/people/glasgow-951.html#larne-reconstruction">The Larne–Inishrush–South Carolina reconstruction</a> compares the missing generations, the two Irish parent routes and the named records that could distinguish them.</p></header>'
            f'<div class="local-family-grid">{"".join(rendered)}</div>{synthesis}</section>')


def apply_locality_membership(branch, people, records, by_person):
    reviewed = LOCALITY_MEMBERS.get(branch['id'])
    if not reviewed:
        return
    members = sorted(slug for slug in reviewed if slug in people)
    branch['members'] = members
    branch['count'] = len(members)
    associated = [record for slug in members for record in by_person.get(slug, [])]
    branch['record_count'] = len(associated)
    branch['review_count'] = sum(bool(people[slug].get('reviewed')) for slug in members)
    branch['countries'] = dict(Counter(people[slug].get('country') or 'other' for slug in members))
    years = [record['y'] for record in associated if record.get('y') is not None]
    branch['from'] = min(years) if years else None
    branch['to'] = max(years) if years else None
    branch['membershipBasis'] = 'Reviewed locality evidence and specifically supported family links; uncertain exported-tree ancestry is excluded.'


def repair_locality_page(page, branch, people):
    stats = (f'<div class="r-inline r-group-stats"><span><strong>{branch["count"]}</strong> reviewed local people</span>'
             f'<span><strong>{branch["record_count"]}</strong> associated records</span>'
             f'<span><strong>{branch["review_count"]}</strong> maintained conclusions</span></div>')
    page = re.sub(r'<div class="r-inline r-group-stats">.*?</div>', stats, page, count=1, flags=re.S)
    country_meta = {
        'ireland': ('#33786b', 'Ireland / Ulster'), 'scotland': ('#496e95', 'Scotland'),
        'america': ('#aa7036', 'United States'), 'canada': ('#8b5f40', 'Canada'),
        'oceania': ('#776499', 'Australia / New Zealand'), 'other': ('#777c76', 'Other / unknown'),
    }
    legend = []
    for country, count in sorted(branch['countries'].items(), key=lambda row: -row[1]):
        colour, label = country_meta.get(country, country_meta['other'])
        legend.append(f'<span class="r-country" style="--c:{colour}">{escape(label)}</span><span class="r-caption">{count}</span>')
    page = re.sub(r'<div class="r-country-legend">.*?</div>', '<div class="r-country-legend">' + ''.join(legend) + '</div>', page, count=1, flags=re.S)
    earliest = sorted((people[slug] for slug in branch['members'] if slug in people), key=lambda person: (person.get('from') or 9999, person['name']))[:5]
    links = ''.join(f'<a href="{escape(person["url"], quote=True)}"><span><strong>{escape(person["name"])}</strong><br><small>{escape(person.get("birth") or "Date not established")} · {escape(person.get("birthPlace") or "Place not established")}</small></span><span>→</span></a>' for person in earliest)
    page = re.sub(r'(<span class="r-kicker">The earliest entries in this group</span><div class="r-linklist">).*?(</div>)', lambda match: match[1] + links + match[2], page, count=1, flags=re.S)
    families = local_family_section(branch['id'], people)
    if 'id="local-family-overview"' in page:
        page = re.sub(r'<section\b(?=[^>]*\bid="local-family-overview")[^>]*>.*?</section>', lambda _: families, page, count=1, flags=re.S)
    else:
        page, count = re.subn(r'<section class="r-section"><div class="r-section-head"><h2>Inside the current research\.</h2>.*?</section>', families, page, count=1, flags=re.S)
        if not count:
            page = page.replace('<section class="r-section"><div class="r-section-head"><h2>People in this group.</h2>', families + '<section class="r-section"><div class="r-section-head"><h2>People in this group.</h2>', 1)
    return page


def repair_branches(changed):
    branches = json.loads((WEB / 'assets/research/branches.json').read_text())
    topic_ids = {t[0] for t in TOPICS}
    branches = [b for b in branches if b['id'] not in topic_ids and not b.get('curatedResearch')]
    people = {p['slug']: p for p in json.loads((WEB / 'assets/research/registry.json').read_text())}
    for slug, values in LOCALITY_PERSON_OVERRIDES.items():
        if slug in people:
            people[slug].update(values)
    records = json.loads((WEB / 'assets/research/record-index.json').read_text())
    by_person = defaultdict(list)
    for r in records:
        by_person[r['p']].append(r)
    for branch in branches:
        apply_locality_membership(branch, people, records, by_person)
    locality_ids = set(LOCALITY_MEMBERS)
    for slug, person in people.items():
        assigned = [branch for branch in (person.get('branches') or []) if branch not in locality_ids]
        assigned.extend(branch_id for branch_id, members in LOCALITY_MEMBERS.items() if slug in members)
        person['branches'] = list(dict.fromkeys(assigned))
    curated = {
        'lisnagaver-rasharkin': 'Alexander and Mary Glasgow’s six-child family is documented through baptisms, census and later marriages. The current parentage study compares a Larne origin through older Alexander or younger James, with Adam of Inishrush as a possible collateral relative. The FT20271 connection to James J and the South Carolina household chronology make this a priority reconstruction; the immediate father and joining generation remain unresolved.',
        'larne-kilwaughter': 'Early Larne and Kilwaughter records lead to the supported Robert–James–Archibald family and its South Carolina migration. Archibald’s missing 1800 boy fits Tennessee Robert, proposed father of James J. Separately, the older Larne ropemaker James is a viable candidate for Adam of Inishrush’s father. These positive family hypotheses require named succession or kinship records before the Irish and American branches can be joined.',
        'early-scottish-records': 'Explore the early Scottish bearers through medieval records, Glasgow property transactions and Edinburgh testaments. Read each occurrence in its own setting, then follow the spouses, children and neighbours named by the documents. Shared names alone do not join these households into one pedigree.',
        'family-glasgow-3970': 'Robert Glaskow is documented at Larne in 1653, but no inspected record names his wife or child. This tree group leads into the Kilwaughter households and the later Robert Glasgow and Rachel Wilson family. Its early connecting relationships remain working hypotheses; the original records and current assessments explain where the evidence becomes firmer.',
    }
    for b in branches:
        associated = [r for member in b['members'] for r in by_person[member]]
        countries = {r['country'] for r in associated} | set(b.get('countries', {}))
        b['topic_ids'] = branch_topic_ids(b, countries)
        if b['id'] in curated:
            b['description'] = curated[b['id']]
        elif b['description'].startswith('A connected family group,') or b.get('descriptionSource') == 'catalogue':
            b['description'] = description(b, people, associated)
            b['descriptionSource'] = 'catalogue'
    hubs = []
    for id, label, countries, text in TOPICS:
        members = sorted({r['p'] for r in records if r['country'] in countries} | {p['slug'] for p in people.values() if p.get('country') in countries or p.get('deathCountry') in countries})
        member_set = set(members)
        rs = [r for r in records if r['p'] in member_set]
        years = [r['y'] for r in rs if r.get('y') is not None]
        hubs.append(dict(id=id, label=label, kind='region', root='', rootId='', members=members, count=len(members), record_count=len(rs), review_count=sum(bool(people.get(p, {}).get('reviewed')) for p in members), countries=dict(Counter(people[p]['country'] for p in members if p in people)), description=text, url=f'/branches/{id}/', **{'from':min(years) if years else None,'to':max(years) if years else None}))
    template = (WEB / 'branches/lisnagaver-rasharkin/index.html').read_text()
    try:
        import study_place_links
    except ModuleNotFoundError:
        from tools import study_place_links
    places_by_person = study_place_links.person_places(study_place_links.load_records(WEB))
    place_names = study_place_links.load_place_names(WEB)
    place_exists = lambda slug: (WEB / 'places' / f'{slug}.html').is_file()
    for b in branches:
        relative = f"branches/{b['id']}/index.html"
        page = (WEB / relative).read_text()
        if b['kind'] == 'family':
            page = page.replace('<span class="r-kicker">Connected family group</span>', f'<span class="r-kicker">{study_place_links.TREE_GROUP}</span>', 1)
            page = page.replace('Birth-country composition of this research group, not an inferred migration route.', 'Where the people in this group were born. This is not a migration route.', 1)
            places = study_place_links.places_for_people(b['members'], places_by_person, place_exists=place_exists, names=place_names)
            page = study_place_links.insert_group_places(page, study_place_links.render_group_places(places))
        css_version = '3.1-repair-2' if b['id'] in LOCAL_FAMILIES else '3.1-repair-1'
        page = re.sub(r'/assets/repair/site\.css\?v=3\.1-repair-[12]', f'/assets/repair/site.css?v={css_version}', page, count=1)
        core_version = '3.1-repair-2' if b['id'] in LOCAL_FAMILIES else '3.1-repair-1'
        page = re.sub(r'/assets/research/core\.js\?v=3\.1-repair-[12]', f'/assets/research/core.js?v={core_version}', page, count=1)
        page = re.sub(r'(<header class="r-page-head">[\s\S]*?<p class="r-lead">)[\s\S]*?(</p>)', lambda m: m[1] + escape(b['description']) + m[2], page, count=1)
        navigation = branch_navigation(b, branches, hubs)
        if re.search(BRANCH_NAV_RE, page, flags=re.S):
            page = re.sub(BRANCH_NAV_RE, lambda _: navigation, page, count=1, flags=re.S)
        else:
            page = page.replace('</header><div class="r-inline r-group-stats">', '</header>' + navigation + '<div class="r-inline r-group-stats">', 1)
        page = page.replace('<span class="r-kicker">Not recorded</span>', '<span class="r-kicker">Research assessment</span>')
        page = re.sub(r'\[\[([A-Za-z_ -]+-\d+)\|([^\]]+)\]\]', lambda m: f'<a href="https://www.wikitree.com/wiki/{m[1]}">{escape(unescape(m[2]).strip())}</a>', page)
        if b['id'] in LOCAL_FAMILIES:
            page = repair_locality_page(page, b, people)
        update(relative, page, changed)
    for hub in hubs:
        children = [b for b in branches if hub['id'] in b['topic_ids']]
        local = [b for b in children if b['kind'] == 'place']
        families = sorted((b for b in children if b['kind'] == 'family'), key=lambda b: -b['count'])
        body = f'<main class="r-main" id="main"><header class="r-page-head"><span class="r-kicker">{study_place_links.REGION}</span><h1>{escape(hub["label"])}</h1><p class="r-lead">{escape(hub["description"])}</p></header><nav class="experience-branch-nav" aria-label="Regional navigation"><div class="r-actions"><a href="/branches/">All families &amp; places</a><a href="/records/?branch={hub["id"]}">Explore these records</a><a href="/map/?branch={hub["id"]}">See these families on the map</a></div></nav>'
        if local:
            body += '<section><h2>Place studies in this region</h2>' + cards(local) + '</section>'
        body += '<section><h2>WikiTree tree groups in this region</h2><p>These groups follow links in the WikiTree family tree and have people or records in this region. Many of their links have not been checked against records, and appearing together here does not establish a relationship between the groups.</p>' + cards(families) + '</section></main>'
        page = template.replace('lisnagaver-rasharkin', hub['id']).replace('Lisnagaver &amp; Rasharkin', escape(hub['label'])).replace('Lisnagaver & Rasharkin', escape(hub['label']))
        page = re.sub(r'/assets/repair/site\.css\?v=3\.1-repair-[12]', '/assets/repair/site.css?v=3.1-repair-1', page, count=1)
        page = re.sub(r'<main\b[\s\S]*?</main>', lambda _: body, page, count=1)
        page = re.sub(r'(<meta\b(?=[^>]*name="description")[^>]*content=")[^"]*', lambda m: m[1] + escape(hub['description'], quote=True), page, count=1)
        update(f'branches/{hub["id"]}/index.html', page, changed)
    update('assets/research/branches.json', json.dumps(branches + hubs, ensure_ascii=False, separators=(',', ':')), changed)
    update('assets/research/registry.json', json.dumps(list(people.values()), ensure_ascii=False, separators=(',', ':')), changed)
    packed_path = WEB / 'assets/v3/registry-packed.json'
    packed = json.loads(packed_path.read_text())
    slug_index = packed['fields'].index('slug')
    for row in packed['rows']:
        person = people.get(row[slug_index])
        if person:
            for index, field in enumerate(packed['fields']):
                if field in person:
                    row[index] = person[field]
    update('assets/v3/registry-packed.json', json.dumps(packed, ensure_ascii=False, separators=(',', ':')), changed)
    views = (WEB / 'assets/research/views.js').read_text()
    views = patch(views, "found=bs.filter(b=>(!kind.value||b.kind===kind.value)", "found=bs.filter(b=>b.kind!=='region'&&(!kind.value||b.kind===kind.value)")
    # One word per concept (site audit S3-04): the labels of tools/study_place_links.py.
    group_labels = f"b.kind==='research'?'{study_place_links.FAMILY_STUDY}':b.kind==='place'?'{study_place_links.PLACE_STUDY}':'{study_place_links.TREE_GROUP}'"
    views = views.replace("b.kind==='research'?'Evidence-led research group':b.kind==='place'?'Local research group':'Atlas family group'", group_labels)
    views = patch(views, "b.kind==='place'?'Local research group':'Atlas family group'", group_labels)
    views = patch(views, "norm(b.label+' '+b.description)", "norm(b.label+' '+b.description+' '+(b.searchTerms||''))")
    update('assets/research/views.js', views, changed)


def repair_atlas_chrome(changed):
    page = (WEB / 'onetree/index.html').read_text()
    if 'aria-label="Section views"' not in page:
        nav = '<nav class="v3-view-nav" aria-label="Section views"><a href="/catalogue/">People</a><a href="/onetree/" aria-current="page">Family atlas</a><a href="/branches/">Families &amp; places</a><a href="/map/">Map</a><a href="/early-records/">Early records</a><a href="/connections/">Connections</a></nav>'
        page, count = re.subn(r'(<div\b[^>]*\bid="g-page"[^>]*>)', lambda m: m[1] + nav, page, count=1)
        if count != 1:
            raise ValueError('Atlas page container not found')
    update('onetree/index.html', page, changed)
    core = (WEB / 'assets/research/core.js').read_text()
    edits = [
        ("json('/assets/v3/registry-packed.json')", "json('/assets/v3/registry-packed.json?v=2')"),
        ("$('#g-page')?.prepend(host)", "const sectionTabs=$('#g-page>.v3-view-nav');if(sectionTabs)sectionTabs.after(host);else $('#g-page')?.prepend(host)"),
        ('<span class="r-scope-label">Exploring</span><strong>${esc(c.name)}</strong>', '<span class="r-scope-label">${c.kind===\'person\'?\'Selected person\':\'Selected group\'}</span><strong>${esc(c.name)}</strong>${c.kind===\'person\'?`<span class="experience-selection-id">${esc(c.id)}</span>`:\'\'}<span class="experience-scope-help">The views below follow this selection. Use the section tabs above to browse the whole collection.</span>'),
        ('id="r-context-clear">Clear scope & filters</button>', 'id="r-context-clear">Clear selection &amp; show all</button>'),
        ("if(path.startsWith('/onetree'))u.hash='view=all';context=null;", "if(path.startsWith('/onetree')){u.hash='view=all';u.searchParams.set('reset','1');storage.sessionSet('glasgow-tree-view-v2',null);clearTimeout(treeSaveTimer)}contextVersion++;context=null;"),
    ]
    for old, new in edits:
        core = patch(core, old, new)
    update('assets/research/core.js', core, changed)


def repair_home_preview(changed):
    page = (WEB / 'index.html').read_text()
    stage = '<a class="repair-canopy-stage" href="/onetree/?reset=1#view=all" aria-label="Open the family Atlas"><canvas id="r-home-canopy" aria-hidden="true"></canvas><span class="repair-canopy-core" aria-hidden="true"><strong>1450</strong></span><div class="repair-home-group-links" id="repair-home-group-links" aria-label="Profile-location colour key"></div></a>'
    if '<div class="repair-canopy-stage">' in page:
        page, count = re.subn(r'<div class="repair-canopy-stage">[\s\S]*?<div\b[^>]*id="repair-home-group-links"[^>]*></div></div>', lambda _: stage, page, count=1)
        if count != 1:
            raise ValueError('Homepage preview container not found')
    page = re.sub(r'(<p class="repair-canopy-caption">)[\s\S]*?(</p>)', lambda m: m[1] + 'A preview of the recorded family tree. The colour key follows profile locations in the Atlas. Click anywhere in the preview to explore the full tree.' + m[2], page, count=1)
    update('index.html', page, changed)
    update('assets/research/home.js', (ROOT / 'tools/home_preview.js').read_text(), changed)


def repair():
    changed = Counter()
    home = (WEB / 'index.html').read_text()
    home = re.sub(r'(<a class="repair-canopy-core"[^>]*>)[\s\S]*?</a>', lambda m: re.sub(r'\s(?:aria-label|title)="[^"]*"', '', m[1][:-1]) + ' aria-label="Explore the early records, 1450 to 1600" title="Explore the early records, 1450 to 1600"><strong>1450</strong></a>', home, count=1)
    update('index.html', home, changed)
    for relative in ['catalogue.html', 'catalogue/index.html', 'catalogue/advanced.html']:
        page = (WEB / relative).read_text().replace('<details class="catalogue-advanced">', '<details class="catalogue-advanced" open>')
        page = page.replace('<strong>Refine results</strong><small>Use family, date, place and evidence filters</small>', '<strong>Search filters</strong><small>Family, dates, places and evidence &middot; click to show or hide</small>')
        update(relative, page, changed)
    for path in [ROOT / 'tools/catalogue_search.js', WEB / 'people/search.js']:
        js = path.read_text()
        updated = js.replace("  if(advanced&&window.matchMedia('(max-width: 700px)').matches) advanced.open=false;", '  // Search filters start expanded on desktop and mobile; visitors can collapse them.')
        if updated != js:
            path.write_text(updated)
            changed['catalogue_filter_default'] += 1
    css = (WEB / 'assets/repair/site.css').read_text()
    marker = '/* Site experience: readable controls, complete coverage and regional browsing. */'
    css = css.split(marker)[0].rstrip() + '\n'
    update('assets/repair/site.css', css + CSS, changed)
    repair_map(changed)
    repair_branches(changed)
    repair_atlas_chrome(changed)
    repair_home_preview(changed)
    repair_ydna_navigation(changed)
    return changed


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--local-studies-only', action='store_true', help='Refresh geographic study navigation only')
    args = parser.parse_args()
    if args.local_studies_only:
        changed = Counter()
        repair_local_study_navigation(changed)
        print(dict(changed))
    else:
        print(dict(repair()))
