#!/usr/bin/env python3
"""Render the curated OPR marriage review in the existing Scottish account."""
from __future__ import annotations

from datetime import date
from html import escape
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "www"
SOURCE = ROOT / "surname-research/indexes/scotlandspeople-opr-marriages-to-1700.json"
START, END = "<!-- opr-marriages-to-1700:start -->", "<!-- opr-marriages-to-1700:end -->"
QUEUE_START, QUEUE_END = "<!-- opr-marriage-identities:start -->", "<!-- opr-marriage-identities:end -->"


def documentary_drafts(data: dict) -> list[dict]:
    """Expose reviewed prose, not internal audit files or raw API responses."""
    drafts = []
    for entry in data.get("new_drafts", []):
        text = (ROOT / entry["path"]).read_text(encoding="utf-8")
        match = re.search(r"```wikitext\s*\n(.*?)\n```", text, re.S | re.I)
        if not match or "== Sources ==" not in match[1]:
            raise ValueError(f"Missing complete WikiTree evidence draft: {entry['path']}")
        drafts.append({
            "id": "opr-marriage-identity-" + "-".join(str(n) for n in entry["rows"]),
            "title": entry["title"], "status": entry["status"],
            "rows": entry["rows"], "assessment": entry["assessment"],
            "draft_wikitext": match[1].strip(),
        })
    return drafts


def render(data: dict) -> str:
    body = []
    drafts_by_row = {n: entry for entry in data.get("documentary_drafts", []) for n in entry["rows"]}
    for row in data["rows"]:
        links = []
        for ident in row.get("profile_ids", []):
            slug = ident.lower()
            href = f"/people/{slug}.html"
            if not (WEB / href.lstrip("/")).exists():
                href = f"https://www.wikitree.com/wiki/{ident}"
            links.append(f'<a href="{escape(href, quote=True)}">{escape(ident)}</a>')
        for ident in row.get('candidate_profile_ids', []):
            href = f'/people/{ident.lower()}.html'
            if not (WEB / href.lstrip('/')).exists():
                href = f'https://www.wikitree.com/wiki/{ident}'
            links.append(f'<a href="{escape(href, quote=True)}">Possible: {escape(ident)}</a>')
        if row.get('identity_review_url'):
            links.append(f'<a href="{escape(row["identity_review_url"], quote=True)}">Current identity draft</a>')
        if row['row'] in drafts_by_row:
            entry = drafts_by_row[row['row']]
            links.append(f'<a href="#{escape(entry["id"])}">Record identity review</a>')
        ref = f"{row['parish_number']}/{row['reference']}"
        when = date.fromisoformat(row["date"]).strftime("%-d %b %Y")
        body.append(
            f'<tr id="{escape(row["id"])}">'
            f'<th scope="row">{escape(row["forename"])} GLASGOW<br>'
            f'<span class="opr-spouse">{escape(row["spouse"])}</span></th>'
            f'<td>{escape(when)}<br>OPR {escape(ref)}</td>'
            f'<td>{escape(row["parish"])}</td>'
            f'<td>{"<br>".join(links) or "Unlinked"}</td>'
            f'<td><strong>{escape(row["status"])}</strong><p>{escape(row["assessment"])}</p></td>'
            f'<td>{escape(row["next_action"])}</td></tr>'
        )
    drafts = []
    for entry in data.get("documentary_drafts", []):
        drafts.append(
            f'<details id="{escape(entry["id"])}" class="opr-marriage-draft"><summary>'
            f'{escape(entry["title"])} · {escape(entry["status"])}</summary>'
            f'<p>{escape(entry["assessment"])}</p>'
            f'<p>Index rows: {", ".join(str(n) for n in entry["rows"])}. '
            'Use the linked existing profile where matched. Compatible candidates remain linked for comparison; do not create a duplicate while identity is unresolved.</p>'
            f'<label for="{escape(entry["id"])}-text">Sourced WikiTree evidence draft</label>'
            f'<textarea id="{escape(entry["id"])}-text" readonly rows="16">{escape(entry["draft_wikitext"])}</textarea></details>'
        )
    draft_section = ('<h3 id="opr-marriage-identity-drafts">Record identity reviews</h3>'
                     '<p>Compatible repeated entries share one handoff. Candidate identities and their tests are kept explicit.</p>'
                     + "".join(drafts)) if drafts else ""
    return f'''{START}
<section id="opr-marriages-to-1700" class="opr-marriage-review" aria-labelledby="opr-marriages-heading">
<h2 id="opr-marriages-heading">Glasgow banns and marriages through 1700</h2>
<p>{escape(data["conclusion"])}</p>
<p>Source: <a href="{escape(data["source_url"], quote=True)}">{escape(data["source_title"])}</a>.
{escape(data["query"])} Reviewed {escape(data["reviewed_at"])} from the supplied index text; original register images have not been inspected for this batch.</p>
<p>The collection combines banns and marriages. An index date alone does not establish a wedding date.
Spouse spellings, alternatives and the explicit “groom surname assumed” warning are preserved below.
The William/Marion Glasgow entries on 10 June 1681 are reciprocal results for one register entry.</p>
<p><a href="/data/scotlandspeople-opr-marriages-to-1700.json">Download the reviewed index (JSON)</a></p>
<label for="opr-marriage-filter">Find a person, spouse, parish or status</label>
<input id="opr-marriage-filter" type="search" placeholder="e.g. Hutcheson, Polwarth, HOLD" aria-controls="opr-marriage-table">
<p id="opr-marriage-count" role="status">{len(body)} of {len(body)} index results</p>
<div class="opr-marriage-table-wrap" tabindex="0" role="region" aria-label="Banns and marriages comparison; scroll horizontally for all columns">
<table id="opr-marriage-table"><caption>All supplied index results with profile assessments</caption>
<thead><tr><th scope="col">Indexed person and spouse</th><th scope="col">Date and reference</th><th scope="col">Parish</th><th scope="col">Profiles</th><th scope="col">Assessment</th><th scope="col">Next action</th></tr></thead>
<tbody>{''.join(body)}</tbody></table></div>
{draft_section}
</section>
<style>
.opr-marriage-review {{ margin: 2rem 0; scroll-margin-top: 5rem; }}
.opr-marriage-review label {{ display: block; font-weight: 600; margin-bottom: .4rem; }}
#opr-marriage-filter {{ width: 100%; max-width: 34rem; padding: .7rem; font: inherit; border: 1px solid #aabca6; border-radius: .3rem; }}
.opr-marriage-table-wrap {{ max-width: 100%; overflow-x: auto; }}
.opr-marriage-review table {{ width: 100%; min-width: 66rem; border-collapse: collapse; }}
.opr-marriage-review th, .opr-marriage-review td {{ border: 1px solid #ccd6c5; padding: .6rem; text-align: left; vertical-align: top; }}
.opr-marriage-review thead th {{ background: #e1f0b4; }}
.opr-marriage-review tbody th {{ font-weight: 600; min-width: 12rem; }}
.opr-marriage-review td p {{ margin: .4rem 0 0; }}
.opr-spouse {{ font-weight: 400; }}
.opr-marriage-review tr[hidden] {{ display: none; }}
.opr-marriage-draft {{ border: 1px solid #ccd6c5; padding: 1rem; margin: .75rem 0; scroll-margin-top: 5rem; }}
.opr-marriage-draft summary {{ cursor: pointer; font-weight: 600; }}
.opr-marriage-draft textarea {{ width: 100%; box-sizing: border-box; padding: .75rem; font: inherit; }}
</style>
<script>
(() => {{
  const input = document.getElementById('opr-marriage-filter');
  const rows = Array.from(document.querySelectorAll('#opr-marriage-table tbody tr'));
  const revealDraft = () => {{
    const draft = document.getElementById(location.hash.slice(1));
    if (draft && draft.classList.contains('opr-marriage-draft')) draft.open = true;
  }};
  addEventListener('hashchange', revealDraft);
  revealDraft();
  input.addEventListener('input', () => {{
    const terms = input.value.toLocaleLowerCase().trim().split(/\\s+/).filter(Boolean);
    let count = 0;
    for (const row of rows) {{
      row.hidden = !terms.every(term => row.textContent.toLocaleLowerCase().includes(term));
      if (!row.hidden) count++;
    }}
    document.getElementById('opr-marriage-count').textContent = `${{count}} of ${{rows.length}} index results`;
  }});
}})();
</script>
{END}'''


def repair() -> dict[str, int]:
    data = json.loads(SOURCE.read_text(encoding="utf-8"))
    if len(data["rows"]) != 55 or any(not row.get("status") for row in data["rows"]):
        raise ValueError("Every supplied marriage row must have a reviewed status before publication")
    data["documentary_drafts"] = documentary_drafts(data)
    data.pop("new_drafts", None)
    page = WEB / "branches/scottish-families/index.html"
    original = page.read_text(encoding="utf-8")
    section = render(data)
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.S)
    if pattern.search(original):
        revised = pattern.sub(lambda _: section, original, count=1)
    else:
        if "</main>" not in original:
            raise ValueError("Scottish families main element is missing")
        revised = original.replace("</main>", section + "\n</main>", 1)
    if 'id="opr-marriages-jump"' not in revised:
        revised, count = re.subn(r"(</h1>)", lambda m: m[0] + '\n<p id="opr-marriages-jump"><a href="#opr-marriages-to-1700">Review the 55 Glasgow banns and marriage results through 1700</a></p>', revised, count=1, flags=re.I)
        if not count:
            raise ValueError("Scottish families heading is missing")
    page.write_text(revised, encoding="utf-8")
    public = WEB / "data/scotlandspeople-opr-marriages-to-1700.json"
    public.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    sources = WEB / "sources/index.html"
    text = sources.read_text(encoding="utf-8")
    note = '<p id="opr-marriages-discovery"><a href="/branches/scottish-families/#opr-marriages-to-1700">Glasgow banns and marriages through 1700</a>: all 55 supplied Scotland’s People index results, matched profiles, new evidence and unresolved identities.</p>'
    if 'id="opr-marriages-discovery"' in text:
        text = re.sub(r'<p id="opr-marriages-discovery">.*?</p>', lambda _: note, text, count=1, flags=re.S)
    else:
        text, count = re.subn(r"(</h1>)", lambda m: m[0] + "\n" + note, text, count=1, flags=re.I)
        if not count:
            raise ValueError("Sources heading is missing")
    sources.write_text(text, encoding="utf-8")
    if data["documentary_drafts"]:
        cards = "".join(
            f'<li><a href="/branches/scottish-families/#{escape(entry["id"])}">{escape(entry["title"])}</a>'
            f' — <strong>{escape(entry["status"])}</strong>: {escape(entry["assessment"])}</li>'
            for entry in data["documentary_drafts"]
        )
        queue = (QUEUE_START + '<section id="opr-marriage-identities" class="r-section"><h2>OPR marriage identities awaiting profiles</h2>'
                 '<p>These documentary identities have dated profile reviews. Their consolidated handoffs distinguish matched profiles, compatible candidates and subjects with no compatible profile found.</p>'
                 '<ul>' + cards + '</ul></section>' + QUEUE_END)
        for relative in ("catalogue.html", "catalogue/index.html"):
            target = WEB / relative
            text = target.read_text(encoding="utf-8")
            pattern = re.compile(re.escape(QUEUE_START) + r".*?" + re.escape(QUEUE_END), re.S)
            if pattern.search(text):
                text = pattern.sub(lambda _: queue, text, count=1)
            else:
                if "</main>" not in text:
                    raise ValueError(f"Catalogue main element missing: {relative}")
                text = text.replace("</main>", queue + "\n</main>", 1)
            target.write_text(text, encoding="utf-8")
    return {"opr_marriage_review_rows": len(data["rows"]), "opr_marriage_identity_drafts": len(data["documentary_drafts"])}


if __name__ == "__main__":
    print(repair())
