"""Collateral research must never become invented paternal descent."""
from copy import deepcopy
import unittest
from unittest.mock import patch

from tools.site_sources.onetree.build import apply_public_siblings
from tools.sync_ancestry_atlas import overlay_model


class ReviewedSiblingsTests(unittest.TestCase):
    def setUp(self):
        self.people = [dict(id=i, name=i, parents=[], childrenRecorded=[]) for i in ('A-1', 'B-1')]
        self.assessment = dict(assertion_id='brothers', people=['A-1', 'B-1'],
                               publication_status='approved', source_ids=['census', 'marriage'],
                               basis='Niece and named father, with qualified identity.', status='probable',
                               perspectives={i: {'relationship': 'sibling'} for i in ('A-1', 'B-1')})

    def test_reciprocal_siblings_do_not_create_a_parent(self):
        with patch('tools.relationship_probability.probability_for_relationship',
                   return_value={'value': .74, 'label': 'Probable · 74%'}):
            meta = apply_public_siblings(self.people, [self.assessment])
        self.assertEqual(meta['publicSiblingScopeIds'], ['A-1', 'B-1'])
        for person, relative in zip(self.people, self.people[::-1]):
            self.assertEqual(person['parents'], [])
            row, = person['siblings']
            self.assertEqual(row['id'], relative['id'])
            self.assertEqual(row['probability']['value'], .74)
            self.assertEqual(row['statusLabel'], 'Probable · 74%')

    def test_unreviewed_unsourced_alternative_or_one_sided_links_are_not_published(self):
        for update in ({'publication_status': 'pending'}, {'source_ids': []},
                       {'display': 'alternative'}, {'lifecycle': 'superseded'},
                       {'status': 'uncertain'}, {'perspectives': {'A-1': {'relationship': 'sibling'}}}):
            people = deepcopy(self.people)
            people[0]['siblings'] = [{'id': 'stale'}]
            self.assertEqual(apply_public_siblings(people, [{**self.assessment, **update}]),
                             {'publicSiblingScopeIds': []})
            self.assertTrue(all('siblings' not in person for person in people))

    def test_main_tree_sync_is_reversible_and_retains_approved_person_fields(self):
        old = dict(meta={}, sections=[], landmarks=[], people=deepcopy(self.people))
        old['people'][0].update(born=1770, note='Retain the approved identity account')
        fresh = deepcopy(old)
        fresh['people'][0].update(born=1780, note='Short export')
        fresh['meta'].update(date='2026-10-18', **apply_public_siblings(fresh['people'], [self.assessment]))
        out = overlay_model(old, fresh)
        self.assertEqual(out['people'][0]['born'], 1770)
        self.assertEqual(out['people'][0]['note'], 'Retain the approved identity account')
        self.assertEqual(out['people'][0]['siblings'][0]['id'], 'B-1')
        self.assertEqual(out, overlay_model(out, fresh))
        cleared = deepcopy(fresh)
        cleared['meta'].update(apply_public_siblings(cleared['people'], []))
        out = overlay_model(out, cleared)
        self.assertTrue(all('siblings' not in person for person in out['people']))
        self.assertTrue(all(not person['parents'] for person in out['people']))


if __name__ == '__main__':
    unittest.main()
