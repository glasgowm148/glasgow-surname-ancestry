// Prepare/apply the reviewed GRONI birth-location cleanup, one profile at a time.
// Default is preparation only. Apply with:
//   WT_EDIT_TABID=<unique-CDP-page-id> node tools/prepare_groni_birth_location_normalization.mjs --apply
// The same tab is pinned for every wt_apply invocation; progress is resumable.
import { readFileSync, writeFileSync, mkdirSync, existsSync } from 'fs';
import { spawn, execFileSync } from 'child_process';

const ROOT = process.cwd();
const LOGS = ['groni-birth-creation-log-2026-09-23.json','groni-extra-birth-creation-log-2026-09-23.json','groni-four-more-birth-creation-log-2026-09-23.json'].map(x => `${ROOT}/surname-research/indexes/${x}`);
const OUT = `${ROOT}/tmp/groni-birth-location-normalization`; mkdirSync(OUT, { recursive: true });
const STATE = `${OUT}/progress.json`;
const tabid = process.env.WT_EDIT_TABID;
if (!tabid) throw Error('Set WT_EDIT_TABID to one unique WikiTree CDP page id.');

function targets() {
  const seen = new Map();
  for (const file of LOGS) for (const p of JSON.parse(readFileSync(file)).created || []) {
    if (p.id && p.uid && p.registration) seen.set(p.id, p);
  }
  return [...seen.values()].sort((a,b) => a.id.localeCompare(b.id));
}
function fetchLocations(profiles) {
  const code = `import json, sys
from src.wikitree_family_export import post_wikitree
ids = json.load(sys.stdin)
out = {}
for start in range(0, len(ids), 25):
    data = post_wikitree({'action': 'getPeople', 'keys': ','.join(ids[start:start+25]), 'fields': 'Name,BirthLocation', 'resolveRedirect': '1'})
    for value in (data.get('people') or {}).values():
        if isinstance(value, dict) and value.get('Name'):
            out[value['Name']] = value.get('BirthLocation') or ''
print(json.dumps(out))`;
  return JSON.parse(execFileSync(`${ROOT}/.venv/bin/python`, ['-c', code], { cwd: ROOT, input: JSON.stringify(profiles.map(p => p.id)), encoding: 'utf8', env: process.env }));
}
function desired(location) {
  const m = String(location || '').match(/^(.+?) registration district, Ireland$/i);
  return m ? `${m[1]}, Ireland` : null;
}
function loadState() { return existsSync(STATE) ? JSON.parse(readFileSync(STATE)) : { completed: {}, errors: {} }; }
function saveState(s) { writeFileSync(STATE, JSON.stringify(s, null, 2) + '\n'); }

const state=loadState(), all=targets();
let locations;
try { locations = fetchLocations(all); } catch (e) { throw Error(`WikiTree API read failed: ${e.message}`); }
for (const p of all) {
  if (state.completed[p.id]?.status === 'applied' || state.completed[p.id]?.status === 'unchanged') continue;
  try {
    const liveLocation = locations[p.id];
    if (!liveLocation) throw Error('Live birth location unavailable from WikiTree API.');
    const next=desired(liveLocation);
    if(!next){state.completed[p.id]={status:'unchanged',location:liveLocation,registration:p.registration};saveState(state);continue;}
    const patch={u:p.uid,summary:`Use concise birth location from GRONI district ${p.registration}`,sugid:'summarySuggestion-bio',set:{mBirthLocation:next},status:{BirthLocation:'guess'},registration:p.registration,profile:p.id,source_location:liveLocation,target_location:next};
    const file=`${OUT}/${p.id}.json`; writeFileSync(file,JSON.stringify(patch,null,2)+'\n');
    let result={};
    if(process.argv.includes('--apply')) await new Promise((resolve,reject)=>{let out='';const c=spawn('node',['tools/wikitree/wt_apply.mjs',file],{env:{...process.env,TABID:tabid,WT_PARALLEL:'1'}});c.stdout.on('data',d=>{out+=d});c.stderr.pipe(process.stderr);c.on('close',code=>{try{result=JSON.parse(out.trim().split(/\n/).pop())}catch(e){return reject(Error(`wt_apply returned non-JSON: ${out}`))} if(code||!result.after?.saved)return reject(Error(`wt_apply did not confirm saved: ${out}`));resolve()});});
    state.completed[p.id]={status:process.argv.includes('--apply')?'applied':'prepared',location:next,registration:p.registration,file,after:result.after||null}; delete state.errors[p.id]; saveState(state);
    if(process.argv.includes('--apply')) { const verified=Object.fromEntries(Object.entries(state.completed).filter(([,v])=>v.status==='applied')); writeFileSync(`${OUT}/live-verified.json`,JSON.stringify({updated:new Date().toISOString(),profiles:verified},null,2)+'\n'); }
  } catch(e) { state.errors[p.id]={error:String(e),registration:p.registration}; saveState(state); if(process.argv.includes('--apply')) throw e; }
}
console.log(JSON.stringify({profiles:all.length,completed:Object.keys(state.completed).length,errors:Object.keys(state.errors).length,output:OUT,apply:process.argv.includes('--apply')},null,2));
