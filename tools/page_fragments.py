"""Deterministically externalise very large, collapsed page sections."""
from __future__ import annotations

import hashlib
import html as _html
import os
import re
from pathlib import Path
from urllib.parse import quote

from bs4 import BeautifulSoup, Tag


THRESHOLD = 50 * 1024


def _safe_page(page_path: str | os.PathLike[str], root: Path) -> tuple[Path, str]:
    p = Path(page_path)
    if p.is_absolute():
        try: p = p.relative_to(root)
        except ValueError: raise ValueError("page_path must be inside site_root")
    if any(x == ".." for x in p.parts): raise ValueError("unsafe page path")
    slug = re.sub(r"[^a-z0-9]+", "-", p.stem.lower()).strip("-") or "page"
    return p, slug


def _write_once(path: Path, data: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_text(encoding="utf-8") == data: return
    path.write_text(data, encoding="utf-8")


def optimize_page(html: str, page_path: str | os.PathLike[str], site_root: str | os.PathLike[str]):
    """Return ``(new_html, stats)`` and materialise large page fragments."""
    root = Path(site_root).resolve()
    rel, slug = _safe_page(page_path, root)
    soup = BeautifulSoup(html, "html.parser")
    seen = set()
    changed_ids = False
    for wrapper in soup.select('.biography-table-wrap'):
        if not wrapper.has_attr('tabindex'):
            wrapper['tabindex']='0';wrapper['role']='region';wrapper['aria-label']='Historical record table';changed_ids=True
    for el in soup.select('[id^="research-note-"]'):
        ident = el['id']; counter=2
        while el['id'] in seen:
            el['id'] = ident + '-' + hashlib.sha256(str(el).encode()).hexdigest()[:8] + '-' + str(counter); counter+=1
            changed_ids = True
        seen.add(el['id'])
    candidates: list[Tag] = []
    candidates.extend(soup.select("details:not([open])"))
    panel = soup.select_one("#wikitree-update.profile-update-panel")
    if panel is not None and panel not in candidates: candidates.append(panel)
    # Outer candidates win, preventing nested extraction and duplicate content.
    chosen = []
    for node in sorted(candidates, key=lambda n: len(str(n)), reverse=True):
        if any(node is x or x in node.parents for x in chosen): continue
        if node.name == "details" and len(str(node)) < THRESHOLD: continue
        if node.name == "section" and len(str(node)) < THRESHOLD: continue
        chosen.append(node)
    stats = {"extracted": 0, "bytes": 0, "fragments": []}
    for node in chosen:
        original = str(node)
        digest = hashlib.sha256(original.encode("utf-8")).hexdigest()[:16]
        key = f"{slug}-{digest}"
        fragment = root / "assets/research/fragments" / f"{key}.html"
        raw_rel = f"/assets/research/fragments/{key}.html"
        standalone_rel = f"/people/research-material/{key}/index.html"
        standalone = _reader_page(soup, original, standalone_rel, str(rel))
        fragment_text = original
        if node.name == "section":
            fs = BeautifulSoup(original, "html.parser")
            inner = fs.find(id="wikitree-update")
            if inner is not None: inner.attrs.pop("id", None)
            fragment_text = str(fs)
        _write_once(fragment, fragment_text)
        _write_once(root / standalone_rel.lstrip("/"), standalone)
        anchors = []
        for el in node.select("[id]"):
            if el.get("id") != "wikitree-update": anchors.append(el["id"])
        if node.name == "section":
            # Keep the stable panel id on the lazy wrapper; injected content must not duplicate it.
            inner = BeautifulSoup(original, "html.parser").find(id="wikitree-update")
            if inner is not None: inner.attrs.pop("id", None)
            full = str(inner or BeautifulSoup(original, "html.parser").contents[0])
            node.clear()
            lazy = BeautifulSoup('<details class="profile-update-lazy"><summary>WikiTree comparison and complete revised profile</summary><a>Open complete content</a></details>', "html.parser").details
            lazy.a["href"] = standalone_rel
            lazy["data-r-fragment"] = raw_rel
            lazy["data-r-fragment-anchors"] = " ".join(anchors)
            node.append(lazy)
            fragment_text = '<details><summary>WikiTree comparison and complete revised profile</summary>' + full + '</details>'
            _write_once(fragment, fragment_text)
        else:
            summary = node.find("summary")
            keep = str(summary) if summary else ""
            node.clear()
            if keep: node.append(BeautifulSoup(keep, "html.parser"))
            link = soup.new_tag("a", href=standalone_rel); link.string = "Open complete content"
            node.append(link); node["data-r-fragment"] = raw_rel
        if anchors: node["data-r-fragment-anchors"] = " ".join(anchors)
        stats["extracted"] += 1; stats["bytes"] += len(original); stats["fragments"].append(raw_rel)
    # Duplicate research-note IDs are made deterministic after transformations.
    seen = set()
    for el in soup.select('[id^="research-note-"]'):
        ident = el["id"]
        if ident in seen: el["id"] = ident + "-" + hashlib.sha256(str(el).encode()).hexdigest()[:8]
        seen.add(el["id"])
    return (str(soup) if chosen or changed_ids else html), stats


def _reader_page(source: BeautifulSoup, body: str, path: str, original: str) -> str:
    doc = BeautifulSoup(str(source), "html.parser")
    if doc.head:
        for old in doc.select('head base'): old.decompose()
        base=doc.new_tag('base',href='/' + Path(original).parent.as_posix().strip('./') + '/');doc.head.insert(0,base)
        if doc.title: doc.title.string='Research material · '+doc.title.get_text()
        canonical=doc.select_one('link[rel=canonical]')
        if canonical: canonical['href']='https://glasgow.phenotype.dev'+path
    main = doc.find('main') or doc.body
    if main is not None:
        main.clear(); main.append(BeautifulSoup(body,"html.parser"))
        for details in main.select('details'): details['open']=''
        paragraph=doc.new_tag('p');a=doc.new_tag('a',href='/'+original);a.string='Back to original page';paragraph.append(a);main.insert(0,paragraph)
    return str(doc)
