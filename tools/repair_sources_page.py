"""Render the source library while preserving published collection notices."""
from collections import Counter
from hashlib import sha256
from html import escape
import json
from pathlib import Path
import re

WEB = Path(__file__).resolve().parents[1] / 'www'
SOURCE_INDEX_FIELDS = ('id', 'title', 'members', 'records', 'citations', 'from', 'to',
                       'image', 'transcription', 'basis', 'date_basis')
COLLECTIONS = (
    ('opr-births-discovery', 'Births & baptisms', 'Scotland · through 1700', r'<p\b[^>]*\bid="opr-births-discovery"[^>]*>.*?</p>'),
    ('opr-marriages-discovery', 'Banns & marriages', 'Scotland · through 1700', r'<p\b[^>]*\bid="opr-marriages-discovery"[^>]*>.*?</p>'),
    ('opr-deaths-to-1700-discovery', 'Deaths & burials', 'Scotland · through 1700', r'<p\b[^>]*\bid="opr-deaths-to-1700-discovery"[^>]*>.*?</p>'),
    ('groni-death-matches', 'Northern Ireland death matches', 'Reviewed registration references', r'<!-- BEGIN GRONI-DEATH-MATCH-LINK -->.*?<!-- END GRONI-DEATH-MATCH-LINK -->'),
    ('irish-civil-death-index', 'Irish civil deaths', '1864–1900 · unverified index leads', r'<!-- BEGIN IRISH-CIVIL-DEATH-INDEX-LINK -->.*?<!-- END IRISH-CIVIL-DEATH-INDEX-LINK -->'),
)


def source_row(row: dict) -> str:
    date = str(row['from']) if row.get('from') is not None else 'Undated'
    if row.get('from') is not None and row.get('to') is not None and row['to'] != row['from']:
        date += '–' + str(row['to'])
    basis = row.get('basis') or 'Catalogue citation'
    basis_label = {'exact source URL': 'Linked source URL', 'citation text within this dossier': 'Dossier citation', 'explicit archive volume and image/page': 'Archive reference'}.get(basis, basis)
    people = len(row.get('members') or [])
    citations, records = row.get('citations') or 0, row.get('records') or 0
    availability = 'Image available' if row.get('image') else 'Transcription available' if row.get('transcription') else 'Citation & linked evidence'
    url = '/sources/' + escape(row['id'], quote=True) + '/'
    return f'''<article class="v3-source-row"><div class="v3-source-date">{escape(date)}<small>{'Reviewed event date' if row.get('date_basis') == 'reviewed event date' else 'Associated dates'}</small></div><div><span class="r-kicker" title="{escape(basis, quote=True)}">{escape(basis_label)}</span><h3><a href="{url}">{escape(row['title'])}</a></h3><p>{people:,} linked {'person' if people == 1 else 'people'} · {citations:,} {'citation' if citations == 1 else 'citations'} · {records:,} record {'association' if records == 1 else 'associations'}</p></div><span class="v3-source-availability">{availability}</span></article>'''


def source_body(rows: list[dict], original: str) -> str:
    notices = []
    for key, title, context, pattern in COLLECTIONS:
        matches = re.findall(pattern, original, re.S)
        if matches:
            notices.append(f'<details class="sources-collection"><summary><span>{escape(title)}</span><small>{escape(context)}</small></summary><div class="sources-collection-detail">{matches[-1]}</div></details>')
    shared = sum(len(row.get('members') or []) > 1 for row in rows)
    media = sum(bool(row.get('image') or row.get('transcription')) for row in rows)
    media_summary = f'<span><strong>{media:,}</strong> with an image or text</span>' if media else '<span>References and catalogue citations</span>'
    initial = sorted(rows, key=lambda row: (row.get('from') if row.get('from') is not None else 9999, row['title'].casefold()))[:24]
    summary = f'1–{len(initial)} of {len(rows):,} source items' if initial else 'No source items published.'
    return f'''<header class="sources-hero"><div><p class="sources-eyebrow">The documentary archive</p><h1>Source library</h1><p class="sources-intro">Search archive references and citations. Follow a source into the people and evidence it connects.</p></div><div class="sources-total"><strong>{len(rows):,}</strong><span>linked source items</span></div></header>
<div class="sources-coverage"><span><strong>{shared:,}</strong> linked to multiple people</span>{media_summary}<a href="#sources-collections">Reviewed collections ↓</a></div>
<form class="v3-source-search sources-search-panel" id="v3-source-search" action="/sources/browse/" method="get">
<div class="sources-search-fields"><label><span>Find a source</span><input id="v3-source-q" name="q" type="search" placeholder="Name, archive reference, place or record type…"></label><label><span>Availability</span><select id="v3-source-kind" name="kind"><option value="all">All source items</option><option value="shared">Linked to multiple people</option><option value="image">Image or text available</option></select></label><button class="r-button primary" type="submit">Search</button></div>
<div class="sources-search-footer"><span>Dates below refer to associated people and events unless marked as reviewed.</span><button id="source-reset" type="button">Clear filters</button></div></form>
<div class="sources-layout"><section class="sources-list" aria-label="Source results"><div class="sources-results-toolbar"><p id="v3-source-count" role="status">{summary}</p><a href="/sources/browse/">Complete index ↗</a></div>
<div class="repair-source-notice" id="repair-source-notice" role="status" hidden></div>
<noscript><p class="repair-static-note">The source listing and linked evidence work without JavaScript. <a href="/sources/browse/">Browse the complete index</a>; filtering requires JavaScript.</p></noscript>
<div id="v3-source-results" aria-label="Source items" data-summary="{summary}">{''.join(source_row(row) for row in initial)}</div>
<nav id="v3-source-pages" class="r-pagination" aria-label="Source pages"><a class="r-button" href="/sources/browse/">Browse the complete source index →</a></nav>
<div class="repair-source-links"><a href="/sources/browse/">Browse without JavaScript</a><a href="/records/">Search record associations →</a></div></section>
<aside class="sources-collections" id="sources-collections" aria-labelledby="sources-collections-heading"><p class="sources-eyebrow">Explore the research</p><h2 id="sources-collections-heading">Reviewed collections</h2><p class="sources-collections-intro">Focused reviews of parish and civil indexes. Each review explains its evidence and open questions.</p>{''.join(notices)}<div class="sources-method"><strong>What is a source item?</strong><p>A linked citation or archive reference in the catalogue. It may be a lead, an index entry or a published extract; an item is not necessarily a distinct original document.</p></div></aside></div>'''


def repair(web: Path | None = None) -> Counter:
    web = web or WEB
    path = web / 'sources/index.html'
    original = path.read_text(encoding='utf-8')
    rows = json.loads((web / 'assets/v3/source-index.json').read_text(encoding='utf-8'))
    main = f'<main class="r-main v3-sources" id="main">{source_body(rows, original)}</main>'
    page, count = re.subn(r'<main\b[\s\S]*?</main>', lambda _: main, original, count=1, flags=re.I)
    if count != 1:
        raise ValueError('Source-library main container missing')
    page = re.sub(r'<title>.*?</title>', '<title>Source library · Glasgow</title>', page, count=1, flags=re.S)
    page = re.sub(r'(<div class="g-crumbs">.*?<strong>).*?(</strong>)', r'\1Sources\2', page, count=1, flags=re.S)
    page = re.sub(r'(<body\b[^>]*data-g-path=")[^"]*', r'\1/sources', page, count=1)
    changed = Counter()
    # Search reads this compact mirror, not the initial HTML or full index.
    # Rebuild it from the public named records so stale/damaged cells cannot
    # survive a release that refreshes the visible listing.
    packed_path = web / 'assets/v3/source-index-packed.json'
    packed = json.dumps({'fields': SOURCE_INDEX_FIELDS,
                         'rows': [[row.get(field) for field in SOURCE_INDEX_FIELDS] for row in rows]},
                        ensure_ascii=False, separators=(',', ':')) + '\n'
    if not packed_path.exists() or packed_path.read_text(encoding='utf-8') != packed:
        packed_path.write_text(packed, encoding='utf-8')
        changed['source_search_index'] += 1
    worker_path = web / 'assets/research/search-worker.js'
    if worker_path.exists():
        worker = worker_path.read_text(encoding='utf-8')
        # Revalidate mutable indexes on a new worker/page load. The worker's
        # in-memory cache still avoids refetching during filtering/pagination.
        updated = worker.replace('fetch(path).then(', "fetch(path,{cache:'no-cache'}).then(")
        if updated != worker:
            worker_path.write_text(updated, encoding='utf-8')
            changed['source_search_cache'] += 1
    for source, target in (('source_library.css', 'assets/v3/source-library.css'), ('source_library.js', 'assets/v3/sources.js')):
        asset = web / target
        asset.parent.mkdir(parents=True, exist_ok=True)
        content = Path(__file__).with_name(source).read_text(encoding='utf-8') + '\n'
        if not asset.exists() or asset.read_text(encoding='utf-8') != content:
            asset.write_text(content, encoding='utf-8')
            changed['source_library_assets'] += 1
        version = sha256(content.encode()).hexdigest()[:10]
        tag = f'<link rel="stylesheet" href="/{target}?v={version}">' if source.endswith('.css') else f'<script defer src="/{target}?v={version}"></script>'
        pattern = r'<link\b[^>]*href="/assets/v3/source-library\.css(?:\?[^"]*)?"[^>]*>' if source.endswith('.css') else r'<script\b[^>]*src="/assets/v3/sources\.js(?:\?[^"]*)?"[^>]*>\s*</script>'
        page = re.sub(pattern, '', page, flags=re.I)
        closing = '</head>' if source.endswith('.css') else '</body>'
        page = page.replace(closing, tag + closing, 1)
    if page != original:
        path.write_text(page, encoding='utf-8')
        changed['source_library_page'] += 1
    return changed


if __name__ == '__main__':
    print(dict(repair()))
