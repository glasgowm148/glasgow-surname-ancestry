# Genealogy toolkit separation

The authoritative reusable system is now an independent, MIT-licensed
`genealogy-research-workbench` repository. Glasgow consumes toolkit `0.3.x`
through a pinned Git submodule at `vendor/genealogy-research-workbench/`, replacing
the former copied source snapshot. See [dependency management](toolkit-dependency.md)
for initialisation, upgrades and release order.

The standalone toolkit now offers a local GEDCOM/OneTree upload workflow and
a connected generic website: people search and dossiers, whole-tree/family/branch
views, timelines, supplied-coordinate maps, sources, research, comparisons,
connection paths and public data downloads. It has a fictional demo, package
builds, MIT licensing and its own tests/CI. These generic views do not replace
Glasgow’s existing researched site automatically.

## Extracted platform-neutral responsibilities

- people, names, events, places, relationships, claims, sources, citations,
  evidence, hypotheses, questions, findings and durable cases;
- fail-closed public projection and raw-DNA rejection;
- TOML project configuration and adapter contracts;
- WikiTree, One-Tree, GEDCOM, FamilySearch, archive, spreadsheet/OCR and DNA
  adapter boundaries;
- configurable catalogue, map and timeline views plus JSON, NDJSON, CSV and
  GeoJSON exports;
- the `genealogy` CLI, packaged starter, generic agent instructions and generic
  research skill;
- synthetic, non-Glasgow end-to-end fixtures and tests;
- atomic research services, record search, evidence-gap and unresolved-work
  reports, relationship-graph traversal, and offline searchable HTML views;
- strict typed-record CLI management and complete local case bundles containing
  claim, evidence and reference indexes plus a durable Markdown handoff;
- explicit WikiTree HTTP transport with caller-owned application identity,
  retries and response/WAF validation, plus family-capture normalisation and
  case persistence, inside the optional adapter boundary;
- reusable WikiTree profile-ID/URL and FamilySearch person-ID validation, with
  Glasgow retaining only compatibility wrappers and project-specific examples.

## Glasgow-owned responsibilities

All `research/`, `surname-research/`, `data/`, `www/`, source captures, DNA
material, project branding, surname rules, source policies and research
hypotheses remain here. `genealogy.toml` is the Glasgow overlay. The established
export, surname-index, synchronisation and catalogue commands remain compatible.

The legacy Glasgow catalogue renderer and synchronisation tools still use their
established internal shapes. The established WikiTree family exporter now offers
`--toolkit-case-directory` as an additive handoff: its captured family is
normalised and saved through the toolkit's `save_wikitree_family_case` adapter
service while the existing Markdown and optional JSON outputs remain unchanged.
Glasgow now owns only the CLI option and project-specific case naming for that
handoff; neutral entity filtering, validation and storage remain in the toolkit.
Remaining WikiTree API requests in that exporter now pass through the toolkit's generic
`WikiTreeHttpClient`; Glasgow retains its own app ID, request headers and error
surface. The Glasgow overlay loader requires the toolkit's validated
`ProjectConfig`; it has no raw-TOML fallback. Glasgow compatibility wrappers retain their established command and data
contracts; the standalone toolkit owns generic model/adapter behaviour. Its
canonical OneTree identity helper is also used by the Glasgow bridge, avoiding
a second set of person-ID rules. The pinned submodule makes local source and
CI installs reproducible without assuming a package-index release exists.
The legacy research-state, plan and evidence-index files remain authoritative
because several Glasgow tools consume their version-1 schemas. Research mode
now offers an additive `--toolkit-research-bundle DIRECTORY` transition. When
explicitly selected, it maps structured profiles, questions and findings into
private neutral records, keeps targets and web searches as private import
provenance, and writes through the toolkit's versioned, checksummed, atomic
bundle API with verified readback. The five legacy state/plan/index/brief/
findings files are left untouched by the bridge and represented by hashes;
raw captures, biographies, FamilySearch page bodies and free-form Markdown
bodies are not duplicated. The bundle destination must differ from the legacy
case directory. No catalogue command is invoked.

Cases maintained by the other legacy producers can be converted without a
refresh or network request by naming exactly one source and destination:

```bash
.venv/bin/python tools/migrate_research_bundle.py \
  --research-dir /path/to/legacy-case \
  --bundle-dir /path/to/private-toolkit-bundle
```

This command performs no case discovery, synchronization or catalogue build.

## Explicit One-Tree bridge

`tools/genealogy_bridge.py` is the first production-facing compatibility path.
It accepts only a caller-supplied legacy JSON file, normalises people and
relationships through the toolkit's One-Tree adapter, and uses the toolkit's
fail-closed public projection. It has no default input or output and never
starts a catalogue build. For example:

```bash
.venv/bin/python tools/genealogy_bridge.py \
  --input /path/to/legacy-onetree.json \
  --export-output /path/to/filtered.json
```

Numeric legacy `Privacy` remains adapter-owned: values of 50 or more are
eligible for public access, while lower values are restricted. A record is still
withheld unless its person is deceased and all referenced records are public.
Raw DNA is rejected before a portable case or export can be written.

The separation changes software ownership and dependency installation. It does
not publish a site or change historical research; no Glasgow catalogue rebuild
is required for the dependency transition.
