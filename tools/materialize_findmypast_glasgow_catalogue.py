#!/usr/bin/env python3
"""Deterministically materialize the reviewed Findmypast Glasgow audit.

Dry-run is the default and only writes a plan beneath the audit directory.
Global ``--apply`` is deliberately fail-closed. Scoped runs may materialize a
fully matched, transcript-validated subset while the master source audit
remains explicitly incomplete; they never represent that subset as a complete
scrape. Range runs use isolated outputs and preserve other scoped work.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, quote, unquote, urlparse

try:
    from project_paths import ROOT, atomic_write_csv, atomic_write_text
except ModuleNotFoundError:
    from tools.project_paths import ROOT, atomic_write_csv, atomic_write_text


AUDIT_DIR = ROOT / "research" / "findmypast-glasgow-audit"
PEOPLE_PATH = AUDIT_DIR / "audit-distinct-people.json"
MATCHES_PATH = AUDIT_DIR / "audit-wikitree-matches.json"
OVERRIDES_PATH = AUDIT_DIR / "catalogue-integration-overrides.json"
PLAN_JSON = AUDIT_DIR / "catalogue-integration-plan.json"
PLAN_MD = AUDIT_DIR / "catalogue-integration-plan.md"
RECORDS_PATH = ROOT / "www" / "map" / "data" / "records.csv"
REGISTER_PATH = ROOT / "surname-research" / "pre-1700" / "evidence-register.md"
QUEUE_PATH = ROOT / "surname-research" / "to-update.md"
PROVENANCE_PATH = AUDIT_DIR / "integration-provenance.md"
PROFILE_AUDIT_PATH = ROOT / "data" / "wikitree" / "catalogue-profile-audit.json"
MANAGED_SOURCE_TYPE = "findmypast-glasgow-surname-audit"
BLOCK_TAG = "FINDMYPAST-GLASGOW-AUDIT"
WT_ID = re.compile(r"^[A-Za-z][A-Za-z0-9' .-]*-\d+$")
VALID_OUTCOMES = {"existing_profile", "new_person", "free_space"}
VALID_CREATION = {"READY", "HOLD"}
ESTIMATED_VITAL = re.compile(
    r"\b(?:estimated|inferred|uncertain|approx(?:imate(?:d|ly)?)?|before|after|about|circa)\b",
    re.IGNORECASE,
)
CSV_EXPORT_COLUMNS = (
    "group_id", "supplement_id", "name", "event_type", "event_date",
    "event_year", "event_year_start", "event_year_end", "place", "country",
    "record_ids", "record_sets", "source_urls", "integration_outcome",
    "profile_id", "creation_status", "handoff_path", "decision_basis",
)


def clean(value: Any) -> str:
    return "" if value is None else str(value).strip()


def location_is_placeholder(value: Any) -> bool:
    """Return whether every supplied place component explicitly says it is unknown."""
    parts = [part.strip() for part in clean(value).split(",") if part.strip()]
    return bool(parts) and all(
        re.fullmatch(
            r"(?:unknown|unspecified|(?:place|location)\s+(?:unknown|not\s+(?:stated|supplied)))",
            part,
            re.IGNORECASE,
        )
        for part in parts
    )


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def slug(value: Any, separator: str = "_") -> str:
    text = re.sub(r"[^A-Za-z0-9]+", separator, clean(value)).strip(separator)
    return text or "unknown"


def year_label(person: dict[str, Any]) -> str:
    if person.get("event_year") is not None:
        return str(person["event_year"])
    start, end = person.get("event_year_start"), person.get("event_year_end")
    return str(start) if start == end else f"{start or '?'}-{end or '?'}"


def display_date(person: dict[str, Any]) -> str:
    return clean(person.get("event_date")) or year_label(person)


def citation(person: dict[str, Any]) -> str:
    sets = "; ".join(person.get("record_sets") or []) or "Findmypast historical record"
    ids = ", ".join(person.get("record_ids") or [])
    url = (person.get("source_urls") or [""])[0]
    core = f"Findmypast, {sets}, {person['name']}, {display_date(person)}, {clean(person.get('place'))}"
    if ids:
        core += f", record ID{'s' if len(person.get('record_ids') or []) != 1 else ''} {ids}"
    return f"[{url} {core}]" if url else core


def source_title(person: dict[str, Any]) -> str:
    anchor = (person.get("record_ids") or [person["group_id"]])[0]
    record_set = (person.get("record_sets") or ["historical record"])[0]
    return f"Findmypast, {record_set}: {person['name']}, {display_date(person)}, record {anchor}"


def findmypast_record_id(url: Any) -> str:
    parsed = urlparse(clean(url))
    if "findmypast." not in parsed.netloc.casefold():
        return ""
    return unquote((parse_qs(parsed.query).get("id") or [""])[0])


def complete_profile_draft(path: Path) -> bool:
    """Require meaningful paste-ready WikiTree content, not mere file presence."""
    if not path.is_file():
        return False
    text = path.read_text(encoding="utf-8")
    required = (
        "[[Category:Glasgow Name Study]]", "== Biography ==",
        "== Research Notes ==", "== Sources ==", "<references />",
    )
    return all(item in text for item in required) and "<ref" in text


def estimated_vital(*values: Any) -> bool:
    """Return whether a rendered key vital is explicitly qualified."""
    return any(ESTIMATED_VITAL.search(clean(value)) for value in values)


def default_handoff(person: dict[str, Any], outcome: str) -> Path:
    prefix = "_".join((
        slug(year_label(person)), slug(person.get("country")),
        slug(person.get("place")), slug(person.get("name")),
    ))
    if outcome == "free_space":
        return ROOT / "surname-research" / "free-space-pages" / f"Findmypast_{prefix}.md"
    return ROOT / "surname-research" / "new-people" / f"{prefix}.md"


def validate_scope(before_year: int | None = None, from_year: int | None = None,
                   through_year: int | None = None) -> None:
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


def scoped_path(path: Path, before_year: int | None = None,
                from_year: int | None = None,
                through_year: int | None = None) -> Path:
    validate_scope(before_year, from_year, through_year)
    if from_year is not None and through_year is not None:
        return path.with_name(f"{path.stem}-{from_year}-{through_year}{path.suffix}")
    if before_year is None:
        return path
    return path.with_name(f"{path.stem}-pre{before_year}{path.suffix}")


def load_inputs(before_year: int | None = None, from_year: int | None = None,
                through_year: int | None = None) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    people = json.loads(PEOPLE_PATH.read_text(encoding="utf-8"))
    matches = json.loads(scoped_path(
        MATCHES_PATH, before_year, from_year, through_year).read_text(encoding="utf-8"))
    overrides = json.loads(OVERRIDES_PATH.read_text(encoding="utf-8"))
    if overrides.get("schema_version") != 1 or not isinstance(overrides.get("groups"), dict):
        raise ValueError(f"Invalid override file: {OVERRIDES_PATH}")
    return people, matches, overrides


def select_people(all_people: list[dict[str, Any]], before_year: int | None = None,
                  from_year: int | None = None,
                  through_year: int | None = None) -> list[dict[str, Any]]:
    validate_scope(before_year, from_year, through_year)
    selected = []
    for person in all_people:
        if isinstance(person.get("event_year_start"), bool) or isinstance(
            person.get("event_year_end"), bool
        ):
            raise ValueError(
                f"{person.get('group_id') or '<missing group_id>'}: invalid event-year range"
            )
        try:
            start = int(person.get("event_year_start"))
            end = int(person.get("event_year_end"))
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"{person.get('group_id') or '<missing group_id>'}: invalid event-year range"
            ) from exc
        if start > end:
            raise ValueError(
                f"{person.get('group_id') or '<missing group_id>'}: reversed event-year range"
            )
        if before_year is not None:
            include = end < before_year
        elif from_year is not None and through_year is not None:
            include = start >= from_year and end <= through_year
        else:
            include = True
        if include:
            selected.append(person)
    return selected


def scope_label(before_year: int | None = None, from_year: int | None = None,
                through_year: int | None = None) -> str:
    if before_year is not None:
        return f"before {before_year}"
    if from_year is not None and through_year is not None:
        return f"{from_year}–{through_year}"
    return "through 1750"


def reviewed_person(person: dict[str, Any], decision: dict[str, Any]) -> dict[str, Any]:
    """Apply narrowly reviewed catalogue interpretations without altering raw transcript data."""
    rendered = dict(person)
    for key in (
        "country", "place", "event_date", "event_year", "event_year_start",
        "event_year_end", "birth_location",
    ):
        override_key = f"catalogue_{key}"
        if override_key in decision:
            rendered[key] = decision[override_key]
    return rendered


def decide(person: dict[str, Any], match: dict[str, Any] | None,
           override: dict[str, Any] | None) -> dict[str, Any]:
    group_id = person["group_id"]
    pre1500 = int(person.get("event_year_start") or 9999) < 1500
    confirmed = list((match or {}).get("confirmed_profile_ids") or [])
    candidates = list((match or {}).get("candidates") or [])
    result: dict[str, Any] = {
        "group_id": group_id, "supplement_id": clean(person.get("supplement_id")) or group_id,
        "name": person["name"], "event_year_start": person.get("event_year_start"),
        "match_audit_present": match is not None, "candidate_count": len(candidates),
        "profile_id": "", "creation_status": "", "notes": "", "decision_source": "",
        "queue_status": "OPEN", "queue_work": "", "substantive_amendment": None,
    }
    if override:
        outcome = clean(override.get("outcome"))
        if outcome not in VALID_OUTCOMES:
            raise ValueError(f"{group_id}: invalid override outcome {outcome!r}")
        result.update({
            "outcome": outcome, "profile_id": clean(override.get("profile_id")),
            "creation_status": clean(override.get("creation_status")),
            "notes": clean(override.get("notes")), "decision_source": "human_override",
            "queue_status": clean(override.get("queue_status")) or "OPEN",
            "queue_work": clean(override.get("queue_work")),
            "substantive_amendment": override.get("substantive_amendment"),
        })
        for key in (
            "country", "place", "event_date", "event_year", "event_year_start",
            "event_year_end", "birth_location",
        ):
            override_key = f"catalogue_{key}"
            if override_key in override:
                result[override_key] = override[override_key]
    elif match is None:
        result.update({"outcome": "blocked_missing_match_audit", "decision_source": "none"})
    elif len(confirmed) == 1:
        result.update({
            "outcome": "existing_profile", "profile_id": confirmed[0],
            "decision_source": "confirmed_live_match_audit",
        })
    elif len(confirmed) > 1:
        result.update({"outcome": "blocked_conflicting_matches", "decision_source": "match_audit"})
    elif pre1500:
        result.update({
            "outcome": "free_space", "creation_status": "READY",
            "decision_source": "pre1500_free_space_rule",
        })
    else:
        no_match = clean((match or {}).get("status")) == "no_wikitree_match_found"
        result.update({
            "outcome": "new_person", "creation_status": "READY" if no_match and not candidates else "HOLD",
            "decision_source": "complete_live_no_match_audit" if no_match and not candidates else "unresolved_candidate_audit",
        })
    outcome = result["outcome"]
    if result["substantive_amendment"] is None:
        # Significance is a reviewed evidence decision.  A legacy filename is
        # never a substitute for that decision or for a content audit.
        result["substantive_amendment"] = False
    if not isinstance(result["substantive_amendment"], bool):
        raise ValueError(f"{group_id}: substantive_amendment must be boolean")
    if result["substantive_amendment"] and outcome != "existing_profile":
        raise ValueError(f"{group_id}: only an existing profile can have a substantive amendment")
    if pre1500 and outcome == "new_person":
        raise ValueError(f"{group_id}: pre-1500 subjects cannot have person-profile drafts")
    if outcome == "existing_profile" and not WT_ID.fullmatch(result["profile_id"]):
        raise ValueError(f"{group_id}: existing_profile requires a valid profile_id")
    if outcome in {"new_person", "free_space"}:
        if result["creation_status"] not in VALID_CREATION:
            raise ValueError(f"{group_id}: {outcome} requires creation_status READY or HOLD")
        supplied = clean((override or {}).get("handoff_path"))
        handoff = (ROOT / supplied).resolve() if supplied else default_handoff(person, outcome).resolve()
        try:
            handoff.relative_to(ROOT)
        except ValueError as exc:
            raise ValueError(f"{group_id}: handoff_path must be inside the repository") from exc
        allowed_dir = ROOT / "surname-research" / ("free-space-pages" if outcome == "free_space" else "new-people")
        if handoff.parent != allowed_dir:
            raise ValueError(f"{group_id}: {outcome} handoff must be directly in {allowed_dir.relative_to(ROOT)}")
        result["handoff_path"] = str(handoff.relative_to(ROOT))
    else:
        result["handoff_path"] = ""
    return result


def build_plan(people_doc: dict[str, Any], matches_doc: dict[str, Any],
               overrides_doc: dict[str, Any], before_year: int | None = None,
               from_year: int | None = None,
               through_year: int | None = None) -> dict[str, Any]:
    all_people = people_doc.get("people") or []
    people = select_people(all_people, before_year, from_year, through_year)
    scoped = before_year is not None or from_year is not None or through_year is not None
    by_id = {item["group_id"]: item for item in people}
    if len(by_id) != len(people):
        raise ValueError("Duplicate group_id in audit-distinct-people.json")
    bad_ids = [item["group_id"] for item in people if (
        clean(item.get("supplement_id")) != item["group_id"]
        or not re.fullmatch(r"fmp-glasgow-[0-9a-f]{12}", item["group_id"])
    )]
    if bad_ids:
        raise ValueError(f"Unstable group/supplement IDs: {bad_ids}")
    record_owners: dict[str, str] = {}
    for person in all_people:
        for record_id in person.get("record_ids") or []:
            prior = record_owners.setdefault(record_id, person["group_id"])
            if prior != person["group_id"]:
                raise ValueError(f"Record ID {record_id} occurs in person groups {prior} and {person['group_id']}")
    matches = {item["group_id"]: item for item in matches_doc.get("people") or []}
    if len(matches) != len(matches_doc.get("people") or []):
        raise ValueError("Duplicate group_id in audit-wikitree-matches.json")
    all_ids = {item["group_id"] for item in all_people}
    unknown_matches = sorted(set(matches) - all_ids)
    unknown_overrides = sorted(set(overrides_doc["groups"]) - all_ids)
    if unknown_overrides or (unknown_matches and not scoped):
        raise ValueError(f"Unknown group IDs: matches={unknown_matches}, overrides={unknown_overrides}")
    decisions = [decide(person, matches.get(group_id), overrides_doc["groups"].get(group_id))
                 for group_id, person in sorted(by_id.items())]
    # Separate conservative people can legitimately share name/year/place.
    # Keep human-supplied paths fixed and make only colliding defaults unique.
    handoff_groups: dict[str, list[dict[str, Any]]] = {}
    for decision in decisions:
        if decision.get("handoff_path"):
            handoff_groups.setdefault(decision["handoff_path"], []).append(decision)
    for path_text, colliding in handoff_groups.items():
        if len(colliding) < 2:
            continue
        for decision in colliding:
            if decision["decision_source"] == "human_override":
                continue
            path = Path(path_text)
            suffix = decision["group_id"].removeprefix("fmp-glasgow-")
            decision["handoff_path"] = str(path.with_name(f"{path.stem}_{suffix}{path.suffix}"))
            decision["handoff_path_disambiguated"] = True
    counts = Counter(item["outcome"] for item in decisions)
    status_counts = Counter(
        f"{item['outcome']}:{item.get('creation_status') or 'n/a'}" for item in decisions
    )
    duplicate_handoffs = sorted(
        path for path, grouped in handoff_groups.items()
        if len(grouped) > 1 and not (
            all(item["outcome"] == "free_space" for item in grouped)
            and (ROOT / path).is_file()
        )
    )
    blockers = []
    source_audit_complete = people_doc.get("summary", {}).get("audit_complete_and_reconciled") is True
    if not source_audit_complete and not scoped:
        blockers.append("source scrape/transcript audit is not complete and reconciled")
    if matches_doc.get("matching_audit_complete_for_snapshot") is not True:
        blockers.append("live WikiTree matching audit is not marked complete for its snapshot")
    source_sha256 = hashlib.sha256(PEOPLE_PATH.read_bytes()).hexdigest()
    if clean(matches_doc.get("source_sha256")) != source_sha256:
        blockers.append("WikiTree match audit does not match the current distinct-people snapshot")
    if matches_doc.get("source_people_count") != len(all_people):
        blockers.append("WikiTree match audit source-person count does not match the current snapshot")
    match_scope = matches_doc.get("scope") or {}
    unexpected_matches = sorted(set(matches) - set(by_id))
    if before_year is not None and (
        match_scope.get("mode") != "event_year_end_before"
        or match_scope.get("before_year") != before_year
        or match_scope.get("predicate") != f"event_year_end < {before_year}"
        or match_scope.get("selected_people_count") != len(by_id)
        or match_scope.get("excluded_people_count") != len(all_people) - len(by_id)
        or unexpected_matches
    ):
        blockers.append(
            f"WikiTree match audit scope is not exactly event_year_end < {before_year} "
            f"({len(unexpected_matches)} out-of-scope match groups)"
        )
    if not scoped and (
        match_scope.get("mode") != "all_people"
        or match_scope.get("predicate") != "all source people"
        or match_scope.get("selected_people_count") != len(by_id)
        or match_scope.get("excluded_people_count") != 0
        or unexpected_matches
    ):
        blockers.append(
            "WikiTree match audit scope is not exactly the complete current person snapshot "
            f"({len(unexpected_matches)} out-of-scope match groups)"
        )
    if from_year is not None and through_year is not None and (
        match_scope.get("mode") != "event_year_range"
        or match_scope.get("from_year") != from_year
        or match_scope.get("through_year") != through_year
        or match_scope.get("predicate") != (
            f"event_year_start >= {from_year} and event_year_end <= {through_year}"
        )
        or match_scope.get("selected_people_count") != len(by_id)
        or match_scope.get("excluded_people_count") != len(all_people) - len(by_id)
        or unexpected_matches
    ):
        blockers.append(
            "WikiTree match audit scope is not exactly "
            f"event_year_start >= {from_year} and event_year_end <= {through_year} "
            f"({len(unexpected_matches)} out-of-scope match groups)"
        )
    missing_matches = sorted(set(by_id) - set(matches))
    if missing_matches:
        blockers.append(f"WikiTree match audit is missing {len(missing_matches)} person groups")
    blocked_decisions = [item["group_id"] for item in decisions if item["outcome"].startswith("blocked_")]
    if blocked_decisions:
        blockers.append(f"{len(blocked_decisions)} person groups have no integration outcome")
    if duplicate_handoffs:
        blockers.append(f"handoff path collisions: {', '.join(duplicate_handoffs)}")
    missing_urls = sorted(item["group_id"] for item in people if not item.get("source_urls"))
    if missing_urls:
        blockers.append(f"{len(missing_urls)} validated groups lack an external source URL")
    missing_amendment_drafts = sorted(
        item["profile_id"] for item in decisions
        if item.get("substantive_amendment")
        and not complete_profile_draft(
            ROOT / "research" / item["profile_id"] / f"{item['profile_id']}.md"
        )
    )
    if missing_amendment_drafts:
        blockers.append(
            "substantive existing-profile amendments lack complete replacement drafts: "
            + ", ".join(missing_amendment_drafts)
        )
    ready = not blockers and len(decisions) == len(by_id) and all(item["outcome"] in VALID_OUTCOMES for item in decisions)
    fingerprint = hashlib.sha256(canonical({
        "people": people_doc, "matches": matches_doc, "overrides": overrides_doc,
    }).encode()).hexdigest()
    capture_times = sorted({stamp for person in people for stamp in person.get("detail_captured_at") or [] if stamp})
    return {
        "schema_version": 1,
        "source_snapshot_sha256": fingerprint,
        "latest_detail_capture_at": capture_times[-1] if capture_times else "",
        "inputs": {
            "people": str(PEOPLE_PATH.relative_to(ROOT)),
            "matches": str(scoped_path(
                MATCHES_PATH, before_year, from_year, through_year).relative_to(ROOT)),
            "overrides": str(OVERRIDES_PATH.relative_to(ROOT)),
        },
        "scope": {
            "before_year": before_year, "from_year": from_year,
            "through_year": through_year, "selected_group_count": len(people),
        },
        "source_audit_complete_and_reconciled": source_audit_complete,
        "source_audit_label": "COMPLETE" if source_audit_complete else "INCOMPLETE",
        "provisional": not ready, "apply_ready": ready, "blockers": blockers,
        "counts": {
            "validated_person_groups": len(people), "matched_audit_groups": len(matches),
            "override_groups": len(set(overrides_doc["groups"]) & set(by_id)), "decisions": dict(sorted(counts.items())),
            "decision_statuses": dict(sorted(status_counts.items())),
            "substantive_existing_amendments": sum(
                bool(item.get("substantive_amendment")) for item in decisions
            ),
        },
        "missing_match_group_ids": missing_matches, "decisions": decisions,
    }


def plan_markdown(plan: dict[str, Any], people_by_id: dict[str, dict[str, Any]]) -> str:
    scope_data = plan.get("scope", {})
    label = scope_label(scope_data.get("before_year"), scope_data.get("from_year"),
                        scope_data.get("through_year"))
    scope = "" if label == "through 1750" else f" {label}"
    lines = [
        f"# Findmypast Glasgow catalogue integration plan{scope}", "",
        f"Source snapshot: `{plan['source_snapshot_sha256']}`; latest detail capture: `{plan['latest_detail_capture_at'] or 'not recorded'}`.", "",
        f"Source scrape/transcript audit: **{plan['source_audit_label']}**. This is a scoped integration of currently transcript-validated records{scope}; it does not claim that the Findmypast scrape or transcript review is complete.", "",
        f"**{'APPLY READY' if plan['apply_ready'] else 'PROVISIONAL — DO NOT APPLY'}**", "",
        f"Validated person groups: **{plan['counts']['validated_person_groups']}**; "
        f"WikiTree-audited groups: **{plan['counts']['matched_audit_groups']}**; "
        f"human overrides: **{plan['counts']['override_groups']}**.", "",
    ]
    if plan["blockers"]:
        lines += ["## Apply blockers", ""] + [f"- {item}" for item in plan["blockers"]] + [""]
    lines += ["## Outcome counts", "", "| Outcome and status | Groups |", "| --- | ---: |"]
    lines += [f"| {key} | {value} |" for key, value in plan["counts"]["decision_statuses"].items()]
    lines += ["", "## Person-group plan", "", "| Group | Person/event | Outcome | Target | Basis |", "| --- | --- | --- | --- | --- |"]
    for decision in plan["decisions"]:
        person = people_by_id[decision["group_id"]]
        target = decision.get("profile_id") or decision.get("handoff_path") or "—"
        event = f"{person['name']}, {display_date(person)}, {clean(person.get('place'))}"
        lines.append(f"| `{decision['group_id']}` | {event} | {decision['outcome']} | {target} | {decision['decision_source']} |")
    lines += ["", "This report is a deterministic preview. It does not prove identity and does not mutate catalogue, findings, drafts, registers, or the update queue.", ""]
    return "\n".join(lines)


def replace_block(text: str, body: str, tag: str = BLOCK_TAG) -> str:
    begin, end = f"<!-- BEGIN {tag} -->", f"<!-- END {tag} -->"
    block = f"{begin}\n{body.rstrip()}\n{end}"
    pattern = re.compile(re.escape(begin) + r".*?" + re.escape(end), re.S)
    return (pattern.sub(block, text) if pattern.search(text) else text.rstrip() + "\n\n" + block + "\n")


def strip_group_rows_from_block(text: str, group_ids: set[str], tag: str = BLOCK_TAG) -> str:
    """Remove selected generated table rows without touching text outside our block."""
    if not group_ids:
        return text
    begin, end = f"<!-- BEGIN {tag} -->", f"<!-- END {tag} -->"
    pattern = re.compile(re.escape(begin) + r".*?" + re.escape(end), re.S)
    match = pattern.search(text)
    if not match:
        return text
    group_pattern = re.compile(
        r"^.*(?:" + "|".join(re.escape(item) for item in sorted(group_ids)) + r").*$\n?",
        re.M,
    )
    cleaned = group_pattern.sub("", match.group(0))
    return text[:match.start()] + cleaned + text[match.end():]


def person_record(person: dict[str, Any], decision: dict[str, Any], header: list[str],
                  before_year: int | None = None,
                  from_year: int | None = None,
                  through_year: int | None = None,
                  source_audit_complete: bool = False) -> dict[str, str]:
    event_type, event_date = clean(person.get("event_type")), display_date(person)
    place = ", ".join(filter(None, (clean(person.get("place")), clean(person.get("country")))))
    ids = ", ".join(person.get("record_ids") or [])
    captured = ", ".join(person.get("detail_captured_at") or [])
    event_role = next((
        clean((record.get("transcript_fields") or {}).get("Event type"))
        for record in person.get("records") or []
        if clean((record.get("transcript_fields") or {}).get("Event type"))
    ), "")
    source_grouping = any(
        clean(fields.get("Event place"))
        and clean(fields.get("Title") or fields.get("Publication title") or fields.get("Collection"))
        and clean(fields.get("Event place")).casefold()
        in clean(fields.get("Title") or fields.get("Publication title") or fields.get("Collection")).casefold()
        for record in person.get("records") or []
        for fields in [record.get("transcript_fields") or {}]
    )
    has_destination = any(
        clean((record.get("transcript_fields") or {}).get("Destination"))
        for record in person.get("records") or []
    )
    explicit_event_role = (
        event_role
        if event_role and not location_is_placeholder(place) and not source_grouping and not has_destination
        else ""
    )
    reviewed_birth_place = clean(person.get("birth_location"))
    transcript_birth_place = next((
        clean((record.get("transcript_fields") or {}).get(label))
        for record in person.get("records") or []
        for label in ("Birth place", "Place of birth")
        if clean((record.get("transcript_fields") or {}).get(label))
    ), "")
    raw_place = clean(person.get("place"))
    usable_event_place = bool(
        raw_place
        and not location_is_placeholder(raw_place)
        and not source_grouping
        and not ("migration" in event_type.casefold() and not explicit_event_role)
    )
    row = {key: "" for key in header}
    row.update({
        "person": person["name"], "profile_id": decision.get("profile_id", ""),
        "region": clean(person.get("country")) or "Unknown",
        "family_group": f"Findmypast Glasgow surname records {scope_label(before_year, from_year, through_year)}",
        "subcluster": event_type, "evidence": "Documented",
        "year": clean(person.get("event_year") if person.get("event_year") is not None else person.get("event_year_start")),
        "filter_year": clean(person.get("event_year") if person.get("event_year") is not None else person.get("event_year_start")),
        "association": f"{event_type.title()} {event_date}".strip(),
        "note": f"Transcript-validated Glasgow-surname record. IDs: {ids}. Separate events/people are not merged without evidence.",
        "record_location": place, "record_precision": "Record-stated place",
        "location_basis": (
            f"Findmypast transcript; explicit event type {explicit_event_role}; no narrower location inferred."
            if explicit_event_role else "Findmypast transcript; no narrower location inferred."
        ),
        "supplement_id": decision["supplement_id"],
        "source_title": source_title(person), "source_url": (person.get("source_urls") or [""])[0],
        "source_type": MANAGED_SOURCE_TYPE,
        "source_status": (f"Full accessible transcript captured {captured or 'date recorded in audit'}; "
                          f"scoped integration {decision['outcome']} {decision.get('creation_status', '')}; "
                          f"master scrape/transcript audit {'complete' if source_audit_complete else 'incomplete'}").strip()
        if before_year is not None or from_year is not None else
        f"Full accessible transcript captured {captured or 'date recorded in audit'}; integration {decision['outcome']} {decision.get('creation_status', '')}".strip(),
    })
    if event_type in {"birth", "baptism"}:
        row["birth_date"], row["birth_status"] = event_date, "documented"
    if decision.get("outcome") == "new_person":
        if reviewed_birth_place and not location_is_placeholder(reviewed_birth_place):
            row["birth_location"] = reviewed_birth_place
            if event_type not in {"birth", "baptism"}:
                row["birth_status"] = "uncertain; inferred from documented context"
        elif transcript_birth_place and not location_is_placeholder(transcript_birth_place):
            row["birth_location"] = transcript_birth_place
        elif usable_event_place:
            row["birth_location"] = place
            if event_type not in {"birth", "baptism"}:
                row["birth_status"] = "uncertain; inferred from documented event"
    if event_type in {"death", "burial"}:
        row["death_date"], row["death_status"] = event_date, "documented"
    return row


def render_draft(person: dict[str, Any], decision: dict[str, Any], match: dict[str, Any]) -> str:
    free_space = decision["outcome"] == "free_space"
    pre1500_free_space = free_space and int(person.get("event_year_start") or 9999) < 1500
    status = (
        "PRE-1500 FREE-SPACE SUBJECT — DO NOT CREATE A PERSON PROFILE"
        if pre1500_free_space else
        "DOCUMENTARY FREE-SPACE SUBJECT — DO NOT CREATE A PERSON PROFILE"
        if free_space else f"{decision['creation_status']} TO CREATE"
    )
    candidates = match.get("candidates") or []
    relative_profiles: dict[str, str] = {}
    for candidate in candidates:
        comparisons = (candidate.get("evidence") or {}).get("relatives", {}).get("comparisons", [])
        for comparison in comparisons:
            # An exact name comparison is only a clue.  Link a relative in the
            # biography only when the audit explicitly proves that identity.
            if (
                comparison.get("exact_match")
                and comparison.get("identity_proven") is True
                and clean(comparison.get("profile_id"))
            ):
                relative_profiles.setdefault(clean(comparison.get("role")), clean(comparison.get("profile_id")))
    records = person.get("records") or []

    # Fail closed when a search/index parser has put the see or office of
    # Glasgow into the surname column.  Such entries are documentary leads,
    # not Glasgow-surname people and must not become person-profile drafts.
    descriptor_text = " ".join(
        clean((record.get("transcript_fields") or {}).get(label))
        for record in records
        for label in ("Additional information", "Description", "Title")
    )
    if re.search(r"\b(?:arch(?:e)?bischop|archbishop|bishop|archdeacon|deacon)\s+of\b", descriptor_text, re.I):
        raise ValueError(
            f"Refusing Glasgow-surname draft for probable office/place descriptor: "
            f"{person['group_id']} ({descriptor_text.strip()})"
        )

    def transcript_value(*labels: str) -> str:
        for record in records:
            fields = record.get("transcript_fields") or {}
            for label in labels:
                value = clean(fields.get(label))
                if value and value != "-":
                    return value
        return ""

    birth_date = transcript_value("Birth date", "Date of birth")
    baptism_date = transcript_value("Baptism date", "Christening date")
    death_date = transcript_value("Death date", "Date of death")
    burial_date = transcript_value("Burial date")
    event_type = clean(person.get("event_type"))
    event_role = transcript_value("Event type")
    event_place = ", ".join(filter(None, (clean(person.get("place")), clean(person.get("country")))))
    if not event_place:
        event_place = transcript_value("Destination", "Residence", "Parish", "County", "Country") or "place not stated"
    reviewed_birth_place = clean(person.get("birth_location"))
    birth_place = reviewed_birth_place or transcript_value("Birth place", "Place of birth")
    gender = transcript_value("Sex", "Gender") or "unknown"
    if birth_date:
        creation_birth = f"{birth_date} (recorded)"
    elif baptism_date:
        creation_birth = f"before {baptism_date} (estimated from baptism)"
    else:
        creation_birth = f"before {display_date(person)} (uncertain; inferred from the person's documented event)"
    creation_death = death_date or (f"before {burial_date}" if burial_date else "unknown")
    source_heading = transcript_value("Title", "Publication title", "Collection")
    raw_place = clean(person.get("place"))
    transcript_event_place = transcript_value("Event place")
    source_grouping = bool(
        source_heading
        and any(
            place.casefold() in source_heading.casefold()
            for place in (raw_place, transcript_event_place)
            if place and not location_is_placeholder(place)
        )
    )
    explicit_residence = bool(
        event_role.casefold() == "residence"
        and raw_place
        and not location_is_placeholder(event_place)
        and not source_grouping
        and not transcript_value("Destination")
    )
    if reviewed_birth_place and not location_is_placeholder(reviewed_birth_place):
        creation_location = reviewed_birth_place
        location_basis = "uncertain; inferred from documented context"
    elif birth_place and not location_is_placeholder(birth_place):
        creation_location = birth_place
        location_basis = "recorded birth place"
    elif "migration" in event_type.casefold() and not explicit_residence:
        creation_location = "unknown"
        location_basis = "not stated; a migration destination or source grouping is not a birthplace"
    else:
        creation_location = event_place
        location_basis = "uncertain; inferred from the person's documented event"

    father = " ".join(filter(None, (
        transcript_value("Father's first name(s)", "Father first name"),
        transcript_value("Father's last name", "Father last name"),
    )))
    mother = " ".join(filter(None, (
        transcript_value("Mother's first name(s)", "Mother first name"),
        transcript_value("Mother's last name", "Mother last name"),
    )))
    spouse = " ".join(filter(None, (
        transcript_value("Spouse's first name(s)", "Spouse first name"),
        transcript_value("Spouse's last name", "Spouse last name"),
    )))
    maternal_grandfather = " ".join(filter(None, (
        transcript_value("Maternal grandfather's first name(s)"),
        transcript_value("Maternal grandfather's last name"),
    )))
    apprentice = " ".join(filter(None, (
        transcript_value("Apprentice first name"),
        transcript_value("Apprentice last name"),
    )))
    master = " ".join(filter(None, (
        transcript_value("Master first name"),
        transcript_value("Master last name"),
    )))
    role = transcript_value("Role")
    subject_is_master = event_type == "apprenticeship" and role.casefold() == "master"
    def linked_relative(role: str, name: str) -> str:
        profile_id = relative_profiles.get(role, "")
        return f"[[{profile_id}|{name}]]" if profile_id else name

    # In master-indexed apprenticeship hits the father fields describe the
    # apprentice, not the Glasgow master.  Never turn those fields into the
    # subject's parentage.
    father_text = linked_relative("father", father) if father and not subject_is_master else ""
    mother_text = linked_relative("mother", mother) if mother else ""
    spouse_text = linked_relative("spouse", spouse) if spouse else ""
    relation_bits = []
    if father and not subject_is_master:
        relation_bits.append(f"father {father_text}")
    if mother:
        relation_bits.append(f"mother {mother_text}")
    if spouse:
        relation_bits.append(f"spouse {spouse_text}")
    if maternal_grandfather:
        relation_bits.append(f"maternal grandfather {maternal_grandfather}")
    if event_type == "apprenticeship":
        if subject_is_master:
            if apprentice:
                relation_bits.append(f"apprentice {apprentice}")
            if father:
                relation_bits.append(f"the apprentice's father {father}")
        elif master:
            relation_bits.append(f"master {master}")
    for label in ("Additional information", "Description", "Source", "Notes"):
        detail = transcript_value(label)
        if detail and re.search(r"\b(?:wife|spouse|husband|daughter|son|father|mother|servant|servitor|master|apprentice)\b", detail, re.I):
            relation_bits.append(f"record wording: {detail}")
    relationships = "; ".join(relation_bits) or "none stated in the transcript"

    record_label = event_type if event_type.casefold().endswith("record") else f"{event_type} record"
    article = "an" if record_label[:1].casefold() in "aeiou" else "a"
    narrative_place = "an unspecified place" if location_is_placeholder(event_place) else event_place
    narrative = f"'''{person['name']}''' appears in {article} {record_label} dated {display_date(person)} at {narrative_place}."
    if birth_date and baptism_date:
        narrative = f"'''{person['name']}''' was born on {birth_date} and baptized on {baptism_date} at {narrative_place}."
    elif birth_date:
        narrative = f"'''{person['name']}''' has a recorded birth date of {birth_date} in a {record_label} associated with {narrative_place}."
    elif baptism_date:
        narrative = f"'''{person['name']}''' was baptized on {baptism_date} at {narrative_place}."
    if event_type == "apprenticeship" and subject_is_master:
        trade = transcript_value("Trade")
        narrative = (
            f"On {display_date(person)} at {event_place}, '''{person['name']}'''"
            + (f", a {trade}," if trade else "")
            + f" was recorded as master of {apprentice or 'an unnamed apprentice'}."
        )
        if father:
            narrative += f" The apprentice's father was {father}."
    elif event_type == "apprenticeship" and master:
        trade = transcript_value("Trade")
        narrative = (
            f"On {display_date(person)} at {event_place}, '''{person['name']}''' was apprenticed"
            + (f" in the {trade} trade" if trade else "")
            + f" to {master}."
        )
    if len(records) > 1:
        dated_entries = []
        for record in sorted(
            records,
            key=lambda item: (item.get("event_year") or 9999, clean(item.get("event_date"))),
        ):
            fields = record.get("transcript_fields") or {}
            entry_date = clean(record.get("event_date") or fields.get("Date") or fields.get("Year"))
            description = clean(fields.get("Occupation") or fields.get("Description"))
            dated_entries.append(
                entry_date + (f" ({description})" if description else "")
            )
        narrative += " The consolidated entries are dated " + ", ".join(dated_entries) + "."
        if "comparison hold" in clean(person.get("duplicate_group_reason")).casefold():
            narrative += " These same-name entries are grouped for comparison only; they may describe more than one person."
    if (father and not subject_is_master) or mother:
        named = " and ".join(filter(None, (father_text, mother_text)))
        narrative += f" The record names {named} as the parent{'s' if father and mother else ''}."
    if spouse:
        narrative += f" The record names {spouse_text} as the spouse."
    if maternal_grandfather:
        narrative += f" The record also names {maternal_grandfather} as the maternal grandfather."
    residence = transcript_value("Residence")
    father_residence = transcript_value("Father residence")
    father_occupation = transcript_value("Father's occupation", "Father occupation")
    occupation = transcript_value("Occupation", "Trade")
    if residence:
        narrative += f" The recorded residence was {residence}."
    if father_residence and father:
        narrative += f" The father was recorded at {father_residence}."
    if father_occupation and father:
        narrative += f" The father's occupation was {father_occupation}."
    if occupation and event_type != "apprenticeship" and len(records) == 1:
        narrative += f" The recorded occupation or trade was {occupation}."
    if role and event_type != "apprenticeship":
        narrative += f" The stated role was {role}."
    for label in (
        "Additional information", "Description", "Source", "Contents text",
        "Destination", "Address", "Parish", "House number", "Folio number", "Notes",
    ):
        detail = transcript_value(label)
        if detail:
            narrative += f" The transcript's {label.casefold()} states: “{detail}”."
    refs = []
    for index, record in enumerate(records, 1):
        fields = record.get("transcript_fields") or {}
        url = clean(record.get("source_url"))
        detail = "; ".join(f"{key}: {value}" for key, value in fields.items() if clean(value))
        refs.append(f'<ref name="FMP{index}">[{url} Findmypast transcript], {detail} (captured {clean(record.get("captured_at"))}).</ref>')
    ref_names = "".join(f'<ref name="FMP{index}" />' for index in range(1, len(refs) + 1))
    heading = "Free-space evidence fields" if free_space else "Minimum creation fields"
    caution = (
        "This file is a supporting free-space research-page draft only. Never convert it to a person-profile draft."
        if free_space else
        "Attach only relationships stated by the record after confirming the relative profile identities; leave all other relationships blank."
    )
    candidate_lines = []
    for item in candidates:
        profile_id = clean(item.get("profile_id"))
        profile = item.get("profile") or {}
        display_name = clean(profile.get("LongName") or profile.get("RealName")) or profile_id
        reasons = [clean(reason) for reason in item.get("missing_for_confirmation") or [] if clean(reason)]
        candidate_lines.append(
            f"* [[{profile_id}|{display_name}]] — "
            + ("; ".join(reasons) if reasons else "possible duplicate; the audit did not establish an identity bridge")
        )
    candidate_assessment = "\n".join(candidate_lines)
    if not candidate_assessment and decision.get("creation_status") != "HOLD":
        candidate_assessment = "No compatible candidate was retained by the completed live WikiTree audit."
    reviewed_note = clean(decision.get("notes"))
    reviewed_note_label = (
        "Reviewed HOLD reason" if decision.get("creation_status") == "HOLD"
        else "Reviewed integration decision"
    )
    estimated_template = "{{Estimated Date}}\n" if estimated_vital(creation_birth, creation_death) else ""
    if decision.get("creation_status") == "HOLD":
        hold_reason = (
            "This draft is on '''HOLD''' because the following possible duplicate profile identities remain unresolved:"
            if candidates else
            "This draft is on '''HOLD''' because the available transcript does not yet distinguish a safe profile identity."
        )
        next_test = (
            "'''Next test:''' inspect the underlying record image and search the relevant local register for an exact "
            "date, place, occupation, or named-relative bridge that confirms or excludes each candidate before creation."
        )
    else:
        hold_reason = "The completed live WikiTree audit retained no compatible profile candidate."
        next_test = (
            "'''Next test before creation:''' repeat the exact-name, date, place, occupation, and named-relative "
            "duplicate search, then inspect the underlying record image where available."
        )
    return f"""<!-- BEGIN FMP-GLASGOW-{person['group_id']} -->
> **{status}**

# {person['name']}, {display_date(person)}

## {heading}

- **Name:** {person['name']}
- **Gender:** {gender}
- **Birth date:** {creation_birth}
- **Birth location:** {creation_location} ({location_basis})
- **Death date:** {creation_death}
- **Recorded event:** {person.get('event_type')}, {display_date(person)}
- **Recorded relationships:** {relationships}
- **Stable research ID:** `{decision['supplement_id']}`
- **Findmypast record IDs:** {', '.join(person.get('record_ids') or [])}

## Paste-ready biography

[[Category:Glasgow Name Study]]
{estimated_template}

== Biography ==

{narrative}{ref_names}

== Research Notes ==

{caution} Each named relative requires a duplicate search and a separately supported profile identity before attachment.

{hold_reason}

{("'''" + reviewed_note_label + ":''' " + reviewed_note) if reviewed_note else ""}

{candidate_assessment}

The {len(person.get('record_ids') or [])} result ID(s) above represent one conservative documentary group because: {clean(person.get('duplicate_group_reason'))}. Preserve uncertainty; a similarly named event is not automatically the same historical person.

{next_test}

== Sources ==

{chr(10).join(refs)}

<references />
<!-- END FMP-GLASGOW-{person['group_id']} -->
"""


def render_finding(person: dict[str, Any], decision: dict[str, Any]) -> str:
    evidence = []
    for record in person.get("records") or []:
        fields = record.get("transcript_fields") or {}
        detail = "; ".join(f"{key}: {value}" for key, value in fields.items() if clean(value))
        evidence.append(
            f"- [{clean(record.get('record_id'))} Findmypast transcript]({clean(record.get('source_url'))}): {detail} "
            f"(captured {clean(record.get('captured_at'))})."
        )
    return f"""## Current conclusion — Findmypast Glasgow surname evidence {decision['supplement_id']}

The transcript-validated {clean(person.get('event_type'))} record for **{person['name']}**, {display_date(person)}, {clean(person.get('place'))}, is assigned to this profile by the completed person-level WikiTree audit. This assignment does not merge any other same-name event.

## Source findings

{chr(10).join(evidence) or '- ' + citation(person)}
- Findmypast record IDs: `{ '`, `'.join(person.get('record_ids') or []) }`.
- Stable research/source ID: `{decision['supplement_id']}`.

## Recommended action — {decision['supplement_id']}

Add the record as supporting evidence while preserving all existing sources and uncertain relationships. Do not infer an unstated birth place, parent, spouse, or child.
"""


def export_rows(cutoff: int, people: list[dict[str, Any]], decisions: dict[str, dict[str, Any]],
                *, inclusive: bool = False) -> tuple[str, str]:
    selected = [person for person in people if (
        int(person.get("event_year_end") or 9999) <= cutoff if inclusive
        else int(person.get("event_year_end") or 9999) < cutoff
    )]
    selected.sort(key=lambda p: (p.get("event_year_start") or 9999, p["name"], p["group_id"]))
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=CSV_EXPORT_COLUMNS, lineterminator="\n")
    writer.writeheader()
    for person in selected:
        decision = decisions[person["group_id"]]
        row = dict(person)
        row.update({
            "record_ids": " | ".join(person.get("record_ids") or []),
            "record_sets": " | ".join(person.get("record_sets") or []),
            "source_urls": " | ".join(person.get("source_urls") or []),
            "integration_outcome": decision["outcome"], "profile_id": decision.get("profile_id", ""),
            "creation_status": decision.get("creation_status", ""), "handoff_path": decision.get("handoff_path", ""),
            "decision_basis": decision["decision_source"],
        })
        writer.writerow({key: clean(row.get(key)) for key in CSV_EXPORT_COLUMNS})
    md = [
        f"# Findmypast surname-only Glasgow audit {'through' if inclusive else 'before'} {cutoff}", "",
        f"This integration export contains **{len(selected)}** transcript-validated conservative person groups whose supported event range ends {'by' if inclusive else 'before'} {cutoff}. Raw result rows, rejected hits, inaccessible details, duplicate IDs, exact queries, page counts and reconciliation remain preserved in [the master audit](findmypast-glasgow-audit/audit-report.md).", "",
        "| Person/event | IDs | Integration |", "| --- | --- | --- |",
    ]
    for person in selected:
        d = decisions[person["group_id"]]
        target = d.get("profile_id") or d.get("handoff_path") or "blocked"
        md.append(f"| {person['name']}, {display_date(person)}, {clean(person.get('place'))} | `{ '`, `'.join(person.get('record_ids') or []) }` | {d['outcome']}: {target} |")
    md.append("")
    return buffer.getvalue(), "\n".join(md)


def export_range(from_year: int, through_year: int, people: list[dict[str, Any]],
                 decisions: dict[str, dict[str, Any]]) -> tuple[str, str]:
    """Export only the isolated inclusive range; never rewrite pre-cutoff exports."""
    selected = select_people(people, from_year=from_year, through_year=through_year)
    selected.sort(key=lambda p: (p.get("event_year_start") or 9999, p["name"], p["group_id"]))
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=CSV_EXPORT_COLUMNS, lineterminator="\n")
    writer.writeheader()
    for person in selected:
        decision = decisions[person["group_id"]]
        row = dict(person)
        row.update({
            "record_ids": " | ".join(person.get("record_ids") or []),
            "record_sets": " | ".join(person.get("record_sets") or []),
            "source_urls": " | ".join(person.get("source_urls") or []),
            "integration_outcome": decision["outcome"],
            "profile_id": decision.get("profile_id", ""),
            "creation_status": decision.get("creation_status", ""),
            "handoff_path": decision.get("handoff_path", ""),
            "decision_basis": decision["decision_source"],
        })
        writer.writerow({key: clean(row.get(key)) for key in CSV_EXPORT_COLUMNS})
    md = [
        f"# Findmypast surname-only Glasgow audit {from_year}–{through_year}", "",
        f"This integration export contains **{len(selected)}** transcript-validated conservative person groups whose supported event ranges fall wholly within {from_year}–{through_year}. Raw result rows, rejected hits, inaccessible details, duplicate IDs, exact queries, page counts and reconciliation remain preserved in [the master audit](findmypast-glasgow-audit/audit-report.md).", "",
        "| Person/event | IDs | Integration |", "| --- | --- | --- |",
    ]
    for person in selected:
        decision = decisions[person["group_id"]]
        target = decision.get("profile_id") or decision.get("handoff_path") or "blocked"
        md.append(
            f"| {person['name']}, {display_date(person)}, {clean(person.get('place'))} | "
            f"`{ '`, `'.join(person.get('record_ids') or []) }` | "
            f"{decision['outcome']}: {target} |"
        )
    md.append("")
    return buffer.getvalue(), "\n".join(md)


def catalogue_audit_entry(person: dict[str, Any], decision: dict[str, Any],
                          match: dict[str, Any]) -> dict[str, Any]:
    """Expose unresolved people in the catalogue's appropriate workbench."""
    candidates = []
    for item in match.get("candidates") or []:
        profile = item.get("profile") or {}
        candidates.append({
            "profile_id": clean(item.get("profile_id")),
            "name": clean(profile.get("LongName") or profile.get("BirthName") or item.get("profile_id")),
            "birth_date": clean(profile.get("BirthDate")),
            "birth_location": clean(profile.get("BirthLocation")),
            "death_date": clean(profile.get("DeathDate")),
            "death_location": clean(profile.get("DeathLocation")),
            "score": 0,
            "url": clean(item.get("url")) or f"https://www.wikitree.com/wiki/{quote(clean(item.get('profile_id')))}",
            "status": "candidate only; identity not established",
        })
    if decision["outcome"] == "free_space":
        action = "do_not_create"
        identity_status = "free_space_only"
    elif decision["creation_status"] == "HOLD":
        action = "hold"
        identity_status = "candidate_review"
    else:
        action = "create_new_profile"
        identity_status = "no_match_found"
    return {
        "identity_status": identity_status,
        "identity_note": (
            "This evidence belongs on a supporting free-space research page; do not create a person profile from it."
            if decision["outcome"] == "free_space" else
            "No profile is confirmed. Creation remains on hold while listed candidates are unresolved."
            if decision["creation_status"] == "HOLD" and candidates else
            "The record does not yet define a safely distinct person. Consolidate it with compatible records before considering profile creation."
            if decision["creation_status"] == "HOLD" else
            "Completed local and live WikiTree searches found no compatible profile."
        ),
        "recommended_action": action,
        "draft_path": decision["handoff_path"],
        "candidates": candidates,
        "searched_profile_count": int(match.get("counts", {}).get("searched_profiles") or 0),
        "source_group_id": person["group_id"],
    }


def write_generated_draft(path: Path, content: str, group_id: str) -> bool:
    """Update our own draft, but preserve a pre-existing hand-edited draft."""
    if not path.exists():
        atomic_write_text(path, content)
        return True
    old = path.read_text(encoding="utf-8")
    begin, end = f"<!-- BEGIN FMP-GLASGOW-{group_id} -->", f"<!-- END FMP-GLASGOW-{group_id} -->"
    if begin not in old or end not in old:
        return False
    pattern = re.compile(re.escape(begin) + r".*?" + re.escape(end), re.S)
    atomic_write_text(path, pattern.sub(content.rstrip(), old))
    return True


def retire_obsolete_generated_drafts(
    decisions: dict[str, dict[str, Any]], valid_group_ids: set[str]
) -> list[str]:
    """Remove only wholly generated drafts now mapped or consolidated away."""
    retired = []
    for path in (ROOT / "surname-research" / "new-people").glob("*.md"):
        text = path.read_text(encoding="utf-8")
        group_ids = re.findall(r"<!-- BEGIN FMP-GLASGOW-(fmp-glasgow-[0-9a-f]{12}) -->", text)
        if len(group_ids) != 1:
            continue
        group_id = group_ids[0]
        end = f"<!-- END FMP-GLASGOW-{group_id} -->"
        begin = f"<!-- BEGIN FMP-GLASGOW-{group_id} -->"
        managed = re.fullmatch(re.escape(begin) + r".*" + re.escape(end) + r"\s*", text, re.S)
        mapped = decisions.get(group_id, {}).get("outcome") in {
            "existing_profile", "free_space",
        }
        stale = group_id not in valid_group_ids
        if managed and (mapped or stale):
            path.unlink()
            retired.append(str(path.relative_to(ROOT)))
    return retired


def apply(plan: dict[str, Any], people_doc: dict[str, Any], matches_doc: dict[str, Any]) -> list[str]:
    if not plan["apply_ready"]:
        raise RuntimeError("Refusing --apply: " + "; ".join(plan["blockers"]))
    before_year = plan.get("scope", {}).get("before_year")
    from_year = plan.get("scope", {}).get("from_year")
    through_year = plan.get("scope", {}).get("through_year")
    people = select_people(people_doc["people"], before_year, from_year, through_year)
    scoped = before_year is not None or from_year is not None or through_year is not None
    people_by_id = {item["group_id"]: item for item in people}
    decisions = {item["group_id"]: item for item in plan["decisions"]}
    people = [reviewed_person(person, decisions[person["group_id"]]) for person in people]
    people_by_id = {item["group_id"]: item for item in people}
    matches = {item["group_id"]: item for item in matches_doc["people"]}
    valid_all_supplements = {
        clean(person.get("supplement_id")) or person["group_id"]
        for person in people_doc["people"]
    }
    changed: list[str] = []
    changed.extend(retire_obsolete_generated_drafts(decisions, valid_all_supplements))

    with RECORDS_PATH.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        header, existing = list(reader.fieldnames or []), list(reader)
    selected_supplements = {person["supplement_id"] for person in people}
    audited_urls = {url for person in people for url in person.get("source_urls") or []}
    audited_record_ids = {record_id for url in audited_urls if (record_id := findmypast_record_id(url))}
    if not scoped:
        preserved = [row for row in existing if (
            row.get("source_type") != MANAGED_SOURCE_TYPE
            and not clean(row.get("supplement_id")).startswith("fmp-glasgow-")
            and clean(row.get("source_url")) not in audited_urls
            and findmypast_record_id(row.get("source_url")) not in audited_record_ids
        )]
    else:
        preserved = [row for row in existing if (
            clean(row.get("supplement_id")) not in selected_supplements
            and clean(row.get("source_url")) not in audited_urls
            and findmypast_record_id(row.get("source_url")) not in audited_record_ids
            and not (
                row.get("source_type") == MANAGED_SOURCE_TYPE
                and clean(row.get("supplement_id")).startswith("fmp-glasgow-")
                and clean(row.get("supplement_id")) not in valid_all_supplements
            )
        )]
    generated = [person_record(
        person, decisions[person["group_id"]], header, before_year,
        from_year, through_year,
        bool(plan["source_audit_complete_and_reconciled"]),
    ) for person in people]
    atomic_write_csv(
        RECORDS_PATH,
        header,
        preserved + generated,
        lineterminator="\n",
    )
    changed.append(str(RECORDS_PATH.relative_to(ROOT)))

    for person in people:
        decision = decisions[person["group_id"]]
        if decision["outcome"] == "existing_profile":
            path = ROOT / "research" / decision["profile_id"] / "findings.md"
            path.parent.mkdir(parents=True, exist_ok=True)
            old = path.read_text(encoding="utf-8") if path.exists() else f"# {decision['profile_id']} research findings\n"
            tag = f"FMP-GLASGOW-{person['group_id']}"
            begin, end = f"<!-- BEGIN {tag} -->", f"<!-- END {tag} -->"
            section = f"{begin}\n{render_finding(person, decision).rstrip()}\n{end}"
            pattern = re.compile(re.escape(begin) + r".*?" + re.escape(end), re.S)
            updated = (
                pattern.sub(section, old)
                if pattern.search(old)
                else old.rstrip() + "\n\n" + section + "\n"
            )
            atomic_write_text(path, updated)
        else:
            path = ROOT / decision["handoff_path"]
            path.parent.mkdir(parents=True, exist_ok=True)
            wrote = write_generated_draft(path, render_draft(person, decision, matches[person["group_id"]]), person["group_id"])
            if not wrote:
                continue
        changed.append(str(path.relative_to(ROOT)))

    profile_audit = json.loads(PROFILE_AUDIT_PATH.read_text(encoding="utf-8")) if PROFILE_AUDIT_PATH.exists() else {"schema_version": 1, "audited_at": "", "entries": {}}
    entries = profile_audit.setdefault("entries", {})
    selected_catalogue_ids = {
        "record-" + re.sub(r"[^a-z0-9]+", "-", supplement.casefold()).strip("-")
        for supplement in selected_supplements
    }
    for key in [key for key, entry in entries.items() if (
        key in selected_catalogue_ids or clean(entry.get("source_group_id")) in decisions
        or (
            clean(entry.get("source_group_id")).startswith("fmp-glasgow-")
            and clean(entry.get("source_group_id")) not in valid_all_supplements
        )
    )]:
        del entries[key]
    for person in people:
        decision = decisions[person["group_id"]]
        if decision["outcome"] != "existing_profile":
            catalogue_id = "record-" + re.sub(r"[^a-z0-9]+", "-", decision["supplement_id"].casefold()).strip("-")
            entries[catalogue_id] = catalogue_audit_entry(person, decision, matches[person["group_id"]])
    latest = clean(plan.get("latest_detail_capture_at"))[:10]
    if latest > clean(profile_audit.get("audited_at")):
        profile_audit["audited_at"] = latest
    atomic_write_text(
        PROFILE_AUDIT_PATH,
        json.dumps(profile_audit, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )
    changed.append(str(PROFILE_AUDIT_PATH.relative_to(ROOT)))

    queue_groups = {
        "existing_profile": ["### Existing-profile amendments", "", "| Target | Status | Work | Handoff |", "| --- | --- | --- | --- |"],
        "new_person": ["### New-person handoffs", "", "READY rows have passed the distinct-person and no-compatible-profile checks; documentary records that cannot define a safe person are routed to supporting free-space research below.", "", "| Target | Status | Work | Handoff |", "| --- | --- | --- | --- |"],
        "free_space": ["### Supporting free-space research (never person profiles)", "", "| Target | Status | Work | Handoff |", "| --- | --- | --- | --- |"],
    }
    scope_heading = scope_label(before_year, from_year, through_year)
    incomplete_note = " Source scrape/transcript audit remains **INCOMPLETE**; this section covers only currently validated records." if not plan["source_audit_complete_and_reconciled"] else ""
    register_lines = [f"## Findmypast Glasgow surname audit {scope_heading}", "", incomplete_note.strip(), "", "| Stable ID | Person/event | Record IDs | Integration |", "| --- | --- | --- | --- |"]
    for person in sorted(people, key=lambda p: (p.get("event_year_start") or 9999, p["name"], p["group_id"])):
        d = decisions[person["group_id"]]
        target = d.get("profile_id") or d.get("handoff_path")
        if d["outcome"] == "existing_profile":
            queue_target = f"[{person['name']} ({target})](https://www.wikitree.com/wiki/{quote(target)})"
            handoff = f"[Replacement draft](../research/{target}/{target}.md)"
        else:
            relative = str(Path(d["handoff_path"]).relative_to("surname-research"))
            queue_target = person["name"]
            handoff = f"[{'Free-space draft' if d['outcome'] == 'free_space' else 'Draft'}]({relative})"
        queue_work = d.get("queue_work") or (
            f"Add {display_date(person)} Findmypast evidence ({d['supplement_id']}); "
            f"{d.get('creation_status') or 'profile amendment'}"
        )
        if d["outcome"] != "existing_profile" or d.get("substantive_amendment"):
            queue_groups[d["outcome"]].append(
                f"| {queue_target} | {d.get('queue_status') or 'OPEN'} | {queue_work} | {handoff} |"
            )
        register_lines.append(f"| `{d['supplement_id']}` | {person['name']}, {display_date(person)}, {clean(person.get('place'))} | `{ '`, `'.join(person.get('record_ids') or []) }` | {d['outcome']}: {target} |")
    queue_lines = [f"## Findmypast Glasgow surname audit {scope_heading}", "", incomplete_note.strip(), ""]
    for outcome in ("existing_profile", "new_person", "free_space"):
        queue_lines.extend(queue_groups[outcome] + [""])
    if before_year is not None:
        block_tag = f"{BLOCK_TAG}-PRE{before_year}"
    elif from_year is not None and through_year is not None:
        block_tag = f"{BLOCK_TAG}-{from_year}-{through_year}"
    else:
        block_tag = BLOCK_TAG
    for path, body in ((QUEUE_PATH, "\n".join(queue_lines)), (REGISTER_PATH, "\n".join(register_lines))):
        old = path.read_text(encoding="utf-8") if path.exists() else ""
        # Remove only selected managed rows from a prior broader block; retain all later groups.
        if scoped:
            old = strip_group_rows_from_block(old, selected_supplements)
        atomic_write_text(path, replace_block(old, body, block_tag))
        changed.append(str(path.relative_to(ROOT)))

    if from_year is not None and through_year is not None:
        csv_text, md_text = export_range(from_year, through_year, people, decisions)
        csv_path = ROOT / "research" / f"findmypast-glasgow-surname-{from_year}-{through_year}.csv"
        md_path = ROOT / "research" / f"findmypast-glasgow-{from_year}-{through_year}.md"
        atomic_write_text(csv_path, csv_text)
        atomic_write_text(md_path, md_text)
        changed += [str(csv_path.relative_to(ROOT)), str(md_path.relative_to(ROOT))]
    else:
        cutoffs = (1600, before_year) if before_year is not None else (1600, 1700, 1750)
        for cutoff in cutoffs:
            csv_text, md_text = export_rows(
                cutoff, people, decisions,
                inclusive=cutoff == 1750 and before_year is None,
            )
            csv_path = ROOT / "research" / f"findmypast-glasgow-surname-pre{cutoff}.csv"
            md_path = ROOT / "research" / f"findmypast-glasgow-pre{cutoff}.md"
            atomic_write_text(csv_path, csv_text)
            atomic_write_text(md_path, md_text)
            changed += [str(csv_path.relative_to(ROOT)), str(md_path.relative_to(ROOT))]

    provenance = [
        f"# Findmypast Glasgow integration provenance {scope_heading}", "",
        f"Materialized from `{plan['inputs']['people']}` and `{plan['inputs']['matches']}` with `{plan['inputs']['overrides']}`.", "",
        f"Source snapshot SHA-256: `{plan['source_snapshot_sha256']}`. Latest saved detail capture: `{plan['latest_detail_capture_at'] or 'not recorded'}`. Integrated person groups {scope_heading}: **{plan['counts']['validated_person_groups']}**.", "",
        f"The master source scrape/transcript audit is **{plan['source_audit_label']}**. This scoped integration includes only currently transcript-validated groups and does not claim a complete Findmypast scrape.", "",
        "Each catalogue row carries the stable `fmp-glasgow-*` supplement/source ID from its conservative person group. Full transcripts remain in the detail overlays named by `audit-distinct-people.json`; raw rows, duplicate IDs, rejected hits, inaccessible records, queries, totals, URLs and page reconciliation remain in the master audit artifacts.", "",
        "No same-name people or separate events were merged by this materializer. Human decisions are auditable in the override file.", "",
    ]
    provenance_path = scoped_path(PROVENANCE_PATH, before_year, from_year, through_year)
    atomic_write_text(provenance_path, "\n".join(provenance))
    changed.append(str(provenance_path.relative_to(ROOT)))
    return sorted(set(changed))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="apply only a plan that passes its global or scoped safeguards")
    parser.add_argument("--before-year", type=int, choices=(1650,), help="integrate only groups whose event_year_end is before this year")
    parser.add_argument("--from-year", type=int, metavar="YEAR", help="range scope start, inclusive")
    parser.add_argument("--through-year", type=int, metavar="YEAR", help="range scope end, inclusive")
    args = parser.parse_args()
    has_range = args.from_year is not None or args.through_year is not None
    if has_range and (args.from_year is None or args.through_year is None):
        parser.error("--from-year and --through-year must be supplied together")
    if has_range and args.before_year is not None:
        parser.error("--before-year cannot be combined with --from-year/--through-year")
    if has_range and not (1 <= args.from_year <= args.through_year <= 9999):
        parser.error("range years must satisfy 1 <= --from-year <= --through-year <= 9999")
    people_doc, matches_doc, overrides_doc = load_inputs(
        args.before_year, args.from_year, args.through_year)
    plan = build_plan(
        people_doc, matches_doc, overrides_doc,
        args.before_year, args.from_year, args.through_year,
    )
    people_by_id = {item["group_id"]: item for item in people_doc["people"]}
    plan_json = scoped_path(
        PLAN_JSON, args.before_year, args.from_year, args.through_year)
    plan_md = scoped_path(
        PLAN_MD, args.before_year, args.from_year, args.through_year)
    atomic_write_text(
        plan_json,
        json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )
    atomic_write_text(plan_md, plan_markdown(plan, people_by_id))
    if args.apply:
        changed = apply(plan, people_doc, matches_doc)
        print(canonical({"applied": True, "changed_files": changed, "counts": plan["counts"]}))
        return 0
    print(canonical({"applied": False, "apply_ready": plan["apply_ready"], "blockers": plan["blockers"], "counts": plan["counts"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
