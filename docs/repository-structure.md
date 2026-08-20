# Repository structure

| Path | Purpose |
| --- | --- |
| `src/` | Reusable WikiTree export and surname-index code |
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
