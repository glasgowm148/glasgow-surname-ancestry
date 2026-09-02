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
            rf'<script\s+{marker}>.*?</script>', script, text, count=1, flags=re.I | re.S
        )
    return text.replace("<head>", f"<head>\n  {script}", 1)


def publish_clean_urls(web_dir: Path = WEB_DIR) -> None:
    for legacy, clean in PAGE_ROUTES.items():
        source = web_dir / legacy
        if not source.exists():
            continue
        target = web_dir / clean.lstrip("/") / "index.html"
        source_text = source.read_text(encoding="utf-8")
        if REDIRECT_MARKER in source_text:
            continue
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
