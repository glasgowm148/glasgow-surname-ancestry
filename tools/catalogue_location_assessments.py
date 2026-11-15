"""Audited uncertain place classifications; source locations/vitals stay untouched.

This module does not infer locations. A caller must provide a reviewed place,
region, basis and source/context identifiers. Writes use the workbench Research
API in an audited transaction; loading opens the configured project read-only.
"""
from __future__ import annotations

from contextlib import contextmanager
import json
from pathlib import Path

from genealogy.store import open_project
from genealogy.store.errors import ConstraintError, StaleRevisionError
from genealogy.store.services import Research, stable_id

ROOT = Path(__file__).resolve().parents[1]
METADATA = "catalogue_location_association"
LIMITATIONS = ("Uncertain catalogue place association inferred from the stated context. "
               "This does not establish birthplace, residence, a journey, or an original record location.")


def association_id(person_id: str, place: str) -> str:
    return stable_id("clm-location", person_id, " ".join(place.split()).casefold())


def record_association(store, *, person_id: str, catalogue_id: str, region: str, place: str,
                       basis_kind: str, basis: str, evidence=(), record_regions=None, expected_revision: int,
                       actor: str = "catalogue-location-review", assessed_on: str | None = None) -> dict:
    """Create/revise one explicitly uncertain person-place classification.

    expected_revision=0 requires no existing assessment. Identical input at its
    current revision is a no-op. Stale revisions always fail, including no-ops.
    Different places receive separate claims; nothing silently supersedes them.
    Evidence objects retain reviewed source/context fields verbatim. Optional
    record_regions applies only to an explicitly matching own record_location;
    the caller must still check that the original region is missing.
    """
    if basis_kind not in {"own_record", "own_profile", "shared_record", "kin"}:
        raise ConstraintError("unsupported location basis_kind")
    copied_evidence = []
    for row in evidence:
        if not isinstance(row, dict) or set(row) - {"catalogue_id", "record_id", "field", "value", "url"}:
            raise ConstraintError("evidence must contain reviewed source-field objects")
        copied_evidence.append({key: str(value) for key, value in row.items() if value is not None})
    values = {"catalogue_id": catalogue_id.strip().casefold(), "region": region.strip(),
              "place": " ".join(place.split()), "basis": basis.strip(),
              "basis_kind": basis_kind, "evidence": copied_evidence,
              "record_regions": dict(record_regions or {})}
    if not all(values[key] for key in ("catalogue_id", "region", "place", "basis")):
        raise ConstraintError("catalogue ID, region, place and explicit basis are required")
    if values["region"].casefold() in {"unknown", "unspecified"}:
        raise ConstraintError("an uncertain classification needs an actual proposed region")
    for record_id, record_region in values["record_regions"].items():
        matched = any(row.get("record_id") == record_id and row.get("field") == "record_location"
                      and row.get("catalogue_id", "").casefold() == values["catalogue_id"]
                      and " ".join(row.get("value", "").split()).casefold() == values["place"].casefold()
                      for row in copied_evidence)
        if basis_kind != "own_record" or not matched or record_region != values["region"]:
            raise ConstraintError("record region requires the same person's explicit matching record_location")
    if isinstance(expected_revision, bool) or not isinstance(expected_revision, int) or expected_revision < 0:
        raise ConstraintError("expected_revision must be a nonnegative integer")
    person = store.require("person", person_id)
    if person["access"] != "public" or person["living"] == "living":
        raise ConstraintError("only public non-living-subject classifications may be projected")
    claim_id = association_id(person_id, values["place"])
    research = Research(store)
    with store.write(actor=actor, tool="catalogue location assessment",
                     source="reviewed local catalogue classification", reason=values["basis"]) as tx:
        claim = store.get("claim", claim_id)
        current = research.current_assessment(claim_id) if claim else None
        actual = current["current_revision"] if current else 0
        if actual != expected_revision:
            raise StaleRevisionError("assessment", claim_id, expected_revision, actual, current)
        if claim and (claim["subject_person_id"] != person_id or claim["predicate"] != "associated_place"
                      or claim["kind"] != "attribute"):
            raise ConstraintError("deterministic association ID belongs to a different claim")
        if claim:
            marker = json.loads(claim.get("extra_json") or "{}").get(METADATA) or {}
            if marker.get("schema_version") != 1 or marker.get("catalogue_id") != values["catalogue_id"]:
                raise ConstraintError("existing association belongs to a different canonical catalogue identity")
        if current and (current.get("extra") or {}).get(METADATA) == values and current.get("confidence") == "possible" and current.get("status") == "uncertain":
            return {"claim_id": claim_id, "revision": actual, "changed": False}
        if not claim:
            research.create_claim(
                tx, id=claim_id, kind="attribute", predicate="associated_place",
                subject_person_id=person_id, value_text=values["place"],
                proposition=f'Uncertain catalogue association with {values["place"]}; this is not a birthplace claim.',
                origin="research", access="public", publication_status="approved",
                extra={METADATA: {"schema_version": 1, "catalogue_id": values["catalogue_id"]}})
        _, revision = research.assess(
            tx, claim_id, expected_revision=expected_revision, new=actual == 0,
            status="uncertain", confidence="possible", reasoning=values["basis"],
            limitations=LIMITATIONS, assessed_on=assessed_on, basis=sorted({row.get("record_id") or row.get("catalogue_id") for row in copied_evidence if row.get("record_id") or row.get("catalogue_id")}),
            extra={METADATA: values})
    return {"claim_id": claim_id, "revision": revision, "changed": True}


@contextmanager
def _store(root, supplied):
    project = None
    try:
        if supplied is None:
            project = open_project(Path(root), readonly=True)
        yield supplied if supplied is not None else project.store
    finally:
        if project:
            project.store.close()


def load_associations(root=ROOT, *, store=None, eligible_catalogue_ids=None) -> dict[str, list[dict]]:
    """Return catalogue ID -> current uncertain claims, with exact provenance.

    Only this module's public approved attribute claims on public people are
    eligible. Optional eligible_catalogue_ids further scopes the projection to
    the already privacy-filtered historical catalogue. No birth/record fields
    are changed and no synthetic map coordinates are generated.
    """
    eligible = None if eligible_catalogue_ids is None else {str(value).casefold() for value in eligible_catalogue_ids}
    result = {}
    with _store(root, store) as current_store:
        research = Research(current_store)
        for claim in current_store.all("SELECT * FROM claim WHERE kind='attribute' AND predicate='associated_place' ORDER BY id"):
            if claim["access"] != "public" or claim["publication_status"] != "approved":
                continue
            marker = json.loads(claim.get("extra_json") or "{}").get(METADATA)
            if not isinstance(marker, dict) or marker.get("schema_version") != 1:
                continue
            person = current_store.get("person", claim["subject_person_id"])
            if not person or person["access"] != "public" or person["living"] == "living":
                continue
            assessment = research.current_assessment(claim["id"])
            if not assessment or assessment["status"] != "uncertain" or assessment["confidence"] != "possible":
                continue
            metadata = (assessment.get("extra") or {}).get(METADATA)
            if not isinstance(metadata, dict):
                continue
            key = str(metadata.get("catalogue_id") or "").casefold()
            if not key or key != marker.get("catalogue_id") or (eligible is not None and key not in eligible):
                continue
            if metadata.get("place") != claim["value_text"] or not metadata.get("region") or not metadata.get("basis"):
                continue
            result.setdefault(key, []).append({
                "claim_id": claim["id"], "assessment_revision": assessment["current_revision"],
                "person_id": person["id"], "region": metadata["region"], "place": metadata["place"],
                "status": assessment["status"], "confidence": assessment["confidence"],
                "basis_kind": metadata.get("basis_kind"), "basis": metadata["basis"],
                "evidence": list(metadata.get("evidence") or []),
                "record_regions": dict(metadata.get("record_regions") or {}),
                "limitations": assessment["limitations"], "assessed_on": assessment["assessed_on"],
            })
    return result
