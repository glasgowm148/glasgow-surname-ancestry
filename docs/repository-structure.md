# Repository structure

| Path | Purpose |
| --- | --- |
| `genealogy.toml` | Glasgow overlay for the reusable toolkit: branding, adapters, paths and privacy policy |
| `src/` | Glasgow WikiTree export and surname-index integration code; generic models live in the sibling toolkit |
| `tools/` | Map builds, data synchronization and focused research utilities |
| `tests/` | Offline unit tests and the Chromium map regression test |
| `data/exports/one-tree/` | Source One-Tree JSON snapshots |
| `data/reference/` | Reference workbooks used for discovery |
| `artifacts/profile-exports/` | Generated profile reports, raw exports and browser snapshots |
| `assets/source-images/` | Source images retained for research |
| `map/` | Interactive map application and its documentation |
| `www/` | Self-contained website root for deployment |
| `www/map/data/` | Authoritative map CSV, geocode cache and generated audits |
| `research/` | Individual WikiTree profile research cases |
| `surname-research/` | Surname-wide evidence, clusters, indexes and update queues |
| `requirements/` | Base, browser and combined dependency sets |
| `.cache/` | Browser profiles, OCR corpora and temporary investigation files |

The repository root intentionally contains only entry-point documentation,
environment files and these top-level project directories. Generated exports
belong under `artifacts/`; durable input snapshots belong under `data/`.

## Toolkit boundary

`../genealogy-research-workbench` is an ordinary sibling repository during
development, installed with `requirements/toolkit-local.txt`. It supplies the
platform-neutral genealogy package and CLI; this repository supplies the Glasgow
research configuration, source policies, surname rules, research cases and website.
Published installs replace the editable path with the versioned dependency in
`pyproject.toml`. Neither arrangement changes the established Glasgow command paths
or authorizes a catalogue rebuild. Restricted people, licensed sources, raw captures
and raw DNA remain excluded from public toolkit exports.
