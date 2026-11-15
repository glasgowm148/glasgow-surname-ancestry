"""Server-rendered statistical overview using only published historical data.

render_dashboard_overview() is deterministic and performs no I/O when an outline
is supplied. load_world_outline() reads the existing public coordinate asset;
passing [] instead produces an explicitly labelled geographic dot plot.
Map cells count each person once; circle area is proportional to that count.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from html import escape
import json
import math
from pathlib import Path
import re

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]


def load_world_outline(web_root: Path | None = None) -> list:
    """Read the maintained public land polygons; missing/invalid files mean no land."""
    path = (web_root or ROOT / "www") / "assets/research/world.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (OSError, ValueError):
        return []


def _coordinate(value, limit):
    if isinstance(value, bool):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) and abs(result) <= limit else None


def record_cells(people: list[dict], max_cells: int = 500) -> tuple[list[dict], int]:
    """Return bounded 5° (or coarser) cells and unique mapped-person count.

    Person/coordinate duplicates are removed before aggregation. Every cell
    counts unique people, so a person may appear in more than one cell.
    Longitude 180 is retained at the eastern edge rather than wrapping west.
    """
    coordinates = defaultdict(set)
    for index, person in enumerate(people):
        if person.get("likely_living"):
            continue
        key = person.get("catalogue_id") or person.get("map_key") or str(index)
        for record in person.get("records") or []:
            lat = _coordinate(record.get("latitude"), 90)
            lon = _coordinate(record.get("longitude"), 180)
            if lat is not None and lon is not None:
                coordinates[(lon, lat)].add(str(key))
    if not coordinates:
        return [], 0
    step = 5
    while True:
        grouped = defaultdict(set)
        for (lon, lat), members in coordinates.items():
            x = min(math.floor((lon + 180) / step), math.ceil(360 / step) - 1)
            y = min(math.floor((lat + 90) / step), math.ceil(180 / step) - 1)
            grouped[(x, y)].update(members)
        if len(grouped) <= max(1, max_cells):
            break
        step *= 2
    cells = [{"longitude": min(180, -180 + (x + 0.5) * step),
              "latitude": min(90, -90 + (y + 0.5) * step),
              "count": len(members), "degrees": step}
             for (x, y), members in sorted(grouped.items())]
    mapped = len(set().union(*coordinates.values()))
    return cells, mapped


def _project(longitude, latitude):
    return 22 + (longitude + 180) / 360 * 676, 22 + (90 - latitude) / 180 * 306


def _rings(value):
    if not isinstance(value, list) or not value:
        return
    if isinstance(value[0], list) and len(value[0]) >= 2 and isinstance(value[0][0], (int, float)):
        yield value
    else:
        for child in value:
            yield from _rings(child)


def _land_path(outline):
    segments = []
    for ring in _rings(outline):
        previous = None
        for coordinate in ring:
            lon = _coordinate(coordinate[0], 180)
            lat = _coordinate(coordinate[1], 90)
            if lon is None or lat is None:
                previous = None
                continue
            x, y = _project(lon, lat)
            command = "M" if previous is None or abs(x - previous) > 338 else "L"
            segments.append(f"{command}{x:.1f},{y:.1f}")
            previous = x
    return " ".join(segments)


def _footprint(people, outline):
    cells, mapped = record_cells(people)
    land = _land_path(outline)
    svg = ['<svg class="statistics-footprint-map" viewBox="0 0 720 350" role="img" aria-label="World footprint of mapped record associations">',
           '<title>Mapped record associations, including approximate location pins</title>']
    for lon in range(-180, 181, 60):
        x, _ = _project(lon, 0)
        svg.append(f'<path class="statistics-map-grid" d="M{x:.1f},22V328" fill="none" stroke="#ffffff" stroke-opacity=".12"/>')
    for lat in (-60, -30, 0, 30, 60):
        _, y = _project(0, lat)
        svg.append(f'<path class="statistics-map-grid" d="M22,{y:.1f}H698" fill="none" stroke="#ffffff" stroke-opacity=".12"/>')
    if land:
        svg.append(f'<path class="statistics-map-land" d="{land}" fill="#426858" fill-opacity=".75" stroke="#a9c6b4" stroke-opacity=".35" stroke-width=".55"/>')
    for cell in sorted(cells, key=lambda row: -row["count"]):
        x, y = _project(cell["longitude"], cell["latitude"])
        radius = 1.35 * math.sqrt(cell["count"])
        # No minimum/maximum radius: circle areas retain the exact count ratio.
        label = (f'{cell["count"]:,} people with records in this {cell["degrees"]}° coordinate cell; '
                 f'cell centre {cell["latitude"]:g}°, {cell["longitude"]:g}°. Pins may be approximate.')
        svg.append(f'<circle class="statistics-map-dot" cx="{x:.2f}" cy="{y:.2f}" r="{radius:.3f}" fill="#dfb77b" fill-opacity=".5" stroke="#f4d9ae" stroke-opacity=".8" stroke-width=".65"><title>{escape(label)}</title></circle>')
    svg.append('</svg>')
    label = "Mapped record footprint" if land else "Geographic dot plot · no land outline available"
    caption = (f'{mapped:,} people with mapped record associations. Circle area shows people per geographic cell; '
               'a person may appear in several cells. Pins include approximate and country-centre locations.')
    return '<figure class="statistics-atlas-figure"><figcaption class="statistics-map-heading">' + label + '</figcaption>' + ''.join(svg) + '<p class="statistics-map-caption">' + caption + '</p></figure>'


def birth_bins(people: list[dict]) -> Counter:
    """Match maintained hundred-year groups using the first shown birth year.

    Approximate/bounded dates and ranges use their first recorded four-digit
    year. This is a presentation grouping, not a new date assessment.
    """
    counts = Counter()
    for person in people:
        if person.get("likely_living"):
            continue
        match = re.search(r"\b(?:1[0-9]|20)\d{2}\b", str(person.get("birth") or ""))
        if match:
            counts[int(match.group()) // 100] += 1
    return counts


def _histogram(people):
    counts = birth_bins(people)
    total = sum(counts.values())
    svg = ['<svg class="statistics-era-histogram" viewBox="0 0 480 185" role="img" aria-label="Recorded birth years by hundred-year group">']
    if counts:
        bins = list(range(min(counts), max(counts) + 1))
        maximum = max(counts.values())
        step = 440 / len(bins)
        svg.append('<path d="M20,139H460" stroke="currentColor" stroke-opacity=".18"/>')
        for index, century in enumerate(bins):
            count = counts[century]
            x = 20 + (index + .5) * step
            height = count / maximum * 103
            label = f'{century * 100}s'
            svg.append(f'<rect class="statistics-era-column" x="{x-step*.31:.2f}" y="{139-height:.2f}" width="{step*.62:.2f}" height="{height:.2f}" rx="3" fill="#b78049"><title>{label}: {count:,} people</title></rect>')
            svg.append(f'<text class="statistics-era-count" x="{x:.2f}" y="{max(22,132-height):.2f}" text-anchor="middle" font-size="10">{count:,}</text>')
            svg.append(f'<text class="statistics-era-label" x="{x:.2f}" y="160" text-anchor="middle" font-size="10">{label}</text>')
    else:
        svg.append('<text x="240" y="95" text-anchor="middle">No usable recorded birth years</text>')
    svg.append('</svg>')
    return ('<article class="statistics-era-card"><span class="statistics-overview-eyebrow">Through time</span>'
            '<h3>Birth years across the centuries</h3>' + ''.join(svg) +
            f'<p class="statistics-overview-caption">{total:,} dated people. First shown birth year, including estimates and bounds; '
            'ranges use their first year. Undated people are omitted; empty periods remain visible.</p></article>')


def _coverage(people, search_index):
    public_ids = {str(p.get("catalogue_id") or p.get("map_key") or index).casefold()
                  for index, p in enumerate(people) if not p.get("likely_living")}
    # Search index rows are the published, per-person root assignments.
    rows = search_index.get("people", []) if isinstance(search_index, dict) else search_index
    assigned = {str(row.get("catalogue_id") or row.get("id") or row.get("map_key") or index).casefold()
                for index, row in enumerate(rows or [])
                if row.get("family_root") and not row.get("likely_living")}
    total = len(public_ids)
    linked = len(assigned & public_ids)
    fraction = linked / total if total else 0
    circumference = 2 * math.pi * 55
    svg = (f'<svg class="statistics-coverage-ring" viewBox="0 0 190 170" role="img" aria-label="{linked:,} of {total:,} people have an exported family-root assignment">'
           '<circle cx="95" cy="78" r="55" fill="none" stroke="#e2e8df" stroke-width="13"/>'
           f'<circle class="statistics-coverage-arc" cx="95" cy="78" r="55" fill="none" stroke="#426f58" stroke-width="13" transform="rotate(-90 95 78)" stroke-dasharray="{fraction*circumference:.5f} {circumference:.5f}"/>'
           f'<text class="statistics-coverage-percent" x="95" y="78" dy=".2em" text-anchor="middle" font-size="29" font-weight="650">{fraction:.1%}</text>'
           '<text x="95" y="99" text-anchor="middle" font-size="10">assigned to a root</text></svg>')
    return ('<article class="statistics-coverage-card"><span class="statistics-overview-eyebrow">Connections</span>'
            '<h3>Family-tree coverage</h3><div class="statistics-coverage-body">' + svg +
            f'<div><strong class="statistics-coverage-total">{linked:,} / {total:,}</strong><p>people assigned to an exported family root</p></div></div>'
            '<p class="statistics-overview-caption">Coverage of recorded tree links, not research confidence or proof of a single family tree.</p></article>')


def render_dashboard_overview(summary_html: str, people: list[dict], search_index, *, outline=None, web_root: Path | None = None) -> str:
    """Render hero, coordinate footprint, timeline and exact root coverage.

    The hero numbers come verbatim from summary_html. Every source total is
    preserved in a collapsed details block. Supply outline=[] for deterministic
    no-map tests, or nested public coordinate rings to render local geography.
    """
    soup = BeautifulSoup(summary_html, "html.parser")
    summary = soup.select_one(".statistics-summary") or soup
    metrics = []
    for block in summary.find_all("div", recursive=False):
        value, label = block.find("strong"), block.find("span")
        if value and label:
            metrics.append((value.get_text(" ", strip=True), label.get_text(" ", strip=True)))
    preferred = ["Historical people", "Mapped records", "Mapped places", "Recorded journeys", "Cross-region life courses"]
    chosen = []
    for target in preferred:
        chosen.extend((value, label) for value, label in metrics if label == target)
        if len(chosen) >= 4:
            break
    if not chosen:
        chosen = metrics[:4]
    numbers = ''.join(f'<div><strong>{escape(value)}</strong><span>{escape("Recorded journeys" if label == "Cross-region life courses" else label)}</span></div>' for value, label in chosen)
    if outline is None:
        outline = load_world_outline(web_root)
    return ('<section class="statistics-overview" aria-label="Catalogue overview">'
            '<div class="statistics-atlas-hero"><div class="statistics-atlas-copy">'
            '<span class="statistics-overview-eyebrow">A surname, across the world</span>'
            '<h2>Glasgow, by<br>the numbers.</h2>'
            '<p>Explore the people, places and recorded connections in the public historical catalogue.</p>'
            '<div class="statistics-atlas-metrics">' + numbers + '</div></div>' +
            _footprint(people, outline) + '</div><div class="statistics-overview-grid">' +
            _histogram(people) + _coverage(people, search_index) + '</div>'
            '<details class="statistics-overview-totals"><summary>All catalogue totals</summary>' +
            summary_html + '</details></section>')
