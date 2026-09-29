#!/usr/bin/env python3
"""Build the approved curated Y-DNA explorer, or a filtered historical summary."""
from __future__ import annotations

import argparse
from html import escape
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[3]

try:
    from tools.repair_primary_navigation import render_primary_navigation
    from tools.public_ydna_research import study_is_approved, restore_lines
    from tools.site_analytics import with_analytics
except ModuleNotFoundError:
    sys.path.insert(0, str(ROOT / "tools"))
    from repair_primary_navigation import render_primary_navigation
    from public_ydna_research import study_is_approved, restore_lines
    from site_analytics import with_analytics


PUBLIC_STUDY_INPUT = ROOT / "www/ydna/glasgow-ydna-story-source/data.json"
PRIVATE_STUDY_INPUT = ROOT / "data/private/withheld-public-assets/ydna/glasgow-ydna-story-source/data.json"
PUBLIC_OUTPUT = ROOT / "www/ydna/index.html"
SOURCE = Path(__file__).resolve().parent


def study_input() -> Path:
    """Use the preserved private study input once publication repair has run."""
    return PRIVATE_STUDY_INPUT if PRIVATE_STUDY_INPUT.exists() else PUBLIC_STUDY_INPUT


def _historical_roots(data: dict[str, object]) -> list[dict[str, str]]:
    """Keep curated historical labels while discarding all tester-level fields."""
    roots: list[dict[str, str]] = []
    for raw in data.get("roots", []):
        if not isinstance(raw, dict):
            continue
        profile = str(raw.get("profile") or "")
        name = str(raw.get("name") or "Unnamed historical line")
        years = str(raw.get("years") or "Dates not stated")
        haplo = str(raw.get("haplo") or "Branch not stated")
        route = str(raw.get("route") or "Route not stated")
        roots.append({"profile": profile, "name": name, "years": years, "haplo": haplo, "route": route})
    return roots


def _render_curated(data: dict[str, object], canonical: str, noindex: bool) -> str:
    """Preserve the full original illustrated study and its shared site shell."""
    page = (SOURCE / "curated-page.html").read_text(encoding="utf-8")
    assert page.count("__CURATED_STUDY_DATA__") == 1
    encoded = json.dumps(data, ensure_ascii=False, indent=2).replace("</", "<\\/")
    page = page.replace("__CURATED_STUDY_DATA__", encoded)
    page = re.sub(r'<base\b[^>]*>', '<base href="/">', page, count=1)
    page = re.sub(r'<link\b(?=[^>]*\brel="canonical")[^>]*>',
                  f'<link rel="canonical" href="{escape(canonical, quote=True)}">', page, count=1)
    page = re.sub(r'<meta\b(?=[^>]*\bname="robots")[^>]*>', '', page)
    if noindex:
        page = page.replace('</head>', '<meta name="robots" content="noindex, noarchive"></head>', 1)
    page = re.sub(r'<nav\b(?=[^>]*\bclass="[^\"]*\bg-nav\b[^\"]*")[^>]*>[\s\S]*?</nav>',
                  render_primary_navigation(Path("ydna/index.html")), page, count=1)
    # The overview gets the approved documentary lines locally. Atlas keeps its
    # separately filtered model rather than inheriting this page's approval.
    page = re.sub(r'<script\b[^>]*\bsrc="/?assets/v3/dna\.js(?:\?[^\"]*)?"[^>]*>\s*</script>',
                  lambda _: '<script>' + (SOURCE / 'overview.js').read_text(encoding='utf-8') + '</script>', page)
    # An old repair inserted the footer initializer twice. Retain one copy.
    footer_seen = False
    def footer_script(match):
        nonlocal footer_seen
        if footer_seen:
            return ''
        footer_seen = True
        return '<script src="/assets/v3/dna-footer.js" defer></script>'
    page = re.sub(r'<script\b[^>]*\bsrc="/?assets/v3/dna-footer\.js(?:\?[^\"]*)?"[^>]*>\s*</script>', footer_script, page)
    return with_analytics(page)


def render(data: dict[str, object], *, canonical: str, noindex: bool = False) -> str:
    """Expose tester details only for the explicitly approved retained study."""
    if study_is_approved(data):
        return _render_curated(data, canonical, noindex)
    roots = _historical_roots(data)
    cards = []
    for root in roots:
        name = escape(root["name"])
        profile = escape(root["profile"])
        link = f'<a href="/people/{profile}/">{name}</a>' if profile else name
        cards.append(
            f"<article><h3>{link}</h3><p>{escape(root['years'])}</p>"
            f"<p><code>{escape(root['haplo'])}</code></p><p>{escape(root['route'])}</p></article>"
        )
    robots = '<meta name="robots" content="noindex, noarchive">\n  ' if noindex else ""
    page = f"""<!doctype html>
<html lang="en-GB">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  {robots}<title>Glasgow Y-DNA · Historical branch summary</title>
  <meta name="description" content="A public historical summary of the Glasgow Y-DNA research, without tester-level genetic data.">
  <link rel="canonical" href="{canonical}">
  <link rel="icon" href="/assets/favicon.svg">
  <link rel="stylesheet" href="/assets/unified/site.css?v=54e36149cb">
  <link rel="stylesheet" href="/assets/v3/site.css">
  <link rel="stylesheet" href="/assets/repair/site.css">
  <link rel="stylesheet" href="/assets/unified/section-submenus.css">
  <script defer src="/assets/unified/routes.js"></script>
  <script defer src="/assets/unified/site.js?v=2528be2335"></script>
  <script defer src="/assets/unified/section-submenus.js"></script>
  <style>
    .g-crumbs a{{color:#30452d;opacity:1}}
    .ydna-main{{max-width:1060px;margin:0 auto;padding:clamp(2rem,6vw,5rem) 1.5rem 5rem}}
    .ydna-kicker{{font-size:.78rem;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:#496844}}
    .ydna-main h1{{max-width:850px;font:500 clamp(2.4rem,7vw,5rem)/1.04 var(--g-serif,Georgia,serif);margin:.4rem 0 1.3rem;color:#30452d}}
    .ydna-lede{{max-width:720px;font-size:1.15rem;line-height:1.7;color:#40523c}}
    .ydna-notice{{max-width:800px;margin:2rem 0;padding:1.3rem 1.5rem;border-left:4px solid #496844;background:#edf1e7;color:#30452d}}
    .ydna-main h2{{margin:3rem 0 .8rem;font:500 2rem/1.15 var(--g-serif,Georgia,serif);color:#30452d}}
    .ydna-main p{{line-height:1.7;color:#40523c}}
    .ydna-branches{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:1rem}}
    .ydna-branches article{{padding:1.2rem;border:1px solid #c5d2bd;background:#fafbf7}}
    .ydna-branches h3{{margin:0;color:#30452d;font:500 1.35rem/1.2 var(--g-serif,Georgia,serif)}}
    .ydna-branches h3 a{{color:inherit;text-underline-offset:3px}}
    .ydna-branches p{{margin:.55rem 0 0;font-size:.94rem}} .ydna-branches code{{color:#496844}}
    .ydna-links{{display:flex;flex-wrap:wrap;gap:.8rem;margin-top:2rem}} .ydna-links a{{padding:.7rem 1rem;border:1px solid #91a987;color:#30452d;text-decoration:none}}
    .ydna-section-bar{{position:sticky;top:var(--g-bar);width:100%;padding:0 36px;background:#e6edde;z-index:45}}
    .v3-site.g-kind-dna #sidebar.ydna-section-bar .main-nav{{display:flex!important;flex-wrap:wrap!important;overflow:visible!important;gap:5px;padding:9px 0;min-height:54px}}
    .ydna-section-bar .main-nav a{{text-decoration:none}}
    .v3-site.g-kind-dna #sidebar.ydna-section-bar .main-nav a[aria-current]{{background:#35542e;color:#fff;border-color:#35542e;box-shadow:0 2px 5px #233b2020}}
    .ydna-main :is(header,section)[id]{{scroll-margin-top:calc(var(--g-bar) + var(--ydna-nav-height,54px) + 16px)}}
    .ydna-main .ydna-section{{padding-bottom:1rem}}
    .ydna-main a{{color:#30452d;text-underline-offset:3px}}
    @media(max-width:760px){{.ydna-section-bar{{padding:0 18px}}.v3-site.g-kind-dna #sidebar.ydna-section-bar .main-nav a{{min-width:0;padding:8px 10px!important;font-size:11px!important}}}}
  </style>
</head>
<body class="g-unified g-kind-dna v3-site" data-g-path="/ydna/index.html">
  <a class="g-skip" href="#main">Skip to page content</a>
  <div class="g-bar"><div class="g-bar-left"><div class="g-crumbs"><a href="/">Glasgow archive</a><i>/</i><strong>Y-DNA</strong></div></div></div>
  <div class="ydna-section-bar" id="sidebar"><nav class="main-nav" aria-label="Y-DNA navigation"><a href="#overview" aria-current="location">Overview</a><a href="#roots">Historical branches</a><a href="#next-steps">Open questions</a></nav></div>
  <main class="ydna-main" id="main">
    <header id="overview">
    <p class="ydna-kicker">Historical research summary</p>
    <h1>Glasgow Y-DNA and the historical branches under study.</h1>
    <p class="ydna-lede">This page keeps the project’s historical branch interpretation visible while individual test results, kit identifiers, comparison matrices and private-call summaries are withheld pending publication approval.</p>
    <div class="ydna-notice"><strong>How to read this summary.</strong> Haplogroup labels describe reported paternal branches. They do not prove a historical pedigree or identify the parent of a named person. The dated routes and relationships below remain research leads unless supported by cited records.</div>
    </header>
    <section class="ydna-section" id="roots" aria-labelledby="ydna-roots-title">
    <h2 id="ydna-roots-title">Current historical branch references</h2>
    <p>These are the named historical lines retained from the curated project summary. They are not a roster of tested people and do not disclose individual genetic results.</p>
    <section class="ydna-branches" aria-label="Historical Y-DNA branches">{''.join(cards)}</section>
    </section>
    <section class="ydna-section" id="next-steps" aria-labelledby="ydna-questions-title">
    <h2 id="ydna-questions-title">What remains open</h2>
    <p>The older North Sea and medieval Britain model is an interpretation of branch history. The links between FT4811, FT25406, FT20271 and later Glasgow families require documentary work alongside any future approved genetic publication. Named historical attachments remain qualified where the underlying paternal chain has not been independently established.</p>
    <nav class="ydna-links" aria-label="Related Y-DNA research"><a href="/timeline">Read the historical timeline</a><a href="/research/">Explore the research questions</a><a href="/privacy/">Privacy and publication policy</a></nav>
    </section>
  </main>
</body>
</html>
"""
    # Render the public-safe content inside the maintained shared site shell.
    # Never recover a shell by copying an old explorer's private data/scripts.
    content = re.search(r'  <div class="ydna-section-bar"[\s\S]*?</main>', page).group()
    shell = (SOURCE / "shell.html").read_text(encoding="utf-8")
    shell = shell.replace("{{primary_navigation}}", render_primary_navigation(Path("ydna/index.html")))
    shell = shell.replace("{{content}}", content)
    navigation = (SOURCE / "navigation.js").read_text(encoding="utf-8")
    body = '<a class="g-skip" href="#main">Skip to page content</a>\n' + shell + '<script>' + navigation + '</script>'
    return with_analytics(re.sub(r'(<body\b[^>]*>)[\s\S]*?(</body>)', lambda m: m[1] + body + m[2], page))


def build(output: Path = PUBLIC_OUTPUT) -> Path:
    data = json.loads(study_input().read_text(encoding="utf-8"))
    is_public = output.resolve() == PUBLIC_OUTPUT.resolve()
    if is_public:
        restore_lines(ROOT / "www")
    page = render(
        data,
        canonical="https://glasgow.phenotype.dev/ydna/",
        noindex=not is_public,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(page, encoding="utf-8")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=PUBLIC_OUTPUT)
    args = parser.parse_args()
    try:
        output = build(args.output)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.exit(1, f"Build failed: {exc}\n")
    print(f"Built {output} ({output.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
