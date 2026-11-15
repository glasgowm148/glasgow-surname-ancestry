import math
import unittest

from bs4 import BeautifulSoup

from tools.statistics_places import places_statistics, render_places_story


class StatisticsPlacesTests(unittest.TestCase):
    def test_counts_use_public_unique_people_and_primary_root_only(self):
        people = [
            {"catalogue_id": "a", "map_key": "Profile-A", "regions": ["Scotland", "Unknown", "Unspecified", ""]},
            {"catalogue_id": "b", "regions": ["Scotland", "Ireland"]},
            {"catalogue_id": "hidden", "likely_living": True, "regions": ["Private"]},
        ]
        root = {"id": "Root-1", "name": "John Glasgow", "catalogued_members": 999}
        index = [
            {"map_key": "profile-a", "family_root": root},
            {"id": "A", "family_root": root},  # alias and repeated row are one person
            {"id": "b", "family_root": root, "family_roots": [{"id": "Other-1"}]},
            {"id": "hidden", "family_root": {"id": "Private-1"}},
            {"id": "external", "family_root": {"id": "External-1"}},
        ]
        summary = '<div class="statistics-summary"><div><strong>1,258</strong><span>Mapped places</span></div></div>'
        counts = places_statistics(people, index, summary)
        self.assertEqual(counts["regions"], 2)
        self.assertEqual(counts["mapped_places"], "1,258")
        self.assertEqual(counts["assigned_people"], 2)
        self.assertEqual(counts["root_count"], 1)
        self.assertEqual(counts["largest_root"], 2)
        self.assertEqual(counts["groups"][0]["name"], "John Glasgow")

    def test_bubbles_have_proportional_area_and_never_overlap(self):
        people, index = [], []
        for root_index, count in enumerate([8, 4, 2, 2, 1, 1, 1, 1, 1]):
            for member in range(count):
                person_id = f"p-{root_index}-{member}"
                people.append({"catalogue_id": person_id})
                index.append({"id": person_id, "family_root": {
                    "id": f"Root-{root_index}", "name": f"Root name {root_index}"}})
        soup = BeautifulSoup(render_places_story(people, index, outline=[]), "html.parser")
        circles = soup.select(".statistics-places-root")
        self.assertEqual(len(circles), 8)
        self.assertAlmostEqual(float(circles[0]["r"]) ** 2 / float(circles[1]["r"]) ** 2, 2, places=5)
        for i, first in enumerate(circles):
            for second in circles[i + 1:]:
                distance = math.hypot(float(first["cx"]) - float(second["cx"]),
                                      float(first["cy"]) - float(second["cy"]))
                self.assertGreater(distance, float(first["r"]) + float(second["r"]))
        self.assertTrue(all(circle["tabindex"] == "0" and circle.find("title") for circle in circles))
        constellation = soup.select_one(".statistics-places-constellation")
        self.assertFalse(constellation.select("line, path"))
        self.assertEqual(soup.select_one(".statistics-places-root-count").text, "8")
        self.assertIn("Only the eight largest groups", soup.text)

    def test_equal_size_groups_and_missing_data_stay_explicit(self):
        people = [{"catalogue_id": f"p-{i}"} for i in range(8)]
        index = [{"id": f"p-{i}", "family_root": {"id": f"Root-{i}"}} for i in range(8)]
        soup = BeautifulSoup(render_places_story(people, index, outline=[]), "html.parser")
        self.assertEqual({float(node["r"]) for node in soup.select(".statistics-places-root")}, {60})
        self.assertIn("Not supplied", soup.select_one(".statistics-story-metrics").text)
        empty = BeautifulSoup(render_places_story([], [], outline=[]), "html.parser")
        self.assertIn("No primary exported-root groups", empty.text)
        self.assertFalse(empty.select(".statistics-places-root"))

    def test_source_names_are_escaped_and_map_semantics_preserved(self):
        person = {"catalogue_id": "a", "records": [{"latitude": 55, "longitude": -3}]}
        name = 'Mary <script>alert("x")</script> Glasgow'
        index = [{"id": "a", "family_root": {"id": 'Root-"1', "name": name}}]
        html = render_places_story([person], index, outline=[])
        soup = BeautifulSoup(html, "html.parser")
        self.assertFalse(soup.select("script"))
        circle = soup.select_one(".statistics-places-root")
        self.assertIn(name, circle["aria-label"])
        self.assertIn("Geographic dot plot", soup.text)
        self.assertIn("not necessarily birthplaces", soup.text)
        self.assertIn("not proved kinship", soup.text)
        self.assertEqual(len(soup.select(".statistics-map-dot")), 1)
