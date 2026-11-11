import unittest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from tools.workbench_legacy_views import Views


class NativeMergeProjectionTests(unittest.TestCase):
    def test_native_merge_chain_and_undo_preserve_historical_participants(self):
        from genealogy.cli import initialize_project
        from genealogy.store import Research, open_project

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'project'
            initialize_project(root, 'Fictional merge projection')
            with open_project(root) as project:
                research = Research(project.store)
                old, middle, survivor, father = ('person-old', 'person-middle', 'person-survivor', 'person-father')
                historical = {'people': ['record-old', 'Fable-2'], 'basis': 'record-old is the literal earlier identifier'}
                legacy = {'people': ['record-old', 'Fable-2'],
                          'perspectives': {'record-old': {'relationship': 'father'}, 'Fable-2': {'relationship': 'child'}},
                          'status': 'possible', 'assessment_history': [historical],
                          'provenance': {'subject_id': 'record-old'}}
                estimate = {'subject_id': 'record-old', 'relative_id': 'Fable-2', 'percent': 25,
                            'assessment_history': [historical]}
                with project.store.write(actor='test', tool='workbench_migrate') as tx:
                    for person in (old, middle, survivor, father):
                        research.create_person(tx, id=person, label=person)
                    for person, system, value in ((old, 'glasgow-local', 'record-old'),
                                                  (middle, 'glasgow-local', 'record-middle'),
                                                  (survivor, 'wikitree', 'Fable-1'),
                                                  (father, 'wikitree', 'Fable-2')):
                        research.map_external(tx, person, system, value)
                    claim = research.relationship_claim(tx, child_id=old, relative_id=father, role='father',
                        extra={'legacy_json': json.dumps(legacy), 'legacy_estimates_json': json.dumps([[0, estimate]])})
                    research.assess(tx, claim, status='possible', estimate_percent=25, estimate_kind='subjective')
                self.assertEqual([legacy], Views(project.store).assessments())

                def check(target):
                    view = Views(project.store)
                    row = view.assessments()[0]
                    self.assertEqual([target, 'Fable-2'], row['people'])
                    self.assertEqual({target, 'Fable-2'}, set(row['perspectives']))
                    self.assertEqual([historical], row['assessment_history'])
                    self.assertEqual({'subject_id': 'record-old'}, row['provenance'])
                    self.assertEqual(target, view.estimates()[0]['subject_id'])
                    self.assertEqual([historical], view.estimates()[0]['assessment_history'])

                with project.store.write(actor='test') as tx:
                    first = research.merge_people(tx, survivor_id=middle, retired_id=old, reason='same record')
                check('record-middle')
                with project.store.write(actor='test') as tx:
                    second = research.merge_people(tx, survivor_id=survivor, retired_id=middle, reason='same household')
                check('Fable-1')
                with project.store.write(actor='test') as tx:
                    research.undo_merge(tx, second, reason='test reversal')
                check('record-middle')
                with project.store.write(actor='test') as tx:
                    research.undo_merge(tx, first, reason='test reversal')
                self.assertEqual([legacy], Views(project.store).assessments())
                self.assertEqual([estimate], Views(project.store).estimates())


class Store:
    def __init__(self, rows):
        self.rows = rows

    def all(self, sql, params=()):
        if "system='wikitree'" in sql:
            return [r for r in self.rows if r.get("system") == "wikitree" and r.get("status", "current") == "current"]
        if "system='glasgow-local'" in sql:
            return [r for r in self.rows if r.get("system") == "glasgow-local" and r.get("status", "current") == "current"]
        if "entity_merge" in sql:
            return [r for r in self.rows if r.get("kind") in {"merge", "split"}]
        if "FROM external_id" in sql:
            return [r for r in self.rows if "system" in r]
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

    def test_active_merge_rewrites_current_participants_not_history(self):
        rows = [
            {"id": "m1", "kind": "merge", "survivor_id": "per-new", "retired_ids": '["per-old"]', "reason": "duplicate",
             "moved_json": '{"rows":[{"table":"external_id","key":{"id":"ext-old"}}]}'},
            {"id": "ext-old", "entity_id": "per-new", "system": "glasgow-local", "value": "record-old", "status": "former"},
            {"id": "ext-new", "entity_id": "per-new", "system": "wikitree", "value": "Glasgow-1406", "status": "current"},
        ]
        view = self.view(rows)
        claim = {"id": "c", "origin": "research", "publication_status": "approved",
                 "extra": {"legacy_estimates": [[0, {"subject_id": "record-old", "relative_id": "Glasgow-1512",
                 "percent": 12, "assessment_history": [{"subject_id": "record-old"}]}]]}}
        with patch.object(view, "claims", return_value=[claim]), patch.object(view, "revisions", return_value=[]):
            out = view.estimates()
        self.assertEqual("Glasgow-1406", out[0]["subject_id"])
        self.assertEqual("record-old", out[0]["assessment_history"][0]["subject_id"])

    def test_undo_merge_and_no_merge_leave_output_unchanged(self):
        rows = [
            {"id": "m1", "kind": "merge", "survivor_id": "per-new", "retired_ids": '["per-old"]', "reason": "duplicate"},
            {"id": "s1", "kind": "split", "survivor_id": "per-old", "retired_ids": "[]", "reason": "undo m1: correction"},
            {"id": "ext-old", "entity_id": "per-old", "system": "glasgow-local", "value": "record-old", "status": "current"},
            {"entity_id": "per-new", "system": "wikitree", "value": "Glasgow-1406", "status": "current"},
        ]
        view = self.view(rows)
        self.assertEqual("record-old", view.person("per-old"))
        self.assertEqual({}, view._merged_public)
        self.assertEqual("per-unmerged", self.view([]).person("per-unmerged"))

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
