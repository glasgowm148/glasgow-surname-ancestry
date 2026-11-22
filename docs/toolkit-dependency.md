# Toolkit dependency management

Glasgow consumes the independent [genealogy-research-workbench](https://github.com/glasgowm148/genealogy-research-workbench) repository through the Git submodule at `vendor/genealogy-research-workbench/`. The parent commit records the exact revision. Run `git ls-tree HEAD vendor/genealogy-research-workbench` to check it.

**18 November 2026.** The local pin is `e18dcea` on toolkit branch `codex/preserve-projection-confidence`. The public projection applies configured grades only to assessments using the project's grading vocabulary. Other assessments retain their stored confidence. The toolkit commit was pushed to its [feature branch](https://github.com/glasgowm148/genealogy-research-workbench/tree/codex/preserve-projection-confidence) and verified against the remote on 22 November 2026.

**26 October 2026.** The submodule used workbench commit `4c9e3b6` (0.10.1: database schema version 2, with resolutions for items kept for review and in-place files tracked by version), the workbench's `main`; a fresh recursive clone fetches it. It is not tagged. Moving from 0.9 needs one database migration, which backs the database up first: `.venv/bin/genealogy db migrate` (the Glasgow database was migrated on 25 October 2026).

`pyproject.toml` declares compatibility with `genealogy-research-workbench>=0.10.0,<0.11.0`. `requirements/base.txt` includes `requirements/toolkit.txt`, which installs the submodule as the Python package. Runtime installation therefore gets the dependency without relying on the development requirements or a package-index publication. CI checks out submodules recursively.

## Clone or initialise

```sh
git clone --recurse-submodules https://github.com/glasgowm148/glasgow-surname-ancestry.git
cd glasgow-surname-ancestry
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements/base.txt -r requirements/dev.txt -c requirements/constraints.txt
```

For an existing clone:

```sh
git submodule update --init --recursive
```

A source ZIP of the Glasgow repository does not include submodule contents. Use a recursive Git clone, or install a matching separately downloaded toolkit explicitly. Do not copy or edit a second snapshot into this repository.

## Develop shared code

Work in the standalone toolkit checkout. To test uncommitted upstream work with Glasgow, deliberately override the installed editable dependency:

```sh
python -m pip install -e /path/to/genealogy-research-workbench
python -m unittest discover -s tests -p 'test_toolkit_integration.py' -v
python -m unittest discover -s tests -p 'test_glasgow_research_toolkit.py' -v
```

The separate checkout may live anywhere. `requirements/toolkit-local.txt` is only a shorthand when it is adjacent to Glasgow. Reinstalling the normal requirements restores the pinned submodule installation.

## Upgrade the pin

1. Finish, test and commit the toolkit change in its own repository.
2. Make that toolkit commit available upstream before sharing a Glasgow commit that references it.
3. Fetch/check out the reviewed toolkit commit in the submodule:

```sh
git -C vendor/genealogy-research-workbench fetch origin
git -C vendor/genealogy-research-workbench checkout <reviewed-toolkit-commit>
python -m pip install -r requirements/base.txt -r requirements/dev.txt -c requirements/constraints.txt
make check
```

4. Commit the updated submodule pointer and any required Glasgow integration changes. Update the compatible version bound if needed. Browser-check affected site paths when the integration changes them.

The toolkit’s generated generic website does not replace Glasgow’s hand-researched site automatically. Existing Glasgow exporters/bridges use shared toolkit services; Glasgow retains its research catalogue, profile drafts and specialised site builders. Shared helpers now used directly include `genealogy.dates.wikitree_date` (WikiTree `YYYY-00-00` placeholders, in the family exporter and surname index) `genealogy.publication.is_historical_birth` and `birth_upper_year` (the single 120-year rule, in the recent-changes sync and the `public_privacy` living screen) and `genealogy.sitecheck` (resolution, scanning and baselines behind `tools/check_internal_links.py`). [Parity](toolkit-parity.md) lists what remains Glasgow-specific.

## Publication and release order

A submodule commit must exist in the toolkit’s remote for a fresh external clone or CI checkout to fetch it. Publish the toolkit repository/commit first, then publish the Glasgow consumer commit. Do not claim remote availability from a local checkout alone. Repository creation, pushes, package-index uploads and deployment remain explicit owner actions; local package and integration checks do not perform them.

## Verification at the separation

See the [19 October 2026 validation record](toolkit-separation-validation.md) for package, fresh-clone, import/build, browser and consumer results, including repairs to the pre-existing research/site failures.
