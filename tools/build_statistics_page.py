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


def first_names_panel(people=None):
    if people is None:
        path = WEB / 'data/people.json'
        data = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
        people = data.get('people', [])
    rows = first_name_rows(people)
    payload = json.dumps(rows, ensure_ascii=True).replace('<', '\\u003c')
    return (
        '<section class="statistics-names" id="first-names" aria-labelledby="first-names-title">'
        '<div class="statistics-feature-head"><div><span class="r-kicker">The names we share</span>'
        '<h2 id="first-names-title">First names</h2>'
        '<p>People born with the Glasgow surname, worldwide.</p></div>'
        '<div class="statistics-name-filters">'
        '<label for="names-century">Birth period<select id="names-century">'
        '<option value="">All years</option>' +
        ''.join(f'<option value="{year}">Before {year}</option>' for year in range(1500, 2100, 100)) +
        '</select></label><label for="names-gender">Gender<select id="names-gender">'
        '<option value="">All genders</option><option>Female</option><option>Male</option>'
        '<option>Unknown</option></select></label><button type="button" id="names-reset">Reset</button></div></div>'
        '<p id="names-summary" role="status" aria-live="polite"></p>'
        '<div class="statistics-name-layout"><div class="statistics-name-chart"><div id="names-pie"></div>'
        '<p class="statistics-pie-hint">Hover or tap a name to explore.</p></div>'
        '<div class="statistics-name-ranking"><h3>The leading names</h3>'
        '<ol id="names-leaders"></ol></div></div>'
        '<details class="statistics-name-counts"><summary id="names-count-title">View all name counts</summary>'
        '<div class="statistics-name-table" tabindex="0" aria-label="All first-name counts"><table><caption>First-name counts and percentages</caption>'
        '<thead><tr><th scope="col">First name</th><th scope="col">People</th><th scope="col">Share</th></tr></thead>'
        '<tbody id="names-rows"></tbody></table></div></details>'
        '<details class="statistics-method"><summary>How these names are counted</summary>'
        '<p>Each person counts once, using the first word of their first given name; spelling variants stay separate. '
        'Birth-period filters are cumulative. Approximate single years are included; missing years, ranges and before/after dates are excluded when a period is selected. '
        'Gender uses the maintained catalogue classifications; initials and ambiguous names may remain Unknown. '
        'The pie labels the 12 most common names and groups the rest as Other names. These are catalogue patterns, not population statistics.</p></details>'
        '<noscript>Enable JavaScript to explore the chart and filters.</noscript>'
        '<script type="application/json" id="names-data">' + payload + '</script></section>'
    )


def _familysearch_registry():
    path = ROOT / "data/familysearch/person-links.json"
    if not path.exists():
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    people = value.get("people") if isinstance(value, dict) else None
    return people if isinstance(people, dict) else {}


def _birth_century_label(year):
    if not year:
        return "Unknown birth"
    century = year // 100 + 1
    return f"{century}{'st' if century == 21 else 'th'} century"


def catalogue_coverage_panel(people=None, registry=None):
    """Catalogue coverage: WikiTree and FamilySearch identities by birth century."""
    people = people or []
    registry = {str(key).lower(): value for key, value in (registry or {}).items()}

    def has_wikitree(person):
        return bool(person.get("profile_ids")) or bool(person.get("wikitree_urls"))

    def has_familysearch(person):
        return str(person.get("catalogue_id", "")).lower() in registry

    total = len(people)
    wikitree = sum(has_wikitree(person) for person in people)
    familysearch = sum(has_familysearch(person) for person in people)
    both = sum(1 for person in people if has_wikitree(person) and has_familysearch(person))

    buckets = {}
    for person in people:
        match = re.search(r"\b(?:1[0-9]|20)\d{2}\b", str(person.get("birth") or ""))
        label = _birth_century_label(int(match.group()) if match else None)
        row = buckets.setdefault(label, [0, 0, 0])
        row[0] += 1
        row[1] += has_wikitree(person)
        row[2] += has_familysearch(person)

    def century_key(label):
        match = re.search(r"(\d+)", label)
        return (1, 0) if not match else (0, int(match.group(1)))

    def share(count, base):
        return f"{100 * count / base:.1f}%" if base else "0.0%"

    def number(count):
        return f"{count:,}"

    rows = "".join(
        f'<tr><th scope="row">{label}</th><td>{number(row[0])}</td>'
        f'<td>{number(row[1])} <span class="statistics-coverage-share">({share(row[1], row[0])})</span></td>'
        f'<td>{number(row[2])} <span class="statistics-coverage-share">({share(row[2], row[0])})</span></td></tr>'
        for label, row in sorted(buckets.items(), key=lambda item: century_key(item[0]))
    )
    metric_parts = []
    for label, value, show_share in (
            ("Catalogue people", total, False),
            ("With a WikiTree ID", wikitree, True),
            ("With a FamilySearch ID", familysearch, True),
            ("With both", both, True)):
        suffix = " · " + share(value, total) if show_share else ""
        metric_parts.append(
            '<div class="statistics-metric"><strong>' + number(value) + '</strong>'
            '<span>' + label + suffix + '</span></div>')
    metrics = "".join(metric_parts)
    return (
        '<section class="statistics-panel" id="catalogue-coverage">'
        '<h3>Catalogue coverage</h3>'
        '<div class="statistics-metric-grid">' + metrics + '</div>'
        '<div class="statistics-generations-table-wrap"><table>'
        '<caption>Catalogue people with WikiTree and FamilySearch identities, by birth century</caption>'
        '<thead><tr><th scope="col">Birth century</th><th scope="col">People</th>'
        '<th scope="col">WikiTree ID</th><th scope="col">FamilySearch ID</th></tr></thead>'
        '<tbody>' + rows + '</tbody></table></div>'
        '<details class="statistics-panel-method"><summary>About this chart</summary>'
        '<p>People in the public research catalogue with a WikiTree or FamilySearch identity. '
        'Century rows use the first recorded birth year; missing or unusable birth dates are shown separately. '
        'Table percentages are within each birth century; the cards are shares of the whole catalogue.</p>'
        '</details></section>'
    )


def enrich_panels(markup, people=None, index=None):
    """Supply complete denominators and full migration flows to reader charts."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(markup, 'html.parser')
    people_path = WEB / 'data/people.json'
    if people is None:
        people = json.loads(people_path.read_text())['people'] if people_path.exists() else []
    index_path = WEB / 'data/catalogue-search-index.json'
    if index is None:
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



def chart_views(panels, summary=None, people=None, index=None):
    """Separate visual stories instead of presenting every table at once."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(panels, 'html.parser')
    all_panels = soup.select('.statistics-panel')
    by_id = {panel.get('id'): panel for panel in all_panels if panel.get('id')}
    for panel in all_panels:
        description = panel.find('p', recursive=False)
        if description:
            method = soup.new_tag('details', attrs={'class': 'statistics-panel-method'})
            heading = soup.new_tag('summary')
            heading.string = 'About this chart'
            method.append(heading)
            method.append(description.extract())
            panel.append(method)
    def panel(ident):
        return str(by_id[ident]) if ident in by_id else ''
    comparison = panel('given-names')
    if comparison:
        comparison = '<details class="statistics-comparison"><summary>Compare first names across all surnames<span>Entire catalogue</span></summary>' + comparison + '</details>'
    try:
        from tools.statistics_generations import render_generations_story
        from tools.statistics_places import render_places_story
        from tools.statistics_journeys import render_journeys_story
    except ModuleNotFoundError:
        from statistics_generations import render_generations_story
        from statistics_places import render_places_story
        from statistics_journeys import render_journeys_story
    migration_script = soup.select_one('.statistics-migration-data')
    flows = json.loads(migration_script.string) if migration_script and migration_script.string else []
    branch_detail = panel('family-branches')
    if branch_detail:
        branch_detail = '<details class="statistics-story-details"><summary>Compare all exported family branches</summary>' + branch_detail + '</details>'
    places_details = (
        '<section class="statistics-places-detail-section"><div class="statistics-story-section-head"><div>'
        '<span class="statistics-story-eyebrow">Places and marriage connections</span>'
        '<h3>Inside the regional records</h3><p>Compare mapped associations and recorded spouse surnames.</p></div></div>'
        '<div class="statistics-grid">' + ''.join(panel(ident) for ident in ('regions', 'mapped-places', 'married-surnames')) +
        '</div>' + branch_detail + '</section>'
    )
    views = {
        'names': first_names_panel(people) + comparison,
        'time': render_generations_story(people or [], panel('birth-centuries')),
        'places': render_places_story(people or [], index or [], summary or '', web_root=WEB) + places_details,
        'journeys': render_journeys_story(flows, panel('migration'), web_root=WEB),
        'coverage': catalogue_coverage_panel(people, _familysearch_registry()),
    }
    if summary is not None:
        try:
            from tools.statistics_overview import render_dashboard_overview
        except ModuleNotFoundError:
            from statistics_overview import render_dashboard_overview
        views['names'] = render_dashboard_overview(summary, people or [], index or [], web_root=WEB) + views['names']
    # Preserve unusual legacy panels rather than dropping their source counts.
    known = {'given-names', 'birth-centuries', 'regions', 'family-branches', 'mapped-places', 'married-surnames', 'migration'}
    views['places'] += ''.join(str(item) for item in all_panels if item.get('id') not in known)
    tabs = [('names', 'Overview', 'statistics-view-names'), ('coverage', 'Catalogue', 'statistics-view-coverage'), ('time', 'Generations', 'statistics-view-time'),
            ('places', 'Places &amp; families', 'statistics-view-places'), ('journeys', 'Journeys', 'statistics-view-journeys')]
    nav = '<nav class="statistics-view-tabs" id="statistics-detail-title" aria-label="Explore statistics">' + ''.join(
        '<a id="statistics-tab-' + key + '" href="#' + anchor + '" data-statistics-view="' + key + '">' + label + '</a>'
        for key, label, anchor in tabs) + '</nav>'
    return nav + ''.join('<section id="statistics-view-' + key + '" class="statistics-view" data-statistics-pane="' + key + '" aria-labelledby="statistics-tab-' + key + '">' + views[key] + '</section>' for key, _, _ in tabs)

def install_chart_assets(shell):
    """Version only this page's maintained assets, without global cache stamping."""
    assets = {
        'statistics_page.css': 'statistics.css',
        'statistics_names.css': 'statistics-names.css',
        'statistics_stories.css': 'statistics-stories.css',
        'statistics_flow.css': 'statistics-flow.css',
        'statistics_names.js': 'statistics-names.js',
        'statistics_panels.js': 'statistics-panels.js',
        'statistics_layout.js': 'statistics-layout.js',
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
    people_path = WEB / 'data/people.json'
    public_people = json.loads(people_path.read_text())['people'] if people_path.exists() else []
    index_path = WEB / 'data/catalogue-search-index.json'
    public_index = json.loads(index_path.read_text()) if index_path.exists() else []
    panels = enrich_panels(panels, public_people, public_index)
    current_summary = rebase_catalogue_links(_current_catalogue_summary() or summary.group(0))
    main = (
        '<main class="r-main statistics-page" id="main"><header class="statistics-page-head">'
        '<div><span class="r-kicker">The Glasgow surname project</span><h1>Statistics explorer</h1></div>'
        '<a class="statistics-about-link" href="/coverage/">About the collection <span aria-hidden="true">↗</span></a></header>'
        + chart_views(panels, current_summary, public_people, public_index) +
        '<details class="statistics-method statistics-page-method"><summary>About these statistics</summary>'
        '<p>Counts describe the public historical catalogue and its documented associations. '
        'A person can appear in more than one place or marriage-surname category, so those charts are not parts of a single whole. '
        '<a href="/coverage/">About the data</a> · <a href="/status/">Catalogue status</a></p><p>' +
        caution + '</p></details></main>'
    )
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
    shell = shell.replace('g-kind-research', 'g-kind-catalogue stats-dashboard')
    shell = repair_site_identity_page(repair_nav_only_page(shell, Path('statistics/index.html')), Path('statistics/index.html'))
    shell = shell.replace('g-kind-catalogue v3-site', 'g-kind-catalogue stats-dashboard v3-site') if 'stats-dashboard' not in shell else shell
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
