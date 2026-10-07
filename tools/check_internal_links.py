#!/usr/bin/env python3
"""Release gate: internal links and asset references that point at nothing.

    python tools/check_internal_links.py [--site www]
        [--baseline data/site/internal-link-baseline.json] [--update-baseline]
        [--report path.json] [--jobs N]

Walks every ``*.html`` file under the site root and checks each internal
``href``, ``src``, ``srcset``, ``poster`` and ``data-r-fragment`` (the lazy
research fragments on person pages). External, ``mailto:``, ``tel:``,
``javascript:``, ``data:`` and same-page ``#…`` links are ignored, as are
values inside scripts, styles, text areas and comments and unfilled template
placeholders.

How a URL resolves (the origin is plain static nginx; ``_redirects`` and
``.htaccess`` are not applied there, and no vhost rewrites are kept in the
repository; ``deploy/nginx/`` holds only cache headers):

- ``<base href>`` is honoured; a fragment file under
  ``assets/research/fragments/`` is resolved against its person page, where
  it is inserted.
- ``/x/`` needs ``x/index.html``; ``/x`` needs the file ``x`` or the
  directory ``x/`` with ``index.html`` (nginx adds the slash). Query strings
  do not matter. A link ``/x`` that exists only as ``x.html`` is broken on
  nginx and is reported under its own cause.
- ``#fragment`` targets are checked only for links into person pages
  (``/people/<slug>.html#id``, using the page's ``id`` attributes and its lazy
  fragments' ``data-r-fragment-anchors``). They are reported, never gated.

Broken links are grouped by cause, the generator pattern that produced them,
with the builder to fix (``CAUSES``). With ``--baseline`` the check ratchets:
exit 0 when every broken (source page, target) pair is already in the
baseline, exit 1 when a new one appears. ``--update-baseline`` writes the
baseline; when one exists it only ever shrinks (pairs no longer broken are
removed, new ones are never added and still fail). Without ``--baseline``
any broken link fails.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from html import unescape
import json
import os
from pathlib import Path
import posixpath
import re
import sys
import time
from urllib.parse import unquote, urljoin, urlsplit

ROOT = Path(__file__).resolve().parents[1]
SITE_HOST = "glasgow.phenotype.dev"
LOCAL_HOSTS = {SITE_HOST, "www." + SITE_HOST}
DEFAULT_BASELINE = ROOT / "data/site/internal-link-baseline.json"
SCHEMA_VERSION = 1
EXAMPLES = 8

_COMMENT = re.compile(r"<!--.*?-->", re.S)
_RAW_BODY = re.compile(r"(<(script|style|textarea)\b[^>]*>).*?</\2\s*>", re.I | re.S)
_TAG = re.compile(r"<([a-zA-Z][a-zA-Z0-9-]*)(\s[^>]*)>", re.S)
_ATTR = re.compile(r"""(?:^|\s)(href|src|srcset|poster|data-r-fragment)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))""", re.I)
_BASE = re.compile(r"""<base\b[^>]*?\bhref\s*=\s*["']([^"']*)["']""", re.I)
_ID = re.compile(r"""\s(?:id|name)\s*=\s*["']([^"']+)["']""", re.I)
_LAZY_ANCHORS = re.compile(r"""data-r-fragment-anchors\s*=\s*["']([^"']*)["']""", re.I)
_PERSON_PAGE = re.compile(r"people/[^/]+\.html")
_FRAGMENT_FILE = re.compile(r"assets/research/fragments/(.+?)-(?:[0-9a-f]{16}|technical)\.html")
_SKIP_SCHEMES = ("mailto:", "tel:", "javascript:", "data:", "blob:", "about:", "sms:", "file:")
_TEMPLATE = ("${", "{{", "<%", "' +", "\" +")
_PROFILE_ID = re.compile(r"[A-Za-z][A-Za-z_'’]*(?:-[A-Za-z][A-Za-z_'’]*)*-\d+")
_ASSET_SUFFIXES = {".css", ".js", ".mjs", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico", ".woff",
                   ".woff2", ".ttf", ".json", ".csv", ".txt", ".pdf", ".xml", ".mp4", ".webm", ".geojson"}
_SKIP_TAGS = {"base", "form"}

# Cause → where the generator lives and the fix. Filled from the current run;
# a cause not listed here falls back to "missing-page".
CAUSES = {
    "research-repository-file": {
        "label": "Research notes link files that stay in the repository (findings.md, images, captures)",
        "builder": "tools/repair_person_hierarchy.py::_safe_markdown_html (lane I1); also page_fragments readers and "
                   "build_study_pages.evidence_log, which reuse it",
        "fix": "After urljoin, keep the link only if the target exists under www/ or is external; otherwise render "
               "the label as text with '(held in the research archive)'.",
    },
    "person-without-page": {
        "label": "Links to /people/<id>.html for people who have no page",
        "builder": "the page generator named in source_patterns (notes: _safe_markdown_html [[ID]] links)",
        "fix": "Link /people/<slug>.html only when the file exists; otherwise link https://www.wikitree.com/wiki/<ID> "
               "and say it opens WikiTree.",
    },
    "relative-link-wrong-folder": {
        "label": "Relative links that resolve inside the wrong folder; the root-absolute path exists",
        "builder": "statistics/: tools/build_statistics_page.py (copies the catalogue pane); catalogue/: "
                   "tools/sync_catalogue_research.py (pending-update grid); ydna/glasgow-ydna-story-source/reference/: "
                   "supplied reference editions published by tools/repair_publication_policy.py",
        "fix": "Write the href root-absolute (leading '/').",
    },
    "privacy-placeholder-href": {
        "label": "The privacy placeholder text was written into an href",
        "builder": "tools/public_privacy.py::PublicPrivacy.project (rewrites url/href strings)",
        "fix": "Drop the link (keep its text) instead of replacing the href with 'Private family details withheld.'.",
    },
    "needs-html-extension": {
        "label": "Extensionless links that exist only as x.html (nginx serves no .html fallback)",
        "builder": "the generator of the source pages (see source_patterns)",
        "fix": "Link the real file (x.html) or publish x/index.html.",
    },
    "missing-fragment-file": {
        "label": "Lazy research fragments that are referenced but missing",
        "builder": "tools/page_fragments.py::optimize_page",
        "fix": "Rebuild fragments with the person page; never delete a fragment a page still references.",
    },
    "missing-asset": {
        "label": "Stylesheets, scripts, images or data files that are missing",
        "builder": "the generator of the source pages (see source_patterns)",
        "fix": "Publish the asset or remove the reference.",
    },
    "missing-page": {
        "label": "Other missing pages",
        "builder": "the generator of the source pages (see source_patterns)",
        "fix": "Point the link at a published page or remove it.",
    },
}

_FILES: frozenset = frozenset()


def _init(files: frozenset) -> None:
    global _FILES
    _FILES = files


def page_url(relative: str) -> str:
    if relative == "index.html":
        return "/"
    if relative.endswith("/index.html"):
        return "/" + relative[: -len("index.html")]
    return "/" + relative


def resolve(path: str, files) -> tuple[str | None, str]:
    """Return (file served for this URL path or None, how)."""
    decoded = unquote(path or "/")
    if not decoded.startswith("/"):
        decoded = "/" + decoded
    slash = decoded.endswith("/")
    normal = posixpath.normpath(decoded)
    if normal.startswith("//") or ".." in normal.split("/"):
        return None, "outside-site"
    rel = normal.lstrip("/")
    if rel in ("", "."):
        return ("index.html", "dir") if "index.html" in files else (None, "missing")
    if slash:
        candidate = rel + "/index.html"
        return (candidate, "dir") if candidate in files else (None, "missing")
    if rel in files:
        return rel, "file"
    if rel + "/index.html" in files:
        return rel + "/index.html", "dir-noslash"
    if rel + ".html" in files:
        return None, "html-fallback"
    return None, "missing"


def _values(name: str, raw: str) -> list[str]:
    value = unescape(raw).strip()
    if name.lower() == "srcset":
        return [part.strip().split()[0] for part in value.split(",") if part.strip()]
    return [value]


def scan(relative: str, site_root: str) -> dict:
    """Check one page. Returns broken links, person-page anchors and counts."""
    text = Path(site_root, relative).read_text(encoding="utf-8", errors="replace")
    fragment = _FRAGMENT_FILE.fullmatch(relative)
    if fragment and "<head" not in text[:4000].lower():
        base = f"https://{SITE_HOST}/people/{fragment.group(1)}.html"
    else:
        base = f"https://{SITE_HOST}{page_url(relative)}"
        match = _BASE.search(text)
        if match:
            base = urljoin(base, unescape(match.group(1)).strip())
    clean = _RAW_BODY.sub(lambda m: m.group(1), _COMMENT.sub(" ", text))
    broken, anchors, checked, internal = [], [], 0, 0
    cache = {}
    for tag in _TAG.finditer(clean):
        name, attrs = tag.group(1).lower(), tag.group(2)
        if name in _SKIP_TAGS or not ("href" in attrs or "src" in attrs or "poster" in attrs or "data-r-fragment" in attrs):
            continue
        for attr in _ATTR.finditer(attrs):
            raw = next(g for g in attr.groups()[1:] if g is not None)
            for value in _values(attr.group(1), raw):
                checked += 1
                low = value.lower()
                if not value or value.startswith("#") or low.startswith(_SKIP_SCHEMES) or any(t in value for t in _TEMPLATE):
                    continue
                try:
                    parts = urlsplit(urljoin(base, value))
                except ValueError:
                    broken.append((name, attr.group(1).lower(), value[:300], value[:300], "invalid-url"))
                    continue
                if parts.scheme not in ("http", "https") or parts.netloc.lower() not in LOCAL_HOSTS:
                    continue
                internal += 1
                path = parts.path or "/"
                if path not in cache:
                    cache[path] = resolve(path, _FILES)
                target, how = cache[path]
                if target is None:
                    broken.append((name, attr.group(1).lower(), value[:300], unquote(path), how))
                elif parts.fragment and _PERSON_PAGE.fullmatch(target) and target != relative:
                    anchors.append((target, unquote(parts.fragment), value[:300]))
    ids = None
    if _PERSON_PAGE.fullmatch(relative):
        ids = set(_ID.findall(clean))
        for listed in _LAZY_ANCHORS.findall(clean):
            ids.update(listed.split())
        ids = sorted(ids)
    return {"page": relative, "broken": broken, "anchors": anchors, "ids": ids,
            "checked": checked, "internal": internal}


def site_files(site_root: Path) -> frozenset:
    files = []
    for directory, _, names in os.walk(site_root):
        prefix = Path(directory).relative_to(site_root).as_posix()
        prefix = "" if prefix == "." else prefix + "/"
        files.extend(prefix + name for name in names)
    return frozenset(files)


def source_pattern(relative: str) -> str:
    parts = relative.split("/")
    if len(parts) == 1:
        return relative
    if parts[-1] == "index.html" and len(parts) >= 3:
        return "/".join(parts[:-2]) + "/*/index.html"
    return "/".join(parts[:-1]) + "/*" + posixpath.splitext(parts[-1])[1]


def target_pattern(target: str) -> str:
    value = re.sub(r"[0-9a-f]{12,}", "<hash>", target)
    value = _PROFILE_ID.sub("<ID>", value)
    value = re.sub(r"(?<=/)[^/]+(\.(?:jpe?g|png|gif|pdf|tiff?|webp|md|json|txt|csv))$", r"<file>\1", value, flags=re.I)
    return re.sub(r"\d+", "<n>", value)


def classify(page: str, value: str, target: str, how: str, files) -> str:
    if "withheld" in value.lower():
        return "privacy-placeholder-href"
    if how == "html-fallback":
        return "needs-html-extension"
    scheme = urlsplit(value).scheme
    if not scheme and not value.startswith("/"):
        path = urlsplit(value).path
        if path and resolve("/" + path, files)[0]:
            return "relative-link-wrong-folder"
    if re.match(r"^/(?:surname-)?research/", target):
        second = target.split("/")[2] if target.count("/") >= 2 else ""
        suffix = posixpath.splitext(target)[1].lower()
        if (suffix and suffix != ".html") or _PROFILE_ID.fullmatch(second) or "/sources/" in target:
            return "research-repository-file"
    if re.fullmatch(r"/people/[^/]+\.html", target):
        return "person-without-page"
    if target.startswith("/assets/research/fragments/"):
        return "missing-fragment-file"
    if posixpath.splitext(target)[1].lower() in _ASSET_SUFFIXES:
        return "missing-asset"
    return "missing-page"


def check(site_root: Path, jobs: int | None = None) -> dict:
    """Scan the site and return all results (no baseline logic)."""
    started = time.time()
    site_root = Path(site_root)
    files = site_files(site_root)
    pages = sorted(f for f in files if f.endswith(".html"))
    jobs = jobs if jobs is not None else max(1, min(8, (os.cpu_count() or 2) // 2))
    if jobs <= 1:
        _init(files)
        results = [scan(page, str(site_root)) for page in pages]
    else:
        with ProcessPoolExecutor(max_workers=jobs, initializer=_init, initargs=(files,)) as pool:
            results = list(pool.map(scan, pages, [str(site_root)] * len(pages), chunksize=64))
    broken, ids, anchor_refs = [], {}, []
    checked = internal = 0
    for result in results:
        checked += result["checked"]
        internal += result["internal"]
        if result["ids"] is not None:
            ids[result["page"]] = set(result["ids"])
        for tag, attr, value, target, how in result["broken"]:
            broken.append({"page": result["page"], "tag": tag, "attr": attr, "href": value, "target": target,
                           "cause": classify(result["page"], value, target, how, files)})
        anchor_refs.extend((result["page"], *ref) for ref in result["anchors"])
    missing_anchors = [{"page": page, "href": value, "target": target, "anchor": anchor}
                       for page, target, anchor, value in anchor_refs if anchor not in ids.get(target, set())]
    return {"site": str(site_root), "pages": len(pages), "references_checked": checked, "internal_references": internal,
            "broken": broken, "anchor_references": len(anchor_refs), "missing_anchors": missing_anchors,
            "elapsed_seconds": round(time.time() - started, 1)}


def pairs_of(broken: list[dict]) -> set[tuple[str, str]]:
    return {(row["page"], row["target"]) for row in broken}


def summarise(broken: list[dict]) -> list[dict]:
    by_cause = defaultdict(list)
    for row in broken:
        by_cause[row["cause"]].append(row)
    summary = []
    for cause, rows in by_cause.items():
        info = CAUSES.get(cause, CAUSES["missing-page"])
        sources = Counter(source_pattern(r["page"]) for r in rows)
        targets = Counter(target_pattern(r["target"]) for r in rows)
        distinct = Counter(r["target"] for r in rows)
        examples, seen = [], set()
        for row in sorted(rows, key=lambda r: (r["page"], r["target"])):
            key = source_pattern(row["page"]), target_pattern(row["target"])
            if key not in seen and len(examples) < EXAMPLES:
                seen.add(key)
                examples.append({"page": row["page"], "href": row["href"], "target": row["target"]})
        summary.append({
            "cause": cause, "label": info["label"], "builder": info["builder"], "fix": info["fix"],
            "links": len(rows), "pairs": len(pairs_of(rows)), "pages": len({r["page"] for r in rows}),
            "distinct_targets": len(distinct),
            "source_patterns": dict(sources.most_common(12)),
            "target_patterns": dict(targets.most_common(12)),
            "top_targets": dict(distinct.most_common(10)),
            "examples": examples,
        })
    summary.sort(key=lambda item: (-item["links"], item["cause"]))
    return summary


def read_baseline(path: Path) -> set[tuple[str, str]] | None:
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return {(page, target) for page, targets in (data.get("pairs") or {}).items() for target in targets}


def write_baseline(path: Path, pairs: set[tuple[str, str]]) -> None:
    grouped = defaultdict(list)
    for page, target in sorted(pairs):
        grouped[page].append(target)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "description": "Known broken internal links as (source page, target path) pairs. "
                       "tools/check_internal_links.py fails on any pair not listed here. "
                       "Only --update-baseline changes this file, and it only removes pairs.",
        "count": len(pairs),
        "pairs": dict(grouped),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--site", type=Path, default=ROOT / "www")
    parser.add_argument("--baseline", type=Path, help="known broken (page, target) pairs; new pairs fail")
    parser.add_argument("--update-baseline", action="store_true",
                        help="write the baseline (created if absent; otherwise pairs are only removed)")
    parser.add_argument("--report", type=Path, help="write the full JSON report here")
    parser.add_argument("--jobs", type=int, help="worker processes (default: half the CPUs, at most 8)")
    args = parser.parse_args(argv)
    if not args.site.is_dir():
        parser.error(f"site root not found: {args.site}")
    baseline_path = args.baseline or (DEFAULT_BASELINE if args.update_baseline else None)

    result = check(args.site, args.jobs)
    current = pairs_of(result["broken"])
    baseline = read_baseline(baseline_path) if baseline_path else None
    new = sorted(current - baseline) if baseline is not None else sorted(current)
    fixed = sorted(baseline - current) if baseline is not None else []
    status = 1 if new else 0
    note = ""
    if args.update_baseline:
        if baseline is None:
            write_baseline(baseline_path, current)
            status, new, note = 0, [], f"baseline created with {len(current)} pairs"
        else:
            kept = baseline & current
            if kept != baseline:
                write_baseline(baseline_path, kept)
            note = f"baseline {len(baseline)} -> {len(kept)} pairs" + (f"; {len(new)} new pairs NOT added" if new else "")
            fixed = []

    new_set = set(new)
    report = {
        "site": result["site"], "pages": result["pages"], "references_checked": result["references_checked"],
        "internal_references": result["internal_references"], "broken_links": len(result["broken"]),
        "broken_pairs": len(current), "distinct_targets": len({row["target"] for row in result["broken"]}),
        "elapsed_seconds": result["elapsed_seconds"],
        "baseline": {"path": str(baseline_path) if baseline_path else None,
                     "pairs": len(baseline) if baseline is not None else None,
                     "new_pairs": len(new), "fixed_pairs": len(fixed), "note": note,
                     "new_examples": [{"page": p, "target": t} for p, t in new[:50]]},
        "causes": summarise(result["broken"]),
        "anchors": {"scope": "links into person pages only; reported, not gated",
                    "references": result["anchor_references"], "missing": len(result["missing_anchors"]),
                    "by_anchor": dict(Counter(re.sub(r"\d+", "<n>", r["anchor"]) for r in result["missing_anchors"]).most_common(15)),
                    "examples": result["missing_anchors"][:EXAMPLES]},
        "broken": sorted(({**row, "new": (row["page"], row["target"]) in new_set} for row in result["broken"]),
                         key=lambda r: (r["cause"], r["page"], r["target"], r["href"])),
    }
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    print(f"Internal links: {result['pages']} pages, {result['internal_references']} internal references, "
          f"{len(result['broken'])} broken ({len(current)} page-target pairs) in {result['elapsed_seconds']}s")
    for cause in report["causes"]:
        print(f"  {cause['links']:6d}  {cause['cause']}: {cause['label']}")
    if baseline is not None or args.update_baseline:
        print(f"Baseline: {len(new)} new pairs, {len(fixed)} fixed pairs. {note}".rstrip())
    for page, target in new[:20]:
        print(f"  NEW  {page} -> {target}")
    if fixed:
        print("Run with --update-baseline to remove the fixed pairs from the baseline.")
    print(f"Anchors into person pages: {report['anchors']['missing']} missing of {report['anchors']['references']} (not gated)")
    return status


if __name__ == "__main__":
    sys.exit(main())
