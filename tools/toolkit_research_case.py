#!/usr/bin/env python3
"""Build a genealogy-research-workbench case from Glasgow's maintained research.

The workbench builds a whole site from one ``ResearchCase``. This tool makes
that case from the Glasgow One-Tree export plus the research Glasgow
maintains in its own formats, so the toolkit can rebuild as much of the
Glasgow site as its model can express, and so the gaps can be measured:

- ``research/canonical_records.json``: Source and Citation records, with
  Glasgow's reading of each record as the citation's abstract;
- ``research/relationship_assessments.json`` and
  ``relationship_probability_estimates.json``: a Claim with Evidence, a
  confidence and an estimate on the matching tree relationship (or a new
  research relationship when the tree has none). Glasgow's grades
  (``tools/evidence_labels.py``) become the project's own grades, with
  Glasgow's labels and meanings;
- ``research/latest-findings.json``: dated Finding records;
- ``research/<profile>/findings.md``: one Study per person, from the sections
  Glasgow publishes (editing logs and captured WikiTree pages stay out);
- ``www/data/people.json``: people the tree export lacks (record subjects
  and newer profiles), with their birth, death, places and family links.
  This is Glasgow's public catalogue, so Glasgow's own publication
  decisions already apply to it.

Text that names a profile Glasgow withholds is never carried: a note
paragraph mentioning one becomes "Private family details withheld.", and
any other record whose text mentions one is left out. This is Glasgow's own
rule (``tools/public_privacy.py``), applied before the workbench's.

It never changes Glasgow's files. The project it writes (default
``data/private/toolkit-build/``, ignored by Git) holds real research: build
and inspect it locally, never commit or upload it. The workbench's own
fail-closed publication rules decide what its site shows.

    .venv/bin/python tools/toolkit_research_case.py [--project DIR] [--build]

Each run starts the project afresh and prints a coverage report: what was
translated, what was left out and why.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from genealogy.case import CaseStore, grade_errors, validate_case  # noqa: E402
from genealogy.cli import initialize_project  # noqa: E402
from genealogy.config import ProjectConfig  # noqa: E402
from genealogy.importing import import_file  # noqa: E402
from genealogy.dates import year_of  # noqa: E402
from genealogy.models import (  # noqa: E402
    Citation, Claim, ClaimStatus, Confidence, Event, Evidence, Finding, LivingStatus, Name, Person, Place,
    Relationship, Sensitivity, Source, Study,
)

RESEARCH = ROOT / "research"
ONE_TREE = ROOT / "data/exports/one-tree/ONT_Glasgow_2026-08-18T15_43.json"
# The public catalogue: Glasgow's own publication decisions are already applied.
CATALOGUE = ROOT / "www/data/people.json"
DEFAULT_PROJECT = ROOT / "data/private/toolkit-build"
PUBLIC = Sensitivity.PUBLIC

try:
    from tools.evidence_labels import STATES, canonical_key  # noqa: E402
except ModuleNotFoundError:  # run from tools/
    from evidence_labels import STATES, canonical_key  # noqa: E402

# Glasgow's research grades (keys of ``evidence_labels.STATES``) and the
# standard workbench grade each counts as. Each becomes a project grade with
# Glasgow's own label and meaning.
GRADES = {"proved": Confidence.DOCUMENTED, "strongly_supported": Confidence.PROBABLE,
          "probable": Confidence.PROBABLE, "possible": Confidence.POSSIBLE,
          "uncertain": Confidence.POSSIBLE, "contradicted": Confidence.DISPROVED}
PARENT_ROLES = {"father", "mother", "parent"}
PARTNER_ROLES = {"husband", "wife", "spouse", "partner"}
FINDING_STATUS = {"confirmed": "reviewed", "qualified": "qualified"}


def person_id(profile: str) -> str:
    return f"one-tree:person:{profile}"


def _short(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()[:12]


WITHHELD = "*Private family details withheld.*"


class Translator:
    def __init__(self, case, private=lambda text: False):
        self.case = case
        # True for text naming a profile Glasgow withholds.
        self.private = private
        self.people = {record.id for record in case.records("Person")}
        # Every identifier a person is known by (merged profiles, catalogue slugs).
        self.alias = {record.id.split(":", 2)[2].casefold(): record.id for record in case.records("Person")
                      if record.id.startswith("one-tree:person:")}
        self.relationships = {}
        for record in case.records("Relationship"):
            self.relationships[(record.kind, record.subject_id, record.object_id)] = record
        self.report: Counter[str] = Counter()
        self.gaps: Counter[str] = Counter()
        self.used_grades: set[str] = set()

    def grades(self) -> dict[str, dict[str, str]]:
        """The ``[grades]`` table for the grades used, in Glasgow's order."""
        return {key: {"label": state["label"], "meaning": state["meaning"], "confidence": GRADES[key].value}
                for key, state in STATES.items() if key in self.used_grades}

    def pid(self, profile: str | None) -> str | None:
        return self.alias.get(str(profile or "").casefold())

    def known(self, profile: str | None) -> bool:
        return self.pid(profile) is not None

    # -- people beyond the tree export ---------------------------------------
    def catalogue(self, people):
        places: dict[str, str] = {}

        def place(name):
            name = " ".join(str(name or "").split())
            if not name:
                return None
            if name not in places:
                places[name] = f"glasgow:place:{_short(name)}"
                self.case.add(Place(id=places[name], name=name, sensitivity=PUBLIC))
            return places[name]

        for row in people:
            keys = [k for k in [*row.get("profile_ids", []), row.get("catalogue_id")] if k]
            existing = next((self.pid(k) for k in keys if self.known(k)), None)
            if existing:
                for key in keys:
                    self.alias.setdefault(key.casefold(), existing)
                continue
            if row.get("likely_living") is not False or not keys:
                self.gaps["catalogue people not marked historical"] += 1
                continue
            new_id = person_id(row["profile_ids"][0] if row.get("profile_ids") else row["catalogue_id"])
            events = []
            for kind in ("birth", "death"):
                date = row.get(kind) if year_of(row.get(kind)) else None
                where = place(row.get(f"{kind}_location"))
                if date or where:
                    events.append(Event(id=f"{new_id}:{kind}", kind=kind, date=date, place_id=where,
                                        participant_ids=[new_id], sensitivity=PUBLIC))
            surname = next(iter(row.get("last_names_at_birth") or []), None)
            self.case.add_many([*events, Person(id=new_id, names=[Name(row.get("name") or keys[0], surname=surname)],
                                                event_ids=[e.id for e in events], living=LivingStatus.DECEASED,
                                                sensitivity=PUBLIC)])
            self.people.add(new_id)
            for key in keys:
                self.alias[key.casefold()] = new_id
            self.report["people added from the catalogue" + (" (record subjects)" if row.get("catalogue_id", "").startswith("record-") else "")] += 1
        for row in people:
            me = next((self.pid(k) for k in [*row.get("profile_ids", []), row.get("catalogue_id")] if self.known(k)), None)
            if not me:
                continue
            for role, kind in (("father", "parent"), ("mother", "parent"), ("spouses", "spouse")):
                for relative in row.get(role) or []:
                    other = self.pid(relative.get("id"))
                    if not other or relative.get("withheld") or other == me:
                        continue
                    key = (kind, me, other)
                    if key in self.relationships or (kind == "spouse" and (kind, other, me) in self.relationships):
                        continue
                    record = Relationship(id=f"glasgow:relationship:{_short(':'.join(key))}", subject_id=me, object_id=other,
                                          kind=kind, sensitivity=PUBLIC)
                    self.case.add(record)
                    self.relationships[key] = record
                    self.report["family links added from the catalogue"] += 1

    # -- sources ---------------------------------------------------------
    def records(self, rows):
        citations = {}
        for row in rows:
            rid = row["record_id"]
            if self.private(json.dumps({k: row.get(k) for k in ("association", "date", "place", "source_url", "role")}, ensure_ascii=False)):
                self.gaps["records naming a withheld profile"] += 1
                continue
            source = Source(id=f"glasgow:source:{rid}", title=row.get("association") or rid,
                            source_type=row.get("role") or "record", url=row.get("source_url") or None,
                            sensitivity=PUBLIC)
            locator = "; ".join(str(row[key]) for key in ("date", "place") if row.get(key))
            reading = " ".join(str(row.get("note") or "").split()) or None
            if reading and self.private(reading):
                self.gaps["record readings naming a withheld profile, left out"] += 1
                reading = None
            citation = Citation(id=f"glasgow:citation:{rid}", source_id=source.id, locator=locator or None,
                                abstract=reading, sensitivity=PUBLIC)
            self.case.add_many([source, citation])
            citations[rid] = citation.id
            self.report["sources from canonical records"] += 1
            if reading:
                self.report["record readings carried as citation abstracts"] += 1
        return citations

    # -- relationship assessments -----------------------------------------
    def assessments(self, rows, estimates, citations):
        percent = {row["assertion_id"]: row["percent"] for row in estimates if row.get("assertion_id") and isinstance(row.get("percent"), int)}
        for row in rows:
            aid = row["assertion_id"]
            pair = row.get("people") or []
            if len(pair) != 2 or not all(self.known(p) for p in pair):
                self.gaps["assessments naming a person who is not public"] += 1
                continue
            roles = {p: str(row["perspectives"].get(other, {}).get("relationship", "")).casefold()
                     for p, other in (pair, pair[::-1])}
            # roles[p] is what p is to the other person.
            parents = [p for p in pair if roles[p] in PARENT_ROLES]
            if len(parents) == 1:
                parent = parents[0]
                child = pair[1] if parent == pair[0] else pair[0]
                kind, subject, obj = "parent", self.pid(child), self.pid(parent)
            elif all(roles[p] in PARTNER_ROLES for p in pair):
                kind, subject, obj = "spouse", self.pid(pair[0]), self.pid(pair[1])
            else:
                self.gaps[f"assessments of other relationships ({'/'.join(sorted(set(roles.values())))})"] += 1
                continue
            if self.private(row.get("basis") or ""):
                self.gaps["assessments whose basis names a withheld profile"] += 1
                continue
            grade = canonical_key(row.get("status"))
            if grade in GRADES:
                confidence = GRADES[grade]
                self.used_grades.add(grade)
            else:
                confidence, grade = Confidence.UNKNOWN, None
                self.gaps[f"assessments with the state '{row.get('status')}', left unassessed"] += 1
            cited = [citations[s] for s in row.get("source_ids", []) if s in citations]
            claim = Claim(id=f"glasgow:claim:{aid}", subject_id=subject, predicate=kind, value=obj,
                          citation_ids=cited, status=ClaimStatus.SUPPORTED if confidence in (
                              Confidence.DOCUMENTED, Confidence.PROBABLE) else ClaimStatus.ASSERTED,
                          confidence=confidence, grade=grade, rationale=row.get("basis"), sensitivity=PUBLIC)
            records = [claim] + [Evidence(id=f"glasgow:evidence:{aid}:{n}", claim_id=claim.id, citation_id=cid,
                                          assessment=row.get("basis") or "Reviewed record.", confidence=confidence,
                                          grade=grade, sensitivity=PUBLIC) for n, cid in enumerate(cited)]
            self.case.add_many(records)
            existing = self.relationships.get((kind, subject, obj)) or (
                self.relationships.get((kind, obj, subject)) if kind == "spouse" else None)
            if existing is None:
                existing = Relationship(id=f"glasgow:relationship:{aid}", subject_id=subject, object_id=obj,
                                        kind=kind, sensitivity=PUBLIC)
                self.case.add(existing)
                self.relationships[(kind, subject, obj)] = existing
                self.report["research relationships not in the tree export"] += 1
            existing.confidence, existing.grade = confidence, grade
            existing.claim_ids = sorted(set(existing.claim_ids) | {claim.id})
            if aid in percent:
                existing.estimate = percent[aid]
                self.report["relationships with an assessed percentage"] += 1
            self.report["assessed relationships"] += 1
            if len(cited) < len(row.get("source_ids", [])):
                self.gaps["assessment sources that are not canonical records"] += len(row["source_ids"]) - len(cited)

    # -- findings ----------------------------------------------------------
    def findings(self, rows):
        sources: dict[str, str] = {}

        def cite(source):
            url = source.get("url")
            if not url:
                return None
            if url not in sources:
                sources[url] = f"glasgow:citation:url:{_short(url)}"
                origin = Source(id=f"glasgow:source:url:{_short(url)}", title=source.get("title") or url,
                                source_type="record", url=url, sensitivity=PUBLIC)
                self.case.add_many([origin, Citation(id=sources[url], source_id=origin.id, sensitivity=PUBLIC)])
                self.report["sources cited by findings"] += 1
            return sources[url]

        for row in rows:
            subjects = [p.get("id") or re.sub(r"^/people/|\.html$", "", p.get("url") or "") for p in row.get("people", [])]
            related = list(dict.fromkeys(self.pid(p) for p in subjects if self.known(p)))
            missing = [p for p in subjects if not self.known(p)]
            if missing and not related:
                self.gaps["findings about people who are not public"] += 1
                continue
            if missing:
                self.gaps["finding subjects who are not public, left unlinked"] += len(missing)
            if self.private(json.dumps([row.get("finding"), row.get("qualification"), row.get("sources")], ensure_ascii=False)):
                self.gaps["findings naming a withheld profile"] += 1
                continue
            cited = [c for c in (cite(source) for source in row.get("sources", [])) if c]
            self.case.add(Finding(id=f"glasgow:finding:{row['id']}", conclusion=row["finding"], related_ids=related,
                                  status=FINDING_STATUS.get(row.get("status"), "reviewed"), recorded_on=row["found_on"],
                                  limitations=row.get("qualification") or None, citation_ids=list(dict.fromkeys(cited)),
                                  kind=row.get("kind") or None, sensitivity=PUBLIC))
            self.report["findings"] += 1

    # -- research notes ------------------------------------------------------
    def markdown(self, text: str) -> str:
        """Glasgow's Markdown → the workbench subset; unsupported parts become text."""
        text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
        blocks = re.split(r"(\n\s*\n)", text)
        for index, block in enumerate(blocks):
            if block.strip() and self.private(block):
                blocks[index] = WITHHELD
                self.report["note paragraphs withheld (they name a withheld profile)"] += 1
        text = "".join(blocks)
        def wiki(match):
            profile, label = match[1], match[2] or match[1]
            return f"[[{self.pid(profile)}|{label}]]" if self.known(profile) else label
        text = re.sub(r"\[\[([A-Za-z][A-Za-z_'’]*(?:-[A-Za-z][A-Za-z_'’]*)*-\d+)(?:\|([^\]]+))?\]\]", wiki, text)
        # Other WikiTree links (categories, Space pages, footnotes) become their label.
        text = re.sub(r"\[\[(?!one-tree:)([^\[\]|]+)(?:\|([^\[\]]+))?\]\]", lambda m: (m[2] or m[1]).strip(), text)
        def link(match):
            return match[0] if match[2].startswith(("http://", "https://")) else match[1]
        text = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", link, text)
        tables = len(re.findall(r"^\s*\|(?:\s*:?-{3,}:?\s*\|)+\s*$", text, re.M))
        if tables:
            self.report["tables in research notes"] += tables
        return text

    def notes(self, directory: Path, sections=None):
        """One Study per person from the sections Glasgow publishes.

        ``sections(profile)`` is Glasgow's own reader filter
        (``build_research_catalog._load_research_findings``): it drops editing
        logs, captured WikiTree pages and unfilled templates.
        """
        for path in sorted(directory.glob("*/findings.md")):
            profile = path.parent.name
            if not self.known(profile):
                self.gaps["research notes about people who are not public"] += 1
                continue
            text = path.read_text(encoding="utf-8")
            title = re.search(r"^#\s+(.+)$", text, re.M)
            if sections is None:
                body = re.sub(r"^#\s+.+\n", "", text, count=1)
            else:
                published = [section for entry in sections(profile) for section in entry["sections"]]
                if not published:
                    self.gaps["research notes with no reader-facing section"] += 1
                    continue
                body = "\n\n".join(f"## {section['title']}\n\n{section['markdown']}" for section in published)
            updated = re.search(r"Last updated:\s*(\d{4}-\d{2}-\d{2})", text)
            self.case.add(Study(id=f"glasgow:notes:{profile}", title=(title[1] if title else f"Research notes: {profile}"),
                                body=self.markdown(body), related_ids=[self.pid(profile)], status="draft",
                                updated_on=updated[1] if updated else None, sensitivity=PUBLIC))
            self.report["research notes"] += 1


def build_case(project: Path, *, one_tree: Path = ONE_TREE, research: Path = RESEARCH, catalogue: Path = CATALOGUE) -> dict:
    if project.exists():
        shutil.rmtree(project)
    initialize_project(project, "Glasgow Surname Project (workbench build)")
    config = ProjectConfig.load(project / "genealogy.toml")
    store = CaseStore(project / config.case_directory)
    case = store.load(config.default_case)
    imported = import_file(project, case, config, one_tree, publish_deceased=True, publish_reviewed_sources=True)
    case = store.load(config.default_case)  # the import saves its own result
    try:
        from tools.public_privacy import from_sources
    except ModuleNotFoundError:  # run from tools/
        from public_privacy import from_sources
    t = Translator(case, from_sources().contains_private_id)
    load = lambda name: json.loads((research / name).read_text(encoding="utf-8"))
    t.catalogue(json.loads(catalogue.read_text(encoding="utf-8"))["people"])
    citations = t.records(load("canonical_records.json"))
    t.assessments(load("relationship_assessments.json"), load("relationship_probability_estimates.json")["estimates"], citations)
    t.findings(load("latest-findings.json")["findings"])
    try:
        from tools.build_research_catalog import _load_research_findings
    except ModuleNotFoundError:
        from build_research_catalog import _load_research_findings
    t.notes(research, lambda profile: _load_research_findings([profile]))
    grades = t.grades()
    with (project / "genealogy.toml").open("a", encoding="utf-8") as handle:
        for key, grade in grades.items():
            handle.write(f"\n[grades.{key}]\n" + "".join(f"{name} = {json.dumps(grade[name], ensure_ascii=False)}\n"
                                                         for name in ("label", "meaning", "confidence")))
    errors = validate_case(case) + grade_errors(case, ProjectConfig.load(project / "genealogy.toml").grades)
    if errors:
        raise ValueError("translated case is invalid:\n" + "\n".join(errors[:20]))
    store.save(case)
    return {"people": imported["people"], "published_people": imported["published_people"],
            "translated": dict(t.report), "gaps": dict(sorted(t.gaps.items(), key=lambda kv: -kv[1]))}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--project", type=Path, default=DEFAULT_PROJECT)
    parser.add_argument("--build", action="store_true", help="also build the workbench site into PROJECT/dist")
    args = parser.parse_args(argv)
    report = build_case(args.project)
    if args.build:
        from genealogy.site import build_site
        config = ProjectConfig.load(args.project / "genealogy.toml")
        case = CaseStore(args.project / config.case_directory).load(config.default_case)
        build_site(case, config, args.project / "dist")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
