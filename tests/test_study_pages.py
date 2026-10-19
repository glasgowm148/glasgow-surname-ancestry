import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from unittest.mock import patch

from tests._generated_data import requires_generated_data
from collections import Counter
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('build_study_pages', ROOT/'tools/build_study_pages.py')
renderer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(renderer)


def study_manifest():
    """Return every branch whose page is maintained by the study renderer."""
    branches = json.loads((ROOT/'www/assets/research/branches.json').read_text())
    return [
        branch for branch in branches
        if branch['id'].startswith('research-')
        or branch['id'] in ('larne-kilwaughter', 'lisnagaver-rasharkin', 'early-scottish-records')
    ]


class StudyPagesTests(unittest.TestCase):
    def test_working_connections_keep_jump_links(self):
        story = {'chapters': [{'id': 'working-links', 'anchor_alias': 'working-links',
                               'title': 'Working family', 'body': ['Reasoning and alternatives.']}]}
        html = renderer.render(dict(id='fixture', label='Fixture', members=[]), {}, [], story,
                               {}, [], {'territories': [], 'counties': []})
        page = BeautifulSoup(html, 'html.parser')
        self.assertIsNotNone(page.select_one('#chapter-working-links'))
        self.assertEqual(page.select_one('#working-links').find_next('article')['id'], 'chapter-working-links')
        ids = [node['id'] for node in page.select('[id]')]
        self.assertEqual(len(ids), len(set(ids)))

    @requires_generated_data
    def test_generated_pages(self):
        studies = study_manifest()
        self.assertTrue(studies)
        for b in studies:
            with self.subTest(study=b['id']):
                soup = BeautifulSoup((ROOT/f'www/branches/{b["id"]}/index.html').read_text(), 'html.parser')
                main = soup.select_one('main.sp-page')
                self.assertIsNotNone(main)
                for name in ('hero','question','evidence'):
                    self.assertEqual(1,len(main.select(f'section#study-{name}')))
                self.assertIsNone(main.select_one('canvas'))
                # ?v= values are content hashes set by tools/stamp_asset_versions.py.
                self.assertEqual(1,len(soup.select('link[href^="/assets/research/study-page.css?v="]')))
                self.assertTrue(soup.select_one('script[src^="/assets/research/study-page.js?v="]').has_attr('defer'))
                people = {a['href'] for a in main.select('.sp-all-people a')}
                # Members without a published page are printed as names, not links.
                self.assertEqual({f'/people/{p}.html' for p in b['members'] if (ROOT/f'www/people/{p}.html').is_file()}, people)
                ids = [node['id'] for node in main.select('[id]')]
                self.assertEqual(len(ids),len(set(ids)))
                paragraphs = [' '.join(p.stripped_strings) for p in main.select('p') if 'sp-keep' not in (p.get('class') or [])]
                self.assertEqual(len(paragraphs),len(set(paragraphs)))
                self.assertNotIn('[...]',main.text)

    def test_minimal_story_and_empty_optional_arrays(self):
        branch = dict(id='fixture',label='Fixture study',members=['example-1'])
        geo = {'territories': [], 'counties': []}
        for authored in ({'id':'fixture'}, {'id':'fixture','clusters':[],'chapters':[],'timeline':[],'gaps':[],'ladder':{}}, {'id':'fixture','clusters':[{}],'chapters':[{}],'timeline':[{}],'gaps':[{}],'facts':[{}],'status':{}}):
            html = renderer.render(branch,{},[],authored,{},[],geo)
            soup = BeautifulSoup(html,'html.parser')
            self.assertEqual('Fixture study',soup.h1.text)
            self.assertIsNone(soup.select_one('#study-map'))
            self.assertIsNone(soup.select_one('#study-timeline'))
            # The fixture member has no page in www/, so the name is printed without a link.
            self.assertIsNone(soup.select_one('a[href="/people/example-1.html"]'))
            self.assertIn('example-1', soup.select_one('.sp-no-page').text)

    def test_fallback_deduplicates_and_omits_whole_group(self):
        branch = dict(id='fixture',label='Fixture',members=['example-1'],description='One unique assessment.')
        soup = BeautifulSoup(renderer.render(branch,{},[],{}, {},[],{'territories':[],'counties':[]}), 'html.parser')
        self.assertEqual(1,soup.text.count('One unique assessment.'))
        self.assertIsNone(soup.select_one('#study-clusters'))
        self.assertIsNone(soup.select_one('#study-story'))
        self.assertIsNone(soup.select_one('.sp-connections'))

    def test_malformed_optional_fields(self):
        story = dict(clusters=[None,{'id':[],'people':{},'status':[]}],chapters=[None,{'body':23,'evidence':[None]}],timeline=[None,{'year':1700,'cluster':[]}],links=[{'from':[],'to':{}}],status='bad',ladder={'proved':5},evidence_log={'source':[]},facts=[None],gaps=[None])
        renderer.render(dict(id='fixture',label='Fixture',members=[]),{},[],story,{},[],{'territories':[],'counties':[]})

    def test_timeline_only_occupied_lanes_and_wrapped_labels(self):
        story = {'clusters':[{'id':'empty','title':'Empty'},{'id':'one','title':'Occupied'}], 'timeline':[{'year':1750,'cluster':'one','label':'A long selected event label with enough words to wrap across two useful lines without losing its accessible description'}]}
        soup = BeautifulSoup(renderer.timeline(story,[]),'html.parser')
        wide = soup.select_one('svg.sp-timeline-wide')
        self.assertIsNotNone(soup.select_one('svg.sp-timeline-narrow'))
        self.assertEqual(['Occupied'],[e.text for e in wide.select('.sp-lane-label')])
        self.assertEqual(2,len(wide.select('.sp-event-label tspan')))
        self.assertEqual(1,len(soup.select('ol li')))
        self.assertNotIn('[...]',soup.text)
        self.assertIn(story['timeline'][0]['label'],soup.ol.text)

    def test_connection_filters_and_chronological_layout(self):
        story = {'clusters':[{'id':'a','title':'Earlier','period':'1710s'},{'id':'b','title':'Later','period':'eighteenth century'},{'id':'c','title':'Unlinked','period':'1800'}], 'links':[{'from':'a','to':'b','label':'Evidence'},{'from':'a','to':'b','label':'Evidence'},{'from':'a','to':'a'},{'from':'a','to':'missing'}]}
        soup = BeautifulSoup(renderer.connections(story),'html.parser')
        self.assertEqual(1,len(soup.select('.sp-edge')))
        self.assertEqual(3,len(soup.select('.sp-node-band')))
        # The links are listed in words and open by default (site audit S3-09): the diagram's labels are not hover-only.
        self.assertTrue(soup.details.has_attr('open'))
        self.assertIn('Earlier → Later', soup.details.text)
        nodes = soup.select('.sp-node > rect:first-of-type')
        self.assertLess(float(nodes[0]['y']),float(nodes[1]['y']))
        self.assertEqual('',renderer.connections({'clusters':story['clusters'],'links':[]}))

    def test_long_links_route_between_rows_and_endpoints_spread(self):
        story = {'clusters':[{'id':'a','title':'A','period':'1650'},{'id':'b','title':'B','period':'1700'},{'id':'c','title':'C','period':'1750'},{'id':'d','title':'D','period':'1752'}],
                 'links':[{'from':'a','to':'b','status':'proved'},{'from':'a','to':'c','status':'hypothesis'},{'from':'a','to':'d','status':'unresolved'},{'from':'c','to':'d','status':'supported'}]}
        soup = BeautifulSoup(renderer.connections(story),'html.parser')
        self.assertEqual(4,len(soup.select('path.sp-edge')))
        starts = [e['d'].split()[0] for e in soup.select('path.sp-edge') if e['data-from']=='a']
        self.assertEqual(len(starts),len(set(starts)))  # three edges leave A at distinct points
        self.assertTrue(soup.select_one('path.sp-edge.sp-unresolved title'))

    def test_map_drops_distant_outliers(self):
        geo = {'territories':[],'counties':[],'helper':{'_rings':lambda g: []}}
        rows = [{'longitude':'-6.5','latitude':'54.95','record_precision':'Townland centrepoint'} for _ in range(3)]+[{'longitude':'-83.9','latitude':'42.0','record_precision':'Settlement centrepoint'}]
        soup = BeautifulSoup(renderer.locator('fixture',rows,geo),'html.parser')
        self.assertEqual(3,len(soup.select('circle')))
        self.assertIn('1 more distant record location is outside this view',soup.figcaption.text)

    def test_single_point_map_window(self):
        geo = {'territories':[],'counties':[],'helper':{'_rings':lambda g: []}}
        soup = BeautifulSoup(renderer.locator('fixture',[{'longitude':'-6','latitude':'55','record_precision':'parish'}],geo),'html.parser')
        self.assertEqual('0 0 480 360',soup.svg['viewbox'])
        self.assertAlmostEqual(240,float(soup.circle['cx']))
        self.assertAlmostEqual(180,float(soup.circle['cy']))

    def test_safe_inline_markup(self):
        html = renderer.inline('<script>x</script> **Bold** [good](https://example.org) [bad](javascript:alert)')
        soup = BeautifulSoup(html,'html.parser')
        self.assertIsNone(soup.script)
        self.assertEqual('Bold',soup.strong.text)
        self.assertEqual(['https://example.org'],[a['href'] for a in soup.select('a')])

    def test_timeline_uses_member_records_and_story_events(self):
        story = {'clusters':[{'id':'one','title':'Household','people':['example-1']}], 'timeline':[{'year':1750,'label':'Original deed','status':'proved','cluster':'one'}]}
        rows = [{'year':'1701','profile_id':'Example-1','person':'Example person','association':'Householder'}]
        soup = BeautifulSoup(renderer.timeline(story,rows),'html.parser')
        self.assertEqual(2,len(soup.select('svg.sp-timeline-wide circle title')))
        self.assertIn('1701',soup.select_one('ol li').text)
        self.assertTrue(soup.select_one('circle.sp-proved'))

    def test_record_confidence_does_not_promote_profile_leads(self):
        self.assertEqual('unresolved',renderer.record_tone({'evidence':'One-Tree profile lead'}))
        self.assertEqual('supported',renderer.record_tone({'evidence':'Documented derivative register','source_status':'Original not inspected'}))
        self.assertEqual('proved',renderer.record_tone({'source_status':'Original civil register inspected'}))

    def test_evidence_accordion_preserves_tables_and_links(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            (root/'notes.md').write_text('## First\n[Record](https://example.org)\n\n### Second\n| A | B |\n|---|---|\n| 1 | 2 |\n')
            # Keep the repository sanitizer while testing the source in a temp root.
            original_run = renderer.runpy.run_path
            with patch.object(renderer,'ROOT',root), patch.object(renderer.runpy,'run_path',side_effect=lambda _: original_run(str(ROOT/'tools/repair_person_hierarchy.py'))):
                soup = BeautifulSoup(renderer.evidence_log({'source':'notes.md'},'fixture'),'html.parser')
            self.assertEqual(2,len(soup.select('details')))
            self.assertTrue(soup.details.has_attr('open'))
            self.assertIsNotNone(soup.table)
            self.assertEqual('https://example.org',soup.a['href'])

    @requires_generated_data
    def test_repair_is_idempotent(self):
        # Run on a copy: tests must never rewrite the published site.
        import shutil
        with tempfile.TemporaryDirectory() as tmp:
            web = Path(tmp)/'www'
            for part in ('assets/research','map/data','branches'):
                shutil.copytree(ROOT/'www'/part, web/part)
            with patch.object(renderer,'WEB',web):
                renderer.repair()
                result = renderer.repair()
        self.assertIsInstance(result,Counter)
        self.assertEqual(len(study_manifest()), result['study_pages'])
        self.assertEqual(0,result['study_pages_updated'])


if __name__ == '__main__':
    unittest.main()
