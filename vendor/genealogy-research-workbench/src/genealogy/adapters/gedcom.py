"""A deliberately small GEDCOM normaliser for INDI and FAM records."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from .base import Adapter, AdapterBatch, AdapterRecord
from ._mapping import place_and_event, record_id
from ..models import (
    Citation, Claim, ClaimStatus, Evidence, Event, ExternalIdentifier, Name,
    Person, Record, Relationship, Sensitivity, Source,
)


class GedcomAdapter(Adapter):
    name = "gedcom"
    capabilities = frozenset({"ingest", "gedcom", "people", "relationships", "events", "places"})

    def ingest(self, payload: Any) -> AdapterBatch:
        if isinstance(payload, bytes):
            payload = payload.decode("utf-8-sig")
        if not isinstance(payload, str):
            raise TypeError("GEDCOM payload must be text or UTF-8 bytes")
        grouped: dict[str, list[str]] = defaultdict(list)
        kinds: dict[str, str] = {}
        current: str | None = None
        for line in payload.splitlines():
            parts = line.strip().split(maxsplit=2)
            if parts and parts[0] == "0":
                current = None
            if len(parts) >= 3 and parts[0] == "0" and parts[1].startswith("@"):
                current = parts[1].strip("@")
                kinds[current] = parts[2].upper()
            if current:
                grouped[current].append(line.rstrip())
        batch = AdapterBatch(adapter=self.name)
        known_sources = {identifier for identifier, kind in kinds.items() if kind == "SOUR"}
        for identifier, lines in grouped.items():
            kind = kinds.get(identifier, "")
            entity_type = (
                "person" if kind == "INDI" else "family" if kind == "FAM"
                else "source" if kind == "SOUR" else "record"
            )
            batch.records.append(AdapterRecord(
                self.external_id(identifier), entity_type, {"gedcom_lines": lines}, Sensitivity.PRIVATE,
                raw=list(lines), provenance={"adapter": self.name, "gedcom_record": identifier, "format": "GEDCOM"},
            ))
            if kind == "INDI":
                entities, missing_sources = self._individual(identifier, lines, known_sources)
                batch.extend_entities(entities)
                batch.warnings.extend(
                    f"GEDCOM individual {identifier} references missing source {source_id}"
                    for source_id in missing_sources
                )
            elif kind == "FAM":
                batch.extend_entities(self._family(identifier, lines))
            elif kind == "SOUR":
                batch.add_entity(self._source(identifier, lines))
        if not batch.records:
            batch.warnings.append("no level-0 GEDCOM records found")
        return batch

    def _individual(
        self,
        identifier: str,
        lines: list[str],
        known_sources: set[str],
    ) -> tuple[list[Record], list[str]]:
        person_id = record_id(self.name, "person", identifier)
        names = [value.replace("/", "").strip() for value in self._all_values(lines, "NAME")]
        person = Person(
            id=person_id,
            names=[
                Name(value=value, kind="birth" if index == 0 else "alias")
                for index, value in enumerate(names)
                if value
            ],
            external_ids=[ExternalIdentifier(system=self.name, value=identifier)],
            sensitivity=Sensitivity.PRIVATE,
        )
        entities: list[Record] = [person]
        for tag, event_kind in (("BIRT", "birth"), ("DEAT", "death")):
            date, place = self._event_values(lines, tag)
            event_entities = place_and_event(self.name, person_id, identifier, event_kind, date, place, Sensitivity.PRIVATE)
            person.event_ids.extend(entity.id for entity in event_entities if hasattr(entity, "kind") and getattr(entity, "kind") == event_kind)
            entities.extend(event_entities)
        if self._event_values(lines, "DEAT") != (None, None) or any(
            len(parts := line.strip().split(maxsplit=2)) >= 2 and parts[1].upper() == "DEAT"
            for line in lines
        ):
            person.living = False
        sex = self._first_value(lines, "SEX")
        if sex:
            entities.append(Claim(
                id=record_id(self.name, "claim", f"{identifier}:sex"),
                subject_id=person_id,
                predicate="sex",
                value=sex,
                sensitivity=Sensitivity.PRIVATE,
            ))
        missing_sources: list[str] = []
        for number, (source_id, locator) in enumerate(self._source_references(lines), start=1):
            if source_id not in known_sources:
                missing_sources.append(source_id)
                continue
            source_record_id = record_id(self.name, "source", source_id)
            citation_id = record_id(self.name, "citation", f"{identifier}:{number}")
            claim_id = record_id(self.name, "claim", f"{identifier}:source:{number}")
            evidence_id = record_id(self.name, "evidence", f"{identifier}:source:{number}")
            entities.extend((
                Citation(
                    id=citation_id, source_id=source_record_id, locator=locator,
                    sensitivity=Sensitivity.PRIVATE,
                ),
                Claim(
                    id=claim_id, subject_id=person_id, predicate="documented-in",
                    value=source_record_id, citation_ids=[citation_id],
                    status=ClaimStatus.SUPPORTED, sensitivity=Sensitivity.PRIVATE,
                ),
                Evidence(
                    id=evidence_id, claim_id=claim_id, citation_id=citation_id,
                    assessment="GEDCOM source citation", sensitivity=Sensitivity.PRIVATE,
                ),
            ))
        return entities, missing_sources

    def _family(self, identifier: str, lines: list[str]) -> list[Record]:
        husband = self._first_value(lines, "HUSB")
        wife = self._first_value(lines, "WIFE")
        children = self._all_values(lines, "CHIL")
        members = {role: value.strip("@") for role, value in (("husband", husband), ("wife", wife)) if value}
        entities: list[Record] = []
        if husband and wife:
            entities.append(Relationship(
                id=record_id(self.name, "relationship", f"{identifier}:spouse"),
                subject_id=record_id(self.name, "person", husband.strip("@")),
                object_id=record_id(self.name, "person", wife.strip("@")), kind="spouse",
                sensitivity=Sensitivity.PRIVATE,
            ))
        for child in children:
            child_id = record_id(self.name, "person", child.strip("@"))
            for role in ("husband", "wife"):
                if role in members:
                    entities.append(Relationship(
                        id=record_id(self.name, "relationship", f"{identifier}:parent:{child.strip('@')}:{role}"),
                        subject_id=child_id, object_id=record_id(self.name, "person", members[role]), kind="parent",
                        sensitivity=Sensitivity.PRIVATE,
                    ))
        participants = [
            record_id(self.name, "person", value.strip("@"))
            for value in (husband, wife)
            if value
        ]
        date, place = self._event_values(lines, "MARR")
        if date or place:
            marriage = place_and_event(
                self.name,
                participants[0] if participants else "",
                identifier,
                "marriage",
                date,
                place,
                Sensitivity.PRIVATE,
            )
            for entity in marriage:
                if isinstance(entity, Event):
                    entity.participant_ids = participants
            entities.extend(marriage)
        return entities

    def _source(self, identifier: str, lines: list[str]) -> Source:
        title = self._first_value(lines, "TITL") or self._first_value(lines, "ABBR") or identifier
        repository = self._first_value(lines, "REPO")
        return Source(
            id=record_id(self.name, "source", identifier),
            title=title,
            source_type="gedcom-source",
            repository=repository.strip("@") if repository else None,
            external_ids=[ExternalIdentifier(system=self.name, value=identifier)],
            sensitivity=Sensitivity.PRIVATE,
        )

    @staticmethod
    def _source_references(lines: list[str]) -> list[tuple[str, str | None]]:
        references: list[tuple[str, str | None]] = []
        for index, line in enumerate(lines):
            parts = line.strip().split(maxsplit=2)
            if len(parts) != 3 or parts[0] != "1" or parts[1].upper() != "SOUR":
                continue
            source_id = parts[2].strip("@")
            locator = None
            for child in lines[index + 1:]:
                child_parts = child.strip().split(maxsplit=2)
                if len(child_parts) < 2 or int(child_parts[0]) <= 1:
                    break
                if len(child_parts) == 3 and child_parts[1].upper() == "PAGE":
                    locator = child_parts[2]
            references.append((source_id, locator))
        return references

    @staticmethod
    def _first_value(lines: list[str], tag: str) -> str | None:
        values = GedcomAdapter._all_values(lines, tag)
        return values[0] if values else None

    @staticmethod
    def _all_values(lines: list[str], tag: str) -> list[str]:
        values: list[str] = []
        for line in lines:
            parts = line.strip().split(maxsplit=2)
            if len(parts) == 3 and parts[1].upper() == tag:
                values.append(parts[2])
        return values

    @staticmethod
    def _event_values(lines: list[str], tag: str) -> tuple[str | None, str | None]:
        for index, line in enumerate(lines):
            parts = line.strip().split(maxsplit=2)
            if len(parts) < 2 or parts[1].upper() != tag:
                continue
            level = int(parts[0])
            date = place = None
            for child in lines[index + 1:]:
                child_parts = child.strip().split(maxsplit=2)
                if len(child_parts) < 2:
                    continue
                child_level = int(child_parts[0])
                if child_level <= level:
                    break
                if len(child_parts) == 3 and child_parts[1].upper() == "DATE":
                    date = child_parts[2]
                if len(child_parts) == 3 and child_parts[1].upper() == "PLAC":
                    place = child_parts[2]
            return date, place
        return None, None
