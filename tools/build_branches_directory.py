#!/usr/bin/env python3
"""Build the no-JavaScript branches directory and its map data."""
from collections import Counter, defaultdict
from datetime import date
from html import escape
from pathlib import Path
import csv
import json
import re
import math
import runpy

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "www"
HUB_BBOXES = {
    "early-ireland": [51.3, -10.8, 55.5, -5.2],
    "scottish-families": [54.4, -8.7, 60.9, -0.5],
    "north-american-families": [24.3, -130.0, 54.9, -52.5],
    "australasian-families": [-47.5, 110.0, -9.0, 179.0],
    "english-welsh-families": [49.8, -6.5, 55.9, 2.1],
    "other-family-places": [-55.0, -180.0, 72.0, 180.0],
}


def precision(raw):
    """Map record precision to the public, deliberately small vocabulary."""
    text = (raw or "").lower()
    if "exact" in text or "record-stated" in text:
        return "exact", 0
    if "townland" in text or "parish" in text:
        return "parish", 1
    if "settlement" in text or "geocoded" in text:
        return "settlement", 2
    if "county" in text:
        return "county", 3
    if "country" in text:
        return "country", 4
    return "none", 5


def as_year(value):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 999999


def _words(text):
    return {w for w in re.findall(r"[a-z]{4,}", (text or "").lower())}


def group_location(rows, hint=""):
    """Choose the commonest usable location at the best available precision.

    A place named in the study title (``hint``) wins over a merely frequent
    member locality, so "Lisnagaver & Rasharkin" is not pinned elsewhere.
    """
    candidates = []
    for row in rows:
        try:
            lat, lon = float(row["latitude"]), float(row["longitude"])
        except (KeyError, TypeError, ValueError):
            continue
        label = (row.get("record_location") or "").strip()
        raw = (row.get("record_precision") or "").strip()
        if not label:
            continue
        value, rank = precision(raw)
        if value == "none":
            continue
        candidates.append((rank, label, lat, lon, value, raw, as_year(row.get("year"))))
    if not candidates:
        return "", None, None, "none", "No mapped place"
    named = [item for item in candidates if _words(item[1]) & _words(hint)]
    if named:
        candidates = named
    best_rank = min(item[0] for item in candidates)
    best = [item for item in candidates if item[0] == best_rank]
    grouped = defaultdict(list)
    for item in best:
        grouped[(item[1], item[2], item[3], item[4], item[5])].append(item)
    chosen = min(grouped.items(), key=lambda item: (-len(item[1]), min(row[6] for row in item[1]), item[0][0]))[0]
    label, lat, lon, value, raw = chosen
    return label, lat, lon, value, raw or "Representative place for the study"


def area_for(*texts):
    for text in texts:
        match = re.search(r"\bCounty\s+[^,;—–]+", text or "", re.I)
        if match:
            return match.group(0).strip()
    for text in texts:
        if text:
            return re.split(r"\s*[;,—–]\s*", text)[0].strip()
    return ""


def status_for(branch, curated):
    if branch["kind"] == "family":
        return "Exported-tree family"
    if branch["kind"] == "place":
        return "Local research study"
    return curated.get(branch["id"], {}).get("status", "Evidence-led study")


def family_summary(branch, place):
    dates = ""
    if branch.get("from") is not None or branch.get("to") is not None:
        dates = f"{int(branch.get('from') or branch.get('to'))}–{int(branch.get('to') or branch.get('from'))}"
    pieces = [f"{branch.get('count', 0)} people"]
    if dates:
        pieces.append(dates)
    if place:
        pieces.append(place)
    return " · ".join(pieces)


def card(group):
    """A compact study card; the title link covers the whole card."""
    meta = [group["place"] or "No mapped place"]
    if group["from"] is not None or group["to"] is not None:
        meta.append(f'{group["from"] or "?"}–{group["to"] or "?"}')
    if group["people"]:
        meta.append(f'{group["people"]} {"person" if group["people"] == 1 else "people"}')
    question = f'<p class="bd-question">{escape(group["question"])}</p>' if group["question"] else ""
    return (f'<article class="bd-card" data-group-id="{escape(group["id"], quote=True)}">'
            f'<span class="bd-status">{escape(group["status"])}</span><h3><a href="{escape(group["url"], quote=True)}">{escape(group["label"])}</a></h3>'
            f'<p class="bd-place">{escape(" · ".join(meta))}</p>{question}</article>')


TERRITORY_DIR = ROOT / "tools/branch_territories"
MAP_BBOX = (-7.7, 54.4, -2.5, 56.2)  # west, south, east, north — must match prepare_branch_territories.CLIP
MAP_SCALE = 330.0


def _project(lon, lat):
    west, south, east, north = MAP_BBOX
    k = math.cos(math.radians((south + north) / 2))
    return (lon - west) * k * MAP_SCALE, (north - lat) * MAP_SCALE


def _map_size():
    return _project(MAP_BBOX[2], MAP_BBOX[1])


def _rings(geometry):
    if geometry["type"] == "Polygon":
        return [geometry["coordinates"]]
    if geometry["type"] == "MultiPolygon":
        return geometry["coordinates"]
    return []


def _path(geometry):
    parts = []
    for polygon in _rings(geometry):
        for ring in polygon:
            points, last = [], None
            for lon, lat in ring:
                x, y = _project(lon, lat)
                point = (round(x, 1), round(y, 1))
                if point != last:
                    points.append(point)
                    last = point
            if len(points) > 2:
                parts.append("M" + "L".join(f"{x:g},{y:g}" for x, y in points) + "Z")
    return "".join(parts)


def _label_point(geometry):
    """Area-weighted centroid of the largest polygon (a simple visual anchor)."""
    best, best_area = None, -1.0
    for polygon in _rings(geometry):
        ring = [_project(lon, lat) for lon, lat in polygon[0]]
        area = cx = cy = 0.0
        for (x0, y0), (x1, y1) in zip(ring, ring[1:] + ring[:1]):
            cross = x0 * y1 - x1 * y0
            area += cross
            cx += (x0 + x1) * cross
            cy += (y0 + y1) * cross
        if abs(area) > best_area and area:
            best_area, best = abs(area), (cx / (3 * area), cy / (3 * area))
    return best or (0.0, 0.0)


def basemap_paths():
    """Non-interactive context: historic counties of Ireland and Great Britain.

    Drawn inline (not as an <image>) so county lines keep a constant width
    when the map is zoomed.
    """
    counties = json.loads((TERRITORY_DIR / "counties.geojson").read_text(encoding="utf-8"))["features"]
    return '<g class="bd-base">' + "".join(
        f'<path class="bd-base-{f["properties"]["country"]}" d="{_path(f["geometry"])}"/>' for f in counties if f.get("geometry")) + '</g>'


def _fixed(x, y, content, cls):
    """A marker that JavaScript keeps at constant screen size while zooming."""
    return f'<g class="{cls}" data-x="{x:.1f}" data-y="{y:.1f}" transform="translate({x:.1f} {y:.1f})">{content}</g>'


def county_labels():
    width, height = _map_size()
    counties = json.loads((TERRITORY_DIR / "counties.geojson").read_text(encoding="utf-8"))["features"]
    labels = []
    for f in counties:
        if not f.get("geometry"):
            continue
        x, y = _label_point(f["geometry"])
        if 40 < x < width - 40 and 20 < y < height - 20:
            name = re.sub(r"^County ", "", f["properties"]["name"] or "")
            labels.append(_fixed(x, y, f'<text>{escape(name)}</text>', "bd-county"))
    return "".join(labels)


LOCATED = ("exact", "townland", "record-stated", "parish", "settlement")


def _inside(lon, lat, geometry):
    for polygon in _rings(geometry):
        ring, hit = polygon[0], False
        for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1]):
            if (y1 > lat) != (y2 > lat) and lon < (x2 - x1) * (lat - y1) / (y2 - y1) + x1:
                hit = not hit
        if hit:
            return True
    return False


def _captures(profile_id, cache={}):
    """Saved record captures (images, transcripts) in one research dossier."""
    if profile_id not in cache:
        folder = ROOT / "research" / profile_id / "captures"
        cache[profile_id] = sum(1 for f in folder.rglob("*") if f.is_file()) if folder.is_dir() else 0
    return cache[profile_id]


def _dossier_kb(profile_id, cache={}):
    """Size of the maintained research notes (Markdown) for one profile."""
    if profile_id not in cache:
        folder = ROOT / "research" / profile_id
        cache[profile_id] = sum(f.stat().st_size for f in folder.rglob("*.md")) / 1024 if folder.is_dir() else 0
    return cache[profile_id]


def rank_territories(territories):
    """Rank study areas by the research recorded for them.

    For each area: records whose mapped place (townland, parish or settlement
    precision only) falls inside its parishes, plus the members of its studies.
    Score = 45% research-note depth (log of Markdown in research dossiers),
    35% sourced evidence: located records with a source plus record captures
    saved in the area's dossiers (log), 20% documented people
    located there, excluding unreviewed One-Tree profile leads (log); each
    normalised to the best area.  Rebuilt from the data on every build.
    """
    with (WEB / "map/data/records.csv").open(encoding="utf-8-sig", newline="") as source:
        records = [r for r in csv.DictReader(source) if r.get("latitude") and any(k in (r.get("record_precision") or "").lower() for k in LOCATED)]
    # Study members count towards an area, except country-wide umbrella groups
    # (e.g. Early Scottish records, 214 people) that are not local to it.
    members = {b["id"]: b.get("members", []) for b in json.loads((WEB / "assets/research/branches.json").read_text(encoding="utf-8"))
               if len(b.get("members", [])) <= 60}
    research_ids = {d.name.lower(): d.name for d in (ROOT / "research").iterdir() if d.is_dir()}
    metrics = {}
    for feature in territories:
        t = feature["properties"]
        inside = [r for r in records if _inside(float(r["longitude"]), float(r["latitude"]), feature["geometry"])]
        leads = {r.get("profile_id") or r["person"] for r in inside if "one-tree" in (r.get("family_group") or "").lower() or "profile lead" in (r.get("family_group") or "").lower()}
        people = {r.get("profile_id") or r["person"] for r in inside}
        ids = {r["profile_id"].lower() for r in inside if r.get("profile_id")} | {m.lower() for sid in t["studies"] for m in members.get(sid, [])}
        dossiers = sorted(research_ids[i] for i in ids if i in research_ids)
        metrics[t["id"]] = dict(people=len(people), leads=len(people & leads), documented=len(people - leads),
                                sourced=sum(1 for r in inside if r.get("source_url")) + sum(_captures(d) for d in dossiers), dossiers=len(dossiers),
                                kb=sum(_dossier_kb(d) for d in dossiers))
    parts = {"kb": .45, "sourced": .35, "documented": .20}
    best = {k: max(math.log1p(m[k]) for m in metrics.values()) or 1 for k in parts}
    for m in metrics.values():
        m["score"] = round(100 * sum(w * math.log1p(m[k]) / best[k] for k, w in parts.items()))
    ordered = sorted(territories, key=lambda f: (-metrics[f["properties"]["id"]]["score"], f["properties"]["label"]))
    for rank, feature in enumerate(ordered, 1):
        feature["properties"]["priority"] = rank
        feature["properties"]["metrics"] = metrics[feature["properties"]["id"]]
    return ordered


def _evidence_line(m):
    people = f'{m["people"]:,} people mapped' + (f' ({m["leads"]:,} unreviewed profile lead{"s" if m["leads"] != 1 else ""})' if m["leads"] else '')
    return escape(f'{m["dossiers"]} research dossiers · {m["sourced"]} sourced records and captures · {people}')


def study_map(groups):
    """Inline SVG of the priority study territories plus the ranked list."""
    by_id = {group["id"]: group for group in groups}
    width, height = _map_size()
    territories = rank_territories(json.loads((TERRITORY_DIR / "territories.geojson").read_text(encoding="utf-8"))["features"])
    shapes, badges, items = [], [], []
    # Separate badges that would overlap (1, 3 and 8 are neighbouring parishes)
    # and join each moved badge to its area with a short leader line.
    anchors = {f["properties"]["id"]: _label_point(f["geometry"]) for f in territories}
    placed = {}
    for tid, (x, y) in anchors.items():
        bx, by = x, y
        for _ in range(40):
            clash = [(px, py) for px, py in placed.values() if math.hypot(bx - px, by - py) < 32]
            if not clash:
                break
            px, py = clash[0]
            dx, dy = (bx - px) or -1.0, (by - py) or -1.0
            norm = math.hypot(dx, dy)
            bx, by = bx + dx / norm * 8, by + dy / norm * 8
        placed[tid] = (bx, by)
    for feature in territories:
        t = feature["properties"]
        studies = [by_id[sid] for sid in t["studies"] if sid in by_id]
        if not studies:
            continue
        primary = studies[0]
        tid = escape(t["id"], quote=True)
        ax, ay = anchors[t["id"]]
        x, y = placed[t["id"]]
        leader = f'<line class="bd-leader" x1="{ax:.1f}" y1="{ay:.1f}" x2="{x:.1f}" y2="{y:.1f}"/>' if math.hypot(x - ax, y - ay) > 4 else ''
        # The badge offset from its area shrinks as the map zooms in (data-ox/oy).
        badge = (f'<g class="bd-badge-g" data-x="{ax:.1f}" data-y="{ay:.1f}" data-ox="{x - ax:.1f}" data-oy="{y - ay:.1f}" transform="translate({x:.1f} {y:.1f})">'
                 f'<circle class="bd-badge" r="13"/><text>{t["priority"]}</text></g>')
        label = f'{t["priority"]}. {t["label"]}: {primary["label"]}'
        shapes.append(f'<a class="bd-territory bd-{t["country"]}" href="{escape(primary["url"], quote=True)}" data-territory="{tid}" aria-label="{escape(label, quote=True)}">'
                      f'<path d="{_path(feature["geometry"])}"/>{leader}{badge}</a>')
        study_links = ''.join(
            f'<li><a href="{escape(s["url"], quote=True)}">{escape(s["label"])}</a> <span class="bd-status">{escape(s["status"])}</span></li>'
            for s in studies)
        items.append(f'<li class="bd-priority-item" data-territory="{tid}"><span class="bd-rank">{t["priority"]}</span><div>'
                     f'<h3><a href="{escape(primary["url"], quote=True)}">{escape(t["label"])}</a></h3>'
                     f'<p>{escape(t["why"])}</p><p class="bd-evidence" title="Research score {t["metrics"]["score"]} of 100">{_evidence_line(t["metrics"])}</p><p class="bd-parishes">Civil parishes shown: {escape(", ".join(sorted({re.sub(r" [(].*[)]$", "", p) for p in t["parishes"]})))}</p>'
                     f'<ul class="bd-priority-studies">{study_links}</ul></div></li>')
    overseas = [g for g in groups if g["tier"] == "study" and not any(r in {"early-ireland", "scottish-families"} for r in g["regions"])]
    return (f'<section id="study-map" class="bd-studymap" aria-labelledby="study-map-title"><div class="bd-studymap-head"><span class="r-kicker">Priority studies</span>'
            '<h2 id="study-map-title">Where the research is concentrated</h2><p>The highlighted areas are the main study areas, numbered by how much research is recorded for them: research dossiers, sourced records and documented people located there. '
            'Hover or tap an area to see its studies; select it to open the leading study. Scroll or pinch to zoom, and drag to move the map.</p></div>'
            f'<div class="bd-studymap-body"><figure class="bd-studymap-figure"><svg class="bd-svg" viewBox="0 0 {width:.0f} {height:.0f}" role="group" aria-label="Map of priority research areas in Ireland and Scotland">'
            + basemap_paths()
            + county_labels()
            + _fixed(*_project(-7.2, 54.55), '<text>IRELAND</text>', 'bd-country')
            + _fixed(*_project(-3.4, 56.12), '<text>SCOTLAND</text>', 'bd-country')
            + ''.join(shapes) +
            '</svg><div class="bd-zoom" hidden><button type="button" data-zoom="in" aria-label="Zoom in">+</button><button type="button" data-zoom="out" aria-label="Zoom out">−</button><button type="button" data-zoom="reset" aria-label="Show the whole map">⤢</button></div><div class="bd-popup" hidden role="status"></div>'
            '<figcaption>Civil-parish outlines mark representative study areas, not proved family lands. Boundaries: '
            '<a href="https://www.townlands.ie/">Townlands.ie</a> and <a href="https://www.openstreetmap.org/copyright">© OpenStreetMap contributors</a> (ODbL); '
            '<a href="https://www.nrscotland.gov.uk/">National Records of Scotland</a> civil parishes (Open Government Licence); '
            'this map made use of data provided by the <a href="https://www.county-borders.co.uk">Historic County Borders Project</a>.</figcaption></figure>'
            f'<ol class="bd-priority">{"".join(items)}</ol></div>'
            + (f'<p class="bd-overseas">Studies beyond Ireland and Scotland: ' + ', '.join(f'<a href="{escape(g["url"], quote=True)}">{escape(g["label"])}</a>' for g in overseas) + '.</p>' if overseas else '')
            + '</section>')


def static_main(directory):
    regions = directory["regions"]
    groups = directory["groups"]
    statuses = sorted({group["status"] for group in groups})
    options = ''.join(f'<option value="{escape(group["id"], quote=True)}">{escape(group["label"])}</option>' for group in regions)
    status_options = ''.join(f'<option value="{escape(value, quote=True)}">{escape(value)}</option>' for value in statuses)
    region_cards = ''.join(
        f'<a class="bd-region-card" href="{escape(region["url"], quote=True)}"><strong>{escape(region["label"])}</strong><small>{region["people"]:,} people</small></a>'
        for region in regions)
    studies = [group for group in groups if group["kind"] == "research"]
    scottish = [group for group in studies if group["region"] == "scottish-families"]
    irish = [group for group in groups if group["kind"] in {"research", "place"} and "early-ireland" in group["regions"]]
    def grouped_cards(items):
        # Most studies name a unique locality, so sub-headings per area would
        # produce one card per heading; order chronologically instead.
        ordered = sorted(items, key=lambda item: (item["from"] if item["from"] is not None else 9999, item["label"]))
        return '<div class="bd-study-grid">' + ''.join(card(item) for item in ordered) + '</div>'

    family_sections = []
    for region in regions:
        families = [group for group in groups if group["kind"] == "family" and region["id"] in group["regions"]]
        items = ''.join(f'<li data-group-id="{escape(group["id"], quote=True)}"><a href="{escape(group["url"], quote=True)}">{escape(group["label"])}</a> · {group["people"]} people · {group["from"] or "?"}–{group["to"] or "?"}</li>' for group in families)
        family_sections.append(f'<details><summary>Connected families in {escape(region["label"])} ({len(families)})</summary><ul>{items}</ul></details>')
    return f'''<main class="r-main" id="main"><header class="r-page-head"><span class="r-kicker">Families &amp; localities</span><h1>Find the place.<br>Follow the family.</h1><p class="r-lead">Start with a region, choose an evidence-led study, then follow named people into their records and connections.</p></header>
{study_map(groups)}
<section id="bd-find" class="bd-find" hidden><label for="bd-q">Find a study or family</label><input id="bd-q" type="search" placeholder="A person, family or place" autocomplete="off"><p id="bd-count" role="status"></p></section>
<section id="experience-regions"><span class="r-kicker">Browse by place</span><h2>Start with a region</h2><div class="bd-region-grid">{region_cards}</div></section>
<section id="research-studies"><span class="r-kicker">Evidence-led studies</span><h2>Scotland studies</h2>{grouped_cards(scottish)}</section>
<section id="irish-research-studies"><span class="r-kicker">Evidence-led studies</span><h2>Ireland &amp; Ulster studies</h2>{grouped_cards(irish)}</section>
<section id="connected-families"><span class="r-kicker">Browse the catalogue exports</span><h2>Connected families</h2>{''.join(family_sections)}<p><a href="/branches/browse/">Browse all family groups</a></p></section></main>'''


def repair():
    changed = Counter()
    branches = json.loads((WEB / "assets/research/branches.json").read_text(encoding="utf-8"))
    palette = json.loads((WEB / "assets/research/palette.json").read_text(encoding="utf-8"))
    data = runpy.run_path(str(ROOT / "tools/repair_research_groups.py"))
    family_browsing = runpy.run_path(str(ROOT / "tools/repair_family_browsing.py"))
    curated = {item["id"]: {**item, "status": family_browsing["status"](item)} for item in data["GROUPS"] + data["IRISH_GROUPS"]}
    with (WEB / "map/data/records.csv").open(encoding="utf-8-sig", newline="") as source:
        records = list(csv.DictReader(source))
    by_person = defaultdict(list)
    for row in records:
        by_person[(row.get("profile_id") or "").lower()].append(row)
    hubs = [branch for branch in branches if branch["kind"] == "region"]
    regions = [{"id": hub["id"], "label": hub["label"], "url": hub["url"], "people": int(hub.get("count") or 0), "bbox": HUB_BBOXES[hub["id"]]} for hub in hubs]
    groups = []
    for branch in branches:
        if branch["kind"] == "region":
            continue
        member_rows = [row for member in branch.get("members", []) for row in by_person[member.lower()]]
        mapped_place, lat, lon, value, precision_label = group_location(member_rows, branch["label"] if branch["kind"] != "family" else "")
        study = curated.get(branch["id"], {})
        display_place = study.get("place") or mapped_place
        topics = [topic for topic in branch.get("topic_ids", []) if topic in HUB_BBOXES]
        if not topics:
            topics = ["other-family-places"]
        countries = branch.get("countries") or {}
        country = max(countries, key=countries.get, default="other")
        summary = branch.get("description") or ""
        if branch["kind"] == "family" and summary.startswith("Browse the relationships attached to"):
            summary = family_summary(branch, display_place)
        groups.append({"id": branch["id"], "label": branch["label"], "url": branch["url"], "kind": branch["kind"],
                       "tier": "study" if branch["kind"] in {"research", "place"} else "family", "region": topics[0], "regions": topics,
                       "area": area_for(display_place, mapped_place), "place": display_place, "lat": lat, "lon": lon,
                       "precision": value, "precision_label": precision_label, "status": status_for(branch, curated),
                       "question": branch.get("question") or study.get("question") or "", "summary": summary,
                       "from": int(branch["from"]) if branch.get("from") is not None else None,
                       "to": int(branch["to"]) if branch.get("to") is not None else None,
                       "people": int(branch.get("count") or 0), "records": int(branch.get("record_count") or 0),
                       "colour": palette.get(country, palette["other"])["color"]})
    directory = {"generated": date.today().isoformat(), "regions": regions, "groups": groups, "migrations": [
        {"from_group": "larne-kilwaughter", "from": [54.852778, -5.889722],
         "to": [34.2746, -81.6187], "label": "Larne & Kilwaughter → South Carolina",
         "status": "supported", "note": "The maintained East Antrim study describes the supported Robert–James–Archibald continuation; the associated record map places Glasgow-2304 in Newberry District."},
        {"from_group": "research-irish-cork-new-zealand", "from": [51.9, -8.5], "to": [-41.0, 174.0],
         "label": "County Cork → New Zealand", "status": "documented",
         "note": "An independent migration family; both ends are shown at county/country level because no townland or New Zealand settlement is mapped."}
    ]}
    output = WEB / "assets/research/branches-directory.json"
    encoded = json.dumps(directory, ensure_ascii=False, indent=2) + "\n"
    if not output.exists() or output.read_text(encoding="utf-8") != encoded:
        output.write_text(encoded, encoding="utf-8")
        changed["branches_directory"] += 1
    page = WEB / "branches/index.html"
    text = page.read_text(encoding="utf-8")
    css = '<link rel="stylesheet" href="/assets/research/branches-directory.css?v=12">'
    text = re.sub(r'<link rel="stylesheet" href="/assets/research/branches-directory\.css\?v=\d+">', "", text)
    text = text.replace("</head>", css + "</head>", 1)
    script = '<script defer src="/assets/research/branches-directory.js?v=5"></script>'
    text = re.sub(r'<script defer src="/assets/research/branches-(?:map|directory)\.js\?v=\d+"></script>', "", text)
    core = re.search(r'(<script defer src="/assets/research/core\.js\?v=[^"]+"></script>)', text)
    text = text[:core.end()] + script + text[core.end():] if core else text.replace("</body>", script + "</body>", 1)
    text = re.sub(r'<main\b[^>]*>.*?</main>', static_main(directory), text, count=1, flags=re.S)
    if text != page.read_text(encoding="utf-8"):
        page.write_text(text, encoding="utf-8")
        changed["branches_directory"] += 1
    changed["home_study_map"] += _home_study_map(directory["groups"], css, script)
    return changed


def _home_study_map(groups, css: str, script: str) -> int:
    """Show the same priority-study map on the homepage, after the family/place starting points."""
    page = WEB / "index.html"
    original = page.read_text(encoding="utf-8")
    section = study_map(groups).replace('class="bd-studymap"', 'class="bd-studymap bd-home-studymap"', 1)
    more = '<p class="bd-home-more"><a href="/branches/#study-map">All study areas and families →</a></p>'
    section = section[:-len("</section>")] + more + "</section>"
    text = re.sub(r'<section id="study-map" class="bd-studymap[^"]*".*?</section>', "", original, count=1, flags=re.S)
    anchor = re.search(r'<section class="v3-section"><div class="v3-section-heading"><div><span class="r-kicker">Follow the evidence</span>.*?</section>', text, flags=re.S)
    if not anchor:
        raise ValueError("homepage 'Follow the evidence' section not found")
    text = text[:anchor.end()] + section + text[anchor.end():]
    text = re.sub(r'<link rel="stylesheet" href="/assets/research/branches-directory\.css\?v=\d+">', "", text)
    text = text.replace("</head>", css + "</head>", 1)
    text = re.sub(r'<script defer src="/assets/research/branches-(?:map|directory)\.js\?v=\d+"></script>', "", text)
    text = text.replace("</body>", script + "</body>", 1)
    if text == original:
        return 0
    page.write_text(text, encoding="utf-8")
    return 1


if __name__ == "__main__":
    print(dict(repair()))
