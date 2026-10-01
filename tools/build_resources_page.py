#!/usr/bin/env python3
"""Generate the public resources page and its homepage community links."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / 'www'
STYLE = '<link rel="stylesheet" href="/assets/repair/resources.css?v=1">'


def external(url, title, text, note):
    return f'<a href="{url}" target="_blank" rel="noopener noreferrer"><span class="r-kicker">Community resource</span><h2>{title}</h2><p>{text}</p><small>{note} &#8599;</small></a>'


def repair():
    about = (WEB / 'about/index.html').read_text(encoding='utf-8')
    home_path = WEB / 'index.html'
    home = home_path.read_text(encoding='utf-8')
    community = ''.join((
        external('https://www.wikitree.com/wiki/Space:Glasgow_Name_Study', 'WikiTree Glasgow Name Study', 'The shared WikiTree study, with profiles, source records and family research.', 'Open the name study'),
        external('https://groups.io/g/glasgowdnaproject/', 'Glasgow DNA Project discussion', 'A discussion group for Y-DNA questions, records and potential connections.', 'Open the discussion group'),
        external('https://glasgowfamilygenealogy.org/', 'Glasgow Family Genealogy', 'A searchable independent family database with photographs, documents and histories. Not all genealogy is verified.', 'Visit the family database'),
    ))
    record_links = ''.join((
        external('https://www.scotlandspeople.gov.uk/', "Scotland's People", 'Official Scottish civil, church and census records. Access and charges vary by collection.', 'Search Scottish records'),
        external('https://www.nidirect.gov.uk/proni', 'PRONI', 'Northern Ireland’s public-records office, with catalogues and selected digital material.', 'Open PRONI'),
        external('https://www.irishgenealogy.ie/', 'IrishGenealogy.ie', 'Irish civil records and selected church records supplied through the Irish government service.', 'Search Irish records'),
    ))
    main = '''<main class="resources-page" id="main"><header class="resources-hero"><span class="r-kicker">Useful places to continue the work</span><h1>Resources for the<br>Glasgow research community.</h1><p>These independent and collaborative resources can help locate records, compare work and contribute carefully. A link is a starting point, not proof of a relationship.</p></header><section class="resources-section" aria-labelledby="resources-community"><div><span class="r-kicker">People and shared research</span><h2 id="resources-community">Work with the community.</h2></div><div class="resources-grid">''' + community + '''</div></section><section class="resources-section resources-records" aria-labelledby="resources-records"><div><span class="r-kicker">Records research</span><h2 id="resources-records">Start with the record.</h2><p>Use original or reliable record images where possible, then bring the citation back to the relevant person’s page or research question.</p></div><div class="resources-grid">''' + record_links + '''</div></section><section class="resources-note"><strong>Using external material</strong><p>External databases, trees and discussions can provide leads. Their claims should be checked against the underlying record before they are added to the project’s documented conclusions.</p><a href="/feedback/">Send a sourced correction &#8594;</a></section></main>'''
    page = re.sub(r'<main>.*?</main>', main, about, count=1, flags=re.S)
    page = re.sub(r'<title>.*?</title>', '<title>Research resources · Glasgow surname archive</title>', page, count=1, flags=re.S)
    page = re.sub(r'<meta name="description" content="[^"]*">', '<meta name="description" content="Community and record-search resources for the Glasgow surname research project.">', page, count=1)
    page = page.replace('data-g-path="/about/index.html"', 'data-g-path="/resources/index.html"')
    page = page.replace('g-kind-about', 'g-kind-resources')
    page = re.sub(r'(<div class="g-crumbs">.*?<strong>).*?(</strong>)', r'\1Research resources\2', page, count=1, flags=re.S)
    page = re.sub(r'<nav class="v3-view-nav".*?</nav>', '', page, count=1, flags=re.S)
    page = page.replace('</head>', STYLE + '</head>', 1)
    resources_path = WEB / 'resources/index.html'
    resources_path.parent.mkdir(parents=True, exist_ok=True)
    changed = {}
    if not resources_path.exists() or resources_path.read_text(encoding='utf-8') != page:
        resources_path.write_text(page, encoding='utf-8')
        changed['resources_page'] = 1

    marker = '<!-- resources-home:start -->'
    home = re.sub(r'<!-- resources-home:start -->.*?<!-- resources-home:end -->', '', home, flags=re.S)
    home_section = marker + '<section class="resources-home"><div class="resources-home-heading"><span class="r-kicker">Continue the research</span><h2>Community and research resources.</h2><p>Find the shared study, join the discussion, or search an independent family database.</p><a href="/resources/">All resources &#8594;</a></div><div class="resources-home-grid">' + community + '</div></section><!-- resources-home:end -->'
    home = home.replace('</main>', home_section + '</main>', 1)
    home = home.replace('</head>', STYLE + '</head>', 1)
    if home_path.read_text(encoding='utf-8') != home:
        home_path.write_text(home, encoding='utf-8')
        changed['resources_home'] = 1
    return changed


if __name__ == '__main__':
    print(repair())
