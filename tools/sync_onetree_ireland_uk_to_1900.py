#!/usr/bin/env python3
"""Add every known Glasgow profile and woman married to a Glasgow."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
import re
import time
import urllib.parse
import urllib.request
from dataclasses import asdict
import sync_onetree_irish_to_1850 as ireland_sync
import sync_onetree_scotland_to_1700 as scotland_sync
from project_paths import MAP_AUDIT_DIR, MAP_CACHE_DIR, MAP_RECORDS as CSV_PATH, merged_map_profiles


CACHE_PATH = MAP_CACHE_DIR / "ireland_uk_geocodes.json"
AUDIT_PATH = MAP_AUDIT_DIR / "onetree_ireland_uk_all.json"
PROFILE_ID = re.compile(r"[A-Za-z][A-Za-z_'’]*(?:-[A-Za-z][A-Za-z_'’]*)*-\d+")
SURNAME_VARIANTS = {
    "glasgow", "glasco", "glassco", "glascoe", "glasgo", "glasow",
    "glascow", "glasoe", "glassgow", "glassgo", "glasko",
}
# Project-created structural placeholders are not historical people and must
# not acquire a synthetic map occurrence merely to satisfy export coverage.
INTENTIONALLY_UNMAPPED_PROFILE_IDS = {"Glasgow-3905"}
REGION_COMPONENTS = {
    "Ireland": {"ireland", "northern ireland", "éire", "eire", "republic of ireland", "ulster"},
    "Scotland": {"scotland"},
    "England": {"england"},
    "Wales": {"wales"},
}
REGION_CENTRES = {
    "Ireland": (53.42, -7.94),
    "Scotland": (56.49, -4.2),
    "England": (52.7, -1.5),
    "Wales": (52.3, -3.7),
    "United Kingdom": (54.0, -2.5),
    "United States": (39.5, -98.35),
    "Canada": (56.13, -106.35),
    "Australia": (-25.27, 133.78),
    "New Zealand": (-41.2, 174.7),
    "India": (22.6, 79.0),
    "France": (46.2, 2.2),
    "South Africa": (-30.6, 22.9),
    "Portugal": (39.6, -8.0),
    "Caribbean": (16.8, -61.0),
    "At Sea": (0.0, -30.0),
    "Unspecified": (54.0, -12.0),
}
SCOTTISH_HINTS = re.compile(
    r"\b(?:argyll|ayr(?:shire)?|berwickshire|bute|clackmannan(?:shire)?|dumfries(?:shire)?|"
    r"dunbarton(?:shire)?|edinburgh(?:shire)?|fife|forfarshire|glasgow|inverness-shire|lanark(?:shire)?|"
    r"linlithgowshire|lothian|midlothian|peeblesshire|perthshire|renfrewshire|roxburghshire|stirlingshire|wigtownshire)\b",
    re.I,
)
IRISH_HINTS = re.compile(
    r"\b(?:antrim|armagh|belfast|carlow|cavan|clare|cork|derry|donegal|down|dublin|fermanagh|galway|"
    r"kerry|kildare|kilkenny|laois|larne|leitrim|limerick|londonderry|longford|louth|mayo|meath|"
    r"monaghan|offaly|roscommon|sligo|tipperary|tyrone|waterford|westmeath|wexford|wicklow)\b",
    re.I,
)
US_HINTS = re.compile(
    r"\b(?:united states(?: of america)?|u\.?s\.?a\.?|alabama|alaska|arizona|arkansas|california|"
    r"colorado|connecticut|delaware|florida|georgia|hawaii|idaho|illinois|indiana|iowa|kansas|kentucky|"
    r"louisiana|maine|maryland|massachusetts|michigan|minnesota|mississippi|missouri|montana|nebraska|"
    r"nevada|new hampshire|new jersey|new mexico|new york|north carolina|north dakota|ohio|oklahoma|"
    r"oregon|pennsylvania|rhode island|south carolina|south dakota|tennessee|texas|utah|vermont|"
    r"virginia|washington|west virginia|wisconsin|wyoming|district of columbia)\b",
    re.I,
)
CANADA_HINTS = re.compile(
    r"\b(?:canada|canada west|upper canada|alberta|british columbia|manitoba|new brunswick|"
    r"newfoundland|nova scotia|ontario|prince edward island|quebec|saskatchewan)\b",
    re.I,
)


def year(value: str | None) -> int | None:
    match = re.match(r"(\d{4})", value or "")
    result = int(match.group(1)) if match else 0
    return result or None


def display_birth_year(profile: dict) -> tuple[int, str, bool]:
    """Return a birth/filter year, estimating adulthood when birth is absent."""
    birth_year = year(profile.get("BirthDate"))
    if birth_year:
        return birth_year, f"b. {birth_year}", False
    spouses = profile.get("Spouses") or []
    if isinstance(spouses, dict):
        spouses = spouses.values()
    marriage_years = [
        year(spouse.get("MarriageDate") or spouse.get("marriage_date"))
        for spouse in spouses
        if isinstance(spouse, dict)
    ]
    marriage_years = [value for value in marriage_years if value]
    if marriage_years:
        estimate = min(marriage_years) - 18
        return estimate, f"est. b. {estimate}", True
    death_year = year(profile.get("DeathDate"))
    if death_year:
        estimate = death_year - 18
        return estimate, f"est. b. {estimate}", True
    return 0, "undated", True


def normalized(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().rstrip(".")).lower()


def events(profile: dict) -> list[tuple[str, str]]:
    result = []
    for field, corrected_field in (
        ("BirthLocation", "CorrectedBirthLocation"),
        ("DeathLocation", "CorrectedDeathLocation"),
    ):
        raw = profile.get(field) or ""
        corrected = profile.get(corrected_field) or ""
        result.append((field, raw))
        if corrected and normalized(corrected) != normalized(raw):
            result.append((field, corrected))
    result.extend(
        ("MarriageLocation", spouse.get("MarriageLocation") or spouse.get("marriage_location") or "")
        for spouse in profile.get("Spouses") or []
    )
    return [(field, value) for field, value in result if value]


def surname_variant(profile: dict) -> bool:
    return (profile.get("LastNameAtBirth") or "").lower() in SURNAME_VARIANTS


def spouse_profiles(profile: dict, profiles: dict, by_numeric_id: dict[str, dict]):
    spouses = profile.get("Spouses") or []
    if isinstance(spouses, dict):
        spouses = spouses.values()
    for spouse in spouses:
        if not isinstance(spouse, dict):
            continue
        yield (
            by_numeric_id.get(str(spouse.get("Id") or ""))
            or profiles.get(spouse.get("Name"))
            or spouse
        )


def included_person(profile: dict, profiles: dict, by_numeric_id: dict[str, dict]) -> bool:
    if profile.get("Name") in INTENTIONALLY_UNMAPPED_PROFILE_IDS:
        return False
    if surname_variant(profile):
        return True
    if profile.get("Gender") != "Female":
        return False
    if (profile.get("LastNameCurrent") or "").lower() in SURNAME_VARIANTS:
        return True
    return any(surname_variant(spouse) for spouse in spouse_profiles(profile, profiles, by_numeric_id))


def has_region(location: str, region: str) -> bool:
    components = {normalized(component) for component in location.split(",")}
    return bool(components & REGION_COMPONENTS[region])


def chosen_event(profile: dict, region: str) -> tuple[str, str] | None:
    if region in REGION_COMPONENTS:
        candidates = [(field, value) for field, value in events(profile) if has_region(value, region)]
    else:
        candidates = [
            (field, value) for field, value in events(profile)
            if "united kingdom" in {normalized(component) for component in value.split(",")}
            and not any(has_region(value, named_region) for named_region in REGION_COMPONENTS)
        ]
    if not candidates:
        return None
    birth = next((event for event in candidates if event[0] == "BirthLocation"), None)
    death = next((event for event in candidates if event[0] == "DeathLocation"), None)
    if birth:
        country_names = {region.lower()}
        if region == "Ireland":
            country_names.add("northern ireland")
        if normalized(birth[1]) in country_names and death and normalized(death[1]) not in country_names:
            return death
        return birth
    if death:
        return death
    return candidates[0]


def infer_region(location: str) -> str:
    """Infer a country from profile text, including historical county-only forms."""
    for region in REGION_COMPONENTS:
        if has_region(location, region):
            return region
    text = normalized(location)
    if SCOTTISH_HINTS.search(text):
        return "Scotland"
    if IRISH_HINTS.search(text) or "n. ireland" in text:
        return "Ireland"
    if "united kingdom" in text or text in {"uk", "great britain"}:
        return "United Kingdom"
    if US_HINTS.search(text) or re.search(r"(?:^|,\s*)(?:pa|va|nc|sc|tn|oh|ar|mo|ia|il|tx|ca|ny|nj|fl|mi|ga|al|ky|la|mn|wa|dc)\.?$", text, re.I):
        return "United States"
    if CANADA_HINTS.search(text):
        return "Canada"
    if re.search(r"\b(?:australia|queensland|new south wales|victoria|tasmania|western australia)\b", text):
        return "Australia"
    if re.search(r"\b(?:new zealand|auckland|canterbury|otago|wellington|oromahoe)\b", text):
        return "New Zealand"
    for region in ("India", "France", "South Africa", "Portugal"):
        if region.lower() in text:
            return region
    if re.search(r"\b(?:barbados|jamaica|guyana|british guiana|saint vincent|cuba)\b", text):
        return "Caribbean"
    if re.search(r"\b(?:at sea|atlantic ocean)\b", text):
        return "At Sea"
    return "Unspecified"


def primary_event(profile: dict) -> tuple[str, str]:
    available = events(profile)
    for field in ("BirthLocation", "DeathLocation", "MarriageLocation"):
        match = next((event for event in available if event[0] == field), None)
        if match:
            return match
    return "Unlocated", ""


def children_index(profiles: dict[str, dict]) -> dict[str, list[dict]]:
    """Index children by the numeric WikiTree ID stored in Father/Mother."""
    result = defaultdict(list)
    for profile in profiles.values():
        for field in ("Father", "Mother"):
            parent_id = str(profile.get(field) or "")
            if parent_id and parent_id not in {"0", "-1"}:
                result[parent_id].append(profile)
    return result


def direct_location_events(profile: dict) -> list[tuple[str, str]]:
    """Return one preferred direct value for each birth/death location field."""
    result = []
    for field, corrected_field in (
        ("BirthLocation", "CorrectedBirthLocation"),
        ("DeathLocation", "CorrectedDeathLocation"),
    ):
        location = profile.get(corrected_field) or profile.get(field) or ""
        if location and normalized(location) not in {"unknown", "not known", "unspecified", "?"}:
            result.append((field, location))
    return result


def profile_label(profile: dict) -> str:
    return (
        profile.get("LongName") or profile.get("BirthName")
        or profile.get("RealName") or profile.get("Name") or "relative"
    )


def infer_location_from_kin(
    profile: dict,
    profiles: dict[str, dict],
    by_numeric_id: dict[str, dict],
    children_by_parent: dict[str, list[dict]],
) -> dict | None:
    """Infer a missing location from the nearest relative with a direct event."""
    profile_name = profile.get("Name") or ""
    profile_numeric_id = str(profile.get("Id") or "")

    parents = []
    for field, relationship in (("Father", "father"), ("Mother", "mother")):
        relative = by_numeric_id.get(str(profile.get(field) or ""))
        if relative:
            parents.append((relationship, relative))

    spouses = [("spouse", relative) for relative in spouse_profiles(profile, profiles, by_numeric_id)]
    children = [
        ("child", relative)
        for relative in children_by_parent.get(profile_numeric_id, [])
        if relative.get("Name") != profile_name
    ]
    siblings = []
    for parent_id in {str(profile.get("Father") or ""), str(profile.get("Mother") or "")} - {"", "0", "-1"}:
        siblings.extend(
            ("sibling", relative)
            for relative in children_by_parent.get(parent_id, [])
            if relative.get("Name") != profile_name
        )

    seen_relatives = set()
    tiers = []
    for tier in (spouses, parents, children, siblings):
        unique = []
        for relationship, relative in tier:
            key = relative.get("Name") or str(relative.get("Id") or "") or profile_label(relative)
            if key in seen_relatives:
                continue
            seen_relatives.add(key)
            unique.append((relationship, relative))
        tiers.append(unique)

    field_priority = {
        "spouse": {"BirthLocation": 2, "DeathLocation": 1},
        "father": {"DeathLocation": 2, "BirthLocation": 1},
        "mother": {"DeathLocation": 2, "BirthLocation": 1},
        "child": {"BirthLocation": 2, "DeathLocation": 1},
        "sibling": {"BirthLocation": 2, "DeathLocation": 1},
    }
    for relatives in tiers:
        candidates = []
        for relationship, relative in relatives:
            for field, location in direct_location_events(relative):
                candidates.append({
                    "relationship": relationship,
                    "relative": relative,
                    "field": field,
                    "location": location,
                    "key": normalized(location),
                })
        if not candidates:
            continue
        counts = Counter(candidate["key"] for candidate in candidates)
        candidates.sort(key=lambda candidate: (
            -counts[candidate["key"]],
            -field_priority[candidate["relationship"]][candidate["field"]],
            -len([part for part in candidate["location"].split(",") if part.strip()]),
            candidate["key"],
        ))
        best = candidates[0]
        event_label = "birthplace" if best["field"] == "BirthLocation" else "death place"
        relative = best["relative"]
        return {
            "field": best["field"],
            "location": best["location"],
            "relationship": best["relationship"],
            "relative_id": relative.get("Name") or "",
            "relative_name": profile_label(relative),
            "event_label": event_label,
            "support_count": counts[best["key"]],
            "basis": f"{best['relationship']} {profile_label(relative)}’s {event_label}",
        }
    return None


def fallback_place(region: str, location: str) -> dict:
    latitude, longitude = REGION_CENTRES.get(region, REGION_CENTRES["Unspecified"])
    if not location:
        return {
            "location_id": "unlocated_onetree_profiles",
            "record_location": "Location not supplied — profile holding point",
            "record_precision": "Non-geographic holding point",
            "location_basis": "Not evidence of residence; shown offshore only so an unlocated profile remains selectable in the map and table.",
            "latitude": latitude,
            "longitude": longitude,
            "source": "unlocated-fallback",
        }
    digest = hashlib.sha1(normalized(location).encode("utf-8")).hexdigest()[:12]
    return {
        "location_id": f"profile_place_{digest}",
        "record_location": location,
        "record_precision": "Country-centre fallback for profile locality",
        "location_basis": f"The profile locality is retained for searching and grouping; its pin uses the {region if region != 'Unspecified' else 'neutral'} centre because no verified coordinate is available.",
        "latitude": latitude,
        "longitude": longitude,
        "source": "country-fallback",
    }


def seed_places(rows: list[dict]) -> dict[str, dict]:
    result = {}
    for row in rows:
        match = re.search(r"Profile-stated [^:]+:\s*(.*)$", row["association"])
        if not match or not row.get("region"):
            continue
        key = row["region"] + "|" + normalized(match.group(1))
        result.setdefault(key, {
            "location_id": row["location_id"],
            "record_location": row["record_location"],
            "record_precision": row["record_precision"],
            "location_basis": row["location_basis"],
            "latitude": float(row["latitude"]),
            "longitude": float(row["longitude"]),
            "source": "existing-map",
        })
    return result


def built_in_place(region: str, location: str) -> dict | None:
    try:
        if region == "Ireland":
            place = ireland_sync.resolve_place(location)
        elif region == "Scotland":
            place = scotland_sync.resolve_place(location)
        else:
            return None
    except ValueError:
        return None
    result = asdict(place)
    result["record_location"] = result.pop("label")
    result["record_precision"] = result.pop("precision")
    result["location_basis"] = result.pop("basis")
    result["source"] = "built-in"
    return result


class Geocoder:
    def __init__(self, enabled: bool):
        self.enabled = enabled
        self.cache = json.loads(CACHE_PATH.read_text(encoding="utf-8")) if CACHE_PATH.exists() else {}
        self.calls = 0
        self.last_request = 0.0

    def save(self) -> None:
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        CACHE_PATH.write_text(json.dumps(self.cache, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    def lookup(self, region: str, location: str) -> dict:
        key = region + "|" + normalized(location)
        if key in self.cache and not (self.enabled and self.cache[key].get("source") == "country-fallback"):
            return self.cache[key]
        if not self.enabled:
            raise RuntimeError(f"Missing cached geocode for {location!r}; rerun with --geocode")
        matches = []
        queries = [location]
        simplified = location.split(",", 1)[0].strip() + ", " + region
        if normalized(simplified) != normalized(location):
            queries.append(simplified)
        if normalized(location).startswith("stitchill,"):
            queries.append("Stichill, Scotland")
        for query in queries:
            wait = 1.05 - (time.monotonic() - self.last_request)
            if wait > 0:
                time.sleep(wait)
            params = urllib.parse.urlencode({
                "q": query,
                "format": "jsonv2",
                "limit": 1,
                "addressdetails": 1,
                "countrycodes": "gb,ie",
            })
            request = urllib.request.Request(
                "https://nominatim.openstreetmap.org/search?" + params,
                headers={
                    "User-Agent": "wikitree-family-map-research/1.0 (local genealogy map)",
                    "Referer": "https://www.wikitree.com/",
                },
            )
            self.last_request = time.monotonic()
            try:
                with urllib.request.urlopen(request, timeout=30) as response:
                    matches = json.load(response)
            except Exception as exc:
                raise RuntimeError(f"Geocode request failed for {query!r}: {exc}") from exc
            if matches:
                break
        self.calls += 1
        if matches:
            match = matches[0]
            location_id = f"osm_{match.get('osm_type', 'place')}_{match.get('osm_id', self.calls)}"
            result = {
                "location_id": location_id,
                "record_location": location,
                "record_precision": "Geocoded profile locality",
                "location_basis": "Coordinates returned by OpenStreetMap Nominatim for the profile-stated locality; the profile field remains a research lead.",
                "latitude": float(match["lat"]),
                "longitude": float(match["lon"]),
                "source": "nominatim",
                "display_name": match.get("display_name", ""),
            }
        else:
            latitude, longitude = REGION_CENTRES[region]
            result = {
                "location_id": region.lower().replace(" ", "_") + "_unspecified",
                "record_location": region + " — exact locality unresolved",
                "record_precision": "Country-level fallback point",
                "location_basis": f"The profile states {location!r}, but automated geocoding did not resolve it; the point represents {region}.",
                "latitude": latitude,
                "longitude": longitude,
                "source": "country-fallback",
            }
        self.cache[key] = result
        self.save()
        if self.calls % 25 == 0:
            print(f"Resolved {self.calls} new locality strings", flush=True)
        return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--geocode", action="store_true", help="Query Nominatim for uncached places")
    args = parser.parse_args()

    profiles, export_paths = merged_map_profiles()
    by_numeric_id = {
        str(profile.get("Id")): profile
        for profile in profiles.values()
        if profile.get("Id")
    }
    children_by_parent = children_index(profiles)
    with CSV_PATH.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)

    regions = list(REGION_COMPONENTS) + ["United Kingdom"]
    regenerated_groups = {
        group
        for region in regions
        for group in (f"{region} profile leads through 1900", f"{region} One-Tree profile leads")
    }
    regenerated_groups.add("Worldwide One-Tree profile leads")
    rows = [row for row in rows if row["family_group"] not in regenerated_groups]
    mapped_ids = {
        profile_id.lower()
        for row in rows
        for profile_id in PROFILE_ID.findall(row["profile_id"])
    }
    seeds = seed_places(rows)
    geocoder = Geocoder(args.geocode)
    qualifying = []
    for profile in profiles.values():
        if not included_person(profile, profiles, by_numeric_id):
            continue
        birth_year, year_label, estimated = display_birth_year(profile)
        event = primary_event(profile)
        inference = None
        if event[0] == "Unlocated":
            inference = infer_location_from_kin(profile, profiles, by_numeric_id, children_by_parent)
            if inference:
                event = (inference["field"], inference["location"])
        region = infer_region(event[1])
        qualifying.append((birth_year, profile["Name"], profile, region, event, year_label, estimated, inference))
    qualifying.sort(key=lambda item: (item[0], item[1], item[3]))

    added = []
    fallback_ids = []
    kin_inferred = []
    for birth_year, name, profile, region, (event_field, event_location), year_label, estimated, inference in qualifying:
        if name.lower() in mapped_ids:
            continue
        place_key = region + "|" + normalized(event_location)
        place = seeds.get(place_key) or built_in_place(region, event_location)
        if not place and place_key in geocoder.cache:
            place = geocoder.lookup(region, event_location)
        place = dict(place or fallback_place(region, event_location))
        event_label = {"BirthLocation": "birthplace", "DeathLocation": "death place", "MarriageLocation": "marriage place", "Unlocated": "location"}[event_field]
        if inference:
            direct_basis = place["location_basis"]
            place["record_precision"] = "Kin-inferred relationship locality"
            place["location_basis"] = (
                f"Inferred from {inference['basis']}; this location is not stated for {profile_label(profile)}. "
                + direct_basis
            )
        group = f"{region} One-Tree profile leads" if region in regions else "Worldwide One-Tree profile leads"
        rows.append({
            "person": profile.get("LongName") or profile.get("BirthName") or name,
            "profile_id": name,
            "region": region,
            "family_group": group,
            "subcluster": "One-Tree profile cohort" + (" · kin-inferred" if inference else ""),
            "evidence": "Kin-inferred One-Tree profile lead" if inference else "One-Tree profile lead",
            "year": year_label,
            "filter_year": str(birth_year) if birth_year else "",
            "association": (
                f"Kin-inferred from {inference['basis']}: {event_location}"
                if inference else f"Profile-stated {event_label}: {event_location}"
            ),
            "note": "One-Tree export profile fields are search leads, not sources; relationships are shown only where the export supplies parent links."
            + (" This map placement is an estimate from kin and is not a directly recorded location for this person." if inference else "")
            + (" Birth year is estimated as 18 years before the earliest marriage, or otherwise 18 years before death." if estimated and birth_year else ""),
            "location_id": place["location_id"],
            "record_location": place["record_location"],
            "record_precision": place["record_precision"],
            "location_basis": place["location_basis"],
            "latitude": str(place["latitude"]),
            "longitude": str(place["longitude"]),
        })
        mapped_ids.add(name.lower())
        added.append(f"{name}|{region}")
        if inference:
            kin_inferred.append({"profile_id": name, **inference})
        if place.get("source") == "country-fallback":
            fallback_ids.append(f"{name}|{region}|{event_location}")

    with CSV_PATH.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    missing = [name for _, name, _, _, _, _, _, _ in qualifying if name.lower() not in mapped_ids]
    audit = {
        "exports": [path.name for path in export_paths],
        "merged_profile_count": len(profiles),
        "cutoff_birth_year": None,
        "selection": "Every locally known Glasgow surname variant, plus women married to Glasgows, regardless of date or country",
        "qualifying_profiles": len(qualifying),
        "estimated_or_undated_associations": sum(item[6] for item in qualifying),
        "newly_added": len(added),
        "new_geocoder_requests": geocoder.calls,
        "kin_inferred_associations": kin_inferred,
        "country_fallbacks": fallback_ids,
        "remaining_missing": missing,
    }
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    AUDIT_PATH.write_text(json.dumps(audit, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if missing:
        raise SystemExit(f"Audit failed: {len(missing)} associations remain missing")
    print(f"{len(qualifying)} qualifying profiles; added {len(added)}; {len(kin_inferred)} kin-inferred; {len(fallback_ids)} country fallbacks; 0 missing")


if __name__ == "__main__":
    main()
