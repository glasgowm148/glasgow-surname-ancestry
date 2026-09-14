# Genealogy toolkit split

The reusable system lives in the ordinary sibling repository
`../genealogy-research-workbench`. This repository remains the Glasgow surname
research project and consumes toolkit version `0.1.x` (or the sibling checkout
through `requirements/toolkit-local.txt` during development).

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
`ProjectConfig`; it has no raw-TOML fallback. Other production paths can migrate
incrementally after the toolkit has a published package and cross-repository CI.
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

No catalogue rebuild was performed as part of this split.
