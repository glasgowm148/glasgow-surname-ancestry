"""Glasgow legacy-registry migration on a fictional Glasgow-shaped checkout (always runnable).

The real migration runs on private local data; see tests/test_workbench_private_data.py,
which reports clearly when those inputs are absent instead of passing.
"""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from genealogy.store import Research, open_project  # noqa: E402

import workbench_legacy_views  # noqa: E402
import workbench_migrate  # noqa: E402

ASSESSMENTS = [
    {   # Reassessed 44% -> 95%; the reverse estimate row kept 44%.
        "assertion_id": "C-test-isaac-father", "people": ["Harrow-14", "Harrow-357"], "status": "proved",
        "publication_status": "approved", "assessment_date": "2026-10-23", "basis": "The will names Isaac.",
        "claim": "Harrow-357 is Isaac's father.", "source_ids": ["will-1805", "will-1805"],
        "perspectives": {"Harrow-14": {"relationship": "father"}, "Harrow-357": {"relationship": "son"}},
        "probability": {"value": 0.95, "reviewed": "2026-10-23"},
        "assessment_history": [{"status": "possible", "probability_percent": 44, "assessment_date": "2026-10-22",
                                "source_basis": "Same county, compatible generation."}],
    },
    {   # No percentage of its own: the estimates file carries it.
        "assertion_id": "C-test-ann-father", "people": ["Harrow-20", "Harrow-357"], "status": "probable",
        "publication_status": "approved", "basis": "Baptism names William.",
        "perspectives": {"Harrow-20": {"relationship": "father"}, "Harrow-357": {"relationship": "daughter"}},
    },
    {   # Brothers at 74%, with a 17% father row filed under the same id.
        "assertion_id": "C-test-brothers", "people": ["Harrow-30", "Harrow-31"], "status": "probable",
        "publication_status": "approved", "basis": "Shared household.", "probability": {"value": 0.74},
        "perspectives": {"Harrow-30": {"relationship": "brother"}, "Harrow-31": {"relationship": "brother"}},
    },
]
ESTIMATES = {"schema_version": 1, "reviewed": "2026-10-23", "method": "subjective_evidence_assessment",
             "note": "Invented.", "estimates": [
                 {"subject_id": "Harrow-14", "relative_id": "Harrow-357", "relationship": "father", "percent": 95,
                  "assessment_status": "proved", "assertion_id": "C-test-isaac-father", "reviewed": "2026-10-23"},
                 {"subject_id": "Harrow-357", "relative_id": "Harrow-14", "relationship": "child", "percent": 44,
                  "assessment_status": "possible", "assertion_id": "C-test-isaac-father", "reviewed": "2026-10-22"},
                 {"subject_id": "Harrow-20", "relative_id": "Harrow-357", "relationship": "father", "percent": 80,
                  "assessment_status": "probable", "assertion_id": "C-test-ann-father"},
                 {"subject_id": "Harrow-357", "relative_id": "Harrow-20", "relationship": "child", "percent": 80,
                  "assessment_status": "probable", "assertion_id": "C-test-ann-father"},
                 {"subject_id": "Harrow-30", "relative_id": "Harrow-31", "relationship": "sibling", "percent": 74,
                  "assessment_status": "probable", "assertion_id": "C-test-brothers"},
                 {"subject_id": "Harrow-30", "relative_id": "Harrow-31", "relationship": "father", "percent": 17,
                  "assessment_status": "uncertain", "assertion_id": "C-test-brothers"},
             ]}
RECORDS = [{"record_id": "will-1805", "association": "Will of William Harrow", "date": "14 October 1805",
            "year": 1805, "place": "Invented County", "source_url": "https://example.invalid/will",
            "source_title": "Invented will book", "note": "Names sons including Isaac.",
            "profiles": {"Harrow-357": {"role": "Testator"}, "Harrow-14": {"role": "Son Isaac"}}}]


FINDINGS = {"schema_version": 1, "scope": "Invented.", "findings": [
    {"id": "will-reading", "found_on": "2026-10-23", "kind": "record", "finding": "The will names Isaac.",
     "status": "confirmed", "qualification": "Transcription only.", "people": [{"id": "Harrow-14", "name": "Isaac"}],
     "sources": [], "detail_url": "/people/harrow-14.html"}]}


def write(root: Path, relative: str, value) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


class GlasgowMigrationFixture(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.source = base / "checkout"
        write(self.source, "research/relationship_assessments.json", ASSESSMENTS)
        write(self.source, "research/relationship_probability_estimates.json", ESTIMATES)
        write(self.source, "research/canonical_records.json", RECORDS)
        write(self.source, "research/latest-findings.json", FINDINGS)
        subprocess.run(["git", "init", "-q", str(self.source)], check=True)
        subprocess.run(["git", "-C", str(self.source), "add", "-A"], check=True)
        subprocess.run(["git", "-C", str(self.source), "-c", "user.email=t@example.invalid", "-c", "user.name=t",
                        "commit", "-qm", "fixture"], check=True)
        self.project = base / "project"
        self.project.mkdir()
        (self.project / "genealogy.toml").write_text(
            '[project]\nname = "Invented"\n[storage]\ndatabase = "private/db.sqlite"\n'
            f'[storage.asset_roots]\nrepository = "{self.source}"\n', encoding="utf-8")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def migrate(self) -> dict:
        with open_project(self.project, create=True) as project:
            return workbench_migrate.Migration(project, self.source).run(["records", "relationships", "findings"])

    def test_stale_reverse_view_is_reconciled_without_choosing_by_order_or_size(self) -> None:
        report = self.migrate()
        resolutions = {(row["assertion_id"], row["resolution"][:5]) for row in report["reconciliation"]}
        self.assertEqual(resolutions, {("C-test-isaac-father", "stale"), ("C-test-brothers", "diffe")})
        self.assertEqual(report["conflicts"], [])
        with open_project(self.project) as project:
            research = Research(project.store)
            claim = research.find_external("glasgow-assertion", "C-test-isaac-father")[0]
            self.assertEqual([h["estimate_percent"] for h in research.assessment_history(claim)], [44, 95])
            father = research.find_external("wikitree", "Harrow-357")[0]
            view = next(v for v in research.relationship_views(father) if v["claim_id"] == claim)
            self.assertEqual((view["role"], view["assessment"]["estimate_percent"]), ("child", 95))
            # The sole estimate is adopted; the different proposition is its own claim, flagged for review.
            ann = research.find_external("glasgow-assertion", "C-test-ann-father")[0]
            self.assertEqual(research.current_assessment(ann)["estimate_percent"], 80)
            self.assertEqual(len(research.review_queue()), 1)
            self.assertEqual(project.store.one("SELECT count(*) n FROM claim WHERE kind='relationship'")["n"], 4)

    def test_rerun_is_idempotent_and_a_changed_legacy_value_becomes_a_new_revision(self) -> None:
        self.migrate()
        with open_project(self.project) as project:
            before = project.store.one("SELECT count(*) n FROM assessment_revision")["n"]
        self.migrate()
        with open_project(self.project) as project:
            self.assertEqual(project.store.one("SELECT count(*) n FROM assessment_revision")["n"], before)
        changed = json.loads(json.dumps(ASSESSMENTS))
        changed[0]["probability"]["value"] = 0.9
        changed[0]["assessment_date"] = "2026-10-24"
        write(self.source, "research/relationship_assessments.json", changed)
        self.migrate()
        with open_project(self.project) as project:
            research = Research(project.store)
            claim = research.find_external("glasgow-assertion", "C-test-isaac-father")[0]
            self.assertEqual([h["estimate_percent"] for h in research.assessment_history(claim)], [44, 95, 90])

    def test_changed_records_and_findings_catch_up_unless_edited_in_the_database(self) -> None:
        self.migrate()
        records = json.loads(json.dumps(RECORDS))
        records[0]["note"] = "Names sons Isaac and Caleb."
        findings = json.loads(json.dumps(FINDINGS))
        findings["findings"][0]["status"] = "qualified"
        write(self.source, "research/canonical_records.json", records)
        write(self.source, "research/latest-findings.json", findings)
        report = self.migrate()
        self.assertEqual(dict(report["refreshed"]), {"record": 1, "finding": 1})
        with open_project(self.project) as project:
            record = Research(project.store).find_external("glasgow-record", "will-1805")[0]
            self.assertEqual(project.store.get("record", record)["summary"], "Names sons Isaac and Caleb.")
            finding = Research(project.store).find_external("glasgow-finding", "will-reading")[0]
            self.assertEqual(project.store.get("finding", finding)["status"], "qualified")
            with project.store.write(actor="researcher", tool="genealogy finding") as tx:
                tx.update("finding", finding, {"limitations": "Recorded in the database"})
        findings["findings"][0]["finding"] = "The will names Isaac and Caleb."
        write(self.source, "research/latest-findings.json", findings)
        report = self.migrate()
        self.assertEqual([c["reason"][:39] for c in report["conflicts"]],
                         ["the legacy input changed after this row"])
        with open_project(self.project) as project:
            self.assertEqual(project.store.get("finding", finding)["statement"], "The will names Isaac.")

    def test_catch_up_keeps_the_views_equal_to_the_edited_legacy_file(self) -> None:
        self.migrate()
        changed = json.loads(json.dumps(ASSESSMENTS))
        changed[2]["probability"]["value"] = 0.8
        changed[2]["basis"] = "Shared household and a later deed."
        estimates = json.loads(json.dumps(ESTIMATES))
        estimates["estimates"][4]["percent"] = 80
        write(self.source, "research/relationship_assessments.json", changed)
        write(self.source, "research/relationship_probability_estimates.json", estimates)
        self.migrate()
        with open_project(self.project) as project:
            files = workbench_legacy_views.Views(project.store).files()
        self.assertEqual(json.loads(files["research/relationship_assessments.json"]), changed)

    def test_a_hand_edited_registry_does_not_override_a_database_assessment(self) -> None:
        self.migrate()
        with open_project(self.project) as project:
            research = Research(project.store)
            claim = research.find_external("glasgow-assertion", "C-test-brothers")[0]
            with project.store.write(actor="researcher", tool="genealogy assess") as tx:
                research.assess(tx, claim, expected_revision=1, status="proved", estimate_percent=90,
                                estimate_kind="subjective", reasoning="Baptisms name both parents.")
        edited = json.loads(json.dumps(ASSESSMENTS))
        edited[2]["probability"]["value"] = 0.5
        write(self.source, "research/relationship_assessments.json", edited)
        report = self.migrate()
        self.assertTrue(any("edited by hand" in c["reason"] for c in report["conflicts"]))
        with open_project(self.project) as project:
            self.assertEqual(Research(project.store).current_assessment(claim)["estimate_percent"], 90)

    def test_legacy_views_round_trip_and_correct_only_the_stale_row(self) -> None:
        self.migrate()
        with open_project(self.project) as project:
            files = workbench_legacy_views.Views(project.store).files()
        self.assertEqual(json.loads(files["research/relationship_assessments.json"]), ASSESSMENTS)
        rows = json.loads(files["research/relationship_probability_estimates.json"])["estimates"]
        self.assertEqual([row["percent"] for row in rows], [95, 95, 80, 80, 74, 17])
        self.assertEqual(rows[1]["assessment_history"][-1]["percent"], 44)
        self.assertEqual([row for i, row in enumerate(rows) if i != 1],
                         [row for i, row in enumerate(ESTIMATES["estimates"]) if i != 1])

    def test_reassessment_in_the_database_flows_to_both_legacy_directions(self) -> None:
        self.migrate()
        with open_project(self.project) as project:
            research = Research(project.store)
            claim = research.find_external("glasgow-assertion", "C-test-isaac-father")[0]
            with project.store.write(actor="researcher", tool="genealogy assess") as tx:
                research.assess(tx, claim, expected_revision=2, status="probable", grade="probable",
                                estimate_percent=85, estimate_kind="subjective", reasoning="A rival Isaac emerged.",
                                assessed_on="2026-10-25")
            files = workbench_legacy_views.Views(project.store).files()
        rows = [row for row in json.loads(files["research/relationship_probability_estimates.json"])["estimates"]
                if row["assertion_id"] == "C-test-isaac-father"]
        self.assertEqual({row["percent"] for row in rows}, {85})
        assessment = json.loads(files["research/relationship_assessments.json"])[0]
        self.assertEqual((assessment["status"], assessment["probability"]["value"]), ("probable", 0.85))
        self.assertEqual(assessment["assessment_history"][-1]["probability_percent"], 95)


if __name__ == "__main__":
    unittest.main()
