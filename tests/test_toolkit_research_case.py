"""The Glasgow → workbench translator, on fictional rows."""
import unittest

from genealogy.case import ResearchCase, validate_case
from genealogy.models import Confidence, ExternalIdentifier, LivingStatus, Name, Person, Place, Relationship, Sensitivity
from tools.evidence_labels import STATES
from tools.toolkit_research_case import Translator, _short, person_id


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

    def test_a_notes_heading_written_as_a_link_is_shown_by_its_words(self):
        import tempfile
        from pathlib import Path
        t = Translator(case())
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory) / "Fable-1"
            folder.mkdir()
            (folder / "findings.md").write_text("# Findings: [Ada Fable (Fable-1)](https://example.org/Fable-1)\n\nLast updated: 2026-09-01\n\n## Birth\n\nSeen.\n", encoding="utf-8")
            t.notes(Path(directory))
        study = next(s for s in t.case.records("Study") if s.id == "glasgow:notes:Fable-1")
        self.assertEqual("Findings: Ada Fable (Fable-1)", study.title)
        self.assertEqual("2026-09-01", study.updated_on)

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

    def test_catalogue_regions_file_places_and_clusters_become_group_studies(self):
        c = case()
        c.add(Place(id="one-tree:place:lantern", name="Lanternby, North Shire, Fableland", sensitivity=Sensitivity.PUBLIC))
        c.add(Place(id="one-tree:place:moss", name="Mossford, Fableland", sensitivity=Sensitivity.PUBLIC))  # filed by its "Fableland" part
        c.add(Place(id="one-tree:place:ridge", name="Ridge, West Shire, Fableland, Old Union", sensitivity=Sensitivity.PUBLIC))  # "Old Union" is split; "Fableland" decides
        c.add(Place(id="one-tree:place:far", name="Farholm", sensitivity=Sensitivity.PUBLIC))  # no part is known
        c.add(Place(id="one-tree:place:words", name="Mossford Fableland.", sensitivity=Sensitivity.PUBLIC))  # no commas: a word decides
        t = Translator(c, private=lambda text: "Hidden-9" in str(text))
        rows = [
            {"catalogue_id": "fable-1", "profile_ids": ["Fable-1"], "likely_living": False, "name": "Ada",
             "clusters": ["Lanternby cluster", "Early Fable records"], "cluster": "Lanternby cluster",
             "records": [{"record_location": "Lanternby,  North Shire, Fableland", "region": "The Fable Isles"},
                         {"record_location": "Lanternby, North Shire, Fableland", "region": "The Fable Isles"},
                         {"record_location": "Lanternby, North Shire, Fableland", "region": "Fableland"}]},
            {"catalogue_id": "fable-2", "profile_ids": ["Fable-2"], "likely_living": False, "name": "Bram", "clusters": ["Lanternby cluster"],
             "regions": ["Old Union"], "birth_location": "Port, Old Union"},
            {"catalogue_id": "fable-2b", "profile_ids": ["Fable-2b"], "likely_living": False, "name": "Cal", "regions": ["The Fable Isles"],
             "birth_location": "Dock, Fableland, Old Union", "death_location": "Quay, Fableland"},
            {"catalogue_id": "living-1", "profile_ids": ["Living-1"], "likely_living": True, "clusters": ["Lanternby cluster"]},
            {"catalogue_id": "fable-3", "profile_ids": ["Fable-3"], "likely_living": False, "clusters": ["Hidden-9 leads"],
             "records": [{"record_location": "Lanternby, North Shire, Fableland", "region": "Lanternby, North Shire, Fableland"}]},
        ]
        t.catalogue(rows)
        t.regions(rows)
        t.groups(rows)
        regions = {p.id: p.region for p in c.records("Place")}
        self.assertEqual("The Fable Isles", regions["one-tree:place:lantern"])  # the region filed most often; a region written as a place is re-filed by its parts
        self.assertEqual("The Fable Isles", regions["one-tree:place:moss"])  # "Fableland" is only ever filed under The Fable Isles
        self.assertEqual("The Fable Isles", regions["one-tree:place:ridge"])  # "Old Union" is split 1:1, so the next part decides
        self.assertIsNone(regions["one-tree:place:far"])
        self.assertEqual("The Fable Isles", regions["one-tree:place:words"])
        studies = {s.id: s for s in c.records("Study") if s.kind == "group"}
        lantern = studies["glasgow:group:" + _short("Lanternby cluster")]
        self.assertEqual(("Lanternby cluster", [person_id("Fable-1"), person_id("Fable-2")], Sensitivity.PUBLIC), (lantern.title, lantern.related_ids, lantern.sensitivity))
        self.assertEqual([person_id("Fable-1")], studies["glasgow:group:" + _short("Early Fable records")].related_ids)
        self.assertEqual(2, len(studies))  # the withheld-profile cluster is left out and counted
        self.assertEqual(1, t.gaps["catalogue groups naming a withheld profile"])
        self.assertEqual([], validate_case(c))

    def test_sibling_assessments_grade_a_symmetric_link_with_reason_and_limitation(self):
        c = case()
        c.add(Relationship(id="one-tree:relationship:sib", subject_id=person_id("Fable-3"), object_id=person_id("Fable-2"),
                           kind="sibling", sensitivity=Sensitivity.PUBLIC))
        t = Translator(c, private=lambda text: "Hidden-9" in str(text))
        citations = t.records([{"record_id": "will-1", "association": "Invented will"}])
        t.assessments([
            {"assertion_id": "s1", "people": ["Fable-2", "Fable-3"], "status": "proved", "basis": "The will names her brother.",
             "limitations": "The will  gives no ages.", "source_ids": ["will-1"],
             "perspectives": {"Fable-2": {"relationship": "sibling"}, "Fable-3": {"relationship": "sibling"}}},
            {"assertion_id": "s2", "people": ["Fable-1", "Fable-2"], "status": "possible", "basis": "Same parish.",
             "limitations": "Hidden-9 is also named.", "source_ids": ["will-1"],
             "perspectives": {"Fable-1": {"relationship": "son"}, "Fable-2": {"relationship": "father"}}},
        ], [], citations)
        sibling = next(r for r in c.records("Relationship") if r.id == "one-tree:relationship:sib")
        self.assertEqual((Confidence.DOCUMENTED, "proved", "The will names her brother."),
                         (sibling.confidence, sibling.grade, sibling.rationale))
        self.assertEqual(1, t.report["assessed sibling relationships"])
        self.assertEqual(2, len(c.records("Relationship")))  # the tree's sibling link, not a second one
        evidence = {e.claim_id: e for e in c.records("Evidence")}
        self.assertEqual("The will gives no ages.", evidence["glasgow:claim:s1"].limitation)
        self.assertIsNone(evidence["glasgow:claim:s2"].limitation)
        self.assertEqual(1, t.gaps["assessment limitations naming a withheld profile, left out"])

    def test_finding_changes_point_at_the_link_and_keep_the_history_consistent(self):
        c = case()
        t = Translator(c)
        t.assessments([{"assertion_id": "a1", "people": ["Fable-1", "Fable-2"], "status": "proved", "basis": "Baptism names him.",
                        "source_ids": [], "perspectives": {"Fable-1": {"relationship": "son"}, "Fable-2": {"relationship": "father"}}}],
                      [], {})
        change = lambda before, after, **extra: {"relationship": "father", "subject": "Bo Fable (Fable-2)", "relative": "Fable-1",
                                                 "before": before, "after": after, "explanation": "Register read.", **extra}
        t.findings([
            {"id": "f1", "found_on": "2026-09-01", "status": "confirmed", "finding": "A first reading.", "people": [{"id": "Fable-2"}],
             "relationship_changes": [change("unmarked", "certain", assessment_after="possible")]},
            {"id": "f2", "found_on": "2026-10-01", "status": "confirmed", "finding": "The original was read.", "people": [{"id": "Fable-2"}],
             "relationship_changes": [change("possible", "certain", assessment_after="proved"),
                                      change("uncertain", "certain"),
                                      change("unmarked", "unknown"),
                                      {**change("unmarked", "certain", assessment_after="proved"), "relative": "Nobody-9"}]},
            {"id": "f3", "found_on": "2026-08-01", "status": "confirmed", "finding": "An older reading.", "people": [{"id": "Fable-2"}],
             "relationship_changes": [change("possible", "certain", assessment_after="strongly_supported")]},
        ])
        changes = {f.id: f.changes for f in c.records("Finding")}
        self.assertEqual([{"record_id": "one-tree:relationship:Fable-2:father", "before": "possible", "after": "proved",
                           "note": "Register read."}], changes["glasgow:finding:f2"])
        self.assertEqual("unknown", changes["glasgow:finding:f1"][0]["before"])
        self.assertEqual(1, len(changes["glasgow:finding:f3"]))  # not the latest, so kept as history
        self.assertEqual(1, t.gaps["finding changes to a state that is not a Glasgow grade ('certain')"])
        self.assertEqual(1, t.gaps["finding changes with no workbench grade on either side"])
        self.assertEqual(1, t.gaps["finding changes to a link with no relationship record"])
        self.assertIn("possible", t.grades())  # a grade used only by a change is defined too

    def test_a_latest_change_that_disagrees_with_the_assessment_is_dropped(self):
        c = case()
        t = Translator(c)
        t.assessments([{"assertion_id": "a1", "people": ["Fable-1", "Fable-2"], "status": "probable", "basis": "Fits.",
                        "source_ids": [], "perspectives": {"Fable-1": {"relationship": "son"}, "Fable-2": {"relationship": "father"}}}],
                      [], {})
        tree = next(r for r in c.records("Relationship") if r.id == "one-tree:relationship:Fable-2:father")
        rows = [{"id": f"f{n}", "found_on": "2026-10-01", "status": "confirmed", "finding": "A reading.", "people": [{"id": "Fable-2"}],
                 "relationship_changes": [{"relationship": "father", "subject_id": "Fable-2", "relative_id": "Fable-1",
                                           "before": "unmarked", "after": "certain", "assessment_after": after}]}
                for n, after in ((1, "probable"), (2, "proved"))]
        t.findings(rows)
        self.assertEqual([1, 0], [len(f.changes) for f in c.records("Finding")])
        self.assertEqual(1, t.gaps["finding changes that disagree with the current assessment"])
        self.assertEqual(("probable", Confidence.PROBABLE), (tree.grade, tree.confidence))  # the assessment is unchanged

    def test_research_tasks_become_questions_and_completed_searches_become_search_records(self):
        import json
        import tempfile
        from pathlib import Path
        c = case()
        t = Translator(c, private=lambda text: "Hidden-9" in str(text))
        with tempfile.TemporaryDirectory() as folder:
            for profile, data in {
                "Fable-1": {"research_tasks": [
                    {"what": "1. Inspect the invented register.", "tests": "Tests the parentage.", "matters": "It would name the father.",
                     "record_target": "Invented register, 1801", "resolves": "An entry naming both parents.", "status": "Archive access required"},
                    {"what": "Read the invented will.", "tests": "Tests the heirs.", "matters": "", "status": "Completed; heirs named"},
                    {"what": "Ask about Hidden-9.", "tests": "", "matters": "", "status": "Open"}],
                    "completed_searches": [{"date": "2026-09-01", "search": "Invented  index,\n1790-1810", "result": " Nothing found. ", "limitation": "Index only;  images not checked."},
                                           {"date": "2026-09-02", "search": "Invented roll", "result": "Only Hidden-9 listed."},
                                           {"date": "September 2026", "search": "Invented census", "result": "Not listed."}]},
                "Nobody-9": {"research_tasks": [{"what": "Find Nobody.", "tests": "", "matters": "", "status": "Open"}],
                             "completed_searches": [{"date": "2026-09-03", "search": "Invented directory", "result": "Nothing."}]},
            }.items():
                (Path(folder) / profile).mkdir()
                (Path(folder) / profile / "presentation.json").write_text(json.dumps(data))
            t.questions(Path(folder))
        questions = {q.id: q for q in c.records("ResearchQuestion")}
        first = questions["glasgow:question:Fable-1:1"]
        self.assertEqual("Inspect the invented register. Why it matters: It would name the father.", first.question)
        self.assertEqual(("An entry naming both parents.", "Invented register, 1801", "open", [person_id("Fable-1")]),
                         (first.resolves, first.next_record, first.status, first.related_ids))
        second = questions["glasgow:question:Fable-1:2"]
        self.assertEqual(("Read the invented will.", "Tests the heirs.", None, "resolved"),
                         (second.question, second.resolves, second.next_record, second.status))
        self.assertEqual(2, len(questions))
        self.assertEqual(1, t.gaps["research questions naming a withheld profile"])
        self.assertEqual(1, t.gaps["research questions about people who are not public"])
        searches = {r.id: r for r in c.records("Search")}
        self.assertEqual(["glasgow:search:Fable-1:1", "glasgow:search:Fable-1:3"], sorted(searches))
        found = searches["glasgow:search:Fable-1:1"]
        self.assertEqual(("Invented index, 1790-1810", "Nothing found.", "2026-09-01", [person_id("Fable-1")], Sensitivity.PUBLIC),
                         (found.search, found.result, found.searched_on, found.related_ids, found.sensitivity))
        self.assertEqual("Index only; images not checked.", found.limitation)
        self.assertIsNone(searches["glasgow:search:Fable-1:3"].searched_on)  # not an ISO date
        self.assertIsNone(searches["glasgow:search:Fable-1:3"].limitation)
        self.assertEqual(1, t.gaps["completed searches naming a withheld profile"])
        self.assertEqual(1, t.gaps["completed searches about people who are not public"])
        self.assertNotIn("completed searches (the workbench has no search record)", t.gaps)
        self.assertEqual([], validate_case(c))

    def test_merged_profiles_become_former_ids_of_public_people(self):
        c = case()
        c.add(Person(id=person_id("Fable-8"), sensitivity=Sensitivity.PRIVATE))
        t = Translator(c, private=lambda text: "Hidden-9" in str(text))
        t.catalogue([{"catalogue_id": "fable-1", "profile_ids": ["Fable-1", "Fable-1a", "Fable-2", "Hidden-9"], "likely_living": False},
                     {"catalogue_id": "fable-8", "profile_ids": ["Fable-8", "Fable-8a"], "likely_living": False}])
        t.former_ids({"Fable-1b": "Fable-1a", "Fable-1c": "Nobody-1"})
        people = {p.id: p for p in c.records("Person")}
        self.assertEqual([person_id("Fable-1a"), person_id("Fable-1b")], people[person_id("Fable-1")].former_ids)
        self.assertEqual([], people[person_id("Fable-8")].former_ids)
        self.assertEqual(1, t.gaps["former profile IDs that are still current records"])
        self.assertEqual(2, t.gaps["former profile IDs of people who are not public"])

    def test_every_tree_person_shows_their_wikitree_id(self):
        c = case()
        c.add(Person(id=person_id("Fable-8"), external_ids=[ExternalIdentifier(system="one-tree:numeric", value="42")], sensitivity=Sensitivity.PRIVATE))
        c.add(Person(id="glasgow:catalogue:fable-9", names=[Name("Nell Fable")], living=LivingStatus.DECEASED, sensitivity=Sensitivity.PUBLIC))
        t = Translator(c, private=lambda text: False)
        t.wikitree_ids()
        t.wikitree_ids()  # a second pass adds nothing
        people = {p.id: p for p in c.records("Person")}
        first = people[person_id("Fable-1")].external_ids[0]
        self.assertEqual(("wikitree", "Fable-1", "https://www.wikitree.com/wiki/Fable-1"), (first.system, first.value, first.url))
        self.assertEqual(["wikitree", "one-tree:numeric"], [i.system for i in people[person_id("Fable-8")].external_ids])
        self.assertEqual([], people["glasgow:catalogue:fable-9"].external_ids)
        self.assertEqual(4, t.report["people with a WikiTree identifier"])  # Fable-1, -2, -3 and -8
        self.assertEqual([], validate_case(c))

    def test_the_config_names_the_surname_the_tree_and_the_grades_used(self):
        import tomllib
        from tools.toolkit_research_case import config_tables
        t = Translator(case(), private=lambda text: False)
        t.used_grades.add("proved")
        config = tomllib.loads("[project]\nname = \"Fictional\"\n" + config_tables(t.grades()))
        self.assertEqual("WikiTree", config["site"]["tree_name"])
        self.assertEqual("Glasgow", config["names"]["surname"])
        self.assertIn("Glasgow", config["names"]["variants"])
        self.assertEqual({"label", "meaning", "confidence"}, set(config["grades"]["proved"]))

    def test_source_qualities_use_the_standard_terms_only_when_clear(self):
        from tools.toolkit_research_case import source_quality, surname_variants
        self.assertEqual(["original", "derivative", "derivative", "derivative", "authored", "authored", None, None, None],
                         [source_quality(v) for v in ("original", "derivative", "published archival transcription",
                                                      "maintained derivative index", "secondary", "tree_only",
                                                      "previously inspected original or published inscription",
                                                      "contemporary source via maintained OCR", None)])
        t = Translator(case())
        t.records([{"record_id": "r1", "association": "Invented index", "source_quality": "parish index transcript"},
                   {"record_id": "r2", "association": "Invented notice", "source_quality": "contemporary source via OCR"}])
        self.assertEqual({"glasgow:citation:r1": "derivative", "glasgow:citation:r2": None},
                         {r.id: r.quality for r in t.case.records("Citation")})
        self.assertEqual(1, t.gaps["source qualities with no clear standard term"])
        variants = surname_variants()
        self.assertEqual(["Glasgow"], list(variants))
        self.assertIn("Glasco", variants["Glasgow"])
        self.assertNotIn("Glasgow", variants["Glasgow"])


if __name__ == "__main__":
    unittest.main()
