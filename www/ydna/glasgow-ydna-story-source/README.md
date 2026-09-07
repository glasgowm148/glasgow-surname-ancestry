# Glasgow Y-DNA — narrative edition

A self-contained HTML research page. Open `index.html` in a browser. The interface needs no installation, server, network connection or external assets; external source links open the referenced sites.

## Reading the page

**The story** is the default view. Five continuous chapters connect the northern background, the medieval British fork, the development of the Glasgow surname, Ulster and Atlantic movement, and the recent tested families. The illustrations explain their significance as well as showing their structure.

**Routes & timeline** provides the fuller historical argument, four qualitative route comparisons, the source-labelled ancestor dates, and the deeper historical stages.

**The family tree** and **People & matches** retain the kit-level material. **Research tools** contains the pair comparator, STR matrix/network, SNP and FT6135 analysis, and SAPP reconstruction. The research plan changes with the chosen question.

The light reading theme is the initial default. The header control switches to dark; a browser that permits local storage remembers the selection.

The dense audit layer from the earlier workbench is integrated into the relevant views rather than parked on a separate evidence page. Family and inheritance tables sit with Robert's pedigree; STR and placement audits sit with the matrix and SAPP model; call tables sit with the SNP analysis; all 17 matches remain in the searchable matches table; and line-level evidence needs sit with the goal-based research plan. All 13 retained tables are visibly represented, while the previous page remains available as an unchanged snapshot from Sources.

The documentary bridge chapter has also been refreshed from the local research pages and logs. It now distinguishes the 1194 Yorkshire Roger de Duffeld, Master John of Huntingdon, Roger de Glasgu, the separate medieval Glasgow bearers, John alias Smith and the later Saltmarket property sequence. The reported Duffield genetic placement and the Anglo-Norman/de Ferrers route are visibly treated as hypotheses requiring kit, pedigree or documentary verification.

## Rebuild or edit

Requires Python 3, standard library only:

```sh
python3 build.py
python3 build.py --output /path/to/site/ydna/index.html
```

Within this repository, publish the rebuilt page with:

```sh
python3 build.py --output ../index.html
```

The builder calculates the correct site-relative base for both the source preview and the public `www/ydna/index.html`. Use `--site-base` only for an unusual external output layout.

- `source/template.html`: narrative prose, page structure, static explanations.
- `source/style.css`: the underlying explorer styles.
- `source/story.css`: the narrative layout and responsive reading styles.
- `source/app.js`: comparisons, interactive explanations, navigation and exports.
- `data.json`: measurements, dated branch model, sources and deeper-stage text.

Narrative prose deliberately remains editable HTML rather than an opaque generated bundle. When updating the source data, review dates and numerical examples in the prose alongside the dynamic tables. The edition is a dated research snapshot, not an automatic live account feed.

## Evidence and interpretation

The supplied Y-DNA explorer and supplied timeline remain the factual basis. Their original bytes are retained under `reference/`. The new narrative and route comparisons are an explanatory synthesis, not a fresh sequence or documentary audit. The 1066–1150 period is the project timeline's historical arrival model, not a newly calculated statistical interval. The quantitative kit data, parent relationships, uncertainty ranges and unknown FT6135 states are preserved.

The selected routes and inheritance layers change the explanation/highlight, not the stored test results. No living tester names, new account data or sequence files are added.

## Reproduce the calculations and browser checks

The matrix audit uses only the standard library:

```sh
python3 verify_matrix.py --output matrix-audit.json
```

It checks the 21 supplied pair distances, eight minimum-spanning trees of weight 15 and four non-additive quartet cases. It analyses the supplied distance matrix, not raw genotypes.

`test_story.py` requires Playwright and Chromium. Set `CHROMIUM_EXECUTABLE` when a particular browser binary is needed:

```sh
python3 test_story.py
```

The browser suite covers the explanatory selectors, source navigation targets, all supplied pair distances, directional swaps, missing vs zero data, pedigree views, FT6135 scenarios, the restored evidence tables, filters, exports, and all eleven views at seven widths in both themes. The current environment had no Playwright Chromium binary, so the updated suite could not be rerun here; the static contracts, JavaScript syntax check and matrix audit were run instead. The checked-in JSON report records the preceding narrative-edition run and should be refreshed when Chromium is available.

**Test environment:** URL and file navigation were blocked by the runtime browser policy, so the unchanged HTML was injected into Chromium. The report records that limitation. These checks exercise rendering and interactions, not a separate hosted or local-file deployment. See `story-test-report.json` for exact results.

## Provenance notes

`NARRATIVE_NOTES.md` records the editorial structure, analytical choices and data-integrity comparison. `ANALYSIS.md` retains the earlier quantitative audit and origins analysis for continuity. The source register marks external references inherited from the earlier build as retained references, rather than implying they were newly checked for this edition.
