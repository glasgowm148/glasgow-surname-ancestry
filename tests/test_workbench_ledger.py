import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch

from tools.workbench_ledger import ledger


class Store:
    def all(self, sql):
        if "input_label, input_sha256" in sql:
            return []
        if "input_label, a.path" in sql:
            return []
        if "SELECT path, sha256" in sql:
            return []
        return []


class Project:
    store = Store()


class ChangedImportStore(Store):
    def all(self, sql):
        if "input_label, input_sha256" in sql:
            return [{"input_label": "notes.md", "input_sha256": "old"}]
        return super().all(sql)


class Views:
    def __init__(self, store):
        self.store = store

    def files(self):
        return {"research/relationship_assessments.json": '{"assessments":[]}' }


class LedgerTests(unittest.TestCase):
    item = {"path": "research/relationship_assessments.json", "sha256": "old", "disposition": "imported",
            "category": "research", "access": "private", "tracked": True}

    def test_db_generated_view_accepts_current_bytes(self):
        with tempfile.TemporaryDirectory() as tmp, patch("tools.workbench_legacy_views.Views", Views), patch("tools.workbench_ledger.ROOT", Path(tmp)):
            path = Path(tmp) / "research/relationship_assessments.json"; path.parent.mkdir()
            path.write_text('{"assessments":[]}', encoding="utf-8")
            result = ledger(Project(), {"source_commit": "x", "files": [self.item], "summarised": []})
        self.assertEqual([], result["problems"])

    def test_tampered_generated_view_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp, patch("tools.workbench_legacy_views.Views", Views), patch("tools.workbench_ledger.ROOT", Path(tmp)):
            path = Path(tmp) / "research/relationship_assessments.json"; path.parent.mkdir(); path.write_text("tampered")
            result = ledger(Project(), {"source_commit": "x", "files": [self.item], "summarised": []})
        self.assertEqual("changed since the inventory; re-run the migration", result["problems"][0]["problem"])

    def test_held_document_view_is_generated_from_database(self):
        class DocumentViews(Views):
            def files(self):
                return {"research/Example-1/research_plan.json": '{"questions":[]}' }
        item = {"path": "research/Example-1/research_plan.json", "sha256": "old", "disposition": "imported",
                "category": "research", "access": "private", "tracked": True}
        with tempfile.TemporaryDirectory() as tmp, patch("tools.workbench_legacy_views.Views", DocumentViews), patch("tools.workbench_ledger.ROOT", Path(tmp)):
            path = Path(tmp) / item["path"]; path.parent.mkdir(parents=True); path.write_text('{"questions":[]}')
            result = ledger(Project(), {"source_commit": "x", "files": [item], "summarised": []})
        self.assertEqual([], result["problems"])

    def test_changed_nongenerated_import_is_rejected(self):
        item = {"path": "notes.md", "sha256": "new", "disposition": "imported",
                "category": "research", "access": "private", "tracked": True}
        result = ledger(type("Project", (), {"store": ChangedImportStore()})(),
                        {"source_commit": "x", "files": [item], "summarised": []})
        self.assertEqual("changed since the inventory; re-run the migration", result["problems"][0]["problem"])


if __name__ == "__main__":
    unittest.main()
