"""Opt-in bridge from Glasgow research folders to neutral toolkit bundles.

The established files remain authoritative and are never written here.  The
bridge deliberately omits raw captures, biographies, and Markdown bodies from
the portable case; their names and checksums retain a verifiable link without
duplicating material whose access or licence may be unknown.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping


LEGACY_SCHEMA_VERSION = 1
LEGACY_FILES = (
    "research_state.json",
    "research_plan.json",
    "evidence_index.json",
    "research_brief.md",
    "findings.md",
)


def _json_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError(f"could not read legacy research JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"legacy research JSON must be an object: {path}")
    return value


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _record_id(kind: str, *parts: object) -> str:
    source = "\0".join(str(part) for part in parts)
    return f"glasgow-legacy:{kind}:{_digest(source)[:20]}"


def _artifact_observations(case_directory: Path) -> list[dict[str, Any]]:
    observations: list[dict[str, Any]] = []
    for filename in LEGACY_FILES:
        path = case_directory / filename
        try:
            content = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise ValueError(f"could not read required legacy artifact {path}: {exc}") from exc
        observations.append({
            "filename": filename,
            "bytes": len(content.encode("utf-8")),
            "sha256": _digest(content),
            "sensitivity": "private",
        })
    return observations


def _confidence(value: Any):
    from genealogy.models import Confidence

    normalised = str(value or "").strip().casefold()
    if normalised in {"documented", "direct", "proved", "proven", "confirmed"}:
        return Confidence.DOCUMENTED
    if normalised in {"probable", "strong", "likely"}:
        return Confidence.PROBABLE
    if normalised in {"possible", "tentative", "weak"}:
        return Confidence.POSSIBLE
    if normalised in {"disproved", "rejected", "excluded"}:
        return Confidence.DISPROVED
    return Confidence.UNKNOWN


def _person_id(wikitree_id: str) -> str:
    return f"wikitree:person:{wikitree_id}"


def _profile_records(profiles: Mapping[str, Any]):
    from genealogy.models import (
        Event, ExternalIdentifier, LivingStatus, Name, Person, Place, Sensitivity,
    )

    people: list[Any] = []
    supporting: dict[str, Any] = {}
    for raw_id, raw_profile in sorted(profiles.items()):
        if not isinstance(raw_profile, Mapping):
            raise ValueError(f"legacy evidence profile {raw_id!r} must be an object")
        wikitree_id = str(raw_profile.get("wikitree_id") or raw_id).strip()
        if not wikitree_id:
            raise ValueError("legacy evidence profile has no WikiTree id")
        person_id = _person_id(wikitree_id)
        event_ids: list[str] = []
        for kind, date_key, place_key in (
            ("birth", "birth_date", "birth_location"),
            ("death", "death_date", "death_location"),
        ):
            date = raw_profile.get(date_key)
            place = raw_profile.get(place_key)
            date_text = str(date).strip() if date not in (None, "") else None
            place_text = str(place).strip() if place not in (None, "") else None
            if not date_text and not place_text:
                continue
            place_id = None
            if place_text:
                place_id = _record_id("place", place_text.casefold())
                supporting.setdefault(place_id, Place(
                    id=place_id,
                    name=place_text,
                    sensitivity=Sensitivity.PRIVATE,
                ))
            event_id = _record_id("event", wikitree_id, kind)
            supporting[event_id] = Event(
                id=event_id,
                kind=kind,
                date=date_text,
                date_precision="supplied" if date_text else "unknown",
                place_id=place_id,
                participant_ids=[person_id],
                sensitivity=Sensitivity.PRIVATE,
            )
            event_ids.append(event_id)
        display_name = str(raw_profile.get("display_name") or wikitree_id).strip()
        death = raw_profile.get("death_date")
        living = LivingStatus.DECEASED if death not in (None, "", "0000-00-00") else LivingStatus.UNKNOWN
        people.append(Person(
            id=person_id,
            names=[Name(value=display_name, kind="preferred")],
            event_ids=event_ids,
            external_ids=[ExternalIdentifier(
                system="wikitree",
                value=wikitree_id,
                url=f"https://www.wikitree.com/wiki/{wikitree_id}",
            )],
            living=living,
            sensitivity=Sensitivity.PRIVATE,
        ))
    return people, list(supporting.values())


def _relationship_records(profiles: Mapping[str, Any], person_ids: set[str]):
    from genealogy.models import Confidence, Relationship, Sensitivity

    signatures: set[tuple[str, str, str]] = set()
    records: list[Any] = []
    for raw_id, raw_profile in sorted(profiles.items()):
        if not isinstance(raw_profile, Mapping):
            continue
        current_wt = str(raw_profile.get("wikitree_id") or raw_id)
        current = _person_id(current_wt)
        relations = raw_profile.get("relations", {})
        if not isinstance(relations, Mapping):
            raise ValueError(f"legacy evidence profile {raw_id!r} relations must be an object")
        for relation_name, related_values in relations.items():
            if relation_name not in {"parents", "children", "siblings", "spouses"}:
                continue
            if not isinstance(related_values, list):
                raise ValueError(
                    f"legacy evidence profile {raw_id!r} {relation_name} must be a list"
                )
            for related_value in related_values:
                related = _person_id(str(related_value))
                if current not in person_ids or related not in person_ids or current == related:
                    continue
                if relation_name == "parents":
                    subject, object_id, kind = current, related, "parent"
                elif relation_name == "children":
                    subject, object_id, kind = related, current, "parent"
                else:
                    subject, object_id = sorted((current, related))
                    kind = "sibling" if relation_name == "siblings" else "spouse"
                signature = (subject, object_id, kind)
                if signature in signatures:
                    continue
                signatures.add(signature)
                records.append(Relationship(
                    id=_record_id("relationship", *signature),
                    subject_id=subject,
                    object_id=object_id,
                    kind=kind,
                    confidence=Confidence.UNKNOWN,
                    sensitivity=Sensitivity.PRIVATE,
                ))
    return records


def build_toolkit_research_case(case_directory: Path):
    """Map one complete legacy Glasgow research folder into a neutral case."""
    from genealogy.case import ResearchCase
    from genealogy.models import (
        Citation, Claim, ClaimStatus, Evidence, ExternalIdentifier, Finding,
        ImportProvenance, Name, Person, ResearchQuestion, Sensitivity, Source,
        contains_raw_dna_material,
    )

    state = _json_object(case_directory / "research_state.json")
    plan = _json_object(case_directory / "research_plan.json")
    index = _json_object(case_directory / "evidence_index.json")
    artifacts = _artifact_observations(case_directory)
    for filename, value in (
        ("research_state.json", state),
        ("research_plan.json", plan),
        ("evidence_index.json", index),
    ):
        if value.get("schema_version") != LEGACY_SCHEMA_VERSION:
            raise ValueError(f"unsupported legacy schema in {filename}")
        if contains_raw_dna_material(value):
            raise ValueError(f"raw DNA material cannot enter a toolkit case from {filename}")

    root_id = state.get("root_wikitree_id")
    if not isinstance(root_id, str) or not root_id:
        raise ValueError("legacy research state has no root_wikitree_id")
    if plan.get("case_id") != root_id or index.get("root_wikitree_id") != root_id:
        raise ValueError("legacy research state, plan and evidence index identify different cases")
    profiles = index.get("profiles")
    if not isinstance(profiles, Mapping):
        raise ValueError("legacy evidence index profiles must be an object")

    case = ResearchCase(
        id=f"wikitree-research-{root_id}",
        title=f"WikiTree research case {root_id}",
        summary=str(plan.get("objective") or "Legacy Glasgow research case compatibility handoff."),
        created_at=str(state.get("created_at") or state.get("updated_at") or ""),
        updated_at=str(state.get("updated_at") or state.get("created_at") or ""),
    )
    people, supporting = _profile_records(profiles)
    root_person_id = _person_id(root_id)
    if root_person_id not in {person.id for person in people}:
        people.append(Person(
            id=root_person_id,
            names=[Name(value=root_id, kind="preferred")],
            external_ids=[ExternalIdentifier(system="wikitree", value=root_id)],
            sensitivity=Sensitivity.PRIVATE,
        ))
    for record in [*supporting, *people]:
        case.add(record)
    person_ids = {person.id for person in people}
    for relationship in _relationship_records(profiles, person_ids):
        case.add(relationship)

    questions = plan.get("questions", [])
    if not isinstance(questions, list):
        raise ValueError("legacy research plan questions must be a list")
    for number, item in enumerate(questions, start=1):
        if not isinstance(item, Mapping):
            raise ValueError("legacy research plan questions must contain objects")
        question = str(item.get("question") or "").strip()
        if not question:
            raise ValueError("legacy research question has no question text")
        case.add(ResearchQuestion(
            id=_record_id("question", root_id, item.get("id", number), number),
            question=question,
            related_ids=[root_person_id],
            priority=str(item.get("priority") or "normal"),
            status=str(item.get("status") or "open"),
            sensitivity=Sensitivity.PRIVATE,
        ))

    findings = plan.get("findings", [])
    if not isinstance(findings, list):
        raise ValueError("legacy research plan findings must be a list")
    for number, item in enumerate(findings, start=1):
        if not isinstance(item, Mapping):
            raise ValueError("legacy research plan findings must contain objects")
        conclusion = str(item.get("claim") or item.get("conclusion") or "").strip()
        if not conclusion:
            raise ValueError("legacy research finding has no claim text")
        confidence = _confidence(item.get("confidence"))
        source_values = item.get("sources", [])
        if not isinstance(source_values, list):
            raise ValueError("legacy research finding sources must be a list")
        citation_ids: list[str] = []
        evidence_ids: list[str] = []
        claim_id = _record_id("claim", root_id, number, conclusion)
        for source_number, source_value in enumerate(source_values, start=1):
            source_text = str(source_value).strip()
            if not source_text:
                continue
            source_id = _record_id("source", root_id, number, source_number, source_text)
            citation_id = _record_id("citation", source_id)
            evidence_id = _record_id("evidence", claim_id, citation_id)
            case.add(Source(
                id=source_id,
                title=source_text,
                source_type="legacy-reference",
                url=source_text if source_text.startswith(("http://", "https://")) else None,
                sensitivity=Sensitivity.PRIVATE,
            ))
            case.add(Citation(
                id=citation_id,
                source_id=source_id,
                sensitivity=Sensitivity.PRIVATE,
            ))
            citation_ids.append(citation_id)
            evidence_ids.append(evidence_id)
        case.add(Claim(
            id=claim_id,
            subject_id=root_person_id,
            predicate="research-finding",
            value=conclusion,
            citation_ids=citation_ids,
            status=ClaimStatus.SUPPORTED if citation_ids else ClaimStatus.ASSERTED,
            confidence=confidence,
            sensitivity=Sensitivity.PRIVATE,
        ))
        for citation_id, evidence_id in zip(citation_ids, evidence_ids):
            case.add(Evidence(
                id=evidence_id,
                claim_id=claim_id,
                citation_id=citation_id,
                assessment="Listed as support in the legacy research plan.",
                confidence=confidence,
                sensitivity=Sensitivity.PRIVATE,
            ))
        case.add(Finding(
            id=_record_id("finding", root_id, number, conclusion),
            conclusion=conclusion,
            related_ids=[root_person_id],
            evidence_ids=evidence_ids,
            status=str(item.get("status") or "draft"),
            confidence=confidence,
            sensitivity=Sensitivity.PRIVATE,
        ))

    queue_observation = {
        "kind": "legacy-work-queue",
        "questions": questions,
        "web_searches": plan.get("web_searches", []),
        "targets": plan.get("targets", []),
        "findings": findings,
        "sensitivity": "private",
    }
    if not isinstance(queue_observation["web_searches"], list):
        raise ValueError("legacy research plan web_searches must be a list")
    if not isinstance(queue_observation["targets"], list):
        raise ValueError("legacy research plan targets must be a list")
    provenance = ImportProvenance(
        id=_record_id("import", root_id, *(item["sha256"] for item in artifacts)),
        adapter="glasgow-legacy-research-v1",
        observations=[
            {
                "kind": "legacy-artifact-manifest",
                "schema_version": LEGACY_SCHEMA_VERSION,
                "artifacts": artifacts,
                "capture_count": len(state.get("captures", [])),
                "error_count": len(state.get("errors", [])),
                "omitted_protected_content": [
                    "captures", "profile biographies", "FamilySearch page bodies",
                    "research_brief.md body", "findings.md body",
                ],
                "sensitivity": "private",
            },
            queue_observation,
        ],
        entity_ids=[
            record.id
            for records in case.record_sets.values()
            for record in records
        ],
        sensitivity=Sensitivity.PRIVATE,
    )
    case.add(provenance)
    return case


def write_toolkit_research_bundle(case_directory: Path, bundle_directory: Path):
    """Write and verify an atomic private toolkit bundle from legacy outputs."""
    from genealogy.artifacts import read_case_artifact_bundle, write_case_artifact_bundle

    if case_directory.resolve() == bundle_directory.resolve():
        raise ValueError("toolkit bundle directory must not overwrite the legacy research directory")
    case = build_toolkit_research_case(case_directory)
    paths = write_case_artifact_bundle(case, bundle_directory)
    verified = read_case_artifact_bundle(bundle_directory)
    if verified.to_dict() != case.to_dict():
        raise ValueError("toolkit bundle readback did not match the converted research case")
    return paths
