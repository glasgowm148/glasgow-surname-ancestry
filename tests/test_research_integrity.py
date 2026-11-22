"""Fictional regressions for identity uniqueness and evidence-backed hold releases."""
from copy import deepcopy
import unittest

from tools.research_integrity import (hold_condition, row_sha256,
                                      validate_creation_document, validate_creation_subjects,
                                      validate_hold_release)


class ResearchIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.held = {"catalogue_id": "record-example-a", "subject_id": "subject-example",
                     "creation_status": "hold_source_verification",
                     "hold_condition": "Inspect the original register year heading.",
                     "assessment": "Two readings remain unresolved."}

    def released(self, decision="satisfied"):
        return {**deepcopy(self.held), "creation_status": "creation_ready", "hold_release": {
            "previous_row_sha256": row_sha256(self.held), "condition": hold_condition(self.held),
            "decision": decision, "reason": "The inspected heading resolves the competing years.",
            "reviewed_by": "fixture-reviewer", "evidence": [
                {"record_id": "rec-fictional", "revision": 2, "locator": "image 4, year heading"}]}}

    def test_same_subject_different_accounts_rejected_case_insensitively(self):
        other = {**self.held, "catalogue_id": "record-example-b", "subject_id": " SUBJECT-EXAMPLE "}
        with self.assertRaisesRegex(ValueError, "Duplicate canonical subject_id"):
            validate_creation_subjects([self.held, other])

    def test_explicit_chained_merges_are_allowed_but_cycles_are_not(self):
        other = {**self.held, "catalogue_id": "record-example-b", "subject_id": "old-subject"}
        aliases = {"old-subject": "middle-subject", "middle-subject": "subject-example",
                   "record-example-b": "record-example-a"}
        validate_creation_subjects([self.held, other], aliases)
        aliases["subject-example"] = "old-subject"
        with self.assertRaisesRegex(ValueError, "cyclic"):
            validate_creation_subjects([self.held, other], aliases)

    def test_alias_subjects_cannot_share_unmerged_accounts(self):
        other = {**self.held, "catalogue_id": "record-example-b", "subject_id": "old-subject"}
        with self.assertRaisesRegex(ValueError, "Duplicate canonical subject_id"):
            validate_creation_subjects([self.held, other], {"old-subject": "subject-example"})

    def test_status_text_and_missing_status_cannot_release_a_hold(self):
        for status in ("creation_ready", None, "resolved"):
            new = {**self.held, "assessment": "No match; creation ready."}
            if status is None:
                del new["creation_status"]
            else:
                new["creation_status"] = status
            with self.subTest(status=status), self.assertRaisesRegex(ValueError, "evidence receipt"):
                validate_hold_release(self.held, new)

    def test_hold_receipt_requires_exact_condition_and_previous_row(self):
        for field, value in (("condition", "A different easier test"),
                             ("previous_row_sha256", "0" * 64), ("decision", "done"),
                             ("reviewed_by", " "), ("reason", ""), ("evidence", [])):
            new = self.released()
            new["hold_release"][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_hold_release(self.held, new)

    def test_evidence_must_exist_at_the_reviewed_revision(self):
        new = self.released()
        for current in (None, 1, 3):
            with self.subTest(current=current), self.assertRaisesRegex(ValueError, "missing or stale"):
                validate_hold_release(self.held, new, evidence_revision=lambda _: current)
        validate_hold_release(self.held, new, evidence_revision=lambda _: 2)

    def test_evidence_needs_locator_and_integer_revision(self):
        for field, value in (("locator", ""), ("record_id", ""), ("revision", True), ("revision", "2")):
            new = self.released()
            new["hold_release"]["evidence"][0][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                validate_hold_release(self.held, new)

    def test_satisfied_and_explicitly_superseded_receipts_are_supported(self):
        for decision in ("satisfied", "superseded"):
            validate_hold_release(self.held, self.released(decision), evidence_revision=lambda _: 2)

    def test_unchanged_hold_needs_no_release(self):
        validate_hold_release(self.held, deepcopy(self.held))

    def _receipt(self, held, decision="superseded"):
        return {"previous_row_sha256": row_sha256(held), "condition": hold_condition(held),
                "decision": decision, "reason": "Merged into the reviewed target account.",
                "reviewed_by": "fixture-reviewer",
                "evidence": [{"record_id": "rec-fictional", "revision": 2, "locator": "image 4"}]}

    def test_merged_target_can_release_several_held_rows_with_one_receipt_each(self):
        held_a = deepcopy(self.held)
        held_b = {**deepcopy(self.held), "catalogue_id": "record-example-b", "subject_id": "subject-example-b",
                  "hold_condition": "Inspect the separate original register heading."}
        proposed = {"catalogue_id": "record-new", "subject_id": "subject-new", "creation_status": "creation_ready",
                    "hold_releases": [self._receipt(held_a), self._receipt(held_b)]}
        aliases = {"record-example-a": "record-new", "subject-example": "subject-new",
                   "record-example-b": "record-new", "subject-example-b": "subject-new"}
        validate_creation_document({"new_people": [proposed]}, {"new_people": [held_a, held_b]}, aliases=aliases)
        proposed["hold_releases"] = [self._receipt(held_a)]
        with self.assertRaisesRegex(ValueError, "does not match the exact previous held row"):
            validate_creation_document({"new_people": [proposed]}, {"new_people": [held_a, held_b]}, aliases=aliases)

    def test_reordering_or_renaming_catalogue_id_cannot_evade_hold(self):
        released = {**self.held, "catalogue_id": "record-renamed", "creation_status": "creation_ready"}
        previous = {"new_people": [self.held]}
        with self.assertRaisesRegex(ValueError, "evidence receipt"):
            validate_creation_document({"new_people": [released]}, previous)
        with self.assertRaisesRegex(ValueError, "silently removed"):
            validate_creation_document({"new_people": []}, previous)


if __name__ == "__main__":
    unittest.main()
