(() => {
  'use strict';
  const research = window.GlasgowResearch;
  const ui = window.GlasgowV3;
  const list = document.querySelector('#v3-early-list');
  if (!research || !ui || !list) return;
  const escape = research.esc;
  const query = document.querySelector('#v3-early-q');
  const era = document.querySelector('#v3-early-era');
  const params = new URLSearchParams(location.search);
  query.value = params.get('q') || '';
  era.value = params.get('era') || 'all';
  let entries = [];
  let page = 0;

  function card(row) {
    const dossier = row.slug && '/people/' + encodeURIComponent(row.slug) + '.html';
    const links = row.sources.slice(0, 3).map((id, index) =>
      `<a href="/sources/${encodeURIComponent(id)}/">Source ${index + 1} →</a>`);
    if (row.atlas) links.push(`<a href="/onetree/?person=${encodeURIComponent(row.atlas_id || row.id)}#person=${encodeURIComponent(row.atlas_id || row.id)}&view=family">Locate in the atlas →</a>`);
    else links.push('<span>Documentary occurrence; not an atlas node</span>');
    if (dossier) links.push(`<a href="${dossier}">Research catalogue →</a>`);
    if (row.url) links.push(`<a href="${escape(row.url)}">Read the documentary register →</a>`);
    const basis = {personal: 'Imported vital or personal event', mention: 'Dated record mention', family: 'Wider family evidence'};
    return `<article class="v3-early-row"><time>${escape(row.date_label || row.year)}</time><div><span class="r-kicker">${escape(row.id)} · ${escape(basis[row.basis] || row.basis)}</span><h3><a href="${escape(dossier || row.url)}">${escape(row.name)}</a></h3><p>${escape(row.place || 'Place not supplied')} · ${escape(row.life)}</p><div class="v3-inline-links">${links.join('')}</div></div>${research.country(row.country)}</article>`;
  }

  function render() {
    const terms = research.norm(query.value).split(' ').filter(Boolean);
    const [from, to] = era.value === 'all' ? [0, 1650] : era.value.split('-').map(Number);
    const rows = entries.filter(row => row.year >= from && row.year <= to &&
      terms.every(term => research.norm([row.id, row.name, row.place, row.life].join(' ')).includes(term)));
    const pages = Math.max(1, Math.ceil(rows.length / 24));
    page = Math.max(0, Math.min(page, pages - 1));
    document.querySelector('#v3-early-count').textContent = rows.length.toLocaleString() + ' early catalogue entries. Separate occurrences are not joined into a founding family.';
    list.innerHTML = rows.slice(page * 24, page * 24 + 24).map(card).join('') || '<p class="r-empty">No early entries match these filters.</p>';
    ui.pageNav(document.querySelector('#v3-early-pages'), pages, page, next => {
      page = next;
      render();
      list.scrollIntoView({block: 'start'});
    });
    ui.update({q: query.value, era: era.value === 'all' ? null : era.value});
  }

  query.oninput = ui.debounce(() => { page = 0; render(); });
  era.onchange = () => { page = 0; render(); };
  research.json('/assets/v3/early-entries.json').then(rows => { entries = rows; render(); })
    .catch(error => ui.fail(list, error));
})();
