"""Preserve specialist Map bookmarks after the simplified Map became primary."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / 'www'

SCRIPT = '''(() => {
  const current = new URL(location.href);
  const mainMap = /\\/map(?:\\/(?:index\\.html)?)?$/;
  if (!mainMap.test(current.pathname)) return;
  const specialistPath = current.pathname.replace(mainMap, '/map/advanced.html');
  // Only old specialist controls trigger migration. Shared search/date filters
  // and the current person/branch/group context continue to use the main Map.
  const legacyKeys = [
    'firstName', 'lastName', 'dateFrom', 'dateTo', 'spouse', 'father', 'mother',
    'tableLocation', 'excludeDeath', 'groupClusters', 'groupLocations',
    'locationLevel', 'males', 'missingParents', 'missingLocation',
    'estimatedLocation', 'hasDescendants', 'hasProfile', 'glasgowWives',
    'hasSuffix', 'hideColumns', 'year', 'undated', 'regions', 'scotland',
    'britain', 'ydna', 'earlyBearers', 'generations', 'minDescendants',
    'lines', 'majorRoots', 'unresolved', 'basis', 'movement', 'movementRoot',
    'path', 'rootA', 'rootB', 'evidence', 'precision', 'clusters'
  ];
  const legacyView = ['individuals', 'roots', 'locations'].includes(current.searchParams.get('view'));
  const legacyDisplay = ['table', 'map'].includes(current.searchParams.get('display'));
  if (legacyView || legacyDisplay || legacyKeys.some(key => current.searchParams.has(key))) {
    // Change only the path: repeated parameters, encoding and hash survive.
    current.pathname = specialistPath;
    location.replace(current.href);
    return;
  }

  function updateSpecialistLinks() {
    const target = new URL(location.href);
    target.pathname = specialistPath;
    // Retain all current context; also translate compatible ordinary filters
    // to the specialist interface's older parameter names.
    if (target.searchParams.has('to') && !target.searchParams.has('year')) {
      target.searchParams.set('year', target.searchParams.get('to'));
    }
    const regions = {scotland:'scotland', ireland:'ireland', england:'britain'};
    const region = regions[target.searchParams.get('country')];
    if (region && !target.searchParams.has('regions')) target.searchParams.set('regions', region);
    document.querySelectorAll('a[href]').forEach(link => {
      const href = new URL(link.href, location.href);
      if (href.origin === target.origin && href.pathname === specialistPath) link.href = target.href;
    });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', updateSpecialistLinks, {once:true});
  else updateSpecialistLinks();
  document.addEventListener('glasgow:filters', updateSpecialistLinks);
  document.addEventListener('glasgow:context', updateSpecialistLinks);
  addEventListener('popstate', updateSpecialistLinks);
  addEventListener('hashchange', updateSpecialistLinks);
  // Refresh on pointer/keyboard activation as well as filter changes.
  document.addEventListener('pointerdown', updateSpecialistLinks, true);
  document.addEventListener('click', updateSpecialistLinks, true);
})();
'''


def repair():
    changed = {}
    asset = WEB / 'assets/repair/map-legacy-routes.js'
    if not asset.exists() or asset.read_text(encoding='utf-8') != SCRIPT:
        asset.parent.mkdir(parents=True, exist_ok=True)
        asset.write_text(SCRIPT, encoding='utf-8')
        changed['map_legacy_routes'] = 1
    path = WEB / 'map/index.html'
    original = path.read_text(encoding='utf-8')
    page = re.sub(r'<script\b[^>]*\bsrc=["\'][^"\']*map-legacy-routes\.js[^"\']*["\'][^>]*>\s*</script>', '', original, flags=re.I)
    page = re.sub(r'(<head\b[^>]*>)', r'\1<script src="/assets/repair/map-legacy-routes.js?v=1"></script>', page, count=1, flags=re.I)
    if page != original:
        path.write_text(page, encoding='utf-8')
        changed['map_legacy_routes'] = changed.get('map_legacy_routes', 0) + 1
    return changed


if __name__ == '__main__':
    print(repair())
