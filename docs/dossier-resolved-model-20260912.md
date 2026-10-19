# Resolved dossier model: verification and handoff

## Finding

The review was correct. Public release `dossier-hypothesis-18.1` contains the contradiction inside individual JSON responses, so uploading that archive correctly could not fix it. At 2026-09-12 10:10:36 UTC, James (Glasgow-3939) and the unnamed child (Glasgow-3940) still had proved presentation parents but unknown top-level parents. Robert's default birth still said c.1779, County Tyrone, without the displayed identity qualification. This is not evidence of an upload or cache failure.

The publisher required an approved publication flag and assertion ID. Only the Robert hypothesis had them; the renderer independently applied other shared assessments and vital overrides. Thus HTML and presentation JSON could disagree with claims and networks.

## Implemented

- `tools/publish_resolved_dossiers.py`: approved shared assessments now supply roles, reasons, source references and current claims consistently. Earlier claim IDs and exact import snapshots remain accessible. Missing approved assertion IDs cause an explicit error, not a silent skip. Network exports include resolved vitals; presentation fact mirrors refresh during publication, even without an HTML rebuild.
- `tools/repair_person_hierarchy.py`: reads resolved relationships and vitals; no independent assessment or reverse-relationship status upgrade. Embedded technical JSON includes the same claims and history. The renderer invokes publication before regeneration. CSS/layout unchanged.
- `research/relationship_assessments.json`: explicit publication mappings for existing reviewed marriages/baptisms. Includes the older approved Alexander–Robert, Alexander–Ann and later-James assessments previously dependent on the reverse-display fallback. No automatic motherhood upgrades.
- `research/canonical_records.json`: existing marriage and household records shared with the relevant child dossiers; published as `/assets/research/canonical-records.json` for machine references.
- `research/vital_assessments.json`: durable source for the existing approved vital and person assessments, mirrored into `www/assets/research/assessments.json` by the publisher. The public register also retains generated documentary chronology reviews and unrelated existing assessments. Source rows take precedence by ID; removing a previously maintained row revokes that publication. Robert's analysis resolves default dates/places to null with qualified alternatives. Alexander/children death qualifiers use the same register. The unnamed child's withdrawn before-1841 death inference now resolves to an unknown death, retaining the original import and the 6 October 2026 source assessment. These are publication mappings, not new historical findings or examination dates.
- Four `research/*/presentation.json` inputs reference their approved vital assessment instead of maintaining parallel factual overrides. Original research notes, imports and WikiTree text were not rewritten.
- Project research skill now explicitly requires cross-output semantic verification and preservation of identity qualifications.

## Checks

| Check | Local | Public at fetch |
|---|---|---|
| James and unnamed-child parents agree across HTML, embedded JSON, presentation, default fields, claims and networks | Pass | Still failing |
| Reciprocal approved relationship roles, interpretations and source references agree | Pass | Still failing in exported defaults |
| Robert's resolved vitals preserve identity alternatives and imported history | Pass | Still failing in exported defaults |
| Robert's separate open father hypothesis and historical attachment survive | Pass | Pass |
| Thomas ordering, Mary's event role, Samuel's separate recorded names, letter possession and single Thomas proof | Pass | Pass |

Commands run:

```sh
.venv/bin/python tools/repair_person_hierarchy.py Glasgow-951 Glasgow-3939 Glasgow-3940 Glasgow-1367 McCaughan-222 Glasgow-3167 Glasgow-987 Glasgow-3896 Glasgow-2413 Glasgow-3975 Glasgow-938 Glasgow-438 Glasgow-973
.venv/bin/python -m unittest tests.test_resolved_public_model tests.test_publish_resolved_dossiers tests.test_robert_hypothesis_exports tests.test_dossier_parents tests.test_dossier_cleanup tests.test_person_dossier_presentation
.venv/bin/ruff check tools/publish_resolved_dossiers.py tools/repair_person_hierarchy.py tools/verify_dossier_delivery.py tests/test_resolved_public_model.py
.venv/bin/python tools/check_public_catalogue.py
.venv/bin/python tools/audit_site_experience.py
.venv/bin/python tools/verify_dossier_delivery.py
.venv/bin/python tools/verify_dossier_archive.py www/glasgow-site-20260912-resolved18-2.tar.gz
```

Targeted generation completed; a repeat produced zero HTML changes. 45 tests passed, lint passed, catalogue checks passed, and 35 experience checks passed. Tests compare actual relationship roles, reasons, sources and historical scope, not just status strings. They also cover standalone publication, idempotence, revocation, unchanged mother assessments, qualified dates and raw WikiTree preservation.

Browser screenshots were captured and inspected for Glasgow-951, 3939, 3940, 1367, 987, 3167 and McCaughan-222 at 1440px and 390px. Family tables reflowed without page overflow; exactly one section-navigation variant was visible. Keyboard Enter opened James's parent disclosure; its supporting-source link opened the source disclosure and reached the visible record. Browser-only link rewriting uses absolute fragment destinations; the first automation selector needed adjustment. Console errors were refused Google Analytics requests, not dossier script failures. No new live visual, 200% zoom or no-JavaScript browser pass is claimed.

Screenshots: `output/playwright/resolved-model-*.png`. Exact source/local/public comparison, HTTP response headers, fetch timestamps and SHA-256 values: `artifacts/dossier-delivery/20260912T101036Z/report.json`, with the fetched public responses beside it. All seven fresh renders matched saved local HTML. All fourteen fetched dossier/network exports differed from corrected local exports.

## Release and remaining scope

Upload archive: `www/glasgow-site-20260912-resolved18-2.tar.gz`. Release manifest: `www/dossier-release.json`, release `dossier-resolved-18.2`. Base source commit: `42af56555bb59832bf1b244550ecbd003142e412`, with uncommitted work; the commit alone does not identify this release. The manifest includes source-input and output hashes.

Base catalogue data build remains `a719ef58108a4436e8ef` (assembled 2026-09-12 09:09 UTC). This is the unchanged catalogue-generation identifier, not the identifier of the new research-resolution overlay or a frontend deployment. No live deployment was performed; the public site still requires the new archive.

The genuine editorial issue is unchanged: no record establishes that the Lisnagaver occupier and Glenleslie Robert are the same man, or that Robert was Alexander's father. Catherine is not promoted to an active mother hypothesis. Child death boundaries remain inferred, independently of documented parents. Elder-7251 has no local dossier; its approved reciprocal perspective is retained in the shared register and its existing external WikiTree link is tested. No unresolved record mapping remains for the assessed relationships on the acceptance dossiers.
