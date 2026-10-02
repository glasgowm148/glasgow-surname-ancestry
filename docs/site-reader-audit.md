# Reader wording and navigation audit — 29 September 2026

## Follow-up audit repairs — 2 October 2026

The delegated audit fixes are maintained in the builders and shared assets:

- Record searches react immediately to person/family changes and honour inherited country scope. Unknown countries show a recoverable error rather than unrelated results.
- Global search reserves results for each category, reports complete counts, includes Latest findings and deduplicates old page names. The worker remains compatible with already-open pages during deployment.
- Explicit catalogue and research-reader index URLs retain their destination and query. Existing catalogue shells recover their correct page class; update badges meet text-contrast requirements.
- Reviewed OPR birth/death sections and downloads survive finalization. William Glasgow's existing parish-index evidence is visible at the start of his biography, with the uninspected original-image limitation retained.
- Finding confidence and profile-identification qualifications are labelled separately. Research questions expose their missing connection while keeping evidence and technical archive targets available in disclosures.
- Free-space introductions end cleanly, studies have individual descriptions and canonical URLs, and all 85 reading bodies remain unchanged from the previous release.
- Assessment prose cannot supply structured event dates. False years inferred from profile identifiers are removed from public evidence, events, source ranges and static readers; original prose, prior values and real dated evidence remain preserved.
- Catalogue snapshot dates agree across readers. The sitemap includes approved public research routes and excludes private, living, duplicate and fragment-only pages.

Regression workflow: run `tools/check_site_audit_fixes.js` through Playwright CLI against the currently open local or production origin, alongside the generated-content and browser quality gates in `docs/site-experience-checks.md`. It covers actual family switching, country scope, search categories, aliases, redirects, OPR downloads and the corrected evidence readers. Screenshots and logs are under `output/playwright/site-fixes-20261002/`. Publication details and final verification are recorded in `docs/public-catalogue-deployment.md`.

The following entries retain the earlier audit history.

The critique identified two connected problems: abstract software language and
too many competing ways into the research. The site should read as family
history research, with clear routes to people, relatives, records and sources.

| Previously | Reader wording |
| --- | --- |
| Atlas / canopy | Family tree / whole tree |
| Person dossier / current position | Biography / biography and research notes |
| Research cluster | Family or research group |
| Mapped associations | Record entries, with an explanation of person–record links |
| Explicit source / candidate match / citation unresolved | Source cited / possible source match / citation needed |
| What would resolve this / record to request or inspect | What evidence would answer this? / next record to check |
| Find the place. Follow the family. | Families and places |

Records & sources now has a primary menu link. Its submenu distinguishes source
references, records by person, and wills and transcriptions. Research retains
open questions, relationship searches, person comparisons and WikiTree study
pages. The homepage reading guide precedes the larger study map, with Alexander's
worked example below the map. Repeated copies of the map script are removed.

The changes preserve research accounts, source references, record tables,
manuscript images, profile identifiers, URLs, confidence distinctions, earlier
assessments and specialist tools. Group labels explain that being listed
together does not prove kinship. Wording is maintained in the rendering inputs
and the project research skill, so rebuilds retain it.

Validation: 29 focused regression tests, 146 desktop/mobile browser checks
(including 320 px), and 733 generated-content checks passed. Asset version
checking found no stale references. Eight representative pages retained their
source destinations, record tables and figures; an older research-note bookmark
was preserved with an alias. Original people and record datasets are unchanged.
These are scoped presentation checks, not a new audit of historical conclusions.

The local release refresh is complete. Production publication remains pending.

Follow-up, 30 September 2026: restored the study map above Alexander's example.
Tree repairs accept both old and current toolbar labels; research restoration
keeps Whole tree, Timeline, Branch cards and Y-DNA in that order and preserves
the Whole tree heading in loaded scripts and templates. Ten focused tests and
34 browser checks passed at 1440, 390 and 320 px, including map zoom and tree
view switching. Production publication remains pending.

Follow-up: restored the shared sidebar on `/compare/`. Clean-route generation
now keeps fresh comparison controls, data scripts and cautions inside the shared
layout. Six focused regression tests passed; desktop and 390/320 px browser
checks covered comparisons, query preservation and mobile navigation. No browser
errors were recorded. Production publication remains pending.
