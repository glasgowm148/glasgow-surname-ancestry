# Navigation/shared-shell completion — 2026-09-30

Implemented the bounded navigation repair in maintained sources:

- `tools/section_submenus.js`: removes the People Filters row and Latest findings fake submenu; orders Family tree as Whole tree, Branch cards, Timeline, Y-DNA, Map; keeps family-study hash links same-document with native hash history, selected-state refresh, back/forward, and mobile close; reuses first-paint server submenu markup.
- `tools/repair_primary_navigation.py`: emits stable first-paint submenus for catalogue, Families & places, Family tree, sources, and About routes; adds Change log, correction, and status destinations to About; adds an idempotent `--reader-shell-only` repair for all place readers, catalogue variants, and the 102 public people readers (clusters, by-name, locations, people indexes, and early bearers), plus status, privacy, compare, candidate-match, changes, and feedback routes. Merged/refresh redirects stay untouched. It preserves page mains, release styling, filter forms, JSON-LD, relative links, and correction scripts, and runs as part of the regular `repair()` path. `--nav-only` now also synchronizes maintained submenu JS/CSS assets.
- `tools/section_submenus.css` keeps a long desktop submenu in the rail scroll area and gives the feedback textarea a readable width and height.
- `tests/test_navigation_completion.py` plus focused updates in `tests/test_primary_navigation.py` cover first-paint placement and order, Filters removal, shell preservation/idempotence, place and people asset/base handling, redirect exclusion, route coverage, CSS cohesion, and JS navigation contracts.

Validation:

```text
python3 -m unittest tests.test_primary_navigation tests.test_navigation_completion
...........
OK (14 tests)
```

The generated public HTML and `www/assets/unified/section-submenus.js` remain untouched in this handoff. Apply the targeted repair after reviewing concurrent `www` edits:

```bash
python3 tools/repair_primary_navigation.py --reader-shell-only
python3 tools/repair_primary_navigation.py --nav-only
```

The first command repairs the 1,265 place readers and the listed catalogue, clean, and legacy route pages without running a broad builder. The second command copies maintained submenu assets and refreshes shared rails only; no release publication was run.

## Shell audit (read-only)

Among 6,833 non-standalone/non-source/non-fragment/non-archival HTML files containing a `<main>` (excluding the two supplied Y-DNA reference pages and the Atlas template), 5,373 currently contain the shared `#g-navigation` rail. The remaining 1,460 are concentrated in legacy generated surfaces: 1,265 place pages, 102 full legacy person/catalogue readers, 79 merged-person redirect pages, six legacy root `.html` aliases, `catalogue/advanced.html`, and the clean-route indexes for candidate matches, status, changes, and feedback; `privacy/index.html` was the other focused About-owned shell gap. The maintained shell repair now covers privacy, changes, and feedback; the broad place/person legacy population remains a separate migration and was not rewritten here.

The audit found 6,833 public reader files with a `<main>` after excluding standalone, source, fragment, archival, supplied-reference, and template pages; 5,373 already had `#g-navigation`. The 1,460 remaining files comprised 1,265 place readers, 181 people readers (79 merged redirects and 102 public legacy readers), six root aliases, catalogue variants, and the focused clean-route pages. The narrow repair covers all place readers, catalogue variants, public people readers, and requested route pages; it intentionally leaves merged redirects unchanged.

The shared-shell conversion removes inherited `<base>` behavior, retains page mains and inline form/privacy styles, preserves root-relative links/scripts, and supplies the shared footer targets. The generated `www` HTML and unified submenu asset remain untouched in this handoff; root can apply the two commands after the concurrent `www` freeze.
