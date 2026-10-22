#!/usr/bin/env python3
"""Build a genealogy-research-workbench case from Glasgow's maintained research.

The workbench builds a whole site from one ``ResearchCase``. This tool makes
that case from the Glasgow One-Tree export plus the research Glasgow
maintains in its own formats, so the toolkit can rebuild as much of the
Glasgow site as its model can express, and so the gaps can be measured:

- ``research/canonical_records.json``: Source and Citation records, with
  Glasgow's reading of each record as the citation's abstract and its
  source quality in the standard terms where the class is unambiguous;
- ``research/relationship_assessments.json`` and
  ``relationship_probability_estimates.json``: a Claim with Evidence, a
  confidence, an estimate and the basis as the link's reason on the matching
  tree relationship (or a new research relationship when the tree has none),
  for parent, spouse and sibling links. The assessment's limitations go on
  each evidence record. Glasgow's grades (``tools/evidence_labels.py``)
  become the project's own grades, with Glasgow's labels and meanings;
- ``research/latest-findings.json``: dated Finding records, with their
  ``relationship_changes`` as the finding's changes where they agree with
  the current assessment;
- ``research/<profile>/findings.md``: one Study per person, from the sections
  Glasgow publishes (editing logs and captured WikiTree pages stay out);
- ``research/<profile>/presentation.json``: the ``research_tasks`` as
  research questions about that person, and its ``completed_searches`` as
  Search records in the research log;
- ``www/data/people.json``: people the tree export lacks (record subjects
  and newer profiles), with their birth, death, places and family links,
  and the extra profile IDs of merged profiles as former IDs.
  This is Glasgow's public catalogue, so Glasgow's own publication
  decisions already apply to it.

Glasgow's surname variants become ``[names.variants]``, with ``[names] surname``
and ``[site] tree_name`` naming the surname and WikiTree for the catalogue's
menus. ``[site] contact_email`` is never set: Glasgow's contact is not published.

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
from collections import Counter, defaultdict
from datetime import date
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
    Citation, Claim, ClaimStatus, Confidence, Event, Evidence, ExternalIdentifier, Finding, LivingStatus, Name, Person, Place,
    Relationship, ResearchQuestion, Search, Sensitivity, Source, Study,
)

RESEARCH = ROOT / "research"
ONE_TREE = ROOT / "data/exports/one-tree/ONT_Glasgow_2026-08-18T15_43.json"
# The public catalogue: Glasgow's own publication decisions are already applied.
CATALOGUE = ROOT / "www/data/people.json"
DEFAULT_PROJECT = ROOT / "data/private/toolkit-build"
# WikiTree merges Glasgow has followed (old profile ID -> current one).
PROFILE_OVERRIDES = ROOT / "data/wikitree/live-profile-overrides.json"
PUBLIC = Sensitivity.PUBLIC

try:
    from tools.evidence_labels import ALIASES, STATES, TREE_DATA_STATUS, canonical_key  # noqa: E402
    from tools.catalogue_machine_data import GLASGOW_SURNAME_VARIANTS  # noqa: E402
except ModuleNotFoundError:  # run from tools/
    from evidence_labels import ALIASES, STATES, TREE_DATA_STATUS, canonical_key  # noqa: E402
    from catalogue_machine_data import GLASGOW_SURNAME_VARIANTS  # noqa: E402

# Glasgow's research grades (keys of ``evidence_labels.STATES``) and the
# standard workbench grade each counts as. Each becomes a project grade with
# Glasgow's own label and meaning.
GRADES = {"proved": Confidence.DOCUMENTED, "strongly_supported": Confidence.PROBABLE,
          "probable": Confidence.PROBABLE, "possible": Confidence.POSSIBLE,
          "uncertain": Confidence.POSSIBLE, "contradicted": Confidence.DISPROVED}
PARENT_ROLES = {"father", "mother", "parent"}
PARTNER_ROLES = {"husband", "wife", "spouse", "partner"}
SIBLING_ROLES = {"sibling", "brother", "sister"}
SYMMETRIC = {"spouse", "sibling"}
# A relationship change names the relative's role to the subject.
CHANGE_KINDS = {**{role: "parent" for role in PARENT_ROLES}, **{role: "spouse" for role in PARTNER_ROLES},
                **{role: "sibling" for role in SIBLING_ROLES}}
FINDING_STATUS = {"confirmed": "reviewed", "qualified": "qualified"}
PROFILE_ID = re.compile(r"[A-Z][A-Za-z_'’]*(?:-[A-Z][A-Za-z_'’]*)*-\d+")
# Glasgow's ``source_quality`` classes (``evidence_labels.RECORD_QUALITY``) in
# the standard Evidence Explained terms. "secondary" is a published history or
# compilation and "tree_only" a family-tree profile: both authored works.
SOURCE_QUALITY = {"original": "original", "derivative": "derivative", "secondary": "authored", "tree_only": "authored"}


def source_quality(value) -> str | None:
    """The standard term for a Glasgow source quality, or None when it is not clear-cut."""
    text = " ".join(str(value or "").casefold().split())
    if text in SOURCE_QUALITY:
        return SOURCE_QUALITY[text]
    if "original" not in text and re.search(r"\b(?:derivative|transcription|transcript|index|abstract)\b", text):
        return "derivative"
    return None


def surname_variants() -> dict[str, list[str]]:
    """``[names.variants]``: Glasgow's spellings, grouped under Glasgow."""
    return {"Glasgow": sorted(v.capitalize() for v in GLASGOW_SURNAME_VARIANTS if v != "glasgow")}


def iso_date(value: str) -> bool:
    """True for a real date written YYYY, YYYY-MM or YYYY-MM-DD, the workbench's research dates."""
    match = re.fullmatch(r"(\d{4})(?:-(\d{2})(?:-(\d{2}))?)?", value)
    try:
        return bool(match) and bool(date(int(match[1]), int(match[2] or 1), int(match[3] or 1)))
    except ValueError:
        return False


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
        # Person id -> profile IDs it replaced (merged profiles).
        self.former: dict[str, list[str]] = {}

    def grades(self) -> dict[str, dict[str, str]]:
        """The ``[grades]`` table for the grades used, in Glasgow's order."""
        return {key: {"label": state["label"], "meaning": state["meaning"], "confidence": GRADES[key].value}
                for key, state in STATES.items() if key in self.used_grades}

    def pid(self, profile: str | None) -> str | None:
        return self.alias.get(str(profile or "").casefold())

    def known(self, profile: str | None) -> bool:
        return self.pid(profile) is not None

    def relationship(self, kind: str, subject: str, obj: str):
        """The recorded link of ``kind``; spouse and sibling links in either order."""
        return self.relationships.get((kind, subject, obj)) or (
            self.relationships.get((kind, obj, subject)) if kind in SYMMETRIC else None)

    def state(self, value) -> str | None:
        """A Glasgow state as a project grade key, "unknown" when it has no grade.

        None for a word that is not one of Glasgow's states at all (the
        relationship changes' "certain"): ``canonical_key`` would read it as
        unassessed, which would misstate the change.
        """
        text = str(value if value is not None else "").strip()
        key = text.casefold().replace(" ", "_")
        if not (text in TREE_DATA_STATUS or key in STATES or key in ALIASES or key.replace("_", "-") in ALIASES):
            return None
        key = canonical_key(value)
        return key if key in GRADES else Confidence.UNKNOWN.value

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
                self.merged(existing, row.get("profile_ids") or [])
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
            self.merged(new_id, row.get("profile_ids") or [])
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

    def merged(self, person: str, profiles) -> None:
        """Note the profile IDs, other than the person's own, a catalogue row lists."""
        own = person.split(":", 2)[2].casefold()
        for profile in profiles:
            if profile and profile.casefold() != own and profile not in self.former.setdefault(person, []):
                self.former[person].append(profile)

    def wikitree_ids(self) -> None:
        """Every tree person's WikiTree ID as an external identifier, so pages show "Glasgow-123", not the record id.

        The import keeps the export's own identifiers only for some people; the
        profile ID in the record id is the one the site and its readers use.
        """
        for record in self.case.records("Person"):
            if record.id.startswith("one-tree:person:") and not any(i.system == "wikitree" for i in record.external_ids):
                profile = record.id.split(":", 2)[2]
                record.external_ids.insert(0, ExternalIdentifier(system="wikitree", value=profile, url=f"https://www.wikitree.com/wiki/{profile}"))
                self.report["people with a WikiTree identifier"] += 1

    def former_ids(self, redirects=None) -> None:
        """``Person.former_ids`` for public people: merged profiles and WikiTree redirects.

        ``redirects`` maps an old WikiTree ID to the current one. A former ID
        must not be a current record, name a withheld profile or be claimed twice.
        """
        for old, new in (redirects or {}).items():
            if self.known(new) and old.casefold() != str(new).casefold():
                self.merged(self.pid(new), [old])
        current = {record.id for records in self.case.record_sets.values() for record in records}
        people = {record.id: record for record in self.case.records("Person")}
        claimed: set[str] = set()
        for person, profiles in sorted(self.former.items()):
            record = people.get(person)
            for profile in profiles:
                former = person_id(profile)
                if record is None or record.sensitivity is not PUBLIC or self.private(profile):
                    self.gaps["former profile IDs of people who are not public"] += 1
                elif former in current or former in claimed:
                    self.gaps["former profile IDs that are still current records"] += 1
                else:
                    record.former_ids.append(former)
                    claimed.add(former)
                    self.report["former profile IDs kept as redirects"] += 1

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
            quality = source_quality(row.get("source_quality"))
            if row.get("source_quality"):
                if quality:
                    self.report["citations with a source quality"] += 1
                else:
                    self.gaps["source qualities with no clear standard term"] += 1
            citation = Citation(id=f"glasgow:citation:{rid}", source_id=source.id, locator=locator or None,
                                abstract=reading, quality=quality, sensitivity=PUBLIC)
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
            elif all(roles[p] in SIBLING_ROLES for p in pair):
                kind, subject, obj = "sibling", self.pid(pair[0]), self.pid(pair[1])
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
            limitation = " ".join(str(row.get("limitations") or "").split()) or None
            if limitation and self.private(limitation):
                self.gaps["assessment limitations naming a withheld profile, left out"] += 1
                limitation = None
            elif limitation and not cited:
                self.gaps["assessment limitations with no canonical record to attach to"] += 1
            elif limitation:
                self.report["assessment limitations carried on evidence"] += 1
            claim = Claim(id=f"glasgow:claim:{aid}", subject_id=subject, predicate=kind, value=obj,
                          citation_ids=cited, status=ClaimStatus.SUPPORTED if confidence in (
                              Confidence.DOCUMENTED, Confidence.PROBABLE) else ClaimStatus.ASSERTED,
                          confidence=confidence, grade=grade, rationale=row.get("basis"), sensitivity=PUBLIC)
            records = [claim] + [Evidence(id=f"glasgow:evidence:{aid}:{n}", claim_id=claim.id, citation_id=cid,
                                          assessment=row.get("basis") or "Reviewed record.", confidence=confidence,
                                          grade=grade, limitation=limitation, sensitivity=PUBLIC)
                                 for n, cid in enumerate(cited)]
            self.case.add_many(records)
            existing = self.relationship(kind, subject, obj)
            if existing is None:
                existing = Relationship(id=f"glasgow:relationship:{aid}", subject_id=subject, object_id=obj,
                                        kind=kind, sensitivity=PUBLIC)
                self.case.add(existing)
                self.relationships[(kind, subject, obj)] = existing
                self.report["research relationships not in the tree export"] += 1
            existing.confidence, existing.grade = confidence, grade
            existing.rationale = row.get("basis") or existing.rationale
            existing.claim_ids = sorted(set(existing.claim_ids) | {claim.id})
            if aid in percent:
                existing.estimate = percent[aid]
                self.report["relationships with an assessed percentage"] += 1
            self.report["assessed relationships"] += 1
            if kind == "sibling":
                self.report["assessed sibling relationships"] += 1
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
                                  kind=row.get("kind") or None, changes=self.changes(row.get("relationship_changes") or []),
                                  sensitivity=PUBLIC))
            self.report["findings"] += 1
        self.reconcile_changes()

    def changes(self, rows) -> list[dict]:
        """A finding's ``relationship_changes`` as workbench changes to the recorded links.

        The relative is the subject's father, mother, spouse or sibling. Each
        side is a Glasgow state as a grade key; "after" is the assessment's own
        state (``assessment_after``) when the change records one.
        """
        result = []
        for change in rows:
            ends = []
            for side in ("subject", "relative"):
                found = PROFILE_ID.search(str(change.get(side) or ""))
                ends.append(self.pid(change.get(f"{side}_id") or (found[0] if found else None)))
            kind = CHANGE_KINDS.get(str(change.get("relationship") or "").casefold())
            record = self.relationship(kind, *ends) if kind and all(ends) else None
            if record is None:
                self.gaps["finding changes to a link with no relationship record"] += 1
                continue
            before = None if change.get("before") is None else self.state(change["before"])
            after = self.state(change.get("assessment_after") or change.get("after"))
            if after is None or (before is None and change.get("before") is not None):
                self.gaps["finding changes to a state that is not a Glasgow grade ('certain')"] += 1
                continue
            if before == after:
                self.gaps["finding changes with no workbench grade on either side"] += 1
                continue
            note = " ".join(str(change.get("explanation") or "").split()) or None
            if note and self.private(note):
                self.gaps["finding change notes naming a withheld profile, left out"] += 1
                note = None
            result.append({"record_id": record.id, "before": before, "after": after, "note": note})
        return result

    def reconcile_changes(self) -> None:
        """Keep each link's history ending where its assessment now stands.

        The workbench requires a record's latest change (by date; on the same
        date the one recorded last) to end at its current grade or confidence.
        A latest change that disagrees is dropped, and the one before it is
        checked in turn; the assessment itself is never altered.
        """
        assessed = {record.id: record for record in self.case.records("Relationship")}
        history: dict[str, list[tuple[str, int, int, Finding]]] = {}
        for order, finding in enumerate(self.case.records("Finding")):
            for index, change in enumerate(finding.changes):
                history.setdefault(change["record_id"], []).append((finding.recorded_on or "", order, index, finding))
        dropped = set()
        for rid, entries in history.items():
            current = assessed[rid].grade or assessed[rid].confidence.value
            for _, _, index, finding in sorted(entries, key=lambda entry: entry[:3], reverse=True):
                if finding.changes[index]["after"] == current:
                    break
                dropped.add((finding.id, index))
                self.gaps["finding changes that disagree with the current assessment"] += 1
        for finding in self.case.records("Finding"):
            finding.changes = [change for index, change in enumerate(finding.changes) if (finding.id, index) not in dropped]
            for change in finding.changes:
                self.used_grades.update(value for value in (change["before"], change["after"]) if value in GRADES)
                self.report["finding changes to an assessed link"] += 1

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
            # A heading written as a Markdown link ("Findings: [Name](url)") is shown by its words.
            heading = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", title[1]).strip() if title else f"Research notes: {profile}"
            self.case.add(Study(id=f"glasgow:notes:{profile}", title=heading,
                                body=self.markdown(body), related_ids=[self.pid(profile)], status="draft",
                                updated_on=updated[1] if updated else None, sensitivity=PUBLIC))
            self.report["research notes"] += 1


    # -- the catalogue's own groupings -------------------------------------
    def regions(self, people) -> None:
        """``Place.region`` from the region Glasgow files each location under.

        Each catalogue row's ``records`` give a ``record_location`` and the
        ``region`` Glasgow shows for it ("United States", "At Sea"); a row
        filed under one region also files its birth and death locations there.
        A place named exactly as one of those locations takes the region most
        often filed for it. Any other place is filed by its parts, from the
        last: the first part that Glasgow files under one region at least four
        times in five ("USA" or "Ohio" under United States, "Scotland" before
        "United Kingdom") decides, then the first such word for a name written
        without commas; a place with no known part or word keeps the last part
        of its name, as the workbench does.
        """
        tidy = lambda text: " ".join(str(text or "").split())
        filed: dict[str, Counter[str]] = defaultdict(Counter)
        for row in people:
            for record in row.get("records") or []:
                where, region = tidy(record.get("record_location")), tidy(record.get("region"))
                if where and region:
                    filed[where.casefold()][region] += 1
            regions = [tidy(r) for r in row.get("regions") or [] if tidy(r)]
            if len(regions) == 1:
                for key in ("birth_location", "death_location"):
                    if tidy(row.get(key)):
                        filed[tidy(row[key]).casefold()][regions[0]] += 1
        clean = lambda part: part.strip(" .;:()").strip()
        by_part: dict[str, Counter[str]] = defaultdict(Counter)
        by_word: dict[str, Counter[str]] = defaultdict(Counter)
        for where, counts in filed.items():
            for part in {clean(part) for part in where.split(",") if clean(part)}:
                by_part[part].update(counts)
                for word in {clean(w) for w in part.split() if clean(w)}:
                    by_word[word].update(counts)

        def decided(counts: Counter[str] | None) -> str | None:
            if not counts:
                return None
            region, n = counts.most_common(1)[0]
            return region if n * 5 >= sum(counts.values()) * 4 else None

        for place in self.case.records("Place"):
            if place.region:
                continue
            name = tidy(place.name).casefold()
            region = decided(filed.get(name)) or (filed[name].most_common(1)[0][0] if filed.get(name) else None)
            how = "named"
            if not region:
                parts = [clean(part) for part in name.split(",") if clean(part)]
                region = next((r for part in reversed(parts) if (r := decided(by_part.get(part)))), None)
                how = "by a part of the name"
            if not region:  # a name written without commas: "Anstruther Wester Fife Scotland"
                words = [clean(w) for w in name.replace(",", " ").split() if clean(w)]
                region = next((r for word in reversed(words) if (r := decided(by_word.get(word)))), None)
                how = "by a word of the name"
            if region:
                place.region = region
                self.report[f"places filed under a catalogue region ({how})"] += 1

    def groups(self, people) -> None:
        """Each catalogue cluster ("Possible group") as a Study of kind ``group`` naming its public members.

        Membership says who the catalogue files together, never that they
        are kin; a cluster with no public member is left out.
        """
        members: dict[str, list[str]] = defaultdict(list)
        for row in people:
            keys = [k for k in [*row.get("profile_ids", []), row.get("catalogue_id")] if k]
            pid = next((self.pid(k) for k in keys if self.known(k)), None)
            if not pid:
                continue
            for name in dict.fromkeys(" ".join(str(c).split()) for c in [*(row.get("clusters") or []), row.get("cluster")] if c):
                if pid not in members[name]:
                    members[name].append(pid)
        for name, pids in sorted(members.items()):
            if self.private(name):
                self.gaps["catalogue groups naming a withheld profile"] += 1
                continue
            self.case.add(Study(id=f"glasgow:group:{_short(name)}", title=name, kind="group", related_ids=pids, status="published",
                                summary=f"The {len(pids)} people the catalogue files under this group. Being filed together says they are studied "
                                        "together, not that they are kin.", sensitivity=PUBLIC))
            self.report["catalogue groups"] += 1

    # -- research questions ----------------------------------------------
    def questions(self, directory: Path):
        """Each ``research_tasks`` entry of a presentation as a question about its person.

        ``what`` is the task, ``resolves`` (else ``tests``) what would answer it,
        ``record_target`` the next record; ``matters`` has no field of its own,
        so it closes the question as "Why it matters: …". A task whose status
        begins "Completed" is resolved; the rest stay open.

        Each ``completed_searches`` entry becomes a Search in the research
        log, about the same person: ``search`` and ``result`` as written,
        ``date`` as ``searched_on`` when it is an ISO date. A search about a
        person who is not public, or whose text names a withheld profile, is
        left out and counted.
        """
        for path in sorted(directory.glob("*/presentation.json")):
            profile = path.parent.name
            data = json.loads(path.read_text(encoding="utf-8"))
            tasks = [task for task in data.get("research_tasks") or [] if isinstance(task, dict) and task.get("what")]
            self.searches(profile, data.get("completed_searches") or [])
            if not tasks:
                continue
            if not self.known(profile):
                self.gaps["research questions about people who are not public"] += len(tasks)
                continue
            for n, task in enumerate(tasks, 1):
                if self.private(json.dumps(task, ensure_ascii=False)):
                    self.gaps["research questions naming a withheld profile"] += 1
                    continue
                text = " ".join(re.sub(r"^\d+\.\s+", "", str(task["what"])).split())
                if task.get("matters"):
                    text += " Why it matters: " + " ".join(str(task["matters"]).split())
                done = str(task.get("status") or "").casefold().startswith("completed")
                self.case.add(ResearchQuestion(
                    id=f"glasgow:question:{profile}:{n}", question=text, related_ids=[self.pid(profile)],
                    status="resolved" if done else "open", resolves=task.get("resolves") or task.get("tests") or None,
                    next_record=task.get("record_target") or None, sensitivity=PUBLIC))
                self.report["research questions" + (" (resolved)" if done else " (open)")] += 1

    def searches(self, profile: str, rows) -> None:
        """A presentation's ``completed_searches`` as Search records about ``profile``."""
        rows = [row for row in rows if isinstance(row, dict)]
        if rows and not self.known(profile):
            self.gaps["completed searches about people who are not public"] += len(rows)
            return
        for n, row in enumerate(rows, 1):
            search, result, limit = (" ".join(str(row.get(key) or "").split()) for key in ("search", "result", "limitation"))
            if self.private(search) or self.private(result) or self.private(limit):
                self.gaps["completed searches naming a withheld profile"] += 1
                continue
            if not search or not result:
                self.gaps["completed searches with no search or no result recorded"] += 1
                continue
            when = str(row.get("date") or "").strip()
            when = when if iso_date(when) else None
            self.case.add(Search(id=f"glasgow:search:{profile}:{n}", search=search, result=result,
                                 related_ids=[self.pid(profile)], searched_on=when, limitation=limit or None, sensitivity=PUBLIC))
            self.report["completed searches in the research log" + ("" if when else " (undated)")] += 1


def config_tables(grades: dict) -> str:
    """The tables appended to the starter ``genealogy.toml``: the site's tree, the surname and its variants, and the grades used.

    Glasgow's record roles have no reader labels or cautions of their own
    (evidence_labels.RECORD_EVIDENCE describes record links, not record
    types), so there is no [source_types] table. [site] contact_email stays
    unset: Glasgow does not publish its contact address. The catalogue's
    "Glasgow at birth" and "Women who married a Glasgow" checks, and its
    WikiTree menu and example ID, take their names from surname and tree_name.
    """
    text = '\n[site]\ntree_name = "WikiTree"\n\n[names]\nsurname = "Glasgow"\n'
    text += "\n[names.variants]\n" + "".join(f"{json.dumps(canonical)} = {json.dumps(spellings)}\n"
                                            for canonical, spellings in surname_variants().items())
    for key, grade in grades.items():
        text += f"\n[grades.{key}]\n" + "".join(f"{name} = {json.dumps(grade[name], ensure_ascii=False)}\n"
                                                 for name in ("label", "meaning", "confidence"))
    return text


def build_case(project: Path, *, one_tree: Path = ONE_TREE, research: Path = RESEARCH, catalogue: Path = CATALOGUE) -> dict:
    missing = [str(path) for path in (one_tree, catalogue, research) if not path.exists()]
    if missing:  # local, Git-ignored inputs: check before replacing the project
        raise FileNotFoundError("missing inputs: " + ", ".join(missing))
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
    rows = json.loads(catalogue.read_text(encoding="utf-8"))["people"]
    t.catalogue(rows)
    t.regions(rows)
    t.groups(rows)
    citations = t.records(load("canonical_records.json"))
    t.assessments(load("relationship_assessments.json"), load("relationship_probability_estimates.json")["estimates"], citations)
    t.findings(load("latest-findings.json")["findings"])
    t.questions(research)
    redirects = {}
    if PROFILE_OVERRIDES.exists():
        try:
            from tools.project_paths import normalized_profile_redirects
        except ModuleNotFoundError:
            from project_paths import normalized_profile_redirects
        redirects = normalized_profile_redirects(json.loads(PROFILE_OVERRIDES.read_text(encoding="utf-8")).get("redirects", {}))
    t.former_ids(redirects)
    t.wikitree_ids()
    try:
        from tools.build_research_catalog import _load_research_findings
    except ModuleNotFoundError:
        from build_research_catalog import _load_research_findings
    t.notes(research, lambda profile: _load_research_findings([profile]))
    with (project / "genealogy.toml").open("a", encoding="utf-8") as handle:
        handle.write(config_tables(t.grades()))
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
