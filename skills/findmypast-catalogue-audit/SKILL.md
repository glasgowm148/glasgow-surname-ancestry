---
name: findmypast-catalogue-audit
description: Audit Findmypast surname records against a birth cutoff, reconcile existing people and held identities, and synchronize this project's research catalogue and local website. Use for systematic logged-in Findmypast coverage or resuming that audit, rather than live WikiTree editing.
---

# Findmypast catalogue audit

Resolve the repository from this skill's real path (the directory containing `skills/`) and run project commands there. If that dependency is unavailable, report it rather than creating lookalike catalogue files elsewhere.

Use the active request's surname, birth cutoff and coverage scope. This project's current audit concerns people **born Glasgow before 1800**, including their later-life records. Read the existing capture/coverage ledger before searching; progress belongs in that ledger, not in this skill.

Use the [project research skill](../wikitree-research/SKILL.md) for identity, evidence, privacy and publication conventions. For capture, reconciliation, builders and verification, read [the runbook](references/catalogue-workflow.md). Load only the project references needed for the current operation.

## Decisions that must survive reuse

- Birth-surname eligibility is separate from a later-life Glasgow surname. Married-in women and age-derived birth years need explicit qualification. A search filter does not establish either fact.
- Keep birth, baptism, death and burial as distinct assertions. An indexed birth year attached to a baptism does not prove infant baptism or exclude an earlier adult. Uncertain estimates and missing corroboration are not concrete conflicts.
- Retain compatible existing candidates with qualified roles. A comparison link does not assign the record's event or parents to that profile. Suggest a new person only when concrete recorded conflicts exclude the compatible alternatives; no match in a bounded search is insufficient.
- Consolidate compatible companion entries into documentary groups; they are not independent corroboration. Preserve discrepancies rather than inventing two people or silently choosing a date.
- Reuse person, draft, provider-record and source IDs. An exact provider-record match can reveal a stale duplicate creation case: reconcile it to the existing profile, retain its redirect/history and withdraw its creation readiness in durable inputs.
- Record source level accurately: inspected transcript, inspected derivative abstract/image, or original record. An abstract image is not the original census or register. Never publish licensed raw images, credentials or private captures.
- Refine approved vital fields in the maintained shared model, complete proposed biography and real amendment queue. Preserve existing relationship assessments unless the combined identity/kinship proposition has actually been reassessed.
- Keep coverage **INCOMPLETE** while pages, birth windows, categories, variants, locked results or material identity/surname questions remain. Separate inspected records, eligible people, matched identities, held records and new-person proposals.

## Work and resource ownership

One parent owns browser interaction and PDF/browser rendering, sequentially. Reuse one existing browser/profile, one automation window/session and one temporary working tab. Set a session name once; changing it can create another window. Save each receipt before navigation. Follow the project research skill's RAM/lifecycle rule and AGENTS.md checkpoints; never clear the user's tabs or shared processes.

Delegate bounded file/search/API comparisons to native workers when useful. Tell every worker that browser launches and rendering are parent-owned. Give non-overlapping file ownership, request short source-backed handoffs, reuse workers and keep shared catalogue JSON, builds, staging and commits with the parent. Do not create extra browser sessions to satisfy a request for maximum agents.

## Batch boundary

Finish a coherent captured batch before opening more coverage or implementing queued follow-ups. Synchronize current accounts, studies, complete drafts, latest findings and affected derived views. Verify actual rendered records, search/filter agreement, source routes and appropriate publication/link checks, then commit only this batch. Local synchronization does not establish live deployment or authorize live WikiTree edits.

Report the next exact coverage step and unresolved dispositions. Leave the full goal active until its complete scope has been verified.
