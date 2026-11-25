from contextlib import redirect_stdout
import importlib.util
from io import StringIO
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("check_release_consistency", ROOT / "tools/check_release_consistency.py")
consistency = importlib.util.module_from_spec(spec)
spec.loader.exec_module(consistency)


class ReleaseConsistencyTests(unittest.TestCase):
    def test_stale_manifest_remains_a_blocker_after_repairing_headline_totals(self):
        with tempfile.TemporaryDirectory() as directory:
            web = Path(directory)
            data = web / 'data'
            data.mkdir()
            (data / 'catalogue-search-index.json').write_text('[{}]')
            (data / 'people.json').write_text('{"people": [{}]}')
            (data / 'records-index.json').write_text('[{}, {}]')
            manifest = data / 'manifest.json'
            original = '{"datasets": [{"name": "people", "count": 1}, {"name": "records", "count": 1}]}'
            manifest.write_text(original)
            (web / 'health.json').write_text('{"counts": {"people": 1, "records": 1}}')

            with patch.object(consistency, 'WEB', web):
                self.assertEqual(['manifest.json records: 1 != 2'], consistency.repair_totals())

            self.assertEqual(original, manifest.read_text())
            self.assertEqual(2, json.loads((web / 'health.json').read_text())['counts']['records'])

    def test_record_and_place_totals_follow_the_published_indexes(self):
        with tempfile.TemporaryDirectory() as directory:
            web = Path(directory)
            (web / "data").mkdir()
            for filename, value in {
                'catalogue-search-index.json': [], 'people.json': {'people': []},
                'records-index.json': [{}, {}], 'places-index.json': [{}],
            }.items():
                (web / 'data' / filename).write_text(json.dumps(value))
            (web / 'health.json').write_text(json.dumps({'counts': {'people': 0, 'records': 1, 'places': 2}}))
            (web / 'status.html').write_text('<strong>1</strong><span>Mapped records</span><strong>2</strong><span>Research places</span>')
            original, consistency.WEB = consistency.WEB, web
            try:
                problems = consistency.check(fix=False)
                self.assertEqual(5, len(problems))
                self.assertTrue(any('source_links' in issue for issue in problems))
                consistency.check(fix=True)
                self.assertEqual([], consistency.check(fix=False))
                self.assertEqual({'people': 0, 'records': 2, 'places': 1},
                                 json.loads((web / 'health.json').read_text())['counts'])
            finally:
                consistency.WEB = original

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

    def test_home_coverage_and_records_share_index_totals(self):
        with tempfile.TemporaryDirectory() as directory:
            web = Path(directory)
            (web / "data").mkdir()
            (web / "coverage").mkdir()
            (web / "records").mkdir()
            (web / "data/catalogue-search-index.json").write_text('[{}]')
            (web / "data/people.json").write_text('{"people": [{}]}')
            (web / "data/records-index.json").write_text('[{}, {}]')
            (web / "index.html").write_text("Search 3 people by name")
            (web / "coverage/index.html").write_text('<strong class="r-coverage-number">5</strong><p>People in the index</p>')
            (web / "records/index.html").write_text('<strong>4</strong><span>record entries</span>')
            with patch.object(consistency, 'WEB', web):
                self.assertEqual(len(consistency.check(fix=True)), 3)
                self.assertEqual(consistency.check(fix=False), [])
            self.assertIn('Search 1 people', (web / "index.html").read_text())
            self.assertIn('>2<', (web / "records/index.html").read_text())

            strip = '<div class="records-status-strip"><div><strong>1</strong><span>Source cited</span></div></div><p id="records-scope">'
            (web / "records/index.html").write_text(strip)
            with patch.object(consistency, 'WEB', web):
                self.assertEqual(consistency.check(fix=False), ['records/index.html citation-status counts: 1 != 2'])

    def test_fix_exits_unsuccessfully_when_people_data_disagrees(self):
        with tempfile.TemporaryDirectory() as directory:
            web = Path(directory)
            (web / "data").mkdir()
            (web / "data/catalogue-search-index.json").write_text('[{}]')
            (web / "data/people.json").write_text('{"people": [], "count": 0}')
            (web / "health.json").write_text('{"counts": {"people": 0}}')
            output = StringIO()
            with patch.object(consistency, "WEB", web), patch(
                "sys.argv", ["check_release_consistency", "--fix", "--no-research"],
            ), redirect_stdout(output):
                with self.assertRaises(SystemExit) as failure:
                    consistency.main()

            self.assertEqual(1, failure.exception.code)
            self.assertIn("fixed: health.json people: 0 != 1", output.getvalue())
            self.assertIn("MISMATCH: people.json people: 0 != search index 1", output.getvalue())
            self.assertNotIn("fixed: people.json", output.getvalue())


if __name__ == "__main__":
    unittest.main()
