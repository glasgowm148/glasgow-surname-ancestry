import json
from pathlib import Path
import tempfile
import unittest

from tools.site_sources.onetree.build import approved_record_parent_nodes
from tools.publish_resolved_dossiers import resolve


class RecordParentTests(unittest.TestCase):
    def test_only_selected_public_historical_parent_closure_is_admitted(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'data').mkdir()
            (root / 'people').mkdir()
            ids = ['record-mother', 'record-grandmother', 'record-unrelated', 'record-private', 'record-recent', 'record-withdrawn']
            index = []
            for ident in ids:
                index.append(dict(id=ident, json_url=f'/people/{ident}.json', html_url=f'/people/{ident}.html', birth_surnames=['Flanagan']))
                dossier = dict(id=ident, name=ident, pending_profile_creation=True,
                    historical_basis=dict(latest_birth_year=1840, source_url='https://example.org/register'),
                    relationships={'parents': []})
                if ident == 'record-private':
                    dossier['private'] = True
                if ident == 'record-recent':
                    dossier['historical_basis']['latest_birth_year'] = 2000
                (root / 'people' / (ident + '.json')).write_text(json.dumps(dossier))
            (root / 'data/people-index.json').write_text(json.dumps(index))
            assessments = []
            def pair(child, parent, withdrawn=False):
                aid = child + '-' + parent
                assessments.append(dict(assertion_id=aid, people=[child, parent],
                    publication_status='approved', working_selection=True, source_ids=['original'],
                    probability={'value': .98}, status='strongly_supported',
                    perspectives={child: {'relationship': 'mother'}}))
                path = root / 'people' / (child.lower() + '.json')
                dossier = json.loads(path.read_text()) if path.exists() else {'id': child, 'relationships': {'parents': []}}
                dossier['relationships']['parents'].append(dict(id=parent, assertion_id=aid, relationship='mother',
                    publication_status='approved', display='historical' if withdrawn else 'current'))
                path.write_text(json.dumps(dossier))
            pair('Child-1', 'record-mother')
            pair('record-mother', 'record-grandmother')
            pair('Child-1', 'record-private')
            pair('Child-1', 'record-recent')
            pair('Child-1', 'record-withdrawn', withdrawn=True)
            nodes = {}
            added = approved_record_parent_nodes(nodes, {'Child-1'}, root, assessments)
            self.assertEqual({'record-mother', 'record-grandmother'}, added)
            self.assertEqual(['Flanagan'], nodes['record-mother']['birth_surnames'])
            self.assertEqual(None, nodes['record-grandmother']['birth_year'])

    def test_record_relative_has_local_account_without_invented_wikitree_url(self):
        original = dict(id='Child-1', relationships={'parents': [dict(
            id='record-parent', relationship='father', url='/people/record-parent.html',
            wikitree_url='https://www.wikitree.com/wiki/record-parent')]}, claims=[])
        result = resolve(original, [])
        self.assertIsNone(result['relationships']['parents'][0]['wikitree_url'])
        self.assertEqual('/people/record-parent.html', result['relationships']['parents'][0]['url'])
        self.assertEqual('https://www.wikitree.com/wiki/record-parent', original['relationships']['parents'][0]['wikitree_url'])


if __name__ == '__main__':
    unittest.main()
