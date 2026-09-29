#!/usr/bin/env python3
"""Reject geographic aliases not evidenced by the same person's places."""

from __future__ import annotations

import json
from typing import Any

try:
    from apply_place_gazetteer import (
        PEOPLE_INDEX, SEARCH_INDEX, geographic_aliases, read_people_index, supported_aliases,
    )
    from place_gazetteer import load
except ModuleNotFoundError:  # Imported as tools.check_location_aliases in tests.
    from tools.apply_place_gazetteer import (
        PEOPLE_INDEX, SEARCH_INDEX, geographic_aliases, read_people_index, supported_aliases,
    )
    from tools.place_gazetteer import load


def invalid_aliases(people: list[dict[str, Any]], gazetteer: dict[str, Any]) -> list[tuple[str, list[str]]]:
    labels = geographic_aliases(gazetteer)
    failures = []
    for person in people:
        supported = supported_aliases(person, gazetteer)
        invalid = sorted(set(person.get("location_aliases", [])) & labels - supported, key=str.casefold)
        if invalid:
            failures.append((person.get("id", "<unknown>"), invalid))
    return failures


def main() -> None:
    gazetteer = load()
    catalogue = json.loads(SEARCH_INDEX.read_text(encoding="utf-8"))
    people_index = read_people_index(PEOPLE_INDEX)
    if [person.get("id") for person in catalogue] != [person.get("id") for person in people_index]:
        raise SystemExit("FAIL indexes contain different people")
    if [person.get("location_aliases") for person in catalogue] != [person.get("location_aliases") for person in people_index]:
        raise SystemExit("FAIL location aliases differ")
    failures = invalid_aliases(catalogue, gazetteer)
    print(f"people: {len(catalogue)}; geographic aliases checked: {sum(bool(set(p.get('location_aliases', [])) & geographic_aliases(gazetteer)) for p in catalogue)}; unsupported: {len(failures)}")
    for person_id, aliases in failures[:20]:
        print(f"{person_id}: {', '.join(aliases)}")
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
