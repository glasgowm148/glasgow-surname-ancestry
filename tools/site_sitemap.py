"""Build a sitemap from approved public indexes and maintained reader sections.

Do not crawl the website tree indiscriminately: it also contains data files,
fragments, legacy redirects and release bundles that are not reader pages.
Unknown modification dates are omitted; export/build timestamps are not claims
that the underlying research changed.
"""
from __future__ import annotations

from datetime import date
import hashlib
from html import escape, unescape
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit
import xml.etree.ElementTree as ET

from tools.site_search import PUBLIC_ROUTES

ROOT = Path(__file__).resolve().parents[1]
SITE_URL = "https://glasgow.phenotype.dev"
NAMESPACE = "http://www.sitemaps.org/schemas/sitemap/0.9"
BLOCKED_PARTS = {"assets", "private", "private-research", "raw", "archive", "fragments", "reference"}
EDITORIAL_ROOTS = ("research", "latest-findings", "early-records", "branches", "compare", "dna")
BROWSE_ROOTS = ("people/by-name", "people/clusters", "people/locations", "catalogue/browse", "sources/browse")
# Source-library browse pages (sources/<type>/<country>/...).  Individual
# source pages (s-<16 hex>) come only from the approved source index.
SOURCE_ITEM = re.compile(r"s-[a-f0-9]{16}")
# Reader pages deliberately left out of the sitemap (site audit S1-07, S1-11,
# S3-11).  Each is still served; the reason is recorded here.
EXCLUDED_ROUTES = {
    "/explore/": "superseded entry page with no generator; nothing links to it",
    "/research/tools.html": "superseded 'research desk' page with no generator; nothing links to it",
    "/events/": "legacy life-events view with no generator; nothing links to it",
}
EXCLUDED_PREFIXES = {
    "/research/queue/": "research workroom: leads, not findings",
    "/candidate-matches/": "research workroom: ranked leads, not findings",
}

READER_GROUPS = (
    ("people", "People and catalogue", ("catalogue", "people", "early-records")),
    ("families", "Families and places", ("branches", "places")),
    ("tree", "Family tree and DNA", ("onetree", "map", "dna", "ydna", "timeline", "connections")),
    ("sources", "Records and sources", ("sources", "records", "research/transcriptions")),
    ("research", "Research and findings", ("research", "latest-findings", "free-space", "compare", "candidate-matches")),
    ("about", "About and help", ()),
)


def reader_group(route):
    for key, _, roots in READER_GROUPS:
        if any(route == "/" + root + "/" or route.startswith("/" + root + "/") for root in roots):
            return key
    return "about"


def directory_route(route):
    """Individual entities remain in their existing complete public directories."""
    if re.fullmatch(r"/people/[^/]+\.html|/places/[^/]+\.html|/sources/s-[a-f0-9]{16}/", route):
        return False
    if re.search(r"/(?:page/\d+/|page-\d+\.html)$", route):
        return False
    return route != "/sitemap/"


def reader_pages(site_root, entries):
    """Use approved XML readers plus explicitly published public workrooms.

    Search-engine exclusion is not a reason to hide a public research tool from
    readers. Private/unlisted files are never discovered by crawling here.
    """
    routes = set(entries)
    registered = {row[1]: row for row in PUBLIC_ROUTES}
    for candidate in registered:
        if candidate.startswith(tuple(EXCLUDED_PREFIXES)):
            result = safe_route(candidate, site_root)
            if result:
                routes.add(result[0])
    rows = []
    for route in sorted(routes):
        if not directory_route(route):
            continue
        if route in registered:
            title, _, _, description, _ = registered[route]
        else:
            _, path = safe_route(route, site_root)
            with path.open() as handle:
                head = handle.read(65_536).split("</head>", 1)[0]
            match = re.search(r"<title\b[^>]*>(.*?)</title>", head, re.I | re.S)
            title = unescape(re.sub(r"<[^>]+>", "", match[1])) if match else route.strip("/").replace("-", " ")
            title = re.sub(r"\s*[·|]\s*(?:The )?Glasgow Surname Project\s*$", "", title, flags=re.I)
            description = ""
        rows.append(dict(url=route, title=" ".join(title.split()), description=description, group=reader_group(route)))
    return sorted(rows, key=lambda row: (row["title"].casefold(), row["url"]))


def build_reader_sitemap(site_root, entries):
    """Render a searchable human directory from the same publication boundary."""
    site_root = Path(site_root)
    rows = reader_pages(site_root, entries)
    cards = []
    for label, url in (
        ("People", "/catalogue/"),
        ("Places", "/places/"),
        ("Source references", "/sources/browse/"),
    ):
        target = safe_route(url, site_root)
        if target:
            cards.append(f'<a href="{escape(target[0])}"><strong>{label}</strong><small>Browse the complete directory →</small></a>')
    sections = []
    jumps = []
    for key, title, _ in READER_GROUPS:
        members = [row for row in rows if row["group"] == key]
        if not members:
            continue
        jumps.append(f'<a href="#{key}">{escape(title)}</a>')
        links = []
        for row in members:
            description = f'<small>{escape(row["description"])}</small>' if row["description"] else ""
            links.append(f'<li><a href="{escape(row["url"], quote=True)}">{escape(row["title"])}</a>{description}</li>')
        sections.append(f'<section class="sitemap-group" id="{key}"><h2>{escape(title)} <small>({len(members):,})</small></h2>'
                        f'<details><summary>Browse {len(members):,} pages</summary><ul>{"".join(links)}</ul></details></section>')
    assets = {}
    for extension in ("css", "js"):
        content = (ROOT / "tools/site_sources" / f"sitemap.{extension}").read_text()
        target = site_root / "assets/unified" / f"sitemap.{extension}"
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists() or target.read_text() != content:
            target.write_text(content)
        assets[extension] = "/assets/unified/" + target.name + "?v=" + hashlib.sha256(content.encode()).hexdigest()[:10]
    body = ('<main id="main" class="sitemap-main"><header><p class="kicker">Explore the project</p><h1>Site map</h1>'
            '<p>Find family studies, historical records and research tools. '
            '<a href="/catalogue/">The research catalogue</a> brings together people, evidence, relationships and proposed WikiTree updates.</p></header>'
            '<p class="sitemap-work"><a href="/catalogue/?needsUpdate=1#catalogue-filters">WikiTree updates</a> · '
            '<a href="/catalogue/?missingProfile=1#catalogue-filters">No WikiTree link</a> · '
            '<a href="/catalogue/#research-queue">Held and pending research</a></p>'
            f'<div class="sitemap-directories">{"".join(cards)}</div>'
            '<p>Individual people, places and source references are listed in the complete directories above. '
            'The sections below link to the site’s guides, studies and tools.</p>'
            f'<nav class="sitemap-jumps" aria-label="Site map sections">{"".join(jumps)}</nav>'
            '<div class="sitemap-search" hidden><label for="sitemap-search">Find a page</label>'
            '<input type="search" id="sitemap-search" placeholder="Try Scottish families, wills or confidence…" autocomplete="off">'
            f'<p id="sitemap-count" role="status">{len(rows):,} pages</p></div>'
            f'{"".join(sections)}<p id="sitemap-empty" hidden>No pages match. Try another name or topic.</p>'
            '<p class="sitemap-footer"><a href="/sitemap.xml">XML sitemap</a> · '
            '<a href="/feedback/">Report a missing page or broken link</a></p></main>')
    page = ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1"><title>Site map · Glasgow Surname Project</title>'
            f'<link rel="canonical" href="{SITE_URL}/sitemap/">'
            f'<link rel="stylesheet" href="{assets["css"]}"></head><body>{body}'
            f'<script src="{assets["js"]}" defer></script></body></html>')
    if (site_root / "resources/index.html").is_file():
        from tools.repair_primary_navigation import repair_reader_shell_page, repair_site_identity_page, repair_nav_only_page
        relative = Path("sitemap/index.html")
        page = repair_reader_shell_page(page, relative, (site_root / "resources/index.html").read_text())
        page = repair_site_identity_page(page, relative)
        page = repair_nav_only_page(page, relative)
    path = site_root / "sitemap/index.html"
    # A targeted build can follow a shared-search update without a site-wide
    # finalizer. Stamp this reader against the actual local assets as well.
    from tools.stamp_asset_versions import VERSIONED_ASSET, asset_path, content_hash
    def version(match):
        target = asset_path(site_root, path, match["url"])
        if target is None or not target.is_file():
            return match[0]
        return f'{match["quote"]}{match["url"]}?v={content_hash(target)}{match["quote"]}'
    page = VERSIONED_ASSET.sub(version, page)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists() or path.read_text() != page:
        path.write_text(page)
    return len(rows)


def source_browse_pages(site_root):
    """Yield source-library browse pages without walking every source item."""
    root = site_root / "sources"
    for directory, subdirectories, files in os.walk(root):
        subdirectories[:] = sorted(d for d in subdirectories if not SOURCE_ITEM.fullmatch(d) and d not in BLOCKED_PARTS)
        for name in sorted(files):
            if name.endswith(".html"):
                yield "/" + (Path(directory) / name).relative_to(site_root).as_posix()


def excluded(route):
    return route in EXCLUDED_ROUTES or route.startswith(tuple(EXCLUDED_PREFIXES))


class HeadMetadata(HTMLParser):
    def __init__(self):
        super().__init__()
        self.noindex = False
        self.modified = None
        self.canonical = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "link" and "canonical" in (attrs.get("rel") or "").lower().split():
            self.canonical = attrs.get("href")
        if tag != "meta":
            return
        name = (attrs.get("name") or attrs.get("property") or "").lower()
        value = attrs.get("content") or ""
        if name in {"robots", "googlebot", "bingbot"} and "noindex" in value.lower():
            self.noindex = True
        if name in {"article:modified_time", "datemodified", "date-modified"}:
            self.modified = valid_date(value)


def valid_date(value):
    value = str(value or "")[:10]
    try:
        return value if date.fromisoformat(value) <= date.today() else None
    except ValueError:
        return None


def safe_route(value, site_root):
    """Canonicalize a real local HTML reader, refusing traversal and artifacts."""
    parsed = urlsplit(str(value or ""))
    if parsed.scheme or parsed.netloc:
        if parsed.scheme != "https" or parsed.netloc != urlsplit(SITE_URL).netloc:
            return None
    path = unquote(parsed.path)
    if not path.startswith("/") or parsed.query or parsed.fragment or "\\" in path:
        return None
    relative = Path(path.lstrip("/"))
    if any(part.startswith(".") or part in BLOCKED_PARTS for part in relative.parts):
        return None
    target = site_root / relative
    if target.is_dir():
        target = target / "index.html"
    try:
        target.resolve().relative_to(site_root.resolve())
    except ValueError:
        return None
    if target.suffix != ".html" or not target.is_file() or target.is_symlink():
        return None
    relative = target.relative_to(site_root)
    if relative.name == "index.html":
        path = "/" if relative.parent == Path(".") else "/" + relative.parent.as_posix() + "/"
    else:
        directory = target.with_suffix("")
        if (directory / "index.html").is_file():
            # Legacy HTML aliases of current clean directory readers.
            return safe_route("/" + directory.relative_to(site_root).as_posix() + "/", site_root)
        path = "/" + relative.as_posix()
    return path, target


def read_index(site_root, path):
    source = site_root / path
    if not source.exists():
        return []
    rows = json.loads(source.read_text())
    if not isinstance(rows, list):
        raise ValueError(f"Expected a public list index: {path}")
    return rows


def eligible(row):
    """Public indexes already exclude withheld people; fail closed on flags."""
    if any(row.get(key) in (True, 1, "1", "true", "True")
           for key in ("living", "isLiving", "is_living", "withheld", "private", "restricted")):
        return False
    privacy = row.get("privacy", row.get("Privacy"))
    return privacy is None or str(privacy) == "60"


def sitemap_entries(site_root=ROOT / "www"):
    site_root = Path(site_root)
    candidates = [row[1] for row in PUBLIC_ROUTES] + ["/people/", "/people/early-bearers/"]
    people = read_index(site_root, "data/people-index.json")
    approved_people = set()
    for row in people:
        if eligible(row):
            url = row.get("html_url")
            if url:
                candidates.append(url)
                approved_people.add(urlsplit(url).path)
    for filename in ("data/places-index.json", "assets/research/branches.json", "assets/research/free-space-index.json"):
        candidates.extend(row.get("url") for row in read_index(site_root, filename) if eligible(row))
    for row in read_index(site_root, "assets/v3/source-index.json"):
        if eligible(row) and re.fullmatch(r"s-[a-f0-9]{16}", str(row.get("id", ""))):
            candidates.append("/sources/" + row["id"] + "/")
    for root in (*EDITORIAL_ROOTS, *BROWSE_ROOTS):
        candidates.extend("/" + p.relative_to(site_root).as_posix()
                          for p in sorted((site_root / root).rglob("*.html")))
    candidates.extend(source_browse_pages(site_root))
    entries = {}
    for candidate in candidates:
        result = safe_route(candidate, site_root)
        if result is None:
            continue
        route, path = result
        if excluded(route):
            continue
        # Entity profiles must be listed in the approved public person index;
        # no loose HTML scan or a malicious editorial filename can add one.
        if re.fullmatch(r"/people/[^/]+\.html", route) and route not in approved_people:
            continue
        if route in entries:
            continue
        with path.open() as handle:
            head = handle.read(65_536).split("</head>", 1)[0]
        if not re.search(r"<html\b", head, re.I):
            continue
        metadata = HeadMetadata()
        metadata.feed(head)
        if metadata.noindex or "data-clean-route-redirect" in head:
            continue
        if metadata.canonical:
            canonical = safe_route(metadata.canonical, site_root)
            if canonical and canonical[0] != route:
                continue  # Index the canonical reader rather than its duplicate.
        entries[route] = metadata.modified
    return entries


def build_sitemap(site_root=ROOT / "www") -> dict[str, int]:
    site_root = Path(site_root)
    entries = sitemap_entries(site_root)
    reader_count = build_reader_sitemap(site_root, entries)
    entries["/sitemap/"] = None
    ET.register_namespace("", NAMESPACE)
    urlset = ET.Element(f"{{{NAMESPACE}}}urlset")
    for route, modified in sorted(entries.items()):
        url = ET.SubElement(urlset, f"{{{NAMESPACE}}}url")
        ET.SubElement(url, f"{{{NAMESPACE}}}loc").text = SITE_URL + route
        if modified:
            ET.SubElement(url, f"{{{NAMESPACE}}}lastmod").text = modified
    ET.indent(urlset)
    content = '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(urlset, encoding="unicode") + "\n"
    path = site_root / "sitemap.xml"
    if not path.exists() or path.read_text() != content:
        path.write_text(content)
    return {"sitemap_urls": len(entries), "sitemap_reader_pages": reader_count}


if __name__ == "__main__":
    print(build_sitemap())
