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


if __name__ == '__main__':
    unittest.main()
