"""Public reading edition of maintained WikiTree studies; originals remain evidence."""
from __future__ import annotations
from html import escape, unescape
import hashlib, json, re
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit
import mwparserfromhell as mw
from bs4 import BeautifulSoup
from tools.public_privacy import from_sources

ROOT=Path(__file__).resolve().parents[1]
EDITION=ROOT/'research/free-space-pages/edition.json'
STATE=ROOT/'research/free-space-pages/sync-state.json'
SENSITIVE=re.compile(r'kitId|kit_num|GEDmatch\s*(?:ID|kit)|MitoYDNA\s*ID|\bkit\s*(?:number|#)|[\w.+-]+@[\w.-]+\.[a-z]{2,}|<Private>',re.I)
PUBLIC_NOTICE='Personal match details, tester identifiers and private information are omitted from this public edition; the historical research and source references are retained.'
EXTRA_FILES={
'Robert de Glasgu Dublin guild':'Robert_de_Glasgu_Dublin_guild.md','Robert de Glascu plea roll 1200':'Robert_de_Glascu_plea_roll_1200.md','Gilbert de Glascu':'Gilbert_de_Glascu.md','Alexander son of Robert de Glascu':'Alexander_son_of_Robert_de_Glascu.md','Robert de Glasgu Dunkeld clerk':'Robert_de_Glasgu_Dunkeld_clerk.md','Robert de Glascu Durham witness':'Robert_de_Glascu_Durham_witness.md','Hugh de Glasgw':'Hugh_de_Glasgw.md','Master Walter de Glasgu':'Master_Walter_de_Glasgu.md','John of Glasgow (Holyrood)':'John_of_Glasgow_Holyrood.md','Richard of Glasgow Arbroath':'Richard_of_Glasgow_Arbroath.md','John de Glasgu (royal account 1343)':'John_de_Glasgu_royal_account_1343.md','John de Glasgu (father of Malcolm)':'John_de_Glasgu_father_of_Malcolm.md','Malcolm son of John de Glasgu':'Malcolm_son_of_John_de_Glasgu.md','William physician de Glasgu':'William_physician_de_Glasgu.md'}


def key(value):
    return unquote(value).replace('_',' ').strip().casefold()


def digest(text): return hashlib.sha256(text.encode()).hexdigest()


def public_text(text, policy, page_id=''):
    """Withhold complete sensitive passages, never rewrite a private identity into a claim."""
    removed=0
    if key(page_id)==key('Space:Personal genetic exploration'):
        text,n=re.subn(r'(?ms)^==\s*My Matches\s*==.*','\n'+PUBLIC_NOTICE+'\n',text);removed+=n
    code=mw.parse(text)
    for table in list(code.filter_tags(matches=lambda n:str(n.tag).lower()=='table',recursive=False)):
        raw=str(table)
        if SENSITIVE.search(raw) or policy.contains_private_id(raw) or (('DNA' in page_id.upper() or re.match(r'Space:R-',page_id)) and re.search(r'(?m)^\|\s*\d{5,}',raw)):
            code.replace(table,PUBLIC_NOTICE);removed+=1
    blocks=re.split(r'(\n\s*\n)',str(code));safe=[]
    for block in blocks:
        if SENSITIVE.search(block) or policy.contains_private_id(block):
            # Within prose/list blocks, retain separate safe lines where possible.
            lines=[]
            for line in block.splitlines():
                if SENSITIVE.search(line) or policy.contains_private_id(line):removed+=1
                else:lines.append(line)
            block='\n'.join(lines)
        safe.append(block)
    result=''.join(safe)
    if SENSITIVE.search(result) or policy.contains_private_id(result):raise ValueError('Unfiltered private passage')
    return result,removed


def sentence_excerpt(text, limit=270):
    """Prefer whole sentences; otherwise truncate at a word boundary visibly."""
    text = ' '.join(text.split())
    if len(text) <= limit:
        return text
    head = text[:limit - 1]
    endings = list(re.finditer(r'[.!?](?:[”\"\']?)(?=\s|$)', head))
    if endings:
        return head[:endings[-1].end()] + '…'
    return head.rsplit(' ', 1)[0].rstrip(',;:—–-') + '…'


def excerpt(text):
    for block in re.split(r"\n\s*\n",text):
        if block.lstrip().startswith(('[[Category:','{{','<small>','{|','=','*','#','<references')):continue
        plain=mw.parse(block).strip_code().strip()
        if len(plain)>85:return sentence_excerpt(plain)
    return 'A historical research account with its original source references.'


def importance(page):
    title=page['title'].casefold()
    if title=='glasgow name study':return 100
    if title=='glasgow research':return 98
    if title.startswith('bearers of'):return 96
    if 'branches in early ireland' in title:return 95
    if 'branches in 15th and' in title:return 94
    if title=='glasgow dna':return 93
    if 'protocol books' in title:return 92
    if 'wills' in title:return 91
    if 'londonderry' in title:return 90
    if 'chronology' in title:return 88
    if 'surname origins' in title:return 86
    if title in ('glasgow history','glasgow ancient ydna'):return 84
    if page.get('summary'):return 82
    if 'hypothesis' in title or 'identifying' in title:return 75
    if re.match(r'r-',title):return 65
    if page.get('startDate'):return 70
    return 60


def slug_for(page):
    title=re.sub(r'[^a-z0-9]+','-',page['title'].lower()).strip('-')[:82]
    return title+'-'+digest(page['wikitreeId'])[:6]


def prepare(pages, source, summaries):
    policy=from_sources();old=json.loads(EDITION.read_text()) if EDITION.exists() else {'pages':{}}
    studies={s['wikitreeId']:s for s in summaries['studies']};inputs={};variants={}
    for captured in source['pages']:
        canonical=key(captured['wikitreeId'])
        if canonical in inputs:variants.setdefault(canonical,[]).append(captured)
        else:inputs[canonical]=captured
    output=[]
    for p in pages:
        p=dict(p);pid=p['wikitreeId'];meta=inputs.get(key(pid));path=ROOT/meta['localFile'] if meta else ROOT/'surname-research/free-space-pages'/EXTRA_FILES[pid[6:]]
        body=path.read_text();body,removed=public_text(body,policy,pid)
        previous=old['pages'].get(pid,{})
        # Local edition edits win on subsequent builds; source refresh needs review.
        local=ROOT/previous.get('editionFile',f'research/free-space-pages/edition/{slug_for(p)}.wiki')
        local_edited=bool(previous.get('localEdited'))
        if previous and local.exists() and (local_edited or digest(local.read_text())!=previous.get('publicHash')):
            body,_=public_text(local.read_text(),policy,pid);local_edited=True
        local.parent.mkdir(parents=True,exist_ok=True);local.write_text(body)
        p.update(localEdited=local_edited,variantFiles=[v['localFile'] for v in variants.get(key(pid),[])],slug=slug_for(p),url='/free-space/'+slug_for(p)+'/',importance=importance({**p,'summary':pid in studies}),summary=studies.get(pid),editionFile=str(local.relative_to(ROOT)),sourceFile=str(path.relative_to(ROOT)),sourceHash=digest(path.read_text()),publicHash=digest(body),omittedPassages=removed,capturedAt=source['capturedAt'] if meta else '2026-08-29',bodyStatus='Blank source' if not body.strip() else 'Local reading edition')
        output.append(p)
    output.sort(key=lambda p:(-p['importance'],p['title'].casefold(),p['wikitreeId']))
    EDITION.write_text(json.dumps({'schema_version':1,'pages':{p['wikitreeId']:p for p in output}},ensure_ascii=False,indent=2)+'\n')
    return output


class Renderer:
    def __init__(self,pages):
        self.links={key(p['wikitreeId']):p['url'] for p in pages};self.refs={};self.headings=[];self.serial=0
    def href(self,target):
        target=unescape(str(target).strip());base,sep,frag=target.partition('#')
        if target.startswith(('http://','https://')):
            u=urlsplit(target)
            if u.hostname in ('www.wikitree.com','wikitree.com','api.wikitree.com') and '/wiki/' in u.path:
                return self.href(unquote(u.path.split('/wiki/',1)[1])+('#'+u.fragment if u.fragment else ''))
            if u.hostname=='glasgow.phenotype.dev':return u.path+('?' + u.query if u.query else '')+('#'+u.fragment if u.fragment else '')
            return target
        if target.startswith('#'):return '#'+self.anchor(frag)
        if key(base) in self.links:return self.links[key(base)]+('#'+self.anchor(re.sub(r'\.(28|29|2C|26|27|3A|2F)',r'%\1',frag,flags=re.I)) if sep else '')
        if re.fullmatch(r'[A-Za-z][A-Za-z_\-\'’]+-\d+',base):
            local='/people/'+base.lower()+'.html'
            if (ROOT/'www'/local.lstrip('/')).exists():return local+('#'+frag if sep else '')
        return 'https://www.wikitree.com/wiki/'+quote(base.replace(' ','_'),safe=":/'()")+('#'+quote(frag) if sep else '')
    @staticmethod
    def anchor(value):return re.sub(r'[^a-z0-9]+','-',unquote(value).casefold()).strip('-') or 'section'
    def inline(self,value):
        code=value if isinstance(value,mw.wikicode.Wikicode) else mw.parse(str(value));out=[]
        for n in code.nodes:
            if isinstance(n,mw.nodes.Text):out.append(escape(str(n)))
            elif isinstance(n,mw.nodes.Comment):continue
            elif isinstance(n,mw.nodes.HTMLEntity):out.append(escape(n.normalize()))
            elif isinstance(n,mw.nodes.Wikilink):
                target=str(n.title)
                if target.startswith('Category:'):continue
                label=self.inline(n.text if n.text is not None else target.replace('Space:',''))
                if target.startswith(('File:','Image:')):label='Source illustration: '+label
                out.append(f'<a href="{escape(self.href(target),quote=True)}">{label}</a>')
            elif isinstance(n,mw.nodes.ExternalLink):
                url=str(n.url);label=self.inline(n.title) if n.title is not None else escape(url)
                if urlsplit(url).scheme in ('http','https'):out.append(f'<a href="{escape(self.href(url),quote=True)}" rel="noopener">{label}</a>')
                else:out.append(label)
            elif isinstance(n,mw.nodes.Heading):out.append(self.heading(n.title,n.level))
            elif isinstance(n,mw.nodes.Template):
                name=str(n.name).strip().lower()
                if name in ('one name study','clear','reflist'):continue
                if name=='!':out.append('|');continue
                if name=='image':
                    caption=str(n.get('caption').value) if n.has('caption') else ''
                    file=str(n.get('file').value).strip() if n.has('file') else ''
                    out.append('<span class="fsp-illustration">'+self.inline(caption)+(f' <a href="{escape(self.href("Image:"+file),quote=True)}">View source illustration</a>' if file else '')+'</span>')
                else:
                    # Preserve citation-template content as labelled source text.
                    values=[self.inline(p.value) for p in n.params if str(p.name).strip().lower() not in ('style','class','width','size')]
                    out.append('<span class="fsp-template">'+escape(str(n.name).strip())+(': '+' · '.join(values) if values else '')+'</span>')
            elif isinstance(n,mw.nodes.Tag):out.append(self.tag(n))
            else:out.append(escape(str(n)))
        return ''.join(out)
    def heading(self,title,level):
        label=mw.parse(str(title)).strip_code();anchor=self.anchor(label);self.serial+=1
        if any(h[0]==anchor for h in self.headings):anchor+='-'+str(self.serial)
        self.headings.append((anchor,label));level=min(5,max(2,level))
        return f'<h{level} id="{anchor}">{self.inline(title)}</h{level}>'
    def tag(self,n):
        name=str(n.tag).lower()
        if name=='ref':
            refname=str(n.get('name').value).strip('"\' ') if n.has('name') else 'citation-'+str(len(self.refs)+1)
            if refname not in self.refs:self.refs[refname]={'number':len(self.refs)+1,'body':''}
            if str(n.contents).strip():self.refs[refname]['body']=self.inline(n.contents)
            return f'<sup><a href="#citation-{self.refs[refname]["number"]}" aria-label="Source {self.refs[refname]["number"]}">[{self.refs[refname]["number"]}]</a></sup>'
        if name=='references':return '<!-- references collected below -->'
        if name in ('script','style','iframe','object'):return ''
        if name in ('table','tr','th','td'):
            attrs=''
            for attr in n.attributes:
                if str(attr.name).lower() in ('colspan','rowspan') and re.fullmatch(r'\d+',str(attr.value).strip('"\' ')):attrs+=f' {attr.name}="{escape(str(attr.value).strip(chr(34)+chr(39)+" "))}"'
            body=self.inline(n.contents)
            if name=='table':
                # MediaWiki headers may appear before the first explicit row.
                soup=BeautifulSoup('<table>'+body+'</table>','html.parser');table=soup.table
                loose=list(table.find_all(['th','td'],recursive=False))
                if loose:
                    row=soup.new_tag('tr');loose[0].insert_before(row)
                    for c in loose:row.append(c.extract())
                return '<div class="fsp-table-scroll">'+str(table)+'</div>'
            return f'<{name}{attrs}>{body}</{name}>'
        if name=='a':
            href=str(n.get('href').value).strip('"\'') if n.has('href') else ''
            return '<a href="'+escape(self.href(href),quote=True)+'">'+self.inline(n.contents)+'</a>' if href and not href.lower().startswith(('javascript:','data:')) else self.inline(n.contents)
        if name=='br':return '<br>'
        if name in ('b','strong','i','em','small','s','del','sub','sup','blockquote','code','pre','div','span','p','ul','ol','li','dl','dt','dd'):
            return f'<{name}>'+self.inline(n.contents)+f'</{name}>' if str(n.contents) else ''
        return self.inline(n.contents)
    def render(self,text):
        # Treat complete tables as blocks, retaining multiline cells and refs.
        code=mw.parse(text);tables=[]
        for n in list(code.filter_tags(matches=lambda n:str(n.tag).lower()=='table',recursive=False)):
            token='EDITIONTABLE'+str(len(tables))+'END';tables.append(n);code.replace(n,'\n\n'+token+'\n\n')
        out=[];paragraph=[];lists=[]
        def flush():
            if paragraph:out.append('<p>'+self.inline('\n'.join(paragraph))+'</p>');paragraph.clear()
        def close_lists():
            while lists:out.append('</li></'+lists.pop()+'>')
        for line in str(code).splitlines():
            table=re.fullmatch(r'EDITIONTABLE(\d+)END',line.strip());h=re.match(r'^(={1,6})\s*(.*?)\s*\1\s*$',line);li=re.match(r'^([*#]+)\s*(.*)',line)
            if li:
                flush();types=['ul' if c=='*' else 'ol' for c in li[1]]
                while len(lists)>len(types) or (lists and lists!=types[:len(lists)]):out.append('</li></'+lists.pop()+'>')
                if len(lists)==len(types):out.append('</li><li>')
                else:
                    while len(lists)<len(types):lists.append(types[len(lists)]);out.append('<'+lists[-1]+'><li>')
                out.append(self.inline(li[2]));continue
            close_lists()
            if table:flush();out.append(self.tag(tables[int(table[1])]))
            elif h:flush();out.append(self.heading(h[2],len(h[1])))
            elif not line.strip():flush()
            elif line.startswith(':'):flush();out.append('<blockquote>'+self.inline(line.lstrip(': '))+'</blockquote>')
            elif line.strip()=='----':flush();out.append('<hr>')
            else:paragraph.append(line)
        flush();close_lists()
        if self.refs:
            out.append('<section class="fsp-citations" aria-label="Source references"><h2 id="source-references">Source references</h2><ol>')
            for ref in self.refs.values():out.append(f'<li id="citation-{ref["number"]}">{ref["body"] or "Named source referenced without its full citation in the saved page."}</li>')
            out.append('</ol></section>')
        html=''.join(out)
        soup=BeautifulSoup(html,'html.parser')
        for a in soup.select('a[href]'):
            if a['href'].lower().startswith(('javascript:','data:')):a.attrs.pop('href')
        for p in soup.select('p'):
            if not p.get_text(strip=True) and not p.find(['img','a']):p.decompose()
        return str(soup)


def shell_page(shell,main,title,path,description=None):
    from tools.site_analytics import with_analytics
    soup=BeautifulSoup(shell,'html.parser')
    soup.title.string=title+' · Glasgow surname archive'
    for tag in soup.select('meta[name="description"],link[rel="canonical"]'):
        tag.decompose()
    soup.head.append(soup.new_tag('meta', attrs={'name': 'description', 'content': description or f'{title}: Glasgow surname research, source references and current questions.'}))
    canonical = '/' + path.lstrip('/')
    if canonical.endswith('index.html'):
        canonical = canonical[:-len('index.html')]
    soup.head.append(soup.new_tag('link', rel='canonical', href='https://glasgow.phenotype.dev' + canonical))
    for old in soup.select('link[href*="/assets/free-space/"],script[src*="/assets/free-space/"]'):old.decompose()
    soup.head.append(soup.new_tag('link',rel='stylesheet',href='/assets/free-space/site.css?v=edition'))
    soup.body.append(soup.new_tag('script',defer='',src='/assets/free-space/site.js?v=edition'))
    soup.body['data-g-path']=path
    classes=[c for c in soup.body.get('class',[]) if not c.startswith('g-kind-')];soup.body['class']=classes+['g-kind-free-space']
    old=soup.find('main');old.replace_with(BeautifulSoup(main,'html.parser'))
    crumb=soup.select_one('.g-crumbs strong')
    if crumb:crumb.string=title
    return with_analytics(str(soup))


TOPICS = {
    'Project and methods': 'The surname project and how to use the research.',
    'Early and medieval': 'Early name bearers and the origins of the surname.',
    'Scotland and records': 'Scottish records, wills, testaments and local history.',
    'Ireland and migration': 'Irish branches, settlement and family movements.',
    'DNA and haplogroups': 'Genetic studies alongside the documentary evidence.',
    'Families and case studies': 'Named families, identities and parentage questions.',
}


COLLECTIONS = (
    ('Early and medieval', 'early', 'Early names & surname origins', '1175–1500'),
    ('Scotland and records', 'scotland', 'Scotland in the records', 'Wills · protocol books · local history'),
    ('Ireland and migration', 'ireland', 'Irish branches & migration', 'Ulster · settlement · family movements'),
    ('Families and case studies', 'families', 'Families & open questions', 'People · identities · possible parents'),
    ('DNA and haplogroups', 'dna', 'DNA alongside the documents', 'Y-DNA · haplogroups · genetic studies'),
    ('Project and methods', 'methods', 'The project & its methods', 'Research guides · scope · sources'),
)

# Reader introductions to existing studies, separate from full evidence warnings.
COLLECTION_PREVIEWS = {
    'early': 'Read the medieval name occurrences and the explicit father–son statements. The records do not establish one continuous medieval pedigree.',
    'scotland': 'Begin with the structured Glasgow burgh protocol index: property transactions, named spouses and family statements. The wider notebook preserves older leads and theories that still need checking.',
    'ireland': 'Follow the early Ulster households and the Archibald–Thomas father statement. Identifying that son with the Lifford adult remains strongly probable; wider family connections are unresolved.',
    'families': 'Compare the proposed parents of John Glasgow, born about 1751 in County Antrim. Robert of Kilwaughter and James remain candidates; no inspected record states the proposed relationships.',
    'dna': 'Compare Y-DNA paternal groups with documented father-to-son lines. Shared ancestry and estimated branch ages do not by themselves identify a missing named ancestor.',
    'methods': 'Use the research directory to choose a person, place, record group or family question, then follow its evidence and current assessment.',
}

COLLECTION_ICONS = {
    'early': '<path d="M12 38h24M16 38V20l8-12 8 12v18M16 20h16M22 38V28h4v10M22 20v-6h4v6M8 38h4V26H8v12m28 0h4V26h-4"/>',
    'scotland': '<path d="M9 10h23l7 7v23H9V10m23 0v8h7M15 24h18M15 29h18M15 34h11"/>',
    'ireland': '<circle cx="13" cy="15" r="5"/><circle cx="35" cy="34" r="5"/><path d="M13 20v6c0 8 17-5 17 3M27 24l3 5-5 2"/>',
    'families': '<circle cx="24" cy="10" r="5"/><circle cx="11" cy="35" r="5"/><circle cx="37" cy="35" r="5"/><path d="M24 15v8M11 30v-7h26v7"/>',
    'dna': '<path d="M13 7c0 13 22 21 22 34M35 7c0 13-22 21-22 34M14 10h20M18 17h12M18 31h12M14 38h20"/>',
    'methods': '<path d="M24 13c-5-5-12-5-17-3v27c5-2 12-2 17 3 5-5 12-5 17-3V10c-5-2-12-2-17 3v27M12 17l7 1m-7 6 7 1m10-7 7-1m-7 8 7-1"/>',
}


def collection_icon(slug):
    return f'<svg class="fsp-collection-icon" viewBox="0 0 48 48" aria-hidden="true" focusable="false">{COLLECTION_ICONS[slug]}</svg>'


def study_preview(page):
    """Use the existing conclusion, keeping its qualifications, or a public excerpt."""
    return sentence_excerpt(page['summary']['conclusion']) if page.get('summary') else excerpt((ROOT / page['editionFile']).read_text())


def display_title(page):
    title = page['title'].replace("''", '')
    if page['wikitreeId'].startswith('Space:Bearers of'):
        return 'Medieval name bearers, c.1175–1500'
    return title


def directory_main(pages, cards):
    categories = [c for c in TOPICS if any(p['category'] == c for p in pages)]
    options = ''.join(f'<option value="{escape(c, quote=True)}">{escape(c)}</option>' for c in categories)
    overview = next(p for p in pages if p['wikitreeId'] == 'Space:Glasgow Name Study')
    shelves = []
    quicklinks = []
    for number, (category, slug, label, scope) in enumerate(COLLECTIONS, 1):
        studies = [p for p in pages if p['category'] == category and p['bodyStatus'] != 'Blank source']
        if category == 'Project and methods':
            studies = [p for p in studies if p is not overview]
        if not studies:
            continue
        lead = studies[0]
        count = sum(p['category'] == category for p in pages)
        links = ''.join(f'<li><a href="{p["url"]}">{escape(display_title(p))}<span aria-hidden="true">↗</span></a></li>' for p in studies[1:3])
        assessment = f'<span class="fsp-assessment">{escape(lead["summary"]["confidence"])}</span>' if lead.get('summary') else ''
        shelves.append(f'''<section class="fsp-collection fsp-collection-{slug}" id="collection-{slug}" aria-labelledby="collection-{slug}-title">
<div class="fsp-collection-head"><div class="fsp-collection-emblem">{collection_icon(slug)}</div><div><span class="fsp-collection-scope">{escape(scope)}</span><h3 id="collection-{slug}-title">{escape(label)}</h3></div><span class="fsp-collection-total"><strong>{count}</strong> studies</span></div>
<div class="fsp-collection-body"><div class="fsp-lead-study"><span class="fsp-small-label">Principal study</span><h4><a href="{lead['url']}" title="{escape(lead['title'].replace(chr(39)*2, ''), quote=True)}">{escape(display_title(lead))}</a></h4>{assessment}<p>{escape(COLLECTION_PREVIEWS[slug])}</p><a class="fsp-study-action" href="{lead['url']}">Read the study <span aria-hidden="true">→</span></a></div><div class="fsp-collection-more"><span class="fsp-small-label">Continue reading</span><ul>{links}</ul><button type="button" class="fsp-collection-button" data-fsp-topic="{escape(category, quote=True)}" data-description="{escape(TOPICS[category], quote=True)}" aria-pressed="false">Browse all {count} studies <span aria-hidden="true">→</span></button></div></div></section>''')
        if slug in ('early', 'scotland', 'ireland', 'dna'):
            quicklabels = {'early': 'Early names', 'scotland': 'Scottish records', 'ireland': 'Irish branches', 'dna': 'DNA studies'}
            quicklinks.append(f'<a href="#collection-{slug}" data-fsp-collection-anchor="{slug}">{collection_icon(slug)}<span>{quicklabels[slug]}<small>{count} studies</small></span><span aria-hidden="true">↓</span></a>')
    return f'''<main class="r-main fsp-main fsp-directory" id="main">
<header class="fsp-hero"><div class="fsp-hero-intro"><span class="fsp-eyebrow">The Glasgow surname project</span><h1>Free-space<br> research library</h1><p>People, places and records behind the Glasgow surname. Follow a family, explore a collection, or begin with the earliest names.</p><div class="fsp-hero-bottom"><a href="#library" class="fsp-hero-action">Explore the collections <span aria-hidden="true">↓</span></a><span>{len(pages)} studies · {len(shelves)} collections</span></div></div><aside class="fsp-overview"><span class="fsp-small-label">Begin with the overview</span><h2><a href="{overview['url']}">Glasgow<br> Name Study</a></h2><p>The story of the name, its historical forms and the main research routes — from medieval occurrences to families around the world.</p><a href="{overview['url']}" class="fsp-study-action">Open the name study <span aria-hidden="true">↗</span></a><div class="fsp-paper-lines" aria-hidden="true"></div></aside></header>
<nav class="fsp-quicklinks" aria-label="Reading routes">{''.join(quicklinks)}</nav>
<section class="fsp-library" id="library" aria-labelledby="fsp-library-title"><div class="fsp-section-heading"><div><span class="fsp-small-label">Find your next study</span><h2 id="fsp-library-title">Explore the collections</h2></div><p id="fsp-count" class="fsp-count" aria-live="polite">{len(shelves)} collections · {len(pages)} studies</p></div><p class="fsp-topic-description" id="fsp-topic-description">Start with a principal study, then follow the related records and family questions.</p>
<form class="fsp-controls" role="search" aria-label="Search the research library"><div class="fsp-search-row"><label class="fsp-search-label"><span class="sr-only">Search studies</span><svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="10" cy="10" r="6"/><path d="m15 15 5 5"/></svg><input id="fsp-search" type="search" placeholder="Search all {len(pages)} studies: a family, place, record or year…" aria-controls="fsp-results"></label><div class="fsp-view-switch" aria-label="Library view"><button type="button" id="fsp-show-collections" aria-pressed="true">Collections</button><button type="button" id="fsp-show-list" aria-pressed="false">Study list</button></div></div><div class="fsp-refine" id="fsp-refine"><label>Topic<select id="fsp-category"><option value="">All topics</option>{options}</select></label><label>Sort by<select id="fsp-order"><option value="importance">Importance first</option><option value="title">Title A–Z</option></select></label><button id="fsp-clear" type="button">Reset filters</button></div></form>
<div class="fsp-collections" id="fsp-collections">{''.join(shelves)}</div>
<div class="fsp-results-panel" id="fsp-results-panel"><noscript><p class="fsp-edition-note">All {len(pages)} studies are listed below. Enable JavaScript to search and browse shorter pages.</p><style>.fsp-view-switch,.fsp-refine,.fsp-collection-button{{display:none}}</style></noscript><h2 class="fsp-print-title">Research studies</h2><div class="fsp-grid" id="fsp-results">{''.join(cards)}</div><div id="fsp-empty" class="g-empty" hidden><h3>No studies found</h3><p>Try a broader name, a different topic or fewer words.</p><button type="button" data-fsp-reset>Clear filters</button></div><nav class="fsp-pagination" id="fsp-pagination" aria-label="Study result pages" hidden><button type="button" id="fsp-prev">← Previous</button><span id="fsp-page-status" aria-live="polite"></span><button type="button" id="fsp-next">Next →</button></nav></div></section>
<aside class="fsp-edition-strip"><span class="fsp-edition-seal" aria-hidden="true">II</span><p><strong>A second edition, kept alongside WikiTree.</strong><br>Full studies and original references, with local corrections preserved. Each study links to its WikiTree edition, draft and available comparisons.</p><a href="#edition-updates">About this edition <span aria-hidden="true">↓</span></a></aside>
<section class="fsp-updates" id="edition-updates"><details><summary>WikiTree updates &amp; edition comparisons</summary><div><p>Confidence belongs to each source and conclusion; a research narrative does not establish every relationship it discusses.</p><p>WikiTree changes are pulled into a comparison, never over an edited local study. Matching text can be marked current; changes on one side can be reviewed for transfer. If both versions changed, both remain available until the differences are resolved.</p><p>Each reading page provides its full local WikiTree draft. Checked remote text and a diff appear after a successful pull. A remote access failure is recorded explicitly. Saving a reviewed draft on WikiTree remains a separate action.</p></div></details></section></main>'''


def build_site(source,pages,studies):
    pages=prepare(pages,source,studies);web=ROOT/'www';shell=(web/'research/index.html').read_text();state=json.loads(STATE.read_text()) if STATE.exists() else {'pages':{}}
    cards=[];index=[]
    for p in pages:
        summary=p.get('summary');description=summary['conclusion'] if summary else (excerpt((ROOT/p['editionFile']).read_text()) if p['bodyStatus']!='Blank source' else 'The saved WikiTree source is blank; related complete studies are linked on its reading page.')
        description=sentence_excerpt(description)
        search=' '.join((p['title'],p['category'],p['wikitreeId'],p.get('location',''),p.get('startDate',''),p.get('endDate',''),' '.join(p.get('tags',[])),description)).casefold()
        dates='–'.join(dict.fromkeys(str(p.get(k,'')) for k in ('startDate','endDate') if p.get(k)))
        facts=''.join(f'<span>{escape(value)}</span>' for value in (dates,p.get('location',''),p['bodyStatus'] if p['bodyStatus']=='Blank source' else '') if value)
        cards.append(f'<article class="fsp-card" data-category="{escape(p["category"],quote=True)}" data-search="{escape(search,quote=True)}" data-importance="{p["importance"]}"><div class="fsp-card-title"><span class="r-kicker">{escape(p["category"])}</span><h3><a href="{p["url"]}">{escape(p["title"].replace(chr(39)*2,""))}</a></h3><div class="fsp-facts">{facts}</div></div><div class="fsp-card-description"><p>{escape(description)}</p><a class="fsp-read-link" href="{p["url"]}">Read the study <span aria-hidden="true">→</span></a></div></article>')
        sync=state.get('pages',{}).get(p['wikitreeId'],{})
        source_text=(ROOT/p['editionFile']).read_text();renderer=Renderer(pages);body=renderer.render(source_text)
        for vi,variant in enumerate(p.get('variantFiles',[]),1):
            variant_text,variant_removed=public_text((ROOT/variant).read_text(),from_sources(),p['wikitreeId'])
            vr=Renderer(pages);variant_html=BeautifulSoup(vr.render(variant_text),'html.parser')
            for element in variant_html.select('[id]'):element['id']='variant-'+str(vi)+'-'+element['id']
            for a in variant_html.select('a[href^="#"]'):a['href']='#variant-'+str(vi)+'-'+a['href'][1:]
            body+='<details class="fsp-saved-variant"><summary>Earlier saved variant of this study</summary><p>This is an additional saved text for the same WikiTree page. It remains available for comparison; the maintained reading above and outgoing draft use the principal account.</p>'+str(variant_html)+'</details>'
        notice=f'<aside class="fsp-notice">{PUBLIC_NOTICE}</aside>' if p['omittedPassages'] else ''
        if not source_text.strip():
            related=[q for q in pages if q['category']==p['category'] and q['bodyStatus']!='Blank source'][:5]
            body='<p>The saved source of this WikiTree page is blank. No missing narrative has been invented.</p><h2>Related complete studies</h2><ul>'+''.join(f'<li><a href="{q["url"]}">{escape(q["title"])}</a></li>' for q in related)+'</ul>'
        contents=''.join(f'<li><a href="#{anchor}">{escape(label)}</a></li>' for anchor,label in renderer.headings)
        if renderer.refs:contents+='<li><a href="#source-references">Source references</a></li>'
        position=''
        if summary:
            position=f'<aside class="fsp-position"><span class="r-kicker">Current research</span><p><strong>{escape(summary["confidence"])}</strong></p><p>{escape(summary["conclusion"])}</p><p><strong>Next question:</strong> {escape(summary["nextAction"])}</p><a href="{escape(summary["publicSupport"]["url"],quote=True)}">{escape(summary["publicSupport"]["label"])} →</a></aside>'
        status=sync.get('status','Not checked against current WikiTree text')
        remote=sync.get('remotePublicText');diff_html=''
        if remote is not None:
            import difflib
            difference='\n'.join(difflib.unified_diff(remote.splitlines(),source_text.splitlines(),fromfile='Current WikiTree',tofile='Local edition',lineterm=''))
            diff_html='<details><summary>Last retrieved WikiTree text and proposed changes</summary><label>Last retrieved WikiTree text<textarea readonly>'+escape(remote)+'</textarea></label><pre>'+escape(difference or 'The public reading texts match.')+'</pre></details>'
        sync_panel=f'<section class="fsp-sync" id="wikitree-comparison"><h2>WikiTree and this edition</h2><p><strong>{escape(status)}</strong></p><p>Saved source: {escape(p["capturedAt"][:10])}. '+(f'Last checked: {escape(sync["checkedAt"])}. ' if sync.get('checkedAt') else '')+'Local corrections are preserved; differences are reviewed before either edition is replaced.</p><p><a href="'+escape(p['viewUrl'],quote=True)+'" rel="noopener">Open the WikiTree page ↗</a> · <a href="/free-space/#edition-updates">How updates are reconciled</a></p>'+diff_html+'<details><summary>Complete local WikiTree draft</summary><p>This is the public-safe local text, ready for review. A live WikiTree save is a separate action.</p><label>Local replacement text<textarea readonly>'+escape(source_text)+'</textarea></label></details></section>'
        main=f'<main class="r-main fsp-main" id="main"><header class="r-page-head"><span class="r-kicker">{escape(p["category"])}</span><h1>{escape(p["title"].replace(chr(39)*2,""))}</h1><p>A maintained local edition of the research, with the original sources and assessments.</p><nav class="r-actions"><a href="/free-space/">← Research library</a><a href="{escape(p["viewUrl"],quote=True)}" rel="noopener">WikiTree edition ↗</a><a href="#wikitree-comparison">Compare editions</a></nav></header>{position}{notice}<div class="fsp-reading-layout"><aside class="fsp-contents"><details open><summary>On this page</summary><ol>{contents}</ol></details></aside><article class="fsp-reading">{body}{sync_panel}</article></div></main>'
        meta_description = p['title'].replace(chr(39)*2, '') + ': ' + description
        target=web/p['url'].strip('/')/'index.html';target.parent.mkdir(parents=True,exist_ok=True);target.write_text(shell_page(shell,main,p['title'],p['url']+'index.html',meta_description))
        index.append({k:p.get(k,'') for k in ('wikitreeId','title','viewUrl','category','editDate','verifiedDate','startDate','endDate','location','tags','url','importance','bodyStatus')}|{'availability':'Local reading edition','summaryUrl':p['url'],'syncStatus':status})
    main=directory_main(pages,cards)
    target=web/'free-space/index.html';target.parent.mkdir(parents=True,exist_ok=True);target.write_text(shell_page(shell,main,'Free-space research library','/free-space/index.html','Browse Glasgow surname studies by topic: medieval names, Scottish records, Irish families, open questions and Y-DNA, with full local research and source references.'))
    (web/'assets/research/free-space-index.json').write_text(json.dumps(index,ensure_ascii=False,separators=(',',':')))
    for suffix in ('css','js'):
        dest=web/'assets/free-space'/('site.'+suffix);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text((ROOT/'tools'/('free_space_edition.'+suffix)).read_text())
    return {'captures':len(source['pages']),'pages':len(pages),'reading_bodies':sum(p['bodyStatus']!='Blank source' for p in pages),'blank_sources':sum(p['bodyStatus']=='Blank source' for p in pages),'privacy_omissions':sum(p['omittedPassages'] for p in pages)}
