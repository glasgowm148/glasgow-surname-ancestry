# Held research review — 30 September 2026

Reviewed all 107 unresolved IDs from the original 140-item worklist across Scottish OPR, older records and Irish collateral lanes. Reports retain searches, inspected sources, compatible candidates, concrete exclusions, source-input patches and next tests. `baseline.json` preserves prior assessments; `integration-summary.json` records the current totals.

Added 21 findings to the 516-entry Latest Findings ledger. Five Irish documentary father statements were found; no existing-profile uncertain/unknown father relationship was proved certain, and no adult identity was newly confirmed. Current review register has 79 compatible, 23 unmatched, four unnamed and one partly matched case, alongside linked subjects and open questions. One new sourced Margaret Androsoune companion draft links the compatible Anderson-3241 candidate. Sparse candidates were retained unless concrete conflicts exclude them.

The Edinburgh 1648 apprentice is **John Gray**, expressly son of deceased Thomas Gray, maltman and burgess of Glasgow: printed Gray heading, p.75/PDF86. The former John Glasgow reading is superseded. Stable dossier IDs and bookmarks remain. Gray candidates and the father candidate remain qualified. Printed Scottish transcriptions were inspected, not original OPR manuscripts. The Sneddon parent names come from an inspected FamilySearch index; the restricted original image remains uninspected.

`pending-amendments-review.json` covers 11 fresh public-profile comparisons: eight managed profiles and three managed by others. Current biographies matched saved captures and distinct cited source URLs were retained. Application review is visible on the site. **No WikiTree edits were saved.**

Maintained sources, subject drafts, OPR review, profile dossiers, Latest Findings and the catalogue queue were synchronized locally. The queue groups 138 handoffs into 89 cases while separate people/event assessments remain expandable. Twenty affected tests pass; desktop and mobile findings rendering and grouped-case expansion were checked. No production upload was performed. Final archive path, checks and size are recorded in `output/queue-resolution-verification-20260930.json` after packaging.

Rerun order: `integrate.py`, `update_findings.py`, subject/OPR builders, targeted profile synchronization, `correct_gray_record.py`, Latest Findings and research-queue builders. These batch scripts preserve original review history and finding dates. Do not rerun older exploratory lane-finalizer scripts over the reviewed conclusions.

Verified release: `www/glasgow-site-20260930-230811.tar.gz`, 144,006,593 bytes (144.01 MB), SHA-256 `b4110ceaa1317b482e0378bf6fa0f6800b797cbea9f19bc2af06a121d26940f6`. Release totals, Atlas destinations, publication boundary (zero failures), gzip integrity and nine selected archive/current-file hashes pass. The earlier archive is superseded. Production remains unchanged.
