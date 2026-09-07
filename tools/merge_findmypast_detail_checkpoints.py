#!/usr/bin/env python3
"""Validate and atomically merge bounded Findmypast detail checkpoints."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse


VALID_STATUSES = {"accessible", "subscription_locked", "not_found", "error"}
COMMON_FIELDS = {
    "access_status",
    "captured_at",
    "requested_url",
    "url",
    "final_url",
    "title",
    "transcript_fields",
    "transcript_text",
}


def load(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path}: top level must be an object")
    return value


def validate_record(path: Path, record_id: str, record: dict) -> None:
    if not record_id or not isinstance(record, dict):
        raise ValueError(f"{path}: invalid record entry {record_id!r}")
    missing = sorted(field for field in COMMON_FIELDS if field not in record)
    if missing:
        raise ValueError(f"{path}: {record_id}: missing {', '.join(missing)}")
    status = record["access_status"]
    if status not in VALID_STATUSES:
        raise ValueError(f"{path}: {record_id}: invalid access_status {status!r}")
    if not isinstance(record["captured_at"], str) or not record["captured_at"]:
        raise ValueError(f"{path}: {record_id}: empty capture provenance")
    try:
        datetime.fromisoformat(record["captured_at"].replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{path}: {record_id}: invalid captured_at") from exc
    for field in ("requested_url", "url", "final_url"):
        value = record[field]
        parsed = urlparse(value) if isinstance(value, str) else None
        if parsed is None or parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError(f"{path}: {record_id}: invalid {field}")
    if not isinstance(record["title"], str):
        raise ValueError(f"{path}: {record_id}: title must be text")
    if not isinstance(record["transcript_fields"], dict):
        raise ValueError(f"{path}: {record_id}: transcript_fields must be an object")
    if not isinstance(record["transcript_text"], str):
        raise ValueError(f"{path}: {record_id}: transcript_text must be text")
    if status == "accessible":
        if not record["transcript_fields"] or not record["transcript_text"].strip():
            raise ValueError(f"{path}: {record_id}: accessible record lacks transcript")
        if record.get("surname_status") not in {"confirmed", "false hit", "unresolved"}:
            raise ValueError(f"{path}: {record_id}: accessible record lacks surname review")
        if not record.get("review_reason"):
            raise ValueError(f"{path}: {record_id}: accessible record lacks review reason")
    elif not record.get("access_note"):
        raise ValueError(f"{path}: {record_id}: inaccessible record lacks access_note")


def validate_part(path: Path, value: dict) -> tuple[int, int, dict]:
    start = value.get("start_index")
    end = value.get("end_index")
    records = value.get("records")
    if not isinstance(start, int) or not isinstance(end, int) or end < start:
        raise ValueError(f"{path}: invalid start/end indexes")
    if not isinstance(records, dict) or len(records) != end - start + 1:
        raise ValueError(
            f"{path}: expected {end - start + 1} records for {start}-{end}, "
            f"found {len(records) if isinstance(records, dict) else 'non-object'}"
        )
    for record_id, record in records.items():
        validate_record(path, record_id, record)
    return start, end, records


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("master", type=Path)
    parser.add_argument("parts", nargs="*", type=Path)
    parser.add_argument(
        "--expected-ids", type=Path,
        help="Optional JSON array containing the complete ordered frozen ID manifest",
    )
    parser.add_argument(
        "--replace-daily-limit", action="store_true",
        help="Replace only existing daily-limit placeholders, using the frozen manifest",
    )
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    master = load(args.master)
    records = master.get("records")
    assigned = master.get("assigned_missing_index_range")
    if not isinstance(records, dict) or not (
        isinstance(assigned, list) and len(assigned) == 2
        and all(isinstance(value, int) for value in assigned)
        and assigned[0] >= 0 and assigned[1] >= assigned[0]
    ):
        raise ValueError(f"{args.master}: invalid master structure")
    if len(records) > assigned[1] - assigned[0] + 1:
        raise ValueError(f"{args.master}: record count exceeds assigned index range")
    for record_id, record in records.items():
        validate_record(args.master, record_id, record)

    expected_ids = None
    if args.expected_ids:
        with args.expected_ids.open(encoding="utf-8") as handle:
            expected_ids = json.load(handle)
        if isinstance(expected_ids, dict):
            expected_ids = expected_ids.get("ids")
        if not isinstance(expected_ids, list) or not all(isinstance(value, str) for value in expected_ids):
            raise ValueError(f"{args.expected_ids}: expected a JSON string array or an object with ids")
        if len(expected_ids) <= assigned[1]:
            raise ValueError(f"{args.expected_ids}: manifest does not cover assigned range")
        master_expected = expected_ids[assigned[0]:assigned[0] + len(records)]
        if list(records) != master_expected:
            raise ValueError(f"{args.master}: IDs do not match the frozen manifest order")
    if args.replace_daily_limit and expected_ids is None:
        raise ValueError("--replace-daily-limit requires --expected-ids")

    next_index = assigned[0] + len(records)
    merged = dict(records)
    loaded_parts = [(path, load(path)) for path in args.parts]
    for path, value in sorted(loaded_parts, key=lambda item: item[1].get("start_index", -1)):
        start, end, part_records = validate_part(path, value)
        if not args.replace_daily_limit and start != next_index:
            raise ValueError(f"{path}: expected start_index {next_index}, found {start}")
        if end > assigned[1]:
            raise ValueError(f"{path}: end_index {end} exceeds assigned range {assigned[1]}")
        overlap = sorted(set(merged) & set(part_records))
        if overlap and not args.replace_daily_limit:
            raise ValueError(f"{path}: {len(overlap)} record IDs overlap the master")
        if expected_ids is not None:
            expected_part = expected_ids[start:end + 1]
            if list(part_records) != expected_part:
                raise ValueError(f"{path}: IDs do not match the frozen manifest order")
        for offset, (record_id, replacement) in enumerate(part_records.items(), start=start):
            if record_id in merged:
                existing = merged[record_id]
                if not args.replace_daily_limit or existing.get("block_reason") != "daily_limit":
                    raise ValueError(f"{path}: {record_id} is not a replaceable daily-limit entry")
                if replacement.get("block_reason") == "daily_limit":
                    raise ValueError(f"{path}: {record_id} retry is still daily-limited")
                merged[record_id] = replacement
            else:
                if offset != next_index:
                    raise ValueError(
                        f"{path}: new index {offset} is not the next uncaptured index {next_index}"
                    )
                merged[record_id] = replacement
                next_index += 1

    statuses = Counter(record.get("access_status") for record in merged.values())

    master["records"] = merged
    now = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    master.setdefault("capture_session", {})["checkpointed_at"] = now
    if next_index == assigned[1] + 1:
        master["capture_session"]["completed_at"] = now

    print(
        json.dumps(
            {
                "validated_parts": len(args.parts),
                "record_count": len(merged),
                "covered_index_range": [assigned[0], next_index - 1],
                "next_index": next_index,
                "access_statuses": dict(sorted(statuses.items())),
                "applied": args.apply,
            },
            indent=2,
        )
    )
    if not args.apply:
        return

    args.master.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{args.master.name}.", dir=args.master.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(master, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, args.master)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)


if __name__ == "__main__":
    main()
