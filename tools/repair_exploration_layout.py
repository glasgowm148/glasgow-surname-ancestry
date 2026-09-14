#!/usr/bin/env python3
"""Apply compact Atlas tools and a reserved Map control strip."""
from collections import Counter
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / 'www'


def repair():
    changed = Counter()
    for extension in ('js', 'css'):
        source = (ROOT / 'tools' / f'exploration_layout.{extension}').read_text()
        target = WEB / 'assets/repair' / f'exploration-layout.{extension}'
        if not target.exists() or target.read_text() != source:
            target.write_text(source)
            changed['exploration_layout'] += 1
    for relative, marker in [('onetree/index.html', 'exploration-atlas'), ('map/index.html', 'exploration-map')]:
        path = WEB / relative
        before = page = path.read_text()
        if marker not in page:
            page = re.sub(r'(<body\b[^>]*\bclass=")([^"]*)', lambda m: m[1] + m[2] + ' ' + marker, page, count=1)
        if marker == 'exploration-atlas':
            page = re.sub(r'<nav\b(?=[^>]*\bclass="v3-view-nav")[^>]*>.*?</nav>', '', page, flags=re.S)
        if '/assets/repair/exploration-layout.css' not in page:
            page = page.replace('</head>', '<link rel="stylesheet" href="/assets/repair/exploration-layout.css?v=1"></head>', 1)
        if '/assets/repair/exploration-layout.js' not in page:
            page = page.replace('</body>', '<script src="/assets/repair/exploration-layout.js?v=1" defer></script></body>', 1)
        if page != before:
            path.write_text(page)
            changed['exploration_layout'] += 1
    path = WEB / 'assets/repair/atlas.js'
    before = path.read_text()
    revised = before.replace('else show(window.innerWidth>=1360)', 'else show(false)')
    if revised != before:
        path.write_text(revised)
        changed['exploration_layout'] += 1
    return changed


if __name__ == '__main__':
    print(dict(repair()))
