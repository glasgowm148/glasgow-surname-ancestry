const {test} = require('node:test');
const assert = require('node:assert/strict');
const {recordMatchesScope} = require('../tools/record_search.js');
const canonical = id => id.toLowerCase();

test('shared baptism records appear for each explicitly associated person', () => {
  const records = [
    {catalogue_id:'glasgow-3103', profile_ids:'Glasgow-3103 | Glasgow-2682 | Duffe-18 | Glasgow-4114'},
    {catalogue_id:'glasgow-3368', profile_ids:'Glasgow-3368 | Glasgow-2682 | Duffe-18 | Glasgow-4114'}
  ];
  for(const record of records){
    assert.equal(recordMatchesScope(record,new Set(['duffe-18']),canonical),true);
    assert.equal(recordMatchesScope(record,new Set([record.catalogue_id]),canonical),true);
    assert.equal(recordMatchesScope(record,new Set(['glasgow-9999']),canonical),false);
    assert.equal(recordMatchesScope(record,new Set(),canonical),false);
    assert.equal(recordMatchesScope(record,null,canonical),true);
  }
});

test('scope respects canonical aliases and does not infer associations from prose', () => {
  const record = {catalogue_id:'glasgow-1', profile_ids:' Glasgow-2 ', note:'Duffe-18'};
  const resolve = id => id.toLowerCase()==='glasgow-2'?'glasgow-3':canonical(id);
  assert.equal(recordMatchesScope(record,new Set(['glasgow-3']),resolve),true);
  assert.equal(recordMatchesScope(record,new Set(['duffe-18']),resolve),false);
  assert.equal(recordMatchesScope({catalogue_id:'glasgow-1'},new Set(['glasgow-1']),canonical),true);
  assert.equal(recordMatchesScope({profile_ids:'Glasgow-1'},new Set(['glasgow-1']),canonical),true);
});
