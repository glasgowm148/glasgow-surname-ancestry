"""Dispatch decisions survive DB revisions and both compatibility directions."""
from __future__ import annotations

from copy import deepcopy
import json
import unittest

from tests import test_workbench_migration as fixture_helpers

Research = fixture_helpers.Research
open_project = fixture_helpers.open_project
workbench_legacy_views = fixture_helpers.workbench_legacy_views
write = fixture_helpers.write


class ResearchStateRoundTrip(unittest.TestCase):
    def setUp(self):
        self.fixture = fixture_helpers.GlasgowMigrationFixture()
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        self.old = {"research_state": {"disposition": "ready"},
                    "last_test": "Earlier review", "next_test": "Read the original"}
        assessments = deepcopy(fixture_helpers.ASSESSMENTS)
        estimates = deepcopy(fixture_helpers.ESTIMATES)
        self.history = [{"status": "possible", "probability_percent": 60,
                         "source_basis": "Before the baptism was found."}]
        assessments[1].update(self.old)
        assessments[1]["assessment_history"] = self.history
        for row in estimates["estimates"]:
            if row["assertion_id"] == "C-test-ann-father":
                row.update(self.old)
                row["assessment_history"] = self.history
        self.assessments, self.estimates = assessments, estimates
        write(self.fixture.source, workbench_legacy_views.ASSESSMENTS, assessments)
        write(self.fixture.source, workbench_legacy_views.ESTIMATES, estimates)
        self.fixture.migrate()

    def views(self):
        with open_project(self.fixture.project) as project:
            views = workbench_legacy_views.Views(project.store)
            return views.assessments(), views.estimates()

    def revise(self, extra=None):
        with open_project(self.fixture.project) as project:
            research = Research(project.store)
            claim = research.find_external("glasgow-assertion", "C-test-ann-father")[0]
            current = research.current_assessment(claim)
            with project.store.write(actor="researcher", tool="genealogy assess") as tx:
                research.assess(tx, claim, expected_revision=current["revision"],
                                status="probable", grade="probable", estimate_percent=80,
                                estimate_kind="subjective", reasoning="Baptism names William.",
                                assessed_on="2026-10-26", research_status="reviewed_no_change",
                                extra=extra)

    @staticmethod
    def pair(assessments, estimates):
        assertion = next(row for row in assessments if row["assertion_id"] == "C-test-ann-father")
        rows = [row for row in estimates if row["assertion_id"] == "C-test-ann-father"]
        return assertion, rows

    def test_unchanged_migration_preserves_existing_metadata_verbatim(self):
        assertions, estimates = self.views()
        self.assertEqual(assertions, self.assessments)
        _, rows = self.pair(assertions, estimates)
        expected = [row for row in self.estimates["estimates"]
                    if row["assertion_id"] == "C-test-ann-father"]
        self.assertEqual(rows, expected)

    def test_current_explicit_decision_overrides_old_metadata_in_both_directions(self):
        new = {"research_state": {"disposition": "reviewed_no_change", "blocker": "Original inaccessible"},
               "last_test": "Compared held transcript and sibling account",
               "next_test": "Reopen when original available"}
        self.revise(new)
        assertion, rows = self.pair(*self.views())
        self.assertEqual(len(rows), 2)
        self.assertEqual({row["relationship"] for row in rows}, {"father", "child"})
        for row in [assertion, *rows]:
            for key, value in new.items():
                self.assertEqual(row[key], value)
        self.assertEqual(assertion["probability"]["value"], .8)
        self.assertEqual(assertion["assessment_history"], self.history)
        for row in rows:
            self.assertEqual(row["percent"], 80)
            self.assertEqual(row["assessment_history"], self.history)

    def test_absent_metadata_does_not_infer_readiness_or_erase_legacy_values(self):
        self.revise()
        assertion, rows = self.pair(*self.views())
        for row in [assertion, *rows]:
            for key, value in self.old.items():
                self.assertEqual(row[key], value)
        self.assertEqual(workbench_legacy_views.research_fields(
            {"research_status": "reviewed_no_change", "extra_json": json.dumps({"research_state": "ready"})}), {})


if __name__ == "__main__":
    unittest.main()
