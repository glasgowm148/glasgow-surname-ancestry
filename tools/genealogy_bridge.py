"""Explicit, non-mutating bridge from a supplied legacy One-Tree JSON file.

This is deliberately not part of any catalogue, synchronisation, or research
refresh command.  It reads only the JSON path supplied by the caller and writes
only paths supplied explicitly on the command line.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Any, Iterable, Mapping

from genealogy.adapters import OneTreeAdapter
from genealogy.case import CaseStore, ResearchCase
from genealogy.config import ProjectConfig
from genealogy.exports import project_for_public_export
from genealogy.models import (
    AccessLevel,
    Citation,
    Claim,
    ClaimStatus,
    Confidence,
    Evidence,
    Finding,
    Record,
    Relationship,
    ResearchQuestion,
    Source,
)
from genealogy.privacy import PrivacyPolicy


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "genealogy.toml"


def _rows(payload: Mapping[str, Any], section: str) -> list[dict[str, Any]]:
    value = payload.get(section, [])
    if not isinstance(value, list) or not all(isinstance(row, Mapping) for row in value):
        raise ValueError(f"legacy JSON {section!r} must be a list of objects")
    return [dict(row) for row in value]


def load_legacy_json(path: Path) -> dict[str, Any]:
    """Read a caller-selected legacy interchange file; never discover inputs."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"invalid legacy JSON: {path}") from error
    if not isinstance(payload, dict):
        raise ValueError("legacy JSON must be an object with a relationships list")
    wrapped = payload.get("data")
    if isinstance(wrapped, Mapping):
        if not all(isinstance(row, Mapping) for row in wrapped.values()):
            raise ValueError("legacy One-Tree data wrapper must map ids to objects")
    else:
        _rows(payload, "relationships")
    return payload


def legacy_access_level(row: Mapping[str, Any]) -> AccessLevel:
    """Translate legacy flags once, conservatively, into toolkit access levels."""
    levels: list[AccessLevel] = []
    explicit = row.get("sensitivity", row.get("access_level"))
    if explicit is not None:
        try:
            levels.append(AccessLevel(explicit))
        except ValueError as error:
            raise ValueError(f"unknown legacy access level: {explicit!r}") from error
    for key, level in (
        ("raw_dna", AccessLevel.RAW_DNA),
        ("raw_sensitive", AccessLevel.RAW_DNA),
        ("licensed_source", AccessLevel.LICENSED),
        ("licensed", AccessLevel.LICENSED),
        ("restricted", AccessLevel.RESTRICTED),
    ):
        if key in row:
            if type(row[key]) is not bool:
                raise ValueError(f"legacy privacy flag {key} must be a boolean")
            if row[key]:
                levels.append(level)
    privacy = row.get("Privacy", row.get("privacy"))
    if privacy is not None:
        try:
            levels.append(AccessLevel.PUBLIC if int(str(privacy)) >= 50 else AccessLevel.RESTRICTED)
        except (TypeError, ValueError) as error:
            raise ValueError(f"legacy Privacy must be numeric: {privacy!r}") from error
    # Older export rows used this explicit marker instead of an access level.
    if "historical" in row:
        if type(row["historical"]) is not bool:
            raise ValueError("legacy privacy flag historical must be a boolean")
        if row["historical"]:
            levels.append(AccessLevel.PUBLIC)
    if not levels:
        return AccessLevel.PRIVATE
    rank = {
        AccessLevel.PUBLIC: 0,
        AccessLevel.RESTRICTED: 1,
        AccessLevel.LICENSED: 2,
        AccessLevel.PRIVATE: 3,
        AccessLevel.RAW_DNA: 4,
    }
    return max(levels, key=rank.__getitem__)


def _adapter_row(row: Mapping[str, Any], *, entity_type: str | None = None) -> dict[str, Any]:
    """Preserve One-Tree fields for the adapter unless a legacy flag needs conversion."""
    converted = dict(row)
    if entity_type is not None:
        converted["entity_type"] = entity_type
    legacy_access_keys = {
        "sensitivity", "access_level", "raw_dna", "raw_sensitive", "licensed_source",
        "licensed", "restricted", "historical",
    }
    if legacy_access_keys.intersection(row):
        converted["sensitivity"] = legacy_access_level(row)
    return converted


def _reject_raw_legacy_material(payload: Mapping[str, Any]) -> None:
    """Keep raw DNA out before a provider wrapper can discard its legacy flag."""
    forbidden = (
        "rawdna", "rawsensitive", "rawgenetic", "genotype", "segment",
        "vcf", "bam", "fastq", "allele",
    )

    def inspect(value: Any) -> None:
        if isinstance(value, Mapping):
            for key, child in value.items():
                normalised = re.sub(r"[^a-z0-9]", "", str(key).casefold())
                if any(token in normalised for token in forbidden):
                    raise ValueError("raw DNA material cannot be imported into a portable case")
                inspect(child)
        elif isinstance(value, list):
            for child in value:
                inspect(child)

    inspect(payload)
    for section in ("people", "relationships", "sources", "citations", "claims", "evidence"):
        for row in _rows(payload, section):
            if legacy_access_level(row) is AccessLevel.RAW_DNA:
                raise ValueError("raw DNA material cannot be imported into a portable case")


def _wrapped_people(payload: Mapping[str, Any]) -> list[dict[str, Any]] | None:
    """Return One-Tree wrapper rows, retaining their provider field names."""
    data = payload.get("data")
    if not isinstance(data, Mapping):
        return None
    result: list[dict[str, Any]] = []
    for fallback, row in data.items():
        if not isinstance(row, Mapping):
            raise ValueError("legacy One-Tree data wrapper must map ids to objects")
        converted = dict(row)
        if not any(str(key).casefold() in {"name", "profile_id", "id"} for key in converted):
            converted["profile_id"] = str(fallback)
        result.append(converted)
    return result


def _id(row: Mapping[str, Any], section: str) -> str:
    value = row.get("id", row.get("external_id"))
    if isinstance(value, bool) or not isinstance(value, (str, int)) or not str(value):
        raise ValueError(f"legacy {section} row needs a non-empty id")
    return str(value)


def _adapter_external_id(row: Mapping[str, Any]) -> str:
    """Mirror the One-Tree adapter's provider-identity selection."""
    for wanted in ("name", "profile_id", "id"):
        for key, value in row.items():
            if str(key).casefold() == wanted and isinstance(value, (str, int)) and not isinstance(value, bool):
                text = str(value).strip()
                if text:
                    return text
    raise ValueError("legacy person row needs Name, profile_id, or id")


def _confidence(value: Any) -> Confidence:
    return Confidence(value if value is not None else Confidence.UNKNOWN)


def _auxiliary_entities(payload: Mapping[str, Any], person_ids: Mapping[str, str]) -> Iterable[Record]:
    """Normalise non-One-Tree records needed to interpret One-Tree edges."""
    for row in _rows(payload, "sources"):
        title = row.get("title")
        if not isinstance(title, str) or not title:
            raise ValueError("legacy source row needs a title")
        yield Source(
            id=_id(row, "sources"), title=title, source_type=str(row.get("source_type", "unknown")),
            repository=row.get("repository"), url=row.get("url"), licence=row.get("licence"),
            sensitivity=legacy_access_level(row),
        )
    for row in _rows(payload, "citations"):
        source_id = row.get("source_id")
        if not isinstance(source_id, str) or not source_id:
            raise ValueError("legacy citation row needs source_id")
        yield Citation(id=_id(row, "citations"), source_id=source_id, locator=row.get("locator"),
                       quotation=row.get("quotation"), sensitivity=legacy_access_level(row))
    for row in _rows(payload, "claims"):
        subject_id, predicate, value = row.get("subject_id"), row.get("predicate"), row.get("value")
        if not all(isinstance(item, str) and item for item in (subject_id, predicate, value)):
            raise ValueError("legacy claim row needs subject_id, predicate and value")
        citations = row.get("citation_ids", [])
        if not isinstance(citations, list) or not all(isinstance(item, str) for item in citations):
            raise ValueError("legacy claim citation_ids must be a list of ids")
        yield Claim(
            id=_id(row, "claims"), subject_id=person_ids.get(subject_id, subject_id), predicate=predicate, value=value,
            citation_ids=citations, status=ClaimStatus(row.get("status", "asserted")),
            confidence=_confidence(row.get("confidence")), sensitivity=legacy_access_level(row),
        )
    for row in _rows(payload, "evidence"):
        claim_id, citation_id, assessment = row.get("claim_id"), row.get("citation_id"), row.get("assessment")
        if not all(isinstance(item, str) and item for item in (claim_id, citation_id, assessment)):
            raise ValueError("legacy evidence row needs claim_id, citation_id and assessment")
        yield Evidence(
            id=_id(row, "evidence"), claim_id=claim_id, citation_id=citation_id, assessment=assessment,
            supports=_exact_bool(row.get("supports", True), "legacy evidence supports"),
            confidence=_confidence(row.get("confidence")),
            sensitivity=legacy_access_level(row),
        )
    for row in _rows(payload, "questions"):
        question = row.get("question")
        if not isinstance(question, str) or not question:
            raise ValueError("legacy question row needs a question")
        yield ResearchQuestion(id=_id(row, "questions"), question=question,
                               sensitivity=legacy_access_level(row))
    for row in _rows(payload, "findings"):
        conclusion = row.get("conclusion")
        if not isinstance(conclusion, str) or not conclusion:
            raise ValueError("legacy finding row needs a conclusion")
        yield Finding(id=_id(row, "findings"), conclusion=conclusion,
                      sensitivity=legacy_access_level(row))


def normalise_legacy_onetree(payload: Mapping[str, Any], *, case_id: str = "legacy-onetree") -> ResearchCase:
    """Make a durable case from an explicitly supplied legacy One-Tree payload.

    The relationship conversion must come from ``AdapterBatch.entities``.  Raw
    adapter observations are provenance, not neutral entities, so a toolkit
    lacking entities fails closed rather than silently accepting them.
    """
    wrapped_people = _wrapped_people(payload)
    people = wrapped_people if wrapped_people is not None else _rows(payload, "people")
    relationships = _rows(payload, "relationships")
    raw_scan_payload = dict(payload, people=people)
    _reject_raw_legacy_material(raw_scan_payload)
    case = ResearchCase(id=case_id, title=str(payload.get("title", "Legacy One-Tree import")))
    # The adapter supplies the canonical person and edge identifiers.  Keeping
    # both row kinds in one batch makes relationship dependencies unambiguous.
    if wrapped_people is not None:
        adapter_payload: Any = payload
    else:
        adapter_payload = [_adapter_row(row, entity_type="person") for row in people]
        adapter_payload.extend(_adapter_row(row) for row in relationships)
    batch = OneTreeAdapter().ingest(adapter_payload)
    entities = getattr(batch, "entities", None)
    if not isinstance(entities, list):
        raise RuntimeError("toolkit OneTreeAdapter did not provide AdapterBatch.entities")
    relationship_entities = [entity for entity in entities if isinstance(entity, Relationship)]
    has_embedded_relationship = any(
        any(str(key).casefold() in {"father", "father_id", "mother", "mother_id"} for key in row)
        for row in people
    )
    if (relationships or has_embedded_relationship) and not relationship_entities:
        raise RuntimeError("OneTreeAdapter produced no neutral relationship entities for non-empty input")
    person_ids: dict[str, str] = {}
    for row in people:
        external_id = _adapter_external_id(row)
        canonical_id = f"one-tree:person:{external_id}"
        person_ids[external_id] = canonical_id
        for key, value in row.items():
            if str(key).casefold() in {"id", "external_id", "profile_id"}:
                person_ids[str(value)] = canonical_id
    for entity in _auxiliary_entities(payload, person_ids):
        case.add(entity)
    batch.add_to_case(case)
    return case


def privacy_policy(config: ProjectConfig) -> PrivacyPolicy:
    """Use the toolkit's single fail-closed policy for every bridge export."""
    return PrivacyPolicy(
        allow_living=config.boolean("privacy", "allow_living", False),
        allow_licensed=config.boolean("privacy", "allow_licensed", False),
        allow_restricted=config.boolean("privacy", "allow_restricted", False),
    )


def _exact_bool(value: Any, setting: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{setting} must be a boolean")
    return value


def export_legacy_onetree(input_path: Path, output_path: Path, *, config_path: Path = CONFIG_PATH) -> Path:
    """Write a JSON public projection, only to the caller-selected output path."""
    if input_path.resolve() == output_path.resolve():
        raise ValueError("refusing to overwrite the legacy input")
    config = ProjectConfig.load(config_path)
    case = normalise_legacy_onetree(load_legacy_json(input_path))
    # The canonical builder validates first and applies the toolkit privacy policy.
    safe = project_for_public_export(case, config)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(safe, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output_path


def save_legacy_case(input_path: Path, output_directory: Path, *, config_path: Path = CONFIG_PATH) -> Path:
    """Save a local case only when a caller explicitly selected its directory."""
    ProjectConfig.load(config_path)  # validates the project boundary before writing
    case = normalise_legacy_onetree(load_legacy_json(input_path))
    return CaseStore(output_directory).save(case)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="explicit legacy One-Tree JSON input")
    outputs = parser.add_mutually_exclusive_group(required=True)
    outputs.add_argument("--export-output", type=Path, help="explicit public JSON output")
    outputs.add_argument("--case-directory", type=Path, help="explicit local durable-case directory")
    args = parser.parse_args(argv)
    try:
        if args.export_output:
            export_legacy_onetree(args.input, args.export_output)
            print(f"Wrote privacy-filtered export to {args.export_output}")
        else:
            saved = save_legacy_case(args.input, args.case_directory)
            print(f"Wrote local case to {saved}")
        return 0
    except (OSError, RuntimeError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
