#!/usr/bin/env python3
"""Regenerate Glasgow's legacy relationship registries from the research database.

After cutover the project database (``genealogy.toml`` ``[storage] database``)
is the only authority for relationship claims and assessments. These two files
remain as *generated compatibility views* for Glasgow's existing site builders
until each builder reads the database directly:

* ``research/relationship_assessments.json``
* ``research/relationship_probability_estimates.json``

Rules:

* A row whose claim has not been reassessed since migration is written back
  verbatim, so an unchanged database reproduces the legacy file exactly.
* Every estimate row is derived from the claim's *current* project assessment:
  both directions of one relationship always show the same percentage. A row
  that previously showed an earlier revision is corrected, with that earlier
  value kept in its ``assessment_history``.
* A claim reassessed through the workbench gets its derived fields (status,
  probability, dates, basis, history) from the database revisions.
* Relationship claims created in the database after migration are appended.

``--check`` compares the files with what the database would generate and fails
on any difference, which catches edits made outside the database. ``--write``
replaces the files (never touching anything else).

    .venv/bin/python tools/workbench_legacy_views.py --check [--root CHECKOUT]
    .venv/bin/python tools/workbench_legacy_views.py --write [--root CHECKOUT]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

from genealogy.store import Research, open_project

ROOT = Path(__file__).resolve().parents[1]
ASSESSMENTS = "research/relationship_assessments.json"
ESTIMATES = "research/relationship_probability_estimates.json"
REVERSE = {"father": "child", "mother": "child", "parent": "child", "spouse": "spouse", "sibling": "sibling",
           "partner": "partner"}
# Revisions written by the migration or a tree import are not new research.
MIGRATION_TOOLS = ("workbench_migrate", "genealogy import")


def _extra(row: dict[str, Any]) -> dict[str, Any]:
    extra = json.loads(row["extra_json"]) if row.get("extra_json") else {}
    # Legacy rows are stored as order-preserving JSON text.
    if "legacy_json" in extra:
        extra["legacy"] = json.loads(extra.pop("legacy_json"))
    if "legacy_estimates_json" in extra:
        extra["legacy_estimates"] = json.loads(extra.pop("legacy_estimates_json"))
    return extra


def dump(value: Any) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False) + "\n"


class Views:
    def __init__(self, store):
        self.store = store
        self.research = Research(store)
        self.wikitree = {row["entity_id"]: row["value"] for row in store.all(
            "SELECT entity_id, value FROM external_id WHERE system='wikitree' AND status='current' ORDER BY value")}

    def revisions(self, claim_id: str) -> list[dict[str, Any]]:
        return self.store.all(
            "SELECT r.*, c.tool FROM assessment a JOIN assessment_revision r ON r.assessment_id=a.id "
            "LEFT JOIN change_set c ON c.id=r.change_set_id WHERE a.claim_id=? AND a.scope_id='project' "
            "ORDER BY r.revision", (claim_id,))

    @staticmethod
    def migrated(revision: dict[str, Any] | None) -> bool:
        return revision is None or (revision.get("tool") or "").startswith(MIGRATION_TOOLS)

    def researched_here(self, claim: dict[str, Any]) -> bool:
        """A relationship claim made in the database after migration (not imported from a file)."""
        return claim["origin"] == "research" and not self.store.one(
            "SELECT 1 FROM import_origin WHERE entity_id=? LIMIT 1", (claim["id"],))

    def person(self, person_id: str) -> str:
        return self.wikitree.get(person_id, person_id)

    def claims(self) -> list[dict[str, Any]]:
        rows = self.store.all("SELECT * FROM claim WHERE kind='relationship' ORDER BY id")
        for row in rows:
            row["extra"] = _extra(row)
        return rows

    def assessments(self) -> list[dict[str, Any]]:
        legacy, new = [], []
        for claim in self.claims():
            extra = claim["extra"]
            revisions = self.revisions(claim["id"])
            current = revisions[-1] if revisions else None
            if "legacy" in extra:
                row = dict(extra["legacy"])
                if not self.migrated(current):
                    row.update(self.derived_assessment(revisions, row))
                legacy.append((extra.get("legacy_index", 0), row))
            elif "legacy_estimates" not in extra and current is not None and self.researched_here(claim):
                new.append(self.new_assessment(claim, revisions))
        return [row for _, row in sorted(legacy, key=lambda item: item[0])] + new

    def derived_assessment(self, revisions: list[dict[str, Any]], row: dict[str, Any]) -> dict[str, Any]:
        current = revisions[-1]
        history = list(row.get("assessment_history") or [])
        for earlier in revisions[:-1]:
            if self.migrated(earlier):
                continue
            history.append({"status": earlier["status"], "probability_percent": earlier["estimate_percent"],
                            "assessment_date": earlier["assessed_on"], "source_basis": earlier["reasoning"]})
        previous = row.get("probability") or {}
        if row.get("status") is not None and (row.get("status") != current["status"] or (
                isinstance(previous, dict) and previous.get("value") is not None)):
            history.append({"status": row.get("status"),
                            "probability_percent": round(previous["value"] * 100) if isinstance(previous, dict)
                            and isinstance(previous.get("value"), (int, float)) else None,
                            "assessment_date": row.get("assessment_date"), "source_basis": row.get("basis")})
        fields: dict[str, Any] = {"status": current["status"], "assessment_date": current["assessed_on"],
                                  "basis": current["reasoning"], "assessment_history": history}
        if current["limitations"] is not None:
            fields["limitations"] = current["limitations"]
        if current["basis_json"]:
            fields["source_ids"] = json.loads(current["basis_json"])
        if current["estimate_percent"] is not None:
            fields["probability"] = {"value": current["estimate_percent"] / 100, "reviewed": current["assessed_on"],
                                     "basis": current["reasoning"], "source_ids": fields.get("source_ids", [])}
        else:
            fields["probability"] = None
        return fields

    def new_assessment(self, claim: dict[str, Any], revisions: list[dict[str, Any]]) -> dict[str, Any]:
        child, relative = self.person(claim["subject_person_id"]), self.person(claim["object_person_id"])
        aid = (self.store.one("SELECT value FROM external_id WHERE entity_id=? AND system='glasgow-assertion'",
                              (claim["id"],)) or {}).get("value") or claim["id"]
        row = {"assertion_id": aid, "people": [child, relative], "claim": claim["proposition"],
               "perspectives": {child: {"relationship": claim["predicate"]},
                                relative: {"relationship": REVERSE[claim["predicate"]]}},
               "publication_status": claim["publication_status"], "source_ids": [],
               "provenance": {"source": "genealogy-research-workbench database", "claim_id": claim["id"]}}
        row.update(self.derived_assessment(revisions, {}))
        return row

    def estimates(self) -> list[dict[str, Any]]:
        legacy, new = [], []
        for claim in self.claims():
            extra = claim["extra"]
            revisions = self.revisions(claim["id"])
            current = revisions[-1] if revisions else None
            percent = current["estimate_percent"] if current else None
            for index, row in extra.get("legacy_estimates", []):
                if self.migrated(current) and row.get("percent") == percent:
                    legacy.append((index, row))
                    continue
                corrected = dict(row)
                if row.get("percent") != percent:
                    history = list(row.get("assessment_history") or [])
                    history.append({"percent": row.get("percent"), "assessment_status": row.get("assessment_status"),
                                    "basis": row.get("basis"), "reviewed": row.get("reviewed"),
                                    "note": "earlier value of this view; it now derives from the current assessment"})
                    corrected["assessment_history"] = history
                if current is not None:
                    corrected.update({"percent": percent, "assessment_status": current["status"]})
                    if not self.migrated(current):
                        corrected.update({"basis": current["reasoning"], "reviewed": current["assessed_on"]})
                legacy.append((index, corrected))
            if not extra.get("legacy_estimates") and "legacy" not in extra and current is not None \
                    and percent is not None and self.researched_here(claim):
                child, relative = self.person(claim["subject_person_id"]), self.person(claim["object_person_id"])
                aid = (self.store.one("SELECT value FROM external_id WHERE entity_id=? AND system='glasgow-assertion'",
                                      (claim["id"],)) or {}).get("value") or claim["id"]
                for subject, other, role in ((child, relative, claim["predicate"]),
                                             (relative, child, REVERSE[claim["predicate"]])):
                    new.append({"subject_id": subject, "relative_id": other, "relationship": role, "percent": percent,
                                "assessment_status": current["status"], "assertion_id": aid,
                                "basis": current["reasoning"], "reviewed": current["assessed_on"]})
        return [row for _, row in sorted(legacy, key=lambda item: item[0])] + new

    def estimates_document(self) -> dict[str, Any]:
        header = json.loads(self.store.meta("glasgow.estimates_header") or "{}")
        later = [row["assessed_on"] for row in self.store.all(
            "SELECT r.assessed_on, c.tool FROM assessment_revision r LEFT JOIN change_set c ON c.id=r.change_set_id "
            "WHERE r.assessed_on IS NOT NULL") if not self.migrated(row)]
        if later and max(later) > (header.get("reviewed") or ""):
            header["reviewed"] = max(later)
        return {**header, "estimates": self.estimates()}

    def files(self) -> dict[str, str]:
        return {ASSESSMENTS: dump(self.assessments()), ESTIMATES: dump(self.estimates_document())}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="fail if the files differ from the database")
    mode.add_argument("--write", action="store_true", help="replace the files with the generated views")
    parser.add_argument("--root", type=Path, default=ROOT, help="checkout whose research/ files to check or write")
    parser.add_argument("--project", type=Path, default=ROOT)
    args = parser.parse_args(argv)
    with open_project(args.project, readonly=args.check) as project:
        generated = Views(project.store).files()
    status = 0
    for relative, text in generated.items():
        path = args.root / relative
        if args.write:
            path.write_text(text, encoding="utf-8")
            print(f"wrote {relative} from the research database")
            continue
        current = path.read_text(encoding="utf-8") if path.is_file() else None
        if current is None or json.loads(current) != json.loads(text):
            status = 1
            before = json.loads(current) if current else None
            rows = before if isinstance(before, list) else (before or {}).get("estimates", [])
            after = json.loads(text)
            after_rows = after if isinstance(after, list) else after["estimates"]
            changed = sum(1 for a, b in zip(rows, after_rows) if a != b) + abs(len(rows) - len(after_rows))
            print(f"{relative}: differs from the database view ({changed} rows). Research must be changed through "
                  "the workbench; regenerate with --write.")
        else:
            print(f"{relative}: matches the research database")
    return status


if __name__ == "__main__":
    sys.exit(main())
