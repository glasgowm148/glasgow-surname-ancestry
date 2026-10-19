# Glasgow site and workbench: feature parity

This compares what the Glasgow site does with what the reusable
[genealogy-research-workbench](https://github.com/glasgowm148/genealogy-research-workbench)
(0.3.0 at `85264b2`, pinned in `vendor/`) builds from someone else's GEDCOM or OneTree export.
It was checked against the toolkit code, its fictional demo and imports of the
real local exports. Those imports were inspected locally and read-only; no real
data entered the toolkit repository.

Classes used below:

- **Reusable**: the workbench provides it for any project.
- **Configurable**: provided, with project settings or Glasgow-specific data layered on top.
- **Missing**: generic enough to belong in the workbench, but not built yet.
- **Needs research**: an export cannot supply it. It appears only when a project records the research.

## Matrix

| Capability | Glasgow site | Workbench 0.3.0 | Class |
| --- | --- | --- | --- |
| People catalogue, search and filters | Name, relative, date, place and evidence filters; worker search shards | Search across names, relatives, places and events; surname, year-range and evidence filters; sort; pagination | Reusable. Sharded search indexes are only needed well beyond about 5,000 people. |
| Person dossiers | Resolved model, family, evidence labels, conclusions, open questions | Names, life dates, family (parents, partners and marriages, children, siblings), events, claims with citations and evidence, linked research | Reusable. Written conclusions need research (`Finding` records). |
| Sources and citations | Source collections, approved PDFs, captures | Bibliography (title, author, publication, repository), citation locators, assessments | Reusable. Images, transcriptions and licensed text need research and rights. |
| Evidence and claims | Claim and evidence model, `/evidence/` label guide | Claim, Citation and Evidence records; one label vocabulary; `evidence.html` guide | Reusable |
| Relationship confidence | Graded states, percentage bands, reviewed probability estimates | Documented/probable/possible/disproved/unassessed; the tree's own marks shown as "tree-marked …" | Reusable. Percentage estimates are not modelled, and each estimate needs research. |
| Alternatives and relationship roles | Competing fathers and hypotheses kept with their own grades | Step, adoptive, foster and non-biological roles; "competing parent records" notice; `Hypothesis` records | Reusable |
| Family tree and branches | Radial whole tree, country colours, named branches, Y-DNA markers | Whole-tree canvas, family focus, branch cards, birth-year slider; a **Families & branches** page of surname groups and connected groups | Reusable. Hand-named branches and country colours are Glasgow-specific; Y-DNA needs research. |
| Timelines | Study timelines, dated events | Filterable event timeline; approximate dates kept as supplied | Reusable |
| Maps | Atlas with location precision, country summaries, Irish/Scottish gazetteer | Offline map of supplied coordinates with a `precision` field; broad locations are drawn as dashed rings; GeoJSON | Reusable. Country summaries are missing; the gazetteer data is Glasgow-specific. No geocoding by design. |
| Comparisons and connections | Compare people; shortest connection | Same, over public recorded relationships | Reusable |
| Research studies | Free-space edition, study pages with rationale and linked subjects | `Study` records: rationale, escaped Markdown body with `[[record]]` references, conclusion, linked subjects; study pages and index with links both ways | Reusable. The content needs research; WikiTree free-space import is Glasgow-specific. |
| Findings log | `/latest-findings/` dated discovery log and feed | `Finding.recorded_on`; a dated Latest findings log, newest first; an Atom feed when `site.base_url` is set | Reusable |
| Drafts and outstanding work | WikiTree profile drafts, diffs, amendment queue and register | Open questions, hypotheses and draft findings listed first | Reusable for research work. The WikiTree editing workflow stays in Glasgow. |
| Privacy filtering | `PublicPrivacy` repair of legacy JSON, search tables and routes | One fail-closed projection feeding every page, the data script, GEDCOM, GeoJSON, CSV and sitemap | Reusable. Glasgow's repairs are specific to its legacy data shapes. |
| Sitemaps and downloads | XML sitemap, reader sitemap, client-side GEDCOM | `sitemap.html`; `sitemap.xml` and canonical links with `site.base_url`; JSON, CSV, GeoJSON, GEDCOM 5.5.1 | Reusable |
| DNA | Y-DNA branches, comparisons, priorities | Adapter boundary only; raw DNA is rejected | Needs research, and stays optional |
| Internal link checking | `tools/check_internal_links.py` with a baseline | `genealogy.sitecheck` and `genealogy check-links`, with a ratcheting baseline | Reusable. Glasgow's checker now uses it and adds its own cause classification. |

## What an export cannot recreate

A GEDCOM or OneTree file holds tree assertions. Without further research the
workbench cannot produce:

- assessed relationship confidence;
- percentage estimates;
- studies and written conclusions (the workbench now publishes these once written);
- source images or transcriptions;
- location precision beyond the supplied coordinates;
- DNA findings.

Imported links therefore read "Unassessed tree link". The tree's own marks,
such as WikiTree's uncertain, confident or DNA-confirmed, are shown as that
tree's statement and never as an assessment. A link's step, adoptive or
non-biological nature is kept as supplied.

## Results from the local real exports (19 October 2026, read-only)

| Export | People | Public after review (0.2.0 → 0.3.0) | Notes |
| --- | ---: | ---: | --- |
| WikiTree GEDCOM | 128 | failed → 94 | 0.2.0 rejected the file: raw line breaks in notes. 207 lines are now kept as continued note text. |
| RootsMagic GEDCOM | 170 | 137 → 137 | `_UID`, `_FSFTID`, `REFN`, `WWW` kept as identifiers |
| Family Tree Maker GEDCOM | 2,079 | 1,460 → 1,474 | 2 step-parent links (`_FREL Step`) are now labelled, not flattened |
| Ancestris GEDCOM | 2,079 | 1,460 → 1,474 | |
| OneTree (Glasco) | 238 | 139 → 198 | |
| OneTree (Glasgow) | 4,394 | 3,133 → 4,065 | WikiTree `YYYY-00-00` dates and guess/before/after qualifiers kept. 959 parent links carry the tree's own mark: 856 confident, 93 uncertain, 9 DNA confirmed and 1 non-biological. Duplicate spouse links are merged. |

The extra published people come from three rule changes:

- `YYYY-00-00` dates can now be assessed;
- burial or cremation records count as evidence of death;
- an approximate birth now counts as up to ten years later (about 1800 is treated as 1810) under the unchanged 120-year rule.

No living-flagged person, restricted record or person with `Privacy` below 50
was published. No withheld person's ID appears in any generated file.
The largest site was 66 MB for 4,065 dossiers, with one shared 7.7 MB data
script, and built in about 25 seconds.
