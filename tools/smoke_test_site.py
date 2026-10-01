#!/usr/bin/env python3
"""Check a deployed static site and compare versioned assets to local www/."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen


PAGES = {
    "/": ("Glasgow family history", None), "/catalogue/": ("Find a person", None),
    "/onetree/": ("The family atlas", None), "/branches/": ("Families and places", None),
    "/ydna/": ("Before the name.", None), "/research/": ("Questions we are working on", None),
    "/people/glasgow-951.html": ("Alexander Glasgow", "Glasgow-951"),
}
USER_AGENT = "Mozilla/5.0 (compatible; GlasgowCatalogueSmoke/1.0; +https://glasgow.phenotype.dev/)"
ASSET_URL = re.compile(r"(?:href|src)=[\"']([^\"']+\.(?:css|js)\?v=[^\"'#]+)[\"']", re.I)
BASE_HREF = re.compile(r"<base\s+[^>]*href=[\"']([^\"']+)[\"']", re.I)

def page_matches(body: bytes, heading: str, person_id: str | None = None) -> bool:
    text = body.decode("utf-8", errors="replace")
    headings = re.findall(r"<h1\b[^>]*>(.*?)</h1>", text, re.I | re.S)
    if not any(re.sub(r"<[^>]+>", "", value).strip() == heading or re.sub(r"<[^>]+>", "", value).strip().startswith(heading) for value in headings):
        return False
    return person_id is None or re.search(r'data-r-person=["\']' + re.escape(person_id) + r'["\']', text) is not None


def fetch(url: str) -> tuple[int, bytes]:
    try:
        with urlopen(Request(url, headers={"User-Agent": USER_AGENT}), timeout=20) as response:
            return response.status, response.read()
    except HTTPError as error:
        return error.code, error.read()
    except URLError as error:
        raise RuntimeError(str(error)) from error


def local_asset(site_root: Path, asset_url: str) -> Path | None:
    parsed = urlsplit(asset_url)
    try:
        path = (site_root / parsed.path.lstrip("/")).resolve()
        path.relative_to(site_root.resolve())
    except ValueError:
        return None
    return path if path.is_file() else None


def smoke_test(base_url: str, site_root: Path) -> list[str]:
    failures: list[str] = []
    base_url = base_url.rstrip("/") + "/"
    seen_assets: set[str] = set()
    for route, (expected, person_id) in PAGES.items():
        url = urljoin(base_url, route.lstrip("/"))
        try:
            status, body = fetch(url)
        except RuntimeError as error:
            failures.append(f"{route}: {error}")
            continue
        if status != 200:
            kind = "access/WAF failure" if status == 403 else "missing page" if status == 404 else "HTTP failure"
            failures.append(f"{route}: {kind} (HTTP {status})")
            continue
        if not page_matches(body, expected, person_id):
            failures.append(f"{route}: missing expected page heading or person identity")
        page = body.decode("utf-8", errors="replace")
        base_match = BASE_HREF.search(page)
        page_base = urljoin(url, base_match.group(1)) if base_match else url
        for asset in ASSET_URL.findall(page):
            parsed = urlsplit(asset)
            if parsed.scheme or parsed.netloc:
                continue
            seen_assets.add(urljoin(page_base, asset))
    for route in ("/data/manifest.json", "/data/catalogue-search-index.json"):
        try:
            status, body = fetch(urljoin(base_url, route.lstrip("/")))
            if status != 200:
                kind = "access/WAF failure" if status == 403 else "missing page" if status == 404 else "HTTP failure"
                failures.append(f"{route}: {kind} (HTTP {status})")
                continue
            data = json.loads(body)
            if route.endswith("manifest.json") and not {"schema_version", "datasets", "build_id"} <= data.keys():
                failures.append(f"{route}: required manifest fields missing")
        except (RuntimeError, json.JSONDecodeError) as error:
            failures.append(f"{route}: {error}")
    for url in sorted(seen_assets):
        try:
            status, served = fetch(url)
        except RuntimeError as error:
            failures.append(f"{url}: {error}")
            continue
        if status != 200:
            kind = "access/WAF failure" if status == 403 else "missing page" if status == 404 else "HTTP failure"
            failures.append(f"{url}: {kind} (HTTP {status})")
            continue
        asset = local_asset(site_root, url)
        if asset is None:
            failures.append(f"{url}: no matching local asset")
        elif hashlib.sha256(served).digest() != hashlib.sha256(asset.read_bytes()).digest():
            failures.append(f"{url}: served content differs from {asset.relative_to(site_root.resolve())}")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base_url")
    parser.add_argument("--site-root", type=Path, default=Path(__file__).parents[1] / "www")
    args = parser.parse_args()
    failures = smoke_test(args.base_url, args.site_root)
    if failures:
        print("FAIL")
        print("\n".join(failures))
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
