#!/usr/bin/env python3
"""Migrate Glasgow's legacy research files into the project research database.

Glasgow-specific adapter: it reads Glasgow's legacy JSON registries, per-profile
research folders and WikiTree state, and writes them only through the
genealogy-research-workbench domain services (``genealogy.store.Research``).

Properties:

* **Read-only on the inputs.** ``--source-root`` (default: this checkout) is never
  written. Every batch records the input path, its SHA-256 and the source Git
  commit; every created row gets an ``import_origin`` pointer into its input.
* **Repeatable.** An unchanged input is skipped. A changed input is imported as a
  new batch: new rows are added, and a relationship assessment whose legacy
  current value changed becomes a *new revision* (catch-up), never an overwrite.
* **No silent choices.** Where legacy views disagree (for example a reverse
  estimate row that kept an older percentage), the assessment record's own
  dated current value is used *only* when the other value appears in that
  record's own history; anything else is kept as a separate claim or a
  ``legacy_item`` conflict and reported in the reconciliation report.
* **Lossless legacy rows.** Fields without a core column are kept verbatim in
  ``extra_json`` (key ``legacy``) so the legacy registries can be regenerated
  from the database (``tools/workbench_legacy_views.py``).

    .venv/bin/python tools/workbench_migrate.py --source-root PATH [--only STEP ...]
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any

from genealogy.store import NameInput, Research, open_project, stable_id
from genealogy.store.assets import register_asset
from genealogy.store.operations import import_genealogy_file
from genealogy.store.vocabulary import FINDING_MAP, PROPOSAL_MAP, normalise

sys.path.insert(0, str(Path(__file__).resolve().parent))
from workbench_documents import SPECS, Documents, spec_for  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
WIKITREE_ID = re.compile(r"^[A-Z][A-Za-z'\-]*-\d+$")
ROOT_NAME = "repository"            # asset root: the Glasgow checkout holding the evidence files
GRADE_VOCABULARY = "glasgow-evidence-labels"
RELATION_ROLES = {"father": "father", "mother": "mother", "parent": "parent", "spouse": "spouse", "wife": "spouse",
                  "husband": "spouse", "sibling": "sibling", "brother": "sibling", "sister": "sibling"}
CHILD_ROLES = {"child", "son", "daughter"}
ACTOR = "glasgow-migration"
# Registries generated from the database (tools/workbench_legacy_views.py). A changed copy
# is a hand edit: it is kept as a conflict, never applied; changes go through
# tools/research_entry.py or the genealogy CLI instead.
GENERATED = ("research/relationship_assessments.json", "research/relationship_probability_estimates.json",
             "research/canonical_records.json", "research/latest-findings.json", "research/vital_assessments.json")
def is_generated(relative: str) -> bool:
    return relative in GENERATED or spec_for(relative) is not None


HAND_EDIT = ("this registry is generated from the research database and was edited by hand; the change was kept "
             "for review and not applied (record it with tools/research_entry.py or the genealogy CLI)")


def record_columns(row: dict, access: str) -> dict[str, Any]:
    """Database columns for a canonical record row (shared by the migration and research_entry)."""
    year = row.get("year")
    return {"title": row.get("association") or row.get("person") or row["record_id"],
            "record_type": row.get("record_type") or row.get("role"), "date_original": row.get("date"),
            "date_start": str(year) if isinstance(year, int) else None,
            "date_kind": "exact" if isinstance(year, int) else "unknown", "place_wording": row.get("place"),
            "summary": row.get("note"), "url": row.get("source_url"), "access": access}


def record_access(row: dict) -> str:
    return "public" if row.get("publish_to_record_index") is not False else "private"


def finding_columns(row: dict) -> dict[str, Any]:
    status, original = normalise(row.get("status"), FINDING_MAP, "draft")
    return {"statement": row["finding"], "recorded_on": row.get("found_on"), "kind": row.get("kind"),
            "status": status, "status_original": original, "qualification": row.get("qualification")}
# Inventory categories -> workbench asset kinds.
ASSET_KINDS = {"original evidence and captures": "capture", "research prose and editorial content": "prose",
               "authoritative research": "data", "imported observations and external tree state": "capture",
               "workflow state": "data", "reference data": "data", "DNA": "dna",
               "generated output containing otherwise unpreserved input": "generated",
               "reproducible derivatives": "derivative", "presentation configuration": "presentation",
               "publication decisions": "data", "tooling": "data", "unclassified": "file"}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def extra_json(value: dict[str, Any] | None) -> str | None:
    """The store's canonical JSON for an extra_json column."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) if value else None


def as_percent(probability: Any) -> tuple[int | None, Any]:
    """(whole percent, exact original) from Glasgow's probability.value fraction."""
    if not isinstance(probability, dict) or not isinstance(probability.get("value"), (int, float)):
        return None, None
    exact = probability["value"] * 100
    return int(round(exact)), probability["value"]


class Migration:
    def __init__(self, project, source: Path):
        self.project = project
        self.store = project.store
        self.research = Research(self.store)
        self.source = source
        self.commit = subprocess.run(["git", "-C", str(source), "rev-parse", "HEAD"], capture_output=True, text=True,
                                     check=True).stdout.strip()
        self.report: dict[str, Any] = {"source_commit": self.commit, "steps": {}, "conflicts": [], "unresolved": []}
        self._people: dict[str, str] = {}
        self._records: set[str] = set()

    # ---------------------------------------------------------------- helpers
    def path(self, relative: str) -> Path:
        return self.source / relative

    def batch(self, tx, relative: str, data: bytes, adapter: str) -> tuple[str, bool]:
        digest = sha256_bytes(data)
        batch_id = stable_id("imp", "glasgow", relative, digest)
        exists = self.store.get("import_batch", batch_id) is not None
        if not exists:
            tx.insert("import_batch", {"id": batch_id, "adapter": adapter, "input_label": relative, "input_sha256": digest,
                                       "input_commit": self.commit, "imported_at": self.store.clock(),
                                       "change_set_id": tx.change_set_id})
        return batch_id, exists

    def origin(self, tx, entity_id: str, batch_id: str, relative: str, pointer: str, payload: Any = None) -> None:
        if not self.store.one("SELECT 1 FROM import_origin WHERE entity_id=? AND import_batch_id=? AND input_path=? AND "
                              "pointer=?", (entity_id, batch_id, relative, pointer)):
            tx.insert("import_origin", {"entity_id": entity_id, "import_batch_id": batch_id, "input_path": relative,
                                        "pointer": pointer,
                                        "content_sha256": None if payload is None else sha256_bytes(
                                            json.dumps(payload, sort_keys=True, ensure_ascii=False).encode())})

    @staticmethod
    def store_header(tx, key: str, document: dict, rows_key: str) -> None:
        """A legacy file's top-level fields other than its rows, for the generated view."""
        header = json.dumps({k: v for k, v in document.items() if k != rows_key}, ensure_ascii=False)
        tx.conn.execute("INSERT INTO schema_meta(key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET "
                        "value=excluded.value", (key, header))

    @staticmethod
    def content_hash(payload: Any) -> str:
        return sha256_bytes(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode())

    def edited_outside_migration(self, table: str, entity_id: str) -> bool:
        """Whether anyone other than this migration changed the row (research recorded in the database)."""
        return self.store.one(
            "SELECT 1 FROM audit_log a JOIN change_set c ON c.id=a.change_set_id WHERE a.table_name=? AND a.row_id=? "
            "AND a.action<>'insert' AND coalesce(c.tool,'') NOT LIKE 'workbench_migrate%' LIMIT 1",
            (table, entity_id)) is not None

    def refresh(self, tx, table: str, entity_id: str, relative: str, payload: Any, changes: dict[str, Any],
                batch_id: str, pointer: str) -> str:
        """Catch an existing row up with a changed legacy input: 'unchanged', 'updated' or 'conflict'."""
        previous = self.store.one(
            "SELECT o.content_sha256 FROM import_origin o JOIN import_batch b ON b.id=o.import_batch_id "
            "WHERE o.entity_id=? AND o.input_path=? AND o.content_sha256 IS NOT NULL "
            # The audit sequence orders batches strictly; timestamps tie within a second.
            "ORDER BY (SELECT max(seq) FROM audit_log WHERE table_name='import_batch' AND row_id=b.id) DESC "
            "LIMIT 1", (entity_id, relative))
        digest = self.content_hash(payload)
        if previous is None or previous["content_sha256"] == digest:
            self.origin(tx, entity_id, batch_id, relative, pointer, payload)
            return "unchanged"
        if is_generated(relative):
            self.legacy(tx, batch_id, relative, f"{pointer}@{digest[:12]}", "conflict", HAND_EDIT, payload, entity_id)
            return "conflict"
        if self.edited_outside_migration(table, entity_id):
            self.legacy(tx, batch_id, relative, f"{pointer}@{digest[:12]}", "conflict",
                        "the legacy input changed after this row was edited in the database; the database row was "
                        "kept and the incoming version preserved here for review", payload, entity_id)
            return "conflict"
        current = self.store.get(table, entity_id)
        tx.update(table, entity_id, changes, expected_revision=current["revision"])
        self.origin(tx, entity_id, batch_id, relative, pointer, payload)
        self.report.setdefault("refreshed", Counter())[table] += 1
        return "updated"

    def legacy(self, tx, batch_id: str | None, relative: str, pointer: str, disposition: str, reason: str,
               payload: Any = None, entity_id: str | None = None) -> None:
        item_id = stable_id("leg", relative, pointer, disposition)
        if not self.store.get("legacy_item", item_id):
            tx.insert("legacy_item", {"id": item_id, "import_batch_id": batch_id, "input_path": relative,
                                      "pointer": pointer, "disposition": disposition, "reason": reason,
                                      "payload_json": json.dumps(payload, sort_keys=True, ensure_ascii=False)
                                      if payload is not None else None, "entity_id": entity_id})
            bucket = "conflicts" if disposition == "conflict" else "unresolved"
            self.report[bucket].append({"input": relative, "pointer": pointer, "reason": reason})

    def person(self, tx, wikitree_id: str, *, name: str | None = None, access: str = "private") -> str:
        """The local person for a WikiTree id (created when research names one not yet known)."""
        if wikitree_id in self._people:
            return self._people[wikitree_id]
        found = self.research.find_external("wikitree", wikitree_id)
        if found:
            self._people[wikitree_id] = found[0]
            return found[0]
        local = not WIKITREE_ID.match(wikitree_id)
        person_id = stable_id("per", "glasgow", wikitree_id)
        if not self.store.get("person", person_id):
            self.research.create_person(
                tx, id=person_id, names=[NameInput(name)] if name else [], label=name or wikitree_id,
                record_defined=local, access=access,
                extra={"created_by": "migration: research names this identifier"})
        self.research.map_external(tx, person_id, "glasgow-local" if local else "wikitree", wikitree_id,
                                   url=None if local else f"https://www.wikitree.com/wiki/{wikitree_id}")
        self._people[wikitree_id] = person_id
        return person_id

    def asset(self, tx, relative: str, *, kind: str, access: str = "private", about: list[str] = ()) -> str | None:
        path = self.path(relative)
        if not path.is_file():
            return None
        asset = register_asset(self.project, tx, path, root=ROOT_NAME, kind=kind, access=access,
                               provenance=f"Glasgow repository {relative} at {self.commit[:12]}")
        for target in about:
            tx.upsert_link(asset["id"], target, "about")
        return asset["id"]

    def read_json(self, relative: str) -> tuple[Any, bytes] | tuple[None, None]:
        path = self.path(relative)
        if not path.is_file():
            self.report["unresolved"].append({"input": relative, "reason": "input not present"})
            return None, None
        data = path.read_bytes()
        return json.loads(data), data

    # ---------------------------------------------------------------- people
    def step_onetree(self) -> dict:
        reports = {}
        for relative, lineage in (("data/exports/one-tree/ONT_Glasgow_2026-08-18T15_43.json", "one-tree:glasgow"),
                                  ("data/exports/one-tree/ONT_Glasco_2026-08-18T16_05.json", "one-tree:glasco")):
            if self.path(relative).is_file():
                result = import_genealogy_file(self.project, self.path(relative), format="one-tree", lineage=lineage,
                                               actor=ACTOR)
                reports[relative] = {key: result.get(key) for key in ("status", "records", "observations",
                                                                      "conflict_count")}
        # Earlier exports are kept as observations of the tree at those dates.
        for relative in ("data/exports/one-tree/ONT_Glasgow_2026-07-22T11_12.json",
                         "data/exports/one-tree/ONT_Glasgow_2026-08-06T13_22.json"):
            if self.path(relative).is_file():
                result = import_genealogy_file(self.project, self.path(relative), format="one-tree",
                                               lineage="one-tree:glasgow", actor=ACTOR)
                reports[relative] = {key: result.get(key) for key in ("status", "records", "observations",
                                                                      "conflict_count")}
        return reports

    def step_catalogue(self) -> dict:
        """The public catalogue's people: Glasgow's existing publication decision and routes."""
        relative = "www/data/people.json"
        data, raw = self.read_json(relative)
        if data is None:
            return {"missing": relative}
        counts = Counter()
        with self.store.write(actor=ACTOR, tool="workbench_migrate catalogue", source=relative,
                              reason="public catalogue people, routes and merged profile ids") as tx:
            batch_id, seen = self.batch(tx, relative, raw, "glasgow-catalogue")
            for index, row in enumerate(data["people"]):
                ids = row.get("profile_ids") or [row["map_key"]]
                person_id = self.person(tx, ids[0], name=row.get("name"))
                current = self.store.get("person", person_id)
                changes = {}
                if row.get("likely_living"):
                    changes["living"] = "living"
                elif row.get("death"):
                    changes["living"] = "deceased"
                if not row.get("likely_living") and current["access"] != "public":
                    changes["access"] = "public"   # listed in the published catalogue
                if row.get("gender") in ("Male", "Female"):
                    changes["sex"] = row["gender"].lower()
                if changes:
                    tx.update("person", person_id, changes)
                if not self.store.one("SELECT 1 FROM person_name WHERE person_id=?", (person_id,)) and row.get("name"):
                    self.research.add_name(tx, person_id, NameInput(row["name"], preferred=True))
                for extra in ids[1:]:
                    self.research.map_external(tx, person_id, "wikitree", extra, status="alias",
                                               note="further profile in the same catalogue entry")
                self.research.add_route(tx, f"people/{row['catalogue_id']}.html", person_id)
                self.origin(tx, person_id, batch_id, relative, f"/people/{index}", row)
                counts["people"] += 1
        return dict(counts)

    def step_wikitree_observations(self) -> dict:
        counts = Counter()
        for relative in ("data/wikitree/profile-evidence.json", "data/wikitree/live-profile-overrides.json"):
            data, raw = self.read_json(relative)
            if data is None:
                continue
            with self.store.write(actor=ACTOR, tool="workbench_migrate wikitree", source=relative,
                                  reason="WikiTree captures as external observations") as tx:
                batch_id, _ = self.batch(tx, relative, raw, "wikitree-capture")
                captured = data.get("generated_at")
                for profile, fields in sorted(data.get("profiles", {}).items()):
                    entity = self.person(tx, profile)
                    _, created = self.research.record_observation(
                        tx, system="wikitree", external_value=profile, fields=fields,
                        captured_on=fields.get("captured_at") if isinstance(fields, dict) else captured,
                        entity_id=entity, import_batch_id=batch_id)
                    counts["observations"] += created
                for old, new in sorted(data.get("redirects", {}).items()):
                    entity = self.person(tx, new)
                    self.research.map_external(tx, entity, "wikitree", old, status="redirect", redirect_to=new,
                                               observed_on=captured)
                    counts["redirects"] += 1
        return dict(counts)

    # ---------------------------------------------------------------- places
    def step_gazetteer(self) -> dict:
        relative = "data/place-gazetteer.json"
        data, raw = self.read_json(relative)
        if data is None:
            return {}
        counts = Counter()
        with self.store.write(actor=ACTOR, tool="workbench_migrate gazetteer", source=relative) as tx:
            batch_id, _ = self.batch(tx, relative, raw, "glasgow-gazetteer")
            for key, entry in sorted(data.get("entries", {}).items()):
                lat, lon = entry.get("latitude", entry.get("lat")), entry.get("longitude", entry.get("lon"))
                place_id = stable_id("plc", "gazetteer", key)
                precision = entry.get("precision")
                self.research.create_place(
                    tx, id=place_id, name=entry.get("name") or key,
                    latitude=lat if isinstance(lat, (int, float)) and isinstance(lon, (int, float)) else None,
                    longitude=lon if isinstance(lat, (int, float)) and isinstance(lon, (int, float)) else None,
                    precision=precision if precision in ("exact", "building", "street", "settlement", "parish",
                                                         "district", "county", "region", "country", "approximate") else None,
                    region=entry.get("country") or entry.get("region"), coordinate_basis=entry.get("source"),
                    extra={"legacy": entry, "key": key})
                self.origin(tx, place_id, batch_id, relative, f"/entries/{key}", entry)
                counts["places"] += 1
            for key, entry in sorted(data.get("ambiguous", {}).items()):
                self.legacy(tx, batch_id, relative, f"/ambiguous/{key}", "unresolved",
                            "ambiguous place name kept for review, not geocoded", entry)
                counts["ambiguous"] += 1
        return dict(counts)

    # ---------------------------------------------------------------- records
    def _source_for(self, tx, row: dict) -> str | None:
        title = row.get("source_title") or row.get("source_url")
        if not title:
            return None
        source_id = stable_id("src", "glasgow", title)
        if not self.store.get("source", source_id):
            self.research.register_source(tx, id=source_id, title=title, kind=row.get("source_type") or "unknown",
                                          url=row.get("source_url"), access="public",
                                          extra={"source_status": row.get("source_status")})
        return source_id

    def _record(self, tx, row: dict, batch_id: str, relative: str, pointer: str, *, access: str) -> str:
        record_id = stable_id("rec", "glasgow", row["record_id"])
        if record_id in self._records:
            return record_id
        if self.store.get("record", record_id):
            self.refresh(tx, "record", record_id, relative, row, {
                **record_columns(row, access),
                "extra_json": extra_json(self._record_extra(tx, record_id, row, relative, pointer))}, batch_id, pointer)
            self._records.add(record_id)
            return record_id
        source_id = self._source_for(tx, row)
        copy_id = None
        if source_id and row.get("source_url"):
            copy_id = self.research.add_copy(
                tx, id=stable_id("cpy", record_id), source_id=source_id, url=row.get("source_url"),
                form="transcript_site" if "transcri" in str(row.get("status", "")).lower() else "unknown",
                description=row.get("status"), access=access,
                inspected="inspected" in json.dumps(row.get("source_status") or "").lower())
        year = row.get("year")
        self.research.add_record(
            tx, id=record_id, title=row.get("association") or row.get("person") or row["record_id"], source_id=source_id,
            copy_id=copy_id, record_type=row.get("record_type") or row.get("role"), date_original=row.get("date"),
            date_start=str(year) if isinstance(year, int) else None, date_kind="exact" if isinstance(year, int) else "unknown",
            place_wording=row.get("place"), summary=row.get("note"), url=row.get("source_url"), access=access,
            extra=self._record_extra(tx, record_id, row, relative, pointer))
        self.research.map_external(tx, record_id, "glasgow-record", row["record_id"])
        self.origin(tx, record_id, batch_id, relative, pointer, row)
        self._records.add(record_id)
        return record_id

    def _record_extra(self, tx, record_id: str, row: dict, relative: str, pointer: str) -> dict:
        """Extra fields; canonical rows keep their order-preserving text and position for the generated view."""
        extra = {"glasgow_record_id": row["record_id"]}
        if relative == "research/canonical_records.json":
            extra.update(legacy_json=json.dumps(row, ensure_ascii=False), legacy_index=int(pointer.strip("/")))
        else:
            current = self.store.get("record", record_id)
            previous = json.loads(current["extra_json"] or "{}") if current else {}
            if "legacy_json" in previous:   # first seen in the canonical file: keep that row
                return previous
            extra["legacy"] = row
        return extra

    def _mentions(self, tx, record_id: str, profiles: dict, *, access: str) -> int:
        count = 0
        for order, (profile, detail) in enumerate(sorted(profiles.items())):
            mention_id = stable_id("men", record_id, profile)
            if self.store.get("mention", mention_id):
                continue
            detail = detail if isinstance(detail, dict) else {"role": str(detail)}
            self.research.add_mention(tx, id=mention_id, record_id=record_id, role=detail.get("role"),
                                      details=detail.get("timeline_group"), sort_order=order, access=access,
                                      extra={"legacy": detail})
            person_id = self.person(tx, profile)
            claim = self.research.identity_claim(tx, id=stable_id("clm", "identity", mention_id), mention_id=mention_id,
                                                 person_id=person_id,
                                                 proposition=f"This record's {detail.get('role') or 'participant'} is {profile}",
                                                 access=access)
            self.research.assess(tx, claim, new=True, status=detail.get("identity_status") or "attributed",
                                 vocabulary="glasgow-record-attribution",
                                 reasoning="Glasgow research attaches this record to the profile.")
            count += 1
        return count

    def step_records(self) -> dict:
        counts = Counter()
        relative = "research/canonical_records.json"
        data, raw = self.read_json(relative)
        if data is not None:
            with self.store.write(actor=ACTOR, tool="workbench_migrate records", source=relative,
                                  reason="canonical records, their sources, mentions and attributions") as tx:
                batch_id, _ = self.batch(tx, relative, raw, "glasgow-canonical-records")
                for index, row in enumerate(data):
                    access = record_access(row)
                    record_id = self._record(tx, row, batch_id, relative, f"/{index}", access=access)
                    counts["mentions"] += self._mentions(tx, record_id, row.get("profiles") or {}, access=access)
                    counts["records"] += 1
        for path in sorted(self.source.glob("research/*/records_mentions.json")):
            relative = path.relative_to(self.source).as_posix()
            data, raw = self.read_json(relative)
            profile = data.get("profile_id") or path.parent.name
            with self.store.write(actor=ACTOR, tool="workbench_migrate records", source=relative) as tx:
                batch_id, _ = self.batch(tx, relative, raw, "glasgow-record-mentions")
                for index, row in enumerate(data.get("records", [])):
                    if not row.get("record_id"):
                        continue
                    record_id = self._record(tx, row, batch_id, relative, f"/records/{index}", access="public")
                    counts["profile mentions"] += self._mentions(tx, record_id, {profile: {"role": row.get("role")}},
                                                                 access="public")
        return dict(counts)

    # ---------------------------------------------------------------- relationships
    def _claim_people(self, row: dict) -> tuple[str, str, str] | None:
        """(child WikiTree id, relative WikiTree id, relative's role) from an assessment's perspectives."""
        perspectives = row.get("perspectives") or {}
        for person, view in perspectives.items():
            role = str((view or {}).get("relationship", "")).casefold()
            others = [p for p in row["people"] if p != person]
            if not others:
                continue
            if role in RELATION_ROLES and RELATION_ROLES[role] in ("father", "mother", "parent"):
                return person, others[0], RELATION_ROLES[role]
        for person, view in perspectives.items():
            role = str((view or {}).get("relationship", "")).casefold()
            others = [p for p in row["people"] if p != person]
            if role in CHILD_ROLES and others:
                return others[0], person, "parent"
            if role in RELATION_ROLES and others:
                first, second = sorted([person, others[0]])
                return first, second, RELATION_ROLES[role]
        return None

    def _estimate_key(self, estimate: dict) -> tuple[str, str, str] | None:
        role = str(estimate.get("relationship", "")).casefold()
        if role in CHILD_ROLES:
            return estimate["relative_id"], estimate["subject_id"], "parent"
        if role in RELATION_ROLES:
            mapped = RELATION_ROLES[role]
            if mapped in ("spouse", "sibling"):
                first, second = sorted([estimate["subject_id"], estimate["relative_id"]])
                return first, second, mapped
            return estimate["subject_id"], estimate["relative_id"], mapped
        return None

    def _revision_fields(self, entry: dict, *, current: bool) -> dict:
        fields = self._raw_revision_fields(entry, current=current)
        extra = dict(fields.get("extra") or {})
        for key in ("status", "grade", "reasoning", "limitations", "research_status", "assessed_on", "attachment_status"):
            value = fields.get(key)
            if value is not None and not isinstance(value, str):
                extra[f"structured_{key}"] = value   # kept verbatim; the text column stays empty
                fields[key] = None
        if fields.get("basis") is not None:
            fields["basis"] = [str(item) for item in fields["basis"]] if isinstance(fields["basis"], list) else None
        fields["extra"] = extra or None
        return fields

    def _raw_revision_fields(self, entry: dict, *, current: bool) -> dict:
        if current:
            percent, exact = as_percent(entry.get("probability"))
            return {"status": entry.get("status"), "grade": entry.get("status"), "vocabulary": GRADE_VOCABULARY,
                    "estimate_percent": percent, "estimate_kind": "subjective" if percent is not None else None,
                    "reasoning": entry.get("basis") or entry.get("reason"), "limitations": entry.get("limitations"),
                    "assessed_on": entry.get("assessment_date"),
                    "working_selection": entry.get("working_selection") if isinstance(entry.get("working_selection"), bool) else None,
                    "research_status": entry.get("hypothesis_status") or entry.get("research_state"),
                    "basis": entry.get("source_ids") or None,
                    "extra": {"probability": entry.get("probability"), "exact_fraction": exact} if exact is not None else None}
        percent = entry.get("probability_percent")
        return {"status": entry.get("status"), "grade": entry.get("status"), "vocabulary": GRADE_VOCABULARY,
                "estimate_percent": percent if isinstance(percent, int) else None,
                "estimate_kind": "subjective" if isinstance(percent, int) else None,
                "reasoning": entry.get("source_basis") or entry.get("basis"), "assessed_on": entry.get("assessment_date"),
                "attachment_status": entry.get("tree_status"), "extra": {"legacy": entry}}

    def step_relationships(self) -> dict:
        counts = Counter()
        relative = "research/relationship_assessments.json"
        assessments, raw = self.read_json(relative)
        estimates_doc, raw_estimates = self.read_json("research/relationship_probability_estimates.json")
        estimates = estimates_doc["estimates"] if estimates_doc else []
        by_assertion: dict[str, list[tuple[int, dict]]] = defaultdict(list)
        for index, estimate in enumerate(estimates):
            by_assertion[estimate.get("assertion_id")].append((index, estimate))
        reconciliation: list[dict] = []
        with self.store.write(actor=ACTOR, tool="workbench_migrate relationships", source=relative,
                              reason="relationship claims, assessments with history, and estimate reconciliation") as tx:
            self.research.ensure_scope(tx, "project", name="Project assessment")
            batch_id, _ = self.batch(tx, relative, raw, "glasgow-relationship-assessments")
            estimate_batch, _ = self.batch(tx, "research/relationship_probability_estimates.json", raw_estimates,
                                           "glasgow-relationship-estimates")
            header = {key: value for key, value in (estimates_doc or {}).items() if key != "estimates"}
            tx.conn.execute("INSERT INTO schema_meta(key, value) VALUES ('glasgow.estimates_header', ?) "
                            "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (json.dumps(header, ensure_ascii=False),))
            for index, row in enumerate(assessments):
                aid = row["assertion_id"]
                parties = self._claim_people(row)
                if parties is None:
                    self.legacy(tx, batch_id, relative, f"/{index}", "unresolved",
                                "no perspective states a relationship role", row)
                    continue
                child, relative_id, role = parties
                claim_id = stable_id("clm", "glasgow", aid)
                rows_here = by_assertion.get(aid, [])

                def same_claim(estimate: dict) -> bool:
                    key = self._estimate_key(estimate)
                    return key is not None and {key[0], key[1]} == {child, relative_id} and (
                        key[2] == role or key[2] == "parent" and role in ("father", "mother")
                        or estimate.get("relationship") in CHILD_ROLES)

                own_percent, _ = as_percent(row.get("probability"))
                adopted = None
                if own_percent is None:
                    values = {e.get("percent") for _, e in rows_here if same_claim(e) and isinstance(e.get("percent"), int)}
                    if len(values) == 1:
                        # The estimates file is the only carrier of this assertion's estimate, in both directions.
                        adopted = [e for _, e in rows_here if same_claim(e)]
                fields = self._revision_fields(row, current=True)
                if adopted:
                    fields["estimate_percent"] = adopted[0]["percent"]
                    fields["estimate_kind"] = "subjective"
                    fields["extra"] = {**(fields.get("extra") or {}), "estimate_source": {
                        "file": "research/relationship_probability_estimates.json",
                        "reviewed": sorted({e.get("reviewed") for e in adopted if e.get("reviewed")}),
                        "basis": adopted[0].get("basis"), "scope": adopted[0].get("scope")}}
                if not self.store.get("claim", claim_id):
                    self.research.relationship_claim(
                        tx, id=claim_id, child_id=self.person(tx, child), relative_id=self.person(tx, relative_id),
                        role=role, proposition=row.get("claim") or f"{relative_id} is the {role} of {child}",
                        access="public" if row.get("publication_status") == "approved" else "private",
                        publication_status="approved" if row.get("publication_status") == "approved" else "unreviewed",
                        # Rows are kept as order-preserving JSON text so the legacy files regenerate byte for byte.
                        extra={"legacy_json": json.dumps(row, ensure_ascii=False), "assertion_id": aid,
                               "legacy_index": index,
                               "legacy_estimates_json": json.dumps([[e_index, e] for e_index, e in rows_here
                                                                    if same_claim(e)], ensure_ascii=False)})
                    self.research.map_external(tx, claim_id, "glasgow-assertion", aid)
                    for entry in row.get("assessment_history") or []:
                        earlier = self._revision_fields(entry, current=False)
                        existing = self.research.current_assessment(claim_id)
                        self.research.assess(tx, claim_id, new=existing is None,
                                             expected_revision=existing["current_revision"] if existing else None, **earlier)
                    current = self.research.current_assessment(claim_id)
                    self.research.assess(tx, claim_id, new=current is None,
                                         expected_revision=current["current_revision"] if current else None, **fields)
                    for source in dict.fromkeys(row.get("source_ids") or []):
                        record_id = stable_id("rec", "glasgow", source)
                        if self.store.get("record", record_id):
                            self.research.add_evidence(tx, id=stable_id("evd", claim_id, record_id), claim_id=claim_id,
                                                       record_id=record_id, interpretation=row.get("reason"))
                        else:
                            self.legacy(tx, batch_id, relative, f"/{index}/source_ids/{source}", "unresolved",
                                        "cited source id is not a canonical record", {"source_id": source}, claim_id)
                    self.origin(tx, claim_id, batch_id, relative, f"/{index}", row)
                    counts["claims"] += 1
                else:
                    claim = self.store.get("claim", claim_id)
                    claim_extra = json.loads(claim["extra_json"] or "{}")
                    refreshed = {**claim_extra, "legacy_json": json.dumps(row, ensure_ascii=False),
                                 "legacy_index": index,
                                 "legacy_estimates_json": json.dumps([[e_index, e] for e_index, e in rows_here
                                                                      if same_claim(e)], ensure_ascii=False)}
                    state = self._catch_up(tx, claim_id, fields, batch_id, relative, f"/{index}", row)
                    if state != "conflict" and refreshed != claim_extra:
                        tx.update("claim", claim_id, {
                            "extra_json": extra_json(refreshed), "proposition": row.get("claim") or claim["proposition"],
                            "access": "public" if row.get("publication_status") == "approved" else claim["access"],
                            "publication_status": "approved" if row.get("publication_status") == "approved"
                            else claim["publication_status"]}, expected_revision=claim["revision"])
                    counts[f"claims already present ({state})"] += 1
                # --------------------------------------------- estimates for this assertion
                current = self.research.current_assessment(claim_id)
                own_history = {entry.get("probability_percent") for entry in row.get("assessment_history") or []}
                for e_index, estimate in by_assertion.pop(aid, []):
                    key = self._estimate_key(estimate)
                    pointer = f"/estimates/{e_index}"
                    self.origin(tx, claim_id, estimate_batch, "research/relationship_probability_estimates.json",
                                pointer, estimate)
                    matches = same_claim(estimate)
                    percent = estimate.get("percent")
                    if matches and (current is None or percent == current["estimate_percent"]):
                        continue
                    if matches and percent in own_history:
                        reconciliation.append({"assertion_id": aid, "row": e_index, "direction": estimate.get("relationship"),
                                               "stale_percent": percent, "current_percent": current["estimate_percent"],
                                               "resolution": "stale view of an earlier revision; both directions now "
                                                             "derive from the current assessment"})
                        continue
                    if not matches and key is not None:
                        # A different proposition filed under the same assertion id: its own claim, flagged.
                        alt_id = stable_id("clm", "glasgow", aid, "estimate", e_index)
                        if not self.store.get("claim", alt_id):
                            self.research.relationship_claim(
                                tx, id=alt_id, child_id=self.person(tx, key[0]), relative_id=self.person(tx, key[1]),
                                role=key[2], proposition=f"{key[1]} is the {key[2]} of {key[0]} (estimate row filed "
                                f"under {aid})", extra={"legacy_estimates_json": json.dumps([[e_index, estimate]], ensure_ascii=False),
                                                        "assertion_id": aid, "filed_under": aid})
                            self.research.assess(tx, alt_id, new=True, status=estimate.get("assessment_status"),
                                                 grade=estimate.get("assessment_status"), vocabulary=GRADE_VOCABULARY,
                                                 estimate_percent=percent if isinstance(percent, int) else None,
                                                 estimate_kind="subjective" if isinstance(percent, int) else None,
                                                 reasoning=estimate.get("basis"), assessed_on=estimate.get("reviewed"))
                            self.research.add_dependency(tx, dependent_id=alt_id, premise_id=claim_id,
                                                         note="estimate row filed under another assertion; review")
                            self.research.flag_dependents(tx, claim_id, "migration: separate proposition under one "
                                                          "assertion id needs review")
                        reconciliation.append({"assertion_id": aid, "row": e_index, "direction": estimate.get("relationship"),
                                               "percent": percent, "current_percent": current and current["estimate_percent"],
                                               "resolution": "different proposition (role or pair) kept as its own "
                                                             "claim and flagged for review"})
                        continue
                    self.legacy(tx, estimate_batch, "research/relationship_probability_estimates.json", pointer,
                                "conflict", "estimate disagrees with the current assessment and is not in its history",
                                estimate, claim_id)
                    reconciliation.append({"assertion_id": aid, "row": e_index, "percent": percent,
                                           "current_percent": current and current["estimate_percent"],
                                           "resolution": "unexplained conflict kept for review; nothing chosen"})
            # --------------------------------------------- estimates without an assessment record
            for aid, rows in by_assertion.items():
                for e_index, estimate in rows:
                    key = self._estimate_key(estimate)
                    if key is None:
                        self.legacy(tx, estimate_batch, "research/relationship_probability_estimates.json",
                                    f"/estimates/{e_index}", "unresolved", "unknown relationship word", estimate)
                        continue
                    claim_id = stable_id("clm", "glasgow", "estimate", key[0], key[1], key[2], aid or "")
                    if not self.store.get("claim", claim_id):
                        self.research.relationship_claim(
                            tx, id=claim_id, child_id=self.person(tx, key[0]), relative_id=self.person(tx, key[1]),
                            role=key[2], extra={"legacy_estimates_json": json.dumps([[e_index, estimate]], ensure_ascii=False),
                                                "assertion_id": aid})
                        percent = estimate.get("percent")
                        self.research.assess(tx, claim_id, new=True, status=estimate.get("assessment_status"),
                                             grade=estimate.get("assessment_status"), vocabulary=GRADE_VOCABULARY,
                                             estimate_percent=percent if isinstance(percent, int) else None,
                                             estimate_kind="subjective" if isinstance(percent, int) else None,
                                             reasoning=estimate.get("basis"), assessed_on=estimate.get("reviewed"))
                        counts["estimate-only claims"] += 1
                    self.origin(tx, claim_id, estimate_batch, "research/relationship_probability_estimates.json",
                                f"/estimates/{e_index}", estimate)
        self.report["reconciliation"] = reconciliation
        counts["reconciled estimate rows"] = len(reconciliation)
        return dict(counts)

    def _catch_up(self, tx, claim_id: str, wanted: dict, batch_id: str, relative: str, pointer: str,
                  row: dict) -> str:
        """A changed legacy current value becomes a new revision, unless the database was reassessed meanwhile."""
        current = self.research.current_assessment(claim_id)
        if current and all(current.get(key) == wanted.get(key) for key in ("status", "estimate_percent", "reasoning",
                                                                            "assessed_on")):
            self.origin(tx, claim_id, batch_id, relative, pointer, row)
            return "unchanged"
        tool = self.store.one("SELECT tool FROM change_set WHERE id=?", (current["change_set_id"],)) if current else None
        if is_generated(relative) and current is not None:
            self.legacy(tx, batch_id, relative, f"{pointer}@{self.content_hash(row)[:12]}", "conflict", HAND_EDIT,
                        row, claim_id)
            return "conflict"
        if current and not str((tool or {}).get("tool") or "").startswith("workbench_migrate"):
            # The database is the authority for assessments: a hand edit to the generated file is not applied.
            self.legacy(tx, batch_id, relative, f"{pointer}@{self.content_hash(row)[:12]}", "conflict",
                        "the generated registry was edited by hand after the assessment was revised in the database; "
                        "kept for review, not applied", row, claim_id)
            return "conflict"
        self.research.assess(tx, claim_id, expected_revision=current["current_revision"] if current else None,
                             new=current is None, **wanted)
        self.origin(tx, claim_id, batch_id, relative, pointer, row)
        self.report.setdefault("caught_up", []).append(claim_id)
        return "updated"

    # ---------------------------------------------------------------- vitals
    def step_vitals(self) -> dict:
        relative = "research/vital_assessments.json"
        data, raw = self.read_json(relative)
        counts = Counter()
        if data is None:
            return {}
        with self.store.write(actor=ACTOR, tool="workbench_migrate vitals", source=relative) as tx:
            batch_id, _ = self.batch(tx, relative, raw, "glasgow-vital-assessments")
            for index, row in enumerate(data.get("assessments", [])):
                self.vital_row(tx, batch_id, relative, index, row, counts)
            self.store_header(tx, "glasgow.vital_assessments_header", data, "assessments")
        return dict(counts)

    def vital_row(self, tx, batch_id: str, relative: str, index: int, row: dict, counts: Counter) -> None:
        """Create (or catch up) one vital-assessment row: its events, vital claims and the stored row."""
        subject = self.person(tx, row["subject"])
        for kind, vital in sorted((row.get("vitals") or {}).items()):
            event_id = stable_id("evt", "glasgow-vital", row["id"], kind)
            date = vital.get("date")
            iso = date if isinstance(date, str) and re.fullmatch(r"\d{4}(-\d{2}(-\d{2})?)?", date) else None
            if self.store.get("event", event_id):
                pointer = f"/assessments/{index}/vitals/{kind}"
                claim_id = stable_id("clm", "glasgow-vital", row["id"], kind)
                state = self.refresh(tx, "event", event_id, relative, vital, {
                    "date_original": date, "date_start": iso, "date_kind": "exact" if iso else "unknown",
                    "place_wording": vital.get("place"),
                    "access": "public" if row.get("status") == "approved" else "private",
                    "extra_json": extra_json({"legacy": vital})}, batch_id, pointer)
                current = self.research.current_assessment(claim_id)
                if state == "updated" and current and (current["status"], current["reasoning"]) != (
                        vital.get("status"), vital.get("note")):
                    self.research.assess(tx, claim_id, expected_revision=current["current_revision"],
                                         status=vital.get("status"), grade=vital.get("status"),
                                         vocabulary=GRADE_VOCABULARY, reasoning=vital.get("note"),
                                         assessed_on=row.get("reviewed"), extra={"label": vital.get("label")})
                counts[f"vital claims already present ({state})"] += 1
                continue
            self.research.add_event(tx, id=event_id, kind=kind, participants=[(subject, "principal")],
                                    date_original=date, date_start=iso,
                                    date_kind="exact" if iso else "unknown", place_wording=vital.get("place"),
                                    access="public" if row.get("status") == "approved" else "private",
                                    extra={"legacy": vital})
            claim_id = self.research.create_claim(
                tx, id=stable_id("clm", "glasgow-vital", row["id"], kind), kind="vital", predicate=kind,
                proposition=f"{kind}: {date or 'date unknown'}{', ' + vital['place'] if vital.get('place') else ''}",
                value_text=date, subject_person_id=subject, event_id=event_id,
                access="public" if row.get("status") == "approved" else "private",
                publication_status="approved" if row.get("status") == "approved" else "unreviewed",
                extra={"assessment_id": row["id"]})
            self.research.assess(tx, claim_id, new=True, status=vital.get("status"), grade=vital.get("status"),
                                 vocabulary=GRADE_VOCABULARY, reasoning=vital.get("note"),
                                 assessed_on=row.get("reviewed"), extra={"label": vital.get("label")})
            self.origin(tx, claim_id, batch_id, relative, f"/assessments/{index}/vitals/{kind}", vital)
            counts["vital claims"] += 1
        # The whole row, order-preserving, so the generated view can be written back exactly.
        note_id = stable_id("not", "glasgow-vital", row["id"])
        text = json.dumps({"legacy_index": index, "row": row}, ensure_ascii=False)
        if not self.store.get("note", note_id):
            self.research.add_note(tx, id=note_id, kind="vital_assessment", title=row["id"], text=text,
                                   links=[(subject, "about")])
            self.origin(tx, note_id, batch_id, relative, f"/assessments/{index}", row)
        else:
            self.refresh(tx, "note", note_id, relative, row, {"text": text}, batch_id, f"/assessments/{index}")


    # ---------------------------------------------------------------- findings
    def step_findings(self) -> dict:
        relative = "research/latest-findings.json"
        data, raw = self.read_json(relative)
        counts = Counter()
        if data is None:
            return {}
        with self.store.write(actor=ACTOR, tool="workbench_migrate findings", source=relative) as tx:
            batch_id, _ = self.batch(tx, relative, raw, "glasgow-latest-findings")
            self.store_header(tx, "glasgow.latest_findings_header", data, "findings")
            for index, row in enumerate(data.get("findings", [])):
                finding_id = stable_id("fnd", "glasgow", row["id"])
                links = [(self.person(tx, person["id"], name=person.get("name")), "subject")
                         for person in row.get("people", []) if person.get("id")]
                if self.store.get("finding", finding_id):
                    state = self.refresh(tx, "finding", finding_id, relative, row, {
                        **finding_columns(row), "extra_json": extra_json({"legacy_json": json.dumps(row, ensure_ascii=False),
                                                  "legacy_index": index, "glasgow_id": row["id"]})},
                        batch_id, f"/findings/{index}")
                    if state == "updated":
                        for target, role in links:
                            tx.upsert_link(finding_id, target, role)
                    counts[f"findings already present ({state})"] += 1
                    continue
                self.research.add_finding(tx, id=finding_id, statement=row["finding"], recorded_on=row.get("found_on"),
                                          kind=row.get("kind"), status=row.get("status"),
                                          qualification=row.get("qualification"), access="public",
                                          publication_status="approved", links=links,
                                          extra={"legacy_json": json.dumps(row, ensure_ascii=False),
                                                 "legacy_index": index, "glasgow_id": row["id"]})
                self.research.map_external(tx, finding_id, "glasgow-finding", row["id"])
                self.origin(tx, finding_id, batch_id, relative, f"/findings/{index}", row)
                counts["findings"] += 1
        return dict(counts)

    # ---------------------------------------------------------------- per-profile research
    def step_profiles(self) -> dict:
        counts = Counter()
        directories = sorted(p for p in (self.source / "research").iterdir() if p.is_dir())
        for directory in directories:
            name = directory.name
            files = sorted(p for p in directory.rglob("*") if p.is_file() and p.name != ".DS_Store")
            if not files:
                continue
            with self.store.write(actor=ACTOR, tool="workbench_migrate profiles", source=f"research/{name}/") as tx:
                subject = self.person(tx, name) if WIKITREE_ID.match(name) else None
                about = [subject] if subject else []
                for path in files:
                    relative = path.relative_to(self.source).as_posix()
                    kind = ("capture" if "/captures/" in relative else
                            "draft" if path.suffix in (".wiki", ".wikitext") else
                            "image" if path.suffix.lower() in (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".webp") else
                            "pdf" if path.suffix.lower() == ".pdf" else
                            "prose" if path.suffix.lower() in (".md", ".txt", ".html") else "data")
                    access = "restricted" if kind in ("capture",) or path.name in ("evidence_index.json",) else "private"
                    asset_id = self.asset(tx, relative, kind=kind, access=access, about=about)
                    counts[f"assets: {kind}"] += 1
                    if path.name in ("findings.md", "research_brief.md") and asset_id:
                        note_id = stable_id("not", relative)
                        existing = self.store.get("note", note_id)
                        if existing is None:
                            self.research.add_note(tx, id=note_id, kind=path.stem, title=relative, asset_id=asset_id,
                                                   links=[(target, "about") for target in about])
                            counts["prose notes"] += 1
                        elif existing["asset_id"] != asset_id:   # the prose changed: the note follows the new bytes
                            tx.update("note", note_id, {"asset_id": asset_id}, expected_revision=existing["revision"])
                            counts["prose notes updated"] += 1
                if subject:
                    counts.update(self._profile_structures(tx, directory, subject))
        return dict(counts)

    def _profile_structures(self, tx, directory: Path, subject: str) -> Counter:
        counts = Counter()
        base = directory.relative_to(self.source).as_posix()
        plan_path = directory / "research_plan.json"
        documents = Documents(self.store)
        if plan_path.is_file() and not documents.frame(f"{base}/research_plan.json"):
            plan = json.loads(plan_path.read_bytes())
            relative = f"{base}/research_plan.json"
            batch_id, _ = self.batch(tx, relative, plan_path.read_bytes(), "glasgow-research-plan")
            for index, question in enumerate(plan.get("questions") or []):
                text = question if isinstance(question, str) else question.get("question") or json.dumps(question)
                question_id = stable_id("qst", relative, index)
                if not self.store.get("question", question_id):
                    self.research.add_question(tx, id=question_id, question=text,
                                               status=None if isinstance(question, str) else question.get("status"),
                                               links=[(subject, "about")],
                                               extra=None if isinstance(question, str) else {"legacy": question})
                    self.origin(tx, question_id, batch_id, relative, f"/questions/{index}", question)
                    counts["questions"] += 1
            for index, search in enumerate(plan.get("web_searches") or []):
                if not isinstance(search, dict):
                    search = {"query": str(search)}
                search_id = stable_id("sch", relative, index)
                if not self.store.get("search", search_id):
                    result = search.get("result") or search.get("outcome") or search.get("finding") or "not recorded"
                    self.research.log_search(tx, id=search_id, scope=search.get("query") or search.get("search") or json.dumps(search),
                                             result=str(result), searched_on=search.get("date") or search.get("searched_on"),
                                             repository=search.get("site") or search.get("url"),
                                             outcome="negative" if re.match(r"\s*(no|none|nothing|not found)\b", str(result), re.I)
                                             else "unknown", links=[(subject, "about")], extra={"legacy": search})
                    self.origin(tx, search_id, batch_id, relative, f"/web_searches/{index}", search)
                    counts["searches"] += 1
            for index, finding in enumerate(plan.get("findings") or []):
                if not isinstance(finding, dict) or not finding.get("claim"):
                    continue
                finding_id = stable_id("fnd", relative, index)
                if not self.store.get("finding", finding_id):
                    self.research.add_finding(tx, id=finding_id, statement=finding["claim"], status="qualified",
                                              qualification=finding.get("reasoning"), links=[(subject, "subject")],
                                              extra={"legacy": finding, "confidence_word": finding.get("confidence")})
                    self.origin(tx, finding_id, batch_id, relative, f"/findings/{index}", finding)
                    counts["plan findings"] += 1
        candidates_path = directory / "parent_candidates.json"
        if candidates_path.is_file() and not documents.frame(f"{base}/parent_candidates.json"):
            relative = f"{base}/parent_candidates.json"
            candidates = json.loads(candidates_path.read_bytes())
            batch_id, _ = self.batch(tx, relative, candidates_path.read_bytes(), "glasgow-parent-candidates")
            for index, candidate in enumerate(candidates if isinstance(candidates, list) else []):
                hypothesis_id = stable_id("hyp", relative, candidate.get("id") or index)
                if self.store.get("hypothesis", hypothesis_id):
                    continue
                people = [self.person(tx, pid) for pid in candidate.get("person_ids") or [] if pid]
                self.research.add_hypothesis(
                    tx, id=hypothesis_id, kind="parentage",
                    statement=f"{candidate.get('candidate') or 'A candidate'} as a parent: {candidate.get('assessment') or ''}".strip(),
                    status=candidate.get("state") or "open", supports="\n".join(candidate.get("supports") or []) or None,
                    objections="\n".join(candidate.get("objections") or []) or None,
                    links=[(subject, "subject"), *((p, "candidate") for p in people)], extra={"legacy": candidate})
                self.origin(tx, hypothesis_id, batch_id, relative, f"/{index}", candidate)
                counts["parent hypotheses"] += 1
        presentation_path = directory / "presentation.json"
        if presentation_path.is_file():
            relative = f"{base}/presentation.json"
            presentation = json.loads(presentation_path.read_bytes())
            batch_id, _ = self.batch(tx, relative, presentation_path.read_bytes(), "glasgow-presentation")
            for index, question in enumerate(presentation.get("evidence_questions") or []):
                text = question.get("question") if isinstance(question, dict) else str(question)
                if not text:
                    continue
                question_id = stable_id("qst", relative, index)
                if not self.store.get("question", question_id):
                    self.research.add_question(tx, id=question_id, question=text, links=[(subject, "about")],
                                               resolves=question.get("answer") if isinstance(question, dict) else None,
                                               access="public", extra={"legacy": question})
                    self.origin(tx, question_id, batch_id, relative, f"/evidence_questions/{index}", question)
                    counts["presentation questions"] += 1
                else:   # editorial presentation stays a file: its extracted questions follow it
                    state = self.refresh(tx, "question", question_id, relative, question, {
                        "question": text, "resolves": question.get("answer") if isinstance(question, dict) else None,
                        "extra_json": extra_json({"legacy": question})}, batch_id, f"/evidence_questions/{index}")
                    counts[f"presentation questions ({state})"] += 1
            for index, item in enumerate(presentation.get("superseded_interpretations") or []):
                finding_id = stable_id("fnd", relative, "superseded", index)
                if self.store.get("finding", finding_id):
                    continue
                text = item.get("interpretation") or item.get("summary") or json.dumps(item, ensure_ascii=False) \
                    if isinstance(item, dict) else str(item)
                self.research.add_finding(tx, id=finding_id, statement=text, status="superseded",
                                          qualification=item.get("reason") if isinstance(item, dict) else None,
                                          links=[(subject, "subject")], extra={"legacy": item})
                self.origin(tx, finding_id, batch_id, relative, f"/superseded_interpretations/{index}", item)
                counts["superseded interpretations"] += 1
        return counts

    # ---------------------------------------------------------------- workflow
    def step_queue(self) -> dict:
        relative = "data/wikitree/profile-update-queue.json"
        if Documents(self.store).frame(relative):
            return {"held in the database": 1}   # changes are recorded with tools/research_entry.py document
        data, raw = self.read_json(relative)
        counts = Counter()
        if data is None:
            return {}
        reviews, _ = self.read_json("research/research-queue-matches.json")
        overrides, _ = self.read_json("research/research-queue-overrides.json")
        with self.store.write(actor=ACTOR, tool="workbench_migrate queue", source=relative,
                              reason="WikiTree proposals with their authored workflow state") as tx:
            batch_id, _ = self.batch(tx, relative, raw, "glasgow-update-queue")
            for profile, entry in sorted(data.get("entries", {}).items()):
                proposal_id = stable_id("prp", "glasgow-queue", profile)
                draft = entry.get("draft_path")
                draft_asset = self.asset(tx, draft, kind="draft") if draft else None
                status_word = entry.get("status") or "pending"
                status = "verified" if "VERIFIED" in status_word.upper() else (
                    "proposed" if status_word.upper().startswith("OPEN") or status_word == "pending" else None)
                existing = self.store.get("proposal", proposal_id)
                if existing:
                    review = (reviews or {}).get("reviews", {}).get(f"update-{profile.lower()}")
                    normalised, original = normalise(status or status_word, PROPOSAL_MAP, "draft")
                    state = self.refresh(tx, "proposal", proposal_id, relative, entry, {
                        "status": normalised, "status_original": original, "rationale": entry.get("summary"),
                        "diff_json": None if entry.get("relationship_changes") is None else json.dumps(
                            entry["relationship_changes"], ensure_ascii=False, sort_keys=True, separators=(",", ":")),
                        "draft_asset_id": draft_asset, "extra_json": extra_json({"legacy": entry, "review": review})},
                        batch_id, f"/entries/{profile}")
                    if state == "updated" and normalised != existing["status"]:
                        tx.insert("proposal_event", {"proposal_id": proposal_id, "at": self.store.clock(),
                                                     "from_status": existing["status"], "to_status": normalised,
                                                     "actor": ACTOR, "note": f"legacy queue status: {status_word}",
                                                     "change_set_id": tx.change_set_id})
                    counts[f"proposals already present ({state})"] += 1
                    continue
                self.research.create_proposal(
                    tx, id=proposal_id, kind="wikitree_update", system="wikitree", target=profile,
                    status=status or status_word, destination=f"https://www.wikitree.com/wiki/{profile}",
                    rationale=entry.get("summary"), diff=entry.get("relationship_changes"), draft_asset_id=draft_asset,
                    authored=bool(entry.get("manual_update", True)), actor=ACTOR,
                    extra={"legacy": entry, "review": (reviews or {}).get("reviews", {}).get(f"update-{profile.lower()}")})
                tx.upsert_link(proposal_id, self.person(tx, profile), "target")
                self.origin(tx, proposal_id, batch_id, relative, f"/entries/{profile}", entry)
                counts["proposals"] += 1
            for profile in data.get("completed_live_profiles") or []:
                self.legacy(tx, batch_id, relative, f"/completed_live_profiles/{profile}", "unresolved",
                            "completed live update recorded without a proposal record", {"profile": profile},
                            self.person(tx, profile))
            for key, value in sorted((overrides or {}).get("draft_replacements", {}).items()):
                self.legacy(tx, batch_id, "research/research-queue-overrides.json", f"/draft_replacements/{key}",
                            "unresolved", "authored draft replacement decision kept verbatim", value)
                counts["draft replacement decisions"] += 1
        return dict(counts)

    # ---------------------------------------------------------------- publication
    def step_approvals(self) -> dict:
        counts = Counter()
        manifests = ("research/ydna-publication-approval.json", "research/publication-restoration-approval.json",
                     "research/transcriptions/public-preview-approvals.json")
        for relative in manifests:
            data, raw = self.read_json(relative)
            if data is None:
                continue
            with self.store.write(actor=ACTOR, tool="workbench_migrate approvals", source=relative,
                                  reason="exact-file publication approvals") as tx:
                batch_id, _ = self.batch(tx, relative, raw, "glasgow-approvals")
                authority = data.get("authorization") or data.get("approval_basis") or "recorded in " + relative
                items = []
                for item in data.get("inputs", []):
                    items.append((item["path"], item["sha256"], item["path"]))
                for item in data.get("publications", []):
                    if "sha256" not in item:
                        # A page approved as a whole, without byte-scoped evidence: kept as a page approval.
                        self.research.add_approval(tx, kind="page", target=item["path"], authority=authority,
                                                   approved_on=data.get("approved_on"), manifest=relative,
                                                   scope=f"{data.get('scope')} ({item.get('kind')})")
                        counts["page approvals"] += 1
                        continue
                    items.append((item["path"], item["sha256"], item.get("source")))
                for item in data.get("approved_assets", []):
                    items.append((item["url"], item["sha256"], "www" + item["url"]))
                for target, digest, source_path in items:
                    approval_id = self.research.add_approval(
                        tx, kind="exact_file", target=target, sha256=digest, source_path=source_path, authority=authority,
                        approved_on=data.get("approved_on"), scope=data.get("scope"), manifest=relative)
                    if source_path and self.path(source_path).is_file():
                        self.asset(tx, source_path, kind="approved_source",
                                   access="private" if source_path.startswith("data/private") else "public")
                    self.origin(tx, approval_id, batch_id, relative, target, {"target": target, "sha256": digest})
                    counts["approvals"] += 1
                for page in data.get("public_pages", []):
                    approval_id = self.research.add_approval(tx, kind="page", target=page, authority=authority,
                                                             approved_on=data.get("approved_on"), manifest=relative,
                                                             scope=data.get("scope"))
                    counts["page approvals"] += 1
        return dict(counts)

    # ---------------------------------------------------------------- studies
    def step_studies(self) -> dict:
        counts = Counter()
        for path in sorted(self.source.glob("tools/study_stories/*.json")):
            relative = path.relative_to(self.source).as_posix()
            story = json.loads(path.read_bytes())
            with self.store.write(actor=ACTOR, tool="workbench_migrate studies", source=relative) as tx:
                batch_id, _ = self.batch(tx, relative, path.read_bytes(), "glasgow-study-story")
                study_id = stable_id("std", "glasgow", story.get("id") or path.stem)
                if self.store.get("study", study_id):
                    continue
                mentioned = sorted(set(re.findall(r"[A-Z][A-Za-z'\-]*-\d+", json.dumps(story))))
                people = [self.person(tx, pid) for pid in mentioned]
                text = lambda value: value if isinstance(value, str) else None  # noqa: E731 (structured values stay in extra)
                self.research.add_study(tx, id=study_id, title=text(story.get("title")) or path.stem, kind="family",
                                        summary=text(story.get("standfirst")), conclusion=text(story.get("answer")),
                                        rationale=text(story.get("question")), status=text(story.get("status")) or "draft",
                                        updated_on=text(story.get("reviewed")), access="public",
                                        links=[(p, "related") for p in people], extra={"legacy": story})
                self.asset(tx, relative, kind="presentation", access="public", about=[study_id])
                self.origin(tx, study_id, batch_id, relative, "/", None)
                counts["studies"] += 1
        return dict(counts)

    # ---------------------------------------------------------------- other inputs
    def step_other_assets(self) -> dict:
        """Remaining inputs the inventory marks for retention, referenced in place by hash."""
        counts = Counter()
        inventory_path = ROOT / "data" / "private" / "workbench" / "inventory" / "inventory.json"
        if not inventory_path.is_file():
            self.report["unresolved"].append({"input": "inventory", "reason": "run tools/workbench_inventory.py first"})
            return {}
        inventory = json.loads(inventory_path.read_text())
        # Per-profile folders are handled by step_profiles; top-level research files are retained here.
        wanted = [row for row in inventory["files"] if row["disposition"] in ("asset", "structured", "unresolved")
                  and (not row["path"].startswith("research/") or row["path"].count("/") == 1)
                  and row["access"] not in ("raw_dna", "secret")]
        for start in range(0, len(wanted), 500):
            with self.store.write(actor=ACTOR, tool="workbench_migrate assets", source="inventory") as tx:
                for row in wanted[start:start + 500]:
                    if self.asset(tx, row["path"], kind=ASSET_KINDS.get(row["category"], "file"), access=row["access"]):
                        counts["assets"] += 1
                    else:
                        counts["missing since inventory"] += 1
        return dict(counts)

    def step_documents(self) -> dict:
        """Hold research plans, parent candidates and the queue files in the database, row by row."""
        counts = Counter()
        documents = Documents(self.store)
        paths = sorted({path.relative_to(self.source).as_posix() for spec in SPECS
                        for path in self.source.glob(spec.pattern) if path.is_file()})
        for relative in paths:
            raw = self.path(relative).read_bytes()
            document = json.loads(raw)
            with self.store.write(actor=ACTOR, tool="workbench_migrate documents", source=relative) as tx:
                batch_id, _ = self.batch(tx, relative, raw, "glasgow-document")
                if documents.frame(relative) is None:
                    documents.store_document(tx, relative, document)
                    counts["documents held"] += 1
                elif documents.compose(relative) != document:
                    self.legacy(tx, batch_id, relative, f"@{sha256_bytes(raw)[:12]}", "conflict",
                                HAND_EDIT.replace("tools/research_entry.py", "tools/research_entry.py document"),
                                document)
                    counts["hand edits kept as conflicts"] += 1
                else:
                    counts["documents unchanged"] += 1
        return dict(counts)

    def step_baselines(self) -> dict:
        """The latest capture of each queued WikiTree profile becomes its observed baseline.

        A three-way comparison needs the remote state a proposal was prepared
        against. Where none was accepted, the most recent capture is the last
        *observed* state; it is recorded as such and never replaces a baseline
        accepted later.
        """
        counts = Counter()
        with self.store.write(actor=ACTOR, tool="workbench_migrate baselines",
                              reason="latest captures as observed baselines for queued profiles") as tx:
            for row in self.store.all("SELECT DISTINCT target FROM proposal WHERE system='wikitree' AND target IS NOT NULL "
                                      "ORDER BY target"):
                profile = row["target"]
                if self.store.one("SELECT 1 FROM remote_baseline WHERE system='wikitree' AND external_value=?", (profile,)):
                    counts["already had a baseline"] += 1
                    continue
                latest = self.research.latest_observation("wikitree", profile)
                if latest is None:
                    counts["queued profiles with no capture"] += 1
                    continue
                self.research.set_baseline(tx, system="wikitree", external_value=profile, observation_id=latest["id"],
                                           accepted_on=latest["captured_on"])
                counts["observed baselines recorded"] += 1
        return dict(counts)

    def privacy_levels(self) -> dict[str, int]:
        """The most recent recorded WikiTree privacy level of each person."""
        levels: dict[str, tuple[str, int]] = {}
        for row in self.store.all("SELECT entity_id, captured_on, fields_json FROM external_observation "
                                  "WHERE system='wikitree' AND entity_id IS NOT NULL"):
            fields = json.loads(row["fields_json"])
            raw = fields.get("raw") if isinstance(fields.get("raw"), dict) else fields
            level = raw.get("Privacy", raw.get("privacy")) if isinstance(raw, dict) else None
            if isinstance(level, int):
                key = row["captured_on"] or ""
                if row["entity_id"] not in levels or key >= levels[row["entity_id"]][0]:
                    levels[row["entity_id"]] = (key, level)
        return {person: level for person, (_, level) in levels.items()}

    def step_publication(self) -> dict:
        """Apply docs/privacy-policy.md to the imported tree facts of published catalogue people.

        * The catalogue's people are Glasgow's existing publication decision (access
          public); nobody else is made public here.
        * WikiTree Privacy 50 and above, and 40: their imported tree facts (events,
          places and tree relationships between two published people) are public.
        * Privacy 35: tree facts only; research narrative about them (findings,
          questions, searches, hypotheses, studies, notes) is withheld.
        * Below 35: no tree facts are published.
        Living people stay out through the projection's living rule.
        """
        counts = Counter()
        levels = self.privacy_levels()
        public = {row["id"] for row in self.store.all("SELECT id FROM person WHERE access='public'")}

        def allowed(person: str) -> bool:
            return person in public and levels.get(person, 60) >= 35

        imported = {row["entity_id"] for row in self.store.all(
            "SELECT DISTINCT o.entity_id FROM import_origin o JOIN import_batch b ON b.id=o.import_batch_id "
            "WHERE b.adapter='one-tree'")}
        with self.store.write(actor=ACTOR, tool="workbench_migrate publication", source="docs/privacy-policy.md",
                              reason="apply the approved WikiTree privacy-level publication policy") as tx:
            for event in self.store.all("SELECT * FROM event WHERE access<>'public' ORDER BY id"):
                if event["id"] not in imported:
                    continue
                people = [row["person_id"] for row in self.store.all(
                    "SELECT person_id FROM event_participant WHERE event_id=?", (event["id"],))]
                if people and all(allowed(person) for person in people):
                    tx.update("event", event["id"], {"access": "public"})
                    counts["imported events published"] += 1
                    if event["place_id"]:
                        place = self.store.get("place", event["place_id"])
                        if place["access"] != "public":
                            tx.update("place", place["id"], {"access": "public"})
                            counts["places published"] += 1
            for claim in self.store.all("SELECT * FROM claim WHERE origin='imported' AND access<>'public' "
                                        "AND kind IN ('relationship', 'attribute', 'vital') ORDER BY id"):
                people = [p for p in (claim["subject_person_id"], claim["object_person_id"]) if p]
                if people and all(allowed(person) for person in people):
                    tx.update("claim", claim["id"], {"access": "public"})
                    counts["imported tree claims published"] += 1
            for person in sorted(p for p in public if 35 <= levels.get(p, 60) < 40):
                for row in self.store.all("SELECT DISTINCT l.from_id, e.type FROM link l JOIN entity e ON e.id=l.from_id "
                                          "WHERE l.to_id=? AND e.type IN ('finding', 'question', 'search', 'hypothesis', "
                                          "'study', 'note')", (person,)):
                    item = self.store.get(row["type"], row["from_id"])
                    if item["access"] != "private":
                        tx.update(row["type"], row["from_id"], {"access": "private"})
                        counts["narrative withheld for Privacy 35 people"] += 1
            counts["published people at Privacy 35 (tree facts only)"] = sum(
                1 for p in public if levels.get(p) is not None and 35 <= levels[p] < 40)
            counts["published people below Privacy 35"] = sum(1 for p in public if levels.get(p, 60) < 35)
        return dict(counts)

    STEPS = ("onetree", "catalogue", "wikitree_observations", "gazetteer", "records", "relationships", "vitals",
             "findings", "profiles", "queue", "documents", "approvals", "studies", "other_assets", "baselines",
             "publication")

    def run(self, only: list[str] | None = None) -> dict:
        for name in self.STEPS:
            if only and name not in only:
                continue
            print(f"migrating {name} ...", flush=True)
            self.report["steps"][name] = getattr(self, f"step_{name}")()
        return self.report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Migrate Glasgow's legacy research into the project database")
    parser.add_argument("--source-root", type=Path, default=ROOT, help="Glasgow checkout to read (never written)")
    parser.add_argument("--project", type=Path, default=ROOT, help="project directory holding genealogy.toml")
    parser.add_argument("--only", nargs="+", choices=Migration.STEPS)
    parser.add_argument("--report", type=Path, default=ROOT / "data/private/workbench/migration-report.json")
    args = parser.parse_args(argv)
    with open_project(args.project, create=True) as project:
        report = Migration(project, args.source_root.resolve()).run(args.only)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report["steps"], indent=1))
    print(f"{len(report.get('reconciliation', []))} reconciled estimate rows, {len(report['conflicts'])} conflicts kept, "
          f"{len(report['unresolved'])} unresolved items; report: {args.report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
