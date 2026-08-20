# Public catalogue deployment

The generated `www/` directory is the complete website root. No hosting credentials or deployment configuration are stored in this repository.

## Release

1. Rebuild: `.venv/bin/python tools/build_family_map.py`
2. Test: `.venv/bin/python -m unittest discover -s tests -v`
3. Check generated entry points: `.venv/bin/python tools/check_public_catalogue.py`
4. Upload the contents of `www/` to the document root for `glasgow.phenotype.dev`.
5. Probe production: `.venv/bin/python tools/check_public_catalogue.py --base-url https://glasgow.phenotype.dev/`

`health.json` exposes the generation date, public people/record/place counts, source-link backlog and core generation checks. The status page presents the same information for readers.

Zero-result searches dispatch a `catalogue:zero-results` browser event. A future privacy-preserving analytics endpoint can subscribe to that event without changing the search interface; no visitor query is currently transmitted by the static site.

After each release, verify the people, records, places and comparison views on a narrow mobile viewport and a desktop viewport. Keep the previous website bundle available on the host for rollback.

## Periodic profile discovery

Run the live audit periodically to find WikiTree profiles created from catalogue drafts:

```bash
.venv/bin/python tools/audit_missing_wikitree_profiles.py --apply-new-draft-matches
```

Automatic linking is deliberately narrow: the previous audit must have found no candidate, exactly one new candidate must appear, and it must match the draft's vital year plus the chronology/place score. Ambiguous results remain candidates for review. The saved link is applied on the next normal catalogue build.
