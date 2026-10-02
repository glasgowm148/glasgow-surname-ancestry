#!/usr/bin/env python3
"""Publish clean routes for the catalogue's primary public pages."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB_DIR = ROOT / "www"
SITE_URL = "https://glasgow.phenotype.dev"
REDIRECT_MARKER = "data-clean-route-redirect"
LOCAL_FILE_LINKS = (
    '<script data-local-file-links>if(location.protocol==="file:")addEventListener("DOMContentLoaded",()=>'
    'document.querySelectorAll(\'a[href^="/"]\').forEach(a=>{const h=a.getAttribute("href"),m=h.match(/^([^?#]*)(.*)$/),p=m[1];'
    'a.href=(p==="/"?"index.html":p.endsWith("/")?p.slice(1)+"index.html":/\\.[^/]+$/.test(p)?p.slice(1):p.slice(1)+"/index.html")+m[2]}));</script>'
)

PAGE_ROUTES = {
    "candidate-matches.html": "/candidate-matches",
    "catalogue.html": "/catalogue",
    "changes.html": "/changes",
    "compare.html": "/compare",
    "feedback.html": "/feedback",
    "status.html": "/status",
    "timeline.html": "/timeline",
    "ydna.html": "/ydna",
    "people/early-bearers.html": "/people/early-bearers",
}

INDEX_ROUTES = {
    "index.html": "/",
    "data/index.html": "/data",
    "map/index.html": "/map",
    "places/index.html": "/places",
    "records/index.html": "/records",
}


def _rewrite_routes(text: str) -> str:
    routes = {**PAGE_ROUTES, **INDEX_ROUTES}
    routes.pop("index.html")
    for legacy, clean in routes.items():
        legacy_path = f"/{legacy}"
        text = text.replace(f"{SITE_URL}{legacy_path}", f"{SITE_URL}{clean}")
        text = text.replace(legacy_path, clean)
    text = text.replace(f"{SITE_URL}/index.html", f"{SITE_URL}/")
    text = text.replace('href="/index.html"', 'href="/"')
    return text


def _with_base(text: str, clean: str) -> str:
    depth = len([part for part in clean.strip("/").split("/") if part])
    base = f'<base href="{"../" * depth or "./"}">{LOCAL_FILE_LINKS}'
    if re.search(r"<base\s+href=", text, flags=re.I):
        text = re.sub(r'<base\s+href="[^"]*"\s*/?>', base, text, count=1, flags=re.I)
        if "data-local-file-links" in text[text.index(base) + len(base):]:
            text = re.sub(r'<script\s+data-local-file-links>.*?</script>', "", text, count=1, flags=re.I | re.S)
        return text
    return text.replace("<head>", f"<head>\n  {base}", 1)


def _with_index_redirect(text: str, clean: str) -> str:
    marker = "data-clean-index-redirect"
    script = (
        f'<script {marker}>if(location.protocol!=="file:"&&location.pathname.endsWith("/index.html"))'
        f'location.replace("{clean}"+location.search+location.hash);</script>'
    )
    if marker in text:
        return re.sub(
            rf'<script\b(?=[^>]*\b{marker}(?:\s|=|>))[^>]*>.*?</script>', script, text, count=1, flags=re.I | re.S
        )
    return text.replace("<head>", f"<head>\n  {script}", 1)


def _with_compare_shell(source: str, web_dir: Path) -> str:
    """Keep the freshly generated comparison inside its shared site shell."""
    shell_path = web_dir / "compare" / "advanced.html"
    if not shell_path.exists():
        return source
    shell = shell_path.read_text(encoding="utf-8")
    if 'class="g-nav"' not in shell:
        return source
    main_pattern = re.compile(r"<main\b[^>]*>(.*?)</main>", re.I | re.S)
    main = main_pattern.search(source)
    if not main or not main_pattern.search(shell):
        raise ValueError("Comparison source or shared shell has no main container")

    # Preserve the generator's cautions and links as well as all controls/results.
    footer = re.search(r"<footer\b[^>]*>(.*?)</footer>", source, re.I | re.S)
    notes = (
        '<aside class="compare-panel" aria-label="About this comparison">'
        + footer[1] + '</aside>'
        if footer else ""
    )
    content = '<main id="main" class="r-main v3-compare">' + main[1] + notes + '</main>'
    shell = main_pattern.sub(lambda _: content, shell, count=1)
    shell = re.sub(r'data-g-path="[^"]*"', 'data-g-path="/compare/"', shell, count=1)
    # The catalogue's generic details/button rules must not recolour the rail.
    shell = shell.replace(
        '</head>',
        '<style id="compare-shell-overrides">'
        '.g-rail :is(.g-mobile-more-links,.g-mobile-section-links)'
        '{margin:0;border:0;border-radius:0;background:transparent}'
        '.v3-compare #compare-submit{color:#fff}'
        '</style></head>', 1,
    )
    for pattern in (r"<title>.*?</title>", r'<meta\b[^>]*name="description"[^>]*>'):
        fresh = re.search(pattern, source, re.I | re.S)
        if fresh:
            shell = re.sub(pattern, lambda _: fresh[0], shell, count=1, flags=re.I | re.S)

    # The source owns comparison data/scripts; the template owns shared UI assets.
    for asset in ("people/external-links.js", "data/compare-index.js", "people/compare.js"):
        pattern = rf'<script\b[^>]*src="/?{re.escape(asset)}(?:\?[^\"]*)?"[^>]*>\s*</script>'
        fresh = re.search(pattern, source, re.I)
        if fresh:
            script = fresh[0].replace(f'src="{asset}', f'src="/{asset}')
            shell = re.sub(pattern, lambda _: script, shell, count=1, flags=re.I)

    try:
        from tools.repair_primary_navigation import NAV, render_primary_navigation
    except ImportError:
        from repair_primary_navigation import NAV, render_primary_navigation
    return NAV.sub(lambda _: render_primary_navigation(Path("compare/index.html")), shell)


def publish_clean_urls(web_dir: Path = WEB_DIR) -> None:
    # Standalone research readers inherit a dossier shell, never its redirect.
    for reader in (web_dir / 'people/research-material').glob('*/index.html'):
        original = reader.read_text(encoding='utf-8')
        repaired = re.sub(r'<script\b(?=[^>]*\bdata-clean-index-redirect(?:\s|=|>))[^>]*>.*?</script>', '', original, flags=re.I | re.S)
        if repaired != original:
            reader.write_text(repaired, encoding='utf-8')
    for legacy, clean in PAGE_ROUTES.items():
        source = web_dir / legacy
        if not source.exists():
            continue
        target = web_dir / clean.lstrip("/") / "index.html"
        source_text = source.read_text(encoding="utf-8")
        if REDIRECT_MARKER in source_text:
            continue
        if clean == "/compare":
            source_text = _with_compare_shell(source_text, web_dir)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            _with_index_redirect(_with_base(_rewrite_routes(source_text), clean), clean),
            encoding="utf-8",
        )

    for filename, clean in INDEX_ROUTES.items():
        path = web_dir / filename
        if not path.exists():
            continue
        path.write_text(
            _with_index_redirect(_rewrite_routes(path.read_text(encoding="utf-8")), clean),
            encoding="utf-8",
        )

    for filename in ("sitemap.xml", "llms.txt"):
        path = web_dir / filename
        if path.exists():
            path.write_text(_rewrite_routes(path.read_text(encoding="utf-8")), encoding="utf-8")

    rules = [f"/{legacy}  {clean}  301" for legacy, clean in PAGE_ROUTES.items()]
    rules += [f"/{legacy}  {clean}  301" for legacy, clean in INDEX_ROUTES.items()]
    (web_dir / "_redirects").write_text("\n".join(rules) + "\n", encoding="utf-8")


if __name__ == "__main__":
    publish_clean_urls()
