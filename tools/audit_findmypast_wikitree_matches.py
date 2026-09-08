#!/usr/bin/env python3
"""Match distinct Findmypast Glasgow people to WikiTree, conservatively.

The input is deliberately treated as a changing upstream snapshot.  Live API
responses are cached by complete request so a rerun only queries newly added
given-name variants or newly plausible profile IDs.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any

try:
    from project_paths import (
        ROOT,
        SURNAME_PROFILE_INDEX,
        WORKBOOK_PATH,
        atomic_write_csv,
        atomic_write_text,
        merged_onetree_profiles,
    )
except ModuleNotFoundError:
    from tools.project_paths import (
        ROOT,
        SURNAME_PROFILE_INDEX,
        WORKBOOK_PATH,
        atomic_write_csv,
        atomic_write_text,
        merged_onetree_profiles,
    )

sys.path.insert(0, str(ROOT / "src"))
from wikitree_family_export import ExportError, post_wikitree  # noqa: E402
from surname_research_index import load_workbook_profiles  # noqa: E402


AUDIT_DIR = ROOT / "research" / "findmypast-glasgow-audit"
INPUT = AUDIT_DIR / "audit-distinct-people.json"
OUTPUT_JSON = AUDIT_DIR / "audit-wikitree-matches.json"
OUTPUT_CSV = AUDIT_DIR / "audit-wikitree-matches.csv"
CACHE = AUDIT_DIR / "audit-wikitree-api-cache.json"
FIELDS = ",".join([
    "Id", "PageId", "Name", "FirstName", "MiddleName", "RealName", "LongName",
    "BirthName", "LastNameAtBirth", "LastNameCurrent", "LastNameOther", "Nicknames",
    "BirthDate", "BirthLocation", "DeathDate", "DeathLocation", "Father", "Mother",
    "Parents", "Spouses", "DataStatus", "Bio", "Touched",
])
GIVEN_VARIANTS = {
    "wm": ("Wm", "William"),
    "william": ("William", "Wm"),
    "jannet": ("Jannet", "Janet"),
    "janet": ("Janet", "Jannet"),
    "marion": ("Marion", "Marian"),
    "marian": ("Marian", "Marion"),
    "helen": ("Helen", "Ellen", "Hellin"),
    "hellin": ("Hellin", "Helen", "Ellen"),
    "hew": ("Hew", "Hugh"),
    "hugh": ("Hugh", "Hew"),
}
SURNAME_EQUIVALENTS = {
    "cunningham": "cunynghame", "cunyngham": "cunynghame",
    "simpson": "simson", "wyllie": "wylie",
}
GIVEN_EQUIVALENTS = {
    "hew": "hugh", "jannet": "janet", "jon": "john", "jno": "john",
    "margt": "margaret", "margarat": "margaret", "michaell": "michael",
    "robt": "robert", "rot": "robert", "tho": "thomas", "thom": "thomas",
    "wm": "william",
}
SURNAME = "Glasgow"


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--offline", action="store_true", help="Use local data and existing API cache only")
    parser.add_argument("--refresh", action="store_true", help="Refresh cached live API requests")
    parser.add_argument(
        "--before-year",
        type=positive_year,
        metavar="YEAR",
        help=("Match only people whose event_year_end is strictly before YEAR; "
              "write separate pre-YEAR outputs"),
    )
    parser.add_argument(
        "--from-year", type=positive_year, metavar="YEAR",
        help="Range scope: require event_year_start on or after YEAR",
    )
    parser.add_argument(
        "--through-year", type=positive_year, metavar="YEAR",
        help="Range scope: require event_year_end on or before YEAR",
    )
    options = parser.parse_args()
    has_range = options.from_year is not None or options.through_year is not None
    if has_range and (options.from_year is None or options.through_year is None):
        parser.error("--from-year and --through-year must be supplied together")
    if has_range and options.before_year is not None:
        parser.error("--before-year cannot be combined with --from-year/--through-year")
    if has_range and options.from_year > options.through_year:
        parser.error("--from-year must not be later than --through-year")
    return options


def positive_year(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("YEAR must be an integer") from exc
    if parsed < 1 or parsed > 9999:
        raise argparse.ArgumentTypeError("YEAR must be between 1 and 9999")
    return parsed


def validate_scope(before_year: int | None, from_year: int | None,
                   through_year: int | None) -> None:
    if before_year is not None and (
        isinstance(before_year, bool) or not 1 <= before_year <= 9999
    ):
        raise ValueError("before_year must be between 1 and 9999")
    has_range = from_year is not None or through_year is not None
    if has_range and (from_year is None or through_year is None):
        raise ValueError("from_year and through_year must be supplied together")
    if has_range and before_year is not None:
        raise ValueError("before_year cannot be combined with a range")
    if has_range and (
        isinstance(from_year, bool) or isinstance(through_year, bool)
        or not 1 <= from_year <= through_year <= 9999
    ):
        raise ValueError("range years must satisfy 1 <= from_year <= through_year <= 9999")


def output_paths(before_year: int | None, from_year: int | None = None,
                 through_year: int | None = None) -> tuple[Path, Path]:
    validate_scope(before_year, from_year, through_year)
    if from_year is not None and through_year is not None:
        stem = f"audit-wikitree-matches-{from_year}-{through_year}"
        return AUDIT_DIR / f"{stem}.json", AUDIT_DIR / f"{stem}.csv"
    if before_year is None:
        return OUTPUT_JSON, OUTPUT_CSV
    stem = f"audit-wikitree-matches-pre{before_year}"
    return AUDIT_DIR / f"{stem}.json", AUDIT_DIR / f"{stem}.csv"


def scoped_people(people: list[dict], before_year: int | None,
                  from_year: int | None = None,
                  through_year: int | None = None) -> list[dict]:
    validate_scope(before_year, from_year, through_year)
    if before_year is None and from_year is None and through_year is None:
        return people
    invalid = []
    selected = []
    for person in people:
        start_value = person.get("event_year_start")
        end_value = person.get("event_year_end")
        if isinstance(start_value, bool) or isinstance(end_value, bool):
            invalid.append(person.get("group_id") or "<missing group_id>")
            continue
        try:
            event_year_start = int(start_value)
            event_year_end = int(end_value)
        except (TypeError, ValueError):
            invalid.append(person.get("group_id") or "<missing group_id>")
            continue
        if event_year_start > event_year_end:
            invalid.append(person.get("group_id") or "<missing group_id>")
            continue
        if before_year is not None and event_year_end < before_year:
            selected.append(person)
        elif (from_year is not None and through_year is not None
              and event_year_start >= from_year and event_year_end <= through_year):
            selected.append(person)
    if invalid:
        raise ValueError(
            "Cannot apply year scope: missing, invalid, or reversed event range for "
            + ", ".join(invalid)
        )
    return selected


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    atomic_write_text(
        path,
        json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
    )


def clean(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").casefold()).strip()


def words(value: Any) -> set[str]:
    return {part for part in clean(value).split() if len(part) >= 3}


def date_parts(value: Any) -> tuple[int | None, int | None, int | None]:
    text = str(value or "").strip()
    for fmt in ("%Y-%m-%d", "%d %b %Y", "%d %B %Y", "%d/%m/%Y"):
        try:
            parsed = datetime.strptime(text, fmt)
            return parsed.year, parsed.month, parsed.day
        except ValueError:
            pass
    found = re.search(r"\b(1[0-9]{3})\b", text)
    return (int(found.group(1)), None, None) if found else (None, None, None)


def exact_date(left: Any, right: Any) -> bool:
    a, b = date_parts(left), date_parts(right)
    return a[0] is not None and None not in a and a == b


def person_event_dates(person: dict) -> list[str]:
    """Use separately stated birth and baptism dates as identity bridges."""
    values = [str(person.get("event_date") or "")]
    for record in person.get("records", []):
        fields = record.get("transcript_fields") or {}
        values.extend(str(fields.get(label) or "") for label in (
            "Birth date", "Date of birth", "Baptism date", "Christening date",
            "Death date", "Date of death", "Burial date",
        ))
    return list(dict.fromkeys(value for value in values if value))


def name_token(value: Any, *, surname: bool = False) -> str:
    token = clean(value)
    if surname:
        return SURNAME_EQUIVALENTS.get(token, token)
    return GIVEN_EQUIVALENTS.get(token, token)


def year(value: Any) -> int | None:
    return date_parts(value)[0]


def given_variants(person: dict) -> list[str]:
    first = (person.get("first_name") or person.get("name", "").split()[0]).strip()
    variants = GIVEN_VARIANTS.get(clean(first), (first,))
    return list(dict.fromkeys(value for value in variants if value))


def profile_given(profile: dict) -> set[str]:
    values = [profile.get("FirstName"), profile.get("RealName"), profile.get("Nicknames")]
    result: set[str] = set()
    for value in values:
        result.update(clean(value).split())
    expanded = set(result)
    for value in result:
        expanded.update(clean(item) for item in GIVEN_VARIANTS.get(value, ()))
    return expanded


def surname_matches(profile: dict) -> bool:
    values = [profile.get("LastNameAtBirth"), profile.get("LastNameCurrent")]
    values.extend(str(profile.get("LastNameOther") or "").split(","))
    return clean(SURNAME) in {clean(value) for value in values}


def place_evidence(record_place: str, profile_place: str) -> dict:
    record_terms, profile_terms = words(record_place), words(profile_place)
    ignored = {"scotland", "ireland", "england", "kingdom", "county", "shire"}
    specific = record_terms - ignored
    overlap = sorted(record_terms & profile_terms)
    exact_locality = bool(specific and specific & profile_terms)
    return {"record": record_place, "profile": profile_place, "overlap": overlap,
            "exact_locality_bridge": exact_locality}


def relative_pairs(person: dict) -> list[dict]:
    fields: dict[str, str] = {}
    for record in person.get("records", []):
        fields.update(record.get("relative_values") or {})
    pairs = []
    for role in ("Father", "Mother"):
        first = next((v for k, v in fields.items() if clean(k).startswith(clean(role)) and "first name" in clean(k)), "")
        last = next((v for k, v in fields.items() if clean(k).startswith(clean(role)) and "last name" in clean(k)), "")
        if first or last:
            pairs.append({"role": role.lower(), "first_name": first, "last_name": last})
    return pairs


def profile_summary(profile: dict) -> dict:
    return {
        key: profile.get(key) or "" for key in (
            "Name", "LongName", "FirstName", "RealName", "LastNameAtBirth", "LastNameCurrent",
            "LastNameOther", "BirthDate", "BirthLocation", "DeathDate", "DeathLocation",
            "Father", "Mother", "DataStatus", "Touched",
        )
    }


def local_sources() -> tuple[dict[str, dict], list[str]]:
    profiles, paths = merged_onetree_profiles()
    sources = [str(path.relative_to(ROOT)) for path in paths]
    workbook = load_workbook_profiles(WORKBOOK_PATH)
    sources.append(str(WORKBOOK_PATH.relative_to(ROOT)))
    for profile_id, value in workbook.items():
        profiles.setdefault(profile_id, {
            "Name": profile_id,
            "LongName": value.get("display_name") or profile_id,
            "FirstName": (value.get("display_name") or profile_id).split()[0],
            "LastNameAtBirth": SURNAME,
            "BirthDate": value.get("birth_date") or "",
            "BirthLocation": value.get("birth_location") or "",
            "DeathDate": value.get("death_date") or "",
            "DeathLocation": value.get("death_location") or "",
        })
    index = read_json(SURNAME_PROFILE_INDEX, {"profiles": {}})
    sources.append(str(SURNAME_PROFILE_INDEX.relative_to(ROOT)))
    for profile_id, value in index.get("profiles", {}).items():
        profiles.setdefault(profile_id, {
            "Name": profile_id,
            "LongName": value.get("display_name") or profile_id,
            "FirstName": (value.get("display_name") or profile_id).split()[0],
            "LastNameAtBirth": SURNAME,
            "BirthDate": value.get("birth_date") or "",
            "BirthLocation": value.get("birth_location") or "",
            "DeathDate": value.get("death_date") or "",
            "DeathLocation": value.get("death_location") or "",
        })
    return profiles, sources


def candidate_plausibility(person: dict, profile: dict) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    wanted = {clean(value) for value in given_variants(person)}
    if not (wanted & profile_given(profile)):
        return False, ["given name does not match a searched variant"]
    if not surname_matches(profile):
        return False, ["profile has no exact Glasgow surname field"]
    event_year = (person.get("event_year") or year(person.get("event_date"))
                  or person.get("event_year_start"))
    birth_year, death_year = year(profile.get("BirthDate")), year(profile.get("DeathDate"))
    event_type = clean(person.get("event_type"))
    if event_year and birth_year:
        if event_type in {"birth", "baptism"} and abs(event_year - birth_year) > 2:
            return False, ["birth/baptism chronology conflicts"]
        if event_type not in {"birth", "baptism"} and not birth_year <= event_year - 12:
            return False, ["profile is too young for the recorded event"]
    if event_year and death_year and death_year < event_year:
        return False, ["profile death precedes the recorded event"]
    if event_year and birth_year and event_year - birth_year > 100:
        return False, ["profile chronology exceeds 100 years at the recorded event"]
    if event_year and birth_year:
        reasons.append(f"chronologically plausible: profile birth {birth_year}, event {event_year}")
    record_place = " ".join([str(person.get("place") or ""), str(person.get("country") or "")])
    place = place_evidence(record_place, " ".join([
        str(profile.get("BirthLocation") or ""), str(profile.get("DeathLocation") or "")]))
    if event_type in {"birth", "baptism"} and (
        not event_year or not birth_year or abs(event_year - birth_year) > 2
    ):
        return False, ["birth/baptism candidate lacks a close profile birth year"]
    if event_type not in {"birth", "baptism", "death", "burial"} and not place["overlap"]:
        return False, ["non-vital same-name profile has no supporting place overlap"]
    if place["overlap"]:
        reasons.append("place overlap: " + ", ".join(place["overlap"]))
    return True, reasons


def build_numeric_index(profiles: dict[str, dict]) -> dict[str, dict]:
    return {str(value.get("Id")): value for value in profiles.values() if value.get("Id")}


def parents_from_profile(profile: dict, profiles: dict[str, dict]) -> dict[str, dict]:
    numeric = build_numeric_index(profiles)
    parents: dict[str, dict] = {}
    for role, field in (("father", "Father"), ("mother", "Mother")):
        raw = profile.get(field)
        candidate = numeric.get(str(raw)) or profiles.get(str(raw))
        if candidate:
            parents[role] = candidate
    raw_parents = profile.get("Parents") or {}
    iterable = raw_parents.values() if isinstance(raw_parents, dict) else raw_parents if isinstance(raw_parents, list) else []
    for candidate in iterable:
        if not isinstance(candidate, dict):
            continue
        gender = clean(candidate.get("Gender"))
        if gender == "male":
            parents["father"] = candidate
        elif gender == "female":
            parents["mother"] = candidate
    return parents


def relative_evidence(person: dict, profile: dict, profiles: dict[str, dict]) -> dict:
    wanted = relative_pairs(person)
    found = parents_from_profile(profile, profiles)
    comparisons = []
    for relative in wanted:
        candidate = found.get(relative["role"], {})
        candidate_first = candidate.get("FirstName") or candidate.get("RealName") or ""
        candidate_last = candidate.get("LastNameAtBirth") or candidate.get("LastNameCurrent") or ""
        first_match = name_token(relative["first_name"]) == name_token(candidate_first)
        last_match = name_token(relative["last_name"], surname=True) == name_token(candidate_last, surname=True)
        comparisons.append({**relative, "profile_id": candidate.get("Name") or "",
                            "profile_name": candidate.get("LongName") or candidate.get("BirthName") or "",
                            "first_name_match": first_match, "last_name_match": last_match,
                            "exact_match": first_match and last_match})
    return {"record_relatives": wanted, "comparisons": comparisons,
            "all_record_relatives_match": bool(wanted) and all(item["exact_match"] for item in comparisons)}


def evaluate_candidate(person: dict, profile: dict, source: str, all_profiles: dict[str, dict]) -> dict:
    event_type = clean(person.get("event_type"))
    event_date = person.get("event_date") or ""
    if event_type in {"birth", "baptism"}:
        profile_date, profile_place = profile.get("BirthDate") or "", profile.get("BirthLocation") or ""
    elif event_type in {"death", "burial"}:
        profile_date, profile_place = profile.get("DeathDate") or "", profile.get("DeathLocation") or ""
    else:
        profile_date, profile_place = "", ""
    date_match = any(exact_date(value, profile_date) for value in person_event_dates(person))
    place = place_evidence(person.get("place", ""), profile_place)
    relatives = relative_evidence(person, profile, all_profiles)
    # Confirmation requires an exact vital-event date, specific locality, and
    # every named parent. Non-vital records remain candidates until a source
    # on the profile directly bridges that event.
    confirmed = (
        event_type in {"birth", "baptism", "death", "burial"}
        and date_match and place["exact_locality_bridge"]
        and relatives["all_record_relatives_match"]
    )
    missing = []
    if event_type not in {"birth", "baptism", "death", "burial"}:
        missing.append("profile has no structured field for this non-vital event")
    if not date_match:
        missing.append("no exact full event-date bridge")
    if not place["exact_locality_bridge"]:
        missing.append("no exact locality bridge")
    if not relatives["record_relatives"]:
        missing.append("record supplies no relative bridge")
    elif not relatives["all_record_relatives_match"]:
        missing.append("named record relatives do not all resolve exactly on the profile")
    return {
        "profile_id": profile.get("Name") or "",
        "url": f"https://www.wikitree.com/wiki/{profile.get('Name')}",
        "sources": [source],
        "profile": profile_summary(profile),
        "evidence": {
            "event_type": person.get("event_type") or "",
            "record_event_date": event_date,
            "profile_event_date": profile_date,
            "exact_full_date_bridge": date_match,
            "place": place,
            "relatives": relatives,
        },
        "decision": "confirmed_match" if confirmed else "possible_candidate",
        "missing_for_confirmation": missing,
    }


class ApiCache:
    def __init__(self, offline: bool, refresh: bool):
        self.offline, self.refresh = offline, refresh
        self.data = read_json(CACHE, {"schema_version": 1, "requests": {}})
        self.data.setdefault("requests", {})

    @staticmethod
    def key(action: str, params: dict[str, str]) -> str:
        return action + ":" + json.dumps(params, sort_keys=True, separators=(",", ":"))

    def request(self, action: str, params: dict[str, str]) -> dict:
        key = self.key(action, params)
        if (key in self.data["requests"] and not self.refresh
                and self.data["requests"][key].get("status") == "success"):
            return self.data["requests"][key]
        if self.offline:
            return {"status": "not_queried_offline", "queried_at": "", "action": action,
                    "params": params, "response": None, "error": "not present in cache"}
        queried_at = utc_now()
        try:
            response = post_wikitree({"action": action, **params})
            entry = {"status": "success", "queried_at": queried_at, "action": action,
                     "params": params, "response": response, "error": ""}
        except ExportError as exc:
            entry = {"status": "error", "queried_at": queried_at, "action": action,
                     "params": params, "response": None, "error": str(exc)}
        self.data["requests"][key] = entry
        write_json(CACHE, self.data)
        return entry


def search_live(api: ApiCache, first_name: str) -> tuple[list[dict], list[dict]]:
    matches: dict[str, dict] = {}
    outcomes = []
    start = 0
    while True:
        params = {"FirstName": first_name, "LastName": SURNAME, "start": str(start), "limit": "100"}
        outcome = api.request("searchPerson", params)
        response = outcome.get("response") or {}
        page = response.get("matches") or []
        outcomes.append({"given_name": first_name, "start": start, "limit": 100,
                         "status": outcome["status"], "queried_at": outcome.get("queried_at", ""),
                         "error": outcome.get("error", ""), "returned": len(page),
                         "reported_total": response.get("total")})
        if outcome["status"] != "success":
            break
        for profile in page:
            if profile.get("Name"):
                matches[profile["Name"]] = profile
        total = int(response.get("total") or 0)
        start += 100
        if not page or start >= total:
            break
    return list(matches.values()), outcomes


def get_live_profile(api: ApiCache, profile_id: str) -> tuple[dict | None, dict]:
    params = {"key": profile_id, "fields": FIELDS, "bioFormat": "wiki", "resolveRedirect": "1"}
    outcome = api.request("getProfile", params)
    profile = (outcome.get("response") or {}).get("profile")
    status = outcome["status"] if isinstance(profile, dict) else (
        "no_profile_returned" if outcome["status"] == "success" else outcome["status"])
    summary = {"requested_profile_id": profile_id, "status": status,
               "queried_at": outcome.get("queried_at", ""), "error": outcome.get("error", ""),
               "resolved_profile_id": profile.get("Name", "") if isinstance(profile, dict) else ""}
    return (profile if isinstance(profile, dict) else None), summary


def main() -> int:
    options = arguments()
    output_json, output_csv = output_paths(
        options.before_year, options.from_year, options.through_year)
    raw_input = INPUT.read_bytes()
    source = json.loads(raw_input)
    source_people = source.get("people", [])
    people = sorted(scoped_people(
        source_people, options.before_year, options.from_year, options.through_year),
                    key=lambda item: item.get("group_id", ""))
    local, local_paths = local_sources()
    all_profiles = dict(local)
    api = ApiCache(options.offline, options.refresh)
    searches: dict[str, tuple[list[dict], list[dict]]] = {}
    entries = []
    for number, person in enumerate(people, 1):
        local_hits: dict[str, dict] = {}
        for profile_id, profile in local.items():
            plausible, _ = candidate_plausibility(person, profile)
            if plausible:
                local_hits[profile_id] = profile
        # Retain candidates already discovered by the upstream grouping even
        # if sparse index metadata is insufficient for heuristic selection.
        for profile_id in person.get("local_wikitree_candidate_ids", []):
            if profile_id in local:
                local_hits[profile_id] = local[profile_id]

        live_hits: dict[str, dict] = {}
        search_outcomes = []
        search_terms = []
        for first_name in given_variants(person):
            search_terms.append({"first_name": first_name, "last_name": SURNAME})
            if first_name not in searches:
                searches[first_name] = search_live(api, first_name)
            found, outcomes = searches[first_name]
            search_outcomes.extend(outcomes)
            for profile in found:
                plausible, _ = candidate_plausibility(person, profile)
                if plausible:
                    live_hits[profile["Name"]] = profile

        plausible_ids = sorted(set(local_hits) | set(live_hits))
        profile_outcomes = []
        detailed: dict[str, dict] = {}
        for profile_id in plausible_ids:
            live_profile, outcome = get_live_profile(api, profile_id)
            profile_outcomes.append(outcome)
            profile = live_profile or local_hits.get(profile_id) or live_hits.get(profile_id)
            if profile:
                detailed[profile.get("Name") or profile_id] = profile
                all_profiles[profile.get("Name") or profile_id] = profile

        candidates: dict[str, dict] = {}
        for profile_id, profile in detailed.items():
            sources = []
            if profile_id in local_hits:
                sources.append("local_export_or_profile_index")
            if profile_id in live_hits or any(item["resolved_profile_id"] == profile_id and item["status"] == "success" for item in profile_outcomes):
                sources.append("live_wikitree_api")
            evaluated = evaluate_candidate(person, profile, sources[0] if sources else "candidate_search", all_profiles)
            evaluated["sources"] = sources
            candidates[profile_id] = evaluated

        confirmed = sorted(key for key, value in candidates.items() if value["decision"] == "confirmed_match")
        all_search_success = bool(search_outcomes) and all(item["status"] == "success" for item in search_outcomes)
        all_profile_success = all(item["status"] == "success" for item in profile_outcomes)
        if len(confirmed) == 1:
            status = "confirmed_match"
        elif len(confirmed) > 1:
            status = "conflicting_confirmed_fingerprints_review_required"
        elif candidates and all_search_success and all_profile_success:
            status = "no_confirmed_match_candidates_only"
        elif not candidates and all_search_success and all_profile_success:
            status = "no_wikitree_match_found"
        else:
            status = "no_match_established_live_search_incomplete"
        entries.append({
            "group_id": person.get("group_id") or "",
            "person": {key: person.get(key) for key in ("name", "first_name", "last_name", "event_type", "event_date", "event_year", "place", "country", "record_ids")},
            "status": status,
            "confirmed_profile_ids": confirmed,
            "search_terms": search_terms,
            "search_outcomes": search_outcomes,
            "get_profile_outcomes": profile_outcomes,
            "candidate_count": len(candidates),
            "candidates": [candidates[key] for key in sorted(candidates)],
            "no_match_status": "not_applicable_confirmed" if confirmed else status,
        })
        print(f"[{number}/{len(people)}] {person.get('name')}: {status} ({len(candidates)} candidates)", flush=True)

    query_times = sorted({item.get("queried_at") for entry in entries for item in entry["search_outcomes"] + entry["get_profile_outcomes"] if item.get("queried_at")})
    complete = all(
        entry["status"] not in {"no_match_established_live_search_incomplete", "conflicting_confirmed_fingerprints_review_required"}
        for entry in entries
    )
    if options.before_year is not None:
        scope = {
            "mode": "event_year_end_before", "before_year": options.before_year,
            "predicate": f"event_year_end < {options.before_year}",
        }
    elif options.from_year is not None and options.through_year is not None:
        scope = {
            "mode": "event_year_range",
            "from_year": options.from_year, "through_year": options.through_year,
            "predicate": (
                f"event_year_start >= {options.from_year} and "
                f"event_year_end <= {options.through_year}"
            ),
        }
    else:
        scope = {"mode": "all_people", "predicate": "all source people"}
    scope.update({
        "selected_people_count": len(people),
        "excluded_people_count": len(source_people) - len(people),
    })
    payload = {
        "schema_version": 1,
        "source_file": str(INPUT.relative_to(ROOT)),
        "source_sha256": hashlib.sha256(raw_input).hexdigest(),
        "source_people_count": len(source_people),
        "scope": scope,
        "source_audit_complete_and_reconciled": source.get("summary", {}).get("audit_complete_and_reconciled", False),
        "provisional": not source.get("summary", {}).get("audit_complete_and_reconciled", False),
        "matching_audit_complete_for_snapshot": complete,
        "query_timestamp_range": [query_times[0], query_times[-1]] if query_times else [],
        "method": {
            "local": "Merged One Tree exports plus surname-research/indexes/profiles.json.",
            "live": "WikiTree searchPerson, all pages of 100 per given-name variant; getProfile(resolveRedirect=1) for every plausible candidate; responses cached by exact request.",
            "confirmation_rule": "Confirm only one exact vital-event full-date, specific-place, and named-relative fingerprint. Non-vital events and incomplete fingerprints remain candidates.",
        },
        "local_sources": local_paths,
        "counts": {
            "people": len(entries),
            "confirmed_matches": sum(entry["status"] == "confirmed_match" for entry in entries),
            "candidate_only": sum(entry["status"] == "no_confirmed_match_candidates_only" for entry in entries),
            "no_match_found": sum(entry["status"] == "no_wikitree_match_found" for entry in entries),
            "live_search_incomplete": sum(entry["status"] == "no_match_established_live_search_incomplete" for entry in entries),
            "conflicting_confirmed": sum(entry["status"] == "conflicting_confirmed_fingerprints_review_required" for entry in entries),
        },
        "people": entries,
    }
    write_json(output_json, payload)
    fieldnames = [
        "group_id", "name", "event_type", "event_date", "place", "status",
        "no_match_status", "profile_id", "candidate_decision", "exact_date",
        "exact_locality", "exact_relatives", "missing_for_confirmation",
        "profile_url",
    ]
    csv_rows = []
    for entry in entries:
        rows = entry["candidates"] or [None]
        for candidate in rows:
            evidence = candidate["evidence"] if candidate else {}
            csv_rows.append({
                "group_id": entry["group_id"], "name": entry["person"]["name"],
                "event_type": entry["person"]["event_type"], "event_date": entry["person"]["event_date"],
                "place": entry["person"]["place"], "status": entry["status"],
                "no_match_status": entry["no_match_status"],
                "profile_id": candidate["profile_id"] if candidate else "",
                "candidate_decision": candidate["decision"] if candidate else "no_candidate",
                "exact_date": evidence.get("exact_full_date_bridge", ""),
                "exact_locality": evidence.get("place", {}).get("exact_locality_bridge", ""),
                "exact_relatives": evidence.get("relatives", {}).get("all_record_relatives_match", ""),
                "missing_for_confirmation": "; ".join(candidate["missing_for_confirmation"]) if candidate else "",
                "profile_url": candidate["url"] if candidate else "",
            })
    atomic_write_csv(output_csv, fieldnames, csv_rows, encoding="utf-8")
    return 0 if complete else 2


if __name__ == "__main__":
    raise SystemExit(main())
