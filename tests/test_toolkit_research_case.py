"""The Glasgow → workbench translator, on fictional rows."""
import unittest

from genealogy.case import ResearchCase
from genealogy.models import Confidence, Person, Relationship, Sensitivity
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
        self.assertEqual((Confidence.PROBABLE, 85), (tree.confidence, tree.estimate))
        self.assertEqual(["glasgow:claim:a1"], tree.claim_ids)
        added = next(r for r in c.records("Relationship") if r.id == "glasgow:relationship:a2")
        self.assertEqual((person_id("Fable-3"), person_id("Fable-2"), "parent"), (added.subject_id, added.object_id, added.kind))
        self.assertEqual(1, t.gaps["assessments naming a record subject or person outside the tree export"])
        self.assertEqual(1, t.gaps["'strongly_supported' grade shown as probable"])

    def test_notes_keep_known_people_as_references_and_flatten_the_rest(self):
        t = Translator(case())
        text = t.markdown("<!-- private --> See [[Fable-1|Ada]], [[Nobody-9]], [[Category:Fable Name Study]], [[1]], "
                          "[a file](../Fable-1/notes.md) and [a record](https://example.org/r).\n| a | b |\n")
        self.assertIn("[[one-tree:person:Fable-1|Ada]]", text)
        self.assertIn("Nobody-9", text)
        self.assertIn("Category:Fable Name Study", text)
        self.assertNotIn("[[1]]", text)
        self.assertIn("a file", text)
        self.assertNotIn("notes.md", text)
        self.assertIn("[a record](https://example.org/r)", text)
        self.assertNotIn("private", text)
        self.assertEqual(1, t.gaps["note table lines shown as plain text: no table support"])

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
        self.assertIn("Limits: The register is a copy.", finding.conclusion)
        self.assertEqual(1, len(c.records("Finding")))


if __name__ == "__main__":
    unittest.main()
