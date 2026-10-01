# Public catalogue deployment

The generated `www/` directory is the complete website root. No hosting credentials or deployment configuration are stored in this repository.

The catalogue's maintained stylesheet is `tools/catalogue-light.css`. Both the catalogue builder and unified-site repair copy it to `www/people/catalogue.css`; a full catalogue build also restores the unified light `/catalogue/` shell. `tools/check_public_catalogue.py` flags a dark stylesheet or a reverted catalogue shell before release. Package a new archive after presentation changes so old CSS cache URLs and old bundles are not reused.

## Release

1. If source data changed, rebuild with `.venv/bin/python tools/build_family_map.py`. For presentation-only changes, preserve the existing generated datasets.
2. Apply maintained presentation repairs: `.venv/bin/python tools/repair_unified_site.py`. This also runs the read-only migration audit; keep the local `www_old/` migration reference available.
3. Test: `.venv/bin/python -m unittest discover -s tests -v`.
4. Check generated entry points: `.venv/bin/python tools/check_public_catalogue.py`. Run the desktop/mobile checks in `docs/site-experience-checks.md`, including family pagination and research-feed identity details.
5. Review the release changes and keep the previous hosted website bundle available for rollback. Upload only the contents of `www/` to the document root for `glasgow.phenotype.dev`, not the repository or private research directories. Prefer an atomic directory switch where the host supports it.
6. Probe production: `.venv/bin/python tools/check_public_catalogue.py --base-url https://glasgow.phenotype.dev/`. Repeat key browser flows against production and check changed stylesheet/script versions.

Preparing local files or passing local checks is not a production deployment. The host upload remains a separate authorized manual step.

After any targeted data or page update, run `.venv/bin/python tools/publish_research_release.py` before packaging. This resolves approved structured assessments while retaining imported provenance, renders source evidence into static HTML, and refreshes the small indexes and `/data/manifest.json`. The unified presentation repair also runs this finalization step. The manifest's build fingerprint and assembly timestamp describe the exported data; its research date is independently derived from dated findings and reviews. Full `people.json` remains explicitly labelled as an imported snapshot. Free-space summary inputs live in `research/free-space-pages/public-study-summaries.json` and are published by `tools/build_free_space_site.py`.

For server reuploads, place the finished bundle at `www/glasgow-site-YYYYMMDD-HHMMSS.tar.gz`. Assemble it outside `www/` first, excluding earlier `glasgow-site-*.tar.gz` bundles and macOS metadata, then move the verified archive into `www/`. Put the website contents directly at archive root so extraction updates the server's document root without adding a nested `www/` directory. Report the exact byte size and decimal MB; label binary MiB explicitly.

## Deployment helpers

`tools/stamp_asset_versions.py --check` finds stale local CSS/JS `?v=` values; run `--write` only after the generated HTML is settled. `tools/deploy_site.py --bundle` creates and verifies the conventional archive. For SSH deployment, set `GLASGOW_DEPLOY_TARGET=user@host:/absolute/document-root` (or use `--target`): the default is an itemised rsync dry-run, and `--execute` is required to upload. `--atomic` uploads to `<document-root>.releases/<timestamp>` and switches the document-root symlink, so the host must permit that symlink arrangement; `--rollback --execute` switches to the preceding release. Every executed deploy runs `tools/smoke_test_site.py` against `--base-url` (defaulting to production). Run the smoke checker directly against a local server when preparing a release: `.venv/bin/python tools/smoke_test_site.py http://127.0.0.1:8765`.

## Pending presentation release

- All requested site tasks completed locally on 30 September 2026. Retains 462 findings, three newly-certain batches covering nine relationship transitions, reciprocal Prescott brother links, Robert/Samuel pending WikiTree amendments and 213 restored comparison panels. Removed redundant Filters/latest-findings submenus; Family Tree now orders Whole tree, Branch cards, Timeline, Y-DNA; oversized timeline panels start collapsed and deep links expand their targets. Submenus have stable first-paint markup and same-page anchors preserve the document. Changes/Feedback appear under About and use the shared shell. Cohesion migration also repairs 1,265 place and 102 public people/group readers; audit has zero unexplained public reader gaps. Free-space is now a complete categorized, importance-sorted second edition of 85 unique studies, including two explicitly blank original captures, with citations, full local drafts and conflict-preserving WikiTree reconciliation. Three principal-page metadata checks succeeded; WikiTree raw text returned HTTP 202 empty, so current live bodies are not asserted. Passed 69 focused tests, the timeline disclosure check, scoped desktop/mobile browser checks, and release validation.
  Latest verified upload bundle: `www/glasgow-site-20260930-182547.tar.gz`, 141,897,269 bytes (141.90 decimal MB), 79,136 rootless members. All 86 Free-space HTML pages are present; 20 affected page/asset hashes match both local files and the archive manifest. SHA-256: `c4dcc815c0ecd8ac62fef7add11bb9ed8a6ec61c0e023ed5691aa0b7b60e5b87`. Verification: `output/site-task-completion-verification-20260930.json`. Supersedes the 17:33 bundle. No live WikiTree saves or production deployment performed. The previously deferred queue is completed locally; see `docs/queued-site-work-2026-09-30.md` and `docs/free-space-edition.md`.

- Branch area popups repaired on 30 September 2026. Regional headings now show the area name and recorded people count on separate lines, avoiding concatenated rank/name/count text. The shared directory popup remains compatible; narrow-screen width is constrained. Audited all seven interactive branch maps and all 56 area popups; verified actual pointer hover and mobile390 layout with no console errors. Eight focused tests passed. Maintained JS/CSS and public assets are synchronized; 4,802 page asset versions updated.
  Previous upload bundle (superseded above): `www/glasgow-site-20260930-173313.tar.gz`, 140,389,867 bytes (140.39 decimal MB), 79,051 rootless archive members. Release checks and gzip integrity pass; all seven affected map pages plus both assets match the archive manifest and local hashes. SHA-256: `e3fbe5ac5616bccce18b599c802e3f3754448441e940cabb866ffe6ae3891fc0`. Verification: `output/branch-popup-audit-20260930.json`. Supersedes the 17:25 bundle and includes the completed research/profile batch. Production upload remains pending; the redesign queue was subsequently completed in the release above.

- Previous research/profile batch completed on 30 September 2026. Latest findings now contains 462 entries, including three newly-certain finding batches covering nine relationship transitions; two batches include father evidence. Historical discoveries retain their original dates. This is a backfill of recoverable dated history, not an exhaustive claim. The four Prescott brothers have reciprocal sourced sibling links; Robert and Samuel have explicitly uncertain father hypotheses and complete pending WikiTree amendments. Current captured biography, complete replacement draft and diff panels are restored on 213 reviewed profiles. Passed 59 focused tests and scoped desktop/mobile browser checks. No live WikiTree edits or production upload performed.
  Previous upload bundle (superseded above): `www/glasgow-site-20260930-172518.tar.gz`, 140,387,466 bytes (140.39 decimal MB), 79,051 rootless archive members. Release checks and gzip integrity pass; 15 affected page/asset hashes match local files and the archive manifest. SHA-256: `eaeadc520dd8208f277669355f5a92f75ed6a7500d476b0b92aac133029dca75`. Verification: `output/relationship-profile-restoration-verification-20260930.json`. Supersedes the 16:24 bundle and earlier archives. Later navigation/design and Free-space second-edition work was subsequently completed in the release above.

- Latest findings added on 30 September 2026 at `/latest-findings/`, with homepage and primary-navigation links. Its table contains 460 sourced discoveries and corrections dated 21 July–30 September, newest first, with evidence limits, search, filters and pagination. All rows remain available without JavaScript. Passed 15 focused tests and desktop/mobile browser checks at 1440, 390 and 320 px. The maintained ledger and build workflow preserve future updates.
  Profile follow-up: all 537 listed people now link to checked profiles, compatible candidates or sourced drafts; 30 consolidated pages cover 84 subject handoffs. Nineteen OPR identity assessments were reconciled. The project agent and research skill require findings updates after every coherent batch. Assessment offers “Relationships newly certain” and “Fathers newly certain”: one dated finding establishes two sibling upgrades; no father upgrade qualifies. Passed 18 focused tests and scoped desktop/mobile checks.
  Previous upload bundle (superseded above): `www/glasgow-site-20260930-162417.tar.gz`, 138,868,165 bytes (138.87 decimal MB). Release totals, Atlas destinations, publication boundaries, asset versions and gzip integrity pass; 79,047 archived files include the release manifest. Nine affected page/asset hashes match current local files and the manifest. SHA-256: `257f6f25c32ff0e054a4aa625520dde42608c5eeb8ee78eb99b4dff73f67778c`. Verification: `output/latest-findings-profile-updates-verification-20260930.json`. Supersedes the 14:05, 15:00 and 16:10 bundles; production upload remains pending.

- Homepage study map restored above Alexander's example on 30 September 2026. Tree restoration and navigation repairs preserve the Whole tree label, its first position and the loaded tree heading. Passed 10 focused tests and 34 desktop/mobile browser checks at 1440, 390 and 320 px. Production upload remains pending.
  The earlier `www/glasgow-site-20260930-140559.tar.gz` is superseded by the Latest findings bundle above, which also preserves these repairs and the saved 30 September research findings.

- Catalogue cells now show their individual status colours: green for supported or tree-marked certain, yellow for uncertain/estimated/bounded dates, red for disputed/contradicted, and grey for unassessed. Birth/death date and place flags remain independent; missing values stay neutral. Includes relationship cells, accessible status text and tooltips; the colour legend was removed at the owner’s request. Passed seven focused regressions, catalogue validation and scoped desktop/mobile/grouped browser checks. Production upload remains pending.

- Reader wording and navigation revised on 29 September 2026: plain genealogy terms, direct Records & sources navigation, clearer homepage reading routes and retained earlier research notes and bookmarks. Passed 29 focused regressions, 146 desktop/mobile browser checks and 733 generated-content checks; asset versions are current. See `docs/site-reader-audit.md`. Production upload remains pending.

- Source library redesigned on 28 September 2026: responsive search panel, compact source rows and a reviewed-collections sidebar that preserves all five published notices. `tools/repair_sources_page.py` maintains the layout and runs during release finalization. Passed 34 focused browser checks (including mobile, scoped search, no-JavaScript listing and failed-worker recovery) and 5 combined sources/records regressions. Production upload remains pending.
- Records loading and presentation repaired on 28 September 2026. Generation and targeted repair attach the records script and stylesheet by path regardless of prior asset versions. Search now has pagination, sorting, scoped links and failed-request retry; the page has a responsive filter panel and compact record rows. Passed 3 focused generator regressions and 48 browser checks, including 1440, 390 and 320 px layouts and HTTP-failure recovery. These are scoped checks, not a full-site release audit. Production upload remains pending.
- Family search renders 24 results per page with accessible previous/next controls, a result range, and page reset when filters change. Curated regional studies remain visible separately.
- Latest research cards identify their subject with a profile identifier, qualified dates and recorded places. These catalogue fields help distinguish namesakes; the linked case remains authoritative where recorded fields are disputed.
- The preceding presentation batch passed nine focused regression tests, 56 desktop/mobile browser checks and the full migration audit. Those results predate the pagination and feed-identity changes; rerun the release checks above before publishing this batch.
- No production upload has been performed for this release preparation.

`health.json` exposes the generation date, public people/record/place counts, source-link backlog and core generation checks. The status page presents the same information for readers.

The original Google Analytics tag (`G-JB207MGBMX`) is restored at the project owner's request. `tools/site_analytics.py` adds exactly one tag to full HTML pages and deduplicates its managed and legacy forms. Run `.venv/bin/python tools/site_analytics.py --check` to check coverage and duplicates. Public privacy and publication boundaries are described in `docs/privacy-policy.md` and `/privacy/`.

Release preparation rejects private identifiers, raw captures, withheld DNA and unapproved licensed assets, inconsistent totals and broken Atlas destinations. Historical transcription assets explicitly approved in `research/transcriptions/public-preview-approvals.json` are restored and retained only when their exact paths and hashes match that manifest and their preserved originals. Asset stamping cannot bypass these gates. Bundles include `release-manifest.json` with each public file's byte count and SHA-256 hash; Python sources, credentials, private directories, escaped symlinks and earlier bundles are excluded. Old bundles are retained outside the public root in `artifacts/site-releases/`.

The full previously curated `/ydna/` study is approved in `research/ydna-publication-approval.json`. Its renderer preserves the historical narrative, diagrams, comparisons, matrices, SNP summaries, tools and exports inside the shared site shell. Release checks compare the embedded study and documentary-line data against the exact approved retained inputs; this exception does not authorize raw sequence files or additional tester records.

The owner also restored Alexander Glasgow's full DNA section, separate matrix exports and six record excerpts, all Atlas tester annotations and controls, and the two supplied Y-DNA reference pages. `research/publication-restoration-approval.json` records the exact retained research sources, including the complete Atlas markup and data recovered from the pre-audit archive. The manuscript asset manifest includes the six dossier excerpts. Builds and release gates preserve these publications while retaining the living-person, restricted-capture and raw-sequence checks.

Executed rsync releases delete excluded files from the public destination as well as obsolete pages, so old public archives and source files cannot survive through exclusion protection. Atomic switching refuses an existing real directory and requires a release directory; establish the host's document-root symlink arrangement separately. Retain rollback bundles outside the served document root.

The supplied `_headers` and `.htaccess` configure basic security headers where supported. Production must be checked for the actual header response, HTTPS and publication boundaries after upload; local files alone do not establish host configuration. Remove private or unapproved assets and old bundles from the host/CDN during an authorized release, retaining the explicitly restored research paths.

Zero-result searches dispatch a local `catalogue:zero-results` browser event; no custom analytics event is configured for it.

After each release, verify the people, records, places and comparison views on a narrow mobile viewport and a desktop viewport. Keep the previous website bundle available on the host for rollback.

## Periodic profile discovery

Run the live audit periodically to find WikiTree profiles created from catalogue drafts:

```bash
.venv/bin/python tools/audit_missing_wikitree_profiles.py --apply-new-draft-matches
```

Automatic linking is deliberately narrow: the previous audit must have found no candidate, exactly one new candidate must appear, and it must match the draft's vital year plus the chronology/place score. Ambiguous results remain candidates for review. The saved link is applied on the next normal catalogue build.

## Prepared local release — 30 September 2026, 19:27

`www/glasgow-site-20260930-192738.tar.gz` supersedes the earlier 18:25 package
for server upload. It is 142,859,653 bytes (142.86 decimal MB), with 79,153
rootless archive members. SHA-256:
`4bd7c5dd6098eab4be99bc84b5234402a45de7eaa1ad67c1f8043e6a86246c32`.
Release totals, Atlas destinations, publication boundaries and content-hash
asset versions passed. Streaming gzip verification read the complete archive
and compared 22 selected final pages/assets against both local files and
`release-manifest.json`.

This package includes the restored side-by-side profile diff on 210 profiles,
filtered catalogue Map view, branch maps before long panels with click-away
previews, and a central 140-item held/pending research queue. The historical
audit backfills 29 dated findings: 38 documented relationship changes across
32 finding batches (14 uncertain/unknown to certain and 24 previously ungraded
to certain; 31 father changes). Already confident links without a recoverable
prior grade remain excluded. The ledger now contains 491 findings.

Passed 36 focused Python tests, the executable Map model fixture and scoped
desktop/mobile browser checks; the two queue tests were rerun after the jump
link correction. Evidence and screenshots are recorded in
`output/catalogue-research-ui-verification-20260930.json`. Research workflow
instructions and automatic release synchronization maintain the audit, queue
and findings views. No production deployment or live WikiTree save occurred
in this batch; hosted pages remain pending manual upload and live verification.

## Manual-amendment comparison repair — 30 September 2026

The renderer now preserves side-by-side comparisons on manual amendments, including manager-blocked replacement drafts. Glasgow-548, Glasgow-567 and Glasgow-822 were rebuilt with both full biographies retained. Seven focused tests and desktop/mobile browser checks passed. The corrected upload bundle supersedes the 21:20 package: `www/glasgow-site-20260930-214345.tar.gz`, 143876515 bytes (143.88 decimal MB). SHA-256: `2082e09d21203e83aab9ee217a43093da1916c27d320528879a6d33f7ef35bb2`. Release gates, gzip integrity and all three repaired-page manifest/local hashes passed. No production upload was performed. Verification: `output/manual-profile-diff-verification-20260930.json`.

## Prepared local release — 30 September 2026, 23:30

`www/glasgow-site-20260930-233047.tar.gz` supersedes the 23:08 archive. It is 144,084,352 bytes (144.08 decimal MB), SHA-256 `d6ccd2dc66cce444e2bcf2ef65ce1121b1cf41eb55a8e421ea7b84e16fea8c35`. All 216 profile comparison panels start collapsed and offer a default Changes only filter, retaining complete readable/copyable text. Glasgow-548’s draft now preserves its full captured family account, adds record-limit notes and qualifies the traditional marriage without removing the story, migration context, conflicting dates or namesake links. Nine focused tests, scoped desktop/mobile interaction checks, release totals, Atlas destinations, publication boundary, gzip integrity and seven selected archive/current-file hashes pass. Research inputs, profile pages, queue, manifest and local index are synchronized. No WikiTree save or production upload performed. Verification: `output/profile-diff-controls-verification-20260930.json`.

## Eleven-profile preservation audit — 30 September 2026

All eleven pending WikiTree biographies were checked against fresh anonymous public captures and reconciled passage by passage. Restored family facts, context, quotations, estimates, dated search history and source limitations; retained supported corrections and competing death indications. All 180 complete existing reference bodies, source URLs and profile links remain. SHA256 review fingerprints invalidate changed captures or replacement drafts. The maintained drafts, queue/register, public people pages/data, research manifest and local index are synchronized. Individual kit-level comparisons are withheld from public summaries; broad historical conclusions remain. Ten focused tests and scoped browser checks pass. No live WikiTree save or production upload occurred.

New upload bundle: `www/glasgow-site-20261001-000224.tar.gz`, 144,115,274 bytes (144.12 decimal MB), SHA-256 `4c7da9be4d1eebf2a4fa69e03ae97911035844a78bacb7478169421f19ba39a9`. Release totals, Atlas destinations, publication boundary, content-hash asset versions, complete gzip stream and 26 selected manifest/local-file hashes pass. Supersedes the 23:30 package. Audit: `research/profile-preservation-audit-2026-09-30/audit.md`; verification: `output/profile-preservation-verification-20260930.json`.


## Performance release — 1 October 2026

Upload bundle: `www/glasgow-site-20261001-111836.tar.gz`, 149,273,265 bytes (149.27 decimal MB), SHA-256 `821b186d65e26e30e5024c0902e24c5344294a99628de6d458f238a7dcbbfb04`. This supersedes all earlier bundles. All 79,443 archived files match the internal manifest; 16 critical page/asset/data hashes also match current local files. Gzip integrity, release totals, Atlas destinations and publication boundaries pass. Browser gates pass at 320/390/1440 px; 35 focused tests and 80 search parity cases pass. See `docs/site-experience-checks.md` for budgets, retained source data and existing full-suite limitations.

Superseded local bundles (23 files) were moved intact to ignored `archive/site-releases/`, outside the public website tree. Their relocation ledger is `archive/site-releases/moved-20261001.json`; historical bundle names in earlier notes refer to this retained location. During the owner’s authorized server upload, remove superseded tarballs from the host/CDN as described above.

No production deployment or Git push was performed. Production caching still requires the host to honour the supplied `.htaccess` or `_headers` configuration and must be checked after upload. Verification: `artifacts/site-performance-release-verification.json` and `artifacts/site-quality-report.json`.

## Full-suite repair release — 1 October 2026

Latest verified upload bundle: `www/glasgow-site-20261001-121650.tar.gz`, 149,136,681 bytes (149.14 decimal MB). SHA-256: `8f105cf1c446769e34c335a502b5d9827f7eb7e750b0f21fd2338ca908187a9c`. All 79,443 public files match the internal release manifest; eight affected pages/assets also match current local files. Verification: `artifacts/site-suite-release-verification.json`. Superseded bundles are preserved outside the public root in `archive/site-releases/`.

The final full suite runs 406 tests with zero failures/errors; six archived-migration checks require the unavailable `www_old` reference and remain skipped. Lint, data validation, dependency checks, all 18 browser gates, release totals, Atlas destinations and publication boundaries pass. This release includes corrected date qualifications, refreshed map/comparison data, accurate work-queue counts, retained merge redirects and the smaller identity resolver index. No push, live profile edit or production deployment was performed.

## Production verification — 1 October 2026

After the owner reported the upload, read-only checks against
`https://glasgow.phenotype.dev/` confirmed all 16 sampled pages, scripts,
stylesheets, packed datasets and source fragments match the local release
byte for byte after gzip decoding. The public catalogue checker and release
smoke checker pass. All sampled requests return 200 over HTTPS; three
conditional requests return 304. Versioned asset URLs work.

Browser checks covered 320, 390 and 1440 px. Search returned the expected
385 Alexander matches, with 50 on the first page; initial search readiness
was 530–771 ms in fresh, unthrottled browser contexts. Filters, findings
pagination (including without JavaScript), source deep links, the filtered
map and merged-profile redirects work. The newly added Gray candidates
compare successfully. The copy handler passes all 167,286 characters of
Alexander's revised biography to the Clipboard API with the same SHA256 as
the maintained draft. That check intercepted the API argument rather than
altering the owner's operating-system clipboard.

The initial 18-page browser run passed all checks except one 320 px tree
layout-shift measurement of 0.106 (limit 0.10). Three isolated repeat runs
measured 0.068, so retain this as an intermittent concern rather than claim
the original run was fully green. No horizontal overflow or JavaScript
page errors were observed. Additional records, places, comparisons and
filtered-map checks passed at 390 and 1440 px apart from the comparison
button's contrast finding below.

Remaining work:

- The host omits `Cache-Control` on all 16 samples, including versioned
  assets and hash-named fragments. Gzip and conditional revalidation work,
  and Cloudflare serves some cache hits, but the supplied `.htaccess` and
  `_headers` policies are not visible in live responses. Configure the
  origin/CDN to revalidate HTML and unversioned data, and serve content-hash
  asset URLs with `public, max-age=31536000, immutable`; verify actual
  responses after applying the rules.
- `#compare-submit` fails WCAG text contrast at both tested widths. Its
  text colour needs correction in the maintained stylesheet and a new
  verified release before the owner uploads it.

Evidence: `artifacts/site-live-release-http-20261001.json`,
`artifacts/site-live-quality-20261001.json`,
`artifacts/site-live-tree-cls-20261001.json`,
`artifacts/site-live-secondary-20261001.json`, and screenshots under
`output/playwright/site-live-*-20261001.png`. These are lab observations,
not production field measurements. No host configuration, site content,
Git push or WikiTree edit was performed during verification.

## Applying caching on an Nginx origin

Uploading `.htaccess` or `_headers` does not configure Nginx. Two maintained
includes are available in `deploy/nginx/`: `cache-map.conf` goes inside the
existing `http {}` context; `cache-headers.conf` goes beside the existing
`add_header` directives in this site's serving `server {}` or `location {}`
block. Keep the current document root, TLS settings and routing intact.

The policy revalidates HTML and unversioned files, gives one-year immutable
caching to content-hash CSS/JS/JSON/CSV query URLs and hash-named catalogue
details/source fragments, and sends `no-store` for errors. A hash query does
not make HTML immutable. Conditional 304 responses retain their cache policy.

Nginx replaces inherited `add_header` directives when a child block defines
its own. Preserve all current security headers and apply the cache include
at the effective serving level; an asset location with its own headers will
otherwise bypass a server-level include. Disable conflicting `expires` or
duplicate `Cache-Control` directives at that same level. This follows the
[Nginx header](https://nginx.org/en/docs/http/ngx_http_headers_module.html)
and [map](https://nginx.org/en/docs/http/ngx_http_map_module.html) documentation.

Run `nginx -t` before reloading the configured host. The project provides
`.venv/bin/python tools/check_nginx_cache.py` to test these exact includes
in an isolated local Nginx process, including immutable/revalidation rules,
invalid versions, unhashed fragments, 404 responses and conditional 304s.
It does not edit or reload the host's existing server configuration.

After the owner supplies the host connection and configuration location,
apply the matching host policy and check actual production responses.
Cloudflare cache rules must respect the origin policy; existing cached
responses may require a targeted purge of the changed URLs. A successful
local Nginx test does not confirm live caching. Apache and compatible static
hosts should use the bundled `.htaccess` and `_headers` instead.

## Follow-up fixes prepared — 1 October 2026, 13:55

New upload bundle: `www/glasgow-site-20261001-135520.tar.gz`, 149,133,900
bytes (149.13 decimal MB; 142.23 MiB). SHA256:
`95be56399f4edb92277c4190c2652d42f6a0cb526b72a9ea93ffe0c51fccf941`.
All 79,443 public files match the internal manifest; ten critical pages,
stylesheets and host-policy files also match the final local files. Gzip,
release totals, Atlas destinations, publication boundaries and asset
versions pass. The superseded 12:16 bundle is retained intact in
`archive/site-releases/`, with `moved-20261001-followup.json` recording it.

The Compare button now has white text on its green background. The tree
reserves the Menu label's width and omits the empty location-picker space
before that picker moves into Filters & tools; all ten location controls
remain visible there. Empty place/comparison containers reserve space to
prevent the footer jumping when their cards load. Maintained styles and
public assets are synchronized; generated URLs use the new content hashes.

All 27 final browser cases pass at 320/390/1440 px, including actual Gray
comparisons, accessibility, overflow and performance limits. Maximum CLS
is 0.0921 and blocking time 146 ms; tree CLS is 0.0326/0.0761/0.0283 at the
three widths. Eleven focused Python tests and all nine self-contained
browser fixture cases pass. The real isolated Nginx verification passes
eleven cache/status cases plus a conditional 304. The wider genealogy
suite was not rerun for these style/configuration changes.

The owner subsequently uploaded the site fixes; verification follows below. Live
cache headers remain unresolved: there is no confirmed connection to this
site's origin, and the available Cloudflare dashboard is signed out.
The Nginx includes above are ready to apply if the origin uses Nginx;
the owner's hosting details are required before changing production.
No production upload, host change, Git push or WikiTree edit was performed.

Verification: `artifacts/site-followup-release-verification-20261001.json`,
`artifacts/site-followup-quality-20261001.json` and
`output/playwright/site-quality-compare-mobile.png`.

## Follow-up production verification — 1 October 2026, 14:49 UTC

After the owner's upload, all five sampled pages/stylesheets return HTTP
200 with gzip and match the current local release after decompression.
All nine browser cases pass for the tree, places and an actual Gray
comparison at 320/390/1440 px. No page errors, serious/critical accessibility
violations or horizontal overflow were observed; maximum CLS is 0.0341
and blocking time 194 ms. These are scoped lab measurements.

All five responses still omit `Cache-Control`. Applying and verifying the
appropriate origin/CDN policy remains the next priority; hosting details
are still required. No host configuration or Git push was performed.

Evidence: `artifacts/site-followup-live-http-20261001.json` and
`artifacts/site-followup-live-browser-20261001.json`.
