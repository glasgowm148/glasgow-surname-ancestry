# Father confidence and branch connections

Use this workflow to connect the Glasgow branches and improve father assessments for people born before 1850, especially the earliest generations. Later records can resolve those earlier people. Work within the existing catalogue, relationship model and site; keep the research goal active while unresolved branches remain.

## Choose work that can change the tree

- First close gaps in individual father-rating coverage. An absent father needs a defensible candidate, not an invented percentage. Then prioritise uncertain links supporting large branches and a specific evidence test likely to change the result.
- Use `research/ancestry-connections/rank_working_joins.py --scope unrated` for coverage and `--scope all-unconfident` for reassessment. Check the current progress page and canonical assessments before relying on an older queue.
- Prefer actual new/replacement father proposals and substantial confidence improvements over repeatedly regrading already-confident parents. Keep chronological priority, descendant impact and attainable evidence separate; a large connectivity gain is not evidence of parentage.
- Start with held findings, complete biographies, existing records and family studies. Use bounded QMD/PDF retrieval under AGENTS.md. A useful tentative family connection can follow from combined evidence without a literal father clause. After a bounded review yields no new discriminant, retain the rating and move to another useful test; do not repeat broken-link checks or unchanged source sweeps.

## Assess the complete relationship

Compare chronology, actual versus estimated dates, residences, occupations, spouses, siblings, associates and property together. Check compatible existing profiles before creating anyone. Missing fields or absent corroboration do not exclude a candidate. Preserve alternatives with concrete reasons.

Distinguish the father named in a record from identification of that father with a particular adult profile. A documented sibling relationship, shared surname, compatible chronology and an established paternal identification for one sibling can justify a confident paternal inference for the other. Explain that inference; do not demand an unsupported hypothetical half-sibling alternative. Assess mothers independently.

Assign one justified subjective percentage to the complete selected father–child proposition. Preserve the prior percentage **or actual qualitative grade**, source basis, scope, alternatives and review date. Do not substitute a band midpoint, multiply supposedly independent probabilities, or let a new percentage alone select or replace a parent. Shared Y-DNA supports a common paternal origin, not a named father or missing generation.

Use inspected original records when accessible. A checked published transcription can still support a qualified conclusion: cite its provenance and say the original is uninspected. Correlated indexes or copied obituaries are not independent witnesses. Verify printed/PDF page numbers before citing them. Preserve unresolved vital-date discrepancies separately rather than silently replacing a field.

## Divide research, centralise integration

Give workers separate branches, families or bounded mechanical tasks. Use the cheapest reliable native model; no Astra. Reuse workers. Request concise handoffs containing subject/father IDs, prior and proposed percentages/grades, evidence IDs and exact locators, reasoning, limits, and affected site surfaces. Unchanged findings are valid; do not manufacture upgrades.

Every worker must know that browser launches and PDF/browser rendering are parent-owned and sequential. Reuse one browser/session and temporary working tab; retain resource ownership receipts and preserve the user's tabs. Maximum agents means lightweight parallel research. Keep shared catalogue/tree publication and staging with one orchestrator to avoid competing writes.

## Save the conclusion in maintained inputs

Reuse assertion, person, draft and source IDs:

- `research/relationship_assessments.json`: current selection/status, exact probability, reason, record scope, source IDs, provenance and retained `assessment_history`.
- `research/relationship_probability_estimates.json`: matching per-pair estimate, source basis and prior review. Preserve already-confident marks and competing assertions independently.
- `research/canonical_records.json`: new public-safe evidence, original-provider citation and reviewed provenance. Post-1900 evidence requires a sourced `historical_basis` birth bound; the event year is not the subject's birth cutoff.
- Each subject's `findings.md`: one overall Current conclusion, a dated sourced account and supersession of stale questions. Cross-reference relatives and reconcile existing studies rather than creating another current account.
- Complete replacement drafts, `research/queue-review-2026-10-17/catalogue-integration.json`, the local update queue and `surname-research/to-update.md`: preserve existing text/citations and use explicit `add`, `replace` or `regrade` amendments. A newly confident existing father is not a new father attachment. Retain proposed-relative links and confidence metadata for catalogue filters and priority sorting.
- `research/latest-findings.json`: dated substantive discoveries, linked subjects, sources, qualification and actual relationship changes. Valid finding statuses are `confirmed` and `qualified`. Exclude UI work, unchanged reviews and negative searches.

Review complete drafts and preservation hashes together. A stale hash requires comparing the exact reviewed/effective texts, checking new evidence, preserving sources and accounting for superseded passages. Never merely refresh a digest to bypass the check.

## Synchronise and measure

Follow `docs/website-research-sync.md`. Use the relevant existing builders, not a full rebuild by default. New opted-in sources use `tools/ingest_canonical_records.py`; reviewed overlays use `tools/publish_resolved_dossiers.py`; targeted accounts use `tools/sync_catalogue_research.py --write <IDs>`. Refresh the actual main Whole tree, its packed payload and standalone model, `tools/build_ancestry_progress.py`, Latest findings and any affected search/navigation/sitemap surfaces. Resolve stale asset references when needed; do not run expensive unrelated repairs by rote.

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
