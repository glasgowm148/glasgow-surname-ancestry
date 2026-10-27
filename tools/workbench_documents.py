"""Glasgow's row-structured documents, held in the research database and generated back.

Each document below is a JSON file of rows (research plans, parent-candidate
lists, the WikiTree update queue and its review files). After migration every
row lives on its own database entity (a question, search, finding, hypothesis
or proposal when the core models it, otherwise a ``document_row`` note), with
its original text kept order-preserving; the rest of the file (top-level keys,
their order and any unmodelled lists) is a ``document_frame`` note carrying the
document's revision. The file is recomposed from those rows, so the database is
the authority and the file a generated view.

Changes are made by editing the file and recording it:
``tools/research_entry.py document PATH --expected-revision N``. A row that
disappears from the file is marked removed, never deleted.
"""
from __future__ import annotations

from dataclasses import dataclass
import fnmatch
import json
import re
from typing import Any

from genealogy.store import Research, StaleRevisionError, StoreError, stable_id
from genealogy.store.vocabulary import PROPOSAL_MAP, QUESTION_MAP, normalise

ROW_TABLES = ("question", "search", "finding", "hypothesis", "proposal")


@dataclass(frozen=True)
class Spec:
    pattern: str
    fields: tuple[tuple[str, str], ...]   # (field, "list" | "dict"); field "" is the document itself

    def matches(self, relative: str) -> bool:
        return fnmatch.fnmatch(relative, self.pattern) and relative.count("/") == self.pattern.count("/")


SPECS = (
    Spec("research/*/research_plan.json", (("questions", "list"), ("web_searches", "list"), ("findings", "list"))),
    Spec("research/*/parent_candidates.json", (("", "list"),)),
    Spec("data/wikitree/profile-update-queue.json", (("entries", "dict"),)),
    Spec("research/research-queue-matches.json", (("reviews", "dict"),)),
    Spec("research/research-queue-overrides.json", (("draft_replacements", "dict"),)),
)


def spec_for(relative: str) -> Spec | None:
    return next((spec for spec in SPECS if spec.matches(relative)), None)


def dump(value: Any) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False) + "\n"


def frame_id(relative: str) -> str:
    return stable_id("not", "document-frame", relative)


def modelled_entity(relative: str, field: str, index: int, key: str | None, row: Any) -> str | None:
    """The entity the migration created for a row, by the migration's own deterministic ids."""
    if relative.endswith("research_plan.json"):
        prefix = {"questions": "qst", "web_searches": "sch", "findings": "fnd"}[field]
        return stable_id(prefix, relative, index)
    if relative.endswith("parent_candidates.json"):
        return stable_id("hyp", relative, (row.get("id") if isinstance(row, dict) else None) or index)
    if relative == "data/wikitree/profile-update-queue.json":
        return stable_id("prp", "glasgow-queue", key)
    return None


def core_columns(table: str, row: Any) -> dict[str, Any]:
    """The modelled columns of a row, as the migration maps them."""
    if table == "question":
        if isinstance(row, str):
            return {"question": row}
        status, original = normalise(row.get("status"), QUESTION_MAP, "open")
        return {"question": row.get("question") or json.dumps(row, ensure_ascii=False), "status": status,
                "status_original": original}
    if table == "search":
        row = row if isinstance(row, dict) else {"query": str(row)}
        result = str(row.get("result") or row.get("outcome") or row.get("finding") or "not recorded")
        return {"scope": row.get("query") or row.get("search") or json.dumps(row, ensure_ascii=False), "result": result,
                "searched_on": row.get("date") or row.get("searched_on"), "repository": row.get("site") or row.get("url"),
                "outcome": "negative" if re.match(r"\s*(no|none|nothing|not found)\b", result, re.I) else "unknown"}
    if table == "finding":
        return {"statement": row["claim"], "qualification": row.get("reasoning")}
    if table == "hypothesis":
        return {"statement": f"{row.get('candidate') or 'A candidate'} as a parent: {row.get('assessment') or ''}".strip(),
                "status": row.get("state") or "open", "supports": "\n".join(row.get("supports") or []) or None,
                "objections": "\n".join(row.get("objections") or []) or None}
    if table == "proposal":
        word = row.get("status") or "pending"
        status = "verified" if "VERIFIED" in word.upper() else (
            "proposed" if word.upper().startswith("OPEN") or word == "pending" else None)
        normalised, original = normalise(status or word, PROPOSAL_MAP, "draft")
        return {"status": normalised, "status_original": original, "rationale": row.get("summary"),
                "diff_json": None if row.get("relationship_changes") is None else json.dumps(
                    row["relationship_changes"], ensure_ascii=False, sort_keys=True, separators=(",", ":"))}
    return {}


MODELLED_TABLE = {"qst": "question", "sch": "search", "fnd": "finding", "hyp": "hypothesis", "prp": "proposal"}


def subject_of(relative: str, research: Research) -> str | None:
    parts = relative.split("/")
    if len(parts) == 3 and parts[0] == "research":
        found = (research.find_external("wikitree", parts[1])
                 or research.find_external("glasgow-local", parts[1]))
        return found[0] if found else None
    return None


def rows_of(document: Any, spec: Spec) -> list[tuple[str, int, str | None, Any]]:
    rows = []
    for field, shape in spec.fields:
        value = document if field == "" else (document.get(field) if isinstance(document, dict) else None)
        if value is None:
            continue
        items = list(value.items()) if shape == "dict" else list(enumerate(value))
        for index, (key, row) in enumerate(items):
            rows.append((field, index, key if shape == "dict" else None, row))
    return rows


def frame_of(document: Any, spec: Spec) -> Any:
    if spec.fields[0][0] == "":
        return None
    return {key: (None if key in dict(spec.fields) else value) for key, value in document.items()}


def row_identity(relative: str, field: str, index: int, key: str | None, row: Any) -> tuple:
    if key is not None:
        return field, "key", key
    if relative.endswith("parent_candidates.json") and isinstance(row, dict) and row.get("id"):
        return field, "id", row["id"]
    return field, "index", index


class Documents:
    def __init__(self, store):
        self.store = store
        self.research = Research(store)

    # ------------------------------------------------------------ reading
    def frames(self) -> list[dict[str, Any]]:
        frames = []
        for note in self.store.all("SELECT * FROM note WHERE kind='document_frame' ORDER BY id"):
            frames.append({**json.loads(note["text"]), "note": note})
        return frames

    def move_document(self, tx, old: str, new: str, expected_revision: int) -> None:
        """Move a document frame while retaining row/entity IDs and history."""
        old_frame = self.frame(old)
        if not old_frame:
            raise StoreError(f"no active held document: {old}")
        if old_frame["note"]["revision"] != expected_revision:
            note = old_frame["note"]
            raise StaleRevisionError("note", note["id"], expected_revision, note["revision"],
                                     {"document": old, "current": self.compose(old)})
        if self.store.get("note", frame_id(new)) or not spec_for(old) or spec_for(old) != spec_for(new):
            raise StoreError("destination exists or document specs are incompatible")
        old_note = old_frame["note"]
        tx.update("note", old_note["id"], {"kind": "document_frame_history",
                                           "text": json.dumps({"document": old, "moved_to": new,
                                                                "frame": old_frame["frame"],
                                                                "recorded": json.loads(old_note["text"]).get("recorded", 0)},
                                                               ensure_ascii=False)}, expected_revision=expected_revision)
        subject = subject_of(new, self.research)
        self.research.add_note(tx, id=frame_id(new), kind="document_frame", title=new,
                               text=json.dumps({"document": new, "frame": old_frame["frame"], "recorded": 0},
                                               ensure_ascii=False), links=[(subject, "about")] if subject else ())
        for row in self.stored_rows(old):
            entity = self.store.get(row["table"], row["entity"])
            meta = {**row, "document": new}
            meta.pop("entity", None); meta.pop("table", None); meta.pop("revision", None)
            changes = {"text": json.dumps(meta, ensure_ascii=False)} if row["table"] == "note" else {
                "extra_json": json.dumps({**json.loads(entity["extra_json"]), "document_row": meta},
                                          ensure_ascii=False, sort_keys=True, separators=(",", ":"))}
            tx.update(row["table"], row["entity"], changes, expected_revision=entity["revision"])

    def frame(self, relative: str) -> dict[str, Any] | None:
        note = self.store.get("note", frame_id(relative))
        if note and note.get("kind") != "document_frame":
            return None
        return {**json.loads(note["text"]), "note": note} if note else None

    def stored_rows(self, relative: str) -> list[dict[str, Any]]:
        marker = f"%{json.dumps(relative)}%"   # then filtered exactly on the parsed field
        rows = []
        for table in ROW_TABLES:
            for entity in self.store.all(f"SELECT id, revision, extra_json FROM {table} WHERE extra_json LIKE ?", (marker,)):
                meta = json.loads(entity["extra_json"])["document_row"]
                if meta["document"] == relative:
                    rows.append({**meta, "entity": entity["id"], "table": table, "revision": entity["revision"]})
        for note in self.store.all("SELECT id, revision, text FROM note WHERE kind='document_row' AND text LIKE ?",
                                   (marker,)):
            meta = json.loads(note["text"])
            if meta["document"] == relative:
                rows.append({**meta, "entity": note["id"], "table": "note", "revision": note["revision"]})
        return rows

    def compose(self, relative: str) -> Any:
        frame = self.frame(relative)
        spec = spec_for(relative)
        rows = sorted((row for row in self.stored_rows(relative) if not row.get("removed")),
                      key=lambda row: (row["field"], row["index"], row.get("key") or ""))
        def collection(field: str, shape: str):
            mine = [row for row in rows if row["field"] == field]
            if shape == "dict":
                return {row["key"]: json.loads(row["row_json"]) for row in mine}
            return [json.loads(row["row_json"]) for row in mine]
        if spec.fields[0][0] == "":
            return collection("", spec.fields[0][1])
        document = dict(frame["frame"])
        for field, shape in spec.fields:
            if field in document:
                document[field] = collection(field, shape)
        return document

    def files(self) -> dict[str, str]:
        return {frame["document"]: dump(self.compose(frame["document"])) for frame in self.frames()}

    # ------------------------------------------------------------ writing
    def _annotate(self, tx, relative: str, field: str, index: int, key: str | None, row: Any, existing_lookup=None) -> str:
        meta = {"document": relative, "field": field, "index": index, "key": key,
                "row_json": json.dumps(row, ensure_ascii=False)}
        target = modelled_entity(relative, field, index, key, row)
        prior = (existing_lookup or {}).get(row_identity(relative, field, index, key, row))
        if prior:
            target, table = prior["entity"], prior["table"]
        table = table if prior else (self.store.entity_type(target) if target else None)
        if target and table is None and self._can_model(target, row):
            table = self._create_modelled(tx, target, relative, row)
        if table in ROW_TABLES:
            entity = self.store.get(table, target)
            extra = json.loads(entity["extra_json"] or "{}")
            if extra.get("document_row") != meta:
                changes = {"extra_json": json.dumps({**extra, "document_row": meta}, ensure_ascii=False,
                                                    sort_keys=True, separators=(",", ":"))}
                if extra.get("document_row") is not None:   # a recorded change: follow it in the modelled columns
                    changes.update(core_columns(table, row))
                tx.update(table, target, changes, expected_revision=entity["revision"])
            return target
        note_id = prior["entity"] if prior else stable_id("not", "document-row", relative, field,
                                                        key if key is not None else index)
        text = json.dumps(meta, ensure_ascii=False)
        existing = self.store.get("note", note_id)
        if existing is None:
            subject = subject_of(relative, self.research)
            self.research.add_note(tx, id=note_id, kind="document_row", title=f"{relative} {field} {key or index}",
                                   text=text, links=[(subject, "about")] if subject else ())
        elif existing["text"] != text:
            tx.update("note", note_id, {"text": text}, expected_revision=existing["revision"])
        return note_id

    @staticmethod
    def _can_model(target: str, row: Any) -> bool:
        prefix = target.split("-", 1)[0]
        if prefix == "fnd":
            return isinstance(row, dict) and bool(row.get("claim"))
        return prefix in MODELLED_TABLE and (prefix != "hyp" or isinstance(row, dict))

    def _create_modelled(self, tx, target: str, relative: str, row: Any) -> str:
        """A new row in a modelled field becomes a real question, search, finding, hypothesis or proposal."""
        table = MODELLED_TABLE[target.split("-", 1)[0]]
        subject = subject_of(relative, self.research)
        about = [(subject, "about")] if subject else []
        columns = core_columns(table, row)
        if table == "question":
            self.research.add_question(tx, id=target, question=columns["question"],
                                       status=columns.get("status_original") or columns.get("status"), links=about)
        elif table == "search":
            self.research.log_search(tx, id=target, scope=columns["scope"], result=columns["result"],
                                     outcome=columns["outcome"], searched_on=columns["searched_on"],
                                     repository=columns["repository"], links=about)
        elif table == "finding":
            self.research.add_finding(tx, id=target, statement=columns["statement"], status="qualified",
                                      qualification=columns["qualification"],
                                      links=[(subject, "subject")] if subject else ())
        elif table == "hypothesis":
            self.research.add_hypothesis(tx, id=target, kind="parentage", statement=columns["statement"],
                                         status=columns["status"], supports=columns["supports"],
                                         objections=columns["objections"], links=about)
        else:
            self.research.create_proposal(tx, id=target, kind="wikitree_update", system="wikitree", status=row.get("status"),
                                          rationale=row.get("summary"), diff=row.get("relationship_changes"),
                                          actor="research_entry")
        return table

    def store_document(self, tx, relative: str, document: Any) -> None:
        """Hold a document's rows and frame in the database (first import or a recorded change)."""
        spec = spec_for(relative)
        seen: set[str] = set()
        existing_rows = self.stored_rows(relative)
        lookup = {row_identity(relative, r["field"], r["index"], r.get("key"), json.loads(r["row_json"])): r
                  for r in existing_rows}
        for field, index, key, row in rows_of(document, spec):
            seen.add(self._annotate(tx, relative, field, index, key, row, lookup))
        for row in existing_rows:
            if row["entity"] not in seen and not row.get("removed"):
                self._mark_removed(tx, row)
        note = self.store.get("note", frame_id(relative))
        # 'recorded' counts recorded changes, so every change raises the document revision.
        recorded = json.loads(note["text"]).get("recorded", 0) + 1 if note else 0
        text = json.dumps({"document": relative, "frame": frame_of(document, spec), "recorded": recorded},
                          ensure_ascii=False)
        subject = subject_of(relative, self.research)
        if note is None:
            self.research.add_note(tx, id=frame_id(relative), kind="document_frame", title=relative, text=text,
                                   links=[(subject, "about")] if subject else ())
        else:
            tx.update("note", note["id"], {"text": text})

    def _mark_removed(self, tx, row: dict[str, Any]) -> None:
        if row["table"] == "note":
            note = self.store.get("note", row["entity"])
            meta = json.loads(note["text"])
            tx.update("note", note["id"], {"text": json.dumps({**meta, "removed": True}, ensure_ascii=False)},
                      expected_revision=note["revision"])
        else:
            entity = self.store.get(row["table"], row["entity"])
            extra = json.loads(entity["extra_json"])
            extra["document_row"] = {**extra["document_row"], "removed": True}
            tx.update(row["table"], row["entity"], {"extra_json": json.dumps(extra, ensure_ascii=False, sort_keys=True,
                                                                             separators=(",", ":"))},
                      expected_revision=entity["revision"])
