import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import repair_person_hierarchy as hierarchy


class RepairSourceCacheTests(unittest.TestCase):
    def test_content_and_parse_counts_with_invalidation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "research").mkdir()
            records = root / "research/canonical_records.json"
            assessments = root / "research/relationship_assessments.json"
            records.write_text('[{"record_id":"one"}]')
            assessments.write_text('[{"status":"possible"}]')
            with patch.object(hierarchy, "ROOT", root), patch.object(
                hierarchy, "_load_json", wraps=hierarchy._load_json
            ) as reads:
                expected = (hierarchy._canonical_records(), hierarchy._relationship_assessments())
                hierarchy._canonical_records()
                hierarchy._relationship_assessments()
                self.assertEqual(reads.call_count, 4)  # uncached baseline
                reads.reset_mock()
                with hierarchy.cached_hierarchy_sources():
                    for _ in range(3):
                        self.assertEqual(
                            (hierarchy._canonical_records(), hierarchy._relationship_assessments()),
                            expected,
                        )
                    self.assertEqual(reads.call_count, 2)
                    records.write_text('[{"record_id":"changed-record"}]')
                    assessments.write_text('[{"status":"strongly_supported"}]')
                    self.assertEqual(hierarchy._canonical_records(), json.loads(records.read_text()))
                    self.assertEqual(hierarchy._relationship_assessments(), json.loads(assessments.read_text()))
                    self.assertEqual(reads.call_count, 4)
                    # A different resolved root must not reuse the old rows.
                    alternate = root / "alternate"
                    (alternate / "research").mkdir(parents=True)
                    (alternate / "research/canonical_records.json").write_text("[]")
                    with patch.object(hierarchy, "ROOT", alternate):
                        self.assertEqual(hierarchy._canonical_records(), [])
                hierarchy._canonical_records()
                self.assertEqual(reads.call_count, 6)  # no cache survives context

    def test_repair_scopes_cache_and_restores_on_failure(self):
        records = hierarchy._canonical_records
        assessments = hierarchy._relationship_assessments

        def fail(_web, **_):
            self.assertIsNot(hierarchy._canonical_records, records)
            self.assertIsNot(hierarchy._relationship_assessments, assessments)
            raise RuntimeError("stopped")

        with patch.object(hierarchy, "publish", side_effect=fail):
            with self.assertRaisesRegex(RuntimeError, "stopped"):
                hierarchy.repair(["Example-1"])
        self.assertIs(hierarchy._canonical_records, records)
        self.assertIs(hierarchy._relationship_assessments, assessments)


if __name__ == "__main__":
    unittest.main()
