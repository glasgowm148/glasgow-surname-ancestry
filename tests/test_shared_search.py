"""Exercise shared search with enough matches to expose category starvation."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from tools.site_search import ROOT, install_search, render_search, search_routes


class SharedSearchTests(unittest.TestCase):
    def run_node(self, script):
        with tempfile.TemporaryDirectory() as directory:
            site = Path(directory)
            install_search(site)
            result = subprocess.check_output(["node", "-e", script, str(site)], text=True)
        return json.loads(result)

    def test_worker_retains_all_categories_and_full_counts(self):
        result = self.run_node(r'''
const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const datasets={
 '/assets/v3/search-people.json':Array.from({length:400},(_,i)=>['person-'+i,(i<200?'Aaron':'James')+' Glasgow '+i,'/people/p-'+i+'.html','','']),
 '/assets/v3/search-records.json':Array.from({length:400},(_,i)=>['record-'+i,(i<200?'Glasgow':'James')+' register '+i,'/sources/r-'+i+'/','','']),
 '/assets/v3/search-places.json':[['place-1','Glasgow','/places/glasgow.html','','']],
 '/assets/research/free-space-index.json':[]
};
let response;const loaded=[];
const ctx={URL,importScripts:()=>{},globalThis:{},fetch:async url=>{loaded.push(new URL(url).pathname);return{ok:true,json:async()=>datasets[new URL(url).pathname]}},
 self:{location:{href:'https://fixture.test/assets/research/search-worker.js'},postMessage:r=>response=structuredClone(r)}};
vm.runInNewContext(fs.readFileSync(path.join(process.argv[1],'assets/research/search-worker.js'),'utf8'),ctx);
(async()=>{const queries={};
 for(const [q,tab] of [['glasgow','all'],['james','all'],['james','records'],['latest research','pages'],['free-space library','pages'],['family atlas','pages']]){
 await ctx.self.onmessage({data:{id:1,type:'search',q,tab}});if(response.error)throw Error(response.error);
 queries[q+'|'+tab]={isArray:Array.isArray(response.result),items:response.result,counts:response.result.counts,total:response.result.total};
 }
 console.log(JSON.stringify({queries,loaded}));
})().catch(e=>{console.error(e);process.exitCode=1});
''')
        glasgow = result["queries"]["glasgow|all"]
        james = result["queries"]["james|all"]
        self.assertEqual(glasgow["counts"]["person"], 400)
        self.assertEqual(glasgow["counts"]["record"], 200)
        self.assertEqual(james["counts"]["person"], 200)
        self.assertEqual(james["counts"]["record"], 200)
        for query in (glasgow, james):
            self.assertTrue(query["isArray"], "Old UI consumers must receive a filterable array")
            self.assertEqual(query["total"], sum(query["counts"].values()))
            for kind in ("person", "record"):
                self.assertEqual(sum(row["kind"] == kind for row in query["items"]), 160)
        for query, route in (("latest research|pages", "/latest-findings/"),
                             ("free-space library|pages", "/free-space/"),
                             ("family atlas|pages", "/onetree/")):
            matches = [row for row in result["queries"][query]["items"] if row["url"] == route]
            self.assertEqual(len(matches), 1)
        # Repeated queries reuse each worker-owned corpus; no extra index fetches.
        self.assertEqual(len(result["loaded"]), len(set(result["loaded"])))

    def test_fallback_uses_same_current_names_aliases_and_unique_routes(self):
        result = self.run_node(r'''
const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const empty=()=>null,body={dataset:{},classList:{contains:()=>false,add:()=>{}}};
const ctx={window:{},document:{body,querySelector:empty,getElementById:empty,querySelectorAll:()=>[],addEventListener:()=>{}},
 localStorage:{getItem:()=>null,setItem:()=>{}},MutationObserver:class{observe(){}},innerWidth:1440,
 matchMedia:()=>({matches:false}),setTimeout,clearTimeout,URL,location:{origin:'https://fixture.test'},
 fetch:async()=>({ok:true,json:async()=>[{title:'Library alias',url:'/free-space/',wikitreeId:'Space:Alias',category:'Project',tags:[]}]})};
ctx.window.addEventListener=()=>{};
vm.runInNewContext(fs.readFileSync(path.join(process.argv[1],'assets/unified/site.js'),'utf8'),ctx);
(async()=>{const results={};for(const q of ['latest findings','latest research','free-space library','family atlas'])results[q]=await ctx.window.GlasgowSite.search(q,'pages');console.log(JSON.stringify(results))})().catch(e=>{console.error(e);process.exitCode=1});
''')
        for query in ("latest findings", "latest research"):
            self.assertEqual([row["url"] for row in result[query]], ["/latest-findings/"])
        self.assertEqual([row["url"] for row in result["free-space library"]], ["/free-space/"])
        self.assertEqual(result["free-space library"][0]["name"], "Research library")
        self.assertEqual(result["family atlas"][0]["name"], "Family tree")

    def test_ui_accepts_legacy_current_and_intermediate_worker_responses(self):
        result = self.run_node(r'''
const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const empty=()=>null,body={dataset:{},classList:{contains:()=>false,add:()=>{}}};
const ctx={window:{},document:{body,querySelector:empty,getElementById:empty,querySelectorAll:()=>[],addEventListener:()=>{}},
 localStorage:{getItem:()=>null,setItem:()=>{}},MutationObserver:class{observe(){}},innerWidth:1440,
 matchMedia:()=>({matches:false}),setTimeout,clearTimeout,URL,location:{origin:'https://fixture.test'}};
ctx.window.addEventListener=()=>{};
const item={name:'James Glasgow',url:'/people/example.html',kind:'person'},counts={person:200,place:0,record:0,page:0};
let response;
ctx.window.GlasgowResearch={search:async()=>response};
vm.runInNewContext(fs.readFileSync(path.join(process.argv[1],'assets/unified/site.js'),'utf8'),ctx);
(async()=>{const results={};
 for(const [name,value] of [['legacy',[item]],['current',Object.assign([item],{counts,total:200})],['intermediate',{items:[item],counts,total:200}]]){
 response=structuredClone(value);const found=await ctx.window.GlasgowSite.search('james','people');
 results[name]={isArray:Array.isArray(found),names:found.filter(r=>r.kind==='person').map(r=>r.name),counts:found.counts||null,total:found.total||null};
 }
 console.log(JSON.stringify(results));
})().catch(e=>{console.error(e);process.exitCode=1});
''')
        for name, response in result.items():
            self.assertTrue(response["isArray"], name)
            self.assertEqual(response["names"], ["James Glasgow"])
        for name in ("current", "intermediate"):
            self.assertEqual(result[name]["counts"]["person"], 200)
            self.assertEqual(result[name]["total"], 200)
        self.assertIsNone(result["legacy"]["counts"])

    def test_dialog_keyboard_navigation_tracks_only_current_results(self):
        result = self.run_node(r'''
const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const assert=require('node:assert/strict');
const events={},attributes={},pending=new Map();
let timer;
const input={value:'',addEventListener:(event,fn)=>events[event]=fn,focus(){},select(){},
 setAttribute:(key,value)=>attributes[key]=value,removeAttribute:key=>delete attributes[key]};
const output={innerHTML:''},dialog={open:false,showModal(){this.open=true},addEventListener(){}};
const elements={'#g-search-dialog':dialog,'#g-search-input':input,'#g-search-results':output,
 '#g-advanced-people':{},'#g-advanced-records':{},'#g-search-announcement':{}};
const location={origin:'https://fixture.test',href:'https://fixture.test/'};
const ctx={window:{location,GlasgowResearch:{search:q=>new Promise(resolve=>pending.set(q,resolve))},addEventListener(){}},
 document:{body:{dataset:{},classList:{contains:()=>false}},addEventListener(){},querySelectorAll:()=>[],
  getElementById:()=>null,querySelector(selector){
   if(elements[selector])return elements[selector];
   const id=selector.slice(1);return output.innerHTML.includes('id="'+id+'"')?{id,scrollIntoView(){}}:null;
  }},
 localStorage:{getItem:()=>null},MutationObserver:class{},innerWidth:1440,
 setTimeout:fn=>{timer=fn;return fn},clearTimeout:()=>{timer=null},URL,location};
vm.runInNewContext(fs.readFileSync(path.join(process.argv[1],'assets/unified/site.js'),'utf8'),ctx);
const item=id=>({name:id,url:'/people/'+id+'.html',kind:'person'});
const press=key=>events.keydown({key,preventDefault(){}});
const type=q=>{input.value=q;events.input()};
const tick=()=>new Promise(resolve=>setImmediate(resolve));
(async()=>{
 ctx.window.GlasgowSite.openSearch('initial');
 pending.get('initial')([item('first'),item('second'),item('last')]);
 await tick();
 press('ArrowUp');
 assert.equal(attributes['aria-activedescendant'],'g-result-2');
 type('intermediate');
 press('Enter');
 assert.equal(location.href,'https://fixture.test/');
 timer();
 press('ArrowDown');
 press('Enter');
 assert.equal(location.href,'https://fixture.test/');
 type('final');
 pending.get('intermediate')([item('obsolete')]);
 await tick();
 assert.doesNotMatch(output.innerHTML,/obsolete/);
 timer();
 pending.get('final')([item('current')]);
 await tick();
 press('ArrowDown');
 assert.equal(attributes['aria-activedescendant'],'g-result-0');
 press('Enter');
 console.log(JSON.stringify(location.href));
})().catch(e=>{console.error(e);process.exitCode=1});
''')
        self.assertEqual(result, "/people/current.html")

    def test_registry_is_unique_and_installation_is_idempotent(self):
        routes = search_routes()
        self.assertEqual(len(routes), len({row["url"] for row in routes}))
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(install_search(Path(directory)), {"shared_search_assets": 2})
            self.assertEqual(install_search(Path(directory)), {})
        with self.assertRaises(ValueError):
            render_search("missing marker")
        for name in ("site.js", "search-worker.js"):
            text = render_search((ROOT / "tools/site_sources/performance" / name).read_text())
            self.assertIn('"name":"Latest findings"', text)


if __name__ == "__main__":
    unittest.main()
