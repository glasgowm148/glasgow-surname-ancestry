#!/usr/bin/env python3
"""Build a crawlable, static research catalogue from the family-map data."""

from __future__ import annotations

import csv
from collections import Counter, defaultdict, deque
from datetime import date
from difflib import SequenceMatcher
from hashlib import sha1
from html import escape
import json
from math import asin, cos, radians, sin, sqrt
from pathlib import Path
import re
import unicodedata
from urllib.parse import quote, urlparse

try:
    from site_analytics import with_analytics
    from public_privacy import from_sources as privacy_from_sources, likely_living as privacy_likely_living, evidence_envelope, public_capture
    from records_page import records_body, records_assets
    import evidence_labels
    from catalogue_theme import CATALOGUE_ASSET_VERSION, write_catalogue_css
    from catalogue_search_markup import compact_statistics, hero_html as catalogue_hero_html, search_panel_html as catalogue_search_panel_html
    from catalogue_location_search import enrichment as catalogue_location_search_enrichment
    from project_paths import (
        RESEARCH_DIR, WEB_DIR, WIKITREE_PROFILE_EVIDENCE,
        WIKITREE_CATALOGUE_PROFILE_AUDIT, WIKITREE_CATALOGUE_PROFILE_LINKS,
    )
    from catalogue_machine_data import (
        SCHEMA_VERSION,
        build_machine_models,
        person_json_schema,
        write_machine_outputs,
    )
except ModuleNotFoundError:  # Imported as tools.build_research_catalog by tests.
    from tools.site_analytics import with_analytics
    from tools.public_privacy import from_sources as privacy_from_sources, likely_living as privacy_likely_living, evidence_envelope, public_capture
    from tools.records_page import records_body, records_assets
    from tools import evidence_labels
    from tools.catalogue_theme import CATALOGUE_ASSET_VERSION, write_catalogue_css
    from tools.catalogue_search_markup import compact_statistics, hero_html as catalogue_hero_html, search_panel_html as catalogue_search_panel_html
    from tools.catalogue_location_search import enrichment as catalogue_location_search_enrichment
    from tools.project_paths import (
        RESEARCH_DIR, WEB_DIR, WIKITREE_PROFILE_EVIDENCE,
        WIKITREE_CATALOGUE_PROFILE_AUDIT, WIKITREE_CATALOGUE_PROFILE_LINKS,
    )
    from tools.catalogue_machine_data import (
        SCHEMA_VERSION,
        build_machine_models,
        person_json_schema,
        write_machine_outputs,
    )


SITE_URL = "https://glasgow.phenotype.dev"
WIKITREE_URL = "https://www.wikitree.com/wiki/"
WIKITREE_ID = re.compile(r"[A-Za-z][A-Za-z_'’]*(?:-[A-Za-z][A-Za-z_'’]*)*-\d+")
CATALOGUE_DIR = WEB_DIR / "people"
DATA_DIR = WEB_DIR / "data"
RECORDS_DIR = WEB_DIR / "records"
PLACES_DIR = WEB_DIR / "places"
GENERATED_MARKER = ".generated-by-build-research-catalog"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROFILE_UPDATE_QUEUE = PROJECT_ROOT / "data/wikitree/profile-update-queue.json"
PROFILE_UPDATE_REGISTER = PROJECT_ROOT / "surname-research/to-update.md"
IGNORED_GENERATIONAL_SUFFIXES = {"jr", "sr", "i", "ii", "iii"}
GLASGOW_SURNAME_VARIANTS = frozenset({
    "glasgow", "glasco", "glassco", "glascoe", "glasgo", "glasow",
    "glascow", "glasoe", "glassgow", "glassgo", "glasko",
})
PARENTAGE_DIRECT_TREE_DIMENSIONS = frozenset({
    "current relationship", "exact-birth parent attachment",
    "parental couple structure", "matching child profile",
    "exact sibling profiles", "sibling-household replication",
    "sibling parental couple", "rare sibling-name pattern",
})

SCOTTISH_AREA_BY_LOCATION = {
    "ayr": "Ayrshire", "edinburgh": "Midlothian", "glasgow_scotland": "Lanarkshire",
    "inveresk": "Midlothian", "linlithgow": "West Lothian", "mid_calder": "West Lothian",
    "musselburgh": "Midlothian", "south_leith": "Midlothian", "osm_node_31816163": "Aberdeenshire",
}
SCOTTISH_AREA_PATTERNS = (
    ("Aberdeenshire", r"\baberdeenshire\b"), ("Angus", r"\bangus\b|\bforfarshire\b"),
    ("Argyll", r"\bargyll\b"), ("Ayrshire", r"\bayrshire\b"),
    ("Berwickshire", r"\bberwickshire\b"), ("Bute", r"\bbuteshire\b|\bbute\b"),
    ("Clackmannanshire", r"\bclackmannanshire\b"), ("Dumfriesshire", r"\bdumfriesshire\b"),
    ("Dunbartonshire", r"\bdunbartonshire\b"),
    ("East Lothian", r"\beast lothian\b|\bhaddingtonshire\b"), ("Fife", r"\bfife\b"),
    ("Inverness-shire", r"\binverness-?shire\b"), ("Lanarkshire", r"\blanark(?:shire)?\b"),
    ("Midlothian", r"\bmidlothian\b|\bedinburghshire\b"), ("Peeblesshire", r"\bpeeblesshire\b"),
    ("Perthshire", r"\bperthshire\b"), ("Renfrewshire", r"\brenfrewshire\b"),
    ("Roxburghshire", r"\broxburghshire\b"), ("Scottish Borders", r"\bscottish borders\b"),
    ("Stirlingshire", r"\bstirlingshire\b"),
    ("West Lothian", r"\bwest lothian\b|\blinlithgowshire\b"),
    ("Wigtownshire", r"\bwigtownshire\b"),
)


def _ids(value: str) -> list[str]:
    return list(dict.fromkeys(WIKITREE_ID.findall(value or "")))


def _slug(value: str) -> str:
    value = value.casefold().replace("’", "'")
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return value or "other"


def _meaningful_suffixes(values: list[str]) -> list[str]:
    return [
        value for value in values
        if value.casefold().strip().rstrip(".") not in IGNORED_GENERATIONAL_SUFFIXES
    ]


def _individual_key(record: dict) -> str:
    profile_ids = _ids(record.get("profile_id", ""))
    if profile_ids:
        return "|".join(profile_ids)
    return record.get("supplement_id") or f"{record.get('person', '')}|{record.get('family_group', '')}"


def _person_slug(key: str, rows: list[dict]) -> str:
    profile_ids = _ids(rows[0].get("profile_id", ""))
    if len(profile_ids) == 1:
        return _slug(profile_ids[0])
    if profile_ids:
        return _slug("--".join(profile_ids))
    supplement = rows[0].get("supplement_id")
    if supplement:
        return f"record-{_slug(supplement)}"
    return f"record-{_slug(rows[0].get('person', 'person'))}-{sha1(key.encode()).hexdigest()[:10]}"


def _format_date(value: str, status: str = "") -> str:
    match = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", value or "")
    if not match or match.group(1) == "0000":
        return ""
    text = match.group(1)
    if match.group(2) != "00":
        text += "-" + match.group(2)
    if match.group(3) != "00":
        text += "-" + match.group(3)
    prefix = {"before": "before ", "after": "after ", "guess": "c. "}.get(status, "")
    return prefix + text


def _format_profile_timestamp(value: str) -> str:
    match = re.match(r"^(\d{4})(\d{2})(\d{2})", value or "")
    return f"{match.group(1)}-{match.group(2)}-{match.group(3)}" if match else value


def _unique(values) -> list:
    return list(dict.fromkeys(value for value in values if value not in (None, "")))


def _location_area(record: dict, location_index: dict[str, list[str]]) -> str:
    """Match the map table's county/area grouping for a mapped record."""
    region = record.get("region") or "Region not specified"
    location_id = record.get("location_id") or ""
    if region == "Ireland":
        counties = [value for value in location_index.get(location_id, []) if re.match(r"^County\s+", value, re.I)]
        county = next((value for value in counties if value.casefold() != "county derry"), counties[0] if counties else "")
        return "County Londonderry" if county.casefold() == "county derry" else county or "County not specified"
    if region == "Scotland":
        if location_id in SCOTTISH_AREA_BY_LOCATION:
            return SCOTTISH_AREA_BY_LOCATION[location_id]
        text = f"{record.get('record_location', '')} {record.get('location_basis', '')}"
        return next((label for label, pattern in SCOTTISH_AREA_PATTERNS if re.search(pattern, text, re.I)), "Area not specified")
    location = record.get("record_location") or ""
    if re.search(r"location not supplied|exact locality unresolved", location, re.I):
        return "Area not specified"
    ignored = {
        "ireland", "northern ireland", "scotland", "england", "wales", "united kingdom", "uk",
        "great britain", "united states", "united states of america", "usa", "canada", "australia",
        "new zealand", "india", "france", "south africa", "portugal", region.casefold(),
    }
    candidates = [part.strip() for part in location.split(",") if part.strip().casefold() not in ignored]
    return candidates[-1] if candidates else "Area not specified"


def _person_location_groups(person: dict, location_index: dict[str, list[str]]) -> list[dict]:
    groups = []
    seen = set()
    for record in person["records"]:
        country = record.get("region") or "Region not specified"
        area = _location_area(record, location_index)
        locality = record.get("record_location") or "Location not specified"
        key = (country, area, locality, record.get("location_id") or "")
        if key in seen:
            continue
        seen.add(key)
        groups.append({"id": key[3], "country": country, "area": area, "locality": locality})
    return sorted(groups, key=lambda item: (item["country"], item["area"], item["locality"]))


def _family_memberships(
    people: list[dict], root_links: dict[str, list[list[object]]], profiles: dict[str, dict],
    descendant_counts: dict[str, int], id_to_slug: dict[str, str],
) -> dict[str, dict]:
    """Choose a shared earliest-ancestor branch while retaining every exported root lead."""
    memberships = {}
    people_by_profile = {
        profile_id: person
        for person in people
        for profile_id in person["profile_ids"]
    }
    for person in people:
        # A root profile is not evidence of a shared parent chain for that
        # person.  Family grouping starts only once an exported father link
        # connects the subject to an ancestral branch.
        has_exported_father = any(
            parent.get("id") and not parent.get("outside_export")
            for parent in person.get("father", [])
        )
        distances = {}
        for profile_id in person["profile_ids"]:
            for root_id, distance in root_links.get(profile_id, []):
                distances[root_id] = min(int(distance), distances.get(root_id, 10**9))
        roots = []
        for root_id, distance in distances.items():
            metadata = profiles.get(root_id, {})
            root_person = people_by_profile.get(root_id, {})
            roots.append({
                "id": root_id,
                "name": metadata.get("full_name") or root_id,
                "birth": root_person.get("birth") or _format_date(metadata.get("birth_date", ""), metadata.get("birth_status", "")),
                "birth_location": root_person.get("birth_location") or metadata.get("birth_location", ""),
                "distance": distance,
                "known_descendants": int(descendant_counts.get(root_id, 0)),
                "catalogue_id": id_to_slug.get(root_id, ""),
            })
        roots.sort(key=lambda root: (-root["known_descendants"], -root["distance"], root["name"].casefold(), root["id"]))
        memberships[person["catalogue_id"]] = {
            "primary": roots[0] if roots and has_exported_father else None,
            "roots": roots,
        }
    member_counts = Counter(
        membership["primary"]["id"] for membership in memberships.values() if membership["primary"]
    )
    for membership in memberships.values():
        primary = membership["primary"]
        if primary and member_counts[primary["id"]] < 2:
            membership["primary"] = None
        primary_id = membership["primary"]["id"] if membership["primary"] else ""
        for root in membership["roots"]:
            root["catalogued_members"] = member_counts[root["id"]] if primary_id == root["id"] else 0
    return memberships


def _first_given_name(person: dict) -> str:
    values = person.get("first_names") or []
    value = values[0] if values else person.get("name", "")
    match = re.search(r"[A-Za-zÀ-ÖØ-öø-ÿ'’]+", value or "")
    return match.group() if match else "Unknown"


def _broad_place(value: str) -> str:
    patterns = (
        ("Ireland", r"\b(?:ireland|antrim|armagh|cavan|derry|donegal|down|fermanagh|londonderry|monaghan|tyrone)\b"),
        ("Scotland", r"\b(?:scotland|lanarkshire|ayrshire|lothian|fife|perthshire|renfrewshire)\b"),
        ("England", r"\bengland\b"), ("Wales", r"\bwales\b"),
        ("United States", r"\b(?:united states|usa|u\.s\.a\.)\b"),
        ("Canada", r"\bcanada\b"), ("Australia", r"\baustralia\b"),
        ("New Zealand", r"\bnew zealand\b"),
    )
    return next((label for label, pattern in patterns if re.search(pattern, value or "", re.I)), "")


def _stat_bars(title: str, introduction: str, values: list[tuple[str, int, str]], limit: int = 12) -> str:
    values = values[:limit]
    maximum = max((count for _, count, _ in values), default=1)
    rows = "".join(
        f'<li><span class="statistics-label">{link or escape(label)}</span><span class="statistics-bar"><i style="width:{max(3, round(count / maximum * 100))}%"></i></span><strong>{count:,}</strong></li>'
        for label, count, link in values
    )
    return f'<section class="statistics-panel"><h3>{escape(title)}</h3><p>{escape(introduction)}</p><ol class="statistics-bars">{rows}</ol></section>'


_GLASGOW_SURNAME = re.compile(r"^(?:glasgow|glasco|glassco|glascoe|glasgo|glasow|glascow|glasoe|glassgow|glassgo|glasko)$", re.I)
_CUNNINGHAM_VARIANTS = {
    "cunningham", "cuningham", "cunninghame", "cuninghame", "cunyngham",
    "cunynghame", "conyngham", "conynghame",
}
_UNKNOWN_MARRIAGE_SURNAMES = {"unknown", "notknown", "detailswithheld", "withheld", "private", "living"}


def _canonical_marriage_surname(value: str) -> str:
    surname = str(value or "").strip()
    key = re.sub(r"[^a-z]", "", surname.casefold())
    if key in _UNKNOWN_MARRIAGE_SURNAMES:
        return ""
    if _GLASGOW_SURNAME.fullmatch(surname):
        return "Glasgow"
    if key in _CUNNINGHAM_VARIANTS:
        return "Cunningham"
    return surname


def _marriage_surname_key(value: str) -> str:
    """Mirror catalogue_search.js normaliseLiteral for marriage-surname grouping."""
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(char for char in text if not unicodedata.combining(char)).lower()
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def _relation_birth_surnames(relation: dict, people_by_profile: dict[str, dict]) -> set[str]:
    profile_id = str(relation.get("id") or "").strip()
    linked = people_by_profile.get(profile_id.casefold())
    if linked and linked.get("last_names_at_birth"):
        return {_canonical_marriage_surname(name) for name in linked["last_names_at_birth"] if name}
    profile_match = re.match(r"^(.+)-\d+$", profile_id)
    if profile_match:
        return {_canonical_marriage_surname(profile_match.group(1).replace("_", " "))}
    name = str(relation.get("name") or "").strip()
    birth_match = re.search(r"\(([^)]+)\)", name)
    if birth_match:
        return {_canonical_marriage_surname(birth_match.group(1))}
    return {_canonical_marriage_surname(name.split()[-1])} if name else set()


def _marriage_surname_values(people: list[dict], catalogue_href: str = "/catalogue.html") -> list[tuple[str, int, str]]:
    people_by_profile = {
        profile_id.casefold(): person
        for person in people
        for profile_id in person.get("profile_ids", [])
    }
    # Group by the same literal normalisation the catalogue search applies to
    # ?marriageSurname= (case, accents and punctuation folded), so each bar's
    # count equals the number of results its link returns.
    surname_people: dict[str, set[str]] = defaultdict(set)
    spellings: dict[str, Counter] = defaultdict(Counter)
    for person in people:
        if not any(_GLASGOW_SURNAME.fullmatch(name or "") for name in person.get("last_names_at_birth", [])):
            continue
        for spouse in person.get("spouses", []):
            for surname in _relation_birth_surnames(spouse, people_by_profile):
                key = _marriage_surname_key(surname)
                if key:
                    surname_people[key].add(person["catalogue_id"])
                    spellings[key][surname] += 1
    labelled = [
        # Label with the most common spelling; on ties avoid stray capitals ("WIlson", "ROSS").
        (min(spellings[key].items(), key=lambda item: (-item[1], bool(re.search(r"[A-Z]{2}", item[0])), item[0]))[0], members)
        for key, members in surname_people.items()
    ]
    return [
        (surname, len(members), f'<a href="{catalogue_href}?marriageSurname={quote(surname)}#catalogue-results">{escape(surname)}</a>')
        for surname, members in sorted(labelled, key=lambda item: (-len(item[1]), item[0]))
    ]


def _marriage_statistics_panel(people: list[dict], catalogue_href: str = "/catalogue.html") -> str:
    return _stat_bars(
        "Surnames joined by marriage to Glasgow",
        "Glasgow-at-birth people by their spouses' recorded birth surnames, including Glasgow; recognised spelling variants are grouped. Shared surnames do not by themselves prove cousinship.",
        _marriage_surname_values(people, catalogue_href),
        limit=24,
    )


def sync_generated_marriage_statistics() -> None:
    """Refresh only the generated marriage panel without rebuilding person pages."""
    people = json.loads((DATA_DIR / "people.json").read_text(encoding="utf-8"))["people"]
    panel = _marriage_statistics_panel(people, "/catalogue/")
    pattern = re.compile(
        r'<section class="statistics-panel"><h3>(?:Surnames of women who married Glasgow|Surnames joined by marriage to Glasgow)</h3>.*?</section>'
    )
    artifact_path = DATA_DIR / "catalogue-statistics.json"
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    for path in (artifact_path, WEB_DIR / "statistics" / "index.html"):
        html = artifact["html"] if path == artifact_path else path.read_text(encoding="utf-8")
        updated, count = pattern.subn(panel, html, count=1)
        if count != 1:
            raise RuntimeError(f"Marriage statistics panel not found in {path}")
        if path == artifact_path:
            artifact["html"] = updated
            path.write_text(json.dumps(artifact, ensure_ascii=False) + "\n", encoding="utf-8")
        else:
            path.write_text(updated, encoding="utf-8")


def sync_generated_profile_work_status() -> dict[str, int]:
    """Refresh profile-work classifications and their small public mirrors.

    This is deliberately narrower than a catalogue build: it reads the
    maintained profile audit, updates only work-status fields in existing
    public records, and refreshes the affected catalogue copy.
    """
    audit_entries = _load_catalogue_profile_audit().get("entries", {})
    people_path = DATA_DIR / "people.json"
    people_payload = json.loads(people_path.read_text(encoding="utf-8"))
    people = people_payload["people"]
    changed_ids = set()
    for person in people:
        audit = audit_entries.get(person["catalogue_id"], {})
        status = _profile_work_status(person, audit)
        candidate_count = len(audit.get("candidates") or [])
        if (person.get("profile_work_status") != status
                or person.get("profile_work_candidate_count") != candidate_count):
            person["profile_work_status"] = status
            person["profile_work_candidate_count"] = candidate_count
            changed_ids.add(person["catalogue_id"])

    if changed_ids:
        people_path.write_text(
            json.dumps(people_payload, ensure_ascii=False, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
        search_path = DATA_DIR / "catalogue-search-index.json"
        search_rows = json.loads(search_path.read_text(encoding="utf-8"))
        by_id = {person["catalogue_id"]: person for person in people}
        for row in search_rows:
            person = by_id.get(row.get("id"))
            if person is not None:
                row["profile_work_status"] = person["profile_work_status"]
                row["profile_work_candidate_count"] = person["profile_work_candidate_count"]
        search_text = json.dumps(search_rows, ensure_ascii=False, separators=(",", ":")) + "\n"
        search_path.write_text(search_text, encoding="utf-8")
        (DATA_DIR / "people-index.js").write_text(
            "window.glasgowPeopleIndex=" + search_text,
            encoding="utf-8",
        )

    counts = Counter(
        person["profile_work_status"] for person in people if not person.get("profile_ids")
    )
    missing_count = sum(count for status, count in counts.items() if status != "linked_free_space")
    workbench = (
        f"{missing_count:,} documentary identities without confirmed destinations: "
        f"{counts['creation_ready']:,} creation-ready, "
        f"{counts['existing_profile_candidate']:,} possible existing-profile matches on HOLD, "
        f"{counts['identity_hold']:,} identity-insufficient HOLD, "
        f"{counts['free_space_only']:,} pre-1500 subjects missing an individual Space page, and "
        f"{counts['unreviewed']:,} awaiting review"
    )
    caution = (
        f"Profile work is consolidation-first: {missing_count:,} documentary identities lack a confirmed WikiTree destination, comprising "
        f"{counts['creation_ready']:,} creation-ready after duplicate review, "
        f"{counts['existing_profile_candidate']:,} on HOLD with possible existing-profile matches, "
        f"{counts['identity_hold']:,} on HOLD because the records do not yet define a safely distinct person, "
        f"{counts['free_space_only']:,} pre-1500 subjects still lacking an individual Space page, and "
        f"{counts['unreviewed']:,} awaiting identity review. {counts['linked_free_space']:,} pre-1500 subjects are already linked to their canonical individual Space pages and are excluded from that work queue."
    )
    artifact_path = DATA_DIR / "catalogue-statistics.json"
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    public_profile_ids = {profile_id for person in people for profile_id in person.get("profile_ids", [])}
    update_count = len(set(_load_profile_updates(_load_wikitree_evidence())) & public_profile_ids)
    for path in (WEB_DIR / "catalogue.html", WEB_DIR / "catalogue" / "index.html", WEB_DIR / "catalogue" / "advanced.html", artifact_path, WEB_DIR / "statistics" / "index.html"):
        html = artifact["html"] if path == artifact_path else path.read_text(encoding="utf-8")
        updated = re.sub(
            r"\d{1,3}(?:,\d{3})* documentary identities without confirmed destinations: .*? awaiting review",
            workbench,
            html,
        )
        updated = re.sub(
            r"Profile work is consolidation-first: .*?(?= A record fact is not by itself a person to create\.)",
            caution,
            updated,
        )
        updated = re.sub(r"\d[\d,]* profiles ranked by significance",
                         f"{update_count:,} profiles ranked by significance", updated)
        # The summary number immediately precedes its label in generated markup.
        updated = re.sub(
            r"<div><strong>\d{1,3}(?:,\d{3})*</strong><span>Creation-ready profiles</span></div>",
            f'<div><strong>{counts["creation_ready"]:,}</strong><span>Creation-ready profiles</span></div>',
            updated,
        )
        if updated != html:
            if path == artifact_path:
                artifact["html"] = updated
                path.write_text(json.dumps(artifact, ensure_ascii=False) + "\n", encoding="utf-8")
            else:
                path.write_text(updated, encoding="utf-8")
    return {"changed_people": len(changed_ids), "creation_ready": counts["creation_ready"]}


def _catalogue_statistics(
    people: list[dict], family_memberships: dict[str, dict], location_to_slug: dict[str, str],
    place_count: int, record_count: int, profile_work_counts: Counter, original_count: int,
    refreshed: str,
) -> str:
    region_people: dict[str, set[str]] = defaultdict(set)
    locality_people: dict[tuple[str, str], set[str]] = defaultdict(set)
    given_names = Counter()
    centuries = Counter()
    migrations = Counter()
    for person in people:
        given_names[_first_given_name(person)] += 1
        birth_year = next((int(match.group()) for match in [re.search(r"\b(?:1[0-9]|20)\d{2}\b", person.get("birth", ""))] if match), None)
        if birth_year:
            centuries[f"{birth_year // 100 + 1}{'th' if birth_year // 100 + 1 not in (21,) else 'st'} century"] += 1
        birth_region, death_region = _broad_place(person.get("birth_location", "")), _broad_place(person.get("death_location", ""))
        if birth_region and death_region and birth_region != death_region:
            migrations[f"{birth_region} → {death_region}"] += 1
        seen_locations = set()
        for record in person["records"]:
            region = record.get("region") or "Unspecified"
            region_people[region].add(person["catalogue_id"])
            location = record.get("record_location") or "Location not specified"
            key = (record.get("location_id") or location, location)
            if key not in seen_locations:
                locality_people[key].add(person["catalogue_id"])
                seen_locations.add(key)
    family_counts = Counter(
        membership["primary"]["id"] for membership in family_memberships.values() if membership["primary"]
    )
    family_roots = {
        membership["primary"]["id"]: membership["primary"]
        for membership in family_memberships.values() if membership["primary"]
    }
    linked_people = sum(1 for membership in family_memberships.values() if membership["primary"])
    cross_region = sum(migrations.values())
    creation_ready_count = profile_work_counts["creation_ready"]
    candidate_hold_count = profile_work_counts["existing_profile_candidate"]
    identity_hold_count = profile_work_counts["identity_hold"]
    free_space_only_count = profile_work_counts["free_space_only"]
    linked_free_space_count = profile_work_counts["linked_free_space"]
    unreviewed_count = profile_work_counts["unreviewed"]
    missing_profile_count = sum(
        count for status, count in profile_work_counts.items()
        if status != "linked_free_space"
    )
    summary = "".join(
        f'<div><strong>{value:,}</strong><span>{escape(label)}</span></div>'
        for label, value in (
            ("Historical people", len(people)), ("Mapped records", record_count), ("Mapped places", place_count),
            ("Exported family roots", len(family_counts)), ("People linked to a root", linked_people),
            ("Cross-region life courses", cross_region), ("Creation-ready profiles", creation_ready_count),
            ("Linked pre-1500 Space pages", linked_free_space_count),
            ("People with original evidence", original_count),
        )
    )
    region_values = sorted(
        ((region, len(members), f'<a href="/people/locations/{_slug(region)}.html">{escape(region)}</a>') for region, members in region_people.items()),
        key=lambda item: (-item[1], item[0]),
    )
    name_values = [
        (name, count, f'<a href="/catalogue.html?first={quote(name)}">{escape(name)}</a>')
        for name, count in given_names.most_common()
    ]
    locality_values = []
    for (location_id, label), members in locality_people.items():
        slug = location_to_slug.get(location_id)
        link = f'<a href="/places/{slug}.html">{escape(label)}</a>' if slug else escape(label)
        locality_values.append((label, len(members), link))
    locality_values.sort(key=lambda item: (-item[1], item[0]))
    family_values = []
    for root_id, count in family_counts.most_common():
        root = family_roots[root_id]
        link = f'<a href="/people/{root["catalogue_id"]}.html">{escape(root["name"])}</a>' if root["catalogue_id"] else escape(root["name"])
        family_values.append((root["name"], count, f'{link}<small>{escape(root_id)}</small>'))
    century_values = sorted(((label, count, "") for label, count in centuries.items()), key=lambda item: item[0])
    migration_values = [(label, count, "") for label, count in migrations.most_common()]
    panels = "".join((
        _stat_bars("People by region", "A person is counted once in every mapped region where a record places them.", region_values),
        _stat_bars("Most frequent given names", "First recorded given name across the public historical catalogue.", name_values),
        _marriage_statistics_panel(people),
        _stat_bars("Largest exported family branches", "Primary earliest-ancestor groups from exported WikiTree parent links.", family_values),
        _stat_bars("Most frequent mapped places", "Unique catalogued people associated with each townland or locality.", locality_values),
        _stat_bars("Birth centuries", "People with a usable birth year; estimates remain estimates.", century_values, 20),
        _stat_bars("Most common recorded migrations", "Different broad birth and death regions on the same profile.", migration_values),
    ))
    return f'''<section id="statistics" class="catalogue-statistics"><div class="catalogue-statistics-heading"><div><p class="kicker">Project overview</p><h2>Catalogue statistics</h2><p>Patterns across public historical people only; likely-living profiles remain withheld.</p><p class="catalogue-refresh">Updated {escape(refreshed)}</p></div></div><div class="statistics-summary">{summary}</div><details id="statistics-detail"><summary><span><strong>Open detailed statistics pane</strong><small>Names, spouse surnames, places, family branches and migration patterns</small></span><span class="statistics-open-label"><span class="statistics-closed-copy">View statistics</span><span class="statistics-open-copy">Hide statistics</span></span></summary><div class="statistics-grid">{panels}</div><p class="statistics-caution">Profile work is consolidation-first: {missing_profile_count:,} documentary identities lack a confirmed WikiTree destination, comprising {creation_ready_count:,} creation-ready after duplicate review, {candidate_hold_count:,} on HOLD with possible existing-profile matches, {identity_hold_count:,} on HOLD because the records do not yet define a safely distinct person, {free_space_only_count:,} pre-1500 subjects still lacking an individual Space page, and {unreviewed_count:,} awaiting identity review. {linked_free_space_count:,} pre-1500 subjects are already linked to their canonical individual Space pages and are excluded from that work queue. A record fact is not by itself a person to create. Family branches follow exported WikiTree parent links and organise research; they do not independently prove descent. Location totals count mapped associations, so one person may appear in several places or regions.</p></details></section>'''


def _catalogue_record_types(person: dict) -> list[str]:
    """Return a small public-facing record vocabulary for catalogue filters."""
    patterns = (
        ("Births and baptisms", r"\b(?:birth|born|bapti[sz]|christen)"),
        ("Marriages", r"\b(?:marriage|married|wedding|spouse|groom|bride)"),
        ("Deaths and burials", r"\b(?:death|died|burial|buried|grave|cemetery)"),
        ("Census and households", r"\b(?:census|household|householder)"),
        ("Wills and probate", r"\b(?:will|probate|testament|administration|executor)\b"),
        ("Land and valuation", r"\b(?:lease|rent|tenant|tithe|valuation|griffith|deed|land)"),
        ("Church records", r"\b(?:church|parish|presbyterian|session|communicant)"),
        ("Military records", r"\b(?:military|army|navy|soldier|officer|service record)"),
        ("Directories and occupations", r"\b(?:directory|occupation|trade|merchant|farmer|weaver)"),
        ("Tax and civil lists", r"\b(?:tax|hearth|freeholder|poll|voter|return)"),
    )
    text = " ".join(
        f"{record.get('association', '')} {record.get('note', '')} {record.get('source_title', '')}"
        for record in person.get("records", [])
    )
    return [label for label, pattern in patterns if re.search(pattern, text, re.I)]


def _evidence_badge(value: str, label: str | None = None) -> str:
    status = re.sub(r"[^a-z0-9]+", "-", (value or "unknown").casefold()).strip("-") or "unknown"
    if label is None:
        key = str(value or "unknown")
        if key in evidence_labels.RECORD_QUALITY:
            label = evidence_labels.quality_label(key)
        elif key.casefold().replace(" ", "_") in evidence_labels.STATES or key.casefold() in evidence_labels.ALIASES:
            label = evidence_labels.label(key)
    return f'<span class="evidence-badge evidence-{escape(status, quote=True)}">{escape(label or value or "Unclassified")}</span>'


def _catalogue_legend_html() -> str:
    """The catalogue legend, taken from the shared evidence vocabulary."""
    states = ("proved", "strongly_supported", "probable", "possible", "unmarked")
    terms = [(evidence_labels.label(key), evidence_labels.meaning(key)) for key in states]
    terms += [(term, evidence_labels.RECORD_EVIDENCE[term]) for term in ("Profile lead", "Estimated")]
    cells = "".join(f'<p><strong>{escape(term)}</strong><span>{escape(text)}</span></p>' for term, text in terms)
    return (
        f'<section class="catalogue-legend"><h2>{escape(evidence_labels.GUIDE_LABEL)}</h2><div class="legend-grid">{cells}</div>'
        f'<p class="legend-warning">{escape(evidence_labels.CLUSTER_NOTE)}</p>'
        f'<p class="legend-guide"><a href="{evidence_labels.GUIDE_URL}">Read the full evidence guide</a></p></section>'
    )


FINDINGS_TEMPLATE_MARKER = re.compile(r"no sourced conclusion recorded yet|_add a url, archive reference", re.I)

# Sections kept in findings.md for the editor, not the reader: WikiTree editing
# logs, hand-off text and site-maintenance notes. They are deliberately not
# published. Add a pattern here when a new kind of internal section appears.
FINDINGS_INTERNAL_HEADINGS = (
    r"\bwikitree\b",
    r"\bhand-?off\b",
    r"\blive\b",
    r"\bpaste[- ]ready\b",
    r"\bscrape\b",
    r"error 966",
    r"website synchroni[sz]ation",
    r"familysearch cleanup",
    r"^prior assessment",
    r"^superseded\b",
    r"^assessment history",
    r"^provisional wording",
)
_FINDINGS_RECORD_WORDS = (
    r"original|manuscript|newspaper|testament|deed|register|record|index|census|probate|will|transcription"
)


def findings_section_category(title: str) -> str:
    """Classify one ``## `` heading of a findings.md file.

    Returns ``conclusion``, ``sources``, ``assessment`` or ``actions`` for a
    heading a rule recognises, ``internal`` for a section that is deliberately
    kept out of the site, and ``notes`` for everything else. Nothing is
    dropped because of an unexpected heading: a section is published unless
    its heading says it is an editing log. ``tools/check_research_publication.py``
    lists the sections published as general notes so they can be given a
    clearer heading.
    """
    lowered = re.sub(r"\s+", " ", title or "").strip().casefold()
    if lowered in {"current conclusion", "conclusion", "current answer"} or lowered.startswith("current conclusion"):
        return "conclusion"
    if lowered == "source findings":
        return "sources"
    if re.search(r"candidate|relationship|identity|duplicate|parentage|father|cluster placement", lowered):
        return "assessment"
    if re.search(r"unresolved|priorit|recommend|suggested|correction|do not add|next records", lowered):
        return "actions"
    if lowered.startswith("source findings") or lowered == "sources":
        return "sources"
    if re.search(r"next (question|proof|step|search)|proof targets?|remaining (work|bridge|question)|open questions?|do not infer", lowered):
        return "actions"
    if any(re.search(pattern, lowered) for pattern in FINDINGS_INTERNAL_HEADINGS):
        return "internal"
    if re.search(r"negative search|\bevidence\b", lowered):
        return "sources"
    if re.search(rf"\b({_FINDINGS_RECORD_WORDS})s?\b.*\b(review|re-?read|reading|audit|pass|search|check)\b", lowered):
        return "sources"
    if re.search(r"placement|family link|\bassessment\b", lowered):
        return "assessment"
    return "notes"


_TABLE_RULE = re.compile(r"\s*\|?[\s:|-]+\|?\s*")


def _findings_section_body(body: str) -> str:
    """Drop unfilled template lines; return what a reader should see, or ''.

    The findings template ships a placeholder table row. Only that row is
    removed. Real rows and paragraphs in the same section are kept, and a
    table header left with no rows is removed with it.
    """
    if not FINDINGS_TEMPLATE_MARKER.search(body):
        return body
    lines = [line for line in body.splitlines() if not FINDINGS_TEMPLATE_MARKER.search(line)]
    kept, index = [], 0
    while index < len(lines):
        line = lines[index]
        following = lines[index + 1] if index + 1 < len(lines) else ""
        after = lines[index + 2] if index + 2 < len(lines) else ""
        if (line.lstrip().startswith("|") and "-" in following and _TABLE_RULE.fullmatch(following)
                and not after.lstrip().startswith("|")):
            index += 2
            continue
        kept.append(line)
        index += 1
    text = "\n".join(kept).strip()
    if not re.sub(r"<!--.*?-->", "", text, flags=re.S).strip():
        return ""
    return text


def _load_research_findings(profile_ids: list[str]) -> list[dict]:
    """Load substantive, public-safe sections from durable case findings."""
    manifest = PROJECT_ROOT / "data/wikitree/research-catalogue-cases.json"
    if manifest.exists():
        aliases = json.loads(manifest.read_text()).get("cases", {})
        profile_ids = list(dict.fromkeys([*profile_ids, *(
            key for key, entry in aliases.items()
            if entry.get("status") == "include_record" and entry.get("profile_id") in profile_ids
        )]))
    findings = []
    for profile_id in profile_ids:
        if manifest.exists() and aliases.get(profile_id, {}).get("status") == "covered":
            continue
        path = RESEARCH_DIR / profile_id / "findings.md"
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        updated = (re.search(r"^Last updated:\s*(.+)$", text, re.M) or [None, ""])[1].strip()
        sections = []
        for block in re.split(r"^##\s+", text, flags=re.M)[1:]:
            title, _, body = block.partition("\n")
            title, body = title.strip(), body.strip()
            category = findings_section_category(title)
            if category == "internal":
                continue
            body = _findings_section_body(body)
            if not body:
                continue
            sections.append({"title": title, "category": category, "markdown": body})
        if sections:
            findings.append({
                "profile_id": profile_id, "updated": updated or None,
                "source_path": f"research/{profile_id}/findings.md", "sections": sections,
            })
    return findings


def _inline_findings(text: str, id_to_slug: dict[str, str]) -> str:
    """Render a small, safe inline Markdown subset and interlink WikiTree IDs."""
    token = re.compile(r"\[([^]]+)]\(([^)]+)\)|`([^`]+)`|\*\*([^*]+)\*\*")

    def plain(value: str) -> str:
        escaped = escape(value)
        return re.sub(
            r"\b([A-Za-z][A-Za-z_'’-]*-\d+)\b",
            lambda match: (
                f'<a href="/people/{id_to_slug[match.group(1)]}.html">{match.group(1)}</a>'
                if match.group(1) in id_to_slug else match.group(1)
            ),
            escaped,
        )

    rendered, cursor = [], 0
    for match in token.finditer(text):
        rendered.append(plain(text[cursor:match.start()]))
        label, url, code, bold = match.groups()
        if label is not None:
            linked_id = ""
            if re.match(r"^https?://(?:www\.)?wikitree\.com/wiki/", url, re.I):
                linked_id = next(iter(_ids(url.rsplit("/", 1)[-1])), "")
            if linked_id:
                href = f'/people/{id_to_slug[linked_id]}.html' if linked_id in id_to_slug else WIKITREE_URL + quote(linked_id)
                rendered.append(f'<a href="{escape(href, quote=True)}">{plain(label)}</a>')
            elif url.startswith(("https://", "http://")):
                rendered.append(f'<a href="{escape(url, quote=True)}">{plain(label)}</a>')
            else:
                rendered.append(f'<span class="local-artifact" title="Local research artifact; not published">{plain(label)}</span>')
        elif code is not None:
            rendered.append(
                f'<code><a href="/people/{id_to_slug[code]}.html">{escape(code)}</a></code>'
                if code in id_to_slug else f"<code>{escape(code)}</code>"
            )
        else:
            rendered.append(f"<strong>{plain(bold)}</strong>")
        cursor = match.end()
    rendered.append(plain(text[cursor:]))
    return "".join(rendered)


def _render_findings_markdown(markdown: str, id_to_slug: dict[str, str]) -> str:
    """Render paragraphs, lists, tables, quotations and code from findings.md."""
    lines, output, index = markdown.splitlines(), [], 0
    special = re.compile(r"^(?:\s*$|```|###\s+|>\s?|[-*+]\s+|\d+[.)]\s+|\|)")
    while index < len(lines):
        line = lines[index]
        if not line.strip():
            index += 1
            continue
        if line.startswith("```"):
            language = line[3:].strip()
            index += 1
            code_lines = []
            while index < len(lines) and not lines[index].startswith("```"):
                code_lines.append(lines[index]); index += 1
            index += index < len(lines)
            output.append(f'<pre class="finding-code" data-language="{escape(language, quote=True)}">{escape(chr(10).join(code_lines))}</pre>')
            continue
        if line.startswith("|") and index + 1 < len(lines) and re.match(r"^\|?\s*:?-+", lines[index + 1]):
            table_lines = [line]
            index += 2
            while index < len(lines) and lines[index].startswith("|"):
                table_lines.append(lines[index]); index += 1
            rows = [[cell.strip() for cell in row.strip().strip("|").split("|")] for row in table_lines]
            head = "".join(f"<th>{_inline_findings(cell, id_to_slug)}</th>" for cell in rows[0])
            body = "".join("<tr>" + "".join(f"<td>{_inline_findings(cell, id_to_slug)}</td>" for cell in row) + "</tr>" for row in rows[1:])
            output.append(f'<div class="table-wrap finding-table"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>')
            continue
        if re.match(r"^[-*+]\s+", line):
            items = []
            while index < len(lines) and re.match(r"^[-*+]\s+", lines[index]):
                items.append(re.sub(r"^[-*+]\s+", "", lines[index])); index += 1
            output.append("<ul>" + "".join(f"<li>{_inline_findings(item, id_to_slug)}</li>" for item in items) + "</ul>")
            continue
        if re.match(r"^\d+[.)]\s+", line):
            items = []
            while index < len(lines) and re.match(r"^\d+[.)]\s+", lines[index]):
                items.append(re.sub(r"^\d+[.)]\s+", "", lines[index])); index += 1
            output.append("<ol>" + "".join(f"<li>{_inline_findings(item, id_to_slug)}</li>" for item in items) + "</ol>")
            continue
        if line.startswith(">"):
            quotes = []
            while index < len(lines) and lines[index].startswith(">"):
                quotes.append(re.sub(r"^>\s?", "", lines[index])); index += 1
            output.append(f'<blockquote>{_inline_findings(" ".join(quotes), id_to_slug)}</blockquote>')
            continue
        if line.startswith("### "):
            output.append(f"<h4>{_inline_findings(line[4:].strip(), id_to_slug)}</h4>"); index += 1
            continue
        paragraph = [line.strip()]
        index += 1
        while index < len(lines) and not special.match(lines[index]):
            paragraph.append(lines[index].strip()); index += 1
        output.append(f'<p>{_inline_findings(" ".join(paragraph), id_to_slug)}</p>')
    return "".join(output)


def _canonical_comparison_name(value: str) -> str:
    tokens = re.findall(r"[a-z]+", value.casefold())
    tokens = [token for token in tokens if token not in {"jr", "sr", "md", "ma", "rev", "reverend"}]
    if tokens and tokens[-1] in GLASGOW_SURNAME_VARIANTS:
        tokens[-1] = "glasgow"
    return " ".join((tokens[0], tokens[-1])) if len(tokens) >= 2 else " ".join(tokens)


def _relative_name_key(value: str) -> str:
    """Normalise a relative's displayed name while retaining given and birth surnames."""
    text = str(value or "").casefold()
    birth_surname = re.search(r"\(([^)]+)\)", text)
    tokens = [token for token in re.findall(r"[a-z]+", text) if token not in {"rev", "reverend", "dr"}]
    if not tokens:
        return ""
    if birth_surname:
        given = [token for token in re.findall(r"[a-z]+", text.split("(", 1)[0]) if token not in {"rev", "reverend", "dr"}]
        surname_tokens = re.findall(r"[a-z]+", birth_surname.group(1))
        surname = surname_tokens[-1] if surname_tokens else ""
    else:
        given, surname = (tokens[:-1], tokens[-1]) if len(tokens) > 1 else (tokens, "")
    return " ".join([*given, surname]).strip()


def _relative_given_name(value: str) -> str:
    unknown = {"baby", "child", "infant", "unnamed", "unknown"}
    descriptors = {
        "older", "younger", "probably", "possible",
        "rev", "reverend", "dr", "doctor", "sir",
        "col", "colonel", "capt", "captain", "major", "lt", "lieutenant",
    }
    tokens = re.findall(r"[a-z]+", str(value or "").casefold())
    if not tokens or tokens[0] in unknown:
        return ""
    given = next((token for token in tokens if token not in descriptors), "")
    # Treat clear historical spelling and familiar-name variants as the same
    # naming clue. Keep this deliberately narrow: an alias match is useful for
    # ranking family leads, but must not collapse distinct profiles.
    return {
        "bessie": "elizabeth",
        "elisabeth": "elizabeth",
        "elizabethe": "elizabeth",
    }.get(given, given)


def _relative_given_names(values: list[str]) -> dict[str, str]:
    result = {}
    for value in values:
        given_name = _relative_given_name(value)
        if given_name:
            result.setdefault(given_name, str(value))
    return result


def _comparison_parent_links(person: dict) -> list[dict]:
    """Return role-aware parent links, including relationship certainty when available."""
    if person.get("_parent_links"):
        return person["_parent_links"]
    links = []
    names = list(person.get("parent_names", []))
    for position, parent_id in enumerate(person.get("parent_ids", [])):
        role = "father" if parent_id == person.get("father_id") else "mother" if parent_id == person.get("mother_id") else "parent"
        links.append({
            "id": parent_id, "name": names[position] if position < len(names) else parent_id,
            "relationship": role, "status": "unknown", "tree_status": "unmarked",
        })
    if not links:
        links.extend({
            "id": None, "name": name, "relationship": "parent",
            "status": "unknown", "tree_status": "unmarked",
        } for name in names)
    return links


def _parent_certainty(link: dict) -> tuple[int, str]:
    """Rank audited assessments above WikiTree's own relationship-status marker."""
    status = link.get("status") or "unknown"
    if status == "proved":
        return 5, link.get("status_label") or "documented parent"
    if status == "strongly_supported":
        return 4, link.get("status_label") or "strongly supported parent"
    if status == "probable":
        return 3, link.get("status_label") or "probable parent"
    if status in {"possible", "disputed"}:
        return 1, link.get("status_label") or "uncertain parent"
    if status == "contradicted":
        return -1, link.get("status_label") or "contradicted parent"
    tree_status = link.get("tree_status") or "unmarked"
    return {
        "dna_confirmed": (4, link.get("tree_status_label") or "WikiTree: confirmed with DNA"),
        "confident": (2, link.get("tree_status_label") or "WikiTree: confident parent"),
        "uncertain": (0, link.get("tree_status_label") or "WikiTree: uncertain parent"),
        "non_biological": (0, link.get("tree_status_label") or "WikiTree: non-biological parent"),
    }.get(tree_status, (1, link.get("tree_status_label") or "WikiTree parent; status unmarked"))


def _date_is_exact(person: dict, kind: str) -> bool:
    return person.get(f"{kind}_status") == "exact"


def _similar_people(index: list[dict]) -> dict[str, list[dict]]:
    """Create explainable same-name comparisons; never assert that two profiles are identical."""
    buckets = defaultdict(list)
    for person in index:
        buckets[_canonical_comparison_name(person["name"])].append(person)
    results = {}
    names_by_id = {person["id"]: person["name"] for person in index}
    ignored_places = {
        "county", "ireland", "scotland", "england", "united", "kingdom", "states", "townland", "parish",
        # Map precision/evidence labels are not geography and must never create
        # a false locality match between otherwise different places.
        "exact", "locality", "unproved", "probable", "estimated", "reference", "location", "unknown",
    }
    normal = lambda value: re.sub(r"[^a-z0-9]+", " ", str(value or "").casefold()).strip()

    def compare_parents(person: dict, other: dict) -> tuple[int, list[str], list[str], bool, str]:
        left, right = _comparison_parent_links(person), _comparison_parent_links(other)
        reasons, conflicts, score, hard_conflict = [], [], 0, False
        shared_pairs = [
            (a, b) for a in left for b in right
            if a.get("id") and a.get("id") == b.get("id")
        ]
        if shared_pairs:
            a, b = max(shared_pairs, key=lambda pair: min(_parent_certainty(pair[0])[0], _parent_certainty(pair[1])[0]))
            certainty = min(_parent_certainty(a)[0], _parent_certainty(b)[0])
            role = a.get("relationship") if a.get("relationship") == b.get("relationship") else "parent"
            if certainty >= 4:
                points, description = 28, f"same independently supported {role} profile"
            elif certainty >= 2:
                points, description = 16, f"same marked-confident {role} profile"
            elif certainty <= 0:
                points, description = 4, f"same {role} profile, but at least one relationship is uncertain"
            else:
                points, description = 9, f"same {role} profile; relationship evidence is unassessed"
            score += points
            reasons.append(f"{description}: {a.get('name') or a.get('id')} (+{points})")
            summary = description.title()
        else:
            left_names = {normal(link.get("name")): link for link in left if normal(link.get("name"))}
            right_names = {normal(link.get("name")): link for link in right if normal(link.get("name"))}
            shared_names = set(left_names) & set(right_names)
            if shared_names:
                name = sorted(shared_names)[0]
                certainty = min(_parent_certainty(left_names[name])[0], _parent_certainty(right_names[name])[0])
                points = 7 if certainty >= 2 else 2
                score += points
                reasons.append(f"same parent name without a shared profile ID: {left_names[name].get('name')} (+{points})")
                summary = "Same parent name; profile identity unproved"
            else:
                summary = "No shared parent is indexed"

        # Different parents only conflict when they occupy the same role. An
        # uncertain or non-biological attachment must not veto a good match.
        for role in ("father", "mother"):
            left_role = [link for link in left if link.get("relationship") == role and link.get("id") and link.get("tree_status") != "non_biological"]
            right_role = [link for link in right if link.get("relationship") == role and link.get("id") and link.get("tree_status") != "non_biological"]
            if not left_role or not right_role or {link["id"] for link in left_role} & {link["id"] for link in right_role}:
                continue
            left_best = max(left_role, key=lambda link: _parent_certainty(link)[0])
            right_best = max(right_role, key=lambda link: _parent_certainty(link)[0])
            certainty = min(_parent_certainty(left_best)[0], _parent_certainty(right_best)[0])
            if certainty >= 4:
                score -= 35; hard_conflict = True
                conflicts.append(f"independently supported {role}s are different (−35)")
                summary = f"Conflicting supported {role}s"
            elif certainty >= 2:
                score -= 18; hard_conflict = True
                conflicts.append(f"marked-confident {role}s are different (−18)")
                summary = f"Different marked-confident {role}s"
            elif certainty > 0:
                score -= 5
                conflicts.append(f"unassessed {role} attachments differ (−5)")
            else:
                conflicts.append(f"uncertain {role} attachments differ (no deduction)")
        return score, reasons, conflicts, hard_conflict, summary

    for person in index:
        direct_relatives = set(person.get("parent_ids", [])) | set(person.get("spouse_ids", [])) | set(person.get("child_ids", []))
        person_places = {normal(value) for value in person.get("locations", []) if value}
        person_tokens = {token for value in person_places for token in value.split() if len(token) > 3 and token not in ignored_places}
        candidates = []
        for other in buckets[_canonical_comparison_name(person["name"])]:
            if other["id"] == person["id"] or other["id"] in direct_relatives:
                continue
            birth_a, birth_b = person.get("birth_year"), other.get("birth_year")
            birth_delta = None
            broad_birth_estimate = "estimated" in {person.get("birth_status"), other.get("birth_status")}
            if birth_a is not None and birth_b is not None:
                birth_delta = abs(birth_a - birth_b)
                maximum_delta = 20 if _date_is_exact(person, "birth") and _date_is_exact(other, "birth") else 100 if broad_birth_estimate else 40
                if birth_delta > maximum_delta:
                    continue
            death_a, death_b = person.get("death_year"), other.get("death_year")
            death_delta = None
            if death_a is not None and birth_b is not None and death_a + 5 < birth_b:
                continue
            if death_b is not None and birth_a is not None and death_b + 5 < birth_a:
                continue
            if death_a is not None and death_b is not None:
                death_delta = abs(death_a - death_b)
                maximum_death_delta = 30 if _date_is_exact(person, "death") and _date_is_exact(other, "death") else 60
                if death_delta > maximum_death_delta:
                    continue

            score, reasons, conflicts = 18, ["same first and last name (+18)"], []
            strong_signals = 0
            if birth_delta is not None:
                if birth_delta == 0: score += 30; strong_signals += 1; reasons.append("same birth year (+30)")
                elif birth_delta <= 2: score += 25; strong_signals += 1; reasons.append(f"birth years within {birth_delta} (+25)")
                elif birth_delta <= 5: score += 18; strong_signals += 1; reasons.append(f"birth years within {birth_delta} (+18)")
                elif birth_delta <= 10: score += 10; reasons.append(f"birth years within {birth_delta} (+10)")
                elif birth_delta <= 20: score += 2; reasons.append(f"birth years within {birth_delta} (+2)")
                elif broad_birth_estimate:
                    conflicts.append(f"record-derived birth estimates differ by {birth_delta}; retained without deduction")
                else: score -= 22; conflicts.append(f"birth years differ by {birth_delta} (−22)")
            else:
                conflicts.append("one birth year is unavailable")
            if death_delta is not None:
                if death_delta == 0: score += 15; strong_signals += 1; reasons.append("same death year (+15)")
                elif death_delta <= 2: score += 10; strong_signals += 1; reasons.append(f"death years within {death_delta} (+10)")
                elif death_delta <= 5: score += 5; reasons.append(f"death years within {death_delta} (+5)")
                elif death_delta > 20: score -= 18; conflicts.append(f"death years differ by {death_delta} (−18)")
            other_places = {normal(value) for value in other.get("locations", []) if value}
            shared_places = person_places & other_places
            other_tokens = {token for value in other_places for token in value.split() if len(token) > 3 and token not in ignored_places}
            locality_match = bool(shared_places or person_tokens & other_tokens)
            if shared_places:
                score += 20; strong_signals += 1; reasons.append("shared recorded place (+20)")
            elif person_tokens & other_tokens:
                score += 8; reasons.append("overlapping locality (+8)")
            spouse_ids = set(person.get("spouse_ids", [])) & set(other.get("spouse_ids", []))
            spouse_names = {normal(value) for value in person.get("spouse_names", [])} & {normal(value) for value in other.get("spouse_names", [])}
            spouse_match = bool(spouse_ids or spouse_names - {""})
            if spouse_ids:
                score += 30; strong_signals += 1; reasons.append("same spouse profile (+30)")
            elif spouse_names - {""}:
                score += 20; strong_signals += 1; reasons.append("same spouse name (+20)")

            parent_points, parent_reasons, parent_conflicts, hard_parent_conflict, parent_summary = compare_parents(person, other)
            score += parent_points; reasons.extend(parent_reasons); conflicts.extend(parent_conflicts)
            parent_match = bool(parent_reasons)
            if parent_match and parent_points >= 16:
                strong_signals += 1
            shared_child_ids = set(person.get("child_ids", [])) & set(other.get("child_ids", []))
            matching_children = sorted(names_by_id.get(child_id, child_id) for child_id in shared_child_ids)
            child_match = bool(shared_child_ids)
            child_name_overlap = []
            if shared_child_ids:
                score += 35; strong_signals += 1
                reasons.append(
                    ("same child profile: " if len(shared_child_ids) == 1 else f"{len(shared_child_ids)} same child profiles: ")
                    + ", ".join(matching_children[:5]) + " (+35)"
                )
            else:
                person_child_names = {
                    _relative_name_key(value): value for value in person.get("child_names", []) if _relative_name_key(value)
                }
                other_child_names = {
                    _relative_name_key(value): value for value in other.get("child_names", []) if _relative_name_key(value)
                }
                shared_child_names = set(person_child_names) & set(other_child_names)
                matching_children = sorted(person_child_names[key] for key in shared_child_names)
                if shared_child_names:
                    score += min(28, 8 + 6 * len(shared_child_names))
                    child_match = len(shared_child_names) >= 2
                    if child_match:
                        strong_signals += 1
                    reasons.append(
                        f"matching child name{'s' if len(matching_children) != 1 else ''}: " + ", ".join(matching_children[:5])
                    )
                person_given = _relative_given_names(person.get("child_names", []))
                other_given = _relative_given_names(other.get("child_names", []))
                exact_given = {given_name for name in matching_children if (given_name := _relative_given_name(name))}
                child_name_overlap = sorted((set(person_given) & set(other_given)) - exact_given)
                if child_name_overlap:
                    score += min(10, 2 * len(child_name_overlap))
                    reasons.append(
                        f"child given-name pattern overlaps: {', '.join(name.title() for name in child_name_overlap[:6])}"
                    )
            duplicate_signal = locality_match or spouse_match or parent_match or child_match
            hard_date_conflict = bool(
                (birth_delta is not None and birth_delta > (10 if _date_is_exact(person, "birth") and _date_is_exact(other, "birth") else 100 if broad_birth_estimate else 20))
                or (death_delta is not None and death_delta > (15 if _date_is_exact(person, "death") and _date_is_exact(other, "death") else 30))
            )
            classification = (
                "possible duplicate" if score >= 70 and strong_signals >= 2
                and duplicate_signal and not hard_date_conflict and not hard_parent_conflict
                else "similar person"
            )
            candidates.append({
                "id": other["id"], "name": other["name"], "catalogue_id": other["catalogue_id"],
                "html_url": other["html_url"], "birth_year": birth_b, "death_year": other.get("death_year"),
                "birth_place": other.get("birth_place"), "death_place": other.get("death_place"),
                "score": max(0, min(100, score)), "classification": classification,
                "match_reasons": reasons, "conflicts": conflicts,
                "matching_children": matching_children, "child_name_overlap": child_name_overlap,
                "parent_comparison": parent_summary,
            })
        ranked = sorted(candidates, key=lambda item: (-item["score"], item.get("birth_year") or 9999, item["id"]))
        results[person["id"]] = ranked[:8] if any(item["score"] > 65 for item in ranked) else ranked[:2]
    return results


def _potential_parentage(
    index: list[dict],
    similar_by_id: dict[str, list[dict]] | None = None,
    requested_subject_ids: set[str] | None = None,
) -> dict[str, dict]:
    """Rank multi-factor parent leads; never treat the score as proof."""
    similar_by_id = similar_by_id or {}
    reviewed_score_ids: dict[str, set[str]] = {}
    for candidate_file in RESEARCH_DIR.glob("*/parent_candidates.json"):
        try:
            reviewed = json.loads(candidate_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        ids = {
            str(profile_id)
            for item in reviewed if isinstance(item, dict)
            for profile_id in ([item.get("score_profile_id")] + list(item.get("score_profile_ids") or []))
            if profile_id
        }
        if ids:
            reviewed_score_ids[candidate_file.parent.name] = ids
    ignored_places = {
        "county", "ireland", "scotland", "england", "united", "kingdom", "states", "townland", "parish",
        # Precision and evidence labels are not geography.
        "exact", "locality", "unproved", "probable", "estimated", "reference", "location", "unknown",
    }
    # A shared country, state or historic county is context, not a shared
    # locality. Keep these tokens from making County Antrim look equivalent
    # to the same townland, or Ohio equivalent to the same township.
    broad_place_tokens = {
        "ireland", "scotland", "england", "wales", "canada", "australia", "zealand",
        "antrim", "armagh", "down", "fermanagh", "londonderry", "derry", "tyrone", "donegal",
        "lanarkshire", "ayrshire", "midlothian", "lothian", "linlithgowshire", "renfrewshire",
        "wigtownshire", "edinburghshire", "haddingtonshire", "aberdeenshire", "kincardineshire",
        "alabama", "alaska", "arizona", "arkansas", "california", "colorado", "connecticut",
        "delaware", "florida", "georgia", "hawaii", "idaho", "illinois", "indiana", "iowa",
        "kansas", "kentucky", "louisiana", "maine", "maryland", "massachusetts", "michigan",
        "minnesota", "mississippi", "missouri", "montana", "nebraska", "nevada", "hampshire",
        "jersey", "mexico", "york", "carolina", "dakota", "ohio", "oklahoma", "oregon",
        "pennsylvania", "rhode", "tennessee", "texas", "utah", "vermont", "virginia",
        "washington", "wisconsin", "wyoming",
    }

    def normal_place(value: str) -> str:
        return re.sub(r"[^a-z0-9]+", " ", str(value).casefold()).strip()

    def canonical_birth_surname(token: str) -> str:
        return "glasgow" if token in GLASGOW_SURNAME_VARIANTS else token

    def birth_surnames(person: dict) -> set[str]:
        """Return only surnames belonging to the person at birth.

        Current/married surnames must never qualify an unlinked biological
        parent. A parenthetical surname is a cautious fallback when the export
        omitted the structured LNAB field.
        """
        values = list(person.get("birth_surnames", []))
        if not values:
            values.extend(re.findall(r"\(([^)]+)\)", str(person.get("name") or "")))
        return {
            canonical_birth_surname(token)
            for value in values for token in re.findall(r"[a-z]+", str(value).casefold())
        }

    def displayed_birth_surnames(value: str) -> set[str]:
        parenthetical = re.findall(r"\(([^)]+)\)", str(value or ""))
        if parenthetical:
            return {
                canonical_birth_surname(token)
                for item in parenthetical for token in re.findall(r"[a-z]+", item.casefold())
            }
        tokens = re.findall(r"[a-z]+", str(value or "").casefold())
        return {canonical_birth_surname(tokens[-1])} if tokens else set()

    def place_data(person: dict) -> tuple[set[str], set[str]]:
        exact = {normal_place(value) for value in person.get("locations", []) if value}
        tokens = {token for value in exact for token in value.split() if len(token) > 3 and token not in ignored_places}
        return exact, tokens

    def countries(person: dict) -> set[str]:
        text = " ".join(str(value) for value in person.get("locations", []) if value).casefold()
        patterns = {
            "ireland": r"\b(?:ireland|antrim|armagh|down|fermanagh|londonderry|tyrone|donegal)\b",
            "scotland": r"\b(?:scotland|lanarkshire|ayrshire|lothian|renfrewshire|wigtownshire)\b",
            "england": r"\bengland\b", "wales": r"\bwales\b", "australia": r"\baustralia\b",
            "canada": r"\bcanada\b", "new zealand": r"\bnew zealand\b",
            "united states": r"\b(?:united states|u\.?s\.?a\.?|america)\b",
        }
        return {country for country, pattern in patterns.items() if re.search(pattern, text)}

    def distance_km(a: dict, b: dict) -> float | None:
        # Some mapped profile places deliberately use a country-centre point
        # when no geocoder match exists. Comparing those coordinates can make
        # Virginia, Ohio and South Carolina appear to be the same place.
        if any(
            re.search(r"\bfallback\b|\bkin[ -]inferred\b|\b(?:country|county|historic[ -]county)[ -]level representative\b", str(item.get("precision") or ""), re.I)
            or "exact locality unproved" in str(item.get("location") or "").casefold()
            for item in (a, b)
        ):
            return None
        if not all(isinstance(item.get(key), (int, float)) for item in (a, b) for key in ("latitude", "longitude")):
            return None
        lat_a, lat_b = radians(a["latitude"]), radians(b["latitude"])
        d_lat = lat_b - lat_a
        d_lon = radians(b["longitude"] - a["longitude"])
        value = sin(d_lat / 2) ** 2 + cos(lat_a) * cos(lat_b) * sin(d_lon / 2) ** 2
        return 6371 * 2 * asin(sqrt(value))

    def identity_quality(person: dict) -> tuple[int, int, int, int]:
        return (
            int(not person.get("alternate_ids")),
            int(person.get("catalogue_id") == str(person.get("id", "")).casefold()),
            int(" and " not in str(person.get("name", "")).casefold()),
            -len(person.get("alternate_ids", [])),
        )

    primary_by_id = {}
    for person in index:
        current = primary_by_id.get(person["id"])
        if current is None or identity_quality(person) > identity_quality(current):
            primary_by_id[person["id"]] = person
    analysis_index = list(primary_by_id.values())
    people_by_id = dict(primary_by_id)
    for person in index:
        for profile_id in person.get("alternate_ids", []):
            people_by_id.setdefault(profile_id, person)
    years = defaultdict(list)
    for person in analysis_index:
        if isinstance(person.get("birth_year"), int):
            years[person["birth_year"]].append(person)

    prepared = {}
    for person in analysis_index:
        exact_places, place_tokens = place_data(person)
        birth_exact, birth_tokens = place_data({"locations": [person.get("birth_place")]})
        dated_records = []
        for record in person.get("_dated_records", []):
            record_exact, record_tokens = place_data({"locations": [record.get("location")]})
            dated_records.append({
                **record, "exact_places": record_exact, "place_tokens": record_tokens,
                "specific_place_tokens": record_tokens - broad_place_tokens,
            })
        prepared[person["id"]] = {
            "given": _relative_given_name(person.get("name", "")), "birth_surnames": birth_surnames(person),
            "exact_places": exact_places, "place_tokens": place_tokens,
            "specific_place_tokens": place_tokens - broad_place_tokens,
            "birth_exact": birth_exact, "birth_tokens": birth_tokens,
            "birth_specific_tokens": birth_tokens - broad_place_tokens,
            "countries": countries(person),
            "birth_countries": countries({"locations": [person.get("birth_place")]}),
            "clusters": set(person.get("research_clusters", [])),
            "dated_records": dated_records,
            "occupations": {
                normal_place(value) for value in person.get("occupations", []) if normal_place(value)
            },
            "spouse_surnames": {
                token
                for spouse_id in person.get("spouse_ids", [])
                if spouse_id in people_by_id
                for token in birth_surnames(people_by_id[spouse_id])
            } | {
                token for name in person.get("spouse_names", []) for token in displayed_birth_surnames(name)
            },
        }

    # This is the same population used by the catalogue statistics pane: one
    # first given name per public historical person.
    given_name_counts = Counter(
        data["given"] for data in prepared.values() if data["given"]
    )

    def rarity_points(given_name: str) -> tuple[int, int]:
        """Return inverse-frequency points and the public-profile frequency."""
        frequency = given_name_counts.get(given_name, 0)
        if frequency <= 1:
            return 12, frequency
        if frequency <= 3:
            return 9, frequency
        if frequency <= 7:
            return 7, frequency
        if frequency <= 15:
            return 5, frequency
        if frequency <= 30:
            return 3, frequency
        if frequency <= 75:
            return 1, frequency
        return 0, frequency

    def branch_rarity_points(given_name: str) -> tuple[int, int]:
        """Weight a name repeated across two family branches.

        Cross-branch recurrence is a stronger clue than a single ordered-name
        match. In this catalogue Adam and Arthur are uncommon enough to be
        genuinely discriminating, whereas John, James and Mary are not.
        """
        frequency = given_name_counts.get(given_name, 0)
        if frequency <= 1:
            return 18, frequency
        if frequency <= 3:
            return 16, frequency
        if frequency <= 7:
            return 14, frequency
        if frequency <= 15:
            return 12, frequency
        if frequency <= 30:
            return 8, frequency
        if frequency <= 75:
            return 3, frequency
        return 0, frequency

    children_by_parent = defaultdict(set)
    for person in analysis_index:
        for parent_id in person.get("parent_ids", []):
            children_by_parent[parent_id].add(person["id"])

    def relation_children(person: dict) -> list[tuple[str, str]]:
        if person.get("_family_links_disclaimed") or person.get("_structural_placeholder"):
            return []
        names = person.get("child_names", [])
        return [
            (child_id, names[position] if position < len(names) and names[position] else people_by_id.get(child_id, {}).get("name", child_id))
            for position, child_id in enumerate(person.get("child_ids", []))
        ]

    def branch_uses_unreviewed_child_links(person: dict, max_depth: int = 3) -> bool:
        """Flag branch clues that travel through unproved pedigree edges."""
        pending = deque([(person, 1)])
        seen = set()
        while pending:
            parent, depth = pending.popleft()
            if parent["id"] in seen or depth > max_depth:
                continue
            seen.add(parent["id"])
            links = {link.get("id"): link for link in parent.get("_child_links", [])}
            for child_id, _ in relation_children(parent):
                link = links.get(child_id) or {}
                reviewed = (
                    link.get("status") in {"proved", "strongly_supported", "probable"}
                    or link.get("tree_status") in {"dna_confirmed", "confident"}
                )
                if not reviewed:
                    return True
                child = people_by_id.get(child_id)
                if child and depth < max_depth:
                    pending.append((child, depth + 1))
        return False

    descendant_cache: dict[tuple[str, int], dict[str, set[str]]] = {}

    def descendant_given_names(person: dict, max_depth: int = 3) -> dict[str, set[str]]:
        cache_key = (person["id"], max_depth)
        cached = descendant_cache.get(cache_key)
        if cached is not None:
            return cached
        result: dict[str, set[str]] = defaultdict(set)
        pending = deque((child_id, name, 1) for child_id, name in relation_children(person))
        seen = set()
        while pending:
            child_id, name, depth = pending.popleft()
            if child_id in seen or depth > max_depth:
                continue
            seen.add(child_id)
            if given_name := _relative_given_name(name):
                result[given_name].add(name)
            child = people_by_id.get(child_id)
            if child and depth < max_depth:
                pending.extend((next_id, next_name, depth + 1) for next_id, next_name in relation_children(child))
        descendant_cache[cache_key] = result
        return result

    def missing_sibling_name_echo(candidate: dict, subject_given: str) -> dict | None:
        """Find a subject name repeated below separate child branches of a candidate's child.

        If two children of Ninian each name a daughter Elizabeth/Bessie, an
        otherwise unplaced Elizabeth may be Ninian's sister and therefore a
        missing child of Ninian's father. This is a collateral naming lead, not
        relationship proof, so only independent branches qualify.
        """
        if not subject_given:
            return None
        best = None
        for anchor_id, anchor_name in relation_children(candidate):
            anchor = people_by_id.get(anchor_id)
            if not anchor:
                continue
            branches = []
            for branch_id, branch_name in relation_children(anchor):
                branch = people_by_id.get(branch_id)
                if not branch:
                    continue
                matches: dict[str, int] = {}
                if _relative_given_name(branch_name or branch.get("name", "")) == subject_given:
                    matches[branch_name or branch.get("name") or branch_id] = 0
                pending = deque((child_id, child_name, 1) for child_id, child_name in relation_children(branch))
                seen = set()
                while pending:
                    descendant_id, descendant_name, depth = pending.popleft()
                    if descendant_id in seen or depth > 2:
                        continue
                    seen.add(descendant_id)
                    if _relative_given_name(descendant_name) == subject_given:
                        matches[descendant_name] = min(depth, matches.get(descendant_name, depth))
                    descendant = people_by_id.get(descendant_id)
                    if descendant and depth < 2:
                        pending.extend(
                            (next_id, next_name, depth + 1)
                            for next_id, next_name in relation_children(descendant)
                        )
                if matches:
                    branches.append({
                        "id": branch_id,
                        "name": branch_name or branch.get("name") or branch_id,
                        "matches": sorted(matches),
                        "minimum_depth": min(matches.values()),
                    })
            if len(branches) < 2:
                continue
            total_matches = sum(len(branch["matches"]) for branch in branches)
            value = {
                "anchor_id": anchor_id,
                "anchor_name": anchor_name or anchor.get("name") or anchor_id,
                "branches": branches,
                "total_matches": total_matches,
                "echo_depth": max(branch["minimum_depth"] for branch in branches),
            }
            if best is None or (len(branches), -value["echo_depth"], total_matches) > (
                len(best["branches"]), -best["echo_depth"], best["total_matches"]
            ):
                best = value
        return best

    def sibling_ids(person: dict) -> set[str]:
        values = set(person.get("_sibling_ids", []))
        for parent_id in person.get("parent_ids", []):
            values.update(children_by_parent.get(parent_id, set()))
        values.discard(person["id"])
        values.difference_update(person.get("alternate_ids", []))
        return values

    def collateral_given_names(person: dict) -> dict[str, set[str]]:
        """Names among a candidate's siblings and their children (nieces/nephews)."""
        result: dict[str, set[str]] = defaultdict(set)
        explicit_names = person.get("sibling_names", [])
        explicit_ids = person.get("_sibling_ids", [])
        for position, name in enumerate(explicit_names):
            if given_name := _relative_given_name(name):
                result[given_name].add(f"sibling {name}")
        for sibling_id in sibling_ids(person):
            sibling = people_by_id.get(sibling_id)
            if not sibling:
                continue
            sibling_name = sibling.get("name") or sibling_id
            if sibling_id in explicit_ids:
                position = explicit_ids.index(sibling_id)
                if position < len(explicit_names) and explicit_names[position]:
                    sibling_name = explicit_names[position]
            if given_name := _relative_given_name(sibling_name):
                result[given_name].add(f"sibling {sibling_name}")
            for _, nibling_name in relation_children(sibling):
                if given_name := _relative_given_name(nibling_name):
                    result[given_name].add(f"niece/nephew {nibling_name}")
        return result

    def all_given_tokens(value: str) -> list[str]:
        """Return first and middle-name tokens, excluding married/birth surnames."""
        text = str(value or "").casefold().replace("’", "'")
        if "(" in text:
            text = text.split("(", 1)[0]
            tokens = re.findall(r"[a-z]+", text)
        else:
            tokens = re.findall(r"[a-z]+", text)
            if len(tokens) > 1:
                tokens = tokens[:-1]
        ignored = {"rev", "reverend", "dr", "older", "younger", "probably", "possible", "unknown"}
        return [token for token in tokens if token not in ignored]

    surname_counts = Counter(
        token
        for person in analysis_index
        for value in person.get("birth_surnames", [])
        for token in re.findall(r"[a-z]+", str(value).casefold())
        if token not in {"unknown"}
    )

    def surname_rarity_points(surname: str) -> tuple[int, int]:
        frequency = surname_counts.get(surname, 0)
        if frequency <= 2:
            return 8, frequency
        if frequency <= 5:
            return 6, frequency
        if frequency <= 15:
            return 4, frequency
        if frequency <= 50:
            return 2, frequency
        return 0, frequency

    def expected_position(person_gender: str | None, parent_role: str) -> tuple[str, int] | None:
        """Scottish naming position for the parent of the person having the children."""
        if person_gender == "Male":
            return ("Male", 1) if parent_role == "father" else ("Female", 2)
        if person_gender == "Female":
            return ("Male", 2) if parent_role == "father" else ("Female", 1)
        return None

    child_group_cache: dict[str, list[dict]] = {}

    def child_groups(person: dict) -> list[dict]:
        """Group dated children by their other recorded parent and retain true ordinal gaps."""
        if person["id"] in child_group_cache:
            return child_group_cache[person["id"]]
        groups: dict[str, dict] = {}
        person_ids = {person["id"], *person.get("alternate_ids", [])}
        for child_id, relation_name in relation_children(person):
            child = people_by_id.get(child_id)
            if not child:
                continue
            other_parent_ids = sorted(set(child.get("parent_ids", [])) - person_ids)
            other_parent_id = other_parent_ids[0] if len(other_parent_ids) == 1 else ""
            group = groups.setdefault(other_parent_id, {
                "other_parent_id": other_parent_id or None,
                "other_parent": people_by_id.get(other_parent_id), "children": [],
            })
            group["children"].append({
                "id": child_id, "name": relation_name or child.get("name") or child_id,
                "given": _relative_given_name(relation_name or child.get("name") or ""),
                "given_tokens": all_given_tokens(relation_name or child.get("name") or ""),
                "gender": child.get("gender"), "birth_year": child.get("birth_year"),
                "birth_place": child.get("birth_place"),
                "death_year": child.get("death_year"), "parent_ids": child.get("parent_ids", []),
                "html_url": child.get("html_url"),
            })
        result = []
        for group in groups.values():
            group["children"].sort(key=lambda child: (child.get("birth_year") is None, child.get("birth_year") or 9999, child["name"]))
            for gender in ("Male", "Female"):
                ordered = [child for child in group["children"] if child.get("gender") == gender and child.get("birth_year") is not None]
                group["sons" if gender == "Male" else "daughters"] = ordered
            reused = set()
            for gender_key in ("sons", "daughters"):
                prior = {}
                for child in group[gender_key]:
                    given = child.get("given")
                    earlier = prior.get(given) if given else None
                    if earlier and earlier.get("death_year") is not None and earlier["death_year"] <= child["birth_year"]:
                        reused.add(given)
                    if given:
                        prior[given] = child
            group["reused_names"] = reused
            result.append(group)
        child_group_cache[person["id"]] = result
        return result

    def positioned_child(group: dict, gender: str, ordinal: int) -> dict | None:
        values = group["sons" if gender == "Male" else "daughters"]
        return values[ordinal - 1] if len(values) >= ordinal else None

    def tradition_controls(person: dict) -> dict:
        """Test known father/mother and in-law positions before inferring unknown grandparents."""
        matches, mismatches, details = 0, 0, []
        for group in child_groups(person):
            partner = group.get("other_parent")
            father = person if person.get("gender") == "Male" else partner if partner and partner.get("gender") == "Male" else None
            mother = person if person.get("gender") == "Female" else partner if partner and partner.get("gender") == "Female" else None
            for expected_person, gender, ordinal, label in (
                (father, "Male", 3, "third son/father"),
                (mother, "Female", 3, "third daughter/mother"),
            ):
                child = positioned_child(group, gender, ordinal)
                expected = _relative_given_name(expected_person.get("name", "")) if expected_person else ""
                observed = child.get("given") if child else ""
                if expected and observed:
                    if expected == observed:
                        matches += 1; details.append(f"{label} matches ({child['name']})")
                    else:
                        mismatches += 1; details.append(f"{label} does not match ({child['name']})")
            if partner:
                for parent_link in _comparison_parent_links(partner):
                    parent_role = parent_link.get("relationship")
                    if parent_role not in {"father", "mother"} or not parent_link.get("name"):
                        continue
                    position = expected_position(partner.get("gender"), parent_role)
                    if not position:
                        continue
                    child = positioned_child(group, *position)
                    expected = _relative_given_name(parent_link["name"])
                    observed = child.get("given") if child else ""
                    if expected and observed:
                        if expected == observed:
                            matches += 1; details.append(f"known in-law position matches ({child['name']})")
                        else:
                            mismatches += 1; details.append(f"known in-law position does not match ({child['name']})")
        factor = max(.65, min(1.35, 1 + .15 * matches - .10 * mismatches))
        return {"matches": matches, "mismatches": mismatches, "factor": factor, "details": details}

    descendant_id_cache: dict[tuple[str, int], set[str]] = {}

    def descendant_ids(person: dict, max_depth: int = 3) -> set[str]:
        key = (person["id"], max_depth)
        if key in descendant_id_cache:
            return descendant_id_cache[key]
        found, pending = set(), deque((child_id, 1) for child_id, _ in relation_children(person))
        while pending:
            child_id, depth = pending.popleft()
            if child_id in found or depth > max_depth:
                continue
            found.add(child_id)
            child = people_by_id.get(child_id)
            if child and depth < max_depth:
                pending.extend((next_id, depth + 1) for next_id, _ in relation_children(child))
        descendant_id_cache[key] = found
        return found

    def people_from_roots(root_ids: set[str], max_depth: int = 2) -> set[str]:
        result = set(root_ids)
        for root_id in root_ids:
            root = people_by_id.get(root_id)
            if root:
                result.update(descendant_ids(root, max_depth))
        return result

    def given_name_profile_ids(profile_ids: set[str]) -> dict[str, set[str]]:
        """Index first names to distinct profiles, preserving repetition counts."""
        values: dict[str, set[str]] = defaultdict(set)
        for profile_id in profile_ids:
            profile = people_by_id.get(profile_id)
            if profile and (given_name := _relative_given_name(profile.get("name", ""))):
                values[given_name].add(profile_id)
        return values

    def branch_spouse_surnames(profile_ids: set[str]) -> set[str]:
        values = set()
        for profile_id in profile_ids:
            profile = people_by_id.get(profile_id)
            if not profile:
                continue
            for spouse_id in profile.get("spouse_ids", []):
                spouse = people_by_id.get(spouse_id)
                if spouse:
                    values.update(token for value in spouse.get("birth_surnames", []) for token in re.findall(r"[a-z]+", str(value).casefold()))
        return values - {"glasgow", "unknown"}

    migration_cache: dict[str, tuple[set[str], set[str]]] = {}

    def person_migration(profile_id: str) -> tuple[set[str], set[str]]:
        """Return migration destinations, keeping only genuinely specific places."""
        if profile_id in migration_cache:
            return migration_cache[profile_id]
        profile = people_by_id.get(profile_id)
        if not profile:
            return set(), set()
        profile_data = prepared[profile["id"]]
        migrated = (
            profile_data["countries"] - profile_data["birth_countries"]
            if profile_data["birth_countries"] else set()
        )
        destination_places = {
            place
            for place in profile_data["exact_places"] - profile_data["birth_exact"]
            if (set(place.split()) - ignored_places - broad_place_tokens)
        } if migrated else set()
        migration_cache[profile_id] = (migrated, destination_places)
        return migration_cache[profile_id]

    def branch_migration(profile_ids: set[str]) -> tuple[set[str], set[str]]:
        destination_countries, destination_places = set(), set()
        for profile_id in profile_ids:
            migrated, places = person_migration(profile_id)
            destination_countries.update(migrated)
            destination_places.update(places)
        return destination_countries, destination_places

    migration_place_counts = Counter(
        place
        for person in analysis_index
        for place in person_migration(person["id"])[1]
    )

    results = {}
    for subject in analysis_index:
        subject_id = subject["id"]
        if requested_subject_ids is not None and subject_id not in requested_subject_ids:
            continue
        subject_birth = subject.get("birth_year")
        subject_birth_expression = str(subject.get("_birth_expression") or "").casefold()
        subject_birth_before = bool(re.search(r"\bbefore\b", subject_birth_expression))
        subject_birth_after = bool(re.search(r"\bafter\b", subject_birth_expression))
        subject_exact_birth = subject.get("birth_status") == "exact" or bool(
            re.search(r"\b\d{4}-\d{2}-\d{2}\b|\b\d{1,2}\s+[a-z]{3,9}\s+\d{4}\b", subject_birth_expression)
        )
        child_details = []
        subject_child_names = subject.get("child_names", [])
        scoring_child_ids = [] if subject.get("_family_links_disclaimed") else subject.get("child_ids", [])
        for child_index, child_id in enumerate(scoring_child_ids):
            child = people_by_id.get(child_id)
            if child:
                relation_name = subject_child_names[child_index] if child_index < len(subject_child_names) else None
                child_details.append({
                    "id": child["id"], "name": relation_name or child["name"], "birth_year": child.get("birth_year"),
                    "death_year": child.get("death_year"), "gender": child.get("gender"),
                    "parent_ids": child.get("parent_ids", []), "html_url": child.get("html_url"),
                })
        known_child_names = {child["name"] for child in child_details}
        child_details.extend(
            {"id": None, "name": name, "birth_year": None, "death_year": None, "gender": None, "parent_ids": [], "html_url": None}
            for name in subject.get("child_names", []) if name not in known_child_names
        )
        child_givens = {_relative_given_name(child["name"]) for child in child_details} - {""}
        dated_child_years = sorted(
            child["birth_year"] for child in child_details if isinstance(child.get("birth_year"), int)
        )
        earliest_child_birth = dated_child_years[0] if dated_child_years else None
        subject_controls = tradition_controls(subject)
        subject_family_groups = child_groups(subject)
        primary_child_group = max(subject_family_groups, key=lambda group: len(group["children"]), default=None)
        earliest_son = positioned_child(primary_child_group, "Male", 1) if primary_child_group else None
        earliest_daughter = positioned_child(primary_child_group, "Female", 1) if primary_child_group else None
        second_son = positioned_child(primary_child_group, "Male", 2) if primary_child_group else None
        second_daughter = positioned_child(primary_child_group, "Female", 2) if primary_child_group else None
        third_son = positioned_child(primary_child_group, "Male", 3) if primary_child_group else None
        third_daughter = positioned_child(primary_child_group, "Female", 3) if primary_child_group else None
        subject_sibling_ids = set() if subject.get("_family_links_disclaimed") else sibling_ids(subject)
        subject_sibling_givens = set(_relative_given_names(subject.get("sibling_names", []))) | {
            _relative_given_name(people_by_id[sibling_id].get("name", ""))
            for sibling_id in subject_sibling_ids if sibling_id in people_by_id
        }
        subject_sibling_givens.discard("")
        subject_descendant_names = descendant_given_names(subject)
        subject_descendant_ids = descendant_ids(subject, 3)
        subject_branch_ids = {subject_id, *subject_descendant_ids}
        subject_branch_name_ids = given_name_profile_ids(subject_branch_ids)
        subject_branch_spouse_surnames = branch_spouse_surnames(subject_branch_ids)
        subject_migration_countries, subject_migration_places = branch_migration(subject_branch_ids)
        subject_ids = {subject_id, *subject.get("alternate_ids", [])}
        subject_similar = {candidate["id"]: candidate for candidate in similar_by_id.get(subject_id, [])}
        existing_parent_ids = set(subject.get("parent_ids", []))
        subject_parent_links = _comparison_parent_links(subject)
        parent_in_law_ids = {
            parent_id
            for spouse_id in subject.get("spouse_ids", [])
            if (spouse := people_by_id.get(spouse_id))
            for parent_id in spouse.get("parent_ids", [])
        }
        excluded_ids = set(subject.get("child_ids", [])) | set(subject.get("spouse_ids", [])) | set(subject.get("_sibling_ids", [])) | subject_ids
        candidates = []
        if isinstance(subject_birth, int) and not subject.get("_structural_placeholder"):
            # Approximate dates can straddle the usual minimum parental age.
            # Search a narrow extension, then require the uncertainty interval
            # to overlap a biologically plausible parent-child gap.
            age_candidate_map = {
                candidate["id"]: candidate
                for year in range(subject_birth - 60, subject_birth - 5)
                for candidate in years.get(year, [])
            }
            for parent_id in existing_parent_ids:
                if parent_id in people_by_id and isinstance(people_by_id[parent_id].get("birth_year"), int):
                    age_candidate_map.setdefault(people_by_id[parent_id]["id"], people_by_id[parent_id])
            age_candidates = list(age_candidate_map.values())
            for candidate in age_candidates:
                if candidate["id"] in excluded_ids or candidate.get("gender") not in {"Male", "Female"}:
                    continue
                candidate_ids = {candidate["id"], *candidate.get("alternate_ids", [])}
                existing_parent = bool(existing_parent_ids & candidate_ids)
                age_gap = subject_birth - candidate["birth_year"]
                if not existing_parent and candidate.get("death_year") is not None and candidate["death_year"] < subject_birth - 1:
                    continue
                role = "possible father" if candidate["gender"] == "Male" else "possible mother"
                candidate_birth_expression = str(candidate.get("_birth_expression") or "").casefold()
                subject_approximate = bool(re.search(r"\b(?:c|circa|about|approx(?:imately)?|estimated)\b", subject_birth_expression))
                candidate_approximate = bool(re.search(r"\b(?:c|circa|about|approx(?:imately)?|estimated)\b", candidate_birth_expression))
                subject_slack = 10 if subject_approximate and not subject_birth_before else 0
                candidate_slack = 10 if candidate_approximate else 0
                max_possible_gap = age_gap + subject_slack + candidate_slack
                minimum_parent_age = 16 if role == "possible father" else 15
                maximum_parent_age = 60 if role == "possible father" else 52
                if not existing_parent and (
                    max_possible_gap < minimum_parent_age
                    or age_gap - subject_slack - candidate_slack > maximum_parent_age
                ):
                    continue
                # A maternal age above 52 is biologically implausible. Fathers
                # retain the wider 16–60-year search window.
                if not existing_parent and role == "possible mother" and age_gap - subject_slack - candidate_slack > 52:
                    continue
                subject_data, candidate_data = prepared[subject_id], prepared[candidate["id"]]
                surname_match = bool(subject_data["birth_surnames"] & candidate_data["birth_surnames"])
                maternal_surname_match = bool(
                    subject_data["birth_surnames"]
                    & (candidate_data["birth_surnames"] | candidate_data["spouse_surnames"])
                )
                # A person already attached as the parent of the subject's
                # spouse is an in-law, not an alternative biological parent.
                # Without an existing direct parent link, offering that person
                # would amount to proposing that the married couple were
                # siblings merely because both families reused similar names.
                if not existing_parent and parent_in_law_ids & candidate_ids:
                    continue
                expected_role = "father" if role == "possible father" else "mother"
                linked_parent = next((
                    link for link in subject_parent_links
                    if link.get("id") in candidate_ids and link.get("relationship") in {expected_role, "parent"}
                ), None)
                competing_parents = [
                    link for link in subject_parent_links
                    if link.get("id") not in candidate_ids and link.get("relationship") in {expected_role, "parent"}
                    and link.get("tree_status") != "non_biological"
                ]
                # Surname is an eligibility check, not evidence: nearly every paternal candidate shares it.
                if not existing_parent and not (surname_match if role == "possible father" else maternal_surname_match):
                    continue

                # A separately audited, proved parent is an exclusion, not a
                # soft deduction. WikiTree's own confident/uncertain marker is
                # useful context but is not equivalent to documentary proof.
                if not linked_parent and any(link.get("status") == "proved" for link in competing_parents):
                    continue
                # A full exact birth date commonly comes from a baptism or
                # civil birth entry. When such a profile already has a parent
                # attached, an unmarked WikiTree confidence flag is not enough
                # reason to generate alternative parents. Explicitly uncertain,
                # disputed or contradicted links remain open to comparison.
                if not linked_parent and subject_exact_birth and any(
                    link.get("status") not in {"possible", "disputed", "contradicted"}
                    and link.get("tree_status") not in {"uncertain", "non_biological"}
                    for link in competing_parents
                ):
                    continue
                if linked_parent and linked_parent.get("tree_status") == "non_biological":
                    continue

                score, reasons, conflicts, naming_signals = 0, [], [], 0
                dimensions: set[str] = set()
                nonparent_tree_path = None
                direct_family_signal = False
                competing_parent_blocks_strong = False
                duplicate_child_proxy = False
                sibling_parent_conflict = False
                relationship_certainty = "Not currently linked as parent"
                if linked_parent:
                    dimensions.add("current relationship")
                    certainty, certainty_label = _parent_certainty(linked_parent)
                    relationship_certainty = certainty_label
                    if candidate.get("death_year") is not None and candidate["death_year"] < subject_birth - 1:
                        score -= 20
                        conflicts.append(
                            f"currently linked parent died before the subject's plausible conception period "
                            f"(−20; candidate died {candidate['death_year']}, subject dated {subject_birth})"
                        )
                    if linked_parent.get("status") == "proved":
                        score += 40; reasons.append(f"independently documented current parent (+40; {certainty_label})")
                    elif linked_parent.get("status") == "strongly_supported":
                        score += 28; reasons.append(f"strongly supported current parent (+28; {certainty_label})")
                    elif linked_parent.get("status") == "probable":
                        score += 14; reasons.append(f"probable current parent (+14; {certainty_label})")
                    elif linked_parent.get("tree_status") == "dna_confirmed":
                        score += 16; reasons.append("current WikiTree parent is marked confirmed with DNA (+16; citation not independently audited here)")
                    elif linked_parent.get("tree_status") == "confident":
                        score += 6; reasons.append("current WikiTree parent is marked confident (+6; not documentary proof)")
                    elif linked_parent.get("tree_status") == "uncertain":
                        reasons.append("currently linked parent is explicitly marked uncertain (+0)")
                    elif subject_exact_birth:
                        score += 10; dimensions.add("exact-birth parent attachment")
                        reasons.append("exact birth date accompanies the current parent attachment (+10; record likely, citation still requires inspection)")
                    elif certainty < 0:
                        score -= 30; conflicts.append(f"current attachment is contradicted (−30; {certainty_label})")
                    else:
                        reasons.append("currently linked as parent, but relationship status is unassessed (+0)")
                elif competing_parents:
                    strongest_competitor = max(competing_parents, key=lambda link: _parent_certainty(link)[0])
                    competitor_certainty, competitor_label = _parent_certainty(strongest_competitor)
                    explicitly_open = (
                        strongest_competitor.get("status") in {"possible", "disputed", "contradicted"}
                        or strongest_competitor.get("tree_status") in {"uncertain", "non_biological"}
                    )
                    if explicitly_open:
                        score -= 6
                        conflicts.append(
                            f"a different linked {expected_role} is explicitly uncertain "
                            "(−6; an existing hypothesis still needs resolving)"
                        )
                    elif strongest_competitor.get("status") in {"strongly_supported", "probable"}:
                        score -= 30; conflicts.append(f"a different {expected_role} is strongly supported (−30; {competitor_label})")
                        competing_parent_blocks_strong = True
                    elif strongest_competitor.get("tree_status") == "dna_confirmed":
                        score -= 35; conflicts.append(f"a different {expected_role} is marked DNA-confirmed on WikiTree (−35)")
                        competing_parent_blocks_strong = True
                    elif strongest_competitor.get("tree_status") == "confident" or competitor_certainty >= 2:
                        score -= 25; conflicts.append(f"a different {expected_role} is marked confident (−25; {competitor_label})")
                        competing_parent_blocks_strong = True
                    else:
                        score -= 15
                        conflicts.append(f"a different {expected_role} is already linked but its evidence is unassessed (−15)")
                        competing_parent_blocks_strong = True
                if not linked_parent:
                    uncle_links = []
                    for parent_link in competing_parents:
                        parent_profile = people_by_id.get(parent_link.get("id"))
                        if parent_profile and (
                            candidate["id"] in parent_profile.get("_sibling_ids", [])
                            or parent_profile["id"] in candidate.get("_sibling_ids", [])
                        ):
                            uncle_links.append(parent_link)
                    if uncle_links:
                        nonparent_tree_path = "uncle/aunt"
                        uncle_certainty = max(_parent_certainty(link)[0] for link in uncle_links)
                        points = 12 if uncle_certainty >= 3 else 5
                        score -= points
                        conflicts.append(
                            f"candidate is currently placed as a sibling of another linked {expected_role} "
                            f"(−{points}; this makes the candidate an uncle/aunt under that tree hypothesis)"
                        )
                    grandparent_links = [
                        parent_link for parent_link in subject_parent_links
                        if (parent_profile := people_by_id.get(parent_link.get("id")))
                        and candidate["id"] in parent_profile.get("parent_ids", [])
                    ]
                    if grandparent_links:
                        nonparent_tree_path = "grandparent"
                        score -= 15
                        conflicts.append("candidate is currently placed one generation above a linked parent (−15; grandparent rather than parent)")
                    co_parent_links = [
                        parent_link for parent_link in subject_parent_links
                        if (parent_profile := people_by_id.get(parent_link.get("id")))
                        and candidate["id"] in parent_profile.get("spouse_ids", [])
                        and parent_link.get("relationship") not in {expected_role, "parent"}
                    ]
                    if co_parent_links:
                        score += 8; dimensions.add("parental couple structure")
                        direct_family_signal = True
                        reasons.append("candidate is the spouse of the linked opposite-sex parent (+8; tree couple clue)")
                dimensions.add("age")
                bounded_before = bool(re.search(r"\bbefore\b", candidate_birth_expression))
                bounded_after = bool(re.search(r"\bafter\b", candidate_birth_expression))
                same_direction_bounds = (
                    (subject_birth_before and bounded_before)
                    or (subject_birth_after and bounded_after)
                )
                if age_gap < minimum_parent_age and max_possible_gap >= minimum_parent_age:
                    age_gap_label = (
                        f"nominally {age_gap} years; approximate dates permit about "
                        f"{minimum_parent_age}–{max_possible_gap} years"
                    )
                elif same_direction_bounds:
                    age_gap_label = f"nominally {age_gap} years; true gap uncertain"
                elif subject_birth_before or bounded_after:
                    age_gap_label = f"at most {age_gap} years"
                elif subject_birth_after or bounded_before:
                    age_gap_label = f"at least {age_gap} years"
                else:
                    age_gap_label = f"{age_gap} years"
                ideal_age = (20 <= age_gap <= 45) if role == "possible father" else (18 <= age_gap <= 40)
                possible_age = (16 <= age_gap <= 55) if role == "possible father" else (15 <= age_gap <= 47)
                if age_gap < minimum_parent_age and max_possible_gap >= minimum_parent_age:
                    score += 4
                    reasons.append(
                        f"the nominal {age_gap}-year gap is too small, but the approximate birth date permits a narrow "
                        f"biologically viable interval ({minimum_parent_age}–{max_possible_gap} years) (+4)"
                    )
                    conflicts.append("parentage requires the approximate birth estimate to be early enough (no deduction)")
                elif (subject_birth_before or subject_birth_after or bounded_before or bounded_after) and (ideal_age or possible_age):
                    score += 10
                    reasons.append(f"bounded birth date gives a parent-child age gap of {age_gap_label} (+10; true age remains uncertain)")
                elif ideal_age:
                    score += 18; reasons.append(f"plausible {age_gap}-year parent-child age gap (+18)")
                elif possible_age:
                    score += 10; reasons.append(f"possible {age_gap}-year parent-child age gap (+10)")
                elif 0 < age_gap <= (60 if role == "possible father" else 50):
                    score += 2; reasons.append(f"less typical {age_gap}-year parent-child age gap (+2)")
                else:
                    score -= 8; conflicts.append(f"chronologically conflicting {age_gap}-year parent-child age gap (−8)")

                if earliest_child_birth is not None:
                    grandchild_gap = earliest_child_birth - candidate["birth_year"]
                    if 40 <= grandchild_gap <= 100:
                        score += 4; dimensions.add("two-generation chronology")
                        reasons.append(
                            f"candidate's birth is {grandchild_gap} years before the subject's earliest dated child "
                            f"({earliest_child_birth}), a compatible grandparent-generation interval (+4)"
                        )
                    elif 28 <= grandchild_gap <= 115:
                        score += 1; dimensions.add("two-generation chronology")
                        reasons.append(
                            f"candidate's birth is {grandchild_gap} years before the subject's earliest dated child "
                            f"({earliest_child_birth}), a marginal two-generation interval (+1)"
                        )
                    else:
                        score -= 8
                        conflicts.append(
                            f"candidate-to-earliest-child interval of {grandchild_gap} years is implausible for two generations (−8)"
                        )

                birth_exact_place = subject_data["birth_exact"] & candidate_data["exact_places"]
                specific_birth_exact_place = {
                    value for value in birth_exact_place
                    if set(value.split()) - ignored_places - broad_place_tokens
                }
                birth_place_tokens = subject_data["birth_specific_tokens"] & candidate_data["specific_place_tokens"]
                exact_place = subject_data["exact_places"] & candidate_data["exact_places"]
                specific_exact_place = {
                    value for value in exact_place
                    if set(value.split()) - ignored_places - broad_place_tokens
                }
                shared_place_tokens = subject_data["place_tokens"] & candidate_data["place_tokens"]
                timed_place_matches = []
                for record in candidate_data["dated_records"]:
                    # Reconstructed/probable map placements cannot turn a
                    # static locality into a time-specific residence claim.
                    if record.get("status") not in {"proved", "strongly_supported"} and record.get("source_quality") != "original":
                        continue
                    shared_record_exact = subject_data["birth_exact"] & record["exact_places"]
                    exact_match = any(
                        set(value.split()) - ignored_places - broad_place_tokens
                        for value in shared_record_exact
                    )
                    token_match = bool(subject_data["birth_specific_tokens"] & record["specific_place_tokens"])
                    if exact_match or token_match:
                        timed_place_matches.append((0 if exact_match else 1, abs(record["year"] - subject_birth), record))
                timed_place_matches.sort(key=lambda match: (match[0], match[1]))
                subject_birth_records = [
                    record for record in subject_data["dated_records"]
                    if abs(record["year"] - subject_birth) <= 20
                ]
                coordinate_matches = []
                for subject_record in subject_birth_records:
                    for candidate_record in candidate_data["dated_records"]:
                        if (distance := distance_km(subject_record, candidate_record)) is not None:
                            coordinate_matches.append((distance, subject_record, candidate_record))
                coordinate_matches.sort(key=lambda match: match[0])
                nearby_match = coordinate_matches[0] if coordinate_matches and coordinate_matches[0][0] <= 30 else None
                birth_locality_match = bool(
                    timed_place_matches or specific_birth_exact_place or specific_exact_place or birth_place_tokens
                )
                if timed_place_matches:
                    match_type, year_delta, record = timed_place_matches[0]
                    if match_type == 0:
                        points = 32 if year_delta <= 15 else 24 if year_delta <= 35 else 12 if year_delta <= 60 else 6
                        location_label = "the subject's stated birthplace"
                    else:
                        points = 22 if year_delta <= 15 else 15 if year_delta <= 35 else 7 if year_delta <= 60 else 3
                        location_label = "the subject's birth locality"
                    score += points
                    dimensions.add("time-specific locality")
                    reasons.append(
                        f"candidate has a supported {record['year']} {record.get('association') or 'record'} in {location_label}, "
                        f"{year_delta} years from the subject's birth (+{points})"
                    )
                elif specific_birth_exact_place:
                    score += 10; dimensions.add("undated locality")
                    reasons.append("candidate is associated with the subject's stated birthplace, but not by a reliable near-contemporary record (+10)")
                elif specific_exact_place:
                    score += 10; dimensions.add("undated locality")
                    reasons.append(
                        f"same specific indexed locality despite wider place-label differences: "
                        f"{', '.join(sorted(specific_exact_place)[:2])} (+10)"
                    )
                elif birth_place_tokens:
                    score += 6; dimensions.add("undated locality")
                    reasons.append(f"candidate has only broad or undated birth-locality overlap: {', '.join(sorted(birth_place_tokens)[:3])} (+6)")
                elif nearby_match:
                    distance, subject_record, candidate_record = nearby_match
                    supported_pair = all(
                        record.get("status") in {"proved", "strongly_supported"} or record.get("source_quality") == "original"
                        for record in (subject_record, candidate_record)
                    )
                    if supported_pair:
                        points = 12 if distance <= 5 else 7 if distance <= 15 else 3
                        birth_locality_match = distance <= 15
                    else:
                        points = 3 if distance <= 5 else 2 if distance <= 15 else 1
                    score += points; dimensions.add("mapped proximity")
                    reasons.append(
                        f"mapped {candidate_record.get('location') or 'candidate locality'} is {distance:.1f} km from the subject's "
                        f"birth-period {subject_record.get('location') or 'locality'} (+{points}{'; one or both placements are unproved' if not supported_pair else ''})"
                    )
                elif exact_place:
                    score += 1; dimensions.add("broad geography")
                    reasons.append("same broad administrative area only (+1; not a locality match)")
                elif shared_place_tokens:
                    score += 1; dimensions.add("broad geography")
                    reasons.append(f"weak broad-area overlap: {', '.join(sorted(shared_place_tokens)[:3])} (+1; not a locality match)")
                else:
                    shared_countries = subject_data["birth_countries"] & candidate_data["countries"]
                    if shared_countries:
                        score -= 10
                        conflicts.append("same country, but no indexed locality overlap (−10)")
                    elif not (subject_data["birth_countries"] and candidate_data["countries"]):
                        conflicts.append("locality comparison is unavailable because one or both profiles lack adequate place data (no deduction)")
                if subject_data["birth_countries"] and candidate_data["countries"] and not subject_data["birth_countries"] & candidate_data["countries"]:
                    score -= 25; conflicts.append("candidate is recorded only outside the subject's birth country (−25)")
                shared_clusters = subject_data["clusters"] & candidate_data["clusters"]
                if shared_clusters:
                    reasons.append("same research cluster (+0; grouping is not kinship evidence)")

                candidate_known_children = [
                    people_by_id[child_id] for child_id in candidate.get("child_ids", [])
                    if child_id not in subject_ids and child_id in people_by_id
                ]
                # Prefer the nearer eligible generation when the current tree
                # offers both a person and that person's adult child as parent
                # candidates in the subject's locality. This is not an
                # exclusion—the older person could still have had a late
                # child—but the child is normally the better first lead.
                nearer_generation_children = [
                    child for child in candidate_known_children
                    if child.get("gender") == candidate.get("gender")
                    and isinstance(child.get("birth_year"), int)
                    and minimum_parent_age <= subject_birth - child["birth_year"] <= maximum_parent_age
                    and child["id"] in prepared
                    and (
                        subject_data["birth_specific_tokens"]
                        & prepared[child["id"]]["birth_specific_tokens"]
                    )
                ]
                if nearer_generation_children:
                    nearer = min(
                        nearer_generation_children,
                        key=lambda child: subject_birth - child["birth_year"],
                    )
                    score -= 6
                    conflicts.append(
                        f"candidate's child {nearer['name']} ({nearer['id']}) is also a plausible {expected_role} "
                        f"in the subject's birth locality (−6; current tree places this candidate one generation farther back)"
                    )
                matching_child_profiles = [
                    (child, subject_similar[child["id"]])
                    for child in candidate_known_children if child["id"] in subject_similar
                ]
                if not matching_child_profiles:
                    # The general duplicate table can suppress a pair when
                    # their attached parents conflict.  For parentage, a
                    # candidate's same-name, same-age child in the same place
                    # must still be resolved before inventing an additional
                    # child profile.
                    for child in candidate_known_children:
                        child_data = prepared.get(child["id"], {})
                        same_identity_shape = (
                            _relative_given_name(child.get("name", "")) == subject_data["given"]
                            and child.get("gender") in {None, "", subject.get("gender")}
                            and isinstance(child.get("birth_year"), int)
                            and abs(child["birth_year"] - subject_birth) <= 3
                            and bool(
                                subject_data["birth_specific_tokens"]
                                & child_data.get("birth_specific_tokens", set())
                            )
                        )
                        if same_identity_shape:
                            matching_child_profiles.append((child, {"score": 80}))
                if matching_child_profiles:
                    proxy_child, proxy_match = max(
                        matching_child_profiles, key=lambda value: value[1].get("score", 0)
                    )
                    duplicate_child_proxy = True
                    dimensions.add("matching child profile")
                    reasons.append(
                        f"candidate already has child profile {proxy_child['name']} ({proxy_child['id']}), which the similar-person "
                        f"scorer matches to the subject at {proxy_match.get('score', 0)}/100 (+0; resolve that possible duplicate "
                        f"before treating the subject as an additional child)"
                    )
                    conflicts.append("candidate parentage depends on resolving a matching existing child profile first")

                contemporary_children = [
                    child for child in candidate_known_children
                    if isinstance(child.get("birth_year"), int)
                    and abs(child["birth_year"] - subject_birth) <= 7
                    and prepared.get(child["id"], {}).get("birth_specific_tokens")
                ]
                if subject_data["birth_specific_tokens"] and contemporary_children:
                    local_children = [
                        child for child in contemporary_children
                        if subject_data["birth_specific_tokens"]
                        & prepared[child["id"]]["birth_specific_tokens"]
                    ]
                    if not local_children:
                        nearest = min(
                            contemporary_children,
                            key=lambda child: abs(child["birth_year"] - subject_birth),
                        )
                        score -= 12
                        dimensions.add("contemporaneous household conflict")
                        conflicts.append(
                            f"candidate's household recorded {nearest['name']} in "
                            f"{nearest.get('birth_place') or 'a different specific locality'} within "
                            f"{abs(nearest['birth_year'] - subject_birth)} years of the subject "
                            "(−12; no contemporaneous child is indexed in the subject's locality)"
                        )
                candidate_groups = child_groups(candidate)
                candidate_child_years = sorted(
                    child["birth_year"] for child in candidate_known_children
                    if isinstance(child.get("birth_year"), int)
                )
                best_co_parent = None
                local_birth_window_awarded = False
                if candidate_child_years:
                    nearest_child_gap = min(abs(year - subject_birth) for year in candidate_child_years)
                    has_older_child = any(year < subject_birth for year in candidate_child_years)
                    has_younger_child = any(year > subject_birth for year in candidate_child_years)
                    co_parent_spans = []
                    for group in candidate_groups:
                        group_years = sorted(
                            child["birth_year"] for child in group["children"]
                            if child["id"] not in subject_ids and isinstance(child.get("birth_year"), int)
                        )
                        if (
                            group.get("other_parent_id")
                            and group_years
                            and any(year < subject_birth for year in group_years)
                            and any(year > subject_birth for year in group_years)
                        ):
                            co_parent_spans.append((group_years[-1] - group_years[0], group, group_years))
                    if co_parent_spans:
                        _, best_group, group_years = min(co_parent_spans, key=lambda value: value[0])
                        best_co_parent = best_group.get("other_parent")
                        points = 3 if subject_birth_before or subject_birth_after else 6
                        score += points; dimensions.add("spouse-specific child window")
                        reasons.append(
                            f"{'subject birth boundary overlaps' if subject_birth_before or subject_birth_after else 'subject\'s birth fits between'} "
                            f"children attributed to the same parental couple "
                            f"({group_years[0]}–{group_years[-1]}) (+{points}"
                            f"{'; other parent ' + best_co_parent['name'] if best_co_parent else ''})"
                        )
                        local_children = []
                        for child in best_group["children"]:
                            child_year = child.get("birth_year")
                            if not isinstance(child_year, int) or abs(child_year - subject_birth) > 25:
                                continue
                            _, child_birth_tokens = place_data({"locations": [child.get("birth_place")]})
                            if subject_data["birth_specific_tokens"] & (child_birth_tokens - broad_place_tokens):
                                local_children.append(child)
                        local_older = [child for child in local_children if child["birth_year"] < subject_birth]
                        local_younger = [child for child in local_children if child["birth_year"] > subject_birth]
                        if local_older and local_younger:
                            older = max(local_older, key=lambda child: child["birth_year"])
                            younger = min(local_younger, key=lambda child: child["birth_year"])
                            score += 10; dimensions.add("local same-spouse child window")
                            local_birth_window_awarded = True
                            reasons.append(
                                f"same-couple children {older['name']} ({older['birth_year']}) and "
                                f"{younger['name']} ({younger['birth_year']}) bracket the subject in the same specific "
                                "birth locality (+10; strong household-placement clue, not proof)"
                            )
                            missing_slot = younger["birth_year"] - older["birth_year"]
                            if not (subject_birth_before or subject_birth_after) and 3 <= missing_slot <= 12:
                                score += 4; dimensions.add("birth-order gap")
                                reasons.append(
                                    f"the subject fills a {missing_slot}-year gap between those same-couple, same-locality "
                                    f"children (+4; corroborated missing birth-order slot)"
                                )
                    elif has_older_child and has_younger_child:
                        score += 3; dimensions.add("household chronology")
                        reasons.append(
                            f"subject's birth fits within the candidate's overall child-bearing span "
                            f"({candidate_child_years[0]}–{candidate_child_years[-1]}) (+3; children are not tied to one spouse)"
                        )
                    elif nearest_child_gap == 0:
                        score += 2; dimensions.add("household chronology")
                        reasons.append("another recorded child shares the subject's birth year (+2; possible twins or date uncertainty)")
                    elif nearest_child_gap <= 3:
                        score += 3; dimensions.add("household chronology")
                        reasons.append(f"a known child was born within {nearest_child_gap} years of the subject (+3)")
                    elif nearest_child_gap <= 8:
                        score += 1; dimensions.add("household chronology")
                        reasons.append(f"a known child was born within {nearest_child_gap} years of the subject (+1)")
                    elif len(candidate_child_years) >= 2 and nearest_child_gap > 20:
                        score -= 6
                        conflicts.append(
                            f"subject lies more than 20 years from the candidate's known child-bearing period (−6; children may be missing)"
                        )

                if not local_birth_window_awarded and subject_data["birth_specific_tokens"]:
                    nearby_local_children = []
                    for child in candidate_known_children:
                        child_year = child.get("birth_year")
                        if not isinstance(child_year, int) or abs(child_year - subject_birth) > 15:
                            continue
                        _, child_birth_tokens = place_data({"locations": [child.get("birth_place")]})
                        if subject_data["birth_specific_tokens"] & (child_birth_tokens - broad_place_tokens):
                            nearby_local_children.append(child)
                    if nearby_local_children:
                        nearest_local_child = min(
                            nearby_local_children,
                            key=lambda child: (abs(child["birth_year"] - subject_birth), child["name"]),
                        )
                        local_gap = abs(nearest_local_child["birth_year"] - subject_birth)
                        points = 6 if local_gap <= 4 else 4 if local_gap <= 10 else 2
                        score += points; dimensions.add("local sibling birth")
                        reasons.append(
                            f"candidate has another child, {nearest_local_child['name']}, born {local_gap} years from the "
                            f"subject in the same specific birth locality (+{points}; possible sibling-household clue)"
                        )

                subject_given = subject_data["given"]
                unresolved_same_named_children = [
                    child for child in candidate_known_children
                    if subject_given
                    and _relative_given_name(child.get("name", "")) == subject_given
                    and child.get("gender") == subject.get("gender")
                    and not (
                        isinstance(child.get("death_year"), int)
                        and child["death_year"] <= subject_birth
                    )
                ]
                if unresolved_same_named_children and not duplicate_child_proxy:
                    same_named = min(
                        unresolved_same_named_children,
                        key=lambda child: abs((child.get("birth_year") or subject_birth) - subject_birth),
                    )
                    score -= 4
                    conflicts.append(
                        f"candidate already has another child named {same_named['name']} ({same_named['id']}) "
                        "without a documented death permitting name reuse (−4; check whether the child profiles duplicate or conflict)"
                    )

                if role == "possible father" and candidate.get("spouse_ids"):
                    spouse_profiles = [people_by_id[spouse_id] for spouse_id in candidate["spouse_ids"] if spouse_id in people_by_id]
                    if best_co_parent in spouse_profiles:
                        spouse_profiles = [best_co_parent, *[spouse for spouse in spouse_profiles if spouse["id"] != best_co_parent["id"]]]
                    dated_spouses = [spouse for spouse in spouse_profiles if isinstance(spouse.get("birth_year"), int)]
                    plausible_spouses = [
                        spouse for spouse in dated_spouses
                        if 15 <= subject_birth - spouse["birth_year"] <= 50
                        and (spouse.get("death_year") is None or spouse["death_year"] >= subject_birth - 1)
                    ]
                    if plausible_spouses:
                        best_spouse = min(plausible_spouses, key=lambda spouse: abs((subject_birth - spouse["birth_year"]) - 29))
                        maternal_age = subject_birth - best_spouse["birth_year"]
                        spouse_birth_expression = str(best_spouse.get("_birth_expression") or "").casefold()
                        spouse_birth_bounded = bool(re.search(
                            r"\b(?:before|after|c|circa|about|approx(?:imately)?|estimated)\b",
                            spouse_birth_expression,
                        )) or subject_birth_before or subject_birth_after
                        points = 3 if spouse_birth_bounded else 7 if 17 <= maternal_age <= 45 else 3
                        score += points; dimensions.add("spouse chronology")
                        reasons.append(
                            f"known spouse {best_spouse['name']} had a {'bounded, possibly plausible' if spouse_birth_bounded else 'plausible'} "
                            f"maternal age ({maternal_age}) at the subject's birth (+{points})"
                        )
                    elif spouse_profiles and len(dated_spouses) == len(spouse_profiles) and all(
                        not re.search(
                            r"\b(?:before|after|c|circa|about|approx(?:imately)?|estimated)\b",
                            str(spouse.get("_birth_expression") or "").casefold(),
                        )
                        for spouse in dated_spouses
                    ):
                        score -= 6
                        conflicts.append("no known spouse has a plausible maternal age at the subject's birth (−6; an unknown spouse remains possible)")

                occupation_overlap = subject_data["occupations"] & candidate_data["occupations"]
                if occupation_overlap:
                    score += 3; dimensions.add("occupation")
                    reasons.append(f"shared recorded occupation: {', '.join(sorted(occupation_overlap)[:2])} (+3; weak household-continuity clue)")

                land_terms = re.compile(r"\b(?:farm|farmer|lease|rent|tithe|tenant|holding|valuation|acre)\w*\b")
                reliable_subject_land = [
                    record for record in subject_data["dated_records"]
                    if land_terms.search(str(record.get("association") or "").casefold())
                    and (record.get("status") in {"proved", "strongly_supported"} or record.get("source_quality") == "original")
                ]
                reliable_candidate_land = [
                    record for record in candidate_data["dated_records"]
                    if land_terms.search(str(record.get("association") or "").casefold())
                    and (record.get("status") in {"proved", "strongly_supported"} or record.get("source_quality") == "original")
                ]
                tenure_pair = next((
                    (candidate_record, subject_record)
                    for candidate_record in reliable_candidate_land for subject_record in reliable_subject_land
                    if candidate_record["exact_places"] & subject_record["exact_places"]
                    and candidate_record["year"] <= subject_record["year"]
                    and subject_record["year"] - candidate_record["year"] <= 100
                ), None)
                if tenure_pair:
                    candidate_record, subject_record = tenure_pair
                    score += 8; dimensions.add("tenancy succession")
                    reasons.append(
                        f"supported land/farming records place candidate ({candidate_record['year']}) before subject "
                        f"({subject_record['year']}) at the same place (+8; tenancy continuity is not proof of kinship)"
                    )

                candidate_given = candidate_data["given"]
                parent_role = "father" if role == "possible father" else "mother"
                subject_given = subject_data["given"]
                if candidate_given and candidate_given == subject_given and candidate.get("gender") == subject.get("gender"):
                    rarity, frequency = rarity_points(candidate_given)
                    points = 4 + min(rarity, 4)
                    score += points; naming_signals += 1; dimensions.add("same-sex generational naming")
                    reasons.append(
                        f"candidate and subject share the given name {candidate_given.title()} (+{points}; weak direct "
                        f"parent-child name recurrence, {frequency} public profiles)"
                    )
                candidate_position = expected_position(subject.get("gender"), parent_role)
                candidate_position_matches = []
                if candidate_position:
                    for group in subject_family_groups:
                        child = positioned_child(group, *candidate_position)
                        if child and child.get("given") == candidate_given:
                            candidate_position_matches.append((group, child))
                if candidate_position_matches:
                    group, expected_child = candidate_position_matches[0]
                    rarity, frequency = rarity_points(candidate_given)
                    # A common first name in the expected Scottish position is
                    # useful, but should not overpower a linked parent or weak
                    # geography. Rarity and independent controls earn the
                    # larger values, rather than every James/Mary match.
                    # A common John/James/Mary in the traditional position is
                    # one weak clue, not a relationship verdict. Rarity and
                    # independently observed adherence to the tradition earn
                    # most of the available weight.
                    raw_points = min(26, 4 + round(1.5 * rarity))
                    points = max(2, round(raw_points * subject_controls["factor"]))
                    score += points; naming_signals += 1; dimensions.add("sex-aware ordered naming")
                    ordinal = {1: "first", 2: "second", 3: "third"}[candidate_position[1]]
                    child_kind = "son" if candidate_position[0] == "Male" else "daughter"
                    reasons.append(
                        f"candidate's name matches the {ordinal} dated {child_kind} {expected_child['name']}, the expected "
                        f"{parent_role} position for a {subject.get('gender', 'unknown-sex').casefold()} subject "
                        f"(+{points}; catalogue rarity {rarity}, {candidate_given.title()} in {frequency} profiles)"
                    )
                    if expected_child.get("given") in group.get("reused_names", set()):
                        score += 3; dimensions.add("name reuse")
                        reasons.append(f"the matched name was deliberately reused after an earlier child's death (+3)")
                    if len(candidate_position_matches) > 1:
                        extra = min(8, 4 * (len(candidate_position_matches) - 1))
                        score += extra; dimensions.add("multiple child groups")
                        reasons.append(f"the same ordered grandparent position matches in {len(candidate_position_matches)} child groups (+{extra})")
                    if subject_controls["matches"] or subject_controls["mismatches"]:
                        dimensions.add("tradition validation")
                        reasons.append(
                            f"family naming controls: {subject_controls['matches']} supporting and "
                            f"{subject_controls['mismatches']} conflicting known positions (already reflected in naming weight)"
                        )
                elif candidate_given in child_givens:
                    rarity, frequency = rarity_points(candidate_given)
                    if rarity:
                        score += rarity; naming_signals += 1; dimensions.add("child naming")
                        reasons.append(
                            f"candidate's given name recurs among another recorded child (+{rarity}; "
                            f"{candidate_given.title()} occurs in {frequency} public profiles)"
                        )

                other_parent_role = "mother" if parent_role == "father" else "father"
                spouse_position = expected_position(subject.get("gender"), other_parent_role)
                candidate_spouse_givens = set(_relative_given_names(candidate.get("spouse_names", [])))
                spouse_position_matches = []
                if spouse_position:
                    for group in subject_family_groups:
                        child = positioned_child(group, *spouse_position)
                        if child and child.get("given") in candidate_spouse_givens:
                            spouse_position_matches.append((group, child))
                if spouse_position_matches:
                    spouse_group, expected_spouse_child = spouse_position_matches[0]
                    expected_spouse_given = expected_spouse_child["given"]
                    rarity, frequency = rarity_points(expected_spouse_given)
                    points = max(2, round((3 + rarity) * subject_controls["factor"]))
                    score += points; naming_signals += 1; dimensions.add("sex-aware ordered naming")
                    ordinal = {1: "first", 2: "second", 3: "third"}[spouse_position[1]]
                    child_kind = "son" if spouse_position[0] == "Male" else "daughter"
                    reasons.append(
                        f"a candidate spouse matches the {ordinal} dated {child_kind} {expected_spouse_child['name']}, "
                        f"the expected {other_parent_role} position (+{points}; {expected_spouse_given.title()} in {frequency} profiles)"
                    )
                    if any(group is spouse_group for group, _ in candidate_position_matches):
                        candidate_rarity, _ = rarity_points(candidate_given)
                        combined_rarity = candidate_rarity + rarity
                        couple_points = min(10, 2 + combined_rarity)
                        score += couple_points; naming_signals += 1
                        if combined_rarity >= 3:
                            dimensions.add("parental couple naming")
                        else:
                            dimensions.add("common parental couple naming")
                        reasons.append(
                            "candidate and spouse jointly match both grandparent positions in the same child group "
                            f"(+{couple_points}; combined catalogue rarity {combined_rarity})"
                        )

                sibling_link_by_id = {link.get("id"): link for link in subject.get("_sibling_links", [])}
                sibling_household_matches = []
                for sibling_id in subject.get("_sibling_ids", []):
                    sibling = people_by_id.get(sibling_id)
                    if not sibling:
                        continue
                    sibling_position = expected_position(sibling.get("gender"), parent_role)
                    if not sibling_position:
                        continue
                    for group in child_groups(sibling):
                        child = positioned_child(group, *sibling_position)
                        if child and child.get("given") == candidate_given:
                            link = sibling_link_by_id.get(sibling_id, {})
                            status = link.get("status") or "unknown"
                            points = 9 if status in {"proved", "strongly_supported", "probable"} else 5 if status == "possible" else 3
                            spouse_match = False
                            sibling_spouse_position = expected_position(sibling.get("gender"), other_parent_role)
                            spouse_child = positioned_child(group, *sibling_spouse_position) if sibling_spouse_position else None
                            if spouse_child and spouse_child.get("given") in candidate_spouse_givens:
                                points += 4; spouse_match = True
                            sibling_household_matches.append((points, sibling, child, spouse_match))
                            break
                if sibling_household_matches:
                    sibling_household_matches.sort(key=lambda match: (-match[0], match[1]["name"]))
                    selected = sibling_household_matches[:3]
                    points = min(26, sum(match[0] for match in selected))
                    score += points; naming_signals += 1; dimensions.add("sibling-household replication")
                    examples = "; ".join(
                        f"{sibling['name']} → {child['name']}{' with spouse-position match' if spouse_match else ''}"
                        for _, sibling, child, spouse_match in selected
                    )
                    reasons.append(
                        f"the same sex-aware parent-name position recurs independently in sibling households: {examples} (+{points})"
                    )

                exact_sibling_child_ids = set(candidate.get("child_ids", [])) & subject_sibling_ids
                sibling_links_by_id = {
                    link.get("id"): link for link in subject.get("_sibling_links", []) if link.get("id")
                }
                hypothesis_only_sibling_ids = {
                    sibling_id for sibling_id in exact_sibling_child_ids
                    if (link := sibling_links_by_id.get(sibling_id))
                    and not link.get("tree_relationship")
                    and link.get("status") in {"possible", "probable", "disputed", "contradicted"}
                }
                if hypothesis_only_sibling_ids:
                    exact_sibling_child_ids -= hypothesis_only_sibling_ids
                    conflicts.append(
                        "the apparent sibling bridge is itself only a research hypothesis for "
                        + ", ".join(
                            people_by_id[sibling_id].get("name", sibling_id)
                            for sibling_id in sorted(hypothesis_only_sibling_ids)
                        )
                        + " (+0; a possible sibling cannot be recycled as exact parentage evidence)"
                    )
                conflicted_sibling_ids = set()
                for sibling_id in exact_sibling_child_ids:
                    sibling = people_by_id.get(sibling_id, {})
                    same_role_parents = {
                        link.get("id")
                        for link in _comparison_parent_links(sibling)
                        if link.get("id") and (
                            link.get("relationship") == expected_role
                            or (
                                link.get("relationship") == "parent"
                                and people_by_id.get(link.get("id"), {}).get("gender") == candidate.get("gender")
                            )
                        )
                    }
                    if same_role_parents - candidate_ids:
                        conflicted_sibling_ids.add(sibling_id)
                if conflicted_sibling_ids:
                    exact_sibling_child_ids -= conflicted_sibling_ids
                    sibling_parent_conflict = True
                    conflicts.append(
                        "the apparent sibling bridge contains competing same-role parents on "
                        + ", ".join(
                            people_by_id[sibling_id].get("name", sibling_id)
                            for sibling_id in sorted(conflicted_sibling_ids)
                        )
                        + " (+0; resolve that tree conflict before using the sibling as parentage evidence)"
                    )
                if exact_sibling_child_ids:
                    points = min(32, 12 + 4 * len(exact_sibling_child_ids))
                    score += points; dimensions.add("exact sibling profiles")
                    direct_family_signal = True
                    sibling_examples = [
                        people_by_id[profile_id]["name"]
                        for profile_id in sorted(exact_sibling_child_ids)
                        if profile_id in people_by_id
                    ]
                    reasons.append(
                        f"candidate is already linked as parent of {len(exact_sibling_child_ids)} exact subject sibling "
                        f"profile{'s' if len(exact_sibling_child_ids) != 1 else ''} (+{points}): "
                        + ", ".join(sibling_examples[:5])
                    )
                    sibling_co_parents = Counter(
                        parent_id
                        for sibling_id in exact_sibling_child_ids
                        if (sibling := people_by_id.get(sibling_id))
                        for parent_id in sibling.get("parent_ids", [])
                        if parent_id not in candidate_ids
                    )
                    if sibling_co_parents:
                        co_parent_id, co_parent_count = sibling_co_parents.most_common(1)[0]
                        opposite_role = "mother" if expected_role == "father" else "father"
                        subject_opposite_parent_ids = {
                            link.get("id") for link in subject_parent_links
                            if link.get("relationship") in {opposite_role, "parent"} and link.get("id")
                        }
                        co_parent = people_by_id.get(co_parent_id)
                        if co_parent_id in subject_opposite_parent_ids:
                            couple_points = 14 if co_parent_count >= 2 else 10
                            score += couple_points; dimensions.add("sibling parental couple")
                            direct_family_signal = True
                            reasons.append(
                                f"the candidate and the subject's linked {opposite_role} "
                                f"{co_parent.get('name', co_parent_id) if co_parent else co_parent_id} are jointly recorded as parents "
                                f"of {co_parent_count} exact sibling profile{'s' if co_parent_count != 1 else ''} "
                                f"(+{couple_points}; strong couple-structure clue)"
                            )
                        elif co_parent_id in candidate.get("spouse_ids", []):
                            couple_points = 8 if co_parent_count >= 2 else 4
                            score += couple_points; dimensions.add("sibling parental couple")
                            reasons.append(
                                f"{co_parent_count} exact sibling profile{'s' if co_parent_count != 1 else ''} share candidate spouse "
                                f"{co_parent.get('name', co_parent_id) if co_parent else co_parent_id} as their other parent "
                                f"(+{couple_points}; candidate parental-couple clue)"
                            )

                candidate_child_names = []
                candidate_relation_names = candidate.get("child_names", [])
                for relative_index, relative_id in enumerate(candidate.get("child_ids", [])):
                    if relative_id in subject_ids or relative_id in exact_sibling_child_ids:
                        continue
                    relative = people_by_id.get(relative_id)
                    if relative:
                        relation_name = candidate_relation_names[relative_index] if relative_index < len(candidate_relation_names) else None
                        candidate_child_names.append(relation_name or relative["name"])
                if not candidate.get("child_ids"):
                    candidate_child_names.extend(candidate.get("child_names", []))
                candidate_child_givens = set(_relative_given_names(candidate_child_names))
                exact_sibling_givens = {
                    _relative_given_name(people_by_id[profile_id].get("name", ""))
                    for profile_id in exact_sibling_child_ids if profile_id in people_by_id
                }
                subject_sibling_overlap = sorted(
                    (subject_sibling_givens - exact_sibling_givens) & candidate_child_givens
                )
                scored_network_names: set[str] = set()
                if subject_sibling_overlap:
                    match_details, raw_points = [], 0
                    for given_name in subject_sibling_overlap:
                        rarity, frequency = branch_rarity_points(given_name)
                        if rarity:
                            raw_points += rarity
                            match_details.append(f"{given_name.title()} +{rarity} ({frequency} public profiles)")
                    bundle_bonus = (
                        min(8, 4 * (len(match_details) - 1))
                        if len(match_details) >= 2 and raw_points >= 8 else 0
                    )
                    points = min(40, raw_points + bundle_bonus)
                    if points:
                        score += points; naming_signals += 1
                        dimensions.add("rare sibling-name pattern")
                        if bundle_bonus:
                            dimensions.add("rare name bundle")
                        scored_network_names.update(
                            given_name for given_name in subject_sibling_overlap
                            if branch_rarity_points(given_name)[0]
                        )
                        reasons.append(
                            f"candidate's other children share uncommon given names with the subject's recorded siblings: "
                            f"{'; '.join(match_details)} (+{points} total"
                            f"{' including +' + str(bundle_bonus) + ' rare-name bundle bonus' if bundle_bonus else ''})"
                        )

                missing_sibling_echo = (
                    missing_sibling_name_echo(candidate, subject_data["given"])
                    if not child_details and not subject_parent_links else None
                )
                if missing_sibling_echo:
                    branch_count = len(missing_sibling_echo["branches"])
                    echo_depth = missing_sibling_echo["echo_depth"]
                    rarity, frequency = branch_rarity_points(subject_data["given"])
                    direct_points = min(40, 8 + rarity + 3 * branch_count)
                    points = max(6, direct_points - 8 * max(0, echo_depth - 1))
                    score += points; naming_signals += 1; dimensions.add("missing-sibling descendant echo")
                    branch_examples = "; ".join(
                        f"{branch['name']} branch: {', '.join(branch['matches'][:3])}"
                        for branch in missing_sibling_echo["branches"][:3]
                    )
                    reasons.append(
                        f"the subject's given name {subject_data['given'].title()} recurs below {branch_count} independent "
                        f"child branches of candidate's child {missing_sibling_echo['anchor_name']} "
                        f"({branch_examples}) (+{points}; catalogue rarity {rarity}, {subject_data['given'].title()} in {frequency} profiles; "
                        f"{'grandchild-level echo' if echo_depth <= 1 else 'more distant descendant echo'}, "
                        f"supports investigating the subject as that child's missing sibling)"
                    )

                candidate_other_roots = (
                    set() if nonparent_tree_path == "grandparent"
                    else set(candidate.get("child_ids", [])) - subject_ids
                )
                candidate_branch_ids = people_from_roots(candidate_other_roots, 2)
                candidate_branch_name_ids = given_name_profile_ids(candidate_branch_ids)
                shared_branch_profiles = subject_branch_ids & candidate_branch_ids
                rare_branch_overlap = sorted(
                    (set(subject_branch_name_ids) & set(candidate_branch_name_ids)) - scored_network_names
                )
                if rare_branch_overlap:
                    weighted_matches = []
                    for given_name in rare_branch_overlap:
                        subject_profiles = subject_branch_name_ids[given_name] - shared_branch_profiles
                        candidate_profiles = candidate_branch_name_ids[given_name] - shared_branch_profiles
                        rarity, frequency = branch_rarity_points(given_name)
                        if not (rarity and subject_profiles and candidate_profiles):
                            continue
                        repetition_bonus = min(
                            8,
                            2 * max(0, min(3, len(subject_profiles)) - 1)
                            + 2 * max(0, min(3, len(candidate_profiles)) - 1),
                        )
                        weighted_matches.append((
                            rarity + repetition_bonus, rarity, repetition_bonus, given_name, frequency,
                            subject_profiles, candidate_profiles,
                        ))
                    weighted_matches.sort(key=lambda match: (-match[0], match[3]))
                    selected_matches = weighted_matches[:3]
                    bundle_bonus = min(8, 4 * max(0, len(selected_matches) - 1))
                    points = min(48, sum(match[0] for match in selected_matches) + bundle_bonus)
                    if points >= 8:
                        score += points; naming_signals += 1; dimensions.add("rare branch-name recurrence")
                        if len(selected_matches) > 1:
                            dimensions.add("rare name bundle")
                        scored_network_names.update(match[3] for match in selected_matches)
                        match_details = []
                        for total, rarity, repetition_bonus, given_name, frequency, subject_profiles, candidate_profiles in selected_matches:
                            subject_examples = ", ".join(
                                people_by_id[profile_id]["name"] for profile_id in sorted(subject_profiles)[:2]
                                if profile_id in people_by_id
                            )
                            candidate_examples = ", ".join(
                                people_by_id[profile_id]["name"] for profile_id in sorted(candidate_profiles)[:2]
                                if profile_id in people_by_id
                            )
                            match_details.append(
                                f"{given_name.title()} +{total} ({frequency} public profiles; subject branch: "
                                f"{subject_examples}; candidate branch: {candidate_examples}"
                                f"{'; +' + str(repetition_bonus) + ' repetition bonus' if repetition_bonus else ''})"
                            )
                        reasons.append(
                            "uncommon given names recur in both otherwise distinct descendant branches: "
                            f"{'; '.join(match_details)} (+{points} total"
                            f"{' including +' + str(bundle_bonus) + ' multi-name bonus' if bundle_bonus else ''})"
                        )

                collateral_names = collateral_given_names(candidate)
                collateral_overlap = sorted((set(subject_descendant_names) & set(collateral_names)) - scored_network_names)
                if collateral_overlap:
                    weighted_matches = []
                    for given_name in collateral_overlap:
                        rarity, frequency = branch_rarity_points(given_name)
                        if rarity:
                            examples = ", ".join(sorted(collateral_names[given_name])[:2])
                            repetition_bonus = min(
                                6,
                                2 * max(0, min(3, len(subject_descendant_names[given_name])) - 1)
                                + 2 * max(0, min(3, len(collateral_names[given_name])) - 1),
                            )
                            weighted_matches.append((rarity + repetition_bonus, rarity, repetition_bonus, given_name, frequency, examples))
                    weighted_matches.sort(key=lambda match: (-match[0], match[3]))
                    selected_matches = weighted_matches[:3]
                    points = sum(match[0] for match in selected_matches)
                    if points >= 8:
                        score += points; naming_signals += 1; dimensions.add("collateral naming")
                        match_details = [
                            f"{given_name.title()} +{total} ({frequency} public profiles; {examples}"
                            f"{'; +' + str(repetition_bonus) + ' repetition bonus' if repetition_bonus else ''})"
                            for total, _, repetition_bonus, given_name, frequency, examples in selected_matches
                        ]
                        reasons.append(
                            f"candidate's sibling and niece/nephew network repeats names in the subject's descendant line "
                            f"(three rarest at most): {'; '.join(match_details)} (+{points} total)"
                        )

                candidate_parent_profiles = [
                    people_by_id[parent_id] for parent_id in candidate.get("parent_ids", []) if parent_id in people_by_id
                ]
                grandparent_role = "father" if subject.get("gender") == "Male" else "mother" if subject.get("gender") == "Female" else None
                grandparent_position = expected_position(candidate.get("gender"), grandparent_role) if grandparent_role else None
                grandparent_name_links = [
                    link for link in _comparison_parent_links(candidate)
                    if link.get("relationship") in {grandparent_role, "parent"}
                    and _relative_given_name(link.get("name", "")) == subject_given
                ] if grandparent_role else []
                if grandparent_position and grandparent_position[0] == subject.get("gender") and grandparent_name_links:
                    position_groups = []
                    for group in candidate_groups:
                        dated_same_sex_children = [
                            child for child in group["children"]
                            if child["id"] not in subject_ids
                            and child.get("gender") == subject.get("gender")
                            and isinstance(child.get("birth_year"), int)
                        ]
                        if not dated_same_sex_children or any(child["birth_year"] == subject_birth for child in dated_same_sex_children):
                            continue
                        prospective_ordinal = 1 + sum(child["birth_year"] < subject_birth for child in dated_same_sex_children)
                        has_required_anchor = (
                            (grandparent_position[1] == 1 and any(child["birth_year"] > subject_birth for child in dated_same_sex_children))
                            or (grandparent_position[1] > 1 and prospective_ordinal == grandparent_position[1])
                        )
                        if prospective_ordinal == grandparent_position[1] and has_required_anchor:
                            position_groups.append(group)
                    if position_groups:
                        grandparent_link = max(grandparent_name_links, key=lambda link: _parent_certainty(link)[0])
                        certainty, certainty_label = _parent_certainty(grandparent_link)
                        rarity, frequency = rarity_points(subject_given)
                        # Even a common grandparent/child-position match is a
                        # real (but weak) clue when it converges with locality,
                        # migration or chronology. Uncommon names may carry a
                        # lead; common names must not create one by themselves.
                        uncommon = rarity >= 3
                        points = (
                            min(18, 8 + rarity + (2 if certainty >= 2 else 0))
                            if uncommon else 2 + rarity
                        )
                        score += points
                        dimensions.add(
                            "grandparent birth-order naming" if uncommon
                            else "common grandparent birth-order naming"
                        )
                        if uncommon:
                            naming_signals += 1
                        ordinal = {1: "first", 2: "second", 3: "third"}.get(grandparent_position[1], str(grandparent_position[1]))
                        child_kind = "son" if subject.get("gender") == "Male" else "daughter"
                        reasons.append(
                            f"the subject would fill the {ordinal} {child_kind} position among the candidate's dated children, "
                            f"and the candidate's linked {grandparent_role} {grandparent_link.get('name')} shares the subject's "
                            f"{'uncommon ' if uncommon else 'common '}given name (+{points}; Scottish grandparent-name pattern, "
                            f"{subject_given.title()} in {frequency} public profiles; {certainty_label}"
                            f"{'; weak alone' if not uncommon else ''})"
                        )
                lineage_surnames = {
                    token
                    for relative in [*candidate_parent_profiles, *[
                        people_by_id[spouse_id] for spouse_id in candidate.get("spouse_ids", []) if spouse_id in people_by_id
                    ]]
                    for value in relative.get("birth_surnames", [])
                    for token in re.findall(r"[a-z]+", str(value).casefold())
                    if token not in {"glasgow", "unknown"}
                }
                descendant_middle_tokens = {
                    token
                    for descendant_id in subject_descendant_ids
                    if (descendant := people_by_id.get(descendant_id))
                    for token in all_given_tokens(descendant.get("name", ""))[1:]
                }
                middle_surname_matches = sorted(lineage_surnames & descendant_middle_tokens)
                if middle_surname_matches:
                    weighted = []
                    for surname in middle_surname_matches:
                        rarity, frequency = surname_rarity_points(surname)
                        if rarity:
                            weighted.append((rarity, surname, frequency))
                    weighted.sort(key=lambda match: (-match[0], match[1]))
                    selected = weighted[:2]
                    points = min(18, sum(match[0] + 2 for match in selected))
                    if points:
                        score += points; naming_signals += 1; dimensions.add("lineage surname as middle name")
                        reasons.append(
                            "candidate-line surnames recur as descendant middle names: "
                            + "; ".join(f"{surname.title()} +{rarity + 2} ({frequency} birth-surname profiles)" for rarity, surname, frequency in selected)
                            + f" (+{points} total)"
                        )

                subject_grandchild_ids = subject_descendant_ids - set(subject.get("child_ids", []))
                subject_grandchild_givens = {
                    _relative_given_name(people_by_id[profile_id].get("name", ""))
                    for profile_id in subject_grandchild_ids if profile_id in people_by_id
                } - {""}
                candidate_parent_givens = {
                    _relative_given_name(parent.get("name", "")) for parent in candidate_parent_profiles
                } - {""}
                great_grandparent_echoes = sorted((subject_grandchild_givens & candidate_parent_givens) - scored_network_names)
                if great_grandparent_echoes:
                    weighted = []
                    for given_name in great_grandparent_echoes:
                        rarity, frequency = rarity_points(given_name)
                        if rarity:
                            weighted.append((rarity, given_name, frequency))
                    weighted.sort(key=lambda match: (-match[0], match[1]))
                    selected = weighted[:2]
                    points = min(10, sum(match[0] for match in selected))
                    if points:
                        score += points; naming_signals += 1; dimensions.add("great-grandparent name echo")
                        reasons.append(
                            "candidate's parents' names recur among the subject's grandchildren: "
                            + "; ".join(f"{given.title()} +{rarity}" for rarity, given, _ in selected)
                            + f" (+{points} total; weak multigeneration clue)"
                        )

                candidate_branch_spouse_surnames = branch_spouse_surnames(candidate_branch_ids)
                repeated_marriage_surnames = sorted(subject_branch_spouse_surnames & candidate_branch_spouse_surnames)
                if repeated_marriage_surnames:
                    weighted = []
                    for surname in repeated_marriage_surnames:
                        rarity, frequency = surname_rarity_points(surname)
                        if rarity:
                            weighted.append((rarity, surname, frequency))
                    weighted.sort(key=lambda match: (-match[0], match[1]))
                    selected = weighted[:2]
                    points = min(10, sum(match[0] for match in selected))
                    if points:
                        score += points; dimensions.add("repeated marriage surnames")
                        reasons.append(
                            "uncommon spouse surnames recur across the subject and candidate branches: "
                            + "; ".join(f"{surname.title()} +{rarity}" for rarity, surname, _ in selected)
                            + f" (+{points} total)"
                        )

                candidate_migration_countries, candidate_migration_places = branch_migration(candidate_branch_ids)
                shared_migration_countries = sorted(subject_migration_countries & candidate_migration_countries)
                shared_migration_places = sorted(subject_migration_places & candidate_migration_places)
                if shared_migration_places:
                    migration_place = min(
                        shared_migration_places,
                        key=lambda place: (migration_place_counts.get(place, 0), place),
                    )
                    frequency = migration_place_counts.get(migration_place, 0)
                    rarity_bonus = 5 if frequency <= 3 else 3 if frequency <= 10 else 1 if frequency <= 30 else 0
                    subject_bearers = sum(
                        migration_place in person_migration(profile_id)[1]
                        for profile_id in subject_branch_ids
                    )
                    candidate_bearers = sum(
                        migration_place in person_migration(profile_id)[1]
                        for profile_id in candidate_branch_ids
                    )
                    repetition_bonus = min(
                        4,
                        max(0, min(subject_bearers, 3) - 1)
                        + max(0, min(candidate_bearers, 3) - 1),
                    )
                    points = min(15, 6 + rarity_bonus + repetition_bonus)
                    score += points; dimensions.add("branch migration")
                    reasons.append(
                        f"descendant branches converge on the same specific migration destination {migration_place} "
                        f"(+{points}; {frequency} migrated public profiles"
                        f"{'; +' + str(repetition_bonus) + ' repeated-branch bonus' if repetition_bonus else ''})"
                    )
                elif shared_migration_countries:
                    score += 1; dimensions.add("broad migration")
                    reasons.append(
                        f"descendant branches share only a broad migration destination country (+1; weak alone): "
                        f"{', '.join(shared_migration_countries[:2])}"
                    )

                candidate_other_descendants = people_from_roots(candidate_other_roots, 3)
                shared_descendants = subject_descendant_ids & candidate_other_descendants
                spouse_bridges = {
                    spouse_id
                    for descendant_id in subject_descendant_ids
                    if (descendant := people_by_id.get(descendant_id))
                    for spouse_id in descendant.get("spouse_ids", [])
                    if spouse_id in candidate_other_descendants
                }
                if shared_descendants or spouse_bridges:
                    points = 10 if spouse_bridges else 6
                    score += points; dimensions.add("branch reconvergence")
                    bridge_names = [people_by_id[profile_id]["name"] for profile_id in sorted(spouse_bridges or shared_descendants)[:2] if profile_id in people_by_id]
                    reasons.append(
                        f"the two branches reconnect through shared descendants or descendant marriages (+{points})"
                        + (f": {', '.join(bridge_names)}" if bridge_names else "")
                    )

                candidate_controls = tradition_controls(candidate)
                if naming_signals and candidate_controls["matches"] >= 2 and candidate_controls["matches"] > candidate_controls["mismatches"]:
                    score += 3; dimensions.add("candidate-family tradition")
                    reasons.append(
                        f"the candidate's own child family has {candidate_controls['matches']} known-position naming matches (+3; branch-level validation)"
                    )

                # Reward convergence between evidence types that can exist on
                # disconnected profiles. Do not count linked-parent/sibling
                # structure here: it is useful display context, but cannot
                # calibrate leads for the very profiles whose links are absent.
                direct_tree_dimensions = PARENTAGE_DIRECT_TREE_DIMENSIONS
                indirect_naming_dimensions = {
                    "same-sex generational naming", "sex-aware ordered naming", "child naming",
                    "parental couple naming", "common parental couple naming",
                    "missing-sibling descendant echo", "rare branch-name recurrence",
                    "collateral naming", "grandparent birth-order naming",
                    "common grandparent birth-order naming", "lineage surname as middle name",
                    "great-grandparent name echo", "candidate-family tradition",
                }
                indirect_categories = set()
                if dimensions & indirect_naming_dimensions:
                    indirect_categories.add("naming")
                if dimensions & {
                    "time-specific locality", "undated locality", "mapped proximity",
                    "tenancy succession", "local same-spouse child window", "local sibling birth",
                }:
                    indirect_categories.add("locality")
                if "branch migration" in dimensions:
                    indirect_categories.add("specific migration")
                if dimensions & {
                    "two-generation chronology", "spouse-specific child window", "birth-order gap",
                    "household chronology", "spouse chronology",
                }:
                    indirect_categories.add("household chronology")
                if dimensions & {
                    "repeated marriage surnames", "lineage surname as middle name",
                    "branch reconvergence", "occupation",
                }:
                    indirect_categories.add("collateral network")
                if len(indirect_categories) >= 3:
                    convergence_points = {3: 5, 4: 8}.get(len(indirect_categories), 10)
                    score += convergence_points
                    dimensions.add("indirect multi-factor convergence")
                    reasons.append(
                        f"{len(indirect_categories)} independent unlinked-profile clue types converge "
                        f"(+{convergence_points}): {', '.join(sorted(indirect_categories))}"
                    )

                structural_dimensions = {
                    "parental couple structure", "exact sibling profiles", "sibling-household replication",
                    "sibling parental couple", "birth-order gap", "local sibling birth",
                    "lineage surname as middle name", "repeated marriage surnames", "branch reconvergence",
                    "rare branch-name recurrence", "grandparent birth-order naming",
                    "local same-spouse child window",
                    "matching child profile",
                    "missing-sibling descendant echo",
                }
                chronology_only_fallback = not (
                    naming_signals or existing_parent or dimensions & structural_dimensions
                )
                independent_anchor_dimensions = {
                    "time-specific locality", "tenancy succession", "local sibling birth",
                    "local same-spouse child window", "spouse-specific child window",
                    "branch migration", "occupation", "exact sibling profiles",
                    "sibling parental couple", "parental couple structure",
                }
                if (
                    score >= 40 and naming_signals and not direct_family_signal
                    and not birth_locality_match
                    and not dimensions & independent_anchor_dimensions
                ):
                    score = min(score, 39)
                    conflicts.append(
                        "descendant-name recurrence has no independent household, record, migration or "
                        "specific-locality anchor (score capped at 39)"
                    )
                if subject.get("_family_links_disclaimed"):
                    score = min(score, 24)
                    conflicts.append(
                        "the subject's current profile explicitly says its displayed family links are not established "
                        "(score capped at 24; tree descendants are excluded from scoring)"
                    )
                elif subject.get("_birth_details_disclaimed"):
                    score = min(score, 39)
                    conflicts.append(
                        "the subject's current profile explicitly says its birth details are unproved "
                        "(score capped at 39)"
                    )
                if candidate.get("_profile_sources_tree_only") and not direct_family_signal and score >= 40:
                    score = min(score, 39)
                    conflicts.append(
                        "the candidate's captured citations consist only of an online family tree "
                        "(score capped at 39 without an exact sibling or parental-couple bridge)"
                    )
                branch_derived_dimensions = {
                    "rare branch-name recurrence", "collateral naming",
                    "lineage surname as middle name", "great-grandparent name echo",
                    "repeated marriage surnames", "branch migration", "broad migration",
                    "branch reconvergence", "missing-sibling descendant echo",
                }
                if (
                    score >= 40
                    and dimensions & branch_derived_dimensions
                    and (
                        branch_uses_unreviewed_child_links(subject)
                        or branch_uses_unreviewed_child_links(candidate)
                    )
                ):
                    score = min(score, 39)
                    conflicts.append(
                        "one or more branch-derived clues pass through unproved or merely possible "
                        "parent-child links (score capped at 39; pedigree structure is not independent evidence)"
                    )
                high_information_dimensions = {
                    "time-specific locality", "mapped proximity", "tenancy succession",
                    "local sibling birth", "local same-spouse child window",
                    "spouse-specific child window", "branch migration", "occupation",
                    "exact sibling profiles", "sibling parental couple",
                    "parental couple structure", "matching child profile",
                    "missing-sibling descendant echo", "rare sibling-name pattern",
                    "rare branch-name recurrence", "collateral naming",
                    "grandparent birth-order naming", "lineage surname as middle name",
                    "repeated marriage surnames", "branch reconvergence",
                }
                if score >= 40 and not direct_family_signal and not dimensions & high_information_dimensions:
                    score = min(score, 39)
                    conflicts.append(
                        "only broad locality, ordinary naming and chronology support the match "
                        "(score capped at 39 until a higher-information tree or record clue is found)"
                    )
                if linked_parent and linked_parent.get("status") == "proved":
                    classification = "documented parent"
                elif linked_parent and linked_parent.get("status") == "strongly_supported":
                    classification = "supported parent"
                else:
                    anchor_dimensions = {
                        "current relationship", "time-specific locality", "tenancy succession",
                        "exact sibling profiles", "rare sibling-name pattern",
                        "sibling-household replication", "sibling parental couple", "parental couple naming", "parental couple structure",
                        "collateral naming", "lineage surname as middle name", "branch reconvergence",
                        "rare branch-name recurrence",
                        "local same-spouse child window",
                        "local sibling birth", "birth-order gap", "grandparent birth-order naming",
                        "matching child profile",
                        "missing-sibling descendant echo",
                    }
                    classification = (
                        "resolve child duplicate first" if duplicate_child_proxy
                        else "resolve sibling tree conflict first" if sibling_parent_conflict
                        else "conflicting tree generation" if nonparent_tree_path in {"grandparent", "uncle/aunt"}
                        else "competing linked parent" if competing_parent_blocks_strong
                        else "strong multi-factor lead"
                        if score >= 65 and (birth_locality_match or direct_family_signal)
                        and (
                            direct_family_signal
                            or naming_signals >= 2
                            or (naming_signals >= 1 and len(dimensions & anchor_dimensions) >= 2)
                        )
                        and len(dimensions) >= 4 and dimensions & anchor_dimensions
                        else "moderate lead" if score >= 40 and len(dimensions) >= 3
                        and (naming_signals or existing_parent or dimensions & (anchor_dimensions - {"spouse-specific child window"}))
                        else "chronology-only fallback" if chronology_only_fallback
                        else "compatible household" if score >= 40 else "weak lead"
                    )
                indirect_dimensions = dimensions - direct_tree_dimensions
                candidates.append({
                    "id": candidate["id"], "name": candidate["name"], "catalogue_id": candidate["catalogue_id"],
                    "html_url": candidate["html_url"], "birth_year": candidate.get("birth_year"),
                    "death_year": candidate.get("death_year"), "gender": candidate.get("gender"),
                    "age_gap": age_gap, "age_gap_label": age_gap_label, "role": role,
                    "locations": candidate.get("locations", []), "score": max(0, min(100, score)),
                    "classification": classification, "reasons": reasons, "conflicts": conflicts,
                    "currently_linked_parent": existing_parent, "naming_signal_count": naming_signals,
                    "relationship_certainty": relationship_certainty,
                    "factor_count": len(dimensions), "factors": sorted(dimensions),
                    "indirect_factor_count": len(indirect_dimensions),
                    "suggested_co_parent": {
                        "id": best_co_parent.get("id"), "name": best_co_parent.get("name"), "html_url": best_co_parent.get("html_url")
                    } if best_co_parent else None,
                })
        ranked = []
        classification_rank = {
            "documented parent": 0, "supported parent": 1, "strong multi-factor lead": 2,
            "moderate lead": 3, "weak lead": 4, "compatible household": 5,
            "chronology-only fallback": 6, "competing linked parent": 7,
            "resolve child duplicate first": 8, "conflicting tree generation": 9,
            "resolve sibling tree conflict first": 8,
        }
        for role in ("possible father", "possible mother"):
            role_candidates = sorted(
                (
                    candidate for candidate in candidates
                    if candidate["role"] == role and not candidate["currently_linked_parent"]
                ),
                key=lambda candidate: (
                    classification_rank.get(candidate["classification"], 9),
                    -candidate["score"], candidate["age_gap"], candidate["name"],
                ),
            )
            selected = role_candidates[:5]
            ranked.extend(selected)
        # The public top-five worklist stays compact, but a maintained dossier
        # must retain scores requested by its reviewed candidate inventory.
        # Include linked, retired and lower-ranked individuals here so “not
        # scored” cannot merely mean “fell outside the global display cap”.
        selected_ids = {candidate["id"] for candidate in ranked}
        wanted_ids = reviewed_score_ids.get(subject_id, set())
        ranked.extend(
            candidate for candidate in candidates
            if candidate["id"] in wanted_ids and candidate["id"] not in selected_ids
        )
        ranked.sort(key=lambda candidate: (
            classification_rank.get(candidate["classification"], 9),
            -candidate["score"], candidate["age_gap"], candidate["name"],
        ))
        results[subject_id] = {
            "children_recorded": child_details,
            "earliest_dated_son": earliest_son,
            "earliest_dated_daughter": earliest_daughter,
            "second_dated_son": second_son,
            "second_dated_daughter": second_daughter,
            "third_dated_son": third_son,
            "third_dated_daughter": third_daughter,
            "naming_controls": subject_controls,
            "candidates": ranked,
            "method": "Automated leads use birth surnames—not married surnames—as parental eligibility, role-specific biological age limits, bounded and approximate-date uncertainty, household chronology, specific time-aware localities, mapped distance, tenancy succession, migration destinations and sex-aware Scottish naming positions across generations. People already attached as the subject's parents stay in the identity summary and are excluded from this alternative-candidate list, regardless of relationship confidence. The main calibration uses clues available on disconnected profiles; existing parent and sibling links are retained as comparison context rather than treated as transferable evidence. Common ordered names and grandparent-to-child echoes receive a small non-zero weight, so a John or James match can support several independent criteria without producing a lead alone. Rare names, repeated bearers and bundles across otherwise distinct branches receive substantially more weight according to catalogue frequency. An exact migration place is weighted by its rarity and repetition across both branches; a shared destination country is worth only one point. Extra weight is added only when at least three independent clue types converge: naming, locality, specific migration, household chronology or collateral networks. Sparse profiles retain a clearly labelled chronology-only fallback instead of disappearing. Countries, states, counties and research clusters do not count as a shared locality, and fallback, broad representative or kin-inferred coordinates are excluded from distance scoring. Shared descendant profiles are removed before branch-name comparison. A candidate already recorded as a parent-in-law is excluded. A confident or independently supported parent is treated as settled; uncertain and unassessed attachments remain open to alternative comparison. A different linked parent, an uncle/aunt or grandparent path, and a matching existing child profile prevent an alternative from being classified as a strong direct-parent lead until the underlying tree conflict or duplicate is resolved. Familiar forms such as Bessie are normalised. Surname remains an eligibility filter worth zero points.",
            "warning": "Naming customs, shared farms and occupations are circumstantial. Children, spouses and collateral relatives may be missing, and tree-derived family networks are not independent evidence. Scores rank research leads; they do not prove parentage.",
        }
    return results


def _best_supporting_evidence(record: dict, dossier: dict) -> dict:
    """Suggest a cited source for a mapped association without claiming a proved match."""
    if record.get("source_type") == "explicit":
        return {
            "title": record.get("source_title"), "url": record.get("source_url"),
            "quality": "original" if "original" in record.get("source_status", "").casefold() else "unknown",
            "status": "explicit", "reason": "Explicitly attached to this mapped association.",
        }
    record_text = f"{record.get('association', '')} {record.get('note', '')}".casefold()
    location_tokens = {
        token for token in re.findall(r"[a-z]{4,}", (record.get("record_location") or "").casefold())
        if token not in {"townland", "county", "ireland", "scotland", "united", "kingdom", "states"}
    }
    years = set(re.findall(r"\b(?:1\d{3}|20\d{2})\b", f"{record.get('year', '')} {record.get('filter_year', '')}"))
    categories = {value.casefold() for value in _catalogue_record_types({"records": [record]})}
    ranked = []
    for item in dossier.get("evidence", []):
        if item.get("provenance") in {"mapped_record", "profile-provenance", "profile-export"}:
            continue
        source = item.get("source") or {}
        title, url = source.get("title") or "", source.get("url") or ""
        if not title and not url:
            continue
        candidate_text = f"{title} {item.get('record_type', '')} {item.get('assertion', '')}".casefold()
        score, reasons = 0, []
        candidate_categories = {value.casefold() for value in _catalogue_record_types({"records": [{"association": candidate_text}]})}
        shared_categories = categories & candidate_categories
        if shared_categories:
            score += 3
            reasons.append("record type")
        shared_years = years & set(re.findall(r"\b(?:1\d{3}|20\d{2})\b", candidate_text))
        if shared_years:
            score += 3
            reasons.append("year")
        shared_places = {token for token in location_tokens if token in candidate_text}
        if shared_places:
            score += min(3, len(shared_places))
            reasons.append("place")
        if re.search(r"\b(?:birth|bapti[sz])\b", record_text) and re.search(r"\b(?:birth|bapti[sz])\b", candidate_text):
            score += 2
        specific_bridge = bool(
            (shared_categories and (shared_years or shared_places))
            or (shared_years and shared_places)
        )
        if specific_bridge and score >= 6:
            ranked.append((score, item.get("source_quality") != "unknown", len(title), item, reasons))
    if not ranked:
        return {"title": None, "url": None, "quality": "unknown", "status": "unresolved", "reason": "No sufficiently specific citation match found."}
    _, _, _, item, reasons = max(ranked, key=lambda value: value[:3])
    source = item.get("source") or {}
    return {
        "title": source.get("title"), "url": source.get("url"), "quality": item.get("source_quality") or "unknown",
        "status": "candidate", "reason": f"Candidate matched on {', '.join(reasons)}; inspect before treating it as the underlying record.",
    }


def _reset_generated_dir(path: Path) -> None:
    """Remove only files in directories previously created by this generator."""
    if not path.exists():
        path.mkdir(parents=True)
    else:
        marker = path / GENERATED_MARKER
        if not marker.exists():
            raise RuntimeError(f"Refusing to replace unmarked directory: {path}")
        for child in sorted(path.rglob("*"), reverse=True):
            if child.is_file() or child.is_symlink():
                child.unlink()
            elif child.is_dir():
                child.rmdir()
    (path / GENERATED_MARKER).write_text("Generated; safe for the catalogue builder to replace.\n", encoding="utf-8")


def _descendant_counter(edges: list[list[str]], known: dict[str, int]):
    children = defaultdict(set)
    for parent, child in edges:
        children[parent].add(child)

    def count(profile_id: str) -> int:
        if profile_id in known:
            return int(known[profile_id])
        found, pending = set(), deque(children.get(profile_id, ()))
        while pending:
            child = pending.popleft()
            if child == profile_id or child in found:
                continue
            found.add(child)
            pending.extend(children.get(child, ()))
        return len(found)

    return count


def _estimated_birth(rows: list[dict]) -> tuple[str, str]:
    if any(str(row.get("birth_status") or "").casefold() == "unknown" for row in rows):
        return "", ""
    dated = sorted((row for row in rows if isinstance(row.get("filter_year"), (int, float))), key=lambda row: row["filter_year"])
    death_record = re.compile(r"\b(?:death|died|burial|buried|probate|will|testament|administration)\b", re.I)
    for row in dated:
        if death_record.search(row.get("association", "")):
            continue
        if re.search(r"\b(?:birth|born|bapti[sz]|christen)", f"{row.get('association', '')} {row.get('note', '')}", re.I):
            year = round(row["filter_year"])
            return f"c. {year} (estimated)", f"Estimated from a birth or baptism record ({row.get('year')})."
    for row in dated:
        context = f"{row.get('association', '')} {row.get('note', '')}"
        if death_record.search(row.get("association", "")):
            continue
        if not re.search(r"\b(?:child|children|minor|infant)\b", context, re.I):
            year = round(row["filter_year"]) - 18
            return f"c. {year} (estimated)", f"Estimated as age 18 at the earliest known adult record ({row.get('year')})."
    return "", ""


def _estimated_birth_location(rows: list[dict]) -> tuple[str, str]:
    residence = re.compile(r"\b(?:residen(?:ce|t)|household(?:er)?|occup(?:ier|ant|ied)|lease|rent|tithe|census|directory|tax|hearth|landholder|dwelling|address)\b", re.I)
    placeholder = re.compile(
        r"\b(?:location|place)\s+(?:not\s+(?:supplied|stated)|unknown)\b|"
        r"\b(?:profile\s+holding\s+point|source\s+grouping)\b|"
        r"^\s*(?:unknown|unspecified)\s*$",
        re.I,
    )
    unresolved_person = not any(_ids(row.get("profile_id", "")) for row in rows)
    for row in sorted(rows, key=lambda item: item.get("filter_year") if isinstance(item.get("filter_year"), (int, float)) else 9999):
        context = f"{row.get('subcluster', '')} {row.get('association', '')} {row.get('note', '')} {row.get('location_basis', '')}"
        source_context = f"{row.get('record_precision', '')} {row.get('source_type', '')} {row.get('source_title', '')} {context}"
        location = (row.get("record_location") or "").strip()
        if not location or placeholder.search(location) or re.search(r"\bsource\s+grouping\b", context, re.I):
            continue
        migration_context = re.search(
            r"\b(?:migration|emigrat|immigrat|destination|arrival|passenger|voyage|transatlantic)",
            context, re.I,
        )
        explicit_residence = re.search(r"\bexplicit\s+event\s+type\s+residence\b", context, re.I)
        if migration_context and not explicit_residence:
            continue
        # A court's seat or jurisdiction locates the proceeding, not the
        # litigant.  Only a separately captured, explicit residence event may
        # override that distinction.
        if re.search(r"\b(?:court|chancery|exchequer)\b|\bbill books?\b", source_context, re.I) and not explicit_residence:
            continue
        if re.search(r"\b(?:birth|born|bapti|christen)", context, re.I):
            basis = f"Estimated from the mapped birth or baptism record ({row.get('year')})."
        elif residence.search(context):
            basis = f"Estimated from the earliest mapped residence record ({row.get('year')})."
        elif not unresolved_person:
            continue
        else:
            basis = f"Estimated from the earliest mapped non-migration life event ({row.get('year')})."
        return f"{location} (estimated)", basis
    return "", ""


def _relations(profile_ids: list[str], profiles: dict[str, dict], field: str) -> list[dict]:
    found = {}
    for profile_id in profile_ids:
        meta = profiles.get(profile_id, {})
        values = meta.get(field, []) if field in {"spouses", "children"} else [meta.get(field)]
        for relation in values:
            if not relation:
                continue
            key = relation.get("id") or relation.get("name")
            if key:
                if relation.get("likely_living"):
                    public_relation = {
                        "id": "", "name": "Living person (details withheld)",
                        "withheld": True, "outside_export": False,
                    }
                else:
                    relation_id = relation.get("id", "")
                    relation_name = relation.get("name", "")
                    id_surname = relation_id.rsplit("-", 1)[0].replace("_", " ") if relation_id else ""
                    if relation_name and id_surname and not re.search(rf"\b{re.escape(id_surname)}\b", relation_name, re.I):
                        relation_name = f"{relation_name} {id_surname}"
                    public_relation = {
                        "id": relation_id, "name": relation_name,
                        "withheld": False, "outside_export": bool(relation.get("outside_export")),
                    }
                    if relation.get("data_status") not in (None, ""):
                        public_relation["data_status"] = str(relation["data_status"])
                    if relation.get("numeric_id"):
                        public_relation["numeric_id"] = relation["numeric_id"]
                    if field == "spouses":
                        public_relation["marriage_date"] = relation.get("marriage_date") or ""
                        public_relation["marriage_location"] = relation.get("marriage_location") or ""
                found.setdefault(key, public_relation)
    return sorted(found.values(), key=lambda relation: relation["name"].casefold())


def _is_external_public_url(value: str) -> bool:
    """Return whether a public citation URL leaves the project catalogue."""
    parsed = urlparse((value or "").strip())
    site_host = urlparse(SITE_URL).hostname
    return bool(
        parsed.scheme in {"http", "https"}
        and parsed.hostname
        and parsed.hostname != site_host
        and parsed.hostname not in {"localhost", "127.0.0.1", "::1"}
    )


def _source_for_record(row: dict, catalogue_id: str) -> dict:
    """Return honest provenance for every association without inventing citations."""
    source_title = (row.get("source_title") or "").strip()
    source_url = (row.get("source_url") or "").strip()
    if source_title or source_url:
        if not source_title or not source_url:
            raise ValueError(f"{catalogue_id}: source_title and source_url must be saved together")
        if not _is_external_public_url(source_url):
            raise ValueError(f"{catalogue_id}: source_url must point to the external public record: {source_url}")
        return {
            "source_title": source_title, "source_url": source_url,
            "source_type": row.get("source_type") or "explicit",
            "source_status": row.get("source_status") or "Explicit source supplied in the map dataset.",
        }
    profile_ids = _ids(row.get("profile_id", ""))
    if profile_ids:
        profile_id = profile_ids[0]
        profile_lead = "profile" in f"{row.get('evidence', '')} {row.get('association', '')}".casefold()
        return {
            "source_title": f"WikiTree profile export for {profile_id}",
            "source_url": WIKITREE_URL + quote(profile_id),
            "source_type": "profile-export" if profile_lead else "profile-provenance",
            "source_status": (
                "Tree/profile provenance only; not an independent source citation."
                if profile_lead else
                "Profile provenance link supplied; the underlying record citation is not yet transcribed in the map dataset."
            ),
        }
    return {
        "source_title": "Underlying source not yet linked",
        "source_url": "",
        "source_type": "unresolved",
        "source_status": "The original external source URL was not saved; recover it before publishing or creating a profile.",
    }


def _likely_living(metas: list[dict], rows: list[dict]) -> bool:
    return privacy_likely_living(*metas, *rows)


def _load_wikitree_evidence() -> dict:
    if not WIKITREE_PROFILE_EVIDENCE.exists():
        return {"schema_version": 1, "profiles": {}}
    payload = json.loads(WIKITREE_PROFILE_EVIDENCE.read_text(encoding="utf-8"))
    if not isinstance(payload.get("profiles"), dict):
        raise ValueError(f"Invalid WikiTree evidence data: {WIKITREE_PROFILE_EVIDENCE}")
    return payload


def _build_people(records: list[dict], profiles: dict[str, dict], edges: list[list[str]], descendant_counts: dict[str, int], wikitree_evidence: dict | None = None, profile_seed_ids: set[str] | None = None) -> list[dict]:
    privacy = privacy_from_sources(wikitree_evidence or {}, profiles)
    evidence_profiles = (wikitree_evidence or {}).get("profiles", {})
    evidence_numeric_ids = {
        str(capture.get("profile_fields", {}).get("Id")): profile_id
        for profile_id, capture in evidence_profiles.items()
        if capture.get("profile_fields", {}).get("Id")
    }

    def captured_parent_relations(profile_ids: list[str], role: str) -> list[dict]:
        """Recover newer live parents that have not reached the map export yet."""
        found = {}
        field = "Father" if role == "father" else "Mother"
        for profile_id in profile_ids:
            capture = evidence_profiles.get(profile_id, {})
            if not public_capture(capture):
                continue
            profile_fields = capture.get("profile_fields", {})
            numeric_id = str(profile_fields.get(field) or "")
            if not numeric_id or numeric_id == "0":
                continue
            relation_id = evidence_numeric_ids.get(numeric_id)
            parents = capture.get("relations", {}).get("parents", [])
            relation = next((item for item in parents if item.get("id") == relation_id), None)
            if relation is None and len(parents) == 1:
                relation = parents[0]
                relation_id = relation.get("id")
            if not relation_id:
                continue
            found[relation_id] = {
                "id": relation_id,
                "name": (relation or {}).get("name") or relation_id,
                "withheld": False,
                "outside_export": relation_id not in profiles,
                "data_status": str(profile_fields.get("DataStatus", {}).get(field) or ""),
                "numeric_id": numeric_id,
            }
        return list(found.values())
    given_name_genders = defaultdict(Counter)
    for profile in profiles.values():
        gender = profile.get("gender", "")
        for token in re.findall(r"[A-Za-zÀ-ɏ]+", profile.get("first_name", "").casefold()):
            if gender in {"Male", "Female"}:
                given_name_genders[token][gender] += 1

    def inferred_gender(name: str, rows: list[dict]) -> str:
        context = " ".join([name, *(f"{row.get('association', '')} {row.get('note', '')}" for row in rows)])
        if re.search(r"\b(?:mrs|miss|widow|wife|mother|daughter)\b", context, re.I):
            return "Female"
        if not re.search(r"\b(?:child|children|infant|minor)\b", context, re.I) and re.search(r"\b(?:mr|husband|father|son)\b", context, re.I):
            return "Male"
        for token in re.findall(r"[A-Za-zÀ-ɏ]+", name.casefold()):
            counts = given_name_genders[token]
            if counts["Male"] > counts["Female"] * 3:
                return "Male"
            if counts["Female"] > counts["Male"] * 3:
                return "Female"
        return ""

    grouped = defaultdict(list)
    for record in records:
        grouped[_individual_key(record)].append(record)
    mapped_profile_ids = {
        profile_id for rows in grouped.values()
        for row in rows for profile_id in _ids(row.get("profile_id", ""))
    }
    for profile_id in sorted(profile_seed_ids or set()):
        if profile_id in mapped_profile_ids or profile_id not in profiles:
            continue
        grouped[profile_id].append({
            "profile_id": profile_id,
            "person": profiles[profile_id].get("full_name") or profile_id,
            "family_group": "WikiTree profile update",
            "filter_year": None,
            "_profile_only": True,
        })
    count_descendants = _descendant_counter(edges, descendant_counts)
    people = []
    for key, rows in grouped.items():
        rows.sort(key=lambda row: (row.get("filter_year") if isinstance(row.get("filter_year"), (int, float)) else 9999, row.get("record_location", "")))
        profile_ids = _unique(profile_id for row in rows for profile_id in _ids(row.get("profile_id", "")))
        metas = [profiles.get(profile_id, {}) for profile_id in profile_ids]
        row_name = (rows[0].get("person") or "").strip()
        profile_name = next((meta.get("full_name") for meta in metas if meta.get("full_name")), "")
        # Some map rows use a WikiTree ID as a temporary display name.  Do not
        # let that suppress the profile's real given name in naming analysis.
        name = profile_name if WIKITREE_ID.fullmatch(row_name) and profile_name else row_name or profile_name or key

        def meta_values(field: str) -> list[str]:
            return _unique(meta.get(field, "") for meta in metas)

        def vital(kind: str) -> tuple[str, str]:
            values = _unique(_format_date(meta.get(f"{kind}_date", ""), meta.get(f"{kind}_status", "")) for meta in metas)
            if not values:
                values = _unique(_format_date(row.get(f"{kind}_date", ""), row.get(f"{kind}_status", "")) for row in rows)
            if values:
                return " / ".join(values), ""
            if kind == "birth" and any(
                str(row.get("birth_status") or "").casefold() == "unknown"
                for row in rows
            ):
                return "", ""
            return _estimated_birth(rows) if kind == "birth" else ("", "")

        birth, birth_note = vital("birth")
        death, death_note = vital("death")
        birth_locations = _unique(meta.get("birth_location", "") for meta in metas)
        if not birth_locations:
            birth_locations = _unique(row.get("birth_location", "") for row in rows)
        if birth_locations:
            birth_location, birth_location_note = " / ".join(sorted(birth_locations)), ""
        else:
            birth_location, birth_location_note = _estimated_birth_location(rows)
        death_locations = _unique(meta.get("death_location", "") for meta in metas)
        if not death_locations:
            death_locations = _unique(row.get("death_location", "") for row in rows)

        mapped_rows = [row for row in rows if not row.get("_profile_only")]
        clusters = _unique(row.get("family_group", "") for row in mapped_rows)
        cluster_counts = Counter(row.get("family_group", "") for row in rows)
        cluster = sorted(cluster_counts, key=lambda value: (-cluster_counts[value], value))[0]
        catalogue_id = _person_slug(key, rows)
        children = _relations(profile_ids, profiles, "children")
        fathers = _relations(profile_ids, profiles, "father_profile")
        mothers = _relations(profile_ids, profiles, "mother_profile")
        for relation in captured_parent_relations(profile_ids, "father"):
            if relation["id"] not in {item.get("id") for item in fathers}:
                fathers.append(relation)
        for relation in captured_parent_relations(profile_ids, "mother"):
            if relation["id"] not in {item.get("id") for item in mothers}:
                mothers.append(relation)
        derived_children_count = len(children)
        reported_counts = _unique(meta.get("profile_children_count") for meta in metas)
        has_children = any(meta.get("has_children") for meta in metas)
        outside_parent_refs = sum(relation.get("outside_export", False) for relation in fathers + mothers)
        relationship_warnings = []
        if reported_counts and derived_children_count != max(int(value) for value in reported_counts):
            relationship_warnings.append(
                f"The export reports {max(int(value) for value in reported_counts)} children but {derived_children_count} named child profiles are recoverable from this export."
            )
        elif has_children and not children:
            relationship_warnings.append("WikiTree marks this person as having children, but no named child profile is recoverable from this export.")
        if outside_parent_refs:
            relationship_warnings.append(f"{outside_parent_refs} parent reference{'s' if outside_parent_refs != 1 else ''} point outside the current export.")
        enriched_records = []
        for index, row in enumerate(rows, start=1):
            if row.get("_profile_only"):
                continue
            record = {field: row.get(field) for field in (
                "year", "filter_year", "region", "family_group", "subcluster", "evidence",
                "association", "note", "location_id", "record_location", "record_precision",
                "location_basis", "latitude", "longitude"
            )}
            record.update(_source_for_record(row, catalogue_id))
            record["record_id"] = sha1(
                f"{catalogue_id}|{index}|{record.get('year')}|{record.get('record_location')}|{record.get('association')}".encode()
            ).hexdigest()[:16]
            enriched_records.append(record)
        suffixes = _meaningful_suffixes(meta_values("suffix"))
        person = {
            "map_key": key,
            "catalogue_id": catalogue_id,
            "name": name,
            "profile_ids": profile_ids,
            "first_names": meta_values("first_name") or [name.split()[0]],
            "last_names_at_birth": meta_values("last_name_at_birth"),
            "last_names_current": meta_values("last_name_current"),
            "suffixes": suffixes,
            "has_suffix": bool(suffixes),
            "gender": next((meta.get("gender") for meta in metas if meta.get("gender")), next((row.get("gender") for row in rows if row.get("gender")), "")) or inferred_gender(name, rows),
            "birth": birth,
            "birth_note": birth_note,
            "_birth_estimate_suppressed": any(
                str(row.get("birth_status") or "").casefold() == "unknown"
                for row in rows
            ),
            "birth_location": birth_location,
            "birth_location_note": birth_location_note,
            "death": death,
            "death_note": death_note,
            "death_location": " / ".join(sorted(death_locations)),
            "spouses": _relations(profile_ids, profiles, "spouses"),
            "children": children,
            "father": fathers,
            "mother": mothers,
            "cluster": cluster,
            "clusters": sorted(clusters),
            "descendants": max((count_descendants(profile_id) for profile_id in profile_ids), default=None),
            "evidence": sorted(_unique(row.get("evidence", "") for row in rows)),
            "recorded_in": sorted(_unique(row.get("record_location", "") for row in rows)),
            "regions": sorted(_unique(row.get("region", "") for row in rows)),
            "records": enriched_records,
            "derived_children_count": derived_children_count,
            "outside_export_parent_references": outside_parent_refs,
            "relationship_warnings": relationship_warnings,
            "likely_living": _likely_living(metas, rows) or any(profile_id.casefold() in privacy.blocked for profile_id in profile_ids),
            "profile_information": [{
                "id": profile_id,
                "full_name": meta.get("full_name", ""),
                "last_name_at_birth": meta.get("last_name_at_birth", ""),
                "last_name_current": meta.get("last_name_current", ""),
                "other_surnames": meta.get("last_name_other", ""),
                "suffix": meta.get("suffix", ""),
                "created": meta.get("profile_created", ""),
                "last_updated": meta.get("profile_touched", ""),
                "connected": bool(meta.get("profile_connected")),
                "reported_children_count": meta.get("profile_children_count"),
                "ydna": bool(meta.get("ydna")),
                "audna": bool(meta.get("audna")),
            } for profile_id, meta in zip(profile_ids, metas)],
            "wikitree_evidence": [
                evidence_profiles[profile_id]
                for profile_id in profile_ids if profile_id in evidence_profiles
            ],
        }
        people.append(privacy.project(person))
    return sorted(people, key=lambda person: (person["name"].casefold(), person["birth"], person["catalogue_id"]))


def _page(
    title: str,
    description: str,
    body: str,
    canonical_path: str,
    extra_head: str = "",
    script: str = "",
    asset_prefix: str | None = None,
    brand_href: str = "/catalogue.html",
) -> str:
    if asset_prefix is None:
        asset_prefix = "../" * canonical_path.strip("/").count("/")
    html = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(title)} · Glasgow Surname Project</title>
<meta name="description" content="{escape(description, quote=True)}"><link rel="canonical" href="{SITE_URL}{canonical_path}">
<link rel="icon" href="{asset_prefix}assets/favicon.svg" type="image/svg+xml"><link rel="stylesheet" href="{asset_prefix}people/catalogue.css?v={CATALOGUE_ASSET_VERSION}">{extra_head}</head>
<body><header><a class="brand" href="{escape(brand_href, quote=True)}">Glasgow Surname Project</a><nav><a href="/map/">Map</a><a href="/catalogue.html">People</a><a href="/records/">Records</a><a href="/places/">Places</a><a href="/compare.html">Compare</a><a href="/data/index.html">Data</a></nav></header>
<main>{body}</main><footer><p>Generated from the same records as the family map. Profile fields and inferred placements are research leads unless supported by cited records.</p><p><a href="/changes.html">Change log</a> · <a href="/feedback.html">Report a correction</a> · <a href="/status.html">Catalogue status</a></p></footer><script src="{asset_prefix}people/external-links.js?v={CATALOGUE_ASSET_VERSION}"></script>{script}</body></html>"""
    if asset_prefix != "/":
        html = html.replace('href="/', f'href="{asset_prefix}').replace('src="/', f'src="{asset_prefix}')
    return with_analytics(html)


def _unified_records_page(title: str, description: str, body: str) -> str:
    """Render the records catalogue inside the maintained research shell.

    The record search remains generated here, rather than relying on the
    post-build repair, so a catalogue rebuild cannot restore its legacy page.
    """
    shell = (WEB_DIR / "sources" / "index.html").read_text(encoding="utf-8")
    shell_main = re.search(r"<main\b[\s\S]*?</main>", shell, flags=re.I)
    if not shell_main:
        raise ValueError("unified research shell has no main container")
    page = shell[:shell_main.start()] + f'<main id="main" class="r-main v3-records">{body}</main>' + shell[shell_main.end():]
    page = re.sub(r'<body\b[^>]*>', '<body data-r-integrated="3" class="g-unified g-kind-research r-v2 v3-site" data-g-path="/records/index.html" data-v3="true" data-repair="3.1-repair-1">', page, count=1, flags=re.I)
    metadata = (
        (r"<title\b[^>]*>[\s\S]*?</title>", f"<title>{escape(title)} · Glasgow</title>"),
        (r'<meta\b(?=[^>]*\bname=["\']description["\'])[^>]*>', f'<meta name="description" content="{escape(description, quote=True)}">'),
        (r'<link\b(?=[^>]*\brel=["\']canonical["\'])[^>]*>', f'<link rel="canonical" href="{SITE_URL}/records/">'),
    )
    for pattern, value in metadata:
        if re.search(pattern, page, flags=re.I):
            page = re.sub(pattern, value, page, count=1, flags=re.I)
        else:
            page = re.sub(r"</head>", value + "</head>", page, count=1, flags=re.I)
    return with_analytics(records_assets(page, WEB_DIR))


def _unified_data_page(body: str) -> str:
    """Keep the generated data guide in the site's maintained navigation shell."""
    css = WEB_DIR / "assets" / "data" / "site.css"
    css.parent.mkdir(parents=True, exist_ok=True)
    css.write_text((PROJECT_ROOT / "tools" / "data-site.css").read_text(encoding="utf-8"), encoding="utf-8")
    page = (WEB_DIR / "resources" / "index.html").read_text(encoding="utf-8")
    page = re.sub(
        r"<main\b[^>]*>[\s\S]*?</main>",
        lambda _: f'<main class="data-page" id="main">{body}</main>',
        page,
        count=1,
        flags=re.I,
    )
    page = re.sub(
        r'<body\b[^>]*>',
        '<body data-r-integrated="3" class="g-unified g-kind-about v3-site" data-g-path="/data/index.html" data-v3="true" data-repair="3.1-repair-1">',
        page,
        count=1,
        flags=re.I,
    )
    page = re.sub(r"<title\b[^>]*>[\s\S]*?</title>", "<title>Research data · Glasgow surname archive</title>", page, count=1, flags=re.I)
    page = re.sub(
        r'<meta\b(?=[^>]*\bname=["\']description["\'])[^>]*>',
        '<meta name="description" content="Machine-readable Glasgow surname research datasets and interpretation rules.">',
        page,
        count=1,
        flags=re.I,
    )
    page = page.replace('</head>', '<link rel="canonical" href="https://glasgow.phenotype.dev/data"><link rel="stylesheet" href="/assets/data/site.css"></head>', 1)
    page = page.replace(' data-g-path="/resources/index.html"', ' data-g-path="/data/index.html"', 1)
    page = page.replace('href="/about/" aria-current="page"', 'href="/about/"', 1)
    page = page.replace('href="/data/">Data &amp; downloads</a>', 'href="/data/" aria-current="page">Data &amp; downloads</a>', 1)
    page = page.replace('<strong>Research resources</strong>', '<strong>Data &amp; downloads</strong>', 1)
    return with_analytics(page)


def _preserve_unified_person_shell(existing: str, generated: str) -> str:
    """Retain the shared rail and dialogs while refreshing person content."""
    if not re.search(r'class=["\'][^"\']*\bg-rail\b', existing):
        return generated

    updated = existing
    main = re.search(r"<main\b[^>]*>[\s\S]*?</main>", generated, re.I)
    if main:
        updated = re.sub(
            r"<main\b[^>]*>[\s\S]*?</main>",
            lambda _: main.group(0),
            updated,
            count=1,
            flags=re.I,
        )

    # Keep discovery metadata current without replacing the established shell.
    for pattern in (
        r"<title\b[^>]*>[\s\S]*?</title>",
        r'<meta\b(?=[^>]*\bname=["\']description["\'])[^>]*>',
        r'<link\b(?=[^>]*\brel=["\']canonical["\'])[^>]*>',
        r'<link\b(?=[^>]*\brel=["\']alternate["\'])(?=[^>]*\btype=["\']application/json["\'])[^>]*>',
        r'<script\b(?=[^>]*\btype=["\']application/ld\+json["\'])[^>]*>[\s\S]*?</script>',
    ):
        fresh = re.search(pattern, generated, re.I)
        if not fresh:
            continue
        if re.search(pattern, updated, re.I):
            updated = re.sub(pattern, lambda _: fresh.group(0), updated, count=1, flags=re.I)
        else:
            updated = re.sub(r"</head>", fresh.group(0) + "</head>", updated, count=1, flags=re.I)
    return with_analytics(updated)


def _relation_html(relations: list[dict], id_to_slug: dict[str, str]) -> str:
    if not relations:
        return "Not recorded"
    links = []
    for relation in relations:
        profile_id, name = relation.get("id", ""), relation.get("name", "") or relation.get("id", "")
        if profile_id in id_to_slug:
            url = f"/people/{id_to_slug[profile_id]}.html"
        elif profile_id:
            url = WIKITREE_URL + quote(profile_id)
        else:
            suffix = f' <small>(numeric reference {escape(relation.get("numeric_id", ""))})</small>' if relation.get("numeric_id") else ""
            links.append(escape(name) + suffix)
            continue
        label = f'{escape(name)} <small>({escape(profile_id)})</small>' if profile_id else escape(name)
        links.append(f'<a href="{url}">{label}</a>')
    return " / ".join(links)


def _linkify_passage_text(value: str) -> str:
    parts = []
    cursor = 0
    for match in re.finditer(r'https?://[^\s<>"\']+', value or ""):
        raw_url = match.group()
        url = raw_url
        while url:
            if url[-1] in ".,;:!?":
                url = url[:-1]
            elif url[-1] == ")" and url.count("(") < url.count(")"):
                url = url[:-1]
            elif url[-1] == "]" and url.count("[") < url.count("]"):
                url = url[:-1]
            else:
                break
        parts.append(escape(value[cursor:match.start()]))
        hostname = (urlparse(url).hostname or "").lower()
        if hostname in {"example.com", "www.example.com"}:
            parts.append('<span class="placeholder-link">placeholder URL omitted</span>')
        else:
            parts.append(f'<a href="{escape(url, quote=True)}">{escape(url)}</a>')
        parts.append(escape(raw_url[len(url):]))
        cursor = match.end()
    parts.append(escape((value or "")[cursor:]))
    return "".join(parts)


def _record_passage_html(passage: str) -> str:
    starts_with_bullet = bool(re.match(r'^\s*[-#*•]\s+', passage))
    sections = [
        section.strip()
        for section in re.split(r'(?:^|[\r\n]\s*)[-#*•]\s+|\s[*•]\s+', passage.strip())
        if section.strip()
    ]
    if len(sections) <= 1:
        return f'<li>{_linkify_passage_text(passage)}</li>'
    introduction, bullets = ("", sections) if starts_with_bullet else (sections[0], sections[1:])
    bullet_rows = "".join(f'<li>{_linkify_passage_text(item)}</li>' for item in bullets)
    intro_html = f'<p class="record-passage-intro">{_linkify_passage_text(introduction)}</p>' if introduction else ""
    return f'<li>{intro_html}<ul class="record-passage-bullets">{bullet_rows}</ul></li>'


def _wikitree_evidence_html(captures: list[dict], id_to_slug: dict[str, str]) -> str:
    if not captures:
        return ""
    sections = []
    for capture in captures:
        profile_id = capture.get("profile_id", "")
        source_rows = []
        for item in capture.get("sources", []):
            links = " ".join(
                f'<a href="{escape(url, quote=True)}">source link {index}</a>'
                for index, url in enumerate(item.get("urls", []), start=1)
            )
            source_rows.append(f"<li>{escape(item.get('citation') or 'Citation text not captured')} {links}</li>")
        location_rows = "".join(
            "<tr>"
            f"<td>{escape(claim.get('event') or 'profile claim')}</td>"
            f"<td>{escape(claim.get('date') or '—')}</td>"
            f"<td>{escape(claim.get('location') or 'Not recorded')}</td>"
            f"<td>{escape(claim.get('status') or 'WikiTree profile field')}</td></tr>"
            for claim in capture.get("location_claims", [])
        )
        category_tags = " ".join(
            f'<span class="tag">{escape(category)}</span>'
            for category in capture.get("categories", [])
        )
        passage_rows = "".join(_record_passage_html(passage) for passage in capture.get("record_passages", []))
        source_urls = {url for item in capture.get("sources", []) for url in item.get("urls", [])}
        extra_urls = [
            url for url in capture.get("external_urls", [])
            if url not in source_urls
            and (urlparse(url).hostname or "").lower() not in {"example.com", "www.example.com"}
        ]
        external_rows = "".join(
            f'<li><a href="{escape(url, quote=True)}">{escape(url)}</a></li>' for url in extra_urls
        )
        relationship_rows = []
        for relation_name, relatives in capture.get("relations", {}).items():
            for relative in relatives:
                relative_id = relative.get("id", "")
                if relative_id in id_to_slug:
                    url = f"/people/{id_to_slug[relative_id]}.html"
                elif relative_id:
                    url = WIKITREE_URL + quote(relative_id)
                else:
                    url = ""
                label = escape(relative.get("name") or relative_id or "Name withheld/not returned")
                linked = f'<a href="{url}">{label}</a>' if url else label
                details = " · ".join(_unique((
                    relative.get("birth_date", ""), relative.get("birth_location", ""),
                    relative.get("death_date", ""), relative.get("death_location", ""),
                    relative.get("marriage_date", ""), relative.get("marriage_location", ""),
                )))
                relationship_rows.append(
                    f"<tr><td>{escape(relation_name.title())}</td><td>{linked}</td><td>{escape(relative_id or '—')}</td><td>{escape(details or '—')}</td></tr>"
                )
        sections.append(f"""<section class="profile-evidence"><h2>WikiTree biography, citations and relationship snapshot</h2>
<p><a href="{escape(capture.get('profile_url') or WIKITREE_URL + profile_id, quote=True)}">{escape(profile_id)}</a> was captured {escape(capture.get('captured_at') or 'date not recorded')}; WikiTree profile revision {escape(_format_profile_timestamp(capture.get('last_updated', '')) or 'unknown')}.</p>
<aside class="notice"><strong>Evidence status:</strong> {escape(capture.get('evidence_status') or 'Profile content is a research lead; inspect underlying records.')}</aside>
{f'<h3>Profile location claims</h3><div class="table-wrap"><table><thead><tr><th>Event</th><th>Date</th><th>Location</th><th>Status</th></tr></thead><tbody>{location_rows}</tbody></table></div>' if location_rows else ''}
{f'<h3>Immediate relationship snapshot</h3><div class="table-wrap"><table><thead><tr><th>Relationship</th><th>Person</th><th>WikiTree ID</th><th>Dates and places returned</th></tr></thead><tbody>{"".join(relationship_rows)}</tbody></table></div>' if relationship_rows else ''}
{f'<h3>Profile categories</h3><p>{category_tags}</p>' if category_tags else ''}
{f'<h3>Record-bearing passages</h3><ul class="record-passages">{passage_rows}</ul>' if passage_rows else ''}
<h3>Profile source citations</h3>{f'<ol>{"".join(source_rows)}</ol>' if source_rows else '<p>No structured source citation was recoverable from the profile biography.</p>'}
{f'<h3>Other external links in the profile</h3><ul>{external_rows}</ul>' if external_rows else ''}
<p class="privacy-note">Raw profile narratives are retained privately. Public citations and historical profile fields are research leads; inspect the original records.</p></section>""")
    return "".join(sections)


def _load_catalogue_profile_audit() -> dict:
    if not WIKITREE_CATALOGUE_PROFILE_AUDIT.exists():
        return {"audited_at": "", "entries": {}}
    payload = json.loads(WIKITREE_CATALOGUE_PROFILE_AUDIT.read_text(encoding="utf-8"))
    return payload if isinstance(payload.get("entries"), dict) else {"audited_at": "", "entries": {}}


def _load_catalogue_profile_links() -> dict:
    if not WIKITREE_CATALOGUE_PROFILE_LINKS.exists():
        return {}
    payload = json.loads(WIKITREE_CATALOGUE_PROFILE_LINKS.read_text(encoding="utf-8"))
    entries = payload.get("entries")
    return entries if isinstance(entries, dict) else {}


def _profile_work_status(person: dict, audit: dict) -> str:
    """Classify documentary identities without turning every record into a profile task."""
    if person.get("profile_ids"):
        return "linked_existing"
    if person.get("wikitree_free_space_url"):
        return "linked_free_space"
    action = audit.get("recommended_action")
    if action == "create_new_profile":
        return "creation_ready"
    if action == "hold":
        return "existing_profile_candidate" if audit.get("candidates") else "identity_hold"
    if action == "do_not_create" and audit.get("identity_status") in {
        "free_space_only", "pre1500_free_space_subject",
    }:
        return "free_space_only"
    return "unreviewed"


def _extract_profile_draft(audit: dict) -> str:
    relative = audit.get("draft_path") or ""
    path = (PROJECT_ROOT / relative).resolve() if relative else None
    if not path or PROJECT_ROOT not in path.parents or not path.exists():
        return ""
    text = path.read_text(encoding="utf-8")
    fenced = re.search(r"```wikitext\s*\n(.*?)\n```", text, re.S | re.I)
    if fenced:
        return fenced.group(1).strip()
    marker = re.search(r"^## Paste-ready biography\s*$", text, re.M | re.I)
    if not marker:
        # Existing-profile replacements are often stored as native WikiTree
        # text without a surrounding Markdown handoff heading.
        if "== Biography ==" in text and "== Sources ==" in text:
            return text.strip()
        return ""
    draft = text[marker.end():]
    end = re.search(r"^## (?:Duplicate audit|After creation)\s*$", draft, re.M | re.I)
    draft = (draft[:end.start()] if end else draft).strip()
    if "== Biography ==" not in draft:
        draft = (
            "{{Estimated Date}}\n[[Category:Glasgow Name Study]]\n\n== Biography ==\n\n"
            + draft
            + ("\n\n== Sources ==\n<references />" if "== Sources ==" not in draft else "")
        )
    return draft


def _is_complete_profile_draft(draft: str, profile_id: str | None = None,
                               *, subject_surname: str | None = None) -> bool:
    required = (
        "== Biography ==", "== Research Notes ==", "== Sources ==",
    )
    return (
        all(item in draft for item in required)
        and bool(re.search(r"<references\s*/\s*>", draft, re.I))
        and "<ref" in draft
        and (bool(profile_id and not profile_id.startswith(("Glasgow-", "Glasco-", "Glasgo-", "Glascow-")))
             or bool(subject_surname and not _GLASGOW_SURNAME.fullmatch(subject_surname))
             or bool(re.search(r"\[\[Category:[^\]]+\]\]", draft)))
    )


def _profile_update_significance(status: str, summary: str) -> int:
    """Rank genealogical impact, not the presence of generic action verbs."""
    text = f"{status} {summary}".casefold()
    if "urgent" in text:
        return 98
    relationship = r"(?:father|mother|parents?|son|daughter|children|brother|sister|spouse|widow|relationship)"
    if (
        re.search(rf"\b(?:record-proved|directly proved|testament-proved)\s+{relationship}\b", text)
        or re.search(rf"\b(?:directly|explicitly)\s+(?:calls|names|identifies|proves?)\b.*\b{relationship}\b", text)
        or re.search(rf"\bproves?\s+(?:both\s+)?{relationship}\b", text)
        or re.search(rf"\b(?:wrong|conflicting|incorrect|unrelated|misread)\b.{{0,40}}\b{relationship}\b", text)
        or re.search(rf"\b(?:replace|detach|remove)\s+(?:the\s+)?(?:unsupported\s+|incorrect\s+|wrong\s+|attached\s+|current\s+)?{relationship}\b", text)
        or re.search(rf"\bdirect\s+{relationship}\b", text)
    ):
        return 96
    if any(term in text for term in (
        "high impact", "family removal", "identity conflict", "conflation",
        "parents remain unknown", "unsupported parent", "unproved parent",
    )):
        return 92
    if re.search(r"\b(?:chronology|merge review|duplicate review|identity unresolved|distinguish|separate)\b", text):
        return 86
    if re.search(
        r"\b(?:correct|replace|change)\b.*\b(?:birth|baptism|death|burial|marriage|date|place|occupation)\b",
        text,
    ):
        return 82
    if re.search(r"\b(?:mark|retain|keep)\b.*\buncertain\b", text):
        return 78
    if re.search(r"\b(?:birth|baptism|death|burial|marriage|residence|occupation)\b", text):
        return 72
    if "source expansion" in text or "archive targets" in text or "citation" in text:
        return 64
    return 55


def _named_wikitree_code_link(match: re.Match) -> str:
    """Convert ``Robert `Glasgow-123``` to a labelled WikiTree link."""
    label, profile_id = match.group(1), match.group(2)
    surname = profile_id.rsplit("-", 1)[0]
    if surname.casefold() not in {token.casefold().rstrip(".") for token in label.split()}:
        label = f"{label} {surname}"
    return f"[[{profile_id}|{label}]]"


def _summary_to_wikitext(value: str) -> str:
    value = value.replace("<br>", "\n").replace("<br/>", "\n")
    value = re.sub(
        r"\b((?:[A-Z]\.|[A-Z][A-Za-z'’-]*)(?:\s+(?:[A-Z]\.|[A-Z][A-Za-z'’-]*)){0,2})\s+`([A-Za-z][A-Za-z_'’-]*-\d+)`",
        _named_wikitree_code_link,
        value,
    )
    value = re.sub(r"`([^`]+)`", r"<code>\1</code>", value)
    value = re.sub(r"\*\*([^*]+)\*\*", r"'''\1'''", value)
    value = re.sub(
        r"(?<!\[)\b([A-Za-z][A-Za-z_'’]*(?:-[A-Za-z][A-Za-z_'’]*)*-\d+)\b(?!\])",
        r"[[\1]]",
        value,
    )
    return value.strip()


def _completed_profile_summary(value: str, *, wikitext: bool = False) -> str:
    """Render a work-queue instruction as prose from an already-updated profile."""
    text = _summary_to_wikitext(value) if wikitext else value.strip()
    clauses = re.split(r"(?<=[.!?;])\s+", text)
    completed = []
    for clause in clauses:
        clause = clause.strip()
        if not clause:
            continue
        punctuation = clause[-1] if clause[-1] in ".!?;" else ""
        body = clause[:-1].strip() if punctuation else clause

        detach = re.match(r"(?i)^detach\s+(.+)$", body)
        if detach:
            target = detach.group(1)
            blank = re.match(r"^(.+?)\s+and leave (?:both )?parents blank$", target, re.I)
            if blank:
                body = f"{blank.group(1)} was detached, and the parent fields were left blank"
            else:
                split = re.match(r"^(.+?)(\s+from\s+.+)$", target, re.I)
                body = f"{split.group(1)} was detached{split.group(2)}" if split else f"{target} was detached"
        elif re.match(r"(?i)^add\s+", body):
            body = re.sub(r"(?i)^add\s+", "The profile now includes ", body)
            body = re.sub(r"(?i)\band retain\b", "and retains", body)
            body = re.sub(r"(?i)\band keep\b", "and keeps", body)
        elif re.match(r"(?i)^retain\s+", body):
            body = re.sub(r"(?i)^retain\s+", "The profile retains ", body)
        elif re.match(r"(?i)^keep\s+", body):
            body = re.sub(r"(?i)^keep\s+", "The profile retains ", body)
        elif re.match(r"(?i)^remove(?:/mark| or mark)?\s+", body):
            body = re.sub(r"(?i)^remove(?:/mark| or mark)?\s+", "The profile was revised by removing or qualifying ", body)
            body = re.sub(r"(?i)\band remove\b", "and removing", body)
            body = re.sub(r"(?i)\band mark\b", "and marking", body)
        elif re.match(r"(?i)^replace\s+", body):
            replacement = re.match(r"(?i)^replace\s+(.+?)\s+with\s+(.+)$", body)
            body = (
                f"{replacement.group(1)} was replaced with {replacement.group(2)}"
                if replacement else re.sub(r"(?i)^replace\s+", "The profile now replaces ", body)
            )
        elif re.match(r"(?i)^change\s+", body):
            change = re.match(r"(?i)^change\s+(.+?)\s+to\s+(.+)$", body)
            body = (
                f"{change.group(1)} is now recorded as {change.group(2)}"
                if change else re.sub(r"(?i)^change\s+", "The profile now records ", body)
            )
        elif re.match(r"(?i)^revise\s+", body):
            revision = re.match(r"(?i)^revise\s+(.+?)\s+to\s+(.+)$", body)
            body = (
                f"{revision.group(1)} was revised to {revision.group(2)}"
                if revision else re.sub(r"(?i)^revise\s+", "The profile now gives a revised ", body)
            )
        elif re.match(r"(?i)^mark\s+", body):
            body = re.sub(r"(?i)^mark\s+", "The profile now marks ", body)
        elif re.match(r"(?i)^correct\s+", body):
            body = re.sub(r"(?i)^correct\s+", "The profile was corrected to reflect ", body)
        elif re.match(r"(?i)^separate\s+", body):
            body = re.sub(r"(?i)^separate\s+", "The profile now treats separately ", body)
        elif re.match(r"(?i)^distinguish\s+", body):
            body = re.sub(r"(?i)^distinguish\s+", "The biography now distinguishes ", body)
        elif re.match(r"(?i)^clarify\s+", body):
            body = re.sub(r"(?i)^clarify\s+", "The biography now clarifies ", body)
        elif re.match(r"(?i)^state\s+", body):
            body = re.sub(r"(?i)^state\s+", "The biography now states ", body)
        elif re.match(r"(?i)^use\s+", body):
            body = re.sub(r"(?i)^use\s+", "The profile now uses ", body)
        elif re.match(r"(?i)^recast\s+", body):
            body = re.sub(r"(?i)^recast\s+", "The profile now presents ", body)
        elif re.match(r"(?i)^flag\s+", body):
            body = re.sub(r"(?i)^flag\s+", "The biography now flags ", body)
        elif re.match(r"(?i)^fix\s+", body):
            body = re.sub(r"(?i)^fix\s+", "The profile now corrects ", body)
        elif re.match(r"(?i)^align\s+", body):
            body = re.sub(r"(?i)^align\s+", "The profile now aligns ", body)
        elif re.match(r"(?i)^clear/mark\s+", body):
            body = re.sub(r"(?i)^clear/mark\s+", "The profile now marks as uncertain ", body)
        elif re.match(r"(?i)^retire/remove\s+", body):
            body = re.sub(r"(?i)^retire/remove\s+", "The profile was retired as ", body)
        elif re.match(r"(?i)^create/attach\s+", body):
            body = re.sub(r"(?i)^create/attach\s+", "The profile now represents and attaches ", body)
        elif re.match(r"(?i)^do not\s+", body):
            body = re.sub(r"(?i)^do not\s+", "The profile does not ", body)
        elif re.match(r"(?i)^retrieve\s+", body):
            body = re.sub(r"(?i)^retrieve\s+", "The following source still requires retrieval: ", body)
        elif re.match(r"(?i)^obtain\s+", body):
            body = re.sub(r"(?i)^obtain\s+", "The following evidence still requires retrieval: ", body)
        elif re.match(r"(?i)^inspect\s+", body):
            body = re.sub(r"(?i)^inspect\s+", "The following original still requires inspection: ", body)
        elif re.match(r"(?i)^test\s+", body):
            body = re.sub(r"(?i)^test\s+", "The following remains an open identity test: ", body)
        elif re.match(r"(?i)^search\s+", body):
            body = re.sub(r"(?i)^search\s+", "The following search remains open: ", body)

        completed.append(body[:1].upper() + body[1:] + punctuation)
    return " ".join(completed).strip()


def _current_conclusion_markdown(findings: str) -> str:
    match = re.search(
        r"^##\s+(?:Current conclusion(?:\s+and\s+tree\s+action)?|Conclusion|Current answer)\s*$\n(.*?)(?=^##\s+|\Z)",
        findings,
        re.M | re.S | re.I,
    )
    return match.group(1).strip() if match else ""


def _findings_to_wikitext(value: str) -> str:
    """Convert the small Markdown subset used in conclusions to WikiTree markup."""
    value = "\n\n".join(
        re.sub(r"\s*\n\s*", " ", paragraph).strip()
        for paragraph in re.split(r"\n\s*\n", value)
        if paragraph.strip()
    )

    def link(match: re.Match) -> str:
        label, url = match.group(1).strip(), match.group(2).strip()
        profile = re.match(r"https?://(?:www\.)?wikitree\.com/wiki/([A-Za-z][A-Za-z_'’-]*-\d+)$", url, re.I)
        if profile:
            profile_id = profile.group(1)
            label = re.sub(rf"\s*\({re.escape(profile_id)}\)\s*$", "", label).strip()
            return f"[[{profile_id}|{label}]]"
        return f"[{url} {label}]" if url.startswith(("https://", "http://")) else label

    text = re.sub(r"\[([^]]+)]\(([^)]+)\)", link, value)
    # Backticks are useful for kit numbers and record identifiers in the
    # catalogue, but a WikiTree ID must become a native profile link in text
    # copied to WikiTree. Preserve the adjacent display name as the label.
    text = re.sub(
        r"\b((?:[A-Z]\.|[A-Z][A-Za-z'’-]*)(?:\s+(?:[A-Z]\.|[A-Z][A-Za-z'’-]*)){0,2})\s+`([A-Za-z][A-Za-z_'’-]*-\d+)`",
        _named_wikitree_code_link,
        text,
    )
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"'''\1'''", text)
    text = re.sub(
        r"(?m)^([^\n.]+?) should be detached from (\[\[[^\]]+\]\])\.\s*",
        lambda match: (
            f"{match.group(2)} was previously attached as a parent of "
            f"{match.group(1).strip()}. However, the evidence reviewed here does not support that relationship. "
        ),
        text,
    )
    text = re.sub(r"\bshould be treated as\b", "is treated as", text, flags=re.I)
    text = re.sub(r"\bshould remain\b", "remains", text, flags=re.I)
    text = re.sub(r"\bshould not be described as\b", "is not described as", text, flags=re.I)
    text = re.sub(
        r"(?m)^Detach (.+?) from (.+?) unless (.+?)\.\s*",
        r"\1 was previously attached to \2. That relationship has been removed and should not be restored unless \3. ",
        text,
    )
    text = re.sub(
        r"(?m)^Detach (.+?) as (.+?)\.\s*",
        r"\1 were previously attached as \2. The evidence reviewed here does not support those relationships. ",
        text,
    )
    text = re.sub(r"(?m)^Do not merge with (.+?)\.\s*", r"This profile remains separate from \1. ", text)
    text = re.sub(r"(?m)^Do not merge (.+?) with (.+?)\.\s*", r"\1 remains separate from \2. ", text)
    text = re.sub(
        r"(?m)^Do not add (.+?) until (.+?)\.\s*",
        r"\1 has not been attached because \2 remains unresolved. ",
        text,
    )
    text = re.sub(
        r"(?m)^Keep (.+?) unconnected until (.+?)\.\s*",
        r"\1 remains unconnected pending \2. ",
        text,
    )
    text = re.sub(r"(?m)^Keep only (.+?)\.\s*", r"Only \1 are retained. ", text)
    text = re.sub(r"\b(.+?) should be removed from (.+?)\.", r"\1 has been removed from \2.", text)
    text = re.sub(r"\b(.+?) should be detached from (.+?)\.", r"\1 has been detached from \2.", text)
    text = re.sub(r"\b(.+?) should not be merged with (.+?)\.", r"\1 remains separate from \2.", text)
    text = re.sub(r"\b(.+?) should not be used to (.+?)\.", r"\1 is not used to \2.", text)
    text = re.sub(r"\bThis profile should represent\b", "This profile now represents", text, flags=re.I)

    def completed_command(match: re.Match) -> str:
        prefix, verb, obj = match.group(1), match.group(2).casefold(), match.group(3).strip()
        if ";" in prefix:
            prefix = ". "
        if verb == "remove":
            sentence = f"{obj[:1].upper() + obj[1:]} has been removed"
        elif verb == "detach":
            sentence = f"{obj[:1].upper() + obj[1:]} has been detached"
        elif verb == "replace":
            replacement = re.match(r"(.+?)\s+with\s+(.+)$", obj, re.I)
            sentence = (
                f"{replacement.group(1)} has been replaced with {replacement.group(2)}"
                if replacement else f"The profile now replaces {obj}"
            )
        elif verb == "do not":
            sentence = f"The profile does not {obj}"
        elif verb in {"keep", "retain"}:
            sentence = f"The profile retains {obj}"
        elif verb == "add":
            sentence = f"The profile now includes {obj}"
        elif verb == "correct":
            sentence = f"The profile now corrects {obj}"
        else:
            sentence = f"The profile now marks {obj}"
        return prefix + sentence + "."

    text = re.sub(
        r"(?im)(^|(?<=[.;])\s+)(Remove|Detach|Replace|Do not|Keep|Retain|Add|Correct|Mark)\s+([^\n.]+)\.",
        completed_command,
        text,
    )
    text = re.sub(r"(?m)^the\b", "The", text)
    text = re.sub(r"(?m)^this\b", "This", text)
    # "Separate testimony" is descriptive prose, not an instruction, but a
    # line-opening imperative detector cannot distinguish it. Keep the public
    # draft human-readable and unambiguous.
    text = re.sub(r"(?m)^Separate testimony\b", "Contemporary testimony", text)
    return text.strip()


def _normalise_complete_wikitree_profile(
    text: str, profile_id: str, capture: dict, *, ensure_research_notes: bool = True
) -> str:
    """Give every replacement draft a consistent, paste-ready WikiTree shape."""
    text = _normalise_ref_opening_tags(text).strip()
    # Captured biographies occasionally contain Markdown syntax.  Convert the
    # small supported forms after every merge so generated drafts remain
    # paste-ready native WikiTree text without altering the evidence wording.
    text = re.sub(
        r"\[([^\]\n]+)\]\((https?://[^)\s]+)\)",
        r"[\2 \1]",
        text,
    )
    text = re.sub(r"\*\*([^*\n]+)\*\*", r"'''\1'''", text)
    text = re.sub(r"`([^`\n]+)`", r"''\1''", text)
    text = re.sub(r"(?mi)^==+\s*Biography\s*==+\s*$", "== Biography ==", text)
    text = re.sub(r"(?mi)^==+\s*(?:Notes|Research notes)\s*==+\s*$", "== Research Notes ==", text)
    text = re.sub(r"(?mi)^==+\s*Sources\s*==+\s*$", "== Sources ==", text)

    # The One Name Study sticker is deprecated. Keep study membership through
    # the category instead; categories belong above the Biography heading.
    text = re.sub(
        r"(?mi)^\{\{One Name Study\s*\|\s*name\s*=\s*Glasgow\s*}}\s*\n?",
        "",
        text,
    ).strip()
    if profile_id.startswith(("Glasgow-", "Glasco-", "Glasgo-", "Glascow-")) and "[[Category:Glasgow Name Study]]" not in text:
        text = "[[Category:Glasgow Name Study]]\n\n" + text
    # Never expose HTML code tags around profile IDs in paste-ready WikiTree
    # biographies, including malformed material inherited from an old draft.
    text = re.sub(
        r"<code>([A-Za-z][A-Za-z_'’-]*-\d+)</code>",
        r"[[\1]]",
        text,
        flags=re.I,
    )
    data_status = (capture.get("profile_fields") or {}).get("DataStatus") or {}
    if any(data_status.get(field) == "guess" for field in ("BirthDate", "DeathDate")) and "{{Estimated Date}}" not in text:
        text = "{{Estimated Date}}\n" + text

    if not re.search(r"(?m)^== Biography ==$", text):
        first_heading = re.search(r"(?m)^==[^=].*?==\s*$", text)
        if first_heading:
            text = text[:first_heading.start()].rstrip() + "\n\n== Biography ==\n\n" + text[first_heading.start():]
        else:
            text += "\n\n== Biography =="

    if not re.search(r"(?m)^== Sources ==$", text):
        text += "\n\n== Sources ==\n\n<references />"

    if ensure_research_notes and not re.search(r"(?m)^== Research Notes ==$", text):
        text = text.replace("== Sources ==", "== Research Notes ==\n\n== Sources ==", 1)

    # Older profiles sometimes placed Research Notes after Sources. Move that
    # complete section back before Sources so the replacement reads naturally.
    sources = re.search(r"(?m)^== Sources ==\s*$", text)
    notes_matches = list(re.finditer(r"(?m)^== Research Notes ==\s*$", text))
    if sources and notes_matches and notes_matches[0].start() > sources.start():
        notes = notes_matches[0]
        following = re.search(r"(?m)^== [^=].*?==\s*$", text[notes.end():])
        notes_end = notes.end() + following.start() if following else len(text)
        notes_block = text[notes.start():notes_end].strip()
        text = (text[:notes.start()] + text[notes_end:]).strip()
        sources = re.search(r"(?m)^== Sources ==\s*$", text)
        text = text[:sources.start()].rstrip() + "\n\n" + notes_block + "\n\n" + text[sources.start():]

    text = re.sub(r"<references\s*/>", "<references />", text, flags=re.I)
    if "<references" not in text.casefold():
        text = text.replace("== Sources ==", "== Sources ==\n\n<references />", 1)
    text = re.sub(r"(?m)^\*\s+(https?://\S+)\s*$", r"* [\1 Archived or supplementary source]", text)
    text = re.sub(r"(?m)^the\b", "The", text)
    text = re.sub(r"(?m)^this\b", "This", text)
    text = re.sub(r"(?m)^Separate testimony\b", "Contemporary testimony", text)
    return text.strip()


_REF_OPEN_RE = re.compile(r"<ref\b(?P<attrs>[^>]*)>", re.I)
_REF_CLOSE_RE = re.compile(r"</ref\s*>", re.I)
_REF_NAME_RE = re.compile(
    r"\bname\s*=\s*(?P<quote>[\"'])(?P<name>[^\"']+)(?P=quote)", re.I
)


def _normalise_ref_opening_tags(text: str) -> str:
    """Keep WikiTree ``<ref>`` opening tags on one physical line."""
    return _REF_OPEN_RE.sub(
        lambda match: "<ref" + re.sub(r"\s+", " ", match.group("attrs")).rstrip() + ">",
        text,
    )


def _named_ref_parts(text: str) -> tuple[dict[str, str], dict[str, list[tuple[int, int]]]]:
    """Return named ref definitions and self-closing usage spans."""
    definitions: dict[str, str] = {}
    usages: dict[str, list[tuple[int, int]]] = defaultdict(list)
    for opening in _REF_OPEN_RE.finditer(text):
        name_match = _REF_NAME_RE.search(opening.group("attrs"))
        if not name_match:
            continue
        name = name_match.group("name")
        if opening.group("attrs").rstrip().endswith("/"):
            usages[name].append(opening.span())
            continue
        closing = _REF_CLOSE_RE.search(text, opening.end())
        if closing:
            definitions.setdefault(name, text[opening.start():closing.end()])
    return definitions, usages


def _restore_captured_named_ref_definitions(
    proposed: str, captured: str, profile_id: str
) -> str:
    """Restore definitions displaced while captured profile detail was merged.

    A definition can live in the captured Biography introduction while its
    self-closing reuses live in retained subsections. Replacing that introduction
    must not leave those later citations unresolved. Put each displaced
    definition at its first retained use, which preserves both citation content
    and its natural location in the prose.
    """
    proposed_definitions, proposed_usages = _named_ref_parts(proposed)
    missing = proposed_usages.keys() - proposed_definitions.keys()
    if not missing:
        return proposed
    captured_definitions, _ = _named_ref_parts(captured)
    unavailable = missing - captured_definitions.keys()
    if unavailable:
        raise ValueError(
            f"WikiTree update has undefined named reference(s) for {profile_id}: "
            + ", ".join(sorted(unavailable))
        )
    replacements = [
        (*proposed_usages[name][0], captured_definitions[name])
        for name in missing
    ]
    for start, end, definition in sorted(replacements, reverse=True):
        proposed = proposed[:start] + definition + proposed[end:]
    return _normalise_ref_opening_tags(proposed)


def _merge_profile_summary_with_captured(
    summary: str, captured: str, profile_id: str, capture: dict
) -> str:
    """Lead with a corrected summary without discarding the captured detail.

    Some early Irish profile drafts were deliberately concise but were
    mistakenly registered as full replacements.  For those audited cases the
    concise Biography introduction and Research Notes are the controlling
    update, while every detailed captured section remains in the paste-ready
    result.
    """
    summary = _normalise_complete_wikitree_profile(summary, profile_id, capture)
    captured = _normalise_complete_wikitree_profile(captured, profile_id, capture)

    def level_two_section(text: str, title: str) -> tuple[int, int, str]:
        heading = re.search(rf"(?m)^== {re.escape(title)} ==\s*$", text)
        if not heading:
            raise ValueError(f"WikiTree profile has no {title} section: {profile_id}")
        following = re.search(r"(?m)^== [^=].*?==\s*$", text[heading.end():])
        end = heading.end() + following.start() if following else len(text)
        return heading.start(), end, text[heading.end():end].strip()

    summary_biography_start, _, summary_biography = level_two_section(summary, "Biography")
    # A controlling summary is intentionally an introduction.  If it acquires
    # detailed Biography subsections it must be merged by hand so none vanish.
    if re.search(r"(?m)^=== [^=].*?===\s*$", summary_biography):
        raise ValueError(
            f"Captured-detail profile summary contains Biography subsections: {profile_id}"
        )

    biography_heading = re.search(r"(?m)^== Biography ==\s*$", captured)
    following_detail = re.search(
        r"(?m)^={2,3} [^=].*?={2,3}\s*$", captured[biography_heading.end():]
    )
    intro_end = (
        biography_heading.end() + following_detail.start()
        if following_detail else len(captured)
    )

    # Keep evidence-supported life-course stickers that lived inside the old
    # Biography introduction and would otherwise be displaced with its prose.
    retained_stickers = []
    for sticker in re.findall(
        r"(?m)^\{\{(?:Ireland Native|Scotland Sticker|Occupation|Migrating Ancestor)[^\n]*}}$",
        captured[biography_heading.end():intro_end],
    ):
        if sticker not in summary and sticker not in retained_stickers:
            retained_stickers.append(sticker)
    summary_prefix_lines = [
        line for line in summary[:summary_biography_start].splitlines()
        if re.match(r"^\s*(?:\[\[Category:|\{\{)", line)
        and line.strip() not in captured[:biography_heading.start()]
    ]
    controlling_intro = "\n".join([*retained_stickers, summary_biography]).strip()
    merged = (
        captured[:biography_heading.start()].rstrip()
        + ("\n" + "\n".join(summary_prefix_lines) if summary_prefix_lines else "")
        + "\n\n== Biography =="
        + "\n\n"
        + controlling_intro
        + "\n\n"
        + captured[intro_end:].lstrip()
    )

    _, _, summary_notes = level_two_section(summary, "Research Notes")
    if summary_notes:
        # Nest the concise assessment beneath one unambiguous heading.  The
        # captured detailed notes then follow unchanged for full context.
        summary_notes = re.sub(
            r"(?m)^(={3,5})([^=].*?)(={3,5})\s*$",
            lambda match: "=" + match.group(1) + match.group(2) + match.group(3) + "=",
            summary_notes,
        )
        notes_heading = re.search(r"(?m)^== Research Notes ==\s*$", merged)
        insertion = (
            "\n\n=== Current evidence assessment ===\n\n"
            + summary_notes.strip()
            + "\n"
        )
        merged = merged[:notes_heading.end()] + insertion + merged[notes_heading.end():]
    merged = _normalise_complete_wikitree_profile(merged, profile_id, capture)
    return _restore_captured_named_ref_definitions(merged, captured, profile_id)


def _source_identity_keys(text: str, extra_urls: list[str] | None = None) -> dict[str, str]:
    """Return stable identities for public sources cited in WikiTree text."""
    identities: dict[str, str] = {}
    urls = list(extra_urls or [])
    urls.extend(re.findall(r"https?://[^\s\]|}<>\"]+", text or ""))
    for raw_url in urls:
        url = raw_url.rstrip(".,;:)")
        if not url or "wikitree.com/" in url.casefold() or "example.com" in url.casefold():
            continue
        findagrave = re.search(r"findagrave\.com/memorial/(\d+)", url, re.I)
        if findagrave:
            key = f"findagrave:{findagrave.group(1)}"
        elif familysearch := re.search(r"familysearch\.org/ark:/61903/1:1:([A-Z0-9-]+)", url, re.I):
            key = f"familysearch-record:{familysearch.group(1).upper()}"
        else:
            parsed = urlparse(url)
            path = (parsed.path or "/").rstrip("/") or "/"
            key = "url:" + (parsed.netloc + path + ("?" + parsed.query if parsed.query else "")).casefold()
        identities.setdefault(key, url)
    for memorial in re.findall(r"\{\{\s*FindAGrave\s*\|\s*(\d+)", text or "", re.I):
        identities.setdefault(f"findagrave:{memorial}", f"FindAGrave memorial {memorial}")
    for ark in re.findall(r"\{\{\s*FamilySearch Record\s*\|\s*([A-Z0-9-]+)", text or "", re.I):
        identities.setdefault(f"familysearch-record:{ark.upper()}", f"FamilySearch record {ark}")
    return identities


def _registered_profile_updates(wikitree_evidence: dict) -> dict[str, dict]:
    """Turn audited OPEN and REOPEN register rows into source-backed updates."""
    if not PROFILE_UPDATE_REGISTER.exists():
        return {}
    captures = wikitree_evidence.get("profiles", {})
    entries = {}
    for line in PROFILE_UPDATE_REGISTER.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|"):
            continue
        columns = [value.strip() for value in line.strip().strip("|").split("|")]
        if len(columns) < 2:
            continue
        status_cell = columns[1].replace("**", "").strip()
        status_match = re.match(r"^(?P<state>REOPEN(?:ED)?|OPEN)\b(?P<rest>.*)$", status_cell, re.I)
        if not status_match:
            continue
        if (
            status_match.group("state").casefold() == "open"
            and status_match.group("rest").strip()
            and not status_match.group("rest").strip().startswith(("—", "-", ":"))
        ):
            continue
        profile_match = re.search(r"wikitree\.com/wiki/([A-Za-z][A-Za-z_'’-]*-\d+)", line)
        if not profile_match:
            continue
        profile_id = profile_match.group(1)
        embedded_summary = ""
        if ":" in status_cell:
            status, embedded_summary = status_cell.split(":", 1)
        else:
            status = status_cell
        summary = embedded_summary.strip() or (columns[2] if len(columns) >= 3 else "")
        draft_path = ""
        draft_wikitext = ""
        if len(columns) >= 2:
            draft_match = re.search(
                r"\[(?:Replacement draft|Complete draft)\]\(([^)]+)\)", " | ".join(columns[1:]), re.I
            )
            if draft_match:
                candidate = (PROFILE_UPDATE_REGISTER.parent / draft_match.group(1)).resolve()
                expected_dir = (RESEARCH_DIR / profile_id).resolve()
                if (
                    candidate.is_file()
                    and candidate.parent == expected_dir
                    and candidate.name == f"{profile_id}.md"
                ):
                    draft_path = str(candidate.relative_to(PROJECT_ROOT))
                    draft_wikitext = _extract_profile_draft({"draft_path": draft_path})
                    if not _is_complete_profile_draft(draft_wikitext, profile_id):
                        raise ValueError(
                            f"Catalogue replacement draft is not complete paste-ready WikiTree text: {profile_id}"
                        )
        findings_path = RESEARCH_DIR / profile_id / "findings.md"
        findings = findings_path.read_text(encoding="utf-8") if findings_path.exists() else ""
        source_links = []
        for label, url in re.findall(r"\[([^\]]+)\]\((https?://[^)]+)\)", findings):
            if "wikitree.com" in url or "glasgow.phenotype.dev" in url:
                continue
            source_links.append((label.strip(), url.strip()))
        for url in (captures.get(profile_id) or {}).get("external_urls", []):
            if "wikitree.com" in url or "glasgow.phenotype.dev" in url:
                continue
            source_links.append((urlparse(url).netloc or "Public source", url))
        unique_sources = []
        seen_urls = set()
        for label, url in source_links:
            if url in seen_urls:
                continue
            seen_urls.add(url)
            unique_sources.append((label.replace("]", ""), url))
        # A public-facing paste draft requires at least one recoverable external
        # source. Pending source-recovery cases stay in the research register.
        if not unique_sources:
            continue
        completed_summary = _completed_profile_summary(summary)
        conclusion = _findings_to_wikitext(_current_conclusion_markdown(findings))
        if not conclusion:
            conclusion = _completed_profile_summary(summary, wikitext=True)
        source_refs = "".join(
            f'<ref name="ProjectSource{number}">[{url} {label}].</ref>'
            for number, (label, url) in enumerate(unique_sources[:5], 1)
        )
        addition = (
            "=== Current research ===\n\n"
            f"{conclusion}\n\n"
            f"This assessment draws on the cited records and public source material.{source_refs}"
        )
        entries[profile_id] = {
            "significance": _profile_update_significance(status, summary),
            "summary": completed_summary,
            "work_queue_summary": summary,
            "status": status,
            "findings_path": str(findings_path.relative_to(PROJECT_ROOT)) if findings_path.exists() else "",
            "insert_before": "== Sources ==",
            # A reviewed full replacement is the paste-ready source of truth.
            # Do not silently append a second generated assessment to it.
            "addition_wikitext": "" if draft_path else addition,
            "registered_update": True,
        }
        if draft_path:
            entries[profile_id]["draft_path"] = draft_path
            entries[profile_id]["reviewed_narrative_reduction"] = True
            # Concise controlling drafts retain the detailed captured sections.
            # A deliberately marked, fully reconciled replacement stands alone;
            # source-identity preservation is still enforced by the loader.
            if "<!-- REVIEWED FULL REPLACEMENT:" not in draft_wikitext:
                entries[profile_id]["preserve_captured_detail"] = True
    return entries


def _validate_profile_preservation_review(profile_id: str, current: str, proposed: str, review: dict) -> None:
    """A previous preservation audit cannot approve changed source texts."""
    import hashlib
    for field, text in (("current_sha256", current), ("proposed_sha256", proposed)):
        digest = hashlib.sha256(text.strip().encode()).hexdigest()
        if review.get(field) != digest:
            raise ValueError(f"Profile preservation review is stale for {profile_id}: {field}; reconcile the complete biographies again")
    if not review.get('all_substantive_passages_accounted_for'):
        raise ValueError(f"Profile preservation review is incomplete for {profile_id}")


def _load_profile_updates(wikitree_evidence: dict) -> dict[str, dict]:
    """Build paste-ready biographies by applying reviewed patches to live WikiTree text."""
    if not PROFILE_UPDATE_QUEUE.exists():
        return {}
    payload = json.loads(PROFILE_UPDATE_QUEUE.read_text(encoding="utf-8"))
    captures = wikitree_evidence.get("profiles", {})
    registered_specifications = (
        _registered_profile_updates(wikitree_evidence)
        if payload.get("include_open_register")
        else {}
    )
    specifications = dict(registered_specifications)
    specifications.update(payload.get("entries", {}))
    completed_live_profiles = set(payload.get("completed_live_profiles", []))
    reopened_profiles = set(payload.get("reopened_completed_profiles", {}))
    updates = {}
    for profile_id, specification in specifications.items():
        if profile_id in completed_live_profiles and profile_id not in reopened_profiles:
            if profile_id not in registered_specifications:
                continue
            # The reviewed biography is live, but an OPEN register row can still
            # describe structured data or relationship work. Keep that task as a
            # manual update without trying to append the register prose again.
            specification = {
                **registered_specifications[profile_id],
                "manual_update": True,
                "registered_update": False,
                "addition_wikitext": "",
            }
        capture = captures.get(profile_id)
        if not capture:
            if specification.get("registered_update"):
                continue
            raise ValueError(f"Update queue profile has no captured WikiTree evidence: {profile_id}")
        manual_update = bool(specification.get("manual_update"))
        remote = (capture.get("biography_wikitext") or "").strip()
        if not remote and not specification.get("registered_update") and not manual_update:
            raise ValueError(f"Update queue profile has no captured WikiTree biography: {profile_id}")
        proposed = _extract_profile_draft(specification) if specification.get("draft_path") else remote
        if not proposed and specification.get("registered_update"):
            proposed = "[[Category:Glasgow Name Study]]\n\n== Biography =="
        if not proposed and not manual_update:
            raise ValueError(f"Update queue draft could not be loaded: {profile_id}")
        for replacement in specification.get("replacements", []):
            old = replacement.get("old") or ""
            if not old or old not in proposed:
                raise ValueError(f"Stale WikiTree update replacement for {profile_id}: {old[:80]!r}")
            proposed = proposed.replace(old, replacement.get("new") or "", 1)
        proposed = _normalise_complete_wikitree_profile(proposed, profile_id, capture)
        if specification.get("preserve_captured_detail"):
            proposed = _merge_profile_summary_with_captured(
                proposed, remote, profile_id, capture
            )
        for replacement in specification.get("post_merge_replacements", []):
            old = replacement.get("old") or ""
            if not old or old not in proposed:
                raise ValueError(
                    f"Stale post-merge WikiTree replacement for {profile_id}: {old[:80]!r}"
                )
            proposed = proposed.replace(old, replacement.get("new") or "", 1)
        addition = specification.get("addition_wikitext") or ""
        if addition:
            marker = specification.get("insert_before") or "== Sources =="
            if marker not in proposed:
                if specification.get("registered_update"):
                    proposed = proposed.rstrip() + "\n\n" + addition.strip() + "\n\n== Sources ==\n\n<references />"
                else:
                    raise ValueError(f"WikiTree update insertion marker missing for {profile_id}: {marker!r}")
            else:
                proposed = proposed.replace(marker, addition.strip() + "\n\n" + marker, 1)
        proposed = _normalise_complete_wikitree_profile(proposed, profile_id, capture)
        proposed = _restore_captured_named_ref_definitions(proposed, remote, profile_id)
        if specification.get('preservation_review_path'):
            review_path = PROJECT_ROOT / specification['preservation_review_path']
            review = json.loads(review_path.read_text())['profiles'][profile_id]
            _validate_profile_preservation_review(profile_id, remote, proposed, review)
        if specification.get("draft_path"):
            # Full replacements may reorganise or qualify citations, but must
            # never silently discard a source present on the captured profile.
            captured_sources = _source_identity_keys(
                remote, list(capture.get("external_urls") or [])
            )
            proposed_sources = _source_identity_keys(proposed)
            missing_sources = [
                captured_sources[key] for key in captured_sources.keys() - proposed_sources.keys()
            ]
            if missing_sources:
                raise ValueError(
                    f"Complete WikiTree draft drops captured source(s) for {profile_id}: "
                    + "; ".join(sorted(missing_sources))
                )
        if proposed == remote and not manual_update:
            if profile_id in reopened_profiles:
                # A later capture can show that a reopened biography amendment
                # was applied. Keep completion history without a false badge.
                continue
            raise ValueError(f"WikiTree update queue produces no change: {profile_id}")
        updates[profile_id] = {
            **specification,
            "profile_id": profile_id,
            "profile_url": capture.get("profile_url") or WIKITREE_URL + profile_id,
            "remote_wikitext": remote,
            "proposed_wikitext": proposed,
            "remote_captured_at": (
                f'{specification["biography_rechecked_at"]} (biography rechecked against the saved revision)'
                if specification.get("biography_rechecked_at") else capture.get("captured_at") or ""
            ),
            "remote_revision": _format_profile_timestamp(capture.get("last_updated", "")),
        }
        if updates[profile_id].get("work_queue_summary"):
            # A pending catalogue badge describes work still to do.  Do not
            # rewrite its imperative instruction into misleading completed
            # prose such as “The profile now includes …”.
            updates[profile_id]["summary"] = updates[profile_id]["work_queue_summary"].strip()
        elif manual_update:
            updates[profile_id]["summary"] = (updates[profile_id].get("summary") or "").strip()
        else:
            updates[profile_id]["summary"] = _completed_profile_summary(
                updates[profile_id].get("summary") or ""
            )
        ranking_text = (
            updates[profile_id].get("work_queue_summary")
            or updates[profile_id].get("summary")
            or ""
        )
        updates[profile_id]["significance"] = _profile_update_significance(
            updates[profile_id].get("status") or "", ranking_text
        )
    return updates


def catalogue_profile_update_ids() -> set[str]:
    """Return queued and reviewed research-only profiles needing catalogue metadata."""
    return set(_load_profile_updates(_load_wikitree_evidence())) | catalogue_research_case_ids()


def catalogue_research_case_ids() -> set[str]:
    path = PROJECT_ROOT / "data/wikitree/research-catalogue-cases.json"
    if not path.exists():
        return set()
    return {entry["profile_id"] for entry in json.loads(path.read_text()).get("cases", {}).values()
            if entry.get("status") == "include" and WIKITREE_ID.fullmatch(entry.get("profile_id", ""))}


def _profile_update_controls(markup: str) -> str:
    """Collapse the editor and filter the diff without changing either biography."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(markup, "html.parser")
    panel = soup.select_one('#wikitree-update')
    if panel is None:
        return markup
    if not panel.select_one('.profile-update-disclosure'):
        disclosure = soup.new_tag('details', attrs={'class': 'profile-update-disclosure'})
        summary = soup.new_tag('summary')
        summary.string = 'Paste-ready revised profile'
        disclosure.append(summary)
        for child in list(panel.contents):
            disclosure.append(child.extract())
        panel.append(disclosure)
    for scroll in panel.select('.profile-diff-scroll'):
        if scroll.find_previous_sibling(class_='profile-diff-controls'):
            continue
        controls = soup.new_tag('label', attrs={'class': 'profile-diff-controls'})
        checkbox = soup.new_tag('input', attrs={'type': 'checkbox', 'class': 'profile-diff-changes-only'})
        if scroll.select_one('.is-changed, .is-added, .is-removed'):
            checkbox['checked'] = ''
        else:
            checkbox['disabled'] = ''
        controls.append(checkbox)
        controls.append(' Changes only — hide unchanged lines')
        scroll.insert_before(controls)
        if checkbox.has_attr('disabled'):
            note = soup.new_tag('p')
            note.string = 'No biography changes in this draft.'
            scroll.insert_before(note)
    for draft in panel.select('section.profile-draft-panel'):
        draft.name = 'details'
        heading = draft.find(['h2', 'h3'])
        if heading:
            heading.name = 'summary'
        draft.attrs.pop('open', None)
    if not panel.select_one('style[data-profile-update-controls]'):
        style = soup.new_tag('style', attrs={'data-profile-update-controls': ''})
        style.string = '''.profile-update-panel>.profile-update-disclosure>summary{cursor:pointer;font-weight:700;min-height:44px;box-sizing:border-box;padding:12px}
.profile-update-panel .profile-diff-controls{display:flex;align-items:center;gap:8px;padding:12px 0;font:600 .85rem/1.5 Arial,sans-serif;cursor:pointer}
.profile-update-panel .profile-diff-controls input{width:18px;min-width:18px;height:18px;min-height:18px;margin:0}
.profile-update-panel .profile-diff-controls:has(input:checked)~.profile-diff-scroll .is-unchanged{display:none}
.profile-update-panel details.profile-draft-panel>summary{cursor:pointer;font-weight:600;padding:12px 0}'''
        panel.append(style)
    return str(soup)


def _profile_update_html(update: dict | None) -> str:
    if not update:
        return ""
    review = update.get("application_review") or {}
    review_note = (
        '<p class="workbench-audit profile-application-review"><strong>Application review, '
        + escape(str(review.get("reviewed_on") or "date not recorded"))
        + ':</strong> ' + escape(str(review.get("assessment") or "")) + '</p>'
        if review.get("assessment") else ""
    )
    if update.get("manual_update"):
        profile_id = update["profile_id"]
        captured = escape(update.get("remote_captured_at") or "date not recorded")
        revision = escape(update.get("remote_revision") or "unknown revision")
        # Manual describes how an amendment must be applied, not whether its
        # biography needs comparing. Manager-blocked drafts can differ too.
        current = update.get("remote_wikitext") or ""
        comparison = (
            '<details open><summary>Side-by-side comparison of the captured and replacement profiles</summary>'
            '<div class="profile-diff-scroll" role="region" aria-label="Scrollable profile comparison" tabindex="0">'
            + _profile_diff_html(current, update["proposed_wikitext"])
            + '</div></details>'
            if current else
            '<p class="profile-capture-note">A current biography capture is unavailable; a comparison cannot yet be shown.</p>'
        )
        return _profile_update_controls(f"""<section id="wikitree-update" class="profile-update-panel">
<div class="candidate-section-heading"><div><p class="kicker">Needs updated on WikiTree</p><h2>Manual or structured correction</h2></div><p>Significance {int(update.get('significance') or 0)}/100</p></div>
<p class="lede">{escape(update.get('summary') or '')}</p>
{review_note}
<p class="workbench-audit">Compared with <a href="{escape(update['profile_url'], quote=True)}">{escape(profile_id)}</a>, captured {captured} · {revision}. This amendment requires manual action in WikiTree; the comparison shows the saved biography and prepared replacement. Relationship, confidence and vital-field changes must be applied separately.</p>
{comparison}
<section class="profile-draft-panel"><h3>Complete WikiTree biography</h3><p>Copy this complete text if the biography needs replacing while making the structured correction. Relationship, confidence and vital-field changes must still be made separately in WikiTree's data fields.</p>
<textarea id="profile-update-draft" class="profile-draft" rows="28" readonly>{escape(update['proposed_wikitext'])}</textarea>
<div class="actions"><button id="copy-profile-update" class="button" type="button">Copy complete profile</button><a class="button secondary" href="{escape(update['profile_url'], quote=True)}">Open WikiTree profile</a></div><p id="profile-update-status" class="form-status" aria-live="polite"></p></section></section>""")
    diff_html = _profile_diff_html(
        update["remote_wikitext"], update["proposed_wikitext"]
    )
    profile_id = update["profile_id"]
    captured = escape(update.get("remote_captured_at") or "date not recorded")
    revision = escape(update.get("remote_revision") or "unknown revision")
    return _profile_update_controls(f"""<section id="wikitree-update" class="profile-update-panel">
<div class="candidate-section-heading"><div><p class="kicker">Needs updated on WikiTree</p><h2>Paste-ready revised profile</h2></div><p>Significance {int(update.get('significance') or 0)}/100</p></div>
<p class="lede">{escape(update.get('summary') or '')}</p>
{review_note}
<p class="workbench-audit">Compared with <a href="{escape(update['profile_url'], quote=True)}">{escape(profile_id)}</a>, captured {captured} · {revision}.</p>
<details open><summary>Side-by-side comparison of the live and replacement profiles</summary><div class="profile-diff-scroll" role="region" aria-label="Scrollable profile comparison" tabindex="0">{diff_html}</div></details>
<section class="profile-draft-panel"><h3>Full replacement WikiTree biography</h3><p>Copy this complete text into the WikiTree biography editor. Removed lines appear red on the left; added lines appear green on the right. Apply any structured vital or relationship correction described in the update separately in WikiTree's data fields.</p>
<textarea id="profile-update-draft" class="profile-draft" rows="28" readonly>{escape(update['proposed_wikitext'])}</textarea>
<div class="actions"><button id="copy-profile-update" class="button" type="button">Copy full revised profile</button><a class="button secondary" href="{escape(update['profile_url'], quote=True)}">Open WikiTree profile</a></div><p id="profile-update-status" class="form-status" aria-live="polite"></p></section></section>""")


def _profile_diff_html(current: str, replacement: str) -> str:
    """Render a complete, aligned two-column biography diff."""
    current_lines = str(current or "").splitlines()
    replacement_lines = str(replacement or "").splitlines()
    rows: list[tuple[str, int | None, str, int | None, str]] = []
    matcher = SequenceMatcher(None, current_lines, replacement_lines, autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for offset, (left, right) in enumerate(zip(current_lines[i1:i2], replacement_lines[j1:j2])):
                rows.append(("unchanged", i1 + offset + 1, left, j1 + offset + 1, right))
        elif tag == "delete":
            for offset, left in enumerate(current_lines[i1:i2]):
                rows.append(("removed", i1 + offset + 1, left, None, ""))
        elif tag == "insert":
            for offset, right in enumerate(replacement_lines[j1:j2]):
                rows.append(("added", None, "", j1 + offset + 1, right))
        else:  # replace: align differing lines row by row.
            width = max(i2 - i1, j2 - j1)
            for offset in range(width):
                left_number = i1 + offset + 1 if i1 + offset < i2 else None
                right_number = j1 + offset + 1 if j1 + offset < j2 else None
                left = current_lines[i1 + offset] if left_number is not None else ""
                right = replacement_lines[j1 + offset] if right_number is not None else ""
                rows.append(("changed", left_number, left, right_number, right))

    rendered = [
        '<div class="profile-update-diff" role="table" aria-label="Profile biography comparison">'
        '<div class="profile-diff-header" role="row">'
        '<span role="columnheader">Current profile</span>'
        '<span role="columnheader">Replacement profile</span></div>'
    ]
    for state, left_number, left, right_number, right in rows:
        left_label = f"Current profile, line {left_number or 'blank'}, {state}"
        right_label = f"Replacement profile, line {right_number or 'blank'}, {state}"
        rendered.append(
            f'<div class="profile-diff-row is-{state}" role="row">'
            f'<div class="profile-diff-cell" role="cell" data-label="Current profile" aria-label="{escape(left_label, quote=True)}">'
            f'<span class="profile-diff-side-label">Current profile</span>'
            f'<span class="profile-diff-line-number">{left_number or ""}</span>'
            f'<span class="profile-diff-text">{escape(left)}</span></div>'
            f'<div class="profile-diff-cell" role="cell" data-label="Replacement profile" aria-label="{escape(right_label, quote=True)}">'
            f'<span class="profile-diff-side-label">Replacement profile</span>'
            f'<span class="profile-diff-line-number">{right_number or ""}</span>'
            f'<span class="profile-diff-text">{escape(right)}</span></div></div>'
        )
    rendered.append("</div>")
    return "".join(rendered)


def _profile_creation_vital(person: dict) -> dict[str, str]:
    """Return one defensible vital field for WikiTree creation and matching."""
    if person.get("_birth_estimate_suppressed"):
        return {}
    for kind in ("birth", "death"):
        value = str(person.get(kind) or "").strip()
        match = re.search(r"\b(1\d{3}|20\d{2})\b", value)
        if not match:
            continue
        year = match.group(1)
        uncertain = bool(re.search(r"(?:\bc\.|\babout\b|\bbefore\b|\bafter\b|\bestimated\b)", value, re.I))
        if value.casefold().startswith("c."):
            value = f"about {year}"
        value = re.sub(r"\s*\(estimated\)\s*", "", value, flags=re.I).strip()
        return {
            "kind": kind.title(), "value": value,
            "status": "uncertain" if uncertain or person.get(f"{kind}_note") else "recorded",
            "basis": str(person.get(f"{kind}_note") or f"Taken from the catalogue's {kind} field."),
        }

    dated = []
    for record in person.get("records", []):
        value = record.get("filter_year")
        if not isinstance(value, (int, float)):
            match = re.search(r"\b(1\d{3}|20\d{2})\b", str(record.get("year") or ""))
            value = int(match.group(1)) if match else None
        if isinstance(value, (int, float)):
            dated.append((round(value), record))
    if not dated:
        return {}

    dated.sort(key=lambda item: item[0])
    first_year, first_record = dated[0]
    first_text = f"{first_record.get('association', '')} {first_record.get('note', '')}"
    if re.search(r"\b(?:death|died|burial|buried|probate|will|administration)\b", first_text, re.I):
        return {
            "kind": "Death", "value": f"about {first_year}", "status": "uncertain",
            "basis": f"Estimated from the earliest death or probate-related record ({first_record.get('year') or first_year}).",
        }
    if re.search(r"\b(?:child|minor|infant)\b", first_text, re.I):
        return {
            "kind": "Birth", "value": f"before or about {first_year}", "status": "uncertain",
            "basis": f"Estimated from the earliest record identifying the person as a child or minor ({first_record.get('year') or first_year}).",
        }
    return {
        "kind": "Birth", "value": f"about {first_year - 18}", "status": "uncertain",
        "basis": f"Estimated as age 18 at the earliest known adult record ({first_record.get('year') or first_year}).",
    }


def _generated_profile_draft(person: dict, audit: dict) -> str:
    lines = ["{{Estimated Date}}", "[[Category:Glasgow Name Study]]", "", "== Biography ==", ""]
    references = []
    for index, record in enumerate(person.get("records", []), start=1):
        year = record.get("year") or "date not recorded"
        place = record.get("record_location") or "an unspecified place"
        description = record.get("association") or record.get("evidence") or "a documentary occurrence"
        note = record.get("note") or "The record does not establish family relationships."
        ref_name = f"CatalogueRecord{index}"
        lines.append(
            f"'''{person['name']}''' was recorded in {year} at '''{place}''': {description}."
            f"<ref name=\"{ref_name}\" /> {note}"
        )
        source_url = record.get("source_url") or ""
        source_title = record.get("source_title") or "Underlying source not yet linked"
        if not _is_external_public_url(source_url):
            raise ValueError(
                f"{person['catalogue_id']}: cannot generate a public profile citation without an external source URL"
            )
        references.append(
            f'<ref name="{ref_name}">[{source_url} {source_title}], {year}, {description}, {place}. '
            "Inspect the linked external source and any underlying image before adding relatives.</ref>"
        )
    lines.extend(["", "== Research Notes ==", ""])
    vital = _profile_creation_vital(person)
    if vital:
        lines.append(
            f"Suggested WikiTree creation field: '''{vital['kind']}: {vital['value']}''' "
            f"({vital['status']}). {vital['basis']}"
        )
    if person.get("birth"):
        lines.append(
            f"The displayed birth value, {person['birth']}, is an adult-status estimate derived from the record chronology, not a recorded birth date."
        )
    lines.append("No parent, spouse or child should be attached unless a separate source identifies the relationship.")
    candidates = audit.get("candidates", [])
    if candidates:
        links = ", ".join(f"[[{item['profile_id']}|{item.get('name') or item['profile_id']}]]" for item in candidates)
        lines.append(f"Live WikiTree duplicate checking retained these profiles for manual comparison: {links}. They are candidates, not proved matches.")
    else:
        lines.append("No compatible profile was retained by the latest live WikiTree duplicate audit.")
    lines.extend(["", "== Sources ==", "", "<references />", "", *references])
    return "\n".join(lines).strip()


def _profile_workbench_html(person: dict, audit: dict, audited_at: str) -> str:
    if person.get("profile_ids"):
        return ""
    if person.get("wikitree_free_space_url"):
        return (
            '<section id="profile-workbench" class="profile-workbench">'
            '<div class="candidate-section-heading"><div><p class="kicker">Documentary subject</p>'
            '<h2>Canonical WikiTree Space page</h2></div>'
            '<p>This evidence is maintained on a supporting free-space page, not forced into a person profile.</p></div>'
            f'<div class="actions"><a class="button" href="{escape(person["wikitree_free_space_url"], quote=True)}">Open WikiTree Space page</a></div>'
            '</section>'
        )
    action = audit.get("recommended_action") or "needs_sourced_draft"
    candidates = audit.get("candidates", [])
    identity_note = audit.get("identity_note") or "No confirmed WikiTree profile is linked."
    if action == "hold" and not candidates and not audit.get("identity_note"):
        identity_note = "The record does not yet define a safely distinct person. Consolidate it with compatible records before considering profile creation."
    candidate_cards = "".join(
        f'<article class="profile-match-card"><div><h3><a href="{escape(item.get("url") or WIKITREE_URL + quote(item["profile_id"]), quote=True)}" target="_blank" rel="noopener noreferrer">{escape(item.get("name") or item["profile_id"])}</a></h3>'
        f'<p><strong><a href="{escape(item.get("url") or WIKITREE_URL + quote(item["profile_id"]), quote=True)}" target="_blank" rel="noopener noreferrer">{escape(item["profile_id"])}</a></strong> · {escape(item.get("birth_date") or "birth unknown")} · {escape(item.get("birth_location") or "place unknown")}</p>'
        f'<small>Automated review score {item.get("score", 0)}; compare the cited records before linking.</small></div>'
        f'<div class="profile-match-actions"><a class="button secondary" href="../compare.html?a={quote(person["catalogue_id"], safe="")}&amp;b={quote(item["profile_id"], safe="")}" target="_blank" rel="noopener">Compare with record</a></div></article>'
        for item in candidates
    )
    if audit.get("review_method"):
        reviewed = escape(audit.get("reviewed_at") or audited_at or "date not recorded")
        audit_summary = (
            f'<p class="workbench-audit"><strong>{escape(audit["review_method"])}:</strong> '
            f'reviewed {reviewed}; see the research notes for the candidate comparison.</p>'
        )
    else:
        audit_summary = (
            f'<p class="workbench-audit"><strong>Live duplicate audit:</strong> checked {escape(audited_at or "date not recorded")} '
            f'across {int(audit.get("searched_profile_count") or 0):,} exact-name or surname-variant search results.</p>'
        )
    vital = _profile_creation_vital(person)
    missing_external_sources = [
        record for record in person.get("records", [])
        if not _is_external_public_url(record.get("source_url") or "")
    ]
    draft = "" if missing_external_sources else (_extract_profile_draft(audit) or _generated_profile_draft(person, audit))
    creation_block = ""
    creation_allowed = action not in {"do_not_create", "hold", "duplicate_profiles"}
    if action == "do_not_create" and audit.get("identity_status") in {
        "free_space_only", "pre1500_free_space_subject",
    }:
        creation_block = (
            '<p class="notice"><strong>No person profile should be created.</strong> '
            f'{escape(identity_note)}</p>'
            + (
                f'<p><small>Supporting-page handoff: {escape(audit.get("draft_path"))}</small></p>'
                if audit.get("draft_path") else ""
            )
        )
    elif missing_external_sources and action != "do_not_create":
        creation_block = (
            '<p class="notice"><strong>Profile draft withheld:</strong> '
            f'{len(missing_external_sources)} mapped record source link'
            f'{"s are" if len(missing_external_sources) != 1 else " is"} missing. '
            'Recover and save the original external record URL before producing paste-ready WikiTree text.</p>'
        )
    elif action == "hold" and draft:
        creation_block = (
            '<section class="profile-draft-panel profile-draft-hold"><h3>Evidence draft — creation on HOLD</h3>'
            f'<p class="notice"><strong>Do not create or merge yet.</strong> {escape(identity_note)} '
            'This full draft identifies the documentary person and preserves the source while the candidate comparison above is resolved.</p>'
            f'<textarea class="profile-draft" rows="22" readonly>{escape(draft)}</textarea>'
            f'<p><small>Research handoff: {escape(audit.get("draft_path") or "path not recorded")}</small></p></section>'
        )
    elif creation_allowed and vital:
        warning = (
            "Review the candidate profiles above before creating a new one."
            if candidates else
            "No close candidate survived the live audit. Verify the source citation before creating the profile."
        )
        creation_block = (
            f'<section class="profile-vital-panel"><h3>Suggested WikiTree creation field</h3><dl><dt>{escape(vital["kind"])}</dt>'
            f'<dd><strong>{escape(vital["value"])}</strong> · mark as {escape(vital["status"])}<small>{escape(vital["basis"])}</small></dd></dl></section>'
            f'<section class="profile-draft-panel"><h3>Paste-ready WikiTree biography</h3><p>{escape(warning)} Use the suggested vital field above so the periodic matcher can find the finished profile.</p>'
            f'<textarea id="profile-draft" class="profile-draft" rows="22" readonly>{escape(draft)}</textarea>'
            '<div class="actions"><button id="copy-profile-draft" class="button" type="button">Copy WikiTree profile text</button></div></section>'
        )
    elif creation_allowed:
        creation_block = '<p class="notice">No defensible birth or death estimate is available, so a creation draft is withheld until a dated record is added.</p>'
    refresh_note = "" if audit.get("identity_status") == "collective_record" else """
<section class="profile-refresh-panel"><h3>Already exists or just created?</h3>
<p>No submission is needed. The periodic live WikiTree audit searches the name, suggested vital date and place; a matching profile will appear as a candidate after the next catalogue refresh.</p></section>"""
    candidate_block = (
        f'<section><h3>Possible existing profiles</h3><p>These are leads, not matches. Check locations, dates, relatives and source text.</p><div class="profile-match-list">{candidate_cards}</div></section>'
        if candidates else '<p class="empty-state">No close existing-profile candidate survived the current live audit.</p>'
    )
    return f"""<section id="profile-workbench" class="profile-workbench"><div class="candidate-section-heading"><div><p class="kicker">Duplicate-safe creation</p><h2>WikiTree profile workbench</h2></div><p>{escape(identity_note)}</p></div>
{audit_summary}{candidate_block}{creation_block}{refresh_note}<p id="profile-link-status" class="form-status" aria-live="polite"></p></section>"""


def _person_page(
    person: dict,
    dossier: dict,
    id_to_slug: dict[str, str],
    location_to_slug: dict[str, str],
    export_version: str,
    generated: str,
    profile_audit: dict | None = None,
    profile_update: dict | None = None,
) -> str:
    slug = person["catalogue_id"]
    wiki_links = " / ".join(f'<a href="{WIKITREE_URL}{quote(profile_id)}">{escape(profile_id)}</a>' for profile_id in person["profile_ids"])
    if not wiki_links and person.get("wikitree_free_space_url"):
        wiki_links = f'<a href="{escape(person["wikitree_free_space_url"], quote=True)}">Individual WikiTree Space page</a>'
    if not wiki_links:
        wiki_links = "No confirmed WikiTree destination"
    map_query = quote(person["profile_ids"][0] if person["profile_ids"] else person["name"])
    map_action = f'<a class="button" href="/map/?display=table&amp;q={map_query}">View on map</a>' if person["records"] else ""
    cluster_tags = " ".join(f'<span class="tag">{escape(cluster)}</span>' for cluster in person["clusters"])
    notes = "".join(f"<li>{escape(note)}</li>" for note in _unique((person["birth_note"], person["birth_location_note"], person["death_note"])))
    relationship_notes = "".join(f"<li>{escape(warning)}</li>" for warning in person["relationship_warnings"])
    profile_workbench = _profile_workbench_html(
        person, profile_audit or {}, (profile_audit or {}).get("_audited_at", "")
    )
    profile_update_panel = _profile_update_html(profile_update)

    finding_sections = [
        {**section, "profile_id": finding["profile_id"], "updated": finding.get("updated")}
        for finding in dossier.get("research_findings", []) for section in finding["sections"]
    ]

    def findings_html(category: str) -> str:
        blocks = []
        for finding in finding_sections:
            if finding["category"] != category:
                continue
            metadata = " · ".join(filter(None, (finding.get("profile_id"), f'updated {finding["updated"]}' if finding.get("updated") else "")))
            blocks.append(
                f'<article class="research-finding"><h3>{escape(finding["title"])}</h3>'
                f'<p class="finding-meta">{escape(metadata)}</p>{_render_findings_markdown(finding["markdown"], id_to_slug)}</article>'
            )
        return "".join(blocks)

    conclusion_findings = findings_html("conclusion")
    source_findings = findings_html("sources")
    assessment_findings = findings_html("assessment")
    action_findings = findings_html("actions")

    def compact_relation_links(group: str) -> str:
        links = []
        for relation in dossier["relationships"][group]:
            url = relation.get("url") or relation.get("wikitree_url") or ""
            name = escape(relation.get("name") or relation.get("id") or "Unknown person")
            linked = f'<a href="{escape(url, quote=True)}">{name}</a>' if url else name
            assessed = relation.get("status") or "unknown"
            certainty_key = assessed if assessed != "unknown" else relation.get("tree_status") or "unmarked"
            status_label = relation.get("status_label") if assessed != "unknown" else relation.get("tree_status_label")
            status_label = escape(status_label or "Relationship status unmarked")
            concise_status = {
                "proved": "documented", "strongly_supported": "supported", "probable": "probable",
                "possible": "uncertain", "disputed": "disputed", "contradicted": "contradicted",
                "dna_confirmed": "DNA confirmed", "confident": "confident", "uncertain": "uncertain",
                "non_biological": "non-biological", "unmarked": "unmarked",
            }.get(certainty_key, certainty_key.replace("_", " "))
            visible_status = f'<small>{escape(concise_status)}</small>' if group == "parents" else ""
            links.append(f'<span class="relation-chip relation-certainty-{escape(certainty_key)}" title="{status_label}">{linked}{visible_status}</span>')
        return "".join(links) or '<span class="not-recorded">Not recorded</span>'

    timeline_cards = []
    for record in sorted(person["records"], key=lambda item: item.get("filter_year") if isinstance(item.get("filter_year"), (int, float)) else 99999):
        place_slug = location_to_slug.get(record.get("location_id", ""))
        place_name = escape(record.get("record_location") or "Location not specified")
        place_html = f'<a href="/places/{place_slug}.html">{place_name}</a>' if place_slug else place_name
        support = _best_supporting_evidence(record, dossier)
        if support.get("url"):
            source_html = f'<a href="{escape(support["url"], quote=True)}">{escape(support.get("title") or "Supporting source")}</a>'
        elif record.get("source_url"):
            source_html = f'<a href="{escape(record["source_url"], quote=True)}">{escape(record.get("source_title") or "Source/provenance")}</a>'
        else:
            source_html = "Underlying citation not yet linked"
        timeline_cards.append(
            f'<article class="timeline-card"><div class="timeline-date">{escape(str(record.get("year") or "Undated"))}</div><div>'
            f'<h3>{escape(record.get("association") or "Recorded occurrence")}</h3><p class="timeline-place">{place_html}</p>'
            f'<p>{escape(record.get("note") or record.get("location_basis") or "No additional note.")}</p>'
            f'<div class="badge-row">{_evidence_badge(record.get("evidence") or "unknown")}{_evidence_badge(support.get("quality") or "unknown", support.get("quality") or "Source unclassified")}</div>'
            f'<details><summary>Source and mapping detail</summary><p>{source_html}</p><p>{escape(support.get("reason") or record.get("source_status") or "")}</p>'
            f'<p><strong>Precision:</strong> {escape(record.get("record_precision") or "Not specified")}</p></details></div></article>'
        )

    known_claims = [claim for claim in dossier["claims"] if claim.get("status") in {"proved", "strongly_supported"}]
    hypothesis_claims = [claim for claim in dossier["claims"] if claim.get("status") in {"possible", "probable", "disputed", "contradicted"}]
    def claim_cards(claims: list[dict]) -> str:
        cards = []
        for claim in claims:
            evidence_count = len(claim.get("evidence_ids", []))
            note_html = f'<p class="claim-note">{escape(claim["notes"])}</p>' if claim.get("notes") else ""
            cards.append(
                f'<article class="claim-card"><p>{escape(claim.get("claim") or "Unnamed claim")}</p>'
                f'<div class="badge-row">{_evidence_badge(claim.get("status") or "unknown")}'
                f'<span>{evidence_count} linked evidence item{"s" if evidence_count != 1 else ""}</span></div>'
                f'{note_html}</article>'
            )
        return "".join(cards) or '<p class="empty-state">No claims in this category have been formally assessed.</p>'

    question_cards = "".join(
        f'<article class="question-card"><h3>{escape(question.get("question") or "Open question")}</h3>'
        f'<p>{escape(question.get("current_conclusion") or "No current conclusion recorded.")}</p>'
        f'<p><strong>Missing bridge:</strong> {escape(question.get("missing_bridge") or "Not specified")}</p></article>'
        for question in dossier["open_questions"]
    ) or '<p class="empty-state">No formal open question is recorded for this person.</p>'
    lead_cards = "".join(
        f'<li><strong>{escape(lead.get("reference") or lead.get("record_type") or "Research target")}</strong> — '
        f'{escape(lead.get("question") or lead.get("reason") or "Inspect this source.")}</li>'
        for lead in dossier["research_leads"][:8]
    )
    quality_counts = Counter(item.get("source_quality") or "unknown" for item in dossier["evidence"])
    quality_summary = "".join(
        f'<div><strong>{count:,}</strong><span>{escape(quality.replace("_", " ").title())}</span></div>'
        for quality, count in sorted(quality_counts.items(), key=lambda item: (-item[1], item[0]))
    ) or '<div><strong>0</strong><span>No evidence captured</span></div>'
    source_items = []
    for source in dossier["source_summary"][:30]:
        title = escape(source.get("title") or "Untitled source")
        linked_title = f'<a href="{escape(source["url"], quote=True)}">{title}</a>' if source.get("url") else title
        source_items.append(f'<li>{_evidence_badge(source.get("source_quality") or "unknown")} {linked_title}</li>')
    source_rows = "".join(source_items)

    def fit_visual(score: int, label: str) -> str:
        label_text = label.replace("_", " ").title()
        band = (
            "high" if label in {"strong multi-factor lead", "possible duplicate", "documented parent", "supported parent"}
            else "low" if label in {"compatible household", "conflicting tree generation"} else "medium" if score >= 40 else "low"
        )
        return (
            f'<div class="fit-visual fit-{band}"><div class="fit-label"><span>Automated fit</span>'
            f'<strong>{score}/100</strong></div><div class="fit-track" role="img" '
            f'aria-label="Automated fit score {score} out of 100"><span style="width:{score}%"></span></div>'
            f'<small>{escape(label_text)}</small></div>'
        )

    similar_cards = []
    for candidate in dossier.get("similar_people", []):
        individual = f'<a href="{escape(candidate["html_url"], quote=True)}"><strong>{escape(candidate["name"])}</strong></a><small><a href="{WIKITREE_URL}{quote(candidate["id"])}">{escape(candidate["id"])}</a></small>'
        dates = f'{candidate.get("birth_year") or "?"}–{candidate.get("death_year") or "?"}'
        places = " → ".join(filter(None, (candidate.get("birth_place"), candidate.get("death_place")))) or "Places not recorded"
        reason_values = candidate.get("match_reasons", []) or ["Same-name comparison"]
        reasons = "".join(f'<li>{escape(reason)}</li>' for reason in reason_values[:3])
        all_reasons = "".join(f'<li>{escape(reason)}</li>' for reason in reason_values)
        conflicts = "; ".join(candidate.get("conflicts", [])) or "No indexed conflict"
        conflict_class = "candidate-conflict clear" if conflicts == "No indexed conflict" or "no deduction" in conflicts else "candidate-conflict"
        similar_cards.append(
            f'<article class="candidate-card duplicate-card"><div class="candidate-card-head"><div><p class="candidate-role">Same-name candidate</p>'
            f'<h4>{individual}</h4></div>{fit_visual(candidate["score"], candidate["classification"])}</div>'
            f'<div class="candidate-facts"><span><strong>Dates</strong>{escape(dates)}</span><span><strong>Places</strong>{escape(places)}</span>'
            f'<span class="wide"><strong>Parent comparison</strong>{escape(candidate.get("parent_comparison") or "No parent comparison available")}</span></div>'
            f'<div class="candidate-signals"><strong>Why it may fit</strong><ul>{reasons}</ul></div>'
            f'<p class="{conflict_class}">{escape(conflicts)}</p>'
            f'<details class="candidate-details"><summary>Full comparison detail</summary><ul>{all_reasons}</ul><p><strong>Conflicts:</strong> {escape(conflicts)}</p></details>'
            f'<div class="candidate-card-actions"><a class="button secondary" href="/compare.html?a={quote(person["profile_ids"][0] if person["profile_ids"] else slug)}&amp;b={quote(candidate["id"])}">Open side-by-side comparison</a></div></article>'
        )
    if similar_cards:
        similar_primary = "".join(similar_cards[:4])
        similar_more = "".join(similar_cards[4:])
        similar_candidates = f'<div class="candidate-card-grid similar-people-cards">{similar_primary}</div>'
        if similar_more:
            similar_candidates += (
                f'<details class="candidate-overflow"><summary>Show {len(similar_cards) - 4} lower-scoring duplicate lead(s)</summary>'
                f'<div class="candidate-card-grid">{similar_more}</div></details>'
            )
    else:
        similar_candidates = '<p class="empty-state">No sufficiently similar same-name person is currently indexed.</p>'
    parentage = dossier.get("potential_parentage", {})
    def dated_child_clue(label: str, child: dict | None) -> str:
        if not child:
            return f'<div><strong>{label}</strong><span>Not identifiable from dated child profiles</span></div>'
        name = escape(child.get("name") or "Unnamed child")
        linked = f'<a href="{escape(child["html_url"], quote=True)}">{name}</a>' if child.get("html_url") else name
        return f'<div><strong>{label}</strong><span>{linked} ({child.get("birth_year") or "date unknown"})</span></div>'

    if person.get("gender") == "Female":
        naming_labels = (
            ("Paternal grandfather position", parentage.get("earliest_dated_son")),
            ("Maternal grandfather position", parentage.get("second_dated_son")),
            ("Maternal grandmother position", parentage.get("earliest_dated_daughter")),
            ("Paternal grandmother position", parentage.get("second_dated_daughter")),
        )
    else:
        naming_labels = (
            ("Paternal grandfather position", parentage.get("earliest_dated_son")),
            ("Maternal grandfather position", parentage.get("second_dated_son")),
            ("Maternal grandmother position", parentage.get("earliest_dated_daughter")),
            ("Paternal grandmother position", parentage.get("second_dated_daughter")),
        )
    controls = parentage.get("naming_controls") or {}
    naming_sequence = (
        '<div class="subject-naming-sequence"><p class="subject-subhead">Naming sequence used by the parentage model</p><div>'
        + ''.join(dated_child_clue(label, child) for label, child in naming_labels)
        + f'</div><p class="naming-control-note">Known-position checks: {controls.get("matches", 0)} support · '
        f'{controls.get("mismatches", 0)} conflict. Ordinals retain unnamed children and recognise reused names.</p></div>'
    )
    parentage_cards = defaultdict(list)
    for candidate in parentage.get("candidates", []):
        individual = f'<a href="{escape(candidate["html_url"], quote=True)}"><strong>{escape(candidate["name"])}</strong></a>'
        if WIKITREE_ID.fullmatch(candidate["id"]):
            individual += f'<small><a href="{WIKITREE_URL}{quote(candidate["id"])}">{escape(candidate["id"])}</a></small>'
        else:
            individual += f'<small>{escape(candidate["id"])}</small>'
        dates = f'{candidate.get("birth_year") or "?"}–{candidate.get("death_year") or "?"}'
        places = " · ".join(candidate.get("locations", [])[:3]) or "No recorded location"
        candidate_factors = candidate.get("factors", [])
        indirect_factors = [value for value in candidate_factors if value not in PARENTAGE_DIRECT_TREE_DIMENSIONS]
        direct_tree_factors = [value for value in candidate_factors if value in PARENTAGE_DIRECT_TREE_DIMENSIONS]
        factors = " · ".join(str(value).replace(" chronology", "").title() for value in indirect_factors) or "Insufficient indexed detail"
        direct_tree_fact = (
            f'<span class="wide"><strong>Existing-tree context (not an independent clue)</strong>'
            f'{escape(" · ".join(str(value).title() for value in direct_tree_factors))}</span>'
            if direct_tree_factors else ""
        )
        co_parent = candidate.get("suggested_co_parent") or {}
        co_parent_fact = (
            f'<span class="wide"><strong>Same-spouse child window</strong>'
            f'<a href="{escape(co_parent.get("html_url"), quote=True)}">{escape(co_parent.get("name") or "Unknown")}</a></span>'
            if co_parent.get("html_url") else ""
        )
        reason_values = candidate.get("reasons", [])
        ranked_reasons = sorted(
            enumerate(reason_values),
            key=lambda item: (-(int((re.search(r"\(\+(\d+)\)", item[1]) or [None, "0"])[1])), item[0]),
        )
        strongest = [reason for _, reason in ranked_reasons[:3]]
        reasons = "".join(f'<li>{escape(reason)}</li>' for reason in strongest)
        all_reasons = "".join(f'<li>{escape(reason)}</li>' for reason in reason_values)
        cautions = "; ".join(candidate.get("conflicts", [])) or "No indexed conflict; documentary proof still required"
        tree_chip = (
            f'<span class="candidate-tree-chip">{escape(candidate.get("relationship_certainty") or "Currently linked in tree")}</span>'
            if candidate.get("currently_linked_parent") else ""
        )
        conflict_class = (
            "candidate-conflict clear" if not candidate.get("conflicts")
            or all("no deduction" in conflict for conflict in candidate.get("conflicts", []))
            else "candidate-conflict"
        )
        parentage_cards[candidate["role"]].append(
            f'<article class="candidate-card parentage-card"><div class="candidate-card-head"><div><p class="candidate-role">{escape(candidate["role"].title())}</p>'
            f'<h4>{individual}</h4>{tree_chip}</div>{fit_visual(candidate["score"], candidate["classification"])}</div>'
            f'<div class="candidate-facts"><span><strong>Dates</strong>{escape(dates)}</span><span><strong>Generation</strong>{escape(candidate.get("age_gap_label") or str(candidate["age_gap"]) + " years")} age gap</span>'
            f'<span class="wide"><strong>Recorded places</strong>{escape(places)}</span>'
            f'<span class="wide"><strong>Independent clue breadth · {candidate.get("indirect_factor_count", len(indirect_factors))}</strong>{escape(factors)}</span>'
            f'{direct_tree_fact}'
            f'{co_parent_fact}'
            f'<span class="wide"><strong>Current relationship</strong>{escape(candidate.get("relationship_certainty") or "Not currently linked as parent")}</span></div>'
            f'<div class="candidate-signals"><strong>Strongest signals</strong><ul>{reasons}</ul></div>'
            f'<p class="{conflict_class}">{escape(cautions)}</p>'
            f'<details class="candidate-details"><summary>Show complete scoring</summary><ul>{all_reasons}</ul><p><strong>Deductions and cautions:</strong> {escape(cautions)}</p></details></article>'
        )
    if not parentage.get("children_recorded"):
        parentage_table = '<p class="empty-state">No named children are recoverable, so child-naming analysis cannot be run.</p>'
    elif not isinstance(person.get("birth"), str) or not re.search(r"\b\d{4}\b", person.get("birth", "")):
        parentage_table = '<p class="empty-state">Children are recorded, but the subject has no usable birth year for an age-gap search.</p>'
    elif not any(parentage_cards.values()):
        parentage_table = '<p class="empty-state">No candidate met the minimum age, location or family-naming threshold.</p>'
    else:
        parentage_groups = []
        for role, title in (("possible father", "Possible fathers"), ("possible mother", "Possible mothers")):
            cards = parentage_cards.get(role, [])
            if cards:
                primary_cards = "".join(cards[:2])
                more_cards = "".join(cards[2:])
                overflow = (
                    f'<details class="candidate-overflow"><summary>Show {len(cards) - 2} lower-scoring {title.lower()}</summary>'
                    f'<div class="candidate-card-grid potential-parentage-cards">{more_cards}</div></details>'
                    if more_cards else ""
                )
                parentage_groups.append(
                    f'<section class="candidate-role-group"><h4>{title}<span>{len(cards)} leads</span></h4>'
                    f'<div class="candidate-card-grid potential-parentage-cards">{primary_cards}</div>{overflow}</section>'
                )
        parentage_table = "".join(parentage_groups)
    parent_roles = {candidate.get("role") for candidate in parentage.get("candidates", [])}
    if parent_roles == {"possible father"}:
        parent_tab_label = "Potential fathers"
    elif parent_roles == {"possible mother"}:
        parent_tab_label = "Potential mothers"
    else:
        parent_tab_label = "Potential parents"
    profile_cards = "".join(
        f'<article class="profile-card"><h3><a href="{WIKITREE_URL}{quote(info["id"])}">{escape(info["id"])}</a></h3>'
        f'<p>{escape(info["full_name"] or person["name"])}</p><p>Updated {escape(_format_profile_timestamp(info["last_updated"]) or "unknown")}</p></article>'
        for info in person["profile_information"]
    )

    def disclosure(section_id: str, title: str, description: str, content: str, count_label: str = "", extra_class: str = "") -> str:
        count_html = f'<span class="disclosure-count">{escape(count_label)}</span>' if count_label else ""
        return (
            f'<details id="{section_id}" class="page-disclosure {escape(extra_class)}"><summary>'
            f'<span class="disclosure-copy"><strong>{escape(title)}</strong><small>{escape(description)}</small></span>'
            f'{count_html}<span class="disclosure-chevron" aria-hidden="true"></span></summary>'
            f'<div class="disclosure-body">{content}</div></details>'
        )

    timeline_disclosure = disclosure(
        "timeline", "Life and record timeline", "Chronological mapped occurrences and their underlying sources.",
        f'<div class="timeline">{"".join(timeline_cards) or "<p class=\"empty-state\">No mapped occurrence is available.</p>"}</div>',
        f'{len(timeline_cards)} record{"s" if len(timeline_cards) != 1 else ""}',
    )
    latest_research_disclosure = disclosure(
        "research-update", "Latest case research", "The current conclusion from the durable research case file.",
        conclusion_findings, "Updated", "research-update-disclosure",
    ) if conclusion_findings else ""
    finding_disclosure = disclosure(
        "research-findings", "Case-file source findings", "Source extracts and analysis regenerated from findings.md.",
        source_findings, f'{len([item for item in finding_sections if item["category"] == "sources"])} section(s)',
    ) if source_findings else ""
    evidence_disclosure = disclosure(
        "evidence", "Evidence assessment", "What is supported, uncertain or disputed in the current case model.",
        f'<div class="quality-summary">{quality_summary}</div><h3>Documented or strongly supported</h3><div class="claim-grid">{claim_cards(known_claims)}</div>'
        f'<h3>Working hypotheses and conflicts</h3><div class="claim-grid">{claim_cards(hypothesis_claims)}</div>'
        f'{f"<div class=\"case-assessments\"><h3>Case-file assessments</h3>{assessment_findings}</div>" if assessment_findings else ""}',
        f'{len(dossier["claims"])} claim{"s" if len(dossier["claims"]) != 1 else ""}',
    )
    questions_disclosure = disclosure(
        "questions", "Research questions", "Open problems, missing bridges and the next records to inspect.",
        f'<div class="question-grid">{question_cards}</div>'
        f'{f"<h3>Next records to inspect</h3><ol class=\"research-leads\">{lead_cards}</ol>" if lead_cards else ""}'
        f'{f"<div class=\"case-actions\"><h3>Case-file priorities and cautions</h3>{action_findings}</div>" if action_findings else ""}',
        f'{len(dossier["open_questions"])} open',
    )
    sources_disclosure = disclosure(
        "sources", "Sources and provenance", "Structured citations and source-quality classifications.",
        f'<p class="section-intro"><strong>Source or provenance:</strong> quality describes the record layer, not every conclusion drawn from it.</p>'
        f'{f"<ol class=\"source-list\">{source_rows}</ol>" if source_rows else "<p class=\"empty-state\">No structured source citation is available.</p>"}',
        f'{len(dossier["source_summary"])} source{"s" if len(dossier["source_summary"]) != 1 else ""}',
    )
    technical_disclosure = disclosure(
        "technical", "Technical profile and raw capture", "Dataset metadata, machine dossier and captured WikiTree biography.",
        f'<h3>WikiTree profile information</h3>{profile_cards}<p><small>Dataset: {escape(export_version)} · generated {escape(generated)}</small></p>'
        f'<p><a href="/people/{slug}.json">Machine-readable dossier</a></p>{_wikitree_evidence_html(person["wikitree_evidence"], id_to_slug)}',
        "Advanced",
    )

    identity_label = escape(
        " · ".join(person["profile_ids"])
        or ("Linked individual Space page" if person.get("wikitree_free_space_url") else "Unlinked documentary person")
    )
    relation_total = sum(len(dossier["relationships"][group]) for group in ("parents", "spouses", "children"))
    candidate_total = len(parentage.get("candidates", [])) + len(dossier.get("similar_people", []))
    body = f"""<nav class="crumb"><a href="/catalogue.html">Catalogue</a> / {escape(person['name'])}</nav>
<article class="person-dossier"><section class="person-hero"><div><p class="kicker">Individual research record</p><h1>{escape(person['name'])}</h1>
<p class="person-life">{escape(person['birth'] or '?')} – {escape(person['death'] or '?')}</p><p class="lede">{identity_label} · {len(person['records'])} mapped association{'s' if len(person['records']) != 1 else ''}</p></div>
<div class="person-hero-summary"><span>{escape(person['birth_location'] or 'Birthplace unknown')}</span><span>→</span><span>{escape(person['death_location'] or 'Death place unknown')}</span></div></section>
<nav class="person-section-nav" aria-label="On this page"><a href="#overview">Overview</a><a href="#candidate-analysis">Compare candidates</a>{'<a href="#wikitree-update">Update WikiTree</a>' if profile_update_panel else ''}{'<a href="#profile-workbench">WikiTree profile</a>' if profile_workbench else ''}<a href="#research-stack">Research &amp; records</a></nav>
<div class="actions">{map_action}{f'<a class="button secondary" href="{WIKITREE_URL}{quote(person["profile_ids"][0])}">Open WikiTree</a>' if person['profile_ids'] else (f'<a class="button secondary" href="{escape(person["wikitree_free_space_url"], quote=True)}">Open WikiTree Space page</a>' if person.get('wikitree_free_space_url') else '')}<a class="button secondary" href="/compare.html?a={quote(person['profile_ids'][0] if person['profile_ids'] else slug)}">Compare</a><a class="button secondary" href="/feedback.html?person={quote(person['profile_ids'][0] if person['profile_ids'] else slug)}">Report a correction</a></div>
<section id="overview" class="identity-shell"><div class="identity-heading"><div><p class="kicker">At a glance</p><h2>Identity &amp; family</h2></div><p>Tree links organise the family; documentary status still varies.</p></div>
<div class="profile-stat-strip"><div><strong>{len(person['records'])}</strong><span>Mapped records</span></div><div><strong>{relation_total}</strong><span>Close relations</span></div><div><strong>{len(dossier['evidence'])}</strong><span>Evidence items</span></div><div><strong>{candidate_total}</strong><span>Candidate leads</span></div></div>
<dl class="facts identity-facts"><dt>Birth</dt><dd>{escape(person['birth'] or 'Not recorded')} · {escape(person['birth_location'] or 'Place not recorded')}</dd><dt>Death</dt><dd>{escape(person['death'] or 'Not recorded')} · {escape(person['death_location'] or 'Place not recorded')}</dd><dt>Parents</dt><dd>{compact_relation_links('parents')}</dd><dt>Spouses</dt><dd>{compact_relation_links('spouses')}</dd><dt>Children</dt><dd>{compact_relation_links('children')}</dd><dt>Gender</dt><dd>{escape(person['gender'] or 'Not recorded')}</dd><dt>WikiTree</dt><dd>{wiki_links}</dd><dt>Research clusters</dt><dd>{cluster_tags or 'None assigned'}</dd><dt>Mapped descendants</dt><dd>{person['descendants'] if person['descendants'] is not None else 'Not calculated'}</dd></dl>
<div class="identity-comparison-context"><p class="subject-subhead">Comparison context</p><p>These child positions and checks are the subject details used to rank possible parents below.</p>{naming_sequence}</div>
{f'<details class="identity-note"><summary>Estimate and relationship notes</summary><div>{f"<ul>{notes}</ul>" if notes else ""}{f"<ul>{relationship_notes}</ul>" if relationship_notes else ""}</div></details>' if notes or relationship_notes else ''}</section>
<section id="candidate-analysis" class="candidate-analysis"><div class="candidate-section-heading"><div><p class="kicker">Relationship comparison</p><h2>Potential parents or duplicates</h2></div><p>Compare scored leads with the subject details above—not proof.</p></div>
<div class="fit-legend" aria-label="Automated fit score legend"><span class="fit-high">Higher-signal lead</span><span class="fit-medium">Review carefully</span><span class="fit-low">Weak lead</span></div>
<div class="candidate-tabs" data-candidate-tabs><div class="candidate-tab-list" role="tablist" aria-label="Potential relationship comparisons">
<button id="parentage-tab" type="button" role="tab" aria-selected="true" aria-controls="potential-parentage">{parent_tab_label} <span>{len(parentage.get('candidates', []))}</span></button>
<button id="duplicates-tab" type="button" role="tab" aria-selected="false" aria-controls="similar-people" tabindex="-1">Possible duplicates <span>{len(dossier.get('similar_people', []))}</span></button></div>
<div id="potential-parentage" class="candidate-tab-panel" role="tabpanel" aria-labelledby="parentage-tab">{parentage_table}<details class="candidate-method-note"><summary>How parent leads are calculated</summary><p>{escape(parentage.get("method") or "Multiple independent clue types are compared.")}</p><p>{escape(parentage.get("warning") or "Naming patterns are clues, not evidence of parentage.")}</p></details></div>
<div id="similar-people" class="candidate-tab-panel" role="tabpanel" aria-labelledby="duplicates-tab">{similar_candidates}<details class="candidate-method-note"><summary>How duplicate leads are calculated</summary><p>Dates are eligibility gates, not merely deductions: chronologically impossible people are excluded. Dates, places, spouses, parent certainty and children's profiles and names are then compared. A high score is a prompt to inspect records, not a merge recommendation.</p></details></div></div></section>
{profile_update_panel}{profile_workbench}<section id="research-stack" class="research-stack"><div class="research-stack-heading"><p class="kicker">Open only what you need</p><h2>Research &amp; records</h2></div>{latest_research_disclosure}{timeline_disclosure}{finding_disclosure}{evidence_disclosure}{questions_disclosure}{sources_disclosure}{technical_disclosure}</section></article>"""
    schema = {"@context": "https://schema.org", "@type": "Person", "name": person["name"], "url": f"{SITE_URL}/people/{slug}.html"}
    if dossier.get("wikitree_url"):
        schema["sameAs"] = dossier["wikitree_url"]
    if person.get("gender"):
        schema["gender"] = person["gender"]
    if dossier["vitals"]["birth"]["status"] == "exact":
        schema["birthDate"] = dossier["vitals"]["birth"]["date"]
    if dossier["vitals"]["death"]["status"] == "exact":
        schema["deathDate"] = dossier["vitals"]["death"]["date"]
    if person["birth_location"]:
        schema["birthPlace"] = person["birth_location"]
    if person["death_location"]:
        schema["deathPlace"] = person["death_location"]
    schema_relations = {"parents": "parent", "spouses": "spouse", "children": "children"}
    for group, schema_key in schema_relations.items():
        values = [
            {"@type": "Person", "name": relation["name"], "url": SITE_URL + relation["url"]}
            for relation in dossier["relationships"][group]
            if relation.get("url") and relation.get("name")
            and (relation.get("tree_relationship") or relation.get("status") == "proved")
        ]
        if values:
            schema[schema_key] = values
    extra = (
        f'<link rel="alternate" type="application/json" href="{SITE_URL}/people/{slug}.json">'
        '<script type="application/ld+json">' + json.dumps(schema, ensure_ascii=False).replace("</", "<\\/") + "</script>"
    )
    return _page(
        person["name"], f"Genealogical record for {person['name']}, including family relationships, places and evidence.",
        body, f"/people/{slug}.html", extra,
        script=f'<script src="/people/candidate-tabs.js?v={CATALOGUE_ASSET_VERSION}" defer></script>' + (f'<script src="/people/profile-creation.js?v={CATALOGUE_ASSET_VERSION}" defer></script>' if profile_workbench else "") + (f'<script src="/people/profile-update.js?v={CATALOGUE_ASSET_VERSION}" defer></script>' if profile_update_panel else ""),
    )


def _people_list_page(title: str, introduction: str, people: list[dict], canonical_path: str) -> str:
    rows = "".join(
        f'<tr><td><a href="/people/{person["catalogue_id"]}.html">{escape(person["name"])}</a></td>'
        f'<td>{escape(person["birth"] or "—")}</td><td>{escape(person["death"] or "—")}</td>'
        f'<td>{escape(person["birth_location"] or "—")}</td><td>{escape(person["death_location"] or "—")}</td>'
        f'<td>{escape(" · ".join(person["recorded_in"]) or "—")}</td></tr>' for person in people
    )
    body = f"""<nav class="crumb"><a href="/catalogue.html">Catalogue</a> / {escape(title)}</nav><p class="kicker">Browse the dataset</p>
<h1>{escape(title)}</h1><p class="lede">{escape(introduction)} {len(people):,} individual{'s' if len(people) != 1 else ''}.</p>
<div class="table-wrap"><table><thead><tr><th>Person</th><th>Birth</th><th>Death</th><th>Birth location</th><th>Death location</th><th>Recorded in</th></tr></thead><tbody>{rows}</tbody></table></div>"""
    return _page(title, introduction, body, canonical_path)


def _write_assets() -> None:
    write_catalogue_css(CATALOGUE_DIR / "catalogue.css")
    (CATALOGUE_DIR / "external-links.js").write_text(
        Path(__file__).with_name("external_links.js").read_text(encoding="utf-8") + "\n",
        encoding="utf-8",
    )
    (CATALOGUE_DIR / "candidate-tabs.js").write_text(
        Path(__file__).with_name("candidate_tabs.js").read_text(encoding="utf-8") + "\n",
        encoding="utf-8",
    )
    (CATALOGUE_DIR / "profile-creation.js").write_text(
        Path(__file__).with_name("profile_creation.js").read_text(encoding="utf-8") + "\n",
        encoding="utf-8",
    )
    (CATALOGUE_DIR / "profile-update.js").write_text(
        Path(__file__).with_name("profile_update.js").read_text(encoding="utf-8") + "\n",
        encoding="utf-8",
    )


def _supporting_source_link(record: dict) -> str:
    """Render the optional source link used in place timelines."""
    url = record.get("supporting_source_url") or ""
    if not url:
        return ""
    return f'<p><a href="{escape(url, quote=True)}">Supporting source</a></p>'


def _write_place_pages(
    public_records: list[dict],
    public_people: list[dict],
    location_to_slug: dict[str, str],
) -> list[dict]:
    people_by_slug = {person["catalogue_id"]: person for person in public_people}
    grouped = defaultdict(list)
    for record in public_records:
        if record.get("location_id"):
            grouped[record["location_id"]].append(record)
    place_index = []
    for location_id, records in sorted(grouped.items()):
        slug = location_to_slug[location_id]
        name = next((record.get("record_location") for record in records if record.get("record_location")), "Location not specified")
        region = next((record.get("region") for record in records if record.get("region")), "Unspecified")
        people = {record["catalogue_id"]: people_by_slug[record["catalogue_id"]] for record in records}
        years = sorted({round(record["filter_year"]) for record in records if isinstance(record.get("filter_year"), (int, float))})
        surnames = sorted({
            surname for person in people.values()
            for surname in [*person.get("last_names_at_birth", []), *person.get("last_names_current", [])]
            if surname
        })
        unresolved_people = [
            person for person in people.values()
            if not person["profile_ids"] or any(
                re.search(r"\b(?:possible|probable|estimated|unproved|profile lead)\b", record.get("evidence", ""), re.I)
                for record in records if record["catalogue_id"] == person["catalogue_id"]
            )
        ]
        timeline = "".join(
            f'<article class="timeline-card"><div class="timeline-date">{escape(str(record.get("year") or "Undated"))}</div><div>'
            f'<h3><a href="/people/{record["catalogue_id"]}.html">{escape(record["person"])}</a></h3>'
            f'<p>{escape(record.get("association") or "Recorded occurrence")}</p><div class="badge-row">'
            f'{_evidence_badge(record.get("evidence") or "unknown")}{_evidence_badge(record.get("supporting_source_quality") or "unknown")}</div>'
            f'<details><summary>Record and source detail</summary><p>{escape(record.get("note") or "No additional note.")}</p>'
            f'{_supporting_source_link(record)}</details></div></article>'
            for record in sorted(records, key=lambda item: item.get("filter_year") if isinstance(item.get("filter_year"), (int, float)) else 99999)
        )
        people_links = "".join(
            f'<a href="/people/{person["catalogue_id"]}.html">{escape(person["name"])}</a>'
            for person in sorted(people.values(), key=lambda item: item["name"].casefold())
        )
        sources = {}
        for record in records:
            title = record.get("supporting_source_title") or record.get("source_title")
            url = record.get("supporting_source_url") or record.get("source_url")
            if title:
                sources[(title, url)] = record.get("supporting_source_quality") or "unknown"
        source_rows = "".join(
            f'<li>{_evidence_badge(quality)} {f"<a href={chr(34)}{escape(url, quote=True)}{chr(34)}>{escape(title)}</a>" if url else escape(title)}</li>'
            for (title, url), quality in list(sources.items())[:40]
        )
        unresolved_links = " · ".join(
            f'<a href="/people/{person["catalogue_id"]}.html">{escape(person["name"])}</a>' for person in unresolved_people
        ) or "No unresolved identity is flagged in the mapped associations."
        map_query = quote(name)
        body = f"""<nav class="crumb"><a href="/places/">Places</a> / {escape(name)}</nav><section class="place-hero-grid"><div><p class="kicker">Place research page</p><h1>{escape(name)}</h1><p class="lede">{escape(region)} · {len(records):,} mapped association{'s' if len(records) != 1 else ''}</p><div class="actions"><a class="button" href="/map/?display=table&amp;q={map_query}">View on map</a><a class="button secondary" href="/records/?place={quote(name)}">Search records here</a></div></div><div class="place-stats"><div class="place-stat"><strong>{len(people):,}</strong><span>People</span></div><div class="place-stat"><strong>{len(records):,}</strong><span>Associations</span></div><div class="place-stat"><strong>{years[0] if years else '—'}</strong><span>Earliest mapped year</span></div><div class="place-stat"><strong>{len(sources):,}</strong><span>Sources/provenance links</span></div></div></section>
<section><h2>People recorded here</h2><div class="place-people">{people_links}</div></section><section><h2>Catalogued surnames</h2><p>{' · '.join(escape(surname) for surname in surnames) or 'No surname metadata available.'}</p></section><section><h2>Place timeline</h2><div class="timeline">{timeline}</div></section><section><h2>Unresolved identities</h2><p>{unresolved_links}</p></section><section><h2>Relevant sources and provenance</h2>{f'<ol class="source-list">{source_rows}</ol>' if source_rows else '<p class="empty-state">No structured source is linked.</p>'}</section>"""
        place_schema = json.dumps({"@context": "https://schema.org", "@type": "Place", "name": name, "url": f"{SITE_URL}/places/{slug}.html"}, ensure_ascii=False).replace("</", "<\\/")
        (PLACES_DIR / f"{slug}.html").write_text(
            _page(name, f"Glasgow surname records and people associated with {name}.", body, f"/places/{slug}.html", f'<script type="application/ld+json">{place_schema}</script>'),
            encoding="utf-8",
        )
        place_index.append({
            "id": location_id, "slug": slug, "name": name, "region": region,
            "people": len(people), "records": len(records), "year_from": years[0] if years else None,
            "year_to": years[-1] if years else None, "surnames": surnames,
            "url": f"/places/{slug}.html",
        })
    (DATA_DIR / "places-index.json").write_text(json.dumps(place_index, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    place_body = f"""<p class="kicker">Townlands, parishes and mapped localities</p><h1>Research places</h1><p class="lede">Search {len(place_index):,} places associated with Glasgow surname people and records.</p><section class="place-search-panel"><div class="public-search-grid"><label><span>Place or surname</span><input id="place-query" type="search" placeholder="e.g. Lisnagaver, Weir or Antrim"></label><label><span>Region</span><select id="place-region"><option value="">Any region</option>{''.join(f'<option>{escape(region)}</option>' for region in sorted({place['region'] for place in place_index}))}</select></label><label><span>Earliest year</span><input id="place-from" type="number" placeholder="From"></label><label><span>Latest year</span><input id="place-to" type="number" placeholder="To"></label></div><p id="place-count" aria-live="polite">Loading places…</p></section><div id="place-results" class="place-results"></div>"""
    (PLACES_DIR / "index.html").write_text(
        _page("Research places", "Search townlands, parishes and mapped places in the Glasgow Surname Project.", place_body, "/places/", script='<script src="/places/search.js" defer></script>', asset_prefix="../"),
        encoding="utf-8",
    )
    (PLACES_DIR / "search.js").write_text(Path(__file__).with_name("place_search.js").read_text(encoding="utf-8") + "\n", encoding="utf-8")
    return place_index


def _write_record_catalog(public_records: list[dict]) -> dict[str, int]:
    records_index = [{
        key: record.get(key) for key in (
            "record_id", "catalogue_id", "person", "profile_ids", "year", "filter_year", "region",
            "record_category", "association", "note", "location_id", "record_location", "record_precision",
            "evidence", "catalogue_url", "place_url", "source_title", "source_url", "source_type",
            "source_status", "supporting_source_title", "supporting_source_url", "supporting_source_quality",
            "supporting_source_status", "supporting_source_reason",
        )
    } for record in public_records]
    (DATA_DIR / "records-index.json").write_text(json.dumps(records_index, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    status_counts = Counter(record.get("supporting_source_status") or "unresolved" for record in public_records)
    body = records_body(public_records)
    (RECORDS_DIR / "index.html").write_text(
        _unified_records_page("Research records", "Search Glasgow surname records by person, place, date and evidence quality.", body),
        encoding="utf-8",
    )
    (RECORDS_DIR / "search.js").write_text(Path(__file__).with_name("record_search.js").read_text(encoding="utf-8") + "\n", encoding="utf-8")
    return {"records": len(public_records), **{f"source_{key}": value for key, value in status_counts.items()}}


def build_comparison_index(
    dossiers: dict[str, dict], profile_audit_entries: dict[str, dict], *, privacy=None
) -> tuple[list[dict], dict[str, dict]]:
    """Return the public comparison index and compact dossier projection."""
    compare_index = sorted(({
        "id": dossier["id"], "alternate_ids": dossier.get("alternate_ids", []),
        "catalogue_id": dossier["catalogue_id"], "name": dossier["name"],
    } for dossier in dossiers.values()), key=lambda person: (person["name"].casefold(), person["id"]))
    compare_dossiers = {}
    for dossier in dossiers.values():
        relationships = {
            group: [{
                key: value
                for key in ("id", "name", "relationship", "status", "status_label", "url", "wikitree_url")
                if (value := relation.get(key)) not in (None, "")
            } for relation in relatives]
            for group, relatives in dossier.get("relationships", {}).items()
        }
        compare_dossiers[dossier["catalogue_id"]] = {
            "id": dossier["id"], "alternate_ids": dossier.get("alternate_ids", []),
            "catalogue_id": dossier["catalogue_id"], "name": dossier["name"],
            "local_url": f'people/{dossier["catalogue_id"]}.html',
            "network_url": f'people/{dossier["catalogue_id"]}.network.json',
            "vitals": dossier.get("vitals", {}),
            "identity": {
                "locations": dossier.get("identity", {}).get("locations", []),
                "research_clusters": dossier.get("identity", {}).get("research_clusters", []),
            },
            "relationships": relationships,
            "evidence": [{
                "date": item.get("date"), "source_quality": item.get("source_quality") or "unknown",
            } for item in dossier.get("evidence", [])],
            "open_question_count": len(dossier.get("open_questions", [])),
        }
    indexed_profile_ids = {
        profile_id for person in compare_index
        for profile_id in (person["id"], *person.get("alternate_ids", []))
    }
    for audit in profile_audit_entries.values():
        for candidate in audit.get("candidates", []):
            if privacy is not None:
                candidate = privacy.project(candidate)
                if candidate.get("withheld"):
                    continue
            profile_id = candidate.get("profile_id") or ""
            if not profile_id or profile_id in indexed_profile_ids:
                continue
            candidate_slug = f"external-{_slug(profile_id)}"
            birth_date = candidate.get("birth_date") or ""
            death_date = candidate.get("death_date") or ""
            locations = _unique([candidate.get("birth_location"), candidate.get("death_location")])
            compare_index.append({
                "id": profile_id, "alternate_ids": [], "catalogue_id": candidate_slug,
                "name": candidate.get("name") or profile_id,
            })
            compare_dossiers[candidate_slug] = {
                "id": profile_id, "alternate_ids": [], "catalogue_id": candidate_slug,
                "name": candidate.get("name") or profile_id,
                "local_url": "", "wikitree_url": candidate.get("url") or WIKITREE_URL + profile_id,
                "network_url": "",
                "vitals": {
                    "birth": {"date": _format_date(birth_date), "place": candidate.get("birth_location") or ""},
                    "death": {"date": _format_date(death_date), "place": candidate.get("death_location") or ""},
                },
                "identity": {"locations": locations, "research_clusters": []},
                "relationships": {"parents": [], "spouses": [], "children": [], "siblings": []},
                "evidence": [
                    {"date": value, "source_quality": "tree_only"}
                    for value in (birth_date, death_date) if _format_date(value)
                ],
                "open_question_count": 0,
            }
            indexed_profile_ids.add(profile_id)
    compare_index.sort(key=lambda person: (person["name"].casefold(), person["id"]))
    return compare_index, compare_dossiers


def write_comparison_index(
    dossiers: dict[str, dict], profile_audit_entries: dict[str, dict], *,
    output: Path = DATA_DIR / "compare-index.js", privacy=None,
) -> tuple[int, int]:
    """Write the comparison data asset without rebuilding the catalogue."""
    compare_index, compare_dossiers = build_comparison_index(
        dossiers, profile_audit_entries, privacy=privacy
    )
    compare_payload = (
        "window.glasgowCompareIndex="
        + json.dumps(compare_index, ensure_ascii=False, separators=(",", ":"))
        + ";\nwindow.glasgowCompareDossiers="
        + json.dumps(compare_dossiers, ensure_ascii=False, separators=(",", ":"))
        + ";\n"
    ).replace("</", "<\\/")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(compare_payload, encoding="utf-8")
    return len(compare_index), len(compare_dossiers)


def _write_support_pages(
    public_people: list[dict],
    public_records: list[dict],
    place_index: list[dict],
    dossiers: dict[str, dict],
    profile_audit_entries: dict[str, dict],
    generated: str,
    export_version: str,
) -> dict:
    write_comparison_index(dossiers, profile_audit_entries)
    compare_body = """<p class="kicker">Test a possible connection</p><h1>Compare two people</h1><p class="lede">Compare vital details, family links, places, research clusters and evidence summaries. Shared context is a lead, not proof of kinship.</p><section class="compare-panel"><div class="compare-fields"><label><span>First person or WikiTree ID</span><input id="compare-a" list="people-options" placeholder="Glasgow-951"></label><button id="compare-submit" type="button">Compare</button><label><span>Second person or WikiTree ID</span><input id="compare-b" list="people-options" placeholder="Glasgow-3904"></label></div><datalist id="people-options"></datalist><p id="compare-status" aria-live="polite">Loading people…</p></section><div id="compare-results" class="compare-results"></div>"""
    (WEB_DIR / "compare.html").write_text(
        _page("Compare people", "Compare two Glasgow Surname Project people and their evidence context.", compare_body, "/compare.html", script=f'<script src="/data/compare-index.js?v={CATALOGUE_ASSET_VERSION}"></script><script src="/people/compare.js?v={CATALOGUE_ASSET_VERSION}" defer></script>'),
        encoding="utf-8",
    )
    (CATALOGUE_DIR / "compare.js").write_text(Path(__file__).with_name("compare_people.js").read_text(encoding="utf-8") + "\n", encoding="utf-8")

    feedback_script = """<script>(()=>{const p=new URLSearchParams(location.search).get('person')||'';const label=document.querySelector('#feedback-person');const link=document.querySelector('#feedback-wikitree');const text=document.querySelector('#feedback-template');label.textContent=p||'No person selected';if(/^[A-Za-z][A-Za-z_'’-]*-\\d+$/.test(p)){link.href='https://www.wikitree.com/wiki/'+encodeURIComponent(p);link.hidden=false}text.value=`Catalogue person: ${p||'[person or page]'}\nCatalogue URL: ${location.href}\nCorrection requested:\n\nSource and exact reference:\n\nReason:`;document.querySelector('#feedback-copy').addEventListener('click',async()=>{await navigator.clipboard.writeText(text.value);document.querySelector('#feedback-copy').textContent='Copied'});})();</script>"""
    feedback_body = """<p class="kicker">Corrections and additional evidence</p><h1>Report a correction</h1><p class="lede">Catalogue entry: <strong id="feedback-person">No person selected</strong></p><section><h2>Profile correction</h2><p>If the person has a WikiTree profile, add the sourced correction there or contact the profile managers. That keeps the public tree and this catalogue aligned.</p><div class="actions"><a id="feedback-wikitree" class="button" href="#" hidden>Open WikiTree profile</a><a class="button secondary" href="https://www.wikitree.com/wiki/Space:Glasgow_Name_Study">Contact the Glasgow Name Study</a></div></section><section><h2>Prepare a precise report</h2><p>Include the affected claim, the correction, and an exact source reference or image location. Do not submit living-person details.</p><textarea id="feedback-template" class="feedback-template" rows="10"></textarea><p><button id="feedback-copy" class="button" type="button">Copy correction template</button></p></section>"""
    (WEB_DIR / "feedback.html").write_text(_page("Report a correction", "How to report corrections and evidence to the Glasgow Surname Project.", feedback_body, "/feedback.html", script=feedback_script), encoding="utf-8")

    changelog_path = Path(__file__).resolve().parents[1] / "data" / "catalogue-changelog.json"
    changelog = json.loads(changelog_path.read_text(encoding="utf-8")) if changelog_path.exists() else {"entries": []}
    change_sections = "".join(
        f'<article class="claim-card"><p class="kicker">{escape(entry.get("date") or "Undated")}</p><h2>{escape(entry.get("title") or "Catalogue update")}</h2><ul>{"".join(f"<li>{escape(change)}</li>" for change in entry.get("changes", []))}</ul></article>'
        for entry in changelog.get("entries", [])
    )
    changes_body = f'<p class="kicker">Release history</p><h1>Catalogue change log</h1><p class="lede">Material changes to the public research catalogue and its interpretation.</p><div class="question-grid">{change_sections or "<p>No change entries recorded.</p>"}</div>'
    (WEB_DIR / "changes.html").write_text(_page("Change log", "Changes to the Glasgow Surname Project public research catalogue.", changes_body, "/changes.html"), encoding="utf-8")

    evidence_counts = Counter(item.get("source_quality") or "unknown" for dossier in dossiers.values() for item in dossier["evidence"])
    source_counts = Counter(record.get("supporting_source_status") or "unresolved" for record in public_records)
    findings_count = sum(bool(dossier.get("research_findings")) for dossier in dossiers.values())
    duplicate_leads = len({
        tuple(sorted((dossier["id"], candidate["id"])))
        for dossier in dossiers.values() for candidate in dossier.get("similar_people", [])
        if candidate.get("classification") == "possible duplicate"
    })
    health = {
        "status": "ok", "generated": generated, "source_export": export_version,
        "counts": {"people": len(public_people), "records": len(public_records), "places": len(place_index),
                   "substantive_findings_files": findings_count, "possible_duplicate_comparisons": duplicate_leads},
        "source_links": dict(source_counts), "evidence_quality": dict(evidence_counts),
        "checks": {"living_people_withheld": True, "person_dossiers_generated": True, "record_search_generated": True, "place_pages_generated": True},
    }
    (WEB_DIR / "health.json").write_text(json.dumps(health, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    status_cards = "".join(
        f'<div class="status-card"><strong>{value:,}</strong><span>{escape(label)}</span></div>'
        for label, value in (("Historical people", len(public_people)), ("Mapped records", len(public_records)), ("Research places", len(place_index)), ("Substantive case files", findings_count), ("Possible duplicate comparisons", duplicate_leads), ("Explicit source links", source_counts.get("explicit", 0)), ("Candidate source matches", source_counts.get("candidate", 0)), ("Unresolved citations", source_counts.get("unresolved", 0)))
    )
    status_body = f'<p class="kicker">Build and provenance health</p><h1>Catalogue status</h1><p class="lede">Generated {escape(generated)} from {escape(export_version)}.</p><div class="status-grid">{status_cards}</div><section><h2>Interpretation</h2><p>Candidate citation matches are research leads awaiting inspection. The status page reports build coverage, not proof that every tree relationship is correct.</p><p><a href="/health.json">Machine-readable health report</a> · <a href="/data/source-review.csv">Source-review queue</a></p></section>'
    (WEB_DIR / "status.html").write_text(_page("Catalogue status", "Build status and source-quality coverage for the Glasgow Surname Project.", status_body, "/status.html"), encoding="utf-8")
    return health


def _write_candidate_match_worklist(dossiers: dict[str, dict]) -> dict:
    """Publish ranked unresolved parent and duplicate leads."""
    parent_matches = []
    duplicate_matches = {}

    def reason_weight(value: str) -> int:
        points = [int(match) for match in re.findall(r"\(\+(\d+)", value or "")]
        return max(points, default=0)

    def strongest_reasons(values: list[str], limit: int = 3) -> list[str]:
        unique = list(dict.fromkeys(values or ["No scoring detail recorded."]))
        ranked = sorted(
            enumerate(unique),
            key=lambda item: (-reason_weight(item[1]), item[0]),
        )
        return [value for _, value in ranked[:limit]]

    def birth_year(dossier: dict) -> int | None:
        match = re.search(r"\b(\d{3,4})\b", str(dossier.get("vitals", {}).get("birth", {}).get("date") or ""))
        return int(match.group(1)) if match else None

    def candidate_location_text(candidate: dict) -> str:
        values = candidate.get("locations", []) or [
            candidate.get("birth_place"), candidate.get("death_place"),
        ]
        if isinstance(values, str):
            values = [values]
        return " | ".join(dict.fromkeys(str(value) for value in values if value))

    for dossier in dossiers.values():
        parent_links = dossier.get("relationships", {}).get("parents", [])
        settled_parent_roles = {
            parent.get("relationship")
            for parent in parent_links
            if parent.get("relationship") in {"father", "mother"}
            and _parent_certainty(parent)[0] >= 2
        }
        eligible_parents = [
            candidate for candidate in dossier.get("potential_parentage", {}).get("candidates", [])
            if candidate.get("classification") in {
                "documented parent", "supported parent", "strong multi-factor lead", "moderate lead",
                "compatible household", "weak lead", "chronology-only fallback", "competing linked parent",
            }
            and (
                (candidate.get("role") == "possible father" and "father" not in settled_parent_roles)
                or (candidate.get("role") == "possible mother" and "mother" not in settled_parent_roles)
            )
        ]
        if eligible_parents:
            for role in ("possible father", "possible mother"):
                role_candidates = [candidate for candidate in eligible_parents if candidate.get("role") == role]
                if not role_candidates:
                    continue
                candidate = max(role_candidates, key=lambda item: (item.get("score", 0), item.get("factor_count", 0), item.get("id", "")))
                parent_matches.append({
                    "subject_id": dossier["id"], "subject_name": dossier["name"],
                    "subject_url": f'/people/{dossier["catalogue_id"]}.html',
                    "subject_year": birth_year(dossier),
                    "subject_gender": dossier.get("identity", {}).get("gender") or "",
                    "candidate_location": candidate_location_text(candidate),
                    "candidate": candidate,
                    "reasons": strongest_reasons(candidate.get("reasons", [])),
                    "conflict": (candidate.get("conflicts") or ["No indexed conflict; documentary proof still required."])[0],
                })

        for candidate in dossier.get("similar_people", []):
            if candidate.get("classification") != "possible duplicate":
                continue
            pair = tuple(sorted((dossier["id"], candidate["id"])))
            row = {
                "subject_id": dossier["id"], "subject_name": dossier["name"],
                "subject_url": f'/people/{dossier["catalogue_id"]}.html',
                "subject_year": birth_year(dossier),
                "subject_gender": dossier.get("identity", {}).get("gender") or "",
                "candidate_location": candidate_location_text(candidate),
                "candidate": candidate,
                "reasons": strongest_reasons(candidate.get("match_reasons", [])),
                "conflict": (candidate.get("conflicts") or ["No indexed conflict; inspect both profiles before merging."])[0],
            }
            current = duplicate_matches.get(pair)
            if current is None or candidate.get("score", 0) > current["candidate"].get("score", 0):
                duplicate_matches[pair] = row

    parent_matches.sort(key=lambda row: (-row["candidate"].get("score", 0), row["subject_name"].casefold(), row["candidate"]["name"].casefold()))
    strong_parent_matches = [row for row in parent_matches if row["candidate"].get("score", 0) >= 40]
    duplicate_rows = sorted(
        duplicate_matches.values(),
        key=lambda row: (-row["candidate"].get("score", 0), row["subject_name"].casefold(), row["candidate"]["name"].casefold()),
    )

    def person_link(name: str, profile_id: str, url: str) -> str:
        return (
            f'<a href="{escape(url, quote=True)}"><strong>{escape(name)}</strong></a>'
            f'<small><a href="{WIKITREE_URL}{quote(profile_id)}">{escape(profile_id)}</a></small>'
        )

    def rows_html(rows: list[dict], kind: str, start: int = 1) -> str:
        def clue_list(values: list[str]) -> str:
            items = []
            for value in values:
                points = reason_weight(value)
                strength = "high" if points >= 10 else "medium" if points >= 5 else "context"
                label = "Strong" if strength == "high" else "Supporting" if strength == "medium" else "Context"
                items.append(
                    f'<li class="match-clue-{strength}"><span class="match-clue-label">{label}</span>'
                    f'<span>{escape(value)}</span></li>'
                )
            return f'<ul class="match-clue-list">{"".join(items)}</ul>'

        rendered = []
        for rank, row in enumerate(rows, start=start):
            candidate = row["candidate"]
            subject = person_link(row["subject_name"], row["subject_id"], row["subject_url"])
            other = person_link(candidate["name"], candidate["id"], candidate["html_url"])
            location_summary = " · ".join(
                value.strip() for value in (row.get("candidate_location") or "").split("|")[:2] if value.strip()
            )
            if location_summary:
                other += f'<small class="match-candidate-location">{escape(location_summary)}</small>'
            parent_role = candidate.get("role", "").replace("possible ", "") if kind == "parent" else ""
            rendered.append(
                f'<tr data-match-kind="{kind}" data-score="{candidate.get("score", 0)}" data-subject-year="{row.get("subject_year") or ""}" '
                f'data-subject-gender="{escape(row.get("subject_gender") or "", quote=True)}" '
                f'data-candidate-year="{candidate.get("birth_year") or ""}" data-candidate-location="{escape(row.get("candidate_location") or "", quote=True)}" '
                f'data-parent-role="{escape(parent_role, quote=True)}"><td class="match-rank">{rank}</td><td class="match-person">{subject}</td>'
                f'<td class="match-direction">{"→" if kind == "parent" else "↔"}</td><td class="match-person">{other}</td>'
                f'<td><span class="score-pill">{candidate.get("score", 0)}</span><small>{escape(candidate.get("classification", "lead").title())}'
                f'{" · " + escape(candidate.get("role", "").replace("possible ", "")) if kind == "parent" else ""}</small></td>'
                f'<td>{clue_list(row["reasons"])}</td><td>{escape(row["conflict"])}</td></tr>'
            )
        return "".join(rendered)

    def match_table(rows: list[dict], kind: str) -> str:
        headers = "Profile needing a parent" if kind == "parent" else "First profile"
        other = "Best potential parent" if kind == "parent" else "Possible duplicate"
        visible, remainder = rows[:60], rows[60:]
        table = (
            '<div class="table-wrap match-worklist"><table><thead><tr><th>Rank</th>'
            f'<th>{headers}</th><th></th><th>{other}</th><th>Score</th><th>Strongest clue</th><th>Main caution</th>'
            f'</tr></thead><tbody>{rows_html(visible, kind)}</tbody></table></div>'
        )
        if remainder:
            table += (
                f'<details class="match-overflow" data-kind="{"parent" if kind == "parent" else "duplicate"}"><summary>Show {len(remainder):,} more {"parentage leads" if kind == "parent" else "duplicate matches"}</summary>'
                '<div class="table-wrap match-worklist"><table><thead><tr><th>Rank</th>'
                f'<th>{headers}</th><th></th><th>{other}</th><th>Score</th><th>Strongest clue</th><th>Main caution</th>'
                f'</tr></thead><tbody>{rows_html(remainder, kind, len(visible) + 1)}</tbody></table></div></details>'
            )
        return table

    filter_script = """<script>(()=>{
const input=document.querySelector('#candidate-max-year');const scoreInput=document.querySelector('#candidate-min-score');const roleInput=document.querySelector('#candidate-parent-role');const locationInput=document.querySelector('#candidate-location');const maleInput=document.querySelector('#candidate-males-only');const clear=document.querySelector('#candidate-max-clear');
const status=document.querySelector('#candidate-filter-status');const rows=[...document.querySelectorAll('tr[data-match-kind]')];
const counts={parent:document.querySelector('#parent-match-count'),duplicate:document.querySelector('#duplicate-match-count')};
const normalise=value=>(value||'').normalize('NFKD').replace(/[\\u0300-\\u036f]/g,'').toLowerCase().trim();
const apply=()=>{const raw=input.value.trim();const max=raw===''?null:Number(raw);const valid=max!==null&&Number.isFinite(max);const minScore=Math.max(0,Number(scoreInput.value)||0);const parentRole=roleInput.value;const candidateLocation=normalise(locationInput.value);const malesOnly=maleInput.checked;
const shown={parent:0,duplicate:0};const ranks={parent:0,duplicate:0};
rows.forEach(row=>{const years=[row.dataset.subjectYear,row.dataset.candidateYear].filter(Boolean).map(Number);const roleMatch=row.dataset.matchKind!=='parent'||!parentRole||row.dataset.parentRole===parentRole;const genderMatch=!malesOnly||row.dataset.subjectGender==='Male';const locationMatch=!candidateLocation||normalise(row.dataset.candidateLocation).includes(candidateLocation);const visible=roleMatch&&genderMatch&&locationMatch&&(!valid||years.every(year=>year<=max))&&Number(row.dataset.score)>=minScore;row.hidden=!visible;if(visible){const kind=row.dataset.matchKind;shown[kind]++;row.querySelector('.match-rank').textContent=++ranks[kind]}});
Object.entries(counts).forEach(([kind,node])=>{if(node)node.textContent=shown[kind].toLocaleString()});
document.querySelectorAll('.match-overflow').forEach(details=>{const visible=details.querySelectorAll('tr[data-match-kind]:not([hidden])').length;details.hidden=visible===0;if((valid||minScore!==40||parentRole||candidateLocation||malesOnly)&&visible)details.open=true;const summary=details.querySelector('summary');if(summary)summary.textContent=`Show ${visible.toLocaleString()} more ${details.dataset.kind==='parent'?'parentage leads':'duplicate matches'}`});
const roleLabel=parentRole==='father'?' father-only':parentRole==='mother'?' mother-only':'';const genderLabel=malesOnly?' for male subjects':'';const locationLabel=candidateLocation?` with candidates recorded in “${locationInput.value.trim()}”`:'';status.textContent=`Showing ${shown.parent.toLocaleString()}${roleLabel} parentage and ${shown.duplicate.toLocaleString()} duplicate leads${genderLabel}${locationLabel}, scoring ${minScore}+${valid?` where every known birth year is ${max} or earlier`:''}. Profiles without a birth year remain visible.`;
const url=new URL(location.href);if(valid)url.searchParams.set('maxYear',String(max));else url.searchParams.delete('maxYear');if(minScore!==40)url.searchParams.set('minScore',String(minScore));else url.searchParams.delete('minScore');if(parentRole)url.searchParams.set('parentRole',parentRole);else url.searchParams.delete('parentRole');if(candidateLocation)url.searchParams.set('candidateLocation',locationInput.value.trim());else url.searchParams.delete('candidateLocation');if(malesOnly)url.searchParams.set('malesOnly','1');else url.searchParams.delete('malesOnly');history.replaceState(null,'',url)};
const params=new URLSearchParams(location.search);const initial=params.get('maxYear');if(initial&&/^\\d{1,4}$/.test(initial))input.value=initial;
const initialScore=params.get('minScore');if(initialScore&&/^\\d{1,3}$/.test(initialScore))scoreInput.value=initialScore;
const initialRole=params.get('parentRole');if(['father','mother'].includes(initialRole))roleInput.value=initialRole;
locationInput.value=params.get('candidateLocation')||'';maleInput.checked=params.get('malesOnly')==='1';
input.addEventListener('input',apply);scoreInput.addEventListener('input',apply);roleInput.addEventListener('change',apply);locationInput.addEventListener('input',apply);maleInput.addEventListener('change',apply);clear.addEventListener('click',()=>{input.value='';scoreInput.value='40';roleInput.value='';locationInput.value='';maleInput.checked=false;apply();input.focus()});apply();
})();</script>"""

    pre1800_parent_matches = sum(1 for row in strong_parent_matches if row.get("subject_year") and row["subject_year"] < 1800)
    pre1800_missing_parent = sum(
        1 for dossier in dossiers.values()
        if (year := birth_year(dossier)) and year < 1800
        and {parent.get("relationship") for parent in dossier.get("relationships", {}).get("parents", [])} != {"father", "mother"}
    )

    page_body = f"""<nav class="crumb"><a href="/catalogue.html">Catalogue</a> / Strong candidate matches</nav>
<p class="kicker">Ranked research worklist</p><h1>Strong candidate matches</h1>
<p class="lede">The highest automated parentage and duplicate scores in the public catalogue. These are investigation priorities, not established relationships or merge recommendations.</p>
<section class="match-filter-bar" aria-labelledby="candidate-filter-heading"><div><p class="kicker">Limit the worklist</p><h2 id="candidate-filter-heading">Filter parentage leads</h2><p>Set the period, parent role, candidate location and strictness you want. The default is 40; lower scores reveal weaker leads for broader review.</p></div><label><span>Maximum year</span><input id="candidate-max-year" type="number" min="1" max="{date.today().year}" inputmode="numeric" placeholder="e.g. 1750"></label><label><span>Minimum score</span><input id="candidate-min-score" type="number" min="0" max="100" value="40" inputmode="numeric"></label><label><span>Parent role</span><select id="candidate-parent-role"><option value="">All missing parents</option><option value="father">Fathers only</option><option value="mother">Mothers only</option></select></label><label><span>Candidate location</span><input id="candidate-location" type="search" placeholder="e.g. Antrim or Lisnagaver"></label><label class="match-filter-toggle"><input id="candidate-males-only" type="checkbox"><span>Male subjects only</span></label><button id="candidate-max-clear" class="button secondary" type="button">Reset</button></section>
<p id="candidate-filter-status" class="section-intro" aria-live="polite"></p>
<div class="quality-summary"><div><strong id="parent-match-count">{len(strong_parent_matches):,}</strong><span>Parentage leads matching the current filters</span></div><div><strong>{pre1800_parent_matches:,}</strong><span>40+ leads for people born before 1800 ({pre1800_missing_parent:,} profiles lack a parent)</span></div><div><strong id="duplicate-match-count">{len(duplicate_rows):,}</strong><span>Unique possible-duplicate pairs</span></div></div>
<section id="parent-matches"><h2>Potential parentage</h2><p class="section-intro">The best eligible candidate for each missing, uncertain or unassessed father or mother role. Scores below 40 include weak chronological fallbacks; confident or independently supported parents, generation conflicts, parent-in-law matches and unresolved child-duplicate cases are omitted.</p>{match_table(parent_matches, "parent") if parent_matches else '<p class="empty-state">No unresolved parentage leads.</p>'}</section>
<section id="duplicate-matches"><h2>Possible duplicates</h2><p class="section-intro">Unique profile pairs classified as possible duplicates. Inspect both profiles and their sources before proposing a merge.</p>{match_table(duplicate_rows, "duplicate") if duplicate_rows else '<p class="empty-state">No possible duplicate pairs.</p>'}</section>"""
    (WEB_DIR / "candidate-matches.html").write_text(
        _page("Strong candidate matches", "Ranked potential-parent and possible-duplicate research leads.", page_body, "/candidate-matches.html", script=filter_script),
        encoding="utf-8",
    )

    def preview_rows(rows: list[dict], symbol: str) -> str:
        return "".join(
            f'<li><span>{person_link(row["subject_name"], row["subject_id"], row["subject_url"])} {symbol} '
            f'{person_link(row["candidate"]["name"], row["candidate"]["id"], row["candidate"]["html_url"])}</span>'
            f'<strong>{row["candidate"].get("score", 0)}</strong></li>'
            for row in rows[:4]
        )

    preview_html = f"""<div class="strong-match-preview"><div class="strong-match-heading"><div><p class="kicker">Highest automated scores</p><h3>Profiles with strong candidate matches</h3></div><a class="button secondary" href="/candidate-matches.html">View ranked worklist</a></div>
<div class="strong-match-grid"><article><h4>Potential parents</h4><p>{len(strong_parent_matches):,} missing parent roles have an unresolved lead scoring 40 or more; {pre1800_parent_matches:,} concern people born before 1800.</p><ol>{preview_rows(strong_parent_matches, "→")}</ol></article>
<article><h4>Possible duplicates</h4><p>{len(duplicate_rows):,} unique profile pairs meet the duplicate threshold.</p><ol>{preview_rows(duplicate_rows, "↔")}</ol></article></div>
<p class="legend-warning">Scores prioritise investigation only; they do not establish parentage or justify a merge.</p></div>"""
    return {"parent_count": len(strong_parent_matches), "duplicate_count": len(duplicate_rows), "preview_html": preview_html}


def build_research_catalog(records: list[dict], profiles: dict[str, dict], edges: list[list[str]], descendant_counts: dict[str, int], early_bearers: list[dict], ydna_timeline: list[dict], export_paths: list[Path], location_index: dict[str, list[str]] | None = None, root_links: dict[str, list[list[object]]] | None = None) -> dict[str, int]:
    wikitree_evidence = _load_wikitree_evidence()
    profile_updates = _load_profile_updates(wikitree_evidence)
    profile_audit_payload = _load_catalogue_profile_audit()
    profile_audit_entries = profile_audit_payload.get("entries", {})
    catalogue_profile_links = _load_catalogue_profile_links()
    profile_audited_at = profile_audit_payload.get("audited_at", "")
    people = _build_people(
        records, profiles, edges, descendant_counts, wikitree_evidence,
        profile_seed_ids=set(profile_updates) | catalogue_research_case_ids(),
    )
    public_people = [person for person in people if not person["likely_living"]]
    pre1500_draft_paths = {
        "record-medieval-1283-alexander-richard-constable": "surname-research/free-space-pages/Alexander_son_of_Richard_constable_of_Glasgow.md",
        "record-medieval-1283-alexander-richard-messenger": "surname-research/free-space-pages/Alexander_son_of_Richard_messenger_of_Glasgow.md",
        "record-medieval-1289-alexander-escheator": "research/free-space-pages/pages/004-andrew-de-glasgu.wiki",
        "record-medieval-1506-john-alias-smith": "surname-research/free-space-pages/John_Glasgow_of_Saltmarket.md",
    }
    pre1500_space_urls = {
        "record-medieval-1283-alexander-richard-constable": "https://www.wikitree.com/wiki/Space:Alexander_son_of_Richard_constable_of_Glasgow",
        "record-medieval-1283-alexander-richard-messenger": "https://www.wikitree.com/wiki/Space:Alexander_son_of_Richard_messenger_of_Glasgow",
        "record-medieval-1289-alexander-escheator": "https://www.wikitree.com/wiki/Space:Andrew_de_Glasgu",
        "record-medieval-1506-john-alias-smith": "https://www.wikitree.com/wiki/Space:John_de_Glasgow_alias_Smith_/_John_Glasgow_of_Saltmarket%27",
    }
    profile_audits_by_catalogue = {}
    for person in public_people:
        destination = catalogue_profile_links.get(person["catalogue_id"], {})
        configured_space_url = str(destination.get("free_space_url") or "")
        if configured_space_url and not configured_space_url.startswith(
            "https://www.wikitree.com/wiki/Space:"
        ):
            raise ValueError(
                f"{person['catalogue_id']}: invalid WikiTree free-space destination"
            )
        person["wikitree_free_space_url"] = (
            configured_space_url or pre1500_space_urls.get(person["catalogue_id"], "")
        )
        person["profile_disposition"] = str(
            destination.get("profile_disposition") or (
                "free_space_only" if person["wikitree_free_space_url"] else ""
            )
        )
        person["free_space_draft_path"] = str(
            destination.get("free_space_draft_path") or ""
        )
        person["has_wikitree_destination"] = bool(
            person["profile_ids"] or person["wikitree_free_space_url"]
        )
        profile_audit = dict(profile_audit_entries.get(person["catalogue_id"], {}))
        if (
            destination.get("profile_disposition") == "free_space_only"
            and not person["profile_ids"]
        ):
            profile_audit.update({
                "candidates": [],
                "draft_path": destination.get("free_space_draft_path", ""),
                "identity_note": destination.get("evidence_note") or (
                    "The evidence belongs on a supporting WikiTree free-space page and "
                    "does not justify a separate person profile."
                ),
                "identity_status": "free_space_only",
                "recommended_action": "do_not_create",
                "searched_profile_count": int(
                    profile_audit.get("searched_profile_count") or 0
                ),
            })
        birth_match = re.search(r"\b(\d{3,4})\b", str(person.get("birth") or ""))
        if (
            not person["profile_ids"] and not profile_audit and birth_match
            and int(birth_match.group(1)) < 1500
        ):
            profile_audit = {
                "candidates": [],
                "draft_path": pre1500_draft_paths.get(person["catalogue_id"], ""),
                "identity_note": (
                    "Pre-1500 documentary subject. Maintain an individual free-space research page; "
                    "do not create or repurpose a WikiTree person profile."
                ),
                "identity_status": "free_space_only",
                "recommended_action": "do_not_create",
                "searched_profile_count": 0,
            }
        profile_audits_by_catalogue[person["catalogue_id"]] = profile_audit
        person["profile_work_status"] = _profile_work_status(person, profile_audit)
        person["profile_work_candidate_count"] = len(profile_audit.get("candidates") or [])
    dossiers, machine_people_index = build_machine_models(public_people)
    withheld_count = len(people) - len(public_people)
    generated = date.today().isoformat()
    source_exports = [path.name for path in export_paths]
    export_version = source_exports[-1] if source_exports else "No One-Tree export identified"
    _reset_generated_dir(CATALOGUE_DIR)
    _reset_generated_dir(DATA_DIR)
    _reset_generated_dir(RECORDS_DIR)
    _reset_generated_dir(PLACES_DIR)
    (CATALOGUE_DIR / "by-name").mkdir()
    (CATALOGUE_DIR / "clusters").mkdir()
    (CATALOGUE_DIR / "locations").mkdir()
    _write_assets()

    id_to_slug = {profile_id: person["catalogue_id"] for person in public_people for profile_id in person["profile_ids"]}
    family_memberships = _family_memberships(
        public_people, root_links or {}, profiles, descendant_counts, id_to_slug,
    )
    similar_by_id = _similar_people(machine_people_index)
    parentage_by_id = _potential_parentage(machine_people_index, similar_by_id)
    for index_entry in machine_people_index:
        for internal_field in (
            "_sibling_ids", "_parent_links", "_spouse_links", "_child_links", "_sibling_links",
            "_dated_records", "_birth_expression", "_structural_placeholder",
            "_family_links_disclaimed", "_birth_details_disclaimed",
            "_profile_sources_tree_only",
        ):
            index_entry.pop(internal_field, None)
        # Absence already means no indexed occupation; omitting the overwhelmingly
        # empty array keeps the resolver index within its public size budget.
        if not index_entry.get("occupations"):
            index_entry.pop("occupations", None)
    for person in public_people:
        dossier = dossiers[person["catalogue_id"]]
        finding_ids = _unique([dossier["id"], *person["profile_ids"]])
        dossier["research_findings"] = _load_research_findings(finding_ids)
        dossier["similar_people"] = similar_by_id.get(dossier["id"], [])
        dossier["potential_parentage"] = parentage_by_id.get(dossier["id"], {
            "children_recorded": [], "earliest_dated_son": None, "earliest_dated_daughter": None,
            "second_dated_son": None, "second_dated_daughter": None,
            "third_dated_son": None, "third_dated_daughter": None,
            "naming_controls": {"matches": 0, "mismatches": 0, "factor": 1, "details": []},
            "candidates": [], "method": "No naming-pattern analysis available.",
            "warning": "These scores are research leads, not evidence of parentage.",
        })
        if dossier["research_findings"]:
            dossier["provenance"]["research_findings"] = "Durable research/<profile-or-catalogue-ID>/findings.md case file"
    profile_updates_by_catalogue = {}
    # A candidate-bearing catalogue row can mention the same WikiTree profile
    # as another row. Publish each profile update once, preferring its canonical
    # catalogue page, so the filter counts profiles rather than candidate rows.
    for profile_id, update in profile_updates.items():
        candidates = [person for person in public_people if profile_id in person["profile_ids"]]
        if not candidates:
            continue
        person = next(
            (candidate for candidate in candidates if candidate["catalogue_id"] == profile_id.casefold()),
            min(candidates, key=lambda candidate: (len(candidate["profile_ids"]), candidate["catalogue_id"])),
        )
        existing = profile_updates_by_catalogue.get(person["catalogue_id"])
        if existing and int(existing.get("significance") or 0) >= int(update.get("significance") or 0):
            continue
        profile_updates_by_catalogue[person["catalogue_id"]] = update
        dossiers[person["catalogue_id"]]["wikitree_update"] = {
            "profile_id": update["profile_id"],
            "significance": int(update.get("significance") or 0),
            "summary": update.get("summary") or "",
            "remote_captured_at": update.get("remote_captured_at") or "",
            "remote_revision": update.get("remote_revision") or "",
            "draft_wikitext": update.get("proposed_wikitext") or "",
            **({"application_review": {key: update["application_review"][key]
                                       for key in ("reviewed_on", "status", "assessment")
                                       if key in update["application_review"]}}
               if update.get("application_review") else {}),
        }
    candidate_worklist = _write_candidate_match_worklist(dossiers)
    location_to_slug = {
        record["location_id"]: _slug(record["location_id"])
        for person in public_people for record in person["records"] if record.get("location_id")
    }
    for person in public_people:
        profile_audit = dict(profile_audits_by_catalogue.get(person["catalogue_id"], {}))
        profile_audit["_audited_at"] = profile_audited_at
        if profile_audit and not person["profile_ids"]:
            draft = _extract_profile_draft(profile_audit)
            dossiers[person["catalogue_id"]]["profile_creation"] = {
                "status": profile_audit.get("recommended_action") or "needs_sourced_draft",
                "identity_note": profile_audit.get("identity_note") or "",
                "draft_path": profile_audit.get("draft_path") or "",
                "draft_wikitext": draft,
                "creation_allowed": (
                    profile_audit.get("recommended_action")
                    not in {"do_not_create", "hold", "duplicate_profiles"}
                ),
            }
        person_path = CATALOGUE_DIR / f"{person['catalogue_id']}.html"
        person_html = _person_page(
            person, dossiers[person["catalogue_id"]], id_to_slug, location_to_slug,
            export_version, generated, profile_audit,
            profile_updates_by_catalogue.get(person["catalogue_id"]),
        )
        if person_path.exists():
            person_html = _preserve_unified_person_shell(
                person_path.read_text(encoding="utf-8"), person_html
            )
        person_path.write_text(person_html, encoding="utf-8")

    name_buckets = defaultdict(list)
    for person in public_people:
        initial = next((character.upper() for character in person["name"] if character.isalpha()), "#")
        name_buckets[initial if "A" <= initial <= "Z" else "#"].append(person)
    name_cards = []
    for initial, members in sorted(name_buckets.items()):
        filename = "other" if initial == "#" else initial.lower()
        path = f"/people/by-name/{filename}.html"
        (CATALOGUE_DIR / "by-name" / f"{filename}.html").write_text(_people_list_page(f"Names beginning {initial}", "Alphabetical catalogue page.", members, path), encoding="utf-8")
        name_cards.append(f'<a class="browse-card" href="{path}"><strong>{escape(initial)}</strong><span>{len(members):,} individuals</span></a>')

    by_cluster = defaultdict(list)
    for person in public_people:
        for cluster in person["clusters"]:
            by_cluster[cluster].append(person)
    cluster_cards = []
    for cluster, members in sorted(by_cluster.items()):
        filename = _slug(cluster)
        path = f"/people/clusters/{filename}.html"
        unique_members = list({person["catalogue_id"]: person for person in members}.values())
        (CATALOGUE_DIR / "clusters" / f"{filename}.html").write_text(_people_list_page(cluster, "People associated with this research cluster.", unique_members, path), encoding="utf-8")
        cluster_cards.append(f'<a class="browse-card" href="{path}"><strong>{escape(cluster)}</strong><span>{len(unique_members):,} individuals</span></a>')

    by_region = defaultdict(lambda: defaultdict(dict))
    for person in public_people:
        for record in person["records"]:
            region = record.get("region") or "Unspecified"
            location = record.get("record_location") or "Location not specified"
            by_region[region][location][person["catalogue_id"]] = person
    region_cards = []
    for region, locations in sorted(by_region.items()):
        members = {person["catalogue_id"]: person for location_people in locations.values() for person in location_people.values()}
        sections = []
        for location, location_people in sorted(locations.items()):
            links = " · ".join(f'<a href="/people/{person["catalogue_id"]}.html">{escape(person["name"])}</a>' for person in sorted(location_people.values(), key=lambda item: item["name"].casefold()))
            location_slug = next((
                location_to_slug[record["location_id"]]
                for person in location_people.values() for record in person["records"]
                if record.get("record_location") == location and record.get("location_id") in location_to_slug
            ), None)
            heading = f'<a href="/places/{location_slug}.html">{escape(location)}</a>' if location_slug else escape(location)
            sections.append(f'<section><h2>{heading}</h2><p>{links}</p></section>')
        filename = _slug(region)
        path = f"/people/locations/{filename}.html"
        body = f'<nav class="crumb"><a href="/catalogue.html">Catalogue</a> / Locations / {escape(region)}</nav><p class="kicker">Browse by location</p><h1>{escape(region)}</h1><p class="lede">{len(members):,} people across {len(locations):,} mapped locations. Individuals appear under every mapped locality associated with them.</p>{"".join(sections)}'
        (CATALOGUE_DIR / "locations" / f"{filename}.html").write_text(_page(f"People recorded in {region}", f"Glasgow surname records grouped by locality in {region}.", body, path), encoding="utf-8")
        region_cards.append(f'<a class="browse-card" href="{path}"><strong>{escape(region)}</strong><span>{len(members):,} individuals · {len(locations):,} locations</span></a>')

    bearer_rows = "".join(
        f'<tr><td><a href="https://www.wikitree.com/wiki/Space:Bearers_of_the_%27%27de_Glasgu%27%27_Name_and_the_Emergence_of_the_Glasgow_Surname%2C_c.1175%E2%80%931500#{quote(item["anchor"])}">{escape(item["name"])}</a></td>'
        f'<td>{escape(item["date"])}</td><td>{escape(item["place"])}</td><td>{escape(item["context"])}</td><td>{escape(item["assessment"])}</td><td>{escape(item["precision"])}</td></tr>'
        for item in early_bearers
    )
    bearer_body = f"""<nav class="crumb"><a href="/catalogue.html">Catalogue</a> / Early bearers</nav><p class="kicker">Medieval documentary register</p><h1>Early bearers of the <em>de Glasgu</em> name</h1>
<p class="lede">{len(early_bearers)} mapped documentary identities or relationship records, c.1175–1506. These records demonstrate personal and family-identifying use but do not prove one hereditary pedigree.</p>
<div class="table-wrap"><table><thead><tr><th>Bearer</th><th>Date</th><th>Documentary place</th><th>Context</th><th>Assessment</th><th>Map precision</th></tr></thead><tbody>{bearer_rows}</tbody></table></div>"""
    (CATALOGUE_DIR / "early-bearers.html").write_text(_page("Early de Glasgu bearers", "Crawlable documentary register of medieval de Glasgu name bearers, c.1175–1506.", bearer_body, "/people/early-bearers.html"), encoding="utf-8")

    public_records = []
    for person in public_people:
        for record in person["records"]:
            supporting = _best_supporting_evidence(record, dossiers[person["catalogue_id"]])
            record_categories = _catalogue_record_types({"records": [record]}) or ["Other records"]
            public_records.append({
                "record_id": record["record_id"], "catalogue_id": person["catalogue_id"],
                "person": person["name"], "profile_ids": " | ".join(person["profile_ids"]),
                "catalogue_url": f"{SITE_URL}/people/{person['catalogue_id']}.html",
                **record, "record_category": " | ".join(record_categories),
                "place_url": f"{SITE_URL}/places/{location_to_slug[record['location_id']]}.html" if record.get("location_id") in location_to_slug else "",
                "supporting_source_title": supporting.get("title") or "",
                "supporting_source_url": supporting.get("url") or "",
                "supporting_source_quality": supporting.get("quality") or "unknown",
                "supporting_source_status": supporting.get("status") or "unresolved",
                "supporting_source_reason": supporting.get("reason") or "",
                "export_version": export_version, "catalogue_generated": generated,
            })
    source_gap_count = sum(record["source_type"] != "explicit" for record in public_records)
    place_index = _write_place_pages(public_records, public_people, location_to_slug)
    record_catalog_stats = _write_record_catalog(public_records)
    refreshed = date.today().strftime("%-d %B %Y")
    region_values = sorted({region for person in public_people for region in person["regions"] if region})
    cluster_values = sorted({cluster for person in public_people for cluster in person["clusters"] if cluster})
    record_type_values = sorted({kind for person in public_people for kind in _catalogue_record_types(person)})
    region_options = "".join(f'<option value="{escape(value, quote=True)}">{escape(value)}</option>' for value in region_values)
    cluster_options = "".join(f'<option value="{escape(value, quote=True)}">{escape(value)}</option>' for value in cluster_values)
    record_type_options = "".join(f'<option value="{escape(value, quote=True)}">{escape(value)}</option>' for value in record_type_values)
    irish_count = sum("Ireland" in person["regions"] for person in public_people)
    early_count = sum(
        any(isinstance(record.get("filter_year"), (int, float)) and record["filter_year"] < 1700 for record in person["records"])
        or bool(re.match(r"^(?:before |c\. )?(?:1[0-6]\d{2}|\d{1,3})\b", person.get("birth", "")))
        for person in public_people
    )
    profile_work_counts = Counter(
        person["profile_work_status"] for person in public_people if not person["profile_ids"]
    )
    missing_profile_count = sum(
        count for status, count in profile_work_counts.items()
        if status != "linked_free_space"
    )
    missing_father_count = sum(not person["father"] for person in public_people)
    original_count = sum(
        any(item.get("source_quality") == "original" for item in dossiers[person["catalogue_id"]]["evidence"])
        for person in public_people
    )
    ranked_updates = sorted(
        (
            (person, profile_updates_by_catalogue[person["catalogue_id"]])
            for person in public_people if person["catalogue_id"] in profile_updates_by_catalogue
        ),
        key=lambda item: (-int(item[1].get("significance") or 0), item[0]["name"].casefold()),
    )
    update_preview_cards = "".join(
        f'<article><div><p class="kicker">Significance {int(update.get("significance") or 0)}/100</p>'
        f'<h3><a href="/people/{person["catalogue_id"]}.html#wikitree-update">{escape(person["name"])}</a></h3>'
        f'<p><a href="{escape(update["profile_url"], quote=True)}">{escape(update["profile_id"])}</a></p></div>'
        f'<p>{escape(update.get("summary") or "")}</p></article>'
        for person, update in ranked_updates[:8]
    )
    update_preview_html = f'''<section class="wikitree-update-preview"><div class="strong-match-heading"><div><p class="kicker">Profile maintenance</p><h2>Needs updated on WikiTree</h2></div><a class="button secondary" href="?needsUpdate=1">Open significance-ranked table</a></div>
<p>{len(ranked_updates):,} source-backed corrections remain on WikiTree. The highest-significance updates are previewed here; the filter opens the complete queue. Each page provides either paste-ready text or the exact manual relationship, confidence or vital-field action.</p><div class="wikitree-update-grid">{update_preview_cards}</div></section>'''
    statistics_html = _catalogue_statistics(
        public_people, family_memberships, location_to_slug, len(place_index), len(public_records),
        profile_work_counts, original_count, refreshed,
    )
    (DATA_DIR / "catalogue-statistics.json").write_text(
        json.dumps({"html": statistics_html}, ensure_ascii=False) + "\n", encoding="utf-8")
    index_body = f"""{catalogue_hero_html(len(public_people))}
{compact_statistics(statistics_html)}
{catalogue_search_panel_html(cluster_options, record_type_options, region_options)}
<div id="catalogue-results" class="catalogue-results search-results" aria-live="polite"></div>
{update_preview_html}
{candidate_worklist["preview_html"]}
<section class="catalogue-featured"><h2>Explore the research</h2><div class="browse-grid featured-grid">
<a class="browse-card" href="/records/"><strong>Search records</strong><span>{len(public_records):,} mapped documentary associations</span></a>
<a class="browse-card" href="/places/"><strong>Explore places</strong><span>{len(place_index):,} townlands, parishes and localities</span></a>
<a class="browse-card" href="/compare.html"><strong>Compare two people</strong><span>Shared family, place and evidence context</span></a>
<a class="browse-card" href="?region=Ireland"><strong>Irish Glasgows</strong><span>{irish_count:,} people with mapped Irish associations</span></a>
<a class="browse-card" href="?to=1699"><strong>Before 1700</strong><span>{early_count:,} early people and documentary occurrences</span></a>
<a class="browse-card" href="?missingProfile=1"><strong>WikiTree identity workbench</strong><span>{missing_profile_count:,} documentary identities without confirmed destinations: {profile_work_counts['creation_ready']:,} creation-ready, {profile_work_counts['existing_profile_candidate']:,} possible existing-profile matches on HOLD, {profile_work_counts['identity_hold']:,} identity-insufficient HOLD, {profile_work_counts['free_space_only']:,} pre-1500 subjects missing an individual Space page, and {profile_work_counts['unreviewed']:,} awaiting review</span></a>
<a class="browse-card" href="?needsUpdate=1"><strong>Needs updated on WikiTree</strong><span>{len(ranked_updates):,} profiles ranked by significance, with paste-ready or exact manual corrections</span></a>
<a class="browse-card" href="?missingFather=1"><strong>Missing fathers</strong><span>{missing_father_count:,} people without a recorded father</span></a>
<a class="browse-card" href="?original=1"><strong>Original-record evidence</strong><span>{original_count:,} people linked to original evidence</span></a>
<a class="browse-card" href="/people/early-bearers.html"><strong>Early <em>de Glasgu</em> bearers</strong><span>{len(early_bearers)} medieval documentary entries</span></a>
<a class="browse-card" href="/timeline.html"><strong>Y-DNA timeline</strong><span>{len(ydna_timeline)} migration and ancestry stages</span></a>
</div></section>
{_catalogue_legend_html()}
<section class="catalogue-browse"><h2>Browse the complete catalogue</h2>
<details class="browse-section"><summary><span>Browse by name</span><small>{len(name_cards)} alphabetical groups</small></summary><div class="browse-grid">{"".join(name_cards)}</div></details>
<details class="browse-section"><summary><span>Browse by country or region</span><small>{len(region_cards)} regions</small></summary><div class="browse-grid">{"".join(region_cards)}</div></details>
<details class="browse-section"><summary><span>Browse by research cluster</span><small>{len(cluster_cards)} research groupings</small></summary><div class="browse-grid">{"".join(cluster_cards)}</div></details></section>
<details class="catalogue-about"><summary>About this catalogue, privacy and data downloads</summary><div><p>This crawlable catalogue contains historical or deceased individuals, family links, mapped places, evidence labels, provenance and research notes. {withheld_count:,} profiles assessed as likely living are omitted from the catalogue, public exports and sitemap.</p><p><small>Source export: {escape(export_version)} · generated {escape(generated)}</small></p><div class="actions"><a class="button" href="/data/people.csv">People CSV</a><a class="button secondary" href="/data/people.json">People JSON</a><a class="button secondary" href="/data/records.csv">Record associations CSV</a></div></div></details>"""
    root_script = (
        '<script>if(location.protocol==="file:")'
        '{document.write(\'<script src="data/people-index.js"><\\/script>\')}</script>'
        f'<script src="people/search.js?v={CATALOGUE_ASSET_VERSION}" defer></script>'
    )
    catalogue_html = _page(
        "Research catalogue",
        "Crawlable Glasgow surname people, family relationships, locations and documentary records.",
        index_body,
        "/catalogue.html",
        script=root_script,
        asset_prefix="",
        brand_href="/index.html",
    )
    people_index_html = _page(
        "Research catalogue",
        "Crawlable Glasgow surname people, family relationships, locations and documentary records.",
        index_body,
        "/catalogue.html",
        script=f'<script src="/people/search.js?v={CATALOGUE_ASSET_VERSION}" defer></script>',
        asset_prefix="../",
    )
    (CATALOGUE_DIR / "index.html").write_text(people_index_html, encoding="utf-8")
    (WEB_DIR / "catalogue.html").write_text(catalogue_html, encoding="utf-8")

    catalogue_search_index = []
    glasgow_name = re.compile(r"\b(?:glasgow|glasco|glassco|glascoe|glasgo|glasow|glascow|glasoe|glassgow|glassgo|glasko)\b", re.I)
    for person in public_people:
        location_claims = [
            claim.get("location", "")
            for capture in person["wikitree_evidence"]
            for claim in capture.get("location_claims", [])
        ]
        birth_year_match = re.search(r"\b\d{4}\b", person["birth"] or "")
        death_year_match = re.search(r"\b\d{4}\b", person["death"] or "")
        birth_year = int(birth_year_match.group()) if birth_year_match else None
        death_year = int(death_year_match.group()) if death_year_match else None
        date_years = _unique(
            [
                int(match.group())
                for value in (person["birth"], person["death"])
                for match in [re.search(r"\b\d{4}\b", value or "")]
                if match
            ]
            + [
                round(record["filter_year"])
                for record in person["records"]
                if isinstance(record.get("filter_year"), (int, float))
            ]
        )
        location_aliases = _unique(
            alias
            for record in person["records"]
            if record.get("location_id")
            for alias in (location_index or {}).get(record["location_id"], [])
        )
        dossier = dossiers[person["catalogue_id"]]
        assessed_parents = {
            (relation.get("id", ""), relation.get("relationship", "")): relation
            for relation in dossier.get("relationships", {}).get("parents", [])
        }
        tree_statuses = {
            "5": ("non_biological", "WikiTree: non-biological parent"),
            "10": ("uncertain", "WikiTree: uncertain parent"),
            "20": ("confident", "WikiTree: confident parent"),
            "30": ("dna_confirmed", "WikiTree: confirmed with DNA"),
        }

        def parent_relations_with_confidence(role: str) -> list[dict]:
            enriched = []
            for relation in person[role]:
                item = dict(relation)
                assessment = assessed_parents.get((relation.get("id", ""), role), {})
                assessed_status = assessment.get("status") or "unknown"
                if assessed_status != "unknown":
                    certainty = assessed_status
                    certainty_label = assessment.get("status_label") or assessed_status.replace("_", " ")
                else:
                    raw_tree_status = str(relation.get("data_status") or "")
                    fallback_status, fallback_label = tree_statuses.get(
                        raw_tree_status, ("unmarked", "WikiTree: relationship status unmarked")
                    )
                    certainty = assessment.get("tree_status") or fallback_status
                    certainty_label = assessment.get("tree_status_label") or fallback_label
                item["certainty"] = certainty
                item["certainty_label"] = certainty_label
                enriched.append(item)
            return enriched

        catalogue_fathers = parent_relations_with_confidence("father")
        catalogue_mothers = parent_relations_with_confidence("mother")
        source_qualities = _unique(item.get("source_quality") for item in dossier["evidence"])
        claim_statuses = _unique(item.get("status") for item in dossier["claims"])
        record_types = _catalogue_record_types(person)
        evidence_text = " ".join(str(value) for value in person["evidence"])
        search_row = {
            "map_key": person["map_key"], "id": person["catalogue_id"], "name": person["name"],
            "profile_ids": person["profile_ids"], "first_names": person["first_names"],
            "last_names_at_birth": person["last_names_at_birth"], "last_names_current": person["last_names_current"],
            "suffixes": person["suffixes"], "has_suffix": person["has_suffix"], "gender": person["gender"],
            "birth": person["birth"], "birth_note": person["birth_note"], "birth_location": person["birth_location"],
            "birth_location_note": person["birth_location_note"], "death": person["death"], "death_location": person["death_location"],
            "spouses": person["spouses"], "father": catalogue_fathers, "mother": catalogue_mothers, "children": person["children"],
            "cluster": person["cluster"], "clusters": person["clusters"], "descendants": person["descendants"],
            "evidence": person["evidence"], "recorded_in": person["recorded_in"], "regions": person["regions"],
            "locations": _unique([person["birth_location"], person["death_location"], *person["recorded_in"], *location_claims]),
            "location_aliases": location_aliases,
            "location_groups": _person_location_groups(person, location_index or {}),
            "family_root": family_memberships[person["catalogue_id"]]["primary"],
            "family_roots": family_memberships[person["catalogue_id"]]["roots"],
            "date_years": date_years, "birth_year": birth_year, "death_year": death_year,
            "missing_father": not person["father"], "missing_mother": not person["mother"],
            "missing_vital_location": not person["birth_location"] or not person["death_location"],
            "estimated_location": bool(person["birth_location_note"]) or any(
                re.search(
                    r"\b(?:estimated|kin-inferred|approximate)\b",
                    " ".join(str(record.get(field) or "") for field in ("record_precision", "location_basis", "association")),
                    re.I,
                )
                for record in person["records"]
            ),
            "has_profile": bool(person["profile_ids"]),
            "wikitree_free_space_url": person["wikitree_free_space_url"],
            "profile_disposition": person["profile_disposition"],
            "has_wikitree_destination": person["has_wikitree_destination"],
            "missing_profile": not person["has_wikitree_destination"],
            "profile_work_status": person["profile_work_status"],
            "profile_work_candidate_count": person["profile_work_candidate_count"],
            "needs_wikitree_update": person["catalogue_id"] in profile_updates_by_catalogue,
            "wikitree_update_significance": int(profile_updates_by_catalogue.get(person["catalogue_id"], {}).get("significance") or 0),
            "wikitree_update_summary": profile_updates_by_catalogue.get(person["catalogue_id"], {}).get("summary") or "",
            "has_original_record": "original" in source_qualities,
            "has_open_questions": bool(dossier["open_questions"]),
            "uncertain_identity": bool(
                len(person["profile_ids"]) > 1
                or re.search(r"\b(?:uncertain|possible|probable|estimated|traditional|profile lead|unproved)\b", evidence_text, re.I)
            ),
            "source_qualities": source_qualities,
            "claim_statuses": claim_statuses,
            "record_types": record_types,
            "record_count": len(person["records"]),
            "woman_married_glasgow": person["gender"].casefold() == "female" and any(
                glasgow_name.search(f"{relation.get('id', '')} {relation.get('name', '')}")
                for relation in person["spouses"]
            ),
            "evidence_terms": _unique(
                [category for capture in person["wikitree_evidence"] for category in capture.get("categories", [])]
                + [item.get("citation", "") for capture in person["wikitree_evidence"] for item in capture.get("sources", [])]
            ),
        }
        search_row.update(catalogue_location_search_enrichment(person, dossier))
        catalogue_search_index.append(search_row)
    search_js = Path(__file__).with_name("catalogue_search.js").read_text(encoding="utf-8")
    (CATALOGUE_DIR / "search.js").write_text(search_js + "\n", encoding="utf-8")

    (DATA_DIR / "people.json").write_text(json.dumps({
        "schema_version": SCHEMA_VERSION, "generated": generated, "source_exports": source_exports,
        "count": len(public_people), "withheld_likely_living_count": withheld_count,
        "people": public_people,
    }, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    (DATA_DIR / "catalogue-search-index.json").write_text(json.dumps(catalogue_search_index, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    (DATA_DIR / "people-index.js").write_text(
        "window.glasgowPeopleIndex="
        + json.dumps(catalogue_search_index, ensure_ascii=False, separators=(",", ":"))
        + ";\n",
        encoding="utf-8",
    )
    machine_stats = write_machine_outputs(CATALOGUE_DIR, DATA_DIR, dossiers, machine_people_index)
    schema_dir = DATA_DIR / "schema"
    schema_dir.mkdir(exist_ok=True)
    (schema_dir / "person.schema.json").write_text(
        json.dumps(person_json_schema(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    public_wikitree_evidence = evidence_envelope(wikitree_evidence, public_people)
    (DATA_DIR / "wikitree-profile-evidence.json").write_text(
        json.dumps(public_wikitree_evidence, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    csv_fields = ["catalogue_id", "name", "profile_ids", "wikitree_free_space_url", "profile_disposition", "has_wikitree_destination", "profile_work_status", "profile_work_candidate_count", "first_names", "last_names_at_birth", "last_names_current", "suffixes", "has_suffix", "gender", "birth", "birth_note", "birth_location", "birth_location_note", "death", "death_location", "spouses", "father", "mother", "children", "cluster", "clusters", "descendants", "evidence", "recorded_in", "regions", "record_count", "derived_children_count", "outside_export_parent_references", "relationship_warnings", "profile_created", "profile_last_updated", "profile_connected", "reported_children_count", "dna_flags", "wikitree_evidence_profiles", "wikitree_evidence_captured", "wikitree_record_passage_count", "wikitree_source_count", "wikitree_external_url_count", "wikitree_location_claims", "export_version", "catalogue_generated", "catalogue_url", "wikitree_urls"]
    with (DATA_DIR / "people.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=csv_fields)
        writer.writeheader()
        for person in public_people:
            row = {field: person.get(field, "") for field in csv_fields}
            for field in ("profile_ids", "first_names", "last_names_at_birth", "last_names_current", "suffixes", "clusters", "evidence", "recorded_in", "regions"):
                row[field] = " | ".join(person[field])
            for field in ("spouses", "father", "mother", "children"):
                row[field] = " | ".join(relation["name"] + (f" [{relation['id']}]" if relation["id"] else "") for relation in person[field])
            row["record_count"] = len(person["records"])
            row["relationship_warnings"] = " | ".join(person["relationship_warnings"])
            row["profile_created"] = " | ".join(_unique(info["created"] for info in person["profile_information"]))
            row["profile_last_updated"] = " | ".join(_unique(info["last_updated"] for info in person["profile_information"]))
            row["profile_connected"] = "yes" if any(info["connected"] for info in person["profile_information"]) else "no"
            row["reported_children_count"] = " | ".join(str(value) for value in _unique(info["reported_children_count"] for info in person["profile_information"]))
            row["dna_flags"] = " | ".join(_unique(flag for info in person["profile_information"] for flag, present in (("Y-DNA", info["ydna"]), ("auDNA", info["audna"])) if present))
            row["wikitree_evidence_profiles"] = " | ".join(capture.get("profile_id", "") for capture in person["wikitree_evidence"])
            row["wikitree_evidence_captured"] = " | ".join(_unique(capture.get("captured_at", "") for capture in person["wikitree_evidence"]))
            row["wikitree_record_passage_count"] = sum(len(capture.get("record_passages", [])) for capture in person["wikitree_evidence"])
            row["wikitree_source_count"] = sum(len(capture.get("sources", [])) for capture in person["wikitree_evidence"])
            row["wikitree_external_url_count"] = sum(len(capture.get("external_urls", [])) for capture in person["wikitree_evidence"])
            row["wikitree_location_claims"] = " | ".join(_unique(claim.get("location", "") for capture in person["wikitree_evidence"] for claim in capture.get("location_claims", [])))
            row["export_version"] = export_version
            row["catalogue_generated"] = generated
            row["catalogue_url"] = f"{SITE_URL}/people/{person['catalogue_id']}.html"
            row["wikitree_urls"] = " | ".join(
                [*(WIKITREE_URL + profile_id for profile_id in person["profile_ids"]),
                 *([person["wikitree_free_space_url"]] if person.get("wikitree_free_space_url") else [])]
            )
            writer.writerow(row)

    record_fields = [
        "record_id", "catalogue_id", "person", "profile_ids", "year", "filter_year",
        "region", "family_group", "subcluster", "evidence", "association", "note",
        "location_id", "record_location", "record_precision", "location_basis",
        "latitude", "longitude", "source_title", "source_url", "source_type",
        "source_status", "record_category", "place_url", "supporting_source_title",
        "supporting_source_url", "supporting_source_quality", "supporting_source_status",
        "supporting_source_reason", "export_version", "catalogue_generated", "catalogue_url",
    ]
    with (DATA_DIR / "records.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=record_fields)
        writer.writeheader()
        writer.writerows({field: record.get(field, "") for field in record_fields} for record in public_records)
    with (DATA_DIR / "source-gaps.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=record_fields)
        writer.writeheader()
        writer.writerows(
            {field: record.get(field, "") for field in record_fields}
            for record in public_records if record["source_type"] != "explicit"
        )
    with (DATA_DIR / "source-review.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=record_fields)
        writer.writeheader()
        writer.writerows(
            {field: record.get(field, "") for field in record_fields}
            for record in public_records if record["supporting_source_status"] in {"candidate", "unresolved"}
        )
    for filename in ("people.csv", "records.csv", "source-gaps.csv", "source-review.csv"):
        (DATA_DIR / f"{filename}.txt").write_bytes((DATA_DIR / filename).read_bytes())

    health = _write_support_pages(
        public_people, public_records, place_index, dossiers, profile_audit_entries, generated, export_version,
    )

    data_body = f"""<header class="data-hero"><span class="r-kicker">For researchers and programmatic clients</span><h1>Research data<br>and downloads.</h1><p>Schema {SCHEMA_VERSION}. These static, cacheable files are generated from the same public historical-person model as the human catalogue. Start with the compact resolver index, then fetch one dossier or depth-one family network.</p></header><!-- research-access:start --><!-- research-access:end --><section class="data-section" aria-labelledby="data-downloads-title"><div class="data-section-head"><span class="r-kicker">Files and interfaces</span><h2 id="data-downloads-title">Choose a starting point.</h2></div><div class="data-download-grid">
<a class="browse-card" href="/data/people-index.json"><strong>people-index.json</strong><span>Compact identity resolver index; no biographies or evidence payloads</span></a>
<a class="browse-card" href="/people/glasgow-951.json"><strong>Per-person dossier</strong><span>Claims, evidence, family status, questions and leads for Glasgow-951</span></a>
<a class="browse-card" href="/people/glasgow-951.network.json"><strong>Immediate-family network</strong><span>Depth-one family links and their best relationship evidence</span></a>
<a class="browse-card" href="/data/resolve/alexander-glasgow.json"><strong>Static name resolver</strong><span>Explainable candidate shortlist for Alexander Glasgow</span></a>
<a class="browse-card" href="/data/people.csv"><strong>people.csv</strong><span>{len(public_people):,} historical or deceased people</span></a>
<a class="browse-card" href="/data/people.json"><strong>people.json</strong><span>Full people, relationships and nested records</span></a>
<a class="browse-card" href="/data/records.csv"><strong>records.csv</strong><span>{len(public_records):,} sourced or provenance-labelled associations</span></a>
<a class="browse-card" href="/data/wikitree-profile-evidence.json"><strong>wikitree-profile-evidence.json</strong><span>{len(public_wikitree_evidence['profiles']):,} full biography, citation and relationship snapshots</span></a>
<a class="browse-card" href="/data/records.csv.txt"><strong>records.csv.txt</strong><span>Plain-text mirror for clients whose host treats CSV as a download</span></a>
<a class="browse-card" href="/data/source-gaps.csv"><strong>source-gaps.csv</strong><span>{source_gap_count:,} associations still needing an explicit underlying citation</span></a>
<a class="browse-card" href="/data/source-review.csv"><strong>source-review.csv</strong><span>Candidate citation matches and unresolved associations requiring inspection</span></a>
<a class="browse-card" href="/map/data/early-bearers.json"><strong>early-bearers.json</strong><span>{len(early_bearers)} medieval documentary entries</span></a>
<a class="browse-card" href="/map/data/ydna-timeline.json"><strong>ydna-timeline.json</strong><span>{len(ydna_timeline)} ancestry and migration stages</span></a>
<a class="browse-card" href="/data/schema/person.schema.json"><strong>person.schema.json</strong><span>JSON Schema for a person dossier</span></a>
<a class="browse-card" href="/catalogue.html"><strong>HTML catalogue</strong><span>Small, citable page for every published person</span></a></div></section>
<aside class="data-notice"><strong>Privacy:</strong> {withheld_count:,} likely-living profiles are withheld from these files. The heuristic is no recorded death plus a birth within the last 120 years.</aside>
<section><h2>Predictable endpoints</h2><div class="table-wrap"><table><thead><tr><th>Purpose</th><th>Path</th></tr></thead><tbody>
<tr><td>Compact global index</td><td><code>/data/people-index.json</code></td></tr><tr><td>Person dossier</td><td><code>/people/&lt;lowercase-wikitree-id&gt;.json</code></td></tr>
<tr><td>Depth-one network</td><td><code>/people/&lt;lowercase-wikitree-id&gt;.network.json</code></td></tr><tr><td>Exact normalised-name candidates</td><td><code>/data/resolve/&lt;name-slug&gt;.json</code></td></tr>
</tbody></table></div><p>The static resolver returns candidates, never a genealogical conclusion. Filter or score candidates using birth year, all locations, spouse names, parents, children and occupations in <code>people-index.json</code>. The generated score is deterministic: normalised name, birth-year tolerance, location and spouse matches add explainable reasons; conflicts subtract a documented amount.</p></section>
<section><h2>Claims, evidence and relationships</h2><p>The dossier follows <strong>Person → Claim → Evidence → Source</strong>. Stable hash-based IDs prevent rebuilds from renumbering unchanged objects. Canonical claim statuses are <code>unknown</code>, <code>possible</code>, <code>probable</code>, <code>strongly_supported</code>, <code>proved</code>, <code>disputed</code> and <code>contradicted</code>; the original project label is retained in <code>status_label</code>. Source quality is <code>original</code>, <code>derivative</code>, <code>secondary</code>, <code>tree_only</code> or <code>unknown</code>.</p><p>A relationship with <code>tree_relationship: true</code> says the exported WikiTree currently connects the people. It is not documentary proof. Children with <code>relationship_source: reconstructed_parent_reference</code> were recovered by reversing child profiles’ Father/Mother fields. A <code>proved</code> relationship carries claim and evidence IDs from the controlled evidence assessment.</p></section>
<section><h2>Research questions and leads</h2><p><code>open_questions</code> come from versioned local research cases. <code>research_leads</code> include pending case targets plus conservatively extracted profile-note actions only when they contain a concrete archive reference, URL, or a record type with a constrained year. Repository, collection/reference, date bounds and reason are retained where supplied. No archive references are invented.</p></section>
<section><h2>Provenance and interpretation</h2><ul><li>Mapped associations, WikiTree tree links, extracted citations, controlled relationship assessments and local research findings retain separate provenance labels.</li><li><code>independence_group</code> groups citations that resolve to the same underlying URL or source key.</li><li>Estimated dates and locations remain explicitly labelled.</li><li>A cluster is a research grouping, not proof of kinship.</li><li>Full profile captures remain available in <code>wikitree-profile-evidence.json</code>, but compact dossiers omit raw biographies.</li></ul></section>"""
    (DATA_DIR / "index.html").write_text(_unified_data_page(data_body), encoding="utf-8")

    sitemap_paths = [
        "/", "/catalogue.html", "/candidate-matches.html", "/records/", "/places/", "/compare.html", "/feedback.html",
        "/changes.html", "/status.html", "/timeline.html", "/ydna", "/people/early-bearers.html", "/data/index.html",
    ]
    sitemap_paths += [f"/people/{person['catalogue_id']}.html" for person in public_people]
    sitemap_paths += [f"/people/by-name/{'other' if initial == '#' else initial.lower()}.html" for initial in sorted(name_buckets)]
    sitemap_paths += [f"/people/clusters/{_slug(cluster)}.html" for cluster in sorted(by_cluster)]
    sitemap_paths += [f"/people/locations/{_slug(region)}.html" for region in sorted(by_region)]
    sitemap_paths += [place["url"] for place in place_index]
    lastmod = date.today().isoformat()
    sitemap = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "".join(f"  <url><loc>{SITE_URL}{escape(path)}</loc><lastmod>{lastmod}</lastmod></url>\n" for path in sitemap_paths) + "</urlset>\n"
    (WEB_DIR / "sitemap.xml").write_text(sitemap, encoding="utf-8")
    (WEB_DIR / "robots.txt").write_text(f"User-agent: OAI-SearchBot\nAllow: /\nDisallow: /map/data/records.csv\n\nUser-agent: ChatGPT-User\nAllow: /\nDisallow: /map/data/records.csv\n\nUser-agent: *\nAllow: /\nDisallow: /map/data/records.csv\n\nSitemap: {SITE_URL}/sitemap.xml\n", encoding="utf-8")
    (WEB_DIR / "llms.txt").write_text(f"""# Glasgow Surname Project

> A documentary and genealogical research dataset for Glasgow surname bearers and women who married Glasgow men. The public static catalogue contains {len(public_people):,} historical or deceased individuals and {len(public_records):,} mapped record associations. {withheld_count:,} likely-living profiles are withheld.

Dataset version: `{export_version}`. Catalogue generated: `{generated}`.

## Primary resources

- [Research catalogue]({SITE_URL}/catalogue.html): crawlable person, name, place and cluster indexes
- [Research records]({SITE_URL}/records/): search mapped associations by person, place, date, type and source quality
- [Research places]({SITE_URL}/places/): townland, parish and locality timelines
- [Compare people]({SITE_URL}/compare.html): side-by-side vital, family, place and evidence context
- [Strong candidate matches]({SITE_URL}/candidate-matches.html): ranked unresolved potential-parent and possible-duplicate worklist
- [Compact people resolver index]({SITE_URL}/data/people-index.json): identity, vital, location and immediate-family fields without biographies
- [Alexander Glasgow dossier]({SITE_URL}/people/glasgow-951.json): example per-person claims, evidence, questions and leads
- [Alexander Glasgow network]({SITE_URL}/people/glasgow-951.network.json): compact depth-one family graph with best relationship evidence
- [Static Alexander resolver]({SITE_URL}/data/resolve/alexander-glasgow.json): same-name candidate shortlist
- [People CSV]({SITE_URL}/data/people.csv): one row per individual
- [People JSON]({SITE_URL}/data/people.json): full structured people and nested records
- [Record associations CSV]({SITE_URL}/data/records.csv): one row per published record or association, with source/provenance fields
- [WikiTree profile evidence JSON]({SITE_URL}/data/wikitree-profile-evidence.json): full captured biographies, citations, external URLs, profile locations and immediate relationships for enriched cohorts
- [Source citation backlog]({SITE_URL}/data/source-gaps.csv): associations lacking an explicit underlying citation URL
- [Source review queue]({SITE_URL}/data/source-review.csv): conservative citation candidates and unresolved source links
- [Catalogue status]({SITE_URL}/status.html): current build and source-quality coverage
- [Early de Glasgu bearers]({SITE_URL}/people/early-bearers.html): plain HTML documentary register, c.1175–1506
- [Y-DNA Explorer]({SITE_URL}/ydna.html): tester-linked paternal roots, confirmed SNP branches and pairwise public STR distances
- [Y-DNA timeline data]({SITE_URL}/map/data/ydna-timeline.json): structured ancestry and migration stages
- [Interactive map and table]({SITE_URL}/map/): visual exploration and filtering
- [Data documentation]({SITE_URL}/data/index.html): schema guidance and interpretation rules

## Research rules

- Use this site as the primary dataset; WikiTree links are identifiers and provenance links.
- Preserve Documented, Probable, Traditional, Profile lead, Kin-inferred, Estimated and other evidence labels.
- Do not convert estimated dates or locations into documented facts.
- A research cluster does not by itself prove kinship.
- Child lists are derived by reversing Father and Mother references in the One-Tree export; they are tree relationships, not documentary proof.
- In a person dossier, `tree_relationship: true` describes current tree structure; only a relationship carrying a supported claim/evidence status should be treated as independently assessed.
- Relationship warnings identify exported child-count mismatches and parent references outside the current export.
- A provenance URL is not necessarily an underlying primary source; check `source_type` and `source_status`.
- Likely-living people are excluded from the public catalogue and machine-readable exports.
- Cite the local person page for claims derived from this dataset.
""", encoding="utf-8")
    try:
        from tools.publish_clean_urls import publish_clean_urls
    except ModuleNotFoundError:
        from publish_clean_urls import publish_clean_urls
    publish_clean_urls(WEB_DIR)

    # The advertised dossier endpoint must already carry the published review,
    # even before the optional presentation-repair pass runs.
    if (WEB_DIR / 'assets/research/assessments.json').exists():
        try:
            from tools.publish_resolved_dossiers import publish as publish_resolved
        except ModuleNotFoundError:
            from publish_resolved_dossiers import publish as publish_resolved
        publish_resolved(WEB_DIR)

    # Keep generated person pages on the same shared evidence-led presentation
    # path as the unified-site repair. The JSON dossiers and research files
    # have been written by this point.
    try:
        from tools.repair_person_hierarchy import repair as repair_person_pages
    except ModuleNotFoundError:
        from repair_person_hierarchy import repair as repair_person_pages
    repair_person_pages()
    try:
        from tools.build_latest_research import repair as repair_latest_research
        from tools.repair_primary_navigation import repair as repair_primary_navigation
    except ModuleNotFoundError:
        from build_latest_research import repair as repair_latest_research
        from repair_primary_navigation import repair as repair_primary_navigation
    repair_latest_research()
    repair_primary_navigation()
    # publish_clean_urls recreates /catalogue/ from the standalone generator.
    # Restore the shared light shell in the same build, so it cannot be skipped.
    try:
        from tools.repair_unified_site import repair_catalogue
    except ModuleNotFoundError:
        from repair_unified_site import repair_catalogue
    repair_catalogue()

    return {
        "people": len(public_people), "records": len(public_records),
        "withheld": withheld_count, "source_gaps": source_gap_count,
        "places": len(place_index), "pages": len(sitemap_paths),
        "wikitree_evidence_profiles": len(public_wikitree_evidence["profiles"]),
        **record_catalog_stats, **machine_stats,
    }
