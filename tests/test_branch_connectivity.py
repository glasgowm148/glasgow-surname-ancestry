import json, tempfile, unittest
from pathlib import Path
from tools.branch_connectivity import _year, _dated, load_public_nodes, summarize


class T(unittest.TestCase):
    def setUp(self):
        self.t = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(self.t, ignore_errors=True))
        (self.t / "data").mkdir()
        (self.t / "people").mkdir()
        self.rows = []

    def add(self, i, y, s="Example", parents=(), gender="Male", vitals=None, extra=None):
        self.rows.append({"id": i, "name": i, "birth_surnames": [s], "json_url": f"/people/{i.lower()}.json"})
        r = [{"id": p, "relationship": "father", "status": st, "lifecycle": "current"} for p, st in parents]
        d = {
            "id": i,
            "name": i,
            "identity": {"gender": gender},
            "vitals": vitals or {"birth": {"date": str(y), "status": "exact"}},
            "relationships": {"parents": r},
            "evidence": [],
        }
        d.update(extra or {})
        (self.t / "people" / f"{i.lower()}.json").write_text(json.dumps(d))

    def finish(self):
        (self.t / "data/people-index.json").write_text(json.dumps(self.rows))
        return load_public_nodes(self.t, {"Example"})

    def test_year_and_dated(self):
        self.assertEqual(_year("c. 1500"), 1500)
        self.assertEqual(_year("before 1500"), 1500)
        self.assertIsNone(_year("after 1500"))
        self.assertEqual(_year("1500-1510"), 1510)
        self.assertIsNone(_year("0000-00-00"))
        d = {"vitals": {"birth": {"date": "1700"}, "death": {"date": "1800"}}, "evidence": [{"date": "1600"}]}
        self.assertEqual(_dated(d)[0][:2], (1600, "dated evidence"))

    def test_cutoffs_views_roots(self):
        self.add("A", 1600, parents=(("F", "strongly_supported"),), gender="Female")
        self.add("B", 1602, parents=(("F", "uncertain"),), gender="Female")
        self.add("F", 1570)
        n, e, q = self.finish()
        s = summarize(n, e, 1600)
        self.assertEqual((s["population"], s["connected_pairs_percent"]), (2, 100))
        self.assertEqual(s["unattached_multi_child_roots"], [])
        s = summarize(n, e, 1700)
        self.assertEqual((s["population"], s["family_roots"][0]["child_count"]), (3, 2))
        self.assertAlmostEqual(summarize(n, e, 1700, "confident")["connected_pairs_percent"], 33.3333333, 4)

    def test_mother_spouse_alias_and_duplicate(self):
        self.add("A", 1600, parents=(("OLD", "strongly_supported"), ("F", "uncertain")), gender="Female")
        self.add("F", 1570, extra={"alternate_ids": ["OLD"]})
        n, e, q = self.finish()
        self.assertEqual(len(e), 1)
        self.assertEqual(e[0]["father"], "F")
        self.assertFalse(q["multiple_fathers"])

    def test_multiple_fathers_and_late_undated_cycle(self):
        self.add("A", 1600, parents=(("F", "uncertain"), ("G", "confident")))
        self.add("F", 1570)
        self.add("G", 1580)
        n, e, q = self.finish()
        self.assertEqual(e, [])
        self.assertTrue(q["multiple_fathers"])
        self.assertIsInstance(summarize(n, e, 1650)["quality"], dict)

    def test_recursive_closure_future(self):
        self.add("A", 1600, parents=(("F", "uncertain"),))
        self.add("F", 1570, parents=(("U", "uncertain"),))
        self.add("U", None)
        n, e, q = self.finish()
        s = summarize(n, e, 1650)
        self.assertIn("U", s["cohort_ids"])
        self.assertIn("U", s["quality"]["undated_ancestors"])

    def test_cycles_flag(self):
        self.add("A", 1600, parents=(("B", "confident"),))
        self.add("B", 1590, parents=(("A", "confident"),))
        n, e, q = self.finish()
        self.assertTrue(q["cycles"])
        s = summarize(n, e, 1650)
        self.assertEqual(s["edge_count"], 0)

    def test_mother_and_spouse_do_not_join(self):
        self.add(
            "A",
            1600,
            extra={
                "relationships": {
                    "parents": [{"id": "M", "relationship": "mother", "status": "certain"}],
                    "spouses": [{"id": "S", "relationship": "spouse", "status": "certain"}],
                }
            },
        )
        self.add("M", 1570, gender="Female")
        self.add("S", 1580)
        n, e, q = self.finish()
        self.assertEqual(e, [])
        self.assertEqual(summarize(n, e, 1650)["component_count"], 3)

    def test_later_born_father_is_not_ancestor_closure(self):
        self.add("A", 1600, parents=(("F", "uncertain"),))
        self.add("F", 1900)
        n, e, q = self.finish()
        s = summarize(n, e, 1650)
        self.assertEqual(s["cohort_ids"], ["A"])
        self.assertEqual(s["quality"]["later_born_ancestors_excluded"], ["F"])

    def test_father_with_later_death_is_included(self):
        self.add("A", 1840, parents=(("F", "uncertain"),))
        self.add("F", None, vitals={"death": {"date": "1900", "status": "exact"}})
        n, e, q = self.finish()
        self.assertEqual(summarize(n, e, 1850)["population"], 2)

    def test_non_surname_alternative_father_is_not_ignored(self):
        self.add("A", 1600, parents=(("F", "uncertain"), ("G", "uncertain")))
        self.add("F", 1570)
        self.add("G", 1570, s="Other")
        n, e, q = self.finish()
        self.assertEqual(e, [])
        self.assertEqual(q["multiple_fathers"], ["A"])


if __name__ == "__main__":
    unittest.main()
