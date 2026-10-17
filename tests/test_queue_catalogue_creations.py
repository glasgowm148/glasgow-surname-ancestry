"""Reviewed creation work must enter the actual catalogue, with complete evidence."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from bs4 import BeautifulSoup

spec = importlib.util.spec_from_file_location("queue_creations", Path(__file__).resolve().parents[1] / "tools/queue_catalogue_creations.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class QueueCatalogueCreationsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.slug = "record-jane-glasgow-1775"
        self.url = "https://www.scotlandspeople.gov.uk/record/1775-jane"
        self.draft = '''[[Category:Glasgow Name Study]]
== Biography ==
Jane Glasgow was named as John Smith's wife in a deed in 1775.<ref>[https://www.scotlandspeople.gov.uk/record/1775-jane Deed, 1775], Jane Glasgow, wife of John Smith.</ref>
== Research Notes ==
The deed does not give her birth date. No compatible profile survived the documented review.
== Sources ==
<references />'''
        self.entry = {
            "subject_id": "jane-1775", "catalogue_id": self.slug, "name": "Jane Glasgow",
            "source_subject_url": self.url, "draft_path": "research/drafts/jane.wiki", "draft_wikitext": self.draft,
            "assessment": "The deed identifies Jane Glasgow as John Smith's wife; the 1775 occurrence is not a birth date.",
            "first_names": ["Jane"], "last_names_at_birth": ["Glasgow"], "last_names_current": ["Smith"], "gender": "Female",
            "birth": "", "birth_location": "", "death": "", "death_location": "",
            "records": [{"person": "Jane Glasgow", "year": "1775", "filter_year": 1775, "family_group": "Scottish deeds",
                "record_location": "Edinburgh, Scotland", "association": "Wife of John Smith in a deed", "note": "Her husband John Smith was a merchant.",
                "evidence": "Proved", "source_title": "Deed, 1775", "source_url": self.url, "source_type": "original"}],
        }
        path = self.root / self.entry["draft_path"]
        path.parent.mkdir(parents=True)
        path.write_text(self.draft)
        (self.root / "www/people").mkdir(parents=True)
        (self.root / "www/people/glasgow-1521.html").write_text('''<!doctype html><html><head><title>William Glasgow</title></head>
<body><aside class="g-rail">Shared navigation</aside><main class="v3-dossier"></main></body></html>''')
        self.save()

    def save(self):
        path = self.root / module.MANIFEST
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"new_people": [self.entry], "profile_updates": {}}))

    def read(self, relative):
        return json.loads((self.root / "www" / relative).read_text())

    def test_integrates_main_filters_complete_draft_evidence_and_is_idempotent(self):
        self.assertEqual(module.apply_creations(self.root)["count"], 1)
        module.apply_creations(self.root)
        people = self.read("data/people.json")
        self.assertEqual(people["count"], 1)
        person = people["people"][0]
        self.assertEqual(person["last_names_current"], ["Smith"])
        self.assertEqual(person["birth"], "")
        row = self.read("data/catalogue-search-index.json")[0]
        self.assertTrue(row["missing_profile"])
        self.assertTrue(row["needs_wikitree_update"])
        self.assertEqual(row["profile_work_status"], "creation_ready")
        self.assertGreater(row["wikitree_update_significance"], 0)
        self.assertIsNone(row["birth_year"])
        self.assertEqual(row["date_years"], [1775])
        self.assertEqual(row["record_count"], 1)
        self.assertEqual(self.read("data/people-index.json")[0]["catalogue_id"], self.slug)
        dossier = self.read(f"people/{self.slug}.json")
        self.assertEqual(dossier["wikitree_update"]["proposed_wikitext"], self.draft)
        self.assertEqual(dossier["evidence"][0]["source"]["url"], self.url)
        self.assertTrue(dossier["research_findings"])
        self.assertTrue((self.root / f"www/people/{self.slug}.network.json").exists())
        soup = BeautifulSoup((self.root / f"www/people/{self.slug}.html").read_text(), "html.parser")
        self.assertEqual(soup.select_one("#profile-update-draft").get_text(), self.draft)
        self.assertIn("Create a new WikiTree profile", soup.get_text())
        self.assertIn("John Smith was a merchant", soup.get_text())
        self.assertIn(self.url, [link["href"] for link in soup.select("a[href]")])
        self.assertIsNotNone(soup.select_one("aside.g-rail"))
        self.assertNotIn("Side-by-side", soup.get_text())
        self.assertNotIn("baptism", soup.get_text())

    def test_reconciles_existing_canonical_rows_without_duplicates(self):
        module.apply_creations(self.root)
        self.entry["assessment"] = "Revised, reviewed identity explanation."
        self.save()
        module.apply_creations(self.root)
        self.assertEqual(len(self.read("data/catalogue-search-index.json")), 1)
        self.assertEqual(len(self.read("data/people-index.json")), 1)
        self.assertEqual(self.read(f"people/{self.slug}.json")["research_findings"][0]["sections"][0]["markdown"], self.entry["assessment"])

    def test_rejects_uncited_incomplete_or_nonhistorical_entries_before_writes(self):
        for field, value in (("draft_wikitext", "== Biography ==\nEmpty"), ("records", []), ("living", True)):
            with self.subTest(field=field):
                original = self.entry.get(field)
                self.entry[field] = value
                self.save()
                with self.assertRaises(ValueError):
                    module.apply_creations(self.root)
                self.assertFalse((self.root / "www/data/people.json").exists())
                if original is None:
                    del self.entry[field]
                else:
                    self.entry[field] = original

    def test_rejects_canonical_collision_with_linked_profile(self):
        data = self.root / "www/data"
        data.mkdir()
        (data / "people.json").write_text(json.dumps({"people": [{"catalogue_id": self.slug, "profile_ids": ["Glasgow-123"]}]}))
        with self.assertRaisesRegex(ValueError, "collision"):
            module.apply_creations(self.root)
        self.assertFalse((data / "catalogue-search-index.json").exists())

    def test_source_verification_hold_remains_visible_without_creation_ready_claim(self):
        self.entry["creation_status"] = "hold_source_verification"
        self.save()
        module.apply_creations(self.root)
        row = self.read("data/catalogue-search-index.json")[0]
        self.assertTrue(row["missing_profile"])
        self.assertTrue(row["needs_wikitree_update"])
        self.assertFalse(row["creation_ready"])
        self.assertEqual(row["profile_work_status"], "identity_hold")
        self.assertIn("verify the source before creation", row["wikitree_update_summary"])
        soup = BeautifulSoup((self.root / f"www/people/{self.slug}.html").read_text(), "html.parser")
        self.assertIn("source verification on HOLD", soup.get_text())
        self.assertNotIn("Create a new WikiTree profile", soup.get_text())
        self.assertEqual(module.reviewed_audits(self.root)[self.slug]["recommended_action"], "hold")

    def test_age_supported_later_record_does_not_fabricate_birth(self):
        self.entry["records"][0].update(year="1911", filter_year=1911)
        self.entry["historical_basis"] = {"earliest_birth_year": 1840, "latest_birth_year": 1841, "source_url": self.url}
        self.save()
        module.apply_creations(self.root)
        row = self.read("data/catalogue-search-index.json")[0]
        self.assertIsNone(row["birth_year"])
        self.assertEqual(row["birth"], "")
        del self.entry["historical_basis"]
        self.save()
        with self.assertRaisesRegex(ValueError, "historical"):
            module.reviewed_people(self.root)

    def test_builder_hooks_keep_unknown_vitals_and_pending_creation(self):
        records = module.reviewed_records(self.root)
        self.assertEqual(records[0]["birth_status"], "unknown")
        people = module.catalogue._build_people(records, {}, [], {}, {"profiles": {}})
        person = module.decorate_person(people[0], self.entry)
        self.assertEqual(person["birth"], "")
        self.assertEqual(person["birth_location"], "")
        self.assertEqual(module.reviewed_audits(self.root)[self.slug]["recommended_action"], "create_new_profile")
        self.assertEqual(module.creation_update(person)["action"], "create_new_profile")
        self.assertIsNone(module.creation_update({"profile_ids": ["Glasgow-123"]}))


if __name__ == "__main__":
    unittest.main()
