"""Build a sitemap from approved public indexes and maintained reader sections.

Do not crawl the website tree indiscriminately: it also contains data files,
fragments, legacy redirects and release bundles that are not reader pages.
Unknown modification dates are omitted; export/build timestamps are not claims
that the underlying research changed.
"""
from __future__ import annotations

from datetime import date
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
    return {"sitemap_urls": len(entries)}


if __name__ == "__main__":
    print(build_sitemap())
