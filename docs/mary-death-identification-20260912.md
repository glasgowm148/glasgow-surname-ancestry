# Mary McCaughan: focused death-identification reconciliation

The cautious presentation was stale. The maintained 5 September master
integration explicitly assesses the Gortahar death pair as high-confidence
identifications through Mary Elder. Her 1871 marriage, Lisnagaver residence,
named father Alexander and Robert Elder's lot-25 succession supply the identity
bridge. The death return does not itself name a husband or maiden surname;
its age of 89 also conflicts with Mary's c.1811 estimate. These are limits on a
strong combined-record identification, not a requirement for another marriage.

The existing approved-assessment register now publishes `date_precision: day`
and `identification_status: strongly_supported` separately. The register date
remains exact rather than approximate. Mary's opening, evidence discussion,
facts, default/embedded/network JSON and linked date displays share the resolved
position. No generator, stylesheet or relationship decision was changed.

## Date correction applied

Original civil death entry 234 was downloaded and visually checked on 12
September. It reads **Seventeenth February 1892**, independently confirmed from
the full page and enlarged row. The earlier 27 February transcription is now
superseded in the maintained research, canonical record and public assessment.
`date_readings` retains it only as correction provenance. This is not uncertainty
about the legible word or a downgrade of Mary's identity. Mary Glasgow-3167's
open-ended death boundary is correspondingly corrected to after 17 February.

## Verification

- Targeted research sync for McCaughan-222: passed; follow-up reported no stale findings.
- Regenerated Mary and linked acceptance/family dossiers with `tools/repair_person_hierarchy.py`.
- 47 tests passed across `test_mary_death_identification`, `test_resolved_public_model`, `test_publish_resolved_dossiers`, `test_robert_hypothesis_exports`, `test_dossier_parents`, `test_dossier_cleanup` and `test_person_dossier_presentation`; new test file passed Ruff.
- Visually inspected Mary's header and expanded evidence at 1440px and 390px. No horizontal page overflow. Checked the qualified date in Alexander's family table.
- Public HTML/JSON fetch: `artifacts/dossier-delivery/20260912T103530Z/report.json`. Previous James, unnamed-child, Robert and reciprocal export checks still pass publicly. Mary's new assessment is local only; public exports still lack it. That report captures the initial local qualifier wording; final screenshots use the shorter correction-pending wording.
- Original sources and historical imports retained. No live WikiTree edit, deployment or new upload archive was made in this pass; date correction should be settled before packaging another release.

Inputs changed: `research/McCaughan-222/presentation.json`, its new `findings.md`,
`research/canonical_records.json` (marriage evidence made available to Mary's
dossier), `www/assets/research/assessments.json`, the narrowly updated project
research skill, and the new regression test. Generated person and shared-data
outputs were refreshed through the existing pipeline.
