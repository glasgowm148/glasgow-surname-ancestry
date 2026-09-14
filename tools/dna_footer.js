/* Relocate existing controls without discarding their export event handlers. */
(() => {
  function moveMetadata() {
    const footer = document.querySelector('.g-footer');
    const header = document.querySelector('.g-kind-dna #g-page > .topbar');
    if (!footer || !header) return;
    const controls = header.querySelectorAll('.snapshot, [data-download="json"]');
    if (!controls.length) return;
    const metadata = document.createElement('div');
    metadata.className = 'dna-footer-metadata';
    metadata.style.cssText = 'display:flex;flex-wrap:wrap;align-items:center;gap:12px';
    for (const control of controls) {
      control.classList.remove('desktop-only');
      metadata.append(control);
    }
    footer.append(metadata);
    header.style.display = 'none';
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', moveMetadata, {once: true});
  } else {
    moveMetadata();
  }
})();
