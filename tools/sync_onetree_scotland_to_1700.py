#!/usr/bin/env python3
"""Add Scottish Glasgow profiles born through 1700 from the newest One-Tree export."""

from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from project_paths import MAP_AUDIT_DIR, MAP_RECORDS as CSV_PATH, latest_onetree_export


AUDIT_PATH = MAP_AUDIT_DIR / "onetree_scotland_through_1700.json"
PROFILE_ID = re.compile(r"[A-Za-z]+-\d+")
SURNAME_VARIANTS = {"glasgow", "glassgo", "glasko", "glascow", "glasgo", "glascoe"}
SCOTTISH_PLACE = re.compile(
    r"\b(?:scotland|ayrshire|lanarkshire|midlothian|edinburghshire|linlithgowshire|"
    r"west lothian|stirlingshire|roxburghshire|glasgow|edinburgh|inveresk|leith|"
    r"stevenston|kirknewton|ardrossan|jedburgh|duddingston|kilwinning)\b",
    re.I,
)


@dataclass(frozen=True)
class Place:
    location_id: str
    label: str
    precision: str
    basis: str
    latitude: float
    longitude: float


PLACES = {
    "scotland": Place("scotland_unspecified", "Scotland — exact locality unproved", "Country-level representative point", "The profile gives Scotland without a county or parish.", 56.49, -4.2),
    "glasgow": Place("glasgow_scotland", "Glasgow", "Settlement centrepoint", "The profile identifies Glasgow but no securely mapped property.", 55.8642, -4.2518),
    "mid_calder": Place("mid_calder", "Mid Calder", "Settlement/parish centrepoint", "The profile identifies Mid Calder but no property.", 55.892, -3.481),
    "edinburgh": Place("edinburgh", "Edinburgh", "Settlement centrepoint", "The profile identifies Edinburgh but no street or property.", 55.9533, -3.1883),
    "stevenston": Place("stevenston", "Stevenston — Ayrshire", "Settlement centrepoint", "The profile identifies Stevenston but no property.", 55.64, -4.753),
    "hirmanscheillis": Place("midlothian_reference", "Hirmanscheillis — Midlothian locality unresolved", "County-level representative point", "The historical locality is stated, but its exact modern point remains unresolved; coordinates represent Midlothian.", 55.83, -3.1),
    "inveresk": Place("inveresk", "Inveresk", "Settlement/parish centrepoint", "The profile identifies Inveresk but no property.", 55.936, -3.05),
    "stirlingshire": Place("stirlingshire_reference", "Stirlingshire — exact locality unproved", "County-level representative point", "The profile supplies historic Stirlingshire but no parish or property.", 56.12, -3.94),
    "linlithgowshire": Place("west_lothian_reference", "Linlithgowshire / West Lothian — exact locality unproved", "County-level representative point", "The profile supplies the historic county but no parish or property.", 55.91, -3.55),
    "ayrshire": Place("ayrshire_reference", "Ayrshire — exact locality unproved", "County-level representative point", "The profile supplies Ayrshire but no parish or property.", 55.46, -4.63),
    "south_leith": Place("south_leith", "South Leith", "Parish/settlement centrepoint", "The profile identifies South Leith but no property.", 55.975, -3.17),
    "lanarkshire": Place("lanarkshire_reference", "Lanarkshire — exact locality unproved", "County-level representative point", "The profile supplies Lanarkshire but no parish or property.", 55.67, -3.78),
    "kirknewton": Place("kirknewton", "Kirknewton — West Lothian", "Settlement/parish centrepoint", "The profile identifies Kirknewton but no property.", 55.887, -3.419),
    "jedburgh": Place("jedburgh", "Jedburgh — Roxburghshire", "Settlement centrepoint", "The profile identifies Jedburgh but no property.", 55.477, -2.554),
    "ardrossan": Place("ardrossan", "Ardrossan — Ayrshire", "Settlement centrepoint", "The profile identifies Ardrossan but no property.", 55.64, -4.812),
    "kilwinning": Place("kilwinning", "Kilwinning — Ayrshire", "Settlement/parish centrepoint", "The profile identifies Kilwinning but no property.", 55.654, -4.7),
    "kilbirnie": Place("kilbirnie", "Kilbirnie — Ayrshire", "Settlement/parish centrepoint", "The profile identifies Kilbirnie but no property.", 55.75, -4.685),
    "linlithgow": Place("linlithgow", "Linlithgow", "Settlement/parish centrepoint", "The profile identifies Linlithgow but no property.", 55.976, -3.6),
    "irvine": Place("irvine", "Irvine — Ayrshire", "Settlement centrepoint", "The profile identifies Irvine but no property.", 55.611, -4.669),
    "gordon": Place("gordon_berwickshire", "Gordon — Berwickshire", "Settlement/parish centrepoint", "The profile identifies Gordon but no property.", 55.68, -2.56),
    "campbeltown": Place("campbeltown", "Campbeltown — Argyll", "Settlement centrepoint", "The profile identifies Campbeltown but no property.", 55.425, -5.607),
    "glencorse": Place("glencorse", "Glencorse — Midlothian", "Settlement/parish centrepoint", "The profile identifies Glencorse but no property.", 55.85, -3.19),
    "cavers": Place("cavers", "Cavers — Roxburghshire", "Parish centrepoint", "The profile identifies Cavers but no property.", 55.43, -2.69),
    "ayr": Place("ayr", "Ayr", "Settlement centrepoint", "The profile identifies Ayr but no property.", 55.458, -4.629),
    "duddingston": Place("duddingston", "Duddingston — Midlothian", "Settlement/parish centrepoint", "The profile identifies Duddingston but no property.", 55.94, -3.147),
    "west_kilbride": Place("west_kilbride", "West Kilbride — Ayrshire", "Settlement/parish centrepoint", "The profile identifies West Kilbride but no property.", 55.695, -4.858),
    "duns": Place("duns", "Duns — Berwickshire", "Settlement/parish centrepoint", "The profile identifies Duns but no property.", 55.778, -2.342),
    "musselburgh": Place("musselburgh", "Musselburgh / Inveresk", "Settlement/parish centrepoint", "The profile identifies Musselburgh or the combined Inveresk and Musselburgh parish.", 55.942, -3.054),
    "quothquan": Place("quothquan", "Quothquan — Libberton, Lanarkshire", "Historic locality representative point", "The profile identifies Quothquan in Libberton parish.", 55.64, -3.63),
    "livingston": Place("livingston", "Livingston — West Lothian", "Settlement/parish centrepoint", "The profile identifies Livingston but no property.", 55.886, -3.522),
    "polwarth": Place("polwarth", "Polwarth — Berwickshire", "Settlement/parish centrepoint", "The profile identifies Polwarth but no property.", 55.75, -2.33),
    "hawick": Place("hawick", "Hawick — Roxburghshire", "Settlement centrepoint", "The profile identifies Hawick but no property.", 55.422, -2.787),
    "roxburghshire": Place("roxburghshire_reference", "Roxburghshire — exact locality unproved", "County-level representative point", "The profile supplies Roxburghshire but no parish or property.", 55.45, -2.5),
    "sorn": Place("sorn", "Sorn — Ayrshire", "Settlement/parish centrepoint", "The profile identifies Sorn but no property.", 55.51, -4.29),
    "skirling": Place("skirling", "Skirling — Peeblesshire", "Settlement/parish centrepoint", "The profile identifies Skirling but no property.", 55.637, -3.36),
    "biggar": Place("biggar", "Biggar — Lanarkshire", "Settlement/parish centrepoint", "The profile identifies Biggar but no property.", 55.623, -3.524),
    "strathblane": Place("strathblane", "Strathblane — Stirlingshire", "Settlement/parish centrepoint", "The profile identifies Strathblane but no property.", 55.985, -4.307),
    "currie": Place("currie", "Currie — Midlothian", "Settlement/parish centrepoint", "The profile identifies Currie but no property.", 55.896, -3.31),
    "carnwath": Place("carnwath", "Carnwath — Lanarkshire", "Settlement/parish centrepoint", "The profile identifies Carnwath but no property.", 55.7, -3.63),
    "saltcoats": Place("saltcoats", "Saltcoats — Ayrshire", "Settlement centrepoint", "The profile identifies Saltcoats but no property.", 55.635, -4.785),
    "midlothian": Place("midlothian_reference", "Midlothian — exact locality unproved", "County-level representative point", "The profile supplies Midlothian but no parish or property.", 55.83, -3.1),
}


def year(value: str | None) -> int | None:
    match = re.match(r"(\d{4})", value or "")
    result = int(match.group(1)) if match else 0
    return result or None


def scottish_event(profile: dict) -> tuple[str, str] | None:
    birth = profile.get("BirthLocation") or ""
    death = profile.get("DeathLocation") or ""
    birth_is_scottish = bool(SCOTTISH_PLACE.search(birth))
    death_is_scottish = bool(SCOTTISH_PLACE.search(death))
    birth_is_country_only = birth.strip().rstrip(".").lower() == "scotland"
    if birth_is_country_only and death_is_scottish and death.strip().rstrip(".").lower() != "scotland":
        return "DeathLocation", death
    if birth_is_scottish:
        return "BirthLocation", birth
    if death_is_scottish:
        return "DeathLocation", death
    for spouse in profile.get("Spouses") or []:
        value = spouse.get("MarriageLocation") or spouse.get("marriage_location") or ""
        if SCOTTISH_PLACE.search(value):
            return "MarriageLocation", value
    return None


def resolve_place(location: str) -> Place:
    text = location.lower().rstrip(".")
    for needle, key in (
        ("mid calder", "mid_calder"), ("south leith", "south_leith"),
        ("west kilbride", "west_kilbride"), ("stevenston", "stevenston"), ("stevenson", "stevenston"),
        ("kilwinning", "kilwinning"), ("kilbirnie", "kilbirnie"), ("kirknewton", "kirknewton"),
        ("linlithgow,", "linlithgow"), ("irvine", "irvine"), ("gordon", "gordon"),
        ("campbeltown", "campbeltown"), ("glencorse", "glencorse"), ("cavers", "cavers"),
        ("duddingston", "duddingston"), ("duns", "duns"), ("quothquan", "quothquan"),
        ("livingston", "livingston"), ("polwarth", "polwarth"), ("hawick", "hawick"),
        ("sorn", "sorn"), ("skirling", "skirling"), ("biggar", "biggar"),
        ("strathblane", "strathblane"), ("currie", "currie"), ("carnwath", "carnwath"),
        ("saltcoats", "saltcoats"), ("musselburgh", "musselburgh"),
        ("jedburgh", "jedburgh"), ("ardrossan", "ardrossan"),
        ("hirmanscheillis", "hirmanscheillis"),
        ("inveresk", "inveresk"), ("edinburgh", "edinburgh"),
        ("leith", "south_leith"), ("midlothian", "midlothian"),
        ("glasgow,", "glasgow"), ("stirlingshire", "stirlingshire"),
        ("linlithgowshire", "linlithgowshire"), ("west lothian", "linlithgowshire"),
        ("roxburghshire", "roxburghshire"), ("ayr,", "ayr"),
        ("ayrshire", "ayrshire"), ("lanarkshire", "lanarkshire"),
    ):
        if needle in text:
            return PLACES[key]
    if text == "scotland":
        return PLACES["scotland"]
    raise ValueError(f"No Scottish placement rule for {location!r}")


def main() -> None:
    export_path = latest_onetree_export()
    profiles = json.loads(export_path.read_text(encoding="utf-8")).get("data", {})

    with CSV_PATH.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)
    if "region" not in fieldnames:
        fieldnames.insert(fieldnames.index("profile_id") + 1, "region")
    for row in rows:
        row["region"] = row.get("region") or "Ireland"
        if row["region"] == "Scotland" and row["family_group"] == "Early Scotland profile leads through 1600":
            row["family_group"] = "Early Scotland profile leads through 1700"

    mapped_ids = {
        token for row in rows if row.get("region") == "Scotland"
        for token in PROFILE_ID.findall(row["profile_id"])
    }
    eligible = {
        profile["Name"]: profile
        for profile in profiles.values()
        if (profile.get("LastNameAtBirth") or "").lower() in SURNAME_VARIANTS
        and (birth_year := year(profile.get("BirthDate"))) is not None
        and birth_year <= 1700
    }
    numeric_to_name = {str(profile.get("Id")): profile["Name"] for profile in profiles.values() if profile.get("Id") and profile.get("Name")}
    direct_events = {name: scottish_event(profile) for name, profile in eligible.items()}
    direct_names = {name for name, event in direct_events.items() if event}
    qualifying = []
    for name, profile in eligible.items():
        birth_year = year(profile.get("BirthDate"))
        event = direct_events[name]
        if not event:
            relatives = {
                numeric_to_name.get(str(profile.get("Father") or "")),
                numeric_to_name.get(str(profile.get("Mother") or "")),
            }
            relatives.update(
                child["Name"] for child in profiles.values()
                if str(child.get("Father") or "") == str(profile.get("Id") or "missing")
                or str(child.get("Mother") or "") == str(profile.get("Id") or "missing")
            )
            if relatives & direct_names:
                event = ("FamilyContext", "Scotland")
        if event:
            qualifying.append((birth_year, name, profile, event))
    qualifying.sort(key=lambda item: (item[0], item[1]))

    added = []
    updated = []
    for birth_year, name, profile, (event_field, event_location) in qualifying:
        event_label = {"BirthLocation": "birthplace", "DeathLocation": "death place", "MarriageLocation": "marriage place", "FamilyContext": "family context"}[event_field]
        if name in mapped_ids:
            generic_rows = [
                existing for existing in rows
                if existing["profile_id"] == name
                and existing.get("region") == "Scotland"
                and existing["evidence"] == "One-Tree profile lead"
                and existing["location_id"] == "scotland_unspecified"
            ]
            if generic_rows:
                place = resolve_place(event_location)
                for existing in generic_rows:
                    if place.location_id == "scotland_unspecified":
                        continue
                    existing.update({
                        "association": f"Profile-stated {event_label}: {event_location}",
                        "location_id": place.location_id,
                        "record_location": place.label,
                        "record_precision": place.precision,
                        "location_basis": place.basis,
                        "latitude": str(place.latitude),
                        "longitude": str(place.longitude),
                    })
                    updated.append(name)
            continue
        place = resolve_place(event_location)
        rows.append({
            "person": profile.get("LongName") or profile.get("BirthName") or name,
            "profile_id": name,
            "region": "Scotland",
            "family_group": "Early Scotland profile leads through 1700",
            "subcluster": "One-Tree Scottish profile cohort",
            "evidence": "One-Tree profile lead",
            "year": f"b. {birth_year}",
            "filter_year": str(birth_year),
            "association": f"Profile-stated {event_label}: {event_location}",
            "note": ("Placed from an attached Scottish parent/child rather than a location on this profile. " if event_field == "FamilyContext" else "") +
                    "One-Tree export profile fields are search leads, not sources; relationships are shown only where the export supplies parent links.",
            "location_id": place.location_id,
            "record_location": place.label,
            "record_precision": place.precision,
            "location_basis": place.basis,
            "latitude": str(place.latitude),
            "longitude": str(place.longitude),
        })
        mapped_ids.add(name)
        added.append(name)

    with CSV_PATH.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    missing = [name for _, name, _, _ in qualifying if name not in mapped_ids]
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    AUDIT_PATH.write_text(json.dumps({
        "export": export_path.name,
        "cutoff_birth_year": 1700,
        "selection": "Glasgow surname variant, known birth year <= 1700, and a Scottish event or directly attached Scottish parent/child",
        "qualifying_profiles": len(qualifying),
        "newly_added_this_run": len(added),
        "updated_to_more_specific_death_location": sorted(set(updated)),
        "remaining_missing": missing,
    }, indent=2) + "\n", encoding="utf-8")
    if missing:
        raise SystemExit(f"Audit failed: {len(missing)} profiles remain missing")
    print(f"{len(qualifying)} Scottish profiles through 1700; added {len(added)}; updated {len(set(updated))}; 0 missing")


if __name__ == "__main__":
    main()
