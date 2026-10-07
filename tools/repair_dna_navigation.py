#!/usr/bin/env python3
"""Keep the DNA overview inside the single Y-DNA application.

The first run preserves the former /dna/ main content as a local repair source,
then presents it as the ``dna-overview`` view in /ydna/.  Subsequent repair
runs use that source, so the legacy URL can remain a redirect without losing
the maintained overview content.
"""

from pathlib import Path
import re

try:
    from tools.site_identity import page_title
except ModuleNotFoundError:
    from site_identity import page_title


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "www"
SOURCE = ROOT / "tools" / "dna_overview_source.html"


def update(path: Path, text: str, changed: dict[str, int]) -> None:
    if not path.exists() or path.read_text(encoding="utf-8") != text:
        path.write_text(text, encoding="utf-8")
        changed["dna_navigation"] = changed.get("dna_navigation", 0) + 1


def overview_source(changed: dict[str, int]) -> str:
    if SOURCE.exists():
        return SOURCE.read_text(encoding="utf-8")
    legacy = (WEB / "dna" / "index.html").read_text(encoding="utf-8")
    match = re.search(r"<main class=\"r-main[^>]*>.*?</main>", legacy, re.S)
    if not match:
        raise RuntimeError("Could not recover the existing DNA overview main content")
    source = match.group(0)
    SOURCE.write_text(source, encoding="utf-8")
    changed["dna_navigation"] = changed.get("dna_navigation", 0) + 1
    return source


def overview_view(source: str) -> str:
    view = re.sub(
        r"^<main class=\"r-main[^\"]*\" id=\"main\">",
        '<section class="view dna-overview-view" id="dna-overview" aria-labelledby="dna-overview-title">',
        source,
        count=1,
    )
    view = re.sub(r"</main>$", "</section>", view, count=1)
    view = view.replace('<h1>Three ways of reading the same line.</h1>', '<h1 id="dna-overview-title">Three ways of reading the same line.</h1>')
    view = view.replace('href="/ydna/">Open the complete Y-DNA explorer', 'href="#overview">Open the Y-DNA explorer')
    view = view.replace('href="/timeline/">Read the historical timeline', 'href="/timeline/">Read the historical timeline')
    return view


def branch_pages(web: Path = WEB) -> list[tuple[str, str, str]]:
    """(href, haplogroup, name) for each Y-DNA branch page under /dna/r-*/."""
    pages = []
    for path in sorted((web / "dna").glob("r-*/index.html")):
        title = re.search(r"<title>(.*?)</title>", path.read_text(encoding="utf-8"), re.S)
        parts = [part.strip() for part in re.split(r"\s+·\s+", title[1])] if title else []
        code = parts[0] if parts else path.parent.name.upper()
        name = parts[1] if len(parts) > 2 else ""
        pages.append((f"/dna/{path.parent.name}/", code, name))
    return pages


def with_branch_pages(view: str, web: Path = WEB) -> str:
    """Link every Y-DNA branch page from the overview (site audit S1-07)."""
    pages = branch_pages(web)
    if not pages:
        return view
    items = "".join(
        f'<li><a href="{href}"><strong>{code}</strong>{" · " + name if name else ""}</a></li>'
        for href, code, name in pages)
    block = ('<section class="dna-branch-pages" id="dna-branch-pages" aria-labelledby="dna-branch-pages-title">'
             '<h2 id="dna-branch-pages-title">Y-DNA branch pages</h2>'
             '<p>One page for each named branch of the Glasgow Y-DNA tree. A shared branch shows a common paternal '
             'line; it does not by itself name the ancestor who links two families.</p>'
             f'<ul>{items}</ul></section>')
    if not view.endswith("</section>"):
        return view + block
    return view[: -len("</section>")] + block + "</section>"


def legacy_redirect() -> str:
    return """<!doctype html>
<html lang=\"en\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">
<title>{title}</title><link rel=\"canonical\" href=\"/ydna/\">
<meta http-equiv=\"refresh\" content=\"0;url=/ydna/\"><script>location.replace('/ydna/'+location.search+location.hash)</script></head>
<body><p>The DNA overview is now part of the <a href=\"/ydna/\">Y-DNA explorer</a>.</p></body></html>
""".replace("{title}", page_title("DNA overview moved"))


def remove_overview_views(html: str) -> str:
    """Remove only generated overview sections, including nested sections."""
    pattern = r'<section\b[^>]*\bid="dna-overview"[^>]*>'
    while match := re.search(pattern, html):
        depth = 1
        for tag in re.finditer(r'</?section\b[^>]*>', html[match.end():]):
            depth += -1 if tag.group().startswith('</') else 1
            if depth == 0:
                end = match.end() + tag.end()
                html = html[:match.start()] + html[end:]
                break
        else:
            raise RuntimeError('Unclosed DNA overview section; refusing to discard content')
    return html


def repair() -> dict[str, int]:
    changed: dict[str, int] = {}
    source = overview_source(changed)
    view = with_branch_pages(overview_view(source))
    ydna_path = WEB / "ydna" / "index.html"
    ydna = ydna_path.read_text(encoding="utf-8")
    ydna = remove_overview_views(ydna)
    ydna = ydna.replace(
        "const h=(hash||'overview').replace(/^#/,'');",
        "const h=(hash||'dna-overview').replace(/^#/,'');",
        1,
    )
    nav_pattern = r'<nav aria-label="(?:Y-DNA navigation|Explorer sections)" class="main-nav">.*?</nav>'
    if not re.search(nav_pattern, ydna, re.S):
        raise RuntimeError("Could not find Y-DNA navigation")
    views = (
        ('dna-overview', 'Overview'), ('overview', 'The story'),
        ('origins', 'Origins &amp; routes'), ('mutation-tree', 'DNA tree'),
        ('roots', 'People &amp; matches'), ('compare', 'Compare tests'),
        ('str-network', 'STR patterns'), ('snp-splits', 'SNP markers'),
        ('sapp-model', 'SAPP model'), ('next-steps', 'Priorities'),
        ('sources', 'Sources'),
    )
    nav = '<nav aria-label="Y-DNA navigation" class="main-nav">'
    for name, label in views:
        current = ' aria-current="page"' if name == 'dna-overview' else ''
        nav += f'<a{current} data-view="{name}" href="#{name}">{label}</a>'
    nav += '</nav>'
    ydna = re.sub(nav_pattern, lambda _: nav, ydna, count=1, flags=re.S)
    ydna = re.sub(r'<div class="g-dna-subnav" role="group" aria-label="Y-DNA sections">.*?</div>', '', ydna, flags=re.S)
    submenu = '<div class="g-dna-subnav" role="group" aria-label="Y-DNA sections">'
    for name, label in views:
        current = ' aria-current="page"' if name == 'dna-overview' else ''
        submenu += f'<a{current} data-view="{name}" href="#{name}">{label}</a>'
    submenu += '</div>'
    rail_link = r'(<a\b(?=[^>]*class="[^"]*g-nav-link")(?=[^>]*href="/ydna/")(?=[^>]*aria-current="page")[^>]*>.*?</a>)'
    if not re.search(rail_link, ydna, re.S):
        raise RuntimeError('Could not find selected Y-DNA item in archive navigation')
    ydna = re.sub(rail_link, lambda match: match.group(1) + submenu, ydna, count=1, flags=re.S)
    ydna = re.sub(r'<div\b[^>]*class="[^"]*\br-research-crosslinks\b[^"]*"[^>]*>.*?</div>', '', ydna, flags=re.S)
    ydna = re.sub(r'<nav\b[^>]*class="[^"]*\bv3-view-nav\b[^"]*"[^>]*>.*?</nav>', '', ydna, flags=re.S)
    if '</main>' not in ydna:
        raise RuntimeError('Could not find the Y-DNA main content boundary')
    ydna = ydna.replace('</main>', view + '</main>', 1)
    style = '''<style id="dna-single-navigation">
.v3-site.g-kind-dna #sidebar .main-nav{flex-wrap:wrap;overflow:visible;white-space:normal;gap:3px;padding:6px 0}
.v3-site.g-kind-dna #sidebar .main-nav a{min-height:38px;padding:8px 10px;font-size:11px}
.v3-site.g-kind-dna .chapter-jumps{position:static}
.v3-site.g-kind-dna .g-dna-subnav{display:grid;gap:2px;margin:-1px 0 7px 15px;padding:6px 0 6px 11px;border-left:2px solid #77906b}
.v3-site.g-kind-dna .g-dna-subnav a{color:#bcd0b1;text-decoration:none;font-size:11px;line-height:1.3;padding:5px 7px;border-radius:4px}
.v3-site.g-kind-dna .g-dna-subnav a:hover{background:#355143;color:#fff}
.v3-site.g-kind-dna .g-dna-subnav a[aria-current="page"]{background:#59734f;color:#fff;font-weight:700}
body.g-nav-collapsed .g-dna-subnav{display:none}
@media(max-width:640px){.v3-site.g-kind-dna #sidebar .main-nav{display:grid;grid-template-columns:repeat(3,minmax(0,1fr))}.v3-site.g-kind-dna #sidebar .main-nav a{justify-content:center;text-align:center;padding:5px;font-size:10px;min-height:32px}}
</style>'''
    ydna = re.sub(r'<style id="dna-single-navigation">.*?</style>', '', ydna, flags=re.S)
    ydna = ydna.replace('</head>', style + '</head>', 1)
    if 'src="/assets/v3/dna.js?v=3.1-repair-1"' not in ydna:
        ydna = ydna.replace('<script src="assets/repair/site.js?v=3.1-repair-1" defer></script>', '<script src="assets/repair/site.js?v=3.1-repair-1" defer></script><script src="/assets/v3/dna.js?v=3.1-repair-1" defer></script>', 1)
    footer_script = '<script src="/assets/v3/dna-footer.js?v=1" defer></script>'
    if footer_script not in ydna:
        ydna = ydna.replace('</body>', footer_script + '</body>', 1)
    update(WEB / 'assets/v3/dna-footer.js', (ROOT / 'tools/dna_footer.js').read_text(encoding='utf-8'), changed)
    update(ydna_path, ydna, changed)
    update(WEB / "dna" / "index.html", legacy_redirect(), changed)
    return changed


if __name__ == "__main__":
    print(repair())
