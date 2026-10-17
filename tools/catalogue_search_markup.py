#!/usr/bin/env python3
"""Search header, filter toolbar and panels for the public research catalogue.

The catalogue builder renders this markup into ``www/catalogue.html``; the
unified-shell repair copies that page body into ``/catalogue/``.  Running this
module applies the same markup to already generated catalogue pages without a
full catalogue rebuild (the select options are read from the existing page, so
no source data is touched).

Every existing control keeps its id because ``tools/catalogue_search.js`` and
bookmarked query strings depend on them.  The toolbar is a thin presentation
layer: panel buttons only show and hide groups of those same controls.
"""

from __future__ import annotations

from pathlib import Path
import re

try:
    from catalogue_theme import CATALOGUE_ASSET_VERSION
except ModuleNotFoundError:  # Imported as tools.catalogue_search_markup.
    from tools.catalogue_theme import CATALOGUE_ASSET_VERSION

WEB = Path(__file__).resolve().parents[1] / "www"
PAGES = ("catalogue.html", "catalogue/index.html", "catalogue/advanced.html", "people/index.html")

RELATIONS = (
    ("spouse", "Spouse", "catalogue-spouse-name", "Full name, including married name"),
    ("father", "Father", "catalogue-father-name", "Full name"),
    ("mother", "Mother", "catalogue-mother-name", "Full name, including married name"),
    ("child", "Child", "catalogue-child-name", "Full name"),
    ("sibling", "Sibling", "catalogue-sibling-name", "Full name, including married name"),
)

SOURCE_QUALITY_OPTIONS = (
    '<option value="original">Original record</option><option value="derivative">Index or transcription</option>'
    '<option value="secondary">Secondary source</option><option value="tree_only">Tree/profile only</option>'
    '<option value="unknown">Unclassified</option>'
)


def hero_html(total: int) -> str:
    return (
        '<section class="catalogue-hero catalogue-hero-compact"><div><h1>Find a person</h1>\n'
        f'<p class="lede">Search {total:,} historical people connected with the Glasgow surname. Open a name for family details, sources and research notes.</p></div>'
        f'<p class="catalogue-total"><strong id="catalogue-total">{total:,}</strong> people in catalogue</p></section>'
    )


def _toggle(key: str, label: str) -> str:
    return (
        f'<button type="button" class="catalogue-filter-toggle" id="catalogue-filter-toggle-{key}" '
        f'data-filter-panel="{key}" aria-expanded="false" aria-controls="catalogue-filter-panel-{key}">'
        f'<span>{label}</span><span class="catalogue-filter-count" hidden></span>'
        '<svg aria-hidden="true" viewBox="0 0 12 12" width="12" height="12"><path d="M2.5 4.5 6 8l3.5-3.5" fill="none" stroke="currentColor" stroke-width="1.6"/></svg></button>'
    )


def _panel(key: str, label: str, body: str, width: str = "") -> str:
    return (
        f'<div class="catalogue-filter-item">{_toggle(key, label)}'
        f'<div class="catalogue-filter-panel{(" " + width) if width else ""}" id="catalogue-filter-panel-{key}" '
        f'role="group" aria-labelledby="catalogue-filter-toggle-{key}" data-filter-panel-body="{key}" hidden>'
        f'<div class="catalogue-filter-panel-head"><h3>{label}</h3>'
        '<button type="button" class="catalogue-filter-close" data-filter-close>Done</button></div>'
        f'{body}</div></div>'
    )


def _check(control_id: str, label: str, note: str = "") -> str:
    note_html = f"<small>{note}</small>" if note else ""
    return f'<label class="catalogue-check"><input id="{control_id}" type="checkbox"><span>{label}{note_html}</span></label>'


def _relative_rows() -> str:
    options = "".join(f'<option value="{key}">{label}</option>' for key, label, _, _ in RELATIONS)
    rows = []
    for index, (key, label, control_id, placeholder) in enumerate(RELATIONS):
        hidden = "" if index == 0 else " hidden"
        rows.append(
            f'<div class="catalogue-relative-row" data-relation="{key}"{hidden}>'
            f'<select id="catalogue-relative-type-{key}" data-relative-select aria-label="Relationship">'
            + options.replace(f'value="{key}"', f'value="{key}" selected') + '</select>'
            f'<label class="catalogue-sr-only" for="{control_id}">{label} name</label>'
            f'<input id="{control_id}" type="search" placeholder="{placeholder}" autocomplete="off">'
            f'<button type="button" class="catalogue-relative-remove" data-relative-remove aria-label="Remove {label.lower()} criterion">Remove</button>'
            '</div>'
        )
    return "".join(rows)


def search_panel_html(cluster_options: str, record_type_options: str, region_options: str) -> str:
    name_panel = (
        '<div class="catalogue-panel-grid">'
        '<label><span>First name(s)</span><input id="catalogue-first-name" type="search" placeholder="e.g. James" autocomplete="off"></label>'
        '<label><span>Last name</span><input id="catalogue-last-name" type="search" placeholder="e.g. Glasgow" autocomplete="off"></label>'
        '<label class="catalogue-panel-wide"><span>Last name matches</span><select id="catalogue-last-scope">'
        '<option value="">Any recorded surname</option><option value="birth">Surname at birth</option>'
        '<option value="current">Current/last surname</option></select></label>'
        '<label class="catalogue-panel-wide"><span>Full name</span><input id="catalogue-name" placeholder="First, last, or both" type="search" autocomplete="off"></label>'
        '</div>'
        '<div class="catalogue-panel-row">'
        '<fieldset class="catalogue-gender-choice"><legend>Gender</legend>'
        '<label title="Any gender, including unrecorded"><input name="catalogue-gender" type="radio" value="both" checked><span>Any</span></label>'
        '<label title="Male"><input name="catalogue-gender" type="radio" value="male" aria-label="Male"><span aria-hidden="true">♂</span></label>'
        '<label title="Female"><input name="catalogue-gender" type="radio" value="female" aria-label="Female"><span aria-hidden="true">♀</span></label>'
        '</fieldset>'
        + '<p class="catalogue-panel-note catalogue-gender-note">Male or Female excludes people with no recorded gender.</p></div>'
        + _check("catalogue-exact-name", "Exact name spelling",
                 "Applies to the main search box: Glasco will not also match Glasgow.")
    )
    relatives_panel = (
        f'<div class="catalogue-relative-rows" id="catalogue-relative-rows">{_relative_rows()}</div>'
        '<button type="button" class="catalogue-add-relative" id="catalogue-add-relative">+ Add relative</button>'
        '<p class="catalogue-panel-note">Each relationship can be used once. People must match every relative entered.</p>'
    )
    dates_panel = (
        '<div class="catalogue-panel-grid catalogue-panel-grid-3">'
        '<label class="catalogue-date-scope"><span>Dates apply to</span><select id="catalogue-date-type"><option value="">Any record</option><option value="birth">Birth</option><option value="death">Death</option></select></label>'
        '<label><span>From year</span><input id="catalogue-date-from" type="number" min="1000" max="2100" placeholder="From"></label>'
        '<label><span>To year</span><input id="catalogue-date-to" type="number" min="1000" max="2100" placeholder="To"></label>'
        '</div><p class="catalogue-panel-note">Either year may be left open. People without a year for the chosen event are excluded.</p>'
    )
    places_panel = (
        '<div class="catalogue-panel-grid">'
        '<label><span>Location applies to</span><select id="catalogue-location-type"><option value="">Any</option><option value="record">Any record</option><option value="birth">Birth</option><option value="marriage">Marriage</option><option value="death">Death</option><option value="bio">Bio</option></select></label>'
        '<label><span>Location</span><input id="catalogue-location" type="search" placeholder="Place name" autocomplete="off"></label>'
        f'<label><span>Country or region</span><select id="catalogue-region"><option value="">Any region</option>{region_options}</select></label>'
        '<label><span>Exclude location</span><input id="catalogue-death-exclude" type="search" placeholder="e.g. USA" autocomplete="off"></label>'
        '</div><p class="catalogue-panel-note">Any searches all recorded places and public biography text. Exclude location uses the same selection; separate places with commas.</p>'
    )
    evidence_panel = (
        '<div class="catalogue-panel-grid catalogue-panel-grid-1">'
        f'<label><span>Possible group</span><select id="catalogue-cluster"><option value="">Any group</option>{cluster_options}</select></label>'
        f'<label><span>Record type</span><select id="catalogue-record-type"><option value="">Any record type</option>{record_type_options}</select></label>'
        f'<label><span>Source quality</span><select id="catalogue-source-quality"><option value="">Any quality</option>{SOURCE_QUALITY_OPTIONS}</select></label>'
        '</div>'
    )
    filters_panel = (
        '<div class="catalogue-check-groups"><div><h4>Surname and marriage</h4>'
        + _check("catalogue-glasgow-at-birth", "Glasgow at birth")
        + _check("catalogue-women-married-glasgow", "Women who married a Glasgow")
        + _check("catalogue-has-suffix", "Has suffix")
        + '</div><div><h4>Family</h4>'
        + _check("catalogue-missing-father", "Missing father")
        + _check("catalogue-missing-mother", "Missing mother")
        + _check("catalogue-has-descendants", "Has descendants")
        + '</div></div>'
    )
    wikitree_panel = (
        '<div class="catalogue-check-groups catalogue-check-groups-1"><div>'
        + _check("catalogue-missing-profile", "No confirmed WikiTree link")
        + _check("catalogue-needs-wikitree-update", "Needs updated on WikiTree")
        + '</div></div>'
        '<div class="catalogue-panel-grid catalogue-panel-grid-1 catalogue-change-filters">'
        '<p class="catalogue-panel-note catalogue-panel-wide">Filter pending relationship amendments by their relationship, action or proposed confidence.</p>'
        '<label><span>Changed relationship</span><select id="catalogue-change-relationship">'
        '<option value="">Any relationship change</option><option value="father">Father</option><option value="mother">Mother</option>'
        '<option value="spouse">Spouse</option><option value="child">Child</option><option value="sibling">Sibling</option></select></label>'
        '<label><span>Relationship change</span><select id="catalogue-change-action">'
        '<option value="">Any change</option><option value="topology">New / replaced relative</option><option value="add">New relationship</option><option value="replace">Replaced relationship</option>'
        '<option value="regrade">Confidence changed</option></select></label>'
        '<label><span>New confidence</span><select id="catalogue-change-confidence">'
        '<option value="">Any confidence</option><option value="confident">Confident ·90–99%</option><option value="probable">Probable ·60–89%</option>'
        '<option value="possible">Possible ·30–59%</option><option value="uncertain">Speculative / uncertain ·1–29%</option><option value="unrated">Unrated</option></select></label>'
        '</div>'
    )
    panels = "".join((
        _panel("name", "Name", name_panel, "is-wide"),
        _panel("relatives", "Relatives", relatives_panel, "is-wide"),
        _panel("dates", "Dates", dates_panel, "is-wide"),
        _panel("places", "Places", places_panel, "is-wide"),
        _panel("evidence", "Evidence", evidence_panel),
        _panel("filters", "Filters", filters_panel, "is-wide"),
        _panel("wikitree", "WikiTree", wikitree_panel),
    ))
    return (
        '<section class="catalogue-search-panel catalogue-toolbar-layout" id="catalogue-search-panel" aria-label="Search the research catalogue" aria-busy="true">\n'
        '<form class="catalogue-search is-loading" id="catalogue-search" role="search" aria-label="Research catalogue">\n'
        '<div class="catalogue-query-row"><label class="catalogue-sr-only" for="catalogue-query">Name, WikiTree ID or any detail</label>'
        '<svg aria-hidden="true" viewBox="0 0 20 20" width="18" height="18"><circle cx="8.5" cy="8.5" r="5.5" fill="none" stroke="currentColor" stroke-width="1.7"/><path d="m13 13 4.5 4.5" stroke="currentColor" stroke-width="1.7"/></svg>'
        '<input id="catalogue-query" type="search" placeholder="Search names, WikiTree IDs or any detail (e.g. James Glasgow, Glasgow-1022, Antrim, 1830)" autocomplete="off">'
        '<button type="submit">Search</button></div>\n'
        f'<div class="catalogue-filter-bar" id="catalogue-filters" role="group" aria-label="Filter results">{panels}</div>\n'
        '<div class="catalogue-filter-backdrop" hidden></div>\n'
        '</form>\n'
        '<div class="catalogue-applied" id="catalogue-applied"><h2 class="catalogue-sr-only" id="catalogue-applied-title">Applied filters</h2>'
        '<span class="catalogue-applied-label" aria-hidden="true">Applied:</span><ul class="catalogue-applied-list" id="catalogue-applied-list" aria-labelledby="catalogue-applied-title"></ul>'
        '<button id="catalogue-search-clear" class="catalogue-clear catalogue-clear-all" type="button" disabled>Clear all</button>'
        '<div class="catalogue-results-summary"><p id="catalogue-results-count" class="catalogue-status" data-state="busy" aria-live="polite">Loading searchable index…</p>'
        '<button id="catalogue-view-results" class="catalogue-view-results" type="button" hidden>View results</button></div></div>'
        '</section>'
    )


def _select_options(page: str, select_id: str) -> str:
    match = re.search(rf'<select id="{select_id}">(.*?)</select>', page, flags=re.S)
    if not match:
        raise ValueError(f"{select_id} not found")
    options = re.sub(r'^<option value="">[^<]*</option>', "", match.group(1))
    # Normalise serialiser differences so repeated runs are stable.
    return re.sub(r'<option value="([^"]*)">([^<]*)</option>', lambda m: f'<option value="{m[1]}">{m[2]}</option>', options)


def _statistics_section(page: str):
    # The old pane contains nested sections; the compact summary does not.
    compact = re.search(r'<section\b(?=[^>]*\bid="statistics")(?=[^>]*\bclass="[^"]*\bcatalogue-statistics-compact\b)[^>]*>.*?</section>', page, re.S)
    return compact or re.search(r'<section\b(?=[^>]*\bid="statistics")[^>]*>.*?</details>(?:\s*</details>)?\s*</section>', page, re.S)


def place_statistics_above_search(page: str) -> str:
    """Compatibility entry point: put statistics after the browsing content."""
    stats = _statistics_section(page)
    if not stats or '</main>' not in page:
        return page
    block = stats.group(0)
    page = page[:stats.start()] + page[stats.end():]
    return page.replace('</main>', block + '\n</main>', 1)


def compact_statistics(page: str) -> str:
    """Keep the summary available without delaying the search controls."""
    block = _statistics_section(page)
    if not block:
        return page
    summary = re.search(r'<div class="statistics-summary">.*?</div>\s*</div>', block[0], re.S)
    refreshed = re.search(r'<p class="catalogue-refresh">.*?</p>', block[0], re.S)
    if not summary:
        raise ValueError('Catalogue statistics summary missing')
    compact = (
        '<section id="statistics" class="catalogue-statistics catalogue-statistics-compact" aria-labelledby="catalogue-statistics-title">'
        '<div class="catalogue-statistics-heading"><div><h2 id="catalogue-statistics-title">Catalogue statistics</h2>'
        + (refreshed[0] if refreshed else '') + '</div>'
        '<a class="catalogue-statistics-link" href="/statistics/">View all statistics →</a></div>'
        + '<details class="catalogue-statistics-fold"><summary>Show catalogue statistics</summary>' + summary[0] + '</details></section>'
    )
    return page[:block.start()] + compact + page[block.end():]


def apply_layout(page: str) -> str:
    """Replace the hero and search panel of a generated catalogue page."""
    hero = re.search(r'<section class="catalogue-hero[^"]*">.*?</section>', page, flags=re.S)
    panel_start = page.rfind('<section', 0, page.index('id="catalogue-search-panel"'))
    panel_end = page.index('</section>', page.index('id="catalogue-search-clear"')) + len('</section>')
    if not hero:
        raise ValueError("catalogue hero not found")
    panel = page[panel_start:panel_end]
    options = {key: _select_options(panel, key) for key in ("catalogue-cluster", "catalogue-record-type", "catalogue-region")}
    total = int(re.search(r'Search ([\d,]+) historical people', hero.group(0)).group(1).replace(",", ""))
    new_panel = search_panel_html(options["catalogue-cluster"], options["catalogue-record-type"], options["catalogue-region"])
    page = page[:panel_start] + new_panel + page[panel_end:]
    page = page.replace(hero.group(0), hero_html(total), 1)
    page = place_statistics_above_search(page)
    page = compact_statistics(page)
    page = page.replace('Open significance-ranked table', 'Open priority-ranked table')
    page = page.replace('profiles ranked by significance, with', 'profiles ranked by update priority, with')
    # The evidence legend follows the shared vocabulary (tools/evidence_labels.py).
    try:
        from build_research_catalog import _catalogue_legend_html
    except ModuleNotFoundError:
        from tools.build_research_catalog import _catalogue_legend_html
    page = re.sub(r'<section class="catalogue-legend">.*?</section>', lambda _: _catalogue_legend_html(), page, count=1, flags=re.S)
    # Start downloading the search index with the page, not after the script runs.
    page = re.sub(r'<link\b(?=[^>]*rel="preload")(?=[^>]*href="[^"]*catalogue-search-(?:index|fast)\.json[^"]*")[^>]*>', '', page)
    preloads = (
        '<link rel="preload" href="/data/catalogue-search-fast.json?v=1" as="fetch" crossorigin="anonymous">',
    )
    missing_preloads = ''.join(preload for preload in preloads if preload.split(' href="', 1)[1].split('"', 1)[0] not in page)
    if missing_preloads:
        page = page.replace("</head>", missing_preloads + "</head>", 1)
    # New markup needs the matching script and stylesheet, not a cached copy.
    return re.sub(r'(people/(?:search\.js|catalogue\.css)\?v=)[^"\'\s<>]+', lambda m: m[1] + CATALOGUE_ASSET_VERSION, page)


def main() -> None:
    for relative in PAGES:
        path = WEB / relative
        original = path.read_text(encoding="utf-8")
        updated = apply_layout(original)
        if updated != original:
            path.write_text(updated, encoding="utf-8")
            print(f"updated {relative}")


if __name__ == "__main__":
    main()
