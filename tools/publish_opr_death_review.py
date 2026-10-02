#!/usr/bin/env python3
"""Publish the reviewed Scotland's People OPR death index into existing site views.

The source JSON is curated by the researcher.  This helper only renders that
safe, reviewed subset; it does not call an API or expose an API capture.
"""
from __future__ import annotations

import argparse
import html
import json
import re
from datetime import date
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "surname-research/indexes/scotlandspeople-opr-deaths-to-1700.json"
PUBLIC = ROOT / "www/data/scotlandspeople-opr-deaths-to-1700.json"
FAMILY = ROOT / "www/branches/scottish-families/index.html"
SOURCES = ROOT / "www/sources/index.html"
START, END = "<!-- opr-deaths-to-1700:start -->", "<!-- opr-deaths-to-1700:end -->"
PERSON_ID = "Glasgow-3056"
PERSON_JSON = ROOT / "www/people/glasgow-3056.json"
PERSON_HTML = ROOT / "www/people/glasgow-3056.html"
PEOPLE_INDEX = ROOT / "www/data/people-index.json"
CATALOGUE_INDEX = ROOT / "www/data/catalogue-search-index.json"
PEOPLE_INDEX_JS = ROOT / "www/data/people-index.js"
DEATH_QUALIFICATION = (
    "Uncertain retained date and place: OPR 668/70/653 does not identify John "
    "as the deceased (opr-668-70-653)."
)


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")


def qualify_glasgow_3056() -> None:
    """Publish the reviewed qualification without changing the imported snapshot."""
    dossier = json.loads(PERSON_JSON.read_text(encoding="utf-8"))
    death = dossier["vitals"]["death"]
    death["status"] = "uncertain"
    death["source_qualification"] = DEATH_QUALIFICATION
    write_json(PERSON_JSON, dossier)

    people = json.loads(PEOPLE_INDEX.read_text(encoding="utf-8"))
    row = next(item for item in people if item["id"] == PERSON_ID)
    row["death_status"] = "uncertain"
    write_json(PEOPLE_INDEX, people)

    catalogue = json.loads(CATALOGUE_INDEX.read_text(encoding="utf-8"))
    row = next(item for item in catalogue if item["id"] == PERSON_ID.lower())
    row["death_status"] = "uncertain"
    row["death_note"] = DEATH_QUALIFICATION
    row["death_location_note"] = DEATH_QUALIFICATION
    write_json(CATALOGUE_INDEX, catalogue)
    PEOPLE_INDEX_JS.write_text(
        "window.glasgowPeopleIndex=" + json.dumps(catalogue, ensure_ascii=False, separators=(",", ":")) + ";\n",
        encoding="utf-8",
    )

    original = PERSON_HTML.read_text(encoding="utf-8")
    soup = BeautifulSoup(original, "html.parser")
    replacements: list[tuple[str, str]] = []

    title = soup.select_one(".v3-person-header .v3-title-line h1")
    title_detail = title.find_next_sibling("p") if title else None
    if title_detail:
        before = str(title_detail)
        title_detail.string = "9 September 1617 – 14 February 1670 (uncertain; unproved as John's death)"
        replacements.append((before, str(title_detail)))

    vital = next((item for item in soup.select(".v3-vitals > div")
                  if item.find("dt") and item.find("dt").get_text(strip=True) == "Death"), None)
    if vital and vital.find("dd"):
        detail = vital.find("dd")
        before = str(detail)
        detail.clear()
        detail.append("14 February 1670 — uncertain; unproved as John's death")
        place = soup.new_tag("span")
        place.string = "Linlithgow, Linlithgowshire, Scotland — retained uncertain"
        detail.append(place)
        replacements.append((before, str(detail)))

    event = next((item for item in soup.select(".v3-life-event")
                  if item.find("h3") and item.find("h3").get_text(strip=True) == "Death"), None)
    if event:
        event_time = event.find("time")
        status = event.select_one(".v3-status")
        if event_time:
            before = str(event_time)
            event_time.string = "14 February 1670 (uncertain)"
            replacements.append((before, str(event_time)))
        if status:
            before = str(status)
            status["data-status"] = "uncertain"
            status.string = "Retained date uncertain; unproved as John's death"
            replacements.append((before, str(status)))

    for before, after in replacements:
        if before != after:
            if before not in original:
                raise RuntimeError("Expected public death display fragment was not found")
            original = original.replace(before, after, 1)
    PERSON_HTML.write_text(original, encoding="utf-8")


def load() -> dict:
    return json.loads(SOURCE.read_text(encoding="utf-8"))


def display_date(value: str) -> str:
    try:
        return date.fromisoformat(value).strftime("%-d %b %Y")
    except (ValueError, TypeError):
        return value or "—"


def profile_links(ids: list[str]) -> str:
    out = []
    for ident in ids or []:
        slug = str(ident).strip().lower()
        if not slug:
            continue
        target = ROOT / "www/people" / f"{slug}.html"
        label = html.escape(str(ident))
        if target.exists():
            out.append(f'<a href="/people/{html.escape(slug)}.html">{label}</a>')
        else:
            out.append(label)
    return ", ".join(out) or "—"


def render_section(data: dict) -> str:
    rows = data.get("rows", [])
    body = []
    for row in rows:
        name = " ".join(x for x in (row.get("forename"), row.get("surname")) if x)
        details = row.get("other_details") or "—"
        ref = f"{row.get('parish_number', '—')}/{row.get('reference') or '—'}"
        date_ref = f"{display_date(row.get('date', ''))} · {ref}"
        body.append(
            "<tr>"
            f"<td>{html.escape(name or '—')}</td>"
            f"<td>{html.escape(str(details))}</td>"
            f"<td>{html.escape(date_ref)}</td>"
            f"<td>{html.escape(str(row.get('parish') or '—'))}</td>"
            f"<td>{profile_links(row.get('profile_ids', []))}</td>"
            f"<td>{html.escape(str(row.get('status') or '—'))}</td>"
            f"<td>{html.escape(str(row.get('assessment') or '—'))}</td>"
            f"<td>{html.escape(str(row.get('next_action') or '—'))}</td>"
            "</tr>"
        )
    title = html.escape(str(data.get("source_title") or "Scotland’s People OPR death review"))
    url = html.escape(str(data.get("source_url") or "#"), quote=True)
    query = html.escape(str(data.get("query") or ""))
    conclusion = html.escape(str(data.get("conclusion") or ""))
    return f'''{START}
<section id="opr-deaths-to-1700" class="opr-death-review" aria-labelledby="opr-deaths-heading">
<h2 id="opr-deaths-heading">Scotland’s People OPR deaths to 1700</h2>
<p>{conclusion}</p>
<p class="opr-death-source">Source: <a href="{url}">{title}</a>. Query: {query}</p>
<div class="opr-table-wrap" tabindex="0" role="region" aria-label="Death and burial index comparison"><table><caption>Reviewed death and burial index leads</caption><thead><tr><th scope="col">Name</th><th scope="col">Other details</th><th scope="col">Date · OPR reference</th><th scope="col">Parish</th><th scope="col">Profiles</th><th scope="col">Status</th><th scope="col">Assessment</th><th scope="col">Next action</th></tr></thead><tbody>{''.join(body)}</tbody></table></div>
</section>
<style>
.opr-death-review {{ margin: 2rem 0; }}
.opr-death-source {{ font-size: .95em; }}
.opr-table-wrap {{ overflow-x: auto; max-width: 100%; }}
.opr-death-review table {{ border-collapse: collapse; min-width: 68rem; width: 100%; }}
.opr-death-review th, .opr-death-review td {{ border: 1px solid #ccd6c5; padding: .45rem .55rem; text-align: left; vertical-align: top; }}
.opr-death-review th {{ background: #e1f0b4; }}
@media (max-width: 700px) {{ .opr-death-review {{ margin: 1.25rem 0; }} .opr-death-review table {{ font-size: .9rem; }} }}
</style>
{END}'''


def replace_section(path: Path, section: str) -> None:
    text = path.read_text(encoding="utf-8")
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.S)
    if pattern.search(text):
        text = pattern.sub(section, text, count=1)
    else:
        pos = text.lower().rfind("</main>")
        if pos < 0:
            raise RuntimeError(f"No </main> in {path}")
        text = text[:pos] + section + "\n" + text[pos:]
    path.write_text(text, encoding="utf-8")


def repair(*, qualify_person: bool = True, web: Path | None = None) -> dict[str, int]:
    data = load()
    public_path = web / 'data/scotlandspeople-opr-deaths-to-1700.json' if web else PUBLIC
    family_path = web / 'branches/scottish-families/index.html' if web else FAMILY
    sources_path = web / 'sources/index.html' if web else SOURCES
    if qualify_person:
        qualify_glasgow_3056()
    public_path.parent.mkdir(parents=True, exist_ok=True)
    public = {k: data.get(k) for k in ("reviewed_at", "source_title", "source_url", "query", "conclusion", "rows")}
    public_path.write_text(json.dumps(public, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    replace_section(family_path, render_section(data))
    family = family_path.read_text(encoding="utf-8")
    jump = '<p id="opr-deaths-jump"><a href="#opr-deaths-to-1700">Review the seven Glasgow death and burial entries through 1700</a></p>'
    if 'id="opr-deaths-jump"' not in family:
        family, count = re.subn(r'(</h1>)', lambda m: m[0] + "\n" + jump, family, count=1, flags=re.I)
        if not count:
            raise RuntimeError(f"No h1 in {FAMILY}")
        family_path.write_text(family, encoding="utf-8")
    sources = sources_path.read_text(encoding="utf-8")
    note = '<p id="opr-deaths-to-1700-discovery">The <a href="/branches/scottish-families/#opr-deaths-to-1700">Scotland’s People OPR deaths and burials review</a> compares all seven supplied entries through 1700 with existing profiles, distinguishing confirmed citations, probable matches and unresolved identities. <a href="/data/scotlandspeople-opr-deaths-to-1700.json">Download the reviewed index (JSON)</a>.</p>'
    if "id=\"opr-deaths-to-1700-discovery\"" in sources:
        sources = re.sub(r'<p id="opr-deaths-to-1700-discovery">.*?</p>', note, sources, count=1, flags=re.S)
    else:
        pos = re.search(r'</h1>', sources, re.I)
        if not pos:
            raise RuntimeError(f"No h1 in {SOURCES}")
        sources = sources[:pos.end()] + "\n" + note + sources[pos.end():]
    sources_path.write_text(sources, encoding="utf-8")
    return {"opr_death_review_rows": len(data.get("rows", []))}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("repair", nargs="?", choices=["repair"], default="repair")
    parser.parse_args()
    repair()
