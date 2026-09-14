# Dossier presentation 18 — parent comparisons and baptism relationships

## Implemented

- Shared documented assessments for James (Glasgow-3939) and the unnamed
  child (Glasgow-3940), each with Alexander and Mary/Molly. Both directions
  use the same record IDs and reviewed family identification. No confidence
  is propagated to a different child's mother or inferred death date.
- `research/Glasgow-951/parent_candidates.json` is the maintained comparison
  inventory: 10 current hypotheses, 3 retired/excluded proposals and 2
  collateral comparisons. These are hypotheses, not 15 distinct fathers.
  The renderer publishes this inventory without maintaining another copy.
- All 10 stored algorithm matches remain accessible with their original
  factors and deductions. Reviewed exclusions take precedence. Rosanna's
  individual score is explicitly not a score for the proposed couple;
  absent scores are not fabricated. Automated output alone does not create
  a new main-account parentage question on other dossiers.
- Forest-green identity header, warm reading surfaces, compact facts,
  documented-relationship ticks visible in closed family groups, and
  collapsed candidate arguments. Original research and WikiTree exports
  remain accessible. Research-note anchors support candidate backlinks.

## Research coverage and unresolved questions

The earlier report's decision not to upgrade baptism relationships is
superseded by this explicit 12 September assessment of entries 75 and 106
and the already-maintained family reconstruction. This is a correction of
unmapped evidence, not a new baptism discovery.

Still unresolved: the early children's exact death dates and the unnamed
child's forename; Alexander's parents; Robert's Lisnagaver/Glenleslie identity
bridge; the source behind the Alexander/Rosanna tradition. Later James's
separate identification remains strongly supported, not automatically
upgraded by the early child's evidence. Candidate source-path provenance
is retained internally; only existing public record and dossier routes are
linked, rather than inventing downloadable research-file URLs.

## Verification scope

Regression coverage includes all six earlier acceptance dossiers plus the
unnamed child, four shared baptism relationship bases, candidate completeness,
unchanged scores, exclusion precedence, internal source/record anchors,
chronology, supersession, reciprocal relationship wording, Samuel's separate
name sources, John-letter possession and original WikiTree markup.

Browser checks cover 1440px and 390px across all seven dossiers; 768px and
360px candidate controls; keyboard open/close; nested disclosure deep links;
no-JavaScript reading/native disclosure operation; exact clipboard copying.
Screenshots are under `output/playwright/final18-*`. No new private originals
or DNA data were introduced. Production publication remains a separate upload.

The release manifest records frontend version 18, the base data build ID,
source commit and HTML hashes separately. The upload archive is checked
against its manifested HTML, JSON and stylesheet before delivery.

Final results: 38 tests passed; 53 existing catalogue fixture tests skipped.
Ruff passed; 35 site-experience checks passed; public-catalogue checks passed.
All seven fresh renders matched saved local HTML byte-for-byte. Network fetch
at 2026-09-12 09:18:11 UTC still returned the previous frontend, not version
18: `artifacts/dossier-delivery/20260912T091811Z/report.json` contains full
hashes and response headers. No deployment was performed. Only blocked
Google Analytics requests appeared in the browser console. The 200% check
used a 720 CSS-pixel viewport at device scale 2, not browser-toolbar zoom.
