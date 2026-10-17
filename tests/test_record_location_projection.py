from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from tools.project_record_locations import (fingerprint, load_projections, project,
                                            project_points, project_csv, stable_record_id)


class RecordLocationProjectionTests(unittest.TestCase):
    def review(self):
        old=dict(year='1700–1770', record_location='Wrong parish', association='Profile locality')
        fields=dict(year='1770', filter_year=1770, record_location='Right parish',
                    association='Recorded residence; not birthplace', location_id='right',
                    source_title='Dated notice', source_url='https://example.org/notice',
                    canonical_source_ids=['notice'])
        return dict(id='Person-1', assessment_id='review-1', publication_status='approved',
                    source_ids=['notice'], vitals={'death':{'place':'Right parish','place_status':'uncertain','qualifier':'Residence; death place inferred'}},
                    map_projection=dict(record_id='0123456789abcdef', match_fingerprints=[old,fingerprint(fields)],
                        record_fields=fields, compact_fields=dict(year='1770',y=1770,place='Right parish',location_id='right'),
                        person_fields=dict(locations=['County','Right parish'],recorded_in=['Right parish']),
                        point=dict(lat=51.0,lon=-1.0,name='Right parish',location_ids=['right']),
                        previous_point=dict(lat=52.0,lon=-2.0,name='Wrong parish',location_ids=['wrong'],items=[['0123456789abcdef','person-1',1700,False]]),
                        previous_location_id='wrong',previous_place_route='/places/wrong.html',
                        reassignment_html='<h1>Reassigned</h1><a href="/places/right.html">Right parish</a>'))

    def fixture(self, root):
        review=self.review();rid=review['map_projection']['record_id']
        registry=root/'registry.json';registry.write_text(json.dumps({'chronology':[review]}))
        old={'record_id':rid,'catalogue_id':'person-1','year':'1700–1770','filter_year':1700,
             'record_location':'Wrong parish','location_id':'wrong','source_url':'https://example.org/profile',
             'document_id':'old-source','person':'Person One','unrelated':'preserve'}
        points=[deepcopy(review['map_projection']['previous_point']),dict(lat=51.0,lon=-1.0,name='Right parish',location_ids=['right'],items=[['other','person-2',1710,False]])]
        data={
            'data/records-index.json':[old,{'record_id':'other','catalogue_id':'person-2','location_id':'right'}],
            'assets/research/record-index.json':[{'id':rid,'p':'person-1','year':'1700–1770','y':1700,'place':'Wrong parish','document_id':'old-source'}, {'id':'other','p':'person-2','location_id':'right','y':1710}],
            f'assets/research/records/{rid}.json':old,
            'assets/research/map-points.json':points,
            'assets/research/event-index.json':[{'p':'person-1','id':'birth','place':'County'},{'p':'person-1','id':'death','place':'Wrong parish','date':'1770-01-01'},{'p':'person-2','id':'death','place':'Elsewhere'}],
            'assets/research/place-index.json':[dict(id='wrong',record_ids=[rid],members=['person-1'],records=1,people=1,year_from=1700,year_to=1700),dict(id='right',record_ids=['other'],members=['person-2'],records=1,people=1,year_from=1710,year_to=1710)],
            'data/resolve/person-one.json':{'query':{'name':'Person One'},'candidates':[{'id':'Person-1','death_place':'Wrong parish','locations':['County','Wrong parish']},{'id':'Person-2','death_place':'Elsewhere'}]},
            'people/person-1.json':{'id':'Person-1','vitals':{'birth':{'place':'County','date':'1700','status':'uncertain'},'death':{'place':'Wrong parish','date':'1770-01-01','status':'exact'}},'imported':{'vitals':{'death':{'place':'Wrong parish'}}},'identity':{'locations':['County','Wrong parish'],'occupation':'farmer'}}}
        for name,value in data.items():
            p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(value))
        p=root/'places/wrong.html';p.parent.mkdir(exist_ok=True);p.write_text('<html><nav>Keep</nav><main><h1>Wrong</h1></main><footer>Keep</footer></html>')
        return registry,data

    def test_stable_id_survives_corrected_year_and_place_but_not_other_records(self):
        review=self.review();p=review['map_projection']
        self.assertEqual(stable_record_id(p['match_fingerprints'][0],'person-1',1,[review]),p['record_id'])
        self.assertEqual(stable_record_id(p['record_fields'],'person-1',99,[review]),p['record_id'])
        self.assertNotEqual(stable_record_id(p['record_fields'],'person-2',1,[review]),p['record_id'])
        self.assertNotEqual(stable_record_id(dict(p['record_fields'],year='1780'),'person-1',1,[review]),p['record_id'])

    def test_idempotent_projection_preserves_birth_imports_and_unrelated_records_then_rolls_back(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);registry,original=self.fixture(root)
            report=project(root,registry,write=True)
            self.assertTrue(report['changed'])
            self.assertFalse(project(root,registry,write=True)['changed'])
            person=json.loads((root/'people/person-1.json').read_text())
            self.assertEqual(person['vitals']['birth'],original['people/person-1.json']['vitals']['birth'])
            self.assertEqual(person['imported'],original['people/person-1.json']['imported'])
            self.assertEqual(person['identity']['occupation'],'farmer')
            records=json.loads((root/'data/records-index.json').read_text())
            self.assertEqual(records[1],original['data/records-index.json'][1])
            self.assertEqual(records[0]['record_id'],'0123456789abcdef')
            self.assertEqual(records[0]['canonical_source_ids'],['notice'])
            self.assertIsNone(records[0]['document_id'])
            points=json.loads((root/'assets/research/map-points.json').read_text())
            self.assertEqual(points[0]['items'],[['other','person-2',1710,False],['0123456789abcdef','person-1',1770,False]])
            self.assertNotIn('Wrong</h1>',(root/'places/wrong.html').read_text())
            project(root,registry,restore=True,write=True)
            for name,value in original.items():
                restored=json.loads((root/name).read_text())
                if name.endswith('map-points.json'):
                    self.assertEqual(sorted(restored,key=lambda x:x['name']),sorted(value,key=lambda x:x['name']))
                else:self.assertEqual(restored,value,name)
            self.assertIn('Wrong</h1>',(root/'places/wrong.html').read_text())

    def test_duplicate_source_rows_fail_before_any_write(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);registry,_=self.fixture(root)
            p=root/'data/records-index.json';rows=json.loads(p.read_text());rows.append(deepcopy(rows[0]));p.write_text(json.dumps(rows))
            before={str(p):p.read_bytes() for p in root.rglob('*') if p.is_file()}
            with self.assertRaisesRegex(ValueError,'one canonical record'):project(root,registry,write=True)
            self.assertEqual(before,{str(p):p.read_bytes() for p in root.rglob('*') if p.is_file()})

    def test_blank_location_or_duplicate_override_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'registry.json';review=self.review()
            path.write_text(json.dumps({'chronology':[review,review]}))
            with self.assertRaisesRegex(ValueError,'unique stable'):load_projections(path)
            review['map_projection']['record_fields']['record_location']=''
            path.write_text(json.dumps({'chronology':[review]}))
            with self.assertRaisesRegex(ValueError,'cannot blank'):load_projections(path)

    def test_ambiguous_map_item_rejected_without_changing_points(self):
        review=self.review();points=[deepcopy(review['map_projection']['previous_point'])]*2
        before=deepcopy(points)
        with self.assertRaisesRegex(ValueError,'one map item'):project_points(points,review)
        self.assertEqual(points,before)

    def test_csv_projection_preserves_other_rows_and_exact_multiline_rollback(self):
        text='\ufeffrecord_id,year,note\r\n0123456789abcdef,1700,"line1\nline2"\r\nother,1800,"unaltered, quote"\r\n'
        fixed,original=project_csv(text,'record_id','0123456789abcdef',{'year':'1770'})
        self.assertTrue(fixed.endswith('other,1800,"unaltered, quote"\r\n'))
        self.assertTrue(fixed.startswith('\ufeffrecord_id,year,note\r\n'))
        again,_=project_csv(fixed,'record_id','0123456789abcdef',{'year':'1770'})
        self.assertEqual(again,fixed)
        restored,_=project_csv(fixed,'record_id','0123456789abcdef',{},original)
        self.assertEqual(restored,text)

    def test_download_original_row_stays_in_record_history_and_restores(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);registry,_=self.fixture(root)
            csv_path=root/'data/records.csv'
            original=b'record_id,year,record_location\r\n0123456789abcdef,1700,Wrong parish\r\nother,1800,Elsewhere\r\n'
            csv_path.write_bytes(original)
            project(root,registry,write=True)
            self.assertIn(b'1770,Right parish',csv_path.read_bytes())
            self.assertFalse(project(root,registry,write=True)['changed'])
            project(root,registry,restore=True,write=True)
            self.assertEqual(csv_path.read_bytes(),original)
