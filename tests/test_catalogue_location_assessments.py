import tempfile
import unittest
from pathlib import Path

from genealogy.store.core import create_store
from genealogy.store.errors import ConstraintError, StaleRevisionError
from genealogy.store.services import Research

from tools.catalogue_location_assessments import (
    LIMITATIONS, association_id, load_associations, record_association,
)


class LocationAssessmentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = create_store(Path(self.temp.name) / "fixture.sqlite", project_id="location-tests")
        self.research = Research(self.store)
        with self.store.write(actor="fixture", tool="fixture") as tx:
            self.person = self.research.create_person(tx, id="person-1", label="Historical person",
                                                       living="deceased", access="public")
            self.research.create_person(tx, id="living-1", living="living", access="public")
            self.research.create_person(tx, id="private-1", living="deceased", access="private")
            self.record = self.research.add_record(tx, id="record-1", title="Original record",
                                                   place_wording="Original source wording", access="public")
            self.vital = self.research.create_claim(
                tx, id="birth-1", subject_person_id=self.person, kind="vital", predicate="birth",
                proposition="Recorded birth", value_text="before 1800", access="public")
        self.original_record = self.store.get("record", self.record)
        self.original_person = self.store.get("person", self.person)
        self.original_birth = self.store.get("claim", self.vital)

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def write(self, **overrides):
        arguments = dict(person_id=self.person, catalogue_id="Glasgow-1", region="Scotland",
                         place="Lanarkshire, Scotland", basis_kind="own_record",
                         basis="A reviewed own-record locality supplies this uncertain classification.",
                         evidence=[{"catalogue_id": "glasgow-1", "record_id": self.record,
                                    "field": "record_location", "value": "Lanarkshire, Scotland",
                                    "url": "https://example.org/held-record"}], expected_revision=0)
        arguments.update(overrides)
        return record_association(self.store, **arguments)

    def test_creates_audited_uncertain_attribute_and_preserves_sources_and_vitals(self):
        result = self.write(record_regions={self.record: "Scotland"})
        claim = self.store.get("claim", result["claim_id"])
        self.assertEqual((claim["kind"], claim["predicate"], claim["value_text"]),
                         ("attribute", "associated_place", "Lanarkshire, Scotland"))
        assessment = self.research.current_assessment(claim["id"])
        self.assertEqual((assessment["status"], assessment["confidence"]), ("uncertain", "possible"))
        self.assertEqual(assessment["limitations"], LIMITATIONS)
        self.assertIsNone(assessment["estimate_percent"])
        loaded = load_associations(store=self.store)["glasgow-1"][0]
        self.assertEqual(loaded["record_regions"], {self.record: "Scotland"})
        self.assertEqual(loaded["basis_kind"], "own_record")
        self.assertEqual(loaded["evidence"][0]["url"], "https://example.org/held-record")
        self.assertTrue(self.store.all("SELECT * FROM audit_log WHERE table_name='claim'"))
        self.assertEqual(self.store.get("person", self.person), self.original_person)
        self.assertEqual(self.store.get("record", self.record), self.original_record)
        self.assertEqual(self.store.get("claim", self.vital), self.original_birth)

    def test_rerun_is_idempotent_stale_revision_is_rejected_and_history_preserved(self):
        created = self.write()
        repeated = self.write(expected_revision=1)
        self.assertEqual(repeated, {"claim_id": created["claim_id"], "revision": 1, "changed": False})
        with self.assertRaises(StaleRevisionError):
            self.write(expected_revision=0)
        with self.assertRaises(ConstraintError):
            self.write(expected_revision=1, catalogue_id="Different-1")
        revised = self.write(expected_revision=1, basis="Additional reviewed context; still uncertain.")
        self.assertEqual(revised["revision"], 2)
        history = self.research.assessment_history(created["claim_id"])
        self.assertEqual(len(history), 2)
        self.assertNotEqual(history[0]["reasoning"], history[1]["reasoning"])
        with self.assertRaises(StaleRevisionError):
            self.write(expected_revision=1, basis="Additional reviewed context; still uncertain.")
        self.assertEqual(self.store.get("claim", created["claim_id"])["revision"], 1)

    def test_multiple_places_have_distinct_claims_and_loader_scopes_public_rows(self):
        self.write()
        self.write(place="Ireland", region="Ireland", basis_kind="kin",
                   evidence=[{"catalogue_id": "relative-1", "field": "birth_location", "value": "Ireland"}])
        self.assertEqual(len(load_associations(store=self.store)["glasgow-1"]), 2)
        self.assertEqual(load_associations(store=self.store, eligible_catalogue_ids=["other"]), {})
        self.assertEqual(len(load_associations(store=self.store, eligible_catalogue_ids=["GLASGOW-1"])["glasgow-1"]), 2)
        with self.assertRaises(ConstraintError):
            self.write(person_id="living-1")
        with self.assertRaises(ConstraintError):
            self.write(person_id="private-1")
        self.assertEqual(association_id(self.person, "  Lanarkshire,   Scotland "),
                         association_id(self.person, "lanarkshire, scotland"))

    def test_record_region_override_requires_explicit_own_matching_location(self):
        for overrides in [
            {"basis_kind": "kin", "record_regions": {self.record: "Scotland"}},
            {"record_regions": {"unmatched-record": "Scotland"}},
            {"record_regions": {self.record: "Ireland"}},
            {"evidence": [{"record_id": self.record, "field": "birth_location",
                           "value": "Lanarkshire, Scotland"}], "record_regions": {self.record: "Scotland"}},
        ]:
            with self.subTest(overrides=overrides), self.assertRaises(ConstraintError):
                self.write(**overrides)
        self.assertFalse(self.store.all("SELECT * FROM claim WHERE predicate='associated_place'"))

    def test_withdrawn_classification_is_not_projected(self):
        result = self.write()
        with self.store.write(actor="fixture", tool="withdraw") as tx:
            self.research.assess(tx, result["claim_id"], expected_revision=1,
                                 confidence="disproved", status="withdrawn",
                                 reasoning="Context no longer supports this association.")
        self.assertEqual(load_associations(store=self.store), {})


if __name__ == "__main__":
    unittest.main()
