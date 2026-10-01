#!/usr/bin/env python3
"""Keep reader introductions and plain navigation wording in local site builds."""
from collections import Counter
from hashlib import sha256
from pathlib import Path
import re
import runpy

try:
    from tools.repair_primary_navigation import NAV, is_excluded, render_primary_navigation, repair as repair_navigation
    from tools.catalogue_search_markup import compact_statistics, hero_html
except ModuleNotFoundError:
    from repair_primary_navigation import NAV, is_excluded, render_primary_navigation, repair as repair_navigation
    from catalogue_search_markup import compact_statistics, hero_html

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / 'www'
SOURCE = ROOT / 'tools/site_sources/reader_guidance'

# Exact interface labels only: leave record quotations, research conclusions,
# identifiers and source titles untouched.
PUBLIC_LABELS = {
    'Family atlas': 'Family tree', 'Family Atlas': 'Family tree',
    'People catalogue': 'People', 'Person dossier': 'Biography',
    'Current position': 'Biography and research notes',
    'Research still needed': 'Further research',
    'Research/export tools': 'Earlier notes and downloads',
    'Structured dossier and technical data': 'Research data and downloads',
    'Machine-readable dossier': 'Person data (JSON)',
    'Source library': 'Sources', 'Research workspace': 'Research questions',
    'Free-space research pages.': 'WikiTree Free-Space Pages',
    'Important external studies, locally summarised.': 'Research summaries',
    'Statistics from the public historical catalogue.': 'Family history statistics',
    'Places, names, branches and movement': 'Places, names, families and migration',
    'Largest exported family branches': 'Largest family groups from WikiTree',
    'Every record. Room to explore.': 'People and records',
    'Return to the canvas': 'Return to the tree', 'Back to canopy': 'Back to the whole tree',
    'What would resolve this': 'What evidence would answer this?',
    'Record to request or inspect': 'Next record to check',
    'Between one person and the whole tree.': 'Families and places',
    'Family & locality studies': 'Family and place studies',
    'Compare two identities': 'Compare two people',
    'Unresolved parentage & matches': 'Possible parents and profile matches',
    'Free-space research library': 'WikiTree Free-Space Pages',
    'Research cluster': 'Family or research group',
    'Needs updated on WikiTree': 'WikiTree profiles to update',
    'What is here. And what it means.': 'What the site includes',
    'One registry. Different coverage.': 'Why the page totals differ',
    'Imports and reviewed assertions.': 'WikiTree details and reviewed research',
    'Colour is place. Status is evidence.': 'Place colours and relationship labels',
    'Dates and map limits.': 'Dates and map locations',
    'Catalogue entries outside the atlas.': 'People outside the family tree',
}

LEGACY_NOTE_ANCHORS = {
    'people/glasgow-951.html': {
        'research-note-a881483109c6': 'research-note-b99bb1785821',
    },
}


def preserve_note_anchors(page, relative):
    for old, current in LEGACY_NOTE_ANCHORS.get(relative, {}).items():
        if f'id="{old}"' not in page:
            page = re.sub(r'(<details\b[^>]*\bid="' + re.escape(current) + r'"[^>]*>)',
                          lambda m: m[1] + f'<span id="{old}" aria-hidden="true"></span>', page, count=1)
    return page


def public_labels(page):
    # Limit replacements to complete headings and controls, never paragraphs,
    # quotations, manuscript readings or arbitrary mentions within a biography.
    pattern = r'(<(?:h[1-6]|span|strong|a|button|summary|dt)\b[^>]*>)([^<>]+)(</(?:h[1-6]|span|strong|a|button|summary|dt)>)'
    def label(match):
        text = match[2].strip()
        replacement = PUBLIC_LABELS.get(text)
        return match[1] + match[2].replace(text, replacement) + match[3] if replacement else match[0]
    page = re.sub(pattern, label, page)
    return page.replace('>Archive and research tools<', '>Earlier notes and research tools<').replace('Citations, provenance and limitations', 'References and source limitations')


def replace_block(page, pattern, replacement):
    page, count = re.subn(pattern, lambda _: replacement, page, count=1, flags=re.S)
    if count != 1:
        raise ValueError(f'Reader guidance target missing: {pattern}')
    return page


def home_page(page):
    intro = (SOURCE / 'home-intro.html').read_text().strip()
    guide = (SOURCE / 'home-start.html').read_text().strip()
    page = re.sub(r'<aside class="reader-start".*?</aside>', '', page, flags=re.S)
    figure = re.search(r'<figure class="repair-canopy-figure">.*?</figure>', page, re.S)
    if not figure:
        raise ValueError('Homepage tree preview missing')
    intro = intro.replace('<!-- reader-tree-preview -->', figure[0])
    # Retain the linked visual in the opening; remove its former lower section.
    page = re.sub(r'<section class="reader-tree"[^>]*>.*?</section>', '', page, count=1, flags=re.S)
    if 'class="reader-intro"' in page:
        page = replace_block(page, r'<section class="reader-intro".*?</section>', intro)
    else:
        page = replace_block(page, r'<section class="v3-home-hero">.*?</section>', intro)
    feature = re.search(r'<section class="v3-feature"[^>]*>.*?</section>', page, re.S)
    if not feature:
        raise ValueError('Homepage research example missing')
    example = feature[0]
    example = re.sub(r'<section[^>]*>', '<section class="v3-feature" id="research-example" aria-labelledby="research-example-title">', example, count=1)
    example = replace_block(example, r'<span class="r-kicker">.*?</span>', '<span class="r-kicker">A question we are investigating · County Antrim</span>')
    example = replace_block(example, r'<h2[^>]*>.*?</h2>', '<h2 id="research-example-title">Who were Alexander Glasgow’s parents?</h2>')
    example = replace_block(example, r'<p>.*?</p>', '<p>Alexander lived at Lisnagaver in County Antrim. Census returns and his children’s marriage records help trace his household. His parentage still needs proof. Read the findings, the source references and the next records to check.</p>')
    example = example.replace('Explore the main research questions', 'See all open questions').replace('Follow Alexander’s evidence', 'Read Alexander’s research').replace('Read the shared sources', 'Find his source records').replace('The leading Gortahar death identification', 'Probable death at Gortahar')
    example = replace_block(example, r'<div class="r-actions">.*?</div>',
                            '<div class="r-actions"><a class="r-button primary" href="/people/glasgow-951.html">Read Alexander’s research →</a>'
                            '<a class="r-button" href="/research/#open-questions">See all open questions →</a>'
                            '<a class="r-button" href="/sources/?person=Glasgow-951">Find his source records</a></div>')
    example = example.replace('/people/glasgow-951.html#life-events', '/people/glasgow-951.html#census-household', 1)
    example = example.replace('/people/glasgow-951.html#life-events', '/people/glasgow-951.html#death-assessment', 1)
    example = example.replace('/events/?person=Glasgow-951&amp;mode=mention', '/people/glasgow-951.html#children-adults')
    example = example.replace('/connections/?a=Glasgow-951&amp;b=Glasgow-3904', '/people/glasgow-951.html#parentage-context')
    # Keep the reading guide first, then the map above Alexander's example.
    page = page[:feature.start()] + page[feature.end():]
    study_map = re.search(r'<section\b(?=[^>]*\bid="study-map")[^>]*>.*?</section>', page, re.S)
    if not study_map:
        raise ValueError('Homepage study map missing')
    map_html = study_map[0]
    page = page[:study_map.start()] + page[study_map.end():]
    intro_end = page.index('</section>', page.index('class="reader-intro"')) + len('</section>')
    page = page[:intro_end] + guide + map_html + example + page[intro_end:]
    replacements = {
        'People Catalogue': 'People', 'Names, families &amp; dossiers': 'Life details, relatives and research notes',
        'Source Records': 'Records &amp; sources', 'Citations &amp; original evidence': 'Census, parish, probate and other records',
        'Y-DNA Explorer': 'Y-DNA research', 'Testers, SNPs &amp; paternal lines': 'DNA results and father-to-son ancestry',
        'Historical Timeline': 'Historical timeline', 'The lineage in context': 'Historical background to the DNA research',
        'Free-space Library': 'WikiTree study pages', 'Direct routes into the archive': 'Ways to explore the research',
        'The family atlas': 'The family tree', 'Open the atlas': 'Open the tree', 'Open the family Atlas': 'Open the family tree',
        'Countries in the family atlas': 'Countries in the family tree', 'All families &amp; localities': 'All families &amp; places',
        'A preview of the recorded family tree. The colour key follows profile locations in the Atlas. Click anywhere in the preview to explore the full tree.': 'Colours show where people were recorded. Select the preview to open the full family tree.',
        'Start with a family. Or a place.': 'Family studies', 'A place to begin': 'Family study',
        'The DNA, in its historical setting.': 'What can Y-DNA tell us?',
        'See how the genetic branches align with documented paternal lines, then follow the proposed history further back.': 'Compare DNA results with family lines traced through fathers and sons, and see where the common ancestor remains unknown.',
        'Follow the connection.': 'How are two people related?', 'Compare identities': 'Compare two people',
    }
    for old, new in replacements.items():
        page = page.replace(old, new)
    page = re.sub(r'<title>.*?</title>', '<title>Glasgow family history · Glasgow Surname Project</title>', page, count=1)
    page = page.replace('<strong>Overview</strong>', '<strong>Home</strong>')
    # Older repairs can append the study-map initializer repeatedly.
    seen = set()
    def single_script(match):
        source = match[1].split('?')[0]
        if source in seen:
            return ''
        seen.add(source)
        return match[0]
    page = re.sub(r'<script\b[^>]*src="([^"]*branches-directory\.js[^\"]*)"[^>]*>\s*</script>', single_script, page)
    return page


def about_page(page):
    intro = (SOURCE / 'about-intro.html').read_text().strip()
    # Retain the independently maintained coverage table and contribution links.
    page = replace_block(page, r'<header class="g-editorial-hero">.*?(?=<div class="g-section-heading">)', intro)
    for old, new in {
        'The name is the starting point. The records tell the story.': 'About this research',
        'Clear about the coverage.': 'What is in the collection?',
        'Supplied snapshot': 'Date compiled', 'Family atlas': 'Family tree', 'Y-DNA pins': 'Y-DNA markers',
        'Include the profile, the exact claim and the underlying source. A precise correction is easier to evaluate and carry back into the research.': 'Send the person’s name, the detail to correct and a reference or link to the record.',
    }.items():
        page = page.replace(old, new)
    return re.sub(r'<title>.*?</title>', '<title>About this research · Glasgow Surname Project</title>', page, count=1)


def coverage_page(page):
    # Preserve totals, named profiles and every limitation in the existing
    # coverage account; simplify its terminology rather than shortening it.
    for old, new in {
        'A transparent account of the imported collection, the shared display assessments and the limits of each view.': 'Where the information came from, what has been checked and what each page can tell you.',
        'The catalogue contains': 'The people index contains',
        'The atlas contains': 'The family tree contains',
        'atlas IDs': 'family-tree profile IDs', 'in the atlas': 'in the family tree',
        'the atlas': 'the family tree', 'corresponding dossier': 'corresponding person page',
        'dossiers': 'person pages', 'curated vital/relationship assessment': 'reviewed assessment of life details or relationships',
        'The display model is a separate, versioned layer.': 'Reviewed conclusions are kept separately from the original details, with earlier versions preserved.',
        'parent/spouse graph': 'parent and spouse relationships',
        'collateral lines': 'the families of siblings and other relatives',
        'An evidence date remains an association until its assertion is evaluated; it is not automatically a life event.': 'A date attached to a source or research note is not treated as an event in someone’s life until its meaning has been checked.',
    }.items():
        page = page.replace(old, new)
    return page


def repair():
    changed = Counter()
    # Person regeneration also rebuilds its shell. Keep its WikiTree action,
    # Latest research link and shared footer before applying reader wording.
    changed.update(repair_navigation())

    def write(path, content):
        if not path.exists() or path.read_text() != content:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
            changed['reader_guidance'] += 1

    css = (SOURCE / 'reader-guidance.css').read_text()
    write(WEB / 'assets/repair/reader-guidance.css', css)
    css_tag = f'<link rel="stylesheet" href="/assets/repair/reader-guidance.css?v={sha256(css.encode()).hexdigest()[:10]}">'
    for relative, transform in [('index.html', home_page), ('about/index.html', about_page)]:
        path = WEB / relative
        page = transform(path.read_text())
        page = re.sub(r'<link\b[^>]*href="/assets/repair/reader-guidance\.css[^"\s]*"[^>]*>', '', page)
        page = page.replace('</head>', css_tag + '</head>', 1)
        description = ('Research findings, family histories, source records and open questions about people named Glasgow and their families.'
                       if relative == 'index.html' else 'What the Glasgow Surname Project has found, what remains uncertain, and how to use the site with WikiTree.')
        page = replace_block(page, r'<meta\b(?=[^>]*\bname="description")[^>]*>',
                             f'<meta name="description" content="{description}">')
        write(path, page)

    path = WEB / 'research/index.html'
    page = replace_block(path.read_text(), r'<header class="v3-page-head">.*?</header>',
                         '<header class="v3-page-head"><span class="r-kicker">Research in progress</span><h1>Questions we are working on</h1>'
                         '<p>These are the family relationships and identities we are still investigating. Each question links to the evidence collected so far, our current conclusion and the records still needed.</p></header>')
    page = re.sub(r'<title>.*?</title>', '<title>Research questions · Glasgow Surname Project</title>', page, count=1)
    write(path, page)
    path = WEB / 'coverage/index.html'
    write(path, coverage_page(path.read_text()))
    path = WEB / 'onetree/index.html'
    page = path.read_text()
    for old, new in {
        'The family atlas': 'The family tree', 'Family Atlas': 'Family tree',
        'Family atlas': 'Family tree', 'THE FAMILY ATLAS': 'THE FAMILY TREE',
        '>Canopy<': '>Whole tree<', 'A readable route into the canopy': 'Browse families by name',
        'Return to the canvas': 'Return to the tree', 'Back to canopy': 'Back to the whole tree',
        'THE COMPLETE CANOPY': 'THE WHOLE TREE',
    }.items():
        page = page.replace(old, new)
    write(path, page)
    # Refresh only catalogue introductory wording, leaving filters/data intact.
    for relative in ('catalogue.html', 'catalogue/index.html', 'catalogue/advanced.html'):
        path = WEB / relative
        page = path.read_text()
        match = re.search(r'<section class="catalogue-hero[^\"]*">.*?</section>', page, re.S)
        if match:
            total = re.search(r'Search ([\d,]+) historical people', match[0])
            if not total:
                raise ValueError(f'Catalogue count missing in {relative}')
            page = page.replace(match[0], hero_html(int(total[1].replace(',', ''))), 1)
            page = compact_statistics(page)
            page = re.sub(r'<title>.*?</title>', '<title>Find a person · Glasgow Surname Project</title>', page, count=1)
            page = re.sub(r'(<div class="g-crumbs">.*?<strong>).*?(</strong>)', r'\1Find a person\2', page, count=1, flags=re.S)
            page = re.sub(r'<link\b[^>]*href="/assets/repair/reader-guidance\.css[^"\s]*"[^>]*>', '', page)
            page = page.replace('</head>', css_tag + '</head>', 1)
            write(path, page)

    submenus = (ROOT / 'tools/section_submenus.js').read_text()
    submenu_version = sha256(submenus.encode()).hexdigest()[:10]
    write(WEB / 'assets/unified/section-submenus.js', submenus)
    catalogue_script = (ROOT / 'tools/catalogue_search.js').read_text()
    catalogue_version = sha256(catalogue_script.encode()).hexdigest()[:10]
    write(WEB / 'people/search.js', catalogue_script)
    # Update the shared labels and their script cache key, leaving historical
    # copies and unrelated asset references unchanged.
    for path in WEB.rglob('*.html'):
        if is_excluded(path) or 'www_old' in path.parts:
            continue
        page = path.read_text()
        if not NAV.search(page):
            continue
        page = public_labels(page)
        page = preserve_note_anchors(page, path.relative_to(WEB).as_posix())
        page = re.sub(r'(class="kicker">)Person dossier ·', r'\1Biography ·', page)
        page = NAV.sub(lambda _: render_primary_navigation(path.relative_to(WEB)), page, count=1)
        page = page.replace('A shared research collection. Profile links and hypotheses are kept distinct from the evidence behind them.',
                            'Family history research, with sources and notes on uncertain relationships.')
        page = page.replace('>Research workspace<', '>Research questions<')
        page = page.replace('Search the archive', 'Search this site').replace('Search the Glasgow archive', 'Search Glasgow family history')
        page = page.replace('Your research notebook.', 'Saved people and pages')
        page = page.replace('Browse by research cluster', 'Browse by family or research group')
        page = page.replace('>Any cluster<', '>Any group<')
        # Accessible tree controls use the same words as their visible labels.
        page = page.replace('aria-label="Interactive family atlas"', 'aria-label="Interactive family tree"')
        page = page.replace('aria-label="Atlas views"', 'aria-label="Family tree views"')
        page = page.replace('Move around the family canvas', 'Move around the family tree')
        titles = {'branches/index.html': 'Families and places', 'free-space/index.html': 'WikiTree Free-Space Pages',
                  'coverage/index.html': 'What the site includes', 'statistics/index.html': 'Family history statistics',
                  'sources/index.html': 'Sources', 'records/index.html': 'Records by person'}
        title = titles.get(path.relative_to(WEB).as_posix())
        if title:
            page = re.sub(r'<title>.*?</title>', f'<title>{title} · Glasgow Surname Project</title>', page, count=1)
        page = page.replace('Browse all people without JavaScript', 'Browse the name index').replace('Browse all family groups without JavaScript', 'Browse family groups').replace('Small data downloads and freshness manifest', 'Download research data')
        page = re.sub(r'(assets/unified/section-submenus\.js\?v=)[^"\s>]+',
                      lambda m: m[1] + submenu_version, page)
        page = re.sub(r'((?:/people/|\b)search\.js\?v=)[^"\s>]+',
                      lambda m: m[1] + catalogue_version, page) if path.parent.name == 'catalogue' or path.parent == WEB / 'people' or path.name == 'catalogue.html' else page
        write(path, page)
    # The evidence guide copies the About shell, including its styles and rail.
    changed.update(runpy.run_path(str(ROOT / 'tools/build_evidence_page.py'))['build']())
    return changed


if __name__ == '__main__':
    print(dict(repair()))
