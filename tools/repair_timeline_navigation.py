#!/usr/bin/env python3
"""Keep the timeline's contextual progress navigation reproducible."""
from collections import Counter
from pathlib import Path
import re
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "www"

NAV = '''<nav aria-label="Timeline progress" class="g-timeline-jumps" data-timeline-progress>
<span class="g-timeline-label">Now viewing <strong data-timeline-current>Deep ancestry</strong></span>
<div class="g-timeline-periods">
<section class="g-timeline-period" data-timeline-period="deep" data-start="R-U106"><a class="g-timeline-period-link" href="#R-U106">Deep ancestry</a><div class="g-timeline-references"><span>Related SNPs</span><a href="#R-U106">R-U106</a></div></section>
<section class="g-timeline-period" data-timeline-period="north-sea" data-start="R-Z17"><a class="g-timeline-period-link" href="#R-Z17">North Sea</a><div class="g-timeline-references"><span>Related SNPs</span><a href="/dna/r-s14827/">R-S14827</a></div></section>
<section class="g-timeline-period" data-timeline-period="medieval" data-start="R-FT4811"><a class="g-timeline-period-link" href="#R-FT4811">Medieval Britain</a><div class="g-timeline-references"><span>Related SNPs</span><a href="/dna/r-ft4811/">R-FT4811</a><a href="/dna/r-ftc49014/">R-FTC49014</a><a href="/dna/r-ft32941/">R-FT32941</a></div></section>
<section class="g-timeline-period" data-timeline-period="glasgow" data-start="R-FT25406"><a class="g-timeline-period-link" href="#R-FT25406">The Glasgow name</a><div class="g-timeline-references"><span>Related SNPs</span><a href="/dna/r-ft25406/">R-FT25406</a><a href="/dna/r-fta30932/">R-FTA30932</a></div></section>
<section class="g-timeline-period" data-timeline-period="ulster" data-start="R-FT20271"><a class="g-timeline-period-link" href="#R-FT20271">Ulster &amp; beyond</a><div class="g-timeline-references"><span>Related SNPs</span><a href="/dna/r-ft20271/">R-FT20271</a><a href="/dna/r-fte32242/">R-FTE32242</a></div></section>
</div><div class="g-timeline-current-references" data-timeline-current-references aria-live="polite"></div></nav>'''

CSS = '''/* Timeline progress navigation: the current historical section keeps its SNP context visible. */
.g-kind-timeline .g-timeline-jumps{display:block;box-sizing:border-box;width:100%;padding:0 clamp(12px,3vw,42px) 10px;overflow:visible;white-space:normal;background:#fdfcf7}.g-kind-timeline .g-timeline-label{display:flex;align-items:baseline;gap:7px;padding:10px 0 6px;font:9px/1.2 var(--g-sans);letter-spacing:1.3px;text-transform:uppercase;color:#7d8d70}.g-kind-timeline .g-timeline-label strong{font:600 12px/1.2 var(--g-serif);letter-spacing:0;text-transform:none;color:#2d5746}.g-kind-timeline .g-timeline-periods{display:flex;align-items:stretch;flex-wrap:wrap;gap:5px;width:100%;min-width:0;overflow:visible;white-space:normal}.g-kind-timeline .g-timeline-period{flex:0 1 auto;min-width:0}.g-kind-timeline .g-timeline-period-link{display:block;padding:8px 12px;border:1px solid #d7e0cf;border-radius:4px;background:#fffefa;font:11px/1.2 var(--g-sans);color:#617855;text-decoration:none;white-space:nowrap}.g-kind-timeline .g-timeline-references{display:none}.g-kind-timeline .g-timeline-period.is-current .g-timeline-period-link{background:#2d5746;border-color:#2d5746;color:#fffdf2;font-weight:600}.g-kind-timeline .g-timeline-current-references{display:flex;align-items:center;flex-wrap:wrap;gap:6px 10px;min-height:31px;margin-top:7px;padding:6px 10px;border:1px solid #cbd9bd;border-radius:4px;background:#f4f8ed;font:10px/1.35 var(--g-sans);white-space:normal}.g-kind-timeline .g-timeline-current-references span{color:#6a7e5e;text-transform:uppercase;letter-spacing:.8px;font-size:9px}.g-kind-timeline .g-timeline-current-references a{color:#315f48;text-decoration:none;border-bottom:1px solid #b6c99f;font-weight:600}.g-kind-timeline .timeline-row{scroll-margin-top:205px}@media(max-width:760px){.g-kind-timeline .g-timeline-jumps{padding:0 12px 8px}.g-kind-timeline .g-timeline-label{padding-top:8px;font-size:8px}.g-kind-timeline .g-timeline-label strong{font-size:10px}.g-kind-timeline .g-timeline-periods{gap:4px}.g-kind-timeline .g-timeline-period{flex:1 1 calc(50% - 2px)}.g-kind-timeline .g-timeline-period-link{padding:8px 7px;font-size:10px;text-align:center;white-space:normal}.g-kind-timeline .g-timeline-current-references{margin-top:5px;padding:6px 8px;gap:5px 9px}.g-kind-timeline .timeline-row{scroll-margin-top:245px}}\n'''

JS = '''(() => {
  const nav = document.querySelector('[data-timeline-progress]');
  if (!nav) return;
  const periods = [...nav.querySelectorAll('[data-timeline-period]')].map(period => ({
    element: period,
    target: document.getElementById(period.dataset.start),
    label: period.querySelector('.g-timeline-period-link').textContent.trim(),
  })).filter(period => period.target);
  const current = nav.querySelector('[data-timeline-current]');
  const currentReferences = nav.querySelector('[data-timeline-current-references]');
  let active = null;
  function select(next) {
    if (!next || next === active) return;
    active = next;
    periods.forEach(period => period.element.classList.toggle('is-current', period === active));
    current.textContent = active.label;
    currentReferences.replaceChildren(...active.element.querySelector('.g-timeline-references').cloneNode(true).childNodes);
    periods.forEach(period => {
      const link = period.element.querySelector('.g-timeline-period-link');
      if (period === active) link.setAttribute('aria-current', 'location');
      else link.removeAttribute('aria-current');
    });
    document.dispatchEvent(new CustomEvent('timeline:sectionchange', {detail:{id:active.target.id}}));
  }
  function offset() {
    const top = parseFloat(getComputedStyle(nav).top) || 0;
    const value = top + nav.getBoundingClientRect().height + 30;
    const rootPadding = parseFloat(getComputedStyle(document.documentElement).scrollPaddingTop) || 0;
    document.documentElement.style.setProperty('--timeline-jump-offset', Math.max(0, value - rootPadding) + 'px');
    return value;
  }
  function update() {
    offset();
    const marker = nav.getBoundingClientRect().bottom + 36;
    let next = periods[0];
    for (const period of periods) {
      if (period.target.getBoundingClientRect().top <= marker) next = period;
      else break;
    }
    select(next);
  }
  function jump(hash, push = false) {
    let target;
    try { target = document.getElementById(decodeURIComponent(hash.slice(1))); } catch (_) { return false; }
    if (!target || !target.matches('.timeline-row, .timeline-snp-anchor')) return false;
    if (target.closest('.deep-hidden')) document.getElementById('deepToggle')?.click();
    let period = periods[0];
    for (const candidate of periods) {
      if (candidate.target === target || (candidate.target.compareDocumentPosition(target) & Node.DOCUMENT_POSITION_FOLLOWING)) period = candidate;
    }
    select(period);
    target.closest('.timeline-row')?.classList.add('visible');
    if (push && location.hash !== hash) history.pushState(null, '', hash);
    window.scrollTo({top:window.scrollY + target.getBoundingClientRect().top - offset(), behavior:'instant'});
    target.setAttribute('tabindex', '-1');
    target.focus({preventScroll:true});
    // Context-row wrapping and browser scroll anchoring can change the nav's
    // height during this frame, especially on mobile. Align once layout settles.
    requestAnimationFrame(() => requestAnimationFrame(() => {
      select(period);
      window.scrollTo({top:window.scrollY + target.getBoundingClientRect().top - offset(), behavior:'instant'});
      update();
    }));
    return true;
  }
  document.addEventListener('click', event => {
    const link = event.target.closest('a[href]');
    if (!link || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    const url = new URL(link.href, location.href);
    if (url.origin !== location.origin || url.pathname !== location.pathname || !url.hash) return;
    if (jump(url.hash, true)) { event.preventDefault(); event.stopImmediatePropagation(); }
  }, true);
  addEventListener('scroll', update, {passive:true});
  addEventListener('resize', update);
  addEventListener('hashchange', () => { jump(location.hash); setTimeout(() => jump(location.hash), 100); });
  new ResizeObserver(update).observe(nav);
  const initial = () => requestAnimationFrame(() => requestAnimationFrame(() => { if (!jump(location.hash)) update(); }));
  // The shared research shell also reveals the initial hash asynchronously.
  // Run after that native jump so browser restoration cannot undo our offset.
  let interacted = false;
  ['pointerdown', 'wheel', 'touchstart', 'keydown'].forEach(type => addEventListener(type, () => { interacted = true; }, {once:true, passive:true}));
  const ready = () => document.fonts.ready.then(() => setTimeout(() => { if (!interacted) initial(); }, 150));
  if (document.readyState === 'complete') ready(); else addEventListener('load', ready, {once:true});
})();\n'''

# Generated pages have appeared with both compact and pretty-printed variants of
# this strip.  Its class is its identity; it must never survive on the Timeline.
SHARED_REFERENCES = re.compile(
    r'<div\\b(?=[^>]*\\bclass=(?:"[^"]*\\br-research-crosslinks\\b[^"]*"|\'[^\']*\\br-research-crosslinks\\b[^\']*\'))[^>]*>.*?</div>',
    re.S | re.I,
)


def update(path, content, changed):
    target = WEB / path
    if not target.exists() or target.read_text(encoding="utf-8") != content:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        changed["timeline_navigation"] += 1


def without_shared_references(page):
    soup = BeautifulSoup(page, 'html.parser')
    for strip in soup.select('.r-research-crosslinks, .v3-view-nav'):
        strip.decompose()
    return str(soup)


def repair():
    changed = Counter()
    page_path = WEB / "timeline/index.html"
    page = page_path.read_text(encoding="utf-8")
    page = without_shared_references(page)
    from repair_timeline_claims import calibrate
    page = calibrate(page)
    for snp in ('s14827', 'ft4811', 'ftc49014', 'ft32941', 'ft25406', 'fta30932', 'ft20271', 'fte32242'):
        page = page.replace('href="/dna/r-' + snp + '/"', 'href="#R-' + snp.upper() + '"')
    page = re.sub(r'<nav\b[^>]*\bclass="[^"]*\bg-timeline-jumps\b[^"]*"[^>]*>.*?</nav>', NAV, page, count=1, flags=re.S)
    for snp in ('s14827', 'ft4811', 'ftc49014', 'ft32941', 'ft25406', 'fta30932', 'ft20271', 'fte32242'):
        page = page.replace('href="/dna/r-' + snp + '/"', 'href="#R-' + snp.upper() + '"')
    page = re.sub(r'<link\b[^>]*href="assets/timeline/timeline-nav\.css[^"<>]*"[^>]*>', '', page)
    page = re.sub(r'<script\b[^>]*src="assets/timeline/timeline-nav\.js[^"<>]*"[^>]*>\s*</script>', '', page)
    assets = '<link rel="stylesheet" href="assets/timeline/timeline-nav.css?v=2"><script defer src="assets/timeline/timeline-nav.js?v=2"></script>'
    if assets not in page:
        page = page.replace('</body>', assets + '</body>')
    if page != page_path.read_text(encoding="utf-8"):
        page_path.write_text(page, encoding="utf-8")
        changed["timeline_navigation"] += 1
    update("assets/timeline/timeline-nav.css", CSS + '\n.g-kind-timeline .timeline-row,.g-kind-timeline .timeline-snp-anchor{scroll-margin-top:var(--timeline-jump-offset,205px);transform:none!important}.timeline-evidence-status{margin:12px 0;padding:10px 12px;border-left:3px solid #809775;background:#f0f4e8;font-size:12px;line-height:1.5}.timeline-evidence-status strong{display:block;color:#35523e}.timeline-document-links{font-size:12px;line-height:1.8}.timeline-document-links a{display:inline-block;margin-right:12px}\n', changed)
    update("assets/timeline/timeline-nav.js", JS, changed)
    return changed


if __name__ == "__main__":
    print(dict(repair()))
