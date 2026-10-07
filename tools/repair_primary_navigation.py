#!/usr/bin/env python3
"""Render the shared primary rail and retain older page repairs."""
import argparse
from collections import Counter
from pathlib import Path
import re
from urllib.parse import urljoin, urlsplit

try:
    from tools import site_identity as identity
except ModuleNotFoundError:
    import site_identity as identity

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
PERSON_FOOTER = identity.footer_html()

PRIMARY_NAV_ITEMS = (
    ('/', 'Home', '<svg class="g-ico" viewbox="0 0 24 24" aria-hidden="true"><path d="m3 10 9-7 9 7M5 9v11h14V9M9 20v-7h6v7"></path></svg>'),
    ('/catalogue/', 'People', '<svg class="g-ico" viewbox="0 0 24 24" aria-hidden="true"><circle cx="9" cy="7" r="3"></circle><path d="M3 21v-4a6 6 0 0 1 12 0v4M17 4a3 3 0 0 1 0 6m1 4a5 5 0 0 1 3 5v2"></path></svg>'),
    ('/branches/', 'Families &amp; places', '<svg class="g-ico" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="5" r="3"></circle><path d="M12 8v5M5 17v-4h14v4"></path><circle cx="5" cy="20" r="2"></circle><circle cx="19" cy="20" r="2"></circle></svg>'),
    ('/onetree/', 'Family tree', '<svg class="g-ico" viewbox="0 0 24 24" aria-hidden="true"><path d="M12 22V6m0 9-7-5m7 2 6-6m-6 14 7-5"></path><circle cx="12" cy="4" r="2"></circle><circle cx="4" cy="9" r="2"></circle><circle cx="19" cy="5" r="2"></circle></svg>'),
    ('/ydna/', 'Y-DNA', '<svg class="g-ico" viewbox="0 0 24 24" aria-hidden="true"><path d="M6 2c0 10 12 10 12 20M18 2C18 12 6 12 6 22M7 5h10m-8 4h6m-6 6h6m-8 4h10"></path></svg>'),
    ('/sources/', 'Records &amp; sources', '<svg class="g-ico" viewBox="0 0 24 24" aria-hidden="true"><path d="M5 3h10l4 4v14H5zM14 3v5h5M8 12h8M8 16h8"></path></svg>'),
    ('/research/', 'Research', '<svg class="g-ico" viewbox="0 0 24 24" aria-hidden="true"><path d="M4 4h6a4 4 0 0 1 4 4v13a5 5 0 0 0-5-3H4zM14 8a4 4 0 0 1 4-4h3v14h-3a5 5 0 0 0-4 3"></path></svg>'),
    ('/latest-findings/', 'Latest findings', '<svg class="g-ico" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9"></circle><path d="M12 7v5l3 2M3 3v5h5"></path></svg>'),
    ('/about/', 'About', '<svg class="g-ico" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9"></circle><path d="M12 11v6M12 7h.01"></path></svg>'),
)

# First-paint links for rails whose local navigation is stable across pages.
# section_submenus.js reconciles query/hash state after load.
SECTION_SUBMENU_ITEMS = {
    '/catalogue/': (
        ('/catalogue/', 'People search'),
        ('/catalogue/?missingProfile=1#catalogue-filters', 'No WikiTree link'),
        ('/catalogue/?needsUpdate=1#catalogue-filters', 'WikiTree updates'),
        ('/catalogue/#research-queue', 'Held &amp; pending research'),
        ('/early-records/', 'Early records'),
    ),
    '/branches/': (
        ('/branches/', 'All families'),
        ('/branches/#research-studies', 'Family studies'),
        ('/branches/scottish-families/', 'Scottish families'),
        ('/branches/early-ireland/', 'Irish families'),
    ),
    '/onetree/': (
        ('/onetree/#view=all', 'Whole tree'),
        ('/onetree/#view=branches', 'Branch cards'),
        ('/onetree/#view=lanes', 'Timeline'),
        ('/onetree/#view=dna', 'Y-DNA'),
        ('/map/', 'Map'),
    ),
    '/sources/': (
        ('/sources/', 'Source references'),
        ('/records/', 'Records by person'),
        ('/research/transcriptions/', 'Wills &amp; transcriptions'),
    ),
    '/research/': (
        ('/research/#open-questions', 'Open questions'),
        ('/connections/', 'Find a relationship'),
        ('/compare/', 'Compare two people'),
        ('/free-space/', 'WikiTree study pages'),
    ),
    # Changes and Feedback stay under About (AGENTS.md).  Status is reached
    # from "About the data" and the top-bar snapshot link.
    '/about/': (
        ('/about/', 'About this project'),
        ('/evidence/', 'How to read the evidence'),
        ('/coverage/', 'About the data'),
        ('/statistics/', 'Statistics'),
        ('/data/', 'Data &amp; downloads'),
        ('/resources/', 'Resources'),
        ('/changes/', 'Change log'),
        ('/privacy/', 'Privacy'),
        ('/feedback/', 'Report a correction'),
    ),
}

SECTION_ROOTS = {
    'about': '/about/', 'changes': '/about/', 'coverage': '/about/', 'data': '/about/',
    'evidence': '/about/', 'feedback': '/about/', 'privacy': '/about/', 'resources': '/about/',
    'statistics': '/about/', 'status': '/about/',
    'branches': '/branches/',
    'catalogue': '/catalogue/', 'early-records': '/catalogue/', 'people': '/catalogue/',
    'map': '/onetree/', 'onetree': '/onetree/', 'places': '/branches/',
    'dna': '/ydna/', 'timeline': '/ydna/', 'ydna': '/ydna/',
    'candidate-matches': '/research/', 'compare': '/research/', 'connections': '/research/',
    'events': '/research/', 'free-space': '/research/', 'records': '/sources/',
    'research': '/research/', 'sources': '/sources/',
    'latest-findings': '/latest-findings/',
}


def section_for(relative: Path) -> str:
    """Return the canonical rail destination owning a generated page."""
    if relative.as_posix() == 'index.html':
        return '/'
    if relative.as_posix().startswith('research/transcriptions/'):
        return '/sources/'
    key = relative.parts[0]
    if key.endswith('.html'):
        key = key[:-5]
    return SECTION_ROOTS.get(key, '/')


def _relative_url(relative: Path) -> str:
    value = '/' + relative.as_posix()
    if value.endswith('/index.html'):
        value = value[:-len('index.html')]
    return value


def render_section_submenu(relative: Path, section: str) -> str:
    """Render stable local links before the deferred submenu script runs."""
    items = SECTION_SUBMENU_ITEMS.get(section, ())
    if not items:
        return ''
    page_url = urlsplit(_relative_url(relative))
    links = []
    for href, label in items:
        target = urlsplit(href)
        current = ''
        if (target.path == page_url.path and target.query == page_url.query
                and (not target.fragment
                     or (section == '/onetree/' and target.fragment == 'view=all' and not page_url.fragment))):
            current = ' aria-current="location"'
        links.append(f'<a href="{href}"{current}>{label}</a>')
    return '<div class="g-section-subnav" role="group" aria-label="Local sections">' + ''.join(links) + '</div>'


def render_primary_navigation(relative: Path) -> str:
    """Render every primary rail link from the one canonical definition."""
    section = section_for(relative)
    submenu = render_section_submenu(relative, section)
    links = []
    for href, label, icon in PRIMARY_NAV_ITEMS:
        links.append(
            f'<a class="g-nav-link" href="{href}"'
            f'{" aria-current=\"page\"" if href == section else ""}>'
            f'{icon}<span>{label}</span></a>'
        )
        if href == section and submenu:
            # Keep the first-paint local rail beside its selected destination;
            # deferred JS can then reuse it without a visible relocation.
            links.append(submenu)
    return f'<nav class="g-nav" aria-label="Main navigation">{"".join(links)}</nav>'


SECTION_LABELS = {href: label for href, label, _ in PRIMARY_NAV_ITEMS}
CRUMBS = re.compile(r'<div class="g-crumbs">(.*?)</div>', re.S)
IN_MAIN_CRUMB = re.compile(r'<nav class="crumb"[^>]*>.*?</nav>', re.S)


def render_breadcrumbs(relative: Path, title_html: str) -> str:
    """One breadcrumb: Home / <section> / <page> (S1-09).

    ``title_html`` is already escaped.  The section level is left out on the
    home page and on a section's own landing page.
    """
    if relative.as_posix() == 'index.html':
        return '<div class="g-crumbs"><strong>Home</strong></div>'
    section = section_for(relative)
    parts = ['<a href="/">Home</a>']
    if section != '/' and urlsplit(_relative_url(relative)).path != section:
        parts.append(f'<a class="g-crumb-section" href="{section}">{SECTION_LABELS[section]}</a>')
    parts.append(f'<strong>{title_html}</strong>')
    return '<div class="g-crumbs">' + '<i>/</i>'.join(parts) + '</div>'


def _is_redirect_stub(page: str) -> bool:
    head = page.split('</head>', 1)[0]
    return ('data-clean-route-redirect' in head
            or bool(re.search(r'<meta\b[^>]*\bhttp-equiv=["\']refresh["\']', head, re.I)))


def repair_site_identity_page(page: str, relative: Path) -> str:
    """Give one page the site's single name, breadcrumb, rail foot and footer.

    Idempotent; changes only shared chrome, never <main> content except a
    duplicate in-page breadcrumb when the top-bar breadcrumb is present.
    """
    if _is_redirect_stub(page):
        return page
    page = re.sub(r'<title\b([^>]*)>(.*?)</title>',
                  lambda m: f'<title{m[1]}>{identity.normalise_title(m[2])}</title>', page, count=1, flags=re.S | re.I)
    og = identity.og_site_name_tag()
    if re.search(r'<meta\b[^>]*\bproperty=["\']og:site_name["\'][^>]*>', page, re.I):
        page = re.sub(r'<meta\b[^>]*\bproperty=["\']og:site_name["\'][^>]*>', og, page, count=1, flags=re.I)
    elif '</title>' in page:
        page = page.replace('</title>', '</title>' + og, 1)
    page = re.sub(r'<span class="g-brand-caption">.*?</span>',
                  f'<span class="g-brand-caption">{identity.SITE_RAIL_CAPTION}</span>', page, count=1, flags=re.S)
    page = page.replace('aria-label="Glasgow archive home"', f'aria-label="{identity.SITE_NAME} home"')
    page = page.replace('aria-label="Glasgow archive" class="g-rail"', f'aria-label="{identity.SITE_NAME}" class="g-rail"')
    # The rail repeated menu links; keep only "Find a connection" (S1-07).
    page = re.sub(r'<div class="repair-quick-links">.*?</div>',
                  '<div class="repair-quick-links"><a href="/connections/">Find a connection &rarr;</a></div>',
                  page, count=1, flags=re.S)
    page = re.sub(r'<div class="g-rail-bottom">.*?(?=</aside>)', lambda _: identity.rail_bottom_html(),
                  page, count=1, flags=re.S)
    crumbs = CRUMBS.search(page)
    if crumbs:
        strong = re.search(r'<strong>(.*?)</strong>', crumbs[1], re.S)
        if strong:
            page = page[:crumbs.start()] + render_breadcrumbs(relative, strong[1].strip()) + page[crumbs.end():]
            page = IN_MAIN_CRUMB.sub('', page)
    page = re.sub(r'<footer\b(?=[^>]*\bclass="g-footer")[^>]*>.*?</footer>',
                  lambda _: identity.footer_html(), page, flags=re.S)
    return page


def repair_site_identity() -> Counter:
    """Apply only the site-identity pass to every public page."""
    changed = Counter()
    for path in WEB.rglob('*.html'):
        if is_excluded(path) or 'www_old' in path.parts:
            continue
        page = path.read_text(encoding='utf-8')
        updated = repair_site_identity_page(page, path.relative_to(WEB))
        if updated != page:
            path.write_text(updated, encoding='utf-8')
            changed['site_identity'] += 1
    return changed


def is_excluded(path: Path) -> bool:
    relative = path.relative_to(WEB)
    return 'glasgow-ydna-story-source' in relative.parts or path.name.endswith('-standalone.html')


READER_SHELL_ROUTES = {
    'catalogue/index.html': ('Find a person', 'Search the Glasgow Surname Project people catalogue and its research filters.'),
    'catalogue.html': ('Find a person', 'Search the Glasgow Surname Project people catalogue and its research filters.'),
    'catalogue/advanced.html': ('Find a person', 'Search the Glasgow Surname Project people catalogue and its research filters.'),
    'changes/index.html': ('Change log', 'Changes to the Glasgow Surname Project public research catalogue.'),
    'changes.html': ('Change log', 'Changes to the Glasgow Surname Project public research catalogue.'),
    'feedback/index.html': ('Report a correction', 'How to report corrections and evidence to the Glasgow Surname Project.'),
    'feedback.html': ('Report a correction', 'How to report corrections and evidence to the Glasgow Surname Project.'),
    'privacy/index.html': ('Privacy and publication policy', 'How the Glasgow Surname Project handles public research, local preferences and third-party links.'),
    'status/index.html': ('Catalogue status', 'Build status and source-quality coverage for the Glasgow Surname Project.'),
    'status.html': ('Catalogue status', 'Build status and source-quality coverage for the Glasgow Surname Project.'),
    'compare/index.html': ('Compare people', 'Compare two Glasgow Surname Project people and their evidence context.'),
    'compare.html': ('Compare people', 'Compare two Glasgow Surname Project people and their evidence context.'),
    'candidate-matches/index.html': ('Strong candidate matches', 'Ranked potential-parent and possible-duplicate research leads.'),
    'candidate-matches.html': ('Strong candidate matches', 'Ranked potential-parent and possible-duplicate research leads.'),
}


def _reader_section(relative: Path) -> str:
    route = relative.as_posix()
    if route.startswith('places/'):
        return '/branches/'
    if route.startswith('people/clusters/'):
        return '/branches/'
    if route.startswith('people/') or route.startswith('early-bearers'):
        return '/catalogue/'
    if route.startswith('catalogue'):
        return '/catalogue/'
    if route.startswith(('compare', 'candidate-matches')):
        return '/research/'
    return '/about/'


def _reader_metadata(page: str, relative: Path) -> tuple[str, str] | None:
    route = relative.as_posix()
    if re.search(r'<meta\b[^>]*\bhttp-equiv=["\']refresh["\']', page, re.I):
        return None
    if route in READER_SHELL_ROUTES:
        return READER_SHELL_ROUTES[route]
    if route.startswith('places/') or route.startswith('people/') or route.startswith('early-bearers'):
        title = re.search(r'<title\b[^>]*>(.*?)</title>', page, re.I | re.S)
        description = re.search(r'<meta\b(?=[^>]*\bname=["\']description["\'])[^>]*\bcontent=["\']([^"\']*)', page, re.I | re.S)
        if title:
            clean_title = re.sub(r'\s+·\s+Glasgow Surname Project\s*$', '', title[1].strip()).strip()
            return clean_title, description[1].strip() if description else clean_title
    return None


def _root_relative_markup(markup: str, base_url: str) -> str:
    """Resolve legacy relative href/src/action values before removing <base>."""
    attribute = re.compile(r'\b(href|src|action)=("|\')([^"\']*)', re.I)

    def replace(match):
        value = match[3]
        if not value or value.startswith(('#', '/', '//', 'data:', 'mailto:', 'tel:', 'javascript:')):
            return match[0]
        resolved = urljoin(base_url, value)
        if not resolved.startswith('/'):
            return match[0]
        return f'{match[1]}={match[2]}{resolved}'

    return attribute.sub(replace, markup)


def repair_reader_shell_page(page: str, relative: Path, template: str | None = None) -> str:
    """Put a legacy public reader page inside the maintained shared shell."""
    metadata = _reader_metadata(page, relative)
    if not metadata:
        return page
    if re.search(r'\bid="g-navigation"(?=\s|>)', page):
        # Stable reader routes may already have the correct rail but retain
        # the resources template's old page kind. Preserve everything else.
        if relative.as_posix() not in READER_SHELL_ROUTES:
            return page
        section = _reader_section(relative)
        kind = 'catalogue' if section == '/catalogue/' else 'research' if section == '/research/' else 'about'
        def normalise_kind(match):
            classes = match[3].split()
            expected = 'g-kind-' + kind
            if expected in classes and sum(c.startswith('g-kind-') for c in classes) == 1:
                return match[0]
            classes = [c for c in classes if not c.startswith('g-kind-')]
            classes.append(expected)
            return match[1] + match[2] + ' '.join(classes) + match[2]
        return re.sub(r'(<body\b[^>]*\bclass=)(["\'])(.*?)(?:\2)', normalise_kind, page, count=1, flags=re.I | re.S)
    old_main = re.search(r'<main\b[\s\S]*?</main>', page, re.I)
    shell = template if template is not None else (WEB / 'resources' / 'index.html').read_text(encoding='utf-8')
    shell_main = re.search(r'<main\b[\s\S]*?</main>', shell, re.I)
    if not old_main or not shell_main:
        return page
    title, description = metadata
    route = relative.as_posix()
    base_match = re.search(r'<base\b[^>]*\bhref=["\']([^"\']+)', page, re.I)
    base_url = urljoin('/' + route, base_match[1] if base_match else './')
    body = _root_relative_markup(old_main.group(0), base_url)
    result = shell[:shell_main.start()] + body + shell[shell_main.end():]
    result = re.sub(r'<title\b[^>]*>.*?</title>', f'<title>{title} · Glasgow Surname Project</title>', result, count=1, flags=re.I | re.S)
    result = re.sub(r'<meta\b(?=[^>]*\bname=["\']description["\'])[^>]*>',
                    f'<meta name="description" content="{description}">', result, count=1, flags=re.I | re.S)
    result = re.sub(r'<strong>Research resources</strong>', f'<strong>{title}</strong>', result, count=1)
    old_body = re.search(r'<body\b([^>]*)>', page, re.I)
    old_classes = ''
    if old_body:
        class_match = re.search(r'\bclass=["\']([^"\']*)', old_body[1], re.I)
        if class_match:
            old_classes = ' ' + class_match[1].strip()
    reader_section = _reader_section(relative)
    kind = ('branches' if reader_section == '/branches/' else
            'research' if reader_section == '/research/' else
            'catalogue' if reader_section == '/catalogue/' else 'about')
    result = re.sub(r'<body\b[^>]*>',
                    f'<body class="g-unified g-kind-{kind} v3-site{old_classes}" data-g-path="/{route}" data-v3="true" data-repair="3.1-repair-1">',
                    result, count=1, flags=re.I)
    canonical = re.search(r'<link\b(?=[^>]*\brel=["\']canonical["\'])[^>]*>', page, re.I | re.S)
    if canonical:
        result = re.sub(r'<link\b(?=[^>]*\brel=["\']canonical["\'])[^>]*>', canonical[0], result, count=1, flags=re.I | re.S)
    # Preserve page-specific styling and behaviour, especially forms, filter
    # tables, JSON-LD and correction/release scripts.
    base_styles = []
    extras = []
    for tag in re.findall(r'<link\b[^>]*>', page, flags=re.I):
        if re.search(r'\brel=["\']stylesheet["\']', tag, re.I) or re.search(r'\.css(?:[?"\'])', tag, re.I):
            tag = _root_relative_markup(tag, base_url)
            (base_styles if re.search(r'people/catalogue\.css', tag, re.I) else extras).append(tag)
    if base_styles:
        # Legacy card/form rules are loaded before the shared CSS so the
        # maintained shell controls body, rail, and footer geometry.
        result = result.replace('<head>', '<head>' + ''.join(base_styles), 1)
    if extras:
        result = result.replace('</head>', ''.join(extras) + '</head>', 1)
    inline_styles = re.findall(r'<style\b[^>]*>[\s\S]*?</style>', page, flags=re.I)
    if inline_styles:
        result = result.replace('</head>', ''.join(inline_styles) + '</head>', 1)
    json_ld = [tag for tag in re.findall(r'<script\b[^>]*>[\s\S]*?</script>', page, flags=re.I)
               if re.search(r'type=["\']application/ld\+json["\']', tag, re.I)]
    if json_ld:
        result = result.replace('</head>', ''.join(json_ld) + '</head>', 1)
    for tag in re.findall(r'<script\b[^>]*>[\s\S]*?</script>', page, flags=re.I):
        if re.search(r'data-(?:local-file-links|clean-index-redirect)|googletagmanager|gtag\(', tag, re.I):
            continue
        if re.search(r'type=["\']application/ld\+json["\']', tag, re.I):
            continue
        tag = _root_relative_markup(tag, base_url)
        result = result.replace('</body>', tag + '</body>', 1)
    return result


def repair_about_shell_page(page: str, relative: Path, template: str | None = None) -> str:
    """Backward-compatible focused wrapper for About-owned reader pages."""
    return repair_reader_shell_page(page, relative, template)


def repair_about_shell() -> Counter:
    """Apply only the About-owned clean and legacy shells."""
    changed = Counter()
    for route in READER_SHELL_ROUTES:
        if _reader_section(Path(route)) != '/about/':
            continue
        path = WEB / route
        if not path.exists():
            continue
        page = path.read_text(encoding='utf-8')
        updated = repair_about_shell_page(page, Path(route))
        if updated != page:
            path.write_text(updated, encoding='utf-8')
            changed['about_shell'] += 1
    return changed


def repair_reader_shell() -> Counter:
    """Apply the narrow reader-shell migration without running site builders."""
    changed = Counter()
    paths = [WEB / route for route in READER_SHELL_ROUTES]
    paths.extend(path for path in (WEB / 'places').rglob('*.html') if not is_excluded(path))
    paths.extend(path for path in (WEB / 'people').rglob('*.html') if not is_excluded(path))
    for route in ('early-bearers.html', 'early-bearers/index.html'):
        paths.append(WEB / route)
    seen = set()
    for path in paths:
        if not path.exists() or path in seen:
            continue
        seen.add(path)
        page = path.read_text(encoding='utf-8')
        updated = repair_reader_shell_page(page, path.relative_to(WEB))
        if updated != page:
            path.write_text(updated, encoding='utf-8')
            changed['reader_shell'] += 1
    return changed


def sync_section_submenu_assets() -> Counter:
    """Copy maintained submenu assets for both narrow and full repairs."""
    changed = Counter()
    for extension in ('js', 'css'):
        source = WEB.parent / 'tools' / f'section_submenus.{extension}'
        target = WEB / 'assets/unified' / f'section-submenus.{extension}'
        content = source.read_text(encoding='utf-8')
        if not target.exists() or target.read_text(encoding='utf-8') != content:
            target.write_text(content, encoding='utf-8')
            changed['section_submenus'] += 1
    return changed


def reorder_atlas_views(page: str) -> str:
    """Keep Whole tree first, including after older research markup is restored."""
    page = page.replace('THE COMPLETE CANOPY', 'THE WHOLE TREE')
    order = ('all', 'branches', 'lanes', 'dna')
    tabs = re.search(r'(<div\b(?=[^>]*\baria-label="(?:Atlas|Family tree) views")[^>]*>)(.*?)(</div>)', page, re.S)
    if not tabs:
        return page
    pattern = re.compile(r'<button\b(?=[^>]*\bdata-view="([^"]+)")[^>]*>.*?</button>', re.S)
    buttons = list(pattern.finditer(tabs[2]))
    sorted_buttons = iter(sorted(buttons, key=lambda item: order.index(item[1]) if item[1] in order else len(order)))
    body = pattern.sub(lambda _: next(sorted_buttons)[0], tabs[2]).replace('>Canopy<', '>Whole tree<')
    return page[:tabs.start(2)] + body + page[tabs.end(2):]


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
    changed = sync_section_submenu_assets()
    for path in WEB.rglob('*.html'):
        if is_excluded(path):
            continue
        relative = path.relative_to(WEB)
        page = path.read_text(encoding='utf-8')
        updated = repair_nav_only_page(page, relative)
        if relative.as_posix() == 'onetree/index.html':
            updated = reorder_atlas_views(updated)
        if updated != page:
            path.write_text(updated, encoding='utf-8')
            changed['primary_navigation'] += 1
    return changed


def repair():
    changed = Counter()
    changed.update(repair_reader_shell())
    changed.update(sync_section_submenu_assets())
    for path in WEB.rglob('*.html'):
        relative = path.relative_to(WEB)
        if 'glasgow-ydna-story-source' in relative.parts or path.name.endswith('-standalone.html'):
            continue
        page = path.read_text(encoding='utf-8')
        updated = NAV.sub(render_primary_navigation(relative), page, count=1)
        if relative.as_posix() == 'onetree/index.html':
            updated = reorder_atlas_views(updated)

        def sections(match):
            # Legacy secondary bars repeated unrelated primary destinations.
            # Purpose-built local controls use separate markup and are retained.
            return ""

        updated = SECTION_NAV.sub(sections, updated)
        if relative.as_posix() == 'catalogue/index.html' and 'href="/changes/"' not in updated:
            updated = updated.replace('</main>', '<p><a href="/changes/">Change log</a></p></main>', 1)
        if relative.as_posix() in {'status/index.html', 'status.html'} and 'class="g-nav-link" href="/research/"' not in updated:
            links = '<a class="g-nav-link" href="/research/">Research</a><a class="g-nav-link" href="/about/">About</a>'
            updated = updated.replace('</nav>', links + '</nav>', 1)
            updated = update_section_submenu_references(updated)
        if relative.parts[0] == 'people' and '<footer' not in updated:
            updated = updated.replace('</main>', '</main>' + PERSON_FOOTER, 1)
        def footer_links(match):
            footer = match.group(0)
            if not re.search(r'href="/changes(?:/|\.html)"', footer):
                footer = footer.replace('</nav>', '<a href="/changes/">Change log</a></nav>', 1)
            footer = re.sub(r'(<a\b[^>]*href="/changes(?:/|\.html)"[^>]*>)Latest research(</a>)', r'\1Change log\2', footer)
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
            latest = '<a href="/changes/">Change log</a>'
            if '</footer>' in updated:
                updated = updated.replace('</footer>', latest + '</footer>', 1)
        if NAV.search(updated):
            updated = update_section_submenu_references(updated)
        updated = repair_site_identity_page(updated, relative)
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
    parser.add_argument('--about-shell-only', action='store_true', help='wrap clean change log and feedback pages in the shared shell')
    parser.add_argument('--reader-shell-only', action='store_true', help='wrap legacy public reader pages in the shared shell')
    parser.add_argument('--identity-only', action='store_true', help='apply only the site name, breadcrumb, rail foot and footer pass')
    args = parser.parse_args()
    if args.identity_only:
        print(dict(repair_site_identity()))
    elif args.reader_shell_only:
        print(dict(repair_reader_shell()))
    elif args.about_shell_only:
        print(dict(repair_about_shell()))
    else:
        print(dict(repair_nav_only() if args.nav_only else repair()))
