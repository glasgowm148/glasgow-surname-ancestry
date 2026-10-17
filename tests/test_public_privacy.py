import json
import unittest

from tools.public_privacy import PublicPrivacy, likely_living, evidence_envelope, from_sources, tester_identifier_pattern
from tools.build_research_catalog import _wikitree_evidence_html, _likely_living, _build_people


class PublicPrivacyTests(unittest.TestCase):
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
