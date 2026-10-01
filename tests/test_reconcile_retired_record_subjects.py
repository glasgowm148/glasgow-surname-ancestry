import csv
import io
import json
import tempfile
import unittest
from pathlib import Path

from tools.reconcile_retired_record_subjects import (
    CURRENT, DISPLAY_NAME, NAME, NEW_SOURCE, OLD, OLD_SOURCE, PROFILE, plan, restore, write_plan,
)


class RetiredRecordReconciliationTests(unittest.TestCase):
    def test_stale_queue_orphan_retired_without_losing_record_and_reversible(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            def put(path, data):
                target = root / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(json.dumps(data))

            put("data/wikitree/catalogue-profile-links.json", {"entries": {
                OLD: {"profile_id": PROFILE}, "record-edinburgh-1577-john-family": {
                    "record_profiles": {NEW_SOURCE: PROFILE}}}})
            put("data/wikitree/catalogue-profile-audit.json", {"entries": {
                OLD: {"recommended_action": "create_new_profile"},
                "unrelated": {"recommended_action": "hold"}}})
            put(f"www/people/{CURRENT}.json", {"id": PROFILE, "name": NAME,
                "research_findings": [{"source": "approved testament reading"}]})
            record = {"source_title": OLD_SOURCE, "year": "1577", "record_id": "original",
                      "source_url": "https://example.org/original", "note": "creation ready"}
            put("www/data/people.json", {"count": 3, "people": [
                {"catalogue_id": OLD, "records": [record], "evidence": ["Documented"]},
                {"catalogue_id": CURRENT, "name": "Margaret Glasgow", "records": [
                    {"source_title": "Birth export", "year": "1575", "record_id": "birth"}],
                    "father": [{"id": "Glasgow-3181"}]},
                {"catalogue_id": "unrelated", "name": "Preserve me", "records": []}]})
            compact = [{"id": OLD, "catalogue_id": OLD},
                       {"id": PROFILE, "catalogue_id": CURRENT, "name": "Margaret Glasgow",
                        "mother_id": None, "reviewed_relationships": {"parents": []}},
                       {"id": "Unrelated-1", "catalogue_id": "unrelated", "name": "Preserve me"}]
            put("www/data/people-index.json", compact)
            put("www/data/catalogue-search-index.json", [
                {"id": OLD, "profile_work_status": "creation_ready"},
                {"id": CURRENT, "name": "Margaret Glasgow", "date_years": [1575]},
                {"id": "unrelated", "name": "Preserve me"}])
            (root / "www/data/people-index.js").write_text("old index")
            put("www/data/resolve/andrew-glasgow.json", {"candidate_count": 2,
                "candidates": [compact[0], compact[2]]})
            registry = [{"id": OLD, "slug": OLD, "name": "Andrew Glasgow"},
                        {"id": PROFILE, "slug": CURRENT, "name": "Margaret Glasgow",
                         "imported": {"name": "Margaret Glasgow"},
                         "search": "Margaret Glasgow Glasgow-3589"},
                        {"id": "Unrelated-1", "slug": "unrelated", "name": "Margaret Glasgow",
                         "search": "Historical mention " + OLD}]
            put("www/assets/research/registry.json", registry)
            put("www/assets/research/search-people.json", registry)
            put("www/assets/research/search-index.json", registry + [
                {"id": "0190c9f52d85ab4f", "kind": "record", "name": "Old record",
                 "search": "[Androw?/Andrew] Glasgow " + OLD + " " + OLD_SOURCE}])
            fields = ["slug", "name", "id"]  # Deliberately reordered packed fields.
            put("www/assets/v3/registry-packed.json", {"fields": fields,
                "rows": [[row[field] for field in fields] for row in registry]})
            put("www/assets/v3/people-quick.json", [
                [row["id"], row["name"], "Life", "Place", row["slug"]] for row in registry])
            put("www/assets/v3/search-people.json", [
                [row["id"], row["name"], f'/people/{row["slug"]}.html', "Meta", row.get("search", "")]
                for row in registry] + [["Brown-1", "Other historical woman", "Life and place"]])
            put(f"www/assets/research/people/{CURRENT}.json", {
                "id": PROFILE, "name": "Margaret Glasgow", "original_vitals": {"name": "Margaret Glasgow"},
                "events": [{"p": CURRENT, "person": "Margaret Glasgow"}]})
            put(f"www/people/{OLD}.json", {"id": OLD, "profile_work_status": "creation_ready"})
            put(f"www/people/{OLD}.network.json", {"person": {"id": OLD}})
            (root / f"www/people/{OLD}.html").write_text(
                '<html><head><title>Old</title><link rel="stylesheet" href="/shell.css"></head>'
                '<body><nav id="site-nav">Keep navigation</nav><main>Creation ready</main>'
                '<footer>Keep footer</footer></body></html>')
            stream = io.StringIO(newline="")
            writer = csv.DictWriter(stream, fieldnames=["person", "profile_id", "source_title",
                "gender", "association", "note", "source_status", "birth_date", "birth_status",
                "birth_location", "record_location"])
            writer.writeheader()
            writer.writerow({"person": "Andrew Glasgow", "source_title": OLD_SOURCE,
                "birth_date": "bef. 1577", "birth_location": "Hirmenschelis", "gender": "Male",
                "record_location": "Hirmenschelis — derivative household locality"})
            path = root / "www/map/data/records.csv"
            path.parent.mkdir(parents=True)
            path.write_text(stream.getvalue(), encoding="utf-8-sig")

            before = {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}
            changes = plan(root)
            self.assertEqual(before, {str(p.relative_to(root)): p.read_bytes()
                                      for p in root.rglob("*") if p.is_file()})
            backup = root / "backup"
            write_plan(root, changes, backup)
            people = json.loads((root / "www/data/people.json").read_text())
            self.assertEqual(people["count"], 2)
            person = next(p for p in people["people"] if p["catalogue_id"] == CURRENT)
            self.assertEqual(person["name"], DISPLAY_NAME)
            self.assertEqual(person["first_names"], ["Marjorie"])
            self.assertEqual([r["record_id"] for r in person["records"]], ["birth", "original"])
            self.assertEqual(person["records"][1]["source_title"], NEW_SOURCE)
            self.assertEqual(person["records"][1]["person"], NAME)
            self.assertEqual(person["records"][1]["source_url"], record["source_url"])
            self.assertEqual(person["father"], [{"id": "Glasgow-3181"}])
            self.assertEqual(people["people"][-1], {"catalogue_id": "unrelated", "name": "Preserve me", "records": []})
            rows = list(csv.DictReader(io.StringIO(path.read_text(encoding="utf-8-sig"))))
            self.assertEqual(rows[0]["profile_id"], PROFILE)
            self.assertEqual(rows[0]["birth_date"], "")
            self.assertIn("derivative household", rows[0]["record_location"])
            self.assertNotIn(OLD, (root / "www/data/people-index.js").read_text())
            resolver = json.loads((root / "www/data/resolve/andrew-glasgow.json").read_text())
            self.assertEqual(resolver["candidate_count"], 1)
            self.assertEqual(resolver["candidates"], [compact[2]])
            alias = json.loads((root / f"www/people/{OLD}.json").read_text())
            self.assertEqual(alias["redirect_to"], f"/people/{CURRENT}.json")
            self.assertEqual(alias["name"], DISPLAY_NAME)
            current_dossier = json.loads((root / f"www/people/{CURRENT}.json").read_text())
            self.assertEqual(current_dossier["name"], DISPLAY_NAME)
            self.assertEqual(current_dossier["research_findings"], [{"source": "approved testament reading"}])
            secondary = json.loads((root / "www/assets/research/registry.json").read_text())
            self.assertEqual(len(secondary), 2)
            self.assertEqual(secondary[0]["name"], DISPLAY_NAME)
            self.assertEqual(secondary[0]["imported"], {"name": "Margaret Glasgow"})
            self.assertEqual(secondary[0]["search"], "Marjorie Glasgow Glasgow-3589")
            self.assertEqual(secondary[1], registry[2])
            packed = json.loads((root / "www/assets/v3/registry-packed.json").read_text())
            self.assertEqual(packed["fields"], fields)
            self.assertEqual(packed["rows"][0], [CURRENT, DISPLAY_NAME, PROFILE])
            quick = json.loads((root / "www/assets/v3/people-quick.json").read_text())
            self.assertEqual(quick[0][1], DISPLAY_NAME)
            self.assertEqual(len(quick), 2)
            compact_search = json.loads((root / "www/assets/v3/search-people.json").read_text())
            self.assertEqual(compact_search[-1], ["Brown-1", "Other historical woman", "Life and place"])
            context = json.loads((root / f"www/assets/research/people/{CURRENT}.json").read_text())
            self.assertEqual(context["events"][0]["person"], DISPLAY_NAME)
            self.assertEqual(context["original_vitals"], {"name": "Margaret Glasgow"})
            secondary_search = json.loads((root / "www/assets/research/search-index.json").read_text())
            self.assertEqual(secondary_search[-1]["id"], "0190c9f52d85ab4f")
            self.assertIn(NEW_SOURCE, secondary_search[-1]["search"])
            self.assertNotIn("creation_ready", json.dumps(alias))
            page = (root / f"www/people/{OLD}.html").read_text()
            self.assertIn("Keep navigation", page)
            self.assertIn("Keep footer", page)
            self.assertIn("/shell.css", page)
            self.assertIn("Superseded reading", page)
            self.assertFalse(plan(root), "Second run must be idempotent")
            restore(root, backup)
            for relative, content in before.items():
                self.assertEqual((root / relative).read_bytes(), content)


if __name__ == "__main__":
    unittest.main()
