"""Banns-based couple proposals must reach both trees without inventing parentage."""
from copy import deepcopy
import unittest
from unittest.mock import patch

from tools.site_sources.onetree.build import apply_public_spouses, apply_working_hypotheses
from tools.sync_ancestry_atlas import overlay_model
from tools.publish_resolved_dossiers import project_catalogue_spouses


class ReviewedSpousesTests(unittest.TestCase):
    def setUp(self):
        self.people = [dict(id=i, name=i, parents=[], partners=[], childrenRecorded=[])
                       for i in ('A-1', 'record-bride', 'Child-1')]
        self.people[0]['childrenRecorded'] = [dict(id='Child-1', role='child')]
        self.people[2]['parents'] = [dict(id='A-1', role='father', status='unmarked')]
        self.assessment = dict(assertion_id='banns-couple', people=['A-1', 'record-bride'],
            publication_status='approved', allow_new_relationship=True, source_ids=['banns'],
            basis='Same groom name and parish as the later father; intended couple explicit.',
            status='probable', record_scope='Banns only; ceremony and maternity unproved.',
            perspectives={i: dict(relationship='spouse', status_label='Probable intended spouse · 88%')
                          for i in ('A-1', 'record-bride')})

    def sync(self, people, assessments):
        with patch('tools.relationship_probability.probability_for_relationship',
                   return_value={'value': .88, 'label': 'Probable · 88%'}):
            return apply_public_spouses(people, assessments)

    def test_couple_reaches_both_directions_without_a_wedding_or_mother(self):
        before = deepcopy(self.people)
        meta = self.sync(self.people, [self.assessment])
        self.assertEqual(meta['publicSpouseScopeIds'], ['A-1', 'record-bride'])
        self.assertEqual(apply_working_hypotheses(self.people, [self.assessment]), 0)
        for person, relative in zip(self.people[:2], self.people[1::-1]):
            row, = person['partners']
            self.assertEqual(row['id'], relative['id'])
            self.assertEqual(row['probability']['value'], .88)
            self.assertNotIn('marriageDate', row)
            self.assertIn('maternity unproved', row['recordScope'])
        self.assertEqual([p['parents'] for p in self.people], [p['parents'] for p in before])
        self.assertEqual(self.people[1]['childrenRecorded'], [])

    def test_unsupported_alternative_and_one_sided_proposals_are_ignored(self):
        for update in ({'publication_status': 'pending'}, {'source_ids': []},
                       {'allow_new_relationship': False}, {'display': 'alternative'},
                       {'lifecycle': 'superseded'}, {'status': 'excluded'},
                       {'perspectives': {'A-1': {'relationship': 'spouse'}}}):
            people = deepcopy(self.people)
            self.assertEqual(self.sync(people, [{**self.assessment, **update}]),
                             {'publicSpouseScopeIds': []})
            self.assertTrue(all(not p['partners'] for p in people))

    def test_main_tree_preserves_identity_and_parents_and_withdraws_the_couple(self):
        old = dict(meta={}, sections=[], landmarks=[], people=deepcopy(self.people))
        old['people'][0].update(born=1700, note='Approved account')
        fresh = deepcopy(old)
        fresh['people'][0].update(born=1690, note='Different imported account')
        fresh['meta'].update(date='2026-10-18', **self.sync(fresh['people'], [self.assessment]))
        out = overlay_model(old, fresh)
        self.assertEqual(out['people'][0]['born'], 1700)
        self.assertEqual(out['people'][0]['note'], 'Approved account')
        self.assertEqual(out['people'][0]['partners'][0]['probability']['value'], .88)
        self.assertEqual(out, overlay_model(out, fresh))
        # A rebuild starts from recorded catalogue relationships, before overlays.
        cleared = deepcopy(old)
        cleared['meta'].update(date='2026-10-18', **self.sync(cleared['people'], []))
        out = overlay_model(out, cleared)
        self.assertTrue(all(not p['partners'] for p in out['people']))
        self.assertEqual([p['parents'] for p in out['people']], [p['parents'] for p in old['people']])

    def test_existing_other_partner_and_real_marriage_details_survive(self):
        self.people[0]['partners'] = [dict(id='Other-1', marriageDate='1710-01-01'),
                                     dict(id='record-bride', marriageDate='1716-07-01')]
        self.sync(self.people, [self.assessment])
        self.assertEqual(self.people[0]['partners'][0]['id'], 'Other-1')
        self.assertEqual(self.people[0]['partners'][1]['marriageDate'], '1716-07-01')
        previous = deepcopy(self.people)
        self.sync(self.people, [self.assessment])
        self.assertEqual(self.people, previous)

    def test_catalogue_cells_and_filter_fields_include_and_can_retire_proposed_spouse(self):
        rows = [dict(id='a-1', profile_ids=['A-1'], spouses=[dict(id='Other-1', name='Recorded partner')]),
                dict(catalogue_id='record-bride', profile_ids=[], spouses=[])]
        original = deepcopy(rows)
        reviewed = {i.casefold(): dict(relationships={'spouses': [dict(
            id=other, name=other, url='/people/'+other.lower()+'.html', probability={'value': .88},
            relationship_source='shared_research_assertion', allow_new_relationship=True,
            status='probable', record_scope='Banns; no ceremony date.')]})
            for i, other in [('A-1', 'record-bride'), ('record-bride', 'A-1')]}
        project_catalogue_spouses(rows, reviewed)
        self.assertEqual([r['id'] for r in rows[0]['spouses']], ['Other-1', 'record-bride'])
        self.assertEqual(rows[1]['spouses'][0]['id'], 'A-1')
        self.assertEqual(rows[0]['spouses'][-1]['probability']['value'], .88)
        previous = deepcopy(rows)
        self.assertEqual(project_catalogue_spouses(rows, reviewed), previous)
        project_catalogue_spouses(rows, {})
        self.assertEqual(rows, original)

    def test_catalogue_does_not_project_an_alternative_couple(self):
        rows = [dict(id='a-1', spouses=[])]
        reviewed = {'a-1': dict(relationships={'spouses': [dict(id='record-bride', status='possible',
            display='alternative', relationship_source='shared_research_assertion', allow_new_relationship=True)]})}
        self.assertEqual(project_catalogue_spouses(rows, reviewed), [dict(id='a-1', spouses=[])])


if __name__ == '__main__':
    unittest.main()
