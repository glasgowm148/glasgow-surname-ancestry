# Father confidence and branch connections

Use this workflow to connect the Glasgow branches and improve father assessments for people born before 1850, especially the earliest generations. Later records can resolve those earlier people. Work within the existing catalogue, relationship model and site; keep the research goal active while unresolved branches remain.

## Choose work that can change the tree

- First close gaps in individual father-rating coverage. An absent father needs a defensible candidate, not an invented percentage. Then prioritise uncertain links supporting large branches and a specific evidence test likely to change the result.
- Use `research/ancestry-connections/rank_working_joins.py --scope unrated` for coverage and `--scope all-unconfident` for reassessment. Check the current progress page and canonical assessments before relying on an older queue.
- Rating coverage includes retained selected named fathers outside the surname graph or without a local father dossier. Exclude anonymous placeholders and unselected alternatives; unavailable graph impact is not zero. Keep current named-father coverage separate from historical graph-link coverage, and verify the denominator before declaring coverage complete.
- Include `--scope unknown --through 1850` when dispatching research, alongside named uncertain links. It ranks actual working descendant reach without inventing a father or connection gain. Documentary connectors outside the measured cohort and unavailable accounts are labelled separately; do not add them to the site's Unknown count. Use an earlier saved cutoff when concentrating on the earliest families.
- Prefer actual new/replacement father proposals and substantial confidence improvements over repeatedly regrading already-confident parents. Keep chronological priority, descendant impact and attainable evidence separate; a large connectivity gain is not evidence of parentage.
- Start with held findings, complete biographies, existing records and family studies. Use bounded QMD/PDF retrieval under AGENTS.md. A useful tentative family connection can follow from combined evidence without a literal father clause. After a bounded review yields no new discriminant, retain the rating and move to another useful test; do not repeat broken-link checks or unchanged source sweeps.

Before choosing a case, run `python -m tools.research_preflight --id Glasgow-N --father Glasgow-M` for its exact overall Current conclusion, completed plans/tests, current approved assessments and up to five linked canonical sources with original pointers. The packet is internal and may contain unpublished notes; never publish or index it. An omitted/truncated item is not absent evidence. `linked_parent_record_needs_review` flags inspected, explicitly linked parent evidence not acknowledged by the current assessment; it does not assign confidence. Read the relevant parent/sibling account when its evidence is cited but not yet reconciled in the child account.

The packet also includes bounded literal kinship leads from eligible captured biographies and current draft paths for both subjects, with exact capture pointers or file/line/character locators. Read the original paragraph and its cited authority before judging the relationship: a copied statement is a lead, not an independently inspected source. These private excerpts do not select a parent, assign a grade or establish that an earlier review overlooked the passage. Follow explicit truncation markers before calling a source absent or a test unperformed.

For an Unknown father, child-only preflight exposes bounded parent/kin paragraphs without retrieving an unverified parent account. Check the current account of any named candidate before repeating its source test: the candidate's identity may already have been resolved elsewhere while the child's summary is stale. Save explicitly reviewed readiness and precise reopening evidence on the existing assertion/estimate, or the person's `research_plan.json` when no father is selected; an unchanged review is not a confidence finding.

Use `rank_working_joins.py --scope all-unconfident --preflight --limit 5` for a bounded dispatch shortlist. Its default actionable order uses explicitly reviewed `research_state.disposition` on existing assertions: `ready`, `awaiting_source` or `reviewed_no_change`; unreviewed readiness remains `unknown`. It also respects the existing explicit `evidence_test.held_evidence_review_exhausted` flag and `resume_when`, with an explicit reopened state taking precedence. Legacy links without an assertion can retain workflow state on their existing father-pair probability estimate; do not invent an assertion solely for dispatch metadata. Retain `last_test`, `next_test`, the precise blocker and the trigger for reopening. Reopen when that evidence/access changes, not because branch impact ranks highly again. For a named father, bind a per-person plan with `research_state.father_id` to the exact reviewed parent. Check an older unbound review against the current pair before adding that binding. Dispatch uses matching plan readiness only when assertion/pair readiness is unreviewed; a former father’s hold must not suppress a replacement or an Unknown-father investigation. Explicit `--sort working-pairs` and `--sort confident-gain` retain pure impact views; do not reinterpret readiness as confidence or alter connectivity mathematics.

For known IDs, read the maintained file directly or use bounded QMD `get`, for example `tools/genealogy/qmd get 'qmd://historical-notes/open-profiles/Glasgow-3166.md:1:80'`. For shell lexical search use an unquoted ID token in the query (`tools/genealogy/qmd search Glasgow-3166 -n 3 --json`); do not wrap the search expression in literal quote characters. An empty quoted-ID query does not establish missing notes. No embedding download is needed for this lookup. Verify the original file/JSON pointer before a historical claim.

## Assess the complete relationship

Compare chronology, actual versus estimated dates, residences, occupations, spouses, siblings, associates and property together. Check compatible existing profiles before creating anyone. Missing fields or absent corroboration do not exclude a candidate. Preserve alternatives with concrete reasons.

Before retrieving an original, search the shared catalogue and held notes by its distinctive date, place, archival reference and named kin, beyond the selected profile IDs. Another profile may already hold its inspected original or a competing identity. Reuse that reading and compare the accounts before a new lookup. Apply an explicit family account consistently across its named siblings; an older tree-only percentage must not silently override a subsequently inspected parent statement. Keep retrospective family roles separate from unproved vital dates, migration and later identities.

Distinguish the father named in a record from identification of that father with a particular adult profile. A documented sibling relationship, shared surname, compatible chronology and an established paternal identification for one sibling can justify a confident paternal inference for the other. Explain that inference; do not demand an unsupported hypothetical half-sibling alternative. Assess mothers independently.

Assign one justified subjective percentage to the complete selected father–child proposition. Preserve the prior percentage **or actual qualitative grade**, source basis, scope, alternatives and review date. Do not substitute a band midpoint, multiply supposedly independent probabilities, or let a new percentage alone select or replace a parent. Shared Y-DNA supports a common paternal origin, not a named father or missing generation.

Use inspected original records when accessible. A checked published transcription can still support a qualified conclusion: cite its provenance and say the original is uninspected. Correlated indexes or copied obituaries are not independent witnesses. Verify printed/PDF page numbers before citing them. Preserve unresolved vital-date discrepancies separately rather than silently replacing a field.

## Divide research, centralise integration

Give workers separate branches, families or bounded mechanical tasks. Use the cheapest reliable native model; no Astra. Reuse workers. Request concise handoffs containing subject/father IDs, prior and proposed percentages/grades, evidence IDs and exact locators, reasoning, limits, and affected site surfaces. Unchanged findings are valid; do not manufacture upgrades.

Every worker must know that browser launches and PDF/browser rendering are parent-owned and sequential. Reuse one browser/session and temporary working tab; retain resource ownership receipts and preserve the user's tabs. Maximum agents means lightweight parallel research. Keep shared catalogue/tree publication and staging with one orchestrator to avoid competing writes.

Send the current conclusion, one specific test, exact source IDs/locators and prior completed tests with each assignment. Require the handoff to say what was actually inspected. An unattempted task is an operational failure, not negative genealogical evidence or completed coverage: retry once with a narrower packet or handle it locally, and use a more reliable native model if the same worker repeatedly fails to inspect evidence. Do not repeat broad discovery merely to keep slots occupied.

## Save the conclusion in maintained inputs

Reuse assertion, person, draft and source IDs:

- Relationship assessments live in the research database (`data/private/workbench/glasgow.sqlite`), not in JSON. Reassess an existing assertion with `.venv/bin/genealogy --project . history glasgow-assertion:<assertion-id>` then `.venv/bin/genealogy --project . assess glasgow-assertion:<assertion-id> --expected-revision N --status <label> --grade <label> --estimate <percent> --reasoning "…" --limitations "…" --assessed-on YYYY-MM-DD --basis <record-id> …`. The earlier revision stays as history; both directions of the pair derive from this one assessment. A new pair is `relationship add wikitree:<child> father|mother wikitree:<parent>` followed by `assess`. For a batch, write a proposal file and run `genealogy proposal check|diff|apply`.
- Then run `make research-views` to regenerate `research/relationship_assessments.json` and `research/relationship_probability_estimates.json` for the existing builders. Never edit those two files by hand: `make check-workbench` fails when they differ from the database. Preserve already-confident marks and competing assertions as separate claims.
- Canonical records (via `tools/research_entry.py upsert record`; never hand-edit `research/canonical_records.json`): new public-safe evidence, original-provider citation and reviewed provenance. Post-1900 evidence requires a sourced `historical_basis` birth bound; the event year is not the subject's birth cutoff.
- Each subject's `findings.md`: one overall Current conclusion, a dated sourced account and supersession of stale questions. Cross-reference relatives and reconcile existing studies rather than creating another current account.
- Complete replacement drafts, `research/queue-review-2026-10-17/catalogue-integration.json`, the local update queue (edit `data/wikitree/profile-update-queue.json`, then `tools/research_entry.py document data/wikitree/profile-update-queue.json --expected-revision N`) and `surname-research/to-update.md`: preserve existing text/citations and use explicit `add`, `replace` or `regrade` amendments. A newly confident existing father is not a new father attachment. Retain proposed-relative links and confidence metadata for catalogue filters and priority sorting.
- Findings (via `tools/research_entry.py upsert finding`; never hand-edit `research/latest-findings.json`): dated substantive discoveries, linked subjects, sources, qualification and actual relationship changes. Valid finding statuses are `confirmed` and `qualified`. Exclude UI work, unchanged reviews and negative searches.

Review complete drafts and preservation hashes together. A stale hash requires comparing the exact reviewed/effective texts, checking new evidence, preserving sources and accounting for superseded passages. Never merely refresh a digest to bypass the check.

For a replacement father, set `working_parent_replacement` with the previous parent and retained alternative assertion; mark that assertion `lifecycle: alternative`. Preserve the previous father ID, grade and sources in `provenance.prior_assessment`. Do not reuse his percentage as a past rating of the new pair.

## Synchronise and measure

Follow `docs/website-research-sync.md`. Use the relevant existing builders, not a full rebuild by default. New opted-in sources use `tools/ingest_canonical_records.py`; reviewed overlays use `tools/publish_resolved_dossiers.py`; targeted accounts use `tools/sync_catalogue_research.py --write <IDs>`. Refresh the actual main Whole tree, its packed payload and standalone model, `tools/build_ancestry_progress.py`, Latest findings and any affected search/navigation/sitemap surfaces. Resolve stale asset references when needed; do not run expensive unrelated repairs by rote.

Batch shared publication under one orchestrator and reuse the read-only source cache within each sync/repair invocation. Complete section builders and backlinks before the final required person render. Do not delete preliminary legacy/diff handling or skip resolved-parentage publication without verifying the affected contract; avoid extra repair/finalization passes merely as a precaution. Verify the new finding IDs in the rendered log and reviewed record IDs in the actual full/compact indexes: later record generators or concurrent snapshot-based publishers can overwrite an otherwise successful build. Replay only affected publication steps after those writers finish. Final content hashes must reflect dependencies' final bytes, with a zero-stale check, rather than relying on a fixed number of blind whole-site passes.

Resolve replacement parents before building the trees. Otherwise the tree builder can restore the former father from a stale current dossier. Verify the selected father set in all three models before the final asset stamp; the old father belongs only among alternatives.

Check actual catalogue filter membership and full/compact agreement, complete drafts, reciprocal relationships, source qualifications, tree selections and preserved vitals. Run the required scoped publication check and `make check-links`. Verify local routes and relevant rendered behavior; report a genuine browser blocker honestly. Reuse the local server, starting it only if absent. Local synchronisation is separate from deployment or live WikiTree saves.

Progress must distinguish new genealogical joins, confidence changes and initial coverage:

- Count first percentages when a saved earlier confidence grade changed; do not invent the earlier percentage. Exclude unchanged initial assessments and newly indexed people from confidence gains.
- Preserve decreases and within-grade percentage changes. Show Confident, Probable, Possible, Uncertain and Unknown together, with current totals separate from the event trend.
- Unknown means no retained named father, not an ungraded named parent. Reduce Unknown only for a previously absent father; replacements with ungraded predecessors must not fabricate an Unknown decline.
- Reconcile new/replacement recommendations with explicit catalogue amendments, selected-cohort membership and exclusions. A missing later attachment flag must not hide an existing reviewed proposal. Use real review dates; keep undated findings visible without invented timestamps.
- Preserve saved measurements and prior assessments. Label net-change baselines and changing review coverage honestly; indexing or publication reconciliation must not appear as a new genealogical connection.

Commit each verified coherent batch before queued follow-up work. Stage only owned changes; preserve unrelated work in shared files. Batch Git reads/writes when many generated cache references change. Do not push. Before handoff, reconcile owned resources again, stop finished renderers/jobs, and report precisely what was released without claiming a hard memory cap.

## Announce findings in the chat

Once a substantive relationship finding is checked and saved, announce it in a separate, prominent blockquote card so it remains visible when the owner scrolls back. Use a short heading such as **New father proposal**, **Father confidence improved**, or **Confidence corrected**, with a restrained coloured icon. Give the named child and father, exact before/after percentages and resulting grade, one sentence explaining the decisive evidence, and checked biography and WikiTree links. Use one card per relationship, or clearly separated rows for a closely related sibling batch. Include decreases and within-grade changes; exclude unchanged reviews, bulk first ratings, indexing and UI work.

For example:

> 🟢 **Father confidence improved**
>
> **[Child](local-biography-URL) → [Father](father-WikiTree-URL): 71% → 95% · Confident**
>
> The baptism names both parents and matches the established household.
>
> [Biography](local-biography-URL) · [Child on WikiTree](child-WikiTree-URL)

For a previously absent father, write **Unknown father → 82% · Probable**, not an invented 0%. For an unmeasured prior grade, retain that actual grade without inventing a percentage. Label a replacement with both fathers. Reserve “new father” for an actual new/replacement attachment; a stronger assessment of an attached father is a confidence improvement. If site synchronization is not finished, say so in the card and complete the normal publication batch. Announcements do not replace the maintained assessment history, latest findings or progress log, and must not imply a live WikiTree save.
