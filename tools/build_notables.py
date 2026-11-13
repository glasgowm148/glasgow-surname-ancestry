#!/usr/bin/env python3
"""Build the searchable Notables reader from the maintained WikiTree study list."""
from __future__ import annotations

from html import escape, unescape
import json
from pathlib import Path
import re

try:
    from tools.site_identity import SITE_URL, page_title
except ModuleNotFoundError:
    from site_identity import SITE_URL, page_title

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / 'www'
SOURCE = ROOT / 'surname-research/free-space-pages/Glasgow_Name_Study.md'
PEOPLE = WEB / 'data/people.json'
EVIDENCE = ROOT / 'data/wikitree/profile-evidence.json'
FS_LINKS = ROOT / 'data/familysearch/person-links.json'
ASSESSMENTS = ROOT / 'research/relationship_assessments.json'


def load(path, default):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return default


def notables_lines():
    text = SOURCE.read_text(encoding='utf-8')
    match = re.search(r'^== Notables ==\s*$([\s\S]*?)(?=^== |\Z)', text, re.M)
    if not match:
        raise RuntimeError('Notables section missing from maintained Glasgow Name Study')
    return [line for line in match.group(1).splitlines() if line.lstrip().startswith('*') and not line.lstrip().startswith('**')]


def useful_date(value):
    text = str(value or '').strip()
    return '' if text in {'0000-00-00', '0000', 'Unknown'} else text


def clean_citation(value):
    """Turn imported escaped markup into readable citation text, never nested links."""
    text = unescape(str(value or ''))
    text = re.sub(r'<a\b[^>]*>(.*?)</a>', r'\1', text, flags=re.I | re.S)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def rows():
    people = {p.get('catalogue_id'): p for p in load(PEOPLE, {}).get('people', [])}
    evidence = load(EVIDENCE, {}).get('profiles', {})
    fs = load(FS_LINKS, {}).get('people', {})
    assessments = load(ASSESSMENTS, [])
    estimates = load(ROOT / 'research/relationship_probability_estimates.json', {}).get('estimates', [])
    out, seen = [], set()
    for line in notables_lines():
        ids = re.findall(r'\[\[([A-Za-z]+-\d+)(?:\|[^]]*)?\]\]', line)
        if not ids:
            continue
        # The first linked profile is the subject; spouse/relative links remain in rationale text.
        pid = ids[0]
        subject_link = re.search(r'\[\[' + re.escape(pid) + r'\|([^]]+)\]\]', line)
        if pid in seen:
            continue
        seen.add(pid)
        key = pid.casefold()
        person = people.get(key) or {}
        profile = evidence.get(pid) or {}
        pf = profile.get('profile_fields', {})
        dates = '–'.join(x for x in (useful_date(person.get('birth') or pf.get('BirthDate')),
                                     useful_date(person.get('death') or pf.get('DeathDate'))) if x)
        name = (person.get('name') or (pf.get('FirstName', '') + ' ' + pf.get('LastNameAtBirth', '')).strip()
                or (subject_link.group(1) if subject_link else pid))
        ref_blocks = re.findall(r'<ref\b[^>]*>(.*?)</ref>', line, re.I)
        rationale = re.sub(r'<ref\b[^>]*>.*?</ref>', '', line, flags=re.I)
        rationale = re.sub(r'^\s*\*\s*', '', rationale)
        rationale = re.sub(r'\[\[([^]|]+)\|([^]]+)\]\]', r'\2', rationale)
        rationale = re.sub(r'\[\[([^]]+)\]\]', r'\1', rationale)
        rationale = clean_citation(re.sub(r"'{2,}", '', rationale))
        citations = []
        for block in ref_blocks:
            plain = re.sub(r'\[\[([^]|]+)\|?([^]]*)\]\]', lambda m: m.group(2) or m.group(1), block)
            plain = re.sub(r'\[(https?://\S+)(?:\s+([^]]+))?\]', lambda m: m.group(2) or m.group(1), plain)
            plain = clean_citation(re.sub(r"'{2,}", '', plain))
            if plain:
                citations.append((plain, []))
            for url, label in re.findall(r'\[(https?://\S+)(?:\s+([^]]+))?\]', block):
                citations.append((label or url, [url.rstrip('.,')]))
        for source in profile.get('sources') or []:
            citation = clean_citation(source.get('citation'))
            urls = source.get('urls') or []
            if citation:
                citations.append((citation, urls))
        rels = []
        for a in assessments:
            if a.get('publication_status') != 'approved' or pid not in a.get('people', []):
                continue
            perspective = (a.get('perspectives') or {}).get(pid, {})
            other_ids = [x for x in a.get('people', []) if x != pid]
            if not other_ids:
                continue
            relative = other_ids[0]
            relkey = relative.casefold()
            rel_local = f'/people/{relkey}.html'
            rel_url = rel_local if (WEB / rel_local.lstrip('/')).exists() else f'https://www.wikitree.com/wiki/{relative}'
            estimate = next((e for e in estimates if e.get('assertion_id') == a.get('assertion_id')
                             and {e.get('subject_id'), e.get('relative_id')} == {pid, relative}), None)
            rels.append({'person': relative, 'url': rel_url, 'name': (people.get(relkey) or {}).get('name', relative),
                         'relationship': perspective.get('relationship', 'connection'),
                         'status': (estimate or {}).get('assessment_status', a.get('status', 'unreviewed')),
                         'percent': (estimate or {}).get('percent'), 'selection': a.get('working_selection'),
                         'lifecycle': a.get('lifecycle'), 'basis': (estimate or {}).get('basis') or a.get('basis', ''),
                         'scope': (estimate or {}).get('scope') or a.get('identity_scope', '') or a.get('limitations', '')})
        local_profile = f'/people/{key}.html'
        profile_url = local_profile if (WEB / local_profile.lstrip('/')).exists() else (profile.get('profile_url') or f'https://www.wikitree.com/wiki/{pid}')
        out.append({'id':pid,'name':name,'dates':dates,'profile':profile_url,
                    'fs':(fs.get(key) or {}).get('id',''),'rationale':rationale,'citations':citations,'relationships':rels})
    return out


def link(url, label):
    if not str(url).startswith(('https://','http://','/')):
        return escape(label)
    external = ' target="_blank" rel="noopener"' if url.startswith(('https://','http://')) else ''
    return f'<a href="{escape(url, quote=True)}"{external}>{escape(label)}</a>'


def brief_summary(person):
    """Short, source-maintained-fact summaries for the public index."""
    summaries = {
        'Glasgow-1030': 'Jhone Glasgow completed a master’s degree; reviewed records do not identify him as Kilbirnie minister, and no family connection is established.',
        'Glasgow-1101': 'The 1635 Glasgow graduate is probably the Donegal cleric appointed in 1661; this identification does not prove migration or birthplace.',
        'Glasgow-1073': 'Rev. John Glasgow served Kilbirnie; Jean Cunningham is named as his wife, while his parents remain uncertain.',
        'Glasgow-1077': 'Ayrshire records identify a merchant namesake; the reported Irvine provost identity remains unverified and is not linked to the minister’s household.',
        'Glasgow-1136': 'A Glasgow M.A. identified in the maintained study; its current entry gives dates but no further biography or family connection.',
        'Glasgow-1075': 'Surgeon Robert Glasgow was Rev. John’s son and Jean Cunningham’s son; Paterson names Margaret Allan as his wife.',
        'Glasgow-3410': 'A Glasgow M.A. identified in the maintained study; its current entry gives dates but no further biography or family connection.',
        'Glasgow-634': 'James Glasgow served as North Carolina Secretary of State; published biography names Maryland minister James Patrick Glasgow as his father.',
        'Glasgow-1076': 'Robert Glasgow owned plantations and enslaved people on St Vincent and commissioned Montgreenan; his assessed father link remains unselected.',
        'Glasgow-1220': 'William Glass founded the British settlement on Tristan da Cunha; the catalogue’s birth year differs from the inherited date.',
        'Glasgow-971': 'Alexander Glasgow was a Scottish merchant and Cork landowner; his proposed ancestry through John remains possible, not established.',
        'Glasgow-473': 'Ellen Glasgow was an American novelist who won the 1942 Pulitzer Prize; no family connection to earlier Scottish branches is stated.',
        'Glasgow-773': 'Sir Thomas Glasgow was an Australian soldier, politician and diplomat; his career does not establish an early Scottish family connection.',
        'Hutcheson-1648': 'George Hutcheson co-founded Glasgow’s hospital and school with his brother Thomas; both were sons of Thomas Hutcheson of Lambhill.',
        'Hutcheson-1649': 'Thomas Hutcheson continued the hospital endowment and school; his maintained father assessment names Thomas Hutcheson of Lambhill.',
        'Glasgow-3958': 'Jemima Glasgow was the mother of novelist Baroness von Tautphoeus; her proposed father James Glasgow remains unselected.',
        'Montgomery-24362': 'Jemima Montgomery, Baroness von Tautphoeus, was an Irish novelist and daughter of Jemima Glasgow and James Montgomery.',
        'Boyle-1708': 'David Boyle was a Scottish politician and University of Glasgow rector; Earl of Glasgow is a title, not his surname.',
        'Glasgow-635': 'Patrick Glasgow ministered at Manokin and All Hallows; identifying him as politician James Glasgow’s father remains unverified.',
    }
    return summaries.get(person['id'], person['rationale'])


def render():
    data = rows()
    body_rows = []
    for p in data:
        sources = []
        for cite, urls in p['citations']:
            for url in urls:
                if url not in [u for u, _ in sources]:
                    sources.append((url, 'Source'))
            if len(sources) >= 2:
                break
        source_links = ' · '.join(link(url, label) for url, label in sources[:2]) or link(p['profile'], 'Sources')
        wiki = link(f'https://www.wikitree.com/wiki/{p["id"]}', 'WikiTree')
        research = link(p['profile'], 'Research')
        fs = link('https://www.familysearch.org/tree/person/details/'+p['fs'], 'FamilySearch') if p['fs'] else ''
        summary = brief_summary(p)
        fs_search = p['fs'] or 'No FamilySearch profile is linked'
        search_text = ' '.join([p['name'], p['dates'], p['rationale'], fs_search, summary] +
                               [f"{r['name']} {r['relationship']} {r['status']} {r['basis']}" for r in p['relationships']] +
                               [cite for cite, _ in p['citations']])
        body_rows.append(f'<tr data-search="{escape(search_text.casefold(),quote=True)}"><th scope="row">{link(p["profile"],p["name"])}<br><small>{escape(p["dates"])}</small></th><td>{escape(summary)}</td><td>{wiki} · {research}{(" · "+fs) if fs else ""} · {source_links}</td></tr>')
    table = ''.join(body_rows)
    shell = (WEB/'research/index.html').read_text(encoding='utf-8')
    shell = re.sub(r'<title>.*?</title>', f'<title>{page_title("Notables")}</title>', shell, count=1, flags=re.S)
    canonical = f'<link rel="canonical" href="{SITE_URL}/notables/">'
    og_url = f'<meta property="og:url" content="{SITE_URL}/notables/">'
    shell = re.sub(r'<link rel="canonical" href="[^"]*"\s*/?>', canonical, shell, count=1) if re.search(r'<link rel="canonical"', shell) else shell.replace('</head>', canonical+'\n</head>', 1)
    shell = re.sub(r'<meta property="og:url" content="[^"]*"\s*/?>', og_url, shell, count=1) if re.search(r'<meta property="og:url"', shell) else shell.replace('</head>', og_url+'\n</head>', 1)
    shell = re.sub(r'<meta content="The Glasgow surname (?:archive|project):[^\"]*" name="description"\s*/?>', '<meta content="Historical people identified in the Glasgow Name Study, with source and relationship qualifications." name="description">', shell, count=1)
    shell = shell.replace('data-g-path="/research/index.html"','data-g-path="/notables/index.html"',1).replace('<strong>Research</strong>','<strong>Notables</strong>',1)
    shell = re.sub(r'<nav class="v3-view-nav" aria-label="Section views">.*?</nav>', '', shell, count=1, flags=re.S)
    main = f'''<main class="r-main" id="main"><header class="v3-page-head"><span class="r-kicker">People in the Glasgow Name Study</span><h1>Notables</h1><p>This index follows the maintained Notables section in the <a href="/free-space/">Glasgow Name Study</a>. Family and identity qualifications remain in the linked research accounts.</p></header><section aria-labelledby="notables-index"><h2 id="notables-index">Historical people</h2><label for="notables-filter">Filter people</label> <input id="notables-filter" type="search" placeholder="Name, dates, or description"><p id="notables-count" aria-live="polite">{len(data)} entries</p><div class="notables-table-wrap"><table id="notables-table"><thead><tr><th scope="col"><button data-sort="0">Person</button></th><th scope="col"><button data-sort="1">Why notable</button></th><th scope="col">Profiles and sources</th></tr></thead><tbody>{table}</tbody></table></div></section></main>'''
    shell = re.sub(r'<main class="r-main" id="main">.*?</main>', main, shell, count=1, flags=re.S)
    script = '''<script>(()=>{const t=document.querySelector('#notables-table'),q=document.querySelector('#notables-filter'),n=document.querySelector('#notables-count'),b=[...t.tBodies[0].rows];function filter(){let s=q.value.trim().toLocaleLowerCase(),v=0;b.forEach(r=>{r.hidden=!r.dataset.search.includes(s);if(!r.hidden)v++});n.textContent=v+' of '+b.length+' entries'}q.addEventListener('input',filter);t.querySelectorAll('[data-sort]').forEach(x=>x.addEventListener('click',()=>{let i=+x.dataset.sort,rows=[...t.tBodies[0].rows],asc=x.dataset.asc!=='true';x.dataset.asc=String(asc);t.querySelectorAll('thead th').forEach((h,j)=>h.setAttribute('aria-sort',j===i?(asc?'ascending':'descending'):'none'));rows.sort((a,b)=>{let A=a.cells[i].innerText.trim(),B=b.cells[i].innerText.trim();return (A.localeCompare(B,undefined,{numeric:true,sensitivity:'base'}))*(asc?1:-1)}).forEach(r=>t.tBodies[0].append(r))}))})();</script>'''
    shell = shell.replace('</head>', '<style>.notables-table-wrap{overflow-x:auto;max-width:100%}#notables-table{width:100%;border-collapse:collapse}#notables-table th,#notables-table td{border-bottom:1px solid #c8cfc4;padding:.75rem;text-align:left;vertical-align:top}#notables-table thead{background:#eef1e9}#notables-table th button{font:inherit;font-weight:700;color:inherit;background:none;border:0;text-decoration:underline;cursor:pointer}#notables-table ul{padding-left:1.2rem;margin:.25rem 0}#notables-filter{max-width:100%;padding:.6rem;border:1px solid #66745e;border-radius:.3rem}@media(max-width:700px){#notables-table{min-width:760px}}</style></head>',1)
    shell = shell.replace('</body>', script+'</body>', 1)
    out = WEB/'notables/index.html'; out.parent.mkdir(parents=True, exist_ok=True); out.write_text(shell, encoding='utf-8')
    return len(data)

if __name__ == '__main__':
    print({'notables':render()})
