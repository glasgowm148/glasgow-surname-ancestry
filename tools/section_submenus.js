/* Selected-section navigation mirrors the page's maintained local navigation. */
(() => {
  function mobileNavigation(rail) {
    const drawer = rail.closest('.g-rail');
    if (!drawer) return null;
    const mobile = matchMedia('(max-width:760px)');
    const extras = document.createElement('div');
    extras.className = 'g-mobile-nav-extras';
    const utilityLinks = [...drawer.children].filter(node =>
      node.matches('.repair-quick-links,.g-rail-bottom'));
    rail.after(extras);
    function disclosure(className, label) {
      const group = document.createElement('details');
      group.className = className;
      const summary = document.createElement('summary');
      summary.textContent = label;
      group.append(summary);
      return group;
    }
    const more = disclosure('g-mobile-more-links', 'More links');
    if (utilityLinks.length) {
      more.append(...utilityLinks);
      extras.append(more);
    }
    let section = null;
    let selected = null;
    function sync() {
      more.open = !mobile.matches;
      if (section) {
        section.open = !mobile.matches;
        if (mobile.matches) extras.prepend(section);
        else selected.after(section);
      }
    }
    mobile.addEventListener('change', sync);
    sync();
    return {
      attach(submenu, link) {
        selected = link;
        section = disclosure('g-mobile-section-links', `${link.textContent.trim()} sections`);
        section.append(submenu);
        sync();
        return section;
      },
    };
  }

  function start() {
    const rail = document.querySelector('.g-nav');
    if (!rail) return;
    const mobileNav = mobileNavigation(rail);
    const primary = [...rail.querySelectorAll(':scope > .g-nav-link')];
    const clean = path => path.replace(/index\.html$/, '').replace(/\/$/, '') || '/';
    const path = clean(location.pathname);
    const roots = [
      [/^\/(research|sources|records|events|free-space|compare|connections|candidate-matches)(\/|$)/, '/research/'],
      [/^\/branches(\/|$)/, '/branches/'],
      [/^\/(catalogue|people|early-records)(\/|\.|$)/, '/catalogue/'],
      [/^\/(ydna|dna)(\/|$)/, '/ydna/'],
      [/^\/timeline(\/|$)/, '/timeline/'],
      [/^\/map(\/|$)/, '/map/'],
      [/^\/onetree(\/|$)/, '/onetree/'],
    ];
    const root = path === '/' ? '/' : roots.find(([pattern]) => pattern.test(path))?.[1];
    if (!root) return;
    const selected = primary.find(link => clean(new URL(link.href).pathname) === clean(root || ''))
      || primary.find(link => link.getAttribute('aria-current') === 'page');
    if (!selected) return;
    primary.forEach(link => {
      if (link === selected) link.setAttribute('aria-current', 'page');
      else link.removeAttribute('aria-current');
    });
    // Overview and Map have no sidebar submenu.
    // Other sections expose only destinations they themselves own.
    if (path === '/' || root === '/map/') return;
    const dna = path === '/ydna';
    const timeline = path === '/timeline';
    const source = document.querySelector(dna ? '#sidebar .main-nav' : timeline ? '.g-timeline-jumps' : '.v3-view-nav');
    let submenu = dna ? rail.querySelector('.g-dna-subnav') : null;
    if (!submenu) submenu = document.createElement('div');
    submenu.classList.add('g-section-subnav');
    submenu.setAttribute('role', 'group');
    submenu.setAttribute('aria-label', `${selected.textContent.trim()} sections`);
    const sectionDisclosure = mobileNav?.attach(submenu, selected);
    if (!mobileNav) selected.after(submenu);
    const fallback = [];
    function ownedLinks() {
      const make = (href, text) => {
        const link = document.createElement('a');
        link.href = href;
        link.textContent = text;
        return link;
      };
      if (path.startsWith('/branches')) return [
        make('/branches/', 'All families'),
        make('/branches/#research-studies', 'Research groups'),
        make('/branches/scottish-families/', 'Scottish families'),
      ];
      if (/^\/(research|records|sources|free-space|events)(\/|$)/.test(path)) return [
        make('/research/#open-questions', 'Open questions'),
        make('/research/transcriptions/', 'Transcriptions'),
        make('/records/', 'Source records'),
        make('/sources/', 'Source notes'),
        make('/free-space/', 'Free-space research'),
      ];
      if (path === '/onetree') return [
        make('/onetree/#view=all', 'All people'),
        make('/onetree/#view=branches', 'Family branches'),
        make('/onetree/#view=dna', 'DNA view'),
      ];
      if (/^\/(catalogue|people|early-records)(\/|$)/.test(path)) return [
        make('/catalogue/', 'People search'),
        make('/catalogue/#catalogue-filters', 'Filters'),
        make('/early-records/', 'Early records'),
      ];
      return [];
    }
    const owned = ownedLinks();
    function owns(url) {
      const target = clean(url.pathname);
      if (root === '/catalogue/') return /^\/(catalogue|people|early-records)(\/|$)/.test(target);
      if (root === '/research/') return /^\/(research|records|sources|free-space|events)(\/|$)/.test(target);
      return target === clean(root);
    }
    if (!source) {
      [...document.querySelectorAll('main h2')].slice(0, 8).forEach((heading, index) => {
        if (!heading.id) heading.id = `section-${index + 1}`;
        const link = document.createElement('a');
        link.href = `${location.pathname}${location.search}#${heading.id}`;
        link.textContent = heading.textContent.replace(/\s+/g, ' ').trim();
        fallback.push(link);
      });
    }
    let signature = '';
    let sourceLinks = [];
    let queued = false;
    function hrefOf(link) {
      const href = link.getAttribute('href') || '';
      return href.startsWith('#') ? `${location.pathname}${location.search}${href}` : link.href;
    }
    function render() {
      queued = false;
      sourceLinks = (owned.length ? owned : source ? [...source.querySelectorAll(timeline
        ? '.g-timeline-period-link' : 'a[href]')] : fallback)
        .filter(link => owns(new URL(hrefOf(link), location.href)));
      const exact = sourceLinks.filter(link => {
        const url = new URL(hrefOf(link), location.href);
        return clean(url.pathname) === path && (!url.hash || url.hash === location.hash);
      });
      const current = exact.find(link => new URL(hrefOf(link), location.href).hash) || exact[0];
      const rows = sourceLinks.map((link, index) => {
        const url = new URL(hrefOf(link), location.href);
        const active = dna || timeline ? link.hasAttribute('aria-current')
          : current ? link === current : link.hasAttribute('aria-current');
        return {index, href: url.href, text: link.textContent.replace(/\s+/g, ' ').trim(), active};
      });
      const next = JSON.stringify(rows);
      if (next === signature) return;
      signature = next;
      const focusIndex = submenu.contains(document.activeElement) ? document.activeElement.dataset.sourceIndex : null;
      const fragment = document.createDocumentFragment();
      rows.forEach(row => {
        const link = document.createElement('a');
        link.href = row.href;
        link.textContent = row.text;
        link.dataset.sourceIndex = row.index;
        if (row.active) link.setAttribute('aria-current', dna ? 'page' : 'location');
        fragment.append(link);
      });
      submenu.replaceChildren(fragment);
      submenu.hidden = !rows.length;
      if (sectionDisclosure) sectionDisclosure.hidden = !rows.length;
      if (focusIndex !== null) submenu.querySelector(`[data-source-index="${focusIndex}"]`)?.focus({preventScroll: true});
    }
    function schedule() {
      if (!queued) { queued = true; requestAnimationFrame(render); }
    }
    submenu.addEventListener('click', event => {
      const link = event.target.closest('a[data-source-index]');
      if (!link || event.button || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      if (dna) {
        event.preventDefault();
        event.stopPropagation();
        sourceLinks[Number(link.dataset.sourceIndex)]?.click();
        schedule();
      }
      if (matchMedia('(max-width:760px)').matches) {
        document.body.classList.remove('g-nav-open');
        document.querySelector('#g-nav-toggle')?.setAttribute('aria-expanded', 'false');
        document.querySelector('#g-nav-toggle')?.focus({preventScroll: true});
      }
    });
    if (source) new MutationObserver(schedule).observe(source, {
      subtree: true, childList: true, characterData: true,
      attributes: true, attributeFilter: ['aria-current', 'class', 'href'],
    });
    addEventListener('hashchange', schedule);
    addEventListener('popstate', schedule);
    render();
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start, {once: true});
  else start();
})();
