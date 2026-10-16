import json, tempfile, unittest
from pathlib import Path
from tools.branch_connectivity import _year, _dated, load_public_nodes, summarize, relationship_status


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

    def test_saved_tree_flags_are_used_without_overriding_research(self):
        self.assertEqual(relationship_status({'status':'unknown','tree_status':'confident'}), ('confident','saved_wikitree_flag'))
        self.assertEqual(relationship_status({'status':'unknown','tree_status':'DNA-confirmed'})[0], 'dna_confirmed')
        self.assertEqual(relationship_status({'status':'unknown','tree_status':'unmarked'})[0], 'unmarked')
        self.assertEqual(relationship_status({'status':'unknown'})[0], 'unknown')
        for status in ['uncertain','possible','probable','unmarked','contradicted']:
            self.assertEqual(relationship_status({'status':status,'tree_status':'confident'})[0],status)

    def test_flagged_father_joins_confident_graph_and_retains_provenance(self):
        self.add('Child',1600,extra={'relationships':{'parents':[{'id':'Father','relationship':'father','status':'unknown','tree_status':'confident'}]}})
        self.add('Father',1570)
        nodes,edges,_=self.finish()
        self.assertEqual(summarize(nodes,edges,1650,'confident')['connected_pairs_percent'],100)
        self.assertEqual(edges[0]['assessment_status'],'unknown')
        self.assertEqual(edges[0]['tree_status'],'confident')
        self.assertEqual(edges[0]['status_basis'],'saved_wikitree_flag')

    def test_non_biological_tree_flag_never_joins_a_paternal_graph(self):
        self.add('Child',1600,extra={'relationships':{'parents':[{'id':'Father','relationship':'father','status':'unknown','tree_status':'non-biological'}]}})
        self.add('Father',1570)
        nodes,edges,_=self.finish()
        self.assertEqual(edges,[])
        self.assertEqual(summarize(nodes,edges,1650)['component_count'],2)

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
