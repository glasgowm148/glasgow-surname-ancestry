"""Derived legacy views replace stale prose after a DB reassessment."""
from copy import deepcopy
import unittest

from tests import test_workbench_migration as fixture_helpers


class AssessmentProjectionTests(unittest.TestCase):
    def test_fresh_mother_estimates_keep_sources_and_scope_in_both_directions(self):
        from genealogy.store import Research, open_project
        from tools.workbench_legacy_views import Views
        scope = "Retrospective family account; original birth entry not inspected."
        with open_project(self.fixture.project) as project:
            research = Research(project.store)
            child = research.find_external("wikitree", "Harrow-14")[0]
            with project.store.write(actor="test", tool="genealogy assess") as tx:
                mother = research.create_person(tx, id="per-new-mother", label="Test mother", access="public")
                claim = research.relationship_claim(tx, child_id=child, relative_id=mother,
                    role="mother", relation_type="biological", id="clm-new-mother", access="public",
                    publication_status="approved")
                research.assess(tx, claim, expected_revision=0, status="proved", grade="proved",
                    estimate_percent=93, estimate_kind="subjective", reasoning="Named mother in the family account.",
                    limitations=scope, assessed_on="2026-10-26", basis=["will-1805"])
            estimates = [x for x in Views(project.store).estimates() if x["assertion_id"] == claim]
        self.assertEqual({x["relationship"] for x in estimates}, {"mother", "child"})
        self.assertEqual(len(estimates), 2)
        for row in estimates:
            self.assertEqual(row["scope"], scope)
            self.assertEqual(row["source_ids"], ["will-1805"])

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

    def test_fresh_maternal_claim_exports_selection_replacement_and_relation_type(self):
        import tools.workbench_legacy_views as views
        view = views.Views.__new__(views.Views)
        view.store = type("Store", (), {"one": lambda self, *args: None})()
        view.person = lambda ident: {"per-child": "Child-1", "per-mother": "Mother-1"}[ident]
        revision = {
            "status": "probable", "assessed_on": "2026-10-26", "reasoning": "Record names Mary.",
            "limitations": "Original image not inspected.", "basis_json": '["record-mary"]',
            "estimate_percent": 93, "extra_json": '{"allow_new_relationship": true, "working_parent_replacement": '
            '{"previous_parent": "Thompson-1"}, "analysis_links": [{"label": "Review", "href": "/review"}], '
            '"research_state": {"disposition": "ready"}}', "working_selection": 1,
            "attachment_status": "unmarked"
        }
        row = view.new_assessment({"id": "claim-mother", "subject_person_id": "per-child",
                                   "object_person_id": "per-mother", "predicate": "mother",
                                   "relation_type": "biological", "proposition": "Mother-1 is mother of Child-1",
                                   "publication_status": "approved"}, [revision])
        self.assertEqual(row["relation_type"], "biological")
        self.assertTrue(row["working_selection"])
        self.assertTrue(row["allow_new_relationship"])
        self.assertEqual(row["working_parent_replacement"]["previous_parent"], "Thompson-1")
        self.assertEqual(row["perspectives"]["Child-1"]["relationship"], "mother")
        self.assertEqual(row["probability"]["scope"], "Original image not inspected.")
        self.assertEqual(row["analysis_links"][0]["label"], "Review")

    def test_fresh_stepmother_claim_uses_step_roles_in_both_views(self):
        import tools.workbench_legacy_views as views
        view = views.Views.__new__(views.Views)
        view.store = type("Store", (), {"one": lambda self, *args: None})()
        view.person = lambda ident: {"per-child": "Child-1", "per-mother": "Mother-1"}[ident]
        revision = {"status": "possible", "assessed_on": "2026-10-26", "reasoning": "Household evidence.",
                    "limitations": "Step relationship; birth maternity unproved.", "basis_json": '["household-1"]',
                    "estimate_percent": 40, "extra_json": '{}', "working_selection": 1, "attachment_status": "unmarked"}
        claim = {"id": "claim-step", "subject_person_id": "per-child", "object_person_id": "per-mother",
                 "predicate": "mother", "relation_type": "step", "proposition": "Mother-1 is stepmother of Child-1",
                 "publication_status": "approved"}
        row = view.new_assessment(claim, [revision])
        self.assertEqual(row["perspectives"], {"Child-1": {"relationship": "stepmother"},
                                                  "Mother-1": {"relationship": "stepchild"}})
        self.assertEqual(row["relation_type"], "step")


if __name__ == "__main__":
    unittest.main()
