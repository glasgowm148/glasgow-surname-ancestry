/* Keep the public Y-DNA section bar and shared sidebar in step. */
(() => {
  const bar = document.querySelector('.ydna-section-bar');
  const links = [...bar.querySelectorAll('.main-nav a')];
  const sections = links.map(link => document.querySelector(link.getAttribute('href')));
  function select(id) {
    links.forEach(link => {
      if (link.hash === `#${id}`) link.setAttribute('aria-current', 'location');
      else link.removeAttribute('aria-current');
    });
  }
  function fromHash() {
    const id = location.hash.slice(1);
    select(sections.some(section => section.id === id) ? id : 'overview');
  }
  let queued = false;
  function syncScroll() {
    queued = false;
    const boundary = bar.getBoundingClientRect().bottom + 24;
    let active = sections[0];
    sections.forEach(section => {
      if (section.getBoundingClientRect().top <= boundary) active = section;
    });
    // A short final section cannot always reach the sticky bar's top edge.
    if (scrollY > 0 && Math.ceil(scrollY + innerHeight) >= document.documentElement.scrollHeight) {
      active = sections.at(-1);
    }
    select(active.id);
  }
  addEventListener('scroll', () => {
    if (!queued) { queued = true; requestAnimationFrame(syncScroll); }
  }, {passive: true});
  addEventListener('hashchange', fromHash);
  new ResizeObserver(() => {
    document.documentElement.style.setProperty('--ydna-nav-height', `${bar.offsetHeight}px`);
  }).observe(bar);
  fromHash();
})();
