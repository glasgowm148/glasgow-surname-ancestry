#!/usr/bin/env python3
"""Add Irish Glasgow profiles born through 1850 from the newest One-Tree export."""

from __future__ import annotations

import csv
import json
import re
from collections import deque
from dataclasses import dataclass
from project_paths import (
    MAP_AUDIT_DIR, MAP_RECORDS as CSV_PATH, atomic_write_csv,
    atomic_write_text, latest_onetree_export, relation_values,
)


AUDIT_PATH = MAP_AUDIT_DIR / "onetree_irish_through_1850.json"
WIKITREE_ID = re.compile(r"[A-Za-z]+-\d+")
IRISH_NAME_VARIANTS = {"glasgow", "glassgo", "glasko", "glascow", "glasgo", "glascoe"}
IRISH_PLACE = re.compile(
    r"\b(?:ireland|ulster|antrim|armagh|carlow|cavan|clare|cork|derry|donegal|down|"
    r"dublin|fermanagh|galway|kerry|kildare|kilkenny|laois|leitrim|limerick|longford|"
    r"louth|mayo|meath|monaghan|offaly|roscommon|sligo|tipperary|tyrone|waterford|"
    r"westmeath|wexford|wicklow)\b",
    re.I,
)
FOREIGN_PLACE = re.compile(
    r"\b(?:united states|usa|canada|australia|new zealand|england|scotland|wales|"
    r"guernsey|ohio|pennsylvania|indiana|illinois|michigan|virginia|kentucky|carolina|"
    r"maryland|tennessee|missouri|iowa|texas|georgia|alabama|mississippi|arkansas|"
    r"california)\b",
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
    "ireland": Place("ireland_unspecified", "Ireland — exact locality unproved", "Country-level representative point", "The profile gives Ireland without a county, parish or townland.", 53.42, -7.94),
    "antrim": Place("county_antrim_reference", "County Antrim — exact locality unproved", "County-level representative point", "The profile supplies County Antrim but no parish or townland.", 54.85, -6.15),
    "tyrone": Place("county_tyrone_reference", "County Tyrone — exact locality unproved", "County-level representative point", "The profile supplies County Tyrone but no parish or townland.", 54.6, -7.3),
    "londonderry": Place("county_londonderry_general", "County Londonderry — exact locality unproved", "County-level representative point", "The profile supplies County Londonderry but no parish or townland.", 54.9, -6.8),
    "killycurragh": Place("killycurragh_derryloran", "Killycurragh townland — Oritor/Derryloran", "Exact townland centrepoint", "The profile identifies Killycurragh in Derryloran, County Tyrone.", 54.683889, -6.834444),
    "gortin": Place("gortin_derryloran", "Gortin townland — Oritor/Derryloran", "Exact townland centrepoint", "The profile identifies Gortin in Derryloran, County Tyrone.", 54.656667, -6.796111),
    "cookstown": Place("cookstown", "Cookstown", "Settlement centrepoint", "The profile supplies Cookstown but no street, church or property.", 54.646, -6.745),
    "dunaghy": Place("dunaghy_parish", "Dunaghy civil parish — County Antrim", "Civil-parish representative point", "The profile identifies Dunaghy; the point represents the civil parish, not a dwelling.", 54.993, -6.257),
    "rasharkin": Place("rasharkin", "Rasharkin", "Settlement centrepoint", "The profile identifies Rasharkin but no property.", 54.955, -6.48),
    "ballymena": Place("ballymena", "Ballymena", "Settlement centrepoint", "The profile identifies Ballymena but no street or property.", 54.863, -6.276),
    "ballymoney": Place("ballymoney_town", "Ballymoney", "Settlement centrepoint", "The profile identifies Ballymoney; its county wording should be audited where it conflicts with modern County Antrim.", 55.066667, -6.513889),
    "kilrea": Place("kilrea_town", "Kilrea", "Settlement centrepoint", "The profile identifies Kilrea but no property.", 54.9639, -6.5559),
    "derrynoose": Place("derrynoose_parish", "Derrynoose civil parish — County Armagh", "Civil-parish representative point", "The profile identifies Derrynoose; the point represents the civil parish.", 54.2675, -6.751667),
    "lisburn": Place("lisburn", "Lisburn / Lisnagarvey", "Settlement centrepoint", "The profile identifies Lisburn or its historical name Lisnagarvey but no property.", 54.516, -6.058),
    "muntober": Place("kildress_parish", "Kildress civil parish", "Parish-level proxy point", "Muntober/Montober is placed at its Kildress parish representative point pending a verified townland coordinate.", 54.660278, -6.8975),
    "borrisoleigh": Place("borrisoleigh", "Borrisoleigh — County Tipperary", "Settlement centrepoint", "The profile identifies Borrisoleigh but no property.", 52.752, -7.954),
    "cork": Place("county_cork_reference", "County Cork — exact locality unproved", "County-level representative point", "The profile supplies County Cork but no parish or townland.", 51.9, -8.5),
    "carrigaline": Place("carrigaline", "Carrigaline — County Cork", "Settlement/parish representative point", "The marriage profile identifies Carrigaline; the point does not represent a specific church or property.", 51.812, -8.399),
    "portglenone": Place("portglenone_reference", "Portglenone", "Settlement centrepoint", "The profile identifies Portglenone but no property.", 54.8741, -6.47318),
    "clough": Place("clough_antrim", "Clough / Clogh, County Antrim", "Settlement centrepoint", "The profile identifies Clough but no property.", 54.96667, -6.28333),
    "kildress": Place("kildress_parish", "Kildress civil parish", "Civil-parish representative point", "The profile identifies a place in Kildress; the point represents the civil parish where a townland point is unavailable.", 54.660278, -6.8975),
    "lissan": Place("lissan_parish", "Lissan civil parish — Cookstown area", "Civil-parish representative point", "The profile identifies a place in Lissan; the point represents the civil parish, not a dwelling.", 54.67, -6.72),
    "ballyclug": Place("ballyclug_parish", "Ballyclug civil parish — County Antrim", "Civil-parish representative point", "The profile identifies Cross in Ballyclug; the point represents the parish pending an exact Cross townland coordinate.", 54.858, -6.254),
    "kildare": Place("county_kildare_reference", "County Kildare — exact locality unproved", "County-level representative point", "The profile supplies County Kildare but no securely distinguished property.", 53.17, -6.91),
    "wicklow": Place("county_wicklow_reference", "County Wicklow — exact locality unproved", "County-level representative point", "The profile says Ballymoney, County Wicklow; this county point avoids confusing it with Ballymoney, County Antrim.", 52.98, -6.04),
    "coltrim": Place("coltrim", "Coltrim townland", "Exact townland centrepoint", "The profile explicitly identifies Coltrim.", 54.6839, -6.68456),
    "armagh": Place("armagh_city", "Armagh", "Settlement centrepoint", "The profile identifies Armagh but no street, church or property.", 54.35, -6.65),
    "tipperary": Place("county_tipperary_reference", "County Tipperary — exact locality unproved", "County-level representative point", "The profile supplies County Tipperary but no parish or townland.", 52.47, -8.16),
    "belfast": Place("belfast", "Belfast", "Settlement centrepoint", "The profile identifies Belfast but no street or property.", 54.5973, -5.9301),
    "magherafelt": Place("magherafelt", "Magherafelt", "Settlement centrepoint", "The profile identifies Magherafelt but no property.", 54.754, -6.607),
    "coleraine": Place("coleraine", "Coleraine", "Settlement centrepoint", "The profile identifies Coleraine but no property.", 55.132, -6.668),
}


def year(value: str | None) -> int | None:
    match = re.match(r"(\d{4})", value or "")
    result = int(match.group(1)) if match else 0
    return result or None


def event_for(profile: dict) -> tuple[str, str] | None:
    birth = profile.get("BirthLocation") or ""
    death = profile.get("DeathLocation") or ""
    birth_is_irish = bool(IRISH_PLACE.search(birth) and not FOREIGN_PLACE.search(birth))
    death_is_irish = bool(IRISH_PLACE.search(death) and not FOREIGN_PLACE.search(death))
    birth_is_country_only = birth.strip().rstrip(".").lower() == "ireland"
    if birth_is_country_only and death_is_irish and death.strip().rstrip(".").lower() != "ireland":
        return "DeathLocation", death
    if birth_is_irish:
        return "BirthLocation", birth
    if death_is_irish:
        return "DeathLocation", death
    for spouse in relation_values(profile, "Spouses"):
        value = spouse.get("MarriageLocation") or spouse.get("marriage_location") or ""
        if IRISH_PLACE.search(value) and not FOREIGN_PLACE.search(value):
            return "MarriageLocation", value
    return None


def resolve_place(location: str) -> Place:
    text = location.lower()
    # Specific locations must precede their counties.
    checks = (
        ("killycurragh", "killycurragh"), ("gortin", "gortin"), ("dunaghy", "dunaghy"),
        ("rasharkin", "rasharkin"), ("ballymena", "ballymena"), ("ballymoney", "wicklow" if "wicklow" in text else "ballymoney"),
        ("kilrea", "kilrea"), ("derrynoose", "derrynoose"), ("lisnagarvey", "lisburn"),
        ("lisburn", "lisburn"), ("muntober", "muntober"), ("montober", "muntober"), ("borrisoleigh", "borrisoleigh"),
        ("carrigaline", "carrigaline"), ("portglenone", "portglenone"), ("clough", "clough"),
        ("ballynasollus", "kildress"), ("drumnaglogh", "kildress"), ("kildress", "kildress"),
        ("ballynagilly", "lissan"), ("brackagh", "lissan"), ("ballyclug", "ballyclug"),
        ("coltrim", "coltrim"), ("magherafelt", "magherafelt"), ("coleraine", "coleraine"),
        ("cookstown", "cookstown"), ("belfast", "belfast"),
    )
    for needle, key in checks:
        if needle in text:
            return PLACES[key]
    if "county antrim" in text or text.strip() == "antrim": return PLACES["antrim"]
    if "county tyrone" in text: return PLACES["tyrone"]
    if "county londonderry" in text: return PLACES["londonderry"]
    if "county cork" in text: return PLACES["cork"]
    if "county kildare" in text: return PLACES["kildare"]
    if "county tipperary" in text: return PLACES["tipperary"]
    if "armagh" in text: return PLACES["armagh"]
    if text.strip().rstrip(".").lower() == "ireland": return PLACES["ireland"]
    raise ValueError(f"No map placement rule for {location!r}")


def profile_index(export: dict) -> tuple[dict[str, dict], dict[str, str]]:
    profiles = {}
    numeric_to_name = {}
    for profile in export.get("data", export).values():
        if profile.get("Name"):
            profiles[profile["Name"]] = profile
        if profile.get("Id") and profile.get("Name"):
            numeric_to_name[str(profile["Id"])] = profile["Name"]
    return profiles, numeric_to_name


def inherited_cluster(name: str, profiles: dict[str, dict], numeric_to_name: dict[str, str], mapped: dict[str, tuple[str, str]]) -> tuple[str, str]:
    queue = deque([(name, 0)])
    seen = {name}
    while queue:
        current, distance = queue.popleft()
        if distance and current in mapped:
            return mapped[current]
        profile = profiles.get(current, {})
        for field in ("Father", "Mother"):
            parent = numeric_to_name.get(str(profile.get(field) or ""))
            if parent and parent not in seen:
                seen.add(parent)
                queue.append((parent, distance + 1))
    return "Unplaced Irish profile leads through 1850", "One-Tree Irish profile cohort"


def main() -> None:
    export_path = latest_onetree_export()
    export = json.loads(export_path.read_text(encoding="utf-8"))
    profiles, numeric_to_name = profile_index(export)

    with CSV_PATH.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames
        rows = list(reader)
    if not fieldnames:
        raise SystemExit("Map CSV has no header")

    mapped_ids = {token for row in rows for token in WIKITREE_ID.findall(row["profile_id"])}
    mapped_clusters = {}
    for row in rows:
        for token in WIKITREE_ID.findall(row["profile_id"]):
            mapped_clusters.setdefault(token, (row["family_group"], row["subcluster"]))

    qualifying = []
    undated_irish_profiles = []
    for profile in profiles.values():
        birth_year = year(profile.get("BirthDate"))
        event = event_for(profile)
        if (
            (profile.get("LastNameAtBirth") or "").lower() in IRISH_NAME_VARIANTS
            and birth_year is None
            and event
        ):
            undated_irish_profiles.append(profile["Name"])
        if (
            (profile.get("LastNameAtBirth") or "").lower() in IRISH_NAME_VARIANTS
            and birth_year is not None
            and birth_year <= 1850
            and event
        ):
            qualifying.append((birth_year, profile["Name"], profile, event))
    qualifying.sort(key=lambda item: (item[0], item[1]))

    added = []
    updated = []
    for birth_year, name, profile, (event_field, event_location) in qualifying:
        event_label = {"BirthLocation": "birthplace", "DeathLocation": "death place", "MarriageLocation": "marriage place"}[event_field]
        if name in mapped_ids:
            generic_rows = [
                existing for existing in rows
                if existing["profile_id"] == name
                and existing.get("region") == "Ireland"
                and existing["evidence"] == "One-Tree profile lead"
                and existing["location_id"] == "ireland_unspecified"
            ]
            if generic_rows:
                place = resolve_place(event_location)
                for existing in generic_rows:
                    if place.location_id == "ireland_unspecified":
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
        family_group, subcluster = inherited_cluster(name, profiles, numeric_to_name, mapped_clusters)
        parent_ids = [
            numeric_to_name.get(str(profile.get(field) or ""))
            for field in ("Father", "Mother")
            if numeric_to_name.get(str(profile.get(field) or ""))
        ]
        note = "One-Tree export profile fields are search leads, not sources."
        if parent_ids:
            note += " Attached parent profile(s): " + ", ".join(parent_ids) + "."
        row = {
            "person": profile.get("LongName") or profile.get("BirthName") or name,
            "profile_id": name,
            "region": "Ireland",
            "family_group": family_group,
            "subcluster": subcluster,
            "evidence": "One-Tree profile lead",
            "year": f"b. {birth_year}",
            "filter_year": str(birth_year),
            "association": f"Profile-stated {event_label}: {event_location}",
            "note": note,
            "location_id": place.location_id,
            "record_location": place.label,
            "record_precision": place.precision,
            "location_basis": place.basis,
            "latitude": str(place.latitude),
            "longitude": str(place.longitude),
        }
        rows.append(row)
        added.append(name)
        mapped_ids.add(name)
        mapped_clusters[name] = (family_group, subcluster)

    atomic_write_csv(CSV_PATH, fieldnames, rows)

    remaining = [name for _, name, _, _ in qualifying if name not in mapped_ids]
    audit = {
        "export": export_path.name,
        "cutoff_birth_year": 1850,
        "selection": "Glasgow surname variant, known birth year <= 1850, and an Irish birth/death/marriage location",
        "qualifying_profiles": len(qualifying),
        "already_represented": len(qualifying) - len(added),
        "added": len(added),
        "added_profile_ids": added,
        "updated_to_more_specific_death_location": sorted(set(updated)),
        "remaining_missing": remaining,
        "not_classifiable_without_birth_year": sorted(undated_irish_profiles),
    }
    atomic_write_text(AUDIT_PATH, json.dumps(audit, indent=2) + "\n")
    if remaining:
        raise SystemExit(f"Audit failed: {len(remaining)} qualifying profiles remain missing")
    print(f"{len(qualifying)} qualifying profiles; added {len(added)}; updated {len(set(updated))}; 0 missing")


if __name__ == "__main__":
    main()
