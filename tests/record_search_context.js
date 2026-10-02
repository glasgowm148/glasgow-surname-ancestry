/* Execute the maintained records controller with a small DOM and real events. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const script = fs.readFileSync('tools/record_search.js', 'utf8');
const tick = () => new Promise(resolve => setImmediate(resolve));
async function start(search, rows, selected = null) {
  const events = {}, elements = {};
  for (const id of ['record-query','record-from','record-to','record-region','record-category','record-quality','r-record-citation','record-sort','record-count','record-results','record-reset','records-scope']) {
    elements[id] = {value:'',tagName:'INPUT',textContent:'',innerHTML:'',addEventListener(){},querySelectorAll(){return []},querySelector(){return null},insertAdjacentHTML(_,html){this.innerHTML+=html},scrollIntoView(){}};
  }
  const location = {search,pathname:'/records/',href:'http://site/records/'+search};
  let context = selected;
  const research = {ready:Promise.resolve(),canonical:id=>String(id).toLowerCase(),context:()=>context,scopeIds:async c=>new Set(c.scope==='family'?['person','relative']:['person'])};
  const sandbox = {URL,URLSearchParams,AbortController,DOMException,setTimeout,clearTimeout,CustomEvent:class{},location,
    history:{replaceState(_,__,url){location.search=new URL(url,'http://site').search}},
    document:{currentScript:{src:'http://site/records/search.js'},querySelector(selector){return elements[selector.split(',').at(-1).slice(1)]},addEventListener(name,callback){events[name]=callback}},
    window:{GlasgowResearch:research,dispatchEvent(){}},fetch:async()=>({ok:true,json:async()=>rows})};
  vm.runInNewContext(script,sandbox);await tick();await tick();
  return {elements,async select(next,query){context=next;location.search=query;events['glasgow:context']();await tick();await tick();}};
}
const row=(id,region)=>({catalogue_id:id,person:id,filter_year:1800,region});
(async()=>{
  const rows=[...Array.from({length:6},()=>row('person','Ireland')),...Array.from({length:31},()=>row('relative','Ireland'))];
  const page=await start('?person=Person',rows,{kind:'person',id:'Person',name:'Selected person',scope:'person'});
  assert.match(page.elements['record-count'].textContent,/of 6 record entries/);
  await page.select({kind:'person',id:'Person',name:'Selected person',scope:'family'},'?person=Person&scope=family');
  assert.match(page.elements['record-count'].textContent,/of 37 record entries/);
  await page.select({kind:'person',id:'Person',name:'Selected person',scope:'person'},'?person=Person');
  assert.match(page.elements['record-count'].textContent,/of 6 record entries/);
  const countries=[row('scot','Scotland'),row('mixed','Scotland / England'),row('irish','Ireland'),row('welsh','Wales'),row('nz','New Zealand'),row('aus','Australia'),row('us','United States'),row('ca','Canada'),row('other','India'),row('unknown','')];
  for(const [country,n,region] of [['scotland',2,''],['ireland',1,'Ireland'],['england',2,''],['oceania',2,''],['america',1,'United States'],['canada',1,'Canada'],['other',2,''],['australia',1,'Australia'],['nz',1,'New Zealand'],['new-zealand',1,'New Zealand'],['wales',1,'Wales']]){
    const filtered=await start('?country='+country,countries);
    assert.match(filtered.elements['record-count'].textContent,new RegExp('of '+n+' record entries'));
    assert.equal(filtered.elements['record-region'].value,region);
  }
  const conflict=await start('?country=scotland&region=Ireland',countries);
  assert.equal(conflict.elements['record-count'].textContent,'No record matches those filters.');
  const unsupported=await start('?country=atlantis',countries);
  assert.equal(unsupported.elements['record-count'].textContent,'Unsupported country filter');
  assert.match(unsupported.elements['record-results'].innerHTML,/Remove this filter/);
  assert.doesNotMatch(unsupported.elements['record-results'].innerHTML,/class="record-card/);
  console.log('Records context and inherited-country regressions passed.');
})().catch(error=>{console.error(error);process.exitCode=1});
