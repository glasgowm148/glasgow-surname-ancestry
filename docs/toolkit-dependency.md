# Toolkit dependency management

The reusable [genealogy-research-workbench](https://github.com/glasgowm148/genealogy-research-workbench) is an independent MIT-licensed repository. Glasgow uses it through a **Git submodule pinned to a reviewed commit** at `vendor/genealogy-research-workbench/`. This replaces the old copied source snapshot. There is one maintained source, and the parent Git commit records exactly which toolkit revision it uses. The pin is toolkit commit `98f9505` on `main` (the whole-tree atlas and reading room, DNA page, update priority, home lead sections, saved views, branch stories), thirteen commits after [v0.8.0](https://github.com/glasgowm148/genealogy-research-workbench/releases/tag/v0.8.0) (commit `7dd370e771c1da5b177b9ade4f1a1f738f91fa19`): the translator sets `Place.region`, change `significance` and `Haplogroup` records. The toolkit's `main` branch (and the `v0.8.0` tag) must be pushed before this Glasgow commit is pushed or shared: until then, a recursive clone cannot fetch the pinned commit.


**Pin (25 October 2026).** The submodule names workbench commit `cd5c605077fa68a4ec2ff0fa490ff105c0679aa3` (0.9.0, the research database), which is the workbench's `main`; a fresh recursive clone fetches it. It is not tagged.

`pyproject.toml` declares compatibility with `genealogy-research-workbench>=0.9.0,<0.10.0`. `requirements/base.txt` includes `requirements/toolkit.txt`, which installs the submodule as the Python package. Runtime installation therefore gets the dependency without relying on the development requirements or a package-index publication. CI checks out submodules recursively.

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
