"""Mechanical review items are resolved only after their check passes (fictional data)."""
from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from genealogy.cli import initialize_project  # noqa: E402
from genealogy.store import NameInput, Research, open_project  # noqa: E402

import workbench_resolve_review_items as resolver  # noqa: E402

EXPORTS = (("imp-new", "ONT_Harrow_2026-08-18T15_43.json", "one-tree:harrow", "2026-10-25T10:00:01Z"),
           ("imp-old", "ONT_Harrow_2026-07-22T11_12.json", "one-tree:harrow", "2026-10-25T10:00:02Z"),
           ("imp-other", "ONT_Harow_2026-08-18T16_05.json", "one-tree:harow", "2026-10-25T10:00:03Z"))


class ResolveReviewItems(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.directory = Path(self.tmp.name) / "project"
        initialize_project(self.directory, "Harrow test")
        with open_project(self.directory) as project:
            research = Research(project.store)
            with project.store.write(actor="test") as tx:
                person = research.create_person(tx, names=[NameInput("Ada Harrow", preferred=True)])
                for batch, label, lineage, when in EXPORTS:
                    tx.insert("import_batch", {"id": batch, "adapter": "one-tree", "input_label": label,
                                               "options_json": json.dumps({"lineage": lineage}), "imported_at": when})
                tx.insert("import_origin", {"entity_id": person, "import_batch_id": "imp-new", "input_path": EXPORTS[0][1],
                                            "pointer": "Person/1"})
                for item, batch, label in (("leg-old", "imp-old", EXPORTS[1][1]), ("leg-other", "imp-other", EXPORTS[2][1])):
                    tx.insert("legacy_item", {"id": item, "import_batch_id": batch, "input_path": label,
                                              "pointer": "Person/1", "disposition": "conflict", "entity_id": person,
                                              "reason": "the same id was loaded earlier with different content",
                                              "payload_json": "{}"})
                tx.insert("legacy_item", {"id": "leg-place", "input_path": "data/place-gazetteer.json",
                                          "pointer": "/ambiguous/x", "disposition": "unresolved",
                                          "reason": "ambiguous place name", "payload_json": "{}"})
                tx.insert("legacy_item", {"id": "leg-queue", "input_path": resolver.QUEUE,
                                          "pointer": "/completed_live_profiles/Harrow-1", "disposition": "unresolved",
                                          "reason": "completed live update", "payload_json": '{"profile": "Harrow-1"}'})

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def run_tool(self, *args: str) -> dict:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(resolver.main(["--project", str(self.directory), *args]), 0)
        return json.loads(out.getvalue())

    def test_only_checked_items_are_resolved_and_only_with_write(self) -> None:
        report = self.run_tool()
        self.assertFalse(report["written"])
        self.assertEqual(report["counts"]["resolved: older OneTree export"], 1)
        self.assertEqual({row["id"] for row in report["left_open"]}, {"leg-other", "leg-place", "leg-queue"})
        with open_project(self.directory) as project:
            self.assertIsNone(project.store.require("legacy_item", "leg-old")["resolution"])
        self.run_tool("--write")
        with open_project(self.directory) as project:
            resolved = project.store.require("legacy_item", "leg-old")
            self.assertIn("older export of the same OneTree tree", resolved["resolution"])
            self.assertEqual(resolved["resolved_by"], "workbench_resolve_review_items")
            self.assertIsNone(project.store.require("legacy_item", "leg-other")["resolution"])
        self.assertEqual(self.run_tool()["counts"].get("resolved: older OneTree export"), None)


if __name__ == "__main__":
    unittest.main()
