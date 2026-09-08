#!/usr/bin/env python3
"""Offline checks for the generated crawlable research catalogue."""

import csv
from collections import Counter
import json
from html import unescape
from pathlib import Path
import re
import unittest

from tools.catalogue_machine_data import _profile_assessment_flags, resolver_candidates
from tools.audit_missing_wikitree_profiles import (
    candidate_summary, discover_drafts, new_draft_match, select_candidates,
)
from tools.materialize_findmypast_glasgow_catalogue import (
    person_record, render_draft, reviewed_person,
)
from tools.build_research_catalog import (
    _canonical_marriage_surname,
    _extract_profile_draft,
    _estimated_birth_location,
    _is_external_public_url,
    _is_complete_profile_draft,
    _potential_parentage,
    _profile_creation_vital,
    _profile_update_significance,
    _supporting_source_link,
    _profile_work_status,
    _relative_given_name,
    _similar_people,
    _source_for_record,
    _source_identity_keys,
    _load_profile_updates,
    _marriage_surname_values,
    _merge_profile_summary_with_captured,
    _normalise_ref_opening_tags,
    _relation_birth_surnames,
)


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "www"


class ResearchCatalogueTest(unittest.TestCase):
    def test_place_timeline_source_link_is_plain_and_escaped(self):
        self.assertEqual(_supporting_source_link({}), "")
        self.assertEqual(
            _supporting_source_link({
                "supporting_source_url": 'https://example.org/record?a=1&b="two"'
            }),
            '<p><a href="https://example.org/record?a=1&amp;b=&quot;two&quot;">'
            'Supporting source</a></p>',
        )

    def test_every_active_creation_handoff_is_registered_and_copy_ready(self):
        discovered = discover_drafts()
        active = {
            catalogue_id: relative
            for catalogue_id, relative in discovered.items()
            if relative.startswith("surname-research/new-people/")
        }
        registered = set(active.values())
        maintained = {
            str(path.relative_to(ROOT))
            for path in (ROOT / "surname-research" / "new-people").glob("*.md")
        }
        self.assertEqual(
            maintained,
            registered,
            "Every maintained creation draft must have a catalogue identity mapping",
        )
        search_index = {
            person["id"]: person
            for person in json.loads(
                (WEB / "data" / "catalogue-search-index.json").read_text(encoding="utf-8")
            )
        }
        for catalogue_id, relative in sorted(active.items()):
            draft = _extract_profile_draft({"draft_path": relative})
            self.assertTrue(draft, relative)
            self.assertTrue(_is_complete_profile_draft(draft), relative)
            self.assertNotRegex(draft, r"<ref\b[^>]*\n[^>]*>", relative)
            self.assertNotRegex(draft, r"\[[^\]\n]+\]\(https?://", relative)
            self.assertNotRegex(draft, r"\*\*[^*\n]+\*\*", relative)
            self.assertNotRegex(draft, r"`[^`\n]+`", relative)
            self.assertNotRegex(
                draft,
                r"(?mi)^#{1,6}\s+(?:HOLD|Minimum creation fields|Paste-ready biography|Duplicate(?: and identity)? audit|Resolution targets?|After creation)\b",
                relative,
            )
            openings = list(re.finditer(r"<ref\b([^>]*)>", draft, re.I))
            definitions = set()
            usages = set()
            for opening in openings:
                name = re.search(
                    r"\bname\s*=\s*([\"'])([^\"']+)\1", opening.group(1), re.I
                )
                if name:
                    (usages if opening.group(1).rstrip().endswith("/") else definitions).add(
                        name.group(2)
                    )
            self.assertEqual(
                sum(not opening.group(1).rstrip().endswith("/") for opening in openings),
                len(re.findall(r"</ref\s*>", draft, re.I)),
                relative,
            )
            self.assertLessEqual(usages, definitions, relative)
            handoff = (ROOT / relative).read_text(encoding="utf-8")
            birth_location = re.search(
                r"^- \*\*Birth(?: ?place| location):\*\* (.+)$", handoff, re.M | re.I
            )
            if birth_location and not re.match(
                r"(?:unknown|place not stated|not determined)\b",
                birth_location.group(1),
                re.I,
            ):
                self.assertTrue(search_index[catalogue_id]["birth_location"], relative)

    @staticmethod
    def _findmypast_draft(
        transcript_fields, *, event_type="baptism", event_date="2 Jan 1700", match=None,
        creation_status="READY", notes="", place="Irvine", country="Scotland"
    ):
        person = {
            "group_id": "fmp-test-person",
            "supplement_id": "fmp-test-person",
            "name": "Test Glasgow",
            "event_type": event_type,
            "event_date": event_date,
            "event_year": 1700,
            "event_year_start": 1700,
            "event_year_end": 1700,
            "place": place,
            "country": country,
            "record_ids": ["test-record"],
            "record_sets": ["Test records"],
            "source_urls": ["https://www.findmypast.example/test-record"],
            "duplicate_group_reason": "one transcript describes one person",
            "records": [{
                "source_url": "https://www.findmypast.example/test-record",
                "captured_at": "2026-09-07",
                "transcript_fields": transcript_fields,
            }],
        }
        decision = {
            "outcome": "new_person",
            "creation_status": creation_status,
            "supplement_id": "fmp-test-person",
            "notes": notes,
        }
        return render_draft(person, decision, match or {"candidates": []})

    def test_findmypast_estimated_date_covers_qualified_key_vitals(self):
        cases = (
            ({"Baptism date": "2 Jan 1700"}, "baptism", "2 Jan 1700"),
            ({"Spouse first name": "Jean"}, "marriage", "2 Jan 1700"),
            ({"Birth date": "About 1670"}, "birth", "About 1670"),
            ({"Birth date": "After 1670"}, "birth", "After 1670"),
            ({"Birth date": "Approximately 1670"}, "birth", "Approximately 1670"),
            ({"Birth date": "1 Jan 1670", "Burial date": "2 Jan 1700"}, "burial", "2 Jan 1700"),
        )
        for fields, event_type, event_date in cases:
            with self.subTest(fields=fields, event_type=event_type):
                draft = self._findmypast_draft(
                    fields, event_type=event_type, event_date=event_date
                )
                self.assertEqual(draft.count("{{Estimated Date}}"), 1)

        exact = self._findmypast_draft(
            {"Birth date": "1 Jan 1700"}, event_type="birth", event_date="1 Jan 1700"
        )
        self.assertNotIn("{{Estimated Date}}", exact)

    def test_findmypast_candidate_name_match_does_not_link_relative(self):
        comparison = {
            "role": "father",
            "profile_id": "Glasgow-123",
            "exact_match": True,
        }
        match = {"candidates": [{
            "profile_id": "Glasgow-999",
            "profile": {"LongName": "Possible Test Glasgow"},
            "evidence": {"relatives": {"comparisons": [comparison]}},
        }]}
        fields = {"Father first name": "John", "Father last name": "Glasgow"}

        draft = self._findmypast_draft(fields, match=match)
        self.assertNotIn("[[Glasgow-123|John Glasgow]]", draft)
        self.assertNotIn("Glasgow-123", draft)
        self.assertIn("father John Glasgow", draft)
        self.assertIn("[[Glasgow-999|Possible Test Glasgow]]", draft)

        comparison["identity_proven"] = True
        proved = self._findmypast_draft(fields, match=match)
        self.assertIn("[[Glasgow-123|John Glasgow]]", proved)

    def test_findmypast_migration_destination_is_not_a_birthplace(self):
        draft = self._findmypast_draft(
            {"Destination": "Antegoa"},
            event_type="residence/migration",
            event_date="10 Mar 1707",
        )
        self.assertIn("**Birth location:** unknown", draft)
        self.assertIn("a migration destination or source grouping is not a birthplace", draft)
        self.assertIn("destination states: “Antegoa”", draft)

        residence = self._findmypast_draft(
            {"Event type": "Residence", "Event place": "Ballykeel, County Antrim"},
            event_type="residence/migration", event_date="1738",
            place="Ballykeel, County Antrim", country="Ireland",
        )
        self.assertIn("**Birth location:** Ballykeel, County Antrim, Ireland", residence)

        grouping = self._findmypast_draft(
            {"Event type": "Residence", "Event place": "Scots-Irish",
             "Title": "Scots-Irish Links, 1575-1725, Pts 1 & 2"},
            event_type="residence/migration", event_date="1707",
            place="Scots-Irish", country="United States",
        )
        self.assertIn("**Birth location:** unknown", grouping)

        reviewed_grouping = self._findmypast_draft(
            {"Event type": "Residence", "Event place": "Scots-Irish",
             "Title": "Scots-Irish Links, 1575-1725, Pts 1 & 2"},
            event_type="residence/migration", event_date="1707",
            place="place unknown", country="Location unknown",
        )
        self.assertIn("**Birth location:** unknown", reviewed_grouping)
        self.assertNotIn("**Birth location:** place unknown", reviewed_grouping)
        self.assertIn("at an unspecified place", reviewed_grouping)
        self.assertNotIn("at place unknown, Location unknown", reviewed_grouping)

        row_person = {
            "group_id": "fmp-source-group", "supplement_id": "fmp-source-group",
            "name": "Nathaniel Glasgow", "event_type": "residence/migration",
            "event_year": 1707, "event_year_start": 1707, "event_year_end": 1707,
            "place": "place unknown", "country": "Location unknown",
            "record_ids": ["test-record"], "record_sets": ["Test records"],
            "source_urls": ["https://www.findmypast.example/test-record"],
            "records": [{"transcript_fields": {
                "Event type": "Residence", "Event place": "Scots-Irish",
                "Title": "Scots-Irish Links, 1575-1725, Pts 1 & 2",
            }}],
        }
        row = person_record(
            row_person,
            {"outcome": "new_person", "creation_status": "HOLD",
             "supplement_id": "fmp-source-group", "profile_id": ""},
            [],
        )
        self.assertNotIn("explicit event type Residence", row["location_basis"])

        row_person["place"] = "Ballykeel, County Antrim"
        row_person["country"] = "Ireland"
        row_person["records"][0]["transcript_fields"]["Event place"] = "Ballykeel, County Antrim"
        row_person["records"][0]["transcript_fields"]["Title"] = "New World Immigrants, volume 2"
        residence_row = person_record(
            row_person,
            {"outcome": "new_person", "creation_status": "READY",
             "supplement_id": "fmp-residence", "profile_id": ""},
            [],
        )
        self.assertIn("explicit event type Residence", residence_row["location_basis"])
        self.assertEqual(
            residence_row["birth_location"],
            "Ballykeel, County Antrim, Ireland",
        )
        self.assertIn("uncertain", residence_row["birth_status"])

        row_person["birth_location"] = "Lindsayland, Biggar, Lanarkshire, Scotland"
        reviewed_location_row = person_record(
            row_person,
            {"outcome": "new_person", "creation_status": "READY",
             "supplement_id": "fmp-reviewed-location", "profile_id": ""},
            [],
        )
        self.assertEqual(
            reviewed_location_row["birth_location"],
            "Lindsayland, Biggar, Lanarkshire, Scotland",
        )
        row_person.pop("birth_location")

        row_person["records"][0]["transcript_fields"]["Destination"] = "Antegoa"
        migration_row = person_record(
            row_person,
            {"outcome": "new_person", "creation_status": "READY",
             "supplement_id": "fmp-migration", "profile_id": ""},
            [],
        )
        self.assertEqual(migration_row.get("birth_location", ""), "")

        self.assertEqual(
            _estimated_birth_location([{
                "filter_year": 1707, "year": "1707",
                "subcluster": "residence/migration",
                "association": "Residence/Migration 1707",
                "record_location": "British West Indies",
            }]),
            ("", ""),
        )
        self.assertEqual(
            _estimated_birth_location([{
                "filter_year": 1738, "year": "1738",
                "subcluster": "residence/migration",
                "association": "Residence/Migration 1738",
                "location_basis": "Findmypast transcript; explicit event type Residence; no narrower location inferred.",
                "record_location": "Ballykeel, County Antrim, Ireland",
            }]),
            (
                "Ballykeel, County Antrim, Ireland (estimated)",
                "Estimated from the earliest mapped residence record (1738).",
            ),
        )
        self.assertEqual(
            _estimated_birth_location([{
                "filter_year": 1712, "year": "1712", "subcluster": "baptism",
                "association": "Baptism 1712", "record_location": "Walston, Scotland",
            }]),
            (
                "Walston, Scotland (estimated)",
                "Estimated from the mapped birth or baptism record (1712).",
            ),
        )
        self.assertEqual(
            _estimated_birth_location([{
                "filter_year": 1887, "year": "1887", "association": "b. 1887",
                "profile_id": "Glasgow-872",
                "record_location": "Location not supplied — profile holding point",
            }]),
            ("", ""),
        )
        self.assertEqual(
            _estimated_birth_location([{
                "filter_year": 1700, "year": "1700", "subcluster": "marriage",
                "association": "Marriage 1700", "record_location": "Irvine, Scotland",
            }]),
            (
                "Irvine, Scotland (estimated)",
                "Estimated from the earliest mapped non-migration life event (1700).",
            ),
        )
        self.assertEqual(
            _estimated_birth_location([{
                "filter_year": 1700, "year": "1700", "subcluster": "marriage",
                "association": "Marriage 1700", "profile_id": "Glasgow-9999",
                "record_location": "Irvine, Scotland",
            }]),
            ("", ""),
        )

    def test_reviewed_findmypast_hold_does_not_claim_no_candidate(self):
        draft = self._findmypast_draft(
            {}, creation_status="HOLD",
            notes="The live audit retained [[Glasgow-1143|Robert Glasgow]] as a possible match.",
        )
        self.assertIn("Reviewed HOLD reason", draft)
        self.assertIn("[[Glasgow-1143|Robert Glasgow]]", draft)
        self.assertNotIn("No compatible candidate was retained", draft)

    def test_court_venue_is_not_inferred_as_birthplace(self):
        self.assertEqual(
            _estimated_birth_location([{
                "filter_year": 1893, "year": "1893",
                "subcluster": "Cape court candidates",
                "association": "Court defendant",
                "record_location": "Cape Supreme Court, Cape Town",
                "record_precision": "Court-jurisdiction representative point",
                "location_basis": "Alexander's residence is unproved.",
                "source_type": "court file index",
            }]),
            ("", ""),
        )
        self.assertEqual(
            _estimated_birth_location([{
                "filter_year": 1692, "year": "1692",
                "subcluster": "court record",
                "association": "Court Record 02/03/1692",
                "record_location": "Dublin, Ireland",
                "source_title": "Court of Chancery Bill Books 1692-1696",
            }]),
            ("", ""),
        )

    def test_reviewed_catalogue_interpretation_preserves_raw_person(self):
        raw = {
            "group_id": "fmp-test", "country": "United States",
            "place": "Ballykeel, Co Ant", "event_date": "",
        }
        decision = {
            "catalogue_country": "Ireland",
            "catalogue_place": "Ballykeel, County Antrim",
        }
        interpreted = reviewed_person(raw, decision)
        self.assertEqual(interpreted["country"], "Ireland")
        self.assertEqual(interpreted["place"], "Ballykeel, County Antrim")
        self.assertEqual(raw["country"], "United States")

    def test_marriage_surname_variants_use_birth_surname(self):
        linked = {"cunynghame-1": {"last_names_at_birth": ["Cunynghame"]}}
        self.assertEqual(_canonical_marriage_surname("Cunninghame"), "Cunningham")
        self.assertEqual(
            _relation_birth_surnames({"id": "Cunynghame-1", "name": "Jean Glasgow"}, linked),
            {"Cunningham"},
        )
        self.assertEqual(
            _relation_birth_surnames({"id": "Cunningham-2", "name": "Henry Cunningham Glasgow"}, {}),
            {"Cunningham"},
        )
        people = json.loads((WEB / "data" / "people.json").read_text(encoding="utf-8"))["people"]
        counts = {surname: count for surname, count, _ in _marriage_surname_values(people)}
        self.assertEqual(counts["Cunningham"], 10)

    def test_ref_opening_tags_are_kept_on_one_line(self):
        text = 'Claim.<ref\n name="SourceA">Citation.</ref> Reuse.<ref\n name="SourceA" />'
        normalised = _normalise_ref_opening_tags(text)
        self.assertIn('<ref name="SourceA">Citation.</ref>', normalised)
        self.assertIn('<ref name="SourceA" />', normalised)
        self.assertNotRegex(normalised, r"<ref\b[^>]*\n[^>]*>")

    def test_preservation_merge_restores_displaced_named_ref_definition(self):
        captured = """== Biography ==

Old introduction.<ref name="Census1851">1851 census citation.</ref>

=== Census ===

The household appeared in 1851.<ref name="Census1851" />

== Research Notes ==

Captured notes.

== Sources ==

<references />"""
        summary = """== Biography ==

Corrected introduction.

== Research Notes ==

Corrected assessment.

== Sources ==

<references />"""

        merged = _merge_profile_summary_with_captured(summary, captured, "Glasgow-1", {})

        self.assertIn(
            'The household appeared in 1851.<ref name="Census1851">'
            "1851 census citation.</ref>",
            merged,
        )
        self.assertNotIn('<ref name="Census1851" />', merged)

    def test_reviewed_full_replacements_bypass_captured_detail_merge(self):
        evidence = json.loads(
            (ROOT / "data" / "wikitree" / "profile-evidence.json").read_text(encoding="utf-8")
        )
        updates = _load_profile_updates(evidence)

        for profile_id in ("Glasgow-1030", "Glasgow-3181"):
            with self.subTest(profile_id=profile_id):
                update = updates[profile_id]
                self.assertFalse(update.get("preserve_captured_detail"))
                self.assertIn(
                    "<!-- REVIEWED FULL REPLACEMENT:", update["proposed_wikitext"]
                )
                self.assertRegex(update["proposed_wikitext"], r"(?m)^=== [^=].*?===$")

    def test_all_profile_updates_have_balanced_and_resolved_ref_tags(self):
        evidence = json.loads(
            (ROOT / "data" / "wikitree" / "profile-evidence.json").read_text(encoding="utf-8")
        )
        updates = _load_profile_updates(evidence)
        opening_pattern = re.compile(r"<ref\b(?P<attrs>[^>]*)>", re.I)
        name_pattern = re.compile(
            r"\bname\s*=\s*(?P<quote>[\"'])(?P<name>[^\"']+)(?P=quote)", re.I
        )
        for profile_id, update in updates.items():
            definitions = set()
            usages = set()
            open_definition_count = 0
            for opening in opening_pattern.finditer(update["proposed_wikitext"]):
                self_closing = opening.group("attrs").rstrip().endswith("/")
                if not self_closing:
                    open_definition_count += 1
                name_match = name_pattern.search(opening.group("attrs"))
                if name_match:
                    (usages if self_closing else definitions).add(name_match.group("name"))
            closing_count = len(
                re.findall(r"</ref\s*>", update["proposed_wikitext"], flags=re.I)
            )
            self.assertEqual(open_definition_count, closing_count, profile_id)
            self.assertLessEqual(usages, definitions, profile_id)
            self.assertNotRegex(
                update["proposed_wikitext"],
                r"<ref\b[^>]*\n[^>]*>",
                profile_id,
            )

    def test_full_profile_rewrites_do_not_discard_captured_narrative(self):
        evidence = json.loads(
            (ROOT / "data" / "wikitree" / "profile-evidence.json").read_text(encoding="utf-8")
        )
        updates = _load_profile_updates(evidence)
        for profile_id, update in updates.items():
            if not update.get("draft_path"):
                continue
            captured = update["remote_wikitext"]
            proposed = update["proposed_wikitext"]
            self.assertGreaterEqual(
                len(proposed), int(len(captured) * 0.75),
                f"{profile_id} rewrite is an unsafe narrative compression",
            )
            if len(proposed) < len(captured):
                self.assertTrue(
                    update.get("reviewed_narrative_reduction"),
                    f"{profile_id} rewrite is shorter without an audited reason",
                )
            captured_headings = re.findall(r"(?m)^={2,4} .* ={2,4}$", captured)
            proposed_headings = re.findall(r"(?m)^={2,4} .* ={2,4}$", proposed)
            self.assertGreaterEqual(
                len(proposed_headings), max(1, len(captured_headings) // 2),
                f"{profile_id} rewrite drops too much profile structure",
            )
            if update.get("preserve_captured_detail"):
                normalise_heading = lambda value: re.sub(r"\s+", " ", value.replace("=", " ")).strip().casefold()
                self.assertLessEqual(
                    {normalise_heading(value) for value in captured_headings},
                    {normalise_heading(value) for value in proposed_headings},
                    f"{profile_id} rewrite did not retain every detailed heading",
                )
            self.assertNotIn("{{One Name Study", proposed, profile_id)
            self.assertNotRegex(
                proposed,
                r"(?i)(?:TODO|example\.com|glasgow\.phenotype\.dev|(?:^|\s)(?:research|sources)/)",
                profile_id,
            )
            self.assertNotRegex(proposed, r"\[[^\]\n]+\]\(https?://", profile_id)
            self.assertNotRegex(proposed, r"\*\*[^*\n]+\*\*", profile_id)
            self.assertNotRegex(proposed, r"`[^`\n]+`", profile_id)
            if profile_id.startswith(("Glasgow-", "Glasco-", "Glasgo-", "Glascow-")):
                self.assertIn("[[Category:Glasgow Name Study]]", proposed, profile_id)

    def test_profile_source_identity_normalises_citation_templates(self):
        old = _source_identity_keys(
            "{{FindAGrave|33531767}}",
            ["https://www.familysearch.org/ark:/61903/1:1:XHRC-7BG"],
        )
        revised = _source_identity_keys(
            "[https://www.findagrave.com/memorial/33531767/archibald-glasgow memorial] "
            "[https://familysearch.org/ark:/61903/1:1:XHRC-7BG census]"
        )
        self.assertLessEqual(old.keys(), revised.keys())

    def test_bounded_birth_and_local_child_window_keep_william_as_parent_lead(self):
        dossier = json.loads((WEB / "people" / "glasgow-3526.json").read_text(encoding="utf-8"))
        fathers = {
            candidate["id"]: candidate
            for candidate in dossier["potential_parentage"]["candidates"]
            if candidate["role"] == "possible father"
        }
        self.assertIn("Glasgow-1026", fathers)
        william = fathers["Glasgow-1026"]
        self.assertEqual(william["age_gap_label"], "28 years")
        self.assertIn("local same-spouse child window", william["factors"])
        self.assertTrue(any("Glasgow-1025" in conflict for conflict in william["conflicts"]))

    def test_catalogue_is_complete_and_crawlable(self):
        catalogue_html = (WEB / "catalogue.html").read_text(encoding="utf-8")
        self.assertIn('<a class="brand" href="index.html">Glasgow Surname Project</a>', catalogue_html)
        payload = json.loads((WEB / "data" / "people.json").read_text(encoding="utf-8"))
        people = payload["people"]
        self.assertGreaterEqual(len(people), 4_000)
        self.assertGreater(payload["withheld_likely_living_count"], 0)
        self.assertTrue(payload["source_exports"])
        self.assertEqual(len(people), len({person["catalogue_id"] for person in people}))
        self.assertTrue(all((WEB / "people" / f"{person['catalogue_id']}.html").exists() for person in people))

        james = next(person for person in people if "Glasgow-3903" in person["profile_ids"])
        html = (WEB / "people" / f"{james['catalogue_id']}.html").read_text(encoding="utf-8")
        self.assertIn('<a class="brand" href="../catalogue.html">Glasgow Surname Project</a>', html)
        for text in ("James Glasgow", "Adam Glasgow", "Rose (Unknown) Glasgow", "Inishrush", "Chronological mapped occurrences"):
            self.assertIn(text, html)
        adam = next(person for person in people if "Glasgow-3902" in person["profile_ids"])
        self.assertTrue(any(child["id"] == "Glasgow-3903" for child in adam["children"]))
        adam_html = (WEB / "people" / f"{adam['catalogue_id']}.html").read_text(encoding="utf-8")
        self.assertIn("James Glasgow", adam_html)
        self.assertIn("Glasgow-3903", adam_html)
        self.assertIn("WikiTree profile information", adam_html)
        self.assertIn("Source or provenance", adam_html)
        self.assertIn("Dataset: ONT_Glas", adam_html)

        archibald = next(person for person in people if "Glasgow-1101" in person["profile_ids"])
        self.assertGreaterEqual(len(archibald["wikitree_evidence"]), 1)
        self.assertGreaterEqual(len(archibald["wikitree_evidence"][0]["sources"]), 10)
        archibald_html = (WEB / "people" / f"{archibald['catalogue_id']}.html").read_text(encoding="utf-8")
        self.assertIn("WikiTree biography, citations and relationship snapshot", archibald_html)
        self.assertIn("Full captured biography text", archibald_html)
        self.assertIn("Rathmelton", archibald_html)

        elizabeth = next(person for person in people if "Glasgow-3961" in person["profile_ids"])
        self.assertIn("Glenarm Town", elizabeth["recorded_in"])
        self.assertGreaterEqual(len(elizabeth["records"]), 2)
        index = json.loads((WEB / "data" / "catalogue-search-index.json").read_text(encoding="utf-8"))
        index_by_key = {person["map_key"]: person for person in index}
        self.assertEqual(len(people), len(index_by_key))
        for person in people:
            shared = index_by_key[person["map_key"]]
            for field in ("name", "profile_ids", "birth", "birth_location", "death", "death_location", "cluster", "suffixes"):
                self.assertEqual(person[field], shared[field])
        self.assertFalse(any(
            person["birth_location_note"] and re.search(
                r"not supplied|not stated|unknown|unspecified|holding point|source grouping",
                person["birth_location"], re.I,
            )
            for person in index
        ))
        self.assertTrue(any(person["has_suffix"] and "M.D." in person["suffixes"] for person in index))
        ignored_suffixes = {"jr", "sr", "i", "ii", "iii"}
        self.assertFalse(any(
            suffix.casefold().strip().rstrip(".") in ignored_suffixes
            for person in index for suffix in person["suffixes"]
        ))
        public_filter_fields = {
            "record_types", "source_qualities", "has_original_record", "has_open_questions",
            "missing_profile", "profile_work_status", "profile_work_candidate_count",
            "missing_father", "missing_mother", "uncertain_identity", "record_count", "location_groups", "family_root", "family_roots",
        }
        self.assertTrue(all(public_filter_fields <= person.keys() for person in index))
        self.assertTrue(all(
            {"id", "country", "area", "locality"} <= group.keys()
            for person in index for group in person["location_groups"]
        ))
        alexander = next(person for person in index if "Glasgow-951" in person["profile_ids"])
        self.assertTrue(any(
            group["country"] == "Ireland" and group["area"] == "County Antrim" and group["locality"] == "Lisnagaver townland"
            for group in alexander["location_groups"]
        ))
        self.assertTrue(alexander["family_root"])
        self.assertTrue(all(
            {"marriage_date", "marriage_location"} <= spouse.keys()
            for spouse in alexander["spouses"]
        ))
        self.assertTrue({"id", "name", "birth", "birth_location", "distance", "catalogue_id"} <= alexander["family_root"].keys())
        branch_counts = Counter(person["family_root"]["id"] for person in index if person["family_root"])
        self.assertTrue(branch_counts)
        self.assertTrue(all(count >= 2 for count in branch_counts.values()))
        self.assertTrue(all(
            any(parent.get("id") and not parent.get("outside_export") for parent in person["father"])
            for person in index if person["family_root"]
        ))
        james_patrick = next(person for person in index if "Glasgow-635" in person["profile_ids"])
        self.assertFalse(james_patrick["father"])
        self.assertIsNone(james_patrick["family_root"])
        self.assertTrue(any(person["family_root"] is None for person in index))
        catalogue_html = (WEB / "catalogue.html").read_text(encoding="utf-8")
        self.assertIn("catalogue-has-suffix", catalogue_html)
        self.assertIn("catalogue-search-panel", catalogue_html)
        self.assertNotIn("Explore the detail", catalogue_html)
        self.assertIn(f'Search {len(people):,} historical people connected with the Glasgow surname.', catalogue_html)
        self.assertNotIn("across documentary records and WikiTree", catalogue_html)
        statistics_start = catalogue_html.index('<section id="statistics"')
        search_start = catalogue_html.index('<section class="catalogue-search-panel"')
        statistics_html = catalogue_html[statistics_start:search_start]
        self.assertIn('<p class="catalogue-refresh">Updated ', statistics_html)
        self.assertIn('catalogue.html?marriageSurname=Smith#catalogue-results', statistics_html)
        self.assertRegex(
            statistics_html,
            r'marriageSurname=Cunningham#catalogue-results">Cunningham</a>.*?<strong>9</strong>',
        )
        self.assertNotIn("mapped record associations</p>", catalogue_html)
        self.assertIn('id="catalogue-date-type"', catalogue_html)
        self.assertIn('id="catalogue-location-type"', catalogue_html)
        self.assertIn('id="catalogue-glasgow-at-birth"', catalogue_html)
        self.assertIn("Glasgow at birth", catalogue_html)
        self.assertIn('<legend>Dates</legend>', catalogue_html)
        self.assertIn('<legend>Places</legend>', catalogue_html)
        self.assertNotIn('<legend>Dates &amp; places</legend>', catalogue_html)
        self.assertGreaterEqual(catalogue_html.count('<option value="">Any record</option>'), 2)
        self.assertNotIn('id="catalogue-missing-parents"', catalogue_html)
        primary_filters_end = catalogue_html.index('<button id="catalogue-search-clear"')
        self.assertLess(catalogue_html.index('id="catalogue-males-only"'), catalogue_html.index('id="catalogue-missing-father"'))
        self.assertLess(catalogue_html.index('id="catalogue-missing-father"'), catalogue_html.index('id="catalogue-missing-mother"'))
        self.assertLess(catalogue_html.index('id="catalogue-missing-mother"'), primary_filters_end)
        self.assertNotIn('catalogue-more-filters', catalogue_html)
        self.assertNotIn('>More filters<', catalogue_html)
        for removed_filter in (
            'catalogue-has-profile', 'catalogue-open-questions', 'catalogue-uncertain-identity',
            'catalogue-original-evidence', 'catalogue-missing-vital-location', 'catalogue-estimated-location',
        ):
            self.assertNotIn(f'id="{removed_filter}"', catalogue_html)
        search_footer = catalogue_html[catalogue_html.index('<div class="catalogue-search-footer">'):catalogue_html.index('</form></section>')]
        for moved_filter in (
            'catalogue-males-only', 'catalogue-missing-father', 'catalogue-missing-mother',
            'catalogue-has-descendants', 'catalogue-women-married-glasgow',
            'catalogue-missing-profile', 'catalogue-needs-wikitree-update', 'catalogue-has-suffix',
        ):
            self.assertIn(f'id="{moved_filter}"', search_footer)
        for heading in ("Names &amp; family", "Research &amp; evidence", "Dates", "Places"):
            self.assertIn(heading, catalogue_html)
        self.assertNotIn('src="/data/people-index.js"', catalogue_html)
        self.assertIn('href="people/catalogue.css?', catalogue_html)
        self.assertIn('src="people/search.js?', catalogue_html)
        self.assertIn('src="people/external-links.js?', catalogue_html)
        self.assertIn('location.protocol==="file:"', catalogue_html)
        for text in (
            "Explore the research", "How to read the evidence", "Browse the complete catalogue",
            "catalogue-region", "catalogue-record-type", "catalogue-source-quality",
            "catalogue-missing-profile", "catalogue-exact-name", "Exact name spelling",
            "About this catalogue, privacy and data downloads",
            "Catalogue statistics", "Open detailed statistics pane", "Most frequent given names",
            "Surnames joined by marriage to Glasgow", "Largest exported family branches",
        ):
            self.assertIn(text, catalogue_html)
        self.assertLess(
            catalogue_html.index("Profiles with strong candidate matches"),
            catalogue_html.index("Explore the research"),
        )
        search_js = (WEB / "people" / "search.js").read_text(encoding="utf-8")
        self.assertIn("catalogue-search-index.json", search_js)
        self.assertIn("Loading searchable index", search_js)
        for key, heading in (("spouse", "Spouse(s)"), ("father", "Father"), ("mother", "Mother")):
            self.assertIn(f"sortHeader('{key}','{heading}')", search_js)
        self.assertNotIn("<th>Suffix</th>", search_js)
        self.assertIn("let sortMode='relevance'", search_js)
        self.assertIn("function relevance(person,filters)", search_js)
        self.assertIn("const normaliseLiteral=", search_js)
        self.assertIn("exact:'exact'", search_js)
        self.assertIn("person._identityExactTokens", search_js)
        self.assertIn("person._birthLastNames", search_js)
        self.assertIn("params.get('birthSurname')", search_js)
        self.assertIn("params.get('marriageSurname')", search_js)
        self.assertIn("person._marriageSurnames.includes(filters.marriageSurname)", search_js)
        self.assertIn("glasgowBirth:'glasgowBirth'", search_js)
        self.assertIn("controls.glasgowBirth.checked&&!person._birthLastNames.includes('glasgow')", search_js)
        self.assertIn("if(filters.exact)", search_js)
        self.assertIn("history.replaceState", search_js)
        self.assertIn("catalogue-result-cards", search_js)
        self.assertIn("catalogue-wikitree-id", search_js)
        self.assertIn("catalogue-group-locations", search_js)
        self.assertIn("catalogue-group-families", search_js)
        self.assertIn("catalogue-group-tree", search_js)
        self.assertIn("function locationBuckets(source)", search_js)
        self.assertIn("groupLocation", search_js)
        self.assertIn("groupFamily", search_js)
        self.assertIn("groupTree", search_js)
        self.assertIn("function groupedFamilyResults(source)", search_js)
        self.assertIn("function oneTreeResults(matches,allPeople,filters,pathIds=null)", search_js)
        self.assertIn("function compareFamilyGroups(a,b)", search_js)
        self.assertIn("const shown=groupedMode?found:found.slice(0,500)", search_js)
        self.assertNotIn("const shown=found.slice(0,500)", search_js)
        self.assertIn("catalogue-group-sort", search_js)
        self.assertIn("locationSort", search_js)
        self.assertIn("familySort", search_js)
        self.assertIn("collapsedFamilies", search_js)
        self.assertIn("data-family-toggle", search_js)
        self.assertIn("data-family-member", search_js)
        self.assertIn("Branch size: most people", search_js)
        self.assertIn("Earliest ancestor: oldest first", search_js)
        self.assertIn("catalogue-family-group", search_js)
        self.assertIn("catalogue-family-root-vitals", search_js)
        self.assertIn('target="_blank" rel="noopener noreferrer">${esc(root.id)}</a>', search_js)
        self.assertIn("catalogue-family-unconnected", search_js)
        self.assertIn("catalogue-one-tree", search_js)
        self.assertIn("data-tree-toggle", search_js)
        self.assertIn("data-folded-spouses", search_js)
        self.assertIn("catalogue-tree-folded-spouse", search_js)
        for marker in (
            "catalogue-tree-ancestors", "catalogue-tree-descendants", "catalogue-tree-evidence",
            "catalogue-tree-expand-depth", "catalogue-tree-compact", "catalogue-tree-breadcrumb",
            "catalogue-tree-direct-match", "catalogue-tree-union", "data-tree-focus",
            "catalogue-tree-couple-node", "catalogue-tree-paths", "connectedTreePathIds",
            "catalogue-tree-parent", "catalogue-tree-overlay", "catalogue-tree-timeline",
            "catalogue-tree-minimap", "catalogue-tree-pins", "catalogue-tree-history",
            "data-tree-export", "treeGedcom", "treeRenderLimit", "aria-posinset",
            "catalogue-tree-spouse-inline", "catalogue-tree-more", "catalogue-tree-navigation",
        ):
            self.assertIn(marker, search_js)
        self.assertIn("Hide details", search_js)
        self.assertNotIn('class="catalogue-tree-partner catalogue-tree-spouse"', search_js)
        catalogue_css = (WEB / "people" / "catalogue.css").read_text(encoding="utf-8")
        self.assertIn(".catalogue-tree-spouse-inline", catalogue_css)
        self.assertIn(".catalogue-tree-person-copy", catalogue_css)
        self.assertIn("glascow|glasgo|glascoe", search_js)
        self.assertIn("not a family branch", search_js)
        self.assertIn("catalogue-location-path-group", search_js)
        self.assertIn("catalogue-relation-confidence", search_js)
        self.assertIn("relationHtml(person.father,true)", search_js)
        self.assertIn("filters.dateType==='birth'?[person.birth_year]", search_js)
        self.assertIn("filters.locationType==='birth'?person._birthLocation", search_js)
        self.assertNotIn("Family branch / earliest ancestor", search_js)
        self.assertNotIn("sortHeader('recorded','Recorded in')", search_js)
        self.assertNotIn("sortHeader('cluster','Cluster')", search_js)
        self.assertNotIn("sortHeader('profile','WikiTree')", search_js)
        self.assertIn("scrollIntoView", search_js)
        self.assertIn("button[data-sort]", search_js)
        external_links_js = (WEB / "people" / "external-links.js").read_text(encoding="utf-8")
        self.assertIn("MutationObserver", external_links_js)
        self.assertIn("noopener", external_links_js)
        self.assertIn("noreferrer", external_links_js)

        updates = [person for person in index if person["needs_wikitree_update"]]
        profile_only_updates = {"Glasgow-3905", "Kyle-3461"}
        base_updates = profile_only_updates | {"Scott-69166", "Glasgow-2462"}
        findmypast_overrides = json.loads(
            (ROOT / "research" / "findmypast-glasgow-audit" / "catalogue-integration-overrides.json").read_text(encoding="utf-8")
        )["groups"]
        findmypast_updates = {
            item["profile_id"]
            for item in findmypast_overrides.values()
            if item["outcome"] == "existing_profile"
            and item["profile_id"] != "Glasgow-4063"
            and item.get("substantive_amendment") is True
        }
        reopened_updates = {
            "Glasgow-951", "Glasgow-938", "Glasgow-2738", "Glasgow-3903",
            "Glasgow-3188", "Glasgow-1495", "Glasgow-3062", "Glasgow-3075",
            "Glasgow-3179", "Wilson-142005", "Glasgow-3539", "Glasgow-1086",
            "Unknown-717333", "Glasgow-867", "Glasgow-2453", "Glasgow-3296",
            "Glasgow-1030", "Glasgow-3163", "Glasgow-3181", "Glasgow-3589",
            "Glasgow-3613", "Glasgow-3942", "Weir-4172",
            "Glasgow-3928",
        }
        self.assertEqual(
            {person["profile_ids"][0] for person in updates},
            base_updates | findmypast_updates | reopened_updates,
        )
        updates_by_profile = {person["profile_ids"][0]: person for person in updates}
        self.assertTrue(all(updates_by_profile[profile_id]["record_count"] == 0 for profile_id in profile_only_updates))
        self.assertGreaterEqual(updates_by_profile["Scott-69166"]["record_count"], 1)
        self.assertGreaterEqual(updates_by_profile["Glasgow-2462"]["record_count"], 1)
        self.assertTrue(all(updates_by_profile[profile_id]["record_count"] >= 1 for profile_id in findmypast_updates))
        self.assertIn("needsUpdate:'needsUpdate'", search_js)
        self.assertIn("'significance:desc','Update significance'", search_js)
        update_count = len(base_updates | findmypast_updates | reopened_updates)
        self.assertIn(f"{update_count} source-backed corrections remain on WikiTree", catalogue_html)
        self.assertIn(f"{update_count} profiles ranked by significance", catalogue_html)
        detached_update_html = (WEB / "people" / "glasgow-2769.html").read_text(encoding="utf-8")
        self.assertIn("[[Glasgow-1983|Robert Glasgow]] was previously attached as Robert&#x27;s father", detached_update_html)
        self.assertIn("== Research Notes ==", detached_update_html)
        self.assertIn("&lt;references /&gt;", detached_update_html)
        self.assertNotIn("Required profile change", detached_update_html)
        self.assertNotIn("Evidence-led project update", detached_update_html)
        rendered_update_drafts = 0
        for update_page in (WEB / "people").glob("*.html"):
            page_text = update_page.read_text(encoding="utf-8")
            draft = re.search(r'<textarea id="profile-update-draft".*?>(.*?)</textarea>', page_text, re.S)
            if not draft:
                continue
            rendered_update_drafts += 1
            draft_text = unescape(draft.group(1))
            for heading in ("== Biography ==", "== Research Notes ==", "== Sources ==", "<references />"):
                self.assertIn(heading, draft_text, update_page.name)
            self.assertLess(draft_text.index("== Research Notes =="), draft_text.index("== Sources =="), update_page.name)
            self.assertNotRegex(
                draft_text,
                r"(?mi)^(?:Required profile change|Evidence-led project update)\b",
                update_page.name,
            )
        self.assertEqual(rendered_update_drafts, update_count)
        self.assertTrue((WEB / "people" / "profile-update.js").exists())

        portable_person = (WEB / "people" / "glasgow-2072.html").read_text(encoding="utf-8")
        self.assertIn('href="../people/catalogue.css?', portable_person)
        self.assertIn('href="../catalogue.html"', portable_person)
        self.assertNotIn('href="/people/', portable_person)

        passage_html = (WEB / "people" / "glasgow-1026.html").read_text(encoding="utf-8")
        self.assertIn('class="record-passage-bullets"', passage_html)
        self.assertIn('<a href="https://familysearch.org/', passage_html)

    def test_machine_dossiers_are_integral_compact_and_private(self):
        bulk = json.loads((WEB / "data" / "people.json").read_text(encoding="utf-8"))
        self.assertEqual(bulk["schema_version"], "1.0")
        compact = json.loads((WEB / "data" / "people-index.json").read_text(encoding="utf-8"))
        self.assertEqual(len(compact), len(bulk["people"]))
        self.assertLess(
            (WEB / "data" / "people-index.json").stat().st_size,
            1_000 * len(compact),
        )
        compact_text = (WEB / "data" / "people-index.json").read_text(encoding="utf-8")
        self.assertNotIn('"biography_text"', compact_text)
        self.assertNotIn('"evidence"', compact_text)
        self.assertNotIn('"_sibling_ids"', compact_text)
        self.assertNotIn('"_parent_links"', compact_text)
        self.assertFalse(any(person["id"] == "Glasgow-933" for person in compact))

        index_ids = {profile_id for person in compact for profile_id in [person["id"], *person.get("alternate_ids", [])]}
        for entry in compact:
            html_path = WEB / entry["html_url"].lstrip("/")
            json_path = WEB / entry["json_url"].lstrip("/")
            network_path = WEB / entry["network_url"].lstrip("/")
            self.assertTrue(html_path.exists(), entry["id"])
            self.assertTrue(json_path.exists(), entry["id"])
            self.assertTrue(network_path.exists(), entry["id"])
            # Complete paste-ready amendment and HOLD drafts are deliberately
            # exposed in the dossier JSON for catalogue consumers.
            self.assertLess(json_path.stat().st_size, 384_000, entry["id"])
            dossier = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(dossier["schema_version"], "1.0")
            self.assertEqual(dossier["id"], entry["id"])
            self.assertNotIn("biography_text", dossier)
            self.assertNotIn("biography_wikitext", dossier)
            claim_ids = [claim["id"] for claim in dossier["claims"]]
            evidence_ids = [evidence["id"] for evidence in dossier["evidence"]]
            lead_ids = [lead["id"] for lead in dossier["research_leads"]]
            self.assertEqual(len(claim_ids), len(set(claim_ids)), entry["id"])
            self.assertEqual(len(evidence_ids), len(set(evidence_ids)), entry["id"])
            self.assertEqual(len(lead_ids), len(set(lead_ids)), entry["id"])
            for claim in dossier["claims"]:
                self.assertTrue(set(claim.get("evidence_ids", [])) <= set(evidence_ids), claim["id"])
            for evidence in dossier["evidence"]:
                self.assertTrue(set(evidence.get("claim_ids", [])) <= set(claim_ids), evidence["id"])
            for group in dossier["relationships"].values():
                for relation in group:
                    self.assertTrue(set(relation.get("evidence_ids", [])) <= set(evidence_ids))
                    if relation.get("json_url"):
                        self.assertIn(relation["id"], index_ids)
                        self.assertTrue((WEB / relation["json_url"].lstrip("/")).exists())
            html = html_path.read_text(encoding="utf-8")
            self.assertIn(f'rel="alternate" type="application/json" href="https://glasgow.phenotype.dev{entry["json_url"]}"', html)

    def test_alexander_glasgow_resolution_and_relationship_evidence(self):
        index = json.loads((WEB / "data" / "people-index.json").read_text(encoding="utf-8"))
        candidates = resolver_candidates(index, "Alexander Glasgow", birth=1811, location="County Antrim", spouse="Mary McCaughan")
        self.assertGreater(len(candidates), 1)
        self.assertEqual(candidates[0]["id"], "Glasgow-951")
        self.assertIn("birth year match", candidates[0]["match_reasons"])
        self.assertIn("location match", candidates[0]["match_reasons"])
        self.assertIn("spouse match", candidates[0]["match_reasons"])

        dossier = json.loads((WEB / "people" / "glasgow-951.json").read_text(encoding="utf-8"))
        robert = next(relation for relation in dossier["relationships"]["children"] if relation["id"] == "Glasgow-938")
        self.assertTrue(robert["tree_relationship"])
        self.assertEqual(robert["relationship_source"], "reconstructed_parent_reference")
        self.assertEqual(robert["status"], "proved")
        evidence = next(item for item in dossier["evidence"] if item["id"] in robert["evidence_ids"])
        self.assertEqual(evidence["source_quality"], "original")
        self.assertIn("father Alexander, farmer", evidence["assertion"])
        self.assertIn("marriage_returns/marriages_1866", evidence["source"]["url"])
        self.assertTrue(dossier["open_questions"])
        self.assertTrue(any(lead["reference"] == "MIC/1P/357" for lead in dossier["research_leads"]))
        network = json.loads((WEB / "people" / "glasgow-951.network.json").read_text(encoding="utf-8"))
        network_robert = next(relation for relation in network["relationships"] if relation["id"] == "Glasgow-938")
        self.assertEqual(network_robert["best_evidence"]["record_type"], "marriage")

        static_resolver = json.loads((WEB / "data" / "resolve" / "alexander-glasgow.json").read_text(encoding="utf-8"))
        self.assertGreater(static_resolver["candidate_count"], 1)
        self.assertIn("Glasgow-951", {candidate["id"] for candidate in static_resolver["candidates"]})

    def test_case_findings_and_similar_people_are_integrated(self):
        dossier = json.loads((WEB / "people" / "glasgow-951.json").read_text(encoding="utf-8"))
        self.assertTrue(dossier["research_findings"])
        sections = [section for finding in dossier["research_findings"] for section in finding["sections"]]
        self.assertIn("Current conclusion", {section["title"] for section in sections})
        self.assertIn("Source findings", {section["title"] for section in sections})
        self.assertTrue(dossier["similar_people"])
        self.assertTrue(all(candidate["id"] != "Glasgow-951" for candidate in dossier["similar_people"]))
        self.assertTrue(all(candidate["match_reasons"] for candidate in dossier["similar_people"]))
        self.assertTrue(dossier["potential_parentage"]["children_recorded"])
        parentage_reasons = [reason for candidate in dossier["potential_parentage"]["candidates"] for reason in candidate["reasons"]]
        self.assertTrue(any("niece/nephew network" in reason and "public profiles" in reason for reason in parentage_reasons))
        html = (WEB / "people" / "glasgow-951.html").read_text(encoding="utf-8")
        for marker in ("Latest case research", "Case-file source findings", "FIN/5/A/236", "Potential parents", "Possible duplicates"):
            self.assertIn(marker, html)
        for marker in ('data-candidate-tabs', 'role="tablist"', 'class="candidate-card parentage-card"', 'class="candidate-card duplicate-card"', 'class="fit-track"'):
            self.assertIn(marker, html)
        self.assertNotIn('class="similar-subject-summary"', html)
        self.assertNotIn('class="parentage-clues"', html)
        self.assertNotIn('<section id="family">', html)
        self.assertIn('<details id="timeline" class="page-disclosure ', html)
        self.assertTrue((WEB / "people" / "candidate-tabs.js").exists())
        overview = html.split('<section id="overview"', 1)[1].split('<section id="candidate-analysis"', 1)[0]
        for marker in ("Glasgow-951", "Birth", "Death", "Parents", "Spouses", "Children", "Comparison context", "Paternal grandfather position", "Paternal grandmother position"):
            self.assertIn(marker, overview)
        self.assertIn("Potential parents or duplicates", html)
        self.assertIn('class="local-artifact"', html)
        self.assertNotIn("wikitree.com/wiki/proni_FIN", html)
        untouched = json.loads((WEB / "people" / "glasgow-1057.json").read_text(encoding="utf-8"))
        self.assertFalse(untouched["research_findings"])

        mapped = json.loads((WEB / "people" / "glasgow-3990.json").read_text(encoding="utf-8"))
        self.assertTrue(mapped["research_findings"])
        self.assertEqual(mapped["research_findings"][0]["profile_id"], "Glasgow-3990")
        mapped_html = (WEB / "people" / "glasgow-3990.html").read_text(encoding="utf-8")
        self.assertIn("Case-file source findings", mapped_html)
        self.assertIn("https://apps.proni.gov.uk/ProniNames_IE/SearchPage.aspx", mapped_html)
        self.assertNotIn('id="profile-link-form"', mapped_html)
        self.assertNotIn("WikiTree profile workbench", html)

        profile_script = (WEB / "people" / "profile-creation.js").read_text(encoding="utf-8")
        self.assertNotIn("JSON.stringify", profile_script)
        self.assertNotIn("Download link update", profile_script)

        audit_payload = json.loads((ROOT / "data" / "wikitree" / "catalogue-profile-audit.json").read_text(encoding="utf-8"))
        expected_audit_entries = {
            catalogue_id
            for catalogue_id, draft_path in discover_drafts().items()
            if draft_path.startswith("surname-research/new-people/")
        }
        expected_audit_entries.update({
            "record-medieval-1283-alexander-richard-constable",
            "record-medieval-1283-alexander-richard-messenger",
            "record-medieval-1289-alexander-escheator",
            "record-medieval-1506-john-alias-smith",
            "record-fmp-glasgow-11443ace3ea2",
            "record-fmp-glasgow-7a66001e8cd6",
            "record-fmp-glasgow-a0b809464cc9",
            "record-hugh-glasgow-tamlaght-o-crilly-1772-declaration",
            "record-thomas-glasco-76891c1835",
        })
        self.assertEqual(set(audit_payload["entries"]), expected_audit_entries)
        bespoke_ids = {
            "record-john-of-portrush-robert-glasgow-1666",
            "record-north-leith-robert-glasgow-1694",
            "record-hugh-glasgow-tamlaght-o-crilly-1740-entry-1272",
            "record-thomas-glasco-76891c1835",
            "record-ballybogy-1825-james-glasgow",
            "record-drumragh-mary-glasgow-1828",
            "record-robert-glasgow-45f84ce490",
            "record-newberry-cleora-glasgow-speers",
            "record-inishrush-lindsey-glasgow-1882",
            "record-alexander-glasgow-94245e5bf7",
        }
        self.assertLessEqual(bespoke_ids, set(audit_payload["entries"]))
        for resolved_id in (
            "record-fmp-glasgow-17ba21591d7d", "record-fmp-glasgow-37cd5c63b64f",
            "record-fmp-glasgow-bacd8e7498f2", "record-fmp-glasgow-27f929774fdc",
            "record-fmp-glasgow-e9bdb7a1c978",
        ):
            self.assertNotIn(resolved_id, audit_payload["entries"])
        self.assertNotIn("record-fmp-glasgow-67ec4399079d", audit_payload["entries"])

        catalogue_people = json.loads(
            (WEB / "data" / "people.json").read_text(encoding="utf-8")
        )["people"]
        unlinked = [person for person in catalogue_people if not person["has_wikitree_destination"]]
        audit_entries = audit_payload["entries"].values()
        expected_work_statuses = Counter(
            "creation_ready" if entry["recommended_action"] == "create_new_profile"
            else "existing_profile_candidate" if entry["candidates"]
            else "identity_hold"
            for entry in audit_entries
            if entry["recommended_action"] != "do_not_create"
        )
        unreviewed_ids = {
            person["catalogue_id"] for person in unlinked
            if person["profile_work_status"] == "unreviewed"
        }
        self.assertEqual(unreviewed_ids, set())
        expected_work_statuses["unreviewed"] = len(unreviewed_ids)
        expected_work_statuses["free_space_only"] = sum(
            1 for person in unlinked
            if audit_payload["entries"].get(person["catalogue_id"], {}).get("recommended_action")
            == "do_not_create"
        )
        self.assertEqual(Counter(person["profile_work_status"] for person in unlinked), expected_work_statuses)
        linked_space = [person for person in catalogue_people if person["profile_work_status"] == "linked_free_space"]
        self.assertEqual(len(linked_space), 6)
        self.assertTrue(all(person["wikitree_free_space_url"].startswith("https://www.wikitree.com/wiki/Space:") for person in linked_space))
        catalogue_html = (WEB / "catalogue.html").read_text(encoding="utf-8")
        self.assertIn("Creation-ready profiles", catalogue_html)
        candidate_holds = expected_work_statuses["existing_profile_candidate"]
        self.assertIn(f"{candidate_holds} possible existing-profile matches on HOLD", catalogue_html)
        self.assertNotIn("Unlinked WikiTree entries", catalogue_html)

        holkham = json.loads((WEB / "people" / "glasgow-4063.json").read_text(encoding="utf-8"))
        self.assertTrue(holkham["research_findings"])
        self.assertEqual(holkham["vitals"]["death"]["date"], "1560-03-23")
        self.assertTrue(any(
            item["source"]["url"].endswith("GBPRS%2FNORFOLK%2FBUR%2F004320950&tab=this")
            for item in holkham["evidence"]
        ))

    def test_profile_creation_vital_always_uses_a_defensible_date(self):
        estimated = _profile_creation_vital({
            "birth": "c. 1667 (estimated)", "birth_note": "Estimated from an adult record.",
            "death": "", "records": [],
        })
        self.assertEqual((estimated["kind"], estimated["value"], estimated["status"]), ("Birth", "about 1667", "uncertain"))
        derived = _profile_creation_vital({
            "birth": "", "death": "", "records": [{"year": "1801", "filter_year": 1801, "association": "taxpayer"}],
        })
        self.assertEqual((derived["kind"], derived["value"]), ("Birth", "about 1783"))

    def test_profile_work_status_is_consolidation_first(self):
        unlinked = {"profile_ids": []}
        self.assertEqual(
            _profile_work_status(unlinked, {"recommended_action": "hold", "candidates": [{"profile_id": "Glasgow-1"}]}),
            "existing_profile_candidate",
        )
        self.assertEqual(
            _profile_work_status(unlinked, {"recommended_action": "hold", "candidates": []}),
            "identity_hold",
        )
        self.assertEqual(
            _profile_work_status(unlinked, {"recommended_action": "create_new_profile", "candidates": []}),
            "creation_ready",
        )
        self.assertEqual(
            _profile_work_status(unlinked, {"recommended_action": "do_not_create", "identity_status": "free_space_only"}),
            "free_space_only",
        )
        self.assertEqual(
            _profile_work_status({"profile_ids": [], "wikitree_free_space_url": "https://www.wikitree.com/wiki/Space:Example"}, {}),
            "linked_free_space",
        )

    def test_profile_update_significance_ranks_genealogical_impact(self):
        relationship = _profile_update_significance("REOPEN", "The testament directly calls Marion his sister.")
        vital = _profile_update_significance("OPEN", "Correct the death date from 11 to 12 December 1878.")
        citation = _profile_update_significance("OPEN", "Add the archive citation.")
        self.assertGreater(relationship, vital)
        self.assertGreater(vital, citation)

    def test_periodic_profile_match_requires_one_new_vital_fingerprint(self):
        previous = {
            "recommended_action": "ready_to_create", "candidates": [],
            "allow_auto_match": True,
        }
        candidate = {"profile_id": "Glasgow-9999", "score": 90, "birth_year_match": True}
        self.assertEqual(new_draft_match([candidate], previous), candidate)
        self.assertIsNone(new_draft_match([candidate, {**candidate, "profile_id": "Glasgow-9998"}], previous))
        self.assertIsNone(new_draft_match([{**candidate, "birth_year_match": False}], previous))
        weak = {"profile_id": "Glasgow-3970", "score": 60, "birth_year_match": False}
        previous_with_fallback = {
            "recommended_action": "ready_to_create", "candidates": [weak],
            "allow_auto_match": True,
        }
        self.assertEqual(new_draft_match([weak, candidate], previous_with_fallback), candidate)

    def test_low_scoring_profile_audit_retains_two_fallbacks(self):
        candidates = [
            {"profile_id": "Glasgow-3970", "score": 60},
            {"profile_id": "Glasgow-1078", "score": 55},
            {"profile_id": "Glasgow-1502", "score": 40},
        ]
        self.assertEqual([item["profile_id"] for item in select_candidates(candidates)], ["Glasgow-3970", "Glasgow-1078"])
        person = {
            "name": "Robert Glascow", "birth": "c. 1667 (estimated)", "birth_location": "Belfast (estimated)",
            "recorded_in": ["Belfast"], "regions": ["Ireland"],
        }
        profile = {
            "Name": "Glasgow-3970", "FirstName": "Robert", "LastNameAtBirth": "Glasgow",
            "BirthDate": "1625-00-00", "BirthLocation": "", "DeathDate": "0000-00-00",
            "DeathLocation": "Larne, County Antrim, Ireland",
        }
        self.assertEqual(candidate_summary(profile, person, 1685)["score"], 60)

    def test_glascow_and_glasgow_share_duplicate_bucket(self):
        common = {
            "death_year": None, "death_status": None, "parent_ids": [], "parent_names": [],
            "spouse_ids": [], "spouse_names": [], "child_ids": [], "child_names": [],
        }
        people = [
            {**common, "id": "record-robert", "catalogue_id": "record-robert", "html_url": "/people/record-robert.html",
             "name": "Robert Glascow", "birth_year": 1667, "birth_status": "estimated", "locations": ["Belfast"]},
            {**common, "id": "Glasgow-3970", "catalogue_id": "glasgow-3970", "html_url": "/people/glasgow-3970.html",
             "name": "Robert Glasgow", "birth_year": 1625, "birth_status": "uncertain", "locations": ["Larne, County Antrim"]},
        ]
        self.assertEqual(_similar_people(people)["record-robert"][0]["id"], "Glasgow-3970")
        self.assertEqual(resolver_candidates(people, "Robert Glascow")[0]["id"], "Glasgow-3970")

    def test_similar_people_compare_children_by_profile_and_name(self):
        base = {
            "name": "John Glasgow", "birth_year": 1800, "death_year": 1860,
            "birth_place": "County Antrim, Ireland", "death_place": "County Antrim, Ireland",
            "locations": ["County Antrim, Ireland"], "parent_ids": [],
            "parent_names": ["Robert Glasgow"], "spouse_ids": [],
            "spouse_names": ["Mary Smith"], "child_ids": [],
            "child_names": ["James Glasgow", "Mary Ann Glasgow", "Robert Glasgow"],
        }
        people = [
            {**base, "id": "Glasgow-9001", "catalogue_id": "glasgow-9001", "html_url": "/people/glasgow-9001.html"},
            {**base, "id": "Glasgow-9002", "catalogue_id": "glasgow-9002", "html_url": "/people/glasgow-9002.html"},
        ]
        candidate = _similar_people(people)["Glasgow-9001"][0]
        self.assertEqual(candidate["classification"], "possible duplicate")
        self.assertEqual(candidate["matching_children"], ["James Glasgow", "Mary Ann Glasgow", "Robert Glasgow"])
        self.assertTrue(any("matching child names" in reason for reason in candidate["match_reasons"]))

        far_apart = {
            **base, "id": "Glasgow-9003", "catalogue_id": "glasgow-9003",
            "html_url": "/people/glasgow-9003.html", "birth_year": 1600, "death_year": 1660,
        }
        results = _similar_people([*people, far_apart])["Glasgow-9001"]
        self.assertNotIn("Glasgow-9003", {item["id"] for item in results})

    def test_similar_people_weights_parent_certainty_and_conflicts(self):
        def person(profile_id, parent_id, parent_status, *, parent_tree_status="unmarked"):
            return {
                "id": profile_id, "alternate_ids": [], "catalogue_id": profile_id.casefold(),
                "html_url": f"/people/{profile_id.casefold()}.html", "name": "James Glasgow",
                "birth_year": 1800, "death_year": 1860, "birth_status": "uncertain", "death_status": "uncertain",
                "birth_place": "County Antrim, Ireland", "death_place": "County Antrim, Ireland",
                "locations": ["County Antrim, Ireland"], "parent_ids": [parent_id],
                "parent_names": [parent_id], "spouse_ids": [], "spouse_names": [],
                "child_ids": [], "child_names": [], "_parent_links": [{
                    "id": parent_id, "name": parent_id, "relationship": "father",
                    "status": parent_status, "status_label": parent_status,
                    "tree_status": parent_tree_status,
                }],
            }

        subject = person("Glasgow-9300", "Glasgow-8000", "proved")
        same_proved = person("Glasgow-9301", "Glasgow-8000", "proved")
        same_uncertain = person("Glasgow-9302", "Glasgow-8000", "unknown", parent_tree_status="uncertain")
        conflicting = person("Glasgow-9303", "Glasgow-8001", "proved")
        confident_conflict = person("Glasgow-9304", "Glasgow-8002", "unknown", parent_tree_status="confident")
        candidates = {item["id"]: item for item in _similar_people([subject, same_proved, same_uncertain, conflicting, confident_conflict])[subject["id"]]}
        self.assertGreater(candidates["Glasgow-9301"]["score"], candidates["Glasgow-9302"]["score"])
        self.assertIn("independently supported father", " ".join(candidates["Glasgow-9301"]["match_reasons"]))
        self.assertIn("at least one relationship is uncertain", " ".join(candidates["Glasgow-9302"]["match_reasons"]))
        self.assertEqual(candidates["Glasgow-9303"]["classification"], "similar person")
        self.assertIn("supported fathers are different", " ".join(candidates["Glasgow-9303"]["conflicts"]))
        self.assertEqual(candidates["Glasgow-9304"]["classification"], "similar person")
        self.assertIn("marked-confident fathers are different", " ".join(candidates["Glasgow-9304"]["conflicts"]))

    def test_potential_parentage_scores_age_and_family_naming_patterns(self):
        def person(profile_id, name, birth, gender, children=None, siblings=None, sibling_ids=None):
            return {
                "id": profile_id, "alternate_ids": [], "catalogue_id": profile_id.casefold(),
                "html_url": f"/people/{profile_id.casefold()}.html", "name": name,
                "birth_year": birth, "death_year": None, "gender": gender,
                "birth_place": "Lisnagaver, County Antrim, Ireland",
                "birth_surnames": ["Glasgow"], "current_surnames": ["Glasgow"],
                "locations": ["Lisnagaver, County Antrim, Ireland"], "parent_ids": [], "spouse_ids": [],
                "spouse_names": [], "child_ids": children or [], "child_names": [],
                "_sibling_ids": sibling_ids or [], "sibling_names": siblings or [],
            }

        people = [
            person("Glasgow-9001", "Alexander Glasgow", 1800, "Male", ["Glasgow-9101", "Glasgow-9102"]),
            person("Glasgow-9101", "John Glasgow", 1825, "Male"),
            person("Glasgow-9102", "Adam Glasgow", 1827, "Male", ["Glasgow-9201"]),
            person("Glasgow-9201", "Zephaniah Glasgow", 1852, "Male"),
            person("Glasgow-8001", "John Glasgow", 1764, "Male", siblings=["Adam Glasgow"], sibling_ids=["Glasgow-8050"]),
            person("Glasgow-8050", "Adam Glasgow", 1770, "Male", ["Glasgow-8051"]),
            person("Glasgow-8051", "Zephaniah Glasgow", 1795, "Male"),
            person("Glasgow-8002", "John Glasgow", 1764, "Male", siblings=["John Glasgow"]),
        ]
        people[0]["parent_ids"] = ["Glasgow-8002"]
        people[0]["_parent_links"] = [{
            "id": "Glasgow-8002", "name": "John Glasgow", "relationship": "father",
            "status": "unknown", "status_label": "WikiTree tree relationship",
            "tree_status": "uncertain", "tree_status_label": "WikiTree: uncertain parent",
        }]
        result = _potential_parentage(people)["Glasgow-9001"]
        self.assertEqual(result["earliest_dated_son"]["name"], "John Glasgow")
        self.assertEqual(result["candidates"][0]["id"], "Glasgow-8001")
        self.assertEqual(result["candidates"][0]["age_gap"], 36)
        reasons = " ".join(result["candidates"][0]["reasons"])
        self.assertIn("first dated son John Glasgow", reasons)
        self.assertIn("expected father position for a male subject", reasons)
        self.assertIn("sibling and niece/nephew network", reasons)
        self.assertIn("Adam +16", reasons)
        self.assertIn("Zephaniah", reasons)
        self.assertIn("Zephaniah +16", reasons)
        self.assertIn("public profiles", reasons)
        self.assertNotIn("surname matches", reasons)
        self.assertEqual(result["candidates"][0]["classification"], "strong multi-factor lead")
        self.assertNotIn("Glasgow-8002", {candidate["id"] for candidate in result["candidates"]})

    def test_bounded_subject_uses_first_child_and_titled_candidate_names(self):
        def person(profile_id, name, birth, place, **extra):
            value = {
                "id": profile_id, "alternate_ids": [], "catalogue_id": profile_id.casefold(),
                "html_url": f"/people/{profile_id.casefold()}.html", "name": name,
                "birth_year": birth, "death_year": None, "gender": "Male",
                "birth_place": place, "birth_surnames": ["Glasgow"],
                "current_surnames": ["Glasgow"], "locations": [place],
                "parent_ids": [], "spouse_ids": [], "spouse_names": [],
                "child_ids": [], "child_names": [], "_parent_links": [],
                "_sibling_ids": [], "_sibling_links": [], "sibling_names": [],
                "occupations": [], "_dated_records": [], "_birth_expression": str(birth),
            }
            value.update(extra)
            return value

        people = [
            person("Glasgow-3960", "John Glasgow", 1707, "County Leitrim, Ireland",
                   child_ids=["Glasgow-3124"], _birth_expression="before 1707"),
            person("Glasgow-3124", "James Glasgow", 1750, "County Leitrim, Ireland",
                   parent_ids=["Glasgow-3960"]),
            person("Glasgow-3967", "James Glasgow R.E", 1678, "Duneane, County Antrim, Ireland",
                   _birth_expression="before 1678"),
            person("Glasgow-635", "Reverend James Patrick Glasgow", 1680, "Ireland",
                   _birth_expression="c. 1680"),
        ]
        result = _potential_parentage(people)["Glasgow-3960"]
        candidates = {candidate["id"]: candidate for candidate in result["candidates"]}
        self.assertEqual(_relative_given_name("Reverend James Patrick Glasgow"), "james")
        self.assertIn("Glasgow-3967", candidates)
        self.assertIn("Glasgow-635", candidates)
        self.assertIn("true gap uncertain", candidates["Glasgow-3967"]["age_gap_label"])
        self.assertEqual(candidates["Glasgow-635"]["age_gap_label"], "at most 27 years")
        self.assertIn("grandparent-generation interval", " ".join(candidates["Glasgow-3967"]["reasons"]))

    def test_parentage_uses_direct_name_locality_and_matching_child_profile(self):
        def person(profile_id, name, birth, place, **extra):
            value = {
                "id": profile_id, "alternate_ids": [], "catalogue_id": profile_id.casefold(),
                "html_url": f"/people/{profile_id.casefold()}.html", "name": name,
                "birth_year": birth, "death_year": None, "gender": "Male",
                "birth_place": place, "birth_surnames": ["Glasgow"], "current_surnames": ["Glasgow"],
                "locations": [place, "Mid Calder"], "research_clusters": ["Scotland leads"],
                "parent_ids": [], "spouse_ids": [], "spouse_names": [], "child_ids": [], "child_names": [],
                "_parent_links": [], "_sibling_ids": [], "_sibling_links": [], "sibling_names": [],
                "occupations": [], "_dated_records": [], "_birth_expression": str(birth),
            }
            value.update(extra)
            return value

        people = [
            person("Glasgow-2453", "William Glasgow", 1630, "Mid Calder, Linlithgowshire, Scotland",
                   child_ids=["Glasgow-2454"], parent_ids=["Glasgow-1084"], _birth_expression="before 1630",
                   _parent_links=[{"id": "Glasgow-1084", "name": "John Glasgow", "relationship": "father", "status": "unknown", "tree_status": "unmarked"}]),
            person("Glasgow-2454", "Issobel Glasgow", 1648, "Mid Calder, Linlithgowshire, Scotland",
                   gender="Female", parent_ids=["Glasgow-2453"]),
            person("Glasgow-1084", "John Glasgow", 1616, "Mid Calder, Midlothian, Scotland"),
            person("Glasgow-1087", "William Glasgow", 1609, "Mid Calder, Midlothian, Scotland",
                   child_ids=["Glasgow-3515"]),
            person("Glasgow-3515", "William Glasgow", 1625, "Kirknewton and East Calder, Midlothian, Scotland",
                   parent_ids=["Glasgow-1087"]),
        ]
        similar = {"Glasgow-2453": [{
            "id": "Glasgow-3515", "name": "William Glasgow", "score": 44,
            "classification": "similar person", "html_url": "/people/glasgow-3515.html",
        }]}
        candidates = {
            candidate["id"]: candidate
            for candidate in _potential_parentage(people, similar)["Glasgow-2453"]["candidates"]
        }
        self.assertIn("Glasgow-1087", candidates)
        reasons = " ".join(candidates["Glasgow-1087"]["reasons"])
        self.assertIn("same specific indexed locality", reasons)
        self.assertIn("share the given name William", reasons)
        self.assertIn("already has child profile William Glasgow (Glasgow-3515)", reasons)
        self.assertIn("resolving a matching existing child profile", " ".join(candidates["Glasgow-1087"]["conflicts"]))
        self.assertEqual(candidates["Glasgow-1087"]["classification"], "resolve child duplicate first")

    def test_childless_subject_uses_repeated_name_in_siblings_descendant_branches(self):
        def person(profile_id, name, birth, gender="Male", **extra):
            value = {
                "id": profile_id, "alternate_ids": [], "catalogue_id": profile_id.casefold(),
                "html_url": f"/people/{profile_id.casefold()}.html", "name": name,
                "birth_year": birth, "death_year": None, "gender": gender,
                "birth_place": None, "birth_surnames": ["Glasgow"], "current_surnames": ["Glasgow"],
                "locations": [], "research_clusters": [], "parent_ids": [], "spouse_ids": [],
                "spouse_names": [], "child_ids": [], "child_names": [], "_parent_links": [],
                "_sibling_ids": [], "_sibling_links": [], "sibling_names": [], "occupations": [],
                "_dated_records": [], "_birth_expression": str(birth),
            }
            value.update(extra)
            return value

        people = [
            person("Glasgow-3915", "Elizabeth Glasgow", 1530, "Female", _birth_expression="before 1530"),
            person("Glasgow-1096", "Robert Glasgow", 1520, child_ids=["Glasgow-3188"],
                   child_names=["Ninian Glasgow"], _birth_expression="c. 1520"),
            person("Glasgow-3188", "Ninian Glasgow", 1550, parent_ids=["Glasgow-1096"],
                   child_ids=["Glasgow-1027", "Glasgow-3075"],
                   child_names=["Robert Glasgow", "William Glasgow"]),
            person("Glasgow-1027", "Robert Glasgow", 1583, parent_ids=["Glasgow-3188"],
                   child_ids=["Glasgow-1092"], child_names=["Bessie Glasgow"]),
            person("Glasgow-3075", "William Glasgow", 1590, parent_ids=["Glasgow-3188"],
                   child_ids=["Glasgow-3361"], child_names=["Bessie Glasgow"]),
            person("Glasgow-1092", "Bessie Glasgow", 1623, "Female", parent_ids=["Glasgow-1027"]),
            person("Glasgow-3361", "Bessie Glasgow", 1628, "Female", parent_ids=["Glasgow-3075"]),
        ]
        candidates = {
            candidate["id"]: candidate
            for candidate in _potential_parentage(people)["Glasgow-3915"]["candidates"]
        }
        self.assertIn("Glasgow-1096", candidates)
        robert = candidates["Glasgow-1096"]
        self.assertIn("missing-sibling descendant echo", robert["factors"])
        reasons = " ".join(robert["reasons"])
        self.assertIn("2 independent child branches", reasons)
        self.assertIn("candidate's child Ninian Glasgow", reasons)
        self.assertIn("Bessie Glasgow", reasons)
        self.assertIn("approximate birth date permits a narrow biologically viable interval", reasons)
        self.assertEqual(_relative_given_name("Bessie Glasgow"), "elizabeth")

    def test_married_surname_does_not_qualify_a_same_surname_father(self):
        def person(profile_id, name, birth, gender="Male", **extra):
            value = {
                "id": profile_id, "alternate_ids": [], "catalogue_id": profile_id.casefold(),
                "html_url": f"/people/{profile_id.casefold()}.html", "name": name,
                "birth_year": birth, "death_year": None, "gender": gender,
                "birth_place": "Lanarkshire, Scotland", "birth_surnames": ["Glasgow"],
                "current_surnames": ["Glasgow"], "locations": ["Lanarkshire, Scotland"],
                "research_clusters": ["Scotland leads"], "parent_ids": [], "spouse_ids": [],
                "spouse_names": [], "child_ids": [], "child_names": [], "_parent_links": [],
                "_sibling_ids": [], "_sibling_links": [], "sibling_names": [], "occupations": [],
                "_dated_records": [], "_birth_expression": str(birth), "birth_status": "uncertain",
            }
            value.update(extra)
            return value

        people = [
            person("Crooks-1812", "Annabella (Crooks) Glasgow", 1800, "Female",
                   birth_surnames=["Crooks"], current_surnames=["Glasgow"],
                   sibling_names=["Margaret Crooks"]),
            person("Glasgow-1648", "Mary Glasgow", 1775,
                   child_names=["Margaret Glasgow"]),
            person("Crooks-100", "John Crooks", 1774,
                   birth_surnames=["Crooks"], current_surnames=["Crooks"],
                   child_names=["Margaret Crooks"]),
        ]
        candidates = {
            candidate["id"]: candidate
            for candidate in _potential_parentage(people)["Crooks-1812"]["candidates"]
        }
        self.assertNotIn("Glasgow-1648", candidates)
        self.assertIn("Crooks-100", candidates)

    def test_exact_birth_with_unmarked_parent_suppresses_competing_parent(self):
        def person(profile_id, name, birth, **extra):
            value = {
                "id": profile_id, "alternate_ids": [], "catalogue_id": profile_id.casefold(),
                "html_url": f"/people/{profile_id.casefold()}.html", "name": name,
                "birth_year": birth, "death_year": None, "gender": "Male",
                "birth_place": "Ayrshire, Scotland", "birth_surnames": ["Glasgow"],
                "current_surnames": ["Glasgow"], "locations": ["Ayrshire, Scotland"],
                "research_clusters": ["Scotland leads"], "parent_ids": [], "spouse_ids": [],
                "spouse_names": [], "child_ids": [], "child_names": [], "_parent_links": [],
                "_sibling_ids": [], "_sibling_links": [], "sibling_names": [], "occupations": [],
                "_dated_records": [], "_birth_expression": str(birth), "birth_status": "uncertain",
            }
            value.update(extra)
            return value

        people = [
            person("Glasgow-9000", "William Glasgow", 1800,
                   birth_status="exact", _birth_expression="1800-04-12",
                   parent_ids=["Glasgow-8000"], sibling_names=["James Glasgow"],
                   _parent_links=[{
                       "id": "Glasgow-8000", "name": "John Glasgow", "relationship": "father",
                       "status": "unknown", "tree_status": "unmarked",
                   }]),
            person("Glasgow-8000", "John Glasgow", 1772),
            person("Glasgow-8001", "Robert Glasgow", 1770,
                   child_names=["James Glasgow"]),
        ]
        candidates = {
            candidate["id"]: candidate
            for candidate in _potential_parentage(people)["Glasgow-9000"]["candidates"]
        }
        self.assertNotIn("Glasgow-8000", candidates)
        self.assertNotIn("Glasgow-8001", candidates)

    def test_potential_father_uses_timed_place_household_and_spouse_chronology(self):
        def person(profile_id, name, birth, gender, **extra):
            value = {
                "id": profile_id, "alternate_ids": [], "catalogue_id": profile_id.casefold(),
                "html_url": f"/people/{profile_id.casefold()}.html", "name": name,
                "birth_year": birth, "death_year": None, "gender": gender,
                "birth_place": "Gortereghy, County Antrim, Ireland", "birth_surnames": ["Glasgow"],
                "current_surnames": ["Glasgow"], "locations": ["Gortereghy, County Antrim, Ireland"],
                "parent_ids": [], "spouse_ids": [], "spouse_names": [],
                "child_ids": [], "child_names": [], "_sibling_ids": [], "sibling_names": [],
                "occupations": [], "_dated_records": [],
            }
            value.update(extra)
            return value

        people = [
            person("Glasgow-9400", "Alexander Glasgow", 1800, "Male",
                   child_ids=["Glasgow-9401"], occupations=["Farmer"],
                   _dated_records=[
                       {"year": 1800, "location": "Gortereghy", "association": "probable birth locality", "status": "probable", "source_quality": "tree_only", "latitude": 54.936944, "longitude": -6.505833},
                       {"year": 1840, "location": "Gortereghy, County Antrim, Ireland", "association": "farm holding", "status": "proved", "source_quality": "original"},
                   ]),
            person("Glasgow-9401", "John Glasgow", 1825, "Male"),
            person("Glasgow-9410", "John Glasgow", 1768, "Male",
                   child_ids=["Glasgow-9411", "Glasgow-9412"], spouse_ids=["Glasgow-9413"], spouse_names=["Mary Glasgow"], occupations=["Farmer"],
                   _dated_records=[{"year": 1798, "location": "Gortereghy, County Antrim, Ireland", "association": "farm lease", "status": "proved", "source_quality": "original"}]),
            person("Glasgow-9411", "Robert Glasgow", 1797, "Male"),
            person("Glasgow-9412", "Adam Glasgow", 1803, "Male"),
            person("Glasgow-9413", "Mary Glasgow", 1770, "Female"),
            person("Glasgow-9420", "John Glasgow", 1768, "Male"),
            person("Glasgow-9430", "John Glasgow", 1768, "Male", locations=["Killoquin"],
                   _birth_expression="before 1768",
                   _dated_records=[{"year": 1768, "location": "Killoquin", "association": "reconstructed locality", "status": "possible", "source_quality": "tree_only", "latitude": 54.963611, "longitude": -6.485556}]),
            person("Glasgow-9440", "John Glasgow", 1768, "Male", locations=["Virginia, United States"],
                   _dated_records=[{"year": 1795, "location": "Virginia, United States", "association": "profile birthplace", "status": "possible", "source_quality": "tree_only", "latitude": 54.936944, "longitude": -6.505833, "precision": "Kin-inferred relationship locality"}]),
        ]
        candidates = {
            item["id"]: item for item in _potential_parentage(people)["Glasgow-9400"]["candidates"]
            if item["role"] == "possible father"
        }
        strong, weak = candidates["Glasgow-9410"], candidates["Glasgow-9420"]
        reasons = " ".join(strong["reasons"])
        self.assertGreater(strong["score"], weak["score"])
        self.assertEqual(strong["classification"], "strong multi-factor lead")
        self.assertIn("supported 1798 farm lease", reasons)
        self.assertIn("fits within the candidate's overall child-bearing span", reasons)
        self.assertIn("plausible maternal age", reasons)
        self.assertIn("land/farming records", reasons)
        self.assertGreaterEqual(strong["factor_count"], 6)
        nearby_reasons = " ".join(candidates["Glasgow-9430"]["reasons"])
        self.assertIn("3.2 km from the subject's birth-period Gortereghy", nearby_reasons)
        self.assertIn("one or both placements are unproved", nearby_reasons)
        self.assertIn("age gap of at least 32 years", nearby_reasons)
        self.assertEqual(candidates["Glasgow-9430"]["age_gap_label"], "at least 32 years")
        self.assertNotIn("no indexed locality overlap", " ".join(candidates["Glasgow-9430"]["conflicts"]))
        self.assertNotIn("mapped", " ".join(candidates["Glasgow-9440"]["reasons"]))

    def test_parent_naming_positions_depend_on_subject_gender(self):
        def person(profile_id, name, birth, gender, **extra):
            value = {
                "id": profile_id, "alternate_ids": [], "catalogue_id": profile_id.casefold(),
                "html_url": f"/people/{profile_id.casefold()}.html", "name": name,
                "birth_year": birth, "death_year": None, "gender": gender,
                "birth_place": "County Antrim, Ireland", "birth_surnames": [name.split()[-1]],
                "current_surnames": [name.split()[-1]], "locations": ["County Antrim, Ireland"],
                "parent_ids": [], "spouse_ids": [], "spouse_names": [], "child_ids": [], "child_names": [],
                "_parent_links": [], "_sibling_ids": [], "_sibling_links": [], "sibling_names": [],
                "occupations": [], "_dated_records": [],
            }
            value.update(extra)
            return value

        people = [
            person("Glasgow-9500", "Ann Glasgow", 1800, "Female", spouse_ids=["Glasgow-9506"], spouse_names=["Adam Glasgow"],
                   child_ids=["Glasgow-9501", "Glasgow-9502", "Glasgow-9503", "Glasgow-9504"]),
            person("Glasgow-9501", "Robert Glasgow", 1823, "Male", parent_ids=["Glasgow-9500", "Glasgow-9506"]),
            person("Glasgow-9502", "John Glasgow", 1825, "Male", parent_ids=["Glasgow-9500", "Glasgow-9506"]),
            person("Glasgow-9503", "Mary Glasgow", 1824, "Female", parent_ids=["Glasgow-9500", "Glasgow-9506"]),
            person("Glasgow-9504", "Ellen Glasgow", 1826, "Female", parent_ids=["Glasgow-9500", "Glasgow-9506"]),
            person("Glasgow-9506", "Adam Glasgow", 1798, "Male"),
            person("Glasgow-9510", "John Glasgow", 1765, "Male"),
            person("Glasgow-9510", "John Glasgow and Family", 1765, "Male", alternate_ids=["Unknown-9512"],
                   catalogue_id="glasgow-9510-unknown-9512"),
            person("Neely-9511", "Mary Neely", 1768, "Female", birth_surnames=["Neely"], current_surnames=["Glasgow"],
                   spouse_names=["Adam Glasgow"]),
        ]
        result = _potential_parentage(people)["Glasgow-9500"]
        self.assertEqual([item["id"] for item in result["candidates"]].count("Glasgow-9510"), 1)
        candidates = {item["id"]: item for item in result["candidates"]}
        father_reasons = " ".join(candidates["Glasgow-9510"]["reasons"])
        mother_reasons = " ".join(candidates["Neely-9511"]["reasons"])
        self.assertIn("second dated son John Glasgow", father_reasons)
        self.assertIn("expected father position for a female subject", father_reasons)
        self.assertIn("first dated daughter Mary Glasgow", mother_reasons)
        self.assertIn("expected mother position for a female subject", mother_reasons)

    def test_parentage_retains_sparse_chronology_fallbacks(self):
        def person(profile_id, name, birth, surname):
            return {
                "id": profile_id, "alternate_ids": [], "catalogue_id": profile_id.casefold(),
                "html_url": f"/people/{profile_id.casefold()}.html", "name": name,
                "birth_year": birth, "death_year": None, "gender": "Male",
                "birth_place": "Kirknewton, Scotland", "birth_surnames": [surname],
                "current_surnames": [surname], "locations": ["Kirknewton, Scotland"],
                "parent_ids": [], "spouse_ids": [], "spouse_names": [], "child_ids": [],
                "child_names": [], "_parent_links": [], "_sibling_ids": [],
                "_sibling_links": [], "sibling_names": [], "occupations": [], "_dated_records": [],
            }

        result = _potential_parentage([
            person("Glascoe-9950", "Robert Glascoe", 1688, "Glascoe"),
            person("Glasgow-9951", "John Glasgow", 1658, "Glasgow"),
        ])["Glascoe-9950"]
        candidate = next(item for item in result["candidates"] if item["id"] == "Glasgow-9951")
        self.assertEqual(candidate["classification"], "chronology-only fallback")
        self.assertGreaterEqual(candidate["score"], 8)

    def test_parentage_scores_birth_order_local_sibling_and_parental_couple_clues(self):
        def person(profile_id, name, birth, gender, **extra):
            value = {
                "id": profile_id, "alternate_ids": [], "catalogue_id": profile_id.casefold(),
                "html_url": f"/people/{profile_id.casefold()}.html", "name": name,
                "birth_year": birth, "death_year": None, "gender": gender,
                "birth_place": "Kirknewton, Scotland", "birth_surnames": [name.split()[-1]],
                "current_surnames": [name.split()[-1]], "locations": ["Kirknewton, Scotland"],
                "parent_ids": [], "spouse_ids": [], "spouse_names": [], "child_ids": [],
                "child_names": [], "_parent_links": [], "_sibling_ids": [],
                "_sibling_links": [], "sibling_names": [], "occupations": [], "_dated_records": [],
            }
            value.update(extra)
            return value

        people = [
            person("Glasgow-9960", "Alexander Glasgow", 1788, "Male",
                   parent_ids=["Stewart-9963"], _sibling_ids=["Glasgow-9962"],
                   _parent_links=[{"id": "Stewart-9963", "name": "Mary Stewart", "relationship": "mother", "tree_status": "confident"}]),
            person("Glasgow-9961", "John Glasgow", 1760, "Male",
                   parent_ids=["Glasgow-9964"], spouse_ids=["Stewart-9963"], spouse_names=["Mary Stewart"],
                   child_ids=["Glasgow-9962"], _parent_links=[{
                       "id": "Glasgow-9964", "name": "Alexander Glasgow", "relationship": "father",
                       "status": "proved", "status_label": "documented father",
                   }]),
            person("Glasgow-9962", "Robert Glasgow", 1792, "Male",
                   parent_ids=["Glasgow-9961", "Stewart-9963"]),
            person("Stewart-9963", "Mary Stewart", 1764, "Female",
                   spouse_ids=["Glasgow-9961"], birth_surnames=["Stewart"]),
            person("Glasgow-9964", "Alexander Glasgow", 1730, "Male"),
        ]
        candidate = next(
            item for item in _potential_parentage(people)["Glasgow-9960"]["candidates"]
            if item["id"] == "Glasgow-9961"
        )
        reasons = " ".join(candidate["reasons"])
        self.assertIn("same specific birth locality", reasons)
        self.assertIn("jointly recorded as parents", reasons)
        self.assertIn("first son position", reasons)
        self.assertIn("Scottish grandparent-name pattern", reasons)
        self.assertIn("local sibling birth", candidate["factors"])
        self.assertIn("sibling parental couple", candidate["factors"])
        self.assertIn("grandparent birth-order naming", candidate["factors"])

    def test_common_grandparent_birth_order_name_is_weak_but_nonzero(self):
        def person(profile_id, name, birth, gender="Male", surname="Glasgow", **extra):
            value = {
                "id": profile_id, "alternate_ids": [], "catalogue_id": profile_id.casefold(),
                "html_url": f"/people/{profile_id.casefold()}.html", "name": name,
                "birth_year": birth, "death_year": None, "gender": gender,
                "birth_place": "Kirknewton, Scotland", "birth_surnames": [surname],
                "current_surnames": [surname], "locations": ["Kirknewton, Scotland"],
                "parent_ids": [], "spouse_ids": [], "spouse_names": [], "child_ids": [],
                "child_names": [], "_parent_links": [], "_sibling_ids": [],
                "_sibling_links": [], "sibling_names": [], "occupations": [], "_dated_records": [],
            }
            value.update(extra)
            return value

        people = [
            person("Glasgow-9970", "Alexander Glasgow", 1788, child_ids=["Glasgow-9974"]),
            person("Glasgow-9971", "John Glasgow", 1760,
                   parent_ids=["Glasgow-9973"], child_ids=["Glasgow-9972"],
                   _parent_links=[{"id": "Glasgow-9973", "name": "Alexander Glasgow",
                                   "relationship": "father", "status": "proved"}]),
            person("Glasgow-9972", "Robert Glasgow", 1792, parent_ids=["Glasgow-9971"]),
            person("Glasgow-9973", "Alexander Glasgow", 1730),
            person("Glasgow-9974", "John Glasgow", 1810, parent_ids=["Glasgow-9970"]),
        ]
        people.extend(
            person(f"Other-{position}", f"Alexander Other{position}", 1850 + position,
                   surname=f"Other{position}")
            for position in range(80)
        )
        people.extend(
            person(f"Else-{position}", f"John Else{position}", 1950 + position,
                   surname=f"Else{position}")
            for position in range(80)
        )
        candidate = next(
            item for item in _potential_parentage(people)["Glasgow-9970"]["candidates"]
            if item["id"] == "Glasgow-9971"
        )
        reasons = " ".join(candidate["reasons"])
        self.assertIn("common grandparent birth-order naming", candidate["factors"])
        self.assertIn("+2; Scottish grandparent-name pattern", reasons)
        self.assertIn("weak alone", reasons)
        self.assertIn("expected father position for a male subject (+4;", reasons)

    def test_specific_migration_destination_outweighs_shared_country(self):
        def person(profile_id, name, birth, locations, **extra):
            value = {
                "id": profile_id, "alternate_ids": [], "catalogue_id": profile_id.casefold(),
                "html_url": f"/people/{profile_id.casefold()}.html", "name": name,
                "birth_year": birth, "death_year": None, "gender": "Male",
                "birth_place": "County Antrim, Ireland", "birth_surnames": ["Glasgow"],
                "current_surnames": ["Glasgow"], "locations": locations,
                "parent_ids": [], "spouse_ids": [], "spouse_names": [], "child_ids": [],
                "child_names": [], "_parent_links": [], "_sibling_ids": [],
                "_sibling_links": [], "sibling_names": [], "occupations": [], "_dated_records": [],
            }
            value.update(extra)
            return value

        destination = "Columbus, Franklin County, Ohio, United States"
        people = [
            person("Glasgow-9980", "Alexander Glasgow", 1800, ["County Antrim, Ireland"],
                   child_ids=["Glasgow-9981"]),
            person("Glasgow-9981", "Robert Glasgow", 1825, ["County Antrim, Ireland", destination],
                   parent_ids=["Glasgow-9980"]),
            person("Glasgow-9982", "John Glasgow", 1765, ["County Antrim, Ireland"],
                   child_ids=["Glasgow-9983"]),
            person("Glasgow-9983", "Daniel Glasgow", 1795, ["County Antrim, Ireland", destination],
                   parent_ids=["Glasgow-9982"]),
            person("Glasgow-9984", "James Glasgow", 1765, ["County Antrim, Ireland"],
                   child_ids=["Glasgow-9985"]),
            person("Glasgow-9985", "Samuel Glasgow", 1795,
                   ["County Antrim, Ireland", "Cleveland, Ohio, United States"],
                   parent_ids=["Glasgow-9984"]),
        ]
        candidates = {
            item["id"]: item for item in _potential_parentage(people)["Glasgow-9980"]["candidates"]
        }
        specific_reasons = " ".join(candidates["Glasgow-9982"]["reasons"])
        broad_reasons = " ".join(candidates["Glasgow-9984"]["reasons"])
        self.assertIn("same specific migration destination", specific_reasons)
        self.assertIn("broad migration", candidates["Glasgow-9984"]["factors"])
        self.assertIn("+1; weak alone", broad_reasons)
        self.assertGreater(candidates["Glasgow-9982"]["score"], candidates["Glasgow-9984"]["score"])

    def test_extended_tree_clues_cover_couples_siblings_names_and_branches(self):
        def person(profile_id, name, birth, gender, **extra):
            value = {
                "id": profile_id, "alternate_ids": [], "catalogue_id": profile_id.casefold(),
                "html_url": f"/people/{profile_id.casefold()}.html", "name": name,
                "birth_year": birth, "death_year": None, "gender": gender,
                "birth_place": "County Antrim, Ireland", "birth_surnames": [name.split()[-1]],
                "current_surnames": [name.split()[-1]], "locations": ["County Antrim, Ireland"],
                "parent_ids": [], "spouse_ids": [], "spouse_names": [], "child_ids": [], "child_names": [],
                "_parent_links": [], "_sibling_ids": [], "_sibling_links": [], "sibling_names": [],
                "occupations": [], "_dated_records": [],
            }
            value.update(extra)
            return value

        subject_children = ["Glasgow-9611", "Glasgow-9612", "Glasgow-9613", "Glasgow-9614", "Glasgow-9615", "Glasgow-9616", "Glasgow-9617"]
        people = [
            person("Glasgow-9600", "Alexander Glasgow", 1800, "Male", spouse_ids=["Irwin-9601"], spouse_names=["Mary Irwin"],
                   child_ids=subject_children, _sibling_ids=["Glasgow-9620", "Glasgow-9621"], sibling_names=["Daniel Glasgow", "Thomas Glasgow"],
                   _sibling_links=[
                       {"id": "Glasgow-9620", "name": "Daniel Glasgow", "status": "probable"},
                       {"id": "Glasgow-9621", "name": "Thomas Glasgow", "status": "probable"},
                   ]),
            person("Irwin-9601", "Mary Irwin", 1802, "Female", birth_surnames=["Irwin"], current_surnames=["Glasgow"],
                   parent_ids=["Irwin-9602", "Irwin-9603"], _parent_links=[
                       {"id": "Irwin-9602", "name": "Robert Irwin", "relationship": "father", "status": "proved"},
                       {"id": "Irwin-9603", "name": "Ellen Irwin", "relationship": "mother", "status": "proved"},
                   ], spouse_ids=["Glasgow-9600"]),
            person("Irwin-9602", "Robert Irwin", 1770, "Male", birth_surnames=["Irwin"]),
            person("Irwin-9603", "Ellen Irwin", 1772, "Female", birth_surnames=["Irwin"]),
            person("Glasgow-9611", "John Neely Glasgow", 1825, "Male", death_year=1826, parent_ids=["Glasgow-9600", "Irwin-9601"]),
            person("Glasgow-9612", "Ellen Glasgow", 1826, "Female", parent_ids=["Glasgow-9600", "Irwin-9601"]),
            person("Glasgow-9613", "Robert Glasgow", 1827, "Male", parent_ids=["Glasgow-9600", "Irwin-9601"],
                   spouse_ids=["Mitchell-9631"], child_ids=["Glasgow-9632"], locations=["County Antrim, Ireland", "Ontario, Canada"]),
            person("Glasgow-9614", "Rose Glasgow", 1828, "Female", parent_ids=["Glasgow-9600", "Irwin-9601"]),
            person("Glasgow-9615", "Alexander Glasgow", 1829, "Male", parent_ids=["Glasgow-9600", "Irwin-9601"]),
            person("Glasgow-9616", "Mary Glasgow", 1830, "Female", parent_ids=["Glasgow-9600", "Irwin-9601"]),
            person("Glasgow-9617", "John Glasgow", 1831, "Male", parent_ids=["Glasgow-9600", "Irwin-9601"]),
            person("Glasgow-9632", "Zephaniah Glasgow", 1850, "Female", parent_ids=["Glasgow-9613", "Mitchell-9631"]),
            person("Glasgow-9620", "Daniel Glasgow", 1802, "Male", child_ids=["Glasgow-9622"]),
            person("Glasgow-9621", "Thomas Glasgow", 1804, "Male", child_ids=["Glasgow-9623"]),
            person("Glasgow-9622", "John Glasgow", 1824, "Male", parent_ids=["Glasgow-9620"]),
            person("Glasgow-9623", "John Glasgow", 1826, "Male", parent_ids=["Glasgow-9621"]),
            person("Glasgow-9700", "John Glasgow", 1765, "Male", parent_ids=["Neely-9701"],
                   _parent_links=[{"id": "Neely-9701", "name": "Euphemia Neely", "relationship": "mother", "status": "probable"}],
                   spouse_ids=["Unknown-9702"], spouse_names=["Rose Unknown"],
                   child_ids=["Glasgow-9703", "Glasgow-9704", "Glasgow-9705", "Glasgow-9706", "Glasgow-9707", "Glasgow-9708"]),
            person("Neely-9701", "Zephaniah Neely", 1740, "Female", birth_surnames=["Neely"]),
            person("Unknown-9702", "Rose Unknown", 1768, "Female", birth_surnames=["Unknown"], spouse_ids=["Glasgow-9700"]),
            person("Glasgow-9703", "Daniel Glasgow", 1795, "Male", parent_ids=["Glasgow-9700", "Unknown-9702"], child_ids=["Mitchell-9631"],
                   locations=["County Antrim, Ireland", "Ontario, Canada"]),
            person("Glasgow-9704", "Mary Glasgow", 1796, "Female", parent_ids=["Glasgow-9700", "Unknown-9702"]),
            person("Glasgow-9705", "Euphemia Glasgow", 1798, "Female", parent_ids=["Glasgow-9700", "Unknown-9702"]),
            person("Glasgow-9706", "Thomas Glasgow", 1805, "Male", parent_ids=["Glasgow-9700", "Unknown-9702"], spouse_ids=["Mitchell-9709"]),
            person("Glasgow-9707", "John Glasgow", 1807, "Male", parent_ids=["Glasgow-9700", "Unknown-9702"]),
            person("Glasgow-9708", "Rose Glasgow", 1809, "Female", parent_ids=["Glasgow-9700", "Unknown-9702"]),
            person("Mitchell-9631", "Anne Mitchell", 1825, "Female", birth_surnames=["Mitchell"], current_surnames=["Mitchell"],
                   parent_ids=["Glasgow-9703"], spouse_ids=["Glasgow-9613"], locations=["County Antrim, Ireland", "Ontario, Canada"]),
            person("Mitchell-9709", "Jane Mitchell", 1805, "Female", birth_surnames=["Mitchell"], spouse_ids=["Glasgow-9706"]),
        ]
        result = _potential_parentage(people)["Glasgow-9600"]
        candidate = next(item for item in result["candidates"] if item["id"] == "Glasgow-9700")
        reasons = " ".join(candidate["reasons"])
        for marker in (
            "expected father position for a male subject", "jointly match both grandparent positions",
            "recurs independently in sibling households", "deliberately reused", "bundle bonus",
            "line surnames recur as descendant middle names", "parents' names recur among the subject's grandchildren",
            "spouse surnames recur", "migration destination", "reconnect through shared descendants",
            "candidate's own child family",
        ):
            self.assertIn(marker, reasons)
        self.assertGreaterEqual(result["naming_controls"]["matches"], 4)
        self.assertIn("Rose Unknown", candidate["suggested_co_parent"]["name"])

    def test_tree_paths_penalize_uncle_and_grandparent_candidates(self):
        def person(profile_id, name, birth, **extra):
            value = {
                "id": profile_id, "alternate_ids": [], "catalogue_id": profile_id.casefold(),
                "html_url": f"/people/{profile_id.casefold()}.html", "name": name,
                "birth_year": birth, "death_year": None, "gender": "Male",
                "birth_place": "County Antrim, Ireland", "birth_surnames": ["Glasgow"],
                "current_surnames": ["Glasgow"], "locations": ["County Antrim, Ireland"],
                "parent_ids": [], "spouse_ids": [], "spouse_names": [], "child_ids": [], "child_names": [],
                "_parent_links": [], "_sibling_ids": [], "_sibling_links": [], "sibling_names": [],
                "occupations": [], "_dated_records": [],
            }
            value.update(extra)
            return value

        people = [
            person("Glasgow-9800", "Alexander Glasgow", 1800, child_ids=["Glasgow-9801", "Glasgow-9802"],
                   parent_ids=["Glasgow-9803"], _parent_links=[{
                       "id": "Glasgow-9803", "name": "Old Glasgow", "relationship": "father",
                       "status": "unknown", "tree_status": "uncertain",
                   }]),
            person("Glasgow-9801", "James Glasgow", 1825, gender="Male", parent_ids=["Glasgow-9800"]),
            person("Glasgow-9802", "Robert Glasgow", 1827, gender="Male", parent_ids=["Glasgow-9800"]),
            person("Glasgow-9803", "Old Glasgow", 1770, parent_ids=["Glasgow-9805"], _sibling_ids=["Glasgow-9804"]),
            person("Glasgow-9804", "Robert Glasgow", 1768, _sibling_ids=["Glasgow-9803"]),
            person("Glasgow-9805", "James Glasgow", 1745),
        ]
        candidates = {item["id"]: item for item in _potential_parentage(people)["Glasgow-9800"]["candidates"]}
        self.assertIn("uncle/aunt", " ".join(candidates["Glasgow-9804"]["conflicts"]))
        self.assertIn("grandparent rather than parent", " ".join(candidates["Glasgow-9805"]["conflicts"]))
        self.assertEqual(candidates["Glasgow-9804"]["classification"], "conflicting tree generation")
        self.assertEqual(candidates["Glasgow-9805"]["classification"], "conflicting tree generation")

    def test_parent_in_law_is_not_offered_as_a_biological_parent(self):
        def person(profile_id, name, birth, gender, **extra):
            value = {
                "id": profile_id, "alternate_ids": [], "catalogue_id": profile_id.casefold(),
                "html_url": f"/people/{profile_id.casefold()}.html", "name": name,
                "birth_year": birth, "death_year": None, "gender": gender,
                "birth_place": "Killycurragh, County Tyrone, Ireland", "birth_surnames": [name.split()[-1]],
                "current_surnames": [name.split()[-1]], "locations": ["Killycurragh, County Tyrone, Ireland"],
                "parent_ids": [], "spouse_ids": [], "spouse_names": [], "child_ids": [], "child_names": [],
                "_parent_links": [], "_sibling_ids": [], "_sibling_links": [], "sibling_names": [],
                "occupations": [], "_dated_records": [],
            }
            value.update(extra)
            return value

        people = [
            person("Glasgow-9900", "Elizabeth Glasgow", 1863, "Female", spouse_ids=["Glasgow-9901"],
                   child_ids=["Glasgow-9903"]),
            person("Glasgow-9901", "James Glasgow", 1863, "Male", parent_ids=["Glasgow-9902"],
                   _parent_links=[{"id": "Glasgow-9902", "name": "Thomas Glasgow", "relationship": "father", "status": "unknown", "tree_status": "uncertain"}]),
            person("Glasgow-9902", "Thomas Glasgow", 1832, "Male", child_ids=["Glasgow-9901"]),
            person("Glasgow-9903", "Thomas Glasgow", 1893, "Male", parent_ids=["Glasgow-9900", "Glasgow-9901"]),
        ]
        candidates = {item["id"] for item in _potential_parentage(people)["Glasgow-9900"]["candidates"]}
        self.assertNotIn("Glasgow-9902", candidates)

    def test_parentage_handles_precise_records_duplicate_children_and_tree_conflicts(self):
        def person(profile_id, name, birth, gender="Male", place="Glasgow, Lanarkshire, Scotland", **extra):
            value = {
                "id": profile_id, "alternate_ids": [], "catalogue_id": profile_id.casefold(),
                "html_url": f"/people/{profile_id.casefold()}.html", "name": name,
                "birth_year": birth, "death_year": None, "gender": gender,
                "birth_place": place, "birth_surnames": ["Glasgow"],
                "current_surnames": ["Glasgow"], "locations": [place],
                "parent_ids": [], "spouse_ids": [], "spouse_names": [],
                "child_ids": [], "child_names": [], "_parent_links": [],
                "_sibling_ids": [], "_sibling_links": [], "sibling_names": [],
                "occupations": [], "_dated_records": [], "_birth_expression": str(birth),
                "birth_status": "estimated", "_family_links_disclaimed": False,
                "_birth_details_disclaimed": False,
            }
            value.update(extra)
            return value

        precise = [
            person("Glasgow-9100", "John Glasgow", 1648, _birth_expression="1648-07-09",
                   parent_ids=["Glasgow-9101"], _parent_links=[{
                       "id": "Glasgow-9101", "name": "James Glasgow", "relationship": "father",
                       "status": "unknown", "tree_status": "unmarked",
                   }]),
            person("Glasgow-9101", "James Glasgow", 1620),
            person("Glasgow-9102", "Robert Glasgow", 1618),
        ]
        self.assertEqual([], _potential_parentage(precise)["Glasgow-9100"]["candidates"])

        duplicate_child = [
            person("Glasgow-9200", "Robert Glasgow", 1582),
            person("Glasgow-9201", "Ninian Glasgow", 1550,
                   child_ids=["Glasgow-9202"], child_names=["Robert Glasgow"]),
            person("Glasgow-9202", "Robert Glasgow", 1583,
                   parent_ids=["Glasgow-9201"]),
        ]
        duplicate_candidates = {
            item["id"]: item for item in _potential_parentage(duplicate_child)["Glasgow-9200"]["candidates"]
        }
        self.assertEqual("resolve child duplicate first", duplicate_candidates["Glasgow-9201"]["classification"])

        sibling_conflict = [
            person("Glasgow-9300", "Hew Glasgow", 1658,
                   _sibling_ids=["Glasgow-9302"], sibling_names=["John Glasgow"]),
            person("Glasgow-9301", "Robert Glasgow", 1618,
                   child_ids=["Glasgow-9302"], child_names=["John Glasgow"]),
            person("Glasgow-9302", "John Glasgow", 1653,
                   parent_ids=["Glasgow-9301", "Glasgow-9303"], _parent_links=[
                       {"id": "Glasgow-9301", "name": "Robert Glasgow", "relationship": "father"},
                       {"id": "Glasgow-9303", "name": "John Glasgow", "relationship": "father"},
                   ]),
            person("Glasgow-9303", "John Glasgow", 1626),
        ]
        conflict_candidates = {
            item["id"]: item for item in _potential_parentage(sibling_conflict)["Glasgow-9300"]["candidates"]
        }
        self.assertEqual(
            "resolve sibling tree conflict first", conflict_candidates["Glasgow-9301"]["classification"]
        )
        self.assertIn("competing same-role parents", " ".join(conflict_candidates["Glasgow-9301"]["conflicts"]))

    def test_parentage_uses_contemporaneous_household_conflicts_and_profile_cautions(self):
        flags = _profile_assessment_flags({"wikitree_evidence": [{
            "biography_text": "This is a research placeholder. His birth, parentage, family and death have not been established."
        }]})
        self.assertTrue(flags["_structural_placeholder"])
        self.assertTrue(flags["_family_links_disclaimed"])
        self.assertTrue(flags["_birth_details_disclaimed"])

        tree_flags = _profile_assessment_flags({"wikitree_evidence": [{"sources": [{
            "citation": "Ancestry user-submitted family tree",
            "url": "https://www.ancestry.co.uk/family-tree/person/tree/1/person/2/facts",
        }]}]})
        self.assertTrue(tree_flags["_profile_sources_tree_only"])
        mixed_flags = _profile_assessment_flags({"wikitree_evidence": [{"sources": [
            {"citation": "Ancestry user-submitted family tree"},
            {"citation": "Scotland parish register baptism index"},
        ]}]})
        self.assertFalse(mixed_flags["_profile_sources_tree_only"])

        def person(profile_id, name, birth, place, **extra):
            value = {
                "id": profile_id, "alternate_ids": [], "catalogue_id": profile_id.casefold(),
                "html_url": f"/people/{profile_id.casefold()}.html", "name": name,
                "birth_year": birth, "death_year": None, "gender": "Male",
                "birth_place": place, "birth_surnames": ["Glasgow"],
                "current_surnames": ["Glasgow"], "locations": [place],
                "parent_ids": [], "spouse_ids": [], "spouse_names": [],
                "child_ids": [], "child_names": [], "_parent_links": [],
                "_sibling_ids": [], "_sibling_links": [], "sibling_names": [],
                "occupations": [], "_dated_records": [], "_birth_expression": str(birth),
                "birth_status": "estimated", "_family_links_disclaimed": False,
                "_birth_details_disclaimed": False,
            }
            value.update(extra)
            return value

        people = [
            person("Glasgow-9400", "Andrew Glasgow", 1685, "Kirknewton, Midlothian, Scotland"),
            person("Glasgow-9401", "John Glasgow", 1661, "Edinburgh, Midlothian, Scotland",
                   child_ids=["Glasgow-9402"], child_names=["George Glasgow"]),
            person("Glasgow-9402", "George Glasgow", 1687, "Kilwinning, Ayrshire, Scotland",
                   parent_ids=["Glasgow-9401"]),
        ]
        candidate = next(
            item for item in _potential_parentage(people)["Glasgow-9400"]["candidates"]
            if item["id"] == "Glasgow-9401"
        )
        self.assertIn("no contemporaneous child is indexed", " ".join(candidate["conflicts"]))

        placeholder = person(
            "Glasgow-9410", "Unknown Glasgow", 1740, "Inishrush, County Londonderry, Ireland",
            _structural_placeholder=True,
        )
        self.assertEqual([], _potential_parentage([placeholder, *people])["Glasgow-9410"]["candidates"])

        bridge_people = [
            person("Glasgow-9411", "Robert Glasgow", 1710, "County Antrim, Ireland",
                   child_ids=["Glasgow-9412"], child_names=["Unknown Glasgow"]),
            person("Glasgow-9412", "Unknown Glasgow", 1740, "Inishrush, County Londonderry, Ireland",
                   child_ids=["Glasgow-9413"], child_names=["Adam Glasgow"],
                   _structural_placeholder=True),
            person("Glasgow-9413", "Adam Glasgow", 1758, "Inishrush, County Londonderry, Ireland"),
        ]
        bridge_candidate = next(
            item for item in _potential_parentage(bridge_people)["Glasgow-9413"]["candidates"]
            if item["id"] == "Glasgow-9411"
        )
        self.assertNotIn("shared descendants", " ".join(bridge_candidate["reasons"]))

        circular_people = [
            person("Glasgow-9420", "Unknown Glasgow", 1740, "Inishrush, County Londonderry, Ireland",
                   _sibling_ids=["Glasgow-9422"],
                   _sibling_links=[{"id": "Glasgow-9422", "status": "possible", "tree_relationship": False}]),
            person("Glasgow-9421", "James Glasgow", 1720, "Moneymore, County Londonderry, Ireland",
                   child_ids=["Glasgow-9422"], child_names=["Arthur Glasgow"]),
            person("Glasgow-9422", "Arthur Glasgow", 1750, "Moneymore, County Londonderry, Ireland",
                   parent_ids=["Glasgow-9421"]),
        ]
        circular_candidate = next(
            item for item in _potential_parentage(circular_people)["Glasgow-9420"]["candidates"]
            if item["id"] == "Glasgow-9421"
        )
        self.assertNotIn("exact subject sibling", " ".join(circular_candidate["reasons"]))
        self.assertIn("cannot be recycled", " ".join(circular_candidate["conflicts"]))

    def test_unassessed_competing_parent_and_broad_area_prevent_strong_classification(self):
        def person(profile_id, name, birth, **extra):
            value = {
                "id": profile_id, "alternate_ids": [], "catalogue_id": profile_id.casefold(),
                "html_url": f"/people/{profile_id.casefold()}.html", "name": name,
                "birth_year": birth, "death_year": None, "gender": "Male",
                "birth_place": "County Antrim, Ireland", "birth_surnames": ["Glasgow"],
                "current_surnames": ["Glasgow"], "locations": ["County Antrim, Ireland"],
                "parent_ids": [], "spouse_ids": [], "spouse_names": [], "child_ids": [], "child_names": [],
                "_parent_links": [], "_sibling_ids": [], "_sibling_links": [], "sibling_names": [],
                "occupations": [], "_dated_records": [],
            }
            value.update(extra)
            return value

        people = [
            person("Glasgow-9910", "James Glasgow", 1840, parent_ids=["Glasgow-9911"],
                   _parent_links=[{"id": "Glasgow-9911", "name": "David Glasgow", "relationship": "father", "status": "unknown", "tree_status": "unmarked"}],
                   child_ids=["Glasgow-9913"]),
            person("Glasgow-9911", "David Glasgow", 1810),
            person("Glasgow-9912", "James Glasgow", 1805, child_names=["John Glasgow", "Mary Glasgow", "Robert Glasgow"]),
            person("Glasgow-9913", "James Glasgow", 1865, parent_ids=["Glasgow-9910"]),
        ]
        candidate = next(
            item for item in _potential_parentage(people)["Glasgow-9910"]["candidates"]
            if item["id"] == "Glasgow-9912"
        )
        self.assertEqual(candidate["classification"], "competing linked parent")
        self.assertIn("evidence is unassessed", " ".join(candidate["conflicts"]))
        self.assertIn("not a locality match", " ".join(candidate["reasons"]))
        self.assertNotIn("recorded siblings", " ".join(candidate["reasons"]))

    def test_public_discovery_files(self):
        robots = (WEB / "robots.txt").read_text(encoding="utf-8")
        self.assertIn("OAI-SearchBot", robots)
        self.assertIn("Sitemap: https://glasgow.phenotype.dev/sitemap.xml", robots)
        sitemap = (WEB / "sitemap.xml").read_text(encoding="utf-8")
        self.assertIn("/catalogue", sitemap)
        self.assertIn("/candidate-matches", sitemap)
        self.assertIn("/people/glasgow-3903.html", sitemap)
        self.assertNotIn("/people/glasgow-933.html", sitemap)
        self.assertGreater(len(re.findall(r"<url>", sitemap)), 4_000)
        self.assertIn("People CSV", (WEB / "llms.txt").read_text(encoding="utf-8"))
        self.assertIn("WikiTree profile evidence JSON", (WEB / "llms.txt").read_text(encoding="utf-8"))
        headers = (WEB / "_headers").read_text(encoding="utf-8")
        self.assertIn("/people/*.json", headers)
        self.assertIn("Content-Type: application/json; charset=utf-8", headers)
        self.assertIn("Content-Type: text/csv; charset=utf-8", headers)
        self.assertIn("Content-Type: text/plain; charset=utf-8", headers)
        self.assertIn("Content-Type: text/html; charset=utf-8", headers)
        schema = json.loads((WEB / "data" / "schema" / "person.schema.json").read_text(encoding="utf-8"))
        self.assertEqual(schema["properties"]["schema_version"]["const"], "1.0")
        evidence = json.loads((WEB / "data" / "wikitree-profile-evidence.json").read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(evidence["profiles"]), 4_000)
        self.assertFalse(evidence["failures"])
        self.assertIn("Glasgow-3961", evidence["profiles"])
        bearers = (WEB / "people" / "early-bearers.html").read_text(encoding="utf-8")
        self.assertIn("Roger de Glasgu", bearers)
        self.assertIn("John de Glasgow alias Smith", bearers)
        self.assertTrue((WEB / "catalogue.html").exists())
        self.assertFalse((WEB / "people" / "glasgow-933.html").exists())
        self.assertIn('name="robots" content="noindex,follow"', (WEB / "map" / "index.html").read_text(encoding="utf-8"))

    def test_public_records_places_comparison_and_status(self):
        health = json.loads((WEB / "health.json").read_text(encoding="utf-8"))
        records = json.loads((WEB / "data" / "records-index.json").read_text(encoding="utf-8"))
        places = json.loads((WEB / "data" / "places-index.json").read_text(encoding="utf-8"))
        self.assertEqual(health["status"], "ok")
        self.assertEqual(health["counts"]["records"], len(records))
        self.assertEqual(health["counts"]["places"], len(places))
        self.assertGreater(health["counts"]["substantive_findings_files"], 0)
        self.assertGreater(health["counts"]["possible_duplicate_comparisons"], 0)
        self.assertTrue(all((WEB / place["url"].lstrip("/")).exists() for place in places))
        for page, marker in (
            ("records/index.html", "Research records"),
            ("places/index.html", "Research places"),
            ("compare.html", "Compare two people"),
            ("candidate-matches.html", "Strong candidate matches"),
            ("feedback.html", "Report a correction"),
            ("changes.html", "Catalogue change log"),
            ("status.html", "Catalogue status"),
        ):
            self.assertIn(marker, (WEB / page).read_text(encoding="utf-8"))
        catalogue = (WEB / "catalogue.html").read_text(encoding="utf-8")
        self.assertIn("Profiles with strong candidate matches", catalogue)
        self.assertIn('href="candidate-matches.html"', catalogue)
        candidate_worklist = (WEB / "candidate-matches.html").read_text(encoding="utf-8")
        self.assertIn("Potential parentage", candidate_worklist)
        self.assertIn("Possible duplicates", candidate_worklist)
        self.assertIn("score-pill", candidate_worklist)
        self.assertIn('class="match-clue-list"', candidate_worklist)
        self.assertIn('class="match-clue-high"', candidate_worklist)
        self.assertIn('class="match-clue-medium"', candidate_worklist)
        self.assertIn('class="match-clue-context"', candidate_worklist)
        self.assertIn('class="match-clue-label">Strong', candidate_worklist)
        self.assertIn('id="candidate-max-year"', candidate_worklist)
        self.assertIn('id="candidate-min-score"', candidate_worklist)
        self.assertIn('id="candidate-min-score" type="number" min="0"', candidate_worklist)
        self.assertIn('id="candidate-parent-role"', candidate_worklist)
        self.assertIn('value="father">Fathers only', candidate_worklist)
        self.assertIn('id="candidate-location"', candidate_worklist)
        self.assertIn('id="candidate-males-only"', candidate_worklist)
        self.assertIn('data-subject-gender="Male"', candidate_worklist)
        self.assertIn('data-candidate-location="', candidate_worklist)
        self.assertIn("maxYear", candidate_worklist)
        self.assertIn("minScore", candidate_worklist)
        self.assertIn("parentRole", candidate_worklist)
        self.assertIn("candidateLocation", candidate_worklist)
        self.assertIn("malesOnly", candidate_worklist)
        self.assertIn('data-subject-year="', candidate_worklist)
        self.assertIn('data-candidate-year="', candidate_worklist)
        self.assertIn('data-parent-role="father"', candidate_worklist)
        self.assertIn("lower scores reveal weaker leads", candidate_worklist)
        self.assertGreater(candidate_worklist.count('data-match-kind="parent"'), 1000)
        self.assertIn("Weak Lead", candidate_worklist)
        self.assertIn("Moderate Lead", candidate_worklist)
        self.assertGreater(candidate_worklist.count('data-match-kind="parent"'), 50)
        person_html = (WEB / "people" / "glasgow-951.html").read_text(encoding="utf-8")
        for marker in ("Identity &amp; family", "Life and record timeline", "Evidence assessment", "Research questions"):
            self.assertIn(marker, person_html)
        self.assertIn("catalogue:zero-results", (WEB / "records" / "search.js").read_text(encoding="utf-8"))
        compare_html = (WEB / "compare.html").read_text(encoding="utf-8")
        compare_js = (WEB / "people" / "compare.js").read_text(encoding="utf-8")
        compare_index = (WEB / "data" / "compare-index.js").read_text(encoding="utf-8")
        self.assertIn("Shared places", compare_js)
        self.assertIn("window.glasgowCompareIndex", compare_js)
        self.assertIn("window.glasgowCompareDossiers", compare_js)
        self.assertIn("The comparison index is not ready.", compare_js)
        self.assertIn("bundled comparison data", compare_js)
        self.assertNotIn("fetch(", compare_js)
        self.assertIn('"id":"Glasgow-3296"', compare_index)
        self.assertIn('window.glasgowCompareDossiers=', compare_index)
        self.assertIn('"glasgow-3296":', compare_index)
        self.assertIn('"open_question_count":', compare_index)
        audit_payload = json.loads((ROOT / "data" / "wikitree" / "catalogue-profile-audit.json").read_text(encoding="utf-8"))
        audit_entries = audit_payload["entries"].values() if isinstance(audit_payload["entries"], dict) else audit_payload["entries"]
        self.assertTrue(all(
            f'"id":"{candidate["profile_id"]}"' in compare_index
            for entry in audit_entries for candidate in entry.get("candidates", [])
        ))
        self.assertLess(compare_html.index("data/compare-index.js"), compare_html.index("people/compare.js"))
        candidate_rows = [row for row in records if row["supporting_source_status"] == "candidate"]
        self.assertTrue(candidate_rows)
        self.assertTrue(all(
            ("year" in row["supporting_source_reason"] or "place" in row["supporting_source_reason"])
            for row in candidate_rows
        ))

    def test_people_csv_is_one_row_per_person(self):
        with (WEB / "data" / "people.csv").open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertGreaterEqual(len(rows), 4_000)
        self.assertEqual(len(rows), len({row["catalogue_id"] for row in rows}))
        james = next(row for row in rows if "Glasgow-3903" in row["profile_ids"])
        self.assertIn("Adam Glasgow", james["father"])
        self.assertIn("Rose (Unknown) Glasgow", james["mother"])
        adam = next(row for row in rows if "Glasgow-3902" in row["profile_ids"])
        self.assertIn("James Glasgow [Glasgow-3903]", adam["children"])
        self.assertTrue(adam["export_version"].startswith("ONT_Glas"))

    def test_every_record_has_provenance_and_source_backlog(self):
        with (WEB / "data" / "records.csv").open(encoding="utf-8-sig", newline="") as handle:
            records = list(csv.DictReader(handle))
        self.assertGreaterEqual(len(records), 4_000)
        self.assertTrue(all(row["source_title"] for row in records))
        self.assertTrue(all(
            not row["source_url"] or _is_external_public_url(row["source_url"])
            for row in records
        ))
        self.assertTrue(all("glasgow.phenotype.dev" not in row["source_url"] for row in records))
        self.assertTrue(all(row["source_type"] and row["source_status"] for row in records))
        self.assertTrue((WEB / "data" / "records.csv.txt").exists())
        with (WEB / "data" / "source-gaps.csv").open(encoding="utf-8-sig", newline="") as handle:
            gaps = list(csv.DictReader(handle))
        self.assertEqual(len(gaps), sum(row["source_type"] != "explicit" for row in records))

    def test_unlinked_glasgow_records_save_original_source_urls(self):
        with (WEB / "map" / "data" / "records.csv").open(encoding="utf-8-sig", newline="") as handle:
            records = list(csv.DictReader(handle))
        unlinked = [
            row for row in records
            if not row["profile_id"] and "glas" in row["person"].casefold()
        ]
        self.assertTrue(unlinked)
        self.assertTrue(all(_is_external_public_url(row["source_url"]) for row in unlinked))
        self.assertTrue(all("glasgow.phenotype.dev" not in row["source_url"] for row in unlinked))

    def test_unlinked_record_ids_never_become_wikitree_urls(self):
        people = json.loads((WEB / "data" / "people.json").read_text(encoding="utf-8"))["people"]
        unlinked = [
            person for person in people
            if not person["profile_ids"] and not person.get("wikitree_free_space_url")
        ]
        self.assertTrue(unlinked)
        for person in unlinked:
            dossier = json.loads(
                (WEB / "people" / f"{person['catalogue_id']}.json").read_text(encoding="utf-8")
            )
            self.assertIsNone(dossier["wikitree_url"], person["catalogue_id"])
            page = (WEB / "people" / f"{person['catalogue_id']}.html").read_text(encoding="utf-8")
            self.assertNotIn(
                f"https://www.wikitree.com/wiki/{person['catalogue_id']}", page,
                person["catalogue_id"],
            )

    def test_public_profile_sources_never_fall_back_to_the_catalogue(self):
        unresolved = _source_for_record({}, "record-example")
        self.assertEqual(unresolved["source_type"], "unresolved")
        self.assertEqual(unresolved["source_url"], "")
        with self.assertRaises(ValueError):
            _source_for_record(
                {
                    "source_title": "Local record",
                    "source_url": "https://glasgow.phenotype.dev/people/record-example.html",
                },
                "record-example",
            )

        james_html = (WEB / "people" / "record-james-glasgow-oritor-gentleman-1826-probate-occurrence.html").read_text(encoding="utf-8")
        draft = james_html.split('<textarea id="profile-draft" class="profile-draft"', 1)[1].split(">", 1)[1].split("</textarea>", 1)[0]
        self.assertNotIn("glasgow.phenotype.dev", draft)
        self.assertIn("apps.proni.gov.uk/ProniNames_IE/SearchPage.aspx", draft)


if __name__ == "__main__":
    unittest.main()
