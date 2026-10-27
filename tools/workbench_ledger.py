#!/usr/bin/env python3
"""Coverage ledger: every inventoried input with its actual disposition in the database.

Joins ``data/private/workbench/inventory/inventory.json`` with the research
database and assigns each input one of:

* ``imported into structured research`` (an import batch read it);
* ``retained as referenced evidence or prose`` (an asset row holds its hash);
* ``replaced by a reproducible derivative`` (generated website output);
* ``preserved as unresolved legacy information`` (legacy_item rows only);
* ``explicitly excluded`` (with the inventory's reason).

Inputs the inventory planned to migrate but the database does not cover, and
inputs whose bytes changed since the inventory, are listed as problems: a
changed input means research continued during migration and the migration
must be re-run (it is repeatable) before cutover.

    .venv/bin/python tools/workbench_ledger.py [--summary docs/workbench-migration/coverage-summary.md]
"""
from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from genealogy.store import open_project

PRIVATE = ROOT / "data" / "private" / "workbench"


def ledger(project, inventory: dict) -> dict:
    store = project.store
    batches: dict[str, set[str]] = {}
    for row in store.all("SELECT input_label, input_sha256 FROM import_batch WHERE input_label IS NOT NULL"):
        batches.setdefault(row["input_label"], set()).add(row["input_sha256"])
    for row in store.all("SELECT b.input_label, a.path FROM import_batch b JOIN asset a ON a.id=b.asset_id"):
        batches.setdefault(f"data/exports/one-tree/{row['input_label']}", set())
    assets: dict[str, set[str]] = {}
    for row in store.all("SELECT path, sha256 FROM asset WHERE root='repository'"):
        assets.setdefault(row["path"], set()).add(row["sha256"])
    # An inventoried file may since have moved through the audited asset API.
    # Keep its original hash covered while that exact asset version is retained.
    for row in store.all("SELECT l.before_json, l.after_json, a.sha256 AS retained_sha256, "
                         "a.root AS retained_root FROM audit_log l JOIN asset a ON a.id=l.row_id "
                         "WHERE l.table_name='asset' AND l.action='update' AND l.before_json IS NOT NULL"):
        before, after = json.loads(row["before_json"]), json.loads(row["after_json"])
        if (before["root"] == after["root"] == row["retained_root"] == "repository"
                and before["sha256"] == after["sha256"] == row["retained_sha256"]
                and before["path"] != after["path"]):
            assets.setdefault(before["path"], set()).add(before["sha256"])
    legacy = {row["input_path"] for row in store.all("SELECT DISTINCT input_path FROM legacy_item")}
    from tools.workbench_migrate import is_generated
    generated_paths = {item["path"] for item in inventory["files"] if is_generated(item["path"])}
    generated: dict[str, str] = {}
    if generated_paths:
        from tools.workbench_legacy_views import Views
        generated = {path: text for path, text in Views(store).files().items() if path in generated_paths}
    rows, problems = [], []
    for item in inventory["files"]:
        path, digest, planned = item["path"], item.get("sha256"), item["disposition"]
        if path in generated:
            actual = "imported into structured research"
            current = ROOT / path
            expected = sha256(generated[path].encode()).hexdigest()
            changed = not current.is_file() or sha256(current.read_bytes()).hexdigest() != expected
        elif path in batches:
            actual = "imported into structured research"
            changed = digest is not None and batches[path] and digest not in batches[path]
        elif planned == "derivative":
            actual, changed = "replaced by a reproducible derivative", False
        elif path in assets:
            actual = "retained as referenced evidence or prose"
            changed = digest is not None and digest not in assets[path]
        elif path in legacy:
            actual, changed = "preserved as unresolved legacy information", False
        elif planned == "excluded":
            actual, changed = "explicitly excluded", False
        else:
            actual, changed = "NOT COVERED", False
        record = {"path": path, "planned": planned, "actual": actual, "category": item["category"],
                  "access": item["access"], "tracked": item["tracked"]}
        if actual == "explicitly excluded":
            record["reason"] = item["consumers"]
        if actual == "NOT COVERED":
            problems.append({**record, "problem": "planned for migration but not in the database"})
        if changed:
            problems.append({**record, "problem": "changed since the inventory; re-run the migration"})
        rows.append(record)
    return {"source_commit": inventory["source_commit"], "files": rows, "problems": problems,
            "summarised_directories": inventory["summarised"]}


def summary(result: dict) -> str:
    counts = Counter((row["category"], row["actual"]) for row in result["files"])
    lines = [f"Source commit `{result['source_commit'][:12]}`. {len(result['files'])} inventoried files; "
             f"{len(result['problems'])} problems.", "", "| Category | Disposition | Files |", "| --- | --- | ---: |"]
    lines += [f"| {category} | {actual} | {count} |" for (category, actual), count in sorted(counts.items())]
    kinds = Counter(problem["problem"] for problem in result["problems"])
    if kinds:
        lines += ["", "| Problem | Files |", "| --- | ---: |"] + [f"| {kind} | {count} |" for kind, count in sorted(kinds.items())]
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--project", type=Path, default=ROOT)
    parser.add_argument("--summary", type=Path, help="write a public-safe count summary here")
    args = parser.parse_args(argv)
    inventory = json.loads((PRIVATE / "inventory" / "inventory.json").read_text())
    with open_project(args.project, readonly=True) as project:
        result = ledger(project, inventory)
    (PRIVATE / "ledger.json").write_text(json.dumps(result, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    text = summary(result)
    if args.summary:
        args.summary.write_text(text, encoding="utf-8")
    print(text)
    return 1 if result["problems"] else 0


if __name__ == "__main__":
    sys.exit(main())
