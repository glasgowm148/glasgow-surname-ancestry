#!/usr/bin/env python3
"""Who links to whom: one reverse-link index for person, study and place pages.

Links on the site run one way: studies, places, source pages, Latest findings
and other people's research notes point at a person, and the person page
points back to none of them. This module computes the reverse direction once,
so that page builders can show what refers to each page.

Output: ``www/data/person-links.json`` (``INDEX_PATH``), beside the other
builder-derived JSON in ``www/data/`` (``latest-findings-index.json``,
``places-index.json``). It holds only what public pages already show, and the
release publication-boundary check scans it with the rest of ``www/``.
Rebuilding without input changes gives a byte-identical file.

Reader API (stable; the person-page renderer depends on it)
-----------------------------------------------------------
``load_person_links(profile_id) -> dict`` returns, for one WikiTree ID (an
alternate ID or a different letter case also works), always this shape::

    {
      "studies":   [{"title": str, "url": str}],   # /branches/... family and study pages
      "places":    [{"title": str, "url": str}],   # /places/... pages that list the person
      "sources":   [{"title": str, "url": str}],   # /sources/<id>/ pages, at most SOURCES_SHOWN
      "sources_total": int,                         # all source pages citing the person
      "findings":  [{"date": "YYYY-MM-DD", "title": str, "url": str}],  # newest first
      "research":  [{"title": str, "url": str}],   # /research/... and /free-space/... pages
      "mentioned_by": [{"id": str, "name": str, "url": str, "section": str}],
    }

Lists are empty (and ``sources_total`` is 0) when the index file is missing or
the person is not in it. Results are cached per process; ``clear_cache()``
drops the cache. ``studies`` lists membership first (the person is in the
group's member list or a study cluster) and pages that only link the person
after it, so a renderer should use neutral wording such as "Family and study
pages" rather than claiming membership. ``mentioned_by`` holds one row per
note section of another person that mentions this person; ``url`` opens that
section on the other person's page (``#research-note-…``).

``load_page_links(url) -> dict`` returns, for a study page (``/branches/x/``),
``{"title", "places": [{title, url, shared_people, via}], "places_total"}``
and, for a place page (``/places/x.html``), the same with ``studies`` and
``studies_total``. ``shared_people`` counts people listed on both pages;
``via`` says how the relation was found (``shared-people``,
``named-in-study-text``).

How each relation is derived (also written to the index as ``derivation``)
---------------------------------------------------------------------------
- studies: ``www/assets/research/branches.json`` member lists (written by the
  catalogue build) and ``tools/study_stories/<id>.json`` clusters and person
  links; plus person links inside ``<main>`` of the built study page
  ``www/branches/<id>/index.html``. Region pages (kind ``region``) list
  family groups, not people, and are left out.
- places: person links inside ``<main>`` of the built place pages
  ``www/places/*.html``. The place builder keeps its records in memory only,
  so the built page is the published list.
- sources: ``www/assets/v3/sources/<id>.json`` (the data the source reader
  and ``tools/publish_static_sources.py`` render), people from citations,
  records and events, kept only when ``www/sources/<id>/index.html`` exists.
- findings: ``research/latest-findings.json``, ordered and paged exactly as
  ``tools/build_latest_findings.py`` does (50 rows a page).
- research: person links and WikiTree IDs inside ``<main>`` of the built
  ``www/research/{subjects,queue,transcriptions}/*/`` and
  ``www/free-space/*/`` pages; listing pages and superseded drafts are skipped.
- mentioned_by: ``research/<ID>/findings.md`` through
  ``tools.build_research_catalog._load_research_findings`` (published
  sections only), passed through the public privacy projection as
  ``tools/sync_catalogue_research.public_findings`` does.

Build order: run after the catalogue build, the study pages, the source pages,
the free-space and research pages and ``build_latest_findings``, and before
the person pages are rendered. ``write_index()`` builds and writes the index
and clears the reader cache; a person-page render pass should call it first.
``python tools/build_backlinks.py`` does the same from the shell (``--check``
compares without writing). The index never reads person pages, and it
reads only person links (never place links) from built study pages, so pages
that render from it cannot feed back into it.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import copy
from datetime import date
from functools import lru_cache
import hashlib
from html import unescape
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urljoin, urlsplit

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "www"
INDEX_RELATIVE = "data/person-links.json"
INDEX_PATH = WEB / INDEX_RELATIVE
STORIES = ROOT / "tools/study_stories"
LEDGER = ROOT / "research/latest-findings.json"
RESEARCH = ROOT / "research"
CASES_MANIFEST = ROOT / "data/wikitree/research-catalogue-cases.json"
SITE_HOST = "glasgow.phenotype.dev"
SCHEMA_VERSION = 1
SOURCES_SHOWN = 10
PAGE_LINKS_SHOWN = 12
FINDINGS_PER_PAGE = 50  # tools/build_latest_findings.py::repair
FINDING_TITLE_LIMIT = 160
SOURCE_TITLE_LIMIT = 120
_SOURCE_FILE_TITLE = re.compile(r"(?:^\.\.?/|\.md\b|\|-)")
TOP_MENTIONED = 10
PERSON_LIST_KEYS = ("studies", "places", "sources", "findings", "research", "mentioned_by")
# Same token rule as tools/public_privacy.PROFILE_TOKEN.
PROFILE_TOKEN = re.compile(r"\b[A-Za-z][A-Za-z_'’]*(?:-[A-Za-z][A-Za-z_'’]*)*-\d+\b")
STUDY_KIND_ORDER = {"place": 0, "research": 1, "family": 2}
# Place names that collide with the surname or name whole countries.
PLACE_NAME_STOP = {
    "glasgow", "scotland", "ireland", "england", "wales", "united states", "united kingdom",
    "usa", "canada", "australia", "new zealand", "ulster", "location not specified",
}
RESEARCH_PAGE_GLOBS = (
    "research/subjects/*/index.html",
    "research/transcriptions/*/index.html",
    "research/queue/*/index.html",
    "free-space/*/index.html",
)
DERIVATION = {
    "studies": "Member lists in www/assets/research/branches.json and clusters and person links in "
               "tools/study_stories/<id>.json; plus person links in <main> of the built study page "
               "www/branches/<id>/index.html. Region pages are left out.",
    "places": "Person links in <main> of the built place pages www/places/*.html.",
    "sources": "People named in citations, records and events of www/assets/v3/sources/<id>.json "
               "where www/sources/<id>/index.html exists; record pages first, then family-tree exports, "
               "then pages titled with a repository path or table fragment.",
    "findings": "research/latest-findings.json, ordered and paged as tools/build_latest_findings.py does.",
    "research": "Person links and WikiTree IDs in <main> of the built research subject, transcription and "
                "queue pages and free-space pages; listing pages and superseded drafts are skipped.",
    "mentioned_by": "Published sections of research/<ID>/findings.md via "
                    "tools.build_research_catalog._load_research_findings and the public privacy "
                    "projection; self-mentions excluded.",
    "pages": "Study and place pages that list the same people (shared-people: study members, not people a "
             "study only discusses) or whose names appear in the study's maintained text (named-in-study-text).",
}

_MAIN = re.compile(r"<main\b[^>]*>(.*)</main>", re.I | re.S)
_BODY = re.compile(r"<body\b[^>]*>(.*)</body>", re.I | re.S)
_DROP = re.compile(r"<(script|style)\b[^>]*>.*?</\1\s*>", re.I | re.S)
_HREF = re.compile(r"""<a\b[^>]*?\bhref\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+))""", re.I | re.S)
_BASE = re.compile(r"""<base\b[^>]*?\bhref\s*=\s*["']([^"']*)["']""", re.I)
_H1 = re.compile(r"<h1\b[^>]*>(.*?)</h1>", re.I | re.S)
_TITLE = re.compile(r"<title\b[^>]*>(.*?)</title>", re.I | re.S)
_TAG = re.compile(r"<[^>]+>")
_NOINDEX = re.compile(r"""<meta\b[^>]*name=["']robots["'][^>]*noindex""", re.I)
_MD_LINK = re.compile(r"\[([^\]]*)\]\(\s*<?([^)\s>]+)>?(?:\s+[^)]*)?\)")
_PEOPLE_PATH = re.compile(r"/people/([^/?#]+)\.html")
_WIKITREE = re.compile(r"^https?://(?:www\.)?wikitree\.com/wiki/([^?#]+)", re.I)


def empty_person_links() -> dict:
    """The shape ``load_person_links`` always returns."""
    return {"studies": [], "places": [], "sources": [], "sources_total": 0,
            "findings": [], "research": [], "mentioned_by": []}


def research_note_anchor(path: str, title: str) -> str:
    """Anchor of one research-note section on a person page.

    Mirrors ``tools/repair_person_hierarchy._research_note_anchor`` (checked by
    ``tests/test_backlinks.py``) without importing the page renderer.
    """
    return "research-note-" + hashlib.sha256((path.lstrip("/") + "|" + title).encode()).hexdigest()[:12]


def _text(fragment: str) -> str:
    return re.sub(r"\s+", " ", unescape(_TAG.sub(" ", fragment or ""))).strip()


def page_url(relative: str) -> str:
    """Public URL of a file under the site root: ``x/index.html`` is ``/x/``."""
    if relative == "index.html":
        return "/"
    if relative.endswith("/index.html"):
        return "/" + relative[: -len("index.html")]
    return "/" + relative


class _People:
    """Public person pages, looked up by WikiTree ID (any case, alternates) or slug."""

    def __init__(self):
        self.rows: dict[str, dict] = {}
        self.by_id: dict[str, str] = {}
        self.by_slug: dict[str, str] = {}
        self.withheld = 0

    def add(self, row: dict) -> None:
        self.rows[row["id"]] = row
        self.by_slug[row["slug"].casefold()] = row["id"]
        for ident in (row["id"], *row["alternate_ids"]):
            self.by_id.setdefault(ident.casefold(), row["id"])

    def from_url(self, url: str) -> str | None:
        parts = urlsplit(url)
        if parts.netloc in ("", SITE_HOST, "www." + SITE_HOST):
            match = _PEOPLE_PATH.fullmatch(unquote(parts.path))
            return self.by_slug.get(match.group(1).casefold()) if match else None
        match = _WIKITREE.match(url)
        if match:
            return self.by_id.get(unquote(match.group(1)).replace(" ", "_").casefold())
        return None

    def in_text(self, text: str) -> set[str]:
        return {self.by_id[token.casefold()] for token in PROFILE_TOKEN.findall(text or "")
                if token.casefold() in self.by_id}


def _blocked(policy, *identifiers) -> bool:
    return bool(policy) and any(str(i).casefold() in policy.blocked for i in identifiers if i)


def _load_people(site_root: Path, policy) -> _People:
    people = _People()
    index = site_root / "data/people-index.json"
    if index.is_file():
        rows = json.loads(index.read_text(encoding="utf-8"))
        rows = rows.get("people", []) if isinstance(rows, dict) else rows
    else:
        rows = []
        for path in sorted((site_root / "people").glob("*.json")):
            if path.name.endswith(".network.json"):
                continue
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except ValueError:
                continue
            rows.append({**data, "html_url": f"/people/{path.stem}.html"})
    for row in rows:
        ident = row.get("id")
        url = row.get("html_url") or (f"/people/{row['catalogue_id']}.html" if row.get("catalogue_id") else "")
        match = _PEOPLE_PATH.fullmatch(url or "")
        if not ident or not match or not (site_root / url.lstrip("/")).is_file():
            continue
        alternates = sorted({str(a) for a in row.get("alternate_ids") or [] if a and str(a) != ident})
        if _blocked(policy, ident, *alternates):
            people.withheld += 1
            continue
        people.add({"id": ident, "alternate_ids": alternates, "name": row.get("name") or ident,
                    "slug": match.group(1), "url": url})
    return people


class _Page:
    __slots__ = ("url", "title", "links", "text", "skip")


def _read_page(path: Path, site_root: Path) -> _Page:
    html = path.read_text(encoding="utf-8", errors="replace")
    page = _Page()
    page.url = page_url(path.relative_to(site_root).as_posix())
    base = "https://" + SITE_HOST + page.url
    base_match = _BASE.search(html)
    if base_match:
        base = urljoin(base, unescape(base_match.group(1)))
    title = _H1.search(html)
    page.title = _text(title.group(1)) if title else ""
    if not page.title:
        head = _TITLE.search(html)
        page.title = re.split(r"\s+[·|]\s+", _text(head.group(1)))[0] if head else page.url
    body = _MAIN.search(html) or _BODY.search(html)
    body = _DROP.sub(" ", body.group(1) if body else html)
    page.links = []
    for match in _HREF.finditer(body):
        href = unescape(next(g for g in match.groups() if g is not None)).strip()
        if href and not href.startswith(("#", "mailto:", "tel:", "javascript:", "data:")):
            page.links.append(urljoin(base, href))
    page.text = _text(body)
    page.skip = bool(_NOINDEX.search(html)) or "superseded" in page.title.casefold()
    return page


def _strings(value) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [s for key in sorted(value) for s in _strings(value[key])]
    if isinstance(value, list):
        return [s for item in value for s in _strings(item)]
    return []


def _studies(site_root: Path, stories_dir: Path, people: _People):
    """Per person: study entries; per study: (title, kind, people, maintained text)."""
    per_person: dict[str, dict[str, tuple]] = defaultdict(dict)
    studies: dict[str, dict] = {}
    path = site_root / "assets/research/branches.json"
    branches = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else []
    for branch in sorted(branches, key=lambda b: str(b.get("id"))):
        sid, kind = str(branch.get("id") or ""), branch.get("kind") or "family"
        page_path = site_root / "branches" / sid / "index.html"
        if not sid or kind == "region" or not page_path.is_file():
            continue
        url = f"/branches/{sid}/"
        story_path = stories_dir / f"{sid}.json"
        story = json.loads(story_path.read_text(encoding="utf-8")) if story_path.is_file() else {}
        if not isinstance(story, dict) or story.get("id") not in (None, sid):
            story = {}
        title = str(story.get("title") or branch.get("label") or sid)
        if kind == "family":
            title = f"Family group: {title}"
        listed = {people.by_slug.get(str(slug).casefold()) for slug in branch.get("members") or []}
        for cluster in story.get("clusters") or []:
            if isinstance(cluster, dict):
                listed |= {people.by_slug.get(str(slug).casefold()) for slug in cluster.get("people") or []}
        listed.discard(None)
        # Story prose and page links can discuss a person to rule them out, so
        # they never count as membership.
        text = " ".join([str(branch.get("label") or ""), str(branch.get("description") or ""), *_strings(story)])
        linked = {people.by_slug.get(slug.casefold()) for slug in _PEOPLE_PATH.findall(text)}
        page = _read_page(page_path, site_root)
        linked |= {people.from_url(link) for link in page.links}
        linked -= listed | {None}
        rank = STUDY_KIND_ORDER.get(kind, 3)
        for pid in listed:
            per_person[pid][url] = (0, rank, title.casefold(), title, url)
        for pid in linked:
            per_person[pid][url] = (1, rank, title.casefold(), title, url)
        studies[url] = {"title": title, "people": listed, "text": text}  # members only
    return per_person, studies


def _places(site_root: Path, people: _People):
    places: dict[str, dict] = {}
    for path in sorted((site_root / "places").glob("*.html")):
        if path.name == "index.html":
            continue
        page = _read_page(path, site_root)
        ids = {pid for pid in map(people.from_url, page.links) if pid}
        places[page.url] = {"title": page.title, "people": ids}
    return places


def _sources(site_root: Path, people: _People):
    per_person: dict[str, list[tuple]] = defaultdict(list)
    folder = site_root / "assets/v3/sources"
    for path in sorted(folder.glob("*.json")) if folder.is_dir() else []:
        if not (site_root / "sources" / path.stem / "index.html").is_file():
            continue
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except ValueError:
            continue
        citations = [c for c in doc.get("citations") or [] if isinstance(c, dict)]
        rows = citations + [r for key in ("records", "events") for r in doc.get(key) or [] if isinstance(r, dict)]
        ids = []
        for row in rows:
            ref = str(row.get("person") or "")
            pid = people.by_slug.get(ref.casefold()) or people.by_id.get(ref.casefold())
            if pid and pid not in ids:
                ids.append(pid)
        if not ids:
            continue
        title = re.sub(r"\s+", " ", str(doc.get("display_title") or doc.get("title") or path.stem)).strip()
        if _SOURCE_FILE_TITLE.search(title):
            rank = 2  # titled with a repository path or a table fragment
        elif (all(c.get("quality") == "tree_only" for c in citations) if citations
              else title.startswith("WikiTree profile export")):
            rank = 1  # a family-tree export, not a record
        else:
            rank = 0
        if len(title) > SOURCE_TITLE_LIMIT:  # the source page's own heading is cut the same way
            title = title[:SOURCE_TITLE_LIMIT].rsplit(" ", 1)[0].rstrip(",;:") + "…"
        url = f"/sources/{path.stem}/"
        for pid in ids:
            per_person[pid].append((rank, title.casefold(), title, url))
    return per_person


def _finding_title(text: str) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    first = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9“\"'(])", text, maxsplit=1)[0]
    if len(first) <= FINDING_TITLE_LIMIT:
        return first
    cut = first[: FINDING_TITLE_LIMIT].rsplit(" ", 1)[0].rstrip(",;:")
    return cut + "…"


def _findings(ledger: Path, people: _People):
    per_person: dict[str, list[dict]] = defaultdict(list)
    if not ledger.is_file():
        return per_person
    rows = []
    for item in json.loads(ledger.read_text(encoding="utf-8")).get("findings", []):
        try:
            found = date.fromisoformat(item["found_on"])
        except (KeyError, TypeError, ValueError):
            continue
        if item.get("id") and item.get("finding"):
            rows.append((-found.toordinal(), item["id"], item))
    rows.sort(key=lambda row: (row[0], row[1]))
    for index, (_, ident, item) in enumerate(rows):
        page = "/latest-findings/" if index < FINDINGS_PER_PAGE else f"/latest-findings/page/{index // FINDINGS_PER_PAGE + 1}/"
        entry = {"date": item["found_on"], "title": _finding_title(item["finding"]), "url": f"{page}#finding-{ident}"}
        seen = set()
        for person in item.get("people") or []:
            pid = people.by_id.get(str(person.get("id") or "").casefold()) or people.from_url(str(person.get("url") or ""))
            if pid and pid not in seen:
                seen.add(pid)
                per_person[pid].append(entry)
    return per_person


def _research(site_root: Path, people: _People):
    per_person: dict[str, dict[str, tuple]] = defaultdict(dict)
    for pattern in RESEARCH_PAGE_GLOBS:
        rank = 1 if pattern.startswith("free-space/") else 0
        for path in sorted(site_root.glob(pattern)):
            page = _read_page(path, site_root)
            if page.skip:
                continue
            ids = {pid for pid in map(people.from_url, page.links) if pid} | people.in_text(page.text)
            for pid in ids:
                per_person[pid][page.url] = (rank, page.title.casefold(), page.title, page.url)
    return per_person


def _mentioned_ids(markdown: str, people: _People) -> set[str]:
    """People a Markdown note names by WikiTree ID, wiki link or person-page link."""
    found = set()

    def link(match):
        target = match.group(2)
        pid = people.from_url(urljoin("https://" + SITE_HOST + "/", target)) if not _WIKITREE.match(target) else people.from_url(target)
        if pid:
            found.add(pid)
        return " " + match.group(1) + " "

    text = _MD_LINK.sub(link, markdown or "")
    found |= people.in_text(text)
    found |= {people.by_slug[slug.casefold()] for slug in _PEOPLE_PATH.findall(text) if slug.casefold() in people.by_slug}
    return found


def _default_findings_loader():
    try:
        from tools.build_research_catalog import _load_research_findings
    except ModuleNotFoundError:
        from build_research_catalog import _load_research_findings
    return _load_research_findings


def _mentions(people: _People, loader, research_root: Path, manifest: Path, policy):
    per_person: dict[str, list[tuple]] = defaultdict(list)
    have_notes = {p.name.casefold() for p in research_root.iterdir() if (p / "findings.md").is_file()} if research_root.is_dir() else set()
    aliased = set()
    if manifest.is_file():
        for entry in (json.loads(manifest.read_text(encoding="utf-8")).get("cases") or {}).values():
            if isinstance(entry, dict) and entry.get("status") == "include_record" and entry.get("profile_id"):
                aliased.add(str(entry["profile_id"]).casefold())
    for pid in sorted(people.rows):
        row = people.rows[pid]
        identifiers = [pid, *row["alternate_ids"]]
        if not any(i.casefold() in have_notes or i.casefold() in aliased for i in identifiers):
            continue
        findings = loader(identifiers)
        if policy:
            findings = policy.project(findings)
        order = 0
        for finding in findings or []:
            if not isinstance(finding, dict) or finding.get("withheld"):
                continue
            source_path = "/" + str(finding.get("source_path") or f"research/{finding.get('profile_id') or pid}/findings.md").lstrip("/")
            for section in finding.get("sections") or []:
                title = str(section.get("title") or "Research note")
                markdown = str(section.get("markdown") or "")
                if not markdown.strip() or (policy and (policy.contains_private_id(title) or "details withheld" in title)):
                    continue
                order += 1
                url = f"{row['url']}#{research_note_anchor(source_path, title)}"
                for other in sorted(_mentioned_ids(markdown, people) - {pid}):
                    per_person[other].append((row["name"].casefold(), pid, order, title, url))
    return per_person


def _public_policy():
    """The public privacy rule without the private Y-DNA tester list.

    Same rows as ``tools/public_privacy.from_sources`` (profile evidence and
    the merged One-Tree profiles), so living and withheld profiles are
    blocked. Tester identifiers live under ``data/private/``, which this
    builder does not read; the release boundary check covers them for the
    written file.
    """
    try:
        from tools.public_privacy import PublicPrivacy, identifier
        from tools.project_paths import merged_map_profiles
    except ModuleNotFoundError:
        from public_privacy import PublicPrivacy, identifier
        from project_paths import merged_map_profiles
    path = ROOT / "data/wikitree/profile-evidence.json"
    evidence = json.loads(path.read_text()) if path.exists() else {}
    profiles, _ = merged_map_profiles()
    rows = list((profiles or {}).items())
    for profile_id, capture in (evidence or {}).get("profiles", {}).items():
        rows.append((profile_id, capture))
        for relatives in (capture.get("relations") or {}).values():
            rows.extend((identifier(relative), relative) for relative in relatives if identifier(relative))
    return PublicPrivacy(rows)


def _cross_links(studies: dict, places: dict) -> dict:
    """Study pages to place pages and back, by shared people or by name."""
    places_of = defaultdict(set)
    for url, place in places.items():
        for pid in place["people"]:
            places_of[pid].add(url)
    names = {}
    for url, place in places.items():
        name = re.split(r"\s+[—–]\s+|,", place["title"])[0].strip()
        if len(name) >= 3 and name.casefold() not in PLACE_NAME_STOP:
            names.setdefault(name, set()).add(url)
    relation = defaultdict(lambda: {"shared": 0, "via": set()})
    for surl, study in studies.items():
        shared = Counter(purl for pid in study["people"] for purl in places_of.get(pid, ()))
        for purl, count in shared.items():
            relation[(surl, purl)]["shared"] = count
            relation[(surl, purl)]["via"].add("shared-people")
        text = study["text"]
        for name, urls in names.items():
            if name in text and re.search(r"(?<![\w’'])" + re.escape(name) + r"(?![\w’'])", text):
                for purl in urls:
                    relation[(surl, purl)]["via"].add("named-in-study-text")
    by_study, by_place = defaultdict(list), defaultdict(list)
    for (surl, purl), value in relation.items():
        via = sorted(value["via"])
        by_study[surl].append({"title": places[purl]["title"], "url": purl, "shared_people": value["shared"], "via": via})
        by_place[purl].append({"title": studies[surl]["title"], "url": surl, "shared_people": value["shared"], "via": via})
    order = lambda item: (-item["shared_people"], -len(item["via"]), item["title"].casefold(), item["url"])
    pages = {}
    for surl, items in by_study.items():
        items.sort(key=order)
        pages[surl] = {"title": studies[surl]["title"], "places": items[:PAGE_LINKS_SHOWN], "places_total": len(items)}
    for purl, items in by_place.items():
        items.sort(key=order)
        pages[purl] = {"title": places[purl]["title"], "studies": items[:PAGE_LINKS_SHOWN], "studies_total": len(items)}
    return pages


def _scrub(value, policy, dropped: Counter, key="entry"):
    """Drop any list entry that carries a withheld identifier."""
    if not policy:
        return value
    if isinstance(value, dict):
        return {k: _scrub(v, policy, dropped, k) for k, v in value.items()}
    if isinstance(value, list):
        kept = []
        for item in value:
            if policy.contains_private_id(json.dumps(item, ensure_ascii=False), include_testers=False):
                dropped[key] += 1
            else:
                kept.append(_scrub(item, policy, dropped, key))
        return kept
    return value


_AUTO = object()


def build(site_root: Path = ROOT / "www", *, stories_dir: Path = STORIES, ledger: Path = LEDGER,
          research_root: Path = RESEARCH, cases_manifest: Path = CASES_MANIFEST,
          findings_loader=None, policy=_AUTO) -> dict:
    """Compute the reverse-link index from the built site and maintained inputs.

    ``policy`` is a ``tools.public_privacy.PublicPrivacy`` (default: built from
    the public profile data) or ``None`` to skip the privacy screen in tests.
    """
    site_root = Path(site_root)
    if policy is _AUTO:
        policy = _public_policy()
    people = _load_people(site_root, policy)
    study_people, studies = _studies(site_root, Path(stories_dir), people)
    places = _places(site_root, people)
    place_people = defaultdict(list)
    for url, place in places.items():
        for pid in place["people"]:
            place_people[pid].append((place["title"].casefold(), place["title"], url))
    sources = _sources(site_root, people)
    findings = _findings(Path(ledger), people)
    research = _research(site_root, people)
    mentions = _mentions(people, findings_loader or _default_findings_loader(), Path(research_root),
                         Path(cases_manifest), policy)

    index_people = {}
    for pid in sorted(people.rows):
        entry = {}
        studies_here = sorted(study_people.get(pid, {}).values())
        if studies_here:
            entry["studies"] = [{"title": t, "url": u} for *_, t, u in studies_here]
        if place_people.get(pid):
            entry["places"] = [{"title": t, "url": u} for _, t, u in sorted(set(place_people[pid]), key=lambda r: (r[0], r[2]))]
        if sources.get(pid):
            rows = sorted(sources[pid], key=lambda r: (r[0], r[1], r[3]))
            entry["sources"] = [{"title": t, "url": u} for *_, t, u in rows[:SOURCES_SHOWN]]
            entry["sources_total"] = len(rows)
        if findings.get(pid):
            entry["findings"] = findings[pid]
        if research.get(pid):
            entry["research"] = [{"title": t, "url": u} for *_, t, u in sorted(research[pid].values())]
        rows, seen = [], set()
        for name_key, other, order, section, url in sorted(mentions.get(pid, [])):
            if (other, section) not in seen:
                seen.add((other, section))
                rows.append({"id": other, "name": people.rows[other]["name"], "url": url, "section": section})
        if rows:
            entry["mentioned_by"] = rows
        if entry:
            index_people[pid] = entry

    dropped = Counter()
    index_people = _scrub(index_people, policy, dropped)
    pages = _scrub(_cross_links(studies, places), policy, dropped)
    aliases = {alt.casefold(): pid for pid, row in people.rows.items() for alt in row["alternate_ids"] if pid in index_people}

    def gaining(key):
        return sum(1 for entry in index_people.values() if entry.get(key))

    inbound = Counter({pid: len({row["id"] for row in entry.get("mentioned_by", [])}) for pid, entry in index_people.items()})
    counts = {
        "people": len(people.rows),
        "people_withheld_skipped": people.withheld,
        "people_with_any_link": len(index_people),
        **{f"people_with_{key}": gaining(key) for key in PERSON_LIST_KEYS},
        "study_pages": len(studies),
        "place_pages": len(places),
        "study_pages_with_places": sum(1 for url in pages if url.startswith("/branches/")),
        "place_pages_with_studies": sum(1 for url in pages if url.startswith("/places/")),
        "entries_dropped_by_privacy_screen": dict(sorted(dropped.items())),
        "most_mentioned": [
            {"id": pid, "name": people.rows[pid]["name"], "mentioned_by_people": n,
             "mentioning_sections": len(index_people[pid]["mentioned_by"])}
            for pid, n in sorted(inbound.items(), key=lambda kv: (-kv[1], kv[0]))[:TOP_MENTIONED] if n
        ],
    }
    return {"schema_version": SCHEMA_VERSION, "derivation": DERIVATION, "counts": counts,
            "aliases": dict(sorted(aliases.items())), "people": index_people,
            "pages": dict(sorted(pages.items()))}


def serialise(index: dict) -> str:
    return json.dumps(index, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"


@lru_cache(maxsize=4)
def _load_index(path: str) -> dict:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"people": {}, "pages": {}, "_lookup": {}}
    lookup = {pid.casefold(): pid for pid in data.get("people") or {}}
    lookup.update({alt: pid for alt, pid in (data.get("aliases") or {}).items()})
    data["_lookup"] = lookup
    return data


def clear_cache() -> None:
    _load_index.cache_clear()


def load_person_links(profile_id) -> dict:
    """Return the connected pages for one person (see the module docstring)."""
    index = _load_index(str(INDEX_PATH))
    key = index["_lookup"].get(str(profile_id or "").casefold())
    entry = (index.get("people") or {}).get(key) or {}
    result = empty_person_links()
    for name in result:
        if name in entry:
            result[name] = copy.deepcopy(entry[name])
    return result


def load_page_links(url: str) -> dict:
    """Return the place links of a study page or the study links of a place page."""
    index = _load_index(str(INDEX_PATH))
    return copy.deepcopy((index.get("pages") or {}).get(url) or {})


def write_index(site_root: Path = WEB, output: Path | None = None) -> dict:
    """Build the index, write it only if it changed, drop the reader cache.

    Call this at the start of a person-page render pass so the pages use a
    current index. Returns the counts plus ``changed``.
    """
    try:
        from tools.project_paths import atomic_write_text
    except ModuleNotFoundError:
        from project_paths import atomic_write_text
    site_root = Path(site_root)
    output = Path(output) if output else site_root / INDEX_RELATIVE
    index = build(site_root)
    text = serialise(index)
    current = output.read_text(encoding="utf-8") if output.exists() else None
    if current != text:
        atomic_write_text(output, text)
    clear_cache()
    return {"output": str(output), "changed": current != text, **index["counts"]}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--site", type=Path, default=WEB, help="site root (default: www)")
    parser.add_argument("--output", type=Path, help=f"index path (default: <site>/{INDEX_RELATIVE})")
    parser.add_argument("--check", action="store_true", help="exit 1 if the index on disk is out of date; write nothing")
    args = parser.parse_args(argv)
    output = args.output or args.site / INDEX_RELATIVE
    if args.check:
        index = build(args.site)
        text = serialise(index)
        current = output.read_text(encoding="utf-8") if output.exists() else ""
        print(json.dumps({"up_to_date": current == text, **index["counts"]}, ensure_ascii=False, indent=1))
        return 0 if current == text else 1
    print(json.dumps(write_index(args.site, output), ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
