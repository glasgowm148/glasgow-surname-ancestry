# Glasgow Surname Ancestry

Evidence-led genealogy research, WikiTree profile maintenance, and interactive
ancestry tools for the Glasgow surname and its variants.

This is the Glasgow research project, not the general-purpose toolkit. It consumes
the platform-neutral `genealogy-research-workbench` package for shared genealogy
models, research cases, exports and adapter contracts. WikiTree and One-Tree are
project adapters; GEDCOM, FamilySearch, archives, spreadsheets/OCR and DNA are
also supported adapter categories. Glasgow-specific branding, surname variants,
privacy boundaries and paths live in [`genealogy.toml`](genealogy.toml).
The established family exporter now delegates WikiTree HTTP retry, WAF and
response validation, family-capture normalisation and neutral case persistence
to toolkit adapter services while retaining this project's application ID,
headers, case naming and command interface.

For development beside the toolkit checkout, install the editable local link:

```bash
python -m pip install -r requirements/base.txt -r requirements/toolkit-local.txt
```

Released deployments use the versioned `genealogy-research-workbench` dependency
declared in [`pyproject.toml`](pyproject.toml). The existing scripts and Makefile
commands below remain unchanged; reading the overlay does not rebuild the catalogue:

```bash
python tools/genealogy_project.py
```

An explicit compatibility bridge can normalise a supplied legacy One-Tree JSON
file and write a privacy-filtered JSON projection without touching `www/` or
starting a rebuild:

```bash
.venv/bin/python tools/genealogy_bridge.py --input /path/to/legacy.json \
  --export-output /path/to/filtered.json
```

The established WikiTree family exporter also has an opt-in neutral handoff,
so a normal capture can be saved as a toolkit case without changing its legacy
Markdown or JSON outputs:

```bash
.venv/bin/python src/wikitree_family_export.py Example-1 \
  --toolkit-case-directory /path/to/cases
```

Iterative research mode has a separate opt-in dual write. It first maintains
the established `research_state.json`, `research_plan.json`,
`evidence_index.json`, `research_brief.md`, and `findings.md`, then writes and
verifies a private neutral toolkit bundle at an explicit, different directory:

```bash
.venv/bin/python src/wikitree_family_export.py Example-1 \
  --research-dir /path/to/legacy-case \
  --toolkit-research-bundle /path/to/private-toolkit-bundle
```

The neutral bundle records private typed facts, questions and findings plus
checksummed legacy-artifact and work-queue provenance. It does not copy raw
captures, biographies, FamilySearch page bodies, or the free-form Markdown
bodies, and it cannot be written over the legacy research directory.

Existing research folders can be migrated later without rerunning a scrape or
sync command. This standalone command accepts exactly one source and one
different destination; it is offline and does not rebuild the catalogue:

```bash
.venv/bin/python tools/migrate_research_bundle.py \
  --research-dir /path/to/legacy-case \
  --bundle-dir /path/to/private-toolkit-bundle
```

The repository is organized into source code, tools, tests, durable data,
generated artifacts, the interactive map, and two established research trees.
See [`docs/repository-structure.md`](docs/repository-structure.md) for the layout
and [`docs/research-workflow.md`](docs/research-workflow.md) for the full research rules.
The implemented toolkit boundary and remaining compatibility migration are recorded
in [`docs/toolkit-migration.md`](docs/toolkit-migration.md).

For surname-wide work, start with
[`surname-research/INDEX.md`](surname-research/INDEX.md). It joins individual
cases to early profiles, location clusters, and explicit relationship hypotheses.

WikiTree research is the default path. It uses the API only and does not start
FamilySearch or Playwright.

Install the lightweight dependencies:

```bash
python -m pip install -r requirements/base.txt
```

Create a case containing the subject, children, and grandchildren:

```bash
python src/wikitree_family_export.py Glasgow-3905 \
  --research-dir research/Glasgow-3905 \
  --descendant-depth 2
```

Depth 2 fetches the root and each child. The child captures include their
children, so grandchildren are indexed without expanding into great-grandchildren.

The original one-shot WikiTree export remains available:

```bash
python src/wikitree_family_export.py Glasgow-1538
```

For iterative AI-assisted research, create a durable case. The first command
below imports an existing export without making network requests:

```bash
python src/wikitree_family_export.py Glasgow-1538 \
  --research-dir research/Glasgow-1538 \
  --import-ai-export artifacts/profile-exports/Glasgow-1538_ai_export.md
```

The case contains:

- `research_brief.md`: compact dossier to give an AI for analysis.
- `findings.md`: durable source-to-finding research log; never overwritten.
- `<WikiTree-ID>.md`: sourced facts and corrections absent from the current profile,
  queued for manual WikiTree review; user edits are never overwritten.
- `research_plan.json`: AI-editable questions, findings, web searches and scrape targets.
- `evidence_index.json`: deduplicated profile and evidence index.
- `captures/`: immutable raw responses retained for provenance.
- `research_state.json`: internal run history; do not edit it manually.

## Iteration

1. Ask the AI to read `research_brief.md` and `research_plan.json`.
2. The exporter scaffolds `<WikiTree-ID>.md` as a manual-review delta file. The AI
   records evidence assessments in `findings.md` and `research_plan.json`, then adds
   only supported facts or corrections missing from the current WikiTree page.
3. When more tree evidence is needed, the AI adds a pending target:

```json
{
  "kind": "wikitree",
  "id": "Glasgow-540",
  "reason": "Test the former-parent hypothesis against this family.",
  "status": "pending"
}
```

FamilySearch is optional and deliberately separate from the main WikiTree loop.
Install it only when needed:

```bash
python -m pip install -r requirements/browser.txt
playwright install chromium
```

To queue a FamilySearch source page, associate its PID with its WikiTree profile:

```json
{
  "kind": "familysearch",
  "id": "9QX2-3ZW",
  "profile_id": "Glasgow-1537",
  "reason": "Inspect records that may name Ralph's parents.",
  "status": "pending"
}
```

4. Consume pending WikiTree targets and rebuild the brief:

```bash
python src/wikitree_family_export.py Glasgow-1538 \
  --research-dir research/Glasgow-1538
```

Use the existing logged-in Chrome session when FamilySearch targets are pending:

```bash
python src/wikitree_family_export.py Glasgow-1538 \
  --research-dir research/Glasgow-1538 \
  --familysearch-cdp
```

If nothing is pending, rerunning only rebuilds the index and brief. Use
`--research-refresh` when a fresh root capture is intentionally required.
Research cases under `research/` also rebuild the surname-wide navigation indexes.

Regenerate only those indexes with:

```bash
.venv/bin/python src/surname_research_index.py
```

Run the offline tests with:

```bash
python -m unittest discover -s tests -v
```

For the standard local quality gate, install the development tool once and run:

```bash
python -m pip install -r requirements/base.txt -r requirements/dev.txt -c requirements/constraints.txt
make check
```

`make check` runs safe Ruff correctness checks, validates the public CSV/JSON
contracts, and runs the offline test suite. `make build` is deliberately
separate because it refreshes the One-Tree map and thousands of generated
catalogue pages:

```bash
make build
```

Keep source code, research notes, generated output, and data refreshes in
separate commits. Never reset or stash another contributor's in-progress
working-tree changes just to make a generated build clean.

Rebuild and test the interactive map with:

```bash
.venv/bin/python tools/sync_wikitree_profile_evidence.py
.venv/bin/python tools/sync_onetree_ireland_uk_to_1900.py
.venv/bin/python tools/build_family_map.py
.venv/bin/python tests/test_family_map.py
```

For ordinary WikiTree tree edits, use the incremental change scanner instead
of waiting for another full One-Tree export:

```bash
.venv/bin/python tools/sync_recent_wikitree_changes.py --apply --refresh-evidence --rebuild
```

The first pass compares the current WikiTree `Touched` value for every locally
known profile. Only changed profiles and newly connected immediate relatives
are saved to `data/wikitree/live-profile-overrides.json`; the underlying
One-Tree exports remain untouched. Parent/child edges, dossiers, networks and
the map are then rebuilt from the merged view.

To discover new or disconnected profiles, save the public
`Special:NetworkFeed` result as HTML and include it:

```bash
.venv/bin/python tools/sync_recent_wikitree_changes.py \
  --feed-html ~/Downloads/wikitree-network-feed.html \
  --apply --refresh-evidence --rebuild
```

The feed is used only to discover profile IDs; current genealogy is always
retrieved from WikiTree's read-only API. Run without `--apply` for a dry-run
change report. IDs which have since been deleted, merged or made private are
reported as warnings and do not prevent the remaining public tree from being
rebuilt.

`sync_wikitree_profile_evidence.py` defaults to the Irish pre-1700 cohort and
captures full public WikiTree biographies, citations, source URLs, categories,
profile locations, and immediate relationships. It writes durable case captures
and `data/wikitree/profile-evidence.json`; the catalogue publishes the historical
subset as `www/data/wikitree-profile-evidence.json`. WikiTree profile prose is a
research lead, not independent evidence.

Use `--scope all-historical --no-research-cases` for the resumable full-catalogue
refresh. Completed profiles are cached and skipped unless `--refresh` is supplied.

WikiTree's AWS WAF challenges generic script user agents with an empty HTTP 202
response. The shared API client uses same-site browser request headers and the
`GlasgowSurnameResearch` application ID, and reports a WAF challenge explicitly
if WikiTree blocks the request before `api.php` processes it.

The One-Tree sync includes every date in the merged exports; the legacy script name is retained for compatibility.
The map build also regenerates the static catalogue under `www/people/`, the
machine-readable person exports under `www/data/`, and `robots.txt`,
`sitemap.xml`, `llms.txt`, and the standalone One Tree viewer under
`www/onetree/glasgow-one-tree-polished/` so profile redirects cannot leave the
viewer pointing at missing catalogue pages.
The public catalogue omits likely-living people (no recorded death and a birth
within the last 120 years), records export provenance, derives named children
from reversed parent links, and produces a citation backlog wherever the map
dataset has only profile or local provenance.

Upload [`www/`](www/) as the website root, or open [`www/index.html`](www/index.html) locally. The generated map is at [`www/map/index.html`](www/map/index.html) and the crawlable catalogue has a flat entry point at [`www/catalogue.html`](www/catalogue.html) plus [`www/people/index.html`](www/people/index.html).

## Public repository boundaries

This repository publishes code, documentation, and durable historical research
notes. Raw genealogy exports, downloaded source documents, browser captures,
generated websites, temporary artifacts, credentials, and raw Y-DNA test data
remain local and are excluded by `.gitignore`.
