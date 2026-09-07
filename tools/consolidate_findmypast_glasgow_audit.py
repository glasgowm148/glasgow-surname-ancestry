#!/usr/bin/env python3
"""Consolidate and reconcile Findmypast Glasgow surname result windows.

The browser capture is deliberately preserved as the source of truth.  This
script produces deterministic, reviewable derivatives without claiming that a
result-row date proves a historical identity.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import parse_qs, urlparse


DEFAULT_INPUT = Path("research/findmypast-glasgow-audit")
TARGET_START = 1
TARGET_END = 1750
PAGE_SIZE = 20
MAX_ACCESSIBLE_PAGES = 75
DATE_FIELDS = ("event_year", "year_of_birth", "year_of_death")
ROW_COLUMNS = (
    "classification",
    "classification_reasons",
    "review_status",
    "review_reason",
    "review_source",
    "detail_access_status",
    "detail_block_reason",
    "detail_captured_at",
    "detail_url",
    "detail_source_file",
    "record_id",
    "record_occurrences",
    "included_in_analysis",
    "exclusion_reason",
    "window_eventyear",
    "window_start",
    "window_end",
    "partition_type",
    "partition_group",
    "partition_group_id",
    "sourcecategory",
    "sourcecountry",
    "sort",
    "control_query",
    "page",
    "page_url_number",
    "page_url_matches_claim",
    "row_on_page",
    "first_name",
    "last_name",
    "event_year",
    "year_of_birth",
    "year_of_death",
    "location",
    "record_set",
    "subscription_locked",
    "transcript_url",
    "image_url",
    "result_page_url",
    "captured_at",
    "source_file",
    "links_json",
    "accessible_detail_json",
    "raw_row_json",
)


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def clean(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return "" if text in {"—", "-", ""} else text


def is_daily_limit(detail: dict[str, Any]) -> bool:
    """Identify temporary fair-use blocking without changing schema status."""
    return clean(detail.get("block_reason")).casefold() == "daily_limit"


def normalized(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", clean(value).casefold()).strip()


def years(value: Any) -> list[int]:
    """Return visible year-like integers, without expanding short years."""
    return [int(part) for part in re.findall(r"(?<!\d)\d{1,4}(?!\d)", clean(value))]


def first_link(row: dict[str, Any], label_fragment: str) -> str:
    for link in row.get("links") or []:
        if label_fragment in normalized(link.get("label")):
            return clean(link.get("url"))
    return ""


def accessible_detail(row: dict[str, Any]) -> dict[str, Any]:
    """Retain detail/transcript fields added by later browser passes."""
    result_keys = {
        "event_year", "first_name", "last_name", "links", "location",
        "record_id", "record_set", "subscription_locked", "year_of_birth",
        "year_of_death",
    }
    return {key: row[key] for key in sorted(row) if key not in result_keys}


def explicit_surname_verdict(row: dict[str, Any]) -> bool | None:
    """Read a browser/reviewer verdict when one is saved with the raw row."""
    for key in ("surname_validated", "surname_is_glasgow"):
        if key in row and isinstance(row[key], bool):
            return row[key]
    for key in ("surname_status", "surname_classification"):
        status = normalized(row.get(key))
        if status in {"confirmed", "glasgow surname", "surname confirmed", "valid"}:
            return True
        if status in {"false hit", "not surname", "office", "place", "title", "rejected"}:
            return False
    return None


def query_is_exact_surname_only(query: dict[str, Any]) -> bool:
    parsed = parse_qs(urlparse(clean(query.get("url"))).query)
    place_keys = {"location", "place", "eventlocation", "parish", "county", "country"}
    filters_match = all(
        (not clean(query.get(key)) and not parsed.get(key))
        or parsed.get(key, [""])[0] == clean(query.get(key))
        for key in ("sourcecategory", "sourcecountry")
    )
    sort_expected = clean(query.get("sort"))
    sort_actual = next((parsed[key][0] for key in ("sort", "_sort", "order_by", "orderby") if parsed.get(key)), "")
    filters_match = filters_match and (sort_actual == sort_expected)
    return (
        normalized(query.get("surname")) == "glasgow"
        and query.get("surname_variants") is False
        and not clean(query.get("place"))
        and parsed.get("lastname", [""])[0].casefold() == "glasgow"
        and parsed.get("eventyear", [""])[0] == str(query.get("eventyear", ""))
        and parsed.get("eventyear_offset", [""])[0] == str(query.get("eventyear_offset", ""))
        and not any(parsed.get(key) for key in place_keys)
        and filters_match
    )


def page_url_number(page: dict[str, Any]) -> int:
    parsed = parse_qs(urlparse(clean(page.get("url"))).query)
    raw = parsed.get("_page", ["1"])[0]
    try:
        return int(raw)
    except (TypeError, ValueError):
        return 0


def interval_is_covered(start: int, end: int, intervals: list[tuple[int, int]]) -> bool:
    cursor = start
    for other_start, other_end in sorted(intervals):
        if other_end < cursor:
            continue
        if other_start > cursor:
            return False
        cursor = max(cursor, other_end + 1)
        if cursor > end:
            return True
    return cursor > end


def facet_counts(data: dict[str, Any], partition_type: str) -> dict[str, int]:
    """Read nonzero partition facets from common capture shapes."""
    aliases = {
        "sourcecategory": ("sourcecategory", "SourceCollection", "source_collection"),
        "sourcecountry": ("sourcecountry", "SourceCountry", "source_country"),
    }.get(partition_type, (partition_type,))
    candidates: list[Any] = []
    for alias in aliases:
        candidates.extend([
            data.get(f"{alias}_facets"),
            (data.get("query") or {}).get(f"{alias}_facets") if isinstance(data.get("query"), dict) else None,
            (data.get("facet_counts") or {}).get(alias) if isinstance(data.get("facet_counts"), dict) else None,
            (data.get("facets") or {}).get(alias) if isinstance(data.get("facets"), dict) else None,
        ])
    for candidate in candidates:
        parsed: dict[str, int] = {}
        if isinstance(candidate, dict):
            for name, value in candidate.items():
                count = value.get("count", value.get("total", 0)) if isinstance(value, dict) else value
                try:
                    parsed[clean(name).casefold()] = int(count)
                except (TypeError, ValueError):
                    pass
        elif isinstance(candidate, list):
            for item in candidate:
                if not isinstance(item, dict):
                    continue
                name = item.get("value", item.get("name", item.get("label", "")))
                count = item.get("count", item.get("total", 0))
                try:
                    parsed[clean(name).casefold()] = int(count)
                except (TypeError, ValueError):
                    pass
        parsed = {name: count for name, count in parsed.items() if name and count > 0}
        if parsed:
            return parsed
    return {}


def partition_value(query: dict[str, Any], partition_type: str) -> str:
    return clean(query.get(partition_type)).casefold()


def same_partition_filters(left: dict[str, Any], right: dict[str, Any]) -> bool:
    return all(
        clean(left.get(key)).casefold() == clean(right.get(key)).casefold()
        for key in ("sourcecategory", "sourcecountry")
    )


def resolve_facet_partitions(window_specs: list[dict[str, Any]]) -> None:
    changed = True
    while changed:
        changed = False
        for spec in window_specs:
            if spec["effective_complete"] or spec["expected_pages"] <= MAX_ACCESSIBLE_PAGES:
                continue
            country_facets = facet_counts(spec["data"], "sourcecountry")
            category_facets = facet_counts(spec["data"], "sourcecategory")
            if country_facets:
                child_type, required = "sourcecountry", country_facets
            elif category_facets:
                child_type, required = "sourcecategory", category_facets
            else:
                continue
            if sum(required.values()) != spec["displayed_total"]:
                continue
            groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
            for child in window_specs:
                cq = child["query"]
                if (
                    child["partition_type"] == child_type
                    and child["partition_group"]
                    and child["start"] == spec["start"] and child["end"] == spec["end"]
                    and (not clean(spec["query"].get("sourcecategory")) or clean(cq.get("sourcecategory")) == clean(spec["query"].get("sourcecategory")))
                    and (not clean(spec["query"].get("sourcecountry")) or clean(cq.get("sourcecountry")) == clean(spec["query"].get("sourcecountry")))
                ):
                    groups[child["partition_group"]].append(child)
            for group, children in groups.items():
                parent_group_id = clean(spec["query"].get("partition_group_id"))
                if parent_group_id and group != parent_group_id:
                    continue
                selected: list[dict[str, Any]] = []
                complete = True
                for value, count in required.items():
                    matches = [
                        child for child in children
                        if child["effective_complete"]
                        and partition_value(child["query"], child_type) == value
                        and child["displayed_total"] == count
                    ]
                    if not matches:
                        complete = False
                        break
                    selected.append(sorted(matches, key=lambda child: child["path"].name)[0])
                if complete and {partition_value(child["query"], child_type) for child in selected} == set(required):
                    spec["effective_complete"] = True
                    spec["partition_superseded"] = True
                    spec["supersession_reason"] = f"complete {child_type} partition group {group}"
                    changed = True
                    break


def resolve_accounted_partitions(window_specs: list[dict[str, Any]]) -> None:
    """Account for parents whose only incomplete children are documented caps."""
    changed = True
    while changed:
        changed = False
        for spec in window_specs:
            if spec["accounted_complete"]:
                continue
            country_facets = facet_counts(spec["data"], "sourcecountry")
            category_facets = facet_counts(spec["data"], "sourcecategory")
            if country_facets:
                child_type, required = "sourcecountry", country_facets
            elif category_facets:
                child_type, required = "sourcecategory", category_facets
            else:
                continue
            if sum(required.values()) != spec["displayed_total"]:
                continue
            groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
            for child in window_specs:
                cq = child["query"]
                if (
                    child["partition_type"] == child_type
                    and child["partition_group"]
                    and child["start"] == spec["start"] and child["end"] == spec["end"]
                    and (not clean(spec["query"].get("sourcecategory")) or clean(cq.get("sourcecategory")) == clean(spec["query"].get("sourcecategory")))
                    and (not clean(spec["query"].get("sourcecountry")) or clean(cq.get("sourcecountry")) == clean(spec["query"].get("sourcecountry")))
                ):
                    groups[child["partition_group"]].append(child)
            for group, children in groups.items():
                parent_group_id = clean(spec["query"].get("partition_group_id"))
                if parent_group_id and group != parent_group_id:
                    continue
                selected = []
                for value, count in required.items():
                    matches = [
                        child for child in children
                        if child["accounted_complete"]
                        and partition_value(child["query"], child_type) == value
                        and child["displayed_total"] == count
                    ]
                    if not matches:
                        break
                    selected.append(matches[0])
                if len(selected) == len(required):
                    spec["accounted_complete"] = True
                    spec["accounted_reason"] = f"category totals accounted by {child_type} group {group}"
                    changed = True
                    break


def classify(row: dict[str, Any], start: int, end: int) -> tuple[str, list[str]]:
    surname = normalized(row.get("last_name"))
    surname_verdict = explicit_surname_verdict(row)
    values = {field: years(row.get(field)) for field in DATE_FIELDS}
    all_years = [year for field_years in values.values() for year in field_years]
    event_years = values["event_year"]
    reasons: list[str] = []

    if surname_verdict is False:
        return "rejected_surname", ["full-record review explicitly rejected Glasgow as the surname"]
    if surname != "glasgow":
        return "non_exact_display_hit", ["displayed surname is not exactly Glasgow; inspect the matched page/transcript"]

    if not all_years:
        return "date_anomaly_review", ["no visible event, birth, or death year"]

    if surname_verdict is not True:
        reasons.append("full record has not yet validated Glasgow as a surname")
    if any(year < 1000 for year in all_years):
        reasons.append("one-to-three-digit year may be a truncated modern year")
    scope_years = event_years or all_years
    if any(year < start or year > end for year in scope_years):
        reasons.append("displayed scope year falls outside the query window")
    if not event_years:
        reasons.append("scope derived from visible birth/death year")

    if all(year > TARGET_END for year in scope_years):
        return "out_of_scope", reasons + [f"displayed scope year is after {TARGET_END}"]
    if any(TARGET_START <= year <= TARGET_END for year in scope_years):
        informational = {
            "full record has not yet validated Glasgow as a surname",
            "scope derived from visible birth/death year",
        }
        if any(reason not in informational for reason in reasons):
            return "date_anomaly_review", reasons
        return "candidate_in_scope", reasons
    return "date_anomaly_review", reasons or ["date cannot establish in-scope event"]


def csv_value(value: Any) -> Any:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return ""
    return value


def write_csv(path: Path, rows: Iterable[dict[str, Any]], columns: Iterable[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns), extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: csv_value(row.get(key, "")) for key in writer.fieldnames})


def range_audit(intervals: list[tuple[int, int]]) -> dict[str, Any]:
    clipped = sorted((max(TARGET_START, a), min(TARGET_END, b)) for a, b in intervals if b >= TARGET_START and a <= TARGET_END)
    gaps: list[list[int]] = []
    overlaps: list[list[int]] = []
    cursor = TARGET_START
    previous_end = TARGET_START - 1
    for start, end in clipped:
        if start > cursor:
            gaps.append([cursor, start - 1])
        if start <= previous_end:
            overlaps.append([start, min(end, previous_end)])
        cursor = max(cursor, end + 1)
        previous_end = max(previous_end, end)
    if cursor <= TARGET_END:
        gaps.append([cursor, TARGET_END])
    return {
        "target": [TARGET_START, TARGET_END],
        "intervals": [list(pair) for pair in clipped],
        "gaps": gaps,
        "overlaps": overlaps,
        "gap_free": not gaps,
    }


def load_windows(input_dir: Path) -> list[tuple[Path, dict[str, Any]]]:
    loaded = []
    for path in input_dir.glob("raw-results-*.json"):
        with path.open(encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, dict) or "query" not in data or "pages" not in data:
            raise ValueError(f"Unexpected window schema: {path}")
        loaded.append((path, data))
    return sorted(loaded, key=lambda item: (int(item[1]["query"].get("eventyear", 0)), item[0].name))


def load_detail_overlays(input_dir: Path) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    """Load immutable record-detail captures keyed by Findmypast record ID."""
    details: dict[str, dict[str, Any]] = {}
    sources: dict[str, str] = {}
    for path in sorted(input_dir.glob("record-details*.json")):
        with path.open(encoding="utf-8") as handle:
            payload = json.load(handle)
        records = payload.get("records") if isinstance(payload, dict) else None
        if not isinstance(records, dict):
            raise ValueError(f"Detail overlay must contain a records object: {path}")
        for record_id, detail in records.items():
            if not clean(record_id) or not isinstance(detail, dict):
                raise ValueError(f"Invalid detail entry in {path}: {record_id!r}")
            if record_id in details and canonical(details[record_id]) != canonical(detail):
                raise ValueError(f"Conflicting detail overlays for {record_id}: {sources[record_id]} and {path.name}")
            details[record_id] = detail
            sources[record_id] = path.name
    return details, sources


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=None)
    args = parser.parse_args()
    input_dir = args.input_dir
    output_dir = args.output_dir or input_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    windows = load_windows(input_dir)
    review_path = input_dir / "record-review-overrides.json"
    if review_path.exists():
        with review_path.open(encoding="utf-8") as handle:
            reviews = json.load(handle)
    else:
        reviews = {}
    if not isinstance(reviews, dict):
        raise ValueError(f"Review overrides must be an object keyed by record ID: {review_path}")
    details, detail_sources = load_detail_overlays(input_dir)
    window_rows: list[dict[str, Any]] = []
    occurrences: list[dict[str, Any]] = []
    intervals: list[tuple[int, int]] = []

    window_specs: list[dict[str, Any]] = []
    for path, data in windows:
        query = data["query"]
        covered = query.get("covered_years") or []
        start, end = (int(covered[0]), int(covered[1])) if len(covered) == 2 else (0, 0)
        pages = data.get("pages") or []
        displayed_total = int(data.get("displayed_total", 0))
        expected_pages = int(data.get("expected_pages", 0))
        actual_rows = sum(len(page.get("rows") or []) for page in pages)
        page_numbers = [int(page.get("page", 0)) for page in pages]
        url_numbers = [page_url_number(page) for page in pages]
        page_lengths = [len(page.get("rows") or []) for page in pages]
        expected_from_total = math.ceil(displayed_total / PAGE_SIZE) if displayed_total else 0
        expected_lengths = (
            [PAGE_SIZE] * max(0, expected_pages - 1)
            + ([displayed_total - PAGE_SIZE * (expected_pages - 1)] if expected_pages else [])
        )
        expected_covered = [
            max(TARGET_START, int(query.get("eventyear", 0)) - int(query.get("eventyear_offset", 0))),
            int(query.get("eventyear", 0)) + int(query.get("eventyear_offset", 0)),
        ]
        directly_usable = (
            expected_pages <= MAX_ACCESSIBLE_PAGES
            and bool(data.get("reconciled"))
            and query_is_exact_surname_only(query)
            and [start, end] == expected_covered
            and expected_pages == expected_from_total
            and displayed_total == actual_rows
            and len(pages) == expected_pages
            and page_numbers == url_numbers == list(range(1, len(pages) + 1))
            and page_lengths == expected_lengths
            and int(data.get("captured_pages", 0)) == len(pages)
            and int(data.get("captured_rows", 0)) == actual_rows
        )
        valid_accessible_pages = sum(
            claimed == actual and 1 <= actual <= MAX_ACCESSIBLE_PAGES
            for claimed, actual in zip(page_numbers, url_numbers)
        )
        partition_limit_evidence = any(
            isinstance(query.get(key), dict) and bool(query.get(key))
            for key in (
                "page_cap_evidence", "facet_retrieval_mismatches",
                "partition_attempts", "date_partition_facets",
            )
        )
        documented_limited_leaf = (
            expected_pages > MAX_ACCESSIBLE_PAGES
            and page_numbers == url_numbers == list(range(1, MAX_ACCESSIBLE_PAGES + 1))
            and page_lengths == [PAGE_SIZE] * MAX_ACCESSIBLE_PAGES
            and int(data.get("captured_pages", 0)) == MAX_ACCESSIBLE_PAGES
            and int(data.get("captured_rows", 0)) == PAGE_SIZE * MAX_ACCESSIBLE_PAGES
            and query_is_exact_surname_only(query)
            and [start, end] == expected_covered
            and partition_limit_evidence
            and clean(query.get("partition_type")) != ""
            and normalized(query.get("sourcecategory")) == "travel migration"
            and not bool(query.get("control_query"))
        )
        window_specs.append({
            "path": path, "data": data, "query": query, "start": start,
            "end": end, "pages": pages, "displayed_total": displayed_total,
            "expected_pages": expected_pages, "directly_usable": directly_usable,
            "partition_type": clean(query.get("partition_type")).casefold(),
            "partition_group": clean(query.get("partition_group")),
            "effective_complete": directly_usable,
            "partition_superseded": False,
            "supersession_reason": "",
            "documented_limited_leaf": documented_limited_leaf,
        })

    # Resolve disjoint facet children first, then nested narrower date windows,
    # then re-run facets so a repaired category can satisfy its broad parent.
    resolve_facet_partitions(window_specs)
    for spec in sorted(window_specs, key=lambda item: item["end"] - item["start"]):
        span = spec["end"] - spec["start"]
        narrower = [
            (other["start"], other["end"])
            for other in window_specs
            if other is not spec and other["effective_complete"]
            and other["end"] - other["start"] < span
            and same_partition_filters(spec["query"], other["query"])
        ]
        narrow_superseded = (
            spec["expected_pages"] > MAX_ACCESSIBLE_PAGES
            and not spec["partition_superseded"]
            and interval_is_covered(spec["start"], spec["end"], narrower)
        )
        if narrow_superseded:
            spec["effective_complete"] = True
            spec["supersession_reason"] = "complete narrower date windows"
        spec["superseded"] = spec["partition_superseded"] or narrow_superseded
    resolve_facet_partitions(window_specs)
    for spec in window_specs:
        spec["superseded"] = spec["partition_superseded"] or bool(spec["supersession_reason"])
        spec["genuine_limited_leaf"] = spec["documented_limited_leaf"] and not spec["superseded"]
        spec["accounted_complete"] = spec["effective_complete"] or spec["genuine_limited_leaf"]
        spec["accounted_reason"] = "documented page-cap-limited leaf" if spec["genuine_limited_leaf"] else ""
    resolve_accounted_partitions(window_specs)

    fully_reconciled_intervals = [
        (spec["start"], spec["end"])
        for spec in window_specs
        if not spec["partition_type"] and spec["effective_complete"]
        and not bool(spec["query"].get("control_query"))
    ]
    searched_intervals = [
        (spec["start"], spec["end"])
        for spec in window_specs
        if not spec["partition_type"] and spec["accounted_complete"]
        and not bool(spec["query"].get("control_query"))
    ]

    for spec in window_specs:
        path, data, query = spec["path"], spec["data"], spec["query"]
        start, end, pages = spec["start"], spec["end"], spec["pages"]
        page_numbers = [int(page.get("page", 0)) for page in pages]
        page_url_numbers = [page_url_number(page) for page in pages]
        page_lengths = [len(page.get("rows") or []) for page in pages]
        actual_rows = sum(len(page.get("rows") or []) for page in pages)
        displayed_total = spec["displayed_total"]
        expected_from_total = math.ceil(displayed_total / PAGE_SIZE) if displayed_total else 0
        expected_pages = spec["expected_pages"]
        declared_pages = int(data.get("captured_pages", 0))
        declared_rows = int(data.get("captured_rows", 0))
        contiguous = page_numbers == list(range(1, len(pages) + 1))
        expected_page_lengths = (
            [PAGE_SIZE] * max(0, expected_pages - 1)
            + ([displayed_total - PAGE_SIZE * (expected_pages - 1)] if expected_pages else [])
        )
        checks = {
            "query_is_exact_surname_only": query_is_exact_surname_only(query),
            "covered_years_match_query": [start, end] == [
                max(TARGET_START, int(query.get("eventyear", 0)) - int(query.get("eventyear_offset", 0))),
                int(query.get("eventyear", 0)) + int(query.get("eventyear_offset", 0)),
            ],
            "displayed_total_equals_actual_rows": displayed_total == actual_rows,
            "declared_rows_equals_actual_rows": declared_rows == actual_rows,
            "declared_pages_equals_actual_pages": declared_pages == len(pages),
            "expected_pages_equals_total_pages": expected_pages == expected_from_total,
            "actual_pages_equals_expected_pages": len(pages) == expected_pages,
            "page_numbers_contiguous": contiguous,
            "page_urls_match_claimed_pages": page_url_numbers == page_numbers,
            "page_row_counts_match_page_size": page_lengths == expected_page_lengths,
            "expected_pages_within_site_cap": expected_pages <= MAX_ACCESSIBLE_PAGES,
            "capture_marked_reconciled": bool(data.get("reconciled")),
        }
        reconciled = all(checks.values())
        analysis_included = (reconciled and not spec["superseded"]) or spec["genuine_limited_leaf"]
        valid_page_count = sum(
            claimed == actual and 1 <= actual <= MAX_ACCESSIBLE_PAGES
            for claimed, actual in zip(page_numbers, page_url_numbers)
        )
        window_rows.append({
            "source_file": path.name,
            "eventyear": query.get("eventyear", ""),
            "offset": query.get("eventyear_offset", ""),
            "covered_start": start,
            "covered_end": end,
            "partition_type": clean(query.get("partition_type")),
            "partition_group": clean(query.get("partition_group")),
            "partition_group_id": clean(query.get("partition_group_id")),
            "sourcecategory": clean(query.get("sourcecategory")),
            "sourcecountry": clean(query.get("sourcecountry")),
            "sort": clean(query.get("sort")),
            "control_query": bool(query.get("control_query")),
            "previous_manual_total": query.get("previous_manual_total", ""),
            "surname": query.get("surname", ""),
            "surname_variants": query.get("surname_variants", ""),
            "place": query.get("place", ""),
            "query_url": query.get("url", ""),
            "started_at": data.get("started_at", ""),
            "completed_at": data.get("completed_at", ""),
            "displayed_total": displayed_total,
            "expected_pages": expected_pages,
            "site_page_cap": MAX_ACCESSIBLE_PAGES,
            "page_cap_exceeded": expected_pages > MAX_ACCESSIBLE_PAGES,
            "superseded": spec["superseded"],
            "superseded_by_narrower_windows": spec["superseded"],
            "effective_complete": spec["effective_complete"],
            "supersession_reason": spec["supersession_reason"],
            "genuine_limited_leaf": spec["genuine_limited_leaf"],
            "accounted_complete": spec["accounted_complete"],
            "accounted_reason": spec["accounted_reason"],
            "sourcecategory_facets_json": canonical(facet_counts(data, "sourcecategory")),
            "sourcecountry_facets_json": canonical(facet_counts(data, "sourcecountry")),
            "date_partition_facets_json": canonical(query.get("date_partition_facets") or {}),
            "facet_retrieval_mismatches_json": canonical(query.get("facet_retrieval_mismatches") or {}),
            "included_in_analysis": analysis_included,
            "captured_pages_declared": declared_pages,
            "captured_pages_actual": len(pages),
            "valid_accessible_pages": valid_page_count,
            "captured_rows_declared": declared_rows,
            "captured_rows_actual": actual_rows,
            "page_numbers": ",".join(map(str, page_numbers)),
            "page_url_numbers": ",".join(map(str, page_url_numbers)),
            "page_row_counts": ",".join(map(str, page_lengths)),
            "reconciled": reconciled,
            "failed_checks": "; ".join(key for key, passed in checks.items() if not passed),
        })
        for page in pages:
            claimed_page = int(page.get("page", 0))
            actual_page = page_url_number(page)
            page_valid = claimed_page == actual_page and 1 <= actual_page <= MAX_ACCESSIBLE_PAGES
            include_row = analysis_included and page_valid
            if include_row:
                exclusion_reason = ""
            elif spec["superseded"]:
                exclusion_reason = "superseded broad/capped window"
            elif spec["accounted_complete"]:
                exclusion_reason = "parent query accounted by partition children"
            elif not page_valid:
                exclusion_reason = "pagination redirect or page beyond site cap"
            else:
                exclusion_reason = "window is not fully reconciled"
            for position, raw_row in enumerate(page.get("rows") or [], 1):
                record_id = clean(raw_row.get("record_id"))
                review = reviews.get(record_id, {})
                detail = details.get(record_id, {})
                reviewed_row = {**raw_row, **detail, **review}
                classification, reasons = classify(reviewed_row, start, end)
                saved_detail = accessible_detail(raw_row)
                if detail:
                    saved_detail["detail_overlay"] = detail
                row = {
                    "classification": classification,
                    "classification_reasons": "; ".join(reasons),
                    "review_status": clean(review.get("surname_status")),
                    "review_reason": clean(review.get("review_reason")),
                    "review_source": clean(review.get("review_source")),
                    "detail_access_status": clean(detail.get("access_status")),
                    "detail_block_reason": clean(detail.get("block_reason")),
                    "detail_captured_at": clean(detail.get("captured_at")),
                    "detail_url": clean(detail.get("url", detail.get("transcript_url"))),
                    "detail_source_file": detail_sources.get(record_id, ""),
                    "record_id": record_id,
                    "included_in_analysis": include_row,
                    "exclusion_reason": exclusion_reason,
                    "window_eventyear": query.get("eventyear", ""),
                    "window_start": start,
                    "window_end": end,
                    "partition_type": clean(query.get("partition_type")),
                    "partition_group": clean(query.get("partition_group")),
                    "partition_group_id": clean(query.get("partition_group_id")),
                    "sourcecategory": clean(query.get("sourcecategory")),
                    "sourcecountry": clean(query.get("sourcecountry")),
                    "sort": clean(query.get("sort")),
                    "control_query": bool(query.get("control_query")),
                    "page": page.get("page", ""),
                    "page_url_number": actual_page,
                    "page_url_matches_claim": claimed_page == actual_page,
                    "row_on_page": position,
                    "first_name": clean(raw_row.get("first_name")),
                    "last_name": clean(raw_row.get("last_name")),
                    "event_year": clean(raw_row.get("event_year")),
                    "year_of_birth": clean(raw_row.get("year_of_birth")),
                    "year_of_death": clean(raw_row.get("year_of_death")),
                    "location": clean(raw_row.get("location")),
                    "record_set": clean(raw_row.get("record_set")),
                    "subscription_locked": bool(raw_row.get("subscription_locked")),
                    "transcript_url": first_link(raw_row, "transcript"),
                    "image_url": first_link(raw_row, "image"),
                    "result_page_url": clean(page.get("url")),
                    "captured_at": clean(page.get("captured_at")),
                    "source_file": path.name,
                    "links_json": canonical(raw_row.get("links") or []),
                    "accessible_detail_json": canonical(saved_detail),
                    "raw_row_json": canonical(raw_row),
                }
                row["_fingerprint"] = hashlib.sha256(canonical(raw_row).encode()).hexdigest()
                occurrences.append(row)

    occurrences.sort(key=lambda row: (
        int(row["window_eventyear"]), int(row["page"]), int(row["row_on_page"]),
        row["record_id"], row["_fingerprint"],
    ))
    raw_occurrences = occurrences
    occurrences = [row for row in raw_occurrences if row["included_in_analysis"]]
    id_counts = Counter(row["record_id"] for row in occurrences if row["record_id"])
    for row in raw_occurrences:
        row["record_occurrences"] = id_counts.get(row["record_id"], 0)

    by_id: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in occurrences:
        if row["record_id"]:
            by_id[row["record_id"]].append(row)
    duplicate_rows = []
    for record_id, rows in sorted(by_id.items()):
        windows_seen = sorted({row["source_file"] for row in rows})
        eventyears_seen = sorted({int(row["window_eventyear"]) for row in rows})
        if len(rows) > 1:
            duplicate_rows.append({
                "record_id": record_id,
                "occurrences": len(rows),
                "distinct_windows": len(windows_seen),
                "window_eventyears": ",".join(map(str, eventyears_seen)),
                "source_files": " | ".join(windows_seen),
                "classifications": ",".join(sorted({row["classification"] for row in rows})),
                "first_name": rows[0]["first_name"],
                "last_name": rows[0]["last_name"],
                "event_year": rows[0]["event_year"],
                "location": rows[0]["location"],
                "record_set": rows[0]["record_set"],
            })

    event_groups: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in occurrences:
        date = clean(row["event_year"])
        key = (
            normalized(row["first_name"]), normalized(row["last_name"]), date,
            normalized(row["location"]),
        )
        if key[0] and key[1] == "glasgow" and date:
            event_groups[key].append(row)
    event_leads = []
    for key, rows in sorted(event_groups.items()):
        distinct_ids = sorted({row["record_id"] for row in rows if row["record_id"]})
        if len(distinct_ids) > 1:
            event_leads.append({
                "first_name": rows[0]["first_name"],
                "last_name": rows[0]["last_name"],
                "event_year": rows[0]["event_year"],
                "location": rows[0]["location"],
                "distinct_record_sets": len({row["record_set"] for row in rows}),
                "record_sets": " | ".join(sorted({row["record_set"] for row in rows})),
                "distinct_record_ids": len(distinct_ids),
                "record_ids": " | ".join(distinct_ids),
                "occurrences": len(rows),
                "classification": ",".join(sorted({row["classification"] for row in rows})),
            })

    classification_counts = Counter(row["classification"] for row in occurrences)
    unique_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in occurrences:
        key = row["record_id"] or f"missing:{row['_fingerprint']}"
        unique_groups[key].append(row)
    unique_class_counts: Counter[str] = Counter()
    for rows in unique_groups.values():
        classes = {row["classification"] for row in rows}
        explicitly_rejected = any(explicit_surname_verdict(json.loads(row["raw_row_json"])) is False for row in rows)
        if explicitly_rejected:
            classification = "rejected_surname"
        else:
            classification = next(
                candidate for candidate in ("candidate_in_scope", "date_anomaly_review", "out_of_scope", "rejected_surname", "non_exact_display_hit")
                if candidate in classes
            )
        unique_class_counts[classification] += 1
    provisional_unique: dict[str, dict[str, Any]] = {}
    provisional_source = sorted(raw_occurrences, key=lambda row: (not row["included_in_analysis"], int(row["window_eventyear"]), int(row["page"])))
    exact_display_unique: dict[str, dict[str, Any]] = {}
    for row in provisional_source:
        valid_observed = row["page_url_matches_claim"] and 1 <= int(row["page_url_number"]) <= MAX_ACCESSIBLE_PAGES
        if valid_observed and normalized(row["last_name"]) == "glasgow":
            key = row["record_id"] or f"missing:{row['_fingerprint']}"
            exact_display_unique.setdefault(key, row)
        if (
            row["classification"] == "candidate_in_scope"
            and valid_observed
        ):
            key = row["record_id"] or f"missing:{row['_fingerprint']}"
            provisional_unique.setdefault(key, row)

    capped_tail_rows: list[dict[str, Any]] = []
    analysis_ids = {row["record_id"] for row in occurrences if row["record_id"]}
    for window in window_rows:
        travel_query = "travel" in normalized(window["sourcecategory"])
        if not window["page_cap_exceeded"] and not travel_query:
            continue
        valid = [
            row for row in raw_occurrences
            if row["source_file"] == window["source_file"]
            and row["page_url_matches_claim"]
            and 1 <= int(row["page_url_number"]) <= MAX_ACCESSIBLE_PAGES
        ]
        exact_positions = [index for index, row in enumerate(valid) if normalized(row["last_name"]) == "glasgow"]
        exact_ids = sorted({valid[index]["record_id"] for index in exact_positions if valid[index]["record_id"]})
        unrecovered_exact_ids = sorted(set(exact_ids) - analysis_ids)
        nonexact_positions = [index for index, row in enumerate(valid) if normalized(row["last_name"]) != "glasgow"]
        strict_split = bool(exact_positions) and (
            not nonexact_positions or max(exact_positions) < min(nonexact_positions)
        )
        displayed = int(window["displayed_total"])
        accessible_capacity = min(displayed, PAGE_SIZE * MAX_ACCESSIBLE_PAGES)
        uncaptured_accessible = max(0, accessible_capacity - len(valid))
        inaccessible_results = max(0, displayed - PAGE_SIZE * MAX_ACCESSIBLE_PAGES)
        unresolved_results = max(0, displayed - len(valid))
        if uncaptured_accessible:
            tail_status = "capture incomplete; accessible pages remain unsaved"
        elif window["page_cap_exceeded"] and inaccessible_results:
            tail_status = "unknown; not fetched because Findmypast redirects beyond page 75"
        else:
            tail_status = "none"
        capped_tail_rows.append({
            "source_file": window["source_file"],
            "covered_start": window["covered_start"],
            "covered_end": window["covered_end"],
            "partition_type": window["partition_type"],
            "partition_group": window["partition_group"],
            "partition_group_id": window["partition_group_id"],
            "sourcecategory": window["sourcecategory"],
            "sourcecountry": window["sourcecountry"],
            "sort": window["sort"],
            "effective_complete_via_replacements": window["effective_complete"],
            "supersession_reason": window["supersession_reason"],
            "genuine_limited_leaf": window["genuine_limited_leaf"],
            "accounted_complete": window["accounted_complete"],
            "query_url": window["query_url"],
            "displayed_total": window["displayed_total"],
            "expected_pages": window["expected_pages"],
            "valid_accessible_pages": window["valid_accessible_pages"],
            "valid_accessible_rows": len(valid),
            "accessible_exact_display_rows": len(exact_positions),
            "accessible_exact_display_unique_ids": len(exact_ids),
            "accessible_exact_ids_recovered_in_analysis": len(set(exact_ids) & analysis_ids),
            "accessible_exact_ids_not_in_analysis": len(unrecovered_exact_ids),
            "unrecovered_accessible_exact_record_ids": " | ".join(unrecovered_exact_ids),
            "first_exact_page": min((int(valid[index]["page"]) for index in exact_positions), default=""),
            "last_exact_page": max((int(valid[index]["page"]) for index in exact_positions), default=""),
            "first_nonexact_page": min((int(valid[index]["page"]) for index in nonexact_positions), default=""),
            "exact_rows_form_prefix_before_nonexact_tail": strict_split,
            "inaccessible_pages": max(0, int(window["expected_pages"]) - MAX_ACCESSIBLE_PAGES),
            "uncaptured_or_inaccessible_pages": max(0, int(window["expected_pages"]) - int(window["valid_accessible_pages"])),
            "uncaptured_accessible_result_rows": uncaptured_accessible,
            "inaccessible_result_rows": inaccessible_results,
            "total_unresolved_result_rows": unresolved_results,
            "inaccessible_tail_status": tail_status,
            "travel_query": travel_query,
        })
    searched_coverage = range_audit(searched_intervals)
    fully_reconciled_coverage = range_audit(fully_reconciled_intervals)
    coverage = searched_coverage
    reconciled_windows = sum(bool(row["reconciled"]) for row in window_rows)
    superseded_windows = sum(bool(row["superseded_by_narrower_windows"]) for row in window_rows)
    blocking_windows = sum(
        bool(row["genuine_limited_leaf"])
        or (
            not row["reconciled"] and not row["superseded_by_narrower_windows"]
            and not row["accounted_complete"] and not row["control_query"]
        )
        for row in window_rows
    )
    timestamp_candidates = [clean(data.get("completed_at")) for _, data in windows]
    timestamp_candidates += [
        clean(page.get("captured_at"))
        for _, data in windows for page in (data.get("pages") or [])
    ]
    source_timestamp = max((value for value in timestamp_candidates if value), default="")
    raw_id_counts = Counter(row["record_id"] for row in raw_occurrences if row["record_id"])
    daily_limit_ids = {record_id for record_id, detail in details.items() if is_daily_limit(detail)}
    # Temporary daily-limit entries retain schema-valid access_status values in
    # their immutable overlays, but are excluded from record-specific status
    # counts so they cannot be mistaken for subscription-gated records.
    detail_status_counts = Counter(
        clean(detail.get("access_status")) or "unspecified"
        for detail in details.values() if not is_daily_limit(detail)
    )
    record_subscription_locked_ids = {
        record_id for record_id, detail in details.items()
        if not is_daily_limit(detail)
        and clean(detail.get("access_status")) == "subscription_locked"
    }
    mismatch_maps = [
        json.loads(row["facet_retrieval_mismatches_json"])
        for row in window_rows if row["facet_retrieval_mismatches_json"] != "{}"
    ]
    summary = {
        "schema_version": 1,
        "derived_from_latest_capture_at": source_timestamp,
        "target_years": [TARGET_START, TARGET_END],
        "windows": len(windows),
        "reconciled_windows": reconciled_windows,
        "unreconciled_windows": len(windows) - reconciled_windows,
        "superseded_capped_windows": superseded_windows,
        "blocking_unreconciled_windows": blocking_windows,
        "genuinely_limited_leaf_queries": sum(bool(row["genuine_limited_leaf"]) for row in window_rows),
        "control_queries": sum(bool(row["control_query"]) for row in window_rows),
        "facet_retrieval_mismatch_queries": len(mismatch_maps),
        "facet_retrieval_mismatch_entries": sum(len(mismatch) for mismatch in mismatch_maps if isinstance(mismatch, dict)),
        "facet_retrieval_mismatch_results": sum(
            sum(int(value) for value in mismatch.values())
            for mismatch in mismatch_maps if isinstance(mismatch, dict)
        ),
        "displayed_total_sum": sum(int(row["displayed_total"]) for row in window_rows),
        "analysis_displayed_total_sum": sum(int(row["displayed_total"]) for row in window_rows if row["included_in_analysis"] and row["reconciled"]),
        "raw_captured_row_occurrences": len(raw_occurrences),
        "excluded_raw_row_occurrences": len(raw_occurrences) - len(occurrences),
        "pagination_redirect_row_occurrences": sum(not row["page_url_matches_claim"] for row in raw_occurrences),
        "raw_unique_record_ids": len(raw_id_counts),
        "raw_duplicate_record_ids": sum(count > 1 for count in raw_id_counts.values()),
        "captured_row_occurrences": len(occurrences),
        "rows_with_record_id": sum(bool(row["record_id"]) for row in occurrences),
        "rows_without_record_id": sum(not row["record_id"] for row in occurrences),
        "unique_record_ids": len(by_id),
        "duplicate_record_ids": len(duplicate_rows),
        "duplicate_occurrences_beyond_first": sum(len(rows) - 1 for rows in by_id.values()),
        "duplicate_ids_across_windows": sum(int(row["distinct_windows"]) > 1 for row in duplicate_rows),
        "same_event_duplicate_group_leads": len(event_leads),
        "provisional_exact_display_unique_candidates": len(provisional_unique),
        "all_observed_exact_display_unique_ids": len(exact_display_unique),
        "capped_queries": sum(bool(row["inaccessible_pages"]) for row in capped_tail_rows),
        "travel_tail_queries": sum(bool(row["travel_query"]) for row in capped_tail_rows),
        "capped_inaccessible_result_rows": sum(int(row["inaccessible_result_rows"]) for row in capped_tail_rows if row["genuine_limited_leaf"]),
        "locked_row_occurrences": sum(bool(row["subscription_locked"]) for row in occurrences),
        "locked_unique_record_ids": len({row["record_id"] for row in occurrences if row["record_id"] and row["subscription_locked"]}),
        "rows_with_transcript_action": sum(bool(row["transcript_url"]) for row in occurrences),
        "rows_with_image_action": sum(bool(row["image_url"]) for row in occurrences),
        "rows_with_saved_accessible_detail": sum(row["accessible_detail_json"] != "{}" for row in occurrences),
        "detail_overlay_record_ids": len(details),
        "detail_overlay_matched_record_ids": len(set(details) & set(raw_id_counts)),
        "detail_overlay_orphan_record_ids": len(set(details) - set(raw_id_counts)),
        "detail_overlay_access_statuses": dict(sorted(detail_status_counts.items())),
        "detail_overlay_record_specific_access_statuses": dict(sorted(detail_status_counts.items())),
        "detail_overlay_record_specific_subscription_locked_ids": len(record_subscription_locked_ids),
        "detail_overlay_temporary_daily_limit_ids": len(daily_limit_ids),
        "detail_overlay_daily_limit_schema_access_status": "subscription_locked" if daily_limit_ids else "",
        "provisional_candidates_with_detail_overlay": sum(row["record_id"] in details for row in provisional_unique.values()),
        "classification_row_occurrences": dict(sorted(classification_counts.items())),
        "classification_unique_records": dict(sorted(unique_class_counts.items())),
        "coverage": coverage,
        "searched_year_coverage": searched_coverage,
        "fully_reconciled_year_coverage": fully_reconciled_coverage,
        "complete_and_reconciled": (
            bool(windows) and not coverage["gaps"] and blocking_windows == 0
            and not daily_limit_ids
        ),
    }

    window_columns = (
        "source_file", "eventyear", "offset", "covered_start", "covered_end",
        "partition_type", "partition_group", "partition_group_id", "sourcecategory", "sourcecountry", "sort", "control_query", "previous_manual_total",
        "surname", "surname_variants", "place", "query_url", "started_at",
        "completed_at", "displayed_total", "expected_pages",
        "site_page_cap", "page_cap_exceeded", "superseded", "superseded_by_narrower_windows",
        "effective_complete", "supersession_reason", "genuine_limited_leaf",
        "accounted_complete", "accounted_reason",
        "sourcecategory_facets_json", "sourcecountry_facets_json",
        "date_partition_facets_json", "facet_retrieval_mismatches_json",
        "included_in_analysis", "captured_pages_declared", "captured_pages_actual",
        "valid_accessible_pages",
        "captured_rows_declared", "captured_rows_actual", "page_numbers",
        "page_url_numbers", "page_row_counts", "reconciled", "failed_checks",
    )
    write_csv(output_dir / "audit-windows.csv", window_rows, window_columns)
    write_csv(output_dir / "audit-all-rows.csv", raw_occurrences, ROW_COLUMNS)
    write_csv(output_dir / "audit-candidate-in-scope.csv", (row for row in occurrences if row["classification"] == "candidate_in_scope"), ROW_COLUMNS)
    write_csv(output_dir / "audit-provisional-exact-display-unique.csv", provisional_unique.values(), ROW_COLUMNS)
    write_csv(output_dir / "audit-exact-display-all-unique.csv", exact_display_unique.values(), ROW_COLUMNS)
    candidate_md = [
        "# Provisional exact-display candidates (unique record IDs)", "",
        "These are result-row leads, not transcript-validated surname identities.", "",
        "| Record ID | Name | Displayed date(s) | Location | Record set | Analysis status |",
        "|---|---|---|---|---|---|",
    ]
    for row in provisional_unique.values():
        dates = "; ".join(filter(None, (row["event_year"], row["year_of_birth"], row["year_of_death"])))
        values = [
            row["record_id"] or f"missing:{row['_fingerprint']}",
            " ".join(filter(None, (row["first_name"], row["last_name"]))),
            dates, row["location"], row["record_set"],
            "included" if row["included_in_analysis"] else row["exclusion_reason"],
        ]
        candidate_md.append("| " + " | ".join(str(value).replace("|", "\\|") for value in values) + " |")
    candidate_md.append("")
    (output_dir / "audit-provisional-exact-display-unique.md").write_text("\n".join(candidate_md), encoding="utf-8")
    write_csv(output_dir / "audit-date-anomalies.csv", (row for row in occurrences if row["classification"] == "date_anomaly_review"), ROW_COLUMNS)
    write_csv(output_dir / "audit-out-of-scope-and-surname-rejections.csv", (row for row in occurrences if row["classification"] in {"out_of_scope", "rejected_surname", "non_exact_display_hit"}), ROW_COLUMNS)
    write_csv(output_dir / "audit-subscription-locked.csv", (row for row in occurrences if row["subscription_locked"]), ROW_COLUMNS)
    duplicate_columns = ("record_id", "occurrences", "distinct_windows", "window_eventyears", "source_files", "classifications", "first_name", "last_name", "event_year", "location", "record_set")
    write_csv(output_dir / "audit-duplicate-record-ids.csv", duplicate_rows, duplicate_columns)
    event_columns = ("first_name", "last_name", "event_year", "location", "distinct_record_sets", "record_sets", "distinct_record_ids", "record_ids", "occurrences", "classification")
    write_csv(output_dir / "audit-same-event-duplicate-leads.csv", event_leads, event_columns)
    capped_tail_columns = (
        "source_file", "covered_start", "covered_end", "partition_type", "partition_group", "partition_group_id",
        "sourcecategory", "sourcecountry", "sort", "query_url", "displayed_total",
        "effective_complete_via_replacements", "supersession_reason",
        "genuine_limited_leaf", "accounted_complete",
        "expected_pages", "valid_accessible_pages", "valid_accessible_rows",
        "accessible_exact_display_rows", "accessible_exact_display_unique_ids",
        "accessible_exact_ids_recovered_in_analysis", "accessible_exact_ids_not_in_analysis",
        "unrecovered_accessible_exact_record_ids",
        "first_exact_page", "last_exact_page", "first_nonexact_page",
        "exact_rows_form_prefix_before_nonexact_tail", "inaccessible_pages",
        "uncaptured_or_inaccessible_pages",
        "uncaptured_accessible_result_rows", "inaccessible_result_rows",
        "total_unresolved_result_rows", "inaccessible_tail_status", "travel_query",
    )
    write_csv(output_dir / "audit-capped-window-tail.csv", capped_tail_rows, capped_tail_columns)
    write_csv(output_dir / "audit-capped-and-travel-tail.csv", capped_tail_rows, capped_tail_columns)
    with (output_dir / "audit-summary.json").open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
    consolidated = {
        "summary": summary,
        "windows": window_rows,
        "rows": [{key: row.get(key, "") for key in ROW_COLUMNS} for row in raw_occurrences],
        "duplicate_record_ids": duplicate_rows,
        "same_event_duplicate_group_leads": event_leads,
        "capped_window_tail": capped_tail_rows,
    }
    with (output_dir / "audit-consolidated.json").open("w", encoding="utf-8") as handle:
        json.dump(consolidated, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")

    if summary["complete_and_reconciled"]:
        status = "COMPLETE AND RECONCILED"
    elif summary["searched_year_coverage"]["gap_free"] and summary["genuinely_limited_leaf_queries"]:
        status = "SEARCHED GAP-FREE; INCOMPLETE ROW ACCESS"
    else:
        status = "INCOMPLETE"
    report = [
        "# Findmypast Glasgow surname result audit",
        "",
        f"**Status: {status}.**",
        "",
        f"Derived from captures completed through `{source_timestamp or 'unknown'}`. Target coverage is {TARGET_START}–{TARGET_END} inclusive.",
        "",
        "## Reconciliation",
        "",
        f"- Query windows: {len(windows)} ({reconciled_windows} internally reconciled; {superseded_windows} capped and superseded; {blocking_windows} blocking).",
        f"- Non-blocking benchmark/control queries: {summary['control_queries']} (page-cap limitations remain explicit).",
        f"- Partition-attempt mismatch diagnostics: {summary['facet_retrieval_mismatch_queries']} queries / {summary['facet_retrieval_mismatch_entries']} checks (values are non-additive and are not counted as inaccessible records).",
        f"- Displayed totals: {summary['displayed_total_sum']} across all queries; {summary['analysis_displayed_total_sum']} across reconciled analysis windows.",
        f"- Raw captured row occurrences: {len(raw_occurrences)}; analysis occurrences after cap/supersession checks: {len(occurrences)}.",
        f"- Pagination-redirect occurrences preserved but excluded: {summary['pagination_redirect_row_occurrences']}.",
        f"- Unique record IDs: {len(by_id)}; missing-ID rows: {summary['rows_without_record_id']}.",
        f"- Duplicate IDs: {len(duplicate_rows)} ({summary['duplicate_ids_across_windows']} occur across windows; {summary['duplicate_occurrences_beyond_first']} repeat occurrences beyond the first).",
        f"- Result-action subscription-locked: {summary['locked_row_occurrences']} row occurrences / {summary['locked_unique_record_ids']} unique IDs.",
        f"- Saved full/detail payloads beyond result rows: {summary['rows_with_saved_accessible_detail']}; transcript actions: {summary['rows_with_transcript_action']}; image actions: {summary['rows_with_image_action']}.",
        f"- Separate detail overlays: {summary['detail_overlay_record_ids']} IDs ({summary['detail_overlay_matched_record_ids']} matched; {summary['detail_overlay_orphan_record_ids']} orphaned); provisional candidates with overlays: {summary['provisional_candidates_with_detail_overlay']}.",
        f"- Record-specific subscription-locked detail overlays: {summary['detail_overlay_record_specific_subscription_locked_ids']} IDs.",
        f"- Temporary Findmypast daily-limit blocks awaiting retry: {summary['detail_overlay_temporary_daily_limit_ids']} IDs. Their immutable overlays retain schema-valid `access_status=subscription_locked`, but they are not record-specific subscription locks.",
        f"- Same-event duplicate group leads: {len(event_leads)}.",
        f"- Provisional exact-display candidates after ID deduplication: {len(provisional_unique)}.",
        f"- All observed exact-display rows after ID deduplication, including anomaly/out-of-scope review classes: {len(exact_display_unique)}.",
        f"- Capped-query result rows inaccessible beyond page {MAX_ACCESSIBLE_PAGES}: {summary['capped_inaccessible_result_rows']} (not assumed empty or non-surname).",
        f"- Searched/category-accounted year gaps: {canonical(searched_coverage['gaps'])}; overlaps: {canonical(searched_coverage['overlaps'])}.",
        f"- Fully captured/reconciled year gaps: {canonical(fully_reconciled_coverage['gaps'])}; overlaps: {canonical(fully_reconciled_coverage['overlaps'])}.",
        "- Displayed totals are per-query audit values; their sum is not a unique-record total when control or replacement windows overlap.",
        "",
        "| Covered years | Displayed | Valid pages / expected | Raw rows | Audit status | Query |",
        "|---|---:|---:|---:|---|---|",
    ]
    for row in window_rows:
        report.append(
            f"| {row['covered_start']}–{row['covered_end']} | {row['displayed_total']} | "
            f"{row['valid_accessible_pages']}/{row['expected_pages']} | {row['captured_rows_actual']} | "
            f"{'reconciled' if row['reconciled'] else ('control; capped observation' if row['control_query'] else ('LIMITED LEAF' if row['genuine_limited_leaf'] else ('capped; superseded' if row['superseded_by_narrower_windows'] else ('accounted by partitions' if row['accounted_complete'] else 'BLOCKING'))))} | [exact query]({row['query_url']}) |"
        )
    report += [
        "",
        "## Review classes",
        "",
    ]
    for key in ("candidate_in_scope", "date_anomaly_review", "out_of_scope", "rejected_surname", "non_exact_display_hit"):
        report.append(f"- `{key}`: {classification_counts.get(key, 0)} row occurrences; {unique_class_counts.get(key, 0)} deduplicated records.")
    report += [
        "",
        "`candidate_in_scope` means an exact displayed Glasgow surname and a non-anomalous visible event year, or where that is blank a visible birth/death year, no later than 1750. It is a lead, not proof of identity or surname usage in the full transcript. `non_exact_display_hit` is likewise not a final rejection: the matched page/transcript must be inspected. Only an explicit saved full-record verdict produces `rejected_surname`. One-to-three-digit years, missing dates, and scope dates outside their query window remain in `date_anomaly_review` because Findmypast can truncate or broadly match dates.",
        "",
        "## Artifacts",
        "",
        "- `audit-windows.csv`: exact queries, URLs, timestamps, totals, claimed/actual page numbers, cap/supersession status and reconciliation checks.",
        "- `audit-all-rows.csv`: every raw occurrence, including preserved redirect duplicates with an explicit exclusion reason.",
        "- `audit-candidate-in-scope.csv`: exact-surname temporal leads through 1750.",
        "- `audit-provisional-exact-display-unique.csv`: valid observed exact-display leads deduplicated by record ID, including clearly flagged rows from accessible prefixes of incomplete/capped queries.",
        "- `audit-provisional-exact-display-unique.md`: human-readable record-ID list for the same provisional leads.",
        "- `audit-exact-display-all-unique.csv`: every valid observed exact-display ID with its temporal/rejection class.",
        "- `audit-date-anomalies.csv`: undated, truncated, or query-window-inconsistent rows needing transcript review.",
        "- `audit-out-of-scope-and-surname-rejections.csv`: later events, non-exact displayed hits, and explicitly rejected surname hits.",
        "- `audit-subscription-locked.csv`: every occurrence whose result action was subscription-locked.",
        "- `audit-duplicate-record-ids.csv`: repeated IDs, including cross-window duplication.",
        "- `audit-same-event-duplicate-leads.csv`: distinct IDs sharing normalized name, event year and location, with their record sets retained.",
        "- `audit-capped-window-tail.csv`: observed structured/non-exact ordering and the still-unknown inaccessible tail for every capped query.",
        "- `audit-capped-and-travel-tail.csv`: the same analysis plus incomplete or uncapped Travel & Migration partition queries.",
        "- `audit-summary.json`: machine-readable counts and gap audit.",
        "- `audit-consolidated.json`: deterministic machine-readable windows, rows and duplicate leads.",
        "",
    ]
    (output_dir / "audit-report.md").write_text("\n".join(report), encoding="utf-8")
    print(canonical(summary))
    return 0 if summary["complete_and_reconciled"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
