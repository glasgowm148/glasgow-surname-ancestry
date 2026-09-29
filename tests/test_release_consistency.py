import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("check_release_consistency", ROOT / "tools/check_release_consistency.py")
consistency = importlib.util.module_from_spec(spec)
spec.loader.exec_module(consistency)


class ReleaseConsistencyTests(unittest.TestCase):
    def test_detects_and_fixes_stale_totals(self):
        with tempfile.TemporaryDirectory() as directory:
            web = Path(directory)
            (web / "data").mkdir()
            people = [{"id": "a", "family_root": {"id": "R"}, "has_original_record": True}, {"id": "b"}, {"id": "c"}]
            (web / "data/catalogue-search-index.json").write_text(json.dumps(people))
            (web / "data/people.json").write_text(json.dumps({"people": people, "count": 3}))
            (web / "health.json").write_text(json.dumps({"counts": {"people": 2}}))
            (web / "catalogue.html").write_text(
                '<p class="lede">Search 2 historical people connected</p><strong id="catalogue-total">2</strong>'
                '<div><strong>2</strong><span>Historical people</span></div>'
                '<div><strong>1</strong><span>People linked to a root</span></div>'
            )
            original, consistency.WEB = consistency.WEB, web
            try:
                problems = consistency.check(fix=False)
                self.assertEqual(4, len(problems), problems)  # health, stat, lede, header; root count is right
                consistency.check(fix=True)
                self.assertEqual([], consistency.check(fix=False))
                page = (web / "catalogue.html").read_text()
                self.assertIn("Search 3 historical people", page)
                self.assertIn('<strong id="catalogue-total">3</strong>', page)
                self.assertEqual(3, json.loads((web / "health.json").read_text())["counts"]["people"])
            finally:
                consistency.WEB = original


if __name__ == "__main__":
    unittest.main()
