#!/usr/bin/env python3
"""Add no-JavaScript evidence summaries to generated source-reader pages."""

from __future__ import annotations

import html
import json
from collections import OrderedDict
from functools import lru_cache
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "www" / "assets" / "v3" / "sources"
PAGES = ROOT / "www" / "sources"
START = "<!-- static-source-evidence:start -->"
END = "<!-- static-source-evidence:end -->"


def esc(value: object) -> str:
    return html.escape(str(value or ""), quote=True)


def person_link(person: str, name: str) -> str:
    page = ROOT / "www" / "people" / f"{person}.html"
    label = esc(name or person)
    return f'<a href="/people/{esc(person)}.html">{label}</a>' if page.exists() else label


IDENTIFIED = ROOT / "research" / "source-library" / "census-reference-overrides.json"
CITATION_ONLY = "Citation only — no transcription yet."


def has_extract(doc: dict) -> bool:
    """A transcription or annotated text; the "[]" placeholder is not one."""
    text = doc.get("transcription")
    if isinstance(text, str):
        try:
            text = json.loads(text) if text.strip().startswith("[") else text.strip()
        except ValueError:
            text = text.strip()
    return bool(text) or bool((doc.get("annotations") or {}).get("lines"))


def citation_only(doc: dict) -> bool:
    image = doc.get("image")
    return not (image and (not isinstance(image, dict) or image.get("url"))) and not has_extract(doc) and not doc.get("records")


@lru_cache(maxsize=1)
def identified_records() -> dict:
    if not IDENTIFIED.exists():
        return {}
    return {row["id"]: row["identified"] for row in json.loads(IDENTIFIED.read_text(encoding="utf-8")).get("sources", []) if row.get("identified")}


def availability(doc: dict) -> str:
    image = doc.get("image")
    extract = has_extract(doc)
    if isinstance(image, dict) and image.get("url"):
        return "A public image or document is supplied with this source item" + (", alongside a published extract." if extract else ".")
    if isinstance(image, str) and image:
        return "A public image or document is supplied with this source item" + (", alongside a published extract." if extract else ".")
    if extract:
        return "A published extract or transcription is available here; no local image is attached to this source item."
    if citation_only(doc):
        return CITATION_ONLY + (" The cited external archive is the route to the original or its catalogue description." if doc.get("url") else " No local image, record entry or external archive link is attached; the underlying record still has to be found and transcribed.")
    if doc.get("url"):
        return "This page publishes catalogue citations and assessments, but no local image or transcription. The cited external archive is the route to the original or its catalogue description."
    return "This page publishes catalogue citations and assessments only; no local image, transcription, or external archive link is attached."


def identified_block(found: dict | None, record_pages: dict) -> str:
    if not found:
        return ""
    page = record_pages.get(found.get("record_id"))
    href = f"/sources/{page}/" if page else found.get("source_url") or ""
    label = esc(found.get("label") or found.get("record_id"))
    people = "".join(f"<li>{person_link(ident.lower(), (info or {}).get('name') or ident)} — {esc((info or {}).get('role'))}</li>" for ident, info in (found.get("profiles") or {}).items())
    return (f'<section class="static-source-identified"><h3>Matching record found</h3>'
            f'<p>{f"<a href={chr(34)}{esc(href)}{chr(34)}>{label}</a>" if href else label}</p>'
            f'<p>{esc(found.get("basis"))}</p>' + (f"<ul>{people}</ul>" if people else "") + "</section>")


def metadata(parts: list[tuple[str, object]]) -> str:
    values = [f"<li><strong>{esc(label)}:</strong> {esc(value)}</li>" for label, value in parts if value]
    return "<ul class=\"r-caption\">" + "".join(values) + "</ul>" if values else ""


def block(doc: dict, found: dict | None = None, pages: dict | None = None) -> str:
    if found is None:
        found = identified_records().get(doc.get("id"))
    if found and pages is None:
        pages = record_pages()
    names = {c.get("person"): c.get("name") for c in doc.get("citations", []) if c.get("person")}
    for row in [*doc.get("records", []), *doc.get("events", [])]:
        if row.get("person"):
            names.setdefault(row["person"], row.get("name"))
    people = OrderedDict((person, name) for person, name in names.items() if person)
    citations = doc.get("citations", [])
    assertions = OrderedDict()
    for citation in citations:
        key = (citation.get("assertion") or "", citation.get("evidence_id") or citation.get("id") or "")
        assertions.setdefault(key, citation)
    people_html = "".join(f"<li>{person_link(person, name)}</li>" for person, name in people.items()) or "<li>No linked catalogue person is published.</li>"
    citation_html = "".join(
        "<li>"
        + esc(c.get("type") or "Citation")
        + (f" — {esc(c.get('date'))}" if c.get("date") else "")
        + (f"; {esc(c.get('place'))}" if c.get("place") else "")
        + "</li>"
        for c in citations
    ) or "<li>No separate citation entry is published.</li>"
    assertion_html = "".join(
        f"<article class=\"v3-source-assertion\"><h3>{esc(c.get('type') or 'Source assertion')}</h3>"
        f"<p>{esc(c.get('assertion') or 'No assertion text supplied.')}</p>"
        + metadata([("Evidence status", c.get("status")), ("Source quality", c.get("quality")), ("Independence group", c.get("independence_group")), ("Source reference", (c.get("source") or {}).get("reference"))])
        + ("<ul>" + "".join(
            f"<li>{esc(claim.get('claim') or claim.get('text'))}"
            + metadata([("Assessment", claim.get("status_label") or claim.get("status")), ("Provenance", claim.get("provenance")), ("Assessment note", claim.get("notes"))])
            + "</li>" for claim in c.get("claims", []) if claim.get("claim") or claim.get("text")) + "</ul>" if c.get("claims") else "")
        + "</article>"
        for c in assertions.values()
    ) or "<p>No source assertion is published.</p>"
    record_html = "".join(
        f"<li><strong>{esc(row.get('name') or row.get('person'))}</strong>"
        f" — {esc(row.get('association') or row.get('label') or 'Association')}"
        + (f"; {esc(row.get('date'))}" if row.get("date") else "")
        + (f"; {esc(row.get('place'))}" if row.get("place") else "")
        + (f"; assessment: {esc(row.get('status'))}" if row.get("status") else "")
        + "</li>"
        for row in doc.get("records", [])
    ) or "<li>No separate record association is published.</li>"
    reviewed_events = [event for event in doc.get("events", []) if event.get("basis") == "reviewed_event_role"]
    reviewed_html = "".join(
        f"<article class=\"v3-source-assertion\"><h3>{esc(event.get('label') or event.get('event_type') or 'Reviewed assessment')}</h3>"
        f"<p>{esc(event.get('note') or 'No assessment note supplied.')}</p>"
        + metadata([("Assessment", event.get("status")), ("Basis", event.get("basis")), ("Date", event.get("date")), ("Place", event.get("place"))])
        + "</article>" for event in reviewed_events
    )
    url = doc.get("url")
    archive = f'<p><a href="{esc(url)}" target="_blank" rel="noopener noreferrer">Open cited archive ↗</a></p>' if url else ""
    return f'''{START}
<section class="v3-reader-bottom static-source-evidence" aria-label="Published source evidence">
<section><h2>Published source evidence</h2><p{' class="static-source-citation-only"' if citation_only(doc) and not found else ''}>{esc(CITATION_ONLY + " The record it cites has been found and is linked below." if found and citation_only(doc) else availability(doc))}</p>{identified_block(found, pages or {})}{archive}<h3>Linked people</h3><ul>{people_html}</ul><h3>Citation entries</h3><ul>{citation_html}</ul><h3>Record associations</h3><ul>{record_html}</ul></section>
<section><h2>Assertions and assessments</h2>{assertion_html}{reviewed_html}<p class="r-caption">These are published catalogue assertions and linked claims, not a transcription of the original record. Assessment labels and provenance retain their published status.</p></section>
</section>
{END}'''


@lru_cache(maxsize=1)
def record_pages() -> dict:
    path = ROOT / "www" / "data" / "records-index.json"
    if not path.exists():
        return {}
    return {r["record_id"]: r["document_id"] for r in json.loads(path.read_text(encoding="utf-8")) if r.get("document_id")}


def main(ids: list[str] | None = None) -> None:
    changed = 0
    found = identified_records()
    pages = record_pages() if found else {}

    files = [SOURCES / f"{i}.json" for i in ids] if ids else SOURCES.glob("*.json")
    for source_file in files:
        doc = json.loads(source_file.read_text(encoding="utf-8"))
        page = PAGES / source_file.stem / "index.html"
        if not page.exists():
            continue
        text = page.read_text(encoding="utf-8")
        replacement = block(doc, found.get(source_file.stem), pages)
        if START in text:
            before, rest = text.split(START, 1)
            _, after = rest.split(END, 1)
            updated = before + replacement + after
        else:
            marker = '<div id="v3-reader"'
            if marker not in text:
                raise RuntimeError(f"Source reader marker missing: {page}")
            updated = text.replace(marker, replacement + "\n" + marker, 1)
        if updated != text:
            page.write_text(updated, encoding="utf-8")
            changed += 1
    print(f"Updated {changed} static source pages.")


if __name__ == "__main__":
    import sys
    main(sys.argv[1:] or None)
