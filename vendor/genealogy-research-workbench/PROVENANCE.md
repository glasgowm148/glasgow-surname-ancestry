# Vendored genealogy-research-workbench

This is a source snapshot of the installable runtime package required by the
Glasgow project. It contains the package under `src/genealogy`, its packaged
starter data, and the upstream `pyproject.toml`; tests, examples, caches, Git
metadata, and generated build metadata are excluded.

- Package: `genealogy-research-workbench`
- Upstream version: `0.1.0`
- Source checkout: `/Users/m/Documents/GitHub/genealogy-research-workbench`
- Source checkout state: no commits and no configured remote (`HEAD` is unresolved)
- Snapshot file manifest SHA-256: `5802d97e2a7bbcc0c57762aff6e8a5734a37afde23f6517731f0da26deec7c18`
- License: no license file was present in the source checkout; no license is asserted here

To reproduce the manifest hash from the repository root, excluding this
provenance file and editable-install build output, run:

```sh
find vendor/genealogy-research-workbench -type f \
  ! -name PROVENANCE.md \
  ! -path '*/__pycache__/*' \
  ! -path '*/genealogy_research_workbench.egg-info/*' \
  -print0 | sort -z | xargs -0 shasum -a 256 | shasum -a 256
```

The snapshot is retained only to make this repository's CI and fresh local
environments install the real workbench package. When an authoritative,
licensed upstream release becomes available, replace this snapshot with a
reviewed pinned dependency and update this record.
