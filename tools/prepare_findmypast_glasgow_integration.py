#!/usr/bin/env python3
"""Prepare transcript-validated Findmypast Glasgow people for integration.

This is deliberately a local, deterministic preparation step.  It does not
change catalogue records, findings, drafts, or registers, and local WikiTree
matches remain review leads rather than asserted identities.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

try:
    from project_paths import ROOT, SURNAME_PROFILE_INDEX, merged_onetree_profiles
except ModuleNotFoundError:
    from tools.project_paths import ROOT, SURNAME_PROFILE_INDEX, merged_onetree_profiles


DEFAULT_DIR = ROOT / "research" / "findmypast-glasgow-audit"
IDENTITY_CLUSTERS_FILE = "record-identity-clusters.json"
SURNAME_VARIANTS = {
    "glasgow", "glasco", "glascow", "glasgo", "glascoe", "glassco", "glassgow",
}
PLACE_STOPWORDS = {
    "and", "county", "country", "great", "kingdom", "parish", "scotland",
    "ireland", "england", "united", "the", "shire", "record", "records",
}
GIVEN_ALIASES = {
    "jas": "james", "jno": "john", "margt": "margaret", "natl": "nathaniel",
    "patk": "patrick", "robt": "robert", "thos": "thomas", "willm": "william",
    "wm": "william",
}
PLACE_OR_OFFICE_TITLES = {
    "abbot of", "archbishop of", "archdeacon of", "bishop of", "canon of",
    "deacon of", "dean of", "minister of", "provost of", "rector of", "vicar of",
}
NON_PERSON_GIVENS = {
    "mr", "mrs", "miss", "unknown", "unnamed", "wid", "widd", "widow",
    "wife", "relict",
}
DATE_YEAR_FIELDS = (
    "Event year", "Year", "Baptism year", "Birth year", "Marriage year",
    "Death year", "Burial year", "Residence year",
)
DATE_FIELDS = (
    "Event date", "Date", "Baptism date", "Birth date", "Marriage date",
    "Death date", "Burial date",
)
REFERENCE_FIELDS = ("Archive reference", "Archive Reference", "Reference", "Item", "Page")
RELATIVE_PREFIXES = ("father", "mother", "spouse", "principal")
DAILY_LIMIT_REASON = (
    "temporary Findmypast daily limit blocked transcript access; "
    "retry after the daily allowance resets"
)
CSV_COLUMNS = (
    "group_id", "supplement_id", "name", "event_type", "event_date", "event_year",
    "temporal_basis", "event_year_start", "event_year_end", "place", "country",
    "record_ids", "record_count", "duplicate_group_reason", "record_sets",
    "source_urls", "image_urls", "detail_captured_at", "transcript_titles",
    "transcript_fields_json", "local_wikitree_candidate_ids",
    "local_wikitree_candidates_json",
)


def clean(value: Any) -> str:
    if value is None:
        return ""
    value = str(value).strip()
    return "" if value in {"", "-", "—"} else value


def norm(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", clean(value).casefold()).strip()


def is_daily_limit(detail: dict[str, Any] | None) -> bool:
    """Treat a fair-use limit as temporary, not a record subscription lock."""
    return norm((detail or {}).get("block_reason")) == "daily limit"


def slug(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "-", clean(value).casefold()).strip("-")


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def provenance_path(path: Path) -> str:
    """Keep repository paths portable while allowing isolated audit checks."""
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def explicit_years(value: Any) -> list[int]:
    """Return unabridged historical years, including supported pre-1000 dates.

    One- and two-digit values are deliberately excluded: modern indexes in
    this scrape use values such as ``29`` and ``78`` for truncated years.
    """
    return [int(part) for part in re.findall(r"(?<!\d)(\d{3,4})(?!\d)", clean(value))]


def usable_given(value: Any) -> bool:
    return bool(re.search(r"[A-Za-z]", clean(value))) and norm(value) not in NON_PERSON_GIVENS


def first_present(fields: dict[str, Any], labels: tuple[str, ...]) -> tuple[str, str]:
    for label in labels:
        if clean(fields.get(label)):
            return label, clean(fields[label])
    return "", ""


def surname_verdict(detail: dict[str, Any]) -> tuple[bool, str]:
    if is_daily_limit(detail):
        return False, DAILY_LIMIT_REASON
    if clean(detail.get("access_status")) != "accessible":
        return False, f"detail access status is {clean(detail.get('access_status')) or 'missing'}"
    if norm(detail.get("surname_status")) != "confirmed":
        return False, f"full-record surname verdict is {clean(detail.get('surname_status')) or 'missing'}"
    fields = detail.get("transcript_fields") or {}
    last_name = first_present(fields, ("Last name", "Last name(s)", "Surname"))[1]
    if norm(last_name) != "glasgow":
        return False, "transcript does not give exact Glasgow in a personal last-name field"
    first_name = first_present(fields, ("First name(s)", "First name", "Forename(s)"))[1]
    first_norm = norm(first_name)
    if first_norm.endswith((" of", " in", " at")):
        return False, "full transcript uses Glasgow as an institution, office, or place descriptor"
    title = norm(fields.get("Title"))
    if title in PLACE_OR_OFFICE_TITLES or title.endswith(" of"):
        return False, f"transcript title {clean(fields.get('Title'))!r} makes Glasgow an office/place descriptor"
    descriptor_text = norm(" ".join((
        clean(fields.get("Title")),
        clean(fields.get("Description")), clean(fields.get("Source")),
        clean(fields.get("Additional information")),
        clean(detail.get("title")), clean(detail.get("heading")),
    )))
    if any(f"{office} glasgow" in descriptor_text for office in PLACE_OR_OFFICE_TITLES):
        return False, "full transcript uses Glasgow as an office or title descriptor"
    if any(phrase in descriptor_text for phrase in ("college of glasgow", "diocese of glasgow", "see of glasgow")):
        return False, "full transcript uses Glasgow as an institution, office, diocese, or place descriptor"
    if not usable_given(first_name):
        return False, "transcript does not identify an individual by a usable given name"
    return True, "full transcript gives a named individual with exact personal last name Glasgow"


def event_type(fields: dict[str, Any]) -> str:
    text = norm(" ".join((clean(fields.get("Record set")), clean(fields.get("Subcategory")), clean(fields.get("Event type")))))
    for label, needles in (
        ("burial", ("burial", "burials")),
        ("baptism", ("baptism", "baptisms")),
        ("birth", ("birth", "births")),
        ("marriage", ("marriage", "marriages")),
        ("death", ("death", "deaths")),
        ("apprenticeship", ("apprentice", "apprentices")),
        ("burgess admission", ("burgess", "guild brethren")),
        ("testament/probate", ("testament", "will", "probate")),
        ("residence/migration", ("residence", "migration")),
        ("covenanter record", ("covenanter", "covenanters")),
        ("court record", ("court", "chancery", "exchequer")),
    ):
        if any(needle in text for needle in needles):
            return label
    return clean(fields.get("Event type")) or clean(fields.get("Subcategory")) or "historical record"


def temporal_scope(detail: dict[str, Any]) -> dict[str, Any]:
    """Use transcript fields only; short displayed years never establish scope."""
    fields = detail.get("transcript_fields") or {}
    # Prefer an event date carrying its own year over derived/index year fields.
    for label in DATE_FIELDS:
        years = explicit_years(fields.get(label))
        if len(set(years)) == 1:
            year = years[0]
            return {
                "accepted": 1 <= year <= 1750, "year": year, "start": year, "end": year,
                "basis": f"transcript field {label}",
                "reason": "" if year <= 1750 else f"transcript date is in {year}, after 1750",
            }

    # Some indexes copy the start of a broad year range into ``Death year`` or
    # another scalar field.  Preserve the range instead of inventing an exact
    # event at its lower bound (for example Burial year/Year Range 1642-1737).
    for label in ("Year Range",) + DATE_YEAR_FIELDS:
        match = re.search(r"(?<!\d)(\d{3,4})\s*[-–]\s*(\d{3,4})(?!\d)", clean(fields.get(label)))
        if match:
            start, end = map(int, match.groups())
            return {
                "accepted": 1 <= start <= end <= 1750,
                "year": None, "start": start, "end": end,
                "basis": f"transcript field {label} range",
                "reason": "" if end <= 1750 else f"transcript event range ends in {end}, after 1750",
            }

    for label in DATE_YEAR_FIELDS:
        years = explicit_years(fields.get(label))
        if len(set(years)) == 1:
            year = years[0]
            return {
                "accepted": 1 <= year <= 1750, "year": year, "start": year, "end": year,
                "basis": f"transcript field {label}",
                "reason": "" if year <= 1750 else f"transcript year {year} is after 1750",
            }
    # Some social-history transcripts put a four-digit document date in the
    # description rather than a date field.  ``Source`` is deliberately not
    # used: values such as "Page 332" are references, not medieval dates.
    narrative_years = [
        int(part)
        for part in re.findall(r"(?<!\d)(\d{4})(?!\d)", clean(fields.get("Description")))
    ]
    if len(set(narrative_years)) == 1:
        year = narrative_years[0]
        return {
            "accepted": 1 <= year <= 1750, "year": year, "start": year, "end": year,
            "basis": "single four-digit year in transcript Description",
            "reason": "" if year <= 1750 else f"transcript narrative year {year} is after 1750",
        }
    # A collection range wholly within scope proves only a bounded event, not
    # an exact year.  This is useful for an otherwise undated named bearer.
    record_set = clean(fields.get("Record set"))
    range_match = re.search(r"(?<!\d)(\d{4})\s*[-–]\s*(\d{4})(?!\d)", record_set)
    if range_match:
        start, end = map(int, range_match.groups())
        if 1 <= start <= end <= 1750:
            return {
                "accepted": True, "year": None, "start": start, "end": end,
                "basis": "transcript record-set range", "reason": "",
            }
    return {
        "accepted": False, "year": None, "start": None, "end": None,
        "basis": "", "reason": "full transcript does not establish an event no later than 1750",
    }


def detail_identity(record_id: str, row: dict[str, Any], detail: dict[str, Any]) -> tuple[dict[str, Any] | None, str]:
    valid, reason = surname_verdict(detail)
    if not valid:
        return None, reason
    temporal = temporal_scope(detail)
    if not temporal["accepted"]:
        return None, temporal["reason"]
    fields = detail.get("transcript_fields") or {}
    first = first_present(fields, ("First name(s)", "First name", "Forename(s)"))[1]
    last = first_present(fields, ("Last name", "Last name(s)", "Surname"))[1]
    date_label, date_value = first_present(fields, DATE_FIELDS)
    place = first_present(fields, ("Place", "Event place", "Residence", "Place as transcribed", "County"))[1]
    country = clean(fields.get("Country"))
    relative_values = {}
    for key, value in fields.items():
        if norm(key).startswith(RELATIVE_PREFIXES) and clean(value):
            relative_values[key] = clean(value)
    references = {key: clean(fields.get(key)) for key in REFERENCE_FIELDS if clean(fields.get(key))}
    return {
        "record_id": record_id,
        "name": " ".join((first, last)),
        "first_name": first,
        "last_name": last,
        "event_type": event_type(fields),
        "event_date": date_value,
        "event_date_label": date_label,
        "event_year": temporal["year"],
        "event_year_start": temporal["start"],
        "event_year_end": temporal["end"],
        "temporal_basis": temporal["basis"],
        "place": place,
        "country": country,
        "record_set": clean(fields.get("Record set")) or clean(row.get("record_set")),
        "source_url": clean(detail.get("final_url") or detail.get("url") or row.get("transcript_url")),
        "image_url": clean(detail.get("image_url") or row.get("image_url")),
        "captured_at": clean(detail.get("captured_at")),
        "title": clean(detail.get("title")),
        "heading": clean(detail.get("heading")),
        "review_reason": clean(detail.get("review_reason")),
        "transcript_fields": fields,
        "transcript_text": clean(detail.get("transcript_text")),
        "relative_values": relative_values,
        "references": references,
        "result_row": row,
    }, ""


def exact_event_key(record: dict[str, Any]) -> tuple[str, ...] | None:
    if not record["place"] or record["event_year"] is None:
        return None
    date_key = norm(record["event_date"]) or f"year {record['event_year']}"
    return (
        norm(record["name"]), norm(record["event_type"]), date_key,
        norm(record["place"]).replace(" ", ""), str(record["event_year"]),
    )


def relative_roles(record: dict[str, Any]) -> dict[str, set[str]]:
    """Build complete relative names so a shared forename cannot hide a conflict."""
    parts: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    for key, value in record["relative_values"].items():
        key_norm = norm(key)
        role = next((prefix for prefix in RELATIVE_PREFIXES if key_norm.startswith(prefix)), key_norm)
        remainder = key_norm[len(role):]
        component = "first" if "first name" in remainder else "last" if "last name" in remainder else "other"
        parts[role][component].add(norm(value))
    result: dict[str, set[str]] = {}
    for role, components in parts.items():
        firsts = components.get("first") or {""}
        lasts = components.get("last") or {""}
        names = {norm(f"{first} {last}") for first in firsts for last in lasts if norm(f"{first} {last}")}
        names.update(components.get("other", set()))
        result[role] = names
    return result


def no_conflicting_relatives(left: dict[str, Any], right: dict[str, Any]) -> bool:
    a, b = relative_roles(left), relative_roles(right)
    return all(not (a[role] and b[role]) or bool(a[role] & b[role]) for role in set(a) | set(b))


def duplicate_evidence(left: dict[str, Any], right: dict[str, Any]) -> str:
    if exact_event_key(left) != exact_event_key(right) or exact_event_key(left) is None:
        return ""
    if not no_conflicting_relatives(left, right):
        return ""
    left_rel = {(role, value) for role, values in relative_roles(left).items() for value in values}
    right_rel = {(role, value) for role, values in relative_roles(right).items() for value in values}
    if left_rel & right_rel:
        precision = "exact event date" if left["event_date"] and right["event_date"] else "event year"
        return f"same {precision}, place, type and named relative"
    left_refs = {norm(value) for key, value in left["references"].items() if "page" not in norm(key) and "item" not in norm(key)}
    right_refs = {norm(value) for key, value in right["references"].items() if "page" not in norm(key) and "item" not in norm(key)}
    if left_refs & right_refs:
        precision = "exact event date" if left["event_date"] and right["event_date"] else "event year"
        return f"same {precision}, place, type and archive/reference identifier"
    return ""


def group_records(
    records: list[dict[str, Any]],
    identity_clusters: list[dict[str, Any]] | None = None,
) -> list[tuple[list[dict[str, Any]], str]]:
    by_key: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        key = exact_event_key(record)
        if key:
            by_key[key].append(record)
    grouped_ids: set[str] = set()
    result: list[tuple[list[dict[str, Any]], str]] = []
    for candidates in by_key.values():
        clusters = [[record] for record in sorted(candidates, key=lambda item: item["record_id"])]
        # Complete-link merging prevents A-B and B-C evidence from silently
        # merging A with a conflicting or unsupported C.
        changed = True
        while changed:
            changed = False
            for left_index, left_group in enumerate(clusters):
                for right_index in range(left_index + 1, len(clusters)):
                    right_group = clusters[right_index]
                    if all(duplicate_evidence(left, right) for left in left_group for right in right_group):
                        clusters[left_index] = left_group + right_group
                        del clusters[right_index]
                        changed = True
                        break
                if changed:
                    break
        for members in clusters:
            grouped_ids.update(member["record_id"] for member in members)
            reasons = {
                duplicate_evidence(left, right)
                for index, left in enumerate(members)
                for right in members[index + 1:]
                if duplicate_evidence(left, right)
            }
            result.append((members, "; ".join(sorted(reasons)) if len(members) > 1 else "singleton; no strong same-event duplicate proof"))
    for record in records:
        if record["record_id"] not in grouped_ids:
            result.append(([record], "singleton; no strong same-event duplicate proof"))
    by_record_id = {record["record_id"]: record for record in records}
    claimed: set[str] = set()
    manual_groups: list[tuple[list[dict[str, Any]], str]] = []
    for cluster in identity_clusters or []:
        record_ids = list(cluster.get("record_ids") or [])
        reason = clean(cluster.get("reason"))
        if len(record_ids) < 2 or not reason:
            raise ValueError("Each manual identity cluster requires at least two record_ids and a reason")
        missing = sorted(set(record_ids) - set(by_record_id))
        overlap = sorted(set(record_ids) & claimed)
        if missing or overlap:
            raise ValueError(f"Invalid manual identity cluster: missing={missing}, repeated={overlap}")
        claimed.update(record_ids)
        manual_groups.append((
            sorted((by_record_id[record_id] for record_id in record_ids), key=lambda item: item["record_id"]),
            "reviewed same-person cluster: " + reason,
        ))
    result = [
        (members, reason) for members, reason in result
        if not any(member["record_id"] in claimed for member in members)
    ]
    result.extend(manual_groups)
    return sorted(result, key=lambda item: item[0][0]["record_id"])


def surname_values(profile: dict[str, Any]) -> set[str]:
    values = [profile.get("LastNameAtBirth"), profile.get("LastNameCurrent")]
    values.extend(clean(profile.get("LastNameOther")).split(","))
    return {re.sub(r"[^a-z]", "", clean(value).casefold()) for value in values if clean(value)}


def primary_given(value: Any) -> str:
    first = norm(value).split()[0] if norm(value) else ""
    return GIVEN_ALIASES.get(first, first)


def profile_year(profile: dict[str, Any], field: str) -> int | None:
    match = re.match(r"^(\d{4})", clean(profile.get(field)))
    year = int(match.group(1)) if match else 0
    return year if year >= 1 else None


def place_terms(value: Any) -> set[str]:
    return {part for part in re.findall(r"[a-z]{4,}", clean(value).casefold()) if part not in PLACE_STOPWORDS}


def load_profiles() -> tuple[dict[str, dict[str, Any]], list[str]]:
    profiles, exports = merged_onetree_profiles()
    provenance = {profile_id: {"one_tree_export"} for profile_id in profiles}
    if SURNAME_PROFILE_INDEX.exists():
        indexed = json.loads(SURNAME_PROFILE_INDEX.read_text(encoding="utf-8")).get("profiles", {})
        for profile_id, item in indexed.items():
            provenance.setdefault(profile_id, set()).add("surname_index")
            profiles.setdefault(profile_id, {
                "Name": profile_id,
                "LongName": item.get("display_name") or profile_id,
                "FirstName": (item.get("display_name") or "").split()[0],
                "LastNameAtBirth": "Glasgow",
                "BirthDate": item.get("birth_date") or "",
                "BirthLocation": item.get("birth_location") or "",
                "DeathDate": item.get("death_date") or "",
                "DeathLocation": item.get("death_location") or "",
            })
    for profile_id, profile in profiles.items():
        profile["_local_sources"] = sorted(provenance.get(profile_id, {"one_tree_export"}))
    return profiles, [str(path.relative_to(ROOT)) for path in exports] + [str(SURNAME_PROFILE_INDEX.relative_to(ROOT))]


def candidate_matches(person: dict[str, Any], profiles: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    wanted_given = primary_given(person["first_name"])
    event_year = person["event_year"]
    if not wanted_given or event_year is None:
        return []
    person_places = place_terms(" ".join((person["place"], person["country"])))
    event_kind = person["event_type"]
    candidates = []
    for profile_id, profile in profiles.items():
        birth_surname = re.sub(r"[^a-z]", "", clean(profile.get("LastNameAtBirth")).casefold())
        if event_kind in {"birth", "baptism"}:
            eligible_surname = birth_surname in SURNAME_VARIANTS
        else:
            eligible_surname = bool(surname_values(profile) & SURNAME_VARIANTS)
        if not eligible_surname:
            continue
        names = {primary_given(profile.get(key)) for key in ("FirstName", "RealName", "BirthName")}
        if wanted_given not in names:
            continue
        birth, death = profile_year(profile, "BirthDate"), profile_year(profile, "DeathDate")
        vital_exact = False
        compatible = True
        chronology = ""
        if event_kind in {"birth", "baptism"}:
            vital_exact = birth is not None and birth == event_year
            compatible = birth is None or birth == event_year
            chronology = "exact birth/baptism year" if vital_exact else "birth year unavailable"
        elif event_kind in {"death", "burial", "testament/probate"}:
            vital_exact = death is not None and death == event_year
            compatible = death is None or death == event_year
            chronology = "exact death/burial/probate year" if vital_exact else "death year unavailable"
        else:
            compatible = (birth is None or event_year - 100 <= birth <= event_year) and (death is None or death >= event_year)
            chronology = "event falls within the local profile's possible lifespan" if compatible else "chronology conflict"
        if not compatible:
            continue
        profile_places = place_terms(" ".join((clean(profile.get("BirthLocation")), clean(profile.get("DeathLocation")))))
        overlap = sorted(person_places & profile_places)
        exact_full = norm(profile.get("FirstName")) == norm(person["first_name"])
        # Common-name chronology alone is not an identity lead.  Vital events
        # require exact-year chronology plus locality; other records require
        # locality and a compatible lifespan.  Live review is still required.
        if event_kind in {"birth", "baptism", "death", "burial", "testament/probate"}:
            supported = vital_exact and bool(overlap)
        else:
            supported = compatible and bool(overlap)
        if not supported:
            continue
        score = 40 + (15 if exact_full else 0) + (35 if vital_exact else 10) + min(20, 10 * len(overlap))
        strength = "exact vital year + locality" if vital_exact and overlap else "exact vital year" if vital_exact else "chronology + locality" if overlap else "chronology only"
        candidates.append({
            "profile_id": profile_id,
            "name": clean(profile.get("LongName") or profile.get("BirthName") or profile_id),
            "birth_date": clean(profile.get("BirthDate")),
            "birth_location": clean(profile.get("BirthLocation")),
            "death_date": clean(profile.get("DeathDate")),
            "death_location": clean(profile.get("DeathLocation")),
            "chronology": chronology,
            "place_overlap": overlap,
            "strength": strength,
            "score": score,
            "local_sources": profile.get("_local_sources", []),
            "url": f"https://www.wikitree.com/wiki/{profile_id}",
            "status": "candidate lead only; identity not established",
        })
    return sorted(candidates, key=lambda item: (-item["score"], item["profile_id"]))[:8]


def stable_id(anchor_record_id: str) -> str:
    """Use one durable source ID so adding a duplicate does not rename a group."""
    digest = hashlib.sha256(anchor_record_id.encode()).hexdigest()[:12]
    return f"fmp-glasgow-{digest}"


def load_details(input_dir: Path) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    details, sources = {}, {}
    for path in sorted(input_dir.glob("record-details*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        records = payload.get("records") if isinstance(payload, dict) else None
        if not isinstance(records, dict):
            raise ValueError(f"Invalid detail overlay: {path}")
        for record_id, detail in records.items():
            if record_id in details and canonical(details[record_id]) != canonical(detail):
                raise ValueError(f"Conflicting details for {record_id}: {sources[record_id]} and {path.name}")
            details[record_id], sources[record_id] = detail, path.name
    return details, sources


def csv_value(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return canonical(value)
    return "" if value is None else str(value)


def outcome_for(reason: str, detail: dict[str, Any] | None, included: bool) -> str:
    if is_daily_limit(detail):
        return "temporary_daily_limit"
    if not included:
        return "unresolved_review"
    status = clean((detail or {}).get("access_status"))
    if status == "subscription_locked":
        return "inaccessible_locked"
    if status in {"error", "not_found"}:
        return "inaccessible_error"
    if "after 1750" in reason:
        return "out_of_scope"
    if any(phrase in reason for phrase in (
        "office/place descriptor", "office or title descriptor",
        "institution, office, diocese, or place descriptor",
        "does not give exact Glasgow",
    )) or norm((detail or {}).get("surname_status")) == "false hit":
        return "rejected_false_hit"
    return "unresolved_review"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_DIR)
    parser.add_argument("--output-dir", type=Path)
    options = parser.parse_args()
    input_dir = options.input_dir
    output_dir = options.output_dir or input_dir
    audit_path = input_dir / "audit-consolidated.json"
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    details, detail_sources = load_details(input_dir)
    review_path = input_dir / "record-review-overrides.json"
    reviews = json.loads(review_path.read_text(encoding="utf-8")) if review_path.exists() else {}
    if not isinstance(reviews, dict):
        raise ValueError(f"Review overrides must be an object keyed by record ID: {review_path}")
    for record_id, review in reviews.items():
        if record_id in details and isinstance(review, dict):
            details[record_id] = {**details[record_id], **review}
    cluster_path = input_dir / IDENTITY_CLUSTERS_FILE
    identity_clusters = json.loads(cluster_path.read_text(encoding="utf-8")) if cluster_path.exists() else []
    if not isinstance(identity_clusters, list):
        raise ValueError(f"Identity clusters must be a list: {cluster_path}")

    # Choose one deterministic row per exact-display ID, including the valid
    # accessible prefix of a capped/unreconciled query.  Only reconciled,
    # included rows may become integration people, but every observed exact ID
    # receives an explicit outcome.
    rows_by_id: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in audit.get("rows", []):
        if (
            clean(row.get("record_id")) and norm(row.get("last_name")) == "glasgow"
            and row.get("page_url_matches_claim") is True
            and 1 <= int(row.get("page_url_number") or 0) <= 75
        ):
            rows_by_id[clean(row["record_id"])].append(row)
    selected_rows = {}
    for record_id, rows in rows_by_id.items():
        included = [row for row in rows if row.get("included_in_analysis") is True]
        pool = included or rows
        selected_rows[record_id] = sorted(pool, key=lambda row: (
                int(row.get("window_eventyear") or 0), int(row.get("page") or 0), int(row.get("row_on_page") or 0),
        ))[0]
    expected_exact_ids = audit.get("summary", {}).get("all_observed_exact_display_unique_ids")
    if expected_exact_ids is not None and int(expected_exact_ids) != len(selected_rows):
        raise AssertionError(
            f"exact-display IDs silently dropped: audit says {expected_exact_ids}, selected {len(selected_rows)}"
        )
    unused_detail_ids = sorted(set(details) - set(selected_rows))
    unused_details = [{
        "record_id": record_id,
        "detail_source_file": detail_sources[record_id],
        "access_status": clean(details[record_id].get("access_status")),
        "block_reason": clean(details[record_id].get("block_reason")),
        "surname_status": clean(details[record_id].get("surname_status")),
        "source_url": clean(details[record_id].get("final_url") or details[record_id].get("url")),
        "reason": (
            DAILY_LIMIT_REASON
            if is_daily_limit(details[record_id]) else
            "captured detail has no observed exact-Glasgow display row in the consolidated audit"
        ),
    } for record_id in unused_detail_ids]

    records, excluded, outcomes = [], [], []
    for record_id in sorted(selected_rows):
        row = selected_rows[record_id]
        included = row.get("included_in_analysis") is True
        common = {
            "record_id": record_id,
            "display_name": " ".join(filter(None, (clean(row.get("first_name")), clean(row.get("last_name"))))),
            "display_event_year": clean(row.get("event_year")),
            "display_location": clean(row.get("location")),
            "record_set": clean(row.get("record_set")),
            "included_in_reconciled_analysis": included,
            "result_classification": clean(row.get("classification")),
            "detail_source_file": detail_sources.get(record_id, ""),
            "block_reason": clean((details.get(record_id) or {}).get("block_reason")),
            "source_url": clean((details.get(record_id) or {}).get("final_url") or
                                (details.get(record_id) or {}).get("url") or row.get("transcript_url")),
        }
        if record_id in details and is_daily_limit(details[record_id]):
            detail = details[record_id]
            outcome = {
                **common,
                "outcome": "temporary_daily_limit",
                "reason": DAILY_LIMIT_REASON,
                "access_status": clean(detail.get("access_status")),
                "block_reason": clean(detail.get("block_reason")),
                "surname_status": clean(detail.get("surname_status")),
                "group_id": "",
            }
            outcomes.append(outcome)
            excluded.append(outcome)
            continue
        if record_id in details and norm(details[record_id].get("surname_status")) == "false hit":
            detail = details[record_id]
            outcome = {
                **common,
                "outcome": "rejected_false_hit",
                "reason": clean(detail.get("review_reason")) or "full-record surname verdict is false hit",
                "access_status": clean(detail.get("access_status")),
                "block_reason": clean(detail.get("block_reason")),
                "surname_status": clean(detail.get("surname_status")),
                "group_id": "",
            }
            outcomes.append(outcome)
            excluded.append(outcome)
            continue
        if not included:
            reason = "exact-display row was observed but is not in a reconciled included audit window"
            outcome = {**common, "outcome": "unresolved_review", "reason": reason, "group_id": ""}
            outcomes.append(outcome)
            excluded.append(outcome)
            continue
        if record_id not in details:
            reason = "full transcript/detail has not been captured"
            outcome = {**common, "outcome": "unresolved_review", "reason": reason, "group_id": ""}
            outcomes.append(outcome)
            excluded.append(outcome)
            continue
        record, reason = detail_identity(record_id, row, details[record_id])
        if record:
            record["detail_source_file"] = detail_sources[record_id]
            records.append(record)
        else:
            outcome = {
                **common, "outcome": outcome_for(reason, details[record_id], included), "reason": reason,
                "access_status": clean(details[record_id].get("access_status")),
                "block_reason": clean(details[record_id].get("block_reason")),
                "surname_status": clean(details[record_id].get("surname_status")),
                "source_url": clean(details[record_id].get("final_url") or details[record_id].get("url")),
                "group_id": "",
            }
            outcomes.append(outcome)
            excluded.append(outcome)

    profiles, profile_sources = load_profiles()
    people = []
    for members, duplicate_reason in group_records(records, identity_clusters):
        record_ids = [member["record_id"] for member in members]
        anchor = members[0]
        group_id = stable_id(anchor["record_id"])
        candidates = candidate_matches(anchor, profiles)
        person = {
            "group_id": group_id,
            "supplement_id": group_id,
            "name": anchor["name"],
            "first_name": anchor["first_name"],
            "last_name": anchor["last_name"],
            "event_type": anchor["event_type"],
            "event_date": anchor["event_date"],
            "event_year": anchor["event_year"],
            "event_year_start": anchor["event_year_start"],
            "event_year_end": anchor["event_year_end"],
            "temporal_basis": anchor["temporal_basis"],
            "place": anchor["place"],
            "country": anchor["country"],
            "record_ids": record_ids,
            "record_count": len(members),
            "duplicate_group_reason": duplicate_reason,
            "record_sets": sorted({member["record_set"] for member in members if member["record_set"]}),
            "source_urls": sorted({member["source_url"] for member in members if member["source_url"]}),
            "image_urls": sorted({member["image_url"] for member in members if member["image_url"]}),
            "detail_captured_at": sorted({member["captured_at"] for member in members if member["captured_at"]}),
            "transcript_titles": sorted({member["title"] for member in members if member["title"]}),
            "local_wikitree_candidate_ids": [item["profile_id"] for item in candidates],
            "local_wikitree_candidates": candidates,
            "match_status": "local candidates only; live WikiTree/API review still required",
            "records": members,
        }
        people.append(person)
        for record_id in record_ids:
            row = selected_rows[record_id]
            outcomes.append({
                "record_id": record_id,
                "display_name": " ".join(filter(None, (clean(row.get("first_name")), clean(row.get("last_name"))))),
                "display_event_year": clean(row.get("event_year")),
                "display_location": clean(row.get("location")),
                "record_set": clean(row.get("record_set")),
                "included_in_reconciled_analysis": True,
                "result_classification": clean(row.get("classification")),
                "detail_source_file": detail_sources.get(record_id, ""),
                "outcome": "validated_in_scope",
                "reason": "full transcript validates an exact Glasgow-surname person and an event no later than 1750",
                "group_id": group_id,
            })
    people.sort(key=lambda item: (
        item["event_year_start"] if item["event_year_start"] is not None else 9999,
        norm(item["name"]), item["group_id"],
    ))
    outcomes.sort(key=lambda item: item["record_id"])
    if len(outcomes) != len(selected_rows) or len({item["record_id"] for item in outcomes}) != len(selected_rows):
        raise AssertionError("every exact-display record ID must receive exactly one outcome")
    outcome_counts = Counter(item["outcome"] for item in outcomes)
    exclusion_counts = Counter(item["reason"] for item in excluded)
    daily_limit_ids = {
        record_id for record_id, detail in details.items() if is_daily_limit(detail)
    }
    record_subscription_locked_ids = {
        record_id for record_id, detail in details.items()
        if not is_daily_limit(detail)
        and clean(detail.get("access_status")) == "subscription_locked"
    }
    summary = {
        "audit_complete_and_reconciled": bool(
            audit.get("summary", {}).get("complete_and_reconciled")
            and not daily_limit_ids
        ),
        "audit_target_years": audit.get("summary", {}).get("target_years"),
        "observed_exact_display_unique_record_ids": len(selected_rows),
        "exact_display_outcome_record_ids": len(outcomes),
        "detail_overlay_record_ids": len(details),
        "detail_ids_without_observed_exact_display_row": len(unused_details),
        "transcript_validated_in_scope_record_ids": len(records),
        "conservative_distinct_people": len(people),
        "same_event_duplicate_groups": sum(item["record_count"] > 1 for item in people),
        "same_event_duplicate_record_ids": sum(item["record_count"] for item in people if item["record_count"] > 1),
        "people_with_local_wikitree_candidates": sum(bool(item["local_wikitree_candidates"]) for item in people),
        "excluded_or_unreviewed_record_ids": len(excluded),
        "record_specific_subscription_locked_record_ids": len(record_subscription_locked_ids),
        "temporary_daily_limit_record_ids": len(daily_limit_ids),
        "daily_limit_schema_access_status": "subscription_locked" if daily_limit_ids else "",
        "outcomes": dict(sorted(outcome_counts.items())),
        "exclusion_reasons": dict(sorted(exclusion_counts.items())),
    }
    payload = {
        "schema_version": 1,
        "source_audit": provenance_path(audit_path),
        "detail_files": sorted({provenance_path(input_dir / name) for name in detail_sources.values()}),
        "local_profile_sources": profile_sources,
        "rules": {
            "surname": "Accessible full transcript; saved confirmed verdict; exact Glasgow personal last-name field; usable given name; office/place titles ending in 'of' rejected.",
            "time": "A four-digit event/date field no later than 1750, one unambiguous narrative document year, or a record-set range wholly within 1750. Short years and broad ranges crossing 1750 are unresolved.",
            "grouping": "Different IDs merge automatically only for the same exact dated, placed, typed event and either a matching complete named relative or matching archive/reference identifier. Reviewed same-person clusters may additionally join compatible records when a written evidence reason is stored in record-identity-clusters.json.",
            "matching": "Local exact/recognised given-name and Glasgow-surname candidates require locality support plus exact vital-year chronology or a compatible non-vital lifespan. They remain leads; live API and person-level evidence review are required.",
            "temporary_access": "block_reason=daily_limit is a temporary fair-use block requiring retry. Its schema-valid access_status remains subscription_locked, but it is excluded from record-specific subscription-lock counts and outcomes.",
            "identity_warning": "Singleton event groups are conservative documentary person candidates, not proof that similarly named records describe different historical people.",
        },
        "summary": summary,
        "people": people,
        "record_outcomes": outcomes,
        "excluded_records": sorted(excluded, key=lambda item: item["record_id"]),
        "unused_detail_records": unused_details,
    }
    json_path = output_dir / "audit-distinct-people.json"
    csv_path = output_dir / "audit-distinct-people.csv"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for person in people:
            row = dict(person)
            row["record_ids"] = " | ".join(person["record_ids"])
            row["record_sets"] = " | ".join(person["record_sets"])
            row["source_urls"] = " | ".join(person["source_urls"])
            row["image_urls"] = " | ".join(person["image_urls"])
            row["detail_captured_at"] = " | ".join(person["detail_captured_at"])
            row["transcript_titles"] = " | ".join(person["transcript_titles"])
            row["transcript_fields_json"] = canonical([item["transcript_fields"] for item in person["records"]])
            row["local_wikitree_candidate_ids"] = " | ".join(person["local_wikitree_candidate_ids"])
            row["local_wikitree_candidates_json"] = canonical(person["local_wikitree_candidates"])
            writer.writerow({column: csv_value(row.get(column)) for column in CSV_COLUMNS})
    print(canonical(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
