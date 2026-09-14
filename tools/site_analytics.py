#!/usr/bin/env python3
"""Keep the shared Google tag on full public HTML pages, including future builds."""
from __future__ import annotations

import argparse
from pathlib import Path
import re

WEB = Path(__file__).resolve().parents[1] / "www"
MEASUREMENT_ID = "G-JB207MGBMX"
HEAD = re.compile(r"<head\b[^>]*>", re.I)
MANAGED_TAG = re.compile(
    r"\n<!-- site-analytics:start -->.*?<!-- site-analytics:end -->\n", re.S
)
GOOGLE_TAG = """
<!-- site-analytics:start -->
<!-- Google tag (gtag.js) -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-JB207MGBMX"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());

  gtag('config', 'G-JB207MGBMX');
</script>
<!-- site-analytics:end -->
"""


def without_analytics(html: str) -> str:
    """Remove only our managed addition, preserving the underlying source HTML."""
    return MANAGED_TAG.sub("", html)


def with_analytics(html: str) -> str:
    html = without_analytics(html)
    return HEAD.sub(lambda match: match[0] + GOOGLE_TAG, html, count=1)


def repair(web: Path = WEB) -> dict[str, int]:
    changed = 0
    for path in web.rglob("*.html"):
        before = path.read_text(encoding="utf-8")
        after = with_analytics(before)
        if after != before:
            path.write_text(after, encoding="utf-8")
            changed += 1
    return {"analytics_pages": changed}


def audit(web: Path = WEB) -> tuple[int, list[str]]:
    pages = 0
    failures = []
    for path in web.rglob("*.html"):
        html = path.read_text(encoding="utf-8")
        if not HEAD.search(html):
            continue  # HTML fragments run within an already tagged document.
        pages += 1
        if html.count(GOOGLE_TAG) != 1 or html != with_analytics(html):
            failures.append(str(path.relative_to(web)))
    return pages, failures


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Check coverage without writing pages")
    args = parser.parse_args()
    if not args.check:
        print(repair())
    pages, failures = audit()
    print(f"Google tag {MEASUREMENT_ID}: {pages} full HTML pages, {len(failures)} failures")
    for failure in failures:
        print(f"FAIL {failure}")
    raise SystemExit(bool(failures))
