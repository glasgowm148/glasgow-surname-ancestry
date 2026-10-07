import importlib.util
import json
from pathlib import Path
import re
import unittest

from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[1]
REGIONS = [
    "early-ireland", "scottish-families", "north-american-families",
    "australasian-families", "english-welsh-families", "other-family-places",
]


def module():
    spec = importlib.util.spec_from_file_location(
        "build_regional_study_maps", ROOT / "tools/build_regional_study_maps.py"
    )
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def directory_module():
    spec = importlib.util.spec_from_file_location(
        "build_branches_directory", ROOT / "tools/build_branches_directory.py"
    )
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


class RegionalStudyMapTests(unittest.TestCase):
    def test_assign_area_requires_named_area_and_respects_country(self):
        helper = module()
        def feature(name, country, ident):
            return {"properties": {"name": name, "country": country, "id": ident, "kind": "state"},
                    "geometry": {"type": "Polygon", "coordinates": []}}
        areas = [feature("Queensland", "au", "au-qld"), feature("Auckland", "nz", "nz-akl")]
        inside = lambda *_: True
        base = {"longitude": "153", "latitude": "-27", "record_precision": "Geocoded profile locality"}
        self.assertEqual("au-qld", helper.assign_area({**base, "region": "Australia", "record_location": "Queensland"}, areas, inside))
        self.assertIsNone(helper.assign_area({**base, "region": "Australia", "record_location": "Auckland"}, areas, lambda *_: False))
        self.assertIsNone(helper.assign_area({**base, "region": "Australia", "record_location": "England, United Kingdom"}, areas, inside))
        self.assertIsNone(helper.assign_area({**base, "region": "Australia", "record_location": "Queensland", "record_precision": "inferred location"}, areas, inside))
        states = [feature("Pennsylvania", "us", "us-pa"), feature("Kansas", "us", "us-ks")]
        fallback = {**base, "region": "United States", "longitude": "-98", "latitude": "39",
                    "record_precision": "Country-centre fallback for profile locality"}
        self.assertEqual("us-pa", helper.assign_area({**fallback, "record_location": "Pennsylvania, United States"}, states, inside))
        self.assertIsNone(helper.assign_area({**fallback, "record_location": "United States"}, states, inside))
        names = [feature("Washington", "us", "us-wa"), feature("Louisiana", "us", "us-la"),
                 feature("Virginia", "us", "us-va"), feature("West Virginia", "us", "us-wv")]
        self.assertEqual('us-la', helper.assign_area({**fallback, 'record_location': 'Washington, Louisiana, United States'}, names, inside))
        self.assertEqual('us-wv', helper.assign_area({**fallback, 'record_location': 'Wheeling, West Virginia, United States'}, names, inside))
        counties = [feature("Leicestershire", "gb", "uk-leics")]
        self.assertIsNone(helper.assign_area({**base, "region": "England", "record_location": "England, United Kingdom"}, counties, inside))

    def test_render_map_shapes_and_list_are_ranked_and_region_specific(self):
        helper = directory_module()
        feature = {"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 0]]]},
                   "properties": {"id": "qld", "country": "au", "label": "Queensland", "priority": 1,
                                  "studies": ["records-qld"], "why": "coverage", "parishes": ["Queensland"],
                                  "metrics": {"people": 1, "documented": 1, "leads": 0, "sourced": 1, "records": 1, "dossiers": 1}}}
        group = {"id": "records-qld", "url": "/records/?branch=australasian-families&q=Queensland",
                 "label": "Records in Queensland", "status": "Regional record coverage", "tier": "study", "regions": ["australasian-families"]}
        soup = BeautifulSoup(helper.render_study_map([group], [feature], [], label="Australia & New Zealand", region_id="australasian-families", overseas=False), "html.parser")
        shapes = soup.select("a.bd-territory[data-territory]")
        items = soup.select(".bd-priority-item[data-territory]")
        self.assertEqual([x["data-territory"] for x in shapes], [x["data-territory"] for x in items])
        self.assertEqual(["1"], [x.select_one("text").get_text() for x in shapes])
        self.assertEqual("australasian-families", soup.select_one("svg[data-region]")["data-region"])
        self.assertIn("Australia & New Zealand", soup.select_one("svg")["aria-label"])
        self.assertIn("Queensland", shapes[0]["aria-label"])

    def test_generated_regional_pages_have_complete_map_contract(self):
        for rid in REGIONS:
            with self.subTest(region=rid):
                path = ROOT / "www/branches" / rid / "index.html"
                soup = BeautifulSoup(path.read_text(), "html.parser")
                maps = soup.select("section#study-map")
                self.assertEqual(1, len(maps))
                self.assertEqual(rid, maps[0].select_one("svg[data-region]")["data-region"])
                shapes = maps[0].select("a.bd-territory[data-territory]")
                items = maps[0].select(".bd-priority-item[data-territory]")
                self.assertTrue(shapes)
                self.assertEqual([x["data-territory"] for x in shapes], [x["data-territory"] for x in items])
                self.assertEqual([str(i) for i in range(1, len(shapes) + 1)], [x.select_one("text").get_text() for x in shapes])
                self.assertEqual(1, len(soup.select('link[href^="/assets/research/branches-directory.css"]')))
                self.assertEqual(1, len(soup.select('script[src^="/assets/research/branches-directory.js"]')))
                for link in maps[0].select("a[href]"):
                    href = link["href"].split("?", 1)[0]
                    if href.startswith("/branches/"):
                        self.assertTrue((ROOT / "www" / href.strip("/") / "index.html").exists(), href)
                    elif href.startswith("/records/"):
                        self.assertTrue((ROOT / "www/records/index.html").exists(), href)
                self.assertIsNotNone(soup.select_one("h1"))
                children = soup.main.find_all(recursive=False)
                self.assertEqual('study-map', children[1].get('id'), rid)

    def test_other_page_excludes_known_core_regions(self):
        metadata = json.loads((ROOT / "www/assets/research/regional-study-maps.json").read_text())
        countries = {area['name'] for area in metadata['other-family-places']['areas']}
        self.assertFalse(countries & module().CORE_COUNTRIES)
        for region in ['north-american-families', 'australasian-families', 'english-welsh-families', 'other-family-places']:
            for area in metadata[region]['areas']:
                self.assertIn('documentary records', area['metrics']['evidence_text'])
                # Reader wording since lane I8 (was "unreviewed profile leads"); it reaches the JSON on the next map build.
                self.assertTrue(any(words in area['metrics']['evidence_text'] for words in
                                    ('from the family tree, not yet checked against records', 'unreviewed profile leads')))


if __name__ == "__main__":
    unittest.main()
