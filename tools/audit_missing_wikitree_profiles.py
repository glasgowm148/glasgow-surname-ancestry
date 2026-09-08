#!/usr/bin/env python3
"""Audit unlinked catalogue people against WikiTree's live person search."""

from __future__ import annotations

import argparse
import csv
from datetime import date
from hashlib import sha1
import json
from pathlib import Path
import re
import sys

try:
    from project_paths import (
        MAP_RECORDS, ROOT, WEB_DIR, WIKITREE_CATALOGUE_PROFILE_LINKS, WIKITREE_DATA_DIR,
        atomic_write_text, relation_values,
    )
except ModuleNotFoundError:
    from tools.project_paths import (
        MAP_RECORDS, ROOT, WEB_DIR, WIKITREE_CATALOGUE_PROFILE_LINKS, WIKITREE_DATA_DIR,
        atomic_write_text, relation_values,
    )

try:
    from build_family_map import _record_slug, apply_catalogue_profile_links
except ModuleNotFoundError:
    from tools.build_family_map import _record_slug, apply_catalogue_profile_links

sys.path.insert(0, str(ROOT / "src"))
from wikitree_family_export import post_wikitree  # noqa: E402


PEOPLE_JSON = WEB_DIR / "data" / "people.json"
OUTPUT = WIKITREE_DATA_DIR / "catalogue-profile-audit.json"
NEW_PEOPLE_DIR = ROOT / "surname-research" / "new-people"
FMP_PEOPLE_PATH = ROOT / "research" / "findmypast-glasgow-audit" / "audit-distinct-people.json"
SURNAME_VARIANTS = {"glasgow", "glasco", "glascow", "glasgo", "glascoe", "glassco", "glassgow"}
GENERIC_PLACE_WORDS = {
    "county", "civil", "parish", "townland", "village", "district", "exact",
    "locality", "unproved", "estimated", "ireland", "scotland", "united", "kingdom",
}
KNOWN_DRAFTS = {
    "record-edinburgh-1577-andrew-glasgow": "surname-research/new-people/1577_Scotland_Hirmenschelis_Andrew_Glasgow.md",
    "record-corsoun-1598-robert-glasgow": "surname-research/new-people/1598_Scotland_Corsoun_Robert_Glasgow.md",
    "record-corsoun-1598-marion-glasgow": "surname-research/new-people/1598_Scotland_Corsoun_Marion_Glasgow.md",
    "record-corsoun-1598-janet-glasgow": "surname-research/new-people/1598_Scotland_Corsoun_Janet_Glasgow.md",
    "record-corsoun-1598-isobel-glasgow": "surname-research/new-people/1598_Scotland_Corsoun_Isobel_Glasgow.md",
    "record-john-glasgow-adf7604c1a": "research/Glasgow-3984/1685_Ireland_Maghrebegg_John_Glasgow.md",
    "record-robert-glascow-c6238069c6": "research/Glasgow-4009/1685_Ireland_Belfast_Robert_Glascow.md",
    "record-saltcoats-1637-john-glasgow": "surname-research/new-people/1637_Scotland_Saltcoats_John_Glasgow.md",
    "record-saltcoats-1637-katherine-glasgow": "surname-research/new-people/1637_Scotland_Saltcoats_Katherine_Glasgow.md",
    "record-saltcoats-1637-agnes-glasgow": "surname-research/new-people/1637_Scotland_Saltcoats_Agnes_Glasgow.md",
    "record-james-glasgow-oritor-gentleman-1826-probate-occurrence": "surname-research/new-people/1826_Ireland_Oritor_James_Glasgow.md",
    "record-james-glasgow-killycurragh-1836-probate-occurrence": "surname-research/new-people/1836_Ireland_Killycurragh_James_Glasgow.md",
    "record-john-of-portrush-robert-glasgow-1666": "surname-research/new-people/1666_Scotland_location_unknown_Robert_Glasgow.md",
    "record-north-leith-robert-glasgow-1694": "surname-research/new-people/1694_Scotland_North_Leith_Robert_Glasgow.md",
    "record-fmp-glasgow-cc9a54fb3b86": "surname-research/new-people/1690_Scotland_Edinburgh_James_Glasgow.md",
    "record-fmp-glasgow-59dea07d1fbb": "surname-research/new-people/1696_Scotland_Edinburgh_James_Glasgow.md",
    "record-hugh-glasgow-tamlaght-o-crilly-1740-entry-1272": "surname-research/new-people/1740_Ireland_Tamlaght_O_Crilly_entry_1272_Hugh_Glasgow.md",
    "record-ballybogy-1825-james-glasgow": "surname-research/new-people/1825_Ireland_Ballybogy_James_Glasgow.md",
    "record-ballybogy-1825-james-glasgow-junior": "research/Glasgow-2981/Glasgow-2981.md",
    "record-drumragh-mary-glasgow-1828": "surname-research/new-people/1828_Ireland_Drumragh_Mary_Glasgow.md",
    "record-robert-glasgow-45f84ce490": "surname-research/new-people/1842_Canada_West_Prescott_Robert_Glasgow.md",
    "record-newberry-cleora-glasgow-speers": "surname-research/new-people/1867_United_States_South_Carolina_Newberry_Cleora_Glasgow.md",
    "record-inishrush-lindsey-glasgow-1882": "surname-research/new-people/1882_Ireland_Inishrush_Lindsey_Glasgow.md",
    "record-alexander-glasgow-94245e5bf7": "surname-research/new-people/1893_South_Africa_Cape_Town_Alexander_Glasgow.md",
}
KNOWN_DUPLICATE_PROFILES = {}
FMP_DRAFT_MARKER = re.compile(
    r"^<!-- BEGIN FMP-GLASGOW-(fmp-glasgow-[0-9a-f]+) -->$", re.M | re.I
)
HOLD_BANNER = re.compile(r"^\s*(?:>\s*)?(?:#+\s*)?\*{0,2}HOLD\b", re.M | re.I)
READY_BANNER = re.compile(
    r"^\s*(?:>\s*)?(?:#+\s*)?\*{0,2}(?:READY TO CREATE|CREATE NEW PROFILE)\b",
    re.M | re.I,
)
_FMP_RELATIVES: dict[str, dict[str, str]] | None = None
GIVEN_NAME_EQUIVALENTS = {
    "geo": "george", "jho": "john", "jhone": "john", "jno": "john",
    "margt": "margaret", "michl": "michael", "robt": "robert",
    "wm": "william",
}


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, help="Audit only the first N unlinked entries")
    parser.add_argument(
        "--apply-new-draft-matches", action="store_true",
        help="Save a newly appeared, unique exact-vital match for the next catalogue build.",
    )
    return parser.parse_args()


def year(value: str | None) -> int | None:
    match = re.search(r"\b(1\d{3}|20\d{2})\b", value or "")
    return int(match.group()) if match else None


def discover_drafts(
    draft_dir: Path = NEW_PEOPLE_DIR,
    root: Path = ROOT,
    known_drafts: dict[str, str] | None = None,
) -> dict[str, str]:
    """Map catalogue identities to maintained drafts, including generated FMP files."""
    drafts = dict(KNOWN_DRAFTS if known_drafts is None else known_drafts)
    for path in sorted(draft_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        relative = str(path.relative_to(root))
        for marker in FMP_DRAFT_MARKER.finditer(text):
            catalogue_id = f"record-{marker.group(1).casefold()}"
            existing = drafts.get(catalogue_id)
            if existing and existing != relative:
                raise ValueError(
                    f"Duplicate draft mapping for {catalogue_id}: {existing} and {relative}"
                )
            drafts[catalogue_id] = relative
    return drafts


def load_audit_people(
    people_path: Path = PEOPLE_JSON,
    records_path: Path = MAP_RECORDS,
    draft_paths: dict[str, str] | None = None,
) -> list[dict]:
    """Overlay draft-backed identities from authoritative records onto the last build.

    This lets the duplicate audit run before the one final catalogue rebuild while
    still seeing newly split or newly added documentary identities.
    """
    payload = json.loads(people_path.read_text(encoding="utf-8"))
    current = {
        person["catalogue_id"]: person
        for person in payload.get("people", [])
        if not person.get("profile_ids")
    }
    drafts = draft_paths if draft_paths is not None else discover_drafts()
    active_ids = {
        catalogue_id for catalogue_id, relative in drafts.items()
        if relative.startswith("surname-research/new-people/")
    }
    with records_path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    apply_catalogue_profile_links(rows)
    grouped: dict[str, list[dict]] = {}
    linked_catalogue_ids: set[str] = set()
    unlinked_catalogue_ids: set[str] = set()
    for row in rows:
        supplement = (row.get("supplement_id") or "").strip()
        if supplement:
            catalogue_id = f"record-{_record_slug(supplement)}"
        else:
            key = f"{row.get('person', '')}|{row.get('family_group', '')}"
            catalogue_id = (
                f"record-{_record_slug(row.get('person', 'person'))}-"
                f"{sha1(key.encode()).hexdigest()[:10]}"
            )
        if (row.get("profile_id") or "").strip():
            linked_catalogue_ids.add(catalogue_id)
        else:
            unlinked_catalogue_ids.add(catalogue_id)
            if catalogue_id in active_ids:
                grouped.setdefault(catalogue_id, []).append(row)
    for catalogue_id in linked_catalogue_ids - unlinked_catalogue_ids:
        current.pop(catalogue_id, None)
    for catalogue_id in active_ids:
        current.pop(catalogue_id, None)
    for catalogue_id, record_rows in grouped.items():
        first = record_rows[0]
        birth_date = (first.get("birth_date") or "").strip()
        birth_status = (first.get("birth_status") or "").strip()
        current[catalogue_id] = {
            "catalogue_id": catalogue_id,
            "name": (first.get("person") or "").strip(),
            "birth": " ".join(filter(None, (birth_date, f"({birth_status})" if birth_status else ""))),
            "birth_location": (first.get("birth_location") or "").strip(),
            "death": (first.get("death_date") or "").strip(),
            "death_location": (first.get("death_location") or "").strip(),
            "gender": (first.get("gender") or "").strip(),
            "profile_ids": [],
            "recorded_in": sorted({
                (row.get("record_location") or "").strip() for row in record_rows
                if (row.get("record_location") or "").strip()
            }),
            "regions": sorted({
                (row.get("region") or "").strip() for row in record_rows
                if (row.get("region") or "").strip()
            }),
            "records": [{
                "year": (row.get("year") or "").strip(),
                "association": (row.get("association") or "").strip(),
                "subcluster": (row.get("subcluster") or "").strip(),
                "source_title": (row.get("source_title") or "").strip(),
            } for row in record_rows],
        }
    return sorted(current.values(), key=lambda item: item["catalogue_id"])


def complete_profile_draft(text: str) -> bool:
    """Require the native WikiTree structure expected by the catalogue builder."""
    required = (
        "[[Category:Glasgow Name Study]]",
        "== Biography ==",
        "== Research Notes ==",
        "== Sources ==",
        "<references />",
    )
    return all(item in text for item in required) and bool(re.search(r"<ref(?:\s|>)", text, re.I))


def draft_is_on_hold(text: str) -> bool:
    """Read the status banner, not later prose discussing a reviewed HOLD reason."""
    preamble = text.split("\n# ", 1)[0]
    return bool(HOLD_BANNER.search(preamble))


def draft_is_creation_ready(text: str) -> bool:
    """Honour an explicit reviewed verdict only when it appears in the status preamble."""
    preamble = text.split("\n# ", 1)[0]
    return bool(READY_BANNER.search(preamble))


def free_space_audit_entry(person: dict) -> dict | None:
    """Return a terminal result for evidence deliberately kept off person profiles."""
    if not (
        person.get("wikitree_free_space_url")
        or person.get("profile_disposition") == "free_space_only"
    ):
        return None
    return {
        "catalogue_id": person["catalogue_id"], "name": person["name"],
        "identity_status": "free_space_only",
        "identity_note": person.get("profile_disposition_note") or (
            "This evidence belongs on a supporting WikiTree free-space page; "
            "do not create a person profile."
        ),
        "recommended_action": "do_not_create", "confirmed_profile_id": "",
        "searched_profile_count": 0, "record_year": None,
        "search_terms": [], "candidates": [],
        "draft_path": person.get("free_space_draft_path") or "",
    }


def search_identity(name: str) -> tuple[str, list[str], str]:
    clean = re.sub(r"^Probably\s+", "", name, flags=re.I).strip()
    if re.search(r"\b(?:children|households)\b|\s+and\s+", clean, re.I):
        return "collective_record", [], "This entry represents more than one person."
    if re.match(r"^(?:Mrs|Widow|Unknown|Unidentified)\b", clean, re.I):
        return "insufficient_identity", [], "The record does not supply a usable given and family name."
    if " or " in clean:
        parts = clean.split()
        return "ambiguous_identity", [parts[0]], "The record leaves the person's surname or identity unresolved."
    parts = clean.split()
    if len(parts) < 2:
        return "insufficient_identity", [], "The record does not supply a complete searchable name."
    return "individual", [parts[0]], ""


def search_surname(name: str) -> str:
    if name == "John Glasgow McKeown":
        return "McKeown"
    return "Glasgow"


def live_matches(first_name: str, last_name: str) -> list[dict]:
    matches: dict[str, dict] = {}
    start = 0
    while True:
        envelope = post_wikitree({
            "action": "searchPerson", "FirstName": first_name,
            "LastName": last_name, "start": str(start), "limit": "100",
        })
        page = [item for item in envelope.get("matches", []) if item.get("Name")]
        for item in page:
            matches[item["Name"]] = item
        start += 100
        if start >= int(envelope.get("total") or 0) or not page:
            break
    return list(matches.values())


def surname_values(candidate: dict) -> set[str]:
    values = {
        candidate.get("LastNameAtBirth", ""), candidate.get("LastNameCurrent", ""),
        *(candidate.get("LastNameOther", "") or "").split(","),
    }
    return {re.sub(r"[^a-z]", "", value.casefold()) for value in values if value}


def place_terms(value: str) -> set[str]:
    return {
        token for token in re.findall(r"[a-z]{4,}", (value or "").casefold())
        if token not in GENERIC_PLACE_WORDS
    }


def normal_name(value: str) -> tuple[str, str]:
    """Return conservative given/surname keys for documentary comparisons."""
    parts = re.findall(r"[a-z]+", (value or "").casefold())
    if not parts:
        return "", ""
    given = GIVEN_NAME_EQUIVALENTS.get(parts[0], parts[0])
    surname = parts[-1]
    if surname in SURNAME_VARIANTS:
        surname = "glasgow"
    return given, surname


def fmp_documentary_relatives(person: dict) -> dict[str, str]:
    """Recover named parents from the transcript audit behind a generated record."""
    global _FMP_RELATIVES
    if _FMP_RELATIVES is None:
        _FMP_RELATIVES = {}
        if FMP_PEOPLE_PATH.exists():
            payload = json.loads(FMP_PEOPLE_PATH.read_text(encoding="utf-8"))
            for item in payload.get("people", []):
                relatives: dict[str, str] = {}
                for record in item.get("records", []):
                    fields = record.get("transcript_fields") or {}
                    for role in ("father", "mother"):
                        first = fields.get(f"{role.title()}'s first name(s)") or fields.get(
                            f"{role.title()} first name"
                        )
                        last = fields.get(f"{role.title()}'s last name") or fields.get(
                            f"{role.title()} last name"
                        )
                        name = " ".join(filter(None, (first, last))).strip()
                        if name:
                            relatives[role] = name
                _FMP_RELATIVES[f"record-{item.get('group_id', '').casefold()}"] = relatives
    return _FMP_RELATIVES.get(person.get("catalogue_id", "").casefold(), {})


def candidate_parent_names(candidate: dict) -> dict[str, str]:
    """Read the candidate's attached father/mother names returned by searchPerson."""
    by_role: dict[str, str] = {}
    for parent in relation_values(candidate, "Parents"):
        role = "father" if parent.get("Gender") == "Male" else "mother" if parent.get("Gender") == "Female" else ""
        if role:
            by_role[role] = parent.get("BirthName") or parent.get("LongName") or parent.get("RealName") or ""
    return by_role


def is_birth_event(person: dict) -> bool:
    """Return whether the defining record records this person's birth/baptism."""
    text = " ".join(
        f"{record.get('association', '')} {record.get('subcluster', '')} "
        f"{record.get('source_title', '')}"
        for record in person.get("records", [])
    )
    return bool(re.search(r"\b(?:birth|born|bapti[sz]|christen)", text, re.I))


def candidate_summary(candidate: dict, person: dict, record_year: int | None) -> dict | None:
    candidate_birth = year(candidate.get("BirthDate"))
    candidate_death = year(candidate.get("DeathDate"))
    birth_event = is_birth_event(person)
    if record_year and candidate_birth:
        if birth_event and abs(candidate_birth - record_year) > 2:
            return None
        if not birth_event and not record_year - 100 <= candidate_birth <= record_year - 14:
            return None
    if record_year and candidate_death and candidate_death < record_year:
        return None
    wanted_surname = search_surname(person["name"]).casefold()
    surnames = surname_values(candidate)
    if wanted_surname == "glasgow" and not (surnames & SURNAME_VARIANTS):
        return None
    if birth_event and wanted_surname == "glasgow":
        birth_surname = re.sub(
            r"[^a-z]", "", (candidate.get("LastNameAtBirth") or "").casefold()
        )
        if birth_surname and birth_surname not in SURNAME_VARIANTS:
            return None
    if wanted_surname != "glasgow" and wanted_surname not in surnames:
        return None

    wanted_given = normal_name(person.get("name", ""))[0]
    candidate_given = normal_name(
        candidate.get("FirstName") or candidate.get("RealName") or candidate.get("LongName") or ""
    )[0]
    if wanted_given and candidate_given and wanted_given != candidate_given:
        return None
    subject_gender = (person.get("gender") or person.get("sex") or "").casefold()
    candidate_gender = (candidate.get("Gender") or "").casefold()
    if subject_gender and candidate_gender and subject_gender != candidate_gender:
        return None

    documentary_relatives = person.get("documentary_relatives") or fmp_documentary_relatives(person)
    profile_relatives = candidate_parent_names(candidate)
    exact_relative_roles = []
    for role, documentary_name in documentary_relatives.items():
        profile_name = profile_relatives.get(role, "")
        if not profile_name:
            continue
        if normal_name(documentary_name) != normal_name(profile_name):
            return None
        exact_relative_roles.append(role)

    subject_place = " ".join([
        person.get("birth_location", ""), *person.get("recorded_in", []), *person.get("regions", []),
    ])
    candidate_place = " ".join([candidate.get("BirthLocation", ""), candidate.get("DeathLocation", "")])
    overlap = sorted(place_terms(subject_place) & place_terms(candidate_place))
    score = 45
    if overlap:
        score += min(30, len(overlap) * 15)
    if "ireland" in subject_place.casefold() and "ireland" in candidate_place.casefold():
        score += 15
    estimated_birth = year(person.get("birth"))
    birth_year_match = bool(estimated_birth and candidate_birth and estimated_birth == candidate_birth)
    death_year_match = bool(record_year and candidate_death and record_year == candidate_death)
    if estimated_birth and candidate_birth:
        difference = abs(estimated_birth - candidate_birth)
        score += 15 if difference <= 5 else 10 if difference <= 15 else 5 if difference <= 30 else 0
    if record_year and candidate_death:
        difference = abs(record_year - candidate_death)
        score += 30 if difference == 0 else 20 if difference <= 2 else 10 if difference <= 5 else 0
    if exact_relative_roles:
        score += min(30, len(exact_relative_roles) * 15)
    birth_year_conflict = bool(
        birth_event and record_year and candidate_birth and candidate_birth != record_year
    )
    if birth_year_conflict:
        # A neighbouring child of the same parents is a valuable family lead,
        # but not a duplicate candidate for the documentary child.
        score = min(score, 65)
    return {
        "profile_id": candidate["Name"],
        "name": candidate.get("LongName") or candidate.get("ShortName") or candidate["Name"],
        "birth_date": candidate.get("BirthDate") or "",
        "birth_location": candidate.get("BirthLocation") or "",
        "death_date": candidate.get("DeathDate") or "",
        "death_location": candidate.get("DeathLocation") or "",
        "location_overlap": overlap,
        "birth_year_match": birth_year_match,
        "death_year_match": death_year_match,
        "gender": candidate.get("Gender") or "",
        "exact_relative_roles": exact_relative_roles,
        "birth_year_conflict": birth_year_conflict,
        "score": score,
        "url": f"https://www.wikitree.com/wiki/{candidate['Name']}",
    }


def new_draft_match(candidates: list[dict], previous: dict) -> dict | None:
    """Apply only a pre-authorised exact-vital match, never an unreviewed lead."""
    previous_ids = {item.get("profile_id") for item in previous.get("candidates", [])}
    newly_found = [item for item in candidates if item.get("profile_id") not in previous_ids]
    if (
        previous.get("allow_auto_match") is True
        and len(newly_found) == 1
        and previous.get("recommended_action") in {
            "create_new_profile", "ready_to_create", "needs_sourced_draft",
        }
        and newly_found[0].get("score", 0) >= 75
        and (newly_found[0].get("birth_year_match") or newly_found[0].get("death_year_match"))
    ):
        return newly_found[0]
    return None


def select_candidates(candidates: list[dict], duplicate_ids: set[str] | None = None) -> list[dict]:
    """Keep strong leads, or the best two eligible fallbacks when none clears 65."""
    duplicate_ids = duplicate_ids or set()
    ranked = sorted(
        {item["profile_id"]: item for item in candidates}.values(),
        key=lambda item: (-item["score"], item["profile_id"]),
    )
    if duplicate_ids:
        return [item for item in ranked if item["profile_id"] in duplicate_ids][:8]
    strong = [item for item in ranked if item["score"] > 65]
    return strong[:8] if strong else ranked[:2]


def main() -> int:
    options = arguments()
    draft_paths = discover_drafts()
    people = load_audit_people(draft_paths=draft_paths)
    if options.limit:
        people = people[: options.limit]

    previous_payload = json.loads(OUTPUT.read_text(encoding="utf-8")) if OUTPUT.exists() else {"entries": {}}
    previous_entries = previous_payload.get("entries", {})
    link_payload = (
        json.loads(WIKITREE_CATALOGUE_PROFILE_LINKS.read_text(encoding="utf-8"))
        if WIKITREE_CATALOGUE_PROFILE_LINKS.exists() else {"schema_version": 1, "entries": {}}
    )
    link_entries = link_payload.setdefault("entries", {})
    searches: dict[tuple[str, str], list[dict]] = {}
    entries = {}
    for index, person in enumerate(people, 1):
        destination = link_entries.get(person["catalogue_id"], {})
        if destination.get("profile_disposition") == "free_space_only":
            person["profile_disposition"] = "free_space_only"
            person["profile_disposition_note"] = destination.get("evidence_note") or ""
            person["free_space_draft_path"] = destination.get("free_space_draft_path") or ""
            person["wikitree_free_space_url"] = destination.get("free_space_url") or ""
        free_space_entry = free_space_audit_entry(person)
        if free_space_entry:
            entries[person["catalogue_id"]] = free_space_entry
            print(
                f"[{index}/{len(people)}] {person['name']}: do_not_create; canonical free-space page",
                flush=True,
            )
            continue
        identity_status, first_names, identity_note = search_identity(person["name"])
        candidates = []
        searched = 0
        record_years = [year(record.get("year")) for record in person.get("records", [])]
        record_year = min((value for value in record_years if value), default=None)
        if first_names:
            surname = search_surname(person["name"])
            for first_name in first_names:
                key = (first_name, surname)
                if key not in searches:
                    searches[key] = live_matches(*key)
                searched += len(searches[key])
                candidates.extend(
                    summary for match in searches[key]
                    if (summary := candidate_summary(match, person, record_year))
                )
        duplicate_ids = KNOWN_DUPLICATE_PROFILES.get(person["catalogue_id"], set())
        candidates = select_candidates(candidates, duplicate_ids)
        has_strong_candidate = any(item["score"] > 65 for item in candidates)
        previous = previous_entries.get(person["catalogue_id"], {})
        auto_match = new_draft_match(candidates, previous) if options.apply_new_draft_matches else None
        if auto_match:
            link_entries[person["catalogue_id"]] = {
                "profile_id": auto_match["profile_id"],
                "catalogue_name": person["name"],
                "matched_at": date.today().isoformat(),
                "evidence_note": (
                    "Periodic WikiTree audit applied a previously authorised exact-vital match after the "
                    "documentary identity comparison was reviewed."
                ),
            }
        draft_path = draft_paths.get(person["catalogue_id"], "")
        draft_text = (ROOT / draft_path).read_text(encoding="utf-8") if draft_path else ""
        if duplicate_ids:
            action = "duplicate_profiles"
            identity_note = "This record is already represented by two apparent duplicate WikiTree profiles; do not create a third."
        elif identity_status != "individual":
            action = "do_not_create" if identity_status in {"collective_record", "insufficient_identity"} else "hold"
        elif draft_text and draft_is_on_hold(draft_text):
            action = "hold"
        elif (
            draft_text
            and draft_is_creation_ready(draft_text)
            and complete_profile_draft(draft_text)
        ):
            # Name/place scores produce research leads, not identity proof. A
            # complete READY draft records the manual candidate exclusions.
            action = "create_new_profile"
        elif has_strong_candidate:
            action = "hold"
        elif draft_text and complete_profile_draft(draft_text):
            action = "create_new_profile"
        else:
            action = "needs_sourced_draft"
        entries[person["catalogue_id"]] = {
            "catalogue_id": person["catalogue_id"], "name": person["name"],
            "identity_status": identity_status, "identity_note": identity_note,
            "recommended_action": action, "confirmed_profile_id": auto_match["profile_id"] if auto_match else "",
            "searched_profile_count": searched, "record_year": record_year,
            "search_terms": [f"{first} {search_surname(person['name'])}" for first in first_names],
            "candidates": candidates, "draft_path": draft_path,
        }
        print(f"[{index}/{len(people)}] {person['name']}: {action}; {len(candidates)} candidate(s)", flush=True)

    if options.apply_new_draft_matches:
        atomic_write_text(
            WIKITREE_CATALOGUE_PROFILE_LINKS,
            json.dumps(link_payload, indent=2, ensure_ascii=False) + "\n",
        )
    atomic_write_text(
        OUTPUT,
        json.dumps({
            "schema_version": 1, "audited_at": date.today().isoformat(),
            "method": "Live WikiTree searchPerson exact-name audit with surname variants, chronology and place screening; candidates are leads, not identity proof.",
            "unlinked_count": len(people), "entries": entries,
        }, indent=2, ensure_ascii=False) + "\n",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
