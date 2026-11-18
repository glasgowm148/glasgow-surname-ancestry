import json
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import wikitree_family_export as exporter


def sample_profile(name: str, first_name: str) -> dict:
    return {
        "Name": name,
        "FirstName": first_name,
        "LastNameCurrent": "Example",
        "BirthDate": "1800-00-00",
        "BirthLocation": "Glasgow, Scotland",
        "DeathDate": "0000-00-00",
        "Bio": "A sourced clue https://example.org/record/1",
        "Parents": {},
        "Children": {},
        "Siblings": {},
        "Spouses": {},
        "FamilySearchPIDs": [],
        "FamilySearchBrowserSources": {},
    }


def sample_envelope() -> dict:
    subject = sample_profile("Example-1", "Alice")
    child = sample_profile("Example-2", "Bob")
    subject["Children"] = {"2": child}
    return {"items": [{"person": subject}]}


class FamilySearchCaptureTests(unittest.TestCase):
    pid = "9QMG-R4T"
    source = f"https://www.familysearch.org/en/tree/person/sources/{pid}/?lang=en"

    def capture(self, page):
        with tempfile.TemporaryDirectory() as directory:
            return exporter.scrape_familysearch_pid(page, self.pid, Path(directory), 0, 0, 0, 0)

    def test_cdp_reuses_and_closes_one_tab_even_after_a_pid_fails(self):
        envelope = sample_envelope()
        person = envelope["items"][0]["person"]
        person["FamilySearchPIDs"] = ["ABCD-123", self.pid]
        page = Mock()
        page.is_closed.return_value = False
        context = Mock()
        context.new_page.return_value = page
        sync = MagicMock()
        playwright = {"playwright.sync_api": SimpleNamespace(sync_playwright=sync)}
        with tempfile.TemporaryDirectory() as directory, patch.dict(sys.modules, playwright), \
             patch.object(exporter, "scrape_familysearch_pid", side_effect=[
                 exporter.ExportError("Unavailable"), {"status": "ok"},
             ]) as scrape:
            browser = sync.return_value.__enter__.return_value.chromium.connect_over_cdp.return_value
            browser.contexts = [context]
            exporter.scrape_familysearch_sources_via_cdp(
                envelope, "http://localhost:9333", Path(directory), 0, 0, 0, 0,
            )
        context.new_page.assert_called_once()
        page.close.assert_called_once()
        browser.close.assert_not_called()
        self.assertEqual([call.kwargs["page"] for call in scrape.call_args_list], [page, page])
        self.assertEqual(person["FamilySearchBrowserSources"][self.pid]["status"], "error")
        self.assertEqual(person["FamilySearchBrowserSources"]["ABCD-123"]["status"], "ok")

    def test_no_browser_connection_without_familysearch_targets(self):
        envelope = sample_envelope()
        sync = Mock()
        playwright = {"playwright.sync_api": SimpleNamespace(sync_playwright=sync)}
        with tempfile.TemporaryDirectory() as directory, patch.dict(sys.modules, playwright):
            output = Path(directory)
            exporter.scrape_familysearch_sources_via_cdp(envelope, "http://localhost:9333", output, 0, 0, 0, 0)
            exporter.scrape_familysearch_sources(envelope, output / "browser", output, True, 0, 0, 0, 0)
            sync.assert_not_called()

    def test_http_failure_including_after_login(self):
        page = Mock(url=self.source)
        for login in (False, True):
            with self.subTest(login=login):
                error_response = Mock(ok=False, status=503)
                page.goto.side_effect = [Mock(ok=True), error_response] if login else [error_response]
                with patch.object(exporter, "looks_like_familysearch_login", return_value=login), patch("builtins.input"):
                    with self.assertRaisesRegex(exporter.ExportError, "503"):
                        self.capture(page)
                page.content.assert_not_called()

    def test_verify_source_destination_before_saving(self):
        page = Mock()
        page.goto.return_value = Mock(ok=True)
        with patch.object(exporter, "looks_like_familysearch_login", return_value=False), \
             patch.object(exporter, "scroll_familysearch_page"), \
             patch.object(exporter, "expand_all_familysearch_sources"), \
             patch.object(exporter, "save_familysearch_page_snapshot") as save:
            for page.url in (self.source.replace(self.pid, "AAAA-BBB"), self.source.replace(".org", ".org.example")):
                with self.assertRaisesRegex(exporter.ExportError, "requested sources page"):
                    self.capture(page)
            save.assert_not_called()
            page.url = self.source
            page.locator.return_value.inner_text.return_value = "Sources"
            page.locator.return_value.evaluate_all.return_value = []
            self.assertEqual(self.capture(page)["status"], "ok")
            save.assert_called_once()

    def test_extract_links_checks_the_host(self):
        page = Mock()
        valid = {"text": "Record", "href": "https://www.familysearch.org/ark:/example"}
        page.locator.return_value.evaluate_all.return_value = [
            valid, valid, {"href": "https://example.org/?next=familysearch.org"},
            {"href": "https://familysearch.org.example.org/record/1"},
            {"href": "https://[invalid/"},
        ]
        self.assertEqual(exporter.extract_page_links(page), [valid])


class ResearchLoopTests(unittest.TestCase):
    def test_json_write_preserves_unrelated_temporary_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "case.json"
            other = path.with_suffix(".json.tmp")
            other.write_text("another writer's data")
            exporter.write_json_file(path, {"name": "Élise"})
            self.assertEqual(json.loads(path.read_text()), {"name": "Élise"})
            self.assertEqual(other.read_text(), "another writer's data")
            self.assertEqual(sorted(p.name for p in path.parent.iterdir()),
                             ["case.json", "case.json.tmp"])

    def test_json_write_preserves_existing_access_permissions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "case.json"
            path.write_text("{}")
            path.chmod(0o640)
            exporter.write_json_file(path, {"updated": True})
            self.assertEqual(path.stat().st_mode & 0o777, 0o640)
            self.assertEqual(json.loads(path.read_text()), {"updated": True})

    def test_json_write_cleans_up_after_replace_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "case.json"
            path.write_text('{"original": true}')
            with patch.object(Path, "replace", side_effect=OSError("disk failure")):
                with self.assertRaisesRegex(OSError, "disk failure"):
                    exporter.write_json_file(path, {"new": True})
            self.assertEqual(json.loads(path.read_text()), {"original": True})
            self.assertEqual(list(path.parent.iterdir()), [path])

    def test_json_writes_can_overlap_without_sharing_temporary_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "case.json"
            replace = Path.replace
            nested = False

            def interleave(temporary, destination):
                nonlocal nested
                if not nested:
                    nested = True
                    exporter.write_json_file(path, {"writer": "inner"})
                return replace(temporary, destination)

            with patch.object(Path, "replace", interleave):
                exporter.write_json_file(path, {"writer": "outer"})
            self.assertEqual(json.loads(path.read_text()), {"writer": "outer"})
            self.assertEqual(list(path.parent.iterdir()), [path])

    def test_project_identifier_wrappers_keep_accepted_forms_and_messages(self) -> None:
        self.assertEqual(
            "Example_Person-42",
            exporter.normalise_wikitree_id("https://www.wikitree.com/wiki/Example%20Person-42"),
        )
        self.assertEqual("9QMG-R4T", exporter.normalise_familysearch_pid("9qmg-r4t"))
        with self.assertRaisesRegex(ValueError, "Glasgow-1538"):
            exporter.normalise_wikitree_id("not-an-id")
        with self.assertRaisesRegex(ValueError, "not a WikiTree URL"):
            exporter.normalise_wikitree_id(
                "https://wikitree.com.example.invalid/wiki/Example-42"
            )
        with self.assertRaisesRegex(ValueError, "9QMG-R4T"):
            exporter.normalise_familysearch_pid("not-a-pid")

    def test_existing_export_can_write_a_neutral_toolkit_case(self) -> None:
        envelope = sample_envelope()
        envelope["items"][0]["person"]["Father"] = "Uncaptured-1"
        child = envelope["items"][0]["person"]["Children"]["2"]
        child["Father"] = "Example-1"
        with tempfile.TemporaryDirectory() as directory:
            path = exporter.write_toolkit_case(envelope, "Example-1", Path(directory))
            data = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(data["id"], "wikitree-Example-1")
        self.assertEqual(len(data["record_sets"]["Person"]), 2)
        self.assertTrue(data["record_sets"]["Relationship"])
        person_ids = {person["id"] for person in data["record_sets"]["Person"]}
        self.assertTrue(all(
            relationship["subject_id"] in person_ids
            and relationship["object_id"] in person_ids
            for relationship in data["record_sets"]["Relationship"]
        ))
        self.assertTrue(data["record_sets"]["ImportProvenance"])

    def test_api_uses_waf_compatible_same_site_headers_and_app_id(self) -> None:
        response = Mock()
        response.status_code = 200
        response.headers = {"content-type": "application/json"}
        response.json.return_value = [{"status": 0, "profile": {"Name": "Example-1"}}]
        with patch.object(exporter.requests, "post", return_value=response) as post:
            envelope = exporter.post_wikitree({"action": "getProfile", "key": "Example-1"})
        self.assertEqual(envelope["status"], 0)
        kwargs = post.call_args.kwargs
        self.assertEqual(kwargs["data"]["appId"], "GlasgowSurnameResearch")
        self.assertEqual(kwargs["headers"]["Origin"], "https://www.wikitree.com")
        self.assertIn("Mozilla/5.0", kwargs["headers"]["User-Agent"])

    def test_api_reports_aws_waf_challenge_explicitly(self) -> None:
        response = Mock()
        response.status_code = 202
        response.headers = {"x-amzn-waf-action": "challenge"}
        with patch.object(exporter.requests, "post", return_value=response):
            with self.assertRaisesRegex(exporter.ExportError, "AWS WAF challenged"):
                exporter.post_wikitree({"action": "getProfile", "key": "Example-1"})

    def test_api_retries_transient_transport_and_server_failures(self) -> None:
        unavailable = Mock()
        unavailable.status_code = 503
        unavailable.headers = {"Retry-After": "not-a-number"}
        unavailable.raise_for_status.side_effect = exporter.requests.HTTPError("503")
        success = Mock()
        success.status_code = 200
        success.headers = {"content-type": "application/json"}
        success.json.return_value = [{"status": 0, "profile": {"Name": "Example-1"}}]

        with (
            patch.object(
                exporter.requests,
                "post",
                side_effect=[
                    exporter.requests.ConnectionError("temporary"),
                    unavailable,
                    success,
                ],
            ) as post,
            patch.object(exporter.time, "sleep") as sleep,
        ):
            envelope = exporter.post_wikitree(
                {"action": "getProfile", "key": "Example-1"}
            )

        self.assertEqual(envelope["profile"]["Name"], "Example-1")
        self.assertEqual(post.call_count, 3)
        self.assertEqual(sleep.call_count, 2)

    def test_api_response_errors_remain_export_errors(self) -> None:
        non_json = Mock()
        non_json.status_code = 200
        non_json.headers = {"Content-Type": "text/html"}
        non_json.text = "<html>temporarily unavailable</html>"
        with patch.object(exporter.requests, "post", return_value=non_json):
            with self.assertRaisesRegex(
                exporter.ExportError,
                "non-JSON content: <html>temporarily unavailable</html>",
            ):
                exporter.post_wikitree({"action": "getProfile", "key": "Example-1"})

    def test_extracts_embedded_export(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "export.md"
            path.write_text(
                "# Export\n\n## Raw structured export\n\n```json\n"
                + json.dumps(sample_envelope())
                + "\n```\n",
                encoding="utf-8",
            )

            result = exporter.extract_envelope_from_ai_export(path)

        self.assertEqual(exporter.envelope_subject_id(result), "Example-1")

    def test_import_uses_export_section_after_quoted_biography(self):
        envelope = sample_envelope()
        envelope["items"][0]["person"]["Bio"] = (
            'Quoted older export\n## Raw structured export\n\n```json\n{"old": true}\n```'
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "export.md"
            path.write_text(exporter.make_markdown(envelope, "Example-1"), encoding="utf-8")
            self.assertEqual(exporter.extract_envelope_from_ai_export(path), envelope)

    def test_capture_keeps_both_collections_when_timestamp_collides(self):
        with tempfile.TemporaryDirectory() as directory:
            case_dir = Path(directory)
            state = {}
            first = sample_envelope()
            second = sample_envelope()
            second["items"][0]["person"]["FirstName"] = "Updated"
            with patch.object(exporter, "utc_now", return_value="2026-11-18T12:00:00Z"):
                first_path = exporter.store_research_capture(case_dir, state, first, "Example-1", "test")
                second_path = exporter.store_research_capture(case_dir, state, second, "Example-1", "test")
            self.assertNotEqual(first_path, second_path)
            self.assertEqual(exporter.read_json_object(case_dir / first_path), first)
            self.assertEqual(exporter.read_json_object(case_dir / second_path), second)

    def test_evidence_index_preserves_facts_and_successful_sources_after_stub(self):
        with tempfile.TemporaryDirectory() as directory:
            case_dir = Path(directory)
            state = {"root_wikitree_id": "Example-1"}
            first = sample_envelope()
            first["items"][0]["person"].update(
                DeathDate="1870-00-00",
                FamilySearchBrowserSources={"ABCD-123": {"status": "ok"}},
            )
            second = {"items": [{"person": {
                "Name": "Example-1",
                "BirthDate": "0000-00-00",
                "DeathDate": "0000",
                "FamilySearchBrowserSources": {"ABCD-123": {"status": "error"}},
            }}]}
            for envelope in (first, second):
                exporter.store_research_capture(case_dir, state, envelope, "Example-1", "test")
            profile = exporter.build_evidence_index(case_dir, state)["profiles"]["Example-1"]
        self.assertEqual(profile["display_name"], "Alice Example")
        self.assertEqual(profile["birth_date"], "1800-00-00")
        self.assertEqual(profile["death_date"], "1870-00-00")
        self.assertEqual(profile["familysearch"]["ABCD-123"]["status"], "ok")
        self.assertEqual(len(profile["capture_paths"]), 2)

    def test_interrupted_research_resumes_after_completed_capture(self):
        with tempfile.TemporaryDirectory() as directory:
            case_dir = Path(directory)
            argv = ["export", "Example-1", "--research-dir", directory, "--descendant-depth", "2"]
            with patch.object(sys, "argv", argv):
                args = exporter.parse_args()
            with patch.object(exporter, "scrape_target", side_effect=[sample_envelope(), KeyboardInterrupt]):
                with self.assertRaises(KeyboardInterrupt):
                    exporter.run_research_mode(args, "Example-1", {})
            state = exporter.read_json_object(case_dir / exporter.RESEARCH_STATE_FILE)
            plan = exporter.read_json_object(case_dir / exporter.RESEARCH_PLAN_FILE)
            capture, = state["captures"]
            self.assertTrue((case_dir / capture["path"]).is_file())
            root, child = plan["targets"]
            self.assertEqual((root["id"], root["status"]), ("Example-1", "complete"))
            self.assertEqual((child["id"], child["status"]), ("Example-2", "pending"))

    def test_invalid_capture_does_not_write_raw_file(self):
        with tempfile.TemporaryDirectory() as directory:
            case_dir = Path(directory)
            with self.assertRaises(exporter.ExportError):
                exporter.store_research_capture(case_dir, {}, {"items": []}, "Example-1", "test")
            self.assertFalse((case_dir / "captures").exists())

    def test_capture_builds_deduplicated_index_and_brief(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            case_dir = Path(directory)
            state, plan = exporter.load_research_case(case_dir, "Example-1")
            exporter.store_research_capture(
                case_dir,
                state,
                sample_envelope(),
                "Example-1",
                "test",
            )
            exporter.set_research_target_status(
                plan,
                "wikitree",
                "Example-1",
                "complete",
            )
            exporter.update_research_outputs(case_dir, state, plan)

            index = exporter.read_json_object(
                case_dir / exporter.RESEARCH_INDEX_FILE
            )
            brief = (case_dir / exporter.RESEARCH_BRIEF_FILE).read_text(
                encoding="utf-8"
            )
            findings = (case_dir / exporter.RESEARCH_FINDINGS_FILE).read_text(
                encoding="utf-8"
            )
            profile_notes = (
                case_dir / exporter.research_profile_notes_file("Example-1")
            ).read_text(encoding="utf-8")

        self.assertEqual(set(index["profiles"]), {"Example-1", "Example-2"})
        self.assertEqual(
            index["profiles"]["Example-1"]["relations"]["children"],
            ["Example-2"],
        )
        self.assertIn("https://example.org/record/1", brief)
        self.assertIn(
            "[complete] wikitree: [Alice Example (Example-1), born 1800, "
            "Glasgow, Scotland](https://www.wikitree.com/wiki/Example-1)",
            brief,
        )
        self.assertIn(
            "[Bob Example (Example-2), born 1800, Glasgow, Scotland]"
            "(https://www.wikitree.com/wiki/Example-2)",
            brief,
        )
        self.assertIn(
            "# Findings: [Alice Example (Example-1), born 1800, "
            "Glasgow, Scotland](https://www.wikitree.com/wiki/Example-1)",
            findings,
        )
        self.assertIn("| Source | Finding | Assessment |", findings)
        self.assertIn(
            "# WikiTree update notes: [Alice Example (Example-1), born 1800, "
            "Glasgow, Scotland](https://www.wikitree.com/wiki/Example-1)",
            profile_notes,
        )
        self.assertNotIn("A sourced clue https://example.org/record/1", profile_notes)
        self.assertIn(
            "WikiTree fact/correction review queue: `Example-1.md`",
            brief,
        )

    def test_existing_findings_are_not_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            case_dir = Path(directory)
            findings_path = case_dir / exporter.RESEARCH_FINDINGS_FILE
            findings_path.write_text("# Curated findings\n", encoding="utf-8")

            state, plan = exporter.load_research_case(case_dir, "Example-1")
            exporter.store_research_capture(
                case_dir,
                state,
                sample_envelope(),
                "Example-1",
                "test",
            )
            exporter.update_research_outputs(case_dir, state, plan)

            self.assertEqual(
                findings_path.read_text(encoding="utf-8"),
                "# Curated findings\n",
            )

    def test_existing_profile_notes_are_not_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            case_dir = Path(directory)
            profile_notes_path = case_dir / "Example-1.md"
            profile_notes_path.write_text("# Curated updates\n", encoding="utf-8")

            state, plan = exporter.load_research_case(case_dir, "Example-1")
            exporter.store_research_capture(
                case_dir,
                state,
                sample_envelope(),
                "Example-1",
                "test",
            )
            exporter.update_research_outputs(case_dir, state, plan)

            self.assertEqual(
                profile_notes_path.read_text(encoding="utf-8"),
                "# Curated updates\n",
            )

    def test_redirect_applies_both_mappings_and_updates_original_queue_target(self):
        envelope = sample_envelope()
        envelope["redirect"] = {"requested": "Old-1", "resolved": "Example-1"}
        plan = exporter.default_research_plan("Old-1")
        exporter.add_research_target(plan, "familysearch", "ABCD-123", "lookup", "Old-1")
        mappings = exporter.research_familysearch_mappings(plan)
        mappings["Example-1"] = ["EFGH-456"]
        exporter.attach_familysearch_pids(envelope, mappings)
        person = envelope["items"][0]["person"]
        self.assertEqual(person["FamilySearchPIDs"], ["ABCD-123", "EFGH-456"])
        self.assertEqual(person["Children"]["2"]["FamilySearchPIDs"], [])
        for status, expected in [("error", "error"), ("ok", "complete")]:
            person["FamilySearchBrowserSources"]["ABCD-123"] = {"status": status}
            exporter.update_familysearch_target_outcomes(plan, envelope, browser_used=True)
            self.assertEqual(plan["targets"][-1]["status"], expected)
            self.assertEqual(plan["targets"][-1]["profile_id"], "Old-1")

    def test_import_redirect_requires_matching_subject(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "capture.md"
            with patch.object(sys, "argv", ["export", "Old-1", "--research-dir", str(root),
                                            "--import-ai-export", str(path)]):
                args = exporter.parse_args()
            envelope = sample_envelope()
            for resolved in ("Example-2", "Example-1"):
                envelope["redirect"] = {"requested": "Old-1", "resolved": resolved}
                path.write_text(exporter.make_markdown(envelope, "Old-1"), encoding="utf-8")
                if resolved == "Example-2":
                    with self.assertRaises(exporter.ExportError):
                        exporter.run_research_mode(args, "Old-1", {})
                    self.assertFalse((root / exporter.RESEARCH_STATE_FILE).exists())
                else:
                    with patch("builtins.print"):
                        self.assertEqual(exporter.run_research_mode(args, "Old-1", {}), 0)
            state = exporter.read_json_object(root / exporter.RESEARCH_STATE_FILE)
            capture, = state["captures"]
            self.assertEqual(capture["requested_wikitree_id"], "Old-1")
            self.assertEqual(capture["subject_wikitree_id"], "Example-1")

    def test_plan_familysearch_target_is_durable(self) -> None:
        plan = exporter.default_research_plan("Example-1")
        exporter.add_research_target(
            plan,
            "familysearch",
            "ABCD-123",
            "Inspect attached records.",
            "Example-2",
        )
        exporter.add_research_target(
            plan,
            "familysearch",
            "ABCD-123",
            "Duplicate should be ignored.",
            "Example-2",
        )

        mappings = exporter.research_familysearch_mappings(plan)

        self.assertEqual(mappings, {"Example-2": ["ABCD-123"]})
        self.assertEqual(len(plan["targets"]), 2)

    def test_descendant_depth_two_queues_children_only(self) -> None:
        plan = exporter.default_research_plan("Example-1")
        queued = exporter.queue_descendant_targets(
            plan,
            sample_envelope(),
            subject_generation=0,
            descendant_depth=2,
        )

        self.assertEqual(queued, 1)
        self.assertEqual(plan["targets"][1]["id"], "Example-2")
        self.assertEqual(plan["targets"][1]["generation"], 1)
        self.assertEqual(
            exporter.queue_descendant_targets(
                plan,
                sample_envelope(),
                subject_generation=1,
                descendant_depth=2,
            ),
            0,
        )


if __name__ == "__main__":
    unittest.main()
