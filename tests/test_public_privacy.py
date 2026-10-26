import json
from pathlib import Path
import tempfile
import unittest

from tools.public_privacy import PublicPrivacy, likely_living, evidence_envelope, from_sources, tester_identifier_pattern, remove_withheld_subject_routes, repair_orphaned_subjects, refresh_positional_search_mirrors, refresh_registry_mirror, remove_withheld_model_nodes
from tools.build_research_catalog import _wikitree_evidence_html, _likely_living, _build_people


class PublicPrivacyTests(unittest.TestCase):
    def test_old_withheld_nodes_are_removed_without_losing_groups_or_people(self):
        with tempfile.TemporaryDirectory() as directory:
            web = Path(directory)
            path = web / 'assets/research/atlas-model.json'
            path.parent.mkdir(parents=True)
            public = [{'id': '@group', 'kind': 'group'}, {'id': 'Example-100', 'kind': 'person'}]
            path.write_text(json.dumps({'meta': {'people': 2}, 'people': public + [{'id': '', 'withheld': True}]}))
            self.assertEqual(1, remove_withheld_model_nodes(web)['withheld_model_nodes'])
            self.assertEqual({'meta': {'people': 1}, 'people': public}, json.loads(path.read_text()))
            self.assertEqual(0, remove_withheld_model_nodes(web)['model_privacy_files'])

    def test_map_items_drop_whole_private_or_malformed_tuples(self):
        public = ['public', 'Example-100', 1800, False]
        point = {'lat': 55, 'lon': -3, 'items': [public, ['private', 'Example-200', 1980, False], ['broken', 1980, False]]}
        expected = {**point, 'items': [public]}
        self.assertEqual(expected, self.policy.project(point))
        self.assertEqual(expected, self.policy.project(self.policy.project(point)))
    def test_packed_model_projection_retains_string_table_references(self):
        from tools.site_payloads import pack_model, unpack_model
        public = {'id': 'Example-100', 'name': 'Historical subject', 'birth': '1800'}
        value = {'people': [{'id': 'Example-200', 'name': 'Private name'}, public]}
        projected = self.policy.project(pack_model(value))
        self.assertEqual({'people': [public]}, unpack_model(projected))
        self.assertEqual(projected, self.policy.project(projected))

    def test_search_terms_named_fields_and_rows_are_not_packed_tables(self):
        postings = {'fields': [1, 3], 'rows': [2, 4], 'public': [3]}
        self.assertEqual(postings, self.policy.project(postings))

    def test_prepared_search_strings_and_postings_are_remapped_together(self):
        table = {'schema_version': 1, 'fields': ['id', 'name'],
                 'strings': ['Example-200', 'Private Example', 'Example-100', 'Historic subject'],
                 'rows': [[-1, -2], [-3, -4]], 'search': {'shared': [0, 1], 'private': [0], 'historic': [1]},
                 'location_search': {'place': [1]}, 'sort_keys': ['name']}
        expected = {'schema_version': 1, 'fields': ['id', 'name'],
                    'strings': ['Example-100', 'Historic subject'], 'rows': [[-1, -2]],
                    'search': {'shared': [0], 'historic': [0]}, 'location_search': {'place': [0]},
                    'sort_keys': ['name']}
        projected = self.policy.project(table)
        self.assertEqual(expected, projected)
        self.assertEqual(projected, self.policy.project(projected))

    def test_packed_table_projection_preserves_field_positions(self):
        fields = ['id', 'title', 'members', 'records', 'citations']
        value = {'fields': fields, 'rows': [
            ['source-one', 'Private Example (Example-200)', ['Example-100', 'Example-200'], 2, 3],
            ['Example-200', 'Private Example', ['Example-200'], 1, 1],
        ]}
        projected = self.policy.project(value)
        self.assertEqual(fields, projected['fields'])
        self.assertEqual([['source-one', 'Private family details withheld.', ['Example-100'], 2, 3]], projected['rows'])
        self.assertNotIn('Private Example', json.dumps(projected))
        self.assertNotIn('Example-200', json.dumps(projected))
        self.assertEqual(projected, self.policy.project(projected))
        with self.assertRaisesRegex(ValueError, 'Malformed packed table'):
            self.policy.project({'fields': fields, 'rows': [['source-one', 2, 3]]})

    def test_kit_screen_preserves_historical_names_and_profile_ids(self):
        pattern = tester_identifier_pattern({"brown", "123456", "AB12345"})
        self.assertIsNone(pattern.search("brown-123456"))
        self.assertIsNone(pattern.search("Historical brown family"))
        self.assertIsNotNone(pattern.search("kit=123456&source=project"))
        self.assertIsNotNone(pattern.search("kit AB12345"))

    def setUp(self):
        self.child = {"id": "Example-200", "name": "Private Example", "birth_date": "1950-01-01", "death_date": "0000-00-00"}
        self.capture = {"profile_id": "Example-100", "profile_fields": {"BirthDate": "1800-01-01", "Father": 456},
                        "biography_text": "A research placeholder. Private Example (Example-200).",
                        "biography_wikitext": "[[Example-200]]", "record_passages": ["Example-200"],
                        "relations": {"children": [self.child], "parents": [{"id": "Example-90", "name": "Historical Example"}]},
                        "sources": [{"citation": "Historic register", "urls": ["https://example.org/register"]},
                                    {"citation": "Example-200 private detail"}],
                        "external_urls": ["https://www.wikitree.com/wiki/Example-200"]}
        self.policy = from_sources({"profiles": {"Example-100": self.capture}}, {})

    def test_zero_death_aliases_and_explicit_withholding(self):
        self.assertTrue(likely_living({"BirthDate": "1950-00-00", "DeathDate": "0000-00-00"}, year=2026))
        self.assertTrue(_likely_living([self.child], []))
        self.assertFalse(likely_living({"birth_date": "1800-00-00"}, year=2026))
        self.assertFalse(likely_living({"BirthDate": "1950-00-00", "DeathDate": "2000-01-01"}, year=2026))
        self.assertFalse(likely_living({"BirthDate": "0000-00-00"}, year=2026))
        self.assertTrue(likely_living({"likely_living": True, "DeathDate": "2000-01-01"}))

    def test_redacted_birth_decades_still_screen_modern_profiles(self):
        self.assertTrue(likely_living({'BirthDateDecade': '1980s', 'DeathDateDecade': 'unknown'}, year=2026))
        self.assertTrue(likely_living({'profile_fields': {'BirthDate': '0000-00-00', 'BirthDateDecade': '1980s'}}, year=2026))
        self.assertTrue(likely_living({'birth_date_decade': '1900s'}, year=2026))
        self.assertFalse(likely_living({'BirthDateDecade': '1890s'}, year=2026))
        self.assertFalse(likely_living({'BirthDateDecade': '1980s', 'DeathDateDecade': '2000s'}, year=2026))
        self.assertFalse(likely_living({'BirthDate': '1800-01-01', 'BirthDateDecade': '1980s'}, year=2026))
        self.assertTrue(likely_living({'BirthDate': '1800-01-01'}, {'BirthDateDecade': '1980s'}, year=2026))

    def test_withheld_subject_routes_remove_names_without_identifiers(self):
        with tempfile.TemporaryDirectory() as directory:
            web = Path(directory)
            (web / 'people/private-1').mkdir(parents=True)
            (web / 'people/private-1.html').write_text('<h1>Private name without identifier</h1>')
            (web / 'people/private-1/index.html').write_text('<h1>Private name</h1>')
            (web / 'people/historical-1.html').write_text('Historical subject')
            policy = PublicPrivacy({'Private-1': {'BirthDateDecade': '1980s'}})
            people = [{'profile_ids': ['Private-1'], 'catalogue_id': 'private-1'}]
            self.assertEqual(2, remove_withheld_subject_routes(web, people, policy))
            self.assertEqual(0, remove_withheld_subject_routes(web, people, policy))
            self.assertEqual('Historical subject', (web / 'people/historical-1.html').read_text())

    def test_withheld_route_cleanup_does_not_follow_external_directories(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            web, outside = root / 'web', root / 'outside'
            web.mkdir(); outside.mkdir()
            (web / 'people').symlink_to(outside, target_is_directory=True)
            private = outside / 'private-1.html'
            private.write_text('Outside the public site')
            policy = PublicPrivacy({'Private-1': {'BirthDateDecade': '1980s'}})
            with self.assertRaisesRegex(ValueError, 'escapes public site'):
                remove_withheld_subject_routes(web, [{'profile_ids': ['Private-1'], 'catalogue_id': 'private-1'}], policy)
            self.assertTrue(private.is_file())

    def test_private_record_rows_are_removed_whole_in_all_index_schemas(self):
        rows = [{'id': 'hash', 'p': 'Example-200', 'person': 'Name without identifier'},
                {'record_id': 'hash2', 'catalogue_id': 'example-200', 'person': 'Name without identifier'},
                {'id': 'example-200', 'name': 'Name without identifier'},
                {'id': 'historic', 'name': 'Historical subject'}]
        self.assertEqual([rows[-1]], self.policy.project(rows))
        self.assertEqual([rows[-1]], self.policy.project(self.policy.project(rows)))

    def test_old_blanked_identifiers_cannot_leave_private_names_in_mirrors(self):
        safe = {'id': 'Example-100', 'catalogue_id': 'example-100', 'person': 'Private Example'}
        orphan = {'record_id': 'hash', 'catalogue_id': '', 'person': 'Private Example'}
        self.assertEqual([safe], self.policy.project([orphan, safe]))
        self.assertEqual({'slug': 'historical', 'name': 'Private Example'},
                         self.policy.project({'slug': 'historical', 'name': 'Private Example'}))
        with tempfile.TemporaryDirectory() as directory:
            web = Path(directory)
            (web / 'index.json').write_text(json.dumps([orphan, safe]))
            (web / 'detail.json').write_text(json.dumps(orphan))
            self.assertEqual({'orphan_mirrors': 1, 'orphan_subject_files': 1}, repair_orphaned_subjects(web, self.policy))
            self.assertEqual([safe], json.loads((web / 'index.json').read_text()))
            self.assertEqual({'orphan_mirrors': 0, 'orphan_subject_files': 0}, repair_orphaned_subjects(web, self.policy))

    def test_positional_search_caches_regenerate_without_private_cells(self):
        with tempfile.TemporaryDirectory() as directory:
            web = Path(directory)
            (web / 'assets/research').mkdir(parents=True)
            (web / 'assets/v3').mkdir()
            public = {'id': 'Example-100', 'name': 'Private Example', 'url': '/people/example-100.html',
                      'meta': '1800', 'search': 'historical', 'life': '1800', 'place': 'Scotland'}
            (web / 'assets/research/search-people.json').write_text(json.dumps([public, self.child]))
            for relative in ('search-people.json', 'people-quick.json'):
                (web / 'assets/v3' / relative).write_text(json.dumps([['Private Example', 'broken cells']]))
            self.assertEqual(2, refresh_positional_search_mirrors(web, self.policy)['positional_search_mirrors'])
            self.assertEqual([['Example-100', 'Private Example', '1800', 'Scotland', 'example-100']],
                             json.loads((web / 'assets/v3/people-quick.json').read_text()))
            self.assertEqual(0, refresh_positional_search_mirrors(web, self.policy)['positional_search_mirrors'])

    def test_registry_restores_checked_owner_and_rebuilds_packed_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            web = Path(directory)
            for folder in ('assets/research', 'assets/v3', 'data', 'people'):
                (web / folder).mkdir(parents=True)
            owner = {'id': 'example-100', 'name': 'Historical subject'}
            (web / 'data/catalogue-search-index.json').write_text(json.dumps([owner]))
            (web / 'people/example-100.json').write_text('{}')
            row = {'id': 'Example-100', 'selection_id': 'Example-100',
                   'slug': 'Private family details withheld.', 'name': owner['name'], 'url': ''}
            (web / 'assets/research/registry.json').write_text(json.dumps([row, {'id': '', 'withheld': True}]))
            (web / 'assets/v3/registry-packed.json').write_text(json.dumps({'fields': ['slug', 'name'], 'rows': []}))
            result = refresh_registry_mirror(web, self.policy)
            self.assertEqual((1, 1), (result['registry_withheld_rows'], result['registry_restored_aliases']))
            self.assertEqual([['example-100', owner['name']]],
                             json.loads((web / 'assets/v3/registry-packed.json').read_text())['rows'])
            self.assertEqual(0, refresh_registry_mirror(web, self.policy)['registry_files'])

    def test_capture_and_all_export_sinks_withhold_private_details(self):
        capture = self.policy.capture(self.capture)
        people = [{"wikitree_evidence": [capture]}]
        exports = [json.dumps(people), json.dumps(evidence_envelope({"cohort_profile_ids": ["Example-200"], "failures": ["Example-200"]}, people)),
                   _wikitree_evidence_html([capture], {})]
        for output in exports:
            self.assertNotIn("Example-200", output)
            self.assertNotIn("Private Example", output)
            self.assertIn("Historical Example", output)
            self.assertIn("Historic register", output)
        self.assertNotIn("Father", capture["profile_fields"])
        self.assertNotIn("biography_text", capture)
        self.assertTrue(capture["assessment_flags"]["_structural_placeholder"])
        self.assertEqual(capture, self.policy.capture(capture))

    def test_explicit_living_status_wins_missing_or_stale_dates(self):
        for flag in (1, True, "1", "true"):
            self.assertTrue(likely_living({"IsLiving": flag}))
            self.assertTrue(likely_living({"profile_fields": {
                "IsLiving": flag, "BirthDate": "1800-01-01", "DeathLocation": "Old claim"}}))
        for flag in (0, False, "0", "false", None):
            self.assertFalse(likely_living({"IsLiving": flag}))
        policy = from_sources({"profiles": {"Example-300": {
            "profile_id": "Example-300", "profile_fields": {"IsLiving": "1"}}}}, {})
        self.assertIn("example-300", policy.blocked)
        self.assertNotIn("Example-300", json.dumps(policy.project({
            "people": [{"id": "Example-300", "name": "Private Example"}]})))

    def test_casefolded_lookup_covers_nested_mirrors(self):
        value = {"imported": {"relations": [{"id": "EXAMPLE-200", "name": "Private Example", "url": "https://example.org"}]}}
        projected = self.policy.project(value)
        self.assertNotIn("Private Example", json.dumps(projected))
        self.assertEqual(projected, self.policy.project(projected))

    def test_restricted_capture_has_only_access_provenance(self):
        capture = self.policy.capture({**self.capture, "privacy": 35})
        self.assertNotIn("sources", capture)
        self.assertNotIn("profile_fields", capture)
        self.assertIn("Restricted capture withheld", capture["publication_scope"])

    def test_legacy_restricted_capture_without_narrative_or_relations(self):
        raw = {"profile_id": "Example-100", "privacy": 35, "profile_fields": {"LongName": "Restricted subject"}, "sources": [{"citation": "Restricted text"}]}
        projected = self.policy.project(raw)
        self.assertNotIn("Restricted subject", json.dumps(projected))
        self.assertNotIn("Restricted text", json.dumps(projected))

    def test_alias_relatives_are_removed_from_citations_and_urls(self):
        capture = {**self.capture, "relations": {"children": [{"Name": "Example-200", "LongName": "Private Example", "BirthDate": "2000-01-01"}]}}
        policy = from_sources({"profiles": {"Example-100": capture}}, {})
        projected = policy.project(capture)
        self.assertNotIn("Example-200", json.dumps(projected))
        self.assertNotIn("Private Example", json.dumps(projected))

    def test_restricted_capture_cannot_supply_historical_parent(self):
        evidence = {"profiles": {"Example-100": {"profile_id": "Example-100", "privacy": 35,
                    "profile_fields": {"Father": 42}, "relations": {"parents": [{"id": "Example-42", "name": "Restricted Parent", "death_date": "1900-01-01"}]}},
                    "Example-42": {"profile_fields": {"Id": 42}}}}
        people = _build_people([], {"Example-100": {"full_name": "Historic subject", "birth_date": "1800-01-01"}}, [], {}, evidence, {"Example-100"})
        self.assertNotIn("Restricted Parent", json.dumps(people))
        self.assertFalse(people[0]["likely_living"])


if __name__ == "__main__":
    unittest.main()


class AllExportsPolicyTest(unittest.TestCase):
    """A builder working on a subset still withholds a relative only another export marks living."""

    def test_all_exports_adds_the_merged_exports_to_the_given_profiles(self):
        from unittest import mock
        living = {"Harrow-9": {"birth_date": "1990-01-01", "death_date": ""}}
        historical = {"Harrow-1": {"birth_date": "1801-05-03", "death_date": "1870-01-01"}}
        import contextlib
        import importlib
        with contextlib.ExitStack() as stack:
            # public_privacy imports these as top-level or tools.* modules, depending on sys.path.
            for name in ("project_paths", "tools.project_paths"):
                try:
                    importlib.import_module(name)
                except ModuleNotFoundError:
                    continue
                stack.enter_context(mock.patch(f"{name}.merged_map_profiles", return_value=(living, [])))
            for name in ("repair_public_dna", "tools.repair_public_dna"):
                try:
                    importlib.import_module(name)
                except ModuleNotFoundError:
                    continue
                stack.enter_context(mock.patch(f"{name}.private_tester_ids", return_value=frozenset()))
            subset = from_sources({}, historical)
            full = from_sources({}, historical, all_exports=True)
        self.assertNotIn("harrow-9", subset.blocked)
        self.assertIn("harrow-9", full.blocked)
        self.assertTrue(full.contains_private_id("spouse Harrow-9"))
        self.assertNotIn("harrow-1", full.blocked)
