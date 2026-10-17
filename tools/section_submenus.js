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
    // This script can be included from both a page-local and shared asset URL.
    // Keep initialization single so it cannot append duplicate rail navigation.
    if (rail.dataset.sectionSubmenusReady === 'true') return;
    rail.dataset.sectionSubmenusReady = 'true';
    // Keep older generated readers discoverable without a full catalogue rebuild.
    const drawer = rail.closest('.g-rail');
    if (drawer && !drawer.querySelector('a[href="/sitemap/"]')) {
      const link = document.createElement('a');
      link.href = '/sitemap/';
      link.className = 'g-sitemap-link';
      link.textContent = 'Site map';
      const utility = drawer.querySelector('.g-rail-bottom,.repair-quick-links');
      if (utility) utility.prepend(link);
      else rail.after(link);
    }
    const mobileNav = mobileNavigation(rail);
    const primary = [...rail.querySelectorAll(':scope > .g-nav-link')];
    const clean = path => path.replace(/index\.html$/, '').replace(/\/$/, '') || '/';
    const path = clean(location.pathname);
    const roots = [
      [/^\/latest-findings(\/|$)/, '/latest-findings/'],
      [/^\/(sources|records|research\/transcriptions)(\/|$)/, '/sources/'],
      [/^\/(research|sources|records|events|free-space|compare|connections|candidate-matches)(\/|$)/, '/research/'],
      [/^\/(about|evidence|resources|coverage|statistics|data|changes|privacy|feedback|status|sitemap)(\/|$)/, '/about/'],
      [/^\/(branches|places)(\/|$)/, '/branches/'],
      [/^\/(catalogue|people|early-records)(\/|\.|$)/, '/catalogue/'],
      // Timeline is part of the Y-DNA section; Map is part of the Atlas.
      [/^\/(ydna|dna|timeline)(\/|$)/, '/ydna/'],
      [/^\/(onetree|map)(\/|$)/, '/onetree/'],
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
    // Overview and the dated findings index are intentionally single-
    // destination rails; headings must not become a lone fake submenu.
    if (path === '/' || root === '/latest-findings/') return;
    // Other sections expose only destinations they themselves own.
    const dna = path === '/ydna';
    const timeline = path === '/timeline';
    const source = document.querySelector(dna ? '#sidebar .main-nav' : timeline ? '.g-timeline-jumps'
      : path === '/onetree' ? '[aria-label="Atlas views"],[aria-label="Family tree views"]' : '.v3-view-nav');
    // Reuse a first-paint submenu emitted by the shared repair. This keeps
    // cross-page rails stable while deferred JS reconciles active state.
    let submenu = dna ? rail.querySelector('.g-dna-subnav')
      : rail.querySelector(':scope > .g-section-subnav');
    if (!submenu) submenu = document.createElement('div');
    submenu.classList.add('g-section-subnav');
    submenu.setAttribute('role', 'group');
    submenu.setAttribute('aria-label', `${selected.textContent.trim()} sections`);
    const sectionDisclosure = mobileNav?.attach(submenu, selected);
    if (!mobileNav) selected.after(submenu);
    const fallback = [];
    const dnaGroups = [
      {label: 'Y-DNA study', links: [
        ['/ydna/#dna-overview', 'Overview'], ['/ydna/#overview', 'The story'],
        ['/ydna/#origins', 'Origins & routes'], ['/ydna/#mutation-tree', 'DNA tree'],
        ['/ydna/#roots', 'People & matches'],
      ]},
      {label: 'Compare & research', links: [
        ['/ydna/#compare', 'Compare tests'], ['/ydna/#str-network', 'STR patterns'],
        ['/ydna/#snp-splits', 'SNP markers'], ['/ydna/#sapp-model', 'SAPP model'],
        ['/ydna/#next-steps', 'Priorities'], ['/ydna/#sources', 'Sources'],
      ]},
      {label: 'Timeline', href: '/timeline/', links: [
        ['/timeline/#R-U106', 'Deep ancestry'], ['/timeline/#R-Z17', 'North Sea'],
        ['/timeline/#R-FT4811', 'Medieval Britain'], ['/timeline/#R-FT25406', 'The Glasgow name'],
        ['/timeline/#R-FT20271', 'Ulster & beyond'],
      ]},
    ];
    function ownedLinks() {
      const make = (href, text, title = '') => {
        const link = document.createElement('a');
        link.href = href;
        link.textContent = text;
        if (title) link.title = title;
        return link;
      };
      if (root === '/ydna/') return dnaGroups.flatMap(group => group.links.map(([href, text]) => {
        const link = make(href, text);
        link.dataset.sectionGroup = group.label;
        return link;
      }));
      if (path.startsWith('/branches')) return [
        make('/branches/', 'All families'),
        make('/branches/#research-studies', 'Family studies'),
        make('/branches/scottish-families/', 'Scottish families'),
        make('/branches/early-ireland/', 'Irish families'),
      ];
      if (root === '/research/') return [
        make('/research/#open-questions', 'Open questions'),
        make('/connections/', 'Find a relationship'),
        make('/compare/', 'Compare two people'),
        make('/free-space/', 'WikiTree study pages'),
      ];
      if (root === '/sources/') return [
        make('/sources/', 'All source types'),
        make('/sources/newspapers/', 'Newspapers'),
        make('/sources/census/', 'Census'),
        make('/sources/births/', 'Births & baptisms'),
        make('/sources/marriages/', 'Marriages & banns'),
        make('/sources/deaths/', 'Deaths & burials'),
        make('/records/', 'Records by person'),
        make('/research/transcriptions/', 'Wills & transcriptions'),
      ];
      if (root === '/about/') return [
        make('/about/', 'About this project'),
        make('/evidence/', 'How to read the evidence'),
        make('/coverage/', 'About the data'),
        make('/statistics/', 'Statistics'),
        make('/data/', 'Data & downloads'),
        make('/resources/', 'Resources'),
        make('/changes/', 'Change log'),
        make('/privacy/', 'Privacy'),
        make('/feedback/', 'Report a correction'),
      ];
      if (root === '/onetree/') return [
        make('/onetree/#view=all', 'Whole tree'),
        make('/onetree/#view=branches', 'Branch cards'),
        make('/onetree/#view=lanes', 'Timeline'),
        make('/onetree/#view=dna', 'Y-DNA'),
        make('/map/', 'Map'),
      ];
      if (/^\/(catalogue|people|early-records)(\/|$)/.test(path)) return [
        make('/catalogue/', 'People search'),
        make('/catalogue/?missingProfile=1#catalogue-filters', 'No WikiTree link', 'People with no confirmed WikiTree link'),
        make('/catalogue/?needsUpdate=1#catalogue-filters', 'WikiTree updates', 'People whose WikiTree details need updating'),
        make('/catalogue/#research-queue', 'Held & pending research'),
        make('/early-records/', 'Early records'),
      ];
      return [];
    }
    const owned = ownedLinks();
    function owns(url) {
      const target = clean(url.pathname);
      if (root === '/catalogue/') return /^\/(catalogue|people|early-records)(\/|$)/.test(target);
      if (root === '/research/') return /^\/(research|free-space|events|compare|connections|candidate-matches)(\/|$)/.test(target);
      if (root === '/sources/') return /^\/(sources|records|research\/transcriptions)(\/|$)/.test(target);
      if (root === '/about/') return /^\/(about|evidence|resources|coverage|statistics|data|changes|privacy|feedback|status)(\/|$)/.test(target);
      if (root === '/branches/') return /^\/(branches|places)(\/|$)/.test(target);
      if (root === '/onetree/') return /^\/(onetree|map)$/.test(target);
      if (root === '/ydna/') return /^\/(ydna|timeline)$/.test(target);
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
      const queryMatches = (url, target) => {
        if (root === '/onetree/') return true; // View hashes also work with reset/geography parameters.
        if (root !== '/catalogue/') return url.search === target.search;
        const required = new URLSearchParams(url.search);
        const actual = new URLSearchParams(target.search);
        return [...required].every(([key, value]) => actual.getAll(key).includes(value));
      };
      const exact = sourceLinks.filter(link => {
        const url = new URL(hrefOf(link), location.href);
        // The Atlas opens on the Canopy when no view is named in the URL.
        const hash = path === '/onetree' && !location.hash ? '#view=all' : location.hash;
        return clean(url.pathname) === path && queryMatches(url, location)
          && (!url.hash || url.hash === hash);
      });
      const current = (root === '/catalogue/' && exact.find(link => new URL(hrefOf(link), location.href).search))
        || exact.find(link => new URL(hrefOf(link), location.href).hash)
        || exact[0]
        || sourceLinks.find(link => {
          const url = new URL(hrefOf(link), location.href);
          return clean(url.pathname) === path && !url.search && !url.hash && !location.hash;
        });
      const rows = sourceLinks.map((link, index) => {
        const url = new URL(hrefOf(link), location.href);
        const localCurrent = (dna || timeline) && source?.querySelector('a[aria-current]');
        const active = localCurrent ? clean(url.pathname) === path && url.hash === new URL(hrefOf(localCurrent), location.href).hash
          : current ? link === current : link.hasAttribute('aria-current');
        return {index, href: url.href, text: link.textContent.replace(/\s+/g, ' ').trim(), title: link.title,
          group: link.dataset.sectionGroup, active};
      });
      const next = JSON.stringify(rows);
      if (next === signature) return;
      signature = next;
      const focusIndex = submenu.contains(document.activeElement) ? document.activeElement.dataset.sourceIndex : null;
      const fragment = document.createDocumentFragment();
      const groups = new Map();
      rows.forEach(row => {
        let container = fragment;
        if (row.group) {
          if (!groups.has(row.group)) {
            const group = document.createElement('div');
            group.className = 'g-section-group';
            group.setAttribute('role', 'group');
            group.setAttribute('aria-label', row.group);
            const destination = dnaGroups.find(item => item.label === row.group)?.href;
            const heading = document.createElement(destination ? 'a' : 'span');
            heading.className = 'g-section-group-title';
            heading.textContent = row.group;
            if (destination) heading.href = destination;
            group.append(heading);
            groups.set(row.group, group);
            fragment.append(group);
          }
          container = groups.get(row.group);
        }
        const link = document.createElement('a');
        link.href = row.href;
        link.textContent = row.text;
        if (row.title) link.title = row.title;
        link.dataset.sourceIndex = row.index;
        if (row.active) link.setAttribute('aria-current', dna ? 'page' : 'location');
        container.append(link);
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
      const link = event.target.closest('a');
      if (!link || event.button || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      const url = new URL(link.href);
      const localLink = dna && source && clean(url.pathname) === path && [...source.querySelectorAll('a[href]')]
        .find(item => new URL(hrefOf(item), location.href).hash === url.hash);
      if (localLink) {
        event.preventDefault();
        event.stopPropagation();
        localLink.click();
        schedule();
      } else if (url.hash && clean(url.pathname) === path && url.search === location.search) {
        // Keep same-page family-study and catalogue anchors in the current
        // document. Hash navigation supplies native history/back behaviour.
        event.preventDefault();
        event.stopPropagation();
        if (location.hash !== url.hash) location.hash = url.hash;
        else document.getElementById(url.hash.slice(1))?.scrollIntoView({block: 'start'});
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
      attributes: true, attributeFilter: ['aria-current', 'aria-selected', 'class', 'href'],
    });
    addEventListener('hashchange', schedule);
    addEventListener('popstate', schedule);
    addEventListener('catalogue:filters-changed', schedule);
    render();
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start, {once: true});
  else start();
})();
