"""Check source migration, reference parity and approved excerpt boundaries."""
import hashlib
import json
from pathlib import Path
import unittest
from bs4 import BeautifulSoup
from tools.build_source_collections import ROOT, WEB, TYPES, guide, newspaper_body


class SourceCollectionsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = json.loads((WEB/'assets/sources/collection-index.json').read_text())
        cls.pages = json.loads((WEB/'assets/sources/collection-pages.json').read_text())
        cls.newspapers = json.loads((WEB/'data/glasgow-newspaper-review.json').read_text())

    def test_every_public_reference_has_a_type_and_preserved_reader(self):
        original = json.loads((WEB/'assets/v3/source-index.json').read_text())
        self.assertEqual({r['id'] for r in original}, {r['id'] for r in self.rows})
        for row in self.rows:
            self.assertTrue(set(row['categories']) <= set(TYPES))
            self.assertTrue(row['categories'])
            self.assertTrue((WEB/'sources'/row['id']/'index.html').exists(), row['id'])
        self.assertEqual(len(self.rows), self.pages['reference_items'])

    def test_every_generated_collection_is_real_and_browsable_without_javascript(self):
        for route in self.pages['pages']:
            path = WEB/route.lstrip('/')/'index.html'
            self.assertTrue(path.exists(), route)
            page = path.read_text()
            self.assertIn('<main', page)
            self.assertNotIn('/assets/v3/sources.js', page)
            if 'sc-browser' in page:
                self.assertIn('Complete collection index', page)
                self.assertIn('Year unresolved', page)

    def test_1851_irish_census_keeps_coverage_and_actual_evidence_together(self):
        page = (WEB/'sources/census/ireland/1851/index.html').read_text()
        for term in ('1851 Irish Census', 'one Belfast ward', 'Fermanagh', 'heads-of-household index', '1922', 'deaths since 1841', 'National Archives', 'Original / provider link'):
            self.assertIn(term, page)
        expected = [r['id'] for r in self.rows if 'census' in r['categories'] and 'Ireland' in r['countries'] and 1851 in r.get('years', [])]
        self.assertTrue(expected)
        for ident in expected: self.assertIn('/sources/'+ident+'/', page)

    def test_census_year_pages_include_shared_references_and_linked_people(self):
        census = [r for r in self.rows if 'census' in r['categories']]
        for row in census:
            for country in row['countries']:
                country = country.lower().replace(' ', '-')
                for year in row.get('years', []) or ['undated']:
                    path = WEB/f'sources/census/{country}/{year}/index.html'
                    self.assertTrue(path.exists(), str(path))
                    self.assertIn('/sources/'+row['id']+'/', path.read_text())
        ireland = [r for r in census if 'Ireland' in r['countries'] and 1851 in r.get('years', [])]
        people = {p['id'] for row in ireland for p in row['people']}
        page = (WEB/'sources/census/ireland/1851/index.html').read_text()
        self.assertIn(f'{len(ireland)} reference items · {len(people)} linked catalogue people', page)
        self.assertIn('Alexander Glasgow', page)
        self.assertIn('not a complete surname search', page)

    def test_census_access_dates_and_emigrant_birthplaces_do_not_create_year_pages(self):
        census = [r for r in self.rows if 'census' in r['categories']]
        overseas = next(r for r in census if r['id']=='s-4b3536e47ecee8f9')
        self.assertEqual(overseas['years'], [1920])
        self.assertEqual(overseas['countries'], ['United States'])
        scottish = next(r for r in census if r['id']=='s-2e89040aaf680d40')
        self.assertEqual(scottish['years'], [1841])
        self.assertIn(scottish['id'], (WEB/'sources/census/scotland/1841/index.html').read_text())
        self.assertFalse((WEB/'sources/census/ireland/2026/index.html').exists())

    def test_newspaper_review_preserves_all_rows_and_uncertainty(self):
        page = (WEB/'sources/newspapers/index.html').read_text()
        soup = BeautifulSoup(page, 'html.parser')
        records = soup.select('#newspaper-records .sc-newspaper')
        retained = [r for r in self.newspapers['rows'] if r['status'] in ('confirmed surname','place study')]
        self.assertEqual(len(records),len(retained))
        self.assertEqual(len(soup.select('.sc-newspaper')), len(self.newspapers['rows']))
        self.assertEqual([x['data-year'] for x in records], sorted(x['data-year'] for x in records))
        for row in self.newspapers['rows']:
            node = soup.find(id='newspaper-'+str(row['image_id']))
            self.assertIsNotNone(node)
            self.assertIn(row['assessment'], node.get_text())
            self.assertIsNotNone(node.find('a',href=row['source_url']))
        self.assertIn('not confirmed surname records',page)
        self.assertEqual(len(soup.select('figure img')), self.pages['inline_newspaper_excerpts'])

    def test_only_hash_approved_bounded_clips_are_public(self):
        manifest = json.loads((ROOT/'research/source-library/newspaper-clippings.json').read_text())
        self.assertIn('explicitly requested', manifest['authorization'])
        approved=set()
        supplied=json.loads((ROOT/'research/source-library/supplied-newspaper-clippings.json').read_text())
        for clip in manifest['assets']+supplied['assets']:
            self.assertTrue(clip['source_path'].startswith('research/source-library/newspaper-clippings/'))
            self.assertLess(clip['width'],1000)
            source=ROOT/clip['source_path'];public=WEB/clip['public_path']
            self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(),clip['sha256'])
            self.assertEqual(source.read_bytes(),public.read_bytes())
            approved.add(public.name)
        self.assertEqual(approved,{p.name for p in (WEB/'assets/sources/newspapers').glob('*.png')})
        gallery=BeautifulSoup((WEB/'sources/newspapers/supplied-clippings/index.html').read_text(),'html.parser')
        self.assertEqual(len(gallery.select('main figure img')),16)
        self.assertEqual(sum(not a['image_id'] for a in supplied['assets']),3)
        self.assertIn('exact image ID pending',gallery.get_text())

    def test_parish_and_civil_collections_keep_full_tables(self):
        for kind,n in [('births',127),('marriages',55),('deaths',7)]:
            page = (WEB/f'sources/{kind}/scotland/opr-to-1700/index.html').read_text()
            soup=BeautifulSoup(page,'html.parser')
            self.assertEqual(len(soup.select('table tbody tr')),n,kind)
            self.assertIn('original',page.lower())
            self.assertIn('scotlandspeople.gov.uk',page)
        civil = (WEB/'sources/deaths/ireland/civil-1864-1900/index.html').read_text()
        self.assertEqual(len(BeautifulSoup(civil,'html.parser').select('table tbody tr')),241)
        self.assertIn('HOLD',civil)
        groni = (WEB/'sources/deaths/ireland/groni-matches/index.html').read_text()
        self.assertIn('152 distinct entries',groni)
        self.assertIn('Paid certificates were not consulted',groni)
        self.assertGreater(len(BeautifulSoup(groni,'html.parser').select('table tbody tr')),150)

    def test_moved_collections_and_downloads_have_no_dead_local_links(self):
        for route in ['newspapers','births/scotland/opr-to-1700','marriages/scotland/opr-to-1700','deaths/scotland/opr-to-1700','deaths/ireland/civil-1864-1900','deaths/ireland/groni-matches']:
            soup=BeautifulSoup((WEB/'sources'/route/'index.html').read_text(),'html.parser')
            for a in soup.select('main a[href^="/"]'):
                href=a['href'].split('#')[0].split('?')[0]
                target=WEB/href.lstrip('/')
                self.assertTrue(target.is_file() or (target/'index.html').is_file(),href)
        branch=(WEB/'branches/scottish-families/index.html').read_text()
        self.assertIn('id="early-newspapers"',branch)
        self.assertIn('/sources/newspapers/',branch)
        self.assertNotIn('early-newspaper-table-wrap',branch)
        self.assertIn('data-source-target="/sources/newspapers/#newspaper-',branch)
        ireland=(WEB/'branches/early-ireland/index.html').read_text()
        self.assertIn('Armagh children',ireland)
        self.assertIn('cannot both be their death',ireland)
