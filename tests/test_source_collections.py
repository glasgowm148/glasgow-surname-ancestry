"""Check source migration, reference parity and approved excerpt boundaries."""
import hashlib
import json
from pathlib import Path
import unittest
from bs4 import BeautifulSoup
from tools.build_source_collections import ROOT, WEB, TYPES, guide, load_clips, newspaper_body, newspaper_card, newspaper_groups, newspaper_country, profile_links
from tools.publish_newspaper_review import PUBLIC_ROW_FIELDS, render as render_newspaper_review


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
        self.assertEqual(len(records), len(newspaper_groups(retained)))
        expected_cards = sum(len(newspaper_groups([r for r in self.newspapers['rows'] if r['status'] == status])) for status in ('confirmed surname', 'place study', 'place or ship', 'reading pending'))
        self.assertEqual(len(soup.select('.sc-newspaper')), expected_cards)
        years = [x['data-year'] for x in records]
        self.assertEqual(years, sorted(years, key=lambda value: int(value.split(',')[0])))
        for row in self.newspapers['rows']:
            node = soup.find(id='newspaper-'+str(row['image_id']))
            self.assertIsNotNone(node)
            article = node.find_parent('article') or node
            self.assertIn(row['assessment'], article.get_text())
            self.assertIsNotNone(article.find('a',href=row['source_url']))
        self.assertIn('not confirmed surname records',page)
        manifest = json.loads((ROOT/'research/source-library/newspaper-clippings.json').read_text())
        approved_paths = [a['public_path'] for a in manifest['assets']] + [extra['public_path'] for a in manifest['assets'] for extra in a.get('additional_excerpts', [])]
        rebuilt = BeautifulSoup(newspaper_body(self.newspapers, load_clips(WEB), WEB), 'html.parser')
        rendered_images = {node.get('src', '').lstrip('/') for node in rebuilt.select('figure img')}
        self.assertTrue(set(approved_paths) <= rendered_images)
        rendered_cards = rebuilt.select('#newspaper-records article.sc-newspaper')
        self.assertEqual(len(rendered_cards), len(newspaper_groups(retained)))
        for card in rendered_cards:
            self.assertEqual(len(card.select('.sc-newspaper-reading > p strong')), 2)

    def test_only_hash_approved_bounded_clips_are_public(self):
        manifest = json.loads((ROOT/'research/source-library/newspaper-clippings.json').read_text())
        self.assertIn('explicitly requested', manifest['authorization'])
        approved=set()
        supplied=json.loads((ROOT/'research/source-library/supplied-newspaper-clippings.json').read_text())
        all_clips = manifest['assets'] + supplied['assets'] + [extra for clip in manifest['assets'] for extra in clip.get('additional_excerpts', [])]
        for clip in all_clips:
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

    def test_search_logs_do_not_claim_missing_retained_excerpts(self):
        row = dict(self.newspapers['rows'][0])
        for status, message in [
            ('reading pending', 'Unverified search lead'),
            ('place or ship', 'excluded from surname evidence'),
            ('confirmed surname', 'Saved excerpt pending'),
        ]:
            row['status'] = status
            card = newspaper_card(row, {}, WEB)
            self.assertIn(message, card)
            if status != 'confirmed surname':
                self.assertNotIn('Saved excerpt pending', card)

    def test_identical_readings_group_but_keep_issue_anchors_and_links(self):
        rows = [
            {'image_id': 'a', 'date': '1800-01-01', 'paper': 'Paper A', 'page': 1,
             'status': 'confirmed surname', 'reading': 'Same notice.', 'source_url': 'https://a'},
            {'image_id': 'b', 'date': '1801-01-01', 'paper': 'Paper B', 'page': 2,
             'status': 'confirmed surname', 'reading': 'Same notice.', 'source_url': 'https://b'},
            {'image_id': 'c', 'date': '1802-01-01', 'paper': 'Paper C', 'page': 3,
             'status': 'confirmed surname', 'reading': 'Different notice', 'source_url': 'https://c'},
        ]
        groups = newspaper_groups(rows)
        self.assertEqual([[r['image_id'] for r in g] for g in groups], [['a', 'b'], ['c']])
        html = newspaper_card(rows[0], {}, WEB, groups[0])
        self.assertEqual(html.count('<article'), 1)
        self.assertIn('id="newspaper-b"', html)
        self.assertIn('https://a', html)
        self.assertIn('https://b', html)
        self.assertIn('Repeated notice — 2 original issues', html)

    def test_profile_links_use_candidate_label_without_inventing_identity(self):
        row = {'profile_ids': ['Glasgow-2375'], 'assessment': 'Compatible candidate; identity remains unresolved.'}
        html = newspaper_card({**row, 'image_id':'x', 'date':'1800-01-01', 'paper':'Paper', 'page':1,
                               'status':'confirmed surname', 'reading':'A reading', 'source_url':'https://x'}, {}, WEB)
        self.assertIn('possible candidate; identity unresolved', html)
        self.assertIn('Aaron Glasgow', html)

    def test_repeated_multi_person_notice_keeps_both_subject_drafts(self):
        base = {'image_id': 'x', 'date': '1775-08-25', 'paper': 'Paper', 'page': 1,
                'status': 'confirmed surname', 'reading': 'James and Ezekiel Glasgow',
                'source_url': 'https://x', 'profile_ids': [], 'assessment': 'Identity unresolved.',
                'subject_links': [{'name': 'James Glasgow', 'url': '/research/subjects/#james'}]}
        second = {**base, 'image_id': 'y', 'source_url': 'https://y',
                  'subject_links': [{'name': 'Ezekiel Glasgow', 'url': '/research/subjects/#ezekiel'}]}
        html = newspaper_card(base, {}, WEB, [base, second])
        self.assertIn('href="/research/subjects/#james"', html)
        self.assertIn('href="/research/subjects/#ezekiel"', html)
        self.assertIn('No profile assigned; identity remains unresolved.', html)
        self.assertEqual(html.count('<article'), 1)

    def test_profile_confidence_requires_curated_match_and_keeps_roles(self):
        base = {'image_id':'x', 'date':'1800-01-01', 'paper':'Paper', 'page':1,
                'status':'confirmed surname', 'reading':'A reading', 'source_url':'https://x',
                'profile_ids':['Glasgow-2375'], 'assessment':'Not the same person; strong match is conditional.'}
        fallback = newspaper_card(base, {}, WEB)
        self.assertIn('possible candidate; identity unresolved', fallback)
        self.assertNotIn('sc-confidence-strong', fallback)
        curated = dict(base, profile_matches=[{'profile_id':'Glasgow-2375', 'confidence':'probable',
                                                'role':'record subject', 'basis':'checked chronology'}])
        checked = newspaper_card(curated, {}, WEB)
        self.assertIn('probable', checked)
        self.assertIn('record subject', checked)
        self.assertIn('checked chronology', checked)

    def test_profile_candidates_show_recorded_life_dates(self):
        html = profile_links({'profile_ids': ['Glasgow-951', 'Glasgow-3904']}, WEB)
        self.assertIn('b. c. 1811; d. 1888', html)
        self.assertIn('b. c. 1770; d. ?', html)
        self.assertIn('href="/people/glasgow-951.html"', html)

    def test_candidate_dates_preserve_dossier_boundaries(self):
        html = profile_links({'profile_ids': ['Glasco-170', 'Glasco-148', 'Glasgow-3944']}, WEB)
        self.assertIn('b. before 1766; d. before 1784', html)
        self.assertIn('d. after 1793', html)
        self.assertIn('b. before 1726', html)
        self.assertNotIn('c. before', html)
        self.assertNotIn('c. after', html)

    def test_excluded_curated_candidate_is_labeled_without_promoting_identity(self):
        html = profile_links({'profile_ids': ['Glasgow-951'], 'profile_matches': [{'profile_id': 'Glasgow-951', 'confidence': 'excluded', 'role': 'comparison name', 'basis': 'conflicting chronology'}]}, WEB)
        self.assertIn('sc-confidence-excluded', html)
        self.assertIn('conflicting chronology', html)

    def test_publisher_preserves_curated_profile_match_fields_for_cards(self):
        self.assertIn('profile_matches', PUBLIC_ROW_FIELDS)
        data = {'rows': [{'image_id': 'x', 'date': '1746-01-01', 'paper': 'Weekly Worcester Journal',
                          'page': 1, 'source_url': 'https://www.newspapers.com/image/123/',
                          'status': 'confirmed surname', 'reading': 'A reading', 'assessment': 'Checked.',
                          'profile_ids': ['Glasgow-2375'], 'profile_matches': [{'profile_id': 'Glasgow-2375',
                          'confidence': 'probable', 'role': 'record subject', 'basis': 'dated place match'}]}],
                'limitations': [], 'conclusion': '', 'scope': '', 'reviewed_at': ''}
        html = render_newspaper_review(data)
        self.assertIn('probable', html)
        self.assertIn('record subject', html)
        self.assertIn('dated place match', html)
        self.assertEqual(newspaper_country('Weekly Worcester Journal'), 'England')

    def test_new_american_papers_reach_country_and_year_routes(self):
        papers = [
            'The North-Carolina Journal', 'North-Carolina Journal',
            'The State Gazette of North-Carolina', 'State Gazette of North Carolina',
            'Weekly Raleigh Register', 'Raleigh Minerva', 'Newbern Gazette',
            "Kline's Carlisle Weekly Gazette", 'Kentucky Gazette',
            'The Encyclopedian Instructor',
            'The Carlisle Gazette, and the Western Repository of Knowledge',
            'The North Carolina Gazette, or, Impartial Intelligencer, and Weekly General Advertiser',
            'North-Carolina Gazette and Wilmington Weekly Post-Boy',
        ]
        for paper in papers:
            with self.subTest(paper=paper):
                self.assertEqual(newspaper_country(paper), 'United States')
        self.assertEqual(newspaper_country('An unreviewed Carlisle paper'), 'Unresolved')

    def test_group_keeps_each_assessment_and_uses_selected_clip_metadata(self):
        rows = [
            {'image_id':'a', 'date':'1800-01-01', 'paper':'A', 'page':1, 'status':'confirmed surname',
             'reading':'Same', 'source_url':'https://a', 'assessment':'First assessment.'},
            {'image_id':'b', 'date':'1801-01-01', 'paper':'B', 'page':2, 'status':'confirmed surname',
             'reading':'Same', 'source_url':'https://b', 'assessment':'Second assessment.'},
        ]
        clips = {'b': {'url':'/b.png', 'width':10, 'height':10, 'caption_note':'B crop.'}}
        html = newspaper_card(rows[0], clips, WEB, rows)
        self.assertIn('Source reference: B · 1801-01-01 · p. 2', html)
        self.assertIn('First assessment.', html)
        self.assertIn('Second assessment.', html)
        self.assertEqual(html.count('<figure>'), 1)

    def test_selected_and_alternative_issue_crops_are_inline_figures(self):
        rows = [{'image_id':'a', 'date':'1800-01-01', 'paper':'A', 'page':1, 'status':'confirmed surname',
                 'reading':'Same', 'source_url':'https://a', 'assessment':'A.'},
                {'image_id':'b', 'date':'1801-01-01', 'paper':'B', 'page':2, 'status':'confirmed surname',
                 'reading':'Same', 'source_url':'https://b', 'assessment':'B.'}]
        clips = {'a': {'url':'/a.png', 'width':10, 'height':10, 'caption_note':'opening',
                       'additional_excerpts':[{'url':'/a-more.png', 'width':10, 'height':10, 'caption_note':'continuation'}]},
                 'b': {'url':'/b.png', 'width':10, 'height':10, 'caption_note':'alternate'}}
        html = newspaper_card(rows[0], clips, WEB, rows)
        self.assertIn('Additional excerpts from this issue', html)
        self.assertIn('/a-more.png', html)
        soup = BeautifulSoup(html, 'html.parser')
        disclosure = next(d for d in soup.select('details')
                          if 'Alternative saved issue excerpts' in d.summary.get_text())
        self.assertIsNotNone(disclosure)
        alt_img = disclosure.select_one('figure img')
        self.assertEqual(alt_img['src'], '/b.png')
        self.assertEqual(alt_img['loading'], 'lazy')
        caption = disclosure.select_one('figcaption')
        self.assertIn('B · 1801-01-01 · p. 2', caption.get_text(' ', strip=True))
        self.assertEqual(caption.find('a', href='https://b').get_text(), 'original page')
        self.assertEqual(len(soup.select('article')), 1)
        self.assertEqual(len(soup.select('article .sc-newspaper-reading p strong')), 2)
        self.assertEqual(soup.select_one('.sc-newspaper-reading').get_text().count('Same'), 1)
        self.assertEqual(len(soup.select('figure')), 3)
        self.assertEqual({img['src'] for img in soup.select('figure img')}, {'/a.png', '/a-more.png', '/b.png'})

    def test_all_retained_pre1800_pages_have_visible_excerpts(self):
        soup = BeautifulSoup((WEB/'sources/newspapers/index.html').read_text(), 'html.parser')
        early = [r for r in self.newspapers['rows'] if r['status']=='confirmed surname' and r['date'][:4].isdigit() and int(r['date'][:4])<1800]
        self.assertTrue(early)
        manifest = json.loads((ROOT/'research/source-library/newspaper-clippings.json').read_text())
        clips = {str(a['image_id']): a for a in manifest['assets']}
        clips.update({str(a['image_id']): a for a in manifest['assets'] for a in a.get('additional_excerpts', [])})
        for row in [r for r in self.newspapers['rows'] if r['status'] in ('confirmed surname','place study')]:
            card = soup.find(id='newspaper-'+str(row['image_id']))
            article = card.find_parent('article') or card
            if str(row['image_id']) in clips:
                self.assertTrue(article.find('img', src='/' + clips[str(row['image_id'])]['public_path']) or article.find('a', href='/' + clips[str(row['image_id'])]['public_path']), row['image_id'])
            if row in early:
                self.assertNotIn('Saved excerpt pending', article.get_text())
        cargo = soup.find(id='newspaper-72017846')
        cargo_asset = next(a for a in manifest['assets'] if str(a['image_id']) == '72017846')
        expected_cargo_excerpts = 1 + len(cargo_asset.get('additional_excerpts', []))
        self.assertEqual(len(cargo.select('figure img')), expected_cargo_excerpts)
        self.assertEqual(len({img['src'] for img in cargo.select('figure img')}), expected_cargo_excerpts)
        self.assertIn('Separate cargo advertisement', cargo.get_text())

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
