# Project Instructions

- Complete authorized work end to end. Infer routine details from context and ask only when missing information would materially change the result or required authorization for an irreversible or out-of-scope action is absent.
- Read only the files and documentation the task needs. Use referenced project docs when their subject applies instead of loading them before every change.
- Verify with the smallest meaningful checks for the change. Fix failures caused by the work and rerun affected checks; expand testing only when the change, a failure, or unresolved risk justifies it.
- Keep prompts, updates, handoffs and final responses concise while preserving decisions, evidence and material limitations.
- When the user explicitly corrects a repeatable workflow or quality rule governed by a project-owned skill, update the applicable `SKILL.md` during the same task so the correction persists.
- Keep durable corrections narrowly scoped. Do not automatically modify system, third-party, unrelated, or non-writable skills, and do not encode one-off preferences as universal rules.

## Website-first research

- The website is the project's main account of current conclusions, evidence, uncertainty, family studies and open questions. Repo notes, agent handoffs and external research must feed it; original records remain the evidence for historical claims.
- Every substantive research task, including work under `research/`, `surname-research/`, free-space drafts and profile investigations, must synchronize public-safe findings into the relevant `www/` pages and data after each coherent batch and before completion.
- Update both maintained source inputs and their public presentation. Include source provenance, explicit confidence/status, current conclusions and next questions; reflect resolved or superseded questions in all affected summaries. A file in the repository or an index link alone is not visible research integration.
- For research tasks, follow `docs/website-research-sync.md` and the project research skill. Local website synchronization is authorized: prefer targeted updates and use a full catalogue build only when required, after preserving hand-edited content in durable sources. If the user defers a build, report the site as pending. Subagent handoffs must identify affected site surfaces and remaining synchronization; the orchestrator completes the integration.
- Do not publish private material, sensitive living-person information, credentials or raw captures. Publish a safe, sourced account and mark pending or uncertain conclusions explicitly.
- Distinguish local synchronization from live publication. No automatic deployment is currently configured: do not claim production is current until an authorized deployment has completed and its affected pages have been checked. A deployment blocker must be reported explicitly.

## UI debugging and browser checks

- Browser reproduction and verification are authorized for requested UI fixes. Open the affected local page, inspect errors, interact with controls and check relevant desktop/mobile rendering without asking again.
- Reproduce reported visual failures and visually verify affected flows after the fix. Keep checks scoped; report blockers or unverified behavior. This authorization does not cover publishing or destructive actions.

## Sub-agent model routing

Use cost-aware delegation for bounded, independent work that can proceed in parallel; it is authorized without further approval. Keep trivial or tightly coupled work local, assign non-overlapping ownership, share only needed context and request concise handoffs. Choose the cheapest reliable model:

- `gpt-5.6-luna` for menial, deterministic, low-risk work: file discovery, formatting, simple data extraction, mechanical edits, and straightforward tests.
- `gpt-5.6-terra` for ordinary implementation, investigation, and multi-step work that is not especially difficult or risky.
- `gpt-6-astra` with `reasoning_effort: "low"` for hard, ambiguous, security-sensitive, architectural, cross-cutting, or reasoning-heavy work. Prefer Astra low over Sol high for these tasks.

When uncertain, use Terra; choose Astra low when a mistake would be costly or substantial judgment is required. The orchestrator owns decisions and integration. Delegation does not authorize work or verification outside the requested scope.
