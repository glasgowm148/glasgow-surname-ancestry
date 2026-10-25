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

from genealogy.store import Research, open_project, stable_id  # noqa: E402

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

    def test_rerun_is_idempotent_and_a_hand_edited_registry_is_not_applied(self) -> None:
        self.migrate()
        with open_project(self.project) as project:
            before = project.store.one("SELECT count(*) n FROM assessment_revision")["n"]
        self.migrate()
        with open_project(self.project) as project:
            self.assertEqual(project.store.one("SELECT count(*) n FROM assessment_revision")["n"], before)
        changed = json.loads(json.dumps(ASSESSMENTS))
        changed[0]["probability"]["value"] = 0.9
        write(self.source, "research/relationship_assessments.json", changed)
        records = json.loads(json.dumps(RECORDS))
        records[0]["note"] = "Edited by hand."
        write(self.source, "research/canonical_records.json", records)
        report = self.migrate()
        self.assertEqual(len(report["conflicts"]), 2)
        self.assertTrue(all("edited by hand" in item["reason"] for item in report["conflicts"]))
        with open_project(self.project) as project:
            research = Research(project.store)
            claim = research.find_external("glasgow-assertion", "C-test-isaac-father")[0]
            self.assertEqual([h["estimate_percent"] for h in research.assessment_history(claim)], [44, 95])
            record = research.find_external("glasgow-record", "will-1805")[0]
            self.assertEqual(project.store.get("record", record)["summary"], "Names sons including Isaac.")

    def test_editorial_presentation_still_catches_up(self) -> None:
        presentation = {"evidence_questions": [{"question": "Which Isaac does the will mean?", "answer": "Open."}]}
        write(self.source, "research/Harrow-14/presentation.json", presentation)
        self.migrate()
        with open_project(self.project) as project:
            workbench_migrate.Migration(project, self.source).run(["profiles"])
        presentation["evidence_questions"][0]["answer"] = "The 1786 Currituck Isaac."
        write(self.source, "research/Harrow-14/presentation.json", presentation)
        with open_project(self.project) as project:
            report = workbench_migrate.Migration(project, self.source).run(["profiles"])
            self.assertEqual(dict(report["refreshed"]), {"question": 1})
            question = stable_id("qst", "research/Harrow-14/presentation.json", 0)
            self.assertEqual(project.store.get("question", question)["resolves"], "The 1786 Currituck Isaac.")

    def test_documents_are_held_row_by_row_and_regenerated(self) -> None:
        import research_entry
        plan = {"case_id": "Harrow-14", "findings": [], "objective": "Find Isaac's father.",
                "questions": ["Who was Isaac's father?", {"question": "Was he born in 1786?", "status": "open"}],
                "web_searches": [{"query": "Currituck wills 1805", "result": "nothing found"}], "targets": ["will"]}
        queue = {"schema_version": 1, "updated_at": "2026-10-25",
                 "entries": {"Harrow-14": {"status": "OPEN", "summary": "Add the will."}}, "completed_live_profiles": []}
        write(self.source, "research/Harrow-14/research_plan.json", plan)
        write(self.source, "data/wikitree/profile-update-queue.json", queue)
        self.migrate()
        with open_project(self.project) as project:
            workbench_migrate.Migration(project, self.source).run(["profiles", "queue", "documents"])
            files = workbench_legacy_views.Views(project.store).files()
            self.assertEqual(json.loads(files["research/Harrow-14/research_plan.json"]), plan)
            self.assertEqual(json.loads(files["data/wikitree/profile-update-queue.json"]), queue)
            search = stable_id("sch", "research/Harrow-14/research_plan.json", 0)
            self.assertEqual(project.store.get("search", search)["outcome"], "negative")
        edited = json.loads(json.dumps(plan))
        edited["questions"].append("Did Isaac move to Tennessee?")
        write(self.source, "research/Harrow-14/research_plan.json", edited)
        with open_project(self.project) as project:
            report = workbench_migrate.Migration(project, self.source).run(["documents"])
            self.assertTrue(any("edited by hand" in c["reason"] for c in report["conflicts"]))
            revision = research_entry.document_revision(project, "research/Harrow-14/research_plan.json")
            research_entry.record_document(project, "research/Harrow-14/research_plan.json", edited,
                                           expected_revision=revision, actor="test", reason="new question")
            files = workbench_legacy_views.Views(project.store).files()
            self.assertEqual(json.loads(files["research/Harrow-14/research_plan.json"]), edited)
            added = stable_id("qst", "research/Harrow-14/research_plan.json", 2)
            self.assertEqual(project.store.get("question", added)["question"], "Did Isaac move to Tennessee?")
            from genealogy.store import StaleRevisionError
            with self.assertRaises(StaleRevisionError):
                research_entry.record_document(project, "research/Harrow-14/research_plan.json", plan,
                                               expected_revision=revision, actor="other", reason=None)
            shorter = {**edited, "questions": edited["questions"][:1]}
            research_entry.record_document(project, "research/Harrow-14/research_plan.json", shorter,
                                           expected_revision=revision + 1, actor="test", reason="questions answered")
            self.assertEqual(json.loads(workbench_legacy_views.Views(project.store).files()[
                "research/Harrow-14/research_plan.json"]), shorter)
            self.assertIsNotNone(project.store.get("question", added))   # kept, marked removed

    def test_entry_tool_records_rows_that_the_views_reproduce_exactly(self) -> None:
        import research_entry
        from genealogy.store import StaleRevisionError
        self.migrate()
        finding = {"id": "deed-reading", "found_on": "2026-10-26", "kind": "property",
                   "finding": "The 1729 deed names no predecessor.", "status": "qualified",
                   "qualification": "Original inspected.", "people": [{"id": "Harrow-357", "name": "William"}],
                   "sources": [], "detail_url": "/people/harrow-357.html"}
        record = {"record_id": "deed-1729", "association": "Deed of William Harrow", "date": "1729", "year": 1729,
                  "source_title": "Invented deed book", "source_url": "https://example.invalid/deed",
                  "note": "No predecessor named.", "profiles": {"Harrow-357": {"role": "Grantor"}}}
        vital = {"id": "william-357-death", "subject": "Harrow-357", "status": "approved", "reviewed": "2026-10-26",
                 "vitals": {"death": {"date": "1805", "place": "Invented County", "status": "probable",
                                      "note": "Will recorded 1806."}}}
        with open_project(self.project) as project:
            for kind, row in (("finding", finding), ("record", record), ("vital", vital)):
                result = research_entry.upsert(project, kind, row, expected_revision=None, actor="test", reason=None)
                self.assertTrue(result["created"])
            files = workbench_legacy_views.Views(project.store).files()
            self.assertEqual(json.loads(files["research/latest-findings.json"])["findings"][-1], finding)
            self.assertEqual(json.loads(files["research/canonical_records.json"])[-1], record)
            self.assertEqual(json.loads(files["research/vital_assessments.json"])["assessments"], [vital])
            changed = {**finding, "status": "confirmed"}
            with self.assertRaisesRegex(Exception, "expected-revision"):
                research_entry.upsert(project, "finding", changed, expected_revision=None, actor="test", reason=None)
            revision = research_entry.current_row(project, "finding", "deed-reading")[1]
            research_entry.upsert(project, "finding", changed, expected_revision=revision, actor="test", reason="re-read")
            with self.assertRaises(StaleRevisionError):
                research_entry.upsert(project, "finding", finding, expected_revision=revision, actor="other", reason=None)
            vital2 = json.loads(json.dumps(vital))
            vital2["vitals"]["death"]["status"] = "proved"
            research_entry.upsert(project, "vital", vital2, expected_revision=1, actor="test", reason=None)
            claim = stable_id("clm", "glasgow-vital", "william-357-death", "death")
            self.assertEqual([h["status"] for h in Research(project.store).assessment_history(claim)],
                             ["probable", "proved"])
            files = workbench_legacy_views.Views(project.store).files()
            self.assertEqual(json.loads(files["research/latest-findings.json"])["findings"][-1], changed)
            for relative, text in files.items():
                write(self.source, relative, json.loads(text))
        report = self.migrate()   # the regenerated files are current, not hand edits
        self.assertEqual(report["conflicts"], [], report["conflicts"])

    def test_publication_applies_the_privacy_level_policy(self) -> None:
        from genealogy.store import NameInput
        with open_project(self.project, create=True) as project:
            research = Research(project.store)
            people, events = {}, {}
            with project.store.write(actor="test", tool="genealogy import") as tx:
                tx.insert("import_batch", {"id": "imp-onetree", "adapter": "one-tree", "imported_at": "2026-10-25"})
                for name, level, access in (("Open-1", 60, "public"), ("Tree-35", 35, "public"),
                                            ("Closed-30", 30, "public"), ("Uncatalogued-2", 60, "private")):
                    person = research.create_person(tx, names=[NameInput(name)], living="deceased", access=access)
                    research.map_external(tx, person, "wikitree", name)
                    research.record_observation(tx, system="wikitree", external_value=name, entity_id=person,
                                                fields={"raw": {"Privacy": level}}, captured_on="2026-08-18")
                    events[name] = research.add_event(tx, kind="birth", participants=[(person, "principal")],
                                                      date_original="1801")
                    tx.insert("import_origin", {"entity_id": events[name], "import_batch_id": "imp-onetree",
                                                "input_path": "one-tree.json", "pointer": name})
                    people[name] = person
                finding = research.add_finding(tx, statement="Narrative about the Privacy 35 person.", access="public",
                                               links=[(people["Tree-35"], "subject")])
            report = workbench_migrate.Migration(project, self.source).run(["publication"])["steps"]["publication"]
            access = {name: project.store.get("event", event)["access"] for name, event in events.items()}
            self.assertEqual(access, {"Open-1": "public", "Tree-35": "public", "Closed-30": "private",
                                      "Uncatalogued-2": "private"})
            self.assertEqual(project.store.get("finding", finding)["access"], "private")
            self.assertEqual(report["published people below Privacy 35"], 1)

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
