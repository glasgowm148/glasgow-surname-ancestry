import json
import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
ONE_TREE = ROOT / "www" / "onetree" / "glasgow-one-tree-polished"


class OneTreeOutputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = json.loads((ONE_TREE / "model.json").read_text(encoding="utf-8"))
        cls.people = {person["id"]: person for person in cls.model["people"]}
        spec = importlib.util.spec_from_file_location("onetree_build", ONE_TREE / "build.py")
        cls.build = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.build)

    def test_no_inferred_relationship_edges_are_published(self):
        self.assertEqual(self.model["meta"]["hypotheses"], 0)
        self.assertFalse(any(person.get("edge", {}).get("type") == "hypothesis" for person in self.people.values()))

    def test_every_recorded_display_edge_is_a_structured_parent(self):
        for person in self.people.values():
            edge = person.get("edge", {})
            if edge.get("type") != "recorded":
                continue
            self.assertIn(
                (edge["parent"], edge["role"]),
                {(relation.get("id"), relation.get("role")) for relation in person.get("parents", [])},
                person["id"],
            )

    def test_profile_destinations_are_canonical(self):
        for person in self.people.values():
            if person.get("kind") != "person":
                continue
            slug = person["catalogueId"]
            self.assertRegex(slug, r"^[a-z0-9_-]+$")
            self.assertTrue(
                (ROOT / "www" / "people" / slug / "index.html").exists()
                or (ROOT / "www" / "people" / f"{slug}.html").exists(),
                person["id"],
            )

    def test_family_branches_drive_structure_and_location_drives_colour(self):
        sections = self.model["sections"]
        self.assertFalse(any(section["id"].startswith("@section-") for section in sections))
        self.assertEqual([section["id"] for section in sections if section["id"].startswith("@")], ["@smaller-families"])
        for section in sections:
            if section["id"] == "@smaller-families":
                continue
            self.assertEqual(self.people[section["id"]]["kind"], "person")
            self.assertTrue(section["label"].endswith(" line"))
        palette = {item["id"]: item for item in self.model["locations"]}
        for person in self.people.values():
            if person.get("kind") != "person":
                continue
            location = palette[person["locationRegion"]]
            self.assertEqual(person["locationLabel"], location["label"])
            self.assertEqual(person["locationColor"], location["color"])
            self.assertIn(person["birthLocationRegion"], palette)
            self.assertIn(person["deathLocationRegion"], palette)

    def test_known_previous_bad_guesses_are_corrected(self):
        self.assertEqual(self.people["Glasgow-8"]["edge"]["parent"], "Glasgow-12")
        james = self.people["Glasgow-2738"]
        self.assertEqual(james["edge"]["parent"], "Glasgow-2769")
        self.assertEqual(james["edge"]["status"], "uncertain")
        self.assertNotIn("@james-father", self.people)

    def test_location_classifier_covers_common_unqualified_places(self):
        cases = {
            "Glasgow High Street": "scotland", "Dublin": "ireland", "Larne": "ireland",
            "Maryland": "america", "Harrisburg, PA": "america", "Alabama": "america",
            "Victoria": "oceania", "Cardiff, Wales": "england",
            "Victoria, British Columbia": "canada",
        }
        for place, expected in cases.items():
            self.assertEqual(self.build.location_for(place), expected, place)

    def test_drawing_parent_prefers_stronger_recorded_evidence(self):
        edge = self.people["Glasgow-1433"]["edge"]
        self.assertEqual((edge["parent"], edge["role"], edge["status"]), ("Allison-6866", "mother", "confident"))

    def test_robert_is_the_shared_recorded_parent_of_major_child_offshoots(self):
        for child_id in ("Glasgow-563", "Glasgow-1965", "Glasgow-193", "Glasgow-653", "Glasgow-8"):
            edge = self.people[child_id]["edge"]
            self.assertEqual(edge["parent"], "Glasgow-12", child_id)
            self.assertEqual(edge["type"], "recorded", child_id)

    def test_progressive_view_preserves_component_roots_and_ordered_routes(self):
        template = (ONE_TREE / "template.html").read_text(encoding="utf-8")
        self.assertIn("componentDepth", template)
        self.assertIn("migrationRoute", template)
        self.assertIn("migrationRoutes", template)
        self.assertIn("aggregateBloom", template)
        self.assertIn("family-local location blooms", template)
        self.assertIn("Ordered country trail", template)

    def test_collection_nodes_do_not_claim_kinship(self):
        for person in self.people.values():
            edge = person.get("edge", {})
            if edge.get("type") == "group":
                self.assertEqual(edge.get("semantic"), "collection")
                self.assertIn(edge.get("parent"), self.people)


if __name__ == "__main__":
    unittest.main()
