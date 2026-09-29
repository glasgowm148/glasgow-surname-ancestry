#!/usr/bin/env python3
"""Build static, evidence-led study narratives inside the existing site shell."""
from collections import Counter
from html import escape
from pathlib import Path
from urllib.parse import urlsplit
import csv
import json
import math
import re
import runpy
import sys
import textwrap

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / 'www'
STORIES = ROOT / 'tools/study_stories'
sys.path.insert(0, str(ROOT / 'tools'))
import evidence_labels  # noqa: E402  (shared public vocabulary)

# Study tone keys are unchanged; their public words come from the shared vocabulary.
TONES = {key: value['label'] for key, value in evidence_labels.STUDY_TONES.items()}
EVIDENCE_CSS = f'/assets/research/evidence.css?v={evidence_labels.VERSION}'
GUIDE = (f'<p class="sp-caption sp-keep evidence-guide-link"><a href="{evidence_labels.GUIDE_URL}">{evidence_labels.GUIDE_LABEL}</a>'
         '<span> What each label means, and why a research cluster does not prove kinship.</span></p>')


def esc(value):
    return escape(str(value if value is not None else ''), quote=True)


def safe_url(value):
    value = str(value or '').strip()
    if any(ord(c) < 32 for c in value) or '\\' in value:
        return ''
    try: p = urlsplit(value)
    except ValueError: return ''
    return value if p.scheme in ('https', 'http') or (not p.scheme and value.startswith(('/', '#')) and not value.startswith('//')) else ''


def link(label, url):
    url = safe_url(url)
    return f'<a href="{esc(url)}">{esc(label)}</a>' if url else esc(label)


def inline(value):
    value = str(value or '')
    parts, pos = [], 0
    for m in re.finditer(r'\[([^\]\n]+)\]\(([^\s)]+)\)|\*\*([^*]+)\*\*', value):
        parts.extend([esc(value[pos:m.start()]), link(m[1], m[2]) if m[1] else '<strong>'+esc(m[3])+'</strong>'])
        pos = m.end()
    return ''.join(parts)+esc(value[pos:])


def tone(value):
    return value if isinstance(value, str) and value in TONES else 'unresolved'


def year(value):
    try:
        n = float(value)
        return int(n) if math.isfinite(n) else None
    except (ValueError, TypeError, OverflowError):
        return None


def record_tone(row):
    """Colour source occurrences, never infer the strength of a relationship."""
    evidence = row.get('evidence', '').lower()
    source = row.get('source_status', '').lower()
    if 'original' in source and 'inspected' in source and 'not' not in source:
        return 'proved'
    if evidence.startswith('documented'):
        return 'supported'
    if evidence in ('probable', 'possible'):
        return 'hypothesis'
    return 'unresolved'


def section(key, title, body):
    return f'<section id="study-{key}" class="sp-section"><h2>{esc(title)}</h2>{body}</section>'


def person(slug, registry, dates=False):
    p = registry.get(slug, {})
    return link(p.get('name', slug), f'/people/{slug}.html')+(f'<small>{esc(p.get("life", "Dates not recorded"))}</small>' if dates else '')


def fallback(branch, group, families):
    boundary = group.get('boundary') or branch.get('membershipBasis') or 'Shared places and surnames do not establish kinship. Consult individual evidence before joining families.'
    answer = group.get('conclusion') or branch.get('description') or 'The linked profiles preserve the current evidence; relationships between separate households remain open.'
    clusters = [dict(id=f'household-{i}', title=f['title'], place=f.get('place'), status='unresolved', status_label=f.get('status'), summary=f.get('evidence'), boundary=f.get('boundary'), people=f.get('members', [])) for i, f in enumerate(families)]
    if not clusters:
        clusters = [dict(id='research-group', title='The record-defined study group', summary=answer, boundary=boundary, people=branch.get('members', []), status='unresolved', status_label='Relationships assessed individually')]
    story = dict(title=branch['label'], standfirst=group.get('description') or branch.get('description'), question=group.get('question') or 'What do the surviving records establish about these people and their connections?', answer=answer, boundary=boundary, clusters=clusters, chapters=[dict(id='current-reading', period='Current assessment', title='What the records show', body=[answer, boundary], evidence=[dict(label=a, url=b) for a,b in group.get('evidence', [])])], gaps=[dict(title=group.get('next') or 'Find a record naming the relationship', why='Distinguish a documented occurrence from a family connection.', priority='high')], ladder={'unresolved': [boundary]})
    if branch['id'] == 'larne-kilwaughter':
        story['evidence_log'] = {'source': 'research/larne-proof-2026-09-21/public-synthesis.md', 'title': 'Original evidence and research log'}
    return story


def locator(study_id, rows, geo):
    territories = [f for f in geo['territories'] if study_id in f['properties'].get('studies', [])]
    points = []
    for r in rows:
        if not any(p in r.get('record_precision', '').lower() for p in ('townland', 'parish', 'settlement')):
            continue
        try:
            lon, lat = float(r['longitude']), float(r['latitude'])
            if math.isfinite(lon) and math.isfinite(lat): points.append((lon, lat, r))
        except (ValueError, KeyError): pass
    if not points and not territories: return ''
    rings = geo['helper']['_rings']
    # Anchor the view on the territory (or the median record point) and leave
    # distant outliers, e.g. emigrant records, out of the locator.
    area = [(x,y) for f in territories for poly in rings(f['geometry']) for ring in poly for x,y in ring]
    if area:
        ax0, ax1 = min(x for x,_ in area), max(x for x,_ in area); ay0, ay1 = min(y for _,y in area), max(y for _,y in area)
    else:
        mx = sorted(x for x,_,_ in points)[len(points)//2]; my = sorted(y for _,y,_ in points)[len(points)//2]
        ax0 = ax1 = mx; ay0 = ay1 = my
    kk = max(.1, math.cos(math.radians((ay0+ay1)/2)))
    def near(x, y):
        dx = max(ax0-x, 0, x-ax1)*kk; dy = max(ay0-y, 0, y-ay1)
        return math.hypot(dx, dy) <= 1.25
    distant = [p for p in points if not near(p[0], p[1])]
    points = [p for p in points if near(p[0], p[1])]
    coords = area+[(x,y) for x,y,_ in points]
    if not coords: return ''
    xs, ys = zip(*coords)
    cx, cy = (min(xs)+max(xs))/2, (min(ys)+max(ys))/2
    k = max(.1, math.cos(math.radians(cy)))
    span = .3 if len(set(zip(xs, ys))) == 1 else .25
    dy = max((max(ys)-min(ys))*1.24, span, (max(xs)-min(xs))*k*1.24*3/4)
    dx = dy*4/3/k
    west, north = cx-dx/2, cy+dy/2
    def project(x,y): return (x-west)/dx*480, (north-y)/dy*360
    def path(f):
        return ' '.join('M'+'L'.join(f'{x:.1f},{y:.1f}' for x,y in [project(*p) for p in ring])+'Z' for poly in rings(f['geometry']) for ring in poly)
    svg = ''.join(f'<path d="{path(f)}" class="sp-county"/>' for f in geo['counties'])
    svg += ''.join(f'<path d="{path(f)}" class="sp-territory"><title>{esc(f["properties"].get("label") or f["properties"].get("name", "Study territory"))}</title></path>' for f in territories)
    for f in territories:
        vertices = [p for poly in rings(f['geometry']) for ring in poly for p in ring]
        if vertices:
            x,_ = project((min(p[0] for p in vertices)+max(p[0] for p in vertices))/2, 0)
            _,top = project(0, max(p[1] for p in vertices)); _,bottom = project(0, min(p[1] for p in vertices))
            # Label beside, not over, the territory so record dots stay visible.
            y = top-9 if top > 26 else bottom+20
            x = max(70, min(410, x))
            svg += f'<text x="{x:.1f}" y="{min(350,y):.1f}" text-anchor="middle" class="sp-map-label">{esc(f["properties"].get("label") or f["properties"].get("name", "Study territory"))}</text>'
    for lon,lat,r in points:
        x,y = project(lon,lat)
        svg += f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" class="sp-map-point"><title>{esc(r.get("person"))} · {esc(r.get("record_location"))} · {esc(r.get("record_precision"))}</title></circle>'
    return section('map', 'A study rooted in place', f'<figure class="sp-map"><svg viewBox="0 0 480 360" role="img" aria-label="Study territory and located records">{svg}</svg><figcaption>Dots represent townland, parish or settlement locations, not individual homes.{f" {len(distant)} more distant record location{'s are' if len(distant) != 1 else ' is'} outside this view." if distant else ""} Shared locations do not prove kinship. Boundaries: townlands.ie / OpenStreetMap, ODbL; National Records of Scotland, OGL; Historic County Borders Project.</figcaption></figure>')


def _timeline_svg(events, lanes, width, wrap, variant):
    """One responsive rendering of the chronology; labels wrap to two lines."""
    lo, hi = events[0]['year']-5, events[-1]['year']+5
    left, right = 34, width-26
    char_w, line_h, slot_h = 6.0, 13, 32
    tracks = {key: [] for key in lanes}
    placed, counts = [], Counter()
    for e in events:
        lane = e['_lane']; x = left+(right-left)*(e['year']-lo)/(hi-lo)
        item = dict(e=e, x=x)
        if not e.get('record'):
            text = f'{e["year"]} · '+str(e.get('label') or 'Record')
            lines = textwrap.wrap(text, width=wrap) or [text]
            if len(lines) > 2:
                lines = lines[:2]; lines[-1] = textwrap.shorten(lines[-1]+' …', width=wrap, placeholder='…').rstrip(' .')
                if not lines[-1].endswith('…'): lines[-1] += '…'
            w = max(map(len, lines))*char_w
            lx = max(6, min(x-w/2, width-6-w))
            slots = tracks[lane]
            start, end = lx-6, lx+w+10
            preferred = counts[lane] % 2
            # Alternate above/below; move outward only when a label would collide.
            slot = None
            for cand in [preferred, 1-preferred] + list(range(2, 40)):
                while len(slots) <= cand: slots.append([])
                lower = [slots[k] for k in range(cand % 2, cand, 2)]
                if all(end < a or start > b for a, b in slots[cand]) and all(not (a-2 <= x <= b+2) for sl in lower for a, b in sl):
                    slot = cand; break
            if slot is None:
                slot = next(c for c in range(len(slots)+1) if c >= len(slots) or all(end < a or start > b for a, b in slots[c]))
                while len(slots) <= slot: slots.append([])
            slots[slot].append((start, end))
            for k in range(slot % 2, slot, 2):
                slots[k].append((x-3, x+3))  # keep the stem clear of later labels
            item.update(lines=lines, lx=lx, slot=slot)
            counts[lane] += 1
        placed.append(item)
    positions, cursor = {}, 8
    for key in lanes:
        used = [i for i, sl in enumerate(tracks[key]) if sl]
        above = max([i//2+1 for i in used if i % 2 == 0] or [0])
        below = max([i//2+1 for i in used if i % 2 == 1] or [0])
        positions[key] = (cursor+18, cursor+38+above*slot_h)
        cursor += 52+above*slot_h+below*slot_h
    height = cursor+26
    svg = ''
    for key, (label_y, y) in positions.items():
        svg += f'<text x="8" y="{label_y}" class="sp-lane-label">{esc(textwrap.shorten(lanes[key], width=int(width/7.5), placeholder="…"))}</text><path d="M{left},{y}H{right}" class="sp-axis"/>'
    ticks = 5 if width > 600 else 3
    for tick in range(ticks+1):
        svg += f'<text x="{left+(right-left)*tick/ticks:.1f}" y="{height-10}" text-anchor="middle" class="sp-tick">{round(lo+(hi-lo)*tick/ticks)}</text>'
    for item in sorted(placed, key=lambda i: not i['e'].get('record')):
        e, x = item['e'], item['x']; y = positions[e['_lane']][1]
        label = f'{e["year"]} — {e.get("label", "Record")}'
        svg += f'<circle tabindex="0" cx="{x:.1f}" cy="{y}" r="{3.5 if e.get("record") else 7}" class="sp-event sp-{tone(e.get("status"))}"><title>{esc(label)}</title></circle>'
        if 'lines' in item:
            slot, n = item['slot'], len(item['lines'])
            above = slot % 2 == 0; level = slot//2
            if above:
                base = y-12-level*slot_h-(n-1)*line_h  # first baseline
                stem = f'M{x:.1f},{y-8}V{base+(n-1)*line_h+3:.1f}'
            else:
                base = y+22+level*slot_h
                stem = f'M{x:.1f},{y+8}V{base-10:.1f}'
            svg += f'<path d="{stem}" class="sp-stem"/><text x="{item["lx"]:.1f}" y="{base:.1f}" class="sp-event-label"><title>{esc(label)}</title>'
            svg += ''.join(f'<tspan x="{item["lx"]:.1f}" dy="{0 if i == 0 else line_h}">{esc(line)}</tspan>' for i, line in enumerate(item['lines']))+'</text>'
    return f'<svg class="sp-timeline-{variant}" viewBox="0 0 {width} {height}" role="img" aria-label="Dated evidence by research cluster">{svg}</svg>'


def timeline(story, rows):
    clusters = story.get('clusters') or []
    lanes = {c['id']: c.get('title', c['id']) for c in clusters}
    lanes['other'] = 'Other records'
    members = {p:c['id'] for c in clusters for p in c.get('people') or []}
    events = [dict(year=year(r.get('year')), label=' · '.join(filter(None,[r.get('person'),r.get('association'),r.get('record_location'),r.get('evidence')])), cluster=members.get(r.get('profile_id','').lower(),'other'), status=record_tone(r), url=r.get('source_url') or '/people/'+r.get('profile_id','').lower()+'.html', record=True) for r in rows]
    events += [dict(e,year=year(e.get('year'))) for e in story.get('timeline') or []]
    events = sorted([e for e in events if e['year'] is not None],key=lambda e:(e['year'], bool(e.get('record'))))
    if not events: return ''
    for e in events:
        e['_lane'] = e.get('cluster') if e.get('cluster') in lanes else 'other'
    occupied = {e['_lane'] for e in events}
    lanes = {key: label for key,label in lanes.items() if key in occupied}
    entries = ''.join('<li>'+link(f'{e["year"]} — {e.get("label", "Record")}', e.get('url'))+'</li>' for e in events)
    figure = _timeline_svg(events, lanes, 1100, 40, 'wide')+_timeline_svg(events, lanes, 360, 27, 'narrow')
    return section('timeline','The record chronology',f'<p class="sp-caption">Small dots are catalogue records; larger dots mark selected story events. A record occurrence alone is not proof of a relationship.</p><figure class="sp-timeline">{figure}</figure><details><summary>Read all {len(events)} dated entries, earliest first</summary><ol>{entries}</ol></details>')


def connections(story, rows=None):
    """Render only asserted, valid cluster links as a readable temporal diagram."""
    clusters = [c for c in story.get('clusters') or []
                if isinstance(c, dict) and isinstance(c.get('id'), str) and c['id']]
    by_id = {c['id']: c for c in clusters}
    if not by_id:
        return ''

    # A stated period is preferred; dated member records and story events only
    # place clusters whose period carries no usable year.
    century = {'seventeenth': 1650, 'eighteenth': 1750, 'nineteenth': 1850,
               'twentieth': 1950, 'sixteenth': 1550, 'fifteenth': 1450}
    members = {str(p).lower(): c['id'] for c in clusters
               for p in (c.get('people') if isinstance(c.get('people'), list) else [])}
    dated = {c['id']: [] for c in clusters}
    for c in clusters:
        period = str(c.get('period') or '').lower()
        nums = [int(n) for n in re.findall(r'(?<!\d)(1[4-9]\d{2}|20\d{2})(?!\d)', period)]
        dated[c['id']].extend(nums)
        if not nums:
            numeric_century = re.search(r'\b(1[4-9]|20)(?:st|nd|rd|th)\s+centur', period)
            if numeric_century:
                dated[c['id']].append((int(numeric_century.group(1)) - 1) * 100 + 50)
            for word, midpoint in century.items():
                if word in period and 'centur' in period:
                    before = period.split(word)[0]
                    dated[c['id']].append(midpoint-30 if 'early' in before else midpoint+30 if 'late' in before else midpoint)
                    break
    from_period = {cid for cid, values in dated.items() if values}
    for r in rows or []:
        if not isinstance(r, dict):
            continue
        cid = members.get(str(r.get('profile_id') or '').lower())
        value = year(r.get('year'))
        if cid and cid not in from_period and value is not None:
            dated[cid].append(value)
    for event in story.get('timeline') or []:
        if not isinstance(event, dict):
            continue
        cid, value = event.get('cluster'), year(event.get('year'))
        if isinstance(cid, str) and cid in dated and cid not in from_period and value is not None:
            dated[cid].append(value)
    earliest = {cid: min(values) if values else 9999 for cid, values in dated.items()}

    # Invalid, duplicate, and self-referential links are deliberately invisible.
    links, seen = [], set()
    for edge in story.get('links') or []:
        if not isinstance(edge, dict):
            continue
        a, b = edge.get('from'), edge.get('to')
        if not isinstance(a, str) or not isinstance(b, str) or a not in by_id or b not in by_id or a == b:
            continue
        key = (a, b, tone(edge.get('status')), str(edge.get('label') or ''))
        if key not in seen:
            seen.add(key)
            links.append(dict(edge, **{'from': a, 'to': b, 'status': tone(edge.get('status'))}))
    if not links:
        return ''

    ordered = sorted(clusters, key=lambda c: (earliest[c['id']], c.get('title', ''), c['id']))
    # Nearby starts read as a generation; undated clusters share a final row.
    layers = []
    for c in ordered:
        e0 = earliest[c['id']]
        if layers and (e0 == 9999) == (earliest[layers[-1][0]] == 9999) and (e0 == 9999 or e0 - earliest[layers[-1][0]] <= 28):
            layers[-1].append(c['id'])
        else:
            layers.append([c['id']])
    layer_of = {cid: i for i, layer in enumerate(layers) for cid in layer}

    # Orient every edge earlier → later and route long edges through virtual
    # waypoints so they travel in the gaps between boxes (Sugiyama style).
    routes = []
    for n, e in enumerate(links):
        a, b = e['from'], e['to']
        start, end = (a, b) if (layer_of[a], earliest[a]) <= (layer_of[b], earliest[b]) else (b, a)
        chain = [start]
        for li in range(layer_of[start]+1, layer_of[end]):
            dummy = f'~{n}~{li}'; layers[li].append(dummy); layer_of[dummy] = li; chain.append(dummy)
        chain.append(end)
        routes.append((e, chain))
    up, down = {}, {}
    for _, chain in routes:
        for u, v in zip(chain, chain[1:]):
            if layer_of[u] != layer_of[v]:
                down.setdefault(u, []).append(v); up.setdefault(v, []).append(u)

    node_w, dummy_w, gap_x, margin = 214, 14, 30, 24
    def wide(item): return dummy_w if item.startswith('~') else node_w
    order = {item: i for layer in layers for i, item in enumerate(layer)}
    for sweep in range(4):
        rng = range(1, len(layers)) if sweep % 2 == 0 else range(len(layers)-2, -1, -1)
        for li in rng:
            nb = up if sweep % 2 == 0 else down
            def bary(item):
                ns = nb.get(item) or (down if nb is up else up).get(item) or []
                return sum(order[x] for x in ns)/len(ns) if ns else order[item]
            layers[li].sort(key=lambda item: (bary(item), order[item]))
            order.update({item: i for i, item in enumerate(layers[li])})

    # Horizontal placement: pull items toward the mean of their neighbours,
    # then push apart to remove overlaps while keeping the crossing-reduced order.
    xs = {}
    for layer in layers:
        total = sum(wide(i) for i in layer)+gap_x*(len(layer)-1); x = -total/2
        for item in layer:
            xs[item] = x+wide(item)/2; x += wide(item)+gap_x
    def settle(layer, desired):
        pos = [desired[i] for i in layer]
        for k in range(1, len(layer)):
            pos[k] = max(pos[k], pos[k-1]+(wide(layer[k-1])+wide(layer[k]))/2+gap_x)
        shift = sum(desired[i]-p for i, p in zip(layer, pos))/len(layer)
        for i, p in zip(layer, pos): xs[i] = p+shift
    for sweep in range(6):
        rng = range(1, len(layers)) if sweep % 2 == 0 else range(len(layers)-2, -1, -1)
        for li in rng:
            nb = up if sweep % 2 == 0 else down
            desired = {i: (sum(xs[n] for n in nb[i])/len(nb[i]) if nb.get(i) else xs[i]) for i in layers[li]}
            settle(layers[li], desired)
    min_x = min(xs[i]-wide(i)/2 for i in xs); max_x = max(xs[i]+wide(i)/2 for i in xs)
    width = max(node_w+2*margin, max_x-min_x+2*margin)
    for i in xs: xs[i] += margin-min_x

    def title_lines(c): return textwrap.wrap(str(c.get('title') or c['id']), width=26) or [c['id']]
    def detail(c): return ' · '.join(filter(None, [str(c.get('period') or ''), str(c.get('place') or '')]))
    heights = {cid: 20+len(title_lines(c))*16+(20 if detail(c) else 0)+6 for cid, c in by_id.items()}
    same_row = any(layer_of[e['from']] == layer_of[e['to']] for e in links)
    top_pad = 58 if same_row else 26
    rows, y = [], top_pad
    for li, layer in enumerate(layers):
        row_h = max([heights[i] for i in layer if not i.startswith('~')] or [0])
        rows.append((y, row_h)); y += row_h+(64 if li < len(layers)-1 else 0)
    height = y+26
    boxes = {cid: (xs[cid]-node_w/2, rows[layer_of[cid]][0], node_w, heights[cid]) for cid in by_id}

    # Spread endpoints when several edges meet one side of a box.
    ports = {}
    for idx, (_, chain) in enumerate(routes):
        u, v = chain[0], chain[1] if len(chain) > 1 else chain[0]
        if layer_of[chain[0]] == layer_of[chain[-1]]:
            ports.setdefault((chain[0], 'top'), []).append((xs[chain[-1]], idx))
            ports.setdefault((chain[-1], 'top'), []).append((xs[chain[0]], idx))
        else:
            ports.setdefault((chain[0], 'bottom'), []).append((xs[chain[1]], idx))
            ports.setdefault((chain[-1], 'top'), []).append((xs[chain[-2]], idx))
    offset = {}
    for (cid, side), items in ports.items():
        items.sort(); step = min(18, (node_w-40)/max(1, len(items)))
        for k, (_, idx) in enumerate(items):
            offset[(cid, side, idx)] = (k-(len(items)-1)/2)*step

    svg, entries = '', ''
    names = {cid: c.get('title', cid) for cid, c in by_id.items()}
    for idx, (e, chain) in enumerate(routes):
        a, b = chain[0], chain[-1]
        if layer_of[a] == layer_of[b]:
            x1 = xs[a]+offset[(a, 'top', idx)]; x2 = xs[b]+offset[(b, 'top', idx)]
            y1, y2 = boxes[a][1], boxes[b][1]
            lift = max(8, min(y1, y2)-18-min(30, abs(x2-x1)*.08))
            d = f'M{x1:.1f},{y1:.1f} C{x1:.1f},{lift:.1f} {x2:.1f},{lift:.1f} {x2:.1f},{y2:.1f}'
            lx, ly = (x1+x2)/2, lift+4
        else:
            pts = [(xs[a]+offset[(a, 'bottom', idx)], boxes[a][1]+boxes[a][3])]
            for dummy in chain[1:-1]:
                ry, rh = rows[layer_of[dummy]]
                pts += [(xs[dummy], ry), (xs[dummy], ry+rh)]
            pts.append((xs[b]+offset[(b, 'top', idx)], boxes[b][1]))
            d = f'M{pts[0][0]:.1f},{pts[0][1]:.1f}'
            for k in range(1, len(pts)):
                (px, py), (qx, qy) = pts[k-1], pts[k]
                if k % 2 == 0 and len(pts) > 2:
                    d += f' L{qx:.1f},{qy:.1f}'  # straight run beside a row of boxes
                else:
                    m = (py+qy)/2
                    d += f' C{px:.1f},{m:.1f} {qx:.1f},{m:.1f} {qx:.1f},{qy:.1f}'
            (px, py), (qx, qy) = pts[0], pts[1]
            lx, ly = (px+qx)/2, (py+qy)/2+4
        label = str(e.get('label') or 'Relationship under review')
        short = textwrap.shorten(label, width=38, placeholder='…')
        lx = max(margin+len(short)*3.2, min(width-margin-len(short)*3.2, lx))
        svg += f'<g class="sp-edge-wrap sp-{e["status"]}"><path tabindex="0" data-from="{esc(e["from"])}" data-to="{esc(e["to"])}" d="{d}" class="sp-edge sp-{e["status"]}"><title>{esc(names[e["from"]])} → {esc(names[e["to"]])}: {esc(label)} ({TONES[e["status"]]})</title></path><text x="{lx:.1f}" y="{ly:.1f}" text-anchor="middle" class="sp-edge-label">{esc(short)}</text></g>'
        entries += f'<li>{esc(names[e["from"]])} → {esc(names[e["to"]])}: {inline(label)} ({TONES[e["status"]]})</li>'
    nodes = ''
    for c in clusters:
        x, yy, w, h = boxes[c['id']]
        lines = title_lines(c); det = detail(c)
        nodes += f'<g tabindex="0" data-cluster="{esc(c["id"])}" class="sp-node sp-{tone(c.get("status"))}"><title>{esc(c.get("title"))} — {esc(c.get("status_label") or TONES[tone(c.get("status"))])}</title><rect x="{x:.1f}" y="{yy:.1f}" width="{w}" height="{h:.1f}" rx="7"/><rect class="sp-node-band" x="{x:.1f}" y="{yy:.1f}" width="6" height="{h:.1f}" rx="3"/>'
        nodes += ''.join(f'<text x="{x+18:.1f}" y="{yy+24+j*16:.1f}" class="sp-node-title">{esc(line)}</text>' for j, line in enumerate(lines))
        if det:
            nodes += f'<text x="{x+18:.1f}" y="{yy+24+len(lines)*16+6:.1f}" class="sp-node-detail">{esc(textwrap.shorten(det, width=32, placeholder="…"))}</text>'
        nodes += '</g>'
    legend = ''.join(f'<span class="sp-key sp-{t}">{label}</span>' for t, label in TONES.items())
    return (f'<h3 class="sp-subhead">How the clusters connect</h3><p class="sp-caption">Rows run from the earliest cluster at the top to the latest below. Hover or focus a line for the link it represents.</p>'
            +('<p class="sp-caption sp-scroll-hint">Swipe sideways to see every cluster in the diagram.</p>' if width > 380 else '')+
            f'<figure class="sp-connections"><div class="sp-scroll"><svg viewBox="0 0 {width:.0f} {height:.0f}" style="max-width:{width:.0f}px;--sp-natural:{width:.0f}px" role="img" aria-label="Research cluster connections">{svg}{nodes}</svg></div><figcaption>{legend}</figcaption></figure>{GUIDE}'
            f'<details class="sp-link-list"><summary>Read every link ({len(links)})</summary><ul>{entries}</ul></details>')


def evidence_log(config, study_id):
    if not config or not isinstance(config.get('source'),str): return ''
    source = (ROOT/config['source']).resolve()
    if not source.is_relative_to(ROOT) or not source.is_file(): return '<p>Evidence log is not yet available.</p>'
    helper = runpy.run_path(str(ROOT/'tools/repair_person_hierarchy.py'))['_safe_markdown_html']
    parts = re.split(r'^#{2,3}\s+(.+?)\s*$',source.read_text(),flags=re.M)
    entries = [(config.get('title','Evidence log'),parts[0])] if parts[0].strip() else []
    entries.extend(zip(parts[1::2],parts[2::2]))
    return '<div class="sp-evidence-log">'+''.join(f'<details {"open" if i==0 else ""}><summary>{esc(title)}</summary><div class="sp-log-body">{helper(body,f"/branches/{study_id}/")}</div></details>' for i,(title,body) in enumerate(entries))+'</div>'


def render(branch, group, families, authored, registry, rows, geo):
    story = fallback(branch,group,families)
    story.update({k:v for k,v in (authored if isinstance(authored,dict) else {}).items() if v is not None})
    for key in ('clusters','chapters','timeline','links','gaps','facts','related'):
        story[key] = [v for v in story.get(key,[]) if isinstance(v,dict)] if isinstance(story.get(key),list) else []
    for key in ('status','ladder','evidence_log'):
        if not isinstance(story.get(key),dict): story[key] = {}
    for c in story['chapters']:
        c['body'] = [v for v in c.get('body',[]) if isinstance(v,str)] if isinstance(c.get('body'),list) else []
        c['evidence'] = [v for v in c.get('evidence',[]) if isinstance(v,dict)] if isinstance(c.get('evidence'),list) else []
    for e in story['timeline']:
        if not isinstance(e.get('cluster'),str): e['cluster'] = 'other'
    seen_ids = set()
    for i,c in enumerate(story['clusters']):
        cid = c.get('id') if isinstance(c.get('id'),str) else None
        c['id'] = cid if cid and cid not in seen_ids else f'group-{i}'
        seen_ids.add(c['id'])
        c['title'] = str(c.get('title') or 'Research cluster')
        c['people'] = [p for p in c.get('people',[]) if isinstance(p,str)] if isinstance(c.get('people'),list) else []
    for t in TONES:
        values = story['ladder'].get(t)
        story['ladder'][t] = [v for v in values if isinstance(v,str)] if isinstance(values,list) else []
    sid = branch['id']; members = branch.get('members',[])
    period = '–'.join(str(year(v) or '?') for v in group.get('years') or [branch.get('from'),branch.get('to')])
    place = group.get('place') or branch['label']
    status = story.get('status') or {'label':'Evidence-led study · connections under review','tone':'unresolved'}
    facts = story.get('facts') or [dict(value=period,label='record span'),dict(value=len(members),label='people in the study'),dict(value=len(rows),label='catalogue records')]
    body = f'<section id="study-hero" class="sp-hero"><a class="sp-back" href="/branches/">← All families &amp; studies</a><p class="sp-kicker">{esc(story.get("kicker", "Evidence-led research study"))}</p><h1>{esc(story["title"])}</h1><p class="sp-standfirst">{inline(story.get("standfirst"))}</p><span class="sp-pill sp-{tone(status.get("tone"))}">{esc(status.get("label"))}</span> <a class="sp-evidence-guide" href="{evidence_labels.GUIDE_URL}">{evidence_labels.GUIDE_LABEL}</a><p class="sp-place">{esc(period)} · {esc(place)}</p><div class="sp-facts">'+''.join(f'<div><strong>{esc(f.get("value"))}</strong><span>{esc(f.get("label"))}</span></div>' for f in facts)+'</div></section>'
    body += '<div class="sp-intro">'+section('question','The question at the heart of this study',f'<blockquote>{inline(story.get("question"))}</blockquote><p>{inline(story.get("answer"))}</p><aside class="sp-boundary"><strong>What this does not show</strong><p>{inline(story.get("boundary"))}</p></aside>')
    body += locator(sid,rows,geo)+'</div>'+timeline(story,rows)
    chapters = ''
    for i,c in enumerate(story.get('chapters') or []):
        chapters += f'<article class="sp-chapter" id="chapter-{esc(c.get("id",str(i)))}"><div class="sp-period">{esc(c.get("period"))}</div><div><h3>{esc(c.get("title"))}</h3>'+''.join(f'<p>{inline(p)}</p>' for p in c.get('body') or [])+'<div class="sp-chips">'+''.join(link(e.get('label','Source'),e.get('url')) for e in c.get('evidence') or [])+'</div></div></article>'
    if chapters: body += section('story','Reading the evidence',chapters)
    scope = ('Membership is based on documented Larne, Glenarm or Kilwaughter evidence and specifically supported family links. '
             'The possible William of Larne → John of Glenleslie → John of Lisnagaver route remains a research hypothesis and does not place Rasharkin people in this locality group.'
             if sid == 'larne-kilwaughter' else '')
    cards = '<div id="local-family-overview">'+(f'<p>{esc(scope)}</p>' if scope else '')+'<div class="sp-cluster-grid">'
    for c in story.get('clusters') or []:
        people = c.get('people') or []
        chips = '<div class="sp-chips local-family-members">'+''.join(person(p,registry) for p in people)+'</div>'
        if len(people) > 12:
            chips = f'<details><summary>{len(people)} people in this research group</summary>{chips}</details>'
        cards += f'<article class="sp-cluster local-family-card sp-{tone(c.get("status"))}" id="cluster-{esc(c["id"])}"><span class="sp-pill">{esc(c.get("status_label") or TONES[tone(c.get("status"))])}</span><h3>{esc(c.get("title"))}</h3><p class="sp-caption">{esc(" · ".join(filter(None,[str(c.get("place") or ""),str(c.get("period") or "")])))}</p><p class="local-family-basis">{inline(c.get("summary"))}</p>'+chips+f'<p class="local-family-boundary sp-boundary{"" if c.get("boundary") else " sp-keep"}"><strong>Still open:</strong> {inline(c.get("boundary") or "No additional relationship is inferred from inclusion in this cluster.")}</p></article>'
    if story['clusters'] and not (len(story['clusters']) == 1 and set(story['clusters'][0]['people']) == set(members)):
        body += section('clusters','Households & research clusters',cards+'</div></div>'+connections(story, rows))
    ladder = story.get('ladder') or {}
    if any(ladder.values()): body += section('ladder','How much can we say?',GUIDE+'<div class="sp-ladder">'+''.join(f'<article class="sp-{t}"><h3>{label}</h3><ul>'+''.join(f'<li>{inline(v)}</li>' for v in ladder.get(t) or [])+'</ul>'+('' if ladder.get(t) else '<p class="sp-empty sp-keep">No separate claim assigned at this level.</p>')+'</article>' for t,label in TONES.items())+'</div>')
    gaps = ''
    for i,g in enumerate(story.get('gaps') or []):
        if not any(g.get(k) for k in ('title','why','where','url')): continue
        gaps += f'<article class="sp-gap"><span class="sp-number">{i+1:02}</span><div><span class="sp-kicker">{esc(g.get("priority","medium"))} priority</span><h3>{inline(g.get("title"))}</h3><p>{inline(g.get("why"))}</p><p>{inline(g.get("where"))}</p>{link("Consult the record →",g.get("url")) if g.get("url") else ""}</div></article>'
    if gaps: body += section('gaps','What would settle it','<div class="sp-gap-grid">'+gaps+'</div>')
    evidence = evidence_log(story.get('evidence_log'),sid)
    if sid == 'larne-kilwaughter':
        evidence = '<div id="larne-original-evidence">'+evidence+'</div>'
    earliest = sorted((p for p in members if year(registry.get(p,{}).get('from')) is not None), key=lambda p: year(registry[p]['from']))[:6]
    if earliest and len(members) > len(earliest):  # otherwise it repeats the full list
        evidence += '<h3 class="sp-subhead">Earliest entries</h3><p class="sp-caption">Ordered by the earliest catalogue date; approximate life dates are not necessarily dated source records.</p><div class="sp-people">'+''.join('<div>'+person(p,registry,True)+'</div>' for p in earliest)+'</div>'
    evidence += '<h3 class="sp-subhead">People in this study</h3>'+('<div class="sp-people sp-all-people">'+''.join('<div>'+person(p,registry,True)+'</div>' for p in members)+'</div>' if members else '<p class="sp-caption sp-empty">No catalogue profiles are linked to this study yet; the evidence above rests on the cited records.</p>')
    evidence += '<h3 class="sp-subhead">Continue the research</h3><div class="sp-chips">'+link('Explore the records',f'/records/?branch={sid}')+link('Open the map',f'/map/?branch={sid}')+''.join(link(e.get('label','Related study'),e.get('url')) for e in story.get('related') or [])+'</div>'
    evidence += f'<p class="sp-caption">{inline(story.get("sources_note") or "Source provenance and individual uncertainties are retained in the linked profiles and dated record entries.")}</p>'
    from bs4 import BeautifulSoup
    page = BeautifulSoup('<main class="sp-page">'+body+section('evidence','Sources & people',evidence)+'</main>', 'html.parser')
    seen = set()
    for paragraph in page.select('p'):
        if 'sp-keep' in (paragraph.get('class') or []): continue
        key = ' '.join(paragraph.stripped_strings)
        if not key or key in seen: paragraph.decompose()
        else: seen.add(key)
    for chapter in page.select('.sp-chapter'):
        if not chapter.select('p, a'): chapter.decompose()
    for empty in page.select('#study-story, #study-ladder'):
        if not empty.select('article'): empty.decompose()
    for boundary in page.select('aside.sp-boundary'):
        if not boundary.select('p'): boundary.decompose()
    return str(page)


def repair():
    groups = runpy.run_path(str(ROOT/'tools/repair_research_groups.py'))
    curated = {g['id']:g for g in groups['GROUPS']+groups['IRISH_GROUPS']}
    local = runpy.run_path(str(ROOT/'tools/repair_site_experience.py'))['LOCAL_FAMILIES']
    registry = {p['slug']:p for p in json.loads((WEB/'assets/research/registry.json').read_text())}
    branches = json.loads((WEB/'assets/research/branches.json').read_text())
    with (WEB/'map/data/records.csv').open(encoding='utf-8-sig',newline='') as f: records = list(csv.DictReader(f))
    helper = runpy.run_path(str(ROOT/'tools/build_branches_directory.py'))
    geo = {'helper':helper,**{name:json.loads((helper['TERRITORY_DIR']/f'{name}.geojson').read_text())['features'] for name in ('territories','counties')}}
    counts = Counter()
    for b in branches:
        if b['id'] not in curated and b['id'] not in ('larne-kilwaughter','lisnagaver-rasharkin','early-scottish-records'): continue
        path = WEB/'branches'/b['id']/'index.html'
        original = path.read_text()
        story_path = STORIES/(b['id']+'.json')
        authored = json.loads(story_path.read_text()) if story_path.exists() else {}
        if authored and authored.get('id')!=b['id']: raise ValueError(f'Story ID mismatch: {story_path}')
        rows = [r for r in records if r.get('profile_id','').lower() in b.get('members',[])]
        main = render(b,curated.get(b['id'],{}),local.get(b['id'],[]),authored,registry,rows,geo)
        match = re.search(r'<main\b[^>]*>',original)
        if not match: raise ValueError(f'Missing main: {path}')
        tag = match[0]
        if 'sp-page' not in tag:
            tag = re.sub(r'class="([^"]*)"',lambda m:f'class="{m[1]} sp-page"',tag) if 'class="' in tag else tag[:-1]+' class="sp-page">'
        main = re.sub(r'^<main[^>]*>',lambda _:tag,main)
        updated = re.sub(r'<main\b[^>]*>.*?</main>',lambda _:main,original,count=1,flags=re.S)
        for ext,markup in [('css','<link rel="stylesheet" href="/assets/research/study-page.css?v=2"/>'),('js','<script defer src="/assets/research/study-page.js?v=2"></script>')]:
            updated = re.sub(rf'/assets/research/study-page\.{ext}\?v=[0-9A-Za-z._-]+', f'/assets/research/study-page.{ext}?v=2', updated)
            if f'/assets/research/study-page.{ext}' not in updated: updated = updated.replace('</head>',markup+'\n</head>')
        updated = re.sub(r'/assets/research/evidence\.css\?v=\w+', EVIDENCE_CSS, updated)
        if '/assets/research/evidence.css' not in updated:
            updated = updated.replace('</head>', f'<link rel="stylesheet" href="{EVIDENCE_CSS}"/>\n</head>', 1)
        if updated!=original: path.write_text(updated); counts['study_pages_updated']+=1
        counts['study_pages']+=1
        counts['authored_stories' if authored else 'fallback_stories']+=1
    return counts


if __name__ == '__main__':
    print(json.dumps(repair(),sort_keys=True))
