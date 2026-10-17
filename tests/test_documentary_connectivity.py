import unittest

from tools.branch_connectivity import summarize


def node(ident, *, year=1500, birth_year=None, cohort_member=True):
    return {
        "id": ident, "name": ident, "url": f"/people/{ident}.html",
        "gender": "Male", "year": year, "birth_year": birth_year or year,
        "cohort_member": cohort_member,
    }


class DocumentaryConnectivityTests(unittest.TestCase):
    def test_uncounted_recorded_connector_joins_two_measured_people(self):
        nodes = {
            "child-a": node("child-a"), "child-b": node("child-b"),
            "father": node("father", year=1400, cohort_member=False),
        }
        edges = [
            {"child": "child-a", "father": "father", "status": "probable"},
            {"child": "child-b", "father": "father", "status": "probable"},
        ]
        result = summarize(nodes, edges, 1650)
        self.assertEqual(result["cohort_ids"], ["child-a", "child-b"])
        self.assertEqual(result["population"], 2)
        self.assertEqual(result["largest_component_size"], 2)
        self.assertEqual(result["connected_pairs_percent"], 100)
        self.assertEqual(result["connector_ids"], ["father"])
        supported = summarize(nodes, edges, 1650, view='supported', cohort_ids=result['cohort_ids'])
        self.assertEqual(supported, result)
        confident = summarize(nodes, edges, 1650, view="confident")
        self.assertEqual(confident["population"], 2)
        self.assertEqual(confident["component_count"], 2)
        self.assertEqual(confident["largest_component_size"], 1)
        self.assertFalse(confident.get("connector_ids"))

    def test_fixed_cohort_traverses_uncounted_intermediate_connectors(self):
        nodes = {
            "grand-a": node("grand-a"), "grand-b": node("grand-b"),
            "parent-a": node("parent-a", year=1400, cohort_member=False),
            "parent-b": node("parent-b", year=1400, cohort_member=False),
            "ancestor": node("ancestor", year=1300, cohort_member=False),
        }
        edges = [
            {"child": "grand-a", "father": "parent-a", "status": "uncertain"},
            {"child": "grand-b", "father": "parent-b", "status": "uncertain"},
            {"child": "parent-a", "father": "ancestor", "status": "uncertain"},
            {"child": "parent-b", "father": "ancestor", "status": "uncertain"},
        ]
        result = summarize(nodes, edges, 1650, cohort_ids={"grand-a", "grand-b"})
        self.assertEqual(result["population"], 2)
        self.assertEqual(result["component_count"], 1)
        self.assertEqual(result["connector_ids"], ["ancestor", "parent-a", "parent-b"])

    def test_later_born_ancestor_is_excluded(self):
        nodes = {
            "child-a": node("child-a", year=1600),
            "child-b": node("child-b", year=1600),
            "late-father": node("late-father", year=1700, birth_year=1700, cohort_member=False),
        }
        edges = [
            {"child": "child-a", "father": "late-father", "status": "documented"},
            {"child": "child-b", "father": "late-father", "status": "documented"},
        ]
        result = summarize(nodes, edges, 1650)
        self.assertEqual(result["population"], 2)
        self.assertEqual(result["component_count"], 2)
        self.assertIn("late-father", result["quality"]["later_born_ancestors_excluded"])


if __name__ == "__main__":
    unittest.main()
