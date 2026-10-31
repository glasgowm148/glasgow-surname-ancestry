"""Reviewed creation work must enter the actual catalogue, with complete evidence."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from bs4 import BeautifulSoup
from tools.site_analytics import with_analytics

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

    def test_creation_search_uses_reviewed_father_and_keeps_unknown_mother(self):
        assessment = {
            "assertion_id": "C-reviewed-jane-father", "people": [self.slug, "Glasgow-9001"],
            "profile_names": {self.slug: "Jane Glasgow", "Glasgow-9001": "William Glasgow"},
            "status": "strongly_supported", "publication_status": "approved",
            "working_selection": True, "allow_new_relationship": True,
            "basis": "Reviewed deed identifies Jane's father.",
            "source_ids": ["test-deed-1775"],
            "perspectives": {
                self.slug: {"relationship": "father", "reason": "The reviewed deed names her father."},
                "Glasgow-9001": {"relationship": "daughter", "reason": "The reviewed deed names Jane."},
            },
        }
        path = self.root / "research/relationship_assessments.json"
        path.write_text(json.dumps([assessment]))
        for _ in range(2):
            module.apply_creations(self.root)
            dossier = self.read(f"people/{self.slug}.json")
            row = self.read("data/catalogue-search-index.json")[0]
            self.assertEqual(dossier["relationships"]["parents"][0]["id"], "Glasgow-9001")
            self.assertEqual([p["id"] for p in row["father"]], ["Glasgow-9001"])
            self.assertFalse(row["missing_father"])
            self.assertTrue(row["missing_mother"])
            self.assertEqual(row["mother"], [])

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
        self.assertFalse(person["uncertain_identity"])
        self.assertFalse(row["uncertain_identity"])
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
        html = (self.root / f"www/people/{self.slug}.html").read_text()
        self.assertEqual(html, with_analytics(html))
        self.assertEqual(soup.select_one("#profile-update-draft").get_text(), self.draft)
        self.assertIsNotNone(soup.select_one(f'a[href="/people/{self.slug}.json"]'))
        self.assertIn("Create a new WikiTree profile", soup.get_text())
        self.assertIn("John Smith was a merchant", soup.get_text())
        self.assertIn(self.url, [link["href"] for link in soup.select("a[href]")])
        self.assertIsNotNone(soup.select_one("aside.g-rail"))
        self.assertNotIn("Side-by-side", soup.get_text())
        self.assertNotIn("baptism", soup.get_text())

    def test_creation_registers_local_route_and_preserves_other_script_data(self):
        path = self.root / 'www/assets/unified/routes.js'
        path.parent.mkdir(parents=True)
        suffix = ';\nwindow.GlasgowIcons={"keep":"icon"};\n'
        path.write_text('window.GlasgowRoutes={"glasgow-1521":"glasgow-1521"}' + suffix)
        module.apply_creations(self.root)
        text = path.read_text()
        routes, _ = json.JSONDecoder().raw_decode(text[len('window.GlasgowRoutes='):])
        self.assertEqual(routes[self.slug], self.slug)
        self.assertEqual(routes['glasgow-1521'], 'glasgow-1521')
        self.assertTrue(text.endswith(suffix))
        module.apply_creations(self.root)
        self.assertEqual(path.read_text(), text)

    def test_creation_does_not_overwrite_a_reviewed_route_alias(self):
        path = self.root / 'www/assets/unified/routes.js'
        path.parent.mkdir(parents=True)
        text = 'window.GlasgowRoutes=' + json.dumps({self.slug: 'glasgow-1521'}) + ';'
        path.write_text(text)
        with self.assertRaisesRegex(ValueError, 'existing route alias'):
            module.apply_creations(self.root)
        self.assertEqual(path.read_text(), text)
        self.assertFalse((self.root / f'www/people/{self.slug}.html').exists())

    def test_canonical_findings_override_manifest_and_preserve_hold_candidates(self):
        self.entry.update(creation_status="identity_hold", candidates=[
            {"name": f"Candidate {i}", "profile_id": f"Glasgow-{9000+i}", "status": "HOLD"} for i in range(6)
        ])
        self.save()
        findings = self.root / "research" / self.slug / "findings.md"
        findings.parent.mkdir(parents=True)
        findings.write_text("Last updated: 2026-10-26\n\n## Fresh source review\nCanonical body.\n")
        module.apply_creations(self.root, [self.slug])
        dossier = self.read(f"people/{self.slug}.json")
        self.assertEqual(dossier["provenance"]["research_findings"], f"research/{self.slug}/findings.md")
        self.assertIn("Canonical body.", json.dumps(dossier["research_findings"]))
        self.assertEqual(len(dossier["profile_work"]["candidates"]), 6)
        self.assertEqual(dossier["creation_status"], "identity_hold")
        html = (self.root / f"www/people/{self.slug}.html").read_text()
        self.assertIn("Canonical body.", html)
        self.assertIn(self.draft.replace("<", "&lt;").replace(">", "&gt;"), html)

    def test_reconciles_existing_canonical_rows_without_duplicates(self):
        module.apply_creations(self.root)
        self.entry["assessment"] = "Revised, reviewed identity explanation."
        self.save()
        module.apply_creations(self.root)
        self.assertEqual(len(self.read("data/catalogue-search-index.json")), 1)
        self.assertEqual(len(self.read("data/people-index.json")), 1)
        self.assertEqual(self.read(f"people/{self.slug}.json")["research_findings"][0]["sections"][0]["markdown"], self.entry["assessment"])

    def test_second_apply_refreshes_four_context_indexes_in_place(self):
        files = ("assets/research/search-people.json", "assets/research/search-index.json",
                 "assets/v3/search-people.json", "assets/v3/people-quick.json")
        registry = self.root / "www/assets/research/registry.json"
        registry.parent.mkdir(parents=True)
        (registry.parent / "people").mkdir()
        registry.write_text(json.dumps([{"id": "unrelated-before", "slug": "unrelated-before"}]))
        packed = self.root / "www/assets/v3/registry-packed.json"
        packed.parent.mkdir(parents=True)
        packed.write_text(json.dumps({"fields": ["id", "slug", "name"], "rows": []}))
        before_rows = {}
        after_rows = {}
        for relative in files:
            compact = "/v3/" in relative
            before_rows[relative] = (["unrelated-before", "1786 Glasgow remains unchanged", "x", "y", "z"] if compact else
                                     {"id": "unrelated-before", "life": "1786", "place": "Glasgow", "custom": True})
            after_rows[relative] = (["unrelated-after", "Keep", "a", "b", "c"] if compact else
                                    {"id": "unrelated-after", "custom": "Keep"})
            (self.root / "www" / relative).write_text(json.dumps([before_rows[relative]]))
        self.entry.update(birth="1775", birth_location="Glasgow, Scotland")
        self.save()
        module.apply_creations(self.root, [self.slug])
        # Existing selected rows keep their position, and any old duplicate is retired.
        for relative in files:
            path = self.root / "www" / relative
            rows = json.loads(path.read_text())
            rows.extend([after_rows[relative], rows[1]])
            path.write_text(json.dumps(rows))
        self.entry.update(birth="on or before 1775", birth_location="", birth_note="Bound from the documented event.")
        self.save()
        module.apply_creations(self.root, [self.slug])
        for relative in files:
            rows = self.read(relative)
            self.assertEqual(len(rows), 3)
            self.assertEqual(rows[0], before_rows[relative])
            self.assertEqual(rows[2], after_rows[relative])
            if "/v3/" in relative:
                self.assertEqual(rows[1][0], self.slug)
                self.assertIn("on or before 1775", rows[1][2 if "people-quick" in relative else 3])
                self.assertNotIn("Glasgow, Scotland", json.dumps(rows[1]))
                if "people-quick" in relative:
                    self.assertEqual(rows[1][3], "")
            else:
                self.assertEqual(rows[1]["id"], self.slug)
                self.assertIn("on or before 1775", rows[1]["life"])
                self.assertEqual(rows[1]["place"], "")

    def test_fresh_page_shows_approved_family_without_captured_attachments(self):
        study = '/branches/scottish-deeds/#chapter-family'
        self.entry['assessment'] += f' [Family study]({study}). [Local notes](research/private.md).'
        self.save()
        brother = 'record-peter-glasgow-1775'
        assessments = [{
            'assertion_id': 'C-test-record-siblings', 'people': [self.slug, brother],
            'publication_status': 'approved', 'status': 'proved', 'allow_new_relationship': True,
            'profile_names': {brother: 'Peter Glasgow'},
            'profile_urls': {brother: {'url': f'/people/{brother}.html'}},
            'claim': 'Jane and Peter are siblings', 'basis': 'Named in the deed.',
            'source_ids': ['test-deed-1775'],
            'perspectives': {self.slug: {'relationship': 'sibling', 'reason': 'Named in the deed.'},
                             brother: {'relationship': 'sibling', 'reason': 'Named in the deed.'}},
        }]
        path = self.root / 'research/relationship_assessments.json'
        path.write_text(json.dumps(assessments))
        module.apply_creations(self.root)
        soup = BeautifulSoup((self.root / f'www/people/{self.slug}.html').read_text(), 'html.parser')
        family = soup.select_one('#family')
        self.assertIn('Siblings', family.get_text())
        self.assertIn('Peter Glasgow', family.get_text())
        self.assertIsNotNone(family.select_one(f'a[href="/people/{brother}.html"]'))
        self.assertNotIn('No family attachments', family.get_text())
        self.assertNotIn('wikitree.com/wiki/record-', str(family))
        self.assertIsNotNone(soup.select_one(f'a[href="{study}"]'))
        self.assertIsNone(soup.select_one('a[href="research/private.md"]'))
        siblings = self.read(f'people/{self.slug}.json')['relationships']['siblings']
        self.assertEqual([row['id'] for row in siblings], [brother])
        network = self.read(f'people/{self.slug}.network.json')
        self.assertTrue(any(row['id'] == brother for row in network['relationships']))

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

    def test_rejects_editorial_footer_even_when_the_biography_is_complete(self):
        for footer in ('\n```\n\n## Relationship and source cautions\nDo not copy this.',
                       '\n\n## Identity review — editing log\nNot profile text.'):
            self.entry['draft_wikitext'] = self.draft + footer
            (self.root / self.entry['draft_path']).write_text(self.entry['draft_wikitext'])
            self.save()
            with self.assertRaisesRegex(ValueError, 'editorial Markdown'):
                module.apply_creations(self.root)

    def test_rejects_canonical_collision_with_linked_profile(self):
        data = self.root / "www/data"
        data.mkdir()
        (data / "people.json").write_text(json.dumps({"people": [{"catalogue_id": self.slug, "profile_ids": ["Glasgow-123"]}]}))
        with self.assertRaisesRegex(ValueError, "collision"):
            module.apply_creations(self.root)
        self.assertFalse((data / "catalogue-search-index.json").exists())

    def test_explicit_case_ignores_unrelated_invalid_draft_before_validation(self):
        broken = dict(self.entry, catalogue_id="record-unrelated-walter",
                      draft_path="research/drafts/walter.wiki")
        broken_path = self.root / broken["draft_path"]
        broken_path.write_text("Unrelated existing draft awaiting its own review.")
        manifest = self.root / module.MANIFEST
        manifest.write_text(json.dumps({"new_people": [broken, self.entry]}))
        before_manifest = manifest.read_bytes()
        before_draft = broken_path.read_bytes()
        with self.assertRaisesRegex(ValueError, "maintained draft does not contain reviewed text"):
            module.reviewed_people(self.root)
        selected = [self.slug]
        self.assertEqual(module.reviewed_people(self.root, selected), [self.entry])
        self.assertEqual(len(module.reviewed_records(self.root, selected)), 1)
        self.assertEqual(set(module.reviewed_audits(self.root, selected)), {self.slug})
        self.assertEqual(module.apply_creations(self.root, selected)["integrated"], selected)
        self.assertEqual(broken_path.read_bytes(), before_draft)
        self.assertEqual(manifest.read_bytes(), before_manifest)
        self.assertFalse((self.root / "www/people/record-unrelated-walter.json").exists())
        self.assertEqual([p["catalogue_id"] for p in self.read("data/people.json")["people"]], selected)

    def test_unknown_or_duplicate_explicit_selection_fails_before_writes(self):
        before = {str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        for selected, error in (([self.slug, "record-unknown"], "Unknown requested"),
                                ([self.slug, self.slug], "Duplicate requested")):
            with self.subTest(selected=selected):
                with self.assertRaisesRegex(ValueError, error):
                    module.apply_creations(self.root, selected)
                after = {str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
                self.assertEqual(after, before)

    def test_source_verification_hold_remains_visible_without_creation_ready_claim(self):
        self.entry["creation_status"] = "hold_source_verification"
        self.save()
        module.apply_creations(self.root)
        row = self.read("data/catalogue-search-index.json")[0]
        self.assertTrue(row["missing_profile"])
        self.assertTrue(row["needs_wikitree_update"])
        self.assertFalse(row["creation_ready"])
        self.assertEqual(row["profile_work_status"], "identity_hold")
        self.assertFalse(row["uncertain_identity"])
        self.assertFalse(self.read("data/people.json")["people"][0]["uncertain_identity"])
        self.assertIn("verify the source before creation", row["wikitree_update_summary"])
        soup = BeautifulSoup((self.root / f"www/people/{self.slug}.html").read_text(), "html.parser")
        self.assertIn("source verification on HOLD", soup.get_text())
        self.assertNotIn("Create a new WikiTree profile", soup.get_text())
        self.assertEqual(module.reviewed_audits(self.root)[self.slug]["recommended_action"], "hold")
        self.assertEqual(module.reviewed_audits(self.root)[self.slug]["identity_status"], "hold_source_verification")
        self.assertNotIn("identity on HOLD", soup.get_text())

    def test_identity_hold_preserves_reviewed_candidates_and_counts(self):
        candidates = [{"profile_id": "Glasgow-321", "name": "Jane Glasgow",
                       "url": "https://www.wikitree.com/wiki/Glasgow-321",
                       "assessment": "Compatible locality; spouse unresolved.",
                       "status": "compatible", "reviewed_at": "2026-10-17"}]
        self.entry.update(creation_status="identity_hold", candidates=candidates)
        self.save()
        audit = module.reviewed_audits(self.root)[self.slug]
        self.assertEqual(audit["identity_status"], "identity_hold")
        self.assertEqual(audit["candidates"], candidates)
        module.apply_creations(self.root)
        person = self.read("data/people.json")["people"][0]
        row = self.read("data/catalogue-search-index.json")[0]
        dossier = self.read(f"people/{self.slug}.json")
        self.assertEqual(person["creation_candidates"], candidates)
        self.assertEqual(person["profile_work_candidate_count"], 1)
        self.assertEqual(row["profile_work_candidate_count"], 1)
        self.assertEqual(row["profile_work_status"], "existing_profile_candidate")
        self.assertTrue(person["uncertain_identity"])
        self.assertTrue(row["uncertain_identity"])
        self.assertEqual(dossier["profile_work"]["candidates"], candidates)
        self.assertEqual(dossier["wikitree_update"]["candidates"], candidates)
        self.assertEqual(dossier["wikitree_update"]["candidate_count"], 1)
        self.assertFalse(row["creation_ready"])
        self.assertIn("resolve the identity before creation", row["wikitree_update_summary"])
        soup = BeautifulSoup((self.root / f"www/people/{self.slug}.html").read_text(), "html.parser")
        panel = soup.select_one("#wikitree-update")
        self.assertIn("identity on HOLD", panel.get_text())
        self.assertIn("Reviewed possible existing-profile matches (1)", panel.get_text())
        self.assertIsNotNone(panel.select_one('a[href="https://www.wikitree.com/wiki/Glasgow-321"]'))
        self.assertNotIn("source verification on HOLD", soup.get_text())
        self.assertNotIn("verify the source before creation", soup.get_text())

    def test_identity_hold_classification_tracks_compatible_candidates(self):
        self.entry["creation_status"] = "identity_hold"
        candidates = [{"profile_id": "Glasgow-1227", "status": "compatible_candidate"},
                      {"profile_id": "Glasgow-1235", "status": "compatible_candidate"}]
        for reviewed_candidates, expected in ((candidates, "existing_profile_candidate"), ([], "identity_hold")):
            with self.subTest(candidate_count=len(reviewed_candidates)):
                self.entry["candidates"] = reviewed_candidates
                person = module.decorate_person({}, self.entry)
                self.assertEqual(person["profile_work_status"], expected)
                self.assertEqual(person["profile_work_candidate_count"], len(reviewed_candidates))
                self.assertEqual(person["creation_status"], "identity_hold")
                self.assertTrue(person["pending_profile_creation"])
                self.assertFalse(person["creation_ready"])
                self.assertTrue(person["uncertain_identity"])
                audit = {"recommended_action": "hold", "candidates": reviewed_candidates}
                self.assertEqual(module.catalogue._profile_work_status(person, audit), expected)

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

    def test_reviewed_person_occupations_override_relative_mentions_in_dossiers(self):
        cases = [
            ([], "Her husband John Smith was a merchant."),
            (["gardener"], "Charles was a gardener; his father Thos was a labourer."),
            (["labourer"], "John appears in the family roster."),
        ]
        for occupations, note in cases:
            with self.subTest(occupations=occupations):
                self.entry["occupations"] = occupations
                self.entry["records"][0]["note"] = note
                self.save()
                records = module.reviewed_records(self.root)
                people = module.catalogue._build_people(records, {}, [], {}, {"profiles": {}})
                person = module.decorate_person(people[0], self.entry)
                dossiers, resolver = module.build_machine_models([person])
                dossier = dossiers[self.slug]
                self.assertEqual(dossier["identity"]["occupations"], occupations)
                person = next(row for row in resolver if row["id"] == self.slug)
                self.assertEqual(person["occupations"], occupations)
                compact = module.compact_resolver_row(person)
                self.assertEqual(compact.get("occupations", []), occupations)

    def test_creation_keeps_parents_but_not_existing_profile_amendment_badges(self):
        self.entry["relationship_changes"] = [{"action": "add", "relationship": "father",
                                                "relative_id": "Glasgow-428", "status": "proved", "confidence_percent": 95},
                                               {"action": "add", "relationship": "mother",
                                                "relative_id": "Example-3", "status": "strongly_supported"}]
        self.save()
        module.apply_creations(self.root)
        dossier = self.read(f"people/{self.slug}.json")
        row = self.read("data/catalogue-search-index.json")[0]
        changes = dossier["wikitree_update"]["relationship_changes"]
        self.assertEqual(changes[0]["relative_id"], "Glasgow-428")
        self.assertEqual(changes[0]["relationship"], "father")
        self.assertEqual(changes[0]["confidence_band"], "confident")
        self.assertEqual(changes[0]["probability"]["minimum"], .9)
        self.assertEqual(changes[0]["confidence_percent"], 95)
        self.assertEqual(changes[1]["relationship"], "mother")
        self.assertIsNone(changes[1]["probability"]["value"])
        self.assertEqual(row["wikitree_update_relationship_changes"], [])
        self.assertTrue(row["needs_wikitree_update"])
        source_queue = json.loads((self.root / module.MANIFEST).read_text())
        self.assertEqual(source_queue["new_people"][0]["relationship_changes"], self.entry["relationship_changes"])


if __name__ == "__main__":
    unittest.main()
