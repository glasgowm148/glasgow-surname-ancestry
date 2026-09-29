// Prepare (and optionally apply) the nine reviewed GRONI death patches plus
// the two consecutive-day infant entries.  Default mode is preparation only.
// Usage: node tools/prepare_groni_death_live_patches.mjs
// Apply only after review: ... --apply.  WT_PARALLEL=1 is passed to wt_apply.
import { readFileSync, mkdirSync, writeFileSync, existsSync } from 'fs';
import { spawn, execFileSync } from 'child_process';

const ROOT = process.cwd();
const reviewed = JSON.parse(readFileSync('/tmp/groni-death-safe-live-patches.json', 'utf8'));
const out = '/tmp/groni-death-live-patches'; mkdirSync(out, { recursive: true });
const infant = [
  { profile: 'Glasgow-4310', u: 51623696, registration: 'D/1868/50/1007/11/275', date: '1868-07-16', place: 'Belfast, Ireland', sex: 'male' },
  { profile: 'Glasgow-4313', u: 51623705, registration: 'D/1873/50/1007/22/120', date: '1873-01-20', place: 'Belfast, Ireland', sex: 'female' },
];

function apiPeople(uids) {
  const code = `import json,sys
from src.wikitree_family_export import post_wikitree
data=post_wikitree({'action':'getPeople','keys':','.join(map(str,json.load(sys.stdin))),'fields':'Name,Bio,DeathDate,DeathLocation','bioFormat':'wiki','resolveRedirect':'1'})
print(json.dumps(data.get('people') or {}))`;
  return JSON.parse(execFileSync(`${ROOT}/.venv/bin/python`, ['-c', code], { cwd: ROOT, input: JSON.stringify(uids), encoding: 'utf8', env: process.env }));
}
function current(u) {
  const people = apiPeople([u]);
  const p = Object.values(people).find(x => String(x.Id || x.Name || '') === String(u)) || Object.values(people)[0];
  if (!p?.Bio && !p?.bio) throw Error(`Could not fetch live biography for uid ${u} from WikiTree API`);
  return { ...p, Bio: p.Bio || p.bio };
}
function deathBlock(p) {
  const i = p.text.indexOf(p.registration);
  if (i < 0) throw Error(`No death citation found for ${p.registration}`);
  const start = p.text.lastIndexOf('\n', i) + 1;
  const end = p.text.indexOf('</ref>', i) + 6;
  if (end < 6 || end - start > 1200) throw Error(`Could not isolate death citation for ${p.registration}`);
  return p.text.slice(start, end).trim()
    .replace(' The identification is an inferred match from the name, age and locality.', '')
    .replace(' This is the indexed death that matches the strong candidate already described above; the index does not independently prove the identification.', '')
    .replace('; the existing Kilrea location is retained.', '.')
    .replace(/; this (?:one-day|five-day|one-month) discrepancy is recorded without changing the structured date\./, '.')
    .replace(/\b\d{4}-\d{2}-\d{2}\b/g, s => new Date(`${s}T00:00:00Z`).toLocaleDateString('en-GB',{day:'numeric',month:'long',year:'numeric',timeZone:'UTC'}));
}
function appendOnce(text, block, registration) {
  if (text.includes(registration)) return text;
  const at = text.search(/^==\s*Sources\s*==/mi);
  return at < 0 ? `${text.trim()}\n\n${block}\n` : `${text.slice(0, at).trimEnd()}\n\n${block}\n\n${text.slice(at)}`;
}

const patches = [];
for (const p of reviewed) {
  const live = current(p.uid);
  const text = appendOnce(live.Bio, deathBlock(p), p.registration);
  patches.push({ u: p.uid, text, summary: p.summary, sugid: p.sugid, set: p.set, status: p.status, registration: p.registration, profile: p.profile, risky: p.manager === 0 || p.date_conflict });
}
for (const p of infant) {
  const natural = new Date(`${p.date}T00:00:00Z`).toLocaleDateString('en-GB',{day:'numeric',month:'long',year:'numeric',timeZone:'UTC'});
  const text = appendOnce(current(p.u).Bio, `An unnamed Glasgow ${p.sex === 'male' ? 'boy' : 'girl'} died on ${natural}, one day after a Belfast birth registration.<ref name="DeathIndex${p.registration.replaceAll('/', '')}">[https://geni.nidirect.gov.uk/search/death GRONI civil death index], unnamed ${p.sex} infant, ${natural}, Belfast registration district, ${p.registration}.</ref>`, p.registration);
  patches.push({ u: p.u, text, summary: `Add indexed infant death record ${p.registration}.`, sugid: 'summarySuggestion-sources', set: { mDeathDate: p.date, mDeathLocation: p.place }, status: { DeathDate: 'guess', DeathLocation: 'guess' }, registration: p.registration, profile: p.profile, risky: true });
}
for (let i = 0; i < patches.length; i++) writeFileSync(`${out}/${String(i + 1).padStart(2, '0')}-${patches[i].profile}.json`, JSON.stringify(patches[i], null, 2) + '\n');
console.log(JSON.stringify({ prepared: patches.length, directory: out, risky: patches.filter(p => p.risky).map(p => `${p.profile}:${p.registration}`), apply: process.argv.includes('--apply') }));
if (!process.argv.includes('--apply')) process.exit(0);
if (!process.env.WT_EDIT_TABID) throw Error('Set WT_EDIT_TABID to one unique WikiTree CDP page id for --apply.');
const verifiedLog = `${out}/verified-live-saves.jsonl`;
const verified = new Set(existsSync(verifiedLog) ? readFileSync(verifiedLog, 'utf8').split(/\r?\n/).filter(Boolean).map(line => JSON.parse(line).registration) : []);
for (const p of patches) {
  if (verified.has(p.registration)) { console.log(JSON.stringify({ profile: p.profile, registration: p.registration, skipped: 'already verified' })); continue; }
  const file = `${out}/${String(patches.indexOf(p) + 1).padStart(2, '0')}-${p.profile}.json`;
  const liveBefore = current(p.u);
  if (liveBefore.Bio.includes(p.registration)) {
    writeFileSync(verifiedLog, JSON.stringify({ profile: p.profile, registration: p.registration, uid: p.u, verified_live: true, unchanged: true, source_id: p.registration, at: new Date().toISOString() }) + '\n', { flag: 'a' });
    console.log(JSON.stringify({ profile: p.profile, registration: p.registration, skipped: 'already live' }));
    continue;
  }
  await new Promise((resolve, reject) => {
    const c = spawn('node', ['tools/wikitree/wt_apply.mjs', file], { env: { ...process.env, TABID: process.env.WT_EDIT_TABID, WT_PARALLEL: process.env.WT_PARALLEL || '1' } });
    let output = ''; c.stdout.on('data', b => { output += b; process.stdout.write(b); }); c.stderr.on('data', b => { output += b; process.stderr.write(b); });
    c.on('exit', code => {
      const lines = output.trim().split(/\r?\n/).reverse(); let result;
      for (const line of lines) { try { const x = JSON.parse(line); if (x.after) { result = x; break; } } catch {} }
      if (code || !result?.after?.saved) return reject(Error(`wt_apply did not confirm saved URL for ${p.profile}`));
      if (!current(p.u).Bio.includes(p.registration)) return reject(Error(`WikiTree API did not verify ${p.registration} for ${p.profile}`));
      writeFileSync(verifiedLog, JSON.stringify({ profile: p.profile, registration: p.registration, uid: p.u, saved_url: result.after.url, verified_live: true, source_id: p.registration, at: new Date().toISOString() }) + '\n', { flag: 'a' }); resolve();
    });
  });
}
