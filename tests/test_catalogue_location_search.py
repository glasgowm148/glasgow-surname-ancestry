import json
import tempfile
from pathlib import Path
import unittest

from tools.catalogue_location_search import enrichment, refresh_search_indexes


class CatalogueLocationSearchTest(unittest.TestCase):
  def test_enrichment_keeps_marriage_and_biography_scopes_separate(self):
    person = {
        "catalogue_id": "Example-1",
        "profile_ids": ["Example-1"],
        "spouses": [{"marriage_location": "Unique Marriage Parish"}],
    }
    dossier = {
        "presentation": {
            "opening": "Unique biography phrase records a life in the archive.",
            "biography_sections": [{"markdown": "The [public account](https://example.test) says more."}],
        },
        "events": [
            {"event_type": "marriage", "place": "Genuine Record Chapel",
             "participants": [{"id": "Example-1", "role": "Groom"}]},
            {"event_type": "marriage", "place": "Child Marriage Church",
             "participants": [{"id": "Example-1", "role": "Father of the groom"}]},
            {"event_type": "marriage", "place": "Malformed participant", "participants": [None]},
        ],
    }
    fields = enrichment(person, dossier)
    self.assertEqual(fields["marriage_locations"], ["Unique Marriage Parish", "Genuine Record Chapel"])
    self.assertIn("unique biography phrase", fields["biography_text"].lower())
    self.assertNotIn("https://", fields["biography_text"])
    self.assertNotIn("Child Marriage Church", fields["marriage_locations"])
    self.assertNotIn("Unique Marriage Parish", fields["biography_text"])
    self.assertNotIn("unique biography phrase", " ".join(fields["marriage_locations"]).lower())


  def test_targeted_refresh_updates_json_and_javascript_index(self):
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        (root / "www/data").mkdir(parents=True)
        (root / "www/people").mkdir()
        person = {"catalogue_id": "Example-2", "profile_ids": [], "spouses": []}
        (root / "www/data/people.json").write_text(json.dumps({"people": [person]}))
        (root / "www/people/example-2.json").write_text(json.dumps({
            "presentation": {"opening": "Bio-only needle term."},
        }))
        (root / "www/data/catalogue-search-index.json").write_text(json.dumps([{"id": "Example-2"}]))
        (root / "www/data/people-index.js").write_text("window.glasgowPeopleIndex=[];\n")

        self.assertEqual(refresh_search_indexes(root), 1)
        row = json.loads((root / "www/data/catalogue-search-index.json").read_text())[0]
        self.assertEqual(row["marriage_locations"], [])
        self.assertEqual(row["biography_text"], "Bio-only needle term.")
        self.assertEqual(json.loads((root / "www/data/people-index.js").read_text().split("=", 1)[1].rstrip(";\n"))[0], row)
