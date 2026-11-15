"""Generations story derived only from public historical catalogue rows."""
from __future__ import annotations

from html import escape

try:
    from tools.statistics_overview import birth_bins
except ModuleNotFoundError:
    from statistics_overview import birth_bins

GENDERS = ("Male", "Female", "Unknown")
COLORS = {"Male": "#52796a", "Female": "#c79252", "Unknown": "#b9b5a7"}


def _composition(counts, by_gender):
    """Use one absolute scale, retaining every intervening empty century."""
    if not counts:
        return '<p class="statistics-generations-empty">No usable recorded birth years are available for a century comparison.</p>'
    centuries = range(min(counts), max(counts) + 1)
    maximum = max(counts.values())
    height = 42 + len(centuries) * 48
    svg = [
        f'<svg class="statistics-generations-gender-chart" viewBox="0 0 800 {height}" role="img" aria-labelledby="generations-composition-title generations-composition-desc">',
        '<title id="generations-composition-title">Recorded gender by birth century</title>',
        '<desc id="generations-composition-desc">Stacked bands use a shared count scale. Every century between the earliest and latest recorded birth year is shown, including empty centuries. Counts are Male, Female and Unknown as recorded in the public catalogue.</desc>',
        '<text x="105" y="17" font-size="11" fill="currentColor">People · same scale for every century</text>',
    ]
    for index, century in enumerate(centuries):
        y = 34 + index * 48
        total = counts[century]
        label = f"{century * 100}s"
        svg.append(
            f'<g class="statistics-generations-century" data-century="{century}" data-total="{total}">'
            f'<text class="statistics-generations-century-label" x="0" y="{y + 20}" font-size="13" fill="currentColor">{label}</text>'
            f'<rect x="105" y="{y}" width="570" height="29" rx="3" fill="currentColor" fill-opacity=".055"/>'
        )
        offset = 105.0
        for gender in GENDERS:
            count = by_gender[gender][century]
            width = 570 * count / maximum
            svg.append(
                f'<rect class="statistics-generations-{gender.lower()}" data-count="{count}" data-gender="{gender}" '
                f'x="{offset:.6f}" y="{y}" width="{width:.6f}" height="29" fill="{COLORS[gender]}">'
                f'<title>{label}: {gender} {count:,}; century total {total:,}</title></rect>'
            )
            if width >= 30:
                svg.append(f'<text x="{offset + width / 2:.3f}" y="{y + 19}" text-anchor="middle" font-size="12" fill="#fff">{count:,}</text>')
            offset += width
        svg.append(
            f'<text class="statistics-generations-century-total" x="690" y="{y + 19}" font-size="13" fill="currentColor">{total:,}</text>'
            '</g>'
        )
    svg.append('</svg>')
    # Visible exact values also cover segments too small to carry a label.
    rows = ''.join(
        f'<tr><th scope="row">{century * 100}s</th>' +
        ''.join(f'<td>{by_gender[gender][century]:,}</td>' for gender in GENDERS) +
        f'<td>{counts[century]:,}</td></tr>' for century in centuries
    )
    return ''.join(svg) + (
        '<details class="statistics-generations-values"><summary>Exact counts by century</summary>'
        '<div class="statistics-generations-table-wrap"><table><thead><tr><th scope="col">Birth century</th>'
        '<th scope="col">Male</th><th scope="col">Female</th><th scope="col">Unknown</th><th scope="col">Total</th>'
        '</tr></thead><tbody>' + rows + '</tbody></table></div></details>'
    )


def render_generations_story(people, chart_html=''):
    """Render date coverage and century composition without changing chart_html.

    Dated means a first shown four-digit birth year accepted by birth_bins,
    including estimates, bounds and ranges. It does not imply an exact date.
    """
    public = [person for person in (people or []) if not person.get("likely_living")]
    counts = birth_bins(public)
    total, dated = len(public), sum(counts.values())
    undated = total - dated
    coverage = dated / total * 100 if total else 0
    missing = undated / total * 100 if total else 0
    by_gender = {
        gender: birth_bins([
            person for person in public
            if (person.get("gender") if person.get("gender") in GENDERS[:2] else "Unknown") == gender
        ]) for gender in GENDERS
    }
    if counts:
        peak = min(counts, key=lambda century: (-counts[century], century))
        peak_count = counts[peak]
        peak_share = peak_count / dated * 100
        headline = f"A catalogue shaped by the {peak * 100}s."
        peak_metric = f'<strong>{peak_share:.1f}%</strong><span>of dated people in the {peak * 100}s</span>'
        interpretation = (
            f'The {peak * 100}s are the largest birth-century group: {peak_count:,} of {dated:,} dated people. '
            'This is the shape of the catalogue, rather than a historical population estimate.'
        )
    else:
        headline = "Generations, waiting for dates."
        peak_metric = '<strong>—</strong><span>No dated century group</span>'
        interpretation = 'A century comparison will appear when usable recorded birth years are available.'
    chart = chart_html or '<p class="statistics-generations-empty">No birth-century chart is available.</p>'
    legend = ''.join(
        f'<span><i class="statistics-generations-{gender.lower()}" aria-hidden="true" style="background:{COLORS[gender]}"></i>{gender}</span>'
        for gender in GENDERS
    )
    return (
        '<section class="statistics-generations" aria-label="Generations in the public historical catalogue">'
        '<div class="statistics-story-hero statistics-generations-hero">'
        '<div class="statistics-story-copy statistics-generations-copy">'
        '<span class="statistics-story-eyebrow">Across generations</span>'
        f'<h2>{escape(headline)}</h2>'
        '<p>Follow recorded birth years through the centuries, then see whose dates are still missing.</p>'
        '<div class="statistics-story-metrics statistics-generations-metrics">'
        f'<div data-metric="dated"><strong>{dated:,}</strong><span>people with a usable birth year</span></div>'
        f'<div data-metric="public"><strong>{total:,}</strong><span>public historical people</span></div>'
        f'<div data-metric="peak">{peak_metric}</div></div>'
        f'<p class="statistics-story-caption">{interpretation}</p></div>'
        f'<div class="statistics-generations-chart">{chart}</div></div>'
        '<section class="statistics-generations-composition" aria-labelledby="generations-composition-heading">'
        '<div class="statistics-generations-section-head"><div>'
        '<span class="statistics-story-eyebrow">Inside each century</span>'
        '<h3 id="generations-composition-heading">Who makes up the generations?</h3>'
        '<p>Recorded gender within each birth-century group, on a shared count scale.</p>'
        f'</div><div class="statistics-generations-legend" aria-label="Recorded gender">{legend}</div></div>'
        + '<div class="statistics-generations-gender-scroll">' + _composition(counts, by_gender) + '</div>' +
        '<p class="statistics-story-caption">Male and Female follow the maintained catalogue classifications. '
        'Every other or missing value is grouped as Unknown.</p></section>'
        '<section class="statistics-generations-coverage" aria-labelledby="generations-coverage-heading">'
        '<div class="statistics-generations-section-head"><div>'
        '<span class="statistics-story-eyebrow">The dates behind the story</span>'
        '<h3 id="generations-coverage-heading">How much of the catalogue can we place in time?</h3></div>'
        f'<strong class="statistics-generations-coverage-percent">{coverage:.1f}%<span>with a usable birth year</span></strong></div>'
        f'<div class="statistics-generations-rail" role="img" aria-label="{dated:,} dated and {undated:,} without a usable birth year, out of {total:,} public historical people">'
        f'<span class="statistics-generations-dated" data-count="{dated}" style="width:{coverage:.10f}%"></span>'
        f'<span class="statistics-generations-undated" data-count="{undated}" style="width:{missing:.10f}%"></span></div>'
        '<div class="statistics-generations-coverage-labels">'
        f'<span><strong>{dated:,}</strong> with a usable birth year</span>'
        f'<span><strong>{undated:,}</strong> without a usable birth year</span></div>'
        '<p class="statistics-story-caption">Date coverage measures whether a person can be grouped by birth year. '
        'It does not measure research confidence or the certainty of a date.</p></section>'
        '<details class="statistics-generations-method"><summary>How these generations are counted</summary>'
        '<p>All figures use public historical catalogue rows and exclude people marked likely living. '
        'The first shown four-digit birth year from 1000 through 2099 determines the hundred-year group '
        '(1800–1899 is labelled 1800s). Estimates and dates marked before or after are included; '
        'ranges use their first shown year. A missing or unrecognised year remains in the public total but '
        'is excluded from century groups. Empty intervening centuries are retained. '
        'Peak-century percentages use dated people; coverage percentages use all public historical people. '
        'Equal peak counts select the earliest century. These groups describe recorded births, not '
        'parent–child generations or a reconstruction of population size.</p></details></section>'
    )
