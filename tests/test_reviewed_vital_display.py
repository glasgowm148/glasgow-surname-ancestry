import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from tools.reviewed_vital_display import apply, refresh_family_summaries


class ReviewedVitalDisplayTests(unittest.TestCase):
    def test_reviewed_death_boundary_removes_stale_exact_metadata(self):
        from bs4 import BeautifulSoup
        from tools import repair_person_hierarchy as renderer
        with TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'people').mkdir()
            dossier=dict(research_assessments=[dict(status='approved',vitals={'death':{}})],
                         vitals=dict(death=dict(date='after 1805-10-14',status='after',place='Death parish')))
            (root/'people/example-1.json').write_text(json.dumps(dossier))
            html='<html><head><script type="application/ld+json">{"@type":"Person","birthDate":"1757-11-28","deathDate":"1805-08-14","deathPlace":"Old parish"}</script></head><body><main>Old account</main></body></html>'
            with patch.object(renderer,'WEB',root), patch.object(renderer,'render_person_dossier',return_value='<h1>Example Person</h1>'), patch.object(renderer,'_set_top_bar_crumbs'), patch.object(renderer,'_ensure_unified_person_shell',side_effect=lambda soup,ident:soup):
                result=BeautifulSoup(renderer._replace_main(html,'Example-1'),'html.parser')
            data=json.loads(result.select_one('script[type="application/ld+json"]').string)
            self.assertNotIn('deathDate',data)
            self.assertEqual('Death parish',data['deathPlace'])
            self.assertEqual('1757-11-28',data['birthDate'])

    def test_death_review_reaches_family_registry_without_changing_birth(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp)
            def write(path, value):
                path=root/path; path.parent.mkdir(parents=True,exist_ok=True)
                path.write_text(json.dumps(value))
            person=dict(id='Example-1',slug='example-1',name='Example Person',
                        birth='1757',birthPlace='Birth parish',country='birth',
                        death='1805-08-14',life='1757 – 14 August 1805',to=1805)
            write('assets/research/registry.json',[person])
            write('assets/v3/registry-packed.json',dict(fields=['slug','death','life'],rows=[['example-1',person['death'],person['life']]]))
            write('assets/research/branches.json',[])
            write('assets/research/palette.json',{})
            model=dict(meta={'reviewedVitalDisplay':{'Example-1':dict(died=1805,deathDisplay='After 14 October 1805',deathplace='Death parish',deathLocationRegion='death')}})
            refresh_family_summaries(model,root)
            row=json.loads((root/'assets/research/registry.json').read_text())[0]
            self.assertEqual(('1757','Birth parish','birth'),(row['birth'],row['birthPlace'],row['country']))
            self.assertEqual(('After 14 October 1805','Death parish','death',1805),(row['death'],row['deathPlace'],row['deathCountry'],row['to']))
            self.assertEqual('1757 – After 14 October 1805',row['life'])
            self.assertEqual(['example-1',row['death'],row['life']],json.loads((root/'assets/v3/registry-packed.json').read_text())['rows'][0])
            refresh_family_summaries(model,root)
            self.assertEqual(row,json.loads((root/'assets/research/registry.json').read_text())[0])

    def test_person_metadata_uses_the_rendered_current_name(self):
        from bs4 import BeautifulSoup
        from tools import repair_person_hierarchy as renderer
        html = '<html><head><title>Old label</title><meta property="og:title" content="Old label"><script type="application/ld+json">{"@type":"Person","name":"Old label","birthDate":"1700"}</script></head><body><main>Old account</main></body></html>'
        with patch.object(renderer, 'render_person_dossier', return_value='<h1>Recorded Person</h1>'), patch.object(renderer, '_set_top_bar_crumbs'), patch.object(renderer, '_ensure_unified_person_shell', side_effect=lambda soup, ident:soup):
            result = BeautifulSoup(renderer._replace_main(html, 'Example-1'), 'html.parser')
        self.assertTrue(result.title.string.startswith('Recorded Person'))
        self.assertEqual(result.title.string, result.select_one('meta[property="og:title"]')['content'])
        data = json.loads(result.select_one('script[type="application/ld+json"]').string)
        self.assertEqual('Recorded Person', data['name'])
        self.assertEqual('1700', data['birthDate'])

    def test_explicit_name_review_preserves_dates_and_parents(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'assets/research').mkdir(parents=True); (root/'people').mkdir()
            a = dict(subject='Example-1', status='approved', project_tree_display=True,
                     tree_projection=dict(name='Recorded Person', first='Recorded', surname='Person'))
            (root/'assets/research/assessments.json').write_text(json.dumps({'assessments': [a]}))
            (root/'people/example-1.json').write_text(json.dumps(dict(name='Recorded Person', research_assessments=[a])))
            person = dict(id='Example-1', name='Wrong label', born=1700, parents=[{'id':'Example-2'}], birthLocationRegion='birth', locationRegion='approved')
            apply(dict(people=[person], meta={}), root, lambda place:'other', {'birth':dict(label='Birth region', color='red')})
            self.assertEqual('Recorded Person', person['name'])
            self.assertEqual(1700, person['born'])
            self.assertEqual([{'id':'Example-2'}], person['parents'])
            self.assertEqual('approved', person['locationRegion'])

    def test_family_summary_and_packed_registry_follow_review(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp)
            def write(path,value):
                p=root/path;p.parent.mkdir(parents=True,exist_ok=True)
                p.write_text(value if isinstance(value,str) else json.dumps(value))
            person=dict(id='Example-1',slug='example-1',name='Example Person',birth='c. 1784',birthPlace='Scotland',country='scotland',life='c. 1784 – 1864')
            write('assets/research/registry.json',[person])
            write('assets/v3/registry-packed.json',dict(fields=['slug','birth','country'],rows=[['example-1','c. 1784','scotland']]))
            write('assets/research/branches.json',[dict(id='family-example-1',kind='family',root='example-1',rootId='Example-1',label='Example Person · c. 1784',members=['example-1'],count=1,record_count=1)])
            write('assets/research/palette.json',dict(ireland=dict(label='Ireland',color='green'),other=dict(label='Other',color='grey')))
            write('branches/family-example-1/index.html','<header class="r-page-head"><h1>Example Person · c. 1784</h1><p class="r-lead">Old summary</p></header><div class="r-country-legend">Scotland 1</div><a href="/people/example-1.html"><small>c. 1784 · Scotland</small></a>')
            model=dict(meta={'reviewedVitalDisplay':{'Example-1':dict(born=1774,birthDisplay='About 1774',birthplace='Ireland',birthLocationRegion='ireland')}})
            refresh_family_summaries(model,root)
            registry=json.loads((root/'assets/research/registry.json').read_text())
            self.assertEqual(registry[0]['life'],'About 1774 – 1864')
            self.assertEqual(json.loads((root/'assets/v3/registry-packed.json').read_text())['rows'][0],['example-1','About 1774','ireland'])
            page=(root/'branches/family-example-1/index.html').read_text()
            self.assertIn('About 1774 · Ireland',page);self.assertNotIn('Scotland',page)
            refresh_family_summaries(model,root)
            self.assertEqual((root/'branches/family-example-1/index.html').read_text(),page)

    def test_explicit_review_preserves_family_and_unreviewed_death(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'assets/research').mkdir(parents=True);(root/'people').mkdir()
            assessment=dict(subject='Example-1',status='approved',project_tree_vitals=True,vitals={'birth':{}})
            (root/'assets/research/assessments.json').write_text(json.dumps({'assessments':[assessment]}))
            (root/'people/example-1.json').write_text(json.dumps(dict(research_assessments=[assessment],vitals={'birth':dict(date='1774',display_date='About 1774',place='Ireland',status='estimated')})))
            person=dict(id='Example-1',born=1784,died=1864,parents=[{'id':'Example-2'}],birthLocationRegion='scotland')
            model=dict(people=[person],meta={});regions={'ireland':{'label':'Ireland','color':'green'}}
            display=apply(model,root,lambda place:'ireland',regions)
            self.assertEqual(person['born'],1774);self.assertEqual(person['birthplace'],'Ireland')
            self.assertEqual(person['birthDisplay'],'About 1774');self.assertTrue(person['bornApprox'])
            self.assertEqual(person['parents'],[{'id':'Example-2'}]);self.assertEqual(person['died'],1864)
            self.assertEqual(display['Example-1']['locationRegion'],'ireland')

    def test_no_explicit_projection_leaves_existing_display(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'assets/research').mkdir(parents=True)
            (root/'assets/research/assessments.json').write_text(json.dumps({'assessments':[dict(subject='Example-1',status='approved')]}))
            model=dict(people=[dict(id='Example-1',born=1784)],meta={})
            self.assertEqual(apply(model,root,lambda place:'other',{}),{})
            self.assertEqual(model['people'][0]['born'],1784)

    def test_incomplete_replacement_is_rejected(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'assets/research').mkdir(parents=True);(root/'people').mkdir()
            a=dict(subject='Example-1',status='approved',project_tree_vitals=True,vitals={'birth':{}})
            (root/'assets/research/assessments.json').write_text(json.dumps({'assessments':[a]}))
            (root/'people/example-1.json').write_text(json.dumps(dict(research_assessments=[a],vitals={'birth':dict(date='1774',place='')})))
            with self.assertRaises(ValueError):apply(dict(people=[dict(id='Example-1')],meta={}),root,lambda place:'other',{})
