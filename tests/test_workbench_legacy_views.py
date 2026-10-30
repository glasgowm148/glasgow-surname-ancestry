import unittest
from unittest.mock import patch

from tools.workbench_legacy_views import Views


class Store:
    def __init__(self, rows):
        self.rows = rows

    def all(self, sql, params=()):
        if "system='wikitree'" in sql:
            return [r for r in self.rows if r["system"] == "wikitree"]
        if "system='glasgow-local'" in sql:
            return [r for r in self.rows if r["system"] == "glasgow-local"]
        return []

    def one(self, sql, params=()):
        if "system='glasgow-assertion'" in sql:
            return None
        return None


class LegacyViewPersonTests(unittest.TestCase):
    def test_imported_estimate_needs_approval_and_native_review_to_export_grade(self):
        view = self.view([])
        claim = dict(id="claim-1", origin="research", publication_status="approved",
                     extra={"legacy_estimates": [[0, {"percent": 25}]]})
        revision = dict(tool="genealogy.assess")
        with patch.object(view, "claims", return_value=[claim]), \
                patch.object(view, "revisions", return_value=[revision]), \
                patch.object(view, "new_assessment", return_value={"status": "uncertain"}) as render:
            self.assertEqual(view.assessments(), [{"status": "uncertain"}])
            render.assert_called_once_with(claim, [revision])
            claim["publication_status"] = "unreviewed"
            self.assertEqual(view.assessments(), [])
            claim["publication_status"] = "approved"
            revision["tool"] = "workbench_migrate"
            self.assertEqual(view.assessments(), [])

    def view(self, rows):
        with patch("tools.workbench_legacy_views.Research"):
            return Views(Store(rows))

    def test_wikitree_alias_has_priority(self):
        view = self.view([
            {"entity_id": "per-child", "value": "Glasgow-9000", "system": "wikitree"},
            {"entity_id": "per-child", "value": "glasgow-local-9000", "system": "glasgow-local"},
        ])
        self.assertEqual("Glasgow-9000", view.person("per-child"))

    def test_unique_local_alias_maps_record_defined_relationship_subject(self):
        view = self.view([
            {"entity_id": "per-child", "value": "glasgow-local-9000", "system": "glasgow-local"},
            {"entity_id": "per-father", "value": "Glasgow-589", "system": "wikitree"},
            {"entity_id": "per-mother", "value": "glasgow-local-9010", "system": "glasgow-local"},
        ])
        self.assertEqual("glasgow-local-9000", view.person("per-child"))
        self.assertEqual("Glasgow-589", view.person("per-father"))
        self.assertEqual("glasgow-local-9010", view.person("per-mother"))

    def test_ambiguous_local_alias_falls_back_to_native_id(self):
        view = self.view([
            {"entity_id": "per-child", "value": "glasgow-local-9000", "system": "glasgow-local"},
            {"entity_id": "per-child", "value": "glasgow-local-9001", "system": "glasgow-local"},
        ])
        self.assertEqual("per-child", view.person("per-child"))

    def test_unmapped_person_falls_back_to_native_id(self):
        self.assertEqual("per-unknown", self.view([]).person("per-unknown"))

    def test_new_assessment_exports_local_child_and_wikitree_parents(self):
        view = self.view([
            {"entity_id": "per-child", "value": "glasgow-local-9000", "system": "glasgow-local"},
            {"entity_id": "per-father", "value": "Glasgow-589", "system": "wikitree"},
            {"entity_id": "per-mother", "value": "Pierce-14470", "system": "wikitree"},
        ])
        claim = {
            "id": "clm-infant-father",
            "subject_person_id": "per-child",
            "object_person_id": "per-father",
            "predicate": "father",
            "relation_type": None,
            "proposition": "The record-defined child has Moses as father.",
            "publication_status": "approved",
        }
        revision = {
            "status": "documented", "assessed_on": "2026-10-26",
            "reasoning": "Explicit parent clause.", "limitations": "Record-defined identity scope.",
            "basis_json": "[]", "estimate_percent": None, "extra_json": "{}",
        }
        row = view.new_assessment(claim, [revision])
        self.assertEqual(["glasgow-local-9000", "Glasgow-589"], row["people"])
        self.assertEqual("father", row["perspectives"]["glasgow-local-9000"]["relationship"])
        self.assertEqual("child", row["perspectives"]["Glasgow-589"]["relationship"])
        self.assertNotIn("per-child", row["people"])

        mother_claim = dict(claim, id="clm-infant-mother", object_person_id="per-mother",
                            predicate="mother", proposition="The record-defined child has Mary as mother.")
        mother_row = view.new_assessment(mother_claim, [revision])
        self.assertEqual(["glasgow-local-9000", "Pierce-14470"], mother_row["people"])
        self.assertEqual("mother", mother_row["perspectives"]["glasgow-local-9000"]["relationship"])
        self.assertEqual("child", mother_row["perspectives"]["Pierce-14470"]["relationship"])


if __name__ == "__main__":
    unittest.main()
