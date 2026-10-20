#!/usr/bin/env python3
"""Write each person page's "In the family tree" links into the page itself.

``tools/site_sources/performance/core.js`` added this row after the page had
rendered, which moved the header and everything below it (a layout shift of
0.104 on Glasgow-951 at 320 px, against a 0.1 budget). The row is now part of
the HTML, with descendant counts from
``www/assets/research/tree-research-status.json``. ``core.js`` leaves a page
that already has ``#profile-tree-links`` alone and still adds the row to a page
built before this change.

The markup, links, titles, icons and the rules for hiding a view mirror
``core.js``. The colours and sizes are the values ``core.js`` copied onto the
row from the header's buttons and kicker, measured in Chrome on 20 October 2026.

Run directly to add the row to every built person page in place. ``--check``
changes nothing and exits 1 when a page lacks the current row.
"""
from __future__ import annotations

import argparse
from html import escape, unescape
import json
from pathlib import Path
import re
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "www"
STATUS = "assets/research/tree-research-status.json"

ICONS = {
    'sun': '<svg viewBox="0 0 16 16" aria-hidden="true"><circle cx="8" cy="8" r="2.4" fill="currentColor"/><circle cx="8" cy="8" r="4.6" fill="none" stroke="currentColor" stroke-width="1.2" opacity=".7"/><circle cx="8" cy="8" r="7" fill="none" stroke="currentColor" stroke-width="1.1" opacity=".45"/></svg>',
    'down': '<svg viewBox="0 0 16 16" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.3"><circle cx="5" cy="2.4" r="1.4"/><circle cx="11" cy="2.4" r="1.4"/><path d="M5 3.8v1.6h6V3.8M8 5.4v1.4"/><rect x="5.6" y="6.8" width="4.8" height="2.6" rx=".8" fill="currentColor" stroke="none"/><path d="M8 9.4v1.4M3.5 10.8h9M3.5 10.8v1.2M8 10.8v1.2M12.5 10.8v1.2"/><circle cx="3.5" cy="13.4" r="1.3"/><circle cx="8" cy="13.4" r="1.3"/><circle cx="12.5" cy="13.4" r="1.3"/></svg>',
    'all': '<svg viewBox="0 0 16 16" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.3"><circle cx="8" cy="8" r="6.3"/><circle cx="8" cy="8" r="1.6" fill="currentColor"/><path d="M8 1.7v4.7M2 8h4.4M14 8H9.6M8 14.3V9.6"/></svg>',
    'time': '<svg viewBox="0 0 16 16" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.4"><path d="M1.5 4h9M4 8h10.5M2.5 12h7"/><circle cx="10.5" cy="4" r="1.3" fill="currentColor"/><circle cx="4" cy="8" r="1.3" fill="currentColor"/><circle cx="9.5" cy="12" r="1.3" fill="currentColor"/></svg>',
}
# core.js's stylesheet, then the values it copied onto the row from the header:
# the default dossier header, and the release-ready header (Glasgow-951).
CSS = (".profile-tree-links{--ptl-fg:#315a43;--ptl-bd:#b8cbbd;--ptl-bg:#fffef9;--ptl-gold:#a77a16;--ptl-fs:.9rem;--ptl-rad:6px;margin:14px 0 0;display:flex;flex-wrap:wrap;align-items:center;gap:8px}.profile-tree-links>.ptl-label{flex:0 0 100%;font-size:.72rem;letter-spacing:.09em;text-transform:uppercase;color:var(--ptl-gold);font-weight:600}.profile-tree-links a{display:inline-flex;align-items:center;gap:6px;min-height:36px;padding:6px 12px;border:1px solid var(--ptl-bd);border-radius:var(--ptl-rad);background:var(--ptl-bg);color:var(--ptl-fg);font-size:var(--ptl-fs);text-decoration:none;line-height:1.2}.profile-tree-links a:hover,.profile-tree-links a:focus-visible{background:color-mix(in srgb,var(--ptl-fg) 12%,var(--ptl-bg))}.profile-tree-links a.ptl-sun{border-color:var(--ptl-gold);background:color-mix(in srgb,var(--ptl-gold) 16%,var(--ptl-bg))}.profile-tree-links a.ptl-sun:hover,.profile-tree-links a.ptl-sun:focus-visible{background:color-mix(in srgb,var(--ptl-gold) 30%,var(--ptl-bg))}.profile-tree-links a.ptl-sun svg{color:var(--ptl-gold)}.profile-tree-links a small{color:inherit!important;opacity:.8;font-size:.85em;font-weight:400}.profile-tree-links svg{width:15px;height:15px;flex:0 0 auto}@media (max-width:560px){.profile-tree-links a{flex:1 1 auto;justify-content:center}}"
       ".dossier-header .profile-tree-links{--ptl-fg:#f7f7ed;--ptl-bd:#86a89a;--ptl-bg:transparent;"
       "--ptl-fs:12.8px;--ptl-rad:6px;--ptl-gold:#ddc791}"
       ".release-ready .dossier-header .profile-tree-links{--ptl-fg:#fffaf0;--ptl-bd:#81947a;"
       "--ptl-fs:11.52px;--ptl-rad:4px;--ptl-gold:#d1bb84}")
STYLE = f'<style id="profile-tree-links-css">{CSS}</style>'

_ACTIONS = re.compile(r'<div class="dossier-actions">(?:(?!</?div\b).)*?</div>', re.S)
_EXISTING_NAV = re.compile(r'<nav id="profile-tree-links"[^>]*>.*?</nav>', re.S)
_EXISTING_STYLE = re.compile(r'<style id="profile-tree-links-css">.*?</style>', re.S)
_PERSON = re.compile(r"""<body\b[^>]*\sdata-g-person=(?:"([^"]*)"|'([^']*)')""")


def _uri(value: str) -> str:
    """JavaScript's encodeURIComponent."""
    return quote(value, safe="-_.!~*'()")


def _count(number: int, word: str) -> str:
    return f"{number:,} {word}{'' if number == 1 else 's'}"


def nav_html(person_id: str, name: str | None, lines: dict | None) -> str:
    """The row core.js builds, with the counts it would fetch.

    Without ``lines`` (no tree status file) every view is shown, as core.js does.
    """
    name = str(name or "this person")
    enc = _uri(person_id)
    at = "/onetree/#person=" + enc
    items = [
        ("sun", "ptl-sun", "/onetree/#view=all&sun=" + enc, "Family sun",
         f"All of {name}’s recorded descendants as rings, one ring per generation", "d"),
        ("down", "", at + "&view=family", "Family tree",
         f"{name}’s ancestors above and descendants below, one row per generation", "any"),
        ("all", "", at + "&view=all", "Whole tree", f"Find {name} in the whole Glasgow tree", None),
        ("time", "", at + "&view=lanes", "Timeline", f"{name} on the family timeline", None),
    ]
    descendants, ancestors = (lines.get(person_id) or [0, 0]) if lines is not None else (0, 0)
    links = []
    for key, cls, href, label, title, needs in items:
        extra = ""
        if needs and lines is not None:
            number = descendants if needs == "d" else descendants + ancestors
            if not number:
                continue
            if key == "sun":
                extra = f"<small>{_count(number, 'descendant')}</small>"
        css_class = f' class="{cls}"' if cls else ""
        links.append(f'<a href="{escape(href, quote=True)}" title="{escape(title, quote=True)}" data-view="{key}"{css_class}>'
                     f'{ICONS[key]}<span>{label}</span>{extra}</a>')
    label = escape("Family tree views for " + name, quote=True)
    return (f'<nav id="profile-tree-links" class="profile-tree-links" aria-label="{label}">'
            f'<span class="ptl-label">In the family tree</span>{"".join(links)}</nav>')


def person_of(page: str) -> dict | None:
    match = _PERSON.search(page)
    if not match:
        return None
    try:
        person = json.loads(unescape(match[1] if match[1] is not None else match[2]))
    except ValueError:
        return None
    return person if isinstance(person, dict) else None


def add_to_page(page: str, lines: dict | None) -> str:
    """Insert, or refresh, the row after the header's action buttons. Idempotent."""
    person = person_of(page)
    page = _EXISTING_STYLE.sub("", _EXISTING_NAV.sub("", page))
    if not person or person.get("tree") is not True or not person.get("id"):
        return page
    actions = _ACTIONS.search(page)
    if not actions or "</head>" not in page:
        return page
    nav = nav_html(str(person["id"]), person.get("name"), lines)
    page = page[:actions.end()] + nav + page[actions.end():]
    return page.replace("</head>", STYLE + "</head>", 1)


def load_lines(web: Path = WEB) -> dict | None:
    path = web / STATUS
    if not path.is_file():
        return None
    lines = json.loads(path.read_text(encoding="utf-8")).get("lines")
    return lines if isinstance(lines, dict) else None


def apply(web: Path = WEB, *, write: bool = True) -> dict:
    lines = load_lines(web)
    counts = {"pages": 0, "changed": 0}
    for path in sorted((web / "people").glob("*.html")):
        text = path.read_text(encoding="utf-8", errors="surrogateescape")
        if 'class="dossier-actions"' not in text:
            continue
        counts["pages"] += 1
        updated = add_to_page(text, lines)
        if updated != text:
            counts["changed"] += 1
            if write:
                path.write_text(updated, encoding="utf-8", errors="surrogateescape")
    return counts


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--check", action="store_true", help="report pages without the current row; change nothing")
    parser.add_argument("--site", type=Path, default=WEB)
    args = parser.parse_args(argv)
    result = apply(args.site, write=not args.check)
    print(json.dumps(result))
    return 1 if args.check and result["changed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
