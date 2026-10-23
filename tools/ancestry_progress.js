(() => {
  'use strict';
  function dailyHistory(snapshots, methodVersion, cohort) {
    const days = new Map();
    for (const row of snapshots) {
      if (row.method_version !== methodVersion) continue;
      const metrics = cohort === 'fixed' ? row.fixed_cohort : row.cohorts?.[cohort];
      if (metrics) days.set(row.date, {date: row.date, metrics});
    }
    return [...days.values()].sort((a, b) => a.date.localeCompare(b.date));
  }
  function historySeries(rows, view, metric) {
    return rows.map(row => {
      const assessed = row.metrics[view]?.edge_count, working = row.metrics.working?.edge_count;
      const value = metric === 'reviewed_confidence_percent'
        ? row.metrics[view]?.individual_confidence?.mean_percent
        : metric === 'assessed_links_percent'
        ? (Number.isFinite(assessed) && working > 0 ? 100 * assessed / working : null)
        : row.metrics[view]?.[metric];
      return {date: row.date, value: Number.isFinite(value) ? value : null};
    });
  }
  function confidenceHistory(snapshots, methodVersion, cohort) {
    const rows = [], revisions = new Map();
    let previous;
    for (const snapshot of snapshots) {
      if (snapshot.method_version !== methodVersion) continue;
      const metrics = cohort === 'fixed' ? snapshot.fixed_cohort : snapshot.cohorts?.[cohort];
      const confidence = metrics?.working?.individual_confidence;
      if (!Number.isFinite(confidence?.mean_percent)) continue;
      const signature = JSON.stringify([snapshot.date, confidence.mean_percent, confidence.rated_edge_count, confidence.unrated_edge_count]);
      if (signature === previous) continue;
      previous = signature;
      const revision = (revisions.get(snapshot.date) || 0) + 1;
      revisions.set(snapshot.date, revision);
      rows.push({date:snapshot.date, revision, ...confidence});
    }
    return rows;
  }
  function uncertaintyMeasurements(metrics) {
    const working = metrics?.working?.edge_count, confident = metrics?.confident?.edge_count;
    const counts = metrics?.working?.edge_status_counts;
    const total = Number.isFinite(working) && Number.isFinite(confident) ? working-confident : null;
    const grades = Object.fromEntries(['uncertain','possible','probable','unmarked'].map(key =>
      [key, counts ? (counts[key] ?? 0) : null]));
    const listing = metrics?.working?.father_listing;
    return {total, percent:total !== null && working > 0 ? 100*total/working : null, working,
      unknown:Number.isFinite(listing?.unknown_count)?listing.unknown_count:null, population:listing?.population, ...grades};
  }
  function individualFindings(rows, kind, cohort, beyond = false) {
    return rows.filter(row => (kind === 'all' || row.kind === kind) &&
      (beyond || (cohort === 'fixed' ? row.baseline : row.cohorts.includes(String(cohort)))));
  }
  if (typeof module !== 'undefined' && module.exports) module.exports = {dailyHistory, historySeries, confidenceHistory, uncertaintyMeasurements, individualFindings};
  if (typeof document === 'undefined') return;
  const element = document.getElementById('ancestry-progress-data');
  if (!element) return;
  const data = JSON.parse(element.textContent), byId = id => document.getElementById(id);
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const number = value => Number(value).toLocaleString('en-GB');
  function renderFindings() {
    const cohort = byId('history-cohort').value === 'fixed' ? 'fixed' : byId('progress-cutoff').value;
    const rows = individualFindings(data.individual_findings || [], byId('findings-kind').value, cohort, byId('findings-all-cohorts').checked);
    const grade = value => ({proved:'Confident', confident:'Confident', strongly_supported:'Confident', probable:'Probable', possible:'Possible', uncertain:'Uncertain', unmarked:'Unmarked', unknown:'Not rated'}[value] || String(value || 'Not recorded').replaceAll('_', ' '));
    const person = value => `<a href="${esc(value.url)}">${esc(value.name)}</a>${value.wikitree_url ? ` · <a href="${esc(value.wikitree_url)}">WikiTree</a>` : ' · local account'} `;
    byId('findings-count').textContent = `${number(rows.length)} findings · ${byId('findings-all-cohorts').checked ? 'all available cohorts' : cohort === 'fixed' ? 'fixed baseline people' : `through ${cohort}`}`;
    byId('findings-rows').innerHTML = rows.length ? rows.map(row => {
      const percentage = row.before_percent == null ? `${row.after_percent}%` : `${row.before_percent}% → ${row.after_percent}%`;
      const label = row.kind === 'change' ? percentage : `${row.kind === 'new' ? 'New father connection' : 'First individual rating'} · ${percentage}`;
      const prior = row.previous_assessment;
      return `<tr><td>${esc(row.date || 'Date not recorded')}</td><td>${person(row.child)}<br>Father: ${person(row.father)}${row.identity_hold ? '<br><strong>Identity HOLD · record-defined person; adult identity unresolved</strong>' : ''}</td><td><strong>${esc(label)}</strong>${prior ? `<br>Prior grade: ${esc(grade(prior.status || prior.assessment_status))}` : ''}<br>Reviewed grade: ${esc(grade(row.assessment_status))}</td><td><details><summary>Evidence and assessment reason</summary><p>${esc(row.reason)}</p>${row.limitations ? `<p>${esc(row.limitations)}</p>` : ''}${prior ? `<p>Prior basis: ${esc(prior.source_basis || prior.reason || prior.basis || 'not recorded')}</p>` : ''}<a href="${esc(row.child.url)}">Read the sourced biography</a></details></td></tr>`;
    }).join('') : '<tr><td colspan="4">No findings of this kind are recorded for this cohort. Choose another finding type or include beyond the selected cohort.</td></tr>';
  }
  function renderPriorities() {
    const early = byId('priority-early').checked, confident = byId('priority-order').value === 'confident';
    const rows = (data.research_priorities || []).filter(row => !early || (row.year != null && row.year <= 1650));
    rows.sort((a,b) => confident
      ? b.confident_pair_gain-a.confident_pair_gain || b.cross_pairs-a.cross_pairs || a.child.localeCompare(b.child)
      : b.cross_pairs-a.cross_pairs || a.child.localeCompare(b.child));
    byId('priority-count').textContent = `Showing ${Math.min(20,rows.length)} of ${number(rows.length)} father links below confident${early?' dated by 1650':''}. Counts use the same people through 1850.`;
    const remaining = uncertaintyMeasurements(data.cohorts['1850']);
    byId('priority-uncertainty-summary').innerHTML = `<strong>${remaining.unknown===null?'Unknown fathers not yet measured':`${number(remaining.unknown)} unknown fathers`} · ${number(remaining.total)} named father links below confident</strong><span>${number(remaining.uncertain)} uncertain · ${number(remaining.possible)} possible · ${number(remaining.probable)} probable${remaining.unmarked?` · ${number(remaining.unmarked)} unmarked`:''} · through 1850</span><a href="#uncertainty-history">See how this has changed over time ↑</a>`;
    byId('priority-rows').innerHTML = rows.slice(0,20).map(row => `<tr><td><a href="${esc(row.father_url)}">${esc(row.father_name)}</a> → <a href="${esc(row.child_url)}">${esc(row.child_name)}</a><small>${esc(row.father)} → ${esc(row.child)} · ${esc(row.year ?? 'Undated')}</small></td><td>${Number.isFinite(row.confidence_percent)?`${row.confidence_percent}%`:'Not individually rated'}<small>${esc(row.status)}</small></td><td>${number(row.child_side)}</td><td>${number(row.cross_pairs)}</td><td>${number(row.confident_pair_gain)}<small>${number(row.confident_child_side)} × ${number(row.confident_parent_side)} people; ${row.confident_component_reduction} fewer confident branches</small></td><td><a href="${esc(row.analysis_url)}">${esc(row.next_test)}</a>${row.last_review?`<small>${esc(row.last_review)}</small>`:''}</td></tr>`).join('');
  }
  byId('priority-order').addEventListener('change', renderPriorities);
  byId('priority-early').addEventListener('change', renderPriorities);
  renderPriorities();
  const historyViews = [
    {key:'confident', label:'Confident', color:'#25734c'},
    {key:'supported', label:'Probable or stronger', color:'#386eaf'},
    {key:'working', label:'Working, including uncertain', color:'#a76812'}
  ];
  const historyMetrics = {
    reviewed_confidence_percent:'Mean individually reviewed father confidence (%)',
    assessed_links_percent:'Share of working father–child links (%)',
    edge_count:'Father–child links', largest_component_size:'People in largest branch',
    connected_pairs_percent:'Connected pairs (%)', component_count:'Separate paternal components'
  };
  function renderUncertaintyTrend(rows) {
    const measured = rows.map(row => ({date:row.date, ...uncertaintyMeasurements(row.metrics)}));
    const recorded = measured.filter(row => row.total !== null);
    const target = byId('uncertainty-trend-chart');
    if (!recorded.length) {
      byId('uncertainty-totals').innerHTML = '<p>No comparable uncertainty counts have been recorded for this cohort.</p>';
      byId('uncertainty-breakdown').innerHTML = '';
      byId('uncertainty-trend-rows').innerHTML = '';
      target.innerHTML = '';
      return;
    }
    const first = recorded[0], last = recorded[recorded.length-1], drop = first.total-last.total;
    const dateLabel = date => new Date(date+'T12:00:00Z').toLocaleDateString('en-GB',{day:'numeric',month:'short',timeZone:'UTC'});
    const change = (start,end) => end===start?'No change':`${number(Math.abs(start-end))} ${end<start?'fewer':'more'}`;
    const strict = recorded.filter(row => row.uncertain !== null);
    const strictFirst = strict[0], strictLast = strict[strict.length-1];
    const unknown = recorded.filter(row => row.unknown !== null), unknownFirst=unknown[0];
    byId('uncertainty-totals').innerHTML = `<div><span>Father links below confident</span><strong>${number(last.total)}</strong><small>${last.percent===null?'':`${last.percent.toFixed(1)}% of ${number(last.working)} father links`}</small></div><div><span>Change since ${esc(dateLabel(first.date))}</span><strong>${recorded.length>1?esc(change(first.total,last.total)):'First count'}</strong><small>${recorded.length>1?`${number(first.total)} → ${number(last.total)} · ${first.total>0?(Math.abs(drop)/first.total*100).toFixed(1)+'% '+(drop>=0?'drop':'increase'):'new baseline'}`:'No earlier comparable count'}</small></div><div><span>Uncertain grade only</span><strong>${last.uncertain===null?'Not recorded':number(last.uncertain)}</strong><small>${strict.length>1?`${number(strictFirst.uncertain)} → ${number(strictLast.uncertain)} · ${esc(change(strictFirst.uncertain,strictLast.uncertain))} since ${esc(dateLabel(strictFirst.date))}`:'Separate from possible and probable'}</small></div>`;
    byId('uncertainty-totals').innerHTML += `<div class="unknown-father-total"><span>Unknown father</span><strong>${last.unknown===null?'Not recorded':number(last.unknown)}</strong><small>${last.unknown===null?'No saved count':`${number(last.unknown)} of ${number(last.population)} people; no named father retained`}</small><small>${unknown.length>1?`${esc(change(unknownFirst.unknown,last.unknown))} since ${esc(dateLabel(unknownFirst.date))}`:unknownFirst?`First measured ${esc(dateLabel(unknownFirst.date))}`:''}</small></div>`;
    const grades = [['unknown','Unknown'],['uncertain','Uncertain'],['possible','Possible'],['probable','Probable'],['unmarked','Unmarked']];
    byId('uncertainty-breakdown').innerHTML = grades.map(([key,label]) => `<span class="uncertainty-${key}">${esc(label)} <strong>${last[key]===null?'Not recorded':number(last[key])}</strong></span>`).join('');
    const width = Math.max(300, Math.min(960,target.clientWidth || 960)), height=240, left=58, right=24, top=20, bottom=42;
    const max = Math.max(1,...recorded.flatMap(row=>[row.total,row.unknown ?? 0]))*1.1;
    const start=Date.parse(measured[0].date), end=Date.parse(measured[measured.length-1].date);
    const x = date => start===end ? (left+width-right)/2 : left+(Date.parse(date)-start)/(end-start)*(width-left-right);
    const y = value => height-bottom-value/max*(height-top-bottom);
    const svg = [`<svg viewBox="0 0 ${width} ${height}" role="img" aria-labelledby="uncertainty-chart-title uncertainty-chart-desc"><title id="uncertainty-chart-title">Unknown and uncertain fathers over time</title><desc id="uncertainty-chart-desc">Lower counts mean fewer gaps. Named father links below confident: ${number(first.total)} on ${esc(first.date)} to ${number(last.total)} on ${esc(last.date)}. Separate series count the uncertain grade and unknown fathers. Unknown: ${last.unknown===null?'not recorded':number(last.unknown)}. Missing earlier counts remain gaps. The vertical axis starts at zero. Full counts are in the table below.</desc>`];
    for (let i=0;i<=4;i++) {
      const value=max*i/4, yy=y(value);
      svg.push(`<line x1="${left}" x2="${width-right}" y1="${yy}" y2="${yy}" class="history-grid"/><text x="${left-10}" y="${yy+4}" text-anchor="end">${number(Math.round(value))}</text>`);
    }
    measured.filter((row,i)=>i===0 || i===measured.length-1 || (measured.length<=6) || i%Math.ceil(measured.length/5)===0).forEach(row=>svg.push(`<text x="${x(row.date)}" y="${height-14}" text-anchor="${row===measured[0]?'start':row===measured[measured.length-1]?'end':'middle'}">${esc(dateLabel(row.date))}</text>`));
    for (const [key,label,color] of [['total','Named fathers below confident','#9b5610'],['uncertain','Uncertain grade only','#a33237'],['unknown','Unknown father','#303f4b']]) {
      let path='', connected=false;
      for (const row of measured) {
        if (row[key]===null) {connected=false;continue;}
        path+=`${connected?'L':'M'}${x(row.date)},${y(row[key])} `;connected=true;
      }
      svg.push(`<path d="${path}" fill="none" stroke="${color}" stroke-width="3" ${key==='uncertain'?'stroke-dasharray="6 4"':''}/>`);
      measured.filter(row=>row[key]!==null).forEach(row=> {
        const labelText=`${row.date}: ${label}, ${number(row[key])}`;
        svg.push(`<circle cx="${x(row.date)}" cy="${y(row[key])}" r="5" fill="${color}" stroke="#fffdf8" stroke-width="2" tabindex="0" aria-label="${esc(labelText)}"><title>${esc(labelText)}</title></circle>`);
      });
    }
    target.innerHTML=svg.join('')+'</svg>';
    const cell = value => value===null?'Not recorded':number(value);
    byId('uncertainty-trend-rows').innerHTML = measured.map(row=>`<tr><th scope="row">${esc(row.date)}</th><td>${cell(row.total)}</td><td>${row.percent===null?'Not recorded':row.percent.toFixed(1)+'%'}</td>${grades.map(([key])=>`<td>${cell(row[key])}</td>`).join('')}</tr>`).join('');
  }
  function renderConfidenceTrend(cohort) {
    const rows = confidenceHistory(data.progress_history, data.history_method_version, cohort);
    const target = byId('confidence-trend-chart');
    if (!rows.length) {
      target.innerHTML = '<p class="history-empty">Exact confidence measurements have not yet been recorded for this cohort.</p>';
      byId('confidence-trend-summary').textContent = '';
      byId('confidence-trend-rows').innerHTML = '';
      return;
    }
    const first = rows[0], last = rows[rows.length-1], delta = last.mean_percent-first.mean_percent;
    const format = value => value.toFixed(2)+'%';
    byId('confidence-trend-summary').textContent = `${format(first.mean_percent)} → ${format(last.mean_percent)} (${delta>=0?'+':'−'}${Math.abs(delta).toFixed(2)} percentage points). ${number(last.rated_edge_count)} of ${number(last.rated_edge_count+last.unrated_edge_count)} father links individually rated; ${last.rated_edges_percent.toFixed(1)}% review coverage.`;
    const width = Math.max(300, Math.min(960, target.clientWidth || 960)), height = 220;
    const left = 62, right = 34, top = 24, bottom = 50;
    const values = rows.map(row=>row.mean_percent), low = Math.min(...values), high = Math.max(...values);
    const padding = Math.max(.5, (high-low)*.2), min = Math.max(0, low-padding), max = Math.min(100, high+padding);
    const x = i => rows.length===1 ? (left+width-right)/2 : left+i/(rows.length-1)*(width-left-right);
    const y = value => height-bottom-(value-min)/(max-min)*(height-top-bottom);
    const label = row => `${row.date} · review ${row.revision}`;
    const svg = [`<svg viewBox="0 0 ${width} ${height}" role="img" aria-labelledby="confidence-trend-title confidence-trend-desc"><title id="confidence-trend-title">Mean reviewed father confidence over time</title><desc id="confidence-trend-desc">Saved reviews in chronological order, evenly spaced. ${esc(byId('confidence-trend-summary').textContent)} The vertical axis starts at ${min.toFixed(2)}%. Full values are in the review data table.</desc>`];
    for (let i=0;i<=4;i++) {
      const value = min+(max-min)*i/4, yy = y(value);
      svg.push(`<line x1="${left}" x2="${width-right}" y1="${yy}" y2="${yy}" class="history-grid"/><text x="${left-10}" y="${yy+4}" text-anchor="end">${value.toFixed(1)}%</text>`);
    }
    svg.push(`<path d="${rows.map((row,i)=>`${i?'L':'M'}${x(i)},${y(row.mean_percent)}`).join(' ')}" fill="none" stroke="#386eaf" stroke-width="3"/>`);
    rows.forEach((row,i)=> {
      const title = `${label(row)}: ${format(row.mean_percent)}, ${row.rated_edge_count} rated father links`;
      svg.push(`<circle cx="${x(i)}" cy="${y(row.mean_percent)}" r="5" fill="#386eaf" stroke="#fffdf8" stroke-width="2" tabindex="0" aria-label="${esc(title)}"><title>${esc(title)}</title></circle>`);
      if (i===0 || i===rows.length-1) svg.push(`<text x="${x(i)}" y="${height-24}" text-anchor="${i===0?'start':'end'}">${esc(label(row))}</text>`);
    });
    target.innerHTML = svg.join('')+'</svg>';
    byId('confidence-trend-rows').innerHTML = rows.map(row=>`<tr><th scope="row">${esc(label(row))}</th><td>${format(row.mean_percent)}</td><td>${number(row.rated_edge_count)}</td><td>${row.rated_edges_percent.toFixed(1)}%</td></tr>`).join('');
  }
  function renderHistory() {
    renderFindings();
    const cutoff = byId('progress-cutoff').value;
    const fixed = byId('history-cohort').value === 'fixed';
    renderConfidenceTrend(fixed ? 'fixed' : cutoff);
    const metric = byId('history-metric').value;
    const rows = dailyHistory(data.progress_history, data.history_method_version, fixed ? 'fixed' : cutoff);
    renderUncertaintyTrend(rows);
    const exactConfidence = metric === 'reviewed_confidence_percent';
    const historyParams = new URLSearchParams(location.search);
    if (metric === 'edge_count') historyParams.delete('history');
    else historyParams.set('history', metric);
    if (fixed) historyParams.delete('historyCohort');
    else historyParams.set('historyCohort', 'selected');
    history.replaceState(null, '', location.pathname+'?'+historyParams+location.hash);
    const views = exactConfidence
      ? [{key:'working', label:'Reviewed father confidence', color:'#386eaf'}]
      : historyViews.filter(view => byId('history-'+view.key).checked);
    const confidenceControls = byId('history-confidence-levels');
    if (confidenceControls) confidenceControls.hidden = exactConfidence;
    const series = views.map(view => ({...view, points:historySeries(rows, view.key, metric)}));
    const values = series.flatMap(view => view.points.filter(p => p.value !== null).map(p => p.value));
    const percent = metric.endsWith('_percent');
    const decimals = metric === 'assessed_links_percent' ? 1 : 3;
    const format = value => percent ? value.toFixed(decimals)+'%' : number(value);
    const dateLabel = value => new Date(value+'T12:00:00Z').toLocaleDateString('en-GB', {day:'numeric', month:'short', timeZone:'UTC'});
    const scope = fixed ? `Fixed baseline: the same ${number(data.history_baseline.population)} people through ${data.history_baseline.cutoff}` : `Historical cohort through ${cutoff}: people available at each snapshot`;
    byId('history-cohort').options[1].textContent = `Selected cohort · through ${cutoff}`;
    byId('history-scope').textContent = scope + '. Comparable confidence measurements use the current method; earlier classification changes are excluded.';
    byId('history-note').textContent = (rows.length < 2 ? 'Only one dated snapshot is available for this cohort; its history starts here. Earlier cutoff measurements have not been reconstructed. ' : '') + 'Confidence coverage is the number of links at each confidence level divided by all working father–child links. Probable or stronger includes confident links. Missing measurements are gaps. Changes can include regrading existing fathers and publication repairs; they do not all represent newly connected families. These are not probabilities that an entire branch is correct.';
    byId('history-table-caption').textContent = `${historyMetrics[metric]} · ${scope}`;
    if (exactConfidence) byId('history-note').textContent = 'This averages exact confidence estimates across reviewed working father links, including uncertain fathers. Unreviewed links have no percentage. Changing which links are reviewed or selected can change the mean; compare review coverage too. This is a research assessment summary, not the probability that a branch or the whole tree is correct. Earlier unrecorded measurements remain gaps.';
    byId('history-table-head').innerHTML = '<tr><th scope="col">Date</th>'+views.map(view => `<th scope="col">${esc(view.label)}</th>`).join('')+(exactConfidence?'<th scope="col">Individually rated</th><th scope="col">Review coverage</th>':'')+'</tr>';
    byId('history-table-body').innerHTML = rows.map(row => '<tr><th scope="row">'+esc(row.date)+'</th>'+views.map(view => {
      const value = historySeries([row], view.key, metric)[0].value;
      return '<td>'+(Number.isFinite(value)?esc(format(value)):'Not recorded')+'</td>';
    }).join('')+(exactConfidence ? (() => {
      const coverage = row.metrics.working?.individual_confidence;
      return coverage ? `<td>${number(coverage.rated_edge_count)} of ${number(coverage.rated_edge_count+coverage.unrated_edge_count)}</td><td>${coverage.rated_edges_percent.toFixed(1)}%</td>` : '<td>Not recorded</td><td>Not recorded</td>';
    })() : '')+'</tr>').join('');
    byId('history-changes').innerHTML = series.map(view => {
      const points = view.points.filter(point => point.value !== null);
      if (!points.length) return '';
      const first = points[0], last = points[points.length-1], delta = last.value-first.value;
      const change = percent ? Math.abs(delta).toFixed(decimals)+' percentage points' : number(Math.abs(delta));
      const coverage = exactConfidence ? rows.find(row => row.date === last.date)?.metrics.working?.individual_confidence : null;
      const total = coverage ? coverage.rated_edge_count + coverage.unrated_edge_count : 0;
      const coverageText = coverage ? `<small>${number(coverage.rated_edge_count)} of ${number(total)} father links individually rated · ${coverage.rated_edges_percent.toFixed(1)}% coverage</small>` : '';
      const before = points.length > 1 ? `<small>${esc(format(first.value))} → ${esc(format(last.value))} · ${esc(dateLabel(first.date))}–${esc(dateLabel(last.date))}</small>` : '';
      return `<div class="history-${exactConfidence?'supported':view.key}"><span>${esc(view.label)}</span><strong>${esc(format(last.value))}</strong><small>${points.length>1?`${delta>0?'+':delta<0?'−':''}${esc(change)} since ${esc(dateLabel(first.date))}`:`First snapshot · ${esc(dateLabel(last.date))}`}</small>${before}${coverageText}</div>`;
    }).join('');
    if (!values.length) {
      byId('history-chart').innerHTML = `<p class="history-empty">${exactConfidence?'No individually rated father links have been recorded for this cohort.':'Select a confidence level to display its history.'}</p>`;
      return;
    }
    const width=Math.max(360, Math.min(960, byId('history-chart').clientWidth || 960)), height=330, left=70, right=28, top=28, bottom=54;
    const low=Math.min(...values), high=Math.max(...values), spread=high-low;
    const padding=Math.max(spread*.18, high*.025, metric==='connected_pairs_percent'?.005:2);
    const min=percent && metric!=='connected_pairs_percent'?0:Math.max(0, low-padding), max=percent && metric!=='connected_pairs_percent'?100:high+padding;
    const start=Date.parse(rows[0].date), end=Date.parse(rows[rows.length-1].date);
    const x=date => start===end ? (left+width-right)/2 : left+(Date.parse(date)-start)/(end-start)*(width-left-right);
    const y=value => height-bottom-(value-min)/(max-min)*(height-top-bottom);
    const svg = [`<svg viewBox="0 0 ${width} ${height}" role="img" aria-labelledby="history-svg-title history-svg-desc"><title id="history-svg-title">${esc(historyMetrics[metric])} over time</title><desc id="history-svg-desc">${esc(scope)}. Daily closing snapshots. Values are also available in the snapshot data table below. The vertical axis starts at ${esc(format(min))}.</desc>`];
    for(let i=0;i<=4;i++) {
      const value=min+(max-min)*i/4, yy=y(value);
      const label=percent?value.toFixed(metric==='connected_pairs_percent'?3:0)+'%':number(Math.round(value));
      svg.push(`<line x1="${left}" x2="${width-right}" y1="${yy}" y2="${yy}" class="history-grid"/><text x="${left-12}" y="${yy+4}" text-anchor="end">${esc(label)}</text>`);
    }
    const ticks = rows.length > 7 ? rows.filter((row,i) => i===0 || i===rows.length-1 || i%Math.ceil(rows.length/6)===0) : rows;
    ticks.forEach(row => svg.push(`<text x="${x(row.date)}" y="${height-18}" text-anchor="middle">${esc(dateLabel(row.date))}</text>`));
    series.forEach(view => {
      let path=''; let connected=false;
      view.points.forEach(point => {
        if(point.value===null){connected=false;return;}
        path+=`${connected?'L':'M'}${x(point.date)},${y(point.value)} `; connected=true;
      });
      svg.push(`<path d="${path}" fill="none" stroke="${view.color}" stroke-width="3" ${view.key==='working'&&!exactConfidence?'stroke-dasharray="7 5"':''}/>`);
      view.points.filter(point => point.value!==null).forEach(point => {
        const label=`${point.date}: ${view.label}, ${format(point.value)}`;
        svg.push(`<circle cx="${x(point.date)}" cy="${y(point.value)}" r="5" fill="${view.color}" stroke="#fffdf8" stroke-width="2" tabindex="0" aria-label="${esc(label)}"><title>${esc(label)}</title></circle>`);
      });
    });
    svg.push('</svg>');
    byId('history-chart').innerHTML=svg.join('');
  }
  function update() {
    const cutoff = byId('progress-cutoff').value, view = byId('progress-view').value;
    const summary = data.cohorts[cutoff][view], early = byId('early-heads').checked;
    const query = byId('head-search').value.trim().toLowerCase();
    const values = [[number(summary.component_count),'separate paternal branches'],[number(summary.unattached_multi_child_roots.length),'unattached fathers with 2+ children'],[summary.largest_component_percent.toFixed(1)+'%','people in the largest branch'],[summary.connected_pairs_percent.toFixed(2)+'%','pairs connected through fathers']];
    byId('connectivity-stats').innerHTML = values.map(([value,label]) => `<div><strong>${esc(value)}</strong><span>${esc(label)}</span></div>`).join('');
    byId('cohort-detail').textContent = `${number(summary.population)} public surname bearers; ${number(summary.edge_count)} father–child links. All views use the same people.`;
    byId('link-view-note').textContent = data.views[view].description;
    byId('threshold-comparison').innerHTML = Object.keys(data.views).map(key => {
      const row = data.cohorts[cutoff][key], label = esc(data.views[key].label);
      return `<tr><th scope="row">${key===view?'<strong>'+label+'</strong>':label}</th><td>${number(row.component_count)}</td><td>${number(row.largest_component_size)}</td><td>${row.connected_pairs_percent.toFixed(2)}%</td></tr>`;
    }).join('');
    const roots = summary.family_roots.filter(r => (!early || (r.year !== null && r.year <= data.early_cutoff)) && (!query || `${r.name} ${r.id}`.toLowerCase().includes(query)));
    byId('head-count').textContent = `${number(roots.length)} ${early?'early ':''}family heads shown, oldest first`;
    byId('family-head-rows').innerHTML = roots.length ? roots.map(r => `<tr><td><a href="${esc(r.url)}">${esc(r.name)}</a><small>${esc(r.id)}</small></td><td>${esc(r.year ?? 'Undated')}<small>${esc(r.year_basis || 'ancestor of dated person')} · ${esc(r.year_status)}</small></td><td>${number(r.child_count)}</td><td>${number(r.descendant_count)}</td></tr>`).join('') : '<tr><td colspan="4">No family head matches these choices.</td></tr>';
    const oldest = summary.family_roots.filter(r => r.year !== null && r.year <= data.early_cutoff).slice(0,6);
    byId('working-origin-map').innerHTML = `<div class="origin-heading">Shared paternal origin · working hypothesis<small>c. 1400–1450, possibly earlier; the founder and intervening generations remain open</small></div><div class="origin-branches">${oldest.map(r => `<div class="origin-branch"><a href="${esc(r.url)}">${esc(r.name)}</a><small>Cohort year ${esc(r.year)} (${esc(r.year_status)}) · ${number(r.descendant_count)} surname descendants</small></div>`).join('')}</div><p class="source-line">${oldest.length} earliest family heads shown. Dotted connections express the common-origin research model; only specific father–child links count in the measurements.</p>`;
    const params = new URLSearchParams(); params.set('through',cutoff); params.set('links',view);
    history.replaceState(null,'',location.pathname+'?'+params+location.hash);
    renderHistory();
  }
  const params = new URLSearchParams(location.search);
  if (data.cohorts[params.get('through')]) byId('progress-cutoff').value=params.get('through');
  if (Object.keys(data.views).includes(params.get('links'))) byId('progress-view').value=params.get('links');
  if (Object.hasOwn(historyMetrics, params.get('history'))) byId('history-metric').value=params.get('history');
  if (params.get('historyCohort') === 'selected') byId('history-cohort').value='selected';
  ['progress-cutoff','progress-view','early-heads'].forEach(id => byId(id).addEventListener('change',update));
  byId('head-search').addEventListener('input',update);
  ['history-cohort','history-metric',...historyViews.map(view=>'history-'+view.key)].forEach(id => byId(id).addEventListener('change',renderHistory));
  ['findings-kind','findings-all-cohorts'].forEach(id => byId(id).addEventListener('change',renderFindings));
  window.addEventListener('resize',renderHistory);
  update();
  if (location.hash === '#uncertain-connections') {
    requestAnimationFrame(() => byId('uncertain-connections').scrollIntoView({block:'start'}));
  }
})();
