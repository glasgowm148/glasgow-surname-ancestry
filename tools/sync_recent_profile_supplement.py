#!/usr/bin/env python3
"""Synchronize recent WikiTree edits missing from the current One-Tree exports."""

from __future__ import annotations

import csv
import json

from project_paths import MAP_RECORDS, MAP_RECENT_PROFILE_SUPPLEMENT, atomic_write_csv


EXTRA_FIELDS = (
    "supplement_id", "birth_date", "birth_status", "death_date", "death_status",
    "birth_location", "death_location", "gender", "source_title", "source_url",
    "source_type", "source_status",
)
PROFILE_RECONCILIATIONS = {
    ("Elizabeth Glascho", "glenarm_town"): {
        "profile_id": "Glasgow-3961",
        "person": "Elizabeth Glasgow (recorded as Eliz Glascho)",
        "source_title": "1669 County Antrim Hearth Money Roll, record 5730",
        "source_url": "https://www.billmacafee.com/1660shearthmoneyrolls/1669hearthmoneyrollsantrim.pdf",
        "source_type": "explicit",
        "source_status": "Public transcription cited on WikiTree profile Glasgow-3961; PRONI T/307/A.",
    },
    ("Sarah Murray", "kilwaughter"): {
        "profile_id": "Murray-20395",
        "person": "Sarah (Murray) Glasgow",
        "note": (
            "Placed in Group 5 by marriage. Live WikiTree profile Murray-20395 "
            "names spouse Glasgow-1504 and a 1729 Kilwaughter marriage; compare "
            "that profile date with the mapped 1727 working-household record."
        ),
    },
}


def main() -> None:
    source = json.loads(MAP_RECENT_PROFILE_SUPPLEMENT.read_text(encoding="utf-8"))
    group = source["family_group"]
    with MAP_RECORDS.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = list(reader.fieldnames or [])
        rows = [row for row in reader if row["family_group"] != group]
    for field in EXTRA_FIELDS:
        if field not in fieldnames:
            fieldnames.append(field)
    for row in rows:
        reconciliation = PROFILE_RECONCILIATIONS.get((row.get("person", ""), row.get("location_id", "")))
        if reconciliation:
            row.update(reconciliation)

    added_profiles = set()
    for profile in source["profiles"]:
        for event in profile["events"]:
            rows.append({
                "person": profile["person"],
                "profile_id": profile.get("profile_id", ""),
                "region": event["region"],
                "family_group": group,
                "subcluster": "Export-gap supplement",
                "evidence": "Recent WikiTree profile lead",
                "year": profile["year"],
                "filter_year": str(profile["filter_year"]),
                "association": f"Recent-edit profile location: {event['record_location']}",
                "note": "Added from the 6 August 2026 recent-edit reconciliation; profile fields are research leads, not source evidence.",
                "location_id": event["location_id"],
                "record_location": event["record_location"],
                "record_precision": event["record_precision"],
                "location_basis": event["location_basis"],
                "latitude": str(event["latitude"]),
                "longitude": str(event["longitude"]),
                **{field: profile.get(field, "") for field in EXTRA_FIELDS},
            })
        added_profiles.add(profile["supplement_id"])

    atomic_write_csv(MAP_RECORDS, fieldnames, rows)
    print(f"Synchronized {len(added_profiles)} recent profiles across {sum(row['family_group'] == group for row in rows)} map rows")


if __name__ == "__main__":
    main()
