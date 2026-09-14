# Person dossier cleanup — 12 September 2026

## Implementation

The existing person-page generator and layout remain in use. Presentation 17:

- Fixes the inherited flex-header collision and clipping in the mobile selection toolbar.
- Uses one opening account, compact family disclosures, question answers, and collapsed supporting evidence, chronology, research and sources. Green ticks denote documented relationships; uncertain relationships retain text labels and amber styling.
- Keeps the complete Thomas–Daniel argument at `#question-thomas-network`. Earlier parent-question record anchors link to the canonical rows instead of repeating them.
- Merges canonical record facts and person-specific roles rather than allowing local copies to shadow them. Dates sort by normalised year/month/day; ranges use their stated starting boundary, with display qualifications preserved.
- Opens every ancestor disclosure for a deep link. WikiTree export copying preserves the original text.
- Rebuilds from inputs even when the presentation version is unchanged; version-only skipping had allowed stale generated content to survive.

Maintained inputs changed: `research/Glasgow-951/presentation.json`,
`research/Glasgow-3939/presentation.json`, `research/Glasgow-1367/presentation.json`,
`research/canonical_records.json`, `research/relationship_assessments.json`.
Original findings, imported values, private source files and WikiTree drafts were not edited.

The additive `presentation` object in each public dossier JSON exposes the same
resolved vitals, relationships, record associations and research account used by
the HTML. It does not turn the retained legacy/import fields into reviewed facts.
Its frontend version is separate from the base catalogue's data build identifier.
There is no automatic production deployment.

## Research coverage and remaining decisions

| Subject / question | Publication treatment | Remaining decision or evidence |
| --- | --- | --- |
| James, entry 75 | Exact 17 January 1837 birth agreement; 9 February baptism stated separately. Child identification, adult-parent continuity and death inference have separate questions. | Adult continuity between Gortereagh and Lisnagaver remains indirect; no burial found. Before 1841 remains an inferred boundary, not an exact death. No relationship confidence was automatically upgraded. |
| Robert, profile scope | Opening, facts, family note, evidence question and exported presentation explicitly separate Lisnagaver from Glenleslie. | The maintained Current conclusion describes Glenleslie, while the explicit land-sequence decision retains the Lisnagaver occupier. A bridge, incompatible overlap or explicit editorial scope decision is still required. |
| Robert, birthplace | Antrim attributed to the Glenleslie census; Tyrone attributed to the imported profile. Neither is transferred unconditionally to the Lisnagaver occupier. | Whether the Glenleslie facts belong to the Lisnagaver man is unresolved. |
| Robert, Alexander's father | One shared possible-relationship basis in both directions; retired pedigree attachment distinguished from an open father hypothesis. | No direct parentage record. Failure of the acreage argument does not exclude Robert. |
| Acreage interpretation | Rejected inference and operative correction remain separately identified. No conversion is asserted for the particular tithe entry. | General use of Plantation measure does not establish the actual unit or parcel correspondence here. |
| Thomas–Daniel | One complete proof argument, separate will and marriage records, retained legacy anchors. | Alexander's brother/cousin connection remains unproved. PRONI will search is linked and labelled; a stable public item/image URL is not supplied. The maintained manifest records inspection of the original. |
| Other retained fixes | Thomas's ordering, Mary's own-death role, shared baptism/death sources, Samuel's two recorded name forms, and John-letter possession preserved. | Possession of the letter is not examination. The Samuel census/birth-index identity bridge remains qualified. No private correspondence or DNA originals were newly published. |

## Verification

Commands:

```text
.venv/bin/python tools/repair_person_hierarchy.py
.venv/bin/python tools/publish_research_release.py
.venv/bin/python -m unittest tests.test_person_dossier_presentation tests.test_dossier_cleanup tests.test_publish_resolved_dossiers tests.test_research_catalog -q
.venv/bin/python tools/audit_site_experience.py
.venv/bin/python tools/check_public_catalogue.py
.venv/bin/python tools/build_dossier_coverage_report.py
.venv/bin/python tools/verify_dossier_delivery.py
```

87 tests considered: 34 ran successfully, 53 existing environment-dependent tests
skipped. Site-experience contracts: 35 checks, no failures. Catalogue check and
Ruff on changed Python/test files passed.

Real Chromium screenshots were captured and inspected for all six acceptance
pages at 1440 and 390 pixels. Alexander's expanded proof was additionally checked
at 768 and 360 pixels. No horizontal page overflow or duplicate visible dossier
navigation was found. Keyboard disclosure activation, nested correction links,
source links, exact clipboard copying and a JavaScript-disabled reading context
were exercised successfully. A 720-CSS-pixel viewport at device scale 2 checked
200%-equivalent reflow; this is not a claim of browser-toolbar zoom testing.
An additional CSS-zoom experiment exposed inherited shell crowding and is not
counted as a successful browser-zoom test. A blocked analytics request was the
only observed console resource error; no dossier JavaScript error was observed.

At 390 pixels, default Alexander page height fell from 37,169 pixels on production
to 4,888 pixels locally (about 87% shorter). Evidence remains in the document and
can be opened without JavaScript. Screenshots: `output/playwright/final-*.png`,
`proof-expanded-*.png`, `family-keyboard-390.png`, `family-expanded-final-1440.png`.

Network comparison captures and exact hashes are written to
`artifacts/dossier-delivery/<UTC fetch time>/report.json`. Fresh rendering is
compared byte-for-byte with saved HTML before comparing with public responses.
The public pages fetched during this pass still lacked the new Robert, James
and duplicate-proof corrections. The upload archive is a local handoff, not a
deployment claim.

## Upload artifact

`www/glasgow-site-20260912-cleanup17.tar.gz` (117 MB), SHA-256:
`bc25998a4f959d23e67e64da12aeb0b52b04eb96c8cd3189482b3712e75a863a`.
`tools/verify_dossier_archive.py` verified the six HTML files, six dossier JSON
files, shared stylesheet and release marker byte-for-byte against the local
build; no older tar archives are nested inside it. The archive's contents belong
directly in the website root, not a new `www/` subdirectory.

Final network evidence: `artifacts/dossier-delivery/20260912T084555Z/report.json`.
Base catalogue data build: `22bc5081316c6a88fbbe`; frontend presentation: `17`.
Commit: `42af56555bb59832bf1b244550ecbd003142e412`, plus the uncommitted changes
listed above. After upload, `/dossier-release.json` provides the release name and
per-page hashes; its presence alone is not a substitute for matching those pages.
