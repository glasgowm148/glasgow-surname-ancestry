#!/usr/bin/env python3
"""Audit unlinked catalogue people against WikiTree's live person search."""

from __future__ import annotations

import argparse
from datetime import date
import json
from pathlib import Path
import re
import sys

try:
    from project_paths import ROOT, WEB_DIR, WIKITREE_CATALOGUE_PROFILE_LINKS, WIKITREE_DATA_DIR
except ModuleNotFoundError:
    from tools.project_paths import ROOT, WEB_DIR, WIKITREE_CATALOGUE_PROFILE_LINKS, WIKITREE_DATA_DIR

sys.path.insert(0, str(ROOT / "src"))
from wikitree_family_export import post_wikitree  # noqa: E402


PEOPLE_JSON = WEB_DIR / "data" / "people.json"
OUTPUT = WIKITREE_DATA_DIR / "catalogue-profile-audit.json"
SURNAME_VARIANTS = {"glasgow", "glasco", "glascow", "glasgo", "glascoe", "glassco", "glassgow"}
GENERIC_PLACE_WORDS = {
    "county", "civil", "parish", "townland", "village", "district", "exact",
    "locality", "unproved", "estimated", "ireland", "scotland", "united", "kingdom",
}
KNOWN_DRAFTS = {
    "record-john-glasgow-adf7604c1a": "research/Glasgow-3984/1685_Ireland_Maghrebegg_John_Glasgow.md",
    "record-jane-glasgow-f9b664dda9": "surname-research/new-people/1831_Ireland_Boveedy_Jane_Glasgow.md",
    "record-robert-glascow-c6238069c6": "research/Glasgow-4009/1685_Ireland_Belfast_Robert_Glascow.md",
    "record-thomas-glasco-76891c1835": "surname-research/new-people/1783_Ireland_Ormond_Quay_Thomas_Glasco.md",
}
KNOWN_DUPLICATE_PROFILES = {}


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


def candidate_summary(candidate: dict, person: dict, record_year: int | None) -> dict | None:
    candidate_birth = year(candidate.get("BirthDate"))
    candidate_death = year(candidate.get("DeathDate"))
    if record_year and candidate_birth and not record_year - 100 <= candidate_birth <= record_year - 14:
        return None
    if record_year and candidate_death and candidate_death < record_year:
        return None
    wanted_surname = search_surname(person["name"]).casefold()
    surnames = surname_values(candidate)
    if wanted_surname == "glasgow" and not (surnames & SURNAME_VARIANTS):
        return None
    if wanted_surname != "glasgow" and wanted_surname not in surnames:
        return None

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
        "score": score,
        "url": f"https://www.wikitree.com/wiki/{candidate['Name']}",
    }


def new_draft_match(candidates: list[dict], previous: dict) -> dict | None:
    """Accept only one newly appeared candidate with the draft's vital fingerprint."""
    previous_ids = {item.get("profile_id") for item in previous.get("candidates", [])}
    newly_found = [item for item in candidates if item.get("profile_id") not in previous_ids]
    if (
        len(newly_found) == 1
        and previous.get("recommended_action") in {"ready_to_create", "needs_sourced_draft"}
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
    payload = json.loads(PEOPLE_JSON.read_text(encoding="utf-8"))
    people = [person for person in payload["people"] if not person.get("profile_ids")]
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
                    "Periodic WikiTree audit found one newly appeared candidate matching the draft's exact vital year "
                    "and chronology/place threshold; inspect if conflicting identity evidence emerges."
                ),
            }
        draft_path = KNOWN_DRAFTS.get(person["catalogue_id"], "")
        draft_text = (ROOT / draft_path).read_text(encoding="utf-8") if draft_path else ""
        if duplicate_ids:
            action = "duplicate_profiles"
            identity_note = "This record is already represented by two apparent duplicate WikiTree profiles; do not create a third."
        elif identity_status != "individual":
            action = "do_not_create" if identity_status in {"collective_record", "insufficient_identity"} else "hold"
        elif has_strong_candidate:
            action = "review_candidates"
        elif draft_path and "**HOLD" not in draft_text:
            action = "ready_to_create"
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
        WIKITREE_CATALOGUE_PROFILE_LINKS.write_text(
            json.dumps(link_payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    OUTPUT.write_text(json.dumps({
        "schema_version": 1, "audited_at": date.today().isoformat(),
        "method": "Live WikiTree searchPerson exact-name audit with surname variants, chronology and place screening; candidates are leads, not identity proof.",
        "unlinked_count": len(people), "entries": entries,
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
