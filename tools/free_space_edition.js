(() => {
  'use strict';
  const contents = document.querySelector('.fsp-contents details');
  if (contents && matchMedia('(max-width:760px)').matches) contents.open = false;
  const updates = document.querySelector('#edition-updates details');
  const revealAnchor = () => { if (location.hash === '#edition-updates' && updates) updates.open = true; };
  revealAnchor();
  addEventListener('hashchange', revealAnchor);
  document.querySelectorAll('a[href="#edition-updates"]').forEach(link => link.addEventListener('click', () => {
    if (updates) updates.open = true;
  }));

  const q = document.getElementById('fsp-search');
  const category = document.getElementById('fsp-category');
  const order = document.getElementById('fsp-order');
  if (!q || !category || !order) return;
  const results = document.getElementById('fsp-results');
  const count = document.getElementById('fsp-count');
  const empty = document.getElementById('fsp-empty');
  const heading = document.getElementById('fsp-library-title');
  const description = document.getElementById('fsp-topic-description');
  const pagination = document.getElementById('fsp-pagination');
  const previous = document.getElementById('fsp-prev');
  const next = document.getElementById('fsp-next');
  const pageStatus = document.getElementById('fsp-page-status');
  const topics = [...document.querySelectorAll('[data-fsp-topic]')];
  const normal = s => String(s || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
  const cards = [...results.querySelectorAll('.fsp-card')].map((element, index) => ({
    element, index, title: element.querySelector('h3').textContent,
    search: normal(element.dataset.search), category: element.dataset.category,
    importance: Number(element.dataset.importance)
  }));
  const pageSize = 12;
  let pageNumber = 1;
  let timer;

  function render(update = true) {
    const terms = normal(q.value).split(' ').filter(Boolean);
    const topic = category.value;
    const sorted = [...cards].sort((a, b) => order.value === 'title'
      ? a.title.localeCompare(b.title) || a.index - b.index
      : b.importance - a.importance || a.index - b.index);
    const matches = sorted.filter(card => (!topic || card.category === topic) && terms.every(term => card.search.includes(term)));
    const totalPages = Math.max(1, Math.ceil(matches.length / pageSize));
    pageNumber = Math.max(1, Math.min(pageNumber, totalPages));
    const start = (pageNumber - 1) * pageSize;
    const matched = new Set(matches);
    const visible = new Set(matches.slice(start, start + pageSize));
    for (const card of sorted) {
      card.element.hidden = !visible.has(card);
      card.element.dataset.fspMatch = String(matched.has(card));
      results.append(card.element);
    }
    count.textContent = matches.length === 1 ? '1 study' : matches.length ? `${start + 1}–${Math.min(start + pageSize, matches.length)} of ${matches.length} studies` : '0 studies';
    empty.hidden = matches.length !== 0;
    heading.textContent = topic || 'All studies';
    description.textContent = topics.find(button => button.dataset.fspTopic === topic)?.dataset.description || 'Browse the full collection, or choose a topic to narrow your reading.';
    topics.forEach(button => button.setAttribute('aria-pressed', String(button.dataset.fspTopic === topic)));
    pagination.hidden = totalPages < 2;
    previous.disabled = pageNumber === 1;
    next.disabled = pageNumber === totalPages;
    pageStatus.textContent = `Page ${pageNumber} of ${totalPages}`;
    if (update) {
      const params = new URLSearchParams();
      if (q.value.trim()) params.set('q', q.value.trim());
      if (topic) params.set('topic', topic);
      if (order.value !== 'importance') params.set('order', order.value);
      if (pageNumber > 1) params.set('page', pageNumber);
      history.replaceState(null, '', location.pathname + (params.size ? '?' + params : '') + location.hash);
    }
  }

  function filter() { clearTimeout(timer); pageNumber = 1; render(); }
  function reset() { q.value = ''; category.value = ''; order.value = 'importance'; filter(); q.focus(); }
  q.addEventListener('input', () => { clearTimeout(timer); timer = setTimeout(filter, 80); });
  category.addEventListener('change', filter);
  order.addEventListener('change', filter);
  document.querySelector('.fsp-controls').addEventListener('submit', event => { event.preventDefault(); filter(); });
  document.getElementById('fsp-clear').addEventListener('click', reset);
  document.querySelector('[data-fsp-reset]').addEventListener('click', reset);
  topics.forEach(button => button.addEventListener('click', () => {
    category.value = button.dataset.fspTopic;
    filter();
  }));
  function turnPage(delta) {
    clearTimeout(timer);
    pageNumber += delta;
    render();
    // Keep focus on a usable control when the last/first page disables its button.
    const focusTarget = delta > 0 ? (next.disabled ? previous : next) : (previous.disabled ? next : previous);
    focusTarget.focus({ preventScroll: true });
    document.querySelector('.fsp-listing').scrollIntoView({ block: 'start' });
  }
  previous.addEventListener('click', () => turnPage(-1));
  next.addEventListener('click', () => turnPage(1));
  function restore() {
    clearTimeout(timer);
    const params = new URLSearchParams(location.search);
    q.value = params.get('q') || '';
    category.value = params.get('topic') || '';
    if (category.selectedIndex < 0) category.value = '';
    order.value = params.get('order') === 'title' ? 'title' : 'importance';
    pageNumber = /^\d+$/.test(params.get('page') || '') ? Number(params.get('page')) : 1;
    if (!Number.isSafeInteger(pageNumber)) pageNumber = 1;
    render(false);
  }
  addEventListener('popstate', restore);
  restore();
})();
