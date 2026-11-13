"""Editorial card presentation for the maintained Notables reader.

Ranks are a browsing order based on public distinction, not genealogical confidence.
Relationships remain qualified summaries of the existing research accounts.
"""
from html import escape
import re
import shutil

# ID, distinction, field, surname connection. Order is deliberately editorial.
FEATURES = [
 ('Glasgow-473', 'Pulitzer Prize–winning novelist', 'Literature', 'Glasgow surname; no established route to the early Scottish branches.'),
 ('Glasgow-773', 'General, senator & diplomat', 'Public life', 'Glasgow surname; his Australian career does not establish an early Scottish family connection.'),
 ('Glasgow-1220', 'Founder of the Tristan da Cunha settlement', 'Exploration', 'Recorded as William (Glasgow) Glass. The catalogue and inherited birth years differ.'),
 ('Glasgow-2265', 'Public-health pioneer & suffrage advocate', 'Medicine', 'The physician is linked from the Name Study’s American Settlers section. The catalogue gives a birth around 1869; Wikipedia gives 1876. Those dates are not reconciled here.'),
 ('Glasgow-634', 'North Carolina Secretary of State', 'Public life', 'Published biography names Maryland minister James Patrick Glasgow as his father; see the research account for the identity assessment.'),
 ('Hutcheson-1648', 'Founder of Hutchesons’ Hospital', 'Philanthropy', ''),
 ('Hutcheson-1649', 'Co-founder of Hutchesons’ school', 'Philanthropy', ''),
 ('Montgomery-24362', 'Baroness von Tautphoeus · novelist', 'Literature', 'Daughter of Jemima Glasgow and James Montgomery. Her mother’s proposed father link is unselected.'),
 ('Glasgow-2075', 'Tyneside songwriter & broadcaster', 'Music & theatre', 'Glasgow surname; no reviewed route to the earlier Scottish families is established on this page.'),
 ('Glasgow-2873', 'United States congressman & judge', 'Public life', 'A Pennsylvania Glasgow family. His public career identifies this Hugh; it does not establish a connection to other Glasgow branches.'),
 ('Glasgow-1780', 'Gujarati translator & professor', 'Church & learning', 'The catalogue connects this County Antrim missionary with the family of John Glasgow and Jane McClure. See his research account for the evidence and family assessments.'),
 ('Glasgow-1076', 'Plantation owner & Montgreenan patron', 'Land & commerce', 'Son of surgeon Robert Glasgow in the reviewed assessment; that father link is explicitly unselected.'),
 ('Glasgow-1073', 'Minister of Kilbirnie', 'Church & learning', 'Father of surgeon Robert Glasgow; his own parents remain uncertain.'),
 ('Glasgow-1075', 'Kilbirnie surgeon & chamberlain', 'Medicine', 'Son of Rev. John Glasgow and Jean Cunningham. Father of Robert of Montgreenan; the reviewed father links remain unselected.'),
 ('Glasgow-635', 'Presbyterian minister in Maryland', 'Church & learning', 'Published biography connects his Maryland ministry to politician James Glasgow. Scottish origins and upstream parentage remain uncertain.'),
 ('Glasgow-971', 'Merchant & owner of Oldcourt', 'Land & commerce', 'His proposed father John Glasgow remains an unselected connection; earlier ancestry is uncertain.'),
 ('Glasgow-1101', 'Glasgow graduate & probable Donegal cleric', 'Church & learning', 'The graduate and cleric are probably the same person; migration and birthplace are not proved.'),
 ('Glasgow-1077', 'Merchant · reported Irvine provost', 'Land & commerce', 'The provost identification is unresolved. His assessed father link to the Kilbirnie minister is unselected.'),
 ('Glasgow-3958', 'Mother of Baroness von Tautphoeus', 'Family connection', 'The novelist was her daughter. Her proposed father James Glasgow of Aughadenvarn remains unselected.'),
 ('Glasgow-1030', 'Early University of Glasgow graduate', 'Church & learning', 'No established family connection; reviewed records do not identify him as the Kilbirnie minister.'),
 ('Glasgow-1136', 'University of Glasgow M.A.', 'Church & learning', 'The maintained entry supplies dates but no further biography or established family connection.'),
 ('Glasgow-3410', 'University of Glasgow M.A.', 'Church & learning', 'The maintained entry supplies dates but no further biography or established family connection.'),
]
# Explicit exclusion: an Earl of Glasgow title alone is outside this surname list.
EXCLUDED = {'Boyle-1708'}

# Exact historical depictions checked 13 November 2026. Originals are retained
# in data/site/notables-images; the builder copies them into the public assets.
# Commons file pages retain fuller provenance and public-domain declarations.
PORTRAITS = {
    'Glasgow-473': ('glasgow-473.jpg', 753, 1521, 'Portrait of Ellen Glasgow',
        'The Critic, published by 1904 · photographer not stated',
        'https://commons.wikimedia.org/wiki/File:Ellen_Glasgow%27s_Portrait.jpg'),
    'Glasgow-773': ('glasgow-773.jpg', 1170, 1639, 'Sir Thomas William Glasgow, around 1930',
        'Fairfax archive · National Library of Australia, c. 1930',
        'https://commons.wikimedia.org/wiki/File:William_Glasgow_1930_(cropped).jpg'),
    'Glasgow-1220': ('glasgow-1220.jpg', 385, 262, 'William Glass outside his house on Tristan da Cunha, depicted by Augustus Earle',
        'William Glass outside his house · Augustus Earle',
        'https://commons.wikimedia.org/wiki/File:William_Glass_Tristan_da_Cunha.jpg'),
    'Hutcheson-1648': ('hutcheson-1648.jpg', 600, 817, 'George Hutcheson, an 1881 portrait plate after Scougall',
        'Hill’s history, 1881, plate at p. 18 · after Scougall',
        'https://archive.org/details/b22651196/page/n43/mode/1up'),
    'Hutcheson-1649': ('hutcheson-1649.jpg', 719, 845, 'Portrait of Thomas Hutcheson',
        'Thomas Hutcheson · unknown artist, seventeenth century',
        'https://commons.wikimedia.org/wiki/File:Thomas_Hutcheson.jpg'),
    'Montgomery-24362': ('montgomery-24362.jpg', 190, 280, 'Portrait of Jemima Montgomery, Baroness von Tautphoeus',
        'Baroness von Tautphoeus · unknown artist and date',
        'https://commons.wikimedia.org/wiki/File:CB40-2009-Jemima.jpg'),
}

CSS = '''
.notables-intro{max-width:65ch}.notable-portrait{margin:0 0 1.25rem}.notable-portrait>div{height:240px;border-radius:6px;background:#e8e5dc;overflow:hidden}.notable-portrait img{display:block;width:100%;height:100%;object-fit:contain}.notable-portrait figcaption{font-size:.7rem;line-height:1.5;color:#606757;padding:.5rem .1rem 0}.notables-reset{font:inherit;align-self:end;min-height:44px;padding:.6rem .8rem;border:1px solid #87927e;border-radius:5px;background:transparent;color:#29452f;cursor:pointer}.notables-toolbar{display:flex;flex-wrap:wrap;align-items:end;gap:1rem;padding:1.2rem;background:#f0eee7;border:1px solid #d6d9ce;border-radius:10px;margin:1.7rem 0 1rem}.notables-control{display:grid;gap:.35rem;flex:1 1 16rem}.notables-control label{font-size:.8rem;font-weight:700;letter-spacing:.05em;text-transform:uppercase}.notables-control input,.notables-control select{font:inherit;width:100%;min-height:44px;box-sizing:border-box;padding:.65rem .75rem;border:1px solid #87927e;border-radius:5px;background:#fff;color:#23382b}.notables-control input:focus-visible,.notables-control select:focus-visible,.notable-card a:focus-visible,.notable-card summary:focus-visible{outline:3px solid #b06430;outline-offset:3px}.notables-results{display:flex;justify-content:space-between;gap:1rem;flex-wrap:wrap;font-size:.85rem;color:#53604e;margin-bottom:1.2rem}.notables-results p{margin:0}.notables-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:1.2rem;list-style:none;padding:0;margin:0}.notable-card{display:flex;flex-direction:column;border:1px solid #d5d9cd;border-top:4px solid #778b6c;border-radius:10px;background:#fffef9;padding:1.4rem;min-width:0;box-shadow:0 3px 14px #25371e08}.notable-card[hidden]{display:none}.notable-card:first-child{border-top-color:#ac733e;background:#fcf7ec}.notable-card .notable-meta{display:flex;justify-content:space-between;gap:.75rem;align-items:center;margin:0 0 1rem;font-size:.75rem;color:#57664d;letter-spacing:.06em;text-transform:uppercase}.notable-rank{font-variant-numeric:tabular-nums;color:#796f5b}#notables-grid .notable-card h2{font-size:1.4rem;line-height:1.22;margin:0 0 .8rem;color:#233b2d;font-weight:800;letter-spacing:-.015em}.notable-name{font-size:1.05rem;font-weight:700;margin:0 0 .25rem}.notable-dates{font-size:.85rem;color:#626a5b;margin:0 0 1rem}.notable-summary{font-size:.95rem;line-height:1.6;margin:0 0 1rem}.notable-connection{padding:.9rem 1rem;background:#f0f3eb;border-radius:6px;font-size:.88rem;line-height:1.6;margin:auto 0 1rem}.notable-connection h3{font-family:inherit;font-size:.75rem;letter-spacing:.05em;text-transform:uppercase;margin:0 0 .4rem;color:#3e563a}.notable-connection p{margin:0}.notable-links{display:flex;flex-wrap:wrap;gap:.55rem 1rem;font-size:.85rem;font-weight:600}.notable-card details{font-size:.85rem;margin-top:1rem;border-top:1px solid #e0e3da;padding-top:.75rem}.notable-card summary{cursor:pointer;color:#465b3e}.notable-card details ul{padding-left:1.2rem;line-height:1.55}.notable-card details li+li{margin-top:.6rem}.notable-card a{overflow-wrap:anywhere}.notables-note{font-size:.85rem;line-height:1.6;color:#5a6353;max-width:75ch;margin-top:1.8rem}.notables-empty{padding:2rem;border:1px dashed #87927e;border-radius:8px;text-align:center}@media(min-width:1500px){.notables-grid{grid-template-columns:repeat(3,minmax(0,1fr))}}@media(max-width:760px){.notables-grid{grid-template-columns:minmax(0,1fr)}.notable-card{padding:1.1rem}.notables-toolbar{padding:1rem}#notables-grid .notable-card h2{font-size:1.3rem}}
'''

SCRIPT = r'''<script>(()=>{
const grid=document.querySelector('#notables-grid'),q=document.querySelector('#notables-filter'),sort=document.querySelector('#notables-sort'),field=document.querySelector('#notables-field'),count=document.querySelector('#notables-count'),empty=document.querySelector('#notables-empty'),cards=[...grid.children];
const normalize=s=>s.normalize('NFKD').replace(/[\u0300-\u036f]/g,'').toLocaleLowerCase();
function update(){
 const terms=normalize(q.value).trim().split(/\s+/).filter(Boolean);let visible=0;
 cards.forEach(c=>{c.hidden=Boolean(field.value&&c.dataset.field!==field.value)||!terms.every(t=>normalize(c.dataset.search).includes(t));if(!c.hidden)visible++});
 [...cards].sort((a,b)=>sort.value==='name'?a.dataset.name.localeCompare(b.dataset.name,undefined,{sensitivity:'base'}):Number(a.dataset.rank)-Number(b.dataset.rank)).forEach(c=>grid.append(c));
 count.textContent=visible+' of '+cards.length+' people';empty.hidden=visible!==0;
}
q.addEventListener('input',update);sort.addEventListener('change',update);field.addEventListener('change',update);
document.querySelector('#notables-reset').addEventListener('click',()=>{q.value='';field.value='';sort.value='notability';update();q.focus()});update();
})();</script>'''



def connection(p, text, link):
    if p['id'] not in {'Hutcheson-1648', 'Hutcheson-1649'}:
        return escape(text)
    def person(pid, name):
        return link('/people/'+pid.lower()+'.html', name)
    return ('The recorded tree connects the brothers through their mother '+
            person('Herbertson-132', 'Helen Herbertson')+', her proposed brother '+
            person('Herbison-440', 'Sir William Herbison')+', and his daughter '+
            person('Herbison-439', 'Margaret Herbison')+', wife of '+
            person('Glasgow-3522', 'William Glasgow')+'. '
            '<strong>This route is uncertain.</strong> Helen and William’s shared father is uncertain; '
            'later Glasgow family links also remain uncertain. This is a recorded family route, not proved Glasgow ancestry.')


def render(data, web, page_title, site_url, link, brief_summary):
    by_id = {p['id']: p for p in data if p['id'] not in EXCLUDED}
    ordered = [(by_id.pop(pid), title, field, conn) for pid, title, field, conn in FEATURES if pid in by_id]
    ordered.extend((p, 'Historical figure in the Glasgow Name Study', 'Research', 'See the research account for family connections.') for p in by_id.values())
    cards = []
    for rank, (p, title, field, conn) in enumerate(ordered, 1):
        summary = brief_summary(p)
        if p['id'] == 'Glasgow-635':
            summary = 'Patrick Glasgow ministered at Manokin and All Hallows in Maryland. Published biography identifies the North Carolina secretary as his son; upstream parentage remains uncertain.'
        dates = p['dates']
        # Do not promote inherited disputed birthdays above the reviewed account.
        if p['id'] == 'Hutcheson-1648': dates = 'Born 1550–1560 · died 1639'
        if p['id'] == 'Hutcheson-1649': dates = 'Born c. 1590 · died 1641 (published biography)'
        if p['id'] == 'Montgomery-24362': dates = '1807–1893'
        if p['id'] == 'Glasgow-2265': dates = 'Born c. 1869 or 1876 · died 1955'
        name = {'Glasgow-473':'Ellen Glasgow', 'Glasgow-773':'Sir Thomas William Glasgow', 'Glasgow-1076':'Sir Robert Glasgow of Montgreenan', 'Montgomery-24362':'Jemima Montgomery', 'Glasgow-2075':'Alex Glasgow'}.get(p['id'],p['name'])
        # Lifespans scan more easily as years; keep explicit date qualifications.
        dates = re.sub(r'(\d{4})-\d{2}(?:-\d{2})?', r'\1', dates)
        conn_html = connection(p, conn, link)
        search = ' '.join([name, p['id'], p['fs'], title, field, dates, summary, re.sub('<[^>]*>', ' ', conn_html), p['rationale']] + [cite for cite, _ in p['citations']])
        portrait = ''
        if p['id'] in PORTRAITS:
            filename, width, height, alt, credit, source = PORTRAITS[p['id']]
            asset = web/'assets/notables'/filename
            asset.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(web.parent/'data/site/notables-images'/filename, asset)
            loading = 'eager' if rank == 1 else 'lazy'
            portrait = f'<figure class="notable-portrait"><div><img src="/assets/notables/{filename}" width="{width}" height="{height}" alt="{escape(alt,quote=True)}" loading="{loading}" decoding="async"></div><figcaption>{link(source,credit)} · Public domain</figcaption></figure>'
        links = [link(p['profile'], 'Research account'), link('https://www.wikitree.com/wiki/'+p['id'], 'WikiTree')]
        if p['fs']: links.append(link('https://www.familysearch.org/tree/person/details/'+p['fs'], 'FamilySearch'))
        citations, seen = [], set()
        for cite, urls in p['citations']:
            if cite in seen: continue
            seen.add(cite)
            citations.append('<li>'+(link(urls[0],cite) if urls else escape(cite))+'</li>')
        sources = '<details><summary>Sources &amp; evidence</summary><ul>'+''.join(citations)+'</ul></details>' if citations else ''
        cards.append(f'''<li class="notable-card" data-rank="{rank}" data-field="{escape(field,quote=True)}" data-name="{escape(name,quote=True)}" data-search="{escape(search,quote=True)}">{portrait}<p class="notable-meta"><span>{escape(field)}</span><span class="notable-rank">{rank:02}</span></p><h2>{escape(title)}</h2><p class="notable-name">{link(p['profile'],name)}</p><p class="notable-dates">{escape(dates or 'Dates not established')}</p><p class="notable-summary">{escape(summary)}</p><div class="notable-connection"><h3>Connection to the Glasgows</h3><p>{conn_html}</p></div><nav class="notable-links" aria-label="{escape(name,quote=True)} profiles">{' '.join(links)}</nav>{sources}</li>''')
    fields = sorted({field for _, _, field, _ in ordered})
    options = ''.join(f'<option value="{escape(field,quote=True)}">{escape(field)}</option>' for field in fields)
    main = f'''<main class="r-main" id="main"><header class="v3-page-head"><span class="r-kicker">The Glasgow Name Study</span><h1>Notables</h1><p class="notables-intro">Writers, pioneers, public figures and benefactors: the people behind the name, and the families connected to it.</p></header><div class="notables-toolbar"><div class="notables-control"><label for="notables-filter">Find a person</label><input id="notables-filter" type="search" placeholder="Name, achievement or family connection…" aria-controls="notables-grid"></div><div class="notables-control"><label for="notables-field">Explore a field</label><select id="notables-field" aria-controls="notables-grid"><option value="">All fields</option>{options}</select></div><div class="notables-control"><label for="notables-sort">Sort people</label><select id="notables-sort" aria-controls="notables-grid"><option value="notability">Most notable first</option><option value="name">Name A–Z</option></select></div><button class="notables-reset" id="notables-reset" type="button">Reset</button></div><div class="notables-results"><p id="notables-count" role="status" aria-live="polite">{len(cards)} people</p><p>{sum(p['id'] in PORTRAITS for p, _, _, _ in ordered)} historical images · family context on every card</p></div><ol class="notables-grid" id="notables-grid" aria-label="Notable people">{''.join(cards)}</ol><p class="notables-empty" id="notables-empty" hidden>No people match your search. Try a surname, place or achievement.</p><p class="notables-note">The default order is an editorial guide to public prominence, not a measure of family confidence. School founders and relatives are included where the study records a family connection; uncertain routes are labelled. Some entries are retained for their historical research interest. Selected from our <a href="/catalogue/">people catalogue</a> and <a href="/free-space/">Glasgow Name Study</a>, with <a href="https://en.wikipedia.org/wiki/Glasgow_(surname)" target="_blank" rel="noopener">Wikipedia’s Glasgow surname list</a> checked for omissions. Modern names without a checked public catalogue match are not included. Images reproduce credited historical depictions, not verified photographs of every subject.</p></main>'''
    shell = (web/'research/index.html').read_text(encoding='utf-8')
    shell = re.sub(r'<title>.*?</title>', '<title>'+escape(page_title('Notables'))+'</title>', shell, count=1, flags=re.S)
    shell = re.sub(r'<link rel="canonical" href="[^"]*"\s*/?>', f'<link rel="canonical" href="{site_url}/notables/">', shell, count=1)
    shell = re.sub(r'<meta property="og:url" content="[^"]*"\s*/?>', f'<meta property="og:url" content="{site_url}/notables/">', shell, count=1)
    shell = re.sub(r'<meta\b(?=[^>]*\bname="description")[^>]*>', '<meta name="description" content="Notable Glasgow writers, pioneers and public figures, with sourced achievements and qualified family connections.">', shell, count=1)
    shell = shell.replace('data-g-path="/research/index.html"','data-g-path="/notables/index.html"',1).replace('<strong>Research</strong>','<strong>Notables</strong>',1)
    shell = re.sub(r'<nav class="v3-view-nav" aria-label="Section views">.*?</nav>', '', shell, count=1, flags=re.S)
    shell = re.sub(r'<main class="r-main" id="main">.*?</main>', lambda _: main, shell, count=1, flags=re.S)
    shell = shell.replace('</head>', '<style>'+CSS+'</style></head>',1).replace('</body>',SCRIPT+'</body>',1)
    out = web/'notables/index.html'
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(shell,encoding='utf-8')
    return len(cards)
