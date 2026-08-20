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


class ResearchLoopTests(unittest.TestCase):
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
