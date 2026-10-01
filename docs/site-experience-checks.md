# Site experience checks

File preservation is not sufficient evidence of a complete migration. Keep
these three layers distinct; a source-contract pass is not a browser pass.

## Generated-content contracts

```sh
.venv/bin/python tools/audit_site_experience.py
.venv/bin/python -m unittest discover -s tests -p 'test_site_experience.py'
```

Checks cover prominent community links, confirmed WikiTree actions, access to
Latest research, complete statistics, preserved family anchors and source-dated
feed entries. The isolated generator test supplies different full and compact
identity datasets so the wrong-data-source regression cannot silently return.
Closed disclosures and explicit hidden attributes do not count as prominence.
CSS and JavaScript visibility still require the browser check below.

The full read-only migration audit includes these generated-content contracts:

```sh
.venv/bin/python tools/repair_unified_site.py --check
```

## Real-browser contracts

With a local preview already running and Playwright CLI installed:

```sh
playwright-cli -s=site-experience open http://127.0.0.1:8080/ --headed
playwright-cli -s=site-experience run-code "$(cat tools/check_site_experience.js)"
playwright-cli -s=site-experience close
```

The script uses the currently open local origin. It checks desktop and mobile
visibility, person-page actions, exposed statistics and research-feed cards,
family sections, and preservation of specialist Map bookmark queries/hashes.
It does not submit forms, change research or visit external community sites.

These checks are a focused regression set, not an exhaustive genealogy audit,
accessibility audit, source-verification exercise or check of every browser flow.
Report generated-contract and browser results separately, including checks not
run. Do not infer working buttons from generated-file counts.


## Performance release gates (1 October 2026)

Run `.venv/bin/python -m tools.finalize_site` after targeted builders, before packaging. The research-release and deployment preparation pipelines call it automatically. It prepares the worker search index, lossless Atlas payload, complete static findings pagination, lazy dossier fragments, unique local assets and content-hash versions. Original source data and full downloadable indexes remain available.

`make check-browser` checks the local preview at port 8765 (or run `tools/check_site_quality.py --base-url URL`). It covers 320/390/1440 px, real search/filter interactions, static pagination without JavaScript, WCAG serious/critical violations, overflow, 500 KB initial HTML, 6 MB initial catalogue data, 6,000 initial DOM elements, CLS ≤0.1 and ≤500 ms blocking time. These are unthrottled lab gates, not production field guarantees. `--fixture-smoke` runs a self-contained public fixture and is a separate CI job; no private datasets or deployment credentials are needed.

`window.GlasgowMetrics` exposes browser-local LCP, layout shifts, long tasks, approximate event-timing INP and search readiness. No visitor identifiers or network reporting were added. Field percentiles still require a separately configured reporting service.

Measured initial payloads: catalogue 15,944,720 → 4,465,419 bytes; Atlas 5,015,216 → 1,941,151 bytes; Alexander Glasgow HTML 2,546,267 → 111,421 bytes. Search parity passes 80 filter/sort cases. Large sections retain complete static reader links; validators expand the same fragments to inspect their evidence. The finalizer removes duplicate local assets and guards branch initialization.

Caching retains existing security headers and MIME types. Apache `.htaccess` gives content-hash query versions one-year immutable caching, while HTML/unversioned data revalidate. `_headers` supports immutable hash-named detail shards and fragments on compatible static hosts. Actual production headers must be checked after upload; server/CDN configuration may override these files.

Validation note: the full existing suite still has 11 older assertion failures and 12 missing optional genealogy-runtime errors. The assertions also fail against the previous release in an isolated checkout; fragment-related regressions were corrected without weakening their evidence assertions. Ruff, data validation, 35 focused tests, 80 search parity cases and desktop/mobile browser gates pass. Live asset hashes remain unchanged until the owner uploads the release.
