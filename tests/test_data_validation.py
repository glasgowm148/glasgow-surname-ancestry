import json
import tempfile
import unittest
from pathlib import Path

from tools.validate_data import validate_catalogue, validate_map_records


class DataValidationTests(unittest.TestCase):
    def test_repository_outputs_match_contracts(self):
        self.assertEqual([], validate_map_records())
        self.assertEqual([], validate_catalogue())

    def test_map_validation_rejects_missing_columns(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "records.csv"
            path.write_text("profile_id\nGlasgow-1\n", encoding="utf-8")
            self.assertTrue(any("missing columns" in error for error in validate_map_records(path)))

    def test_catalogue_validation_rejects_count_drift(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "people.json"
            path.write_text(json.dumps({"schema_version": "1.0", "count": 1, "people": []}), encoding="utf-8")
            self.assertTrue(any("count does not match" in error for error in validate_catalogue(path)))
