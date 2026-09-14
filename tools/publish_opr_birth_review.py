#!/usr/bin/env python3
"""Publish the reviewed Scotland's People OPR births and baptisms index."""
from __future__ import annotations

from datetime import date
from html import escape
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "www"
SOURCE = ROOT / "surname-research/indexes/scotlandspeople-opr-births-to-1700.json"
START, END = "<!-- opr-births-to-1700:start -->", "<!-- opr-births-to-1700:end -->"
QUEUE_START, QUEUE_END = "<!-- opr-birth-identity-drafts:start -->", "<!-- opr-birth-identity-drafts:end -->"


def display_date(value: str) -> str:
    if value == "1700-00-00":
        return "1700 (year assumed; day/month unknown)"
    try:
        return date.fromisoformat(value).strftime("%-d %b %Y")
    except (ValueError, TypeError):
        return value or "—"


def documentary_drafts(data: dict) -> list[dict]:
    drafts = []
    for entry in data.get("new_drafts", []):
        text = (ROOT / entry["path"]).read_text(encoding="utf-8")
        match = re.search(r"```wikitext\s*\n(.*?)\n```", text, re.S | re.I)
        if not match or "== Sources ==" not in match[1]:
            raise ValueError(f"Missing complete WikiTree evidence draft: {entry['path']}")
        drafts.append({"id": "opr-birth-identity-" + "-".join(str(n) for n in entry["rows"]),
                       "title": entry["title"], "status": entry["status"], "rows": entry["rows"],
                       "assessment": entry["assessment"], "draft_wikitext": match[1].strip()})
    return drafts


def render(data: dict) -> str:
    drafts_by_row = {n: e for e in data.get("documentary_drafts", []) for n in e["rows"]}
    body = []
    for row in data["rows"]:
        links = []
        for ident in row.get("profile_ids", []):
            slug = str(ident).lower()
            href = f"/people/{slug}.html" if (WEB / "people" / f"{slug}.html").exists() else f"https://www.wikitree.com/wiki/{ident}"
            links.append(f'<a href="{escape(href, quote=True)}">{escape(str(ident))}</a>')
        if row["row"] in drafts_by_row:
            entry = drafts_by_row[row["row"]]
            links.append(f'<a href="#{escape(entry["id"])}">HOLD handoff</a>')
        ref = f'{row.get("parish_number", "—")}/{row.get("reference", "—")}'
        parent = row.get("parents_other") or "—"
        body.append(f'<tr id="{escape(str(row["id"]))}"><th scope="row">{escape(str(row.get("forename") or "—"))} {escape(str(row.get("surname") or ""))}</th>'
                    f'<td>{escape(str(parent))}<br>Gender: {escape(str(row.get("gender") or "U"))}</td><td>{escape(display_date(row.get("date", "")))}<br>OPR {escape(ref)}</td>'
                    f'<td>{escape(str(row.get("parish") or "—"))}</td><td>{"<br>".join(links) or "Unlinked"}</td>'
                    f'<td><strong>{escape(str(row.get("status") or "—"))}</strong><p>{escape(str(row.get("assessment") or "—"))}</p></td>'
                    f'<td>{escape(str(row.get("next_action") or "—"))}</td></tr>')
    drafts = ''.join(f'<details id="{escape(e["id"])}" class="opr-birth-draft"><summary>{escape(e["title"])} · {escape(e["status"])}</summary><p>{escape(e["assessment"])}</p><p>Index rows: {", ".join(map(str, e["rows"]))}. This handoff is not a created WikiTree profile.</p><label for="{escape(e["id"])}-text">Sourced WikiTree evidence draft</label><textarea id="{escape(e["id"])}-text" readonly rows="16">{escape(e["draft_wikitext"])}</textarea></details>' for e in data.get("documentary_drafts", []))
    draft_section = ('<h3>Identities awaiting a confirmed profile</h3>' + drafts) if drafts else ''
    return f'''{START}<section id="opr-births-to-1700" class="opr-birth-review" aria-labelledby="opr-births-heading"><h2 id="opr-births-heading">Scotland’s People OPR births and baptisms through 1700</h2><p>{escape(data["conclusion"])}</p><p>Source: <a href="{escape(data["source_url"], quote=True)}">{escape(data["source_title"])}</a>. {escape(data["query"])} Reviewed {escape(data["reviewed_at"])} from the supplied index text; original register images have not been inspected for this batch.</p><p>The supplied BirthDate column is an index date, not automatic proof of a birthday. The same reference/date may represent different readings or multiple children; it is not an automatic duplicate-person or twins decision. Exact references are transcribed from the source. Indexed parent text is retained as supplied.</p><p><a href="/data/scotlandspeople-opr-births-to-1700.json">Download the reviewed index (JSON)</a></p><label for="opr-birth-filter">Find a person, parent, parish or status</label><input id="opr-birth-filter" type="search" aria-controls="opr-birth-table"><p id="opr-birth-count" role="status">{len(body)} of {len(body)} index results</p><div class="opr-birth-table-wrap" tabindex="0"><table id="opr-birth-table"><caption>Reviewed births and baptisms index leads</caption><thead><tr><th scope="col">Indexed child</th><th scope="col">Indexed parents/other</th><th scope="col">Date and reference</th><th scope="col">Parish</th><th scope="col">Profiles</th><th scope="col">Assessment</th><th scope="col">Next action</th></tr></thead><tbody>{''.join(body)}</tbody></table></div>{draft_section}</section><style>.opr-birth-review{{margin:2rem 0}}.opr-birth-table-wrap{{overflow-x:auto}}.opr-birth-review table{{border-collapse:collapse;min-width:70rem;width:100%}}.opr-birth-review th,.opr-birth-review td{{border:1px solid #ccd6c5;padding:.6rem;text-align:left;vertical-align:top}}.opr-birth-review th{{background:#e1f0b4}}.opr-birth-review tr[hidden]{{display:none}}.opr-birth-draft{{border:1px solid #ccd6c5;padding:1rem;margin:.75rem 0}}.opr-birth-draft textarea{{width:100%;box-sizing:border-box}}</style><script>(()=>{{const i=document.getElementById('opr-birth-filter'),rs=[...document.querySelectorAll('#opr-birth-table tbody tr')],open=()=>{{const d=document.getElementById(location.hash.slice(1));if(d&&d.classList.contains('opr-birth-draft'))d.open=true}};addEventListener('hashchange',open);open();i.addEventListener('input',()=>{{const ts=i.value.toLowerCase().trim().split(/\\s+/).filter(Boolean),n=rs.filter(r=>{{r.hidden=!ts.every(t=>r.textContent.toLowerCase().includes(t));return !r.hidden}}).length;document.getElementById('opr-birth-count').textContent=`${{n}} of ${{rs.length}} index results`}})}})();</script>{END}'''


def repair() -> dict[str, int]:
    data = json.loads(SOURCE.read_text(encoding="utf-8"))
    if len(data["rows"]) != 127 or any(not r.get("status") for r in data["rows"]):
        raise ValueError("Every supplied birth row must have a reviewed status before publication")
    data["documentary_drafts"] = documentary_drafts(data)
    data.pop("new_drafts", None)
    page = WEB / "branches/scottish-families/index.html"
    text = page.read_text(encoding="utf-8"); section = render(data)
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.S)
    text = pattern.sub(lambda _: section, text, count=1) if pattern.search(text) else text.replace("</main>", section + "\n</main>", 1)
    if 'id="opr-births-jump"' not in text:
        text = re.sub(r"(</h1>)", r'\1\n<p id="opr-births-jump"><a href="#opr-births-to-1700">Review the 127 births and baptisms through 1700</a></p>', text, count=1, flags=re.I)
    page.write_text(text, encoding="utf-8")
    (WEB / "data/scotlandspeople-opr-births-to-1700.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    sources = WEB / "sources/index.html"; st = sources.read_text(encoding="utf-8")
    note = '<p id="opr-births-discovery"><a href="/branches/scottish-families/#opr-births-to-1700">Scotland’s People OPR births and baptisms through 1700</a>: reviewed 127 supplied index results. <a href="/data/scotlandspeople-opr-births-to-1700.json">Download the reviewed index</a>.</p>'
    st = re.sub(r'<p id="opr-births-discovery">.*?</p>', note, st, count=1, flags=re.S) if 'id="opr-births-discovery"' in st else re.sub(r"(</h1>)", r"\1\n" + note, st, count=1, flags=re.I)
    sources.write_text(st, encoding="utf-8")
    if data["documentary_drafts"]:
        cards = ''.join(f'<li><a href="/branches/scottish-families/#{escape(e["id"])}">{escape(e["title"])}</a> — <strong>{escape(e["status"])}</strong>: {escape(e["assessment"])}</li>' for e in data["documentary_drafts"])
        queue = QUEUE_START + '<section id="opr-birth-identity-drafts" class="r-section"><h2>OPR birth identities awaiting profiles</h2><p>These documentary identities use unique birth markers and remain unconfirmed until resolved.</p><ul>' + cards + '</ul></section>' + QUEUE_END
        for relative in ("catalogue.html", "catalogue/index.html"):
            target = WEB / relative
            ct = target.read_text(encoding="utf-8")
            cp = re.compile(re.escape(QUEUE_START) + r".*?" + re.escape(QUEUE_END), re.S)
            ct = cp.sub(lambda _: queue, ct, count=1) if cp.search(ct) else ct.replace("</main>", queue + "\n</main>", 1)
            target.write_text(ct, encoding="utf-8")
    return {"opr_birth_review_rows": len(data["rows"]), "opr_birth_identity_drafts": len(data["documentary_drafts"])}


if __name__ == "__main__":
    print(repair())
