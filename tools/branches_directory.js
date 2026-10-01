/* Families & places: priority-study map and in-page search.
 * The page works without this file: every territory is a link and every
 * study and family is listed.  This adds hover/tap popups, list-to-map
 * highlighting, wheel/pinch/button zoom with drag to pan, and a text filter
 * over the static lists.
 */
(() => {
  'use strict';
  if (window.__branchesDirectoryInitialized) return;
  window.__branchesDirectoryInitialized = true;
  const map = document.getElementById('study-map');
  if (map) initMap(map);
  initSearch();

  function initMap(map) {
    const svg = map.querySelector('.bd-svg');
    const popup = map.querySelector('.bd-popup');
    const figure = map.querySelector('.bd-studymap-figure');
    const list = map.querySelector('.bd-priority');
    const zoomControls = map.querySelector('.bd-zoom');
    const shapes = [...map.querySelectorAll('.bd-territory')];
    const items = [...map.querySelectorAll('.bd-priority-item')];
    const areaDetails = [...map.querySelectorAll('.bd-area-details')];
    const wideScreen = matchMedia('(min-width: 901px)');
    let wideLayout;
    let selectedArea = areaDetails[0];
    const fixed = [...svg.querySelectorAll('[data-x]')];
    const regional = map.classList.contains('bd-regional-studymap');
    const regionalBadges = regional ? fixed.filter(g => g.classList.contains('bd-badge-g')) : [];
    const ordinaryFixed = regional ? fixed.filter(g => !g.classList.contains('bd-badge-g')) : fixed;
    const [, , W, H] = svg.getAttribute('viewBox').split(/\s+/).map(Number);
    const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
    const MAX_ZOOM = 10;
    let view = {x: 0, y: 0, w: W, h: H};
    let active = null;
    let touched = false;
    let touchPreview = false;

    const byId = id => ({
      shape: shapes.find(s => s.dataset.territory === id),
      item: items.find(i => i.dataset.territory === id),
    });

    // ---- zoom and pan -------------------------------------------------
    const zoomLevel = () => W / view.w;

    function clamp(v) {
      const w = Math.min(W, Math.max(W / MAX_ZOOM, v.w));
      const h = w * H / W;
      return {w, h, x: Math.min(W - w, Math.max(0, v.x)), y: Math.min(H - h, Math.max(0, v.y))};
    }

    function render() {
      svg.setAttribute('viewBox', `${view.x} ${view.y} ${view.w} ${view.h}`);
      const z = zoomLevel(), s = 1 / z;
      // Markers and labels keep their on-screen size; badge offsets shrink so
      // separated badges move back over their areas as the map zooms in.
      for (const g of ordinaryFixed) {
        const x = +g.dataset.x + (+g.dataset.ox || 0) / z;
        const y = +g.dataset.y + (+g.dataset.oy || 0) / z;
        g.setAttribute('transform', `translate(${x} ${y}) scale(${s})`);
        const leader = g.parentNode.querySelector(':scope > .bd-leader');
        if (leader) { leader.setAttribute('x2', x); leader.setAttribute('y2', y); }
      }
      if (regionalBadges.length) renderRegionalBadges(z);
      svg.classList.toggle('is-zoomed', z > 1.01);
      if (active) place(byId(active).shape);
    }

    function renderRegionalBadges(z) {
      // A map's user units expand with zoom.  This counter-scale makes the
      // 13-unit badge a 13px badge at every responsive width and zoom level.
      const unit = W / Math.max(1, svg.clientWidth) / z;
      const spacing = 32 * unit, step = 8 * unit;
      const svgBox = svg.getBoundingClientRect(), controlsBox = zoomControls.getBoundingClientRect();
      const controls = {left: view.x + (controlsBox.left - svgBox.left) * unit,
        right: view.x + (controlsBox.right - svgBox.left) * unit,
        top: view.y + (controlsBox.top - svgBox.top) * unit,
        bottom: view.y + (controlsBox.bottom - svgBox.top) * unit};
      const placed = [];
      for (const g of regionalBadges) {
        const anchorX = +g.dataset.x, anchorY = +g.dataset.y;
        const pad = 16 * unit;
        const valid = (x, y) => {
          if (z <= 1.01 && (x < pad || x > W - pad || y < pad || y > H - pad)) return false;
          if (x > controls.left - pad && x < controls.right + pad && y > controls.top - pad && y < controls.bottom + pad) return false;
          return placed.every(p => Math.hypot(x - p.x, y - p.y) >= spacing);
        };
        let x = anchorX, y = anchorY, found = false;
        // Test the anchor, then nearest positions in 8px rings.  Unlike a
        // post-layout clamp, every accepted position has already passed both
        // the edge, control and badge-separation checks.
        for (let ring = 0; ring <= 40 && !found; ring++) {
          const radius = ring * step;
          const angles = ring ? 16 : 1;
          for (let i = 0; i < angles; i++) {
            const angle = i * Math.PI * 2 / angles;
            const candidateX = anchorX + Math.cos(angle) * radius;
            const candidateY = anchorY + Math.sin(angle) * radius;
            if (valid(candidateX, candidateY)) {
              x = candidateX;
              y = candidateY;
              found = true;
              break;
            }
          }
        }
        placed.push({x, y});
        g.setAttribute('transform', `translate(${x} ${y}) scale(${unit})`);
        const shape = g.parentNode;
        let leader = shape.querySelector(':scope > .bd-leader');
        if (!leader && Math.hypot(x - anchorX, y - anchorY) > 4) {
          leader = document.createElementNS('http://www.w3.org/2000/svg', 'line');
          leader.setAttribute('class', 'bd-leader');
          shape.insertBefore(leader, g);
        }
        if (leader) {
          leader.setAttribute('x1', anchorX);
          leader.setAttribute('y1', anchorY);
          leader.setAttribute('x2', x);
          leader.setAttribute('y2', y);
        }
      }
    }

    function animateTo(target) {
      target = clamp(target);
      if (reduced) { view = target; render(); return; }
      const start = {...view}, t0 = performance.now();
      const step = now => {
        const n = Math.min(1, (now - t0) / 220), e = 1 - (1 - n) ** 3;
        view = {x: start.x + (target.x - start.x) * e, y: start.y + (target.y - start.y) * e,
                w: start.w + (target.w - start.w) * e, h: start.h + (target.h - start.h) * e};
        render();
        if (n < 1) requestAnimationFrame(step);
      };
      requestAnimationFrame(step);
    }

    // Screen point -> SVG user units in the current view.
    function toSvg(clientX, clientY) {
      const r = svg.getBoundingClientRect();
      return {x: view.x + (clientX - r.left) / r.width * view.w, y: view.y + (clientY - r.top) / r.height * view.h};
    }

    function zoomAt(factor, clientX, clientY, animate = false) {
      const p = toSvg(clientX, clientY);
      const w = view.w / factor, h = view.h / factor;
      const next = {w, h, x: p.x - (p.x - view.x) / factor, y: p.y - (p.y - view.y) / factor};
      if (animate) animateTo(next); else { view = clamp(next); render(); }
    }

    function zoomCentre(factor) {
      const r = svg.getBoundingClientRect();
      zoomAt(factor, r.left + r.width / 2, r.top + r.height / 2, true);
    }

    svg.addEventListener('wheel', e => {
      e.preventDefault();
      const delta = e.deltaMode === 1 ? e.deltaY * 16 : e.deltaY;
      zoomAt(Math.exp(-delta * 0.0022), e.clientX, e.clientY);
    }, {passive: false});

    svg.addEventListener('dblclick', e => { e.preventDefault(); zoomAt(2, e.clientX, e.clientY, true); });

    zoomControls.hidden = false;
    zoomControls.addEventListener('click', e => {
      const button = e.target.closest('button');
      if (!button) return;
      if (button.dataset.zoom === 'in') zoomCentre(1.8);
      else if (button.dataset.zoom === 'out') zoomCentre(1 / 1.8);
      else animateTo({x: 0, y: 0, w: W, h: H});
    });

    // Drag to pan (mouse or one finger when zoomed); two fingers pinch.
    const pointers = new Map();
    let drag = null, pinch = null, dragged = false;
    svg.addEventListener('pointerdown', e => {
      pointers.set(e.pointerId, e);
      dragged = false;
      if (pointers.size === 1) drag = {x: e.clientX, y: e.clientY, view: {...view}};
      if (pointers.size === 2) {
        const [a, b] = [...pointers.values()];
        pinch = {dist: Math.hypot(a.clientX - b.clientX, a.clientY - b.clientY), view: {...view}};
        drag = null;
      }
    });
    svg.addEventListener('pointermove', e => {
      if (!pointers.has(e.pointerId)) return;
      pointers.set(e.pointerId, e);
      const r = svg.getBoundingClientRect();
      if (pinch && pointers.size === 2) {
        const [a, b] = [...pointers.values()];
        const dist = Math.hypot(a.clientX - b.clientX, a.clientY - b.clientY);
        const cx = (a.clientX + b.clientX) / 2, cy = (a.clientY + b.clientY) / 2;
        view = pinch.view;
        zoomAt(dist / pinch.dist, cx, cy);
        dragged = true;
        e.preventDefault();
      } else if (drag) {
        const dx = e.clientX - drag.x, dy = e.clientY - drag.y;
        if (!dragged && Math.hypot(dx, dy) < 5) return;
        if (zoomLevel() <= 1.01 && e.pointerType === 'touch') return; // let the page scroll
        dragged = true;
        svg.classList.add('is-dragging');
        view = clamp({...drag.view, x: drag.view.x - dx / r.width * view.w, y: drag.view.y - dy / r.height * view.h});
        render();
      }
    });
    const release = e => {
      pointers.delete(e.pointerId);
      if (e.type === 'pointercancel') { touched = false; touchPreview = false; }
      if (pointers.size < 2) pinch = null;
      if (!pointers.size) { drag = null; svg.classList.remove('is-dragging'); }
    };
    svg.addEventListener('pointerup', release);
    svg.addEventListener('pointercancel', release);
    // A drag must not also follow the territory link it started on.
    svg.addEventListener('click', e => { if (dragged) { e.preventDefault(); e.stopPropagation(); dragged = false; touched = false; touchPreview = false; } }, true);

    // ---- highlight and popup -----------------------------------------
    // A compact tooltip beside the badge; it ignores the pointer, so it never
    // blocks a neighbouring area.  Links live in the ranked list.
    function place(shape) {
      const badge = shape.querySelector('.bd-badge').getBoundingClientRect();
      const box = figure.getBoundingClientRect();
      const cx = badge.left + badge.width / 2 - box.left, cy = badge.top + badge.height / 2 - box.top;
      const w = popup.offsetWidth, h = popup.offsetHeight;
      const left = cx + 22 + w > box.width - 8 ? cx - 22 - w : cx + 22;
      popup.style.left = `${Math.max(8, left)}px`;
      popup.style.top = `${Math.min(Math.max(8, cy - h / 2), box.height - h - 8)}px`;
    }

    // Scroll only the list's own box, never the page.
    function reveal(item) {
      const top = item.offsetTop - list.offsetTop, bottom = top + item.offsetHeight;
      if (top < list.scrollTop) list.scrollTo({top, behavior: reduced ? 'auto' : 'smooth'});
      else if (bottom > list.scrollTop + list.clientHeight) list.scrollTo({top: bottom - list.clientHeight, behavior: reduced ? 'auto' : 'smooth'});
    }

    function show(id, {fromMap = false} = {}) {
      const {shape, item} = byId(id);
      if (!shape || !item) return;
      if (fromMap) {
        const details = item.querySelector('.bd-area-details');
        if (details) {
          selectedArea = details;
          if (!wideScreen.matches) for (const other of areaDetails) other.open = other === details;
          details.open = true;
        }
      }
      if (active === id) return;
      hide();
      active = id;
      shape.classList.add('is-active');
      item.classList.add('is-active');
      shape.parentNode.appendChild(shape); // draw the active area on top
      const title = document.createElement('strong');
      // A selector list returns the first DOM match, not the first selector:
      // h3 wraps the name, rank and count on regional pages.
      title.textContent = (item.querySelector('.bd-area-name') || item.querySelector('h3')).textContent.trim();
      const count = item.querySelector('.bd-area-heading small');
      const people = document.createElement('p');
      people.className = 'bd-popup-people';
      people.textContent = count?.textContent.trim() || '';
      const why = document.createElement('p');
      why.textContent = item.querySelector('p').textContent;
      const studies = document.createElement('ul');
      for (const a of item.querySelectorAll('.bd-priority-studies a')) {
        const li = document.createElement('li');
        li.textContent = a.textContent;
        studies.append(li);
      }
      const hint = document.createElement('em');
      hint.textContent = touched ? 'Tap again to open the leading study' : 'Click to open the leading study';
      popup.replaceChildren(title, ...(count ? [people] : []), why, studies, hint);
      popup.hidden = false;
      place(shape);
      if (fromMap) reveal(item);
    }

    function hide() {
      if (!active) return;
      const {shape, item} = byId(active);
      shape?.classList.remove('is-active');
      item?.classList.remove('is-active');
      popup.hidden = true;
      active = null;
    }

    // A stationary click on the map background dismisses a preview. Keep
    // area links, controls, popups and drag gestures on their existing paths.
    figure.addEventListener('click', e => {
      if (e.defaultPrevented || dragged || e.target.closest('.bd-territory,button,a,.bd-popup')) return;
      hide();
      touched = false;
      touchPreview = false;
    });

    for (const shape of shapes) {
      const id = shape.dataset.territory;
      shape.addEventListener('pointerenter', e => { if (e.pointerType !== 'touch' && !svg.classList.contains('is-dragging')) show(id, {fromMap: true}); });
      shape.addEventListener('focus', () => show(id, {fromMap: true}));
      shape.addEventListener('pointerdown', e => {
        touched = e.pointerType === 'touch';
        // Focus can preview the area before click fires. Remember whether
        // this tap started on an area that was already selected.
        touchPreview = touched && active !== id;
      });
      // On touch screens the first tap previews the area; a second tap opens it.
      shape.addEventListener('click', e => {
        if (touched && touchPreview) { e.preventDefault(); show(id, {fromMap: true}); }
        touched = false;
        touchPreview = false;
      });
    }
    for (const item of items) {
      const id = item.dataset.territory;
      item.addEventListener('pointerenter', e => { if (e.pointerType !== 'touch') show(id); });
      item.addEventListener('focusin', () => show(id));
    }
    for (const details of areaDetails) {
      details.addEventListener('toggle', () => {
        if (details.open && !wideScreen.matches) {
          selectedArea = details;
          for (const other of areaDetails) if (other !== details) other.open = false;
        }
      });
    }
    figure.addEventListener('pointerleave', e => { if (e.pointerType !== 'touch') hide(); });
    list.addEventListener('pointerleave', e => { if (e.pointerType !== 'touch') hide(); });
    document.addEventListener('pointerdown', e => { if (!map.contains(e.target)) hide(); });
    document.addEventListener('keydown', e => {
      if (e.key === 'Escape') hide();
      if (!figure.contains(document.activeElement)) return;
      if (e.key === '+' || e.key === '=') zoomCentre(1.8);
      if (e.key === '-') zoomCentre(1 / 1.8);
    });

    // Keep the list exactly as tall as the map so hovering never moves the page.
    const sync = () => {
      const wide = wideScreen.matches;
      if (wide !== wideLayout) {
        wideLayout = wide;
        const selected = items.find(item => item.dataset.territory === active)?.querySelector('.bd-area-details') || selectedArea;
        for (const details of areaDetails) details.open = wide || details === selected;
      }
      list.style.maxHeight = wide ? `${figure.offsetHeight}px` : '';
      render();
      if (active) place(byId(active).shape);
    };
    new ResizeObserver(sync).observe(figure);
    sync();
    svg.classList.add('is-enhanced');
  }

  // Text filter over the static study cards, priority list and family lists.
  function initSearch() {
    const find = document.getElementById('bd-find');
    const input = document.getElementById('bd-q');
    const count = document.getElementById('bd-count');
    if (!find || !input) return;
    find.hidden = false;
    const norm = s => s.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
    const rows = [...document.querySelectorAll('.bd-card, .bd-priority-item, #connected-families li')]
      .map(el => ({el, text: norm(el.textContent)}));
    const details = [...document.querySelectorAll('#connected-families details')];
    const initial = new URLSearchParams(location.search).get('q');
    if (initial) input.value = initial;

    function apply() {
      const terms = norm(input.value).split(/\s+/).filter(Boolean);
      let shown = 0;
      for (const row of rows) {
        const match = terms.every(t => row.text.includes(t));
        row.el.hidden = !match;
        if (match && !row.el.matches('.bd-priority-item')) shown++;
      }
      for (const d of details) {
        const any = [...d.querySelectorAll('li')].some(li => !li.hidden);
        d.hidden = !any;
        if (terms.length) d.open = any;
      }
      document.querySelectorAll('#research-studies, #irish-research-studies').forEach(section => {
        section.hidden = terms.length > 0 && !section.querySelector('.bd-card:not([hidden])');
      });
      count.textContent = terms.length ? `${shown} ${shown === 1 ? 'study or family matches' : 'studies and families match'}` : '';
      const url = new URL(location.href);
      if (terms.length) url.searchParams.set('q', input.value.trim()); else url.searchParams.delete('q');
      history.replaceState(null, '', url);
    }
    input.addEventListener('input', apply);
    if (initial) apply();
  }
})();
