/* Execute the production catalogue map model against a bounded fixture. */
const assert = require('assert');
const fs = require('fs');
const path = require('path');

const source = fs.readFileSync(path.join(__dirname, '..', 'tools', 'catalogue_search.js'), 'utf8');
const start = source.indexOf('  async function catalogueMapModel(');
const end = source.indexOf('  function catalogueMapMarkup(', start);
assert(start >= 0 && end > start, 'catalogueMapModel boundaries must remain discoverable');
const catalogueMapModel = new Function(`${source.slice(start, end)}; return catalogueMapModel;`)();

const people = [
  {id: 'alpha-1', name: 'Alpha Glasgow'},
  {id: 'beta-2', name: 'Beta Glasgow'},
  {id: 'unmapped-3', name: 'Unmapped Glasgow'},
];
const data = {world: [], points: [
  {lat: 55, lon: -4, name: 'Glasgow', precision: 'Settlement centrepoint', items: [['r1', 'alpha-1']]},
  {lat: 55, lon: -4, name: 'Glasgow', precision: 'Settlement centrepoint', items: [['r2', 'beta-2'], ['r3', 'outside-9']]},
  {lat: 40, lon: -98, name: 'United States · country-level point', broad: true, items: [['r4', 'beta-2']]},
  {lat: null, lon: 0, name: 'Invalid null', items: [['r5', 'alpha-1']]},
  {lat: '', lon: '', name: 'Invalid empty', items: [['r6', 'alpha-1']]},
  {lat: 'not-a-coordinate', lon: 0, name: 'Invalid text', items: [['r7', 'alpha-1']]},
  {lat: 91, lon: 0, name: 'Invalid range', items: [['r8', 'alpha-1']]},
]};

(async () => {
  const model = await catalogueMapModel(people, data);
  assert.strictEqual(model.total, 3);
  assert.strictEqual(model.mappedPeople.size, 2);
  assert.strictEqual(model.unmapped, 1);
  assert.deepStrictEqual([...model.mappedPeople].sort(), ['alpha-1', 'beta-2']);
  assert.strictEqual(model.markers.length, 2, 'same supplied location should consolidate people');
  assert.strictEqual(model.markers[1].broad, true);
  assert.match(model.markers[1].precision, /Approximate|country[- ]level|fallback/i);
  assert.ok(model.markers.every(marker => marker.people.has('alpha-1') || marker.people.has('beta-2')));
  console.log('Catalogue map model fixture passed.');
})().catch(error => { console.error(error); process.exitCode = 1; });
