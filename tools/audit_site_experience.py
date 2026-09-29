"""Read-only presentation contracts; browser checks cover computed visibility."""
from html.parser import HTMLParser
from pathlib import Path
import json
import re

WEB = Path(__file__).resolve().parents[1] / 'www'
COMMUNITY = (
    'https://www.wikitree.com/wiki/Space:Glasgow_Name_Study',
    'https://groups.io/g/glasgowdnaproject/',
    'https://glasgowfamilygenealogy.org/',
)
# Destinations folded out of the primary rail, mapped to the rail section whose
# submenu now offers them.
SUBMENU_DESTINATIONS = {'/statistics/': '/research/', '/resources/': '/about/'}


class Element:
    def __init__(self, tag, attrs, parent):
        self.tag, self.attrs, self.parent = tag, dict(attrs), parent
        self.children = []

    def has_class(self, value):
        return value in (self.attrs.get('class') or '').split()

    def ancestors(self):
        node = self.parent
        while node:
            yield node
            node = node.parent

    def exposed(self):
        chain = [self, *self.ancestors()]
        for index, node in enumerate(chain):
            if 'hidden' in node.attrs or node.attrs.get('aria-hidden') == 'true':
                return False
            if re.search(r'(?:display\s*:\s*none|visibility\s*:\s*hidden)', node.attrs.get('style') or '', re.I):
                return False
            if node.tag == 'details' and 'open' not in node.attrs:
                if not any(child.tag == 'summary' and child.parent is node for child in chain[:index]):
                    return False
        return True


class Page(HTMLParser):
    VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}

    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.nodes, self.stack = [], []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        node = Element(tag, attrs, self.stack[-1] if self.stack else None)
        if node.parent:
            node.parent.children.append(node)
        self.nodes.append(node)
        if tag not in self.VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in self.VOID:
            self.stack.pop()

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                break

    def links(self, href):
        return [node for node in self.nodes if node.tag == 'a' and node.attrs.get('href') == href]


def audit(web=WEB):
    failures, checks = [], 0
    cache = {}

    def page(relative):
        if relative not in cache:
            path = web / relative
            cache[relative] = Page(path.read_text(encoding='utf-8')) if path.exists() else Page('')
        return cache[relative]

    def require(condition, message):
        nonlocal checks
        checks += 1
        if not condition:
            failures.append(message)

    for relative in ('index.html', 'resources/index.html'):
        document = page(relative)
        for href in COMMUNITY:
            require(any(link.exposed() and any(n.tag == 'main' for n in link.ancestors())
                        for link in document.links(href)), f'{relative}: missing prominent community link {href}')

    for relative in ('catalogue/index.html', 'status/index.html', 'data/index.html'):
        document = page(relative)
        require(any(link.exposed() for link in document.links('/changes/')), f'{relative}: missing accessible Latest research / Change log link')
        # Statistics and Resources are folded into the Research and About
        # section submenus (tools/section_submenus.js); the primary rail must
        # keep their owning sections and load the submenu script.
        # Compact utility pages deliberately omit the full navigation rail.
        # Their direct Change log link above is the functional discovery route.
        has_primary_nav = any(node.has_class('g-nav-link') for node in document.nodes)
        if has_primary_nav:
            for href, owner in SUBMENU_DESTINATIONS.items():
                require(any(link.has_class('g-nav-link') for link in document.links(owner)), f'{relative}: missing primary destination {owner} (owner of {href})')
                require(any(node.tag == 'script' and 'section-submenus.js' in (node.attrs.get('src') or '') for node in document.nodes),
                        f'{relative}: missing section submenu script providing {href}')

    submenu_script = web / 'assets/unified/section-submenus.js'
    submenu_source = submenu_script.read_text(encoding='utf-8') if submenu_script.exists() else ''
    for href, owner in SUBMENU_DESTINATIONS.items():
        require(f"make('{href}'" in submenu_source, f'section submenus: {owner} submenu does not offer {href}')

    for slug in ('glasgow-2223', 'glasgow-951'):
        document = page(f'people/{slug}.html')
        href = 'https://www.wikitree.com/wiki/' + slug.replace('glasgow-', 'Glasgow-')
        require(any(link.exposed() and (any(n.has_class('profile-wikitree-actions') or n.has_class('dossier-actions') for n in link.ancestors()))
                    for link in document.links(href)), f'{slug}: missing exposed own WikiTree action')
        require(any(node.has_class('dossier-header') for node in document.nodes)
                or any(node.attrs.get('id') == 'person-summary' for node in document.nodes),
                f'{slug}: missing person summary')
        folds = [node for node in document.nodes if node.has_class('person-technical-fold') or node.attrs.get('id') == 'archive-tools']
        require(all(node.tag == 'details' and 'open' not in node.attrs for node in folds), f'{slug}: technical material not collapsed')

    summary_sizes = []
    for relative in ('catalogue/index.html', 'statistics/index.html'):
        summaries = [node for node in page(relative).nodes if node.has_class('statistics-summary')]
        summary_sizes.append(len([node for node in summaries[0].children if node.tag == 'div']) if summaries else 0)
    require(summary_sizes[0] > 1 and summary_sizes[0] == summary_sizes[1], 'statistics: headline totals differ from the maintained catalogue')
    panels = [node for node in page('statistics/index.html').nodes if node.has_class('statistics-panel')]
    require(len(panels) >= 7 and all(node.exposed() for node in panels), 'statistics: detailed panels missing or collapsed')

    feed = page('changes/index.html')
    require(any(node.attrs.get('id') == 'latest-research' for node in feed.nodes), 'changes: missing Latest research feed')
    entries = [node for node in feed.nodes if node.has_class('latest-research-entry')]
    require(bool(entries), 'changes: empty Latest research feed')
    require(any(node.tag == 'time' and re.fullmatch(r'\d{4}-\d{2}-\d{2}', node.attrs.get('datetime') or '') for node in feed.nodes), 'changes: no recorded feed dates')

    families = page('branches/index.html')
    for anchor in ('experience-regions', 'research-studies', 'irish-research-studies'):
        require(any(node.attrs.get('id') == anchor for node in families.nodes), f'families: missing preserved regional anchor {anchor}')
    study_cards = [node for node in families.nodes if node.has_class('bd-card')]
    group_ids = [node.attrs.get('data-group-id') for node in study_cards]
    require(len(group_ids) == len(set(group_ids)), 'families: duplicate data-group-id among study cards')
    directory_path = WEB / 'assets/research/branches-directory.json'
    require(directory_path.exists(), 'families: missing branches-directory.json')
    if directory_path.exists():
        directory = json.loads(directory_path.read_text(encoding='utf-8'))
        allowed_precision = {'exact', 'parish', 'settlement', 'county', 'country', 'none'}
        for group in directory.get('groups', []):
            value = group.get('precision')
            require(value in allowed_precision, f'families: invalid precision for {group.get("id", "unknown")}')
            coords_null = group.get('lat') is None and group.get('lon') is None
            require(coords_null == (value == 'none'), f'families: coordinates and precision disagree for {group.get("id", "unknown")}')
    return {'experience_checks': checks, 'experience_failures': len(failures)}, failures


if __name__ == '__main__':
    import json
    summary, failures = audit()
    print(json.dumps(summary))
    for failure in failures:
        print('FAIL ' + failure)
    raise SystemExit(bool(failures))
