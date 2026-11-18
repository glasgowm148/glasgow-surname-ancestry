import json
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
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
