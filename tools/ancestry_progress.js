(() => {
  'use strict';
  const element = document.getElementById('ancestry-progress-data');
  if (!element) return;
  const data = JSON.parse(element.textContent), byId = id => document.getElementById(id);
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const number = value => Number(value).toLocaleString('en-GB');
  function update() {
    const cutoff = byId('progress-cutoff').value, view = byId('progress-view').value;
    const summary = data.cohorts[cutoff][view], early = byId('early-heads').checked;
    const query = byId('head-search').value.trim().toLowerCase();
    const values = [[number(summary.component_count),'separate paternal branches'],[number(summary.unattached_multi_child_roots.length),'unattached fathers with 2+ children'],[summary.largest_component_percent.toFixed(1)+'%','people in the largest branch'],[summary.connected_pairs_percent.toFixed(2)+'%','pairs connected through fathers']];
    byId('connectivity-stats').innerHTML = values.map(([value,label]) => `<div><strong>${esc(value)}</strong><span>${esc(label)}</span></div>`).join('');
    byId('cohort-detail').textContent = `${number(summary.population)} public surname bearers; ${number(summary.edge_count)} father–child links. Both views use the same people.`;
    const roots = summary.family_roots.filter(r => (!early || (r.year !== null && r.year <= data.early_cutoff)) && (!query || `${r.name} ${r.id}`.toLowerCase().includes(query)));
    byId('head-count').textContent = `${number(roots.length)} ${early?'early ':''}family heads shown, oldest first`;
    byId('family-head-rows').innerHTML = roots.length ? roots.map(r => `<tr><td><a href="${esc(r.url)}">${esc(r.name)}</a><small>${esc(r.id)}</small></td><td>${esc(r.year ?? 'Undated')}<small>${esc(r.year_basis || 'ancestor of dated person')} · ${esc(r.year_status)}</small></td><td>${number(r.child_count)}</td><td>${number(r.descendant_count)}</td></tr>`).join('') : '<tr><td colspan="4">No family head matches these choices.</td></tr>';
    const oldest = summary.family_roots.filter(r => r.year !== null && r.year <= data.early_cutoff).slice(0,6);
    byId('working-origin-map').innerHTML = `<div class="origin-heading">Shared paternal origin · working hypothesis<small>c. 1400–1450, possibly earlier; the founder and intervening generations remain open</small></div><div class="origin-branches">${oldest.map(r => `<div class="origin-branch"><a href="${esc(r.url)}">${esc(r.name)}</a><small>Cohort year ${esc(r.year)} (${esc(r.year_status)}) · ${number(r.descendant_count)} surname descendants</small></div>`).join('')}</div><p class="source-line">${oldest.length} earliest family heads shown. Dotted connections express the common-origin research model; only specific father–child links count in the measurements.</p>`;
    const params = new URLSearchParams(); params.set('through',cutoff); params.set('links',view);
    history.replaceState(null,'',location.pathname+'?'+params+location.hash);
  }
  const params = new URLSearchParams(location.search);
  if (data.cohorts[params.get('through')]) byId('progress-cutoff').value=params.get('through');
  if (['working','confident'].includes(params.get('links'))) byId('progress-view').value=params.get('links');
  ['progress-cutoff','progress-view','early-heads'].forEach(id => byId(id).addEventListener('change',update));
  byId('head-search').addEventListener('input',update);
  update();
})();
