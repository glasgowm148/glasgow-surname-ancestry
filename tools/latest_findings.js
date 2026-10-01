/* Progressive enhancement: the complete dated table also works without JS. */
(() => {
  const body = document.getElementById('lf-rows');
  if (!body) return;
  const rows = [...body.children];
  const form = document.getElementById('lf-controls');
  const query = document.getElementById('lf-query');
  const kind = document.getElementById('lf-kind');
  const status = document.getElementById('lf-status');
  const order = document.getElementById('lf-order');
  const count = document.getElementById('lf-count');
  const pagination = document.getElementById('lf-pagination');
  const previous = document.getElementById('lf-prev');
  const next = document.getElementById('lf-next');
  const pageLabel = document.getElementById('lf-page');
  const empty = document.getElementById('lf-empty');
  const pageSize = 50;
  let page = 0;
  let filtered = [];
  const params = new URLSearchParams(location.search);
  query.value = params.get('q') || '';
  if ([...kind.options].some(option => option.value === params.get('type'))) kind.value = params.get('type');
  if ([...status.options].some(option => option.value === params.get('status'))) status.value = params.get('status');
  if (params.get('order') === 'oldest') order.value = 'oldest';
  function render() {
    const last = Math.max(0, Math.ceil(filtered.length / pageSize) - 1);
    page = Math.min(page, last);
    const start = page * pageSize;
    body.replaceChildren(...filtered.slice(start, start + pageSize));
    [...body.children].forEach(row => { row.querySelector('.lf-date').href = `${location.pathname}${location.search}#${row.id}`; });
    count.textContent = filtered.length
      ? `${start + 1}–${Math.min(start + pageSize, filtered.length)} of ${filtered.length.toLocaleString()} findings${filtered.length !== rows.length ? ` (${rows.length.toLocaleString()} total)` : ''} · ${order.value === 'oldest' ? 'oldest' : 'newest'} first`
      : `0 of ${rows.length.toLocaleString()} findings`;
    empty.hidden = filtered.length !== 0;
    if(['relationship-certain','father-certain','relationship-ungraded'].includes(status.value)){
      const father=status.value==='father-certain',total=filtered.reduce((n,row)=>n+Number((father?row.dataset.fatherCount:row.dataset.changeCount)||0),0),ungraded=filtered.reduce((n,row)=>n+Number((father?row.dataset.fatherUngradedCount:row.dataset.ungradedCount)||0),0);
      count.textContent+=` · ${total} ${father?'father':'relationship'} changes (${total-ungraded} uncertain/unknown, ${ungraded} previously ungraded)`;
    }
    empty.textContent = status.value === 'father-certain' && !rows.some(row => row.dataset.relationshipUpgrade.split(' ').includes('father'))
      ? 'No dated finding currently documents a previously uncertain or unknown father relationship becoming certain.'
      : status.value === 'relationship-certain' && !rows.some(row => row.dataset.relationshipUpgrade)
        ? 'No dated finding currently documents a previously uncertain or unknown relationship becoming certain.'
        : 'No findings match those filters. Try another name or place, or reset the filters.';
    pagination.hidden = filtered.length <= pageSize;
    previous.disabled = page === 0;
    next.disabled = page === last;
    pageLabel.textContent = `Page ${page + 1} of ${last + 1}`;
  }
  function apply(updateURL = true) {
    const terms = query.value.toLocaleLowerCase().trim().split(/\s+/).filter(Boolean);
    filtered = rows.filter(row => (!kind.value || row.dataset.kind === kind.value)
      && (!status.value || (status.value === 'relationship-certain'
        ? Boolean(row.dataset.relationshipUpgrade)
        : status.value === 'father-certain'
          ? row.dataset.relationshipUpgrade.split(' ').includes('father')
          : status.value === 'relationship-ungraded'
            ? Number(row.dataset.ungradedCount)>0
            : row.dataset.status === status.value))
      && terms.every(term => row.dataset.search.includes(term)));
    filtered.sort((a, b) => {
      const date = a.dataset.date.localeCompare(b.dataset.date);
      return (order.value === 'oldest' ? date : -date) || a.id.localeCompare(b.id);
    });
    page = 0;
    const anchor = location.hash.startsWith('#finding-') && filtered.findIndex(row => `#${row.id}` === location.hash);
    if (typeof anchor === 'number' && anchor >= 0) page = Math.floor(anchor / pageSize);
    if (updateURL && location.protocol !== 'file:') {
      const url = new URL(location.href);
      for (const [key, value] of [['q', query.value.trim()], ['type', kind.value], ['status', status.value], ['order', order.value === 'oldest' ? 'oldest' : '']]) {
        if (value) url.searchParams.set(key, value); else url.searchParams.delete(key);
      }
      history.replaceState(null, '', url);
    }
    render();
  }
  form.hidden = false;
  form.addEventListener('submit', event => event.preventDefault());
  query.addEventListener('input', () => apply());
  [kind, status, order].forEach(control => control.addEventListener('change', () => apply()));
  form.addEventListener('reset', () => setTimeout(() => apply(), 0));
  previous.addEventListener('click', () => { page--; render(); document.getElementById('lf-table-title').scrollIntoView({block:'start'}); });
  next.addEventListener('click', () => { page++; render(); document.getElementById('lf-table-title').scrollIntoView({block:'start'}); });
  window.addEventListener('hashchange', () => apply(false));
  window.addEventListener('popstate', () => {
    const values = new URLSearchParams(location.search);
    query.value = values.get('q') || ''; kind.value = values.get('type') || '';
    status.value = values.get('status') || ''; order.value = values.get('order') || 'newest';
    apply(false);
  });
  apply(false);
  if (location.hash.startsWith('#finding-')) document.getElementById(location.hash.slice(1))?.scrollIntoView();
})();
