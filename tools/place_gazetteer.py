#!/usr/bin/env python3
"""Small, evidence-led locality-to-place hierarchy for catalogue search."""

from __future__ import annotations

from collections import Counter, defaultdict
import csv
import json
from pathlib import Path
import re
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PATH = ROOT / "data" / "place-gazetteer.json"
TOKEN_RE = re.compile(r"[^a-z0-9]+")
IRISH_COUNTY_NAMES = {
    "Antrim", "Armagh", "Carlow", "Cavan", "Clare", "Cork", "Donegal", "Down", "Dublin",
    "Fermanagh", "Galway", "Kerry", "Kildare", "Kilkenny", "Laois", "Leitrim", "Limerick",
    "Londonderry", "Longford", "Louth", "Mayo", "Meath", "Monaghan", "Offaly", "Roscommon",
    "Sligo", "Tipperary", "Tyrone", "Waterford", "Westmeath", "Wexford", "Wicklow",
}
OTHER_COUNTY_NAMES = {
    "Aberdeenshire", "Angus", "Argyll", "Ayrshire", "Banffshire", "Berwickshire", "Caithness",
    "Clackmannanshire", "Dumfriesshire", "Dunbartonshire", "East Lothian", "Fife", "Inverness-shire",
    "Kincardineshire", "Kinross-shire", "Lanarkshire", "Midlothian", "Morayshire", "Orkney",
    "Peeblesshire", "Perthshire", "Renfrewshire", "Roxburghshire", "Selkirkshire", "Shetland",
    "Stirlingshire", "Sutherland", "West Lothian", "Wigtownshire", "Buckinghamshire", "Cornwall",
    "Cumberland", "Derbyshire", "Devon", "Dorset", "Durham", "Essex", "Gloucestershire", "Hampshire",
    "Herefordshire", "Hertfordshire", "Kent", "Lancashire", "Leicestershire", "Lincolnshire", "Middlesex",
    "Norfolk", "Northumberland", "Nottinghamshire", "Shropshire", "Somerset", "Staffordshire", "Suffolk",
    "Surrey", "Sussex", "Warwickshire", "Westmorland", "Wiltshire", "Worcestershire", "Anglesey",
    "Breconshire", "Caernarfonshire", "Cardiganshire", "Carmarthenshire", "Denbighshire", "Flintshire",
    "Glamorgan", "Merionethshire", "Monmouthshire", "Montgomeryshire", "Pembrokeshire", "Radnorshire",
}
KNOWN_COUNTIES = IRISH_COUNTY_NAMES | OTHER_COUNTY_NAMES
COUNTY_RE = re.compile(r"\bCounty\s+(?!of\b)(" + "|".join(sorted(KNOWN_COUNTIES, key=len, reverse=True)) + r")\b", re.I)

# These are deliberately few: they cover places commonly written without a
# county in this collection, where a conventional historic county is useful.
CURATED: dict[str, dict[str, Any]] = {
    "belfast": {"name": "Belfast", "county": "Antrim", "country": "Ireland",
                "aliases": ["Northern Ireland", "Ulster"], "provenance": "curated",
                "comment": "Conventional historic-county assignment."},
    "derry": {"name": "Derry", "county": "Londonderry", "country": "Ireland",
              "aliases": ["Northern Ireland", "Ulster"], "provenance": "curated",
              "comment": "City and county are commonly searched under Derry."},
    "londonderry": {"name": "Londonderry", "county": "Londonderry", "country": "Ireland",
                    "aliases": ["Derry", "Northern Ireland", "Ulster"], "provenance": "curated",
                    "comment": "Derry is a common alternative county name."},
    "glasgow": {"name": "Glasgow", "county": "Lanarkshire", "country": "Scotland",
                "aliases": [], "provenance": "curated",
                "comment": "Conventional historic-county assignment."},
    "edinburgh": {"name": "Edinburgh", "county": "Midlothian", "country": "Scotland",
                  "aliases": [], "provenance": "curated",
                  "comment": "Conventional historic-county assignment."},
    "cookstown": {"name": "Cookstown", "county": "Tyrone", "country": "Ireland",
                  "aliases": ["Northern Ireland", "Ulster"], "provenance": "curated",
                  "comment": "Reviewed 26 October 2026: 1,013 of 1,014 records place it in Tyrone; the Meath reading is a name collision."},
    "coleraine": {"name": "Coleraine", "county": "Londonderry", "country": "Ireland",
                  "aliases": ["Northern Ireland", "Ulster"], "provenance": "curated",
                  "comment": "Reviewed 26 October 2026: 8 of 9 records; the Offaly reading is a name collision."},
    "moneymore": {"name": "Moneymore", "county": "Londonderry", "country": "Ireland",
                  "aliases": ["Northern Ireland", "Ulster"], "provenance": "curated",
                  "comment": "Reviewed 26 October 2026: 36 of 38 records; the Galway reading is a name collision."},
    "derrynoose": {"name": "Derrynoose", "county": "Armagh", "country": "Ireland",
                   "aliases": ["Northern Ireland", "Ulster"], "provenance": "curated",
                   "comment": "Reviewed 26 October 2026: 9 of 10 records; the parish is in Armagh, the Louth reading a collision."},
    "portadown": {"name": "Portadown", "county": "Armagh", "country": "Ireland",
                  "aliases": ["Northern Ireland", "Ulster"], "provenance": "curated",
                  "comment": "Reviewed 26 October 2026: the town is in Armagh; 3 records associate it with Antrim through other places named with it."},
    "portglenone": {"name": "Portglenone", "county": "Antrim", "country": "Ireland",
                    "aliases": ["Northern Ireland", "Ulster"], "provenance": "curated",
                    "comment": "Reviewed 26 October 2026: 7 of 8 records; the town is in Antrim, across the Bann from Londonderry."},
}

NORTHERN_IRELAND_COUNTIES = {"Antrim", "Armagh", "Down", "Fermanagh", "Londonderry", "Tyrone"}
COUNTRY_ALIASES = {"Ireland": {"Ireland", "Eire", "Éire"}}


def key(value: str) -> str:
    """Return the case-insensitive key used for locality matching."""
    return TOKEN_RE.sub(" ", value.casefold()).strip()


def _county_aliases(county: str) -> set[str]:
    aliases = {county, f"County {county}", f"Co {county}", f"Co. {county}"}
    if county == "Londonderry":
        aliases.update({"Derry", "County Derry", "Co Derry", "Co. Derry"})
    return aliases


def aliases_for_entry(entry: dict[str, Any]) -> set[str]:
    """Return the searchable country, county and province aliases for an entry."""
    country = entry["country"]
    aliases = set(COUNTRY_ALIASES.get(country, {country}))
    aliases.add(country)
    aliases.update(_county_aliases(entry["county"]))
    aliases.update(entry.get("aliases", []))
    if country == "Ireland" and entry["county"] in NORTHERN_IRELAND_COUNTIES:
        aliases.update({"Northern Ireland", "Ulster"})
    elif country == "Ireland":
        aliases.add("Republic of Ireland")
    return aliases


def load(path: Path = DEFAULT_PATH) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def aliases_for_text(text: str, gazetteer: dict[str, Any] | None = None) -> set[str]:
    """Find every whole locality phrase in a place string, add hierarchy aliases."""
    entries = (gazetteer or load()).get("entries", {})
    haystack = f" {key(text)} "
    aliases: set[str] = set()
    for locality, entry in entries.items():
        if f" {locality} " in haystack:
            aliases.update(aliases_for_entry(entry))
    return aliases


def _parts(place: str) -> list[str]:
    """Candidate locality components before the first explicit county/country."""
    parts = [part.strip() for part in place.split(",")]
    result = []
    for part in parts:
        if not part or COUNTY_RE.search(part) or key(part) in {"ireland", "scotland", "england", "wales", "united kingdom"}:
            break
        if len(key(part)) >= 3 and not any(char.isdigit() for char in part):
            result.append(part)
    return result


def _county_from_text(text: str) -> str | None:
    match = COUNTY_RE.search(text)
    return match.group(1).strip().title() if match else None


def _country_from_text(text: str, fallback: str = "") -> str:
    folded = key(text)
    for country in ("Ireland", "Scotland", "England", "Wales"):
        if key(country) in folded:
            return country
    if key(fallback) in {"northern ireland", "ulster", "republic of ireland", "eire", "eire"}:
        return "Ireland"
    return fallback


def derive_gazetteer(records_csv: Path, search_index: Path) -> dict[str, Any]:
    """Build unambiguous entries from authoritative map rows and explicit places."""
    # Import lazily: build_family_map imports this module for runtime lookup.
    from build_family_map import IRISH_COUNTY_LOCATION_IDS

    id_counties: dict[str, set[str]] = defaultdict(set)
    for county, location_ids in IRISH_COUNTY_LOCATION_IDS.items():
        for location_id in location_ids:
            id_counties[location_id].add(county)
    evidence: dict[str, Counter[tuple[str, str]]] = defaultdict(Counter)

    with records_csv.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            place = " ".join((row.get("record_location") or "", row.get("location_basis") or ""))
            counties = set(id_counties.get(row.get("location_id") or "", set()))
            explicit = _county_from_text(place)
            if explicit:
                counties.add(explicit)
            country = _country_from_text(place, row.get("region") or "")
            if not country or not counties:
                continue
            for locality in _parts(row.get("record_location") or ""):
                for county in counties:
                    evidence[key(locality)][(county, country)] += 1

    people = json.loads(search_index.read_text(encoding="utf-8"))
    for person in people:
        for place in [*(person.get("locations") or []), person.get("birth_location") or "", person.get("death_location") or ""]:
            county = _county_from_text(place)
            if not county:
                continue
            country = _country_from_text(place, "Ireland" if county in IRISH_COUNTY_NAMES else "")
            for locality in _parts(place):
                evidence[key(locality)][(county, country)] += 1

    entries: dict[str, Any] = {}
    ambiguous: dict[str, Any] = {}
    for locality, candidates in sorted(evidence.items()):
        names = {name for name in locality.split()}
        if not names:
            continue
        if len(candidates) != 1:
            ambiguous[locality] = {
                "name": locality.title(),
                "counties": sorted({county for county, _country in candidates}),
                "provenance": f"derived: {sum(candidates.values())} records",
            }
            continue
        (county, country), count = candidates.most_common(1)[0]
        entries[locality] = {
            "name": locality.title(), "county": county, "country": country,
            "aliases": (["Northern Ireland", "Ulster"] if country == "Ireland" and county in NORTHERN_IRELAND_COUNTIES else []),
            "provenance": f"derived: {count} records",
        }
    entries.update(CURATED)
    for locality in CURATED:
        ambiguous.pop(locality, None)
    return {"schema_version": 1, "entries": entries, "ambiguous": ambiguous}


def main() -> None:
    data = derive_gazetteer(ROOT / "www/map/data/records.csv", ROOT / "www/data/catalogue-search-index.json")
    DEFAULT_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(data['entries'])} entries; {len(data['ambiguous'])} ambiguous localities")


if __name__ == "__main__":
    main()
