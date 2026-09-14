"""Migration contracts for visible content, not merely preserved files."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]


def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'tools' / (name + '.py'))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


class SiteExperienceTests(unittest.TestCase):
    def test_metadata_comparison_ignores_serialization_only(self):
        helper = module('repair_unified_site')
        old = '<meta name="description" content="Mary &amp; John">'
        new = '<meta content="Mary &amp; John" name="description"/>'
        self.assertEqual(helper._metadata_signature(old, helper.DESCRIPTION_RE), helper._metadata_signature(new, helper.DESCRIPTION_RE))
        changed = '<meta name="description" content="Another person">'
        self.assertNotEqual(helper._metadata_signature(old, helper.DESCRIPTION_RE), helper._metadata_signature(changed, helper.DESCRIPTION_RE))
        self.assertNotEqual(helper._metadata_signature(old, helper.DESCRIPTION_RE), helper._metadata_signature('', helper.DESCRIPTION_RE))

    def test_generated_presentation_contracts(self):
        summary, failures = module('audit_site_experience').audit()
        self.assertGreater(summary['experience_checks'], 25)
        self.assertEqual([], failures)

    def test_actions_use_full_identity_data_not_compact_index(self):
        helper = module('repair_profile_wikitree_links')
        with tempfile.TemporaryDirectory() as directory:
            web = Path(directory)
            (web / 'data').mkdir()
            (web / 'people').mkdir()
            people = [
                {'catalogue_id':'glasgow-2223', 'profile_ids':['Glasgow-2223']},
                {'catalogue_id':'early-bearer', 'profile_ids':[], 'wikitree_free_space_url':'https://www.wikitree.com/wiki/Space:Documentary_bearer'},
                {'catalogue_id':'unresolved', 'profile_ids':[], 'candidate_ids':['Glasgow-2223']},
            ]
            (web / 'data/people.json').write_text(json.dumps({'people':people}))
            (web / 'data/people-index.json').write_text(json.dumps({'people':[{'id':'Glasgow-2223'}]}))
            for person in people:
                (web / 'people' / (person['catalogue_id'] + '.html')).write_text('<html><head></head><body><h1>Person</h1></body></html>')
            helper.WEB = web
            helper.repair()
            mary = (web / 'people/glasgow-2223.html').read_text()
            self.assertIn('class="profile-wikitree-actions"', mary)
            self.assertIn('href="https://www.wikitree.com/wiki/Glasgow-2223"', mary)
            self.assertIn('Read the maintained Space page', (web / 'people/early-bearer.html').read_text())
            self.assertNotIn('profile-wikitree-actions', (web / 'people/unresolved.html').read_text())
            self.assertEqual({}, helper.repair())

    def test_closed_disclosures_do_not_count_as_prominent_links(self):
        parser = module('audit_site_experience').Page
        page = parser('<details><summary><a href="/title">Title</a></summary><a href="/hidden">Hidden</a></details><a hidden href="/also-hidden">Hidden</a>')
        self.assertTrue(page.links('/title')[0].exposed())
        self.assertFalse(page.links('/hidden')[0].exposed())
        self.assertFalse(page.links('/also-hidden')[0].exposed())

    def test_locality_groups_use_reviewed_membership(self):
        branches = {row['id']: row for row in json.loads((ROOT / 'www/assets/research/branches.json').read_text())}
        larne = branches['larne-kilwaughter']
        lisnagaver = branches['lisnagaver-rasharkin']
        self.assertTrue({'glasgow-867', 'glasgow-1371'} <= set(lisnagaver['members']))
        self.assertTrue({'glasgow-867', 'glasgow-1371', 'glasgow-1022'}.isdisjoint(larne['members']))
        self.assertIn('uncertain exported-tree ancestry is excluded', larne['membershipBasis'])
        registry = {row['slug']: row for row in json.loads((ROOT / 'www/assets/research/registry.json').read_text())}
        self.assertNotIn('larne-kilwaughter', registry['glasgow-867']['branches'])
        self.assertNotIn('larne-kilwaughter', registry['glasgow-1371']['branches'])
        self.assertEqual('Hugh Glasgow', registry['glasgow-1503']['name'])
        self.assertNotIn('glasgow-1499', larne['members'])
        packed = json.loads((ROOT / 'www/assets/v3/registry-packed.json').read_text())
        packed_people = {row[packed['fields'].index('slug')]: dict(zip(packed['fields'], row)) for row in packed['rows']}
        self.assertEqual('Hugh Glasgow', packed_people['glasgow-1503']['name'])

    def test_locality_pages_show_established_families(self):
        expected = {
            'lisnagaver-rasharkin': ('Alexander Glasgow and Mary McCaughan', 'Thomas and Daniel Glasgow'),
            'larne-kilwaughter': ('The 1653 and 1669 households', 'Robert Glasgow and Rachel Wilson'),
        }
        for branch, titles in expected.items():
            soup = BeautifulSoup((ROOT / f'www/branches/{branch}/index.html').read_text(), 'html.parser')
            section = soup.select_one('#local-family-overview')
            self.assertIsNotNone(section)
            self.assertEqual(5, len(section.select('.local-family-card')))
            page_titles = {node.get_text(' ', strip=True) for node in section.select('.local-family-card h3')}
            self.assertTrue(set(titles) <= page_titles)
            for card in section.select('.local-family-card'):
                self.assertTrue(card.select_one('.local-family-basis'))
                self.assertTrue(card.select_one('.local-family-boundary'))
                self.assertTrue(card.select('.local-family-members a'))
        larne_text = BeautifulSoup((ROOT / 'www/branches/larne-kilwaughter/index.html').read_text(), 'html.parser').get_text(' ', strip=True)
        self.assertIn('does not place Rasharkin people in this locality group', larne_text)
        self.assertIn('Hugh Glasgow', larne_text)

    def test_alexander_locality_links_to_branch(self):
        soup = BeautifulSoup((ROOT / 'www/people/glasgow-951.html').read_text(), 'html.parser')
        link = soup.select_one('.dossier-locality a')
        self.assertIsNotNone(link)
        self.assertEqual('/branches/lisnagaver-rasharkin/', link['href'])
        self.assertEqual('Lisnagaver, Rasharkin parish', link.get_text(strip=True))


if __name__ == '__main__':
    unittest.main()
