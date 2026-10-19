# Toolkit dependency management

The reusable [genealogy-research-workbench](https://github.com/glasgowm148/genealogy-research-workbench) is an independent MIT-licensed repository. Glasgow uses it through a **Git submodule pinned to a reviewed commit** at `vendor/genealogy-research-workbench/`. This replaces the old copied source snapshot. There is one maintained source, and the parent Git commit records exactly which toolkit revision it uses. The published [v0.2.0 release](https://github.com/glasgowm148/genealogy-research-workbench/releases/tag/v0.2.0) is commit `cc7a3d8c657e5813c26f136005c36179e96ee56e`.

`pyproject.toml` declares compatibility with `genealogy-research-workbench>=0.2.0,<0.3.0`. `requirements/base.txt` includes `requirements/toolkit.txt`, which installs the submodule as the Python package. Runtime installation therefore gets the dependency without relying on the development requirements or a package-index publication. CI checks out submodules recursively.

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

The toolkit’s generated generic website does not replace Glasgow’s hand-researched site automatically. Existing Glasgow exporters/bridges use shared toolkit services; Glasgow retains its research catalogue, profile drafts and specialised site builders.

## Publication and release order

A submodule commit must exist in the toolkit’s remote for a fresh external clone or CI checkout to fetch it. Publish the toolkit repository/commit first, then publish the Glasgow consumer commit. Do not claim remote availability from a local checkout alone. Repository creation, pushes, package-index uploads and deployment remain explicit owner actions; local package and integration checks do not perform them.

## Verification at the separation

See the [19 October 2026 validation record](toolkit-separation-validation.md) for package, fresh-clone, import/build, browser and consumer results, including repairs to the pre-existing research/site failures.
