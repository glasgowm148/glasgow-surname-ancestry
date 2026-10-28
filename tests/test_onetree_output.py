import json
import importlib.util
from pathlib import Path
import unittest
from urllib.parse import unquote, urlsplit

from bs4 import BeautifulSoup

from tests._generated_data import requires_generated_data


ROOT = Path(__file__).resolve().parents[1]
ONE_TREE = ROOT / "www" / "onetree" / "glasgow-one-tree-polished-3"


@requires_generated_data
class OneTreeOutputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = json.loads((ONE_TREE / "model.json").read_text(encoding="utf-8"))
        cls.people = {person["id"]: person for person in cls.model["people"]}
        spec = importlib.util.spec_from_file_location(
            "onetree_build", ROOT / "tools" / "site_sources" / "onetree" / "build.py"
        )
        cls.build = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.build)

    def test_selected_working_edges_remain_explicitly_uncertain(self):
        edges = [p for p in self.people.values() if p.get('edge', {}).get('type') == 'hypothesis']
        self.assertEqual(self.model['meta']['hypotheses'], len(edges))
        for person in edges:
            edge = person['edge']
            self.assertIn(edge['status'], {'uncertain', 'possible', 'probable'})
            self.assertTrue(any(r.get('hypothesis') and r.get('id') == edge['parent']
                                and r.get('role') == edge['role']
                                and r.get('status') == edge['status']
                                and r.get('assertion_id') for r in person['parents']), person['id'])

    def test_primary_whole_tree_carries_the_same_selected_connections(self):
        from tools.site_payloads import unpack_model
        from tools.stamp_asset_versions import VERSIONED_ASSET, asset_path, content_hash
        packed = ROOT / 'www/assets/research/atlas-model-packed.json'
        primary = unpack_model(json.loads(packed.read_text()))
        people = {p['id']: p for p in primary['people']}
        selected = [p for p in self.people.values() if p.get('edge', {}).get('type') == 'hypothesis']
        self.assertEqual(primary['meta']['hypotheses'], len(selected))
        for person in selected:
            self.assertEqual(people[person['id']]['edge'], person['edge'])
        for person in self.people.values():
            if person.get('documentary'):
                self.assertEqual(people[person['id']], person)
        for relative in ['assets/research/atlas-boot.js', 'onetree/index.html']:
            path = ROOT / 'www' / relative
            for match in VERSIONED_ASSET.finditer(path.read_text()):
                if '/assets/research/atlas' in match['url']:
                    self.assertEqual(match['version'], content_hash(asset_path(ROOT / 'www', path, match['url'])))

    def test_historical_fathers_match_the_current_dossiers_in_both_viewers(self):
        from tools.branch_connectivity import load_public_nodes, summarize
        from tools.site_payloads import unpack_model
        strategy = json.loads((ROOT / 'research/ancestry-connections/strategy.json').read_text())
        nodes, edges, quality = load_public_nodes(ROOT / 'www', set(strategy['variants']))
        cohort = summarize(nodes, edges, 1850)
        scope = set(cohort['cohort_ids'])
        allowed = scope | set(cohort['connector_ids'])
        primary = unpack_model(json.loads((ROOT / 'www/assets/research/atlas-model-packed.json').read_text()))
        for model in [self.model, primary]:
            people = {p['id']: p for p in model['people']}
            self.assertTrue(scope <= people.keys())
            for edge in edges:
                if edge['child'] not in scope or edge['father'] not in allowed:
                    continue
                fathers = [r['id'] for r in people[edge['child']]['parents'] if r.get('role') == 'father' and r.get('id')]
                self.assertEqual(fathers, [edge['father']], edge['child'])
            for ident in scope & set(quality['multiple_fathers']):
                self.assertFalse([r for r in people[ident]['parents'] if r.get('role') == 'father'], ident)

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
            if person.get('documentary'):
                destination = urlsplit(person['catalogueUrl'])
                self.assertFalse(destination.scheme or destination.netloc, person['id'])
                self.assertTrue(destination.path.startswith('/'), person['id'])
                page = ROOT / 'www' / destination.path.strip('/')
                if page.suffix != '.html':
                    page /= 'index.html'
                self.assertTrue(page.is_file(), person['id'])
                if destination.fragment:
                    self.assertIsNotNone(BeautifulSoup(page.read_text(), 'html.parser').find(
                        id=unquote(destination.fragment)), person['id'])
                continue
            slug = person["catalogueId"]
            if slug is None:
                # No published dossier: the Atlas links to WikiTree instead (tools/repair_atlas_destinations.py).
                self.assertFalse((ROOT / "www" / "people" / f"{person['id'].lower()}.html").exists(), person["id"])
                continue
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
        self.assertEqual(james["edge"]["status"], "probable")  # rated 64% on 22 October 2026
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
        # The father was rated proved (95%) on 22 October 2026, which ties the confident
        # mother's rank; a recorded father is drawn ahead of an equally graded mother.
        edge = self.people["Glasgow-1433"]["edge"]
        self.assertEqual((edge["parent"], edge["role"], edge["status"]), ("Glasgow-3375", "father", "proved"))

    def test_robert_is_the_shared_recorded_parent_of_major_child_offshoots(self):
        for child_id in ("Glasgow-563", "Glasgow-1965", "Glasgow-193", "Glasgow-653", "Glasgow-8"):
            edge = self.people[child_id]["edge"]
            self.assertEqual(edge["parent"], "Glasgow-12", child_id)
            self.assertEqual(edge["type"], "recorded", child_id)

    def test_template_embeds_relationship_aware_family_index(self):
        # The linked-families viewer (polished-3) replaced the earlier progressive
        # component view; its layout engine is embedded in the template itself.
        template = (ONE_TREE / "template.html").read_text(encoding="utf-8")
        self.assertEqual(1, template.count("__MODEL__"))
        begin, end = template.find("/* FAMILY_INDEX_BEGIN"), template.find("/* FAMILY_INDEX_END */")
        self.assertGreater(begin, -1)
        self.assertGreater(end, begin)
        index = template[begin:end]
        self.assertIn("function buildFamilyIndex", index)
        for key in ("partners", "coparent", "forestRoots", "componentOf", "ancestors", "descendants"):
            self.assertIn(key, index)
        # Exports never label a spouse attachment as a displayed parent.
        self.assertIn("Layout attachment", template)
        self.assertIn("Layout link type", template)
        self.assertIn("drawMigrationPoints", template)

    def test_collection_nodes_do_not_claim_kinship(self):
        for person in self.people.values():
            edge = person.get("edge", {})
            if edge.get("type") == "group":
                self.assertEqual(edge.get("semantic"), "collection")
                self.assertIn(edge.get("parent"), self.people)


if __name__ == "__main__":
    unittest.main()
