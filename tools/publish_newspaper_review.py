#!/usr/bin/env python3
"""Publish the curated Glasgow newspaper review without exposing captures."""
from __future__ import annotations

from html import escape
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "www"
SOURCE = ROOT / "surname-research/indexes/glasgow-newspaper-review.json"
START, END = "<!-- early-newspapers:start -->", "<!-- early-newspapers:end -->"
PUBLIC_ROW_FIELDS = ("image_id", "date", "paper", "page", "source_url", "queries",
                     "status", "reading", "assessment", "profile_ids", "draft_url", "reviewed_on")


def profile_links(ids: list[str]) -> str:
    links = []
    for ident in ids or []:
        ident = str(ident).strip()
        if not ident:
            continue
        slug = ident.lower()
        href = f"/people/{slug}.html" if (WEB / "people" / f"{slug}.html").exists() else f"https://www.wikitree.com/wiki/{ident}"
        links.append(f'<a href="{escape(href, quote=True)}">{escape(ident)}</a>')
    return ", ".join(links) or "—"


def render(data: dict) -> str:
    groups = {status: [] for status in ("confirmed surname", "place study", "place or ship", "reading pending")}
    for row in sorted(data["rows"], key=lambda item: (item.get("date", ""), item.get("image_id", ""))):
        links = [profile_links(row.get("profile_ids", []))]
        if row.get("draft_url"):
            links.append(f'<a href="{escape(str(row["draft_url"]), quote=True)}">Research draft</a>')
        issue = f'{row.get("date", "—")} · {row.get("paper", "—")} · p. {row.get("page", "—")}'
        reading = row.get("reading") or "—"
        source = row.get("source_url") or "#"
        groups[row["status"]].append(
            f'<tr id="newspaper-{escape(str(row.get("image_id", "")))}">'
            f'<td>{escape(issue)}<br><a href="{escape(str(source), quote=True)}">Newspapers.com image</a></td>'
            f'<td>{escape(reading)}</td><td><strong>{escape(str(row.get("status", "—")))}</strong><br>{escape(str(row.get("assessment", "—")))}</td>'
            f'<td>{"<br>".join(links)}</td></tr>'
        )
    def table(rows: list[str], caption: str) -> str:
        return ('<div class="early-newspaper-table-wrap" tabindex="0" role="region" aria-label="' + escape(caption) + '"><table><caption>' + escape(caption) + '</caption><thead><tr><th scope="col">Issue</th><th scope="col">Passage read</th><th scope="col">Status and assessment</th><th scope="col">Profiles and drafts</th></tr></thead><tbody>' + ''.join(rows) + '</tbody></table></div>')
    records = groups["confirmed surname"]
    places = groups["place study"]
    exclusions = groups["place or ship"]
    pending = groups["reading pending"]
    counts = f'{len(data["rows"])} catalogued pages · {len(records)} surname records retained · {len(places)} place-study records · {len(exclusions)} place/vessel hits excluded · {len(pending)} readings pending.'
    retained_table = table(records, "Retained Glasgow surname records") if records else '<p>No surname record confirmed in this batch.</p>'
    places_table = ('<h3>Records for place studies</h3><p>These inspected notices concern places in our studies. They are separate from surname evidence and do not establish a Glasgow family connection.</p>' + table(places, "Retained place-study records — not surname evidence")) if places else ''
    exclusions_table = ('<details class="early-newspaper-exclusions"><summary>Excluded search hits (' + str(len(exclusions)) + ') — places and vessels</summary><p>These passages do not name people with the Glasgow surname and are not retained surname records. The log prevents repeating these false matches.</p>' + table(exclusions, "Excluded search hits — not surname records") + '</details>') if exclusions else ''
    pending_table = ('<details><summary>Readings still pending (' + str(len(pending)) + ')</summary>' + table(pending, "Unresolved search hits") + '</details>') if pending else ''
    limitations = " ".join(str(item) for item in data.get("limitations", []))
    return f'''{START}
<section id="early-newspapers" class="early-newspaper-review" aria-labelledby="early-newspapers-heading">
<h2 id="early-newspapers-heading">Glasgow newspaper records for our studies</h2>
<p><strong>{escape(counts)}</strong></p>
<p>{escape(str(data.get("conclusion", "")))}</p>
<p><strong>Scope:</strong> {escape(str(data.get("scope", "")))} <strong>Reviewed:</strong> {escape(str(data.get("reviewed_at", "")))}.</p>
<p class="early-newspaper-limitations"><strong>Limits:</strong> {escape(limitations)}</p>
{retained_table}
{places_table}
{exclusions_table}
{pending_table}
</section>
<style>.early-newspaper-review{{margin:2rem 0}}.early-newspaper-table-wrap{{overflow-x:auto;max-width:100%}}.early-newspaper-review table{{border-collapse:collapse;min-width:60rem;width:100%}}.early-newspaper-review th,.early-newspaper-review td{{border:1px solid #ccd6c5;padding:.55rem;text-align:left;vertical-align:top}}.early-newspaper-review th{{background:#e1f0b4}}</style>
{END}'''


def replace_marked(text: str, section: str) -> str:
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.S)
    if pattern.search(text):
        return pattern.sub(section, text, count=1)
    if "</main>" not in text:
        raise ValueError("main element is missing")
    return text.replace("</main>", section + "\n</main>", 1)


def repair() -> dict[str, int]:
    data = json.loads(SOURCE.read_text(encoding="utf-8"))
    required = {"reviewed_at", "title", "scope", "conclusion", "limitations", "rows"}
    if not required.issubset(data) or not isinstance(data["rows"], list):
        raise ValueError("newspaper review metadata or rows are missing")
    allowed = {"confirmed surname", "place study", "place or ship", "reading pending"}
    if any(row.get("status") not in allowed for row in data["rows"]):
        raise ValueError("every newspaper row needs an allowed reviewed status")
    public = {key: data[key] for key in ("reviewed_at", "title", "scope", "conclusion", "limitations", "rows")}
    public["rows"] = [{key: row[key] for key in PUBLIC_ROW_FIELDS if key in row}
                      for row in data["rows"]]
    public["counts"] = {
        "catalogued_pages": len(public["rows"]),
        "inspected_pages": sum(row["status"] != "reading pending" for row in public["rows"]),
        "retained_surname_records": sum(row["status"] == "confirmed surname" for row in public["rows"]),
        "retained_place_study_records": sum(row["status"] == "place study" for row in public["rows"]),
        "excluded_place_or_vessel_hits": sum(row["status"] == "place or ship" for row in public["rows"]),
        "pending_readings": sum(row["status"] == "reading pending" for row in public["rows"]),
    }
    for row in public["rows"]:
        if not re.fullmatch(r"https://www\.newspapers\.com/image/\d+/", row.get("source_url", "")):
            raise ValueError("use stable original image links without browser credentials")
    (WEB / "data").mkdir(parents=True, exist_ok=True)
    (WEB / "data/glasgow-newspaper-review.json").write_text(json.dumps(public, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    page = WEB / "branches/scottish-families/index.html"
    revised = replace_marked(page.read_text(encoding="utf-8"), render(public))
    if 'id="early-newspapers-jump"' not in revised:
        revised = revised.replace("</h1>", '</h1><p id="early-newspapers-jump"><a href="#early-newspapers">Review early Glasgow newspaper records</a></p>', 1)
    page.write_text(revised, encoding="utf-8")
    sources = WEB / "sources/index.html"
    note = '<p id="early-newspapers-discovery"><a href="/branches/scottish-families/#early-newspapers">Glasgow newspaper records for our studies</a>: verified surname passages, separately labelled place records, identity limits and an excluded-search-hit log.</p>'
    text = sources.read_text(encoding="utf-8")
    if 'id="early-newspapers-discovery"' in text:
        text = re.sub(r'<p id="early-newspapers-discovery">.*?</p>', note, text, count=1, flags=re.S)
    else:
        text = text.replace("</h1>", "</h1>" + note, 1)
    sources.write_text(text, encoding="utf-8")
    try:
        from tools.build_source_collections import repair as repair_collections, ready
    except ModuleNotFoundError:
        from build_source_collections import repair as repair_collections, ready
    if ready(WEB):
        repair_collections(WEB)
    return {"newspaper_pages_inspected": public["counts"]["inspected_pages"],
            "newspaper_surname_records": sum(row["status"] == "confirmed surname" for row in data["rows"]),
            "newspaper_place_study_records": sum(row["status"] == "place study" for row in data["rows"])}


if __name__ == "__main__":
    print(repair())
