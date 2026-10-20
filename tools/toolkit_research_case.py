#!/usr/bin/env python3
"""Build a genealogy-research-workbench case from Glasgow's maintained research.

The workbench builds a whole site from one ``ResearchCase``. This tool makes
that case from the Glasgow One-Tree export plus the research Glasgow
maintains in its own formats, so the toolkit can rebuild as much of the
Glasgow site as its model can express, and so the gaps can be measured:

- ``research/canonical_records.json``: Source and Citation records;
- ``research/relationship_assessments.json`` and
  ``relationship_probability_estimates.json``: a Claim with Evidence, a
  confidence and an estimate on the matching tree relationship (or a new
  research relationship when the tree has none);
- ``research/latest-findings.json``: dated Finding records;
- ``research/<profile>/findings.md``: one Study of research notes per person.

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

from genealogy.case import CaseStore, validate_case  # noqa: E402
from genealogy.cli import initialize_project  # noqa: E402
from genealogy.config import ProjectConfig  # noqa: E402
from genealogy.importing import import_file  # noqa: E402
from genealogy.models import (  # noqa: E402
    Citation, Claim, ClaimStatus, Confidence, Evidence, Finding, Relationship, Sensitivity, Source, Study,
)

RESEARCH = ROOT / "research"
ONE_TREE = ROOT / "data/exports/one-tree/ONT_Glasgow_2026-08-18T15_43.json"
DEFAULT_PROJECT = ROOT / "data/private/toolkit-build"
PUBLIC = Sensitivity.PUBLIC

# Glasgow grades → the workbench vocabulary. "Strongly supported" and
# "uncertain" have no workbench equivalent; they map to the nearest grade
# and are counted in the report.
GRADES = {"proved": Confidence.DOCUMENTED, "strongly_supported": Confidence.PROBABLE,
          "probable": Confidence.PROBABLE, "possible": Confidence.POSSIBLE,
          "uncertain": Confidence.POSSIBLE, "disproved": Confidence.DISPROVED}
PARENT_ROLES = {"father", "mother", "parent"}
PARTNER_ROLES = {"husband", "wife", "spouse", "partner"}
FINDING_STATUS = {"confirmed": "reviewed", "qualified": "qualified"}


def person_id(profile: str) -> str:
    return f"one-tree:person:{profile}"


def _short(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()[:12]


class Translator:
    def __init__(self, case):
        self.case = case
        self.people = {record.id for record in case.records("Person")}
        self.relationships = {}
        for record in case.records("Relationship"):
            self.relationships[(record.kind, record.subject_id, record.object_id)] = record
        self.report: Counter[str] = Counter()
        self.gaps: Counter[str] = Counter()

    def known(self, profile: str | None) -> bool:
        return bool(profile) and person_id(profile) in self.people

    # -- sources ---------------------------------------------------------
    def records(self, rows):
        citations = {}
        for row in rows:
            rid = row["record_id"]
            source = Source(id=f"glasgow:source:{rid}", title=row.get("association") or rid,
                            source_type=row.get("role") or "record", url=row.get("source_url") or None,
                            sensitivity=PUBLIC)
            locator = "; ".join(str(row[key]) for key in ("date", "place") if row.get(key))
            citation = Citation(id=f"glasgow:citation:{rid}", source_id=source.id, locator=locator or None,
                                sensitivity=PUBLIC)
            self.case.add_many([source, citation])
            citations[rid] = citation.id
            self.report["sources from canonical records"] += 1
            if row.get("note"):
                self.gaps["record readings (canonical record notes) not carried: no field for a reading"] += 1
        return citations

    # -- relationship assessments -----------------------------------------
    def assessments(self, rows, estimates, citations):
        percent = {row["assertion_id"]: row["percent"] for row in estimates if row.get("assertion_id") and isinstance(row.get("percent"), int)}
        for row in rows:
            aid = row["assertion_id"]
            pair = row.get("people") or []
            if len(pair) != 2 or not all(self.known(p) for p in pair):
                self.gaps["assessments naming a record subject or person outside the tree export"] += 1
                continue
            roles = {p: str(row["perspectives"].get(other, {}).get("relationship", "")).casefold()
                     for p, other in (pair, pair[::-1])}
            # roles[p] is what p is to the other person.
            parents = [p for p in pair if roles[p] in PARENT_ROLES]
            if len(parents) == 1:
                parent = parents[0]
                child = pair[1] if parent == pair[0] else pair[0]
                kind, subject, obj = "parent", person_id(child), person_id(parent)
            elif all(roles[p] in PARTNER_ROLES for p in pair):
                kind, subject, obj = "spouse", person_id(pair[0]), person_id(pair[1])
            else:
                self.gaps[f"assessments of other relationships ({'/'.join(sorted(set(roles.values())))})"] += 1
                continue
            status = str(row.get("status"))
            confidence = GRADES.get(status, Confidence.UNKNOWN)
            if status in ("strongly_supported", "uncertain"):
                self.gaps[f"'{status}' grade shown as {confidence.value}"] += 1
            cited = [citations[s] for s in row.get("source_ids", []) if s in citations]
            claim = Claim(id=f"glasgow:claim:{aid}", subject_id=subject, predicate=kind, value=obj,
                          citation_ids=cited, status=ClaimStatus.SUPPORTED if confidence in (
                              Confidence.DOCUMENTED, Confidence.PROBABLE) else ClaimStatus.ASSERTED,
                          confidence=confidence, rationale=row.get("basis"), sensitivity=PUBLIC)
            records = [claim] + [Evidence(id=f"glasgow:evidence:{aid}:{n}", claim_id=claim.id, citation_id=cid,
                                          assessment=row.get("basis") or "Reviewed record.", confidence=confidence,
                                          sensitivity=PUBLIC) for n, cid in enumerate(cited)]
            self.case.add_many(records)
            existing = self.relationships.get((kind, subject, obj)) or (
                self.relationships.get((kind, obj, subject)) if kind == "spouse" else None)
            if existing is None:
                existing = Relationship(id=f"glasgow:relationship:{aid}", subject_id=subject, object_id=obj,
                                        kind=kind, sensitivity=PUBLIC)
                self.case.add(existing)
                self.relationships[(kind, subject, obj)] = existing
                self.report["research relationships not in the tree export"] += 1
            existing.confidence = confidence
            existing.claim_ids = sorted(set(existing.claim_ids) | {claim.id})
            if aid in percent:
                existing.estimate = percent[aid]
                self.report["relationships with an assessed percentage"] += 1
            self.report["assessed relationships"] += 1
            if len(cited) < len(row.get("source_ids", [])):
                self.gaps["assessment sources that are not canonical records"] += len(row["source_ids"]) - len(cited)

    # -- findings ----------------------------------------------------------
    def findings(self, rows):
        for row in rows:
            related = [person_id(p["id"]) for p in row.get("people", []) if self.known(p.get("id"))]
            missing = [p for p in row.get("people", []) if not self.known(p.get("id"))]
            if missing and not related:
                self.gaps["findings about record subjects only (no person in the tree export)"] += 1
                continue
            if missing:
                self.gaps["finding subjects outside the tree export left unlinked"] += len(missing)
            conclusion = row["finding"]
            if row.get("qualification"):
                conclusion += f" Limits: {row['qualification']}"
                self.gaps["finding limitations folded into the conclusion: no field for them"] += 1
            if row.get("sources"):
                self.gaps["finding sources not linked: a Finding cannot cite a source directly"] += 1
            self.gaps[f"finding type '{row.get('kind')}' not carried"] += 1
            self.case.add(Finding(id=f"glasgow:finding:{row['id']}", conclusion=conclusion, related_ids=related,
                                  status=FINDING_STATUS.get(row.get("status"), "reviewed"), recorded_on=row["found_on"],
                                  sensitivity=PUBLIC))
            self.report["findings"] += 1

    # -- research notes ------------------------------------------------------
    def markdown(self, text: str) -> str:
        """Glasgow's Markdown → the workbench subset; unsupported parts become text."""
        text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
        def wiki(match):
            profile, label = match[1], match[2] or match[1]
            return f"[[{person_id(profile)}|{label}]]" if self.known(profile) else label
        text = re.sub(r"\[\[([A-Za-z][A-Za-z_'’]*(?:-[A-Za-z][A-Za-z_'’]*)*-\d+)(?:\|([^\]]+))?\]\]", wiki, text)
        # Other WikiTree links (categories, Space pages, footnotes) become their label.
        text = re.sub(r"\[\[(?!one-tree:)([^\[\]|]+)(?:\|([^\[\]]+))?\]\]", lambda m: (m[2] or m[1]).strip(), text)
        def link(match):
            return match[0] if match[2].startswith(("http://", "https://")) else match[1]
        text = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", link, text)
        tables = len(re.findall(r"^\|.*\|\s*$", text, re.M))
        if tables:
            self.gaps["note table lines shown as plain text: no table support"] += tables
        return text

    def notes(self, directory: Path):
        for path in sorted(directory.glob("*/findings.md")):
            profile = path.parent.name
            if not self.known(profile):
                self.gaps["research notes for record subjects or people outside the tree export"] += 1
                continue
            text = path.read_text(encoding="utf-8")
            title = re.search(r"^#\s+(.+)$", text, re.M)
            body = re.sub(r"^#\s+.+\n", "", text, count=1)
            updated = re.search(r"Last updated:\s*(\d{4}-\d{2}-\d{2})", text)
            self.case.add(Study(id=f"glasgow:notes:{profile}", title=(title[1] if title else f"Research notes: {profile}"),
                                body=self.markdown(body), related_ids=[person_id(profile)], status="draft",
                                updated_on=updated[1] if updated else None, sensitivity=PUBLIC))
            self.report["research notes"] += 1


def build_case(project: Path, *, one_tree: Path = ONE_TREE, research: Path = RESEARCH) -> dict:
    if project.exists():
        shutil.rmtree(project)
    initialize_project(project, "Glasgow Surname Project (workbench build)")
    config = ProjectConfig.load(project / "genealogy.toml")
    store = CaseStore(project / config.case_directory)
    case = store.load(config.default_case)
    imported = import_file(project, case, config, one_tree, publish_deceased=True, publish_reviewed_sources=True)
    case = store.load(config.default_case)  # the import saves its own result
    t = Translator(case)
    load = lambda name: json.loads((research / name).read_text(encoding="utf-8"))
    citations = t.records(load("canonical_records.json"))
    t.assessments(load("relationship_assessments.json"), load("relationship_probability_estimates.json")["estimates"], citations)
    t.findings(load("latest-findings.json")["findings"])
    t.notes(research)
    errors = validate_case(case)
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
