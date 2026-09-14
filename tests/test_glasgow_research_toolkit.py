from __future__ import annotations

import json
import io
from contextlib import redirect_stdout
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from genealogy.artifacts import read_case_artifact_bundle
from genealogy.models import ImportProvenance, LivingStatus
from glasgow_research_toolkit import LEGACY_FILES, write_toolkit_research_bundle
from tools.migrate_research_bundle import main as migrate_research_bundle
import wikitree_family_export as exporter


def write_synthetic_legacy_case(directory: Path) -> None:
    state = {
        "schema_version": 1,
        "root_wikitree_id": "Fixture-1",
        "created_at": "2026-09-08T12:00:00Z",
        "updated_at": "2026-09-08T12:05:00Z",
        "captures": [{
            "path": "captures/private-source.json",
            "source": "synthetic",
        }],
        "errors": [],
    }
    plan = {
        "schema_version": 1,
        "case_id": "Fixture-1",
        "objective": "Resolve a fictional historical identity.",
        "questions": [{
            "id": "identity",
            "question": "Which fictional record identifies the subject?",
            "status": "open",
            "answer": "",
        }],
        "web_searches": [{
            "id": "search-1",
            "query": "fictional archive catalogue",
            "status": "pending",
        }],
        "targets": [{
            "kind": "familysearch",
            "id": "XXXX-XXX",
            "profile_id": "Fixture-1",
            "status": "pending",
        }],
        "findings": [{
            "claim": "A fictional index supports the subject's residence.",
            "confidence": "probable",
            "sources": ["https://example.invalid/catalogue/fixture"],
        }],
    }
    index = {
        "schema_version": 1,
        "root_wikitree_id": "Fixture-1",
        "generated_at": "2026-09-08T12:05:00Z",
        "capture_count": 1,
        "profiles": {
            "Fixture-1": {
                "wikitree_id": "Fixture-1",
                "display_name": "Historical Fixture",
                "birth_date": "1800-00-00",
                "birth_location": "Fictional Parish",
                "death_date": "1870-00-00",
                "death_location": "Fictional Parish",
                "relations": {
                    "parents": [], "children": ["Fixture-2"],
                    "siblings": [], "spouses": [],
                },
                "biography": "LICENSED PRIVATE BIOGRAPHY MUST NOT BE COPIED",
                "capture_paths": ["captures/private-source.json"],
            },
            "Fixture-2": {
                "wikitree_id": "Fixture-2",
                "display_name": "Possibly Living Fixture",
                "birth_date": "",
                "birth_location": "",
                "death_date": "",
                "death_location": "",
                "relations": {
                    "parents": ["Fixture-1"], "children": [],
                    "siblings": [], "spouses": [],
                },
                "biography": "RESTRICTED LIVING DETAIL MUST NOT BE COPIED",
                "capture_paths": ["captures/private-source.json"],
            },
        },
    }
    directory.mkdir(parents=True)
    for filename, value in (
        ("research_state.json", state),
        ("research_plan.json", plan),
        ("evidence_index.json", index),
    ):
        (directory / filename).write_text(
            json.dumps(value, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    (directory / "research_brief.md").write_text(
        "# Legacy brief\n\nRESTRICTED BRIEF BODY MUST NOT BE COPIED\n",
        encoding="utf-8",
    )
    (directory / "findings.md").write_text(
        "# Legacy findings\n\nLICENSED FINDINGS BODY MUST NOT BE COPIED\n",
        encoding="utf-8",
    )


class GlasgowResearchToolkitTests(unittest.TestCase):
    def test_opt_in_bundle_preserves_legacy_files_and_verifies_private_case(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            legacy = root / "legacy"
            bundle = root / "bundle"
            write_synthetic_legacy_case(legacy)
            before = {name: (legacy / name).read_bytes() for name in LEGACY_FILES}

            paths = write_toolkit_research_bundle(legacy, bundle)
            case = read_case_artifact_bundle(bundle)

            self.assertEqual(before, {name: (legacy / name).read_bytes() for name in LEGACY_FILES})
            self.assertEqual("wikitree-research-Fixture-1", case.id)
            self.assertEqual(2, len(case.records("Person")))
            self.assertEqual(1, len(case.records("Relationship")))
            self.assertEqual(1, len(case.records("ResearchQuestion")))
            self.assertEqual(1, len(case.records("Finding")))
            living = next(
                person for person in case.records("Person")
                if person.id == "wikitree:person:Fixture-2"
            )
            self.assertEqual(LivingStatus.UNKNOWN, living.living)
            for records in case.record_sets.values():
                for record in records:
                    self.assertEqual("private", record.sensitivity)

            provenance = case.records(ImportProvenance)[0]
            queue = next(item for item in provenance.observations if item["kind"] == "legacy-work-queue")
            self.assertEqual("fictional archive catalogue", queue["web_searches"][0]["query"])
            self.assertEqual("XXXX-XXX", queue["targets"][0]["id"])
            manifest = json.loads(paths["bundle-manifest.json"].read_text(encoding="utf-8"))
            self.assertEqual(1, manifest["bundle_schema_version"])
            self.assertEqual("private-by-default", manifest["privacy"])
            self.assertEqual(0o700, stat.S_IMODE(bundle.stat().st_mode))
            self.assertTrue(all(stat.S_IMODE(path.stat().st_mode) == 0o600 for path in paths.values()))

            bundled_text = "\n".join(path.read_text(encoding="utf-8") for path in paths.values())
            self.assertNotIn("LICENSED PRIVATE BIOGRAPHY", bundled_text)
            self.assertNotIn("RESTRICTED LIVING DETAIL", bundled_text)
            self.assertNotIn("RESTRICTED BRIEF BODY", bundled_text)
            self.assertNotIn("LICENSED FINDINGS BODY", bundled_text)

    def test_raw_dna_marker_fails_before_bundle_write(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            legacy = root / "legacy"
            bundle = root / "bundle"
            write_synthetic_legacy_case(legacy)
            index_path = legacy / "evidence_index.json"
            index = json.loads(index_path.read_text(encoding="utf-8"))
            index["profiles"]["Fixture-1"]["raw_dna"] = {"genotypes": "AA"}
            index_path.write_text(json.dumps(index), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "raw DNA"):
                write_toolkit_research_bundle(legacy, bundle)
            self.assertFalse(bundle.exists())

    def test_bundle_cannot_overwrite_the_legacy_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            legacy = Path(temporary) / "legacy"
            write_synthetic_legacy_case(legacy)
            before = {name: (legacy / name).read_bytes() for name in LEGACY_FILES}
            with self.assertRaisesRegex(ValueError, "must not overwrite"):
                write_toolkit_research_bundle(legacy, legacy)
            self.assertEqual(before, {name: (legacy / name).read_bytes() for name in LEGACY_FILES})

    def test_standalone_migration_uses_only_explicit_synthetic_directories(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            legacy = root / "legacy"
            bundle = root / "bundle"
            write_synthetic_legacy_case(legacy)
            before = {name: (legacy / name).read_bytes() for name in LEGACY_FILES}

            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(0, migrate_research_bundle([
                    "--research-dir", str(legacy), "--bundle-dir", str(bundle),
                ]))

            self.assertIn("Toolkit bundle manifest", output.getvalue())
            self.assertEqual(before, {name: (legacy / name).read_bytes() for name in LEGACY_FILES})
            self.assertEqual("wikitree-research-Fixture-1", read_case_artifact_bundle(bundle).id)

    def test_standalone_migration_preserves_same_directory_guard(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            legacy = Path(temporary) / "legacy"
            write_synthetic_legacy_case(legacy)
            with self.assertRaises(SystemExit) as raised:
                migrate_research_bundle([
                    "--research-dir", str(legacy), "--bundle-dir", str(legacy),
                ])
            self.assertEqual(2, raised.exception.code)

    def test_research_command_dual_writes_only_when_explicitly_requested(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            legacy = root / "legacy"
            bundle = root / "bundle"
            write_synthetic_legacy_case(legacy)
            captures = legacy / "captures"
            captures.mkdir()
            (captures / "private-source.json").write_text(json.dumps({
                "items": [{
                    "person": {
                        "Name": "Fixture-1",
                        "FirstName": "Historical",
                        "LastNameCurrent": "Fixture",
                        "DeathDate": "1870-00-00",
                        "Bio": "PRIVATE CAPTURE BODY MUST NOT BE COPIED",
                        "Parents": {}, "Children": {}, "Siblings": {}, "Spouses": {},
                    },
                }],
            }), encoding="utf-8")
            plan_path = legacy / "research_plan.json"
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
            plan["targets"] = [{
                "kind": "wikitree", "id": "Fixture-1", "generation": 0,
                "reason": "Synthetic capture already present.", "status": "complete",
            }]
            plan_path.write_text(json.dumps(plan), encoding="utf-8")

            output = io.StringIO()
            with (
                patch.object(sys, "argv", [
                    "wikitree_family_export.py", "Fixture-1",
                    "--research-dir", str(legacy),
                    "--toolkit-research-bundle", str(bundle),
                ]),
                redirect_stdout(output),
            ):
                self.assertEqual(0, exporter.main())

            self.assertIn("Private toolkit research bundle", output.getvalue())
            case = read_case_artifact_bundle(bundle)
            self.assertEqual("wikitree-research-Fixture-1", case.id)
            self.assertNotIn(
                "PRIVATE CAPTURE BODY",
                (bundle / "case.json").read_text(encoding="utf-8"),
            )


if __name__ == "__main__":
    unittest.main()
