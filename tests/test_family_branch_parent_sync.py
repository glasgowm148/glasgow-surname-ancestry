import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from bs4 import BeautifulSoup

from tools.sync_catalogue_research import refresh_family_branch_parents


class FamilyBranchParentSyncTest(unittest.TestCase):
    def test_current_hypothesis_replaces_stale_row_without_changing_children(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            branch = root / 'branches/family-example-1/index.html'
            branch.parent.mkdir(parents=True)
            branch.write_text('<h1>Family</h1><div class="r-family-tree">'
                              '<div class="r-family-row">No parents attached in this model</div>'
                              '<div class="r-family-row"><a href="/people/example-1.html">Selected person</a></div>'
                              '<div class="r-family-row"><a href="/people/example-5.html">Child</a></div></div>')
            registry = root / 'assets/research/branches.json'
            registry.parent.mkdir(parents=True)
            registry.write_text(json.dumps([{'id': 'family-example-1', 'rootId': 'Example-1'}]))
            person = root / 'people/example-1.json'
            person.parent.mkdir()
            person.write_text(json.dumps({'relationships': {'parents': [
                {'id': 'Example-2', 'name': 'Preferred father', 'relationship': 'father',
                 'url': '/people/example-2.html', 'status': 'probable', 'display': 'hypothesis',
                 'lifecycle': 'current', 'probability': {'value': .64, 'label': 'Probable · 64%'}},
                {'id': 'Example-3', 'name': 'Recorded mother', 'relationship': 'mother',
                 'status': 'unknown', 'tree_status_label': 'WikiTree: confident parent',
                 'probability': {'value': None}},
                {'id': 'Example-4', 'name': 'Alternative father', 'relationship': 'father',
                 'display': 'alternative', 'lifecycle': 'alternative'},
            ]}}))
            before = branch.read_text()
            self.assertEqual(refresh_family_branch_parents(['Example-1'], site_root=root), ['family-example-1'])
            self.assertEqual(branch.read_text(), before)
            refresh_family_branch_parents(['Example-1'], site_root=root, write=True)
            page = BeautifulSoup(branch.read_text(), 'html.parser')
            rows = page.select('.r-family-row')
            self.assertEqual(rows[0].select_one('a')['href'], '/people/example-2.html')
            self.assertEqual(rows[0].get_text().count('64%'), 1)
            self.assertNotIn('Alternative father', rows[0].get_text())
            mother = rows[0].select('.r-family-person')[1].get_text()
            self.assertIn('WikiTree: confident parent', mother)
            self.assertNotIn('%', mother)
            original_rows = BeautifulSoup(before, 'html.parser').select('.r-family-row')
            self.assertEqual([str(row) for row in rows[1:]], [str(row) for row in original_rows[1:]])
            self.assertEqual(refresh_family_branch_parents(['Example-1'], site_root=root, write=True), [])

    def test_child_only_sync_refreshes_parent_branch_and_research_counts(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            page = root / 'branches/family-example-1/index.html'
            page.parent.mkdir(parents=True)
            page.write_text('<div class="r-group-stats"><span><strong>2</strong> people</span>'
                            '<span><strong>0</strong> records</span><span><strong>0</strong> conclusions</span></div>'
                            '<div class="r-family-tree"><div class="r-family-row">No parents</div>'
                            '<div class="r-family-row"><div class="r-family-person">'
                            '<a data-r-person-link="Example-2">Child</a>'
                            '<span class="r-chip" data-status="unknown">Unassessed</span></div></div></div>')
            branches = root / 'assets/research/branches.json'
            branches.parent.mkdir(parents=True)
            branches.write_text(json.dumps([{'id': 'family-example-1', 'rootId': 'Example-1',
                                            'members': ['example-1', 'example-2'],
                                            'record_count': 0, 'review_count': 0}]))
            (branches.parent / 'record-index.json').write_text(json.dumps([{'id': 'record-1', 'p': 'example-2'}]))
            account = root / 'people/example-1.json'
            account.parent.mkdir()
            account.write_text(json.dumps({'relationships': {'children': [
                {'id': 'Example-2', 'status': 'proved', 'probability': {'value': .98, 'label': 'Confident · 98%'}}]},
                'research_findings': [{'sections': [{'category': 'conclusion', 'markdown': 'A register names the child.'}]}]}))
            self.assertEqual(refresh_family_branch_parents(['Example-2'], site_root=root, write=True), ['family-example-1'])
            rendered = BeautifulSoup(page.read_text(), 'html.parser')
            chip = rendered.select_one('.r-family-person .r-chip')
            self.assertEqual(chip.get_text(), 'Confident · 98%')
            self.assertEqual(chip['data-status'], 'proved')
            self.assertEqual([n.get_text() for n in rendered.select('.r-group-stats strong')], ['2', '1', '1'])
            saved = json.loads(branches.read_text())[0]
            self.assertEqual((saved['record_count'], saved['review_count']), (1, 1))
            self.assertEqual(refresh_family_branch_parents(['Example-2'], site_root=root, write=True), [])

    def test_reviewed_daughters_join_existing_paternal_family_without_import_rewrite(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            page = root / 'branches/family-example-1/index.html'
            page.parent.mkdir(parents=True)
            page.write_text('<div class="r-group-stats"><span><strong>3</strong> people</span>'
                            '<span><strong>3</strong> records</span><span><strong>3</strong> conclusions</span></div>'
                            '<div class="r-country-legend"></div>'
                            '<div class="r-linklist"><a href="/people/example-1.html">Old</a></div>'
                            '<div class="r-family-tree"><div class="r-family-row">No parents</div></div>')
            assets = root / 'assets/research'
            assets.mkdir(parents=True)
            branches = assets / 'branches.json'
            branches.write_text(json.dumps([{'id': 'family-example-1', 'kind': 'family',
                                             'rootId': 'Example-1',
                                             'members': ['example-1', 'example-2', 'example-3'],
                                             'count': 3, 'record_count': 3, 'review_count': 3,
                                             'countries': {'america': 3}}]))
            (assets / 'record-index.json').write_text(json.dumps([
                {'id': f'record-{number}', 'p': f'example-{number}'}
                for number in range(1, 6)
            ]))
            registry = assets / 'registry.json'
            registry.write_text(json.dumps([{
                'id': f'Example-{number}', 'slug': f'example-{number}',
                'name': f'Example {number}', 'url': f'/people/example-{number}.html',
                'birth': f'18{number:02d}', 'birthPlace': 'America', 'from': 1800 + number,
                'country': 'america',
                'branches': ['family-example-1'] if number <= 3 else [],
            } for number in range(1, 7)]))
            packed = root / 'assets/v3/registry-packed.json'
            packed.parent.mkdir(parents=True)
            packed.write_text(json.dumps({'fields': ['slug', 'branches'], 'rows': [
                [f'example-{number}', ['family-example-1'] if number <= 3 else []]
                for number in range(1, 7)
            ]}))
            data = root / 'data'
            data.mkdir()
            catalogue = data / 'catalogue-search-index.json'
            catalogue.write_text(json.dumps([{
                'id': f'example-{number}',
                'family_root': ({'id': 'Example-1', 'distance': 1 if number == 2 else 2,
                                 'catalogued_members': 2} if number in (2, 3) else None),
                'family_roots': [],
                'children': [{'id': 'Example-3', 'name': 'Example 3'}] if number == 2 else [],
            } for number in range(1, 7)]))
            imported = data / 'people-index.json'
            imported.write_text('imported snapshot\n')
            people = root / 'people'
            people.mkdir()
            for number in range(1, 7):
                father = ({'id': 'Example-2', 'relationship': 'father',
                           'status': 'strongly_supported', 'display': 'current',
                           'lifecycle': 'current', 'publication_status': 'approved'}
                          if number in (4, 5) else
                          {'id': 'Example-2', 'relationship': 'father',
                           'status': 'possible', 'display': 'alternative',
                           'lifecycle': 'alternative', 'publication_status': 'approved'}
                          if number == 6 else None)
                (people / f'example-{number}.json').write_text(json.dumps({
                    'relationships': {'parents': [father] if father else []},
                    'research_findings': [{'sections': [
                        {'category': 'conclusion', 'markdown': 'Reviewed.'}]}],
                }))
            self.assertEqual(refresh_family_branch_parents(['Example-4', 'Example-5', 'Example-6'],
                                                           site_root=root, write=True),
                             ['family-example-1'])
            branch = json.loads(branches.read_text())[0]
            self.assertEqual(branch['members'], [f'example-{number}' for number in range(1, 6)])
            self.assertEqual((branch['count'], branch['record_count'], branch['review_count']),
                             (5, 5, 5))
            rendered = BeautifulSoup(page.read_text(), 'html.parser')
            self.assertEqual([item.get_text() for item in rendered.select('.r-group-stats strong')],
                             ['5', '5', '5'])
            self.assertIn('Example 4', rendered.select_one('.r-linklist').get_text())
            saved_registry = {item['slug']: item for item in json.loads(registry.read_text())}
            self.assertIn('family-example-1', saved_registry['example-4']['branches'])
            self.assertIn('family-example-1', saved_registry['example-5']['branches'])
            self.assertEqual(saved_registry['example-6']['branches'], [])
            self.assertEqual(json.loads(packed.read_text())['rows'][3][1], ['family-example-1'])
            saved_catalogue = {item['id']: item for item in json.loads(catalogue.read_text())}
            self.assertEqual(saved_catalogue['example-4']['family_root']['id'], 'Example-1')
            self.assertEqual(saved_catalogue['example-5']['family_root']['distance'], 2)
            self.assertEqual(saved_catalogue['example-2']['family_root']['catalogued_members'], 4)
            self.assertEqual([item['id'] for item in saved_catalogue['example-2']['children']],
                             ['Example-3', 'Example-4', 'Example-5'])
            self.assertIsNone(saved_catalogue['example-6']['family_root'])
            self.assertEqual(imported.read_text(), 'imported snapshot\n')
            for field in ('family_root', 'family_roots'):
                target = saved_catalogue['example-4'][field]
                if isinstance(target, list):
                    target = target[0]
                target['birth_location'] = 'Preserve reviewed root metadata'
            catalogue.write_text(json.dumps(list(saved_catalogue.values())))
            self.assertEqual(refresh_family_branch_parents(['Example-4', 'Example-5', 'Example-6'],
                                                           site_root=root, write=True), [])
            self.assertEqual(json.loads(catalogue.read_text())[3]['family_root']['birth_location'],
                             'Preserve reviewed root metadata')
            saved_catalogue['example-4']['family_root'] = None
            saved_catalogue['example-4']['family_roots'] = []
            catalogue.write_text(json.dumps(list(saved_catalogue.values())))
            self.assertEqual(refresh_family_branch_parents(['Example-4'], site_root=root, write=True),
                             ['family-example-1'])
            restored = {item['id']: item for item in json.loads(catalogue.read_text())}
            self.assertEqual(restored['example-4']['family_root']['id'], 'Example-1')


if __name__ == '__main__':
    unittest.main()
