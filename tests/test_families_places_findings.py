"""Families, places, latest findings and research questions joined through data (site audit lane I4)."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

from bs4 import BeautifulSoup

from tools import study_place_links as links
from tools import build_latest_findings as findings
from tools import repair_research_questions as questions

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('build_study_pages_i4', ROOT / 'tools/build_study_pages.py')
studies = importlib.util.module_from_spec(spec)
spec.loader.exec_module(studies)
ATOM = '{http://www.w3.org/2005/Atom}'


class StudyPlaceLinkTests(unittest.TestCase):
    records = [
        {'catalogue_id': 'glasgow-1', 'location_id': 'kilwaughter', 'record_location': 'Kilwaughter', 'region': 'Ireland', 'record_category': 'Marriages | Church records'},
        {'catalogue_id': 'glasgow-2', 'location_id': 'kilwaughter', 'record_location': 'Kilwaughter', 'region': 'Ireland', 'record_category': 'Wills and probate'},
        {'catalogue_id': 'glasgow-2', 'location_id': 'Larne Town', 'record_location': 'Larne', 'region': 'Ireland'},
        {'catalogue_id': 'smith-9', 'location_id': 'kilwaughter', 'record_location': 'Kilwaughter', 'region': 'Ireland'},
    ]
    branches = [
        {'id': 'larne', 'label': 'Larne & Kilwaughter', 'kind': 'place', 'type': links.PLACE_STUDY, 'url': '/branches/larne/', 'members': ['glasgow-1', 'glasgow-2']},
        # Same name as the place, but nobody in it is recorded there: never linked.
        {'id': 'kilwaughter-name-only', 'label': 'Kilwaughter', 'kind': 'research', 'type': links.FAMILY_STUDY, 'url': '/branches/kilwaughter-name-only/', 'members': ['glasgow-7']},
        {'id': 'family-glasgow-1', 'label': 'Tree group', 'kind': 'family', 'type': links.TREE_GROUP, 'url': '/branches/family-glasgow-1/', 'members': ['glasgow-1']},
    ]

    def test_places_for_a_study_come_from_its_people_records(self):
        by_person = links.person_places(self.records)
        places = links.places_for_people(['glasgow-1', 'glasgow-2'], by_person)
        self.assertEqual([('kilwaughter', 2), ('larne-town', 1)], [(p['slug'], p['people']) for p in places])
        self.assertEqual('/places/kilwaughter.html', places[0]['url'])
        self.assertEqual([], links.places_for_people(['glasgow-7'], by_person))
        only = links.places_for_people(['glasgow-2'], by_person, place_exists=lambda slug: slug == 'kilwaughter')
        self.assertEqual(['kilwaughter'], [p['slug'] for p in only])

    def test_studies_for_a_place_never_match_by_name(self):
        index = links.studies_by_person(self.branches)
        people = [r['catalogue_id'] for r in self.records if r['location_id'] == 'kilwaughter']
        found = links.studies_for_people(people, index)
        self.assertEqual(['larne'], [s['id'] for s in found])
        self.assertEqual(2, found[0]['people'])
        groups = links.studies_for_people(people, index, kinds=(links.TREE_GROUP_KIND,))
        self.assertEqual(['family-glasgow-1'], [g['id'] for g in groups])
        html = links.render_place_studies(found, groups, [], findings=3, slug='kilwaughter')
        soup = BeautifulSoup(html, 'html.parser')
        self.assertEqual('Families studied here', soup.h2.text)
        self.assertEqual('/branches/larne/', soup.select_one('.place-study-list a')['href'])
        self.assertIn('not all been checked', soup.select_one('.place-tree-groups').text)
        self.assertEqual('/latest-findings/places/#place-kilwaughter', soup.select_one('.place-findings a')['href'])
        empty = BeautifulSoup(links.render_place_studies([], [], []), 'html.parser')
        self.assertIn('No family study covers', empty.text)

    def test_source_library_links_only_existing_collections(self):
        rows = links.source_collections(self.records[:2], collection_exists=lambda folder, country: folder != 'church')
        self.assertEqual({'/sources/marriages/ireland/', '/sources/wills-probate/ireland/'}, {r['url'] for r in rows})

    def test_one_label_per_kind_of_group(self):
        self.assertEqual(links.TREE_GROUP, links.study_type({'kind': 'family'}))
        self.assertEqual(links.PLACE_STUDY, links.study_type({'kind': 'place'}))
        self.assertEqual(links.HOUSEHOLD, links.study_type({'kind': 'research'}, 'Documented household'))
        self.assertEqual(links.POSSIBLE_GROUP, links.study_type({'kind': 'research'}, 'Locality / record cluster'))
        self.assertEqual(links.FAMILY_STUDY, links.study_type({'kind': 'research'}, 'Evidence-led study'))

    def test_study_places_block_and_group_insert_are_idempotent(self):
        places = [{'slug': f'p{i}', 'name': f'Place {i}', 'url': f'/places/p{i}.html', 'people': 1} for i in range(17)]
        soup = BeautifulSoup(links.render_study_places(places), 'html.parser')
        self.assertEqual('Places in this study', soup.h3.text)
        self.assertEqual(17, len(soup.select('a')))
        self.assertIn('2 more places', soup.summary.text)
        self.assertEqual('', links.render_study_places([]))
        page = '<main><h1>x</h1></main>'
        section = links.render_group_places(places[:2])
        once = links.insert_group_places(page, section)
        self.assertEqual(once, links.insert_group_places(once, section))


class StudyPageTextTests(unittest.TestCase):
    def setUp(self):
        studies.PEOPLE.clear()
        studies.PEOPLE.update({'glasgow-951': {'name': 'Alexander Glasgow'}, 'glasgow-1499': {'name': 'Hugh Glasgow'}})

    def tearDown(self):
        studies.PEOPLE.clear()

    def test_ids_in_prose_become_linked_names_only_when_the_registry_agrees(self):
        html = studies.inline('Alexander-951 and Glasgow-1499 differ from John-1499 and Glasgow-99999.')
        soup = BeautifulSoup(html, 'html.parser')
        self.assertEqual(['/people/glasgow-951.html', '/people/glasgow-1499.html'], [a['href'] for a in soup.select('a')])
        self.assertIn('John-1499', soup.text)  # first name disagrees: left as written
        self.assertIn('Glasgow-99999', soup.text)
        linked = BeautifulSoup(studies.inline('[Hugh-1499’s lease](/sources/x/)'), 'html.parser')
        self.assertEqual(1, len(linked.select('a')))
        self.assertEqual('Hugh Glasgow’s lease', linked.a.text)
        self.assertEqual('Alexander Glasgow → x', studies.plain_names('Alexander-951 → x'))

    def test_people_are_grouped_by_household_and_ordered_by_date(self):
        registry = {'a': {'name': 'A', 'from': '1790'}, 'b': {'name': 'B', 'from': '1750'}, 'c': {'name': 'C'}, 'd': {'name': 'D', 'from': '1700'}}
        clusters = [{'title': 'First household', 'people': ['a', 'b']}, {'title': 'Second', 'people': ['c']}]
        soup = BeautifulSoup(studies.people_list(['a', 'b', 'c', 'd'], clusters, registry), 'html.parser')
        self.assertEqual(['First household', 'Second', 'Others in this study'], [h.text for h in soup.select('.sp-people-group')])
        self.assertEqual(['B', 'A'], [a.text for a in soup.select('.sp-people')[0].select('a')])

    def test_link_labels_and_dates(self):
        self.assertEqual('Open the source ↗', studies.target_label('https://example.org/'))
        self.assertEqual('Read the study →', studies.target_label('/branches/x/'))
        self.assertEqual('6 October 2026', studies.long_date('2026-10-06'))
        self.assertEqual('', studies.long_date('2026-13-01'))
        block = BeautifulSoup(studies.findings_block([{'date': '2026-10-06', 'url': '/latest-findings/#finding-a', 'summary': 'A lease.'}], '/latest-findings/studies/x/'), 'html.parser')
        self.assertEqual('/latest-findings/#finding-a', block.select_one('.sp-findings a')['href'])
        self.assertIn('every finding about people in this study (1)', block.text)


class LatestFindingsSubjectTests(unittest.TestCase):
    rows = [
        {'id': 'b', 'found_on': '2026-10-06', 'kind': 'record', 'status': 'qualified', 'finding': 'Second & newer finding.',
         'qualification': 'Identity not proved.', 'people': [{'name': 'Hugh Glasgow', 'url': '/people/glasgow-1499.html'}],
         '_page_url': '/latest-findings/', '_people': ['glasgow-1499'], '_studies': [{'id': 'larne', 'label': 'Larne'}],
         '_places': [{'slug': 'larne-town', 'name': 'Larne'}]},
        {'id': 'a', 'found_on': '2026-09-30', 'kind': 'record', 'status': 'confirmed', 'finding': 'First finding.',
         'people': [], '_page_url': '/latest-findings/page/2/', '_people': [], '_studies': [], '_places': []},
    ]

    def test_subject_export_is_newest_first_and_readable(self):
        data = findings.subject_index(self.rows)
        self.assertEqual(['b'], data['people']['glasgow-1499'])
        self.assertEqual(['b'], data['studies']['larne'])
        self.assertEqual(['b'], data['places']['larne-town'])
        self.assertEqual('/latest-findings/studies/larne/', data['study_pages']['larne'])
        self.assertEqual('/latest-findings/page/2/#finding-a', data['findings']['a']['url'])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / findings.SUBJECT_INDEX
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps(data))
            self.assertEqual(['b'], [f['id'] for f in findings.findings_for('Glasgow-1499', web=Path(directory))])
            self.assertEqual([], findings.findings_for('nobody', 'places', web=Path(directory)))

    def test_atom_feed_is_well_formed(self):
        feed = ET.fromstring(findings.atom_feed(self.rows).encode('utf-8'))
        entries = feed.findall(f'{ATOM}entry')
        self.assertEqual(2, len(entries))
        self.assertEqual('2026-10-06T00:00:00Z', feed.find(f'{ATOM}updated').text)
        self.assertIn('Second & newer', entries[0].find(f'{ATOM}title').text)
        self.assertTrue(entries[0].find(f'{ATOM}link').get('href').endswith('/latest-findings/#finding-b'))

    def test_published_feed_and_head_link(self):
        feed = ROOT / 'www/latest-findings/feed.xml'
        if not feed.exists():
            self.skipTest('latest findings not built')
        root = ET.parse(feed).getroot()
        self.assertEqual(f'{ATOM}feed', root.tag)
        self.assertTrue(root.findall(f'{ATOM}entry'))
        head = BeautifulSoup((ROOT / 'www/latest-findings/index.html').read_text(encoding='utf-8'), 'html.parser').head
        link = head.select_one('link[rel="alternate"][type="application/atom+xml"]')
        self.assertEqual('/latest-findings/feed.xml', link['href'])


class ResearchQuestionLinkTests(unittest.TestCase):
    def test_question_links_are_well_formed_and_local_where_possible(self):
        for region, title, *_rest, url in questions.ADDITIONAL_QUESTIONS:
            self.assertFalse(url.endswith(("'", '"')), title)
            self.assertNotEqual('https://www.wikitree.com/wiki/Space:Glasgow%20Name%20Study', url, title)

    def test_every_question_names_its_people_or_study(self):
        keys = [q[0] for q in questions.QUESTIONS] + [q[1] for q in questions.ADDITIONAL_QUESTIONS]
        self.assertEqual(set(keys), set(questions.QUESTION_SUBJECTS))
        if not (ROOT / 'www/assets/research/registry.json').exists():
            self.skipTest('site not built')
        for key in keys:
            soup = BeautifulSoup(questions.subjects_html(key), 'html.parser')
            hrefs = [a['href'] for a in soup.select('a')]
            self.assertTrue(hrefs, key)
            self.assertTrue(all(h.startswith(('/people/', '/branches/')) for h in hrefs), key)


if __name__ == '__main__':
    unittest.main()
