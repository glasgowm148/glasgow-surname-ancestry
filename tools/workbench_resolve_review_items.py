#!/usr/bin/env python3
"""Resolve the migration's mechanical review items, each only after checking it.

The Glasgow migration kept 636 items for review (``legacy_item`` rows). Some
need a researcher; others are mechanical and can be closed once a check shows
the information is held elsewhere in the database. This tool checks each such
item and records a resolution with the reason; anything that fails its check
stays open and is listed. Nothing is deleted and no item's recorded content is
changed (``genealogy legacy resolve`` semantics, schema version 2).

Mechanical classes:

* an older OneTree export differs from the newest export, and the newest
  export's content is what the database kept (the older content stays on the
  item and as that export's external observation);
* a completed live WikiTree update with no proposal record, when the update
  queue document held in the database still lists the profile as completed (a
  profile reopened for new work qualifies only if the reopening explicitly
  retains the earlier completion);
* an authored draft-replacement decision, when the overrides document held in
  the database carries the identical decision.

Judgement items (ambiguous place names, conflicts where the kept content is
not the newest, anything failing a check) are left open.

    .venv/bin/python tools/workbench_resolve_review_items.py [--write]
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import sys

from genealogy.store import Research, open_project

sys.path.insert(0, str(Path(__file__).resolve().parent))
from workbench_documents import Documents  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
QUEUE = "data/wikitree/profile-update-queue.json"
OVERRIDES = "research/research-queue-overrides.json"
EXPORT_TIME = re.compile(r"_(\d{4}-\d{2}-\d{2}T\d{2}_\d{2})\.json$")


def export_time(label: str) -> str | None:
    match = EXPORT_TIME.search(label)
    return match.group(1) if match else None


def onetree_conflict(store, item: dict) -> str | None:
    batch = store.one("SELECT input_label FROM import_batch WHERE id=?", (item["import_batch_id"],))
    kept = store.one("SELECT b.input_label FROM import_origin o JOIN import_batch b ON b.id=o.import_batch_id "
                     "WHERE o.entity_id=? ORDER BY b.imported_at, b.rowid LIMIT 1", (item["entity_id"],))
    if not batch or not kept:
        return None
    lineages = {label: store.one("SELECT options_json FROM import_batch WHERE input_label=?", (label,))["options_json"]
                for label in (batch["input_label"], kept["input_label"])}
    same_tree = len({json.loads(value or "{}").get("lineage") for value in lineages.values()}) == 1
    older, newest = export_time(batch["input_label"]), export_time(kept["input_label"])
    newest_overall = max(export_time(row["input_label"]) or "" for row in store.all(
        "SELECT input_label FROM import_batch WHERE adapter='one-tree' AND options_json=?",
        (lineages[kept["input_label"]],)))
    if same_tree and older and newest and older < newest and newest == newest_overall:
        return (f"Superseded: {batch['input_label']} is an older export of the same OneTree tree; the database kept "
                f"this record's content from the newest export, {kept['input_label']}. The older content stays on "
                "this item and as that export's external observation.")
    return None


def completed_update(item: dict, queue: dict) -> str | None:
    profile = json.loads(item["payload_json"]).get("profile")
    if not profile or profile not in queue.get("completed_live_profiles", []):
        return None
    held = (f"Held: {profile} is listed as a completed live update in {QUEUE}, which the database holds row by "
            "row; that list is the record of the update. No proposal record is created after the fact.")
    reopened = (queue.get("reopened_completed_profiles") or {}).get(profile)
    if reopened is None:
        return held
    if reopened.get("previous_live_completion_retained") is True:
        return (f"{held} The profile was reopened on {reopened.get('reopened_at')} for new work, with the earlier "
                "completed update explicitly retained.")
    return None


def draft_replacement(item: dict, overrides: dict) -> str | None:
    key = item["pointer"].removeprefix("/draft_replacements/")
    held = overrides.get("draft_replacements", {}).get(key)
    if held is not None and held == json.loads(item["payload_json"]):
        return (f"Held: the identical decision is in {OVERRIDES} (draft_replacements/{key}), which the database "
                "holds row by row and regenerates byte-identically.")
    return None


def decide(project) -> tuple[list[dict], Counter, list[dict]]:
    store = project.store
    documents = Documents(store)
    # A document the database does not hold confirms nothing: its items stay open.
    queue, overrides = ({} if documents.frame(name) is None else documents.compose(name) for name in (QUEUE, OVERRIDES))
    decisions, counts, left = [], Counter(), []
    for item in store.all("SELECT * FROM legacy_item WHERE resolution IS NULL ORDER BY input_path, pointer, id"):
        resolution = None
        if item["disposition"] == "conflict" and item["input_path"].startswith("ONT_"):
            kind, resolution = "older OneTree export", onetree_conflict(store, item)
        elif item["input_path"] == QUEUE and item["pointer"].startswith("/completed_live_profiles/"):
            kind, resolution = "completed live update", completed_update(item, queue)
        elif item["input_path"] == OVERRIDES and item["pointer"].startswith("/draft_replacements/"):
            kind, resolution = "draft replacement", draft_replacement(item, overrides)
        else:
            kind = item["reason"]
        if resolution:
            decisions.append({"id": item["id"], "expected_revision": item["revision"], "resolution": resolution})
            counts[f"resolved: {kind}"] += 1
        else:
            counts[f"left open: {kind}"] += 1
            left.append({"id": item["id"], "input_path": item["input_path"], "pointer": item["pointer"],
                         "reason": item["reason"]})
    return decisions, counts, left


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--project", type=Path, default=ROOT)
    parser.add_argument("--write", action="store_true", help="record the resolutions (default: report only)")
    args = parser.parse_args(argv)
    with open_project(args.project) as project:
        decisions, counts, left = decide(project)
        if args.write and decisions:
            research = Research(project.store)
            with project.store.write(actor="workbench_resolve_review_items", tool="workbench_resolve_review_items",
                                     reason="close mechanical migration review items after checking each") as tx:
                for decision in decisions:
                    research.resolve_legacy_item(tx, decision["id"], resolution=decision["resolution"],
                                                 expected_revision=decision["expected_revision"],
                                                 resolved_by="workbench_resolve_review_items")
    print(json.dumps({"written": bool(args.write and decisions), "counts": dict(sorted(counts.items())),
                      "left_open": left if len(left) <= 40 else f"{len(left)} items"}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
