"""Source-library repair preserves published notices and static navigation."""
import json
from pathlib import Path
import tempfile
import unittest

from tools.repair_sources_page import repair


ROW = {'id':'s-one', 'title':'Parish register', 'members':['glasgow-951'], 'from':1800,
       'to':1800, 'citations':1, 'records':1, 'basis':'exact source URL'}
NOTES = '''<p id="opr-births-discovery">Reviewed 127 index results. <a href="/births/">Births</a></p>
<p id="opr-marriages-discovery">55 supplied results.</p>
<p id="opr-deaths-to-1700-discovery">Seven entries; some unresolved.</p>
<!-- BEGIN GRONI-DEATH-MATCH-LINK --><aside>72 matches, 22 leads and 53 new profiles.</aside><!-- END GRONI-DEATH-MATCH-LINK -->
<!-- BEGIN IRISH-CIVIL-DEATH-INDEX-LINK --><aside>241 leads. Originals remain unverified.</aside><!-- END IRISH-CIVIL-DEATH-INDEX-LINK -->'''
PAGE = '<!doctype html><html><head><title>Sources</title></head><body data-g-path="/sources/index.html"><div class="g-crumbs"><strong>Records</strong></div><main><header><h1>Find records</h1>' + NOTES + '</header></main><script defer src="/assets/v3/sources.js?v=old"></script></body></html>'


class SourcesPageTests(unittest.TestCase):
    def test_repair_retains_notices_and_static_listing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'sources').mkdir()
            (root / 'assets/v3').mkdir(parents=True)
            (root / 'assets/research').mkdir()
            worker = root / 'assets/research/search-worker.js'
            worker.write_text('fetch(path).then(r=>r.json())')
            (root / 'sources/index.html').write_text(PAGE)
            (root / 'assets/v3/source-index.json').write_text(json.dumps([ROW]))
            repair(root)
            self.assertIn("fetch(path,{cache:'no-cache'})", worker.read_text())
            page = (root / 'sources/index.html').read_text()
            self.assertIn('Source library · Glasgow', page)
            self.assertIn('<strong>Sources</strong>', page)
            self.assertEqual(5, page.count('class="sources-collection"'))
            for note in ('Reviewed 127 index results.', '55 supplied results.', 'Seven entries; some unresolved.', '72 matches, 22 leads and 53 new profiles.', '241 leads. Originals remain unverified.'):
                self.assertIn(note, page)
            self.assertIn('href="/sources/s-one/"', page)
            self.assertIn('1 linked person · 1 citation · 1 record entry', page)
            self.assertIn('href="/sources/browse/"', page)
            self.assertEqual(1, page.count('src="/assets/v3/sources.js?v='))
            self.assertEqual(1, page.count('href="/assets/v3/source-library.css?v='))
            packed_path = root / 'assets/v3/source-index-packed.json'
            packed = json.loads(packed_path.read_text())
            self.assertEqual(ROW, {key: value for key, value in zip(packed['fields'], packed['rows'][0]) if value is not None})
            self.assertEqual({}, dict(repair(root)))
            self.assertEqual(page, (root / 'sources/index.html').read_text())
            packed['rows'][0].pop(1)
            packed_path.write_text(json.dumps(packed))
            self.assertEqual({'source_search_index': 1}, dict(repair(root)))
            repaired = json.loads(packed_path.read_text())
            self.assertEqual(len(repaired['fields']), len(repaired['rows'][0]))

    def test_collection_updates_survive_repeated_repair(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'sources').mkdir()
            (root / 'assets/v3').mkdir(parents=True)
            path = root / 'sources/index.html'
            path.write_text(PAGE)
            (root / 'assets/v3/source-index.json').write_text(json.dumps([ROW]))
            repair(root)
            path.write_text(path.read_text().replace('Reviewed 127 index results.', 'Reviewed 128 index results.'))
            repair(root)
            page = path.read_text()
            self.assertEqual(1, page.count('Reviewed 128 index results.'))
            self.assertNotIn('Reviewed 127', page)


if __name__ == '__main__':
    unittest.main()
