# Local genealogy tooling — 30 September 2026

Installed for `/Users/m/wikitree-api-scrape`. Four project-scoped stdio MCPs
are configured in `.codex/config.toml`; the existing mac-mcp, browser,
GitHub, authentication, provider routing and Caveman skills remain unchanged.

| Component | Pinned version | Result |
| --- | --- | --- |
| [QMD](https://github.com/tobi/qmd/releases/tag/v2.8.3) | `@tobilu/qmd` 2.8.3 | Local BM25 search over the reviewed corpus and 5,537 open, non-living profile summaries |
| [PDF-MCP](https://github.com/jztan/pdf-mcp/releases/tag/v3.4.0) | 3.4.0 | Keyword search and local Tesseract OCR; one public-domain source, 140 PDF pages |
| [GedcomMCP](https://github.com/airy10/GedcomMCP/tree/8a3767398eafecfbcfc5a30f98ab27c7d3e8d866) | tag `v0.1.0a5`, package reports 0.1.0 | Eight query tools over a minimal historical working copy: 57 people, 18 families |
| [research-sources-mcp](https://github.com/ibarrajo/research-sources-mcp/tree/2786a161c047d8bd6d4063bb7da86bb610760c9e) | 1.0.0 / commit `2786a161…` + recorded compatibility patch | Verified Open Archives search only |
| [Caveman CLI](https://docs.caveman.so/) | `@caveman-ai/cli` 1.3.4; signed binary bundle `bin-v1.1.7` | Explicit local compression, shrinking and exact CCR recovery |
| [uv](https://github.com/astral-sh/uv/releases/tag/0.12.21) | 0.12.21 | Installed inside a private bootstrap venv; global Python remains unchanged |

Runtime, dependency locks, indexes, provenance and test evidence live under:

`/Users/m/Library/Application Support/genealogy-tools/` (mode 0700).

QMD and Caveman use npm lockfiles. PDF/GEDCOM package resolutions are recorded
in `pdf-requirements.lock` and `gedcom-requirements.lock`; GEDCOM uses FastMCP
2.14.7 and PDF uses FastMCP 3.4.7 in separate environments. Research Sources
uses SDK 1.31.0 and a patched lockfile; its production dependency audit is clean.
No global PATH or system package was replaced.

## Access and privacy

`tools/genealogy/mcp_guard.py` removes unlisted tools at discovery and rejects
direct calls independently of Codex's client allowlist. It hides resources and
prompts, strips inherited credentials/provider environment, and caps responses
at approximately 14 KB, five search results, 80 note lines or two PDF pages.
QMD uses lexical queries with reranking disabled. PDF queries force keyword
mode; remote PDF fetching, cloud OCR, remote embeddings, telemetry and update
checks are disabled. No embedding model is downloaded or used.

`tools/genealogy/collections.json` is the reviewed SHA256 allowlist:

- `research/Glasgow-428/findings.md`
- `research/Glasgow-2917/findings.md`
- `research/Glasgow-3172/findings.md`
- Grant's *The Commissariot Record of Lanark: Register of Testaments,
  1595–1800* (1903), with provenance from the project's evidence register.

QMD now covers all 5,585 locally stored Open IDs, representing 5,537 current
profiles after resolving 48 merged/renamed IDs. Anonymous API verification
confirmed Privacy=60 and IsLiving=0 for every selected ID. It includes 4,544
approved public research accounts; the remainder have basic profile fields only.
The three verbatim case notes and one PDF retain their separate hash allowlist.
The 31 testament PDFs and 38 images, private `.cache`, full legacy trees,
living-person details, raw DNA, restricted/licensed captures and the modern
1987 source remain unindexed. Add sources only after reviewing their full
content and permissions, then record their SHA256 and provenance in the manifest.
Local retrieval still sends returned excerpts into the configured model context.
These access restrictions apply to the four new MCPs. The existing shell/UI
tools in this chat retain their OS filesystem access; this installation does
not provide an OS-level privacy sandbox for every Codex capability.

Staged notes retain the exact original text after six metadata lines; subtract
six from staged line numbers to cite original lines. PDF copies are byte-identical:
PDF page numbers match the original. Tool results include original file paths.
Verify the linked record or page before asserting facts; OCR can misread text.

The open-profile expansion uses an anonymous explicit API status check over the
existing local Open IDs. It records the capital `Name`, `Privacy` and `IsLiving`
fields; privacy/living results and renamed IDs are stored in runtime
`open-profile-status.json`. Future captures preserve
`IsLiving`. Local refresh uses that snapshot with a living-person veto and a
fallback to a documented death date or a birth date at least 120 years old.
WikiTree Open means `Privacy=60`; see the [WikiTree Privacy Policy](https://www.wikitree.com/wiki/Help%3APrivacy_Policy)
and the [official API field documentation](https://github.com/wikitree/wikitree-api/blob/main/getPeople.md).

Public dossier generation exposes selected claims, evidence metadata, questions,
conclusions, assessments and actions. It excludes raw narratives, DNA material
and transcriptions. Generated note records use source JSON pointers and retain
the original source mapping; the six-line offset remains available for older
raw-case material.

The GEDCOM working copy retains only names, sex, historical birth/death events,
and relationships wholly within the selected subset. Selection requires explicit
birth <=1850 and death <=1900, excludes restricted/private markers and omits
notes, sources, media, submitters and addresses. The copy is mode 0444. Only its
exact path may be loaded; save/add/delete/update tools are unavailable. Tree
relationships remain unverified leads, not primary evidence. Original tree
provenance is kept privately in `historical-tree-provenance.json`.

Open Archives is the sole exposed external provider. Its `birth_year` and
`death_year` fields are lower and upper **record event years**, not lifespan
filters. The patched adapter applies the supported date-query syntax and excludes
undated/out-of-range records; upper year must be <=1900. The guard permits one
call per second, below the provider's four calls/second limit. Send public
historical subjects only, never private family information.

## Passive refresh and usage

macOS LaunchAgent:

`~/Library/LaunchAgents/com.wikitree.genealogy-index-refresh.plist`

It runs daily at 03:00 local time, or on the next computer wake if asleep.
It does not wake the computer or run at login/every 15 minutes. Refresh uses no
model, paid API or network calls: it regenerates eligible public summaries, stages
hash-approved files, runs `qmd update`, and warms the PDF keyword cache. Successful
`sync_catalogue_research.py --write` batches and completed
`publish_research_release.py` runs invoke refresh automatically. A failed refresh
is reported as a failure; the daily fallback and manual command can retry it.
Changed, missing or symlinked hash-approved notes/PDFs are withheld and stale
copies removed until review approves a new hash. Public summaries update
automatically through the eligibility/content projection; new profiles need
verified non-living/open metadata. Revoked eligibility removes staged summaries.
The daily refresh does not recheck WikiTree: run the explicit status command when
refreshing remote privacy/living status. Full-text
PDF warm-up does not force OCR over pages that already have a text layer; use
`pdf_read_pages(..., ocr=true)` for approved scanned pages that lack text.
State is in `genealogy-refresh-state.json` and `pdf-warm-state.json`; logs are
`refresh.log` and `refresh-errors.log` under the runtime.

Manual commands from the project:

```sh
./tools/genealogy/qmd search 'Currituck William' -n 5 --json
./tools/genealogy/qmd get 'qmd://historical-notes/Glasgow-428-findings.md:7:40'
python3 tools/genealogy/check_open_status.py
python3 tools/genealogy/refresh.py --refresh
./tools/genealogy/caveman compress < public-safe-input.txt
./tools/genealogy/caveman shrink < public-safe-command-output.txt
./tools/genealogy/caveman retrieve CCR_HANDLE
```

Caveman is explicit CLI operation. No automatic Codex inference proxy was enabled:
changing the provider route would affect existing ChatGPT authentication. Recover
the original CCR source before citing it; compressed evidence is never authoritative.
Existing Caveman skills continue to govern concise responses.

## Verification

- All four guarded stdio servers initialize and list exactly their intended tools.
- QMD finds William's Currituck case and retrieves a bounded original-mapped excerpt.
- PDF corpus search returns original-mapped pages (tested matches include PDF pages
  11 and 27). Local Tesseract reads an image-only verification copy of original
  PDF page 9, and keyword search finds the resulting OCR on derived page 1.
  The temporary PDF was removed; OCR's publication-year misreading demonstrates
  why the original page remains authoritative.
- GEDCOM loads the historical working copy and returns a family relationship.
- Open Archives returns a public 1721 record with source URL and event date.
- Unlisted write calls, private PDF paths, unrestricted GEDCOM loads, semantic
  QMD calls and modern external year ranges are rejected.
- All eight valid original tree/export hashes match the initial baseline.
  The original Gramps database contains 2,079 people; legacy RootsMagic snapshots
  contain 169–170. Two apparent GEDCOMs failed header validation.
- Expanded QMD finds Glasgow-1150 with bounded excerpts and original JSON
  pointers. Eligibility, living/restricted/DNA exclusion and stale-summary removal
  pass focused fixture checks. The approved batch hooks and daily schedule are
  verified; a local refresh finishes with 5,537 profiles, 140 PDF pages and no
  withheld allowlist files or unfinished work. The separate changed-hash test
  confirms withholding and stale-copy removal for verbatim notes/PDFs.
- Caveman reduced a 59,201-byte neutral fixture to 15,161 bytes (74.1% estimated
  token reduction); `retrieve` restored the exact SHA256/bytes. Its aggregate
  evaluator exits nonzero despite reporting 11/12 probes retained, one recoverable,
  none lost; recovery/compression tests passed independently.
- Research Sources cache initialization, native SQLite binding, build and tests
  passed; focused historical API tests passed. Compatibility changes are saved
  in `runtime backups/research-sources/runtime.patch`.
- The research skill shrank from 96,952 bytes to about 5.6 KB. Its introduction
  and all 23 H2/H3 sections are preserved verbatim in the core/references;
  frontmatter validation passes. Four task-specific references route identity,
  profiles, website/catalogue and transcription work.

Re-run stdio verification:

```sh
'/Users/m/Library/Application Support/genealogy-tools/pdf-venv/bin/python' \
  /Users/m/wikitree-api-scrape/tools/genealogy/verify.py
```

Detailed evidence: `verification.json`, `ocr-verification.json`,
`caveman-audit.md`, `legacy-adapter-audit.md`, and
`research-sources-runtime-audit.md` in the runtime. The test source artifacts
are local; no private tree contents were sent to an external provider.

## Blockers and restart

Direct Gramps and RootsMagic MCPs were not installed. The only direct-local
Gramps candidate, [gramps-ez-mcp](https://github.com/dsblank/gramps-ez-mcp),
is a prototype requiring the Gramps Python runtime and tree-name lookup; compatibility
with this 5.2-era tree and a safe copied-tree path is unverified. Other maintained
Gramps servers require Gramps Web, which was not deployed. No reliable maintained
direct RootsMagic genealogy adapter was found for the existing version-8 `.rmtree`
snapshots. They remain outside agent-visible collections; no custom replacement
system was built.

Research Sources' WikiTree and Chronicling America tools remain unexposed because
live verification returned HTML/403 instead of usable API JSON. Find A Grave is
advertised by its README but is absent from the actual tool registration. Only
the repaired and verified Open Archives tool is configured.

Quit and reopen Codex, then start a new chat for this project to load the four MCPs
and revised skill. Existing user-level servers remain configured. This current
chat has verified servers through a local MCP client but has **not** hot-loaded
their tools into its callable tool set. No Gramps/RootsMagic application restart
or database migration is needed. Existing website/research edits were preserved;
this tooling task did not deploy or rebuild the public website.

## Backups and exact rollback

Original files are under runtime `backups/`:

- `AGENTS.md.before`
- `skill-before/SKILL.md` (including pre-existing uncommitted changes)
- `.gitignore.before` (the ignore file was not changed)

Research Sources source/package backups and its patch are under
`runtime backups/research-sources/`. Global Codex configuration and auth were
not modified and their fingerprints match the verification baseline.

Preview rollback, then apply it:

```sh
python3 /Users/m/wikitree-api-scrape/tools/genealogy/rollback.py
python3 /Users/m/wikitree-api-scrape/tools/genealogy/rollback.py --apply
```

Expansion backups, including the already-edited website sync/capture scripts,
are under runtime `backups/open-profile-expansion/`. To undo this expansion
while retaining the installed tools:

```sh
python3 /Users/m/wikitree-api-scrape/tools/genealogy/rollback_expansion.py --apply
```

Expansion rollback restores the preceding three-case corpus and 15-minute
schedule, saving current edits before restoration. Full rollback also restores
the website sync/capture scripts and removes the installed tools.

The script stops/removes the LaunchAgent, restores AGENTS.md and the original
research skill, and moves the project configuration, new tooling, references,
report and installed runtime into a timestamped
`~/Library/Application Support/genealogy-tools.rollback-YYYYMMDD-HHMMSS/`.
Current versions are retained before originals are restored, so later local
edits are recoverable. No original tree, existing Caveman skill, user-level MCP,
authentication or provider setting is touched. Restart Codex after rollback.
Dry-run and applied rollback were verified in an isolated fixture; the real
installation remains active.

To stop refresh alone without uninstalling:

```sh
launchctl bootout gui/$(id -u)/com.wikitree.genealogy-index-refresh
```

To resume it:

```sh
launchctl bootstrap gui/$(id -u) \
  /Users/m/Library/LaunchAgents/com.wikitree.genealogy-index-refresh.plist
```
