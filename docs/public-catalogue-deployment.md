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
