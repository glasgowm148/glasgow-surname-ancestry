/* Focus one statistical story at a time; every chart remains readable without JS. */
(() => {
  'use strict';
  const navToggle = document.getElementById('g-nav-toggle');
  if (navToggle) navToggle.addEventListener('click', event => {
    if (!matchMedia('(min-width: 761px) and (max-width: 1100px)').matches) return;
    event.stopImmediatePropagation();
    document.body.classList.toggle('g-nav-open');
    navToggle.setAttribute('aria-expanded', String(document.body.classList.contains('g-nav-open')));
  }, true);
  // Keep the chart surface quiet: combine interpretation and mode notes once.
  document.querySelectorAll('.statistics-panel').forEach(panel => {
    const method = panel.querySelector('.statistics-panel-method');
    if (!method) return;
    const seen = new Set();
    panel.querySelectorAll('.statistics-chart-note').forEach(note => {
      const wording = note.textContent.trim();
      if (seen.has(wording)) note.remove();
      else { seen.add(wording); method.append(note); }
    });
    panel.querySelectorAll('.statistics-chart-method').forEach(details => details.remove());
  });
  const tabs = [...document.querySelectorAll('[data-statistics-view]')];
  const panes = [...document.querySelectorAll('[data-statistics-pane]')];
  if (!tabs.length || !panes.length) return;
  const nav = tabs[0].closest('nav');
  nav.setAttribute('role', 'tablist');
  function select(key, updateHistory = false) {
    const selected = tabs.find(tab => tab.dataset.statisticsView === key) || tabs[0];
    key = selected.dataset.statisticsView;
    tabs.forEach(tab => {
      const active = tab === selected;
      tab.setAttribute('role', 'tab');
      tab.setAttribute('aria-selected', String(active));
      tab.setAttribute('aria-controls', 'statistics-view-' + tab.dataset.statisticsView);
      tab.tabIndex = active ? 0 : -1;
    });
    panes.forEach(pane => {
      pane.hidden = pane.dataset.statisticsPane !== key;
      pane.setAttribute('role', 'tabpanel');
      pane.tabIndex = 0;
    });
    if (updateHistory && location.hash !== selected.hash) history.pushState(null, '', selected.hash);
  }
  function fromHash(scroll = false) {
    let id;
    try { id = decodeURIComponent(location.hash.slice(1)); } catch (_) { id = ''; }
    const target = document.getElementById(id);
    const pane = target && target.closest('[data-statistics-pane]');
    select(pane ? pane.dataset.statisticsPane : 'names');
    if (pane && target) {
      let parent = target.parentElement;
      while (parent && parent !== pane) {
        if (parent.tagName === 'DETAILS') parent.open = true;
        parent = parent.parentElement;
      }
      if (scroll) requestAnimationFrame(() => target.scrollIntoView({block: 'start'}));
    }
  }
  tabs.forEach((tab, index) => {
    tab.addEventListener('click', event => {
      event.preventDefault();
      select(tab.dataset.statisticsView, true);
    });
    tab.addEventListener('keydown', event => {
      let next;
      if (event.key === 'ArrowRight') next = (index + 1) % tabs.length;
      if (event.key === 'ArrowLeft') next = (index + tabs.length - 1) % tabs.length;
      if (event.key === 'Home') next = 0;
      if (event.key === 'End') next = tabs.length - 1;
      if (next !== undefined) {
        event.preventDefault();
        select(tabs[next].dataset.statisticsView, true);
        tabs[next].focus();
      }
    });
  });
  addEventListener('hashchange', () => fromHash(true));
  addEventListener('popstate', () => fromHash(false));
  fromHash(Boolean(location.hash));
})();
