# Repository structure

| Path | Purpose |
| --- | --- |
| `genealogy.toml` | Glasgow overlay for the reusable toolkit: branding, adapters, paths and privacy policy |
| `src/` | Glasgow WikiTree export and surname-index integration code; generic models live in the independent toolkit |
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
| `vendor/genealogy-research-workbench/` | Independent toolkit Git submodule pinned to a reviewed upstream commit |
| `.cache/` | Browser profiles, OCR corpora and temporary investigation files |

The repository root intentionally contains only entry-point documentation,
environment files and these top-level project directories. Generated exports
belong under `artifacts/`; durable input snapshots belong under `data/`.

## Toolkit boundary

`vendor/genealogy-research-workbench/` is a Git submodule of the independent,
MIT-licensed toolkit repository, not a copied source snapshot. The base
requirements install that pinned checkout. Its generic models, adapters,
import/upload workflow and site builder can serve other family-history projects;
Glasgow supplies its own configuration, research cases and specialised website.

Use `git submodule update --init --recursive` after cloning, and consult
[toolkit dependency management](toolkit-dependency.md) for development and upgrades.
The consumer metadata requires toolkit `0.2.x`; the gitlink pins the exact source
revision. A separate editable checkout can override it intentionally in a local
virtual environment. No toolkit installation or configuration read authorises a
catalogue rebuild. Restricted people, licensed sources, raw captures and raw DNA
remain excluded from public toolkit exports.
