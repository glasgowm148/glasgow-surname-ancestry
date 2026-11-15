import copy
import unittest
from tools.catalogue_locations import prepare, project, memberships, unknown, association_html


def person(key, records=(), **extra):
    return dict(catalogue_id=key,name=key,records=list(records),regions=[],recorded_in=[],
                birth_location='',death_location='',**extra)


def region(place):
    return {'Leith, Scotland':'Scotland','Belfast, Ireland':'Ireland','Scotland':'Scotland'}.get(place,'')


class LocationClassificationTests(unittest.TestCase):
    def test_same_subject_region_and_missing_event_preserved(self):
        p=person('p',[dict(record_id='r',record_location='Leith, Scotland',region=''),
                      dict(record_id='blank',record_location='',region='')])
        before=copy.deepcopy(p)
        rows,unresolved=prepare([p],{'p'},region)
        self.assertFalse(unresolved)
        self.assertEqual(p,before)
        self.assertEqual(rows[0]['record_regions'],{'r':'Scotland'})
        project([p],{'p':rows})
        self.assertEqual(p['records'][0]['region'],'Scotland')
        self.assertEqual(p['records'][1]['record_location'],'')
        self.assertEqual(p['birth_location'],'')
        self.assertNotIn('Unspecified',p['regions'])
        self.assertEqual({r['record_location'] for r in memberships(p)},{'Leith, Scotland'})

    def test_kin_routes_use_original_fields_without_propagating_estimates(self):
        parent=person('parent',[dict(record_id='r',record_location='Leith, Scotland',region='Scotland')])
        child=person('child',[dict(record_location='',region='')],father=[dict(id='parent')])
        grandchild=person('grandchild',[dict(record_location='',region='')],father=[dict(id='child')])
        rows,unresolved=prepare([parent,child,grandchild],{'child','grandchild'},region)
        self.assertEqual([(r['catalogue_id'],r['place'],r['basis_kind']) for r in rows],[('child','Scotland','kin'),('grandchild','Scotland','kin')])
        self.assertFalse(unresolved)
        self.assertIn('2 relationship steps',rows[1]['basis'])
        original_evidence=[e for e in rows[1]['evidence'] if e['field']!='held_kin_route']
        self.assertEqual({e['catalogue_id'] for e in original_evidence},{'parent'})
        # A saved estimate alone is not an original geographic anchor.
        parent['records']=[]
        child['location_associations']=[dict(place='Scotland',region='Scotland',basis_kind='kin')]
        rows,unresolved=prepare([parent,child,grandchild],{'grandchild'},region)
        self.assertFalse(rows)
        self.assertEqual(len(unresolved),1)


    def test_capture_parents_outside_export_supply_shared_ohio_locality(self):
        from tools.catalogue_location_regions import region_for_location
        p=person('daughter',[dict(record_location='',region='')],
                 father=[dict(id='',numeric_id='123',outside_export=True)],
                 mother=[dict(id='',numeric_id='456',outside_export=True)],
                 wikitree_evidence=[dict(profile_url='https://example.test/daughter',relations={
                    'parents':[
                        dict(id='Parent-1',birth_location='Cleveland, Cuyahoga County, Ohio'),
                        dict(id='Parent-2',birth_location='Cleveland, Cuyahoga County, Ohio')],
                    'siblings':[dict(id='Sibling-1',birth_location='Ohio',death_location='USA')]} )])
        rows,unresolved=prepare([p],{'daughter'},region_for_location)
        self.assertFalse(unresolved)
        self.assertEqual(rows[0]['place'],'Cleveland, Cuyahoga County, Ohio')
        self.assertEqual(rows[0]['region'],'United States')
        self.assertEqual(rows[0]['basis_kind'],'kin')
        self.assertTrue(any('Parent-1' in e['field'] for e in rows[0]['evidence']))
        self.assertTrue(any('Parent-2' in e['field'] for e in rows[0]['evidence']))
        project([p],{'daughter':rows})
        self.assertEqual(p['birth_location'],'')
        self.assertEqual(p['records'][0]['record_location'],'')

    def test_single_relative_multiple_fields_do_not_fabricate_locality_consensus(self):
        p=person('p',[dict(record_location='',region='')],wikitree_evidence=[dict(relations={
            'parents':[dict(id='one-parent',birth_location='Leith, Scotland',death_location='Leith, Scotland')]}
        )])
        rows,_=prepare([p],{'p'},region)
        self.assertEqual(rows[0]['place'],'Scotland')
        p['wikitree_evidence'][0]['relations']['parents'][0]['withheld']=True
        rows,_=prepare([p],{'p'},region)
        self.assertFalse(rows)

    def test_conflicting_kin_do_not_produce_a_location(self):
        a=person('a',[dict(record_location='Leith, Scotland',region='Scotland')])
        b=person('b',[dict(record_location='Belfast, Ireland',region='Ireland')])
        c=person('c',[dict(record_location='',region='')],father=[dict(id='a')],mother=[dict(id='b')])
        rows,unresolved=prepare([a,b,c],{'c'},region)
        self.assertFalse(rows)
        self.assertEqual(len(unresolved),1)

    def test_shared_entry_and_collection_distinguished(self):
        a=person('a',[dict(record_id='r1',record_location='Leith, Scotland',region='Scotland',source_url='https://example.test/records/123')])
        b=person('b',[dict(record_id='r2',record_location='',region='',source_url='https://example.test/records/123')])
        rows,_=prepare([a,b],{'b'},region)
        self.assertEqual(rows[0]['basis_kind'],'shared_record')
        a['records'][0]['source_url']=b['records'][0]['source_url']='https://example.test/collection'
        rows,unresolved=prepare([a,b],{'b'},region)
        self.assertFalse(rows)
        self.assertEqual(len(unresolved),1)

    def test_changed_source_label_blocks_record_region_projection(self):
        p=person('p',[dict(record_id='r',record_location='Different place',region='')])
        assoc=dict(place='Leith, Scotland',region='Scotland',basis_kind='own_record',basis='Held place',record_regions={'r':'Scotland'})
        project([p],{'p':[assoc]})
        self.assertEqual(p['records'][0]['region'],'')
        self.assertEqual(p['records'][0]['record_location'],'Different place')

    def test_uncertainty_visible_and_empty_people_do_not_change_chart_scope(self):
        self.assertEqual(memberships(person('no-records')),[])
        p=person('p',[dict(record_location='',region='')])
        a=dict(place='Scotland',region='Scotland',basis_kind='kin',basis='Parent context',evidence=[],record_regions={})
        project([p],{'p':[a]})
        self.assertTrue(p['estimated_location'])
        html=association_html(p)
        self.assertIn('uncertain association',html)
        self.assertIn('do not establish a birthplace',html)
        self.assertEqual(p['records'][0]['record_location'],'')


if __name__=='__main__':unittest.main()
