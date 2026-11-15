"""Cinematic Places story, derived from the published people and search index.

No family connections are inferred. Each bubble is one primary exported-root
group, and its area is proportional to its distinct eligible-person membership.
"""
from __future__ import annotations

from collections import defaultdict
from html import escape
import math
from pathlib import Path

from bs4 import BeautifulSoup

try:
    from tools.statistics_overview import _footprint, load_world_outline
except ModuleNotFoundError:
    from statistics_overview import _footprint, load_world_outline


def _identity(person, index):
    return str(person.get("catalogue_id") or person.get("id") or person.get("map_key") or index).casefold()


def places_statistics(people: list[dict], search_index, summary_html: str = "") -> dict:
    """Count source labels and distinct primary-root memberships, without I/O."""
    eligible = {}
    aliases = {}
    for index, person in enumerate(people):
        if person.get("likely_living"):
            continue
        key = _identity(person, index)
        eligible[key] = person
        for field in ("catalogue_id", "id", "map_key"):
            if person.get(field):
                aliases[str(person[field]).casefold()] = key
        aliases[key] = key
    regions = set()
    for person in eligible.values():
        for label in person.get("regions") or []:
            label = str(label).strip()
            if label and label.casefold() not in {"unknown", "unspecified"}:
                regions.add(label)
    rows = search_index.get("people", []) if isinstance(search_index, dict) else search_index
    members = defaultdict(set)
    roots = {}
    for index, row in enumerate(rows or []):
        if row.get("likely_living"):
            continue
        person_key = aliases.get(_identity(row, index))
        root = row.get("family_root")
        if person_key is None or not isinstance(root, dict) or not root.get("id"):
            continue
        root_key = str(root["id"]).casefold()
        members[root_key].add(person_key)
        roots.setdefault(root_key, {"id": str(root["id"]), "name": str(root.get("name") or root["id"])})
    groups = [{**roots[key], "count": len(group)} for key, group in members.items()]
    groups.sort(key=lambda group: (-group["count"], group["id"].casefold()))
    soup = BeautifulSoup(summary_html, "html.parser")
    mapped_places = None
    for label in soup.find_all("span"):
        if label.get_text(" ", strip=True).casefold() == "mapped places":
            value = label.parent.find("strong")
            if value:
                mapped_places = value.get_text(" ", strip=True)
                break
    return {"regions": len(regions), "mapped_places": mapped_places,
            "root_count": len(groups), "assigned_people": len(set().union(*members.values())) if members else 0,
            "largest_root": groups[0]["count"] if groups else 0, "groups": groups,
            "eligible_people": len(eligible)}


def _constellation(groups):
    shown = groups[:8]
    parts = ['<svg class="statistics-places-constellation" viewBox="0 0 900 360" role="group" aria-label="Eight largest primary exported-root groups; separate circles do not imply shared ancestry">',
             '<title>Primary exported-root groups sized by distinct catalogue membership</title>']
    if not shown:
        parts.append('<text x="450" y="180" text-anchor="middle">No primary exported-root groups in this snapshot</text>')
    else:
        maximum = shown[0]["count"]
        colors = ["#426f58", "#b78049", "#58889b", "#8b7397", "#8e9c62", "#bd766d", "#c2a04a", "#527c7b"]
        for index, group in enumerate(shown):
            # Four fixed columns and two rows guarantee non-overlap even when
            # every group has the same count. Radius is never clamped.
            x = 112.5 + (index % 4) * 225
            y = 85 if index < 4 else 245
            radius = 60 * math.sqrt(group["count"] / maximum)
            name = group["name"]
            displayed_name = name if len(name) <= 29 else name[:28].rstrip() + "…"
            description = f'{name} ({group["id"]}): {group["count"]:,} people in this primary exported-root group'
            parts.append(f'<g class="statistics-places-root-group" data-root="{escape(group["id"], quote=True)}" data-count="{group["count"]}">')
            parts.append(f'<circle class="statistics-places-root" cx="{x:g}" cy="{y:g}" r="{radius:.5f}" fill="{colors[index]}" tabindex="0" role="img" aria-label="{escape(description, quote=True)}"><title>{escape(description)}</title></circle>')
            parts.append(f'<text class="statistics-places-root-count" x="{x:g}" y="{y:g}" dy=".32em" text-anchor="middle" font-size="23" font-weight="650" fill="#fff" pointer-events="none" aria-hidden="true">{group["count"]:,}</text>')
            # Fixed label rows allow circles to vary without a ragged baseline.
            name_y = 165 if index < 4 else 325
            parts.append(f'<text class="statistics-places-root-name" x="{x:g}" y="{name_y}" text-anchor="middle" font-size="12">{escape(displayed_name)}<title>{escape(name)}</title></text>')
            parts.append(f'<text class="statistics-places-root-id" x="{x:g}" y="{name_y + 15}" text-anchor="middle" font-size="10">{escape(group["id"])}</text></g>')
    parts.append("</svg>")
    total_shown = sum(group["count"] for group in shown)
    return ('<section class="statistics-places-branches" aria-labelledby="statistics-places-branches-title">'
            '<div class="statistics-places-branch-head"><div><span class="statistics-story-eyebrow">A forest of branches</span>'
            '<h3 id="statistics-places-branches-title">Family groups, in proportion.</h3></div>'
            f'<p>{len(shown)} largest groups · {total_shown:,} group memberships shown</p></div>' + '<div class="statistics-places-constellation-wrap">' + "".join(parts) + '</div>' +
            '<p class="statistics-story-caption">Circle area represents distinct people assigned to each primary exported-root group. '
            'These are groups from exported parent links, not proved kinship or proof that separate groups share an ancestor. '
            'Only the eight largest groups are shown.</p></section>')


def render_places_story(people: list[dict], search_index, summary_html: str = "", *,
                        web_root: Path | None = None, outline=None) -> str:
    """Render map-led Places story and eight non-overlapping family bubbles.

    Pass outline=[] for pure deterministic tests without geographic land paths.
    Omitted outline reads the same maintained public world asset as Overview.
    Summary-derived mapped-place totals are preserved verbatim, never guessed.
    """
    counts = places_statistics(people, search_index, summary_html)
    if outline is None:
        outline = load_world_outline(web_root)
    metrics = [(f'{counts["regions"]:,}', "Regional labels"),
               (counts["mapped_places"] or "Not supplied", "Mapped places"),
               (f'{counts["root_count"]:,}', "Primary root groups"),
               (f'{counts["assigned_people"]:,}', "People assigned to roots")]
    metric_html = "".join(f'<div><strong>{escape(value)}</strong><span>{escape(label)}</span></div>'
                          for value, label in metrics)
    return ('<section class="statistics-places-story" aria-label="Places and family groups">'
            '<div class="statistics-story-hero statistics-places-hero"><div class="statistics-story-copy">'
            '<span class="statistics-story-eyebrow">Places &amp; families</span>'
            '<h2>Roots in a<br>wider world.</h2>'
            '<p>Recorded places and the family groups represented in the catalogue.</p>'
            '<div class="statistics-story-metrics">' + metric_html +
            '</div><p class="statistics-story-caption">Regional labels use several geographic levels. '
            'Unknown and unspecified labels are excluded; a person may be associated with several places. These are not necessarily birthplaces.</p></div>'
            '<div class="statistics-places-atlas">' + _footprint(people, outline) + '</div></div>' +
            _constellation(counts["groups"]) + '</section>')
