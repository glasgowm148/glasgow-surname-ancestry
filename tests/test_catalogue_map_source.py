"""Source and data contracts for the filtered People catalogue map."""

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class CatalogueMapSourceTests(unittest.TestCase):
    def test_map_joins_only_filtered_catalogue_ids_to_supplied_points(self):
        people = json.loads((ROOT / "www/data/catalogue-search-index.json").read_text())
        points = json.loads((ROOT / "www/assets/research/map-points.json").read_text())
        ids = {str(person["id"]) for person in people}
        mapped = {
            str(item[1])
            for point in points
            for item in point.get("items", [])
            if isinstance(item, list) and len(item) > 1 and str(item[1]) in ids
        }
        self.assertGreater(len(mapped), 100)
        self.assertTrue(mapped <= ids)
        self.assertTrue(any(str(person["id"]) not in mapped for person in people))

    def test_map_source_preserves_precision_and_profile_links(self):
        source = (ROOT / "tools/catalogue_search.js").read_text()
        self.assertIn("Supplied representative point", source)
        self.assertIn("map-country-associations.json", source)
        self.assertIn("Coordinates and precision are inherited", source)
        self.assertIn('personUrl(person)', source)
        self.assertIn('if(resultView===\'map\')', source)
        self.assertIn('params.set(\'view\',\'map\')', source)


if __name__ == "__main__":
    unittest.main()
