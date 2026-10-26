"""Tree-group place lists link only place pages that exist (fictional data)."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tools.study_place_links import refresh_group_places


class GroupPlacesRefresh(unittest.TestCase):
    def test_a_stale_list_loses_places_the_build_no_longer_makes(self):
        with TemporaryDirectory() as directory:
            web = Path(directory)
            def put(relative, text):
                path = web / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text)
            put('assets/research/branches.json', json.dumps([
                {'id': 'family-harrow-1', 'kind': 'family', 'members': ['harrow-1', 'harrow-2']},
                {'id': 'harrow-parish', 'kind': 'place', 'members': ['harrow-1']}]))
            put('data/records-index.json', json.dumps([
                {'catalogue_id': 'harrow-1', 'location_id': 'fennick_parish', 'record_location': 'Fennick parish'},
                {'catalogue_id': 'harrow-2', 'location_id': 'old_mill', 'record_location': 'Old Mill'}]))
            put('places/fennick-parish.html', '<html></html>')
            stale = ('<main><section class="r-section group-places" id="group-places"><ul>'
                     '<li><a href="/places/old-mill.html">Old Mill</a></li></ul></section></main>')
            put('branches/family-harrow-1/index.html', stale)
            put('branches/harrow-parish/index.html', stale)
            self.assertEqual(refresh_group_places(web), ['branches/family-harrow-1/index.html'])
            page = (web / 'branches/family-harrow-1/index.html').read_text()
            self.assertIn('/places/fennick-parish.html', page)
            self.assertNotIn('/places/old-mill.html', page)
            self.assertEqual(refresh_group_places(web), [])          # idempotent
            self.assertIn('old-mill', (web / 'branches/harrow-parish/index.html').read_text())  # place studies untouched


if __name__ == '__main__':
    unittest.main()
