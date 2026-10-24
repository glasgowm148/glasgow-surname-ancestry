---
name: findmypast-catalogue-audit
description: Audit Findmypast surname records against a birth cutoff, reconcile existing people and held identities, and synchronize this project's research catalogue and local website. Use for systematic logged-in Findmypast coverage or resuming that audit, rather than live WikiTree editing.
---

# Findmypast catalogue audit

Resolve the repository from this skill's real path (the directory containing `skills/`) and run project commands there. If that dependency is unavailable, report it rather than creating lookalike catalogue files elsewhere.

Use the active request's surname, birth cutoff and coverage scope. This project's current audit concerns people **born Glasgow before 1800**, including their later-life records. Read the existing capture/coverage ledger before searching; progress belongs in that ledger, not in this skill. Before transcript/detail navigation, preflight every known result ID against all approved saved receipts, current canonical records/public record index and relevant current person findings. Use `tools/fmp_record_preflight.py` with explicit IDs or a rows file; inspect its current help/schema. Prioritize cached but unintegrated records before opening new browser pages. Inspect current keyed review dispositions and their source pointers; an absent preflight HOLD flag is not proof of no prior review. Treat superseded disposition snapshots as history. Preserve HOLD dispositions and skip refetching accessible fields unless the preflight records a specific unanswered field or source question. A search row or citation is not a full receipt, but do not fetch a full receipt when existing accessible fields already answer the question. Screening or skipping an ID still advances coverage; call a record first-seen, newly integrated or duplicate as appropriate, not “new” by default. Stop repeating no-hit queries unless a new discriminator changes the search.

Use the [project research skill](../wikitree-research/SKILL.md) for identity, evidence, privacy and publication conventions. For capture, reconciliation, builders and verification, read [the runbook](references/catalogue-workflow.md). Load only the project references needed for the current operation.

## Decisions that must survive reuse

- Check exact provider URLs in the source library and secondary/reference citations even when a stronger primary source has replaced the provider URL. Reuse existing source and record IDs, and check retired person aliases before treating the entry as missing. Source-library presence alone does not resolve identity.
- For an existing alias repair, inspect the targeted reconciler's writes before launching builders. If it already updates the source reader, record/source indexes and collection membership, and no source, category or route is added, verify those affected fields instead of repeating the full source-collection rebuild. Refresh other views only when their inputs changed.
- Birth-surname eligibility is separate from a later-life Glasgow surname. Married-in women and age-derived birth years need explicit qualification. A search filter does not establish either fact.
- Assess scope for each recorded role. A child born after the cutoff may have a pre-cutoff Glasgow parent whose evidence belongs in the catalogue. An out-of-scope indexed subject does not exclude the whole record; screen named relatives before skipping it.
- Keep birth, baptism, death and burial as distinct assertions. Inspect the actual current vital fields before describing an existing date as exact or bounded. An indexed birth year attached to a baptism does not prove infant baptism or exclude an earlier adult. Uncertain estimates and missing corroboration are not concrete conflicts.
- Retain compatible existing candidates with qualified roles. A comparison link does not assign the record's event or parents to that profile. Suggest a new person only when concrete recorded conflicts exclude the compatible alternatives; no match in a bounded search is insufficient.
- Consolidate compatible companion entries into documentary groups; they are not independent corroboration. Preserve discrepancies rather than inventing two people or silently choosing a date.
- Reuse person, draft, provider-record and source IDs. Follow verified saved-receipt pointers even outside the current capture file; keep capture counts separate from query coverage. An exact provider-record match can reveal a stale duplicate creation case: reconcile it to the existing profile, retain its redirect/history and withdraw its creation readiness in durable inputs.
- Record source level accurately: inspected transcript, inspected derivative abstract/image, or original record. An abstract image is not the original census or register. Never publish licensed raw images, credentials or private captures.
- Refine approved vital fields in the maintained shared model, complete proposed biography and real amendment queue. Preserve existing relationship assessments unless the combined identity/kinship proposition has actually been reassessed.
- Keep coverage **INCOMPLETE** while pages, birth windows, categories, variants, locked results or material identity/surname questions remain. Separate inspected records, eligible people, matched identities, held records and new-person proposals.

## Work and resource ownership

When using Mac MCP `browser_do` to navigate an existing tab, set `new_tab=false` explicitly: supplying `tab_handle` alone can still open another tab. Check the returned handle/native tab ID against the owned tab, and reconcile the inventory immediately after a mismatch.

One parent owns browser interaction and PDF/browser rendering, sequentially. Reuse one existing browser/profile, one automation window/session and one temporary working tab. Set a session name once; changing it can create another window. Save each receipt before navigation. Follow the project research skill's RAM/lifecycle rule and AGENTS.md checkpoints; never clear the user's tabs or shared processes.

Delegate bounded file/search/API comparisons to native workers when useful. Tell every worker that browser launches and rendering are parent-owned. Give non-overlapping file ownership, request short source-backed handoffs, reuse workers and keep shared catalogue JSON, builds, staging and commits with the parent. Do not create extra browser sessions to satisfy a request for maximum agents. Keep the existing RAM and browser lifecycle rules: reuse owned resources, inventory at checkpoints and release only task-owned resources.

## Batch boundary

Combine related result pages into one reviewed publication batch when their identity decisions can be completed together. Finish a coherent batch of substantive findings before synchronizing; coverage-ledger updates and already-held/skipped records do not require a site build. Validate the selected batch's actual schemas and complete proposed texts before shared writes; make resumable integration replace its own marked blocks rather than append duplicates. For changed records, use the dependency order: ingest reviewed records, synchronize affected person/source accounts, update latest findings, update affected studies, then refresh backlinks and only the affected derived views. Verify changed surfaces and required publication/link checks before continuing. Local synchronization does not establish live deployment or authorize live WikiTree edits.

Report the next exact coverage step and unresolved dispositions. Leave the full goal active until its complete scope has been verified.
