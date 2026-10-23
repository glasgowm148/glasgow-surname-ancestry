const {test} = require('node:test');
const assert = require('node:assert/strict');
const {dailyHistory, historySeries, confidenceHistory, uncertaintyMeasurements} = require('../tools/ancestry_progress.js');
const {researchHistory} = require('../tools/ancestry_progress.js');

const finding=(kind,before,after,extra={})=>({kind,before_percent:before,after_percent:after,cohorts:['1850'],baseline:true,date:'2026-10-23',assessment_status:after>=90?'proved':after>=60?'probable':'possible',research_event:kind==='first'?null:{type:kind==='new'?'father_attachment':'confidence_change',date:'2026-10-23'},...extra});
test('first-time grading and new indexed people cannot inflate research gains',()=>{
  const rows=[...Array.from({length:1000},()=>finding('first',null,99)),finding('new',null,99,{research_event:null,baseline:false}),finding('new',null,67,{research_event:null})];
  const result=researchHistory(rows,'1850');
  assert.equal(result.increases,0);assert.equal(result.newFathers,0);assert.equal(result.firstRatings,1000);
  assert.deepEqual(result.points.map(p=>p.confident),[0]);
});
test('five-grade research history retains downgrades and changes within a grade',()=>{
  const result=researchHistory([finding('change',71,95,{previous_assessment:{status:'probable'}}),finding('change',95,80,{previous_assessment:{status:'proved'}}),finding('change',80,85,{previous_assessment:{status:'probable'}}),finding('change',22,35,{previous_assessment:{status:'uncertain'}})],'1850');
  assert.equal(result.increases,3);assert.equal(result.decreases,1);
  assert.deepEqual(Object.fromEntries(['confident','probable','possible','uncertain','unknown'].map(k=>[k,result.points.at(-1)[k]])),{confident:0,probable:0,possible:1,uncertain:-1,unknown:0});
  assert.equal(result.points[0].date,null); // No invented earlier measurement date.
});
test('an evidenced father attachment moves Unknown once; an unselected candidate score is not its earlier grade',()=>{
  const result=researchHistory([finding('new',18,38,{previous_assessment:{status:'uncertain',working_selection:false},research_event:{type:'father_attachment',date:'2026-10-16'}})],'fixed');
  assert.equal(result.increases,0);assert.equal(result.newFathers,1);
  assert.equal(result.points.at(-1).unknown,-1);assert.equal(result.points.at(-1).possible,1);assert.equal(result.points.at(-1).uncertain,0);
  assert.equal(result.points.at(-1).date,'2026-10-16');
});
test('research gains follow the selected cohort and exclude undated reviews',()=>{
  const rows=[finding('change',71,95,{cohorts:['1850'],baseline:false}),finding('change',71,95,{cohorts:['1650','1850'],research_event:{type:'confidence_change',date:null}})];
  assert.equal(researchHistory(rows,'1850').increases,1);
  assert.equal(researchHistory(rows,'1650').increases,0);
  assert.equal(researchHistory(rows,'fixed').increases,0);
});

test('first percentages count a changed saved grade without inventing an earlier percentage',()=>{
  const result=researchHistory([
    finding('first',null,95,{previous_assessment:{status:'uncertain'},research_event:{type:'confidence_change',date:'2026-10-23',before_grade:'uncertain',after_grade:'confident'}}),
    finding('first',null,75,{previous_assessment:{status:'confident'},research_event:{type:'confidence_change',date:'2026-10-23',before_grade:'confident',after_grade:'probable'}}),
    finding('first',null,99,{previous_assessment:{status:'confident'}}),
    finding('first',null,99,{previous_assessment:{status:'unmarked'}})
  ],'1850');
  assert.equal(result.increases,1);assert.equal(result.decreases,1);assert.equal(result.qualitativeChanges,2);
  assert.equal(result.firstRatings,2);assert.equal(result.points.at(-1).unknown,0);
  assert.equal(result.points.at(-1).uncertain,-1);assert.equal(result.points.at(-1).probable,1);
});
test('replacement recommendations keep ungraded named fathers separate from absent fathers',()=>{
  const rows=[finding('new',null,67,{assertion_id:'replacement',catalogue_father_action:'replace',research_event:{type:'father_replacement',date:'2026-10-23',before_grade:null,after_grade:'probable'}}),
    finding('new',null,42,{assertion_id:'addition',catalogue_father_action:'add',research_event:{type:'father_attachment',date:'2026-10-23',before_grade:'unknown',after_grade:'possible'}}),
    finding('new',null,97,{assertion_id:'outside',catalogue_father_action:'add',cohorts:[],baseline:false,research_event:null})];
  const result=researchHistory([...rows,rows[0]],'1850');
  assert.equal(result.newFathers,1);assert.equal(result.replacements,1);assert.equal(result.increases,0);
  assert.equal(result.ungradedReplacements,1);assert.equal(result.points.at(-1).unknown,-1);
  assert.equal(result.catalogueProposals,3);assert.equal(result.cohortProposals,2);
});

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

test('confidence trend retains same-day changes without inventing earlier percentages', () => {
  const measured = (mean, rated) => ({working:{individual_confidence:{mean_percent:mean, rated_edge_count:rated, unrated_edge_count:100-rated, rated_edges_percent:rated}}});
  const snapshots = [
    {date:'2026-10-20', method_version:3, fixed_cohort:{working:{edge_count:100}}},
    {date:'2026-10-21', method_version:2, fixed_cohort:measured(99, 50)},
    {date:'2026-10-21', method_version:3, fixed_cohort:measured(82, 20)},
    {date:'2026-10-21', method_version:3, fixed_cohort:measured(82, 20)},
    {date:'2026-10-21', method_version:3, fixed_cohort:measured(86, 21)},
    {date:'2026-10-21', method_version:3, fixed_cohort:measured(85, 22)},
    {date:'2026-10-22', method_version:3, cohorts:{1650:measured(90, 10)}}
  ];
  assert.deepEqual(confidenceHistory(snapshots, 3, 'fixed').map(row=>[row.date,row.revision,row.mean_percent,row.rated_edge_count]), [
    ['2026-10-21',1,82,20], ['2026-10-21',2,86,21], ['2026-10-21',3,85,22]
  ]);
  assert.deepEqual(confidenceHistory(snapshots, 3, '1650').map(row=>row.mean_percent), [90]);
});

test('uncertainty separates all below confident from the narrower grade and review gaps', () => {
  const result = uncertaintyMeasurements({working:{edge_count:1396,edge_status_counts:{uncertain:137,possible:145,probable:444,proved:653,confident:2,strongly_supported:15}},confident:{edge_count:670}});
  assert.equal(result.total,726);
  assert.equal(result.uncertain,137);
  assert.equal(result.unmarked,0);
  assert.equal(result.unknown,null);
  assert.equal(uncertaintyMeasurements({working:{father_listing:{unknown_count:395,population:1798}}}).unknown,395);
  assert.equal(result.total,result.uncertain+result.possible+result.probable+result.unmarked);
  assert.equal(result.percent,100*726/1396);
  assert.equal(uncertaintyMeasurements({working:{edge_count:100}}).total,null);
  assert.equal(uncertaintyMeasurements({working:{edge_count:100},confident:{edge_count:50}}).uncertain,null);
  assert.equal(uncertaintyMeasurements({working:{edge_count:0},confident:{edge_count:0}}).percent,null);
});

test('uncertainty daily comparisons preserve increases, missing grades and changing denominators', () => {
  const snapshots = [
    {date:'2026-10-20',method_version:2,cohorts:{1850:{working:{edge_count:200},confident:{edge_count:190}}}},
    {date:'2026-10-20',method_version:3,cohorts:{1850:{working:{edge_count:100,edge_status_counts:{uncertain:20,unmarked:30}},confident:{edge_count:50}}}},
    {date:'2026-10-21',method_version:3,cohorts:{1850:{working:{edge_count:110,edge_status_counts:{uncertain:25,unmarked:35}},confident:{edge_count:50}}}},
    {date:'2026-10-22',method_version:3,cohorts:{1850:{working:{edge_count:120},confident:{edge_count:70}}}}
  ];
  const rows=dailyHistory(snapshots,3,'1850').map(row=>uncertaintyMeasurements(row.metrics));
  assert.deepEqual(rows.map(row=>row.total),[50,60,50]);
  assert.deepEqual(rows.map(row=>row.uncertain),[20,25,null]);
  assert.equal(rows[1].percent,100*60/110);
});
