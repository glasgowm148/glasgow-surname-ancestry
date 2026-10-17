/* Page filtering enhances the complete static directory; links need no JS. */
(() => {
  const input = document.getElementById('sitemap-search');
  if (!input) return;
  const groups = [...document.querySelectorAll('.sitemap-group')];
  const entries = groups.flatMap(group => [...group.querySelectorAll('li')]);
  const normalise = text => text.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
  const texts = new Map(entries.map(entry => [entry, normalise(entry.textContent + ' ' + entry.querySelector('a').getAttribute('href'))]));
  const previous = new Map();
  document.querySelector('.sitemap-search').hidden = false;
  function filter() {
    const terms = normalise(input.value.trim()).split(/\s+/).filter(Boolean);
    let count = 0;
    entries.forEach(entry => {
      entry.hidden = !terms.every(term => texts.get(entry).includes(term));
      if (!entry.hidden) count++;
    });
    groups.forEach(group => {
      const detail = group.querySelector('details');
      group.hidden = ![...group.querySelectorAll('li')].some(entry => !entry.hidden);
      if (terms.length) {
        if (!previous.has(detail)) previous.set(detail, detail.open);
        if (!group.hidden) detail.open = true;
      } else if (previous.has(detail)) {
        detail.open = previous.get(detail);
        previous.delete(detail);
      }
    });
    document.getElementById('sitemap-count').textContent = `${count.toLocaleString()} of ${entries.length.toLocaleString()} pages`;
    document.getElementById('sitemap-empty').hidden = count !== 0;
  }
  input.addEventListener('input', filter);
  document.querySelectorAll('.sitemap-jumps a').forEach(link => link.addEventListener('click', () => {
    const section = document.getElementById(link.hash.slice(1));
    if (section) section.querySelector('details').open = true;
  }));
  window.addEventListener('beforeprint', () => groups.forEach(group => {
    const detail = group.querySelector('details');
    detail.dataset.beforePrint = String(detail.open);
    detail.open = true;
  }));
  window.addEventListener('afterprint', () => groups.forEach(group => {
    const detail = group.querySelector('details');
    detail.open = detail.dataset.beforePrint === 'true';
  }));
})();
