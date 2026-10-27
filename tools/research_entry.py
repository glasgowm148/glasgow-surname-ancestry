#!/usr/bin/env python3
"""Record Glasgow findings, canonical records and vital assessments in the research database.

The database is the authority for these three registries; the JSON files
(`research/latest-findings.json`, `research/canonical_records.json`,
`research/vital_assessments.json`) are generated from it. Write a row in exactly
the format those files use, then record it here:

    .venv/bin/python tools/research_entry.py show finding daniel-deed-title-review-20261020
    .venv/bin/python tools/research_entry.py upsert finding row.json --expected-revision 3
    .venv/bin/python tools/research_entry.py upsert record row.json            # a new record
    .venv/bin/python tools/research_entry.py upsert vital row.json --expected-revision 1

`show` prints the current row and its revision. Changing an existing row needs
`--expected-revision` (the revision you read); if someone changed it since, the
command stops with the current row so the change can be redone, and nothing is
written. A new row needs no revision. Every change is audited with `--actor`
and `--reason`, and the affected JSON file is regenerated afterwards.

Research plans, parent-candidate lists and the WikiTree queue files are held row
by row: edit the file, then record it with
`document PATH --expected-revision N` (`document PATH --show` prints N). A row
removed from the file is kept in the database, marked removed.

Relationship assessments are not entered here: use `genealogy assess`.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from genealogy.store import Research, StaleRevisionError, StoreError, open_project, stable_id  # noqa: E402

import workbench_legacy_views as views  # noqa: E402
from workbench_documents import Documents, dump as document_dump, spec_for  # noqa: E402
from workbench_asset_paths import relocate_research_assets  # noqa: E402
from workbench_migrate import (  # noqa: E402
    Migration, extra_json, finding_columns, record_access, record_columns,
)

KINDS = {
    "finding": ("finding", "id", views.FINDINGS),
    "record": ("record", "record_id", views.RECORDS),
    "vital": ("note", "id", views.VITALS),
}
TOOL = "research_entry"


def entity_id(kind: str, key: str) -> str:
    return {"finding": stable_id("fnd", "glasgow", key), "record": stable_id("rec", "glasgow", key),
            "vital": stable_id("not", "glasgow-vital", key)}[kind]


def current_row(project, kind: str, key: str) -> tuple[dict[str, Any], int] | None:
    table = KINDS[kind][0]
    row = project.store.get(table, entity_id(kind, key))
    if row is None:
        return None
    generated = views.Views(project.store)
    if kind == "finding":
        rows = generated.findings()["findings"]
    elif kind == "record":
        rows = generated.records()
    else:
        rows = generated.vitals()["assessments"]
    field = KINDS[kind][1]
    return next(item for item in rows if item.get(field) == key), row["revision"]


def next_index(project, table: str) -> int:
    if table == "note":
        rows = project.store.all("SELECT text FROM note WHERE kind='vital_assessment'")
        values = [json.loads(row["text"]).get("legacy_index", -1) for row in rows]
    else:
        rows = project.store.all(f"SELECT extra_json FROM {table} WHERE extra_json LIKE '%\"legacy_json\"%'")
        values = [json.loads(row["extra_json"]).get("legacy_index", -1) for row in rows]
    return max(values, default=-1) + 1


def upsert(project, kind: str, row: dict[str, Any], *, expected_revision: int | None, actor: str,
           reason: str | None) -> dict[str, Any]:
    table, field, relative = KINDS[kind]
    key = row.get(field)
    if not key:
        raise StoreError(f"a {kind} row needs its '{field}'")
    if kind == "finding" and not row.get("finding"):
        raise StoreError("a finding row needs its 'finding' text")
    if kind == "vital" and not row.get("subject"):
        raise StoreError("a vital-assessment row needs its 'subject' WikiTree id")
    target = entity_id(kind, key)
    store = project.store
    existing = store.get(table, target)
    if existing is not None and expected_revision is None:
        raise StoreError(f"{kind} {key} exists at revision {existing['revision']}; read it with 'show {kind} {key}' "
                         f"and pass --expected-revision {existing['revision']}")
    if existing is not None and existing["revision"] != expected_revision:
        current = current_row(project, kind, key)
        raise StaleRevisionError(table, target, expected_revision, existing["revision"],
                                 current[0] if current else existing)
    if existing is None and expected_revision not in (None, 0):
        raise StoreError(f"{kind} {key} does not exist yet; omit --expected-revision to create it")
    migration = Migration(project, ROOT)
    counts: Counter = Counter()
    with store.write(actor=actor, tool=f"{TOOL} {kind}", source="tools/research_entry.py", reason=reason) as tx:
        batch_id = stable_id("imp", "research-entry", kind, key, migration.content_hash(row), store.clock())
        tx.insert("import_batch", {"id": batch_id, "adapter": "research-entry", "input_label": relative,
                                   "input_sha256": migration.content_hash(row), "imported_at": store.clock(),
                                   "change_set_id": tx.change_set_id})
        research = Research(store)
        if kind == "finding":
            links = [(migration.person(tx, person["id"], name=person.get("name")), "subject")
                     for person in row.get("people", []) if person.get("id")]
            if existing is None:
                research.add_finding(tx, id=target, statement=row["finding"], recorded_on=row.get("found_on"),
                                     kind=row.get("kind"), status=row.get("status"),
                                     qualification=row.get("qualification"), access="public",
                                     publication_status="approved", links=links,
                                     extra={"legacy_json": json.dumps(row, ensure_ascii=False),
                                            "legacy_index": next_index(project, "finding"), "glasgow_id": key})
                research.map_external(tx, target, "glasgow-finding", key)
            else:
                index = json.loads(existing["extra_json"] or "{}").get("legacy_index")
                tx.update("finding", target, {**finding_columns(row), "extra_json": extra_json(
                    {"legacy_json": json.dumps(row, ensure_ascii=False), "legacy_index": index, "glasgow_id": key})},
                    expected_revision=expected_revision)
                for person, role in links:
                    tx.upsert_link(target, person, role)
        elif kind == "record":
            access = record_access(row)
            if existing is None:
                migration._record(tx, row, batch_id, relative, f"/{next_index(project, 'record')}", access=access)
            else:
                index = json.loads(existing["extra_json"] or "{}").get("legacy_index")
                tx.update("record", target, {**record_columns(row, access), "extra_json": extra_json(
                    {"glasgow_record_id": key, "legacy_json": json.dumps(row, ensure_ascii=False),
                     "legacy_index": index})}, expected_revision=expected_revision)
            counts["mentions"] += migration._mentions(tx, target, row.get("profiles") or {}, access=access)
        else:
            if existing is None:
                migration.vital_row(tx, batch_id, relative, next_index(project, "note"), row, counts)
            else:
                index = json.loads(existing["text"]).get("legacy_index")
                tx.update("note", target, {"text": json.dumps({"legacy_index": index, "row": row}, ensure_ascii=False)},
                          expected_revision=expected_revision)
                for kind_name, vital in sorted((row.get("vitals") or {}).items()):
                    event_id = stable_id("evt", "glasgow-vital", key, kind_name)
                    claim_id = stable_id("clm", "glasgow-vital", key, kind_name)
                    if store.get("event", event_id) is None:   # a newly assessed vital: create it
                        migration.vital_row(tx, batch_id, relative, index, {**row, "vitals": {kind_name: vital}}, counts)
                        continue
                    date = vital.get("date")
                    iso = date if isinstance(date, str) and len(date) in (4, 7, 10) and date[:4].isdigit() else None
                    tx.update("event", event_id, {"date_original": date, "date_start": iso,
                                                  "date_kind": "exact" if iso else "unknown",
                                                  "place_wording": vital.get("place"),
                                                  "extra_json": extra_json({"legacy": vital})})
                    assessment = research.current_assessment(claim_id)
                    if assessment and (assessment["status"], assessment["reasoning"]) != (vital.get("status"),
                                                                                         vital.get("note")):
                        research.assess(tx, claim_id, expected_revision=assessment["current_revision"],
                                        status=vital.get("status"), grade=vital.get("status"),
                                        vocabulary="glasgow-evidence-labels", reasoning=vital.get("note"),
                                        assessed_on=row.get("reviewed"), extra={"label": vital.get("label")})
        # The next migration run must see this row as current, not as a hand edit.
        migration.origin(tx, target, batch_id, relative, f"/{key}", row)
    after = store.get(table, target)
    return {"kind": kind, "key": key, "entity": target, "revision": after["revision"],
            "created": existing is None, **({"mentions_added": counts["mentions"]} if kind == "record" else {})}


def document_revision(project, relative: str) -> int:
    frame = Documents(project.store).frame(relative)
    if frame is None:
        raise StoreError(f"{relative} is not held in the research database yet; run make migrate-workbench")
    return frame["note"]["revision"]


def record_document(project, relative: str, document: Any, *, expected_revision: int | None, actor: str,
                    reason: str | None, move_from: str | None = None) -> dict[str, Any]:
    """Record an edited plan, candidate list or queue file, row by row, at the revision it was read."""
    if spec_for(relative) is None:
        raise StoreError(f"{relative} is not one of the documents held row by row")
    documents = Documents(project.store)
    frame = documents.frame(relative)
    moved_assets = None
    with project.store.write(actor=actor, tool=f"{TOOL} document", source=relative, reason=reason) as tx:
        if move_from:
            if expected_revision is None:
                raise StoreError("a document move needs the source document's --expected-revision")
            prefix = str(Path(move_from).parent) + "/"
            if any(f["document"].startswith(prefix) and f["document"] != move_from
                   for f in documents.frames()):
                raise StoreError("the source folder has other held documents; move them together before relocating assets")
            documents.move_document(tx, move_from, relative, expected_revision)
            moved_assets = relocate_research_assets(project, tx, str(Path(move_from).parent),
                                                    str(Path(relative).parent))
        elif frame is not None:
            current = project.store.get("note", frame["note"]["id"])
            if expected_revision is None:
                raise StoreError(f"{relative} is at revision {current['revision']}; pass --expected-revision "
                                 f"{current['revision']} after checking it is the version you edited")
            if current["revision"] != expected_revision:
                raise StaleRevisionError("note", current["id"], expected_revision, current["revision"],
                                         {"document": relative, "current": documents.compose(relative)})
        documents.store_document(tx, relative, document)
        if moved_assets:
            migration = Migration(project, project.directory)
            for path in sorted({row["path"] for row in moved_assets["moved"]}):
                migration.asset(tx, path, kind="prose" if path.endswith(".md") else "data", access="private")
    return {"document": relative, "revision": document_revision(project, relative), "created": frame is None,
            **({"moved_from": move_from, "asset_versions_relocated": moved_assets["count"]} if moved_assets else {})}


def regenerate(project, relative: str, root: Path) -> None:
    text = views.Views(project.store).files()[relative]
    (root / relative).write_text(text, encoding="utf-8")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--project", type=Path, default=ROOT)
    sub = parser.add_subparsers(dest="command", required=True)
    show = sub.add_parser("show", help="print the current row and its revision")
    show.add_argument("kind", choices=sorted(KINDS))
    show.add_argument("key", help="finding id, record_id or vital-assessment id")
    put = sub.add_parser("upsert", help="create a row, or change one at the revision you read")
    put.add_argument("kind", choices=sorted(KINDS))
    put.add_argument("row", type=Path, help="a JSON file holding one row in the registry's own format")
    put.add_argument("--expected-revision", type=int)
    put.add_argument("--actor", default="research_entry")
    put.add_argument("--reason")
    doc = sub.add_parser("document", help="record an edited research plan, parent-candidate list or queue file")
    doc.add_argument("path", help="the file, relative to the project (e.g. research/Glasgow-951/research_plan.json)")
    doc.add_argument("--expected-revision", type=int, help="the revision printed by --show before you edited it")
    doc.add_argument("--show", action="store_true", help="print the document's current revision only")
    doc.add_argument("--actor", default="research_entry")
    doc.add_argument("--reason")
    doc.add_argument("--move-from", help="old held document path after git mv; expected revision belongs to this source")
    args = parser.parse_args(argv)
    try:
        readonly = args.command == "show" or (args.command == "document" and args.show)
        with open_project(args.project, readonly=readonly) as project:
            if args.command == "document":
                relative = Path(args.path).as_posix()
                if args.show:
                    print(json.dumps({"document": relative, "revision": document_revision(project, relative)}))
                    return 0
                document = json.loads((args.project / relative).read_text(encoding="utf-8"))
                result = record_document(project, relative, document, expected_revision=args.expected_revision,
                                         actor=args.actor, reason=args.reason, move_from=args.move_from)
                (args.project / relative).write_text(document_dump(Documents(project.store).compose(relative)),
                                                     encoding="utf-8")
                print(json.dumps(result, ensure_ascii=False))
                return 0
            if args.command == "show":
                found = current_row(project, args.kind, args.key)
                if found is None:
                    raise StoreError(f"no {args.kind} {args.key}")
                print(json.dumps({"revision": found[1], "row": found[0]}, indent=2, ensure_ascii=False))
                return 0
            row = json.loads(args.row.read_text(encoding="utf-8"))
            result = upsert(project, args.kind, row, expected_revision=args.expected_revision, actor=args.actor,
                            reason=args.reason)
            regenerate(project, KINDS[args.kind][2], args.project)
            print(json.dumps(result, ensure_ascii=False))
            return 0
    except StaleRevisionError as error:
        print(f"error: {error}\ncurrent row:\n{json.dumps(error.current, indent=2, ensure_ascii=False, default=str)}",
              file=sys.stderr)
        return 1
    except (StoreError, ValueError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
