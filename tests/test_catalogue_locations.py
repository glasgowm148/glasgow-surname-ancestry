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

    def test_kin_uses_common_region_without_propagating(self):
        parent=person('parent',[dict(record_id='r',record_location='Leith, Scotland',region='Scotland')])
        child=person('child',[dict(record_location='',region='')],father=[dict(id='parent')])
        grandchild=person('grandchild',[dict(record_location='',region='')],father=[dict(id='child')])
        rows,unresolved=prepare([parent,child,grandchild],{'child','grandchild'},region)
        self.assertEqual([(r['catalogue_id'],r['place'],r['basis_kind']) for r in rows],[('child','Scotland','kin')])
        self.assertEqual(unresolved[0]['catalogue_id'],'grandchild')

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
