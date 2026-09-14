"""Public index-only testament entries, distinct from manuscript transcriptions."""

from datetime import date
from html import escape
import re

try:
    from tools.render_transcription_kin_cards import render_kin_card
except ModuleNotFoundError:
    from render_transcription_kin_cards import render_kin_card


def display_date(value):
    try:
        day = date.fromisoformat(str(value))
        return f"{day.day} {day.strftime('%B %Y')}"
    except ValueError:
        return str(value or "Date not supplied")


def record_reference(item):
    return item.get("reference") or item.get("reference_number") or item.get("record", "")


def render_index_confirmation(confirmation):
    if not confirmation:
        return ""
    description = str(confirmation.get("description", ""))
    record_type = confirmation.get("record_type", "")
    record_type = {
        "TD": "Testament dative",
        "TT": "Testament testamentar",
        "TD&Inventory": "Testament dative and inventory",
        "TT&Inventory": "Testament testamentar and inventory",
    }.get(record_type, record_type)
    fields = [
        ("Name in the index", confirmation.get("indexed_name", "")),
        ("Testament date", display_date(confirmation.get("date"))),
        ("Court", confirmation.get("court", "")),
        ("Reference", confirmation.get("reference", "")),
        ("Record type", record_type),
    ]
    facts = "".join(
        ('<div class="tx-confirmation-wide">' if label == "Record type" else '<div>')
        + f'<dt>{escape(label)}</dt><dd>{escape(str(value))}</dd></div>'
        for label, value in fields if value
    )
    return (
        '<section class="tx-index-confirmed" id="index-confirmation" aria-labelledby="index-confirmation-title">'
        '<header class="tx-confirmation-intro">'
        '<p class="tx-confirmation-eyebrow">ScotlandsPeople &middot; Archival index</p>'
        f'<h2 class="tx-confirmation-title" id="index-confirmation-title">{escape(description or "Indexed record")}</h2>'
        '<p class="tx-confirmation-status">Confirmed by the index</p></header>'
        f'<dl class="tx-entry-facts tx-confirmation-facts">{facts}</dl>'
        '<p class="tx-confirmation-note"><strong>Evidence note.</strong> '
        'These details come from the supplied index entry. The testament date is not necessarily the death date. '
        'Unclear handwriting and identities beyond the indexed description are assessed separately below.</p>'
        '</section>'
    )


def render_index_card(item, walkthrough):
    try:
        from tools.render_transcription_compact_cards import render_compact_card
    except ModuleNotFoundError:
        from render_transcription_compact_cards import render_compact_card
    return render_compact_card(item, walkthrough, index_only=True)


def render_index_entry(item, walkthrough):
    fields = [
        ("Indexed date", display_date(item.get("date"))),
        ("Court", item.get("court", "")),
        ("Reference", record_reference(item)),
        ("Record type", item.get("record_type", "")),
    ]
    if item.get("supplementary_date"):
        fields.append(("Supplementary eik", display_date(item["supplementary_date"])))
    facts = "".join(f'<div><dt>{escape(label)}</dt><dd>{escape(str(value))}</dd></div>' for label, value in fields if value)
    return (
        '<section class="tx-index-entry">'
        '<div class="tx-index-notice"><p class="r-kicker">Record details confirmed by the index</p>'
        '<h2>A record to transcribe</h2><p>This entry is included from the supplied ScotlandsPeople wills-index results. '
        'No original image is linked to this catalogue entry yet, and no manuscript transcription is claimed.</p></div>'
        f'<dl class="tx-entry-facts">{facts}</dl>'
        '<section class="tx-index-description" id="passage-index-description"><p class="r-kicker">What the index says</p>'
        f'<blockquote>{escape(item.get("index_description", ""))}</blockquote>'
        '<p>The description above is retained as supplied. Its date is the indexed testament date, not automatically a date of death.</p></section>'
        + render_kin_card(walkthrough)
        + '<section class="tx-index-next"><h2>Next: the original register</h2>'
        '<p>Match the original pages to the court reference, establish the record boundaries, and transcribe the family clauses and remaining text. '
        'The relationships shown here come from the index description and have not yet been checked against the manuscript.</p></section>'
        + f'<p class="tx-index-source">Source: {escape(item.get("index_source", "User-supplied ScotlandsPeople wills index"))}. '
        'The catalogue also retains independently identified records outside this result set.</p></section>'
    )
