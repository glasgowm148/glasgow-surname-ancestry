"""Derived legacy views replace stale prose after a DB reassessment."""
from copy import deepcopy
import unittest

from tests import test_workbench_migration as fixture_helpers


class AssessmentProjectionTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixture_helpers.GlasgowMigrationFixture()
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        assessments = deepcopy(fixture_helpers.ASSESSMENTS)
        row = assessments[0]
        row["record_scope"] = "Old scope with prior 62%."
        row["probability"]["scope"] = "Old probability scope."
        row["perspectives"]["Harrow-14"]["reason"] = "Old reason with prior 62%."
        row["provenance"] = {"prior_assessment": {"probability_percent": 62, "status": "possible"}}
        fixture_helpers.write(self.fixture.source, "research/relationship_assessments.json", assessments)
        estimates = deepcopy(fixture_helpers.ESTIMATES)
        for estimate in estimates["estimates"]:
            if estimate["assertion_id"] == "C-test-isaac-father":
                estimate["scope"] = "Old scope with prior 62%."
                estimate["source_ids"] = ["old-source"]
        fixture_helpers.write(self.fixture.source, "research/relationship_probability_estimates.json", estimates)
        self.fixture.migrate()

    def test_current_reason_and_limits_replace_stale_legacy_text_both_directions(self):
        from genealogy.store import Research, open_project
        import tools.workbench_legacy_views as views
        original = deepcopy(self.fixture.assessments if hasattr(self.fixture, "assessments") else fixture_helpers.ASSESSMENTS)
        with open_project(self.fixture.project) as project:
            research = Research(project.store)
            claim = research.find_external("glasgow-assertion", "C-test-isaac-father")[0]
            current = research.current_assessment(claim)
            with project.store.write(actor="test", tool="genealogy assess") as tx:
                research.assess(tx, claim, expected_revision=current["revision"], status="proved", grade="proved",
                                 estimate_percent=93, estimate_kind="subjective", reasoning="The inspected will names Isaac as son.",
                                 limitations="The will is a transcription; later identity remains unproved.",
                                 assessed_on="2026-10-26", basis=["will-1805"],
                                 extra={"provenance": {"review_lane": "lane-01"}})
            assertion = next(r for r in views.Views(project.store).assessments() if r["assertion_id"] == "C-test-isaac-father")
            estimates = [r for r in views.Views(project.store).estimates() if r["assertion_id"] == "C-test-isaac-father"]
        self.assertEqual(assertion["probability"]["value"], .93)
        self.assertEqual(assertion["reason"], "The inspected will names Isaac as son.")
        self.assertEqual(assertion["claim"], "The inspected will names Isaac as son.")
        self.assertEqual(assertion["record_scope"], "The will is a transcription; later identity remains unproved.")
        self.assertEqual(assertion["perspectives"]["Harrow-14"]["reason"], assertion["reason"])
        self.assertEqual(assertion["perspectives"]["Harrow-357"]["reason"], assertion["reason"])
        self.assertNotIn("status_label", assertion["perspectives"]["Harrow-14"])
        self.assertEqual(assertion["provenance"]["review_lane"], "lane-01")
        self.assertEqual(assertion["provenance"]["prior_assessment"]["probability_percent"], 62)
        self.assertEqual({r["percent"] for r in estimates}, {93})
        self.assertEqual({r["basis"] for r in estimates}, {assertion["reason"]})
        self.assertEqual({r["scope"] for r in estimates}, {"The will is a transcription; later identity remains unproved."})
        self.assertEqual({tuple(r["source_ids"]) for r in estimates}, {("will-1805",)})
        self.assertEqual(original, self.fixture.assessments if hasattr(self.fixture, "assessments") else fixture_helpers.ASSESSMENTS)


if __name__ == "__main__":
    unittest.main()
