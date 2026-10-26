"""tmp/ clean-up deletes only checked classes and never what the database references (fictional data)."""
from __future__ import annotations

import contextlib
import gzip
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from genealogy.cli import initialize_project  # noqa: E402
from genealogy.store import open_project  # noqa: E402
from genealogy.store.assets import register_asset  # noqa: E402

import workbench_tmp_cleanup as cleanup  # noqa: E402


class TmpCleanup(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "project"
        initialize_project(self.root, "Harrow test")
        with (self.root / "genealogy.toml").open("a") as config:
            config.write('\n[storage.asset_roots]\nrepository = "."\n')
        scratch = self.root / "tmp"
        self.files = {
            "kept-notes": scratch / "a-20261020" / "notes.md",
            "referenced": scratch / "a-20261020" / "lead.pdf",
            "duplicate": scratch / "a-20261020" / "copy.json",
            "cache": scratch / "a-20261020" / "Cache" / "x.bin",
            "old-staged": scratch / "a-20261020" / "staged" / "page.html",
            "new-staged": scratch / "b-20261025" / "staged" / "page.html",
        }
        for name, path in self.files.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"{name} bytes")
        (self.root / "research").mkdir()
        (self.root / "research" / "kept.json").write_text("duplicate bytes")
        old_bundle = scratch / "a-20261020" / "glasgow-site-bundle-1.tar.gz"
        new_bundle = scratch / "b-20261025" / "glasgow-site-bundle-2.tar.gz"
        for bundle in (old_bundle, new_bundle):
            with gzip.open(bundle, "wb") as handle:
                handle.write(b"x")
        (self.root / "dist").mkdir()
        with gzip.open(self.root / "dist" / "glasgow-site-1.tar.gz", "wb") as handle:
            handle.write(b"release")
        import os
        os.utime(self.files["old-staged"].parents[1], (1, 1))
        os.utime(old_bundle, (1, 1))
        self.files["old-bundle"], self.files["new-bundle"] = old_bundle, new_bundle
        inventory = self.root / "data/private/workbench/inventory/inventory.json"
        inventory.parent.mkdir(parents=True)
        inventory.write_text(json.dumps({"files": [
            {"path": "research/kept.json", "sha256": cleanup.sha256(self.root / "research" / "kept.json")}]}))
        with open_project(self.root) as project:
            with project.store.write(actor="test") as tx:
                register_asset(project, tx, self.files["referenced"], root="repository", kind="scratch_lead")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def run_tool(self, *args: str) -> dict:
        out = io.StringIO()
        patches = [mock.patch.object(cleanup, "ROOT", self.root),
                   mock.patch.object(cleanup, "REPORT", self.root / "report.json"),
                   mock.patch.object(cleanup, "INVENTORY", self.root / "data/private/workbench/inventory/inventory.json")]
        with contextlib.ExitStack() as stack, contextlib.redirect_stdout(out):
            for patch in patches:
                stack.enter_context(patch)
            self.assertEqual(cleanup.main(["--project", str(self.root), "--scratch", str(self.root / "tmp"), *args]), 0)
        return json.loads((self.root / "report.json").read_text())

    def test_only_checked_classes_are_planned_and_a_dry_run_deletes_nothing(self) -> None:
        self.files["duplicate"].write_text("duplicate bytes")
        report = self.run_tool()
        planned = {Path(row["path"]).name: row["class"] for row in report["files"]}
        self.assertEqual(planned, {"copy.json": "duplicate", "x.bin": "cache", "page.html": "staged site copy",
                                   "glasgow-site-bundle-1.tar.gz": "older release bundle"})
        self.assertEqual(report["deleted"], 0)
        self.assertTrue(all(path.exists() for path in self.files.values()))

    def test_delete_keeps_references_notes_and_the_newest_copies(self) -> None:
        self.files["duplicate"].write_text("duplicate bytes")
        self.run_tool("--delete")
        gone = {name for name, path in self.files.items() if not path.exists()}
        self.assertEqual(gone, {"duplicate", "cache", "old-staged", "old-bundle"})
        self.assertTrue((self.root / "research" / "kept.json").exists())

    def test_a_copy_whose_other_file_changed_is_not_a_duplicate(self) -> None:
        self.files["duplicate"].write_text("duplicate bytes")
        (self.root / "research" / "kept.json").write_text("edited since the inventory")
        report = self.run_tool()
        self.assertNotIn("copy.json", {Path(row["path"]).name for row in report["files"]})


if __name__ == "__main__":
    unittest.main()
