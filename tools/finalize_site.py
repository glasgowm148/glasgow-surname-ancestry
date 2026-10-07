"""Shared deterministic presentation finalizer for targeted builds and releases."""
from __future__ import annotations
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))


def finalize(site_root=ROOT/'www'):
    from tools.catalogue_search_index import build as build_search
    from tools.site_payloads import build as build_atlas
    from tools.page_fragments import optimize_page
    from tools.site_assets import deduplicate_assets
    from tools.stamp_asset_versions import stamp
    from tools.catalogue_search_markup import apply_layout, PAGES
    from tools.catalogue_theme import write_catalogue_css
    from tools.repair_person_hierarchy import CSS as person_css
    from tools.site_analytics import with_analytics
    from tools.repair_release_readiness import snapshot, about_dates
    from datetime import date
    from tools.publish_reviewed_collections import publish as publish_collections
    counts=Counter(publish_collections(site_root))
    from tools.build_source_collections import repair as repair_source_collections, ready as source_collections_ready
    if source_collections_ready(site_root):
        counts.update(repair_source_collections(site_root))
    health_path=site_root/'health.json'
    generated=date.fromisoformat(json.loads(health_path.read_text())['generated']) if health_path.exists() else None
    manifest_path=site_root/'data/manifest.json'
    manifest=json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    counts.update(build_search(site_root))
    build_atlas(site_root)
    write_catalogue_css(site_root/'people/catalogue.css')
    (site_root/'assets/repair/person-hierarchy.css').write_text(person_css)
    (site_root/'assets/unified/performance.css').write_text((ROOT/'tools/site_sources/performance/site.css').read_text())
    for relative in PAGES:
        path=site_root/relative
        if not path.exists():continue
        before=path.read_text();after=apply_layout(before)
        if after!=before:path.write_text(after)
    copies={'people/search.js':'catalogue_search.js','people/profile-update.js':'profile_update.js','records/search.js':'record_search.js','assets/research/branches-directory.js':'branches_directory.js','assets/research/core.js':'site_sources/performance/core.js','assets/unified/site-metrics.js':'site_metrics.js'}
    for dest,src in copies.items():
        path=site_root/dest;content=(ROOT/'tools'/src).read_text()
        if not path.exists() or path.read_text()!=content:path.parent.mkdir(parents=True,exist_ok=True);path.write_text(content)
    from tools.site_search import install_search
    counts.update(install_search(site_root))
    # No raw research or per-person private metadata enters this public hash map.
    paths=set()
    for folder in ['data','assets/research','assets/v3']:
        paths.update((site_root/folder).glob('*.json'))
    versions={'/'+p.relative_to(site_root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()[:10] for p in sorted(paths)}
    (site_root/'assets/unified/data-versions.js').write_text('globalThis.GlasgowDataVersions='+json.dumps(versions,separators=(',',':'))+';\n')
    # Work on large maintained dossiers, never recursively on their standalone fallbacks.
    for path in (site_root/'people').glob('*.html'):
        if path.stat().st_size < 100_000:continue
        before=path.read_text();after,stats=optimize_page(before,path.relative_to(site_root),site_root)
        if after!=before:path.write_text(after);counts['fragment_pages']+=1
        counts['fragments']+=stats['extracted']
    for path in site_root.rglob('*.html'):
        before=path.read_text()
        if not re.search(r'<head(?:\s|>)',before,re.I):continue
        after=before
        # Supplied reference editions have exact publication approval; their
        # original presentation is preserved apart from existing cache versions.
        reference = path.relative_to(site_root).parts[0]=='reference'
        if generated and not reference:
            # The family tree page states its own import date (repair_public_dna);
            # the catalogue date must not overwrite it.
            if path.relative_to(site_root).as_posix()!='onetree/index.html':
                after=snapshot(after,generated)
            if path.relative_to(site_root).as_posix()=='about/index.html':
                after=about_dates(after,generated,manifest)
        tree = 'g-kind-tree' in after
        if reference or not tree:
            after=re.sub(r'<link\b[^>]*href="/assets/unified/performance\.css[^>]*>', '', after)
        if reference:
            after=re.sub(r'<script\b[^>]*src="/assets/unified/site-metrics\.js[^>]*>\s*</script>', '', after)
        if not reference and tree and '/assets/unified/performance.css' not in after:
            after=after.replace('</head>','<link rel="stylesheet" href="/assets/unified/performance.css?v=1"></head>',1)
        if 'src="/assets/research/core.js' in after and 'src="/assets/unified/data-versions.js' not in after:
            after=re.sub(r'(<script\b[^>]*src="/assets/research/core\.js[^>]*>)',r'<script src="/assets/unified/data-versions.js?v=1"></script>\1',after,count=1)
        if not reference and 'src="/assets/v3/ui.js' in after and 'src="/assets/unified/site-metrics.js' not in after:
            after=after.replace('</body>','<script src="/assets/unified/site-metrics.js?v=1" defer></script></body>',1)
        after,duplicates=deduplicate_assets(after,base_url='https://glasgow.phenotype.dev/'+path.relative_to(site_root).as_posix())
        after=with_analytics(after)
        counts['duplicate_asset_tags_removed']+=len(duplicates)
        if after!=before:path.write_text(after);counts['asset_pages']+=1
    # Pages written late in a release also get the one site name, breadcrumb and footer.
    if Path(site_root).resolve()==(ROOT/'www').resolve():
        from tools.repair_primary_navigation import repair_site_identity
        counts.update({'identity_'+str(k):v for k,v in repair_site_identity().items()})
    # Dependencies are stamped before their consumers, iterating to a fixed point.
    for _ in range(6):
        _,stale=stamp(site_root,write=True)
        if not stale:break
    if stamp(site_root,write=False)[1]:raise ValueError('Asset versions did not settle')
    write_cache_rules(site_root)
    from tools.site_sitemap import build_sitemap
    counts.update(build_sitemap(site_root))
    return dict(counts)


def write_cache_rules(site_root):
    (site_root/'.htaccess').write_text((ROOT/'tools/site_sources/performance/htaccess.txt').read_text()+'''# Managed public static release caching. Versioned resources are immutable.
<IfModule mod_headers.c>
  Header set Cache-Control "public, max-age=0, must-revalidate"
  <If "%{QUERY_STRING} =~ /(?:^|&)v=[a-f0-9]{10}(?:&|$)/">
    Header set Cache-Control "public, max-age=31536000, immutable"
  </If>
  <FilesMatch "[a-f0-9]{16}\\.(json|html)$">
    Header set Cache-Control "public, max-age=31536000, immutable"
  </FilesMatch>
</IfModule>
''')
    base_headers=(ROOT/'tools/site_sources/performance/headers.txt').read_text().replace('/*\n','/*\n  Cache-Control: public, max-age=0, must-revalidate\n',1)
    (site_root/'_headers').write_text(base_headers+'''/data/catalogue-details/*
  Cache-Control: public, max-age=31536000, immutable
/assets/research/fragments/*
  Cache-Control: public, max-age=31536000, immutable
''')


if __name__=='__main__':print(finalize())
