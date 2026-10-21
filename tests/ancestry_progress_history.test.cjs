const {test} = require('node:test');
const assert = require('node:assert/strict');
const {dailyHistory, historySeries} = require('../tools/ancestry_progress.js');

test('daily history uses the final comparable snapshot and excludes method changes', () => {
  const rows = dailyHistory([
    {date:'2026-10-15', method_version:2, fixed_cohort:{confident:{edge_count:500}}},
    {date:'2026-10-16', method_version:3, fixed_cohort:{confident:{edge_count:346}}},
    {date:'2026-10-16', method_version:3, fixed_cohort:{confident:{edge_count:347}}},
    {date:'2026-10-17', method_version:3, fixed_cohort:{confident:{edge_count:345}, supported:{edge_count:384}}}
  ], 3, 'fixed');
  assert.deepEqual(historySeries(rows, 'confident', 'edge_count'), [
    {date:'2026-10-16', value:347}, {date:'2026-10-17', value:345}
  ]);
  assert.deepEqual(historySeries(rows, 'supported', 'edge_count'), [
    {date:'2026-10-16', value:null}, {date:'2026-10-17', value:384}
  ]);
});

test('early cohorts begin with recorded measurements, without historical backfill', () => {
  const rows = dailyHistory([
    {date:'2026-10-16', method_version:3, fixed_cohort:{confident:{edge_count:347}}},
    {date:'2026-10-20', method_version:3, cohorts:{1650:{confident:{edge_count:74}}}}
  ], 3, '1650');
  assert.deepEqual(historySeries(rows, 'confident', 'edge_count'), [{date:'2026-10-20', value:74}]);
  assert.deepEqual(dailyHistory([], 3, '1650'), []);
});

test('confidence coverage uses each dated working denominator and preserves gaps', () => {
  const rows = [
    {date:'2026-10-16', metrics:{working:{edge_count:100}, confident:{edge_count:30}}},
    {date:'2026-10-17', metrics:{working:{edge_count:120}, confident:{edge_count:48}}},
    {date:'2026-10-18', metrics:{working:{edge_count:0}, confident:{edge_count:0}}},
    {date:'2026-10-19', metrics:{working:{edge_count:120}}}
  ];
  assert.deepEqual(historySeries(rows, 'confident', 'assessed_links_percent').map(p => p.value), [30, 40, null, null]);
});

test('exact confidence tracks within-band changes without filling older snapshots', () => {
  const rows = [
    {date:'2026-10-20', metrics:{working:{edge_count:100}}},
    {date:'2026-10-21', metrics:{working:{individual_confidence:{mean_percent:82}}}},
    {date:'2026-10-22', metrics:{working:{individual_confidence:{mean_percent:86}}}},
    {date:'2026-10-23', metrics:{working:{individual_confidence:{mean_percent:null}}}}
  ];
  assert.deepEqual(historySeries(rows, 'working', 'reviewed_confidence_percent').map(p => p.value), [null, 82, 86, null]);
});
