#!/usr/bin/env python3
"""Validate the small set of public JSON/CSV contracts used by the build."""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sys
from pathlib import Path

try:
    from project_paths import MAP_RECORDS, WEB_DIR
except ModuleNotFoundError:  # Imported as tools.validate_data.
    from tools.project_paths import MAP_RECORDS, WEB_DIR


PROFILE_ID = re.compile(r"^[A-Za-z][A-Za-z_'’]*(?:-[A-Za-z][A-Za-z_'’]*)*-\d+$")
MAP_FIELDS = {
    "person", "profile_id", "region", "family_group", "subcluster", "evidence",
    "year", "filter_year", "association", "note", "location_id", "record_location",
    "record_precision", "location_basis", "latitude", "longitude",
}
PERSON_FIELDS = {"catalogue_id", "name", "profile_ids", "records", "likely_living"}
RECORD_FIELDS = {"family_group", "location_id", "record_location", "latitude", "longitude"}


def _number(value: object, label: str, errors: list[str]) -> None:
    if value in (None, ""):
        return
    try:
        number = float(value)
    except (TypeError, ValueError):
        errors.append(f"{label}: expected a number, got {value!r}")
        return
    if not math.isfinite(number):
        errors.append(f"{label}: expected a finite number")


def validate_map_records(path: Path = MAP_RECORDS) -> list[str]:
    errors: list[str] = []
    try:
        handle = path.open(encoding="utf-8-sig", newline="")
    except OSError as exc:
        return [f"{path}: {exc}"]
    with handle:
        reader = csv.DictReader(handle)
        fields = set(reader.fieldnames or [])
        missing = MAP_FIELDS - fields
        if missing:
            errors.append(f"{path}: missing columns: {', '.join(sorted(missing))}")
        for line, row in enumerate(reader, start=2):
            profile_ids = re.findall(r"[A-Za-z][A-Za-z_'’]*(?:-[A-Za-z][A-Za-z_'’]*)*-\d+", row.get("profile_id", ""))
            # Documentary records may intentionally have no WikiTree profile.
            # If an ID is present, every embedded ID must still be valid.
            for profile_id in profile_ids:
                if not PROFILE_ID.fullmatch(profile_id):
                    errors.append(f"{path}:{line}: invalid profile ID {profile_id!r}")
            if not row.get("person", "").strip():
                errors.append(f"{path}:{line}: person is empty")
            # Unresolved documentary rows can intentionally have no family
            # group or mapped location; their source fields carry the context.
            _number(row.get("filter_year"), f"{path}:{line}: filter_year", errors)
            _number(row.get("latitude"), f"{path}:{line}: latitude", errors)
            _number(row.get("longitude"), f"{path}:{line}: longitude", errors)
    return errors


def validate_catalogue(path: Path = WEB_DIR / "data" / "people.json") -> list[str]:
    errors: list[str] = []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"{path}: {exc}"]
    if not isinstance(payload, dict):
        return [f"{path}: top level must be an object"]
    if payload.get("schema_version") != "1.0":
        errors.append(f"{path}: unsupported schema_version {payload.get('schema_version')!r}")
    people = payload.get("people")
    if not isinstance(people, list):
        return errors + [f"{path}: people must be a list"]
    if payload.get("count") != len(people):
        errors.append(f"{path}: count does not match people length")
    for index, person in enumerate(people):
        label = f"{path}:people[{index}]"
        if not isinstance(person, dict):
            errors.append(f"{label}: expected an object")
            continue
        missing = PERSON_FIELDS - person.keys()
        if missing:
            errors.append(f"{label}: missing fields: {', '.join(sorted(missing))}")
        if not isinstance(person.get("profile_ids", []), list):
            errors.append(f"{label}: profile_ids must be a list")
        else:
            for profile_id in person["profile_ids"]:
                if not isinstance(profile_id, str) or not PROFILE_ID.fullmatch(profile_id):
                    errors.append(f"{label}: invalid profile ID {profile_id!r}")
        records = person.get("records", [])
        if not isinstance(records, list):
            errors.append(f"{label}: records must be a list")
            continue
        for record_index, record in enumerate(records):
            record_label = f"{label}.records[{record_index}]"
            if not isinstance(record, dict):
                errors.append(f"{record_label}: expected an object")
                continue
            missing = RECORD_FIELDS - record.keys()
            if missing:
                errors.append(f"{record_label}: missing fields: {', '.join(sorted(missing))}")
            _number(record.get("latitude"), f"{record_label}.latitude", errors)
            _number(record.get("longitude"), f"{record_label}.longitude", errors)
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--map", dest="map_path", type=Path, default=MAP_RECORDS)
    parser.add_argument("--catalogue", type=Path, default=WEB_DIR / "data" / "people.json")
    args = parser.parse_args()
    errors = validate_map_records(args.map_path) + validate_catalogue(args.catalogue)
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print(f"Validated {args.map_path} and {args.catalogue}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
