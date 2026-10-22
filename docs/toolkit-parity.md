# Glasgow site and workbench: feature parity

This compares what the Glasgow site does with what the reusable
[genealogy-research-workbench](https://github.com/glasgowm148/genealogy-research-workbench)
(`v0.6.0`, pinned in `vendor/`) builds from someone else's GEDCOM or OneTree export.
It was checked against the toolkit code, its fictional demo and imports of the
real local exports. Those imports were inspected locally and read-only; no real
data entered the toolkit repository.

Classes used below:

- **Reusable**: the workbench provides it for any project.
- **Configurable**: provided, with project settings or Glasgow-specific data layered on top.
- **Missing**: generic enough to belong in the workbench, but not built yet.
- **Needs research**: an export cannot supply it. It appears only when a project records the research.

## Matrix

| Capability | Glasgow site | Workbench 0.6.0 | Class |
| --- | --- | --- | --- |
| People catalogue, search and filters | Name, relative, date, place and evidence filters; worker search shards | Search across names, relatives, places and events; surname, year-range and evidence filters; sort; pagination. Past 300 people the page writes its first 100 and pages the rest; the search covers everyone | Reusable. Sharded search indexes are only needed well beyond about 5,000 people. |
| Person dossiers | Resolved model, family, evidence labels, conclusions, open questions | Names, life dates, family (parents, partners and marriages, children, siblings), events, claims with citations and evidence, linked research | Reusable. Written conclusions need research (`Finding` records). |
| Sources and citations | Source collections, approved PDFs, captures, a reading of each record | Bibliography (title, author, publication, repository), citation locators and abstracts (the researcher's reading of a record), assessments | Reusable. Images, transcriptions and licensed text need research and rights. |
| Evidence and claims | Claim and evidence model, `/evidence/` label guide | Claim, Citation and Evidence records; one label vocabulary; `evidence.html` guide | Reusable |
| Relationship confidence | Graded states, percentage bands, reviewed probability estimates | Documented/probable/possible/disproved/unassessed, plus a project's own grades defined in `genealogy.toml` (each counted as a standard grade); optional assessed `estimate` shown as "Probable (70%)"; the tree's own marks shown as "tree-marked …" | Reusable. Each estimate needs research; Glasgow's band scale stays Glasgow-specific. |
| Alternatives and relationship roles | Competing fathers and hypotheses kept with their own grades | Step, adoptive, foster and non-biological roles; "competing parent records" notice; `Hypothesis` records | Reusable |
| Family tree and branches | Radial whole tree, country colours, named branches, Y-DNA markers | Whole-tree canvas, family focus, branch cards, birth-year slider; a **Families & branches** page of surname groups and connected groups | Reusable. Hand-named branches and country colours are Glasgow-specific; Y-DNA needs research. |
| Timelines | Study timelines, dated events | Filterable event timeline; approximate dates kept as supplied. Past 300 events, a page per decade and a search across all of them | Reusable |
| Maps | Atlas with location precision, country summaries, Irish/Scottish gazetteer | Offline map of supplied coordinates with a `precision` field; broad locations are drawn as dashed rings; places grouped and summarised by recorded country or region; GeoJSON | Reusable. The gazetteer data is Glasgow-specific. No geocoding by design. |
| Comparisons and connections | Compare people; shortest connection | Same, over public recorded relationships | Reusable |
| Research studies | Free-space edition, study pages with rationale and linked subjects | `Study` records: rationale, escaped Markdown body with `[[record]]` references, conclusion, linked subjects; study pages and index with links both ways | Reusable. The content needs research; WikiTree free-space import is Glasgow-specific. |
| Research log | Completed searches on each profile (`completed_searches` in `presentation.json`) | `Search` records: where each search looked and what it found, including nothing; a **Research log** on Research (the newest 50 and the total) and on each person's page; withheld when anything it names is not public | Reusable. The searches need research. |
| Findings log | `/latest-findings/` dated discovery log and feed | `Finding.recorded_on`; a dated Latest findings log, newest first; an Atom feed when `site.base_url` is set | Reusable. Glasgow's feed is written by the shared `genealogy.feeds.atom_feed`. |
| Drafts and outstanding work | WikiTree profile drafts, diffs, amendment queue and register | Open questions, hypotheses and draft findings listed first | Reusable for research work. The WikiTree editing workflow stays in Glasgow. |
| Privacy filtering | `PublicPrivacy` repair of legacy JSON, search tables and routes | One fail-closed projection feeding every page, the data script, GEDCOM, GeoJSON, CSV and sitemap | Reusable. Glasgow's repairs are specific to its legacy data shapes. |
| Sitemaps and downloads | XML sitemap, reader sitemap, client-side GEDCOM | `sitemap.html`; `sitemap.xml` and canonical links with `site.base_url`; JSON, CSV, GeoJSON, GEDCOM 5.5.1 | Reusable |
| DNA | Y-DNA branches, comparisons, priorities | Adapter boundary only; raw DNA is rejected | Needs research, and stays optional |
| Import formats and media | WikiTree API captures, GEDCOM, OneTree | GEDCOM 5.5.1 and 7, GEDCOM 7 `.gdz` archives, OneTree JSON. Archive media stay in the private copy and are never published | Reusable. Publishing media needs rights review, which is research. |
| Internal link checking | `tools/check_internal_links.py` with a baseline | `genealogy.sitecheck` and `genealogy check-links`, with a ratcheting baseline | Reusable. Glasgow's checker now uses it and adds its own cause classification. |

## Page-by-page adoption of shared code

Glasgow's pages are built by its own tools from WikiTree captures, research
ledgers and the existing `www/` shell. The workbench builds every page from one
`ResearchCase`. Replacing a Glasgow builder with a workbench page would mean
moving Glasgow's research into case records first. So adoption is per piece:
a shared function is used where its output is identical or strictly better,
and it is checked against the real build before it lands.

| Page | Glasgow builder | Shared code used | Not adopted, and why |
| --- | --- | --- | --- |
| Latest findings (`/latest-findings/`, `feed.xml`) | `tools/build_latest_findings.py` from `research/latest-findings.json` | `genealogy.feeds.atom_feed` writes the feed. The output was byte-identical for all 864 findings before and after the change. | The page, kinds, statuses and pagination stay in Glasgow. `Finding` now has homes for the ledger's `kind`, `qualification` (`limitations`) and `relationship_changes` (`changes`), which the case translator uses. |
| Evidence guide and badges (`/evidence/`) | `tools/evidence_labels.py` | `genealogy.labels` vocabulary for toolkit grades and claim statuses | Glasgow's percentage bands and legacy aliases stay local. |
| Studies (`/branches/<study>/`, free-space edition) | `tools/build_study_pages.py`, `tools/free_space_edition.py` | None | Study prose is WikiTree wikitext parsed with `mwparserfromhell`. The workbench's `genealogy.markup` is a Markdown subset with `[[record-id]]` references, so it would change the text. Glasgow's study layout (timelines, connection diagrams, locator maps) has no workbench equivalent. |
| Branches (`/branches/`) | `tools/build_branches_directory.py` | None | Branches are hand-named, with Y-DNA and country colours. The workbench's surname and connected-family groups are computed, so they would replace curated content. |
| Internal links | `tools/check_internal_links.py` | `genealogy.sitecheck` | Glasgow keeps its cause classification and baseline. |

Candidates checked on 20 October 2026:

- **Dossier family roles: not adopted.** Glasgow's data has no step, adoptive or foster parent links. "Adopted" appears only in quoted source text. Its WikiTree non-biological marks already print as "Tree-marked non-biological … link" through `tools/evidence_labels.py`. Switching to `genealogy.labels.parent_role` would change that wording without adding information.
- **Findings as case records: deferred.** Mirroring `research/latest-findings.json` into toolkit `Finding` records would have no reader yet: no Glasgow page or export reads a case. It becomes worthwhile when a Glasgow page is built from a case. The toolkit model now has a home for the ledger's `kind`, `qualification` and `relationship_changes` fields.
- **Studies: not adopted.** Adoption needs a wikitext-to-Markdown conversion that keeps every reference. Until that exists, Glasgow's builder is the right tool.

## Rebuilding the Glasgow site from its research

`tools/toolkit_research_case.py` makes a workbench case from the One-Tree
export, Glasgow's public catalogue and its research files. `genealogy build`
then builds a whole site from that case. The project is private (default
`data/private/toolkit-build/`) and never committed. Glasgow's own rules apply
first:

- research notes come from the sections Glasgow publishes
  (`build_research_catalog._load_research_findings`), so editing logs and
  captured WikiTree pages stay out;
- a note paragraph naming a withheld profile becomes "Private family details
  withheld.";
- any other record whose text names a withheld profile is left out.

Since 21 October 2026 the translator also carries, for the workbench's
development release after 0.6.0:

- sibling assessments, as graded `sibling` links;
- each assessment's basis as the link's reason (`Relationship.rationale`)
  and its limitations on each of its evidence records (`Evidence.limitation`);
- a finding's `relationship_changes` as `Finding.changes` on the link they
  reassessed. "After" is the assessment's own state (`assessment_after`)
  where the change records one;
- `research_tasks` in `research/<profile>/presentation.json` as research
  questions about that person: `what` is the question and `matters` closes
  it as "Why it matters: …"; `resolves` (else `tests`) is what would answer
  it, and `record_target` is the next record. A task whose status begins
  "Completed" is resolved; the rest stay open;
- with workbench 0.8.0 (since 22 October 2026), the `completed_searches` in
  the same file as `Search` records in the research log, about that person:
  the search and its result as written, and the date as `searched_on` when
  it is an ISO date. A search about a person who is not public, or naming a
  withheld profile, is left out;
- Glasgow's surname variants as `[names.variants]`, grouped under Glasgow;
- the extra profile IDs of a merged catalogue person, and WikiTree merge
  redirects where the local overrides file is present, as `former_ids` of
  public people;
- source quality as `Citation.quality` where Glasgow's class is clear-cut:
  original → original; derivative, transcription and index → derivative;
  published history (`secondary`) and tree profile (`tree_only`) → authored.

Maintained totals for the new mappings, from the repository's research files:

| Glasgow research | Maintained | Carried | Left out, and why |
| --- | ---: | ---: | --- |
| Sibling assessments | 13 | 13 when both siblings are public | Same rules as other assessments |
| Assessment limitations | 199 | 199 on evidence records, when the assessment is carried | A limitation naming a withheld profile is left out |
| Relationship changes in findings | 66 | 16 agree with the current assessment | 45 record only that the link became "certain", which is not one of Glasgow's grades; 5 concern a link with no relationship record (resolved against the tree export, they may match) |
| Research tasks | 21 | 21 questions (4 resolved, 17 open) when the person is public | |
| Completed searches | 61 | Now carried as `Search` records when the person is public | A search naming a withheld profile is left out |
| Source qualities | 25 | 22 | 3 are not clear-cut: "previously inspected original or published inscription" and "contemporary source via maintained OCR" |

These were checked by translating the research files against stand-in
people, which validated with no errors and built with no broken links. The
real build needs the Git-ignored One-Tree export and `www/data/people.json`;
the table below is from the last run that had them.

Not carried:

- `[source_types]`: Glasgow's record roles are free text with no reader
  label or caution of their own. `evidence_labels.RECORD_EVIDENCE` describes
  how a record links to a person, not the record's type.
- `[site] contact_email`: Glasgow's contact address is not published.
- `Citation.information`: Glasgow does not record the informant's knowledge.

Totals only, 20 October 2026, with workbench 0.6.0:

| Glasgow research | Maintained | In the workbench site | What is left out, and why |
| --- | ---: | ---: | --- |
| People | 4,869 public in the catalogue | 4,834 | The One-Tree export (4,065 public), plus 769 catalogue people it lacks, 99 of them record subjects. 831 family links come from the catalogue |
| Canonical records → sources | 285 | 285, with 284 readings as citation abstracts | None. Every reading is already published in `www/assets/research/canonical-records.json` |
| Relationship assessments | 301 | 253, with Glasgow's grades and wording; 185 with a percentage | 35 name a person who is not public; 13 sibling assessments |
| Dated findings | 874 | 644, all with their records and type | 230 concern only people who are not public |
| Research notes → studies | 1,251 | 1,063, with 489 tables | 162 are about people who are not public; 26 have no reader-facing section; 60 paragraphs withheld |

Glasgow's grades come from `tools/evidence_labels.py`: Documented, Strongly
supported, Probable, Possible and Uncertain keep Glasgow's labels and
meanings on every page and in the evidence guide, each counted as the
nearest workbench grade.

The build has 6,175 pages and no broken links. No page is over Glasgow's
500 KB budget: the catalogue, timeline, places and sources pages write one
page of records and keep the rest on paged pages, and the shared data
script is 5.5 MB (17.6 MB with 0.5.0). No generated file names a withheld
profile.

Still to do:

1. **Rerun the real build** with the One-Tree export and catalogue present, and replace the totals above. Check the link report, the 500 KB budget and the withheld-profile scan again.
2. **Record the grade reached in relationship changes.** 45 changes say only "certain", and 12 of those name an assessment. Adding `assessment_after` would let them carry.
3. **Larger single pages that are Glasgow's content**: the longest study (460 KB) and the studies index (400 KB) are within budget but would need paging as the research grows.

Done: **completed searches** (61) are now carried as `Search` records and
shown in the research log on the Research page and on each person's page.

## What an export cannot recreate

A GEDCOM or OneTree file holds tree assertions. Without further research the
workbench cannot produce:

- assessed relationship confidence and percentage estimates (the workbench displays these once recorded);
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
