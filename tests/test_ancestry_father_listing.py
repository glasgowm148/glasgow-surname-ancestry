import unittest

from tools.build_ancestry_progress import has_named_father, father_listing_counts


class FatherListingTests(unittest.TestCase):
    def dossier(self, **fields):
        return {'relationships': {'parents': [{
            'id':'Example-1', 'name':'John Example', 'relationship':'father', **fields}]}}

    def test_no_father_and_placeholder_are_unknown(self):
        self.assertFalse(has_named_father({}))
        self.assertFalse(has_named_father(self.dossier(name='Unknown Glasgow')))

    def test_grade_and_graph_exclusion_do_not_make_a_named_father_unknown(self):
        self.assertTrue(has_named_father(self.dossier(status='unknown')))
        self.assertTrue(has_named_father(self.dossier(status='uncertain')))
        self.assertTrue(has_named_father(self.dossier(id='Glassfuird-2')))

    def test_unselected_or_rejected_fathers_do_not_fill_the_gap(self):
        for fields in [{'lifecycle': 'alternative'}, {'display': 'alternative'},
                       {'status': 'rejected'}, {'publication_status': 'withheld'}]:
            self.assertFalse(has_named_father(self.dossier(**fields)))

    def test_missing_accounts_are_not_invented_unknown_fathers(self):
        self.assertEqual(father_listing_counts(['a', 'b', 'c'], {'a': True, 'b': False}),
                         dict(unknown_count=1, named_count=1, unavailable_count=1, population=3))


if __name__ == '__main__':
    unittest.main()
