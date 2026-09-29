#!/usr/bin/env python3
"""Apply the public privacy and superseded-source publication policy."""
from __future__ import annotations

import argparse
from pathlib import Path
from shutil import copy2
import re

try:
    from site_analytics import with_analytics
except ImportError:
    from tools.site_analytics import with_analytics

def unversioned(text):
    return re.sub(r"\?v=[^\"'\s<>]+", "?v=", text)


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "www"
PRIVATE_ARCHIVE = ROOT / "data/private/publication-source-archives"
SOURCE_ARCHIVE = ROOT / "archive/www_old/ydna/glasgow-ydna-story-source/reference"
REFERENCE_PATHS = ("original-upload.html", "supplied-timeline.html")


def _privacy_page() -> str:
    """Render the public disclosure from the maintained publication policy."""
    return with_analytics("""<!doctype html>
<html lang="en-GB">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Privacy and publication policy · Glasgow Surname Project</title>
  <meta name="description" content="How the Glasgow Surname Project handles public research, local preferences and third-party links.">
  <link rel="canonical" href="https://glasgow.phenotype.dev/privacy/">
  <link rel="icon" href="/assets/favicon.svg">
  <link rel="stylesheet" href="/assets/unified/site.css?v=54e36149cb">
  <script defer src="/assets/unified/site.js?v=2528be2335"></script>
  <style>
    .privacy-main{max-width:800px;margin:0 auto;padding:clamp(2rem,7vw,5rem) 1.5rem 5rem}
    .privacy-kicker{font-size:.78rem;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:#496844}
    .privacy-main h1{font:500 clamp(2.3rem,7vw,4.7rem)/1.04 var(--g-serif,Georgia,serif);margin:.4rem 0 1.5rem;color:#30452d}
    .privacy-main h2{margin:2.5rem 0 .7rem;font:500 1.8rem/1.2 var(--g-serif,Georgia,serif);color:#30452d}
    .privacy-main p{max-width:68ch;font-size:1.02rem;line-height:1.75;color:#40523c}
    .privacy-callout{margin:2rem 0;padding:1.35rem 1.5rem;border-left:4px solid #496844;background:#edf1e7}
    .privacy-callout strong{color:#30452d}
    .g-crumbs a{color:#30452d;opacity:1}
    .privacy-main a{color:#30452d;text-underline-offset:3px}
  </style>
</head>
<body class="g-unified">
  <a class="g-skip" href="#main">Skip to page content</a>
  <div class="g-bar"><div class="g-bar-left"><div class="g-crumbs"><a href="/">Glasgow archive</a><i>/</i><strong>Privacy</strong></div></div></div>
  <main class="privacy-main" id="main">
    <p class="privacy-kicker">Project information</p>
    <h1>Privacy and publication policy</h1>
    <div class="privacy-callout"><strong>Google Analytics is used on this site.</strong>
      <p>Google Analytics helps measure visits and page use. Google may set analytics cookies or collect usage information under its own privacy terms.</p>
    </div>
    <h2>Browser preferences and external links</h2>
    <p>Some pages can store a presentation preference in your browser, such as a selected Y-DNA colour theme. That preference stays in your browser. Links to WikiTree, FamilyTreeDNA, groups.io and other services open those services, which have their own privacy information.</p>
    <p>Normal web hosting can keep technical access logs, including request information, under the host’s own retention arrangements.</p>
    <h2>Research published here</h2>
    <p>This is a filtered historical research publication. People assessed as likely living are omitted from public catalogue views, exports and the sitemap. Historical conclusions are qualified where evidence is incomplete.</p>
    <p>The curated Y-DNA study publishes its previously supplied kit comparisons, marker matrices and SNP call summaries with project-owner publication approval. They remain a dated research snapshot with the evidence limits explained alongside the results. Raw sequence files and additional private tester records are not published.</p>
    <p>If you send a correction or enquiry, choose only the information needed to explain the request. It is used to assess that request.</p>
    <h2>Superseded source pages</h2>
    <p>Two earlier Y-DNA presentation pages are preserved here as supplied research references. They remain dated source material; the maintained <a href="/ydna">Y-DNA</a> and <a href="/timeline">timeline</a> pages provide the current account.</p>
  </main>
</body>
</html>
""")


def _reference_page(*, source: Path, label: str) -> str:
    """Return the supplied reference with the shared public analytics tag."""
    try:
        from tools.approved_restorations import reference_html
    except ModuleNotFoundError:
        from approved_restorations import reference_html
    return reference_html(source.read_text(encoding="utf-8"))


def repair(
    web: Path = WEB,
    private_archive: Path = PRIVATE_ARCHIVE,
    source_archive: Path = SOURCE_ARCHIVE,
) -> dict[str, int]:
    """Preserve original references privately and replace public copies safely.

    Existing private files are never overwritten, so a later run cannot replace
    the preserved supplied source with a regenerated public page.
    """
    private_archive.mkdir(parents=True, exist_ok=True)
    public_reference = web / "ydna/glasgow-ydna-story-source/reference"
    changed = {"private_archives": 0, "privacy_page": 0, "superseded_pages": 0}
    privacy = web / "privacy/index.html"
    privacy_page = _privacy_page()
    if not privacy.exists() or privacy.read_text(encoding="utf-8") != privacy_page:
        privacy.parent.mkdir(parents=True, exist_ok=True)
        privacy.write_text(privacy_page, encoding="utf-8")
        changed["privacy_page"] += 1
    for name in REFERENCE_PATHS:
        source = source_archive / name
        preserved = private_archive / name
        if not preserved.exists():
            if not source.exists():
                raise FileNotFoundError(f"missing archival source: {source}")
            copy2(source, preserved)
            changed["private_archives"] += 1
        page = _reference_page(source=preserved, label=name)
        target = public_reference / name
        if not target.exists() or target.read_text(encoding="utf-8") != page:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(page, encoding="utf-8")
            changed["superseded_pages"] += 1
    return changed


def audit(
    web: Path = WEB,
    private_archive: Path = PRIVATE_ARCHIVE,
    source_archive: Path = SOURCE_ARCHIVE,
) -> list[str]:
    """List missing or stale policy artifacts without changing public files."""
    failures: list[str] = []
    privacy = web / "privacy/index.html"
    if not privacy.exists() or unversioned(privacy.read_text(encoding="utf-8")) != unversioned(_privacy_page()):
        failures.append("privacy/index.html")
    targets = {
        "original-upload.html": ("/ydna", "Open the current Y-DNA page"),
        "supplied-timeline.html": ("/timeline", "Open the current timeline"),
    }
    for name in REFERENCE_PATHS:
        if not (private_archive / name).exists():
            failures.append(f"private archive: {name}")
        path = web / "ydna/glasgow-ydna-story-source/reference" / name
        source = private_archive / name
        expected = _reference_page(source=source, label=name)
        if not path.exists() or unversioned(path.read_text(encoding="utf-8")) != unversioned(expected):
            failures.append(str(path.relative_to(web)))
    return failures


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Check that repair makes no further changes")
    args = parser.parse_args()
    if args.check:
        failures = audit()
        print(f"Publication policy: {len(failures)} failures")
        for failure in failures:
            print(f"FAIL {failure}")
        raise SystemExit(bool(failures))
    print(repair())
