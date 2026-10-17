"""Captured parent lists have names, not explicit father/mother roles."""
import unittest

from tools.build_research_catalog import _captured_parent_relations, _merge_captured_parents


def capture(father=9, mother=8, parents=()):
    return {"profile_fields": {"Name": "Child-1", "Id": 1, "Father": father,
            "Mother": mother, "DataStatus": {"Father": "20", "Mother": "10"},
            "Privacy": 60, "IsLiving": 0}, "relations": {"parents": list(parents)}}


class CapturedParentRelationsTest(unittest.TestCase):
    def resolve(self, child, role="father", numeric=None, target_fields=None):
        people = {"Child-1": child}
        for ident in ("Parent-1", "Parent-2", "Parent-3"):
            people[ident] = {"profile_fields": {"Privacy": 60, "IsLiving": 0}}
        if target_fields:
            people["Parent-1"]["profile_fields"].update(target_fields)
        return _captured_parent_relations(
            ["Child-1"], role, people, numeric or {}, {"Parent-1": {}})

    def test_stale_father_recovered_by_known_mother(self):
        child = capture(parents=[{"id": "Parent-1", "name": "A"}, {"id": "Parent-2"}])
        row, = self.resolve(child, numeric={"8": "Parent-2"})
        self.assertEqual((row["id"], row["numeric_id"], row["data_status"]),
                         ("Parent-1", "9", "20"))
        self.assertFalse(row["outside_export"])

    def test_stale_mother_recovered_by_known_father(self):
        child = capture(parents=[{"id": "Parent-2"}, {"id": "Parent-1"}])
        row, = self.resolve(child, "mother", {"9": "Parent-2"})
        self.assertEqual((row["id"], row["data_status"]), ("Parent-1", "10"))

    def test_single_named_parent_requires_explicit_other_zero(self):
        for role in ("father", "mother"):
            child = capture(father=9 if role == "father" else 0,
                            mother=9 if role == "mother" else 0,
                            parents=[{"id": "Parent-1"}])
            self.assertEqual(self.resolve(child, role)[0]["id"], "Parent-1")
        child["profile_fields"].pop("Father")
        self.assertEqual(self.resolve(child, "mother"), [])

    def test_ambiguous_or_conflicting_snapshots_fail_closed(self):
        for parents, numeric in [
            ([{"id": "Parent-1"}, {"id": "Parent-2"}], {}),
            ([{"id": "Parent-1"}], {"8": "Parent-1"}),
            ([{"id": "Parent-1"}], {"8": "Parent-2"}),
            ([{"id": "Parent-1"}, {"id": "Parent-2"}, {"id": "Parent-3"}], {"8": "Parent-2"}),
        ]:
            with self.subTest(parents=parents, numeric=numeric):
                self.assertEqual(self.resolve(capture(parents=parents), numeric=numeric), [])

    def test_exact_numeric_role_needs_no_named_list(self):
        self.assertEqual(self.resolve(capture(), numeric={"9": "Parent-1"})[0]["id"], "Parent-1")

    def test_subject_privacy_and_living_guard(self):
        for fields in ({"Privacy": 40}, {"IsLiving": 1}, {"BirthDate": "2020-01-01"}):
            child = capture(parents=[{"id": "Parent-1"}])
            child["profile_fields"].update(fields)
            self.assertEqual(self.resolve(child, numeric={"9": "Parent-1"}), [])

    def test_recovery_does_not_publish_withheld_or_living_target(self):
        child = capture(parents=[{"id": "Parent-1"}, {"id": "Parent-2"}])
        for fields in ({"Privacy": 40}, {"IsLiving": 1}):
            self.assertEqual(self.resolve(child, numeric={"8": "Parent-2"}, target_fields=fields), [])
        child["relations"]["parents"][0]["withheld"] = True
        self.assertEqual(self.resolve(child, numeric={"8": "Parent-2"}), [])

    def test_only_matching_unresolved_placeholder_is_replaced(self):
        prior = [{"id": "", "numeric_id": 9}, {"id": "Parent-2"},
                 {"id": "", "numeric_id": 7}]
        parent = {"id": "Parent-1", "numeric_id": "9"}
        merged = _merge_captured_parents(prior, [parent])
        self.assertEqual(merged, [prior[1], prior[2], parent])
        self.assertEqual(_merge_captured_parents(merged, [parent]), merged)
        self.assertEqual(prior[0]["id"], "")
        self.assertEqual(_merge_captured_parents(
            [{"id": "", "numeric_id": 9, "withheld": True}], [parent]),
            [{"id": "", "numeric_id": 9, "withheld": True}])


if __name__ == "__main__":
    unittest.main()
