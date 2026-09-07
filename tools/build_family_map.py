#!/usr/bin/env python3
"""Rebuild the embedded family-map dataset from the authoritative CSV."""

from __future__ import annotations

import csv
from datetime import date
from hashlib import sha1
import json
import re
from collections import defaultdict, deque
try:
    from project_paths import (
        MAP_HTML as HTML_PATH, HUB_HTML, MAP_RECORDS as CSV_PATH,
        MAP_EARLY_BEARERS, MAP_YDNA_TIMELINE, RESEARCH_DIR,
        SURNAME_RESEARCH_DIR, WIKITREE_PROFILE_EVIDENCE,
        WIKITREE_CATALOGUE_PROFILE_LINKS, merged_map_profiles,
    )
    from build_research_catalog import build_research_catalog, catalogue_profile_update_ids
except ModuleNotFoundError:  # Imported as tools.build_family_map in tests.
    from tools.project_paths import (
        MAP_HTML as HTML_PATH, HUB_HTML, MAP_RECORDS as CSV_PATH,
        MAP_EARLY_BEARERS, MAP_YDNA_TIMELINE, RESEARCH_DIR,
        SURNAME_RESEARCH_DIR, WIKITREE_PROFILE_EVIDENCE,
        WIKITREE_CATALOGUE_PROFILE_LINKS, merged_map_profiles,
    )
    from tools.build_research_catalog import build_research_catalog, catalogue_profile_update_ids
GLASGOW_ID = re.compile(
    r"(?:Glasgow|Glasco|Glassco|Glascoe|Glasgo|Glasow|Glascow|Glasoe|Glassgow|Glassgo|Glasko)-\d+",
    re.I,
)
WIKITREE_ID = re.compile(r"[A-Za-z][A-Za-z_'’]*(?:-[A-Za-z][A-Za-z_'’]*)*-\d+")
DUPLICATE_PROFILE_IDS = {"Glasgow-3472", "Glasgow-3927"}
EXCLUDED_MAP_GROUPS = {"Associated person"}
# Historically meaningful branch founders can remain Roots even when WikiTree
# also supplies an asserted ancestral chain above them.
CURATED_BRANCH_ROOT_IDS = {"Glasgow-1078"}
KNOWN_DESCENDANT_COUNTS = {
    "Glasgow-506": 30, "Glasgow-591": 34, "Glasgow-635": 178,
    "Glasgow-822": 158, "Glasgow-971": 32, "Glasgow-1026": 169,
    "Glasgow-1078": 136, "Glasgow-1101": 0, "Glasgow-1136": 0,
    "Glasgow-1189": 6, "Glasgow-1190": 13, "Glasgow-1241": 0,
    "Glasgow-1622": 1, "Glasgow-1655": 56, "Glasgow-1657": 67,
    "Glasgow-1675": 11, "Glasgow-1970": 7, "Glasgow-2057": 19,
    "Glasgow-2058": 12, "Glasgow-2074": 4, "Glasgow-2249": 63,
    "Glasgow-2539": 35, "Glasgow-2656": 0, "Glasgow-2824": 3,
    "Glasgow-2880": 3, "Glasgow-2917": 93, "Glasgow-2972": 2,
    "Glasgow-2988": 2, "Glasgow-3001": 0, "Glasgow-3124": 0,
    "Glasgow-3126": 1, "Glasgow-3135": 1, "Glasgow-3137": 0,
    "Glasgow-3171": 0, "Glasgow-3172": 0, "Glasgow-3175": 0,
    "Glasgow-3439": 12, "Glasgow-3443": 0, "Glasgow-3444": 0,
    "Glasgow-3449": 0, "Glasgow-3556": 0, "Glasgow-3593": 4,
    "Glasgow-3814": 0, "Glasgow-3905": 49, "Glasgow-3920": 3,
}
PROFILE_METADATA_OVERRIDES = {
    # Updated on WikiTree after the latest local One-Tree export.
    "Glasgow-4063": {
        "first_name": "Robert", "last_name_at_birth": "Glasgow",
        "last_name_current": "Glasgow", "gender": "Male",
        "death_date": "1560-03-23", "death_location": "Holkham, Norfolk, England",
        "death_status": "certain",
    },
    "Glasgow-3941": {
        "first_name": "Robert", "last_name_at_birth": "Glasgow",
        "last_name_current": "Glasgow", "gender": "Male",
        "birth_date": "1776-00-00", "birth_status": "before",
    },
    "Glasgow-3549": {
        "birth_date": "1704-08-20", "birth_location": "Ayrshire, Scotland",
        "birth_status": "", "gender": "Male",
    },
    "Glasgow-1052": {
        "birth_date": "1822-00-00", "birth_status": "guess", "gender": "Male",
    },
    "Glasgow-1421": {
        "birth_date": "1870-05-09", "birth_location": "Ballymoney, County Antrim, Ireland",
        "birth_status": "", "gender": "Male",
    },
    "Glasgow-569": {
        "birth_date": "1860-00-00", "birth_location": "Funchal, Madeira, Portugal",
        "birth_status": "guess", "gender": "Male",
    },
    "Glasgow-3375": {
        "birth_date": "1661-00-00", "birth_location": "Kilwinning, Ayrshire, Scotland",
        "birth_status": "before", "gender": "Male",
    },
    "Glasgow-3023": {
        "birth_date": "1500-00-00", "death_date": "1500-00-00",
        "birth_location": "Scotland", "death_location": "Jedburgh, Roxburghshire, Scotland",
        "birth_status": "guess", "death_status": "guess", "gender": "Male",
    },
    "Glasgow-1790": {
        "first_name": "Mary Anne", "last_name_at_birth": "Glasgow", "last_name_current": "Smith",
        "birth_date": "1866-00-00", "death_date": "1958-11-19",
        "birth_location": "Ireland", "death_location": "Ontario, Canada", "gender": "Female",
    },
}


def _record_slug(value: str) -> str:
    value = value.casefold().replace("’", "'")
    return re.sub(r"[^a-z0-9]+", "-", value).strip("-") or "other"


def apply_catalogue_profile_links(records: list[dict]) -> int:
    """Apply reviewed static-site link requests before map/catalogue grouping."""
    if not WIKITREE_CATALOGUE_PROFILE_LINKS.exists():
        return 0
    entries = json.loads(WIKITREE_CATALOGUE_PROFILE_LINKS.read_text(encoding="utf-8")).get("entries", {})
    grouped = defaultdict(list)
    for record in records:
        if not record.get("profile_id"):
            key = record.get("supplement_id") or f"{record.get('person', '')}|{record.get('family_group', '')}"
            grouped[key].append(record)
    applied = 0
    for key, rows in grouped.items():
        supplement = rows[0].get("supplement_id")
        catalogue_id = (
            f"record-{_record_slug(supplement)}" if supplement else
            f"record-{_record_slug(rows[0].get('person', 'person'))}-{sha1(key.encode()).hexdigest()[:10]}"
        )
        entry = entries.get(catalogue_id) or {}
        record_profiles = entry.get("record_profiles") or {}
        record_splits = entry.get("record_splits") or {}
        if record_profiles or record_splits:
            for row in rows:
                source_title = str(row.get("source_title") or "")
                profile_id = str(record_profiles.get(source_title) or "")
                if WIKITREE_ID.fullmatch(profile_id):
                    row["profile_id"] = profile_id
                    applied += 1
                split_id = str(record_splits.get(source_title) or "")
                if split_id and not row.get("profile_id"):
                    row["supplement_id"] = split_id
            continue
        profile_id = str(entry.get("profile_id") or "")
        if not WIKITREE_ID.fullmatch(profile_id):
            continue
        for row in rows:
            row["profile_id"] = profile_id
            applied += 1
    return applied
IRISH_COUNTY_LOCATION_IDS = {
    "Antrim": {
        "ballyboley_larne", "ballykeel_kilwaughter", "ballymena", "ballymoney_town",
        "belfast", "drumcon", "glenarm_town", "glenleslie", "gortereghy", "killoquin_ed",
        "kilroot", "kilwaughter", "kilwaughter_demesne", "larne_town", "lisburn",
        "lisnagaver", "moneyleck", "portglenone_reference", "rasharkin",
    },
    "Armagh": {"armagh_city"},
    "Donegal": {
        "aughnish_donegal", "ballindrait_raphoe", "ballyshannon", "cloghole",
        "clondavaddog_parish", "killybegs", "ramelton", "shannon_clonleigh", "tullyfern_parish",
    },
    "Down": {"belfast", "lisburn"},
    "Dublin": {"christchurch_dublin", "dublin_city", "ormond_quay", "st_john_dublin"},
    "Leitrim": {"gortaggle_leitrim", "lareen_leitrim"},
    "Londonderry": {
        "boveedy", "coleraine", "coltrim", "derry_city", "desertoghill", "drimbolg",
        "drumcon", "drumearn", "drumlamph", "dunnabraggy", "first_kilrea", "inishrush",
        "kilrea_town", "lissan_parish", "magherabeg_londonderry", "magherafelt", "moneymore",
        "portglenone_reference", "st_nossonus", "tamlaght_parish", "tyanee",
    },
    "Longford": {"lanesborough"},
    "Louth": {"drogheda"},
    "Tyrone": {
        "cavankilgreen", "cookstown", "derryloran_parish", "drummond_derryloran",
        "kildress_parish", "lissan_parish", "loy", "st_luran",
    },
    "Wicklow": {"county_wicklow_reference"},
}
IRISH_COUNTIES = (
    "Antrim|Armagh|Carlow|Cavan|Clare|Cork|Donegal|Down|Dublin|Fermanagh|Galway|Kerry|"
    "Kildare|Kilkenny|Laois|Leitrim|Limerick|Londonderry|Longford|Louth|Mayo|Meath|"
    "Monaghan|Offaly|Roscommon|Sligo|Tipperary|Tyrone|Waterford|Westmeath|Wexford|Wicklow"
)
IRISH_COUNTY_RE = re.compile(rf"\bCounty\s+({IRISH_COUNTIES})\b", re.I)
NORTHERN_IRELAND_COUNTIES = {"Antrim", "Armagh", "Down", "Fermanagh", "Londonderry", "Tyrone"}


def load_records() -> list[dict]:
    with CSV_PATH.open(encoding="utf-8-sig", newline="") as handle:
        records = [
            record
            for record in csv.DictReader(handle)
            if record["family_group"] not in EXCLUDED_MAP_GROUPS
        ]
    for record in records:
        for field in ("filter_year", "latitude", "longitude"):
            value = record[field].strip()
            record[field] = float(value) if value else None
    return records


def location_search_index(records: list[dict]) -> dict[str, list[str]]:
    """Build country/county aliases for each granular mapped location."""
    rows_by_location = defaultdict(list)
    for record in records:
        rows_by_location[record["location_id"]].append(record)

    overrides = defaultdict(set)
    for county, location_ids in IRISH_COUNTY_LOCATION_IDS.items():
        for location_id in location_ids:
            overrides[location_id].add(county)

    result = {}
    for location_id, rows in rows_by_location.items():
        regions = {row["region"] for row in rows if row.get("region")}
        aliases = set(regions)
        counties = set(overrides.get(location_id, set()))
        if not counties and "Ireland" in regions:
            direct_text = " ".join(
                f'{row.get("record_location", "")} {row.get("location_basis", "")}'
                for row in rows
            )
            counties.update(match.title() for match in IRISH_COUNTY_RE.findall(direct_text))
        if "Ireland" in regions:
            aliases.update({"Ireland", "Eire", "Éire"})
            if counties & NORTHERN_IRELAND_COUNTIES:
                aliases.update({"Northern Ireland", "Ulster"})
            if counties and not counties & NORTHERN_IRELAND_COUNTIES:
                aliases.add("Republic of Ireland")
        for county in counties:
            aliases.update({county, f"County {county}", f"Co {county}", f"Co. {county}"})
            if county == "Londonderry":
                aliases.update({"Derry", "County Derry", "Co Derry", "Co. Derry"})
        result[location_id] = sorted(aliases)
    return result


def walk_objects(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk_objects(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_objects(child)


def relationship_edges(records: list[dict]) -> list[list[str]]:
    try:
        profiles, _ = merged_map_profiles()
    except FileNotFoundError:
        return []

    mapped_ids = {
        profile_id
        for record in records
        for profile_id in WIKITREE_ID.findall(record["profile_id"])
    }
    by_name = {}
    by_numeric_id = {}
    for item in profiles.values():
        name = item.get("Name")
        numeric_id = item.get("Id")
        if name and numeric_id:
            by_name.setdefault(name, item)
            by_numeric_id[str(numeric_id)] = name

    edges = set()
    for child_name in mapped_ids:
        child = by_name.get(child_name)
        if not child:
            continue
        for field in ("Father", "Mother"):
            parent_name = by_numeric_id.get(str(child.get(field) or ""))
            if parent_name in mapped_ids and parent_name != child_name:
                edges.add((parent_name, child_name))
    return [list(edge) for edge in sorted(edges)]


def root_metadata(records: list[dict], edges: list[list[str]]) -> tuple[list[str], dict[str, int], dict[str, list[list[object]]]]:
    mapped_ids = {
        profile_id
        for record in records
        for profile_id in WIKITREE_ID.findall(record["profile_id"])
        if GLASGOW_ID.fullmatch(profile_id) and profile_id not in DUPLICATE_PROFILE_IDS
    }
    parents = defaultdict(set)
    children = defaultdict(set)
    for parent, child in edges:
        if parent in mapped_ids and child in mapped_ids:
            parents[child].add(parent)
            children[parent].add(child)

    links = {}
    for profile_id in sorted(mapped_ids):
        queue = deque([(profile_id, 0)])
        shortest = {profile_id: 0}
        roots = {}
        while queue:
            current, distance = queue.popleft()
            current_parents = parents[current]
            if not current_parents:
                roots[current] = min(distance, roots.get(current, distance))
                continue
            for parent in current_parents:
                next_distance = distance + 1
                if next_distance < shortest.get(parent, 10**9):
                    shortest[parent] = next_distance
                    queue.append((parent, next_distance))
        if not roots:
            roots[profile_id] = 0
        links[profile_id] = [[root, distance] for root, distance in sorted(roots.items())]

    for root in sorted(CURATED_BRANCH_ROOT_IDS & mapped_ids):
        queue = deque([(root, 0)])
        seen = {root}
        while queue:
            current, distance = queue.popleft()
            if [root, distance] not in links[current]:
                links[current].append([root, distance])
                links[current].sort()
            for child in children[current]:
                if child not in seen:
                    seen.add(child)
                    queue.append((child, distance + 1))

    patriarch_ids = sorted({root for profile_links in links.values() for root, _ in profile_links})
    descendant_counts = {}
    for root in patriarch_ids:
        seen = {root}
        queue = deque([root])
        while queue:
            current = queue.popleft()
            for child in children[current]:
                if child not in seen:
                    seen.add(child)
                    queue.append(child)
        descendant_counts[root] = KNOWN_DESCENDANT_COUNTS.get(root, len(seen) - 1)
    return patriarch_ids, descendant_counts, links


def profile_metadata(records: list[dict], include_profile_ids: set[str] | None = None) -> dict[str, dict]:
    try:
        profiles, _ = merged_map_profiles()
    except FileNotFoundError:
        return {}
    live_evidence = {}
    if WIKITREE_PROFILE_EVIDENCE.exists():
        live_evidence = json.loads(
            WIKITREE_PROFILE_EVIDENCE.read_text(encoding="utf-8")
        ).get("profiles", {})
        for profile_id, evidence in live_evidence.items():
            fields = evidence.get("profile_fields") or {}
            current = profiles.get(profile_id, {})
            try:
                evidence_public = int(fields.get("Privacy") or current.get("Privacy") or 0) >= 50
            except (TypeError, ValueError):
                evidence_public = False
            if fields.get("Name") and evidence_public:
                current_touched = str(current.get("Touched") or "")
                evidence_touched = str(fields.get("Touched") or evidence.get("last_updated") or "")
                if not current_touched or not evidence_touched or evidence_touched >= current_touched:
                    profiles.setdefault(profile_id, {}).update(fields)
            spouses = (evidence.get("relations") or {}).get("spouses") or []
            current_touched = str(profiles.get(profile_id, {}).get("Touched") or "")
            evidence_touched = str(fields.get("Touched") or evidence.get("last_updated") or "")
            if evidence_public and spouses and (not current_touched or not evidence_touched or evidence_touched >= current_touched):
                profiles.setdefault(profile_id, {})["Spouses"] = [
                    {
                        "Name": spouse.get("id") or "",
                        "LongName": spouse.get("name") or "",
                        "BirthName": spouse.get("name") or "",
                        "MarriageDate": spouse.get("marriage_date") or "",
                        "MarriageLocation": spouse.get("marriage_location") or "",
                    }
                    for spouse in spouses
                ]
    by_numeric_id = {
        str(profile.get("Id")): profile
        for profile in profiles.values()
        if profile.get("Id")
    }

    def likely_living(profile: dict) -> bool:
        if profile.get("DeathDate") not in (None, "", "0000-00-00") or profile.get("DeathLocation"):
            return False
        birth_match = re.match(r"^(\d{4})", profile.get("BirthDate") or "")
        return bool(birth_match and int(birth_match.group(1)) >= date.today().year - 120)

    def profile_name(profile: dict) -> str:
        return (
            profile.get("LongName") or profile.get("BirthName")
            or " ".join(
                part for part in (
                    profile.get("Prefix"), profile.get("FirstName") or profile.get("RealName"),
                    profile.get("MiddleName"), profile.get("LastNameCurrent") or profile.get("LastNameAtBirth"),
                    profile.get("Suffix"),
                ) if part
            )
            or profile.get("Name") or ""
        )

    def relation_profile(profile: dict | None) -> dict | None:
        if not profile:
            return None
        profile_id = profile.get("Name") or ""
        profile_display_name = profile_name(profile)
        return {
            "id": profile_id, "name": profile_display_name, "outside_export": False,
            "likely_living": likely_living(profile),
        } if profile_id or profile_display_name else None

    children_by_parent = defaultdict(list)
    for child in profiles.values():
        child_relation = relation_profile(child)
        if not child_relation:
            continue
        for field in ("Father", "Mother"):
            parent = by_numeric_id.get(str(child.get(field) or ""))
            if parent and parent.get("Name"):
                children_by_parent[parent["Name"]].append(child_relation)

    def parent_profile(numeric_id, data_status="") -> dict | None:
        if not numeric_id:
            return None
        parent = relation_profile(by_numeric_id.get(str(numeric_id)))
        result = parent or {
            "id": "", "name": "Parent outside current One-Tree export",
            "numeric_id": str(numeric_id), "outside_export": True,
            "likely_living": False,
        }
        result["data_status"] = str(data_status or "")
        return result

    mapped_ids = {
        profile_id.lower()
        for record in records
        for profile_id in WIKITREE_ID.findall(record["profile_id"])
    }
    selected_ids = mapped_ids | {profile_id.casefold() for profile_id in (include_profile_ids or set())}

    research_ids = set()
    for base in (RESEARCH_DIR, SURNAME_RESEARCH_DIR):
        if not base.exists():
            continue
        for path in base.rglob("*.md"):
            research_ids.update(WIKITREE_ID.findall(path.name))
            try:
                research_ids.update(WIKITREE_ID.findall(path.read_text(encoding="utf-8")))
            except UnicodeDecodeError:
                continue
    research_ids = {profile_id.lower() for profile_id in research_ids}

    duplicate_groups = defaultdict(list)
    for profile in profiles.values():
        birth_date = profile.get("BirthDate") or ""
        if not birth_date or birth_date.startswith("0000"):
            continue
        key = (
            re.sub(r"\W+", "", (profile.get("FirstName") or "").lower()),
            re.sub(r"\W+", "", (profile.get("MiddleName") or "").lower()),
            birth_date,
            re.sub(r"\W+", "", (profile.get("BirthLocation") or "").lower()),
        )
        if key[0] and key[3]:
            duplicate_groups[key].append(profile.get("Name"))
    duplicates = {
        profile_id: sorted(candidate for candidate in candidates if candidate != profile_id)
        for candidates in duplicate_groups.values() if len(candidates) > 1
        for profile_id in candidates
    }

    result = {}
    for profile in profiles.values():
        profile_id = profile.get("Name")
        if not profile_id or profile_id.lower() not in selected_ids:
            continue
        statuses = profile.get("DataStatus") or {}
        raw_spouses = profile.get("Spouses") or []
        if isinstance(raw_spouses, dict):
            raw_spouses = raw_spouses.values()
        evidence_spouses = {
            (spouse.get("id") or spouse.get("name") or "").casefold(): spouse
            for spouse in ((live_evidence.get(profile_id, {}).get("relations") or {}).get("spouses") or [])
            if isinstance(spouse, dict) and (spouse.get("id") or spouse.get("name"))
        }
        spouses = []
        seen_spouses = set()
        for spouse in raw_spouses:
            if not isinstance(spouse, dict):
                continue
            spouse_id = spouse.get("Name") or ""
            spouse_name = profile_name(spouse)
            key = spouse_id or spouse_name
            if not key or key in seen_spouses:
                continue
            seen_spouses.add(key)
            evidence_spouse = evidence_spouses.get(spouse_id.casefold()) or evidence_spouses.get(spouse_name.casefold()) or {}
            spouses.append({
                "id": spouse_id,
                "name": spouse_name,
                "marriage_date": spouse.get("MarriageDate") or spouse.get("marriage_date") or evidence_spouse.get("marriage_date") or "",
                "marriage_location": spouse.get("MarriageLocation") or spouse.get("marriage_location") or evidence_spouse.get("marriage_location") or "",
            })
        result[profile_id] = {
            "first_name": profile.get("FirstName") or profile.get("RealName") or "",
            "middle_name": profile.get("MiddleName") or "",
            "real_name": profile.get("RealName") or "",
            "full_name": profile_name(profile),
            "last_name_at_birth": profile.get("LastNameAtBirth") or "",
            "last_name_current": profile.get("LastNameCurrent") or "",
            "last_name_other": profile.get("LastNameOther") or "",
            "suffix": profile.get("Suffix") or "",
            "gender": profile.get("Gender") or "",
            "spouses": spouses,
            "children": sorted(
                {child["id"] or child["name"]: child for child in children_by_parent.get(profile_id, [])}.values(),
                key=lambda child: child["name"].casefold(),
            ),
            "birth_date": profile.get("BirthDate") or "",
            "death_date": profile.get("DeathDate") or "",
            "birth_location": profile.get("CorrectedBirthLocation") or profile.get("BirthLocation") or "",
            "death_location": profile.get("CorrectedDeathLocation") or profile.get("DeathLocation") or "",
            "father": bool(profile.get("Father")),
            "mother": bool(profile.get("Mother")),
            "father_profile": parent_profile(profile.get("Father"), statuses.get("Father")),
            "mother_profile": parent_profile(profile.get("Mother"), statuses.get("Mother")),
            "has_children": bool(profile.get("HasChildren")),
            "birth_status": statuses.get("BirthDate") or "",
            "death_status": statuses.get("DeathDate") or "",
            "research_note": profile_id.lower() in research_ids,
            "duplicate_candidates": duplicates.get(profile_id, []),
            "profile_created": profile.get("Created") or "",
            "profile_touched": profile.get("Touched") or "",
            "profile_connected": bool(profile.get("Connected")),
            "profile_children_count": profile.get("childrenCount"),
            "ydna": bool(profile.get("yDNA")),
            "audna": bool(profile.get("auDNA")),
            "likely_living": likely_living(profile),
        }
        profile_evidence = live_evidence.get(profile_id, {})
        evidence_fields = profile_evidence.get("profile_fields") or {}
        try:
            evidence_public = int(evidence_fields.get("Privacy") or profile.get("Privacy") or 0) >= 50
        except (TypeError, ValueError):
            evidence_public = False
        evidence_relations = (profile_evidence.get("relations") or {}) if evidence_public else {}
        evidence_touched = str(profile_evidence.get("last_updated") or "")
        if evidence_relations and (not result[profile_id]["profile_touched"] or not evidence_touched or evidence_touched >= result[profile_id]["profile_touched"]):
            # Children are always reconstructed from current Father/Mother
            # references. Unioning an older relationship snapshot here can
            # reintroduce a child after its parent was corrected on WikiTree.
            for field, relation_name in (("spouses", "spouses"),):
                live_relatives = [
                    {
                        "id": relative.get("id") or "",
                        "name": profile_name(profiles.get(relative.get("id") or "", {})) or relative.get("name") or relative.get("id") or "",
                        "outside_export": (relative.get("id") or "") not in profiles,
                        "likely_living": likely_living(profiles.get(relative.get("id") or "", {})),
                    }
                    for relative in evidence_relations.get(relation_name, [])
                    if relative.get("id") or relative.get("name")
                ]
                result[profile_id][field] = sorted(
                    {
                        relative["id"] or relative["name"]: relative
                        for relative in [*result[profile_id][field], *live_relatives]
                    }.values(),
                    key=lambda relative: relative["name"].casefold(),
                )
    for profile_id, override in PROFILE_METADATA_OVERRIDES.items():
        if profile_id.lower() not in selected_ids:
            continue
        result.setdefault(profile_id, {
            "first_name": "", "middle_name": "", "real_name": "", "full_name": "",
            "birth_date": "", "death_date": "",
            "birth_location": "", "death_location": "", "last_name_at_birth": "",
            "last_name_current": "", "last_name_other": "", "suffix": "", "gender": "", "spouses": [], "children": [], "father": False,
            "mother": False, "father_profile": None, "mother_profile": None,
            "has_children": False, "birth_status": "",
            "death_status": "", "research_note": profile_id.lower() in research_ids,
            "duplicate_candidates": [],
            "profile_created": "", "profile_touched": "", "profile_connected": False,
            "profile_children_count": None, "ydna": False, "audna": False,
            "likely_living": False,
        }).update(override)
    return result


def main() -> None:
    records = load_records()
    applied_profile_links = apply_catalogue_profile_links(records)
    dated_years = [int(record["filter_year"]) for record in records if record["filter_year"] is not None]
    data_year_range = {"min": min(1400, min(dated_years)), "max": max(dated_years)}
    ydna_timeline = json.loads(MAP_YDNA_TIMELINE.read_text(encoding="utf-8"))
    early_bearers = json.loads(MAP_EARLY_BEARERS.read_text(encoding="utf-8"))
    edges = relationship_edges(records)
    patriarch_ids, descendant_counts, root_links = root_metadata(records, edges)
    profiles = profile_metadata(records, catalogue_profile_update_ids())
    _, catalogue_export_paths = merged_map_profiles()
    location_index = location_search_index(records)
    html = HTML_PATH.read_text(encoding="utf-8")
    data_block = (
        "  // Generated by tools/build_family_map.py from the CSV and newest One-Tree export.\n"
        f"  const records = {json.dumps(records, ensure_ascii=False, separators=(',', ':'))};\n"
        f"  const dataYearRange = {json.dumps(data_year_range, separators=(',', ':'))};\n"
        f"  const relationshipEdges = {json.dumps(edges, ensure_ascii=False, separators=(',', ':'))};\n"
        f"  const profileMeta = {json.dumps(profiles, ensure_ascii=False, separators=(',', ':'))};\n"
        f"  const locationSearchIndex = {json.dumps(location_index, ensure_ascii=False, separators=(',', ':'))};\n"
        f"  const ydnaTimeline = {json.dumps(ydna_timeline, ensure_ascii=False, separators=(',', ':'))};\n"
        f"  const earlyBearers = {json.dumps(early_bearers, ensure_ascii=False, separators=(',', ':'))};\n"
    )
    html, replacements = re.subn(
        r"(?:  // Generated by tools/build_family_map\.py[^\n]*\n)*  const records = .*?(?=  const groups =)",
        data_block,
        html,
        count=1,
        flags=re.DOTALL,
    )
    if replacements != 1:
        raise SystemExit("Could not identify the embedded map-data block")

    root_block = (
        "  // Generated root view metadata from mapped One-Tree parent/child links.\n"
        f"  const patriarchIds = new Set({json.dumps(patriarch_ids, ensure_ascii=False, separators=(',', ':'))});\n"
        f"  const patriarchDescendantCounts = new Map(Object.entries({json.dumps(descendant_counts, ensure_ascii=False, separators=(',', ':'))}));\n"
        f"  const rootProfileLinks = new Map(Object.entries({json.dumps(root_links, ensure_ascii=False, separators=(',', ':'))}));\n"
    )
    html, root_replacements = re.subn(
        r"  // (?:Root view:|Generated root view metadata).*?(?=  const standalonePatriarchKeys)",
        root_block,
        html,
        count=1,
        flags=re.DOTALL,
    )
    if root_replacements != 1:
        raise SystemExit("Could not identify the root-view metadata block")

    location_count = len({record["location_id"] for record in records})
    html = re.sub(
        r"\d+ location pins for \d+ record associations\.",
        f"{location_count} location pins for {len(records)} record associations.",
        html,
        count=1,
    )
    html = re.sub(
        r"Explore [\d,]+ record associations across [\d,]+ mapped locations",
        f"Explore {len(records):,} record associations across {location_count:,} mapped locations",
        html,
        count=1,
    )
    # Remove the original Folium marker groups and layer control. The dynamic
    # renderer below uses the generated records and otherwise these stale
    # markers remain a large, hidden second map dataset.
    html, legacy_blocks = re.subn(
        r"\n\s*var feature_group_[\s\S]*?(?=\n</script>\n<script>\n\n\(function\(\)\{)",
        "\n",
        html,
        count=1,
    )
    if "var feature_group_" in html:
        raise SystemExit("Could not remove every legacy Folium marker group")
    HTML_PATH.write_text(html, encoding="utf-8")

    hub = HUB_HTML.read_text(encoding="utf-8")
    hub_stats = {
        "records": len(records),
        "locations": location_count,
        "roots": len(patriarch_ids),
        "ydna": len(ydna_timeline),
    }
    for stat_name, stat_value in hub_stats.items():
        hub = re.sub(
            rf'(<[^>]+data-stat="{stat_name}"[^>]*>)[^<]+',
            lambda match, value=stat_value: match.group(1) + f"{value:,}",
            hub,
        )
    refreshed = date.today()
    refreshed_label = f"{refreshed.day} {refreshed.strftime('%B %Y')}"
    hub = re.sub(
        r'(<time id="last-updated" datetime=")[^"]+(">)[^<]+',
        rf"\g<1>{refreshed.isoformat()}\g<2>{refreshed_label}",
        hub,
        count=1,
    )
    HUB_HTML.write_text(hub, encoding="utf-8")
    catalogue_stats = build_research_catalog(
        records, profiles, edges, descendant_counts, early_bearers,
        ydna_timeline, catalogue_export_paths, location_index, root_links,
    )
    print(
        f"Embedded {len(records)} records, {location_count} locations, {len(edges)} relationship edges and {len(patriarch_ids)} roots"
        + (f"; applied {applied_profile_links} reviewed profile link(s)" if applied_profile_links else "")
        + ("; removed legacy marker block" if legacy_blocks else "")
        + f"; generated {catalogue_stats['people']} catalogue people across {catalogue_stats['pages']} crawlable pages"
    )


if __name__ == "__main__":
    main()
