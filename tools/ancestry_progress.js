(() => {
  'use strict';
  function namedFatherCoverage(summary) {
    if (!summary) return 'Current named-father rating coverage is unavailable.';
    const count = value => value.toLocaleString('en-GB');
    const percent = summary.coverage_percent === null ? 'No retained named fathers.' : `${summary.coverage_percent.toFixed(1)}% coverage.`;
    return `${count(summary.rated_count)} of ${count(summary.named_count)} retained named fathers individually rated; ${count(summary.unrated_count)} ungraded. ${percent}`;
  }
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
    return rows.filter(row => (kind === 'all' || (kind === 'research' ? !!row.research_event : kind === 'change' ? row.research_event?.type === 'confidence_change' || row.kind === 'change' : row.kind === kind)) &&
      (beyond || (cohort === 'fixed' ? row.baseline : row.cohorts.includes(String(cohort)))));
  }
  const researchGrades = [
    {key:'confident',label:'Confident',color:'#25734c'},
    {key:'probable',label:'Probable',color:'#386eaf'},
    {key:'possible',label:'Possible',color:'#98630b'},
    {key:'uncertain',label:'Uncertain',color:'#a33237'},
    {key:'unknown',label:'Unknown',color:'#303f4b'}
  ];
  function findingGrade(status, percent) {
    if (['proved','confident','strongly_supported','certain','dna_confirmed'].includes(status)) return 'confident';
    if (['probable','possible','uncertain'].includes(status)) return status;
    if (!Number.isFinite(percent)) return null;
    return percent >= 90 ? 'confident' : percent >= 60 ? 'probable' : percent >= 30 ? 'possible' : 'uncertain';
  }
  function researchHistory(findings, cohort) {
    const scoped = individualFindings(findings,'all',cohort), days=new Map(), seen=new Set(), rowsByDate={};
    let increases=0,decreases=0,newFathers=0,replacements=0,qualitativeChanges=0,undated=0,ungradedReplacements=0;
    const rank={uncertain:1,possible:2,probable:3,confident:4};
    for (const row of scoped) {
      const event=row.research_event;
      if (!event || !Number.isFinite(row.after_percent)) continue;
      const structural=['father_attachment','father_replacement'].includes(event.type);
      const before=event.before_grade || findingGrade(row.previous_assessment?.status || row.previous_assessment?.assessment_status || row.previous_assessment?.tree_status,row.before_percent);
      const after=event.after_grade || findingGrade(row.assessment_status,row.after_percent);
      const numeric=Number.isFinite(row.before_percent) && row.before_percent!==row.after_percent;
      const qualitative=before && after && before!==after && rank[before] && rank[after];
      if (!structural && !(event.type==='confidence_change' && (numeric || qualitative))) continue;
      const signature=JSON.stringify([row.assertion_id,event.date,event.type,row.before_percent,row.after_percent,before,after]);
      if (row.assertion_id && seen.has(signature)) continue;
      seen.add(signature);
      if (!/^\d{4}-\d{2}-\d{2}$/.test(event.date || '')) {undated++;continue;}
      if (!days.has(event.date)) days.set(event.date,{date:event.date,...Object.fromEntries(researchGrades.map(g=>[g.key,0])),increases:0,decreases:0,newFathers:0,replacements:0});
      const day=days.get(event.date);
      const change=event.type==='father_attachment'?'new':event.type==='father_replacement'?'replaced':
        (numeric ? row.after_percent>row.before_percent : rank[after]>rank[before])?'improved':'lowered';
      (rowsByDate[event.date] ||= []).push({row,before,after,change});
      if (event.type==='father_attachment') {day.unknown--;day.newFathers++;newFathers++;}
      else if (event.type==='father_replacement') {
        day.replacements++;replacements++;
        if (before) day[before]--;else ungradedReplacements++;
      } else {
        if (before) day[before]--;
        if (!numeric) qualitativeChanges++;
        if (numeric ? row.after_percent>row.before_percent : rank[after]>rank[before]) {day.increases++;increases++;}
        else {day.decreases++;decreases++;}
      }
      day[after]++;
    }
    const totals=Object.fromEntries(researchGrades.map(g=>[g.key,0]));
    const points=[{date:null,...totals,increases:0,decreases:0,newFathers:0,replacements:0}];
    for (const day of [...days.values()].sort((a,b)=>a.date.localeCompare(b.date))) {
      for (const grade of researchGrades) totals[grade.key]+=day[grade.key];
      points.push({...day,...totals});
    }
    const proposals=rows=>new Set(rows.filter(r=>['add','replace'].includes(r.catalogue_father_action)).map(r=>r.assertion_id)).size;
    return {points,rowsByDate,increases,decreases,newFathers,replacements,qualitativeChanges,undated,ungradedReplacements,
      catalogueProposals:proposals(findings),cohortProposals:proposals(scoped),
      firstRatings:scoped.filter(row=>row.kind==='first' && !row.research_event).length};
  }
  function priorityRows(rows, order='branch', kind='all', early=false) {
    const value = n => Number.isFinite(n) ? n : -1;
    return rows.filter(row => (!early || (row.year != null && row.year <= 1650)) &&
      (kind === 'all' || (kind === 'unknown' ? row.status === 'unknown' : row.status !== 'unknown')))
      .sort((a,b) => (order === 'confident' ? value(b.confident_pair_gain)-value(a.confident_pair_gain)
        : order === 'working' ? value(b.cross_pairs)-value(a.cross_pairs) : b.child_side-a.child_side) ||
        b.child_side-a.child_side || a.child.localeCompare(b.child));
  }
  if (typeof module !== 'undefined' && module.exports) module.exports = {priorityRows, namedFatherCoverage, dailyHistory, historySeries, confidenceHistory, uncertaintyMeasurements, individualFindings, researchHistory};
  if (typeof document === 'undefined') return;
  const element = document.getElementById('ancestry-progress-data');
  if (!element) return;
  const data = JSON.parse(element.textContent), byId = id => document.getElementById(id);
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const number = value => Number(value).toLocaleString('en-GB');
  const DAY = 86400000;
  const time = iso => Date.parse(iso+'T12:00:00Z');
  const addDays = (iso, n) => new Date(time(iso)+n*DAY).toISOString().slice(0,10);
  const shortDate = iso => new Date(time(iso)).toLocaleDateString('en-GB',{day:'numeric',month:'short',timeZone:'UTC'});
  const longDate = iso => new Date(time(iso)).toLocaleDateString('en-GB',{weekday:'long',day:'numeric',month:'long',year:'numeric',timeZone:'UTC'});
  const today = data.reviewed || data.progress_history.at(-1)?.date;
  const gradeLabel = value => ({proved:'Confident', confident:'Confident', strongly_supported:'Confident', certain:'Confident', dna_confirmed:'Confident', probable:'Probable', possible:'Possible', uncertain:'Uncertain', unmarked:'Unmarked', unknown:'Unknown'}[value] || (value ? String(value).replaceAll('_', ' ') : 'Not recorded'));
  const gradeKey = value => ({proved:'confident', strongly_supported:'confident', certain:'confident', dna_confirmed:'confident'}[value] || value || 'none');
  const gradeChip = value => `<span class="pd-grade g-${esc(gradeKey(value))}">${esc(gradeLabel(value))}</span>`;
  const CHANGES = [
    {key:'improved', count:'increases', label:'Ratings improved', one:'Rating improved', short:'improved', up:true},
    {key:'new', count:'newFathers', label:'New fathers', one:'New father', short:'new fathers', up:true},
    {key:'replaced', count:'replacements', label:'Replacement fathers', one:'Replacement father', short:'replaced', up:true},
    {key:'lowered', count:'decreases', label:'Ratings lowered', one:'Rating lowered', short:'lowered', up:false}
  ];
  const GRADES = ['confident','probable','possible','uncertain','unknown'];
  const state = {cutoff:String(data.primary_cutoff), view:'working', range:'30', day:null, priorityLimit:20, findingsLimit:100, research:null};

  // ---------- Key measure tiles ----------
  function sparkline(points, label) {
    const values = points.map(p => p.value);
    if (values.length < 2) return '<span class="pd-spark-empty">Trend starts with the next daily snapshot</span>';
    const w = 132, h = 34, pad = 4, low = Math.min(...values), high = Math.max(...values), span = high-low || 1;
    const x = i => pad + i/(values.length-1)*(w-2*pad), y = v => h-pad-(v-low)/span*(h-2*pad);
    const d = values.map((v,i) => `${i?'L':'M'}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join('');
    return `<svg class="pd-spark" viewBox="0 0 ${w} ${h}" role="img" aria-label="${esc(label)}"><title>${esc(label)}</title><path d="${d}"/><circle cx="${x(values.length-1)}" cy="${y(values.at(-1))}" r="3.5"/></svg>`;
  }
  function comparisons(series) {
    const last = series.at(-1);
    if (!last) return {};
    const prev = series.length > 1 ? series.at(-2) : null;
    let week = null;
    for (const point of series) if (point.date <= addDays(last.date,-7)) week = point;
    return {last, prev, week: week || (series.length > 1 ? series[0] : null), partial: !week};
  }
  function delta(from, to, better, format) {
    if (!from || !Number.isFinite(from.value) || !Number.isFinite(to?.value)) return '<span class="pd-delta flat">No earlier count</span>';
    const change = to.value - from.value, size = Math.abs(change);
    if (size < 1e-9 || format(size) === format(0)) return '<span class="pd-delta flat">No change</span>';
    const good = better === 'up' ? change > 0 : better === 'down' ? change < 0 : null;
    const tone = good === null ? 'neutral' : good ? 'good' : 'bad';
    const word = good === null ? '' : `<span class="pd-sr">${good ? ' (better)' : ' (worse)'}</span>`;
    return `<span class="pd-delta ${tone}"><b aria-hidden="true">${change > 0 ? '▲' : '▼'}</b>${change > 0 ? '+' : '−'}${esc(format(size))}${word}</span>`;
  }
  function changeLines(series, better, format) {
    const {last, prev, week, partial} = comparisons(series);
    if (!last) return '<div class="pd-deltas"><span class="pd-delta flat">No daily history recorded</span></div>';
    const prevLabel = prev ? (prev.date === addDays(last.date,-1) ? 'since yesterday' : `since ${shortDate(prev.date)}`) : 'since yesterday';
    const weekLabel = week ? (partial ? `since ${shortDate(week.date)}` : 'in 7 days') : 'in 7 days';
    return `<div class="pd-deltas"><span>${delta(prev, last, better, format)} <small>${esc(prevLabel)}</small></span><span>${delta(week, last, better, format)} <small>${esc(weekLabel)}</small></span></div>`;
  }
  function tile({id, label, value, sub, series, better, format, note}) {
    const trend = series ? sparkline(series, `${label}: ${series.length} daily values from ${series[0] ? shortDate(series[0].date) : ''}`) : '';
    return `<article class="pd-kpi" id="kpi-${id}"><h3>${esc(label)}${better ? `<span class="pd-better">${better === 'up' ? 'higher is better' : 'lower is better'}</span>` : ''}</h3><p class="pd-value">${value}</p><p class="pd-kpi-sub">${sub}</p>${series ? changeLines(series, better, format) : ''}${note ? `<p class="pd-kpi-note">${note}</p>` : ''}${trend}</article>`;
  }
  function seriesOf(rows, get) {
    return rows.map(row => ({date:row.date, value:get(row.metrics)})).filter(p => Number.isFinite(p.value));
  }
  function renderKpis() {
    const {cutoff, view} = state, current = data.cohorts[cutoff], summary = current[view];
    const rows = dailyHistory(data.progress_history, data.history_method_version, cutoff);
    const pts = v => v.toFixed(2)+' pts', count = v => number(Math.round(v)), pts1 = v => v.toFixed(1)+' pts';
    const viewName = {working:'all working links', supported:'probable or stronger links', confident:'confident links only'}[view];
    byId('kpi-scope').textContent = `${number(summary.population)} people born through ${cutoff} · branches counted with ${viewName} · updated ${longDate(today)}`;
    const listing = current.working.father_listing || {};
    const coverage = data.current_named_father_coverage?.cohorts?.[cutoff];
    const research = state.research, todays = research.rowsByDate[today] || [];
    const lastDays = Array.from({length:14}, (_,i) => addDays(today, i-13));
    const dayCount = date => (research.rowsByDate[date] || []).length;
    const weekTotal = lastDays.slice(-7).reduce((sum,date) => sum+dayCount(date), 0);
    const lastActive = Object.keys(research.rowsByDate).sort().at(-1);
    const bars = (() => {
      const counts = lastDays.map(dayCount), high = Math.max(1,...counts), w = 132, h = 34, band = w/counts.length;
      return `<svg class="pd-spark pd-spark-bars" viewBox="0 0 ${w} ${h}" role="img" aria-label="Research changes per day, last 14 days: ${counts.join(', ')}"><title>Research changes per day, last 14 days</title>${counts.map((c,i) => c ? `<rect x="${(i*band+1.5).toFixed(1)}" y="${(h-2-c/high*(h-6)).toFixed(1)}" width="${(band-3).toFixed(1)}" height="${(c/high*(h-6)).toFixed(1)}" rx="1.5"/>` : `<rect class="zero" x="${(i*band+1.5).toFixed(1)}" y="${h-3}" width="${(band-3).toFixed(1)}" height="1"/>`).join('')}</svg>`;
    })();
    const byKind = rows => CHANGES.map(c => [c, rows.filter(r => r.change === c.key).length]).filter(([,n]) => n).map(([c,n]) => `${number(n)} ${c.short}`).join(' · ');
    const tiles = [
      tile({id:'pairs', label:'Connected pairs', value:`${summary.connected_pairs_percent.toFixed(2)}%`, sub:'of all pairs of people are joined through fathers', better:'up', format:pts,
        series:seriesOf(rows, m => m[view]?.connected_pairs_percent)}),
      tile({id:'branches', label:'Separate branches', value:number(summary.component_count), sub:`paternal branches, including ${number(summary.unattached_multi_child_roots.length)} unattached fathers with 2+ children`, better:'down', format:count,
        series:seriesOf(rows, m => m[view]?.component_count)}),
      tile({id:'largest', label:'People in largest branch', value:number(summary.largest_component_size), sub:`${summary.largest_component_percent.toFixed(1)}% of ${number(summary.population)} people`, better:'up', format:count,
        series:seriesOf(rows, m => m[view]?.largest_component_size)}),
      tile({id:'unknown', label:'Unknown fathers', value:Number.isFinite(listing.unknown_count) ? number(listing.unknown_count) : '–', sub:`people with no named father, of ${number(listing.population ?? summary.population)}`, better:'down', format:count,
        series:seriesOf(rows, m => m.working?.father_listing?.unknown_count)}),
      tile({id:'rated', label:'Named fathers rated', value:coverage?.coverage_percent == null ? '–' : `${coverage.coverage_percent.toFixed(1)}%`,
        sub:coverage ? `${number(coverage.rated_count)} of ${number(coverage.named_count)} named fathers individually rated; ${number(coverage.unrated_count)} ungraded` : 'Coverage unavailable',
        note:'Current figure only; daily history of this measure is not recorded yet.'}),
      `<article class="pd-kpi" id="kpi-today"><h3>Research changes today</h3><p class="pd-value">${number(todays.length)}</p><p class="pd-kpi-sub">${todays.length ? esc(byKind(todays)) : lastActive ? `None recorded on ${esc(shortDate(today))}; last on <a href="#day-${esc(lastActive)}" data-day="${esc(lastActive)}">${esc(shortDate(lastActive))}</a>` : 'No dated research changes yet'}</p><div class="pd-deltas"><span><span class="pd-delta neutral">${number(dayCount(addDays(today,-1)))}</span> <small>yesterday</small></span><span><span class="pd-delta neutral">${number(weekTotal)}</span> <small>in the last 7 days</small></span></div>${bars}</article>`,
      gradeTile(rows, current)
    ];
    byId('kpi-grid').innerHTML = tiles.join('');
    byId('link-view-note').textContent = `Links counted: ${data.views[view].label}. ${data.views[view].description}`;
  }
  function gradeTile(rows, current) {
    const grades = [
      {key:'confident', label:'Confident', better:'up', get:m => m.confident?.edge_count},
      {key:'probable', label:'Probable', better:null, get:m => m.working?.edge_status_counts ? (m.working.edge_status_counts.probable ?? 0) : null},
      {key:'possible', label:'Possible', better:null, get:m => m.working?.edge_status_counts ? (m.working.edge_status_counts.possible ?? 0) : null},
      {key:'uncertain', label:'Uncertain', better:'down', get:m => m.working?.edge_status_counts ? (m.working.edge_status_counts.uncertain ?? 0) : null}
    ];
    const unmarked = current.working.edge_status_counts?.unmarked ?? 0;
    const values = grades.map(g => g.get(current)), total = values.reduce((a,b) => a+(b||0), 0) + unmarked;
    const bar = grades.map((g,i) => values[i] ? `<span class="g-${g.key}" style="flex:${values[i]}" title="${esc(g.label)}: ${number(values[i])}"></span>` : '').join('') + (unmarked ? `<span class="g-unmarked" style="flex:${unmarked}" title="Unmarked: ${number(unmarked)}"></span>` : '');
    const count = v => number(Math.round(v));
    const anchor = comparisons(seriesOf(rows, grades[0].get));
    const prevHeader = !anchor.prev ? 'Since yesterday' : anchor.prev.date === addDays(anchor.last.date,-1) ? 'Since yesterday' : `Since ${shortDate(anchor.prev.date)}`;
    const weekHeader = anchor.week && anchor.partial ? `Since ${shortDate(anchor.week.date)}` : 'In 7 days';
    const list = grades.map((g,i) => {
      const series = seriesOf(rows, g.get), {last, prev, week, partial} = comparisons(series);
      return `<tr><th scope="row"><i class="pd-swatch g-${g.key}"></i>${g.label}${g.better ? `<span class="pd-better">${g.better === 'up' ? 'more is better' : 'fewer is better'}</span>` : ''}</th><td class="pd-num">${number(values[i] ?? 0)}</td><td>${delta(prev, last, g.better, count)}</td><td>${delta(week, last, g.better, count)}</td></tr>`;
    }).join('');
    return `<article class="pd-kpi pd-kpi-wide" id="kpi-grades"><h3>Father links by grade</h3><p class="pd-kpi-sub">${number(total)} named father links in the working pedigree${unmarked ? `, including ${number(unmarked)} unmarked` : ''}</p><div class="pd-stack" role="img" aria-label="${esc(grades.map((g,i) => `${g.label} ${values[i] ?? 0}`).join(', '))}">${bar}</div><div class="pd-grade-table"><table><thead><tr><th scope="col">Grade</th><th scope="col">Links</th><th scope="col">${esc(prevHeader)}</th><th scope="col">${esc(weekHeader)}</th></tr></thead><tbody>${list}</tbody></table></div></article>`;
  }

  // ---------- What changed each day ----------
  function dayList() {
    const dated = Object.keys(state.research.rowsByDate).sort();
    const first = dated[0] || today, start = state.range === 'all' ? first : addDays(today, 1-Number(state.range));
    const days = [];
    for (let date = start < first && state.range === 'all' ? first : start; date <= today; date = addDays(date,1)) days.push(date);
    return days;
  }
  function dayCounts(date) {
    const rows = state.research.rowsByDate[date] || [];
    return Object.fromEntries(CHANGES.map(c => [c.key, rows.filter(r => r.change === c.key).length]));
  }
  function renderDayChart() {
    const target = byId('research-history-chart'), days = dayList();
    const width = Math.max(300, Math.min(1100, target.clientWidth || 800)), height = width < 520 ? 220 : 260;
    const left = 34, right = 8, top = 14, bottom = 30, plotW = width-left-right, plotH = height-top-bottom;
    const counts = days.map(dayCounts);
    const up = counts.map(c => c.improved+c.new+c.replaced), down = counts.map(c => c.lowered);
    const niceStep = v => { const raw = v/4, p = 10**Math.floor(Math.log10(raw || 1)); return (p >= 10 ? [1,2,2.5,5,10] : [1,2,5,10]).map(m => m*p).find(s => s >= raw) || p*10; };
    const step = niceStep(Math.max(4, ...up, ...down)), maxUp = Math.max(step, Math.ceil(Math.max(0,...up)/step)*step), maxDown = Math.max(step, Math.ceil(Math.max(0,...down)/step)*step);
    const y = v => top + (maxUp - v)/(maxUp+maxDown)*plotH, band = plotW/days.length, barW = Math.max(3, Math.min(24, band*.68));
    const svg = [`<svg viewBox="0 0 ${width} ${height}" role="img" aria-labelledby="day-chart-title day-chart-desc"><title id="day-chart-title">Research findings per day</title><desc id="day-chart-desc">Columns above the line count improved ratings, new fathers and replacements; below the line, lowered ratings. The same values are in the table of changes per day.</desc>`];
    for (let v = -maxDown; v <= maxUp; v += step) svg.push(`<line class="pd-grid${v === 0 ? ' pd-zero' : ''}" x1="${left}" x2="${width-right}" y1="${y(v)}" y2="${y(v)}"/><text class="pd-axis" x="${left-6}" y="${y(v)+4}" text-anchor="end">${Math.abs(v)}</text>`);
    const tickEvery = Math.ceil(days.length / Math.max(2, Math.floor(plotW/64)));
    days.forEach((date, i) => {
      const cx = left + band*(i+.5), c = counts[i], total = up[i]+down[i];
      if (date === state.day) svg.push(`<rect class="pd-selected" x="${left+band*i}" y="${top}" width="${band}" height="${plotH}"/>`);
      let base = 0;
      const segments = CHANGES.filter(k => k.up && c[k.key]);
      segments.forEach((k, j) => {
        const y0 = y(base), y1 = y(base + c[k.key]), last = j === segments.length-1;
        svg.push(`<path class="pd-bar b-${k.key}" d="${barPath(cx-barW/2, y1 + (j ? 0 : 0), barW, y0 - y1 - (j ? 2 : 1), last ? 4 : 0, 'up')}"/>`);
        base += c[k.key];
      });
      if (c.lowered) { const y0 = y(0), y1 = y(-c.lowered); svg.push(`<path class="pd-bar b-lowered" d="${barPath(cx-barW/2, y0+1, barW, y1-y0-1, 4, 'down')}"/>`); }
      if (i % tickEvery === 0 || i === days.length-1) {
        if (i === days.length-1 || (days.length-1-i)*band >= 60) svg.push(`<text class="pd-axis" x="${cx}" y="${height-10}" text-anchor="${i === 0 ? 'start' : i === days.length-1 ? 'end' : 'middle'}" ${i === 0 ? `dx="${-band/2+2}"` : i === days.length-1 ? `dx="${band/2-2}"` : ''}>${esc(shortDate(date))}</text>`);
      }
      const label = `${longDate(date)}: ${total ? CHANGES.map(k => `${c[k.key]} ${k.short}`).join(', ') : 'no research changes'}`;
      svg.push(`<rect class="pd-hit" data-day="${date}" x="${left+band*i}" y="${top}" width="${band}" height="${plotH}" tabindex="${total ? 0 : -1}" role="button" aria-label="${esc(label)}${total ? '. Show findings' : ''}" aria-pressed="${date === state.day}"/>`);
    });
    svg.push('</svg><div class="pd-tip" id="day-tip" hidden></div>');
    target.innerHTML = svg.join('');
    const tip = byId('day-tip');
    target.querySelectorAll('.pd-hit').forEach(hit => {
      const show = () => {
        const date = hit.dataset.day, c = dayCounts(date), total = Object.values(c).reduce((a,b) => a+b, 0);
        tip.innerHTML = `<strong>${esc(longDate(date))}</strong>${total ? CHANGES.filter(k => c[k.key]).map(k => `<span><i class="pd-swatch b-${k.key}"></i>${esc(k.label)}<b>${c[k.key]}</b></span>`).join('') + '<em>Select to list the findings</em>' : '<span>No research changes recorded</span>'}`;
        tip.hidden = false;
        const box = target.getBoundingClientRect(), r = hit.getBoundingClientRect();
        const tipW = tip.offsetWidth, x = Math.min(Math.max(4, r.left - box.left + r.width/2 - tipW/2), box.width - tipW - 4);
        tip.style.left = x+'px'; tip.style.top = '4px';
      };
      hit.addEventListener('mouseenter', show); hit.addEventListener('focus', show);
      hit.addEventListener('mouseleave', () => { tip.hidden = true; }); hit.addEventListener('blur', () => { tip.hidden = true; });
      const pick = () => { if ((state.research.rowsByDate[hit.dataset.day] || []).length) selectDay(hit.dataset.day, true); };
      hit.addEventListener('click', pick);
      hit.addEventListener('keydown', event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); pick(); } });
    });
  }
  function barPath(x, y, w, h, r, dir) {
    h = Math.max(h, 0); r = Math.min(r, h, w/2);
    if (!r) return `M${x},${y}h${w}v${h}h${-w}Z`;
    return dir === 'up'
      ? `M${x},${y+h}V${y+r}Q${x},${y} ${x+r},${y}H${x+w-r}Q${x+w},${y} ${x+w},${y+r}V${y+h}Z`
      : `M${x},${y}H${x+w}V${y+h-r}Q${x+w},${y+h} ${x+w-r},${y+h}H${x+r}Q${x},${y+h} ${x},${y+h-r}Z`;
  }
  function netByGrade(date) {
    const point = state.research.points.find(p => p.date === date), previous = state.research.points[state.research.points.indexOf(point)-1];
    return Object.fromEntries(GRADES.map(g => [g, point && previous ? point[g]-previous[g] : 0]));
  }
  function signed(value) { return value > 0 ? `<span class="pd-pos">+${number(value)}</span>` : value < 0 ? `<span class="pd-neg">−${number(-value)}</span>` : '<span class="pd-nil">0</span>'; }
  function renderDayTable() {
    const research = state.research, dates = Object.keys(research.rowsByDate).sort().reverse();
    byId('research-history-rows').innerHTML = dates.length ? dates.map(date => {
      const c = dayCounts(date), net = netByGrade(date), n = research.rowsByDate[date].length;
      return `<tr id="day-${date}" class="${date === state.day ? 'is-selected' : ''}"><th scope="row"><a href="#day-${date}" data-day="${date}">${esc(shortDate(date))}</a><small>${esc(new Date(time(date)).toLocaleDateString('en-GB',{weekday:'short',timeZone:'UTC'}))}</small></th><td>${c.improved || ''}</td><td>${c.lowered || ''}</td><td>${c.new || ''}</td><td>${c.replaced || ''}</td>${GRADES.map(g => `<td>${signed(net[g])}</td>`).join('')}<td><button type="button" class="pd-link" data-day="${date}" aria-label="Show the ${n} findings of ${esc(longDate(date))}">${n} finding${n === 1 ? '' : 's'}</button></td></tr>`;
    }).join('') : '<tr><td colspan="11">No dated research changes are recorded for this cohort.</td></tr>';
    const last = research.points.at(-1);
    byId('research-history-total').innerHTML = `<tr><th scope="row">All dates</th><td>${number(research.increases)}</td><td>${number(research.decreases)}</td><td>${number(research.newFathers)}</td><td>${number(research.replacements)}</td>${GRADES.map(g => `<td>${signed(last[g])}</td>`).join('')}<td></td></tr>`;
  }
  function findingCard({row, before, after, change}) {
    const kind = CHANGES.find(c => c.key === change);
    const pct = Number.isFinite(row.before_percent) ? `${row.before_percent}% → ${row.after_percent}%` : `${row.after_percent}%`;
    const person = p => `<a href="${esc(p.url)}">${esc(p.name)}</a>${p.wikitree_url ? ` <a class="pd-wt" href="${esc(p.wikitree_url)}" aria-label="${esc(p.name)} on WikiTree">WikiTree</a>` : ''}`;
    const prior = row.previous_assessment;
    return `<li class="pd-finding c-${change}"><div class="pd-f-top"><span class="pd-kind"><i class="pd-swatch b-${change}"></i>${esc(kind.one)}</span>${gradeChip(before || 'unknown')}<span aria-label="to">→</span>${gradeChip(after)}<span class="pd-pct">${esc(pct)}</span></div>
<p class="pd-f-who">${person(row.child)} <span class="pd-arrow" aria-label="child of">←</span> ${person(row.father)}${row.identity_hold ? ' <strong class="pd-hold">Identity on hold</strong>' : ''}</p>
${row.reason ? `<details><summary>Reason and evidence</summary><p>${esc(row.reason)}</p>${row.limitations ? `<p>${esc(row.limitations)}</p>` : ''}${prior && (prior.source_basis || prior.reason || prior.basis) ? `<p><strong>Before:</strong> ${esc(prior.source_basis || prior.reason || prior.basis)}</p>` : ''}<p><a href="${esc(row.child.url)}">Read the sourced biography</a></p></details>` : ''}</li>`;
  }
  function renderDayDetail() {
    const target = byId('day-detail'), rows = state.day ? state.research.rowsByDate[state.day] || [] : [];
    if (!state.day || !rows.length) {
      target.innerHTML = '';
      target.hidden = true;
      return;
    }
    target.hidden = false;
    const c = dayCounts(state.day), order = CHANGES.map(k => k.key);
    const sorted = [...rows].sort((a,b) => order.indexOf(a.change)-order.indexOf(b.change));
    const shown = state.dayAll ? sorted : sorted.slice(0, 30);
    target.innerHTML = `<div class="pd-day-head"><h3>${esc(longDate(state.day))}</h3><p>${CHANGES.filter(k => c[k.key]).map(k => `${number(c[k.key])} ${k.short}`).join(' · ')}</p><button type="button" class="pd-close" id="day-close" aria-label="Close the day's findings">Close</button></div><ol class="pd-findings">${shown.map(findingCard).join('')}</ol>${shown.length < sorted.length ? `<p><button type="button" class="pd-more" id="day-all">Show all ${number(sorted.length)} findings of this day</button></p>` : ''}`;
    byId('day-close').addEventListener('click', () => selectDay(null));
    byId('day-all')?.addEventListener('click', () => { state.dayAll = true; renderDayDetail(); });
  }
  function selectDay(date, focus) {
    state.day = date && state.research.rowsByDate[date] ? date : null;
    state.dayAll = false;
    if (state.day && state.range !== 'all' && state.day < addDays(today, 1-Number(state.range))) setRange('all', false);
    renderDayChart(); renderDayTable(); renderDayDetail(); saveParams();
    if (state.day && focus) byId('day-detail').scrollIntoView({block:'nearest', behavior:'smooth'});
  }
  function setRange(range, draw = true) {
    state.range = range;
    document.querySelectorAll('.pd-seg button').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.range === range)));
    if (draw) { renderDayChart(); saveParams(); }
  }
  function renderResearch() {
    const research = state.research = researchHistory(data.individual_findings || [], state.cutoff);
    byId('research-history-scope').textContent = `Research findings for people born through ${state.cutoff}${Object.keys(research.rowsByDate).length ? `, ${shortDate(Object.keys(research.rowsByDate).sort()[0])} to ${shortDate(today)}` : ''}.`;
    byId('research-history-summary').innerHTML = CHANGES.map(c => `<div class="pd-chip c-${c.key}"><i class="pd-swatch b-${c.key}"></i><span>${esc(c.label)}</span><strong>${number(research[c.count])}</strong></div>`).join('');
    byId('research-history-exclusions').textContent = `${number(research.qualitativeChanges)} changes count a saved earlier grade without an old percentage. ${number(research.firstRatings)} initial ratings without a changed earlier grade are review coverage and are not counted. ${research.ungradedReplacements ? `${research.ungradedReplacements} replacement fathers had an ungraded named predecessor; their new grades are added without inventing a prior grade. ` : ''}${research.undated ? `${research.undated} undated findings stay in the individual findings but cannot be placed on a day.` : ''}`;
    byId('research-catalogue-reconciliation').innerHTML = `<a href="/catalogue/?needsUpdate=1&changeRelationship=father&changeAction=topology#catalogue-filters">${number(research.catalogueProposals)} pending new or replacement father recommendations in the catalogue</a>: ${number(research.cohortProposals)} concern this cohort and ${number(research.catalogueProposals-research.cohortProposals)} fall outside it.`;
    if (state.day && !research.rowsByDate[state.day]) state.day = null;
    renderDayChart(); renderDayTable(); renderDayDetail();
  }

  // ---------- Panels ----------
  function renderFindings() {
    const query = byId('findings-search').value.trim().toLowerCase(), all = byId('findings-all-cohorts').checked;
    let rows = individualFindings(data.individual_findings || [], byId('findings-kind').value, state.cutoff, all);
    if (query) rows = rows.filter(row => `${row.child.name} ${row.child.id} ${row.father.name} ${row.father.id} ${row.research_event?.date || row.date || ''}`.toLowerCase().includes(query));
    const person = value => `<a href="${esc(value.url)}">${esc(value.name)}</a>${value.wikitree_url ? ` · <a href="${esc(value.wikitree_url)}">WikiTree</a>` : ' · local account'} `;
    byId('findings-count').textContent = `${number(rows.length)} finding${rows.length === 1 ? '' : 's'} · ${all ? 'all cohorts' : `people born through ${state.cutoff}`}${query ? ` · matching “${query}”` : ''}${rows.length > state.findingsLimit ? ` · showing the first ${number(state.findingsLimit)}` : ''}`;
    byId('findings-rows').innerHTML = rows.length ? rows.slice(0, state.findingsLimit).map(row => {
      const percentage = row.before_percent == null ? `${row.after_percent}%` : `${row.before_percent}% → ${row.after_percent}%`;
      const event = row.research_event;
      const label = event?.type === 'father_replacement' ? `Replacement father · ${row.after_percent}%` : event?.type === 'father_attachment' ? `New father connection · ${row.after_percent}%` : event?.type === 'confidence_change' && row.before_percent == null ? `${gradeLabel(event.before_grade)} → ${gradeLabel(row.assessment_status)} · ${row.after_percent}% (first percentage)` : row.kind === 'change' ? percentage : `${row.kind === 'new' ? 'Newly indexed relationship' : 'First individual rating'} · ${percentage}`;
      const prior = row.previous_assessment;
      return `<tr><td>${esc(event?.date || row.date || 'Date not recorded')}</td><td>${person(row.child)}<br>Father: ${person(row.father)}${row.identity_hold ? '<br><strong>Identity HOLD · record-defined person; adult identity unresolved</strong>' : ''}</td><td><strong>${esc(label)}</strong>${prior ? `<br>Prior grade: ${esc(gradeLabel(event?.type === 'confidence_change' || event?.type === 'father_replacement' ? event.before_grade || prior.status || prior.assessment_status : prior.status || prior.assessment_status))}` : ''}<br>Reviewed grade: ${esc(gradeLabel(row.assessment_status))}</td><td><details><summary>Evidence and reason</summary><p>${esc(row.reason)}</p>${row.limitations ? `<p>${esc(row.limitations)}</p>` : ''}${prior ? `<p>Prior basis: ${esc(prior.source_basis || prior.reason || prior.basis || 'not recorded')}</p>` : ''}<a href="${esc(row.child.url)}">Read the sourced biography</a></details></td></tr>`;
    }).join('') : '<tr><td colspan="4">No findings match. Choose another kind, clear the search or include people outside the cohort.</td></tr>';
    byId('findings-more').hidden = rows.length <= state.findingsLimit;
  }
  function renderPriorities() {
    const early = byId('priority-early').checked;
    const rows = priorityRows(data.research_priorities || [], byId('priority-order').value, byId('priority-kind').value, early);
    const missing = rows.filter(row => row.status === 'unknown').length;
    byId('priority-count').textContent = `Showing ${number(Math.min(state.priorityLimit, rows.length))} of ${number(rows.length)}: ${number(missing)} unknown fathers and ${number(rows.length-missing)} named links below confident${early ? ` dated by ${data.early_cutoff}` : ''}.`;
    const all = data.research_priorities || [], named = all.filter(row => row.status !== 'unknown');
    const countGrade = grade => named.filter(row => row.status === grade).length;
    byId('priority-uncertainty-summary').innerHTML = `<div class="pd-chip"><span>Unknown fathers</span><strong>${number(all.length-named.length)}</strong></div>` + ['uncertain','possible','probable','unmarked'].filter(g => g !== 'unmarked' || countGrade(g)).map(g => `<div class="pd-chip"><i class="pd-swatch g-${g}"></i><span>${esc(gradeLabel(g))}</span><strong>${number(countGrade(g))}</strong></div>`).join('');
    byId('priority-rows').innerHTML = rows.slice(0, state.priorityLimit).map(row => {
      const unknown = row.status === 'unknown';
      const father = unknown ? '<strong>Unknown father</strong>' : `<a href="${esc(row.father_url)}">${esc(row.father_name)}</a>`;
      const pairs = unknown ? 'Not yet estimable' : number(row.cross_pairs);
      const gain = unknown ? 'Father not identified' : `${number(row.confident_pair_gain)}<small>${number(row.confident_child_side)} × ${number(row.confident_parent_side)} people; ${row.confident_component_reduction} fewer confident branches</small>`;
      return `<tr><td>${father} → <a href="${esc(row.child_url)}">${esc(row.child_name)}</a><small>${unknown ? '' : `${esc(row.father)} → `}${esc(row.child)} · ${esc(row.year ?? 'Undated')}</small></td><td>${unknown ? 'Unknown · no father listed' : Number.isFinite(row.confidence_percent) ? `${row.confidence_percent}%` : 'Not individually rated'}${unknown ? '' : `<small>${esc(row.status)}</small>`}</td><td>${number(row.child_side)}</td><td>${pairs}</td><td>${gain}</td><td><a href="${esc(row.analysis_url)}">${esc(row.next_test)}</a>${row.last_review ? `<small>${esc(row.last_review)}</small>` : ''}</td></tr>`;
    }).join('') || '<tr><td colspan="6">No research priorities match these filters.</td></tr>';
    byId('priority-more').hidden = rows.length <= state.priorityLimit;
  }
  function renderCohortPanels() {
    const {cutoff, view} = state, summary = data.cohorts[cutoff][view];
    const early = byId('early-heads').checked, query = byId('head-search').value.trim().toLowerCase();
    byId('cohort-detail').textContent = `People born through ${cutoff}: ${number(summary.population)} public surname bearers; ${number(data.cohorts[cutoff].working.edge_count)} working father–child links. All thresholds use the same people.`;
    byId('named-father-coverage').textContent = namedFatherCoverage(data.current_named_father_coverage?.cohorts?.[cutoff]);
    byId('threshold-comparison').innerHTML = Object.keys(data.views).map(key => {
      const row = data.cohorts[cutoff][key], label = esc(data.views[key].label);
      return `<tr${key === view ? ' class="is-selected"' : ''}><th scope="row">${key === view ? '<strong>'+label+'</strong>' : label}</th><td>${number(row.component_count)}</td><td>${number(row.largest_component_size)}</td><td>${number(row.unattached_multi_child_roots.length)}</td><td>${row.connected_pairs_percent.toFixed(2)}%</td></tr>`;
    }).join('');
    const roots = summary.family_roots.filter(r => (!early || (r.year !== null && r.year <= data.early_cutoff)) && (!query || `${r.name} ${r.id}`.toLowerCase().includes(query)));
    byId('head-count').textContent = `${number(roots.length)} ${early ? 'early ' : ''}family heads shown, oldest first · born through ${cutoff}, ${data.views[view].label.toLowerCase()}`;
    const earlyHeads = summary.family_roots.filter(r => r.year !== null && r.year <= data.early_cutoff).length;
    byId('sum-heads').textContent = `${number(summary.family_roots.length)} family head${summary.family_roots.length === 1 ? '' : 's'} without a father in the selected pedigree, ${number(earlyHeads)} dated by ${data.early_cutoff}.`;
    byId('family-head-rows').innerHTML = roots.length ? roots.map(r => `<tr><td><a href="${esc(r.url)}">${esc(r.name)}</a><small>${esc(r.id)}</small></td><td>${esc(r.year ?? 'Undated')}<small>${esc(r.year_basis || 'ancestor of dated person')} · ${esc(r.year_status)}</small></td><td>${number(r.child_count)}</td><td>${number(r.descendant_count)}</td></tr>`).join('') : '<tr><td colspan="4">No family head matches these choices.</td></tr>';
    const oldest = summary.family_roots.filter(r => r.year !== null && r.year <= data.early_cutoff).slice(0,6);
    byId('working-origin-map').innerHTML = `<div class="origin-heading">Shared paternal origin · working hypothesis<small>c. 1400–1450, possibly earlier; the founder and intervening generations remain open</small></div><div class="origin-branches">${oldest.map(r => `<div class="origin-branch"><a href="${esc(r.url)}">${esc(r.name)}</a><small>Cohort year ${esc(r.year)} (${esc(r.year_status)}) · ${number(r.descendant_count)} surname descendants</small></div>`).join('')}</div><p class="source-line">${oldest.length} earliest family heads shown. Dotted connections express the common-origin research model; only specific father–child links count in the measurements.</p>`;
  }

  // ---------- Catalogue coverage history (snapshot charts) ----------
  const historyViews = [
    {key:'confident', label:'Confident', color:'#25734c'},
    {key:'supported', label:'Probable or stronger', color:'#386eaf'},
    {key:'working', label:'Working, including uncertain', color:'#a76812'}
  ];
  const historyMetrics = {
    reviewed_confidence_percent:'Mean individually reviewed father confidence (%)',
    assessed_links_percent:'Share of working graph father–child links (%)',
    edge_count:'Father–child links', largest_component_size:'People in largest branch',
    connected_pairs_percent:'Connected pairs (%)', component_count:'Separate paternal components'
  };
  const chartWidth = target => Math.max(300, Math.min(960, target.clientWidth || 720));
  function renderUncertaintyTrend(rows) {
    const measured = rows.map(row => ({date:row.date, ...uncertaintyMeasurements(row.metrics)}));
    const recorded = measured.filter(row => row.total !== null);
    const target = byId('uncertainty-trend-chart');
    if (!recorded.length) {
      byId('uncertainty-totals').innerHTML = '<p>No comparable uncertainty counts have been recorded for this cohort.</p>';
      byId('uncertainty-breakdown').innerHTML = ''; byId('uncertainty-trend-rows').innerHTML = ''; target.innerHTML = '';
      return;
    }
    const first = recorded[0], last = recorded.at(-1), drop = first.total-last.total;
    const change = (start,end) => end === start ? 'No change' : `${number(Math.abs(start-end))} ${end < start ? 'fewer' : 'more'}`;
    const strict = recorded.filter(row => row.uncertain !== null), strictFirst = strict[0], strictLast = strict.at(-1);
    const unknown = recorded.filter(row => row.unknown !== null), unknownFirst = unknown[0];
    byId('uncertainty-totals').innerHTML = `<div><span>Father links below confident</span><strong>${number(last.total)}</strong><small>${last.percent === null ? '' : `${last.percent.toFixed(1)}% of ${number(last.working)} father links`}</small></div><div><span>Change since ${esc(shortDate(first.date))}</span><strong>${recorded.length > 1 ? esc(change(first.total,last.total)) : 'First count'}</strong><small>${recorded.length > 1 ? `${number(first.total)} → ${number(last.total)} · ${first.total > 0 ? (Math.abs(drop)/first.total*100).toFixed(1)+'% '+(drop >= 0 ? 'drop' : 'increase') : 'new baseline'}` : 'No earlier comparable count'}</small></div><div><span>Uncertain grade only</span><strong>${last.uncertain === null ? 'Not recorded' : number(last.uncertain)}</strong><small>${strict.length > 1 ? `${number(strictFirst.uncertain)} → ${number(strictLast.uncertain)} · ${esc(change(strictFirst.uncertain,strictLast.uncertain))} since ${esc(shortDate(strictFirst.date))}` : 'Separate from possible and probable'}</small></div><div><span>Unknown father</span><strong>${last.unknown === null ? 'Not recorded' : number(last.unknown)}</strong><small>${last.unknown === null ? 'No saved count' : `${number(last.unknown)} of ${number(last.population)} people`}${unknown.length > 1 ? ` · ${esc(change(unknownFirst.unknown,last.unknown))} since ${esc(shortDate(unknownFirst.date))}` : ''}</small></div>`;
    const grades = [['unknown','Unknown'],['uncertain','Uncertain'],['possible','Possible'],['probable','Probable'],['unmarked','Unmarked']];
    byId('uncertainty-breakdown').innerHTML = grades.map(([key,label]) => `<span>${esc(label)} <strong>${last[key] === null ? 'Not recorded' : number(last[key])}</strong></span>`).join('');
    const width = chartWidth(target), height = 240, left = 52, right = 16, top = 16, bottom = 34;
    const max = Math.max(1,...recorded.flatMap(row => [row.total,row.unknown ?? 0]))*1.1;
    const start = time(measured[0].date), end = time(measured.at(-1).date);
    const x = date => start === end ? (left+width-right)/2 : left+(time(date)-start)/(end-start)*(width-left-right);
    const y = value => height-bottom-value/max*(height-top-bottom);
    const svg = [`<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Unknown and below-confident fathers over time; the table below has every value">`];
    for (let i = 0; i <= 4; i++) { const value = max*i/4, yy = y(value); svg.push(`<line class="pd-grid" x1="${left}" x2="${width-right}" y1="${yy}" y2="${yy}"/><text class="pd-axis" x="${left-8}" y="${yy+4}" text-anchor="end">${number(Math.round(value))}</text>`); }
    measured.filter((row,i) => i === 0 || i === measured.length-1 || i % Math.ceil(measured.length/(width < 500 ? 3 : 5)) === 0).forEach(row => svg.push(`<text class="pd-axis" x="${x(row.date)}" y="${height-12}" text-anchor="${row === measured[0] ? 'start' : row === measured.at(-1) ? 'end' : 'middle'}">${esc(shortDate(row.date))}</text>`));
    for (const [key,label,color] of [['total','Named fathers below confident','#9b5610'],['uncertain','Uncertain grade only','#a33237'],['unknown','Unknown father','#303f4b']]) {
      let path = '', connected = false;
      for (const row of measured) { if (row[key] === null) { connected = false; continue; } path += `${connected ? 'L' : 'M'}${x(row.date)},${y(row[key])} `; connected = true; }
      svg.push(`<path d="${path}" fill="none" stroke="${color}" stroke-width="2" stroke-linejoin="round" ${key === 'uncertain' ? 'stroke-dasharray="6 4"' : ''}/>`);
      measured.filter(row => row[key] !== null).forEach(row => { const t = `${row.date}: ${label}, ${number(row[key])}`; svg.push(`<circle cx="${x(row.date)}" cy="${y(row[key])}" r="4" fill="${color}" stroke="#fffef9" stroke-width="2"><title>${esc(t)}</title></circle>`); });
    }
    target.innerHTML = svg.join('')+'</svg>';
    const cell = value => value === null ? 'Not recorded' : number(value);
    byId('uncertainty-trend-rows').innerHTML = measured.map(row => `<tr><th scope="row">${esc(row.date)}</th><td>${cell(row.total)}</td><td>${row.percent === null ? 'Not recorded' : row.percent.toFixed(1)+'%'}</td>${grades.map(([key]) => `<td>${cell(row[key])}</td>`).join('')}</tr>`).join('');
  }
  function renderConfidenceTrend(cohort) {
    const rows = confidenceHistory(data.progress_history, data.history_method_version, cohort);
    const target = byId('confidence-trend-chart');
    if (!rows.length) {
      target.innerHTML = '<p class="history-empty">Exact confidence measurements have not yet been recorded for this cohort.</p>';
      byId('confidence-trend-summary').textContent = ''; byId('confidence-trend-rows').innerHTML = '';
      return;
    }
    const first = rows[0], last = rows.at(-1), deltaValue = last.mean_percent-first.mean_percent, format = value => value.toFixed(2)+'%';
    byId('confidence-trend-summary').textContent = `${format(first.mean_percent)} → ${format(last.mean_percent)} (${deltaValue >= 0 ? '+' : '−'}${Math.abs(deltaValue).toFixed(2)} percentage points). ${number(last.rated_edge_count)} of ${number(last.rated_edge_count+last.unrated_edge_count)} graph father links individually rated; ${last.rated_edges_percent.toFixed(1)}% review coverage.`;
    const width = chartWidth(target), height = 210, left = 56, right = 16, top = 18, bottom = 34;
    const values = rows.map(row => row.mean_percent), low = Math.min(...values), high = Math.max(...values);
    const padding = Math.max(.5, (high-low)*.2), min = Math.max(0, low-padding), max = Math.min(100, high+padding);
    const x = i => rows.length === 1 ? (left+width-right)/2 : left+i/(rows.length-1)*(width-left-right);
    const y = value => height-bottom-(value-min)/(max-min)*(height-top-bottom);
    const label = row => `${row.date} · review ${row.revision}`;
    const svg = [`<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Mean reviewed father confidence by saved review; the axis starts at ${min.toFixed(1)}%">`];
    for (let i = 0; i <= 4; i++) { const value = min+(max-min)*i/4, yy = y(value); svg.push(`<line class="pd-grid" x1="${left}" x2="${width-right}" y1="${yy}" y2="${yy}"/><text class="pd-axis" x="${left-8}" y="${yy+4}" text-anchor="end">${value.toFixed(1)}%</text>`); }
    svg.push(`<path d="${rows.map((row,i) => `${i ? 'L' : 'M'}${x(i)},${y(row.mean_percent)}`).join(' ')}" fill="none" stroke="#386eaf" stroke-width="2" stroke-linejoin="round"/>`);
    rows.forEach((row,i) => {
      svg.push(`<circle cx="${x(i)}" cy="${y(row.mean_percent)}" r="4" fill="#386eaf" stroke="#fffef9" stroke-width="2"><title>${esc(`${label(row)}: ${format(row.mean_percent)}, ${row.rated_edge_count} rated graph father links`)}</title></circle>`);
      if (i === 0 || i === rows.length-1) svg.push(`<text class="pd-axis" x="${x(i)}" y="${height-12}" text-anchor="${i === 0 ? 'start' : 'end'}">${esc(shortDate(row.date))}</text>`);
    });
    target.innerHTML = svg.join('')+'</svg>';
    byId('confidence-trend-rows').innerHTML = rows.map(row => `<tr><th scope="row">${esc(label(row))}</th><td>${format(row.mean_percent)}</td><td>${number(row.rated_edge_count)}</td><td>${row.rated_edges_percent.toFixed(1)}%</td></tr>`).join('');
  }
  function renderSnapshotHistory() {
    const fixed = byId('history-cohort').value === 'fixed', cohort = fixed ? 'fixed' : state.cutoff, metric = byId('history-metric').value;
    const rows = dailyHistory(data.progress_history, data.history_method_version, cohort);
    byId('history-cohort').options[1].textContent = `Selected cohort · born through ${state.cutoff}`;
    const scope = fixed ? `Fixed baseline: the same ${number(data.history_baseline.population)} people through ${data.history_baseline.cutoff}` : `Cohort born through ${state.cutoff}: people available at each snapshot`;
    byId('history-scope').textContent = scope + '. Comparable measurements use the current method; earlier classification changes are excluded.';
    renderUncertaintyTrend(rows);
    renderConfidenceTrend(cohort);
    const exactConfidence = metric === 'reviewed_confidence_percent';
    const views = exactConfidence ? [{key:'working', label:'Reviewed father confidence', color:'#386eaf'}] : historyViews.filter(view => byId('history-'+view.key).checked);
    byId('history-confidence-levels').hidden = exactConfidence;
    const series = views.map(view => ({...view, points:historySeries(rows, view.key, metric)}));
    const values = series.flatMap(view => view.points.filter(p => p.value !== null).map(p => p.value));
    const percent = metric.endsWith('_percent'), decimals = metric === 'assessed_links_percent' ? 1 : 3;
    const format = value => percent ? value.toFixed(decimals)+'%' : number(value);
    byId('history-note').textContent = rows.length < 2 ? 'Only one dated snapshot is available for this cohort; its history starts here.' : '';
    byId('history-table-caption').textContent = `${historyMetrics[metric]} · ${scope}`;
    byId('history-table-head').innerHTML = '<tr><th scope="col">Date</th>'+views.map(view => `<th scope="col">${esc(view.label)}</th>`).join('')+(exactConfidence ? '<th scope="col">Individually rated</th><th scope="col">Review coverage</th>' : '')+'</tr>';
    byId('history-table-body').innerHTML = rows.map(row => '<tr><th scope="row">'+esc(row.date)+'</th>'+views.map(view => {
      const value = historySeries([row], view.key, metric)[0].value;
      return '<td>'+(Number.isFinite(value) ? esc(format(value)) : 'Not recorded')+'</td>';
    }).join('')+(exactConfidence ? (() => {
      const coverage = row.metrics.working?.individual_confidence;
      return coverage ? `<td>${number(coverage.rated_edge_count)} of ${number(coverage.rated_edge_count+coverage.unrated_edge_count)}</td><td>${coverage.rated_edges_percent.toFixed(1)}%</td>` : '<td>Not recorded</td><td>Not recorded</td>';
    })() : '')+'</tr>').join('');
    byId('history-changes').innerHTML = series.map(view => {
      const points = view.points.filter(point => point.value !== null);
      if (!points.length) return '';
      const first = points[0], last = points.at(-1), change = last.value-first.value;
      const size = percent ? Math.abs(change).toFixed(decimals)+' percentage points' : number(Math.abs(change));
      return `<div class="history-${exactConfidence ? 'supported' : view.key}"><span>${esc(view.label)}</span><strong>${esc(format(last.value))}</strong><small>${points.length > 1 ? `${change > 0 ? '+' : change < 0 ? '−' : ''}${esc(size)} since ${esc(shortDate(first.date))}` : `First snapshot · ${esc(shortDate(last.date))}`}</small></div>`;
    }).join('');
    const target = byId('history-chart');
    if (!values.length) { target.innerHTML = `<p class="history-empty">${exactConfidence ? 'No individually rated father links have been recorded for this cohort.' : 'Select a confidence level to display its history.'}</p>`; return; }
    const width = chartWidth(target), height = 280, left = 64, right = 16, top = 18, bottom = 34;
    const low = Math.min(...values), high = Math.max(...values), spread = high-low;
    const padding = Math.max(spread*.18, high*.025, metric === 'connected_pairs_percent' ? .005 : 2);
    const min = percent && metric !== 'connected_pairs_percent' ? 0 : Math.max(0, low-padding), max = percent && metric !== 'connected_pairs_percent' ? 100 : high+padding;
    const start = time(rows[0].date), end = time(rows.at(-1).date);
    const x = date => start === end ? (left+width-right)/2 : left+(time(date)-start)/(end-start)*(width-left-right);
    const y = value => height-bottom-(value-min)/(max-min)*(height-top-bottom);
    const svg = [`<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="${esc(historyMetrics[metric])} over time. ${esc(scope)}. The axis starts at ${esc(format(min))}; the snapshot table has every value.">`];
    for (let i = 0; i <= 4; i++) { const value = min+(max-min)*i/4, yy = y(value); svg.push(`<line class="pd-grid" x1="${left}" x2="${width-right}" y1="${yy}" y2="${yy}"/><text class="pd-axis" x="${left-8}" y="${yy+4}" text-anchor="end">${esc(percent ? value.toFixed(metric === 'connected_pairs_percent' ? 2 : 0)+'%' : number(Math.round(value)))}</text>`); }
    const ticks = rows.filter((row,i) => i === 0 || i === rows.length-1 || i % Math.ceil(rows.length/(width < 500 ? 3 : 5)) === 0);
    ticks.forEach(row => svg.push(`<text class="pd-axis" x="${x(row.date)}" y="${height-12}" text-anchor="${row === rows[0] ? 'start' : row === rows.at(-1) ? 'end' : 'middle'}">${esc(shortDate(row.date))}</text>`));
    series.forEach(view => {
      let path = '', connected = false;
      view.points.forEach(point => { if (point.value === null) { connected = false; return; } path += `${connected ? 'L' : 'M'}${x(point.date)},${y(point.value)} `; connected = true; });
      svg.push(`<path d="${path}" fill="none" stroke="${view.color}" stroke-width="2" stroke-linejoin="round" ${view.key === 'working' && !exactConfidence ? 'stroke-dasharray="7 5"' : ''}/>`);
      view.points.filter(point => point.value !== null).forEach(point => svg.push(`<circle cx="${x(point.date)}" cy="${y(point.value)}" r="4" fill="${view.color}" stroke="#fffef9" stroke-width="2"><title>${esc(`${point.date}: ${view.label}, ${format(point.value)}`)}</title></circle>`));
    });
    target.innerHTML = svg.join('')+'</svg>';
  }

  // ---------- State, URL and events ----------
  function saveParams() {
    const params = new URLSearchParams(location.search);
    params.set('through', state.cutoff); params.set('links', state.view);
    const metric = byId('history-metric').value;
    if (metric === 'edge_count') params.delete('history'); else params.set('history', metric);
    if (byId('history-cohort').value === 'fixed') params.delete('historyCohort'); else params.set('historyCohort', 'selected');
    if (state.day) params.set('day', state.day); else params.delete('day');
    if (state.range === '30') params.delete('range'); else params.set('range', state.range);
    history.replaceState(null, '', location.pathname+'?'+params+location.hash);
  }
  const isOpen = id => byId(id)?.open;
  function update() {
    state.cutoff = byId('progress-cutoff').value; state.view = byId('progress-view').value;
    state.findingsLimit = 100;
    renderResearch();
    renderKpis();
    renderCohortPanels();
    renderFindings();
    if (isOpen('catalogue-history')) renderSnapshotHistory();
    saveParams();
  }
  const params = new URLSearchParams(location.search);
  if (data.cohorts[params.get('through')]) byId('progress-cutoff').value = params.get('through');
  if (Object.keys(data.views).includes(params.get('links'))) byId('progress-view').value = params.get('links');
  if (Object.hasOwn(historyMetrics, params.get('history'))) byId('history-metric').value = params.get('history');
  if (params.get('historyCohort') === 'selected') byId('history-cohort').value = 'selected';
  setRange(['14','30','all'].includes(params.get('range')) ? params.get('range') : '30', false);
  ['progress-cutoff','progress-view'].forEach(id => byId(id).addEventListener('change', update));
  ['early-heads'].forEach(id => byId(id).addEventListener('change', renderCohortPanels));
  byId('head-search').addEventListener('input', renderCohortPanels);
  ['history-cohort','history-metric',...historyViews.map(view => 'history-'+view.key)].forEach(id => byId(id).addEventListener('change', () => { renderSnapshotHistory(); saveParams(); }));
  ['findings-kind','findings-all-cohorts'].forEach(id => byId(id).addEventListener('change', () => { state.findingsLimit = 100; renderFindings(); }));
  byId('findings-search').addEventListener('input', () => { state.findingsLimit = 100; renderFindings(); });
  byId('findings-more').addEventListener('click', () => { state.findingsLimit += 100; renderFindings(); });
  ['priority-order','priority-early','priority-kind'].forEach(id => byId(id).addEventListener('change', () => { state.priorityLimit = 20; renderPriorities(); }));
  byId('priority-more').addEventListener('click', () => { state.priorityLimit += 20; renderPriorities(); });
  document.querySelectorAll('.pd-seg button').forEach(button => button.addEventListener('click', () => setRange(button.dataset.range)));
  document.addEventListener('click', event => {
    const link = event.target.closest('[data-day]');
    if (!link || link.classList.contains('pd-hit')) return;
    event.preventDefault();
    selectDay(state.day === link.dataset.day && link.tagName === 'BUTTON' ? null : link.dataset.day, true);
  });
  byId('catalogue-history').addEventListener('toggle', () => { if (byId('catalogue-history').open) renderSnapshotHistory(); });
  let resizeTimer, lastWidth = innerWidth;
  window.addEventListener('resize', () => {
    if (innerWidth === lastWidth) return;
    lastWidth = innerWidth; clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => { renderDayChart(); if (isOpen('catalogue-history')) renderSnapshotHistory(); }, 120);
  });
  function reveal() {
    const id = decodeURIComponent(location.hash.slice(1));
    if (!id) return;
    if (/^day-\d{4}-\d{2}-\d{2}$/.test(id)) { selectDay(id.slice(4), true); return; }
    const target = byId(id);
    if (!target) return;
    for (let node = target; node; node = node.parentElement) if (node.tagName === 'DETAILS') node.open = true;
    if (isOpen('catalogue-history')) renderSnapshotHistory();
    requestAnimationFrame(() => target.scrollIntoView({block:'start'}));
  }
  update();
  renderPriorities();
  if (params.get('day')) selectDay(params.get('day'), false);
  window.addEventListener('hashchange', reveal);
  reveal();
})();
