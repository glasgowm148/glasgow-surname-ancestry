#!/usr/bin/env python3
"""Build the public statistics page from the maintained statistics artifact."""
from pathlib import Path
import json
import re
import hashlib
from collections import Counter
try:
    from tools.site_identity import SITE_NAME, page_title
except ModuleNotFoundError:
    from site_identity import SITE_NAME, page_title

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / 'www'
STATISTICS_ARTIFACT = WEB / 'data/catalogue-statistics.json'


def _statistics_markup() -> str:
    """Read the generated source, retaining compatibility with old catalogue pages."""
    if STATISTICS_ARTIFACT.exists():
        return json.loads(STATISTICS_ARTIFACT.read_text(encoding='utf-8'))['html']

    catalogue = (WEB / 'catalogue/index.html').read_text(encoding='utf-8')
    start = re.search(
        r'<section\b(?=[^>]*\bid="statistics")(?=[^>]*\bclass="[^"]*\bcatalogue-statistics\b)[^>]*>',
        catalogue,
    )
    if not start:
        raise RuntimeError('Could not locate the maintained catalogue statistics pane')
    end = re.search(r'</details>(?:</details>)?</section>', catalogue[start.end():])
    if not end:
        raise RuntimeError('Could not locate the end of the maintained catalogue statistics pane')
    statistics = catalogue[start.start():start.end() + end.end()]
    # Some historical catalogue pages wrap the source in this disclosure.
    if 'class="catalogue-overview"' in statistics:
        statistics = re.sub(
            r'<details class="catalogue-overview">.*?</summary>', '', statistics, count=1, flags=re.S)
        statistics = re.sub(r'</details>\s*</section>$', '</section>', statistics, count=1)
    return statistics


def rebase_catalogue_links(markup: str) -> str:
    """Make the catalogue pane's links root-absolute for /statistics/.

    The pane is written for the catalogue page, which sets <base href="/">;
    copied into /statistics/ its relative links would resolve in the wrong
    folder (catalogue.html?first=John -> /statistics/catalogue.html).
    """
    markup = re.sub(r'href="(people/|places/)', r'href="/\1', markup)
    return re.sub(r'href="/?catalogue\.html(?=[?#"])', 'href="/catalogue/', markup)


def _current_catalogue_summary() -> str | None:
    """Use targeted count repairs already applied to the public catalogue."""
    catalogue_path = WEB / 'catalogue/index.html'
    if not catalogue_path.exists():
        return None
    catalogue = catalogue_path.read_text(encoding='utf-8')
    summary = re.search(
        r'<div class="statistics-summary">.*?</div>\s*</div>', catalogue, re.S)
    return summary.group(0) if summary else None



def first_name_rows(people):
    """Aggregate the public birth-surname cohort without exposing extra fields."""
    counts = Counter()
    for person in people:
        if person.get('likely_living') or not any(
                str(name).strip().casefold() == 'glasgow'
                for name in person.get('last_names_at_birth', [])):
            continue
        names = person.get('first_names') or []
        first = str(names[0]).strip().split() if names else []
        name = first[0].strip('[]?').title() if first else ''
        if not name or name.casefold() in {'unknown', 'unnamed', 'not', 'n.n.', 'nn', 'private'}:
            name = 'Unknown first name'
        birth = str(person.get('birth') or '')
        years = re.findall(r'\b[1-2]\d{3}\b', birth)
        # A bound or range is not a point estimate; exclude it from year cutoffs.
        year = int(years[0]) if len(years) == 1 and not re.search(
            r'before|after|bef\.?|aft\.?|[<>]', birth, re.I) else None
        gender = person.get('gender')
        gender = gender if gender in ('Male', 'Female') else 'Unknown'
        counts[(name, year, gender)] += 1
    return [[name, year, gender, count] for (name, year, gender), count in
            sorted(counts.items(), key=lambda item: (item[0][0], item[0][1] or 0, item[0][2]))]


def first_names_panel():
    path = WEB / 'data/people.json'
    data = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
    rows = first_name_rows(data.get('people', []))
    payload = json.dumps(rows, ensure_ascii=True).replace('<', '\\u003c')
    return (
        '<section class="statistics-names" id="first-names" aria-labelledby="first-names-title">'
        '<span class="r-kicker">Given names through time</span>'
        '<h2 id="first-names-title">First names of people born Glasgow</h2>'
        '<p>People whose recorded surname at birth was Glasgow, wherever they were born. '
        'Each catalogue person counts once, using the first word of their first given name; spelling variants stay separate.</p>'
        '<div class="statistics-name-filters">'
        '<label for="names-century">Born before<select id="names-century">'
        '<option value="">All years</option>' +
        ''.join(f'<option value="{year}">Before {year} (&lt;{year})</option>' for year in range(1500, 2100, 100)) +
        '</select></label><label for="names-gender">Gender<select id="names-gender">'
        '<option value="">All genders</option><option>Female</option><option>Male</option>'
        '<option>Unknown</option></select></label><button type="button" id="names-reset">Reset filters</button></div>'
        '<p id="names-summary" role="status" aria-live="polite"></p>'
        '<div class="statistics-name-layout"><div class="statistics-name-chart"><div id="names-pie"></div><p class="statistics-pie-hint">Hover, tap or focus a slice to explore a name.</p></div>'
        '<div class="statistics-name-table"><table><caption>First-name counts and percentages</caption>'
        '<thead><tr><th scope="col">First name</th><th scope="col">People</th><th scope="col">Share</th></tr></thead>'
        '<tbody id="names-rows"></tbody></table></div></div>'
        '<p class="statistics-name-note">Year filters are cumulative: before 1800 includes all dated births earlier than 1800. '
        'Approximate single years are included; missing years, date ranges and before/after dates are excluded when a year filter is selected. '
        'Gender uses the maintained catalogue classifications. Clear historical given names are classified in the underlying workbench; initials and ambiguous names remain Unknown. The pie shows the 12 most common names and groups the rest as Other names; the table lists every name. '
        'These are catalogue patterns, not population statistics.</p>'
        '<noscript>Enable JavaScript to explore the chart and filters.</noscript>'
        '<script type="application/json" id="names-data">' + payload + '</script></section>'
    )


def enrich_panels(markup):
    """Supply complete denominators and full migration flows to reader charts."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(markup, 'html.parser')
    people_path = WEB / 'data/people.json'
    people = json.loads(people_path.read_text())['people'] if people_path.exists() else []
    index_path = WEB / 'data/catalogue-search-index.json'
    index = json.loads(index_path.read_text()) if index_path.exists() else []
    ids = {
        'People by region': 'regions', 'Most frequent given names': 'given-names',
        'Surnames joined by marriage to Glasgow': 'married-surnames',
        'Largest exported family branches': 'family-branches',
        'Most frequent mapped places': 'mapped-places', 'Birth centuries': 'birth-centuries',
        'Most common recorded migrations': 'migration',
    }
    for panel in soup.select('.statistics-panel'):
        title = panel.find('h3')
        if not title:
            continue
        name = title.get_text()
        if name in ids:
            panel['id'] = ids[name]
        if name == 'Most frequent given names' and people:
            panel['data-total'] = str(len(people))
        if name == 'Largest exported family branches' and index:
            panel['data-total'] = str(sum(bool(row.get('family_root')) for row in index))
        if name == 'Most common recorded migrations':
            panel['class'].append('statistics-migration-panel')
            if people:
                try:
                    from tools.build_research_catalog import _broad_place
                except ModuleNotFoundError:
                    from build_research_catalog import _broad_place
                flows = Counter()
                for person in people:
                    origin = _broad_place(person.get('birth_location', ''))
                    destination = _broad_place(person.get('death_location', ''))
                    if origin and destination and origin != destination:
                        flows[(origin, destination)] += 1
                data = soup.new_tag('script', type='application/json')
                data['class'] = 'statistics-migration-data'
                data.string = json.dumps([[a, b, count] for (a, b), count in
                                          sorted(flows.items(), key=lambda row: (-row[1], row[0]))])
                panel.append(data)
    return str(soup)


def install_chart_assets(shell):
    """Version only this page's maintained assets, without global cache stamping."""
    assets = {
        'statistics_page.css': 'statistics.css',
        'statistics_names.css': 'statistics-names.css',
        'statistics_names.js': 'statistics-names.js',
        'statistics_panels.js': 'statistics-panels.js',
    }
    for source_name, target_name in assets.items():
        content = (ROOT / 'tools' / source_name).read_bytes()
        target = WEB / 'assets/repair' / target_name
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists() or target.read_bytes() != content:
            target.write_bytes(content)
        url = '/assets/repair/' + target_name + '?v=' + hashlib.sha256(content).hexdigest()[:10]
        if target_name.endswith('.css'):
            shell = shell.replace('</head>', '<link rel="stylesheet" href="' + url + '"></head>', 1)
        else:
            shell = shell.replace('</body>', '<script src="' + url + '" defer></script></body>', 1)
    return shell

def repair():
    statistics_source = _statistics_markup()
    shell = (WEB / 'research/index.html').read_text(encoding='utf-8')
    # The pane was once nested in a disclosure before the browse section; the
    # filter-toolbar catalogue places it as a sibling section after the results.
    block = re.search(
        r'<section\b(?=[^>]*\bid="statistics")(?=[^>]*\bclass="[^"]*\bcatalogue-statistics\b)[^>]*>'
        r'(.*?</details>)</section>',
        statistics_source, re.S)
    if not block:
        raise RuntimeError('Could not locate the maintained catalogue statistics pane')
    statistics = block.group(1)
    summary = re.search(r'<div class="statistics-summary">.*?</div>(?=\s*<details\b)', statistics, re.S)
    detail = re.search(
        r'<details id="statistics-detail">.*?<div class="statistics-grid">(.*)</div><p class="statistics-caution">(.*?)</p></details>',
        statistics, re.S)
    if not summary or not detail:
        raise RuntimeError('Could not locate the maintained statistics summary or detail panels')
    panels, caution = detail.groups()
    panels = rebase_catalogue_links(panels)
    panels = panels.replace(
        'First recorded given name across the public historical catalogue.',
        'All surnames, all years and all genders across the public historical catalogue. '
        'This panel does not follow the pie-chart filters; the pie includes only people whose surname at birth was Glasgow.')
    panels = enrich_panels(panels)
    current_summary = rebase_catalogue_links(_current_catalogue_summary() or summary.group(0))
    main = '''<main class="r-main statistics-page" id="main"><header class="v3-page-head statistics-page-head"><span class="r-kicker">The collection, at a glance</span><h1>The Glasgow catalogue,<br>by the numbers.</h1><p>Explore the names, places and journeys in the public historical catalogue. Counts describe the collection and its documented associations. <a href="/coverage/">About the data</a> · <a href="/status/">Catalogue status</a></p><nav class="statistics-page-jumps" aria-label="Statistics sections"><a href="#first-names">First names</a><a href="#statistics-detail-title">Comparisons</a><a href="#migration">Recorded journeys</a></nav></header><section class="statistics-page-summary" aria-label="Catalogue summary">''' + current_summary + '''</section><section class="statistics-page-panels" aria-labelledby="statistics-detail-title"><div class="statistics-page-intro"><span class="r-kicker">Patterns in the collection</span><h2 id="statistics-detail-title">Places, names, branches and movement</h2><p>Switch between bars and pies where categories form a meaningful whole. Open linked counts to explore the people behind each chart.</p></div><div class="statistics-grid">''' + panels + '''</div><p class="statistics-caution">''' + caution + '''</p></section></main>'''
    main = main.replace('<section class="statistics-page-panels"', first_names_panel() + '<section class="statistics-page-panels"', 1)
    shell = re.sub(r'<title>.*?</title>', lambda _: f'<title>{page_title("Statistics")}</title>', shell, count=1, flags=re.S)
    shell = re.sub(r'<meta content="The Glasgow surname (?:archive|project):[^"]*" name="description"\s*/?>', '<meta content="Statistics from the public historical catalogue: places, names, branches and recorded movement." name="description">', shell, count=1)
    shell = re.sub(r'<link\b(?=[^>]*\brel=["\']canonical["\'])[^>]*>',
                   '<link rel="canonical" href="https://glasgow.phenotype.dev/statistics/">', shell, count=1)
    shell = shell.replace('data-g-path="/research/index.html"', 'data-g-path="/statistics/index.html"')
    shell = shell.replace('<strong>Research</strong>', '<strong>Statistics</strong>', 1).replace('data-g-path="/research/index.html"', 'data-g-path="/statistics/index.html"')
    shell = re.sub(r'<nav class="v3-view-nav" aria-label="Section views">.*?</nav>', '', shell, count=1, flags=re.S)
    shell = re.sub(r'<main class="r-main" id="main">.*?</main>', main, shell, count=1, flags=re.S)
    try:
        from tools.repair_primary_navigation import repair_nav_only_page, repair_site_identity_page
    except ModuleNotFoundError:
        from repair_primary_navigation import repair_nav_only_page, repair_site_identity_page
    shell = shell.replace('g-kind-research', 'g-kind-catalogue')
    shell = repair_site_identity_page(repair_nav_only_page(shell, Path('statistics/index.html')), Path('statistics/index.html'))
    shell = install_chart_assets(shell)
    output = WEB / 'statistics/index.html'
    output.parent.mkdir(parents=True, exist_ok=True)
    before = output.read_text(encoding='utf-8') if output.exists() else None
    if before != shell:
        output.write_text(shell, encoding='utf-8')
        return {'statistics_page': 1}
    return {}


if __name__ == '__main__':
    print(repair())
