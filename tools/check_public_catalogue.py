#!/usr/bin/env python3
"""Check the generated catalogue locally and optionally probe a deployment."""

from __future__ import annotations

import argparse
from html.parser import HTMLParser
import json
from pathlib import Path
import time
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "www"
REQUIRED = (
    "catalogue.html", "records/index.html", "places/index.html", "compare.html",
    "feedback.html", "changes.html", "status.html", "health.json",
    "data/people-index.json", "data/records-index.json", "data/places-index.json",
    "data/compare-index.js", "people/compare.js",
    "free-space/index.html", "assets/research/free-space-index.json",
)


class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links: list[str] = []
        self.base = ""

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == "base" and values.get("href"):
            self.base = values["href"]
        if tag in {"a", "link", "script"}:
            target = values.get("href") or values.get("src")
            if target:
                self.links.append(target)


class PageSemantics(HTMLParser):
    """Small, deliberately structural view used by deployment probes."""
    def __init__(self):
        super().__init__()
        self.title = ""
        self.h1: list[str] = []
        self.person_ids: list[str] = []
        self.body_classes: set[str] = set()
        self._title = False
        self._h1 = False

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        self._title |= tag == "title"
        self._h1 |= tag == "h1"
        if tag == 'body':
            self.body_classes.update(values.get('class', '').split())
        if values.get("data-r-person"):
            self.person_ids.append(values["data-r-person"])

    def handle_endtag(self, tag):
        self._title &= tag != "title"
        self._h1 &= tag != "h1"

    def handle_data(self, data):
        if self._title:
            self.title += data
        if self._h1:
            self.h1.append(data)


def local_checks() -> list[str]:
    failures = [f"missing {path}" for path in REQUIRED if not (WEB / path).exists()]
    if failures:
        return failures
    css_path = WEB / "people/catalogue.css"
    if not css_path.exists():
        failures.append("missing people/catalogue.css")
    else:
        css = css_path.read_text(encoding="utf-8")
        if ":root{color-scheme:light;" not in css or "color-scheme:dark" in css or "#07100e" in css:
            failures.append("catalogue stylesheet has lost its maintained light palette")
    catalogue_path = WEB / "catalogue/index.html"
    if not catalogue_path.exists() or not catalogue_shell_matches(catalogue_path.read_text(encoding="utf-8")):
        failures.append("catalogue route has lost its unified light shell")
    try:
        health = json.loads((WEB / "health.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        failures.append(f"health.json is not valid JSON: {exc}")
        health = {}
    if health.get("status") != "ok":
        failures.append("health.json status is not ok")
    for relative in REQUIRED:
        path = WEB / relative
        if path.suffix != ".html":
            continue
        parser = LinkParser()
        parser.feed(path.read_text(encoding="utf-8"))
        for link in parser.links:
            parsed = urlsplit(link)
            if parsed.scheme or parsed.netloc or link.startswith(("#", "mailto:")):
                continue
            if parsed.path.startswith("/"):
                target = (WEB / parsed.path.lstrip("/")).resolve()
            else:
                base = urlsplit(parser.base).path if parser.base else ""
                target = (path.parent / base / parsed.path).resolve() if parsed.path else path
            try:
                target.relative_to(WEB.resolve())
            except ValueError:
                failures.append(f"{relative}: link leaves website root: {link}")
                continue
            if parsed.path.endswith("/"):
                target /= "index.html"
            if not target.exists():
                failures.append(f"{relative}: missing link target {link}")
    return failures


def catalogue_shell_matches(page: str) -> bool:
    parsed = PageSemantics()
    parsed.feed(page)
    return {'g-unified', 'g-kind-catalogue'}.issubset(parsed.body_classes)


def deployed_checks(base_url: str) -> list[str]:
    failures = []
    expected = {
        "health.json": lambda body: json.loads(body).get("status") == "ok",
        "catalogue.html": lambda body: page_matches(body, "Find a person"),
        "records/": lambda body: page_matches(body, "Research records"),
        "places/": lambda body: page_matches(body, "Research places"),
        "free-space/": lambda body: page_matches(body, "Free-space research library"),
        "compare.html": lambda body: page_matches(body, "Compare two people"),
        "data/compare-index.js": lambda body: b"window.glasgowCompareDossiers=" in body,
        "people/compare.js": lambda body: b"bundled comparison data" in body,
        "people/glasgow-951.html": lambda body: page_matches(body, "Alexander Glasgow", "Glasgow-951"),
    }
    user_agent = "Mozilla/5.0 (compatible; GlasgowCatalogueHealth/1.0; +https://glasgow.phenotype.dev/)"
    for path, marker in expected.items():
        url = urljoin(base_url.rstrip("/") + "/", path)
        started = time.monotonic()
        try:
            request = Request(url, headers={"User-Agent": user_agent})
            with urlopen(request, timeout=20) as response:
                body = response.read().decode("utf-8", "replace")
                status = response.status
        except Exception as exc:  # Network and HTTP failures are both actionable here.
            status = getattr(exc, "code", None)
            label = "access/WAF failure" if status == 403 else "missing page" if status == 404 else "request failure"
            failures.append(f"{url}: {label} ({exc})")
            continue
        elapsed = time.monotonic() - started
        if status != 200:
            label = "access/WAF failure" if status == 403 else "missing page" if status == 404 else "HTTP failure"
            failures.append(f"{url}: {label} (HTTP {status})")
        try:
            valid = marker(body.encode("utf-8") if isinstance(body, str) else body)
        except (ValueError, json.JSONDecodeError):
            valid = False
        if not valid:
            failures.append(f"{url}: expected marker missing")
        print(f"ok {status} {elapsed:.2f}s {url}")
    return failures


def page_matches(body: bytes, heading: str, person_id: str | None = None) -> bool:
    parsed = PageSemantics()
    parsed.feed(body.decode("utf-8", "replace"))
    return heading in " ".join(" ".join(parsed.h1).split()) and (person_id is None or person_id in parsed.person_ids)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", help="Also probe a deployed website, e.g. https://glasgow.phenotype.dev/")
    args = parser.parse_args()
    failures = local_checks()
    if args.base_url:
        failures.extend(deployed_checks(args.base_url))
    if failures:
        print("\n".join(f"FAIL {item}" for item in failures))
        return 1
    print("Catalogue checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
