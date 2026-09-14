/* Keep the exploration surface primary; retain the original bound controls. */
(() => {
  function start() {
    if (document.body.classList.contains('exploration-atlas')) {
      const toolbar = document.querySelector('.view-toolbar');
      const header = document.querySelector('#app .main > .topbar');
      if (toolbar && header && !document.getElementById('atlas-options')) {
        const options = document.createElement('details');
        options.id = 'atlas-options';
        const summary = document.createElement('summary');
        summary.textContent = 'Filters & tools';
        const panel = document.createElement('div');
        panel.className = 'atlas-options-panel';
        options.append(summary, panel);
        const menu = document.getElementById('menu');
        const search = header.querySelector('.search-wrap');
        if (menu) { menu.setAttribute('aria-label', 'Browse family branches'); toolbar.prepend(menu); }
        if (search) toolbar.prepend(search);
        const list = document.getElementById('v3-atlas-directory-toggle');
        if (list) toolbar.append(list);
        const geography = document.getElementById('geography');
        if (geography) {
          const title = document.createElement('strong');
          title.textContent = 'Highlight a place';
          panel.append(title, geography);
        }
        for (const selector of ['.colour-controls', '.early-tools', '.view-tools']) {
          const element = document.querySelector(selector);
          if (element) panel.append(element);
        }
        const extras = document.createElement('div');
        extras.className = 'atlas-extra-tools';
        header.querySelectorAll('.top-actions > button').forEach(button => extras.append(button));
        panel.append(extras);
        toolbar.append(options);
        header.hidden = true;
        document.querySelector('.v3-atlas-tools')?.setAttribute('hidden', '');
        document.getElementById('repair-testers-toggle')?.addEventListener('click', () => { options.open = false; });
        document.addEventListener('click', event => {
          if (!options.contains(event.target)) options.open = false;
        });
        document.addEventListener('keydown', event => {
          if (event.key === 'Escape' && options.open) { options.open = false; summary.focus(); }
        });
        options.addEventListener('toggle', () => window.dispatchEvent(new Event('resize')));
      }
    }
    if (document.body.classList.contains('exploration-map')) {
      const frame = document.querySelector('.r-map-frame');
      if (frame && !document.getElementById('map-control-strip')) {
        const strip = document.createElement('div');
        strip.id = 'map-control-strip';
        strip.setAttribute('role', 'group');
        strip.setAttribute('aria-label', 'Map zoom and movement');
        for (const selector of ['.r-map-tools', '.map-pan']) {
          const controls = frame.querySelector(selector);
          if (controls) strip.append(controls);
        }
        frame.prepend(strip);
        window.dispatchEvent(new Event('resize'));
      }
    }
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start, {once: true});
  else start();
})();
