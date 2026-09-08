#!/usr/bin/env python3
"""Enrich mapped historical people from WikiTree's public read-only API.

The default cohort is every linked profile associated with an Irish mapped
record before 1700, plus comparable profiles in the One-Tree export and recent
profile supplement. Full WikiTree biography markup is retained as profile
evidence, never promoted to independent documentary proof.
"""

from __future__ import annotations

import argparse
import csv
from datetime import date, datetime, timezone
from html import unescape
import json
import re
import sys
from pathlib import Path

from project_paths import (
    MAP_RECENT_PROFILE_SUPPLEMENT,
    MAP_RECORDS,
    RESEARCH_DIR,
    ROOT,
    SRC_DIR,
    WIKITREE_PROFILE_EVIDENCE,
    atomic_write_text,
    merged_map_profiles,
)

sys.path.insert(0, str(SRC_DIR))

from wikitree_family_export import (  # noqa: E402
    ExportError,
    FIELDS,
    RELATION_NAMES,
    get_people,
    load_research_case,
    merge_profile,
    post_wikitree,
    set_research_target_status,
    store_research_capture,
    update_research_outputs,
    write_json_file,
)


WIKITREE_ID = re.compile(r"[A-Za-z][A-Za-z_'’]*(?:-[A-Za-z][A-Za-z_'’]*)*-\d+")
IRISH_PLACE = re.compile(
    r"\b(?:ireland|ulster|antrim|armagh|carlow|cavan|clare|cork|derry|donegal|"
    r"down|dublin|fermanagh|galway|kerry|kildare|kilkenny|laois|leitrim|"
    r"limerick|londonderry|longford|louth|mayo|meath|monaghan|offaly|"
    r"roscommon|sligo|tipperary|tyrone|waterford|westmeath|wexford|wicklow)\b",
    re.I,
)
URL = re.compile(r"https?://[^\s<>\]\[|}\"']+")
GLASGOW_NAMES = {"glasgow", "glascow", "glasco", "glascoe", "glasgo", "glassgo", "glasko"}
RECORD_TERMS = re.compile(
    r"\b(?:bapti[sz]|birth|born|christen|marri|death|died|burial|grave|cemetery|"
    r"will\b|probate|testament|deed|memorial|lease|rent|register|census|hearth|"
    r"tax|residen|occup|land|court|parish|church|minister|rector|clerk|merchant|"
    r"source|archive|record|roll|calendar|volume|folio|page|reference)\w*",
    re.I,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profiles", nargs="+", metavar="WIKITREE_ID")
    parser.add_argument(
        "--scope", choices=("irish-pre-1700", "all-historical"),
        default="irish-pre-1700",
    )
    parser.add_argument("--cutoff", type=int, default=1700)
    parser.add_argument("--batch-size", type=int, default=50)
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--no-research-cases", action="store_true")
    return parser.parse_args()


def year(value: object) -> int | None:
    match = re.match(r"^(\d{4})", str(value or ""))
    return int(match.group(1)) if match and match.group(1) != "0000" else None


def irish_pre_cutoff_cohort(cutoff: int) -> list[str]:
    ids: set[str] = set()
    with MAP_RECORDS.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            try:
                filter_year = int(float(row.get("filter_year") or 9999))
            except ValueError:
                continue
            if row.get("region") == "Ireland" and filter_year < cutoff:
                ids.update(WIKITREE_ID.findall(row.get("profile_id", "")))

    profiles, _ = merged_map_profiles()
    for profile in profiles.values():
        birth_year = year(profile.get("BirthDate"))
        locations = " | ".join(
            str(profile.get(field) or "")
            for field in ("BirthLocation", "DeathLocation")
        )
        surname_values = {
            str(profile.get(field) or "").casefold()
            for field in ("LastNameAtBirth", "LastNameCurrent")
        }
        if (
            birth_year is not None
            and birth_year < cutoff
            and IRISH_PLACE.search(locations)
            and surname_values & GLASGOW_NAMES
        ):
            ids.add(profile["Name"])

    if MAP_RECENT_PROFILE_SUPPLEMENT.exists():
        supplement = json.loads(MAP_RECENT_PROFILE_SUPPLEMENT.read_text(encoding="utf-8"))
        for profile in supplement.get("profiles", []):
            profile_id = profile.get("profile_id") or ""
            events = profile.get("events") or []
            if (
                profile_id
                and int(profile.get("filter_year") or 9999) < cutoff
                and any(event.get("region") == "Ireland" for event in events)
            ):
                ids.update(WIKITREE_ID.findall(profile_id))
    return sorted(ids, key=lambda value: (value.rsplit("-", 1)[0], int(value.rsplit("-", 1)[1])))


def all_historical_cohort() -> list[str]:
    profiles, _ = merged_map_profiles()
    minimum_record_year: dict[str, int] = {}
    ids: set[str] = set()
    with MAP_RECORDS.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            if row.get("family_group") == "Associated person":
                continue
            try:
                record_year = int(float(row.get("filter_year") or 9999))
            except ValueError:
                record_year = 9999
            for profile_id in WIKITREE_ID.findall(row.get("profile_id", "")):
                ids.add(profile_id)
                minimum_record_year[profile_id] = min(
                    minimum_record_year.get(profile_id, 9999), record_year
                )

    cutoff = date.today().year - 120
    historical = []
    for profile_id in ids:
        profile = profiles.get(profile_id, {})
        death_date = str(profile.get("DeathDate") or "")
        if (death_date and not death_date.startswith("0000")) or profile.get("DeathLocation"):
            historical.append(profile_id)
            continue
        birth_year = year(profile.get("BirthDate"))
        if birth_year is not None and birth_year < cutoff:
            historical.append(profile_id)
            continue
        if birth_year is None and minimum_record_year.get(profile_id, 9999) < cutoff:
            historical.append(profile_id)
    return sorted(historical, key=lambda value: (value.rsplit("-", 1)[0], int(value.rsplit("-", 1)[1])))


def chunks(values: list[str], size: int):
    for start in range(0, len(values), size):
        yield values[start : start + size]


def relation_values(person: dict, relation: str) -> list[dict]:
    raw = person.get(relation) or {}
    values = raw.values() if isinstance(raw, dict) else raw if isinstance(raw, list) else []
    return [value for value in values if isinstance(value, dict)]


def extract_person_items(envelope: dict) -> list[dict]:
    items = envelope.get("items")
    if not isinstance(items, list):
        raise RuntimeError("WikiTree getRelatives returned no items collection")
    return [item for item in items if isinstance(item, dict) and isinstance(item.get("person"), dict)]


def clean_wikitext(value: str) -> str:
    value = re.sub(r"<!--.*?-->", " ", value, flags=re.S)
    value = re.sub(r"\[\[Category:[^\]]+\]\]", " ", value, flags=re.I)
    value = re.sub(r"\{\{[^{}]*\}\}", " ", value)
    value = re.sub(r"\[\[([^\]|]+)\|([^\]]+)\]\]", r"\2", value)
    value = re.sub(r"\[\[([^\]]+)\]\]", r"\1", value)
    value = re.sub(r"\[(https?://\S+)\s+([^\]]+)\]", r"\2 (\1)", value)
    value = re.sub(r"</?(?:ref|references)\b[^>]*>", " ", value, flags=re.I)
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"'{2,5}", "", value)
    value = re.sub(r"^\s*=+\s*(.*?)\s*=+\s*$", r"\1", value, flags=re.M)
    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r"\n\s*\n\s*\n+", "\n\n", value)
    return unescape(value).strip()


def source_items(bio: str) -> list[dict]:
    candidates = re.findall(r"<ref\b[^>]*>(.*?)</ref>", bio, flags=re.I | re.S)
    sections = re.split(r"^\s*==+\s*Sources?\s*==+\s*$", bio, flags=re.I | re.M)
    if len(sections) > 1:
        candidates.extend(
            line.strip().lstrip("*# ")
            for line in sections[-1].splitlines()
            if line.strip().startswith(("*", "#", "<ref"))
        )
    found: list[dict] = []
    seen: set[str] = set()
    for raw in candidates:
        citation = clean_wikitext(raw)
        if not citation or citation.casefold() in {"see also:", "source:"}:
            continue
        key = re.sub(r"\s+", " ", citation).casefold()
        if key in seen:
            continue
        seen.add(key)
        found.append({"citation": citation, "urls": list(dict.fromkeys(URL.findall(raw)))})
    return found


def record_passages(bio: str) -> list[str]:
    passages = []
    for paragraph in re.split(r"\n\s*\n", clean_wikitext(bio)):
        paragraph = re.sub(r"\s+", " ", paragraph).strip().lstrip("*# ")
        if len(paragraph) >= 25 and RECORD_TERMS.search(paragraph):
            passages.append(paragraph)
    return list(dict.fromkeys(passages))


def template_names(profile: dict, bio: str) -> list[str]:
    names = set(re.findall(r"\{\{\s*([^|}\n]+)", bio))
    raw = profile.get("Templates") or []
    values = raw.values() if isinstance(raw, dict) else raw if isinstance(raw, list) else []
    for value in values:
        if isinstance(value, str):
            names.add(value)
        elif isinstance(value, dict):
            names.add(str(value.get("name") or value.get("Name") or ""))
    return sorted(name.strip() for name in names if name.strip())


def categories(profile: dict, bio: str) -> list[str]:
    found = set(re.findall(r"\[\[Category:\s*([^\]|]+)", bio, flags=re.I))
    raw = profile.get("Categories") or []
    values = raw.keys() if isinstance(raw, dict) else raw if isinstance(raw, list) else []
    for value in values:
        if isinstance(value, str):
            found.add(value.removeprefix("Category:"))
    return sorted(value.strip() for value in found if value.strip())


def related_profile(value: dict) -> dict:
    display_name = (
        value.get("LongName") or value.get("BirthName")
        or " ".join(
            part for part in (
                value.get("Prefix"), value.get("FirstName") or value.get("RealName"),
                value.get("MiddleName"), value.get("LastNameCurrent") or value.get("LastNameAtBirth"),
                value.get("Suffix"),
            ) if part
        )
        or value.get("Name") or ""
    )
    return {
        "id": value.get("Name") or "",
        "name": display_name,
        "birth_date": value.get("BirthDate") or "",
        "birth_location": value.get("BirthLocation") or "",
        "death_date": value.get("DeathDate") or "",
        "death_location": value.get("DeathLocation") or "",
        "marriage_date": value.get("marriage_date") or value.get("MarriageDate") or "",
        "marriage_location": value.get("marriage_location") or value.get("MarriageLocation") or "",
    }


def profile_evidence(profile: dict, person: dict, captured_at: str) -> dict:
    bio = profile.get("Bio") if isinstance(profile.get("Bio"), str) else profile.get("bio") or ""
    relation_map = {
        relation.casefold(): [related_profile(value) for value in relation_values(person, relation)]
        for relation in RELATION_NAMES
    }
    location_claims = []
    for event, location in (
        ("birth", profile.get("BirthLocation")),
        ("death", profile.get("DeathLocation")),
    ):
        if location:
            location_claims.append({"event": event, "location": location, "status": "WikiTree profile field"})
    for spouse in relation_map["spouses"]:
        if spouse["marriage_location"]:
            location_claims.append({
                "event": "marriage", "location": spouse["marriage_location"],
                "date": spouse["marriage_date"], "related_profile_id": spouse["id"],
                "status": "WikiTree relationship field",
            })
    return {
        "profile_id": profile.get("Name") or person.get("Name") or "",
        "profile_url": f"https://www.wikitree.com/wiki/{profile.get('Name') or person.get('Name')}",
        "captured_at": captured_at,
        "last_updated": profile.get("Touched") or "",
        "created": profile.get("Created") or "",
        "privacy": profile.get("Privacy"),
        "connected": bool(profile.get("Connected")),
        "profile_fields": {
            field: profile.get(field)
            for field in (
                "Id", "PageId", "Name", "FirstName", "MiddleName", "MiddleInitial",
                "LastNameAtBirth", "LastNameCurrent", "LastNameOther", "Nicknames",
                "RealName", "ShortName", "LongName", "BirthName", "Prefix", "Suffix",
                "Gender", "BirthDate", "BirthLocation", "DeathDate", "DeathLocation",
                "Father", "Mother", "DataStatus", "Privacy", "Connected", "Created",
                "Touched", "HasChildren", "NoChildren", "childrenCount", "yDNA", "auDNA",
            )
            if profile.get(field) not in (None, "", [], {})
        },
        "categories": categories(profile, bio),
        "templates": template_names(profile, bio),
        "location_claims": location_claims,
        "relations": relation_map,
        "biography_text": clean_wikitext(bio),
        "biography_wikitext": bio,
        "record_passages": record_passages(bio),
        "sources": source_items(bio),
        "external_urls": list(dict.fromkeys(URL.findall(bio))),
        "evidence_status": "WikiTree profile narrative and citations; verify each cited underlying record independently.",
    }


def main() -> int:
    options = parse_args()
    if options.profiles:
        targets = sorted(set(options.profiles))
        scope = "Explicit WikiTree profile selection"
    elif options.scope == "all-historical":
        targets = all_historical_cohort()
        scope = "Every linked historical/deceased person in the public map catalogue"
    else:
        targets = irish_pre_cutoff_cohort(options.cutoff)
        scope = f"Linked profiles with Irish mapped/profile evidence before {options.cutoff}"
    if not targets:
        raise SystemExit("No target WikiTree profiles were selected")

    existing = {"schema_version": 1, "profiles": {}}
    if WIKITREE_PROFILE_EVIDENCE.exists():
        existing = json.loads(WIKITREE_PROFILE_EVIDENCE.read_text(encoding="utf-8"))
    evidence_profiles = existing.setdefault("profiles", {})
    pending = targets if options.refresh else [target for target in targets if target not in evidence_profiles]
    captured_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    captured_this_run = []
    failures = []

    def persist() -> None:
        display_names = {}
        for profile_id, evidence in evidence_profiles.items():
            fields = evidence.get("profile_fields") or {}
            display_names[profile_id] = (
                fields.get("LongName") or fields.get("BirthName")
                or " ".join(
                    part for part in (
                        fields.get("Prefix"), fields.get("FirstName") or fields.get("RealName"),
                        fields.get("MiddleName"), fields.get("LastNameCurrent") or fields.get("LastNameAtBirth"),
                        fields.get("Suffix"),
                    ) if part
                )
                or profile_id
            )
        for evidence in evidence_profiles.values():
            for relatives in (evidence.get("relations") or {}).values():
                for relative in relatives:
                    if relative.get("id") in display_names:
                        relative["name"] = display_names[relative["id"]]
        existing.update({
            "schema_version": 1,
            "generated_at": captured_at,
            "scope": scope,
            "cohort_profile_ids": targets,
            "captured_profile_ids": [target for target in targets if target in evidence_profiles],
            "failures": failures,
        })
        atomic_write_text(
            WIKITREE_PROFILE_EVIDENCE,
            json.dumps(existing, ensure_ascii=False, indent=2) + "\n",
        )

    batch_total = (len(pending) + options.batch_size - 1) // options.batch_size
    for batch_number, batch in enumerate(chunks(pending, options.batch_size), start=1):
        try:
            relatives = post_wikitree({
                "action": "getRelatives", "keys": ",".join(batch),
                "fields": "Id,PageId,Name,FirstName,MiddleName,LastNameAtBirth,LastNameCurrent,RealName,LongName,BirthName,BirthDate,BirthLocation,DeathDate,DeathLocation,Father,Mother",
                "getParents": "1", "getChildren": "1", "getSiblings": "1", "getSpouses": "1",
            })
            items = extract_person_items(relatives)
            by_requested = {
                str(item.get("user_name") or item["person"].get("Name")): item
                for item in items
            }
            for missing_target in [target for target in batch if target not in by_requested]:
                try:
                    fallback = post_wikitree({
                        "action": "getProfile", "key": missing_target,
                        "fields": ",".join(FIELDS), "bioFormat": "wiki",
                        "resolveRedirect": "1",
                    })
                except ExportError as exc:
                    failures.append({"profile_id": missing_target, "error": str(exc)})
                    continue
                fallback_profile = fallback.get("profile")
                if isinstance(fallback_profile, dict) and fallback_profile.get("Name"):
                    by_requested[missing_target] = {
                        "person": fallback_profile, "user_name": missing_target,
                    }
            all_names = set(batch)
            for item in items:
                person = item["person"]
                if person.get("Name"):
                    all_names.add(person["Name"])
                for relation in RELATION_NAMES:
                    all_names.update(
                        value["Name"] for value in relation_values(person, relation) if value.get("Name")
                    )
            full_profiles = get_people(sorted(all_names))
        except ExportError as exc:
            failures.extend({"profile_id": target, "error": str(exc)} for target in batch)
            persist()
            print(f"Batch {batch_number}/{batch_total}: API ERROR {exc}", file=sys.stderr, flush=True)
            break

        for target in batch:
            item = by_requested.get(target)
            if not item:
                if not any(failure["profile_id"] == target for failure in failures):
                    failures.append({"profile_id": target, "error": "No public profile returned"})
                continue
            person = item["person"]
            subject_name = person.get("Name") or target
            profile = dict(full_profiles.get(subject_name, person))
            for relation in RELATION_NAMES:
                raw = person.get(relation) or {}
                if isinstance(raw, dict):
                    profile[relation] = {
                        str(key): merge_profile(value, full_profiles)
                        for key, value in raw.items() if isinstance(value, dict)
                    }
                elif isinstance(raw, list):
                    profile[relation] = [
                        merge_profile(value, full_profiles) for value in raw if isinstance(value, dict)
                    ]
                else:
                    profile[relation] = {}
            item["person"] = profile
            evidence_profiles[subject_name] = profile_evidence(profile, profile, captured_at)
            captured_this_run.append(subject_name)

            if not options.no_research_cases and options.scope == "irish-pre-1700":
                case_dir = RESEARCH_DIR / subject_name
                state, plan = load_research_case(case_dir, subject_name)
                store_research_capture(
                    case_dir, state, {"items": [item]}, subject_name,
                    "wikitree-api-irish-pre-1700",
                )
                set_research_target_status(
                    plan, "wikitree", subject_name, "complete",
                    "Public profile, biography, sources and immediate relationships captured through the WikiTree API.",
                )
                write_json_file(case_dir / "research_state.json", state)
                write_json_file(case_dir / "research_plan.json", plan)
                update_research_outputs(case_dir, state, plan)
        persist()
        print(
            f"Batch {batch_number}/{batch_total}: {len(captured_this_run)}/{len(pending)} refreshed",
            flush=True,
        )

    persist()
    captured = [target for target in targets if target in evidence_profiles]
    print(
        f"WikiTree evidence: {len(captured)}/{len(targets)} profiles "
        f"({len(captured_this_run)} refreshed); "
        f"{sum(len(evidence_profiles[p]['sources']) for p in captured)} source entries; "
        f"{sum(len(evidence_profiles[p]['external_urls']) for p in captured)} external URLs"
    )
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
