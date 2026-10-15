"""Execute both maintained matchers; packing must preserve IDs and ranking."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from tools.catalogue_search_index import build, refresh

ROOT=Path(__file__).parents[1]


class CatalogueWorkerParityTests(unittest.TestCase):
    def test_refresh_updates_visible_flags_and_cache_versions(self):
        from tools.stamp_asset_versions import content_hash
        with tempfile.TemporaryDirectory() as temp:
            site = Path(temp)
            (site / 'data').mkdir(); (site / 'people').mkdir(); (site / 'catalogue').mkdir()
            source = site / 'data/catalogue-search-index.json'
            rows = [{'id': 'example', 'name': 'Example Glasgow', 'profile_ids': ['Glasgow-1'],
                     'needs_wikitree_update': False}]
            source.write_text(json.dumps(rows)); build(site)
            (site / 'people/search.js').write_text('// Older deployed runtime awaiting refresh')
            page = site / 'catalogue/index.html'
            page.write_text('<script src="/people/search.js?v=old"></script>')
            rows[0]['needs_wikitree_update'] = True
            rows[0]['wikitree_update_summary'] = 'New reviewed family amendment'
            changes = [{'action': 'add', 'relationship': 'father', 'status': 'uncertain', 'relative_id': 'Glasgow-2'}]
            rows[0]['wikitree_update_relationship_changes'] = changes
            source.write_text(json.dumps(rows)); refresh(site)
            packed = json.loads((site / 'data/catalogue-search-fast.json').read_text())
            flag = packed['fields'].index('needs_wikitree_update')
            self.assertEqual(sum(bool(row[flag]) for row in packed['rows']), 1)
            def unpack(value):
                if isinstance(value, int) and not isinstance(value, bool) and value < 0:
                    return packed['strings'][-value-1]
                if isinstance(value, list): return [unpack(v) for v in value]
                if isinstance(value, dict): return {k: unpack(v) for k, v in value.items()}
                return value
            change_column = packed['fields'].index('wikitree_update_relationship_changes')
            self.assertEqual(unpack(packed['rows'][0][change_column]), changes)
            self.assertIn('catalogue-search-fast.json?v=' + content_hash(site / 'data/catalogue-search-fast.json'),
                          (site / 'people/search.js').read_text())
            self.assertIn('/people/search.js?v=' + content_hash(site / 'people/search.js'), page.read_text())
            frozen = page.read_bytes(); refresh(site)
            self.assertEqual(page.read_bytes(), frozen)

    def test_badge_distinguishes_new_relationships_from_other_work(self):
        source = (ROOT / 'tools/catalogue_search.js').read_text()
        helper = source[source.index('  function relationshipUpdateLabel('):source.index('  function resultRow(')]
        script = "const esc=s=>String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;');\n" + helper + '''
const base={needs_wikitree_update:true,wikitree_update_significance:86};
console.log(JSON.stringify([
 updateBadge(base),
 updateBadge({...base,wikitree_update_relationship_changes:[{action:'add',relationship:'father',status:'uncertain'}]}),
 updateBadge({...base,wikitree_update_relationship_changes:[{action:'regrade',relationship:'father',status:'certain'}]}),
 updateBadge({...base,wikitree_update_relationship_changes:[{action:'add',relationship:'father',status:'uncertain'},{action:'add',relationship:'mother',status:'possible'}]}),
 updateBadge({...base,needs_wikitree_update:false,wikitree_update_relationship_changes:[{action:'add',relationship:'father',status:'uncertain'}]})
]));'''
        badges = json.loads(subprocess.check_output(['node', '-e', script], text=True))
        self.assertIn('significance 86</small>', badges[0])
        self.assertIn('class="catalogue-relationship-badge">new uncertain father</span>', badges[1])
        self.assertEqual(badges[0], badges[2])
        self.assertIn('new uncertain father · new uncertain mother', badges[3])
        self.assertEqual(badges[4], '')

    def test_generated_worker_preserves_filters_and_sorting(self):
        rows=[]
        for i,(name,gender,place,bio) in enumerate([
            ('Alice Glasgow','Female','Yorkshire','Lived in Ulster.'),
            ('Bob Glasco','Male','New York, USA','Worked in a foundry.'),
            ('Alice Brown','Female','Antrim','Lived in Yorkshire.')]):
            rows.append({'id':f'person-{i}','name':name,'gender':gender,'profile_ids':[f'Glasgow-{i+1}'],
                         'first_names':[name.split()[0]],'last_names_at_birth':[name.split()[1]],
                         'last_names_current':[name.split()[1]], 'birth':str(1800+i), 'birth_year':1800+i,
                         'date_years':[1800+i],'birth_location':place,'locations':[place],
                         'biography_text':bio,'clusters':['Group alpha' if i<2 else 'Group beta'],
                         'record_types':['Birth'],'source_qualities':['original'], 'regions':['Ireland' if i==2 else 'England'],
                         'evidence_terms':['Inspected register'], 'missing_father':i==2,'missing_mother':True,
                         'has_profile':True,'record_count':i+1,'has_original_record':i==0,
                         'father':[] if i==2 else [{'id':'Glasgow-900','name':'Father Glasgow','certainty':'uncertain'}],
                         'spouses':[{'id':'Brown-3','name':'Jane Brown','marriage_location':'Antrim'}] if i==0 else []})
        source=(ROOT/'tools/catalogue_search.js').read_text()
        baseline=source[source.index('  const normaliseLiteral='):source.index('  const esc=')]
        baseline+=source[source.index('  function prepare('):source.index('  let searchWorker=')]
        baseline+=source[source.index('  function matches('):source.index('  function sortHeader(')]
        script=r'''
const fs=require('fs'),vm=require('vm'),root=process.argv[1];
const responses=new Map(),raw=JSON.parse(fs.readFileSync(root+'/data/catalogue-search-index.json'));
const worker={self:{postMessage:m=>responses.set(m.id,m)},fetch:async url=>({ok:true,json:async()=>JSON.parse(fs.readFileSync(root+(url==='fast'?'/data/catalogue-search-fast.json':'/data/catalogue-search-advanced.json')))})};
vm.createContext(worker);vm.runInContext(fs.readFileSync(root+'/people/catalogue-worker.js','utf8'),worker);
const original={raw:structuredClone(raw),controls:{},sortMode:'relevance',gender:'both'};
vm.createContext(original);vm.runInContext(fs.readFileSync(process.argv[2],'utf8')+'; const selectedGender=()=>gender; const source=prepare(raw);',original);
const defaults={query:[],phrase:'',exact:false,name:'',first:'',last:'',lastScope:'',sibling:'',child:'',birthSurname:'',spouse:'',marriageSurname:'',father:'',mother:'',dateType:'',locationType:'',location:'',region:'',cluster:'',recordType:'',sourceQuality:'',excluded:[],from:null,to:null,gender:'both',flags:{}};
const cases=[{q:'glasgow'}, {q:'Alice Yorkshire'}, {q:'register'}, {q:'Glasco',exact:true},
 {gender:'female'}, {sibling:'bob'}, {location:'yorkshire',locationType:'bio'}, {location:'antrim',locationType:'marriage'},
 {excluded:['united states']}, {cluster:'group alpha'}, {flags:{missingFather:true}}, {from:1801,to:1802},
 {father:'father glasgow'}, {last:'glasco',lastScope:'birth'}, {spouse:'jane brown'}, {sourceQuality:'original'}];
(async()=>{await worker.self.onmessage({data:{type:'load',id:1,url:'fast',advancedUrl:'advanced'}});
 if(responses.get(1).error)throw Error(responses.get(1).error);
 let checks=0;
 for(const test of cases)for(const mode of ['relevance','name:desc','birth:asc','spouse:asc','significance:desc']){
  const filters={...defaults,...test,flags:{...test.flags}};
  original.input=test.q||'';original.exact=filters.exact;
  filters.phrase=vm.runInContext('(exact?normaliseLiteral:normalise)(input)',original);
  filters.query=filters.phrase.split(' ').filter(Boolean);
  original.gender=filters.gender;original.sortMode=mode;original.filters=filters;
  original.controls=Object.fromEntries(['missingFather','missingMother','missingProfile','needsUpdate','descendants','wives','glasgowBirth','suffix'].map(k=>[k,{checked:!!filters.flags[k]}]));
  const expected=vm.runInContext('source.filter(p=>matches(p,filters)).sort((a,b)=>comparePeople(a,b,filters)).map(p=>p.id)',original);
  const id=++checks+1;await worker.self.onmessage({data:{id,type:'filter',filters,sortMode:mode}});
  const got=responses.get(id);if(got.error)throw Error(got.error);
  if(JSON.stringify(got.result)!==JSON.stringify(expected))throw Error(JSON.stringify({test,mode,expected,actual:got.result}));
 }
 console.log(checks);
})().catch(e=>{console.error(e);process.exitCode=1});
'''
        with tempfile.TemporaryDirectory() as directory:
            site=Path(directory);(site/'data').mkdir()
            (site/'data/catalogue-search-index.json').write_text(json.dumps(rows))
            build(site);baseline_path=site/'baseline.js';baseline_path.write_text(baseline)
            before=(site/'data/catalogue-search-fast.json').read_bytes()
            subprocess.run([sys.executable,'-c','from pathlib import Path;import sys;from tools.catalogue_search_index import build;build(Path(sys.argv[1]))',str(site)],
                           cwd=ROOT,env={**os.environ,'PYTHONHASHSEED':'73'},check=True,capture_output=True)
            self.assertEqual(before,(site/'data/catalogue-search-fast.json').read_bytes(),'Rebuilds must keep content hashes stable across Python processes')
            output=subprocess.check_output(['node','-e',script,str(site),str(baseline_path)],text=True)
            self.assertEqual(int(output),80)


if __name__=='__main__':unittest.main()
