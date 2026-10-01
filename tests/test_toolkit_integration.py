"""Non-mutating integration checks for the reusable genealogy toolkit boundary."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from tools.genealogy_bridge import export_legacy_onetree, normalise_legacy_onetree
from tools.genealogy_project import load_project_config, load_toolkit_project_config


ROOT = Path(__file__).resolve().parents[1]


def public_legacy_payload() -> dict[str, object]:
    """Synthetic Glasgow-project-side records; no real research data is used."""
    return {
        "title": "Synthetic bridge test",
        "people": [
            {"id": "historic", "Name": "Historical Test Person", "DeathDate": "1900-01-01", "Privacy": 60},
            {"id": "living", "Name": "Living Test Person", "Privacy": 60},
            {"id": "restricted", "Name": "Restricted Test Person", "DeathDate": "1900-01-01", "Privacy": 40},
            {"id": "licensed", "name": "Licensed Test Person", "living": "deceased", "licensed_source": True},
            {"id": "contradictory", "name": "Contradictory Test Person", "living": "deceased", "sensitivity": "public", "restricted": True},
        ],
        "sources": [
            {"id": "open-source", "title": "Synthetic open source", "sensitivity": "public"},
            {"id": "licensed-source", "title": "Synthetic licensed source", "licensed_source": True},
        ],
        "citations": [
            {"id": "open-citation", "source_id": "open-source", "sensitivity": "public"},
            {"id": "licensed-citation", "source_id": "licensed-source", "sensitivity": "public"},
        ],
        "relationships": [
            {"id": "public-edge", "subject_id": "historic", "object_id": "historic", "kind": "associate", "Privacy": 60},
            {"id": "living-edge", "subject_id": "historic", "object_id": "living", "kind": "associate", "Privacy": 60},
            {"id": "restricted-edge", "subject_id": "historic", "object_id": "restricted", "kind": "associate", "Privacy": 60},
            {"id": "licensed-edge", "subject_id": "historic", "object_id": "licensed", "kind": "associate", "Privacy": 60},
        ],
        "claims": [
            {"id": "public-claim", "subject_id": "historic", "predicate": "was-recorded", "value": "yes", "citation_ids": ["open-citation"], "sensitivity": "public"},
            {"id": "licensed-claim", "subject_id": "historic", "predicate": "was-recorded", "value": "withheld", "citation_ids": ["licensed-citation"], "sensitivity": "public"},
            {"id": "living-claim", "subject_id": "living", "predicate": "was-recorded", "value": "withheld", "citation_ids": ["open-citation"], "sensitivity": "public"},
        ],
    }


class ToolkitIntegrationTests(unittest.TestCase):
    def test_glasgow_overlay_is_complete_and_does_not_authorize_rebuilds(self):
        config = load_project_config()
        self.assertEqual(config["project"]["id"], "glasgow-surname-ancestry")
        self.assertIn("wikitree", config["adapters"]["enabled"])
        self.assertIn("gedcom", config["adapters"]["enabled"])
        self.assertFalse(config["exports"]["allow_catalogue_rebuild"])

    def test_overlay_loader_cannot_bypass_toolkit_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / "genealogy.toml"
            config_path.write_text(
                "[project]\ncase_directory = '../outside'\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "project.case_directory"):
                load_project_config(config_path)

    def test_configured_toolkit_cli_validates_only_the_isolated_fixture(self):
        command = [str(ROOT / ".venv/bin/genealogy"), "--project", str(ROOT), "validate"]
        result = subprocess.run(command, cwd=ROOT, check=False, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Research case is valid", result.stdout)

    def test_explicit_bridge_filters_sensitive_people_and_dependencies(self):
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            input_path = temporary / "legacy.json"
            output_path = temporary / "public.json"
            input_path.write_text(json.dumps(public_legacy_payload()), encoding="utf-8")
            export_legacy_onetree(input_path, output_path)
            exported = json.loads(output_path.read_text(encoding="utf-8"))
        visible = {
            record["id"]
            for records in exported.values()
            if isinstance(records, list)
            for record in records
        }
        self.assertIn("one-tree:person:Historical Test Person", visible)
        self.assertIn("one-tree:relationship:public-edge", visible)
        self.assertIn("public-claim", visible)
        self.assertNotIn("one-tree:person:Living Test Person", visible)
        self.assertNotIn("one-tree:person:Restricted Test Person", visible)
        self.assertNotIn("one-tree:person:Licensed Test Person", visible)
        self.assertNotIn("one-tree:person:Contradictory Test Person", visible)
        self.assertNotIn("one-tree:relationship:living-edge", visible)
        self.assertNotIn("one-tree:relationship:restricted-edge", visible)
        self.assertNotIn("one-tree:relationship:licensed-edge", visible)
        self.assertNotIn("licensed-claim", visible)
        self.assertNotIn("living-claim", visible)

    def test_raw_dna_is_rejected_before_a_case_or_export_can_be_written(self):
        payload = public_legacy_payload()
        people = payload["people"]
        assert isinstance(people, list)
        people.append({"id": "raw-kit", "name": "Raw kit", "raw_dna": True})
        with self.assertRaisesRegex(ValueError, "raw DNA"):
            normalise_legacy_onetree(payload)
        nested = public_legacy_payload()
        nested_people = nested["people"]
        assert isinstance(nested_people, list)
        nested_people.append({"id": "nested-kit", "raw_data": {"genotypes": "AA"}})
        with self.assertRaisesRegex(ValueError, "raw DNA"):
            normalise_legacy_onetree(nested)
        contradictory = public_legacy_payload()
        contradictory_people = contradictory["people"]
        assert isinstance(contradictory_people, list)
        contradictory_people.append({
            "id": "raw-kit", "name": "Raw kit", "sensitivity": "public", "raw_sensitive": True,
        })
        with self.assertRaisesRegex(ValueError, "raw DNA"):
            normalise_legacy_onetree(contradictory)

    def test_bridge_rejects_ambiguous_privacy_and_invalid_cases(self):
        ambiguous = public_legacy_payload()
        people = ambiguous["people"]
        assert isinstance(people, list)
        people.append({"id": "ambiguous", "name": "Ambiguous", "historical": "false"})
        with self.assertRaisesRegex(ValueError, "historical must be a boolean"):
            normalise_legacy_onetree(ambiguous)

        invalid = public_legacy_payload()
        citations = invalid["citations"]
        assert isinstance(citations, list)
        citations.append({
            "id": "dangling", "source_id": "missing-source", "sensitivity": "public",
        })
        with tempfile.TemporaryDirectory() as directory:
            input_path = Path(directory) / "invalid.json"
            output_path = Path(directory) / "public.json"
            input_path.write_text(json.dumps(invalid), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "invalid research case"):
                export_legacy_onetree(input_path, output_path)
            self.assertFalse(output_path.exists())

    def test_bridge_requires_neutral_onetree_entities_for_relationships(self):
        case = normalise_legacy_onetree(public_legacy_payload())
        self.assertTrue(case.records("Relationship"))

    def test_bridge_accepts_an_explicit_onetree_data_wrapper(self):
        case = normalise_legacy_onetree({
            "data": {
                "fixture-parent": {"Name": "fixture-parent", "Id": 101, "Privacy": 60, "DeathDate": "1900"},
                "fixture-child": {"Name": "fixture-child", "Id": 102, "Privacy": 60, "DeathDate": "1920", "Father": 101},
            },
        })
        self.assertEqual(len(case.records("Person")), 2)
        self.assertTrue(case.records("Relationship"))

    def test_legacy_overlay_cli_contract_remains_available(self):
        result = subprocess.run(
            [sys.executable, "tools/genealogy_project.py", "--help"], cwd=ROOT,
            check=False, capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--json", result.stdout)

    def test_installed_toolkit_loads_the_glasgow_overlay(self):
        toolkit_config = load_toolkit_project_config()
        self.assertEqual(toolkit_config.project_id, "glasgow-surname-ancestry")
        self.assertEqual(toolkit_config.raw["surname"]["primary"], "Glasgow")


if __name__ == "__main__":
    unittest.main()
