#!/usr/bin/env python3
"""Build source-type, jurisdiction and year collections from public evidence."""
from __future__ import annotations
from collections import Counter
from hashlib import sha256
from html import escape as e
import csv
import json
from pathlib import Path
import re
import shutil
from urllib.parse import urlparse, unquote

try:
    from tools.source_collection_index import build_index
except ModuleNotFoundError:
    from source_collection_index import build_index

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / 'www'
INPUT = ROOT / 'research/source-library'
TYPES = {
    'newspapers': ('Newspapers', 'Reported events, notices, advertisements and letters. OCR matches need visual checking; Glasgow the city and named vessels are excluded from surname evidence.'),
    'census': ('Census', 'Households and population returns, arranged by census year and jurisdiction. Coverage and the meaning of a household relationship vary by census.'),
    'births': ('Births & baptisms', 'Civil births and parish baptisms. Baptism and registration dates must be distinguished from the date of birth.'),
    'marriages': ('Marriages & banns', 'Civil marriages, church marriages and proclamations of banns. Banns alone do not prove that a wedding took place.'),
    'deaths': ('Deaths & burials', 'Civil deaths, burial registers, monumental inscriptions and notices. Reported ages and inferred birth years may be inaccurate.'),
    'wills-probate': ('Wills & probate', 'Wills, testaments, inventories and grants. Probate dates differ from death dates; calendars may survive when original wills do not.'),
    'land-tax': ('Land, tax & valuation', 'Tenure, ownership, occupiers, leases, taxation and valuations. An occupier list is not a complete household census.'),
    'church': ('Church & parish records', 'Parish registers and other church evidence. Denomination, parish coverage, gaps and the purpose of each entry matter.'),
    'military': ('Military & service', 'Service, pensions, rolls and military accounts. Identify the regiment, period and record series before linking a namesake.'),
    'directories': ('Directories', 'Published addresses and occupations. Edition dates can lag collection; entries need not include every resident.'),
    'education': ('Schools & universities', 'Admissions, school notices and educational records. Institutional coverage is selective and names may be abbreviated.'),
    'histories': ('Histories & biographies', 'Published histories and later accounts. Follow their citations to contemporary evidence and assess their authorship.'),
    'pedigrees': ('Profiles & family accounts', 'WikiTree profiles, family trees and later genealogies. These are secondary accounts; attached family relationships remain claims to assess.'),
    'other': ('Other references', 'References whose record type is unresolved, or which span several kinds of evidence. Inspect the source page before classifying further.'),
}
COUNTRIES = ['Ireland', 'Scotland', 'England', 'United States', 'Canada', 'Australia', 'New Zealand', 'Netherlands']
PERIODS = {'before-1800': ('Before 1800', 0, 1799), '1800-1849': ('1800–1849', 1800, 1849), '1850-1899': ('1850–1899', 1850, 1899), '1900-1949': ('1900–1949', 1900, 1949), '1950-onwards': ('1950 onwards', 1950, 9999), 'undated': ('Year unresolved', None, None)}


def slug(value):
    return re.sub(r'[^a-z0-9]+', '-', value.lower()).strip('-')


def ready(web):
    return (INPUT / 'coverage.json').exists() and all((web / relative).exists() for relative in (
        'assets/v3/source-index.json', 'data/glasgow-newspaper-review.json',
        'branches/scottish-families/index.html', 'branches/early-ireland/index.html'))


def write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists() or path.read_text(encoding='utf-8') != content:
        path.write_text(content, encoding='utf-8')
        return 1
    return 0


def links(items):
    return '<ul>' + ''.join(f'<li><a href="{e(x["url"], quote=True)}">{e(x["title"])}</a></li>' for x in items) + '</ul>'


def display_title(row):
    title = re.sub(r'\s*[\[(]https?://[^\s\])]+[\])]', '', row['title'])
    title = re.sub(r'https?://\S+', '', title).strip(' .:;')
    if title: return title
    parts = [unquote(p).replace('_', ' ') for p in urlparse(row.get('original_url') or row['title']).path.split('/') if p and p != 'pages']
    return ' / '.join(parts) or 'Source reference ' + row['id']


def card(row):
    year = ', '.join(map(str, row.get('years') or [])) or 'Year unresolved'
    detail = f'/sources/{row["id"]}/'
    original = row.get('original_url')
    label = 'Profile / family account' if row['original_kind'] == 'profile' else 'Original / provider link'
    origin = f'<a href="{e(original, quote=True)}">{label} ↗</a>' if original else '<span>Original link not recorded; see the citation</span>'
    places = ' · '.join(row['places'][:2])
    people = census_people_links(row, detail) if 'census' in row['categories'] else ''
    return f'<article class="sc-reference"><div class="sc-year">{e(year)}<small>{e(row["year_basis"])}</small></div><div><h3><a href="{detail}">{e(display_title(row))}</a></h3><p>{len(row["members"])} linked people · {row["citations"]} citations</p>{people}{("<p>Linked record places: " + e(places) + "</p>") if places else ""}<div class="sc-record-links"><a href="{detail}">Evidence & people</a>{origin}</div></div></article>'


def census_people_links(row, fallback):
    return '<p class="sc-census-people">People linked to this reference: ' + ' · '.join(
        f'<a href="{e(person.get("url") or fallback, quote=True)}">{e(person["name"])}</a>'
        for person in row.get('people', [])) + '</p>' if row.get('people') else ''


def census_summary(rows):
    people = {p['id']: p for row in rows for p in row.get('people', [])}
    dated = sum(bool(row.get('years')) for row in rows)
    return f'<section class="sc-census-summary"><h2>People in the collected census references</h2><p><strong>{len(rows):,} reference items · {len(people):,} linked catalogue people</strong>. Several citations may describe the same household; one return can name several people. Linked people include spouses and relatives and are not a verified count of Glasgow surname entries. This is our collected evidence, not a complete surname search of the surviving census.</p><p>{dated:,} references have a supported census year; {len(rows)-dated:,} remain unresolved. Years come from the enumeration title or original census URL; access dates, birth years and archive numbers are excluded. Countries identify the census jurisdiction where stated, rather than a person’s birthplace.</p></section>'


def browser(rows, category, country='', year='', period=''):
    rows = sorted(rows, key=lambda r: (r['year'] or 9999, r['title'].casefold(), r['id']))
    opts = ''.join(f'<option>{e(v)}</option>' for v in COUNTRIES)
    years = sorted({y for r in rows for y in r.get('years', [])})
    yearopts = '<option value="undated">Year unresolved</option>' + ''.join(f'<option value="{y}">{y}</option>' for y in years)
    initial = ''.join(card(r) for r in rows[:24])
    rest = '<details class="sc-static-index"><summary>Complete collection index — all reference links</summary><ul>' + ''.join(f'<li><a href="/sources/{e(r["id"])}/">{e(display_title(r))}</a></li>' for r in rows) + '</ul></details>'
    return f'''<section class="sc-browser" data-category="{category}" data-country="{e(country, quote=True)}" data-year="{year}" data-period="{period}"><h2>Collected references <span class="sc-count-badge">{len(rows):,}</span></h2><p>Reference items in this project, not the total surviving archive. A reference can appear in several types or locations; several references can concern the same record. Countries are inferred from source descriptions and recorded places, so check the citation. Undated and ambiguous items remain available.</p><form class="sc-filters"><label>Search within this collection<input type="search" name="q" placeholder="Name, parish, townland, archive reference…"></label><label>Country / jurisdiction<select name="country"><option value="">All / unresolved</option>{opts}</select></label><label>Record year<select name="year"><option value="">All / unresolved</option>{yearopts}</select></label><label>Source link<select name="availability"><option value="">All references</option><option value="original">Original / provider link recorded</option><option value="none">Original link missing</option></select></label><button type="reset">Clear filters</button></form><p class="sc-result-count" role="status">{len(rows):,} reference items · earliest first</p><div class="sc-results">{initial or '<p>No reference item assigned to this collection yet. This does not mean the archive has no relevant records.</p>'}</div><nav class="sc-pager" aria-label="Reference pages"></nav>{rest}<noscript><p>Open the complete collection index above to see every reference without JavaScript.</p></noscript></section>'''


def guide(config, category, country='', year=None):
    keys = []
    if category == 'census' and country == 'Ireland':
        if year in (1821, 1831, 1841, 1851) or year is None: keys.append('census/ireland/1821-1851')
        if year in (1861, 1871, 1881, 1891) or year is None: keys.append('census/ireland/1861-1891')
        if year in (1901, 1911) or year is None: keys.append('census/ireland/1901-1911')
        if year == 1926 or year is None: keys.append('census/ireland/1926')
    if category == 'census' and country == 'Scotland': keys.append('census/scotland/1841-1921')
    if category == 'census' and country == 'England': keys.append('census/england-wales/1841-1921')
    if category == 'census' and country == 'United States' and (year == 1890 or year is None): keys.append('census/united-states/1890')
    if category in ('births', 'marriages', 'deaths', 'church'):
        if country == 'Scotland': keys.extend(['church/scotland/opr', 'civil/scotland/statutory'])
        if country == 'Ireland': keys.append('civil/ireland/bmd')
        if country == 'England': keys.append('civil/england-wales/bmd')
    if category == 'wills-probate' and country == 'Ireland': keys.append('probate/ireland/1858-1922')
    if category == 'land-tax' and country == 'Ireland': keys.extend(['land/ireland/tithe-1823-1837', 'land/ireland/griffiths-1847-1864'])
    sections = []
    if category == 'census' and country == 'Ireland' and year == 1851:
        sections.append('<p class="sc-callout"><strong>1851 survives in fragments.</strong> Antrim, one Belfast ward and parts of Fermanagh retain material; Dublin city has a heads-of-household index. These are not complete county or national returns. Some returns record people absent and deaths since 1841, making the original page particularly useful for family research.</p>')
    for key in keys:
        g = config['collections'][key]
        sections.append(f'<section class="sc-guide"><h3>{e(g["title"])}</h3>' + ''.join(f'<p>{e(p)}</p>' for p in g['paragraphs']) + links(g['links']) + '</section>')
    if not sections:
        sections.append('<p>Availability depends on the particular repository, locality, date range and record series. We have not established complete coverage for this collection. Follow each provider link for its holdings and access terms; a missing result is not proof of absence.</p>')
    return '<section class="sc-coverage"><h2>Coverage, survival & limitations</h2>' + ''.join(sections) + '<p><strong>Reading the evidence:</strong> an index, transcript, provider search page and original image are different sources. A recorded image link does not mean its reading or identity match is confirmed. Inspect the assessment and source page before changing a family relationship. Repository guides checked 4 October 2026.</p></section>'


def profile_links(row, web):
    out = []
    for ident in row.get('profile_ids', []):
        local = f'/people/{ident.lower()}.html'
        href = local if (web / local.lstrip('/')).exists() else 'https://www.wikitree.com/wiki/' + ident
        out.append(f'<a href="{e(href, quote=True)}">{e(ident)}</a>')
    if row.get('draft_url'): out.append(f'<a href="{e(row["draft_url"], quote=True)}">Research draft</a>')
    return ' · '.join(out) or 'No profile assigned; identity remains separate.'


def newspaper_card(row, clips, web):
    ident = str(row['image_id'])
    clip = clips.get(ident)
    media = ''
    if clip:
        note = e(clip.get('caption_note','Saved excerpt.'))
        media = f'<figure><a href="{clip["url"]}"><img src="{clip["url"]}" width="{clip["width"]}" height="{clip["height"]}" loading="lazy" alt="Newspaper excerpt for {e(row["date"], quote=True)}; reading and assessment follow"></a><figcaption>{note} Source reference: {e(row["paper"])} · {e(row["date"])} · p. {e(str(row.get("page", "?")))}. Open for full size; inspect the <a href="{e(row["source_url"], quote=True)}">original page</a> for context.</figcaption></figure>'
    country = newspaper_country(row['paper'])
    return f'<article class="sc-newspaper" id="newspaper-{ident}" data-year="{row["date"][:4]}" data-paper="{e(row["paper"], quote=True)}" data-country="{country}" data-clip="{int(bool(clip))}"><header><span class="sc-status">{e(row["status"])}</span><h3>{e(row["date"])} · {e(row["paper"])} · p. {e(str(row.get("page", "?")))}</h3><a href="{e(row["source_url"], quote=True)}">Original newspaper page ↗</a></header>{media}<div class="sc-newspaper-reading"><p><strong>Reading:</strong> {e(row.get("reading", ""))}</p><p><strong>Assessment:</strong> {e(row.get("assessment", ""))}</p><p>{profile_links(row, web)}</p>{"<p class=\"sc-muted\">Inline excerpt not saved; follow the original page link.</p>" if not clip else ""}</div></article>'


def newspaper_country(paper):
    # Publication location, never the subject's place of residence.
    if re.search(r'belfast|irishman|dublin|sligo|derry|impartial reporter|freeman|northern star|drogheda|leinster', paper, re.I): return 'Ireland'
    if re.search(r'caledonian|edinburgh|scotland|scots|fife|aberdeen', paper, re.I): return 'Scotland'
    if re.search(r'ohio|pitts|pennsyl|virginia|new york|american|washington|maryland', paper, re.I): return 'United States'
    if re.search(r'london|england|newcastle|ipswich|derby|morning chronicle|morning post|^the times$', paper, re.I): return 'England'
    if re.search(r'haarlem|leydse|gravenhaeg', paper, re.I): return 'Netherlands'
    return 'Unresolved'


def newspaper_body(data, clips, web, country='', year=None):
    rows = sorted(data['rows'], key=lambda r: (r['date'], str(r['image_id'])))
    if country: rows = [r for r in rows if newspaper_country(r['paper']) == country]
    if year: rows = [r for r in rows if r['date'].startswith(str(year))]
    retained = [r for r in rows if r['status'] in ('confirmed surname', 'place study')]
    controls = '<form class="sc-newspaper-filters sc-filters"><label>Find a name or place<input type="search" name="q" placeholder="Lisnagaver, Rasharkin, William…"></label><label>Year<select name="year"><option value="">All years</option>' + ''.join(f'<option>{v}</option>' for v in sorted({r['date'][:4] for r in retained})) + '</select></label><label>Newspaper<select name="paper"><option value="">All papers</option>' + ''.join(f'<option>{e(v)}</option>' for v in sorted({r['paper'] for r in retained})) + '</select></label><label>Clippings<select name="clip"><option value="">All records</option><option value="1">Saved clippings</option></select></label><button type="reset">Clear filters</button></form>'
    body = f'<section id="newspaper-records"><h2>Reviewed newspaper records</h2><p>{len(retained)} retained pages in this collection; {sum(str(r["image_id"]) in clips for r in retained)} have saved inline excerpts. Ordered earliest first. A passage may identify more than one person. “Place study” records remain separate from surname evidence.</p>{controls}<p id="sc-newspaper-count" role="status">{len(retained)} retained pages</p><div class="sc-newspaper-list">' + ''.join(newspaper_card(r, clips, web) for r in retained) + '</div></section>'
    for status, title in [('reading pending', 'Unresolved search hits'), ('place or ship', 'Excluded city and vessel matches')]:
        group = [r for r in rows if r['status'] == status]
        body += f'<details class="sc-review-log"><summary>{title} — {len(group)} pages</summary><p>These are search leads or exclusions, not confirmed surname records.</p>' + ''.join(newspaper_card(r, {}, web) for r in group) + '</details>'
    return body


def load_clips(web):
    manifest_path = INPUT / 'newspaper-clippings.json'
    if not manifest_path.exists(): return {}
    manifest = json.loads(manifest_path.read_text())
    result = {}
    retained = {str(r['image_id']) for r in json.loads((ROOT / 'surname-research/indexes/glasgow-newspaper-review.json').read_text())['rows'] if r['status'] in ('confirmed surname', 'place study')}
    for item in manifest['assets']:
        if str(item['image_id']) not in retained: raise ValueError('Clip is not an inspected retained record')
        source = ROOT / item['source_path']
        target = web / item['public_path']
        if source.exists():
            if sha256(source.read_bytes()).hexdigest() != item['sha256']: raise ValueError('Approved clip changed')
            target.parent.mkdir(parents=True, exist_ok=True)
            if not target.exists(): shutil.copyfile(source, target)
        if not target.exists() or sha256(target.read_bytes()).hexdigest() != item['sha256']: raise ValueError('Public clip does not match approval')
        result[str(item['image_id'])] = {'url': '/' + item['public_path'], 'width': item['width'], 'height': item['height'], 'caption_note':item.get('caption_note','Saved excerpt.')}
    return result


def supplied_clippings(web):
    path = INPUT / 'supplied-newspaper-clippings.json'
    if not path.exists(): return ''
    data = json.loads(path.read_text())
    body = '<p>Sixteen usable, distinct excerpts supplied with this research are preserved here. Three nearly blank screenshots and one repeated coffee-advert crop add no evidence. Some crops lack an issue heading; a matching notice does not prove which edition a crop came from. Three clippings still need an exact original image link. Search links are labelled accordingly. No additional profile identity or relationship is inferred here.</p>'
    for item in sorted(data['assets'], key=lambda x:x['date']):
        source = ROOT / item['source_path'];target = web / item['public_path']
        if sha256(source.read_bytes()).hexdigest() != item['sha256']: raise ValueError('Supplied clip changed')
        target.parent.mkdir(parents=True,exist_ok=True)
        if not target.exists(): shutil.copyfile(source,target)
        if sha256(target.read_bytes()).hexdigest() != item['sha256']: raise ValueError('Public supplied clip changed')
        ident = item.get('image_id')
        original = 'Original newspaper page ↗' if ident else 'Find original issue — search link; exact image ID pending'
        matched = f'<p><a href="/sources/newspapers/#newspaper-{ident}">Reviewed notice and profile assessment →</a></p>' if ident else '<p>Original full-page and identity review remain pending. Treat this as a supplied excerpt, not a new checked profile match.</p>'
        body += f'<article class="sc-newspaper"><header><span class="sc-status">{e(item["status"])}</span><h2>{e(item["date"])} · {e(item["paper"])} · p. {e(str(item["page"]))}</h2><a href="{e(item["source_url"],quote=True)}">{original}</a></header><figure><a href="/{item["public_path"]}"><img loading="lazy" src="/{item["public_path"]}" width="{item["width"]}" height="{item["height"]}" alt="Supplied historical clipping; description follows"></a><figcaption>{e(item["caption_note"])}</figcaption></figure><div class="sc-newspaper-reading"><p>{e(item["description"])}</p>{matched}</div></article>'
    return body


def collection_sections(web):
    """Reuse maintained reviewed tables; retain a durable source for the migrated audit."""
    try:
        from tools.publish_opr_birth_review import render as births
        from tools.publish_opr_marriage_review import render as marriages
        from tools.publish_opr_death_review import render_section as deaths
        from tools.publish_irish_death_index import render as irish_deaths
    except ModuleNotFoundError:
        from publish_opr_birth_review import render as births
        from publish_opr_marriage_review import render as marriages
        from publish_opr_death_review import render_section as deaths
        from publish_irish_death_index import render as irish_deaths
    out = {}
    for kind, func in [('births', births), ('marriages', marriages), ('deaths', deaths)]:
        source = ROOT / f'surname-research/indexes/scotlandspeople-opr-{kind}-to-1700.json'
        out[f'{kind}/scotland/opr-to-1700'] = func(json.loads(source.read_text()))
    path = ROOT / 'surname-research/indexes/irish-civil-deaths-1864-1900.csv'
    with path.open(newline='') as f: rows = list(csv.DictReader(f))
    target = web / 'data/irish-civil-deaths-1864-1900.csv'
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists() or target.read_bytes() != path.read_bytes(): shutil.copyfile(path, target)
    out['deaths/ireland/civil-1864-1900'] = irish_deaths(rows, json.loads(path.with_suffix('.json').read_text()))
    branch = web / 'branches/early-ireland/index.html'
    snapshot = INPUT / 'legacy-collections/groni-death-matches.html'
    pattern = r'<!-- BEGIN GRONI-DEATH-MATCH -->.*?<!-- END GRONI-DEATH-MATCH -->'
    match = re.search(pattern, branch.read_text(), re.S)
    if match and '<table' in match[0]: write(snapshot, match[0] + '\n')
    if snapshot.exists():
        section = snapshot.read_text()
        # Earlier public summaries linked exports which are no longer published.
        # Preserve the inspected table without exposing an unreviewed crosswalk.
        def download_link(match):
            href, label = match.groups()
            return match[0] if (web / href.lstrip('/')).exists() else label + ' (public download unavailable)'
        section = re.sub(r'<a href="(/data/[^"]+)"[^>]*>(.*?)</a>', download_link, section, flags=re.S)
        out['deaths/ireland/groni-matches'] = section
    return out


def move_branch_tables(web, data, sections):
    branch = web / 'branches/scottish-families/index.html'
    text = branch.read_text()
    for kind in ('births', 'marriages', 'deaths'):
        name = f'opr-{kind}-to-1700'
        pattern = rf'<!-- {name}:start -->.*?<!-- {name}:end -->'
        target = f'/sources/{kind}/scotland/opr-to-1700/'
        ids = re.findall(r'\bid="([^"]+)"', sections[f'{kind}/scotland/opr-to-1700'])
        aliases = ''.join(f'<span id="{e(ident, quote=True)}" data-source-target="{target}#{e(ident, quote=True)}"></span>' for ident in ids if ident != name)
        metadata = json.loads((ROOT / f'surname-research/indexes/scotlandspeople-opr-{kind}-to-1700.json').read_text())
        conclusion = '<p>' + e(metadata.get('conclusion','')) + '</p>'
        replacement = f'<!-- {name}:start --><section id="{name}"><h2>Scottish parish {kind} through 1700</h2>{conclusion}<p>The reviewed index, profile assessments, source links and record limitations are now in <a href="{target}">Sources: {TYPES[kind][0]}</a>. These index entries remain subject to original-register and identity checks.</p>{aliases}</section><!-- {name}:end -->'
        text = re.sub(pattern, lambda _: replacement, text, flags=re.S)
    counts = Counter(r['status'] for r in data['rows'])
    aliases = ''.join(f'<span id="newspaper-{e(str(r["image_id"]))}" data-source-target="/sources/newspapers/#newspaper-{e(str(r["image_id"]))}"></span>' for r in data['rows'])
    replacement = f'<!-- early-newspapers:start --><section id="early-newspapers"><h2>Glasgow newspaper records for our studies</h2><p>{counts["confirmed surname"]} verified surname pages and {counts["place study"]} separately labelled place-study pages are organised in <a href="/sources/newspapers/">Sources: Newspapers</a>, with saved clippings, original-page links and profile assessments.</p><p>{e(data["conclusion"])}</p>{aliases}</section><!-- early-newspapers:end -->'
    text = re.sub(r'<!-- early-newspapers:start -->.*?<!-- early-newspapers:end -->', lambda _: replacement, text, flags=re.S)
    redirect = '<script id="source-collection-aliases">(()=>{const follow=()=>{const node=document.getElementById(location.hash.slice(1));if(node?.dataset.sourceTarget&&location.protocol!=="file:")location.replace(node.dataset.sourceTarget)};addEventListener("hashchange",follow);follow()})();</script>'
    if 'id="source-collection-aliases"' not in text: text = text.replace('</body>', redirect + '</body>', 1)
    write(branch, text)
    branch = web / 'branches/early-ireland/index.html'
    text = branch.read_text()
    for name, title, target, start, end in [('groni-death-matches', 'Northern Ireland Glasgow death entries', '/sources/deaths/ireland/groni-matches/', 'BEGIN GRONI-DEATH-MATCH', 'END GRONI-DEATH-MATCH'), ('irish-civil-death-index', 'Irish civil deaths, 1864–1900', '/sources/deaths/ireland/civil-1864-1900/', 'BEGIN IRISH-CIVIL-DEATH-INDEX', 'END IRISH-CIVIL-DEATH-INDEX')]:
        conclusions = ''
        if name == 'groni-death-matches':
            # Keep the family's substantive connections and competing identities
            # visible here; only the source tables and lookup tools move.
            section = sections.get('deaths/ireland/groni-matches','').split('<h3>')[0]
            conclusions = ''.join(p for p in re.findall(r'<p\b[^>]*>.*?</p>', section, re.S) if 'download' not in p.lower())
        replacement = f'<!-- {start} --><section id="{name}"><h2>{title}</h2>{conclusions}<p>The collected entries, match review, outstanding questions and original-provider links are in <a href="{target}">Sources: {title}</a>. Index references and proposed identities are separately qualified there.</p></section><!-- {end} -->'
        text = re.sub(re.escape('<!-- ' + start + ' -->') + r'.*?' + re.escape('<!-- ' + end + ' -->'), lambda _: replacement, text, flags=re.S)
    write(branch, text)


def repair(web=None):
    web = web or WEB
    config = json.loads((INPUT / 'coverage.json').read_text())
    rows = build_index(web)
    for row in rows:
        row['display_title'] = display_title(row)
        for person in row.get('people', []):
            local = '/people/' + person['id'].lower() + '.html'
            person['url'] = local if (web / local.lstrip('/')).exists() else '/sources/' + row['id'] + '/'
    counts = Counter(c for r in rows for c in r['categories'])
    clips = load_clips(web)
    supplied = supplied_clippings(web)
    newspaper = json.loads((web / 'data/glasgow-newspaper-review.json').read_text())
    review_counts = Counter(r['status'] for r in newspaper['rows'])
    sections = collection_sections(web)
    template = (web / 'sources/index.html').read_text()
    old_manifest = web / 'assets/sources/collection-pages.json'
    old_pages = json.loads(old_manifest.read_text()).get('pages', []) if old_manifest.exists() else []
    stats = Counter()
    index_path = web / 'assets/sources/collection-index.json'
    stats['index'] += write(index_path, json.dumps(rows, ensure_ascii=False, separators=(',', ':')) + '\n')
    css = Path(__file__).with_name('source_collections.css').read_text() + '\n'
    js = Path(__file__).with_name('source_collections.js').read_text() + '\n'
    stats['assets'] += write(web / 'assets/sources/collections.css', css)
    stats['assets'] += write(web / 'assets/sources/collections.js', js)
    cv, jv = sha256(css.encode()).hexdigest()[:10], sha256(js.encode()).hexdigest()[:10]
    written = []
    def page(route, title, body):
        path = '/sources/' + (route.strip('/') + '/' if route else '')
        crumbs = '<div class="g-crumbs"><a href="/">Glasgow archive</a><i>/</i>' + ('<a href="/sources/">Sources</a><i>/</i>' if route else '') + f'<strong>{e(title)}</strong></div>'
        out = re.sub(r'<main\b[\s\S]*?</main>', lambda _: '<main class="r-main sc-main" id="main">' + body + '</main>', template, count=1, flags=re.I)
        out = re.sub(r'<title>.*?</title>', lambda _: f'<title>{e(title)} · Glasgow Sources</title>', out, count=1, flags=re.S)
        out = re.sub(r'<meta\b[^>]*name="description"[^>]*>', '', out)
        out = re.sub(r'<div class="g-crumbs">.*?</div>', lambda _: crumbs, out, count=1, flags=re.S)
        nav = '<div aria-label="Source collections" class="g-section-subnav sc-nav" role="group">' + ''.join(f'<a href="/sources/{key}/"' + (' aria-current="location"' if route.split('/')[0] == key else '') + f'>{e(TYPES[key][0])}</a>' for key in ['newspapers','census','births','marriages','deaths','wills-probate','land-tax']) + '<a href="/sources/">All source types</a><a href="/records/">Records by person</a></div>'
        out = re.sub(r'<div\b[^>]*class="[^"]*g-section-subnav[^\"]*"[^>]*>.*?</div>', lambda _: nav, out, count=1, flags=re.S)
        out = re.sub(r'(<body\b[^>]*data-g-path=")[^"]*', lambda m: m[1] + path.rstrip('/'), out, count=1)
        out = re.sub(r'<link\b[^>]*href="/assets/(?:v3/source-library|sources/collections)\.css[^\"]*"[^>]*>', '', out)
        out = re.sub(r'<script\b[^>]*src="/assets/(?:v3/sources|sources/collections)\.js[^\"]*"[^>]*>\s*</script>', '', out)
        out = out.replace('</head>', f'<link rel="stylesheet" href="/assets/sources/collections.css?v={cv}"></head>', 1)
        out = out.replace('</body>', f'<script defer src="/assets/sources/collections.js?v={jv}"></script></body>', 1)
        stats['pages'] += write(web / path.lstrip('/') / 'index.html', out)
        written.append(path)
    def people_count(group):
        return len({ident for row in group for ident in row['members']})
    def hero(title, intro, count=None, people=None):
        total = f'{count:,} collected reference items' if count is not None else ''
        if people is not None: total += f' · {people:,} linked catalogue people'
        return '<header class="sc-hero"><p class="sc-eyebrow">The source library</p><h1>' + e(title) + '</h1><p>' + e(intro) + '</p>' + (f'<span class="sc-total">{total}</span>' if total else '') + '</header>'
    tiles = ''.join(f'<a class="sc-tile" href="/sources/{key}/"><span>{counts[key]:,} references</span><h2>{e(title)}</h2><p>{e(description)}</p></a>' for key,(title,description) in TYPES.items())
    featured = '<section><h2>Start with a reviewed collection</h2><div class="sc-featured">' + ''.join(f'<a href="{url}">{label}<span>{description}</span></a>' for url,label,description in [('/sources/newspapers/?clip=1#newspaper-records','Saved newspaper clippings',f'{len(clips)} saved excerpts linked to reviewed notices, with identity limits'),('/sources/census/ireland/1851/','1851 Irish Census','Surviving fragments, local references and the records lost in 1922'),('/sources/census/ireland/1831/','1831 Irish Census','Derry householders and religious counts; not a list of every person'),('/sources/deaths/ireland/civil-1864-1900/','Irish civil deaths, 1864–1900','241 index leads, qualified matches and original-record checks'),('/sources/births/scotland/opr-to-1700/','Scottish parish registers through 1700','Reviewed births, baptisms, parents and unresolved identities')]) + '</div></section>'
    intro = '<p class="sc-callout">This library brings together original-record references, indexes, transcripts and family accounts. Counts describe our collected references, not unique people or complete archival holdings. Country and year groups are navigation aids; uncertain or missing dates remain visible. Each item opens its evidence, linked profiles and the recorded provider link. A profile citation is labelled as a family account.</p>'
    page('', 'Sources', hero('Sources', 'Follow the record, its people and the original source.', len(rows)) + featured + '<section><h2>Browse by record type</h2><div class="sc-type-grid">' + tiles + '</div></section>' + intro + '<p><a href="/sources/browse/">Complete reference index</a> · <a href="/records/">Records by person</a> · <a href="/research/transcriptions/">Wills & transcriptions</a></p>')
    for category, (title, description) in TYPES.items():
        selected = [r for r in rows if category in r['categories']]
        countries = [c for c in COUNTRIES if any(c in r['countries'] for r in selected)]
        if category in ('census','newspapers'): countries = sorted(set(countries + ['Ireland','Scotland']))
        if category == 'newspapers': countries = sorted(set(countries + [newspaper_country(r['paper']) for r in newspaper['rows'] if r['status'] in ('confirmed surname','place study')]) - {'Unresolved'})
        def country_count(country):
            count = sum(country in r['countries'] for r in selected)
            if category == 'newspapers':
                reviewed = sum(newspaper_country(r['paper']) == country and r['status'] in ('confirmed surname','place study') for r in newspaper['rows'])
                return f'{reviewed} retained pages · {count} references'
            return f'{count:,} references'
        countrylinks = '<section><h2>By country & location</h2><div class="sc-location-links">' + ''.join(f'<a href="/sources/{category}/{slug(c)}/">{c} <span>{country_count(c)}</span></a>' for c in countries) + '</div><p>Use the collection search for a county, parish, townland or address. Newspaper country groups identify the place of publication; the subject may have lived elsewhere.</p></section>'
        body = hero(title, description, len(selected), people_count(selected) if category == 'census' else None) + countrylinks
        if category == 'census': body += census_summary(selected)
        if category == 'newspapers':
            body += '<p><a href="/sources/newspapers/supplied-clippings/">Browse all 16 distinct supplied clippings</a>, including three still awaiting exact original-page links.</p>'
            inspected = len(newspaper['rows']) - review_counts['reading pending']
            body += f'<section class="sc-coverage"><h2>Coverage & limits</h2><p>{len(newspaper["rows"])} pages catalogued · {inspected} original passages reviewed · {review_counts["confirmed surname"]} surname pages retained · {review_counts["place study"]} place-study page · {review_counts["place or ship"]} city/vessel pages excluded · {review_counts["reading pending"]} readings pending. Searches are selective and incomplete; these totals do not measure all newspaper holdings or all Glasgow mentions.</p><p>OCR hits and highlighted search words are leads. Saved excerpts may show only part of a notice; inspect the original page before treating a reading or namesake as proved. Missing issues, uneven digitisation, spelling variants and poor OCR can hide a relevant record. Free promotional access is temporary; original links may later require a subscription.</p><details><summary>Search coverage and detailed qualifications</summary><p>' + e(newspaper['scope']) + '</p><p>' + e(' '.join(newspaper['limitations'])) + '</p></details></section>' + newspaper_body(newspaper, clips, web)
        body += browser(selected, category)
        page(category, title, body)
        for country in countries:
            subset = [r for r in selected if country in r['countries']]
            route = category + '/' + slug(country)
            exact_years = sorted({y for r in subset for y in r.get('years', [])}) if category == 'census' else []
            if category == 'census' and country == 'Ireland': exact_years = sorted(set(exact_years + [1821,1831,1841,1851,1861,1871,1881,1891,1901,1911,1926]))
            if category == 'census' and country == 'United States': exact_years = sorted(set(exact_years + [1890]))
            if category == 'newspapers': exact_years = sorted({int(r['date'][:4]) for r in newspaper['rows'] if newspaper_country(r['paper']) == country and r['status'] in ('confirmed surname','place study')})
            if exact_years:
                subdivisions = '<h2>By record year</h2><div class="sc-location-links">' + ''.join(f'<a href="/sources/{route}/{y}/">{y}<span>{sum(y in r.get("years",[]) for r in subset)} references</span></a>' if category == 'census' else f'<a href="/sources/{route}/{y}/">{y}</a>' for y in exact_years) + (f'<a href="/sources/{route}/undated/">Year unresolved<span>{sum(not r.get("years") for r in subset)} references</span></a>' if category == 'census' and any(not r.get('years') for r in subset) else '') + '</div>'
            else:
                subdivisions = '<h2>By record period</h2><div class="sc-location-links">' + ''.join(f'<a href="/sources/{route}/{p}/">{label}</a>' for p,(label,lo,hi) in PERIODS.items() if any((r['year'] is None if lo is None else r['year'] is not None and lo <= r['year'] <= hi) for r in subset)) + '</div>'
            speciallinks = '<div class="sc-location-links">' + ''.join(f'<a href="/sources/{key}/">{e("Old Parish Registers through 1700" if "opr-to-1700" in key else "GRONI death match review" if "groni" in key else "Civil deaths 1864–1900")}</a>' for key in sections if key.startswith(route + '/')) + '</div>'
            body = hero(f'{country}: {title}', description, len(subset), people_count(subset) if category == 'census' else None) + subdivisions + speciallinks + guide(config, category, country)
            if category == 'census': body += census_summary(subset)
            if category == 'newspapers': body += newspaper_body(newspaper, clips, web, country)
            body += browser(subset, category, country)
            page(route, f'{country}: {title}', body)
            for year in exact_years:
                group = [r for r in subset if year in r.get('years', [])]
                adjective = {'Ireland':'Irish', 'Scotland':'Scottish', 'England':'England', 'United States':'United States'}.get(country, country)
                heading = f'{year} {adjective} Census' if category == 'census' else f'{country} newspapers, {year}'
                if category == 'census':
                    heading = {('Ireland',1740): '1740 Irish Protestant householders', ('Ireland',1766): '1766 Irish religious census', ('Canada',1793): '1793 Nova Scotia poll-tax returns', ('England',1939): '1939 England & Wales Register'}.get((country,year), heading)
                body = hero(heading, description, len(group), people_count(group) if category == 'census' else None) + f'<p><a href="/sources/{route}/">← All {country} {title.lower()}</a></p>' + guide(config, category, country, year)
                if category == 'census': body += census_summary(group)
                if category == 'newspapers': body += newspaper_body(newspaper, clips, web, country, year)
                body += browser(group, category, country, year=year)
                page(route + '/' + str(year), heading, body)
            if category == 'census' and exact_years and any(not r.get('years') for r in subset):
                group = [r for r in subset if not r.get('years')]
                title_undated = f'{country}: census year unresolved'
                page(route + '/undated', title_undated, hero(title_undated, 'Collected census references whose enumeration year is not established.', len(group)) + census_summary(group) + browser(group, category, country, year='undated'))
            if not exact_years:
                for period,(label,lo,hi) in PERIODS.items():
                    group = [r for r in subset if (r['year'] is None if lo is None else r['year'] is not None and lo <= r['year'] <= hi)]
                    if not group: continue
                    body = hero(f'{country}: {title}, {label}', description, len(group)) + f'<p><a href="/sources/{route}/">← All {country} {title.lower()}</a></p>' + guide(config, category, country) + browser(group, category, country, period=period)
                    page(route + '/' + period, f'{country}: {title}, {label}', body)
    for route, section in sections.items():
        category, country, _ = route.split('/')
        country = next(c for c in COUNTRIES if slug(c) == country)
        title = ('Scottish ' + TYPES[category][0].lower() + ' through 1700') if 'opr' in route else 'Irish civil deaths, 1864–1900' if 'civil' in route else 'Northern Ireland death match review'
        page(route, title, hero(title, 'The collected entries, their source references, profile assessments and outstanding checks.') + guide(config, category, country) + section)
    if supplied: page('newspapers/supplied-clippings', 'Supplied newspaper clippings', hero('Supplied newspaper clippings', 'The excerpts received during the newspaper study, with their provenance and remaining source checks.') + supplied)
    move_branch_tables(web, newspaper, sections)
    # Remove only obsolete pages previously owned by this builder.
    for obsolete in set(old_pages) - set(written):
        if re.fullmatch(r'/sources/[a-z-]+/[a-z-]+/[a-z0-9-]+/', obsolete):
            target = web / obsolete.lstrip('/') / 'index.html'
            if target.exists(): target.unlink(); stats['retired_pages'] += 1
    stats['manifest'] += write(web / 'assets/sources/collection-pages.json', json.dumps({'reference_items':len(rows), 'reference_counts':dict(counts), 'inline_newspaper_excerpts':len(clips), 'pages':written}, indent=2) + '\n')
    return dict(stats)

if __name__ == '__main__': print(repair())
