#!/usr/bin/env python3
"""Add no-JavaScript evidence summaries to generated source-reader pages."""

from __future__ import annotations

import html
import json
from collections import OrderedDict
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


def availability(doc: dict) -> str:
    image = doc.get("image")
    extract = bool(doc.get("transcription")) or bool((doc.get("annotations") or {}).get("lines"))
    if isinstance(image, dict) and image.get("url"):
        return "A public image or document is supplied with this source item" + (", alongside a published extract." if extract else ".")
    if isinstance(image, str) and image:
        return "A public image or document is supplied with this source item" + (", alongside a published extract." if extract else ".")
    if extract:
        return "A published extract or transcription is available here; no local image is attached to this source item."
    if doc.get("url"):
        return "This page publishes catalogue citations and assessments, but no local image or transcription. The cited external archive is the route to the original or its catalogue description."
    return "This page publishes catalogue citations and assessments only; no local image, transcription, or external archive link is attached."


def metadata(parts: list[tuple[str, object]]) -> str:
    values = [f"<li><strong>{esc(label)}:</strong> {esc(value)}</li>" for label, value in parts if value]
    return "<ul class=\"r-caption\">" + "".join(values) + "</ul>" if values else ""


def block(doc: dict) -> str:
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
<section><h2>Published source evidence</h2><p>{esc(availability(doc))}</p>{archive}<h3>Linked people</h3><ul>{people_html}</ul><h3>Citation entries</h3><ul>{citation_html}</ul><h3>Record associations</h3><ul>{record_html}</ul></section>
<section><h2>Assertions and assessments</h2>{assertion_html}{reviewed_html}<p class="r-caption">These are published catalogue assertions and linked claims, not a transcription of the original record. Assessment labels and provenance retain their published status.</p></section>
</section>
{END}'''


def main() -> None:
    changed = 0
    for source_file in SOURCES.glob("*.json"):
        doc = json.loads(source_file.read_text(encoding="utf-8"))
        page = PAGES / source_file.stem / "index.html"
        if not page.exists():
            continue
        text = page.read_text(encoding="utf-8")
        replacement = block(doc)
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
    main()
