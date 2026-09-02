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
)


class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in {"a", "link", "script"}:
            values = dict(attrs)
            target = values.get("href") or values.get("src")
            if target:
                self.links.append(target)


def local_checks() -> list[str]:
    failures = [f"missing {path}" for path in REQUIRED if not (WEB / path).exists()]
    if failures:
        return failures
    health = json.loads((WEB / "health.json").read_text(encoding="utf-8"))
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
            target = (path.parent / parsed.path).resolve() if parsed.path else path
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


def deployed_checks(base_url: str) -> list[str]:
    failures = []
    expected = {
        "health.json": '"status": "ok"',
        "catalogue.html": "Browse the complete catalogue",
        "records/": "Research records",
        "places/": "Research places",
        "compare.html": "Compare two people",
        "data/compare-index.js": "window.glasgowCompareDossiers=",
        "people/compare.js": "bundled comparison data",
        "people/glasgow-951.html": "Latest case research",
    }
    for path, marker in expected.items():
        url = urljoin(base_url.rstrip("/") + "/", path)
        started = time.monotonic()
        try:
            request = Request(url, headers={"User-Agent": "GlasgowCatalogueHealth/1.0"})
            with urlopen(request, timeout=20) as response:
                body = response.read().decode("utf-8", "replace")
                status = response.status
        except Exception as exc:  # Network and HTTP failures are both actionable here.
            failures.append(f"{url}: {exc}")
            continue
        elapsed = time.monotonic() - started
        if status != 200:
            failures.append(f"{url}: HTTP {status}")
        if marker not in body:
            failures.append(f"{url}: expected marker missing")
        print(f"ok {status} {elapsed:.2f}s {url}")
    return failures


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
