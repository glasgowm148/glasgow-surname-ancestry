"""Journey story: exact public birth/death-region counts and schematic geography."""
from collections import Counter
from html import escape
from pathlib import Path

try:
    from tools.statistics_overview import _land_path, _project, load_world_outline
except ModuleNotFoundError:
    from statistics_overview import _land_path, _project, load_world_outline

# Same broad-region centres used by sync_onetree_ireland_uk_to_1900.py.
# These locate schematic endpoint symbols, never a person's exact locality.
CENTRES = {
    'Ireland': (53.42, -7.94), 'Scotland': (56.49, -4.2),
    'England': (52.7, -1.5), 'Wales': (52.3, -3.7),
    'United States': (39.5, -98.35), 'Canada': (56.13, -106.35),
    'Australia': (-25.27, 133.78), 'New Zealand': (-41.2, 174.7),
}


def normalise_flows(rows):
    counts = Counter()
    for row in rows or []:
        if not isinstance(row, (list, tuple)) or len(row) != 3:
            continue
        origin, destination, count = row
        if (not isinstance(origin, str) or not isinstance(destination, str)
                or type(count) is not int or count <= 0 or origin == destination):
            continue
        counts[(origin, destination)] += count
    return [(a, b, count) for (a, b), count in
            sorted(counts.items(), key=lambda item: (-item[1], item[0]))]


def _journey_map(rows, outline):
    shown = [row for row in rows if row[0] in CENTRES and row[1] in CENTRES][:6]
    svg = ['<svg class="statistics-journeys-map" viewBox="0 0 720 350" role="group" aria-label="Schematic map of the six largest mappable birth and death region pairs">',
           '<title>Recorded birth-to-death region connections; arcs are not travel routes</title>']
    land = _land_path(outline)
    if land:
        svg.append('<path class="statistics-journeys-land" d="' + land + '"/>')
    maximum = max((row[2] for row in shown), default=1)
    nodes = set()
    for origin, destination, count in reversed(shown):
        lat1, lon1 = CENTRES[origin]
        lat2, lon2 = CENTRES[destination]
        x1, y1 = _project(lon1, lat1)
        x2, y2 = _project(lon2, lat2)
        control_y = min(y1, y2) - min(75, 25 + abs(x2-x1) * .12)
        caption = f'{origin} → {destination}: {count:,} people'
        svg.append(
            f'<path class="statistics-journeys-arc" d="M{x1:.2f},{y1:.2f} Q{(x1+x2)/2:.2f},{control_y:.2f} {x2:.2f},{y2:.2f}" '
            f'fill="none" stroke-width="{5*count/maximum:.6f}" tabindex="0" role="img" aria-label="{escape(caption, quote=True)}">'
            f'<title>{escape(caption)}</title></path>')
        nodes.update((origin, destination))
    offsets = {'Ireland': (-12, 19), 'Canada': (-18, -15), 'United States': (-18, 24),
               'Australia': (-8, 24), 'New Zealand': (-28, 24)}
    for name in sorted(nodes):
        lat, lon = CENTRES[name]
        x, y = _project(lon, lat)
        svg.append(f'<circle class="statistics-journeys-node" cx="{x:.2f}" cy="{y:.2f}" r="3.6"><title>{escape(name)}</title></circle>')
        if name in offsets:
            dx, dy = offsets[name]
            svg.append(f'<text class="statistics-journeys-map-label" x="{x+dx:.2f}" y="{y+dy:.2f}" text-anchor="middle">{escape(name)}</text>')
    if not shown:
        svg.append('<text x="360" y="175" text-anchor="middle" fill="currentColor">No mappable region pairs</text>')
    svg.append('</svg>')
    return ('<figure class="statistics-journeys-geography"><figcaption>The largest recorded connections</figcaption>' +
            ''.join(svg) + '<p class="statistics-story-caption">Up to six leading connections at broad regional centres. '
            'Arcs are schematic birth/death links, not reconstructed travel routes.</p></figure>')


def _corridors(rows, total):
    if not rows:
        return '<p>No regional connections are recorded.</p>'
    maximum = rows[0][2]
    items = []
    for origin, destination, count in rows[:5]:
        share = count / total * 100
        items.append(
            '<li class="statistics-journeys-corridor" data-count="' + str(count) + '">'
            '<div class="statistics-journeys-corridor-label"><span>' + escape(origin) +
            ' <i aria-hidden="true">→</i> ' + escape(destination) + '</span><strong>' +
            f'{count:,}' + '</strong><small>' + f'{share:.1f}% of recorded journeys' +
            '</small></div><div class="statistics-journeys-track" aria-hidden="true"><i style="width:' +
            f'{count/maximum*100:.8f}%' + '"></i></div></li>')
    return '<ol class="statistics-journeys-corridors">' + ''.join(items) + '</ol>'


def render_journeys_story(flows, chart_html='', *, outline=None, web_root=None):
    rows = normalise_flows(flows)
    total = sum(row[2] for row in rows)
    origins = Counter()
    destinations = Counter()
    for origin, destination, count in rows:
        origins[origin] += count
        destinations[destination] += count
    largest = rows[0] if rows else None
    if outline is None:
        outline = load_world_outline(web_root)
    metrics = [
        (f'{total:,}', 'people with different birth and death regions'),
        (str(len(rows)), 'recorded regional connections'),
        (f'{largest[2]/total:.1%}' if largest else '—', 'in the leading connection'),
    ]
    numbers = ''.join('<div><strong>' + value + '</strong><span>' + label + '</span></div>'
                      for value, label in metrics)
    def leader(counter):
        if not counter:
            return '<strong>—</strong><span>No recorded region</span>'
        name, count = counter.most_common(1)[0]
        return '<strong>' + escape(name) + '</strong><span>' + f'{count:,}' + ' people</span>'
    return (
        '<section class="statistics-journeys-story" aria-label="Recorded journeys">'
        '<div class="statistics-story-hero statistics-journeys-hero"><div class="statistics-story-copy">'
        '<span class="statistics-story-eyebrow">Across borders</span>'
        '<h2>Journeys across<br>the globe.</h2>'
        '<p>Follow broad birth and death regions recorded for the same people.</p>'
        '<div class="statistics-story-metrics">' + numbers + '</div></div>' +
        _journey_map(rows, outline) + '</div>'
        '<section class="statistics-journeys-flow-section"><div class="statistics-story-section-head">'
        '<div><span class="statistics-story-eyebrow">The complete picture</span>'
        '<h3>How the regions connect</h3><p>Every recorded regional pair, with widths scaled to the number of people.</p></div>'
        '<span class="statistics-story-badge">' + f'{total:,}' + ' people · ' + str(len(rows)) + ' pairs</span></div>' +
        chart_html + '</section>'
        '<div class="statistics-journeys-detail-grid"><section class="statistics-journeys-leading">'
        '<span class="statistics-story-eyebrow">The leading corridors</span><h3>Five connections, in focus</h3>' +
        _corridors(rows, total) + '<p class="statistics-story-caption">Each person belongs to one recorded birth/death pair. '
        'These bars compare the five largest pairs on a common count scale.</p></section>'
        '<aside class="statistics-journeys-endpoints"><span class="statistics-story-eyebrow">At either end</span>'
        '<div><span class="statistics-journeys-endpoint-label">Most common birth region</span>' +
        leader(origins) + '</div><div><span class="statistics-journeys-endpoint-label">Most common death region</span>' +
        leader(destinations) + '</div><p class="statistics-story-caption">Figures describe catalogue endpoints. '
        'Intermediate moves and routes are not inferred.</p></aside></div></section>'
    )
