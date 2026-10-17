# Catalogue identity review — 17 October 2026

All 511 original worklist items have dispositions: 455 existing-profile matches
(including explicitly tentative candidates), 29 cases requiring new-profile
suggestions, 14 existing studies and 13 exclusions from separate profile creation.
The 29 creation cases consolidate into 27 sourced people, with complete public
drafts in the catalogue's “Needs updated on WikiTree” section and the maintained
`surname-research/to-update.md` register. Unnamed occurrences and non-surname
associates remain in their historical evidence accounts.

`baseline.json` freezes the original denominator. `progress.json` records every
original ID, including grouped members and explicit individual draft destinations.
The current worklist consolidates repeated notes; a smaller visible row count does
not delete a source, merge live people or change the 511-item review denominator.

The four scoped reports retain actual searches, inherited search dates, source
citations, candidate comparisons and unresolved record-specific qualifications.
Source collections are distinct from person/case grouping keys. Missing fields
and missing extra corroboration are not exclusions. The final William Alexander
check therefore retained compatible plain-William profiles instead of proposing
a duplicate; competing father/daughter identities remain separately qualified.

`integrate.py` applies the supplied scope reports, preserving earlier assessments
and individual event mappings. `refresh_drafts.py` refreshes source dispositions
and the creation register. `verify.py` checks the complete baseline, visible queue,
actual draft contents, newspaper publication and full/compact filter membership, including every main-catalogue creation and amendment.
`candidate-notes.json` records new comparisons carried into person findings and
public subject accounts. The follow-up integration creates 59 previously absent existing-profile accounts, checks basic public metadata for 18 former ID-only rows, and updates 287 complete proposed biographies. Eight checked profiles already covered their relevant records. The main No WikiTree link filter is now 90 (formerly 63), and WikiTree updates is 495 (formerly 269): 88 existing queued drafts were revised, 199 existing-profile amendments were added, and 27 creation drafts were added. Two creation drafts retain source-verification holds. Five complete comparisons contain private family material and remain local; their safe historical additions are explicitly labelled on the public site.

All synchronization is local. No live WikiTree edits, profile creations,
messages, merges, pushes or production deployment were performed.

Two source drafts with confirmed record destinations were moved from the creation
folder to Glasgow-3175 and Glasgow-634. `draft-retirements.json` preserves the old
locators appearing in the frozen input evidence.

The initial 511-item identity audit did not fully integrate the main filters or replacement biographies. `catalogue-integration.json`, `prepare_catalogue_integration.py`, `assemble_amendments.py` and `finalize_catalogue.py` now maintain that integration. The public record passages are in `amendments/`; full public replacements are in each person’s research folder, and private comparisons remain under ignored `data/wikitree/`. The catalogue builder consumes these maintained inputs so a rebuild retains both work queues. `verify.py` asserts each creation’s membership in both filters, each amendment’s actual draft or labelled private-comparison state, public research sections and full/compact index equality.
