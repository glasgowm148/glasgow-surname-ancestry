"""Constrained mapping for one-tree relationship exports and profile wrappers."""

from collections.abc import Mapping
from typing import Any

from ._mapping import MappingAdapter, input_sensitivity, person_entities, record_id, text, value_for
from .base import AdapterBatch, AdapterRecord
from ..models import Record, Relationship, Sensitivity


class OneTreeAdapter(MappingAdapter):
    name = "one-tree"
    entity_type = "relationship"
    capabilities = frozenset({"ingest", "row-mapping", "relationships", "people"})

    def ingest(self, payload: Any) -> AdapterBatch:
        """Handle both individual rows and ``{data: {key: profile}}`` exports."""
        wrapped = isinstance(payload, Mapping) and isinstance(payload.get("data"), Mapping)
        source_rows = payload["data"] if wrapped else payload
        if isinstance(source_rows, Mapping):
            rows = list(source_rows.items()) if wrapped else [(None, source_rows)]
        else:
            rows = [(None, row) for row in source_rows]
        id_to_profile: dict[str, str] = {}
        for fallback, row in rows:
            if isinstance(row, Mapping):
                external = text(value_for(row, "name", "profile_id", "id")) or text(fallback)
                numeric = text(value_for(row, "id"))
                if external and numeric:
                    id_to_profile[numeric] = external
        batch = AdapterBatch(adapter=self.name)
        for number, (fallback, row) in enumerate(rows, start=1):
            if not isinstance(row, Mapping):
                raise TypeError("One-Tree payload rows must be mappings")
            raw, data = dict(row), dict(row)
            external_value = text(value_for(data, "name", "profile_id", "id")) or text(fallback) or str(number)
            entity_type = text(value_for(data, "entity_type")) or ("relationship" if self._is_relation(data) else "person")
            sensitivity = _provider_sensitivity(data, Sensitivity.PRIVATE)
            batch.records.append(AdapterRecord(
                self.external_id(external_value, text(value_for(data, "url"))), entity_type, data, sensitivity,
                raw=raw, provenance={"adapter": self.name, "row": number, "wrapper": wrapped},
            ))
            batch.extend_entities(self.normalise_row(external_value, data, entity_type, sensitivity, id_to_profile))
        return batch

    @staticmethod
    def _is_relation(data: Mapping[str, Any]) -> bool:
        return bool(value_for(data, "subject_id", "person_id", "child_id", "from_id", "object_id", "relative_id", "parent_id", "to_id"))

    def normalise_row(self, external_value: str, data: dict, entity_type: str, sensitivity: Sensitivity, id_to_profile: Mapping[str, str] | None = None) -> list[Record]:
        id_to_profile = id_to_profile or {}
        if entity_type == "person":
            entity_data = _with_living_from_death(data)
            entities = person_entities(self.name, external_value, entity_data, sensitivity)
            for role in ("father", "mother"):
                related = _profile_value(text(value_for(data, role, f"{role}_id")), id_to_profile)
                if related:
                    entities.append(Relationship(id=record_id(self.name, "relationship", f"{external_value}:{role}"), subject_id=record_id(self.name, "person", external_value), object_id=record_id(self.name, "person", related), kind="parent", sensitivity=sensitivity))
            return entities
        subject = text(value_for(data, "subject_id", "person_id", "child_id", "from_id"))
        object_ = text(value_for(data, "object_id", "relative_id", "parent_id", "to_id"))
        kind = text(value_for(data, "relationship", "relationship_type", "kind", "type"))
        if subject and object_ and kind:
            return [Relationship(id=record_id(self.name, "relationship", external_value), subject_id=record_id(self.name, "person", _profile_value(subject, id_to_profile)), object_id=record_id(self.name, "person", _profile_value(object_, id_to_profile)), kind=kind.casefold(), sensitivity=sensitivity)]
        return []


def _profile_value(value: str | None, id_to_profile: Mapping[str, str]) -> str:
    return id_to_profile.get(value or "", value or "")


def _with_living_from_death(data: Mapping[str, Any]) -> dict[str, Any]:
    result = dict(data)
    death = text(value_for(data, "death_date", "deathdate"))
    if value_for(data, "living", "is_living") is None and death and death.replace("0", "").replace("-", "").strip():
        result["living"] = False
    return result


def _provider_sensitivity(data: Mapping[str, Any], fallback: Sensitivity) -> Sensitivity:
    return input_sensitivity(data, fallback, provider_privacy=True)
