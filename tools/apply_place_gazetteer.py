#!/usr/bin/env python3
"""Apply evidence-backed gazetteer aliases to the two generated people indexes."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    from place_gazetteer import (
        COUNTRY_ALIASES, IRISH_COUNTY_NAMES, KNOWN_COUNTIES, NORTHERN_IRELAND_COUNTIES,
        ROOT, _county_aliases, _county_from_text, _country_from_text, aliases_for_entry,
        aliases_for_text, load,
    )
except ModuleNotFoundError:  # Imported as tools.apply_place_gazetteer in tests.
    from tools.place_gazetteer import (
        COUNTRY_ALIASES, IRISH_COUNTY_NAMES, KNOWN_COUNTIES, NORTHERN_IRELAND_COUNTIES,
        ROOT, _county_aliases, _county_from_text, _country_from_text, aliases_for_entry,
        aliases_for_text, load,
    )


SEARCH_INDEX = ROOT / "www" / "data" / "catalogue-search-index.json"
PEOPLE_INDEX = ROOT / "www" / "data" / "people-index.js"
JS_PREFIX = "window.glasgowPeopleIndex="


def own_places(person: dict[str, Any]) -> list[str]:
    """Return only place strings carried by this catalogue person."""
    return [
        *(value for value in person.get("locations", []) if isinstance(value, str)),
        *(value for value in (person.get("birth_location"), person.get("death_location")) if isinstance(value, str)),
    ]


def supported_aliases(person: dict[str, Any], gazetteer: dict[str, Any]) -> set[str]:
    """Geographic aliases justified by this person, without cross-person pooling."""
    places = own_places(person)
    support = set().union(*(aliases_for_text(place, gazetteer) for place in places)) if places else set()
    text = " ".join(places).casefold()
    for region in (region for region in person.get("regions", []) if isinstance(region, str)):
        support.add(region)
        support.update(COUNTRY_ALIASES.get(region, set()))
    for country in ("Ireland", "Scotland", "England", "Wales", "Northern Ireland", "Ulster", "Republic of Ireland"):
        if country.casefold() in text:
            support.add(country)
            support.update(COUNTRY_ALIASES.get(country, set()))
    for place in places:
        county = _county_from_text(place)
        if not county:
            continue
        support.update(_county_aliases(county))
        country = _country_from_text(place, "Ireland" if county in IRISH_COUNTY_NAMES else "")
        if country == "Ireland":
            support.update(COUNTRY_ALIASES["Ireland"])
            support.update({"Northern Ireland", "Ulster"} if county in NORTHERN_IRELAND_COUNTIES else {"Republic of Ireland"})
    return support


def geographic_aliases(gazetteer: dict[str, Any]) -> set[str]:
    labels = {"Ireland", "Eire", "Éire", "Northern Ireland", "Ulster", "Republic of Ireland", "Scotland", "England", "Wales"}
    for county in KNOWN_COUNTIES:
        labels.update(_county_aliases(county))
    for entry in gazetteer["entries"].values():
        labels.update(aliases_for_entry(entry))
    return labels


def apply_entries(people: list[dict[str, Any]], gazetteer: dict[str, Any]) -> int:
    """Add hierarchy aliases and discard only unsupported geographic leakage."""
    changed = 0
    labels = geographic_aliases(gazetteer)
    for person in people:
        additions = set()
        for place in own_places(person):
            additions.update(aliases_for_text(place, gazetteer))
        aliases = set(person.get("location_aliases", []))
        supported = supported_aliases(person, gazetteer)
        updated = sorted((aliases - labels) | (aliases & supported) | additions, key=str.casefold)
        if updated != person.get("location_aliases", []):
            person["location_aliases"] = updated
            changed += 1
    return changed


def read_people_index(path: Path) -> list[dict[str, Any]]:
    source = path.read_text(encoding="utf-8")
    if not source.startswith(JS_PREFIX):
        raise ValueError(f"Unexpected people index prefix: {path}")
    return json.loads(source[len(JS_PREFIX):].strip().removesuffix(";"))


def write_people_index(path: Path, people: list[dict[str, Any]]) -> None:
    path.write_text(
        JS_PREFIX + json.dumps(people, ensure_ascii=False, separators=(",", ":")) + ";\n",
        encoding="utf-8",
    )


def main() -> None:
    gazetteer = load()
    catalogue_people = json.loads(SEARCH_INDEX.read_text(encoding="utf-8"))
    people_index = read_people_index(PEOPLE_INDEX)
    catalogue_changed = apply_entries(catalogue_people, gazetteer)
    people_changed = apply_entries(people_index, gazetteer)
    if [person.get("id") for person in catalogue_people] != [person.get("id") for person in people_index]:
        raise SystemExit("Generated indexes do not contain the same people in the same order")
    if catalogue_changed:
        SEARCH_INDEX.write_text(json.dumps(catalogue_people, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    if people_changed:
        write_people_index(PEOPLE_INDEX, people_index)
    if [person.get("location_aliases") for person in catalogue_people] != [person.get("location_aliases") for person in people_index]:
        raise SystemExit("Location aliases differ between generated indexes")
    print(f"catalogue changed: {catalogue_changed}; people index changed: {people_changed}")


if __name__ == "__main__":
    main()
