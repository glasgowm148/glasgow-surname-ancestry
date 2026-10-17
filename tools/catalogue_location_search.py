#!/usr/bin/env python3
"""Public-safe location, biography and field-status catalogue search metadata."""

from __future__ import annotations

import json
import re
from pathlib import Path

try:
    from catalogue_field_status import FIELDS, field_statuses
except ModuleNotFoundError:
    from tools.catalogue_field_status import FIELDS, field_statuses

try:
    from dossier_resolution import GENERATED_ANSWERS
except ModuleNotFoundError:
    from tools.dossier_resolution import GENERATED_ANSWERS


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "www"
DATA = WEB / "data"
JS_PREFIX = "window.glasgowPeopleIndex="


def _unique(values):
    seen = set()
    return [value for value in values if value and value not in seen and not seen.add(value)]


def _plain_markdown(value: object) -> str:
    """Keep readable public prose while dropping markup and link destinations."""
    text = str(value or "")
    text = re.sub(r"!?(?:\[([^\]]*)\]\([^)]*\))", r"\1", text)
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"[*_#>]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def biography_text(dossier: dict) -> str:
    """Return only narrative that is already approved for the public dossier."""
    presentation = dossier.get("presentation") or {}
    values = [presentation.get("opening")]
    position = presentation.get("position") or {}
    answer = position.get("answer")
    if answer and str(answer).strip() not in GENERATED_ANSWERS:
        values.append(answer)
    values.extend(
        point for point in (position.get("points") or []) if isinstance(point, str)
    )
    values.extend(section.get("markdown") for section in presentation.get("biography_sections") or []
                  if isinstance(section, dict))
    return " ".join(_unique(_plain_markdown(value) for value in values))


def marriage_locations(person: dict, dossier: dict) -> list[str]:
    """Use explicit marriage fields or a public event where the person married.

    A marriage which only mentions the person as a parent or witness must not
    become that person's marriage place.
    """
    values = [spouse.get("marriage_location") for spouse in person.get("spouses") or []
              if isinstance(spouse, dict)]
    person_ids = {person.get("catalogue_id"), *(person.get("profile_ids") or [])}
    for event in dossier.get("events") or []:
        if not isinstance(event, dict) or event.get("event_type") != "marriage":
            continue
        roles = {
            str(participant.get("role") or "").casefold()
            for participant in event.get("participants") or []
            if isinstance(participant, dict) and participant.get("id") in person_ids
        }
        if roles & {"bride", "groom", "spouse"}:
            values.append(event.get("place"))
    return _unique(str(value).strip() for value in values if str(value or "").strip())


def enrichment(person: dict, dossier: dict) -> dict:
    statuses = field_statuses(person)
    for review in sorted(dossier.get("research_assessments") or [],
                         key=lambda item: (item.get("reviewed", ""), item.get("id", ""))):
        if review.get("status") != "approved" or review.get("derived_from") != "documentary_chronology":
            continue
        projection = review.get("catalogue_projection") or {}
        statuses.update({field: status for field, status in (projection.get("field_statuses") or {}).items()
                         if field in FIELDS})
    return {
        "field_statuses": statuses,
        "marriage_locations": marriage_locations(person, dossier),
        "biography_text": biography_text(dossier),
    }


def refresh_search_indexes(root: Path = ROOT) -> int:
    """Refresh enrichment in the two browser search artifacts without a build."""
    web = root / "www"
    if not all((web / path).exists() for path in (
        "data/people.json", "data/catalogue-search-index.json", "data/people-index.js",
    )):
        return 0
    people = json.loads((web / "data" / "people.json").read_text(encoding="utf-8"))["people"]
    by_id = {person["catalogue_id"]: person for person in people}
    rows_path = web / "data" / "catalogue-search-index.json"
    rows = json.loads(rows_path.read_text(encoding="utf-8"))
    changed = 0
    for row in rows:
        person = by_id.get(row.get("id"))
        dossier_path = web / "people" / f"{row.get('id')}.json"
        dossier = json.loads(dossier_path.read_text(encoding="utf-8")) if person and dossier_path.exists() else {}
        fields = enrichment(person or {}, dossier)
        if any(row.get(key) != value for key, value in fields.items()):
            row.update(fields)
            changed += 1
    serialized = json.dumps(rows, ensure_ascii=False, separators=(",", ":")) + "\n"
    rows_path.write_text(serialized, encoding="utf-8")
    (web / "data" / "people-index.js").write_text(
        JS_PREFIX + serialized.rstrip() + ";\n", encoding="utf-8"
    )
    return changed


if __name__ == "__main__":
    print(f"refreshed {refresh_search_indexes()} catalogue search rows")
