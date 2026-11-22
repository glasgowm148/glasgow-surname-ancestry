"""Fictional evidence contracts and offline, receipt-backed controller regressions."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from tools import research_batch as batch
from tools import research_batch_contract as contract


def packet():
    return {
        "format": "research-evidence-packet", "format_version": 1, "task_id": "fictional",
        "subjects": [{"id": "ada"}],
        "records": [{"id": "register", "revision": 2, "locator": "Fictional register, folio 7",
                     "text": "Ada Vale; co-parent Eli Reed; baptised 2 March 1801.",
                     "roles": [
                         {"id": "name", "kind": "name", "subject_id": "ada", "literal": "Ada Vale"},
                         {"id": "coparent", "kind": "coparent", "subject_id": "ada", "literal": "Eli Reed"},
                         {"id": "baptism", "kind": "baptism", "subject_id": "ada", "literal": "2 March 1801"}]}],
        "requested_fields": [
            {"id": "name", "subject_id": "ada", "field": "recorded_name"},
            {"id": "baptism", "subject_id": "ada", "field": "baptism_date"},
            {"id": "spouse", "subject_id": "ada", "field": "recorded_spouse"}],
    }


def field(ident="name"):
    kind, literal, normalized = {
        "name": ("recorded_name", "Ada Vale", "Ada Vale"),
        "baptism": ("baptism_date", "2 March 1801", "1801-03-02"),
        "spouse": ("recorded_spouse", "Eli Reed", "Eli Reed"),
    }[ident]
    return {"field_id": ident, "subject_id": "ada", "field": kind,
            "record_id": "register", "record_revision": 2,
            "role_id": "coparent" if ident == "spouse" else ident,
            "locator": "Fictional register, folio 7", "literal": literal, "normalized": normalized}


def extraction():
    return {"task_id": "fictional", "extracted_fields": [field(), field("baptism")],
            "missing_fields": [{"field_id": "spouse", "reason": "Only a co-parent is recorded."}],
            "contradictions": []}


def decision(ident, action="accept", replacement=None):
    return {"field_id": ident, "decision": action, "reason": "Checked the typed source quotation.",
            "corrected_field": replacement}


def review():
    return {"task_id": "fictional", "verdict": "accept", "field_decisions": [
        decision("name"), decision("baptism"), decision("spouse", "unresolved")]}


def save(path, value):
    path.write_text(json.dumps(value), encoding="utf-8")


def event(response):
    return json.dumps({"type": "text", "sessionID": "offline-session",
                       "part": {"type": "text", "text": json.dumps(response)}}) + "\n"


def hold_precondition():
    previous = {"subject_id": "ada", "catalogue_id": "ada-draft",
                "creation_status": "hold_source_verification", "status": "ready",
                "hold_condition": "Inspect the original register heading."}
    proposed = {**previous, "creation_status": "creation_ready", "hold_release": {
        "previous_row_sha256": contract.digest(previous),
        "condition": previous["hold_condition"], "decision": "satisfied",
        "reason": "The fictional heading was inspected.", "reviewed_by": "fictional-reviewer",
        "evidence": [{"record_id": "register", "revision": 2, "locator": "Fictional register, folio 7"}]}}
    return {"id": "release", "kind": "hold_release", "previous": previous, "proposed": proposed}


def failed_preconditions():
    unsupported = hold_precondition()
    del unsupported["proposed"]["hold_release"]
    stale = hold_precondition()
    stale["proposed"]["hold_release"]["evidence"][0]["revision"] = 1
    spoofed = hold_precondition()
    spoofed["status_field"] = "status"
    del spoofed["proposed"]["hold_release"]
    return {
        "duplicate_subject": {"id": "creations", "kind": "creation_subjects", "new_people": [
            {"subject_id": "ada", "catalogue_id": "ada-draft"},
            {"subject_id": " ADA ", "catalogue_id": "second-draft"}]},
        "conflicting_pid": {"id": "matches", "kind": "familysearch_matches", "people": {
            "ada-draft": {"id": "TEST-123", "confidence": "high"},
            "eli-draft": {"id": "TEST-123", "confidence": "medium"}}},
        "unsupported_release": unsupported,
        "stale_release": stale,
        "spoofed_status": spoofed,
        "malformed_hold": {**hold_precondition(), "previous": []},
        "malformed_proposed_hold": {**hold_precondition(), "proposed": []},
        "malformed_creation_rows": {"id": "creations", "kind": "creation_subjects", "new_people": ""},
        "malformed_creation_aliases": {"id": "creations", "kind": "creation_subjects",
                                       "new_people": [{"subject_id": "ada"}], "canonical_aliases": ["ada"]},
    }


class EvidenceContractTests(unittest.TestCase):
    def test_partial_name_substring_is_not_a_supported_name(self):
        evidence, proposed = packet(), field()
        evidence["records"][0]["text"] = evidence["records"][0]["text"].replace("Ada Vale", "Joanne Vale")
        evidence["records"][0]["roles"][0]["literal"] = "Joanne Vale"
        proposed.update(literal="Joanne Vale", normalized="Joanne")
        contract.validate_packet(evidence)
        contract.validate_field(evidence, proposed)
        proposed["normalized"] = "Anne"
        with self.assertRaisesRegex(ValueError, "not supported"):
            contract.validate_field(evidence, proposed)

    def test_list_or_dict_field_ids_raise_value_error_at_contract_boundaries(self):
        for ident in (["name"], {"id": "name"}):
            for boundary in ("packet", "field", "extracted", "missing", "review", "correction"):
                with self.subTest(ident=ident, boundary=boundary), self.assertRaises(ValueError):
                    evidence, response, reviewer = packet(), extraction(), review()
                    if boundary == "packet":
                        evidence["requested_fields"][0]["id"] = ident
                        contract.validate_packet(evidence)
                    elif boundary == "field":
                        contract.validate_field(evidence, {**field(), "field_id": ident})
                    elif boundary == "extracted":
                        response["extracted_fields"][0]["field_id"] = ident
                        contract.validate_extraction(evidence, response)
                    elif boundary == "missing":
                        response["missing_fields"][0]["field_id"] = ident
                        contract.validate_extraction(evidence, response)
                    else:
                        if boundary == "review":
                            reviewer["field_decisions"][0]["field_id"] = ident
                        else:
                            reviewer["field_decisions"][0] = decision(
                                "name", "correct", {**field(), "field_id": ident})
                        contract.review_proposal(evidence, response, reviewer)

    def test_accepting_reviewer_cannot_make_failed_preconditions_ready(self):
        for fault, condition in failed_preconditions().items():
            with self.subTest(fault=fault):
                evidence = packet()
                evidence["preconditions"] = [condition]
                proposal = contract.review_proposal(evidence, extraction(), review())
                self.assertEqual(proposal["status"], "withheld_proposal")
                self.assertIs(proposal["preconditions"]["passed"], False)
                self.assertEqual([row["precondition_id"] for row in proposal["preconditions"]["issues"]],
                                 [condition["id"]])
                self.assertIs(proposal["application_enabled"], False)

    def test_supported_fields_and_explicit_absence_survive_review(self):
        proposal = contract.review_proposal(packet(), extraction(), review())
        self.assertEqual([row["normalized"] for row in proposal["suggested_fields"]],
                         ["Ada Vale", "1801-03-02"])
        self.assertEqual([row["field_id"] for row in proposal["withheld_fields"]], ["spouse"])
        self.assertEqual(proposal["status"], "reviewed_proposal")
        self.assertTrue(proposal["documentary_scope_only"])
        self.assertIs(proposal["application_enabled"], False)

    def test_coparent_cannot_become_spouse_even_when_name_is_literal(self):
        response = extraction()
        response["missing_fields"] = []
        response["extracted_fields"].append(field("spouse"))
        checks = contract.validate_extraction(packet(), response)
        self.assertEqual([row["field_id"] for row in checks["field_issues"]], ["spouse"])
        self.assertNotIn("spouse", [row["field_id"] for row in checks["valid_fields"]])
        reviewer = review()
        reviewer["field_decisions"][-1] = decision("spouse")
        with self.assertRaisesRegex(ValueError, "invalid"):
            contract.review_proposal(packet(), response, reviewer)

    def test_baptism_cannot_become_birth(self):
        evidence, proposed = packet(), field("baptism")
        evidence["requested_fields"][1]["field"] = proposed["field"] = "birth_date"
        with self.assertRaisesRegex(ValueError, "role"):
            contract.validate_field(evidence, proposed)

    def test_stale_missing_or_misquoted_evidence_is_blocked(self):
        for change in ({"record_revision": 1}, {"record_revision": True},
                       {"record_id": "missing"}, {"locator": "folio 8"},
                       {"literal": "Ada Reed", "normalized": "Ada Reed"},
                       {"normalized": "Eli Reed"}, {"role_id": "missing"}):
            with self.subTest(change=change):
                response = extraction()
                response["extracted_fields"][0].update(change)
                checks = contract.validate_extraction(packet(), response)
                self.assertEqual([row["field_id"] for row in checks["field_issues"]], ["name"])
                with self.assertRaisesRegex(ValueError, "invalid"):
                    contract.review_proposal(packet(), response, review())

    def test_invalid_dates_and_invented_normalization_are_blocked(self):
        for literal, normalized in (("31 February 1801", "1801-02-28"),
                                    ("1801-02-29", "1801-02-29"),
                                    ("about 2 March 1801", "1801-03-02"),
                                    ("1801", "1801-01-01"),
                                    ("2 March 1801", "1801-03-03")):
            with self.subTest(literal=literal, normalized=normalized):
                evidence, proposed = packet(), field("baptism")
                evidence["records"][0].update(text=literal)
                evidence["records"][0]["roles"] = [{
                    "id": "baptism", "kind": "baptism", "subject_id": "ada", "literal": literal}]
                proposed.update(literal=literal, normalized=normalized)
                contract.validate_packet(evidence)
                with self.assertRaises(ValueError):
                    contract.validate_field(evidence, proposed)

    def test_qualified_source_date_cannot_be_made_exact_by_shortening_quote(self):
        evidence = packet()
        evidence["records"][0]["text"] = evidence["records"][0]["text"].replace(
            "2 March 1801", "about 2 March 1801")
        evidence["records"][0]["roles"][2]["literal"] = "about 2 March 1801"
        contract.validate_packet(evidence)
        with self.assertRaises(ValueError):
            contract.validate_field(evidence, field("baptism"))

    def test_shortened_literals_cannot_change_a_name_or_day(self):
        evidence = packet()
        evidence["records"][0]["text"] = "Joanne Vale; baptised 12 March 1801."
        evidence["records"][0]["roles"] = [
            {"id": "name", "kind": "name", "subject_id": "ada", "literal": "Joanne Vale"},
            {"id": "baptism", "kind": "baptism", "subject_id": "ada", "literal": "12 March 1801"}]
        contract.validate_packet(evidence)
        for proposed in ({**field(), "literal": "anne", "normalized": "Anne"}, field("baptism")):
            with self.subTest(field=proposed["field"]), self.assertRaisesRegex(ValueError, "complete"):
                contract.validate_field(evidence, proposed)

    def test_all_exact_date_alternatives_and_qualifiers_are_withheld(self):
        for literal in ("2 March 1801 or 3 March 1801", "ca. 2 March 1801", "2 March 1801?",
                        "before 2 March 1801", "2/3 March 1801"):
            evidence = packet()
            evidence["records"][0]["text"] = literal
            evidence["records"][0]["roles"] = [{
                "id": "baptism", "kind": "baptism", "subject_id": "ada", "literal": literal}]
            proposed = {**field("baptism"), "literal": literal}
            with self.subTest(literal=literal), self.assertRaises(ValueError):
                contract.validate_field(evidence, proposed)

    def test_curated_role_quote_must_itself_exist_in_source(self):
        evidence = packet()
        evidence["records"][0]["roles"][0]["literal"] = "Ada Reed"
        with self.assertRaisesRegex(ValueError, "literal source"):
            contract.validate_packet(evidence)

    def test_extractor_must_decide_each_requested_id_exactly_once(self):
        for fault in ("omitted", "duplicate", "extracted_and_missing", "unknown"):
            with self.subTest(fault=fault):
                response = extraction()
                if fault == "omitted":
                    response["missing_fields"] = []
                elif fault == "duplicate":
                    response["extracted_fields"].append(field())
                elif fault == "extracted_and_missing":
                    response["missing_fields"].append({"field_id": "name", "reason": "absent"})
                else:
                    response["missing_fields"].append({"field_id": "other", "reason": "absent"})
                with self.assertRaises(ValueError):
                    contract.validate_extraction(packet(), response)

    def test_reviewer_must_decide_each_requested_id_exactly_once(self):
        for fault in ("omitted", "duplicate", "unknown", "accept_absence"):
            with self.subTest(fault=fault):
                reviewer = review()
                if fault == "omitted":
                    reviewer["field_decisions"].pop()
                elif fault == "duplicate":
                    reviewer["field_decisions"].append(decision("name"))
                elif fault == "unknown":
                    reviewer["field_decisions"][-1]["field_id"] = "other"
                else:
                    reviewer["field_decisions"][-1] = decision("spouse")
                with self.assertRaises(ValueError):
                    contract.review_proposal(packet(), extraction(), reviewer)

    def test_correction_requires_explicit_valid_replacement_and_role(self):
        response = extraction()
        response["extracted_fields"][0]["normalized"] = "Invented Name"
        for replacement in (None, {"normalized": "Ada Vale"},
                            {**field(), "role_id": "coparent"},
                            {**field(), "record_revision": 1}, field("baptism")):
            with self.subTest(replacement=replacement):
                reviewer = review()
                reviewer.update(verdict="revise", reasons=["Read Ada Vale instead."])
                reviewer["field_decisions"][0] = decision("name", "correct", replacement)
                with self.assertRaises(ValueError):
                    contract.review_proposal(packet(), response, reviewer)
        reviewer["field_decisions"][0] = decision("name", "correct", field())
        proposal = contract.review_proposal(packet(), response, reviewer)
        self.assertEqual(proposal["suggested_fields"][0], field())

    def test_hidden_replacements_and_prose_only_revision_cannot_accept_blocked_field(self):
        response = extraction()
        response["extracted_fields"][0]["normalized"] = "Invented Name"
        for action in ("accept", "reject", "unresolved"):
            with self.subTest(action=action):
                reviewer = review()
                reviewer["field_decisions"][0] = decision("name", action, field())
                with self.assertRaises(ValueError):
                    contract.review_proposal(packet(), response, reviewer)
        reviewer = review()
        reviewer.update(verdict="revise", reasons=["Replace invented name with Ada Vale."])
        with self.assertRaisesRegex(ValueError, "invalid"):
            contract.review_proposal(packet(), response, reviewer)

    def test_unresolved_overall_review_remains_withheld(self):
        for verdict in ("unresolved", "insufficient_packet"):
            reviewer = review()
            reviewer["verdict"] = verdict
            proposal = contract.review_proposal(packet(), extraction(), reviewer)
            self.assertEqual(proposal["status"], "withheld_proposal")
            self.assertIs(proposal["application_enabled"], False)


class BatchControllerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="test-research-batch-")
        self.addCleanup(self.temp.cleanup)
        # macOS's default temp path may start with the /var -> /private/var alias.
        self.root = Path(self.temp.name).resolve()
        self.assertNotIn(batch.PROJECT, self.root.parents)
        self.source = self.root / "input.json"
        save(self.source, packet())
        self.run = self.root / "run"
        self.calls = []
        self.which = patch.object(batch.shutil, "which", return_value="/mock/opencode")
        self.which.start()
        self.addCleanup(self.which.stop)
        # Fail closed if a future controller change ignores the injected runner.
        self.process = patch.object(batch.subprocess, "Popen", side_effect=AssertionError("Real process forbidden"))
        self.process.start()
        self.addCleanup(self.process.stop)

    def runner(self, command, *, cwd, env, timeout):
        payload = json.loads(Path(command[command.index("--file") + 1]).read_text())
        self.calls.append({"command": command, "cwd": cwd, "env": env,
                           "timeout": timeout, "payload": payload})
        response = review() if "evidence_packet" in payload else extraction()
        return 0, event(response), "offline diagnostic\n"

    def prepare(self):
        return batch.prepare(self.source, self.run)

    def assert_precondition_blocks_extract(self, fault, reason):
        evidence = packet()
        condition = failed_preconditions()[fault]
        evidence["preconditions"] = [condition]
        save(self.source, evidence)
        manifest = self.prepare()
        self.assertIs(manifest["preconditions"]["passed"], False)
        checks = batch.extract(self.run, runner=self.runner)
        self.assertEqual(checks["status"], "blocked_preconditions")
        self.assertEqual(checks["preconditions"]["issues"][0]["precondition_id"], condition["id"])
        self.assertRegex(checks["preconditions"]["issues"][0]["reason"], reason)
        self.assertIs(checks["application_enabled"], False)
        self.assertEqual(json.loads((self.run / "field-checks.json").read_text()), checks)
        self.assertFalse((self.run / "extract-started.json").exists())
        self.assertEqual(self.calls, [])

    def test_duplicate_creation_subjects_block_extract_before_runner(self):
        self.assert_precondition_blocks_extract("duplicate_subject", "Duplicate canonical subject_id")

    def test_conflicting_familysearch_pid_blocks_extract_before_runner(self):
        self.assert_precondition_blocks_extract("conflicting_pid", "PID assigned to distinct")

    def test_unsupported_hold_release_blocks_extract_before_runner(self):
        self.assert_precondition_blocks_extract("unsupported_release", "evidence receipt")

    def test_stale_hold_release_evidence_blocks_extract_before_runner(self):
        self.assert_precondition_blocks_extract("stale_release", "missing or stale")

    def test_spoof_status_field_cannot_bypass_held_creation_state(self):
        self.assert_precondition_blocks_extract("spoofed_status", "actual existing held status")

    def test_malformed_preconditions_are_reported_without_a_model_request(self):
        for fault, reason in (("malformed_hold", "rows must be objects"),
                              ("malformed_proposed_hold", "rows must be objects"),
                              ("malformed_creation_rows", "must be an array"),
                              ("malformed_creation_aliases", "must be an object")):
            with self.subTest(fault=fault):
                self.run = self.root / fault
                self.assert_precondition_blocks_extract(fault, reason)

    def test_review_rejects_failed_preconditions_before_runner_or_receipt_access(self):
        for fault, condition in failed_preconditions().items():
            with self.subTest(fault=fault):
                evidence = packet()
                evidence["preconditions"] = [condition]
                save(self.source, evidence)
                run = self.root / fault
                batch.prepare(self.source, run)
                with self.assertRaisesRegex(ValueError, "preconditions failed; review cannot override"):
                    batch.review(run, runner=self.runner)
                self.assertFalse((run / "review-started.json").exists())
        self.assertEqual(self.calls, [])

    def test_valid_frozen_preconditions_allow_extract_and_review(self):
        evidence = packet()
        evidence["preconditions"] = [
            {"id": "creations", "kind": "creation_subjects", "new_people": [
                {"subject_id": "ada", "catalogue_id": "ada-draft"}]},
            {"id": "matches", "kind": "familysearch_matches", "people": {
                "ada-draft": {"id": "TEST-123", "confidence": "high"}}},
            hold_precondition()]
        save(self.source, evidence)
        manifest = self.prepare()
        self.assertIs(manifest["preconditions"]["passed"], True)
        self.assertEqual(batch.extract(self.run, runner=self.runner)["field_issues"], [])
        proposal = batch.review(self.run, runner=self.runner)
        self.assertEqual(proposal["status"], "reviewed_proposal")
        self.assertIs(proposal["preconditions"]["passed"], True)
        self.assertEqual(proposal["preconditions"]["issues"], [])
        self.assertEqual(len(self.calls), 2)

    def test_prepare_freezes_packet_and_refuses_overwrite(self):
        manifest = self.prepare()
        frozen = (self.run / "packet.json").read_bytes()
        canonical = json.dumps(packet(), sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
        self.assertEqual(manifest["packet_sha256"], hashlib.sha256(canonical).hexdigest())
        changed = packet()
        changed["records"][0]["revision"] = 3
        save(self.source, changed)
        self.assertEqual((self.run / "packet.json").read_bytes(), frozen)
        with self.assertRaisesRegex(ValueError, "empty"):
            self.prepare()
        self.assertEqual((self.run / "packet.json").read_bytes(), frozen)
        self.assertEqual(self.calls, [])

    def test_extract_and_review_use_isolated_runner_and_reuse_receipts(self):
        self.prepare()
        with patch.dict(batch.os.environ, {"OPENCODE_CONFIG": "/fictional/ambient.json"}):
            checks = batch.extract(self.run, runner=self.runner, timeout=13)
            proposal = batch.review(self.run, runner=self.runner, timeout=17)
        self.assertEqual(checks["field_issues"], [])
        self.assertEqual(proposal["suggested_fields"][0]["normalized"], "Ada Vale")
        self.assertEqual(batch.extract(self.run, runner=self.runner), checks)
        self.assertEqual(batch.review(self.run, runner=self.runner), proposal)
        self.assertEqual(len(self.calls), 2)
        for call, timeout in zip(self.calls, (13, 17)):
            self.assertEqual(call["timeout"], timeout)
            self.assertNotIn(batch.PROJECT, Path(call["cwd"]).parents)
            self.assertNotIn("OPENCODE_CONFIG", call["env"])
            config = json.loads(call["env"]["OPENCODE_CONFIG_CONTENT"])
            self.assertEqual(config["agent"]["batch-packet"]["permission"], {"*": "deny"})
            self.assertIs(config["mcp"]["mac-mcp"]["enabled"], False)
        for stage in ("extract", "review"):
            receipt = json.loads((self.run / f"{stage}-receipt.json").read_text())
            self.assertEqual(receipt["status"], "completed")
            self.assertEqual(receipt["session_ids"], ["offline-session"])
        self.assertIs(proposal["application_enabled"], False)

    def test_tampered_packet_is_rejected_before_runner(self):
        self.prepare()
        changed = packet()
        changed["records"][0]["revision"] = 3
        save(self.run / "packet.json", changed)
        with self.assertRaisesRegex(ValueError, "changed"):
            batch.extract(self.run, runner=self.runner)
        self.assertEqual(self.calls, [])

    def test_tampered_response_is_rejected_for_replay_and_review(self):
        self.prepare()
        batch.extract(self.run, runner=self.runner)
        changed = extraction()
        changed["extracted_fields"][0]["normalized"] = "Ada"
        save(self.run / "extract-response.json", changed)
        for operation in (batch.extract, batch.review):
            with self.subTest(operation=operation.__name__), self.assertRaisesRegex(ValueError, "changed|receipt"):
                operation(self.run, runner=self.runner)
        self.assertEqual(len(self.calls), 1)

    def test_tampered_review_response_is_rejected_on_replay(self):
        self.prepare()
        batch.extract(self.run, runner=self.runner)
        batch.review(self.run, runner=self.runner)
        changed = review()
        changed["verdict"] = "unresolved"
        save(self.run / "review-response.json", changed)
        with self.assertRaisesRegex(ValueError, "changed"):
            batch.review(self.run, runner=self.runner)
        self.assertEqual(len(self.calls), 2)

    def test_failed_model_execution_is_receipted_and_never_silently_retried(self):
        for failure in ("exit", "tool", "bad_json", "wrong_task", "timeout"):
            with self.subTest(failure=failure):
                run = self.root / failure
                batch.prepare(self.source, run)
                calls = []

                def failed(command, *, cwd, env, timeout):
                    calls.append(command)
                    if failure == "timeout":
                        raise subprocess.TimeoutExpired(command, timeout)
                    if failure == "exit":
                        return 1, event(extraction()), "failed"
                    if failure == "tool":
                        return 0, json.dumps({"type": "tool_use"}) + "\n" + event(extraction()), ""
                    if failure == "bad_json":
                        return 0, json.dumps({"type": "text", "part": {"text": "not JSON"}}), ""
                    return 0, event({"task_id": "different-task"}), ""

                with self.assertRaises((ValueError, subprocess.TimeoutExpired)):
                    batch.extract(run, runner=failed)
                receipt = json.loads((run / "extract-receipt.json").read_text())
                self.assertEqual(receipt["status"], "failed")
                with self.assertRaisesRegex(ValueError, "Previous stage failed"):
                    batch.extract(run, runner=failed)
                self.assertEqual(len(calls), 1)

    def test_completed_but_incomplete_extraction_fails_without_another_model_call(self):
        self.prepare()
        calls = []

        def incomplete(command, *, cwd, env, timeout):
            calls.append(command)
            response = extraction()
            response["missing_fields"] = []
            return 0, event(response), ""

        for _ in range(2):
            with self.assertRaisesRegex(ValueError, "Every requested field"):
                batch.extract(self.run, runner=incomplete)
        self.assertEqual(len(calls), 1)

    def test_uncertain_started_stage_never_retries(self):
        self.prepare()
        save(self.run / "extract-started.json", {"stage": "extract"})
        with self.assertRaisesRegex(ValueError, "uncertain"):
            batch.extract(self.run, runner=self.runner)
        self.assertEqual(self.calls, [])

    def test_output_refuses_source_directories_and_symlink_ancestors(self):
        project = self.root / "project"
        project.mkdir()
        with patch.object(batch, "PROJECT", project):
            for name in ("research", "data", "www", "surname-research", "vendor", "tools", "tests", ".git"):
                with self.subTest(name=name), self.assertRaisesRegex(ValueError, "overwrite"):
                    batch.prepare(self.source, project / name / "run")
        alias = self.root / "alias"
        alias.symlink_to(self.root, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "symlink"):
            batch.prepare(self.source, alias / "run")

    def test_output_dotdot_cannot_bypass_source_directory_guard(self):
        project = self.root / "project"
        (project / "scratch").mkdir(parents=True)
        (project / "tools").mkdir()
        with patch.object(batch, "PROJECT", project), self.assertRaisesRegex(ValueError, "overwrite"):
            batch.prepare(self.source, project / "scratch" / ".." / "tools" / "run")

    def test_apply_is_disabled_even_without_a_run_directory(self):
        with patch("sys.stderr") as stderr:
            self.assertEqual(batch.main(["apply", str(self.root / "absent")]), 2)
        self.assertIn("application is disabled", "".join(call.args[0] for call in stderr.write.call_args_list))
        self.assertEqual(self.calls, [])

    def test_same_run_is_locked_while_distinct_workers_can_progress(self):
        self.prepare()
        other = self.root / "other"
        batch.prepare(self.source, other)
        entered, release = threading.Event(), threading.Event()

        def held_runner(command, *, cwd, env, timeout):
            entered.set()
            if not release.wait(5):
                raise AssertionError("Test did not release first worker")
            return 0, event(extraction()), ""

        with ThreadPoolExecutor(max_workers=2) as workers:
            first = workers.submit(batch.extract, self.run, runner=held_runner)
            try:
                self.assertTrue(entered.wait(5), "First worker never entered runner")
                with self.assertRaisesRegex(ValueError, "Another controller"):
                    batch.extract(self.run, runner=self.runner)
                second = workers.submit(batch.extract, other, runner=self.runner)
                self.assertEqual(second.result(timeout=5)["field_issues"], [])
            finally:
                release.set()
            self.assertEqual(first.result(timeout=5)["field_issues"], [])


class BatchInterruptionTests(unittest.TestCase):
    def test_interrupt_terminates_active_batch_subprocess(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            packet_path = root / "input.json"
            save(packet_path, packet())
            run = root / "run"
            batch.prepare(packet_path, run)
            pid_file = root / "stub-pid"
            opencode = root / "opencode"
            opencode.write_text(
                f"#!{sys.executable}\n"
                "from pathlib import Path\n"
                "import os, time\n"
                "pid_file = Path(os.environ['RESEARCH_TEST_PID_FILE'])\n"
                "pending = pid_file.with_suffix('.tmp')\n"
                "pending.write_text(str(os.getpid()))\n"
                "pending.replace(pid_file)\n"
                "time.sleep(30)\n",
                encoding="utf-8",
            )
            opencode.chmod(0o700)
            env = {**os.environ, "PATH": f"{root}{os.pathsep}{os.environ.get('PATH', '')}",
                   "RESEARCH_TEST_PID_FILE": str(pid_file)}
            command = [sys.executable, "-m", "tools.research_batch", "batch", "--workers", "1", str(run)]
            with subprocess.Popen(command, cwd=batch.PROJECT, env=env, start_new_session=True,
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) as process:
                try:
                    deadline = time.monotonic() + 5
                    while not pid_file.exists() and process.poll() is None and time.monotonic() < deadline:
                        time.sleep(0.02)
                    self.assertTrue(pid_file.exists(), "Offline OpenCode stub did not start")
                    process.send_signal(signal.SIGINT)
                    _, stderr = process.communicate(timeout=4)
                    self.assertEqual(process.returncode, 130, stderr)
                    with self.assertRaises(ProcessLookupError):
                        os.kill(int(pid_file.read_text()), 0)
                    receipt = json.loads((run / "extract-receipt.json").read_text())
                    self.assertEqual(receipt["status"], "failed")
                    self.assertIn("interrupted", receipt["error"])
                finally:
                    if process.poll() is None:
                        process.kill()
                    if pid_file.exists():
                        try:
                            os.kill(int(pid_file.read_text()), signal.SIGKILL)
                        except ProcessLookupError:
                            pass


if __name__ == "__main__":
    unittest.main()
