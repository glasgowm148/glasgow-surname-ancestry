#!/usr/bin/env python3
"""Render the shared primary rail and retain older page repairs."""
import argparse
from collections import Counter
from pathlib import Path
import re

WEB = Path(__file__).resolve().parents[1] / 'www'
NAV = re.compile(r'<nav\b(?=[^>]*\bclass="[^"]*\bg-nav\b[^"]*")[^>]*>.*?</nav>', re.S)
ATLAS = re.compile(r'<a\b(?=[^>]*\bhref="/onetree/")[^>]*>.*?</a>', re.S)
FAMILIES = re.compile(r'<a\b(?=[^>]*\bhref="/branches/")[^>]*>.*?</a>', re.S)
RECORDS = re.compile(r'<a\b(?=[^>]*\bhref="/(?:sources|records)/")[^>]*>.*?</a>', re.S)
RESEARCH = re.compile(r'<a\b(?=[^>]*\bhref="/research/")[^>]*>.*?</a>', re.S)
TRANSCRIPTIONS = re.compile(r'<a\b(?=[^>]*\bhref="/research/transcriptions/")[^>]*>.*?</a>', re.S)
STATISTICS = re.compile(r'<a\b(?=[^>]*\bhref="/statistics/")[^>]*>.*?</a>', re.S)
RESOURCES = re.compile(r'<a\b(?=[^>]*\bhref="/resources/")[^>]*>.*?</a>', re.S)
# Map is a view of the Atlas and Timeline part of Y-DNA; their sidebar entries
# live in those sections' submenus (tools/section_submenus.js).
SECTION_NAV = re.compile(r'<nav\b(?=[^>]*\bclass="[^"]*\bv3-view-nav\b[^"]*")[^>]*>.*?</nav>', re.S)
PERSON_FOOTER = '<footer class="g-footer"><div><span class="g-footer-name">The Glasgow Surname Project</span><p>A shared research collection. Profile links and hypotheses are kept distinct from the evidence behind them.</p></div><nav class="g-footer-links" aria-label="Project information"><a href="/about/">About the project</a><a href="/catalogue/">Browse people</a><a href="/research/">Research workspace</a><a href="/changes/">Latest research</a><a href="/feedback/">Suggest a correction &nearr;</a></nav></footer>'

PRIMARY_NAV_ITEMS = (
    ('/', 'Overview', '<svg class="g-ico" viewbox="0 0 24 24" aria-hidden="true"><path d="m3 10 9-7 9 7M5 9v11h14V9M9 20v-7h6v7"></path></svg>'),
    ('/catalogue/', 'People', '<svg class="g-ico" viewbox="0 0 24 24" aria-hidden="true"><circle cx="9" cy="7" r="3"></circle><path d="M3 21v-4a6 6 0 0 1 12 0v4M17 4a3 3 0 0 1 0 6m1 4a5 5 0 0 1 3 5v2"></path></svg>'),
    ('/branches/', 'Families &amp; places', '<svg class="g-ico" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="5" r="3"></circle><path d="M12 8v5M5 17v-4h14v4"></path><circle cx="5" cy="20" r="2"></circle><circle cx="19" cy="20" r="2"></circle></svg>'),
    ('/onetree/', 'Atlas', '<svg class="g-ico" viewbox="0 0 24 24" aria-hidden="true"><path d="M12 22V6m0 9-7-5m7 2 6-6m-6 14 7-5"></path><circle cx="12" cy="4" r="2"></circle><circle cx="4" cy="9" r="2"></circle><circle cx="19" cy="5" r="2"></circle></svg>'),
    ('/ydna/', 'Y-DNA', '<svg class="g-ico" viewbox="0 0 24 24" aria-hidden="true"><path d="M6 2c0 10 12 10 12 20M18 2C18 12 6 12 6 22M7 5h10m-8 4h6m-6 6h6m-8 4h10"></path></svg>'),
    ('/research/', 'Research', '<svg class="g-ico" viewbox="0 0 24 24" aria-hidden="true"><path d="M4 4h6a4 4 0 0 1 4 4v13a5 5 0 0 0-5-3H4zM14 8a4 4 0 0 1 4-4h3v14h-3a5 5 0 0 0-4 3"></path></svg>'),
    ('/about/', 'About', '<svg class="g-ico" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9"></circle><path d="M12 11v6M12 7h.01"></path></svg>'),
)

SECTION_ROOTS = {
    'about': '/about/', 'changes': '/about/', 'coverage': '/about/', 'data': '/about/',
    'feedback': '/about/', 'resources': '/about/', 'status': '/about/',
    'branches': '/branches/',
    'catalogue': '/catalogue/', 'early-records': '/catalogue/', 'people': '/catalogue/',
    'map': '/onetree/', 'onetree': '/onetree/',
    'dna': '/ydna/', 'timeline': '/ydna/', 'ydna': '/ydna/',
    'candidate-matches': '/research/', 'compare': '/research/', 'connections': '/research/',
    'events': '/research/', 'free-space': '/research/', 'records': '/research/',
    'research': '/research/', 'sources': '/research/', 'statistics': '/research/',
}


def section_for(relative: Path) -> str:
    """Return the canonical rail destination owning a generated page."""
    if relative.as_posix() == 'index.html':
        return '/'
    return SECTION_ROOTS.get(relative.parts[0], '/')


def render_primary_navigation(relative: Path) -> str:
    """Render every primary rail link from the one canonical definition."""
    section = section_for(relative)
    links = ''.join(
        f'<a class="g-nav-link" href="{href}"'
        f'{" aria-current=\"page\"" if href == section else ""}>'
        f'{icon}<span>{label}</span></a>'
        for href, label, icon in PRIMARY_NAV_ITEMS
    )
    return f'<nav class="g-nav" aria-label="Main navigation">{links}</nav>'


def is_excluded(path: Path) -> bool:
    relative = path.relative_to(WEB)
    return 'glasgow-ydna-story-source' in relative.parts or path.name.endswith('-standalone.html')


def update_section_submenu_references(page: str) -> str:
    """Use one cache version and one deferred submenu script per rail page."""
    css = re.compile(r'<link\b(?=[^>]*\bhref="[^"]*assets/unified/section-submenus\.css(?:\?[^"]*)?")[^>]*>', re.S)
    script = re.compile(r'<script\b(?=[^>]*\bsrc="[^"]*assets/unified/section-submenus\.js(?:\?[^"]*)?")[^>]*>\s*</script>', re.S)
    found = False

    def stylesheet(match):
        nonlocal found
        if found:
            return ''
        found = True
        return '<link rel="stylesheet" href="/assets/unified/section-submenus.css?v=4">'

    page = css.sub(stylesheet, page)
    if not found:
        page = page.replace('</head>', '<link rel="stylesheet" href="/assets/unified/section-submenus.css?v=4"></head>', 1)
    page = script.sub('', page)
    return page.replace('</body>', '<script src="/assets/unified/section-submenus.js?v=4" defer></script></body>', 1)


def repair_nav_only_page(page: str, relative: Path) -> str:
    """Replace only a g-nav and its subsection asset references."""
    updated, count = NAV.subn(render_primary_navigation(relative), page, count=1)
    return update_section_submenu_references(updated) if count else page


def repair_nav_only() -> Counter:
    """Apply the canonical rail without invoking unrelated legacy repairs."""
    changed = Counter()
    for path in WEB.rglob('*.html'):
        if is_excluded(path):
            continue
        page = path.read_text(encoding='utf-8')
        updated = repair_nav_only_page(page, path.relative_to(WEB))
        if updated != page:
            path.write_text(updated, encoding='utf-8')
            changed['primary_navigation'] += 1
    return changed


def repair():
    changed = Counter()
    for extension in ('js', 'css'):
        source = WEB.parent / 'tools' / f'section_submenus.{extension}'
        target = WEB / 'assets/unified' / f'section-submenus.{extension}'
        content = source.read_text(encoding='utf-8')
        if not target.exists() or target.read_text(encoding='utf-8') != content:
            target.write_text(content, encoding='utf-8')
            changed['section_submenus'] += 1
    for path in WEB.rglob('*.html'):
        relative = path.relative_to(WEB)
        if 'glasgow-ydna-story-source' in relative.parts or path.name.endswith('-standalone.html'):
            continue
        page = path.read_text(encoding='utf-8')
        updated = NAV.sub(render_primary_navigation(relative), page, count=1)

        def sections(match):
            # Legacy secondary bars repeated unrelated primary destinations.
            # Purpose-built local controls use separate markup and are retained.
            return ""

        updated = SECTION_NAV.sub(sections, updated)
        if relative.as_posix() == 'catalogue/index.html' and 'href="/changes/"' not in updated:
            updated = updated.replace('</main>', '<p><a href="/changes/">Latest research</a></p></main>', 1)
        if relative.as_posix() in {'status/index.html', 'status.html'} and 'class="g-nav-link" href="/research/"' not in updated:
            links = '<a class="g-nav-link" href="/research/">Research</a><a class="g-nav-link" href="/about/">About</a>'
            updated = updated.replace('</nav>', links + '</nav>', 1)
            updated = update_section_submenu_references(updated)
        if relative.parts[0] == 'people' and '<footer' not in updated:
            updated = updated.replace('</main>', '</main>' + PERSON_FOOTER, 1)
        def footer_links(match):
            footer = match.group(0)
            if not re.search(r'href="/changes(?:/|\.html)"', footer):
                footer = footer.replace('</nav>', '<a href="/changes/">Latest research</a></nav>', 1)
            footer = re.sub(r'(<a\b[^>]*href="/changes(?:/|\.html)"[^>]*>)Change log(</a>)', r'\1Latest research\2', footer)
            for url, label in (
                ('https://www.wikitree.com/wiki/Space:Glasgow_Name_Study', 'WikiTree Name Study'),
                ('https://groups.io/g/glasgowdnaproject/', 'Discussion group'),
            ):
                if f'href="{url}"' not in footer:
                    footer = footer.replace('</nav>', f'<a href="{url}" target="_blank" rel="noopener noreferrer">{label} &nearr;</a></nav>', 1)
            return footer

        updated = re.sub(
            r'<nav\b(?=[^>]*\bclass="[^"]*\bg-footer-links\b[^"]*")[^>]*>.*?</nav>',
            footer_links, updated, flags=re.S,
        )
        if not re.search(r'href="/changes/"', updated):
            latest = '<a href="/changes/">Latest research</a>'
            if '</footer>' in updated:
                updated = updated.replace('</footer>', latest + '</footer>', 1)
        if NAV.search(updated):
            updated = update_section_submenu_references(updated)
        if relative.as_posix() == 'research/index.html' and 'class="repair-transcriptions-card"' not in updated:
            card = '<a class="repair-research-card repair-transcriptions-card" href="/research/transcriptions/"><h2>Wills &amp; testament transcriptions</h2><p>Read the latest saved LLM-assisted readings, linked profiles, source references and unresolved passages.</p><span>Explore the transcriptions &rarr;</span></a>'
            if 'repair-transcriptions-card"' not in updated:
                updated = updated.replace('<div class="repair-research-grid">', '<div class="repair-research-grid">' + card, 1)
        if updated != page:
            path.write_text(updated, encoding='utf-8')
            changed['primary_navigation'] += 1
    return changed


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--nav-only', action='store_true', help='replace only rails and submenu asset references')
    args = parser.parse_args()
    print(dict(repair_nav_only() if args.nav_only else repair()))
