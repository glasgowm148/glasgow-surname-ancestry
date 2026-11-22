# Proposal-only research batch controller

`tools/research_batch.py` runs bounded, tool-free extraction and explicit SOL field
review. It **cannot apply database changes**. `apply` always fails before reading
or creating a run. It does not browse, infer identities, create profiles, choose
parents, assign confidence percentages or publish a website.

## Commands

From the repository, prepare a small, curated, approved historical evidence packet:

```sh
.venv/bin/python tools/research_batch.py prepare PACKET.json \
  --output .cache/research-batches/CASE-001 --route deepseek
.venv/bin/python tools/research_batch.py extract .cache/research-batches/CASE-001
.venv/bin/python tools/research_batch.py review .cache/research-batches/CASE-001
.venv/bin/python tools/research_batch.py status .cache/research-batches/CASE-001
```

- `prepare` and `status` make no model requests.
- `extract` makes one DeepSeek Flash request, or one direct SOL request when
  prepared with `--route sol`.
- `review` makes one SOL request. It is a separate, explicit expense.
- An unchanged completed stage reuses its hash-checked receipt. Failed stages,
  interrupted stages and changed inputs do not silently retry. Inspect the result
  and prepare a new run deliberately if needed.
- `prepare` creates a new run directory exclusively; do not pre-create or reuse
  it. This prevents concurrent preparation from overwriting another run.
- A stage timeout defaults to 180 seconds, configurable from 1 to 300 seconds.
  Its process group is terminated on timeout/interruption.
- No model invocation is made for failed packet integrity preconditions.

Process prepared runs with one or two workers:

```sh
.venv/bin/python tools/research_batch.py batch \
  .cache/research-batches/CASE-001 .cache/research-batches/CASE-002 \
  --workers 2 --review
```

Omit `--review` to produce extraction/check artifacts only, never a reviewed
proposal. Duplicate run paths are refused. A per-run lock prevents simultaneous
controllers spending requests on the same stage. A blocked extraction returns
status `blocked_fields`, `blocked_protocol` or `blocked_preconditions`; the CLI
returns nonzero for blocked results. Successful execution is not research completion.

## Packet contract

The packet is JSON with unique keys, format `research-evidence-packet`, version 1,
and a maximum serialized input size of 64,000 bytes. It contains subjects,
revisioned records, curated source-role quotations and explicitly requested fields.

Example: the source names two parents, but does not establish marriage:

```json
{
  "format": "research-evidence-packet",
  "format_version": 1,
  "task_id": "example-coparent",
  "subjects": [{"id": "parent-a"}],
  "records": [{
    "id": "record-example",
    "revision": 1,
    "locator": "fictional register, page 4",
    "text": "Child Ellen, parents Martin Vale and Jane Reed. No marriage stated.",
    "roles": [{
      "id": "coparent-role",
      "kind": "coparent",
      "subject_id": "parent-a",
      "literal": "Jane Reed"
    }]
  }],
  "requested_fields": [
    {"id": "other-parent", "subject_id": "parent-a", "field": "recorded_coparent"},
    {"id": "spouse", "subject_id": "parent-a", "field": "recorded_spouse"}
  ]
}
```

Documentary roles must be curated from the evidence; the extractor may not invent
or relabel them. The controller checks that quotes exist and roles match field
types, but cannot prove the curator's historical interpretation. A false `spouse`
label supplied in the packet still needs semantic review. Do not automatically
convert a preflight dossier's prose into trusted role declarations. The existing
`research_preflight.py` output is an evidence inventory, not this typed format.

Supported fields and roles are defined centrally in
`tools/research_batch_contract.py::FIELD_ROLES`. They include literal names,
father/mother/coparent/spouse roles, explicit birth surname and event-specific
dates/places. None creates a person or family edge. Additional packet context,
including proposed operations, is data only, never executed or exported as
workbench apply operations.

Exact date normalization accepts a full ISO or day/month-name/year date.
Each extracted literal must preserve its complete curated role quotation;
shortening `12 March` to `2 March` or `Joanne` to `anne` is rejected. Date-role
quotations should delimit the entire date datum, including qualifiers, rather
than an arbitrary paragraph. Qualified or alternative dates are withheld rather than made exact. A baptism role cannot
support a birth field; coparent cannot support spouse. Literal year-only birth
values do not become invented full dates. Name/place normalization cannot extract
partial words, such as `Anne` from `Joanne`.

## Extraction and field review

Each requested field needs exactly one extracted or missing-field decision.
Extracted items contain exactly:

```json
{
  "field_id": "other-parent",
  "subject_id": "parent-a",
  "field": "recorded_coparent",
  "record_id": "record-example",
  "record_revision": 1,
  "role_id": "coparent-role",
  "locator": "fictional register, page 4",
  "literal": "Jane Reed",
  "normalized": "Jane Reed"
}
```

Missing values use `{"field_id": "spouse", "reason": "Only coparenthood is documented"}`.

SOL must return one `field_decisions` entry per requested field:

```json
{
  "field_id": "spouse",
  "decision": "unresolved",
  "reason": "There is no spouse role or marriage evidence in this packet.",
  "corrected_field": null
}
```

The decisions are `accept`, `correct`, `reject`, or `unresolved`. Corrections
require a complete replacement field using the same field ID/subject/type and
are revalidated against source roles. Prose corrections cannot silently change
data. Invalid or absent fields cannot be accepted. No requested field may be
omitted or decided twice.

`proposal.json` retains suggested and withheld fields, input/output hashes and
`application_enabled: false`. `reviewed_proposal` means a source-scoped review
recommendation, not permission to apply a database mutation. An overall unresolved
or insufficient-packet review produces `withheld_proposal`.

## Existing integrity gates

Optional `preconditions` can use `creation_subjects`, `hold_release`, or
`familysearch_matches`, each with a unique ID. They reuse the existing functions
documented in [research-integrity.md](research-integrity.md):

- `creation_subjects`: `new_people` and optional explicit `canonical_aliases`.
- `hold_release`: `previous`, `proposed`, and optional `status_field`. The actual
  held status must match; evidence revisions come from this frozen packet.
- `familysearch_matches`: `people` and optional explicit `canonical_aliases`.

These are **checks on supplied frozen inputs**, not fresh identity decisions or
live database staleness checks. A future writer must re-resolve authoritative IDs,
revisions and holds inside its write transaction. SOL cannot override a failed
precondition through its review response.

## Isolation and receipts

Model execution uses an isolated temporary directory, explicit pinned models,
tool-denying ephemeral agents and normal OpenCode authentication. External skills
and plugins are disabled for those invocations; the current mac-mcp server is
disabled in the per-process configuration. No global connection change is made.
The exact extraction prompt is identical for the DeepSeek and direct SOL routes.

Run artifacts are private operational spools, not another research authority.
Inside the checkout, output is restricted to `.cache`, `artifacts`, `tmp` or
`test-results`; symlink paths and `..` escapes into source/research directories
are refused. Prefer `.cache/research-batches` for real unpublished material.
Do not put restricted/living-person evidence into model packets merely because
the output directory is private.

Each stage records the request/response hashes, selected model, session IDs,
wall time, raw events and provider-reported token fields. Those fields do not
establish subscription allowance percentages. A completed execution receipt may
still have a blocked field/protocol result; inspect `field-checks.json` and the
proposal status as well as the process exit code.

## Offline checks

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest tests.test_research_batch
```

Tests use fictional packets, temporary directories and mocked model runners.
They cover source-role confusion, date qualifiers, stale references, missing
decisions, structured corrections, disabled application, output isolation,
precondition failures, process-result failures, tampering, replay and locks.
