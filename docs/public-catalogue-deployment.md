# Public catalogue deployment

The generated `www/` directory is the complete website root. No hosting credentials or deployment configuration are stored in this repository.

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

## Pending presentation release

- Family search renders 24 results per page with accessible previous/next controls, a result range, and page reset when filters change. Curated regional studies remain visible separately.
- Latest research cards identify their subject with a profile identifier, qualified dates and recorded places. These catalogue fields help distinguish namesakes; the linked case remains authoritative where recorded fields are disputed.
- The preceding presentation batch passed nine focused regression tests, 56 desktop/mobile browser checks and the full migration audit. Those results predate the pagination and feed-identity changes; rerun the release checks above before publishing this batch.
- No production upload has been performed for this release preparation.

`health.json` exposes the generation date, public people/record/place counts, source-link backlog and core generation checks. The status page presents the same information for readers.

Google Analytics uses measurement ID `G-JB207MGBMX`. The supplied Google tag is added once in the head of each full public HTML document; embedded HTML fragments use their containing page's tag. `tools/site_analytics.py` maintains this addition without rebuilding page content, and both the family-map build and unified-site repair run it automatically. Run `.venv/bin/python tools/site_analytics.py --check` to check complete coverage. Source snapshots retain their original HTML apart from this managed tag in the public copy; private originals remain unchanged.

Zero-result searches dispatch a local `catalogue:zero-results` browser event; no custom analytics event is configured for it.

After each release, verify the people, records, places and comparison views on a narrow mobile viewport and a desktop viewport. Keep the previous website bundle available on the host for rollback.

## Periodic profile discovery

Run the live audit periodically to find WikiTree profiles created from catalogue drafts:

```bash
.venv/bin/python tools/audit_missing_wikitree_profiles.py --apply-new-draft-matches
```

Automatic linking is deliberately narrow: the previous audit must have found no candidate, exactly one new candidate must appear, and it must match the draft's vital year plus the chronology/place score. Ambiguous results remain candidates for review. The saved link is applied on the next normal catalogue build.
