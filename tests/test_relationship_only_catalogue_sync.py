import unittest
from unittest.mock import patch

from bs4 import BeautifulSoup

from tools.sync_catalogue_research import discrepancies


class RelationshipOnlyCatalogueSyncTest(unittest.TestCase):
    def test_new_research_grade_refreshes_an_unchanged_profile_account(self):
        dossier = {'id': 'Example-1', 'research_findings': [], 'wikitree_update': None}
        old = '<main class="person-dossier-readable"><section id="family">Unassessed father link</section></main>'
        current = '<section id="family"><a href="/people/example-2.html">Father</a> Confident · 99%</section>'
        with patch('tools.sync_catalogue_research.render_person_dossier', return_value=current):
            issues = discrepancies(dossier, BeautifulSoup(old, 'html.parser'), [], None, {}, {})
            self.assertEqual(issues, ['visible relationships'])
            updated = BeautifulSoup('<main class="person-dossier-readable">' + current + '</main>', 'html.parser')
            self.assertEqual(discrepancies(dossier, updated, [], None, {}, {}), [])


if __name__ == '__main__':
    unittest.main()
