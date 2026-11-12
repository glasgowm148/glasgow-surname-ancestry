#!/usr/bin/env python3
"""Regenerate Glasgow's legacy relationship registries from the research database.

After cutover the project database (``genealogy.toml`` ``[storage] database``)
is the only authority for relationship claims and assessments. These two files
remain as *generated compatibility views* for Glasgow's existing site builders
until each builder reads the database directly:

* ``research/relationship_assessments.json``
* ``research/relationship_probability_estimates.json``
* ``research/canonical_records.json``, ``research/latest-findings.json`` and
  ``research/vital_assessments.json``: each row as last entered (by the migration
  or ``tools/research_entry.py``), with any other database edit overlaid

Rules:

* A row whose claim has not been reassessed since migration is written back
  verbatim, so an unchanged database reproduces the legacy file exactly.
* Every estimate row is derived from the claim's *current* project assessment:
  both directions of one relationship always show the same percentage. A row
  that previously showed an earlier revision is corrected, with that earlier
  value kept in its ``assessment_history``.
* A claim reassessed through the workbench gets its derived fields (status,
  probability, dates, basis, history) from the database revisions.
* Relationship claims created in the database after migration are appended,
  as are explicitly approved native reassessments of imported estimate-only
  claims. Unreviewed imports retain their original compatibility shape.

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

sys.path.insert(0, str(Path(__file__).resolve().parent))

ROOT = Path(__file__).resolve().parents[1]
ASSESSMENTS = "research/relationship_assessments.json"
ESTIMATES = "research/relationship_probability_estimates.json"
RECORDS = "research/canonical_records.json"
FINDINGS = "research/latest-findings.json"
VITALS = "research/vital_assessments.json"
# Writers that keep the stored legacy row current; any other edit is overlaid from the columns.
ROW_KEEPERS = ("workbench_migrate", "research_entry")
REVERSE = {"father": "child", "mother": "child", "parent": "child", "spouse": "spouse", "sibling": "sibling",
           "partner": "partner"}
# Revisions written by the migration, a tree import or the entry tool (which keeps the stored
# legacy row current) are written back verbatim from that row.
MIGRATION_TOOLS = ("workbench_migrate", "genealogy import", "research_entry")


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


def research_fields(revision: dict[str, Any]) -> dict[str, Any]:
    """Export only explicit dispatch metadata from the current revision.

    Missing fields leave the stored compatibility row untouched; research_status
    alone does not imply a readiness decision.
    """
    extra = _extra(revision)
    fields = {key: extra[key] for key in ("last_test", "next_test") if key in extra}
    for key in ("working_selection", "attachment_status"):
        if revision.get(key) is not None:
            fields[key] = bool(revision[key]) if key == "working_selection" else revision[key]
    if isinstance(extra.get("research_state"), dict):
        fields["research_state"] = extra["research_state"]
    structural = ("allow_new_relationship", "lifecycle", "display", "hypothesis_status", "status_label", "current", "role_correction",
                  "tree_parent_replacement", "working_parent_replacement", "previous_working_selection",
                  "model_note", "analysis_links", "historical_assertions", "profile_names", "profile_urls")
    fields.update({key: extra[key] for key in structural if key in extra})
    return fields


class Views:
    def __init__(self, store):
        self.store = store
        self.research = Research(store)
        self.wikitree = {row["entity_id"]: row["value"] for row in store.all(
            "SELECT entity_id, value FROM external_id WHERE system='wikitree' AND status='current' ORDER BY value")}
        local_rows = store.all(
            "SELECT entity_id, value FROM external_id "
            "WHERE system='glasgow-local' AND status='current' ORDER BY value")
        local_values: dict[str, list[str]] = {}
        for row in local_rows:
            local_values.setdefault(row["entity_id"], []).append(row["value"])
        # A local alias is safe only when it uniquely identifies the public
        # subject.  Multiple aliases are retained in the database but must not
        # silently choose one for a generated relationship view.
        self.local = {entity_id: values[0] for entity_id, values in local_values.items()
                      if len(set(values)) == 1}
        self._merged_entities = self._active_merge_map()
        self._merged_public = self._public_merge_map()

    def _active_merge_map(self) -> dict[str, str]:
        """Return retired entity -> survivor for merges not undone.

        This deliberately reads merge records, rather than replacing strings in
        legacy JSON.  A split whose reason names a merge is the workbench's
        reversible undo marker; chained merges are resolved transitively.
        """
        rows = self.store.all("SELECT id,kind,survivor_id,retired_ids,reason FROM entity_merge ORDER BY id")
        undone = {row["reason"].split("undo ", 1)[1].split(":", 1)[0]
                  for row in rows if row.get("kind") == "split" and str(row.get("reason") or "").startswith("undo ")}
        direct = {}
        for row in rows:
            if row.get("kind") != "merge" or row.get("id") in undone:
                continue
            for retired in json.loads(row.get("retired_ids") or "[]"):
                direct[retired] = row["survivor_id"]
        result = {}
        for retired in direct:
            seen = set()
            current = retired
            while current in direct and current not in seen:
                seen.add(current)
                current = direct[current]
            if current == retired:
                raise ValueError(f"cyclic active entity merge involving {retired}")
            result[retired] = current
        return result

    def _public_merge_map(self) -> dict[str, str]:
        if not self._merged_entities:
            return {}
        aliases = self.store.all("SELECT id,entity_id,system,value,status FROM external_id")
        by_id = {row.get("id"): row for row in aliases}
        result = {}
        for retired, survivor in self._merged_entities.items():
            target = self.wikitree.get(survivor)
            if not target:
                target = self.local.get(survivor)
            if not target:
                raise ValueError(f"merged survivor {survivor} has no canonical alias")
            moved_aliases = []
            for merge in self.store.all("SELECT moved_json FROM entity_merge WHERE kind='merge'"):
                for item in json.loads(merge.get("moved_json") or "{}").get("rows", []):
                    if item.get("table") != "external_id":
                        continue
                    key = item.get("key", {})
                    alias = by_id.get(key.get("id"))
                    if alias and alias.get("entity_id") == survivor and alias.get("value"):
                        moved_aliases.append(alias["value"])
            if not moved_aliases:
                continue
            for old in moved_aliases:
                result[old] = target
        return result

    def _legacy_participants(self, row: dict[str, Any]) -> dict[str, Any]:
        """Normalize only current participant fields; history/provenance untouched."""
        if not self._merged_public:
            return row
        row = dict(row)
        for key in ("subject_id", "relative_id"):
            if row.get(key) in self._merged_public:
                row[key] = self._merged_public[row[key]]
        if isinstance(row.get("people"), list):
            row["people"] = [self._merged_public.get(x, x) for x in row["people"]]
        if isinstance(row.get("perspectives"), dict):
            row["perspectives"] = {self._merged_public.get(k, k): v for k, v in row["perspectives"].items()}
        return row

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
        person_id = self._merged_entities.get(person_id, person_id)
        return self.wikitree.get(person_id, self.local.get(person_id, person_id))

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
                row = self._legacy_participants(row)
                if not self.migrated(current):
                    row.update(self.derived_assessment(revisions, row))
                legacy.append((extra.get("legacy_index", 0), row))
            elif current is not None and (
                    ("legacy_estimates" not in extra and self.researched_here(claim))
                    or ("legacy_estimates" in extra
                        and claim["publication_status"] == "approved"
                        and not self.migrated(current))):
                # An explicitly approved reassessment of an imported estimate
                # also needs a structured grade. Otherwise a retained tree
                # grade can disagree with it and hide the exact percentage.
                # Mere migration or a private review grants no publication.
                new.append(self.new_assessment(claim, revisions))
        return [row for _, row in sorted(legacy, key=lambda item: item[0])] + new

    def derived_assessment(self, revisions: list[dict[str, Any]], row: dict[str, Any]) -> dict[str, Any]:
        current = revisions[-1]
        history = list(row.get("assessment_history") or [])
        previous = row.get("probability") or {}
        if row.get("status") is not None and (row.get("status") != current["status"] or (
                isinstance(previous, dict) and previous.get("value") is not None)):
            history.append({"status": row.get("status"),
                            "probability_percent": round(previous["value"] * 100) if isinstance(previous, dict)
                            and isinstance(previous.get("value"), (int, float)) else None,
                            "assessment_date": row.get("assessment_date"), "source_basis": row.get("basis")})
        # The retained legacy state predates reviews made in the workbench.
        # Appending it last reverses that sequence after a second review and
        # turns a real earlier increase into a fictitious historical decrease.
        for earlier in revisions[:-1]:
            if self.migrated(earlier):
                continue
            history.append({"status": earlier["status"], "probability_percent": earlier["estimate_percent"],
                            "assessment_date": earlier["assessed_on"], "source_basis": earlier["reasoning"]})
        fields: dict[str, Any] = {"status": current["status"], "assessment_date": current["assessed_on"],
                                  "basis": current["reasoning"], "assessment_history": history}
        # A reassessment is authoritative for explanatory text as well as the
        # derived status.  Keep the legacy row's shape and relationship roles,
        # but replace stale prose that otherwise continues to describe the
        # previous review (for example, an old percentage or "no parent
        # clause" qualification).  Current explicit research metadata is
        # merged below without manufacturing prior history.
        if current["reasoning"] is not None:
            fields["reason"] = current["reasoning"]
            if row.get("claim") is not None:
                fields["claim"] = current["reasoning"]
            perspectives = row.get("perspectives")
            if isinstance(perspectives, dict):
                fresh_perspectives = {}
                for person, perspective in perspectives.items():
                    if isinstance(perspective, dict):
                        fresh = dict(perspective)
                        fresh["reason"] = current["reasoning"]
                        fresh.pop("status_label", None)
                        fresh_perspectives[person] = fresh
                    else:
                        fresh_perspectives[person] = perspective
                fields["perspectives"] = fresh_perspectives
        if current["limitations"] is not None:
            fields["limitations"] = current["limitations"]
            if row.get("record_scope") is not None:
                fields["record_scope"] = current["limitations"]
        if current["basis_json"]:
            fields["source_ids"] = json.loads(current["basis_json"])
        if current["estimate_percent"] is not None:
            fields["probability"] = {"value": current["estimate_percent"] / 100, "reviewed": current["assessed_on"],
                                     "basis": current["reasoning"], "source_ids": fields.get("source_ids", [])}
            if current["limitations"] is not None and (not row.get("probability")
                    or row["probability"].get("scope") is not None):
                fields["probability"]["scope"] = current["limitations"]
        else:
            fields["probability"] = None
        explicit_provenance = _extra(current).get("provenance")
        if isinstance(explicit_provenance, dict):
            fields["provenance"] = {**(row.get("provenance") or {}), **explicit_provenance}
        fields.update(research_fields(current))
        return fields

    def new_assessment(self, claim: dict[str, Any], revisions: list[dict[str, Any]]) -> dict[str, Any]:
        child, relative = self.person(claim["subject_person_id"]), self.person(claim["object_person_id"])
        relation_type = claim.get("relation_type")
        role = ("stepfather" if claim["predicate"] == "father" else "stepmother" if claim["predicate"] == "mother"
                else claim["predicate"]) if relation_type == "step" else claim["predicate"]
        reverse_role = "stepchild" if relation_type == "step" and claim["predicate"] in {"father", "mother"} \
            else REVERSE[claim["predicate"]]
        aid = (self.store.one("SELECT value FROM external_id WHERE entity_id=? AND system='glasgow-assertion'",
                              (claim["id"],)) or {}).get("value") or claim["id"]
        row = {"assertion_id": aid, "people": [child, relative], "claim": claim["proposition"],
               "relation_type": claim.get("relation_type"),
               "perspectives": {child: {"relationship": role},
                                relative: {"relationship": reverse_role}},
               "publication_status": claim["publication_status"], "source_ids": [],
               "provenance": {"source": "genealogy-research-workbench database", "claim_id": claim["id"]}}
        row.update(self.derived_assessment(revisions, {}))
        return row

    def _merged_claim_origins(self):
        """Recover literal pre-merge aliases for native claims from reversible merge receipts."""
        if not self._merged_entities:
            return {}
        aliases = {row["id"]: row for row in self.store.all("SELECT id,system,value FROM external_id")}
        merges = self.store.all("SELECT id,kind,survivor_id,retired_ids,moved_json,reason FROM entity_merge")
        undone = {row["reason"].split("undo ", 1)[1].split(":", 1)[0] for row in merges
                  if row["kind"] == "split" and str(row["reason"] or "").startswith("undo ")}
        active = [row for row in merges if row["kind"] == "merge" and row["id"] not in undone]
        direct = {retired: row["survivor_id"] for row in active for retired in json.loads(row["retired_ids"])}
        origins = {}
        def depth(person):
            seen = set()
            while person in direct and person not in seen:
                seen.add(person)
                person = direct[person]
            return len(seen)
        for merge in active:
            retired = json.loads(merge["retired_ids"])[0]
            moved = json.loads(merge["moved_json"])["rows"]
            values = [aliases[item["key"]["id"]] for item in moved
                      if item["table"] == "external_id" and item.get("status") == "current"
                      and item["key"].get("id") in aliases]
            values = [row for row in values if row["system"] in {"wikitree", "glasgow-local"}]
            values.sort(key=lambda row: row["system"] != "wikitree")
            if not values:
                continue
            alias = values[0]["value"]
            for item in moved:
                if item["table"] != "claim" or item.get("kept_on_retired"):
                    continue
                pair = (item["key"]["id"], item["column"])
                if pair not in origins or depth(retired) > origins[pair][0]:
                    origins[pair] = (depth(retired), alias)
        return {pair: value for pair, (_, value) in origins.items()}

    def estimates(self) -> list[dict[str, Any]]:
        legacy, new = [], []
        originals = {}
        claim_origins = self._merged_claim_origins()
        for claim in self.claims():
            extra = claim["extra"]
            revisions = self.revisions(claim["id"])
            current = revisions[-1] if revisions else None
            percent = current["estimate_percent"] if current else None
            for index, row in extra.get("legacy_estimates", []):
                if self.migrated(current) and row.get("percent") == percent:
                    projected = self._legacy_participants(row)
                    originals[id(projected)] = row
                    legacy.append((index, projected))
                    continue
                corrected = dict(row)
                corrected = self._legacy_participants(corrected)
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
                        if current["limitations"] is not None and row.get("scope") is not None:
                            corrected["scope"] = current["limitations"]
                        if current["basis_json"]:
                            corrected["source_ids"] = json.loads(current["basis_json"])
                        corrected.update(research_fields(current))
                originals[id(corrected)] = row
                legacy.append((index, corrected))
            if not extra.get("legacy_estimates") and "legacy" not in extra and current is not None \
                    and percent is not None and self.researched_here(claim):
                child, relative = self.person(claim["subject_person_id"]), self.person(claim["object_person_id"])
                aid = (self.store.one("SELECT value FROM external_id WHERE entity_id=? AND system='glasgow-assertion'",
                                      (claim["id"],)) or {}).get("value") or claim["id"]
                relation_type = claim.get("relation_type")
                for subject, other, role in ((child, relative, claim["predicate"]),
                                             (relative, child, REVERSE[claim["predicate"]])):
                    display_role = ("stepfather" if role == "father" else "stepmother" if role == "mother"
                                    else "stepchild" if role == "child" else role) \
                    if relation_type == "step" else role
                    row = {"subject_id": subject, "relative_id": other, "relationship": display_role, "percent": percent,
                                "assessment_status": current["status"], "assertion_id": aid,
                                "basis": current["reasoning"], "reviewed": current["assessed_on"],
                                "source_ids": json.loads(current["basis_json"] or "[]"),
                                **({"scope": current["limitations"]} if current["limitations"] is not None else {}),
                                **research_fields(current)}
                    new.append(row)
                    original = dict(row)
                    child_origin = claim_origins.get((claim["id"], "subject_person_id"), child)
                    relative_origin = claim_origins.get((claim["id"], "object_person_id"), relative)
                    original.update(subject_id=child_origin if subject == child else relative_origin,
                                    relative_id=relative_origin if subject == child else child_origin)
                    originals[id(row)] = original
        rows = [row for _, row in sorted(legacy, key=lambda item: item[0])] + new
        return self._coalesce_merged_estimates(rows, originals)

    def _coalesce_merged_estimates(self, rows, originals):
        """One current pair after a native identity merge; all original estimates remain auditable."""
        def key(row):
            return (str(row.get("subject_id", "")).casefold(),
                    str(row.get("relative_id", "")).casefold(), row.get("relationship"))

        groups = {}
        for row in rows:
            if row.get("lifecycle") in {"historical", "superseded"} and (
                    row.get("percent") is None or row.get("display") == "historical"):
                continue
            groups.setdefault(key(row), []).append(row)
        replacements, omitted = {}, set()
        for pair, members in groups.items():
            if len(members) < 2:
                continue
            source_rows = [originals.get(id(row), row) for row in members]
            original_pairs = {key(row) for row in source_rows}
            changed = any(key(source) != pair for source in source_rows)
            # Existing independent duplicate claims still fail the downstream strict index.
            if not changed or len(original_pairs) != len(members):
                continue
            fields = ("percent", "assessment_status", "lifecycle", "display", "working_selection")
            signatures = {tuple(row.get(field) for field in fields) for row in members}
            if len(signatures) != 1:
                raise ValueError(f"Native identity merge has conflicting current estimates: {pair}")
            combined = dict(members[0])
            combined["merged_estimate_provenance"] = [
                {"original": source, "current": row} for source, row in zip(source_rows, members)]
            combined["native_identity_merges"] = {old: target for old, target in self._merged_public.items()
                if old.casefold() in {value for source in source_rows for value in key(source)[:2]}
                and target.casefold() in pair[:2]}
            combined["assertion_ids"] = list(dict.fromkeys(row["assertion_id"] for row in members if row.get("assertion_id")))
            for field in ("source_ids", "assessment_history"):
                values = []
                for row in members:
                    for value in row.get(field, []) or []:
                        if value not in values:
                            values.append(value)
                if values:
                    combined[field] = values
            combined["basis"] = "\n\n".join(dict.fromkeys(row.get("basis") or "" for row in members))
            replacements[id(members[0])] = combined
            omitted.update(id(row) for row in members[1:])
        return [replacements.get(id(row), row) for row in rows if id(row) not in omitted]



    def estimates_document(self) -> dict[str, Any]:
        header = json.loads(self.store.meta("glasgow.estimates_header") or "{}")
        later = [row["assessed_on"] for row in self.store.all(
            "SELECT r.assessed_on, c.tool FROM assessment_revision r LEFT JOIN change_set c ON c.id=r.change_set_id "
            "WHERE r.assessed_on IS NOT NULL") if not self.migrated(row)]
        if later and max(later) > (header.get("reviewed") or ""):
            header["reviewed"] = max(later)
        return {**header, "estimates": self.estimates()}

    def edited_elsewhere(self, table: str, entity_id: str) -> bool:
        return self.store.one(
            "SELECT 1 FROM audit_log a JOIN change_set c ON c.id=a.change_set_id WHERE a.table_name=? AND a.row_id=? "
            "AND a.action='update' AND NOT (" + " OR ".join("coalesce(c.tool,'') LIKE ?" for _ in ROW_KEEPERS) + ") "
            "LIMIT 1", (table, entity_id, *(f"{tool}%" for tool in ROW_KEEPERS))) is not None

    def ordered_rows(self, table: str) -> list[tuple[dict[str, Any], dict[str, Any]]]:
        rows = []
        for row in self.store.all(f"SELECT * FROM {table} WHERE extra_json LIKE '%\"legacy_json\"%' ORDER BY id"):
            extra = json.loads(row["extra_json"])
            rows.append((extra.get("legacy_index", 10 ** 9), row["id"], json.loads(extra["legacy_json"]), row))
        return [(legacy, row) for _, _, legacy, row in sorted(rows, key=lambda item: (item[0], item[1]))]

    def records(self) -> list[dict[str, Any]]:
        result = []
        for legacy, row in self.ordered_rows("record"):
            if self.edited_elsewhere("record", row["id"]):
                for key, column in (("association", "title"), ("date", "date_original"), ("place", "place_wording"),
                                    ("note", "summary"), ("source_url", "url"), ("record_type", "record_type")):
                    if key in legacy or row[column] is not None:
                        legacy[key] = row[column]
            result.append(legacy)
        return result

    def findings(self) -> dict[str, Any]:
        rows = []
        for legacy, row in self.ordered_rows("finding"):
            if self.edited_elsewhere("finding", row["id"]):
                legacy.update({"finding": row["statement"], "found_on": row["recorded_on"], "kind": row["kind"],
                               "status": row["status_original"] or row["status"], "qualification": row["qualification"]})
            rows.append(legacy)
        return {**json.loads(self.store.meta("glasgow.latest_findings_header") or "{}"), "findings": rows}

    def vitals(self) -> dict[str, Any]:
        rows = []
        for note in self.store.all("SELECT * FROM note WHERE kind='vital_assessment' ORDER BY id"):
            stored = json.loads(note["text"])
            row = stored["row"]
            for kind, vital in (row.get("vitals") or {}).items():
                claim = self.store.one("SELECT id FROM claim WHERE kind='vital' AND predicate=? AND extra_json LIKE ?",
                                       (kind, f'%"assessment_id":"{row["id"]}"%'))
                revisions = self.revisions(claim["id"]) if claim else []
                current = revisions[-1] if revisions else None
                if current is not None and not (current.get("tool") or "").startswith(ROW_KEEPERS):
                    vital.update({"status": current["status"], "note": current["reasoning"]})
            rows.append((stored.get("legacy_index", 10 ** 9), note["id"], row))
        return {**json.loads(self.store.meta("glasgow.vital_assessments_header") or "{}"),
                "assessments": [row for _, _, row in sorted(rows, key=lambda item: (item[0], item[1]))]}

    def files(self) -> dict[str, str]:
        from workbench_documents import Documents
        return {ASSESSMENTS: dump(self.assessments()), ESTIMATES: dump(self.estimates_document()),
                RECORDS: dump(self.records()), FINDINGS: dump(self.findings()), VITALS: dump(self.vitals()),
                **Documents(self.store).files()}


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
    matched = written = 0
    for relative, text in generated.items():
        path = args.root / relative
        if args.write:
            if not path.is_file() or path.read_text(encoding="utf-8") != text:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text, encoding="utf-8")
                written += 1
                print(f"wrote {relative} from the research database")
            continue
        current = path.read_text(encoding="utf-8") if path.is_file() else None
        if current is None or json.loads(current) != json.loads(text):
            status = 1
            before = json.loads(current) if current else None
            key = next((k for k in ("estimates", "findings", "assessments") if isinstance(before, dict) and k in before), None)
            rows = before if isinstance(before, list) else (before or {}).get(key, [])
            after = json.loads(text)
            after_rows = after if isinstance(after, list) else after.get(key, [])
            changed = sum(1 for a, b in zip(rows, after_rows) if a != b) + abs(len(rows) - len(after_rows))
            print(f"{relative}: differs from the database view ({changed} rows). Research must be changed through "
                  "the workbench; regenerate with --write.")
        else:
            matched += 1
            if relative in (ASSESSMENTS, ESTIMATES, RECORDS, FINDINGS, VITALS):
                print(f"{relative}: matches the research database")
    if args.check:
        print(f"{matched} of {len(generated)} generated files match the research database")
    else:
        print(f"{written} of {len(generated)} generated files rewritten; the rest already matched")
    return status


if __name__ == "__main__":
    sys.exit(main())
