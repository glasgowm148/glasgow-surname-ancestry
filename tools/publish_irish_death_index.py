#!/usr/bin/env python3
"""Publish the maintained Irish civil-death index into existing site pages."""

from __future__ import annotations

import csv
import html
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "surname-research/indexes/irish-civil-deaths-1864-1900.csv"
WEB = ROOT / "www"
PUBLIC_CSV = WEB / "data/irish-civil-deaths-1864-1900.csv"
IRELAND = WEB / "branches/early-ireland/index.html"
SOURCES = WEB / "sources/index.html"
SECTION_START = "<!-- BEGIN IRISH-CIVIL-DEATH-INDEX -->"
SECTION_END = "<!-- END IRISH-CIVIL-DEATH-INDEX -->"
LINK_START = "<!-- BEGIN IRISH-CIVIL-DEATH-INDEX-LINK -->"
LINK_END = "<!-- END IRISH-CIVIL-DEATH-INDEX-LINK -->"
TOP_START = "<!-- BEGIN IRISH-CIVIL-DEATH-INDEX-TOP -->"
TOP_END = "<!-- END IRISH-CIVIL-DEATH-INDEX-TOP -->"
OFFICIAL_SEARCH = "https://www.irishgenealogy.ie/"


def clean_marker(text: str, start: str, end: str) -> str:
    return re.sub(re.escape(start) + r".*?" + re.escape(end), "", text, flags=re.S)


def birth_range(row: dict[str, str]) -> str:
    if row.get("parse_note"):
        return "HOLD"
    try:
        year, age = int(row["death_year"]), int(row["age_at_death"])
    except (KeyError, ValueError):
        return "—"
    return f"{year - age - 1}–{year - age}"


def render(rows: list[dict[str, str]], metadata: dict) -> str:
    body = []
    for row in rows:
        note = row.get("parse_note", "").strip()
        status = "HOLD" if note else row.get("source_status", "index-only").strip() or "index-only"
        body.append(
            "<tr data-search=\"{}\"><td>{}</td><td>{}</td><td>{}</td><td>{}</td>"
            "<td>{}</td><td>{}</td><td>{}</td></tr>".format(
                html.escape(" ".join(str(v) for v in row.values()), quote=True),
                html.escape(row.get("full_name", "")),
                html.escape(row.get("death_year", "")),
                html.escape(row.get("sr_district_reg_area", "")),
                html.escape((row.get("age_at_death", "") + " (unverified)") if note else row.get("age_at_death", "") or "—"),
                birth_range(row),
                html.escape(row.get("group_registration_id", "") or "—"),
                html.escape(status + (f": {note}" if note else "")),
            )
        )
    return f'''{SECTION_START}
<section id="irish-civil-death-index" class="irish-death-index" aria-labelledby="irish-death-index-title">
<style>
#irish-civil-death-index {{ min-width:0; max-width:100%; box-sizing:border-box; margin-top:2.5rem; padding:1.5rem; border:1px solid var(--g-line,#d8ddd4); border-radius:12px; background:var(--g-surface,#fff); }}
#irish-civil-death-index [hidden] {{ display:none !important; }}
#irish-civil-death-index .idi-toolbar {{ display:flex; gap:1rem; align-items:end; flex-wrap:wrap; margin:1rem 0; }}
#irish-civil-death-index label {{ display:grid; gap:.35rem; max-width:36rem; flex:1 1 18rem; }}
#irish-civil-death-index input {{ box-sizing:border-box; width:100%; min-width:0; padding:.65rem .75rem; font:inherit; border:1px solid var(--g-line,#aab3a5); border-radius:6px; }}
#irish-civil-death-index .idi-scroll {{ overflow-x:auto; max-width:100%; border:1px solid var(--g-line,#d8ddd4); border-radius:8px; }}
#irish-civil-death-index table {{ border-collapse:collapse; width:100%; min-width:760px; font-size:.9rem; }}
#irish-civil-death-index th,#irish-civil-death-index td {{ padding:.65rem .7rem; text-align:left; vertical-align:top; border-bottom:1px solid var(--g-line,#e1e5de); }}
#irish-civil-death-index th {{ background:var(--g-soft,#f4f6f1); }}
#irish-civil-death-index .idi-note {{ max-width:75ch; }}
</style>
<span class="r-kicker">Index-only research lead</span>
<h2 id="irish-death-index-title">Irish civil deaths, 1864–1900</h2>
<p class="idi-note">{html.escape(metadata['conclusion'])}</p>
<p class="idi-note">Source collection: <a href="{OFFICIAL_SEARCH}">IrishGenealogy.ie civil deaths</a> (<a href="https://www.irishgenealogy.ie/faq/">index guide</a>). Names and registration identifiers retain the export's spelling. A district is a registration area, not proof of birthplace or exact residence. Birth ranges are calculated from the death year and reported age; inaccurate ages can put the true birth outside that range. Resolve original entries and compare relatives, occupations and residences before assigning profiles.</p>
<p><a href="/data/irish-civil-deaths-1864-1900.csv" download>Download the 241-row lookup list (CSV)</a> · Reviewed {html.escape(metadata['reviewed_at'])}</p>
<div class="idi-toolbar"><label for="idi-filter">Filter the index<input id="idi-filter" type="search" autocomplete="off" placeholder="Name, district, group ID, status…"></label><p id="idi-count" role="status" aria-live="polite">{len(rows)} records</p></div>
<details><summary>Browse {len(rows)} lookup rows</summary><div class="idi-scroll" tabindex="0" role="region" aria-label="Irish death index table"><table><thead><tr><th scope="col">Name</th><th scope="col">Death year</th><th scope="col">District</th><th scope="col">Reported age</th><th scope="col">Approx. birth year range</th><th scope="col">Group ID</th><th scope="col">Status</th></tr></thead><tbody>{''.join(body)}</tbody></table></div></details>
<script>(function(){{const input=document.getElementById('idi-filter'), rows=[...document.querySelectorAll('#irish-civil-death-index tbody tr')], count=document.getElementById('idi-count'); input.addEventListener('input',()=>{{const q=input.value.toLowerCase().trim();let shown=0;rows.forEach(row=>{{const hit=row.dataset.search.toLowerCase().includes(q);row.hidden=!hit;if(hit)shown++;}});count.textContent=`${{shown}} record${{shown===1?'':'s'}}`;if(q)input.closest('section').querySelector('details').open=true;}});}})();</script>
</section>
{SECTION_END}'''


def repair() -> dict[str, int]:
    if not SOURCE.exists():
        raise FileNotFoundError(f"Maintained source is not ready: {SOURCE}")
    with SOURCE.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    required = {"full_name", "death_year", "group_registration_id", "sr_district_reg_area", "age_at_death", "estimated_birth_year", "parse_note", "source_title", "source_url", "source_type", "source_status"}
    if not rows or not required.issubset(rows[0]):
        raise ValueError("Irish death CSV is empty or lacks required columns")
    if len(rows) != 241:
        raise ValueError(f"Expected 241 Irish death-index rows, found {len(rows)}")
    PUBLIC_CSV.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(SOURCE, PUBLIC_CSV)
    metadata = json.loads(SOURCE.with_suffix('.json').read_text(encoding='utf-8'))
    section = render(rows, metadata)
    ireland = clean_marker(IRELAND.read_text(encoding="utf-8"), SECTION_START, SECTION_END)
    ireland = clean_marker(ireland, TOP_START, TOP_END)
    ireland = ireland.replace('</h1>', '</h1>' + TOP_START + '<p><a href="#irish-civil-death-index">Irish civil-death lookup list, 1864–1900</a> — 241 index leads awaiting original-record and identity checks.</p>' + TOP_END, 1)
    if "</main>" not in ireland:
        raise ValueError("Ireland page has no closing main element")
    IRELAND.write_text(ireland.replace("</main>", section + "</main>", 1), encoding="utf-8")
    link = f'''{LINK_START}<aside class="repair-static-note" aria-label="Irish civil-death index"><p><strong>Irish registration lookup list:</strong> <a href="/branches/early-ireland/#irish-civil-death-index">Irish civil deaths, 1864–1900</a> — {len(rows)} recovered index leads, including two malformed rows on HOLD. Original registrations and profile matches remain unverified.</p></aside>{LINK_END}'''
    sources = clean_marker(SOURCES.read_text(encoding="utf-8"), LINK_START, LINK_END)
    if "</h1>" not in sources:
        raise ValueError("Sources page has no main heading")
    SOURCES.write_text(sources.replace("</h1>", "</h1>" + link, 1), encoding="utf-8")
    return {"rows": len(rows), "pages": 2, "download": 1}


if __name__ == "__main__":
    print(repair())
