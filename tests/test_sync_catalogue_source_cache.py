import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import repair_person_hierarchy as hierarchy
from tools import sync_catalogue_research as sync


class HierarchySourceCacheTests(unittest.TestCase):
    def test_reuses_parses_and_reloads_changed_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            research = root / "research"
            research.mkdir()
            records = research / "canonical_records.json"
            assessments = research / "relationship_assessments.json"
            records.write_text(json.dumps([
                {"record_id": "r1", "profiles": {"Glasgow-1": {"role": "child"}}},
                {"record_id": "r2", "profiles": {"Glasgow-2": {"role": "parent"}}},
            ]))
            assessments.write_text("[]")
            original_records = hierarchy._canonical_records
            original_assessments = hierarchy._relationship_assessments
            with patch.object(hierarchy, "ROOT", root), \
                 patch.object(hierarchy, "_canonical_records", wraps=original_records) as record_reads, \
                 patch.object(hierarchy, "_relationship_assessments", wraps=original_assessments) as assessment_reads:
                with sync.cached_hierarchy_sources():
                    first = hierarchy._canonical_record_rows("Glasgow-1")
                    second = hierarchy._canonical_record_rows("Glasgow-2")
                    self.assertEqual([row["record_id"] for row in first], ["r1"])
                    self.assertEqual([row["record_id"] for row in second], ["r2"])
                    self.assertEqual(record_reads.call_count, 1)
                    self.assertEqual(assessment_reads.call_count, 1)

                    records.write_text(json.dumps([
                        {"record_id": "r3", "profiles": {"Glasgow-1": {"role": "child"}}},
                    ]))
                    assessments.write_text(json.dumps([{"publication_status": "approved",
                                                        "people": ["Glasgow-1"], "source_ids": ["r3"]}]))
                    self.assertEqual([row["record_id"] for row in hierarchy._canonical_record_rows("Glasgow-1")], ["r3"])
                    self.assertEqual(record_reads.call_count, 2)
                    self.assertEqual(assessment_reads.call_count, 2)
                self.assertIs(hierarchy._canonical_records, record_reads)
                self.assertIs(hierarchy._relationship_assessments, assessment_reads)
                self.assertEqual([row["record_id"] for row in hierarchy._canonical_record_rows("Glasgow-1")], ["r3"])
                self.assertEqual(record_reads.call_count, 3)
                self.assertEqual(assessment_reads.call_count, 3)

    def test_main_scopes_cache_and_restores_on_failure(self):
        original_records = hierarchy._canonical_records
        original_assessments = hierarchy._relationship_assessments
        with patch.object(sync, "_run", side_effect=RuntimeError("stopped")):
            with self.assertRaisesRegex(RuntimeError, "stopped"):
                sync.main()
        self.assertIs(hierarchy._canonical_records, original_records)
        self.assertIs(hierarchy._relationship_assessments, original_assessments)


if __name__ == "__main__":
    unittest.main()
