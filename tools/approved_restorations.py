"""Preserve the previous research publications explicitly restored by the owner."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re

try:
    from tools.site_analytics import with_analytics, without_analytics
    from tools.site_html import read_html
    from tools.site_payloads import unpack_model
except ModuleNotFoundError:
    from site_analytics import with_analytics, without_analytics
    from site_html import read_html
    from site_payloads import unpack_model

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / 'data/private/withheld-public-assets'
MANIFEST = ROOT / 'research/publication-restoration-approval.json'


def entries(private=PRIVATE):
    if private.resolve() != PRIVATE.resolve() or not MANIFEST.exists():
        return {}
    data = json.loads(MANIFEST.read_text())
    if data.get('schema_version') != 1 or data.get('scope') != 'previous-public-research-restoration':
        raise ValueError('Invalid research restoration approval')
    return {entry['path']: entry for entry in data['publications']}


def source(entry):
    path = (ROOT / entry['source']).resolve()
    if not path.is_relative_to(ROOT / 'data/private'):
        raise ValueError('Restoration source must be a retained private original')
    content = path.read_bytes()
    if hashlib.sha256(content).hexdigest() != entry['sha256']:
        raise ValueError('Approved restoration source changed: ' + entry['path'])
    return content.decode('utf-8')


def model_script(page):
    match = re.search(r'<script\b[^>]*id="tree-data"[^>]*>(.*?)</script>', page, re.S)
    return match if match and match[1] != '__MODEL__' else None


def normalise(page):
    page = re.sub(r'(<head\b[^>]*>)\s*', r'\1', without_analytics(page))
    return re.sub(r'\?v=[a-zA-Z0-9._-]+', '?v=VERSION', page).strip()


def reference_html(page):
    # The supplied pages moved into /reference/; their shared icon lives at root.
    page = re.sub(r'(href=["\'])(?:\.\./)*assets/favicon\.svg(["\'])',
                  r'\1/assets/favicon.svg\2', page)
    return with_analytics(page)


def usable_tester_panel(page):
    page = page.replace('THE COMPLETE CANOPY', 'THE WHOLE TREE')
    if 'function show(open)' not in page:
        return page
    return page.replace("requestAnimationFrame(()=>window.dispatchEvent(new Event('resize')))",
        "requestAnimationFrame(()=>{window.dispatchEvent(new Event('resize'));if(innerWidth<900){const target=open?panel:(toggle.closest('details')||toggle);target.style.scrollMarginTop='76px';target.scrollIntoView({block:'start'});}})")


def documentary_renderer(page):
    """Allow named documentary ancestors while preserving the supplied UI."""
    page = page.replace('Selected uncertain working father.</b>',
                        "Selected uncertain working ${esc(r.role||'parent')}.</b>")
    replacements = {
        "const wiki=id=>'https://www.wikitree.com/wiki/'+encodeURIComponent(id);":
        "const wiki=id=>{const p=D.people.find(p=>p.id===id);return p?.wikitreeUrl||p?.recordUrl||'https://www.wikitree.com/wiki/'+encodeURIComponent(id)};",
        "const catalogue=p=>p.catalogueId===null?": "const catalogue=p=>p.catalogueUrl|| (p.catalogueId===null?",
        "encodeURIComponent(p.catalogueId||p.id.toLowerCase())+'.html';": "encodeURIComponent(p.catalogueId||p.id.toLowerCase())+'.html');",
        "const life=p=>{const b=yearText(p,'born')": "const life=p=>{if(p.documentary)return 'Recorded '+p.recordPeriod;if(p.lifeLabel)return p.lifeLabel;const b=yearText(p,'born')",
        "title=\"Copy WikiTree ID\" aria-label=\"Copy WikiTree ID\"": "title=\"Copy person ID\" aria-label=\"Copy person ID\"",
        "const rows=[['WikiTree ID','Name'": "const rows=[['Person ID','Name'",
        "linked descendants through recorded parent relationships.": "linked descendants through parent relationships, including selected uncertain links.",
        "'Recorded ancestry route'": "'Ancestry route · uncertain links labelled'",
        "p.parents.map(relationHTML).join('')": "p.parents.map(r=>relationHTML(r)+(r.hypothesis?`<p><b>Selected uncertain working ${esc(r.role||'parent')}.</b> ${esc(r.reason||'')} ${(r.analysis_links||[]).map(a=>`<a href=\"${esc(a.href)}\">${esc(a.label)}</a>`).join(' · ')}</p>`:'')).join('')",
    }
    # The helper replacement is atomic; subsequent calls preserve identical JS.
    if "const catalogue=p=>p.catalogueUrl|| (" in page:
        return page
    for old, new in replacements.items():
        page = page.replace(old, new)
    page = page.replace("Selected uncertain working ${esc(r.role||'parent')}.</b>",
                        "Selected ${r.status==='probable'?'probable':'uncertain'} working ${esc(r.role||'parent')}.</b>")
    page = page.replace("Selected ${r.status==='probable'?'probable':'uncertain'} working father.</b>",
                        "Selected ${r.status==='probable'?'probable':'uncertain'} working ${esc(r.role||'parent')}.</b>")
    page = page.replace('>WikiTree ${icon(\'out\')}</a>',
                        ">${p.documentary&&!p.wikitreeUrl?'Source account':'WikiTree'} ${icon('out')}</a>")
    return page


def approved_document(relative, content, private=PRIVATE):
    if relative == 'assets/research/atlas-model-packed.json':
        try:
            return approved_document('assets/research/atlas-model.json', json.dumps(unpack_model(json.loads(content))), private)
        except (ValueError, KeyError, TypeError, IndexError):
            return False
    if relative.startswith(('assets/research/fragments/', 'people/research-material/')):
        # A moved fragment inherits only its explicitly approved dossier's scope.
        # The approved parent must actually link to this immutable public output.
        target=ROOT/'www'/relative
        if not target.exists() or target.read_text()!=content:return False
        for parent, item in entries(private).items():
            if item['kind'] != 'dossier':continue
            path=ROOT/'www'/parent
            if not path.exists():continue
            page=path.read_text()
            if '/'+relative not in page:continue
            if approved_document(parent, read_html(path), private):return True
        return False
    entry = entries(private).get(relative)
    if entry is None:
        return False
    if entry['kind'] == 'dossier':
        if 'data-r-fragment=' in content:
            content=read_html(ROOT/'www'/relative)
        return ('id="paternal-dna"' in content
                and all(path in content for path in ('glasgow-951-dna-matrix.json', 'glasgow-951-dna-matrix.csv'))
                and 'awaiting publication permission' not in content)
    original = source(entry)
    try:
        if entry['kind'] == 'exact':
            return json.loads(content) == json.loads(original) if relative.endswith('.json') else content.replace('\r\n', '\n') == original.replace('\r\n', '\n')
        if entry['kind'] == 'reference':
            return normalise(content) == normalise(reference_html(original))
        if entry['kind'] == 'atlas-model':
            actual, previous = json.loads(content), json.loads(original)
            return (actual.get('dna') == previous['dna']
                    and set(previous.get('landmarks', [])).issubset(actual.get('landmarks', [])))
        if entry['kind'] == 'atlas-renderer':
            if relative.endswith('.js'):
                return normalise(content) == normalise(documentary_renderer(usable_tester_panel(original)))
            old_model, new_model = model_script(original), model_script(content)
            if old_model and (not new_model or json.loads(old_model[1])['dna'] != json.loads(new_model[1]).get('dna')):
                return False
            # Research functions and controls remain the supplied implementation;
            # the shared shell, cache URLs and filtered genealogy model can evolve.
            for token in ('id="dna-toggle"', 'id="dna-total"', 'id="repair-tester-panel"',
                          'repair-dna-legend', 'function dnaCallout(d)', 'function dnaBadge(d)'):
                if token in original and token not in content:
                    return False
            pattern = r'function renderDNA\(\)\{.*?(?=\n(?:/\*.*?\*/\s*)?let searchItems=)'
            old = re.search(pattern, original, re.S)
            new = re.search(pattern, content, re.S)
            return not old or bool(new and new[0] == old[0])
    except (ValueError, KeyError):
        return False
    return False


def restored_model(current, original):
    current['dna'] = original['dna']
    current['landmarks'] = list(dict.fromkeys(original.get('landmarks', []) + current.get('landmarks', [])))
    current.setdefault('meta', {})['dnaCoverage'] = original['meta']['dnaCoverage']
    return current


def cache_urls(page):
    """Keep later content-hash URLs when restoring original research markup."""
    return dict(re.findall(r'([/A-Za-z0-9_.-]+\.(?:js|css))\?v=([A-Za-z0-9._-]+)', page))


def restore_atlas(web, private=PRIVATE):
    approved = entries(private)
    if not approved:
        return None
    models = renderers = assets = 0
    for relative, entry in approved.items():
        if entry['kind'] not in {'atlas-model', 'atlas-renderer', 'exact'}:
            continue
        target = web / relative
        original = source(entry)
        if entry['kind'] == 'exact':
            raw = (ROOT / entry['source']).read_bytes()
            if not target.exists() or target.read_bytes() != raw:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(raw)
                assets += 1
            continue
        rendered = documentary_renderer(usable_tester_panel(original)) if entry['kind'] == 'atlas-renderer' and relative.endswith('.js') else usable_tester_panel(original)
        if entry['kind'] == 'atlas-model':
            current = json.loads(target.read_text()) if target.exists() else json.loads(original)
            rendered = json.dumps(restored_model(current, json.loads(original)), ensure_ascii=False, separators=(',', ':')) + '\n'
        elif entry['kind'] == 'atlas-renderer' and relative.endswith('.html'):
            try:
                from tools.repair_public_dna import _inject_public_dna_summary_css
            except ModuleNotFoundError:
                from repair_public_dna import _inject_public_dna_summary_css
            rendered = _inject_public_dna_summary_css(rendered)
            old_model = model_script(original)
            current_model = model_script(target.read_text()) if target.exists() else None
            if old_model and current_model:
                model = restored_model(json.loads(current_model[1]), json.loads(old_model[1]))
                payload = json.dumps(model, ensure_ascii=False, separators=(',', ':')).replace('<', r'\u003c')
                rendered = rendered.replace(old_model[1], payload, 1)
            # Retain the current shared head and navigation on the interactive
            # public page; restored DNA controls live inside its original app.
            if relative == 'onetree/index.html' and target.exists():
                current = target.read_text()
                for pattern in (r'<head\b.*?</head>', r'<aside\b[^>]*class="[^"]*g-rail[^"]*".*?</aside>',
                                r'<div class="g-bar">.*?(?=<div class="g-page")'):
                    previous = re.search(pattern, current, re.S)
                    if previous:
                        rendered = re.sub(pattern, lambda _: previous[0], rendered, count=1, flags=re.S)
            # Loaded tree templates can otherwise reintroduce old visible labels.
            if entry['kind'] == 'atlas-renderer':
                try:
                    from tools.repair_primary_navigation import reorder_atlas_views
                except ModuleNotFoundError:
                    from repair_primary_navigation import reorder_atlas_views
                rendered = reorder_atlas_views(rendered)
        if entry['kind'] == 'atlas-renderer' and target.exists():
            current = target.read_text()
            urls = cache_urls(current)
            rendered = re.sub(r'([/A-Za-z0-9_.-]+\.(?:js|css))\?v=([A-Za-z0-9._-]+)',
                              lambda m: m[1] + '?v=' + urls.get(m[1], m[2]), rendered)
            if '<head' in rendered:
                rendered = with_analytics(rendered)
        if not target.exists() or target.read_text() != rendered:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(rendered)
            if entry['kind'] == 'atlas-model': models += 1
            elif entry['kind'] == 'atlas-renderer': renderers += 1
            else: assets += 1
    boot = web / 'assets/research/atlas-boot.js'
    if boot.exists():
        before = boot.read_text()
        after = before.replace("fetch('/assets/research/atlas-model.json')",
                               "fetch('/assets/research/atlas-model.json',{cache:'no-cache'})")
        if after != before:
            boot.write_text(after)
    return models, renderers, assets


def audit(web, private=PRIVATE):
    failures = []
    for relative in entries(private):
        path = web / relative
        if not path.exists() or not approved_document(relative, path.read_text(), private):
            failures.append('Approved research restoration missing or changed: ' + relative)
    return failures
