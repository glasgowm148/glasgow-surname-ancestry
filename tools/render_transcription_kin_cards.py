"""Render explicitly maintained kin groups for transcription preview cards."""

from html import escape


GROUPS = (("spouse", "Spouse"), ("children", "Children"), ("other_kin", "Other kin"))


def render_kin_card(walkthrough):
    """Use documentary kin metadata, never infer family from an estate office."""
    walkthrough = walkthrough or {}
    ident = str(walkthrough.get("id", ""))
    groups = walkthrough.get("card_kin", {})
    index_based = walkthrough.get("card_kin_basis") == "index"
    context = ""
    if index_based:
        subject = walkthrough.get("card_kin_subject", "")
        context = '<p class="tx-kin-kicker">Kin named in the index'
        if subject:
            context += f'<span>Relationships to {escape(str(subject))}</span>'
        context += '</p>'
    rows = []
    for key, label in GROUPS:
        people = []
        for entry in groups.get(key, []):
            name = str(entry.get("name", "")).strip()
            if not name:
                continue
            href = f"/research/transcriptions/{ident}/"
            if entry.get("evidence_study"):
                href += f'#tx-letterform-{ident}-{entry["evidence_study"]}'
            elif entry.get("evidence_step"):
                href += f'#passage-{entry["evidence_step"]}'
            relationship = str(entry.get("relationship", "")).strip()
            note = str(entry.get("note", "")).strip()
            detail = "; ".join(value for value in (relationship, note) if value)
            status = str(entry.get("status", "explicit")).lower()
            qualifier = {
                "probable": "probable relationship",
                "possible": "possible relationship",
                "uncertain": "uncertain relationship",
                "inferred": "inferred relationship",
            }.get(status, "")
            if qualifier and not any(word in detail.lower() for word in ("probable", "possible", "uncertain", "inferred")):
                detail = "; ".join(value for value in (detail, qualifier) if value)
            detail_html = f'<span class="tx-kin-detail"> ({escape(detail)})</span>' if detail else ""
            people.append(f'<li><a href="{escape(href, quote=True)}">{escape(name)}</a>{detail_html}</li>')
        if not people:
            continue
        content = '<ul class="tx-kin-names">' + "".join(people) + "</ul>"
        rows.append(f'<div class="tx-kin-row"><dt>{label}:</dt><dd>{content}</dd></div>')
    if not rows:
        return ""
    basis = "index description" if index_based else "reviewed passages"
    return (f'<section class="tx-kin-card" aria-label="Family relationships in the {basis}">'
            + context + '<dl>' + "".join(rows) + '</dl></section>')
