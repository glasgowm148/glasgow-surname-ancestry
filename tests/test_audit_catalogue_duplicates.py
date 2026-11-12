import unittest
from tools.audit_catalogue_duplicates import scan


def row(ident, name="John Example", association="", **fields):
    return {"catalogue_id": ident, "name": name, "records": [
        {"association": association, "year": "1800", "record_location": "Exampletown",
         "source_url": "https://example.org/record/1"}], **fields}


class DuplicateAuditTests(unittest.TestCase):
    def test_same_name_and_year_do_not_merge(self):
        groups, _ = scan([row("record-a"), row("record-b")])
        self.assertEqual([], groups)

    def test_generic_same_name_source_does_not_define_a_person(self):
        groups, _ = scan([row("record-a", association="John Example — collection"),
                          row("record-b", association="John Example — collection")])
        self.assertEqual([], groups)

    def test_shared_record_parent_and_child_stay_separate(self):
        groups, _ = scan([
            row("record-a", association="John Example is named as father of John Example, christened on 2 Jan 1800 at Exampletown."),
            row("record-b", association="John Example was christened on 2 Jan 1800 at Exampletown, father John Example.")])
        self.assertEqual([], groups)

    def test_same_detailed_event_merges_without_requiring_same_provider_url(self):
        a = "John Example is named as father of Mary Example, christened on 2 Jan 1800 at Exampletown."
        first, second = row("record-a", association=a), row("record-b", association=a)
        second["records"][0]["source_url"] = "https://example.org/record/2"
        groups, _ = scan([first, second])
        self.assertEqual(["record-b"], groups[0]["retired"])

    def test_conflicting_vitals_stop_a_merge(self):
        a = "John Example is named as father of Mary Example, christened on 2 Jan 1800 at Exampletown."
        groups, rejected = scan([row("record-a", association=a, birth="1760"),
                                 row("record-b", association=a, birth="1780")])
        self.assertEqual([], groups)
        self.assertTrue(rejected)

    def test_royal_sussex_cluster_retains_unresolved_identity(self):
        rows = []
        for ident, regiment in [("record-a", "Royal Sussex Regiment"), ("record-b", "R Sussex, Taff")]:
            item = row(ident, name="A E Glasgow")
            item["records"][0].update(source_url="https://www.ancestry.co.uk/search/collections/1262/records/" + ident,
                                      note="Ancestry index transcript; Regiment or Corps: " + regiment)
            rows.append(item)
        groups, _ = scan(rows)
        self.assertIn("does not prove", groups[0]["qualification"])
