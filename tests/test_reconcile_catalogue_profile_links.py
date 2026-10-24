"""Bounded profile-link retirement safeguards, using isolated public fixtures."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from tools.reconcile_catalogue_profile_links import apply, plan


class ProjectionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.ids = ['record-fmp-'+str(i) for i in range(4)]
        links = {};people = [];search = [];index = [];records = []
        for i, old in enumerate(self.ids):
            profile = f'Glasgow-{i+1}';slug = profile.lower()
            url = f'https://www.findmypast.co.uk/transcript?id=RECORD{i}'
            evidence = [{'id': f'E{i}', 'source': {'url': url}, 'subjects': [old]}]
            dossier = {'id': profile,'name': f'Person{i}','vitals': {'birth': {'date': '1700', 'status': 'guess'}},
                       'relationships': {'parents': [{'id': 'Glasgow-99', 'status': 'uncertain', 'probability': 42}]},'evidence': evidence,
                       'open_questions': ['Same-name identity unresolved']}
            self.put(f'www/people/{slug}.json', dossier)
            self.put(f'www/people/{old}.json', {'id':old,'vitals':{'birth': {'date':'1680'}},'relationships':{'parents':[]},'claims':[{'claim':'Historical estimate'}],'evidence':evidence})
            for name in [old,slug]:self.put(f'www/people/{name}.html','<html><head><link rel="canonical" href="/old"/></head><body><main>Prior account</main></body></html>')
            links[old]={'profile_id':profile,'matched_at':'2026-10-22','evidence_note':'Same provider record'}
            people += [{'catalogue_id':old,'name':f'Person{i}','records':[{'source_url':url,'association':'Named subject','supplement_id':old[7:],'source_status':'scoped integration new_person READY'}]},
                       {'catalogue_id':slug,'name':f'Person{i}','birth':'1700','father':['Glasgow-99'],'records':[]}]
            search += [{'id':old,'profile_work_status':'creation_ready'},{'id':slug,'name':f'Person{i}'}]
            index += [{'id':old},{'id':profile,'catalogue_id':slug}]
            records += [{'id':str(i),'catalogue_id':old,'profile_ids':'','source_url':url}]
            self.put(f'www/assets/v3/sources/s{i}.json', {'members':[old], 'events':[{'person':old,'role':'witness','participants':[{'id':old,'role':'witness'}]}]})
        people += [{'catalogue_id':'unrelated','name':'Untouched','records':[],'father':['Keep']}]
        self.put('data/wikitree/catalogue-profile-links.json',{'entries':links})
        self.put('www/data/people.json',{'people':people,'count':len(people)})
        self.put('www/data/people-index.json',index)
        self.put('www/data/catalogue-search-index.json',search)
        self.put('www/data/records-index.json',records)
        self.put('www/data/chunks/people-0001.json',{'items':index,'count':len(index)})
        self.put('www/data/chunks/records-0001.json',{'items':records,'count':len(records)})
        self.put('www/data/chunks/families-0001.json',{'items':[{'id':'region','kind':'region','members':[self.ids[0],'glasgow-1'],'count':2}]})
        self.put('www/data/compare-index.js','window.glasgowCompareIndex='+json.dumps(index)+';\nwindow.glasgowCompareDossiers='+json.dumps({**{old:{'id':old} for old in self.ids},'glasgow-1':{'vitals':'unchanged'}})+';\n')
        self.put('www/data/resolve/person.json',{'candidates':index,'candidate_count':len(index)})
        self.put('www/data/resolve/unrelated.json',{'candidates':[{'id':'unrelated'}],'candidate_count':99})
        self.put('www/assets/v3/source-index.json',[{'id':f's{i}','members':[old]} for i,old in enumerate(self.ids)])
        self.put('www/assets/sources/collection-index.json',[{'id':f'collection{i}','members':[old], 'people':[{'id':old,'name':f'Person{i}','url':f'/people/{old}.html'}]} for i,old in enumerate(self.ids)])
        self.before = {f'record{i}':self.read(f'www/people/glasgow-{i+1}.json') for i in range(4)}

    def put(self,path,value):
        target=self.root/path;target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(value if isinstance(value,str) else json.dumps(value))
    def read(self,path):return json.loads((self.root/path).read_text())
    def snapshot(self):return {str(p.relative_to(self.root)):p.read_bytes() for p in self.root.rglob('*') if p.is_file()}

    def test_four_subjects_retire_without_adopting_genealogy(self):
        original=self.snapshot();proposed=plan(self.root,self.ids)
        self.assertEqual(original,self.snapshot())
        self.assertTrue(proposed)
        apply(self.root,self.ids,refresh=False)
        self.assertEqual((self.root/'www/data/resolve/unrelated.json').read_bytes(),original['www/data/resolve/unrelated.json'])
        people=self.read('www/data/people.json')['people']
        self.assertFalse(any(p['catalogue_id'] in self.ids for p in people))
        self.assertEqual(next(p for p in people if p['catalogue_id']=='unrelated'),{'catalogue_id':'unrelated','name':'Untouched','records':[],'father':['Keep']})
        for i,old in enumerate(self.ids):
            self.assertEqual(self.read(f'www/people/glasgow-{i+1}.json'),self.before[f'record{i}'])
            current=next(p for p in people if p['catalogue_id']==f'glasgow-{i+1}')
            self.assertEqual(current['birth'],'1700');self.assertEqual(current['father'],['Glasgow-99'])
            self.assertEqual(current['records'][0]['profile_id'],f'Glasgow-{i+1}')
            self.assertEqual(current['records'][0]['retired_catalogue_id'],old)
            self.assertNotIn('new_person READY',current['records'][0]['source_status'])
            alias=self.read(f'www/people/{old}.json')
            self.assertEqual(alias['status'],'superseded')
            self.assertEqual(alias['superseded_documentary_account']['claims'][0]['claim'],'Historical estimate')
            event=self.read(f'www/assets/v3/sources/s{i}.json')['events'][0]
            self.assertEqual(event['person'],f'glasgow-{i+1}');self.assertEqual(event['participants'][0]['id'],f'glasgow-{i+1}')
            self.assertEqual(event['role'],'witness')
            collection=self.read('www/assets/sources/collection-index.json')[i]
            self.assertEqual(collection['members'],[f'glasgow-{i+1}'])
            self.assertEqual(collection['people'][0]['id'],f'glasgow-{i+1}')
        self.assertEqual(plan(self.root,self.ids),{})
        self.assertFalse(any(p['id'] in self.ids for p in self.read('www/data/chunks/people-0001.json')['items']))
        self.assertEqual(self.read('www/data/chunks/records-0001.json')['items'][0]['catalogue_id'],'glasgow-1')
        region=self.read('www/data/chunks/families-0001.json')['items'][0]
        self.assertEqual(region['members'],['glasgow-1']);self.assertEqual(region['count'],1)
        comparison=(self.root/'www/data/compare-index.js').read_text()
        self.assertNotIn(self.ids[0],comparison);self.assertIn('unchanged',comparison)

    def test_invalid_later_target_causes_no_partial_writes(self):
        path=self.root/'www/people/glasgow-4.json';path.unlink();before=self.snapshot()
        with self.assertRaisesRegex(ValueError,'canonical target'):apply(self.root,self.ids,refresh=False)
        self.assertEqual(before,self.snapshot())

    def test_missing_provider_proof_causes_no_writes(self):
        d=self.read('www/people/glasgow-4.json');d['evidence']=[];self.put('www/people/glasgow-4.json',d);before=self.snapshot()
        with self.assertRaisesRegex(ValueError,'provider-record proof'):apply(self.root,self.ids,refresh=False)
        self.assertEqual(before,self.snapshot())

    def test_unexplained_genealogy_is_not_adopted(self):
        d=self.read(f'www/people/{self.ids[0]}.json');d['relationships']['parents']=[{'id':'Glasgow-99'}];self.put(f'www/people/{self.ids[0]}.json',d);before=self.snapshot()
        with self.assertRaisesRegex(ValueError,'genealogical edges'):apply(self.root,self.ids,refresh=False)
        self.assertEqual(before,self.snapshot())

    def test_only_explicit_subject_is_projected(self):
        apply(self.root,[self.ids[0]],refresh=False)
        ids={p['catalogue_id'] for p in self.read('www/data/people.json')['people']}
        self.assertTrue(set(self.ids[1:]) <= ids)
        self.assertNotIn(self.ids[0],ids)

    def test_existing_documentary_row_is_not_duplicated(self):
        data=self.read('www/data/people.json')
        old=next(p for p in data['people'] if p['catalogue_id']==self.ids[0])
        current=next(p for p in data['people'] if p['catalogue_id']=='glasgow-1')
        current['records']=[deepcopy(old['records'][0])]
        current['records'][0]['profile_id']='Glasgow-1'
        current['records'][0]['source_status']='Existing reviewed record'
        self.put('www/data/people.json',data)
        apply(self.root,[self.ids[0]],refresh=False)
        current=next(p for p in self.read('www/data/people.json')['people'] if p['catalogue_id']=='glasgow-1')
        self.assertEqual(len(current['records']),1)
        self.assertEqual(current['records'][0]['source_status'],'Existing reviewed record')

    def test_resumed_alias_repair_finds_direct_reader_without_wrapper_record_ids(self):
        old = self.ids[0]
        apply(self.root, [old], refresh=False)
        self.put('www/assets/research/record-index.json', [
            {'id': 'R0', 'p': 'glasgow-1'}, {'id': 'KEEP', 'p': 'unrelated'}])
        self.put('www/assets/research/records/R0.json', {
            'record_id': 'R0', 'catalogue_id': old, 'profile_ids': '',
            'catalogue_url': f'/people/{old}.html',
            'source_status': 'scoped integration new_person READY',
            'source_url': 'https://www.findmypast.co.uk/transcript?id=RECORD0'})
        self.put('www/assets/research/records/KEEP.json', {'catalogue_id': 'unrelated'})
        current = self.read('www/people/glasgow-1.json')
        apply(self.root, [old], refresh=False)
        record = self.read('www/assets/research/records/R0.json')
        self.assertEqual(record['catalogue_id'], 'glasgow-1')
        self.assertEqual(record['catalogue_url'], '/people/glasgow-1.html')
        self.assertEqual(record['profile_ids'], 'Glasgow-1')
        self.assertNotIn('READY', record['source_status'])
        self.assertEqual(self.read('www/assets/research/records/KEEP.json'), {'catalogue_id': 'unrelated'})
        self.assertEqual(self.read('www/people/glasgow-1.json'), current)

    def add_legacy_fixture(self):
        old=self.ids[0]
        invented={'p':old,'id':'birth','kind':'personal','basis':'imported_vital','year':1680}
        mention={'p':old,'id':'E0','kind':'mention','basis':'source_association','source_url':'https://www.findmypast.co.uk/transcript?id=RECORD0','role':'witness','participants':[{'id':old,'role':'witness'}]}
        canonical={'p':'glasgow-1','id':'birth','kind':'personal','basis':'reviewed_vital','year':1700}
        wrapper={'id':old,'catalogue_id':old,'vitals':{'birth':{'date':'1680'}},'relationships':{'parents':[]},'events':[invented,mention],'record_ids':['R0'],'review':{'action':'create_new_profile'}}
        self.put(f'www/assets/research/people/{old}.json',wrapper)
        self.put('www/assets/research/people/glasgow-1.json',{'id':'Glasgow-1','vitals':{'birth':{'date':'1700'}},'relationships':{'parents':[{'id':'Glasgow-99'}]}})
        self.put('www/assets/research/event-index.json',[canonical,invented,mention])
        self.put(f'www/assets/v3/events/{old}.json',[invented,mention])
        self.put('www/assets/v3/events/glasgow-1.json',[canonical])
        self.put('www/assets/research/records/R0.json',{'record_id':'R0','catalogue_id':old,'source_status':'scoped integration new_person READY'})
        self.put('www/assets/research/coverage.json',{'catalogue_only':[old,'unrelated'],'catalogue':99})
        self.put('www/assets/research/branches.json',[{'id':'region','kind':'region','members':[old,'glasgow-1'],'count':2}])
        self.put('www/assets/research/search-index.json',[{'id':'R0','kind':'record','search':'record '+old+' unchanged claim'}])
        self.put('www/assets/v3/relationships.json',{'nodes':{old:{'id':old},'glasgow-1':{'id':'Glasgow-1'}},'edges':[]})
        self.put('www/assets/v3/relationship-routing.json',{'nodes':[['glasgow-1','Glasgow-1'],[old,old],['unrelated','Unrelated']],'edges':[['edge',0,2,'partner']]})
        self.put('www/assets/unified/search-people.json',[{'id':old},{'id':'unrelated'}])
        self.put('www/assets/unified/search-records.json',[{'url':f'/people/{old}.html#research-stack','name':'Recorded subject'}])
        self.put('www/assets/unified/routes.js','window.GlasgowRoutes='+json.dumps({old:old,'unrelated':'unrelated'})+';\n')

    def test_residual_legacy_wrappers_after_alias_retirement(self):
        apply(self.root,[self.ids[0]],refresh=False)
        self.add_legacy_fixture()
        alias=(self.root/f'www/people/{self.ids[0]}.json').read_bytes()
        canonical_wrapper=self.read('www/assets/research/people/glasgow-1.json')
        apply(self.root,[self.ids[0]],refresh=False)
        wrapper=self.read(f'www/assets/research/people/{self.ids[0]}.json')
        self.assertEqual(wrapper['status'],'superseded')
        self.assertNotIn('review',wrapper)
        self.assertEqual(wrapper['superseded_documentary_account']['vitals']['birth']['date'],'1680')
        target_wrapper=self.read('www/assets/research/people/glasgow-1.json')
        self.assertEqual(target_wrapper['vitals'],canonical_wrapper['vitals'])
        self.assertEqual(target_wrapper['relationships'],canonical_wrapper['relationships'])
        self.assertEqual(target_wrapper['mentions'][0]['p'],'glasgow-1')
        self.assertNotIn('events',target_wrapper)  # No imported synthetic birth.
        self.assertEqual((self.root/f'www/people/{self.ids[0]}.json').read_bytes(),alias)
        events=self.read('www/assets/research/event-index.json')
        self.assertEqual(len(events),2)
        self.assertEqual(events[0]['year'],1700)
        self.assertEqual(events[1]['p'],'glasgow-1')
        self.assertEqual(events[1]['participants'][0]['role'],'witness')
        self.assertFalse(any(e.get('year')==1680 for e in self.read('www/assets/v3/events/glasgow-1.json')))
        self.assertEqual(self.read('www/assets/v3/relationship-routing.json')['edges'][0][1:3],[0,1])
        self.assertEqual(self.read('www/assets/research/records/R0.json')['catalogue_id'],'glasgow-1')
        self.assertNotIn(self.ids[0],self.read('www/assets/research/coverage.json')['catalogue_only'])
        self.assertNotIn(self.ids[0],self.read('www/assets/research/search-index.json')[0]['search'])
        self.assertEqual(self.read('www/assets/unified/search-people.json'),[{'id':'unrelated'}])
        self.assertEqual(self.read('www/assets/unified/search-records.json')[0]['url'],'/people/glasgow-1.html#research-stack')
        self.assertIn('"'+self.ids[0]+'":"glasgow-1"',(self.root/'www/assets/unified/routes.js').read_text())
        self.assertEqual(plan(self.root,[self.ids[0]]),{})

    def test_missing_canonical_event_cache_contains_documentary_events_only(self):
        self.add_legacy_fixture()
        (self.root/'www/assets/v3/events/glasgow-1.json').unlink()
        apply(self.root,[self.ids[0]],refresh=False)
        events=self.read('www/assets/v3/events/glasgow-1.json')
        self.assertEqual(len(events),1)
        self.assertEqual(events[0]['basis'],'source_association')
        self.assertEqual(events[0]['p'],'glasgow-1')

    def test_legacy_genealogy_edge_blocks_entire_plan(self):
        self.add_legacy_fixture()
        graph=self.read('www/assets/v3/relationships.json')
        graph['edges']=[{'a':self.ids[0],'b':'glasgow-1','type':'parent'}]
        self.put('www/assets/v3/relationships.json',graph)
        before=self.snapshot()
        with self.assertRaisesRegex(ValueError,'legacy relationship edge'):
            apply(self.root,[self.ids[0]],refresh=False)
        self.assertEqual(self.snapshot(),before)


if __name__=='__main__':unittest.main()
