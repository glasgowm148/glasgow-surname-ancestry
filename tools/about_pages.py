#!/usr/bin/env python3
"""Reader text for the correction (feedback) and status pages.

``tools/build_research_catalog.py::_write_support_pages`` calls these
renderers during a full catalogue build.  ``apply_to_site()`` puts the same
text into the already built pages so the change can be applied without a
full build:

    .venv/bin/python -m tools.about_pages

The status page reads only ``www/health.json`` (written by the catalogue
build), the same totals that About, statistics and the people search show.
"""
from __future__ import annotations

from datetime import date
from html import escape
import json
from pathlib import Path
import re

try:
    from tools import site_identity as identity
except ModuleNotFoundError:  # run as a plain script from tools/
    import site_identity as identity

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "www"


def reader_date(value: str | None) -> str:
    """'2026-09-27' -> '27 September 2026'; unknown values pass through."""
    try:
        day = date.fromisoformat(str(value or "")[:10])
    except ValueError:
        return str(value or "")
    return f"{day.day} {day:%B %Y}"


def export_description(export_version: str | None) -> str:
    """Describe the WikiTree export without printing its internal file name."""
    match = re.search(r"(\d{4}-\d{2}-\d{2})", str(export_version or ""))
    if match:
        return f"the WikiTree export of {reader_date(match[1])}"
    return "the WikiTree export used for this build"


def load_health(web: Path = WEB) -> dict:
    return json.loads((web / "health.json").read_text(encoding="utf-8"))


def headline_totals(health: dict) -> tuple[int, int, int]:
    """People, record entries and places: the one set of site-wide totals."""
    counts = health["counts"]
    return counts["people"], counts["records"], counts["places"]


def render_status_body(health: dict) -> str:
    counts = health.get("counts", {})
    links = health.get("source_links", {})
    people, records, places = headline_totals(health)
    cards = (
        ("People in the index", people),
        ("Record entries linked to people", records),
        ("Places", places),
        ("People with written research notes", counts.get("substantive_findings_files", 0)),
        ("Possible duplicate pairs to compare", counts.get("possible_duplicate_comparisons", 0)),
    )
    card_html = "".join(
        f'<div class="status-card"><strong>{value:,}</strong><span>{escape(label)}</span></div>'
        for label, value in cards)
    explicit, candidate, unresolved = (links.get(key, 0) for key in ("explicit", "candidate", "unresolved"))
    source_html = "".join(
        f'<div class="status-card"><strong>{value:,}</strong><span>{escape(label)}</span></div>'
        for label, value in (("Source cited", explicit), ("Possible source match", candidate),
                             ("Source still to be added", unresolved)))
    return (
        '<p class="kicker">About the data</p><h1>Catalogue status</h1>'
        f'<p class="lede">These totals come from the catalogue compiled on {escape(reader_date(health.get("generated")))} '
        f'from {escape(export_description(health.get("source_export")))}. The About page, the statistics page and '
        'the people search use the same totals.</p>'
        f'<div class="status-grid">{card_html}</div>'
        '<section id="record-sources"><h2>Sources for each record entry</h2>'
        '<p>A record entry links a person to a record. '
        f'{explicit:,} entries cite their source directly. {candidate:,} have a possible match in the source library '
        f'that still needs checking. {unresolved:,} still need their source added. This is a measure of how far the '
        'linking work has gone, not of how many records are missing.</p>'
        f'<div class="status-grid">{source_html}</div></section>'
        '<section><h2>What these numbers do not show</h2><p>They describe what the catalogue contains, not whether '
        'every family relationship is correct. A possible source match is a lead until someone has checked it.</p>'
        '<p><a href="/coverage/">About the data</a> · <a href="/statistics/">Statistics</a> · '
        '<a href="/changes/">Change log</a></p>'
        '<p><a href="/health.json">Download these totals (JSON)</a> · '
        '<a href="/data/source-review.csv">Entries waiting for a source check (CSV)</a></p></section>'
    )


FEEDBACK_SCRIPT = """<script>(()=>{const p=new URLSearchParams(location.search).get('person')||'';const line=document.querySelector('#feedback-person-line');const label=document.querySelector('#feedback-person');const link=document.querySelector('#feedback-wikitree');const text=document.querySelector('#feedback-template');if(p){label.textContent=p;line.hidden=false}if(/^[A-Za-z][A-Za-z_'’-]*-\\d+$/.test(p)){link.href='https://www.wikitree.com/wiki/'+encodeURIComponent(p);link.hidden=false}text.value=`Person or page: ${p||'[name, dates or page link]'}\\nPage link: ${p?location.href:'[paste the page address]'}\\nWhat is wrong, and what should it say:\\n\\nThe record (archive, reference, date) or how you know:\\n\\n`;const copy=document.querySelector('#feedback-copy');copy.addEventListener('click',async()=>{try{await navigator.clipboard.writeText(text.value);copy.textContent='Copied'}catch(error){text.select();copy.textContent='Selected: press Ctrl+C or ⌘C to copy'}});})();</script>"""


def render_feedback_body() -> str:
    if identity.CONTACT_URL:
        email = identity.contact_email()
        route = (f'Email it to {identity.contact_link_html(email)}.' if email
                 else f'Send it with {identity.contact_link_html("the correction form")}.')
        send = (f'<p>{route} Photographs or scans of records are welcome.</p>'
                f'<div class="actions">{identity.contact_link_html("Send a correction", "button")}</div>')
    else:
        send = (
            '<p>A direct contact route for corrections is being set up. Until it is ready you can raise a correction '
            f'with the <a href="{identity.WIKITREE_STUDY_URL}">{escape(identity.WIKITREE_STUDY_NAME)}</a> or in the '
            f'<a href="{identity.DISCUSSION_GROUP_URL}">{escape(identity.DISCUSSION_GROUP_NAME)}</a>. '
            'If the person has a WikiTree profile, you can also add a sourced correction there.</p>')
    return (
        '<p class="kicker">Corrections and new evidence</p><h1>Report a correction</h1>'
        '<p class="lede">Found a mistake, or hold a record, photograph or family paper that would help? '
        'Corrections and new evidence are welcome.</p>'
        '<p id="feedback-person-line" hidden>About: <strong id="feedback-person"></strong></p>'
        '<section id="what-to-include"><h2>What a useful correction contains</h2><ul>'
        '<li>The person’s name and dates, or the address of their page on this site.</li>'
        '<li>The detail that is wrong, and what you think it should say.</li>'
        '<li>The record that shows it: the archive or website, the reference and the date, or a photograph of it. '
        'If you know it from family papers or memory, say so.</li>'
        '<li>Please do not send details of people who may still be living.</li></ul></section>'
        f'<section id="how-to-send"><h2>How to send it</h2>{send}</section>'
        '<section id="wikitree-profile"><h2>If the person is on WikiTree</h2><p>Adding the sourced correction to the '
        'WikiTree profile, or telling its managers, keeps the shared tree and this site in step.</p>'
        '<div class="actions"><a id="feedback-wikitree" class="button" hidden>Open the WikiTree profile</a></div></section>'
        '<section id="prepare"><h2>Prepare your message</h2><p>Fill in this outline and copy it into your message.</p>'
        '<textarea id="feedback-template" class="feedback-template" rows="10" aria-label="Correction outline"></textarea>'
        '<p><button id="feedback-copy" class="button" type="button">Copy the outline</button></p></section>'
        + identity.who_runs_this_html(include_contact=False)
    )


def _replace_main(page: str, body: str) -> str:
    match = re.search(r"(<main\b[^>]*>)(.*?)(</main>)", page, re.S)
    if not match:
        raise ValueError("page has no <main>")
    return page[:match.start(2)] + body + page[match.end(2):]


def apply_to_site(web: Path = WEB) -> dict[str, int]:
    """Refresh the built feedback and status pages in place."""
    changed = 0
    health = load_health(web)
    for route in ("feedback.html", "feedback/index.html", "status.html", "status/index.html"):
        path = web / route
        if not path.exists():
            continue
        page = path.read_text(encoding="utf-8")
        if "data-clean-route-redirect" in page:
            continue
        if route.startswith("feedback"):
            updated = _replace_main(page, render_feedback_body())
            updated = re.sub(r"<script>\(\(\)=>\{const p=new URLSearchParams.*?</script>",
                             lambda _: FEEDBACK_SCRIPT, updated, count=1, flags=re.S)
        else:
            updated = _replace_main(page, render_status_body(health))
        if updated != page:
            path.write_text(updated, encoding="utf-8")
            changed += 1
    return {"about_pages": changed}


if __name__ == "__main__":
    print(apply_to_site())
