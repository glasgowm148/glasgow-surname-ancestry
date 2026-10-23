import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from tools.reviewed_vital_display import apply, refresh_family_summaries


class ReviewedVitalDisplayTests(unittest.TestCase):
    def test_explicit_name_review_preserves_dates_and_parents(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'assets/research').mkdir(parents=True); (root/'people').mkdir()
            a = dict(subject='Example-1', status='approved', project_tree_display=True,
                     tree_projection=dict(name='Recorded Person', first='Recorded', surname='Person'))
            (root/'assets/research/assessments.json').write_text(json.dumps({'assessments': [a]}))
            (root/'people/example-1.json').write_text(json.dumps(dict(name='Recorded Person', research_assessments=[a])))
            person = dict(id='Example-1', name='Wrong label', born=1700, parents=[{'id':'Example-2'}])
            apply(dict(people=[person], meta={}), root, lambda place:'other', {})
            self.assertEqual('Recorded Person', person['name'])
            self.assertEqual(1700, person['born'])
            self.assertEqual([{'id':'Example-2'}], person['parents'])

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
