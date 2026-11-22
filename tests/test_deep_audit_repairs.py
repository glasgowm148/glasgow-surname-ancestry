"""DeepSeek-authored repair regressions, independently reviewed and hardened by SOL."""
from copy import deepcopy
import unittest

from genealogy.store import Research, open_project
from tests import test_queue_catalogue_creations as creation_tests
from tools.research_entry import record_document
from tools.research_integrity import hold_condition, row_sha256, validate_hold_release
from tools.workbench_documents import Documents

module = creation_tests.module


class StatusOnlyReceiptTests(unittest.TestCase):
    def test_status_only_receipt_uses_the_callers_status_field(self):
        previous = {"status": "blocked"}
        receipt = {"previous_row_sha256": row_sha256(previous),
                   "condition": hold_condition(previous, status_field="status"),
                   "decision": "satisfied", "reason": "Fictional source checked.",
                   "reviewed_by": "fixture", "evidence": [
                       {"record_id": "rec-fixture", "revision": 1, "locator": "page 2"}]}
        validate_hold_release(previous, {"status": "answered", "hold_release": receipt},
                              status_field="status", evidence_revision=lambda _: 1)
        receipt["condition"] = "creation_ready"
        with self.assertRaisesRegex(ValueError, "previous verification condition"):
            validate_hold_release(previous, {"status": "answered", "hold_release": receipt}, status_field="status")


class PublisherAuthorityTests(unittest.TestCase):
    def setUp(self):
        self.fixture = creation_tests.QueueCatalogueCreationsTests(methodName="test_duplicate_subject_blocks_targeted_creation_before_output_changes")
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root
        self.entry = deepcopy(self.fixture.entry)
        (self.root / "genealogy.toml").write_text('[project]\nname="Fictional"\n[storage]\ndatabase="test.sqlite"\n')

    def store(self, rows):
        with open_project(self.root, create=True) as project:
            with project.store.write(actor="fixture", tool="fixture") as tx:
                Documents(project.store).store_document(tx, str(module.MANIFEST),
                                                        {"new_people": rows, "profile_updates": {}})

    def save(self, rows):
        import json
        (self.root / module.MANIFEST).write_text(json.dumps({"new_people": rows, "profile_updates": {}}))

    def test_fake_and_valid_looking_unrecorded_receipts_are_both_blocked(self):
        held = {**self.entry, "creation_status": "hold_source_verification"}
        self.store([held])
        exact = {"previous_row_sha256": row_sha256(held), "condition": hold_condition(held),
                 "decision": "satisfied", "reason": "Claimed review", "reviewed_by": "fixture",
                 "evidence": [{"record_id": "rec-nonexistent", "revision": 1, "locator": "page 2"}]}
        for receipt in ({"unrelated": True}, exact):
            self.save([{**held, "creation_status": "creation_ready", "hold_release": receipt}])
            with self.subTest(receipt=receipt), self.assertRaisesRegex(ValueError, "workbench before publishing"):
                module.reviewed_people(self.root)

    def test_properly_recorded_release_with_native_evidence_succeeds(self):
        held = {**self.entry, "creation_status": "hold_source_verification"}
        self.store([held])
        with open_project(self.root) as project:
            documents = Documents(project.store)
            with project.store.write(actor="fixture", tool="fixture") as tx:
                record = Research(project.store).add_record(tx, title="Fictional register")
            ready = {**held, "creation_status": "creation_ready", "hold_release": {
                "previous_row_sha256": row_sha256(held), "condition": hold_condition(held),
                "decision": "satisfied", "reason": "Fictional original checked", "reviewed_by": "fixture",
                "evidence": [{"record_id": record, "revision": project.store.get("record", record)["revision"],
                              "locator": "page 2"}]}}
            record_document(project, str(module.MANIFEST), {"new_people": [ready], "profile_updates": {}},
                            expected_revision=documents.frame(str(module.MANIFEST))["note"]["revision"],
                            actor="fixture", reason="Reviewed release")
        self.save([ready])
        self.assertEqual(self.entry["catalogue_id"], module.reviewed_people(self.root)[0]["catalogue_id"])

    def test_renaming_or_swapping_ids_does_not_create_a_recorded_ready_decision(self):
        self.store([self.entry])
        for change in ({"catalogue_id": "record-renamed"},
                       {"catalogue_id": self.entry["subject_id"], "subject_id": self.entry["catalogue_id"]}):
            self.save([{**self.entry, **change}])
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, "workbench before publishing"):
                module.reviewed_people(self.root)

    def test_unchanged_native_merge_preserves_the_source_hold(self):
        source = {**self.entry, "catalogue_id": "record-held-source", "subject_id": "held-source",
                  "creation_status": "hold_source_verification"}
        self.store([self.entry, source])
        self.save([self.entry, source])
        rows = module.reviewed_people(self.root, merge_state=({"record-held-source": self.entry["catalogue_id"]}, {}))
        self.assertEqual(1, len(rows))
        self.assertEqual("hold_source_verification", rows[0]["creation_status"])


class UnselectedParentProjectionTests(unittest.TestCase):
    def assessment(self, role='father', **changes):
        row = {'assertion_id': 'fixture-parent', 'people': ['Fixture-1', 'Fixture-2'],
               'perspectives': {'Fixture-1': {'relationship': role}, 'Fixture-2': {'relationship': 'child'}},
               'publication_status': 'approved', 'status': 'possible', 'source_ids': ['fixture-source'],
               'reason': 'Fictional source-scoped parent hypothesis.', 'basis': 'Fictional record.',
               'profile_names': {'Fixture-1': 'Fictional child', 'Fixture-2': 'Fictional parent'},
               'working_selection': False, 'allow_new_relationship': True,
               'provenance': {'new_father_attachment': True}, 'lifecycle': 'current', 'display': 'current',
               'probability': {'value': 0.4}}
        row.update(changes)
        return row

    def resolve(self, assessment, *, original_parent=None, subject='Fixture-1'):
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        from tools import publish_resolved_dossiers as publisher
        dossier = {'id': subject, 'name': 'Fictional subject', 'claims': [], 'relationships': {'parents': []}}
        if original_parent:
            dossier['relationships']['parents'].append(original_parent)
        with tempfile.TemporaryDirectory() as temporary, patch.object(publisher, 'HISTORY_SEED', Path(temporary) / 'absent'):
            result = publisher.resolve(deepcopy(dossier), [], [assessment])
        rows = [{'id': subject, 'father': [], 'mother': [], 'missing_father': True, 'missing_mother': True}]
        publisher.project_catalogue_parents(rows, {subject.casefold(): result})
        return result, rows[0]

    def test_unselected_added_father_is_alternative_and_keeps_evidence(self):
        assessment = self.assessment()
        result, row = self.resolve(assessment)
        self.assertEqual([], row['father'])
        self.assertTrue(row['missing_father'])
        relation = result['relationships']['parents'][0]
        self.assertEqual(('alternative', 'alternative'), (relation['lifecycle'], relation['display']))
        self.assertEqual(['fixture-source'], relation['source_ids'])
        self.assertEqual('current', assessment['display'])

    def test_selected_or_retained_father_is_not_blanket_removed(self):
        for changes in ({'working_selection': True}, {'attachment_status': 'attached'},
                        {'attachment_status': 'retained'}, {'provenance': {'new_father_attachment': False}}):
            with self.subTest(changes=changes):
                _, row = self.resolve(self.assessment(**changes))
                self.assertEqual(['Fixture-2'], [p['id'] for p in row['father']])
                self.assertFalse(row['missing_father'])

    def test_real_imported_tree_parent_is_preserved(self):
        original = {'id': 'Fixture-2', 'name': 'Fictional captured father', 'relationship': 'father',
                    'tree_relationship': True, 'status': 'unknown'}
        _, row = self.resolve(self.assessment(), original_parent=original)
        self.assertEqual(['Fixture-2'], [p['id'] for p in row['father']])

    def test_approved_mother_with_false_selection_is_preserved(self):
        _, row = self.resolve(self.assessment(role='mother'))
        self.assertEqual(['Fixture-2'], [p['id'] for p in row['mother']])
        self.assertFalse(row['missing_mother'])

    def test_reciprocal_child_is_an_inspectable_alternative(self):
        result, _ = self.resolve(self.assessment(), subject='Fixture-2')
        relation = result['relationships']['children'][0]
        self.assertEqual('Fixture-1', relation['id'])
        self.assertEqual('alternative', relation['display'])


if __name__ == "__main__":
    unittest.main()
