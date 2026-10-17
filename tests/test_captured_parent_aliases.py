import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from tools.site_sources.onetree.build import apply_captured_parent_aliases
from tools.sync_ancestry_atlas import overlay_model


class CapturedParentAliasesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.site = Path(self.tmp.name)
        (self.site / 'people').mkdir()
        self.parent = dict(id='Alias-1', name='Old parent', role='mother',
                           status='confident', probability={'value': .94}, note='Captured note')
        self.people = [
            dict(id='Child-1', kind='person', name='Child', born=1900, note='Approved account',
                 parents=[deepcopy(self.parent)],
                 edge=dict(parent='Alias-1', type='recorded', role='mother', status='confident')),
            dict(id='Alias-1', kind='person', name='Old parent', born=1850,
                 childrenRecorded=[dict(id='Child-1', role='child', status='uncertain',
                                        probability={'value': .6}), {'id': 'Other-1'}]),
            dict(id='Parent-1', kind='person', name='Current parent', born=1851,
                 note='Retain parent account', childrenRecorded=[{'id': 'Unrelated-1'}])]
        self.raw = dict(id='Parent-1', name='Current parent', relationship='mother',
                        relationship_source='wikitree_parent_field', tree_relationship=True,
                        status='unknown', tree_status='unmarked')
        self.write_dossiers([self.raw])

    def tearDown(self):
        self.tmp.cleanup()

    def write_dossiers(self, parents, target=True):
        data = dict(id='Child-1', relationships={'parents': parents})
        (self.site / 'people/child-1.json').write_text(json.dumps(data))
        if target:
            (self.site / 'people/parent-1.json').write_text(json.dumps({'id': 'Parent-1'}))

    def repair(self, people=None, redirects=None):
        return apply_captured_parent_aliases(self.people if people is None else people, self.site,
                                            {'Alias-1': 'Parent-1'} if redirects is None else redirects)

    def test_alias_retargets_row_edge_and_reciprocal_without_reassessment(self):
        before = deepcopy(self.people)
        metadata = self.repair()
        self.assertEqual(len(metadata['capturedParentIdentityRepairs']), 1)
        row = self.people[0]['parents'][0]
        self.assertEqual(row, dict(self.parent, id='Parent-1', name='Current parent', inModel=True))
        self.assertEqual(self.people[0]['edge'], dict(before[0]['edge'], parent='Parent-1'))
        self.assertEqual(self.people[1]['childrenRecorded'], [{'id': 'Other-1'}])
        self.assertEqual(self.people[2]['childrenRecorded'], [{'id': 'Unrelated-1'},
            dict(before[1]['childrenRecorded'][0], name='Child', inModel=True)])
        for old, current in zip(before, self.people):
            for key in ('born', 'note'):
                self.assertEqual(old.get(key), current.get(key))
        snapshot = deepcopy(self.people)
        self.assertEqual(self.repair(), metadata)
        self.assertEqual(self.people, snapshot)

    def test_empty_export_placeholder_retains_grade_and_other_role_edge(self):
        for placeholder in ['', 'Parent outside current One-Tree export']:
            with self.subTest(placeholder=placeholder):
                people = deepcopy(self.people)
                people[0]['parents'][0].update(id='', name=placeholder)
                people[0]['parents'].append(dict(id='Father-1', role='father', status='confident'))
                people[0]['edge'].update(parent='Father-1', role='father')
                self.repair(people)
                self.assertEqual(people[0]['parents'][0]['id'], 'Parent-1')
                self.assertEqual(people[0]['parents'][0]['probability'], self.parent['probability'])
                self.assertEqual(people[0]['edge']['parent'], 'Father-1')

    def test_placeholder_group_edge_restores_actual_parent(self):
        self.people[0]['parents'][0].update(id='', name='')
        self.people[0]['edge'] = dict(parent='@smaller-families', type='group')
        self.repair()
        self.assertEqual(self.people[0]['edge'], dict(parent='Parent-1', type='recorded',
            role='mother', status='confident', semantic='parent'))

    def test_rejects_different_named_private_hypothesis_and_ambiguous_model_rows(self):
        changes = [dict(id='Different-1'), dict(id='', name='A different named mother'),
                   dict(id='', name='Private parent'), dict(id='', name='', withheld=True),
                   dict(hypothesis=True), dict(status='rejected'), dict(alternative=True)]
        for change in changes:
            with self.subTest(change=change):
                people = deepcopy(self.people)
                people[0]['parents'][0].update(change)
                before = deepcopy(people)
                self.assertEqual(self.repair(people)['capturedParentIdentityRepairs'], [])
                self.assertEqual(people, before)
        self.people[0]['parents'].append(deepcopy(self.parent))
        before = deepcopy(self.people)
        self.assertEqual(self.repair()['capturedParentIdentityRepairs'], [])
        self.assertEqual(self.people, before)

    def test_rejects_unqualified_or_ambiguous_public_roles(self):
        changes = [dict(hypothesis=True), dict(withheld=True), dict(alternative=True),
                   dict(status='rejected'), dict(publication_status='withheld'),
                   dict(current=False), dict(lifecycle='superseded'),
                   dict(relationship_source='research'), dict(tree_relationship=False)]
        for change in changes:
            with self.subTest(change=change):
                self.write_dossiers([dict(self.raw, **change)])
                before = deepcopy(self.people)
                self.assertEqual(self.repair()['capturedParentIdentityRepairs'], [])
                self.assertEqual(self.people, before)
        self.write_dossiers([self.raw, dict(self.raw, id='Other-1')])
        self.assertEqual(self.repair()['capturedParentIdentityRepairs'], [])

    def test_requires_saved_survivor_existing_role_and_public_model_target(self):
        self.assertEqual(self.repair(redirects={})['capturedParentIdentityRepairs'], [])
        self.assertEqual(self.repair(redirects={'Alias-1': 'Loop-1', 'Loop-1': 'Alias-1'})[
            'capturedParentIdentityRepairs'], [])
        for change in ('role', 'model', 'dossier', 'identity'):
            with self.subTest(change=change):
                people = deepcopy(self.people)
                if change == 'role':
                    people[0]['parents'] = []
                elif change == 'model':
                    people.pop()
                elif change == 'dossier':
                    (self.site / 'people/parent-1.json').unlink()
                else:
                    (self.site / 'people/parent-1.json').write_text(json.dumps({'id': 'Different-1'}))
                self.assertEqual(self.repair(people)['capturedParentIdentityRepairs'], [])
                self.write_dossiers([self.raw])

    def test_redirect_chain_and_post1850_father(self):
        self.people[0]['parents'][0]['role'] = 'father'
        self.people[0]['edge']['role'] = 'father'
        self.write_dossiers([dict(self.raw, relationship='father')])
        metadata = self.repair(redirects={'Alias-1': 'Alias-2', 'Alias-2': 'Parent-1'})
        self.assertEqual(self.people[0]['parents'][0]['id'], 'Parent-1')
        self.assertEqual(metadata['capturedParentIdentityRepairs'][0]['aliases'], ['Alias-1', 'Alias-2'])

    def test_main_overlay_replays_identity_only_and_preserves_approved_account(self):
        retained = dict(meta={}, sections=[], landmarks=[], dna={'approved': ['retain']},
                        people=deepcopy(self.people))
        metadata = self.repair()
        fresh = dict(meta=dict(date='2026-10-17', **metadata), sections=[], landmarks=[],
                     people=deepcopy(self.people))
        fresh['people'][0].update(born=1901, note='Fresh short account')
        fresh['people'][2].update(born=1852, note='Fresh parent account')
        result = overlay_model(retained, fresh)
        for old, current in zip(retained['people'], result['people']):
            self.assertEqual(old.get('born'), current.get('born'))
            self.assertEqual(old.get('note'), current.get('note'))
        self.assertEqual(result['people'][0]['parents'], self.people[0]['parents'])
        self.assertEqual(result['people'][0]['edge'], self.people[0]['edge'])
        self.assertEqual(result['people'][1]['childrenRecorded'], self.people[1]['childrenRecorded'])
        self.assertEqual(result['people'][2]['childrenRecorded'], self.people[2]['childrenRecorded'])
        self.assertEqual(result['meta']['capturedParentIdentityRepairs'], metadata['capturedParentIdentityRepairs'])
        self.assertEqual(result['dna'], retained['dna'])
        self.assertEqual(overlay_model(result, fresh), result)
        retained['people'][0]['parents'][0]['id'] = 'Different-1'
        retained['people'][0]['edge']['parent'] = 'Parent-1'
        protected = overlay_model(retained, fresh)
        self.assertEqual(protected['people'], retained['people'])

    def test_main_can_restore_public_survivor_missing_from_older_atlas(self):
        retained = dict(meta={}, sections=[], landmarks=[], people=deepcopy(self.people[:-1]))
        metadata = self.repair()
        fresh = dict(meta=dict(date='2026-10-17', **metadata), sections=[], landmarks=[],
                     people=deepcopy(self.people))
        result = overlay_model(retained, fresh)
        people = {p['id']: p for p in result['people']}
        self.assertIn('Alias-1', people)
        self.assertEqual(people['Parent-1']['born'], 1851)
        self.assertEqual(people['Child-1']['parents'][0]['id'], 'Parent-1')
        self.assertEqual(people['Alias-1']['childrenRecorded'], [{'id': 'Other-1'}])
        self.assertEqual(overlay_model(result, fresh), result)
        retained['people'][0]['parents'][0]['id'] = 'Different-1'
        retained['people'][0]['edge']['parent'] = 'Alias-1'
        protected = overlay_model(retained, fresh)
        self.assertEqual(protected['people'], retained['people'])


if __name__ == '__main__':
    unittest.main()
