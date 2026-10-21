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
      const value = metric === 'assessed_links_percent'
        ? (Number.isFinite(assessed) && working > 0 ? 100 * assessed / working : null)
        : row.metrics[view]?.[metric];
      return {date: row.date, value: Number.isFinite(value) ? value : null};
    });
  }
  if (typeof module !== 'undefined' && module.exports) module.exports = {dailyHistory, historySeries};
  if (typeof document === 'undefined') return;
  const element = document.getElementById('ancestry-progress-data');
  if (!element) return;
  const data = JSON.parse(element.textContent), byId = id => document.getElementById(id);
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const number = value => Number(value).toLocaleString('en-GB');
  const historyViews = [
    {key:'confident', label:'Confident', color:'#25734c'},
    {key:'supported', label:'Probable or stronger', color:'#386eaf'},
    {key:'working', label:'Working, including uncertain', color:'#a76812'}
  ];
  const historyMetrics = {
    assessed_links_percent:'Share of working father–child links (%)',
    edge_count:'Father–child links', largest_component_size:'People in largest branch',
    connected_pairs_percent:'Connected pairs (%)', component_count:'Separate paternal components'
  };
  function renderHistory() {
    const cutoff = byId('progress-cutoff').value;
    const fixed = byId('history-cohort').value === 'fixed';
    const metric = byId('history-metric').value;
    const rows = dailyHistory(data.progress_history, data.history_method_version, fixed ? 'fixed' : cutoff);
    const views = historyViews.filter(view => byId('history-'+view.key).checked);
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
    byId('history-table-head').innerHTML = '<tr><th scope="col">Date</th>'+views.map(view => `<th scope="col">${esc(view.label)}</th>`).join('')+'</tr>';
    byId('history-table-body').innerHTML = rows.map(row => '<tr><th scope="row">'+esc(row.date)+'</th>'+views.map(view => {
      const value = historySeries([row], view.key, metric)[0].value;
      return '<td>'+(Number.isFinite(value)?esc(format(value)):'Not recorded')+'</td>';
    }).join('')+'</tr>').join('');
    byId('history-changes').innerHTML = series.map(view => {
      const points = view.points.filter(point => point.value !== null);
      if (!points.length) return '';
      const first = points[0], last = points[points.length-1], delta = last.value-first.value;
      const change = percent ? Math.abs(delta).toFixed(decimals)+' percentage points' : number(Math.abs(delta));
      return `<div class="history-${view.key}"><span>${esc(view.label)}</span><strong>${esc(format(last.value))}</strong><small>${points.length>1?`${delta>0?'+':delta<0?'−':''}${esc(change)} since ${esc(dateLabel(first.date))}`:`First snapshot · ${esc(dateLabel(last.date))}`}</small></div>`;
    }).join('');
    if (!values.length) {
      byId('history-chart').innerHTML = '<p class="history-empty">Select a confidence level to display its history.</p>';
      return;
    }
    const width=Math.max(360, Math.min(960, byId('history-chart').clientWidth || 960)), height=330, left=70, right=28, top=28, bottom=54;
    const low=Math.min(...values), high=Math.max(...values), spread=high-low;
    const padding=Math.max(spread*.18, high*.025, metric==='connected_pairs_percent'?.005:2);
    const min=metric==='assessed_links_percent'?0:Math.max(0, low-padding), max=metric==='assessed_links_percent'?100:high+padding;
    const start=Date.parse(rows[0].date), end=Date.parse(rows[rows.length-1].date);
    const x=date => start===end ? (left+width-right)/2 : left+(Date.parse(date)-start)/(end-start)*(width-left-right);
    const y=value => height-bottom-(value-min)/(max-min)*(height-top-bottom);
    const svg = [`<svg viewBox="0 0 ${width} ${height}" role="img" aria-labelledby="history-svg-title history-svg-desc"><title id="history-svg-title">${esc(historyMetrics[metric])} over time</title><desc id="history-svg-desc">${esc(scope)}. Daily closing snapshots. Values are also available in the snapshot data table below. The vertical axis starts at ${esc(format(min))}.</desc>`];
    for(let i=0;i<=4;i++) {
      const value=min+(max-min)*i/4, yy=y(value);
      const label=percent?value.toFixed(metric==='assessed_links_percent'?0:3)+'%':number(Math.round(value));
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
      svg.push(`<path d="${path}" fill="none" stroke="${view.color}" stroke-width="3" ${view.key==='working'?'stroke-dasharray="7 5"':''}/>`);
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
  ['progress-cutoff','progress-view','early-heads'].forEach(id => byId(id).addEventListener('change',update));
  byId('head-search').addEventListener('input',update);
  ['history-cohort','history-metric',...historyViews.map(view=>'history-'+view.key)].forEach(id => byId(id).addEventListener('change',renderHistory));
  window.addEventListener('resize',renderHistory);
  update();
})();
