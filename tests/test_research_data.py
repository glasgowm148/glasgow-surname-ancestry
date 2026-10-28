import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "tools"), str(ROOT)]
import research_data  # noqa: E402


class ResearchDataTest(unittest.TestCase):
    def test_reads_the_generated_files_where_there_is_no_database(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "research").mkdir()
            (root / "research/relationship_assessments.json").write_text(json.dumps([{"id": "R-1"}]))
            (root / "research/latest-findings.json").write_text(json.dumps({"findings": [{"id": "F-1"}]}))
            self.assertEqual(research_data.relationship_assessments(root), [{"id": "R-1"}])
            self.assertEqual(research_data.latest_findings(root), {"findings": [{"id": "F-1"}]})
            self.assertEqual(research_data.canonical_records(root), [])
            self.assertEqual(research_data.vital_assessments(root), {})

    @unittest.skipUnless((ROOT / "research").is_dir(), "needs the project's research folder")
    def test_database_rows_equal_the_generated_files(self):
        for name, relative in (("relationship_assessments", "research/relationship_assessments.json"),
                               ("latest_findings", "research/latest-findings.json")):
            path = ROOT / relative
            if path.is_file():
                self.assertEqual(getattr(research_data, name)(), json.loads(path.read_text(encoding="utf-8")), name)


if __name__ == "__main__":
    unittest.main()
