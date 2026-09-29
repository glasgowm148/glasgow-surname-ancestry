#!/usr/bin/env python3
"""Remove location aliases leaked from unmapped records in the generated search index.

Until 24 Sep 2026, ``build_family_map.location_search_index`` pooled every
record without a ``location_id`` under the empty id.  Each person with an
unmapped record therefore inherited the regions/counties of all the others,
so e.g. Midlothian-only people matched a catalogue location search for
"Ireland".  The builders are fixed; this repairs the already generated
``catalogue-search-index.json`` and ``people-index.js`` without a full rebuild.

A pooled alias is kept only when the person's own recorded places or regions
support it.  Aliases from real mapped locations are never touched.
"""

from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from build_family_map import NORTHERN_IRELAND_COUNTIES, location_search_index  # noqa: E402

WEB = ROOT / "www"
JSON_INDEX = WEB / "data" / "catalogue-search-index.json"
JS_INDEX = WEB / "data" / "people-index.js"
JS_PREFIX = "window.glasgowPeopleIndex="


def pooled_aliases() -> set[str]:
    """Exactly the aliases the old code attached to the empty location id."""
    rows = list(csv.DictReader(open(WEB / "map/data/records.csv", encoding="utf-8-sig")))
    pooled = [{**row, "location_id": "__unmapped__"} for row in rows if not row["location_id"]]
    return set(location_search_index(pooled).get("__unmapped__", []))


def supported(alias: str, person: dict, other_aliases: set[str]) -> bool:
    places = " ".join([*(person.get("locations") or []), person.get("birth_location") or "", person.get("death_location") or ""]).lower()
    regions = set(person.get("regions") or [])
    if alias in {"Ireland", "Eire", "Éire"}:
        return "Ireland" in regions or "ireland" in places
    if alias in {"Northern Ireland", "Ulster"}:
        return any(county.lower() in places or county in other_aliases for county in NORTHERN_IRELAND_COUNTIES)
    if alias == "Republic of Ireland":
        return "Republic of Ireland" in other_aliases
    county = re.sub(r"^(?:County|Co\.?)\s+", "", alias)
    if county != alias or alias in {"Antrim", "Down", "Armagh", "Tyrone", "Fermanagh", "Londonderry", "Donegal"}:
        return county.lower() in places
    return alias in regions or alias.lower() in places


def repair(people: list[dict], leaked: set[str]) -> int:
    changed = 0
    for person in people:
        aliases = person.get("location_aliases") or []
        others = {alias for alias in aliases if alias not in leaked}
        kept = [alias for alias in aliases if alias not in leaked or supported(alias, person, others)]
        if kept != aliases:
            person["location_aliases"] = kept
            changed += 1
    return changed


def main() -> None:
    leaked = pooled_aliases()
    people = json.loads(JSON_INDEX.read_text(encoding="utf-8"))
    changed = repair(people, leaked)
    JSON_INDEX.write_text(json.dumps(people, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    js = JS_INDEX.read_text(encoding="utf-8")
    body = js[len(JS_PREFIX):].rstrip().rstrip(";")
    embedded = json.loads(body)
    changed_js = repair(embedded, leaked)
    JS_INDEX.write_text(JS_PREFIX + json.dumps(embedded, ensure_ascii=False, separators=(",", ":")) + ";\n", encoding="utf-8")
    print(f"pooled aliases: {sorted(leaked)}")
    print(f"repaired {changed} people in {JSON_INDEX.name}, {changed_js} in {JS_INDEX.name}")


if __name__ == "__main__":
    main()
