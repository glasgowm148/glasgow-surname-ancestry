"""Per-field catalogue colours from saved WikiTree marks and explicit qualifiers."""

import re


FIELDS = {
    "birth": "BirthDate", "birth_location": "BirthLocation",
    "death": "DeathDate", "death_location": "DeathLocation",
}
TREE_STATUS = {"guess": "uncertain", "certain": "certain", "before": "before", "after": "after"}


def field_statuses(person: dict) -> dict:
    """Keep date and place certainty independent; precision alone proves nothing."""
    result = {}
    for field, tree_field in FIELDS.items():
        value = str(person.get(field) or "").strip()
        if not value:
            continue
        marks = {
            TREE_STATUS[mark]
            for capture in person.get("wikitree_evidence") or []
            if (mark := ((capture.get("profile_fields") or {}).get("DataStatus") or {}).get(tree_field)) in TREE_STATUS
        }
        text = f"{value} {person.get(field + '_note') or ''}".casefold()
        if re.search(r"\b(?:uncertain|unproved|probable|possible|disputed|contradicted)\b", text):
            status = "disputed" if re.search(r"\b(?:disputed|contradicted)\b", text) else "uncertain"
        elif re.search(r"\b(?:estimated|approximate|approximately|about|circa)\b|^c\.\s*\d", text):
            status = "estimated"
        elif value.casefold().startswith(("before ", "after ")):
            status = value.split()[0].casefold()
        elif len(marks) > 1:
            status = "uncertain"
        else:
            status = next(iter(marks), "unmarked")
        result[field] = status
    return result
