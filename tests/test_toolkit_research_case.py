"""The Glasgow → workbench translator, on fictional rows."""
import unittest

from genealogy.case import ResearchCase
from genealogy.models import Confidence, Person, Relationship, Sensitivity
from tools.evidence_labels import STATES
from tools.toolkit_research_case import Translator, person_id


def case():
    c = ResearchCase(id="t", title="T")
    for profile in ("Fable-1", "Fable-2", "Fable-3"):
        c.add(Person(id=person_id(profile), sensitivity=Sensitivity.PUBLIC))
    c.add(Relationship(id="one-tree:relationship:Fable-2:father", subject_id=person_id("Fable-2"),
                       object_id=person_id("Fable-1"), kind="parent", sensitivity=Sensitivity.PUBLIC))
    return c


class TranslatorTests(unittest.TestCase):
    # A perspective is keyed by the person whose page shows it and names what
    # the other person is to them: {"Child-1": {"relationship": "father"}}.
    def test_assessment_grades_the_tree_link_and_adds_research_links(self):
        c = case()
        t = Translator(c)
        citations = t.records([{"record_id": "bapt-1", "association": "Invented baptism", "date": "1 May 1801",
                                "place": "Invented Parish", "source_url": "https://example.org/b"}])
        t.assessments([
            {"assertion_id": "a1", "people": ["Fable-1", "Fable-2"], "status": "strongly_supported", "basis": "Baptism names him.",
             "source_ids": ["bapt-1"], "perspectives": {"Fable-1": {"relationship": "son"}, "Fable-2": {"relationship": "father"}}},
            {"assertion_id": "a2", "people": ["Fable-3", "Fable-2"], "status": "possible", "basis": "Same parish.",
             "source_ids": [], "perspectives": {"Fable-3": {"relationship": "mother"}, "Fable-2": {"relationship": "daughter"}}},
            {"assertion_id": "a3", "people": ["Fable-1", "record-x"], "status": "proved", "perspectives": {}},
        ], [{"assertion_id": "a1", "percent": 85}], citations)
        tree = next(r for r in c.records("Relationship") if r.id == "one-tree:relationship:Fable-2:father")
        self.assertEqual((Confidence.PROBABLE, "strongly_supported", 85), (tree.confidence, tree.grade, tree.estimate))
        self.assertEqual(["glasgow:claim:a1"], tree.claim_ids)
        self.assertEqual("strongly_supported", c.records("Claim")[0].grade)
        added = next(r for r in c.records("Relationship") if r.id == "glasgow:relationship:a2")
        self.assertEqual((person_id("Fable-3"), person_id("Fable-2"), "parent"), (added.subject_id, added.object_id, added.kind))
        self.assertEqual((Confidence.POSSIBLE, "possible"), (added.confidence, added.grade))
        self.assertEqual(1, t.gaps["assessments naming a person who is not public"])
        # Only the grades in use are defined, with Glasgow's own wording.
        self.assertEqual(["strongly_supported", "possible"], list(t.grades()))
        self.assertEqual({"label": STATES["strongly_supported"]["label"], "meaning": STATES["strongly_supported"]["meaning"],
                          "confidence": "probable"}, t.grades()["strongly_supported"])

    def test_disproved_assessments_use_the_contradicted_grade(self):
        c = case()
        t = Translator(c)
        t.assessments([{"assertion_id": "a1", "people": ["Fable-1", "Fable-2"], "status": "disproved", "basis": "Dates cannot fit.",
                        "source_ids": [], "perspectives": {"Fable-1": {"relationship": "son"}, "Fable-2": {"relationship": "father"}}}], [], {})
        tree = next(r for r in c.records("Relationship") if r.id == "one-tree:relationship:Fable-2:father")
        self.assertEqual((Confidence.DISPROVED, "contradicted"), (tree.confidence, tree.grade))

    def test_record_readings_become_citation_abstracts_unless_they_name_a_withheld_profile(self):
        c = case()
        t = Translator(c, private=lambda text: "Hidden-9" in str(text))
        t.records([{"record_id": "r1", "association": "Invented baptism", "note": "Entry 7  names Ada,\n daughter of Bram."},
                   {"record_id": "r2", "association": "Invented letter", "note": "Mentions Hidden-9."}])
        abstracts = {r.id: r.abstract for r in c.records("Citation")}
        self.assertEqual("Entry 7 names Ada, daughter of Bram.", abstracts["glasgow:citation:r1"])
        self.assertIsNone(abstracts["glasgow:citation:r2"])
        self.assertEqual(1, t.report["record readings carried as citation abstracts"])
        self.assertEqual(1, t.gaps["record readings naming a withheld profile, left out"])

    def test_notes_keep_known_people_as_references_and_flatten_the_rest(self):
        t = Translator(case())
        text = t.markdown("<!-- private --> See [[Fable-1|Ada]], [[Nobody-9]], [[Category:Fable Name Study]], [[1]], "
                          "[a file](../Fable-1/notes.md) and [a record](https://example.org/r).\n| a | b |\n|---|---|\n| 1 | 2 |\n")
        self.assertIn("[[one-tree:person:Fable-1|Ada]]", text)
        self.assertIn("Nobody-9", text)
        self.assertIn("Category:Fable Name Study", text)
        self.assertNotIn("[[1]]", text)
        self.assertIn("a file", text)
        self.assertNotIn("notes.md", text)
        self.assertIn("[a record](https://example.org/r)", text)
        self.assertNotIn("private", text)
        self.assertEqual(1, t.report["tables in research notes"])

    def test_findings_link_known_people_and_keep_their_limits(self):
        c = case()
        t = Translator(c)
        t.findings([{"id": "f1", "found_on": "2026-10-01", "kind": "vital", "status": "qualified", "finding": "Ada was baptised.",
                     "qualification": "The register is a copy.", "people": [{"id": "Fable-1"}, {"id": "record-x"}],
                     "sources": [{"title": "Register", "url": "https://example.org"}]},
                    {"id": "f2", "found_on": "2026-10-02", "kind": "record", "status": "confirmed", "finding": "A record.",
                     "people": [{"id": "record-y"}], "sources": []}])
        finding = c.records("Finding")[0]
        self.assertEqual([person_id("Fable-1")], finding.related_ids)
        self.assertEqual(("qualified", "2026-10-01"), (finding.status, finding.recorded_on))
        self.assertEqual(("Ada was baptised.", "The register is a copy.", "vital"), (finding.conclusion, finding.limitations, finding.kind))
        self.assertEqual(1, len(finding.citation_ids))
        self.assertEqual("https://example.org", next(s for s in c.records("Source") if s.id.startswith("glasgow:source:url:")).url)
        self.assertEqual(1, len(c.records("Finding")))

    def test_text_naming_a_withheld_profile_is_never_carried(self):
        c = case()
        t = Translator(c, private=lambda text: "Hidden-9" in str(text))
        body = t.markdown("Ada's line is public.\n\nShe is an ancestor of [H (Hidden-9)](https://www.wikitree.com/wiki/Hidden-9).\n\nMore.")
        self.assertNotIn("Hidden-9", body)
        self.assertIn("Private family details withheld.", body)
        self.assertIn("Ada's line is public.", body)
        t.findings([{"id": "f1", "found_on": "2026-10-01", "status": "confirmed", "finding": "Hidden-9 is her grandson.",
                     "people": [{"id": "Fable-1"}], "sources": []}])
        t.records([{"record_id": "r1", "association": "Letter from Hidden-9"}])
        self.assertEqual([], c.records("Finding"))
        self.assertEqual([], [r for r in c.records("Source") if "Hidden-9" in r.title])
        self.assertEqual(1, t.gaps["findings naming a withheld profile"])

    def test_catalogue_people_join_the_case_with_their_aliases_and_family(self):
        c = case()
        t = Translator(c)
        t.catalogue([
            {"catalogue_id": "fable-1", "profile_ids": ["Fable-1", "Fable-1a"], "likely_living": False, "name": "Ada"},
            {"catalogue_id": "record-bea", "profile_ids": [], "likely_living": False, "name": "Bea Fable",
             "last_names_at_birth": ["Fable"], "birth": "c. 1790", "birth_location": "Invented Parish", "death": "Date not established",
             "father": [{"id": "Fable-1a"}], "mother": [{"id": "Hidden-1", "withheld": True}], "spouses": [{"id": "Fable-3"}]},
            {"catalogue_id": "living-1", "profile_ids": ["Living-1"], "likely_living": True, "name": "Someone"},
        ])
        bea = person_id("record-bea")
        self.assertEqual(bea, t.pid("RECORD-BEA"))
        self.assertEqual(person_id("Fable-1"), t.pid("Fable-1a"))
        self.assertFalse(t.known("Living-1"))
        person = next(p for p in c.records("Person") if p.id == bea)
        self.assertEqual(["Bea Fable"], [n.value for n in person.names])
        events = {e.kind: e for e in c.records("Event") if bea in e.participant_ids}
        self.assertEqual(["birth"], sorted(events))
        self.assertEqual("c. 1790", events["birth"].date)
        links = {(r.kind, r.subject_id, r.object_id) for r in c.records("Relationship")}
        self.assertIn(("parent", bea, person_id("Fable-1")), links)
        self.assertIn(("spouse", bea, person_id("Fable-3")), links)
        self.assertFalse(any("Hidden-1" in r.object_id for r in c.records("Relationship")))


if __name__ == "__main__":
    unittest.main()
