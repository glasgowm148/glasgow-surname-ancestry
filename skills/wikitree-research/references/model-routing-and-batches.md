# Model routing and agent-operated research batches

## Trigger and owner interface

Use for ordinary requests to research historical people/families, extract records,
assess identities or relationships, or integrate a research batch. The owner
speaks normally; **the agent operates the tools**. Do not hand the owner commands,
packet templates, model-selection chores or instructions to coordinate workers.
Infer routine operational details and ask only for evidence, access or a decision
that cannot be discovered and materially changes the task.

Keep the owner's actual research goal active through retrieval, proposals,
review and authorized integration. A completed extraction or proposal is not
completion of an identity investigation or a saved research update.

## Route the work, not every conversation turn

- Use deterministic parsers, database lookups and existing validators for known
  formats, ID resolution, normalization, duplicate checks and bookkeeping.
- For substantial repetitive literal extraction in OpenCode, use
  `tools/research_batch.py` with its DeepSeek route and at most two workers.
- For a small latency-sensitive packet, direct SOL extraction is supported by
  `--route sol`; SOL was faster on the small controlled comparison. This is not
  proof of lower subscription usage or better general research accuracy.
- Use SOL for substantive identity comparisons, selected parentage, confidence
  changes, contradictory evidence and hold releases. Do not let DeepSeek decide
  these by itself or routinely audit them only after mutation.
- Use Astra only for bounded source-pixel reading, preserve alternatives, and
  have SOL evaluate any resulting genealogical interpretation. A visual response
  is not an identity or relationship finding.
- Do not spend a SOL call supervising successful mechanical steps or repeat
  broad research just to keep workers busy. Do not spawn extra reviewers for
  every trivial field. A small difficult case may be best handled directly by
  SOL rather than decomposed into multiple agents.

The controller explicitly pins its routes and denies all worker tools. In
OpenCode, call it as the installed repository capability; do not replace it with
unrestricted `general` workers and assume they are cheaper. In another harness,
respect native model/provider and delegation rules; do not silently switch
authentication, providers or paid balances to reproduce a model label.

## Operate the existing controller yourself

Read `docs/research-batch-controller.md` for the exact packet/response schema and
CLI. Read `docs/research-integrity.md` when a duplicate, hold or crosswalk check
is relevant. These are instructions for the agent, not setup homework for the owner.

1. Resolve current canonical subjects/claims, revisions, candidate identities,
   contrary evidence, completed tests and active holds. Reuse
   `tools/research_preflight.py` and task-specific source retrieval rather than
   loading whole generated registries into context.
2. Assemble a bounded typed evidence packet from inspected excerpts. Source roles
   are curated inputs: include exact quotations and locators, not labels inferred
   from a model summary. The preflight inventory is not already a typed packet;
   the agent must prepare that transformation carefully.
3. Freeze the packet in a unique private operational run under
   `.cache/research-batches/`. Run `prepare`, then `extract`; choose the model route
   according to the workload above. Use `batch` only for independent prepared runs.
4. Inspect deterministic field checks and integrity preconditions. A blocked or
   invalid result is not research success. Repair packet/schema mistakes from
   evidence, not by weakening a role, inventing a value, changing IDs or deleting
   a hold. A failed/uncertain execution must not be silently replayed; inspect
   its receipt before deliberately preparing another run.
5. Where semantic review is required, run `review` and consume structured
   `field_decisions`, corrections and withheld fields. Rejected or missing fields
   cannot be accepted based on explanatory prose alone. Preserve coparent/spouse,
   baptism/birth and documentary-name/resolved-identity distinctions.
6. Reuse completed matching receipts instead of spending another model request.
   Report what was inspected, accepted, unresolved or blocked. Do not claim that
   a process exit or JSON response proves a historical conclusion.

For a one-off case where packet orchestration would exceed the work itself,
perform the same bounded evidence and review discipline directly with the
appropriate model. The owner still should not be asked to operate the machinery.

## Integration and authority

The controller is **proposal-only**: `apply` is disabled. It does not browse,
create profiles, select parents or publish. Its preconditions check frozen
inputs, not fresh database state, and a `reviewed_proposal` is not write approval.

When the owner authorizes research integration, the owning agent performs it
through the existing revision-checked workbench entry/proposal tools, after
required substantive review. Re-read authoritative identities, revisions and
holds immediately before a write. Preserve existing candidates and evidence.
Do not bypass a failed check via generic table edits, raw SQL or hand-edited
generated JSON. Never treat a reviewer-name string as authenticated approval.
Respect current task restrictions; proposal review alone does not authorize
live WikiTree/FamilySearch edits, merges, messages or deployment.

Follow the existing targeted website synchronization and verification rules
for authorized changes. Do not trigger a full-site rebuild after each person.
Keep spool artifacts private and separate from the authoritative research database.

## Handoff and recovery

Keep packet/run paths, canonical subject IDs, current stage, relevant revisions,
verified outcomes and exact next action in the existing task/handoff. After an
interruption, inspect those receipts and the current workbench before repeating
execution. Report blockers directly rather than asking the owner to run recovery
commands. Operational progress is not genealogical confidence or evidence of a
completed write.
