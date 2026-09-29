"""Compact catalogue previews; full evidence remains on the individual cases."""
from functools import lru_cache
from html import escape
import json
from pathlib import Path
import re

try:
    from tools.render_transcription_kin_cards import render_kin_card
except ModuleNotFoundError:
    from render_transcription_kin_cards import render_kin_card


@lru_cache(maxsize=1)
def card_labels():
    path = Path(__file__).resolve().parents[1] / "research/transcriptions/card-labels.json"
    return json.loads(path.read_text(encoding="utf-8"))


def render_compact_card(item, walkthrough, *, preview="", index_only=False, related=False, status=None):
    ident = str(item["id"])
    labels = card_labels().get(ident, {})
    indexed = item.get("index_confirmation", {})
    name = labels.get("name") or indexed.get("indexed_name") or str(item.get("title", ident)).split(":", 1)[0].split(",", 1)[0]
    location = labels.get("location", "")
    year_match = re.search(r"\d{4}", ident) or re.search(r"\d{4}", str(indexed.get("date", item.get("date", ""))))
    year = year_match[0] if year_match else "Undated"
    href = f"/research/transcriptions/{ident}/"
    if related:
        label, action = "Related baptism", "View baptism"
    elif index_only:
        label, action = "Awaiting transcription", "View indexed record"
    else:
        label = {
            "Illustrated manuscript reading": "Illustrated reading",
            "Original supplied; fresh reading pending": "Reading pending",
            "Earlier reading; original not yet matched": "Earlier reading",
        }.get(status, status or "")
        action = "View reading"
    location_html = f'<small class="tx-card-location">{escape(location)}</small>' if location else ""
    status_html = f'<p class="tx-status">{escape(label)}</p>' if label else ""
    preview = preview if ("<img" in preview or "tx-licensed-withheld" in preview) else ""
    return (
        f'<article class="tx-card tx-card-compact" id="{escape(ident, quote=True)}">'
        + preview
        + '<header class="tx-card-heading"><div class="tx-year-block">'
        f'<span>{escape(year)}</span>{location_html}</div><div class="tx-card-title">'
        f'{status_html}<h2><a href="{href}">{escape(name)}</a></h2></div></header>'
        + render_kin_card(walkthrough)
        + f'<a class="tx-case-link" href="{href}">{escape(action)} <span aria-hidden="true">&rarr;</span></a></article>'
    )
