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
    return [line for line in match.group(1).splitlines() if line.lstrip().startswith('*')]


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


def render():
    data = rows()
    body_rows = []
    for p in data:
        citations = '<ul>' + ''.join('<li>' + (link(urls[0], cite) if urls else escape(cite)) + '</li>' for cite, urls in p['citations']) + '</ul>' if p['citations'] else '<span>Sources are listed on the profile.</span>'
        relations = '<ul>' + ''.join('<li>' + escape(r['relationship'].title()) + ': ' + link(r['url'], r['name']) + ' — ' + escape(r['status']) + (f' ({r["percent"]}%)' if r['percent'] is not None else '') + (f' — {"selected working connection" if r["selection"] == 1 or r["selection"] is True else "not selected" if r["selection"] == 0 or r["selection"] is False else "alternative" if r["lifecycle"] == "alternative" else r["lifecycle"]}' if r['selection'] is not None or r['lifecycle'] else '') + ((': '+escape(r['basis'])) if r['basis'] else '') + ((' Limits: '+escape(r['scope'])) if r['scope'] else '') + '</li>' for r in p['relationships']) + '</ul>' if p['relationships'] else '<span>No reviewed family connection listed.</span>'
        fs = link('https://www.familysearch.org/tree/person/details/'+p['fs'], 'FamilySearch profile') if p['fs'] else 'No FamilySearch profile is linked'
        portrait_text = p['rationale'].lower()
        portrait = ('Portrait selected' if 'selected as the portrait by the owner' in portrait_text else
                    'Portrait saved; image and title checked; profile selection pending' if 'saved on familysearch' in portrait_text and 'single memory and title have been verified' in portrait_text else
                    'Portrait source listed for a relative; no portrait claimed for this person' if 'portrait source for the daughter' in portrait_text else
                    'Portrait source available; verification and selection pending' if 'portrait' in portrait_text else
                    'No verified portrait source listed')
        fs_search = p['fs'] or 'No FamilySearch profile is linked'
        search_text = ' '.join([p['name'], p['dates'], p['rationale'], fs_search, portrait] +
                               [f"{r['name']} {r['relationship']} {r['status']} {r['basis']}" for r in p['relationships']] +
                               [cite for cite, _ in p['citations']])
        body_rows.append(f'<tr data-search="{escape(search_text.casefold(),quote=True)}"><th scope="row">{link(p["profile"],p["name"])}<br><small>{escape(p["dates"])}</small></th><td>{escape(p["rationale"])}</td><td>{relations}</td><td>{citations}<p>{fs}</p></td><td>{escape(portrait)}</td></tr>')
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
    main = f'''<main class="r-main" id="main"><header class="v3-page-head"><span class="r-kicker">People in the Glasgow Name Study</span><h1>Notables</h1><p>This index follows the maintained Notables section in the <a href="/free-space/">Glasgow Name Study</a>. The historical list is a discovery aid: a shared surname or profile label alone does not prove a family connection.</p></header><section aria-labelledby="notables-index"><h2 id="notables-index">Historical people and their evidence</h2><label for="notables-filter">Filter people</label> <input id="notables-filter" type="search" placeholder="Name, dates, or description"><p id="notables-count" aria-live="polite">{len(data)} entries</p><div class="notables-table-wrap"><table id="notables-table"><thead><tr><th scope="col"><button data-sort="0">Person</button></th><th scope="col"><button data-sort="1">Why notable</button></th><th scope="col"><button data-sort="2">Family connections</button></th><th scope="col"><button data-sort="3">Profile and sources</button></th><th scope="col">Portrait status</th></tr></thead><tbody>{table}</tbody></table></div></section><p class="notables-method">Family connections reproduce current reviewed assessments, including alternatives and unselected links. An absent connection is not evidence against kinship. Follow the cited sources and person accounts for identity limits.</p></main>'''
    shell = re.sub(r'<main class="r-main" id="main">.*?</main>', main, shell, count=1, flags=re.S)
    script = '''<script>(()=>{const t=document.querySelector('#notables-table'),q=document.querySelector('#notables-filter'),n=document.querySelector('#notables-count'),b=[...t.tBodies[0].rows];function filter(){let s=q.value.trim().toLocaleLowerCase(),v=0;b.forEach(r=>{r.hidden=!r.dataset.search.includes(s);if(!r.hidden)v++});n.textContent=v+' of '+b.length+' entries'}q.addEventListener('input',filter);t.querySelectorAll('[data-sort]').forEach(x=>x.addEventListener('click',()=>{let i=+x.dataset.sort,rows=[...t.tBodies[0].rows],asc=x.dataset.asc!=='true';x.dataset.asc=String(asc);rows.sort((a,b)=>{let A=a.cells[i].innerText.trim(),B=b.cells[i].innerText.trim();return (A.localeCompare(B,undefined,{numeric:true,sensitivity:'base'}))*(asc?1:-1)}).forEach(r=>t.tBodies[0].append(r))}))})();</script>'''
    shell = shell.replace('</head>', '<style>.notables-table-wrap{overflow-x:auto;max-width:100%}#notables-table{width:100%;border-collapse:collapse}#notables-table th,#notables-table td{border-bottom:1px solid #c8cfc4;padding:.75rem;text-align:left;vertical-align:top}#notables-table thead{background:#eef1e9}#notables-table th button{font:inherit;font-weight:700;color:inherit;background:none;border:0;text-decoration:underline;cursor:pointer}#notables-table ul{padding-left:1.2rem;margin:.25rem 0}#notables-filter{max-width:100%;padding:.6rem;border:1px solid #66745e;border-radius:.3rem}@media(max-width:700px){#notables-table{min-width:760px}}</style></head>',1)
    shell = shell.replace('</body>', script+'</body>', 1)
    out = WEB/'notables/index.html'; out.parent.mkdir(parents=True, exist_ok=True); out.write_text(shell, encoding='utf-8')
    return len(data)

if __name__ == '__main__':
    print({'notables':render()})
