# Structured export follow-up

Bounded format/content skim of CSV, JSON, exported HTML/site, and Y-DNA files in `chatgpt_dump/`. No rows containing living-person or DNA details were reproduced, and no files were published or edited.

## Already represented / mostly presentation variants

- The 87-row family-record exports (`glasgow_family_records_*.csv`, including root-based, year-slider, clean-SVG, and filter-year variants) share the same person/profile, family-group, evidence, year, association, note, and location schema. They are successive presentation/filter exports of the same record set, rather than clearly new source material. The maintained map source is `www/map/data/records.csv` (4,887 lines including header), substantially larger and already carries the project’s current record inventory.
- The 52-row people/location exports and 30-row pin exports repeat the same map aggregates (person, profile, family group, evidence, coordinates, precision, location IDs). They appear to be intermediate map snapshots; no distinct source-reference column or archival reference surfaced in the skim.
- The 16-row exact-location pin variants and 18-row coordinate lookup are display-support tables. They do not expose a new documentary source in their headers.
- The exported map HTML files are self-contained visual builds or filter variants. Their structure references embedded data/CSV/JSON and does not, by filename/schema skim, identify an unrepresented original record.
- The three `glasgow-ydna-*.html` exports and their source-upload copies are page/presentation snapshots. They contain embedded references and Y-DNA narrative/UI material, but this scan did not extract or compare sensitive participant-level content. The maintained public data surface is `www/map/data/ydna-timeline.json` (15 entries) and `www/ydna.html`; no safe, clearly new public-safe source row was established.
- `glasgow-working-family-atlas/family-link-audit.json` and `legacy-hypotheses-reference.json` are implementation/audit exports. They may document UI/model state, but are not evidence candidates by themselves.

## Clear follow-up candidates (source-level review still required)

- `glasgow_death_records_estimated_birth_year(1).csv` has 241 data rows with registration ID, district, age at death, estimated birth year, and parse notes. This is the strongest structured candidate for a source audit because it has record identifiers and derived dates; the export alone does not establish whether all rows/provenance already exist in maintained research.
- `glasgow_londonderry_and_antrim_records.csv` has 87 rows and explicit profile/evidence/location fields. Its schema matches the family-record exports, so it is probably represented in the broader map inventory, but the Londonderry/Antrim subset should be reconciled by record/source reference before dismissal.
- `glasgow-wikitree-ids.csv` has 1,695 profile rows and identity/place fields. It is an export index, not documentary evidence; compare against the current catalogue only if a missing-profile or stale-ID audit is requested.
- `ONT_Glasgow_1400,1500_2026-08-04T10_07(1).json` is a five-key generated search/page payload (`data`, `html`, `surname`, `location`, `centuries`). It may contain an early-period search capture, but format inspection cannot establish novelty without a source-level comparison; defer to the medieval-review agent.

## Conclusion

No CSV/JSON/exported-site/Y-DNA file yielded a safe, proven novel finding from this bounded schema and presentation comparison. The death-record CSV and the Londonderry/Antrim subset are the only structured files warranting targeted source-ID reconciliation; the Y-DNA and living-person material remains intentionally unextracted.

## Source-ID reconciliation results

- `glasgow_londonderry_and_antrim_records.csv` (87 rows): 44 rows match `www/map/data/records.csv` on normalized person/profile/year/association/location fields. One additional row matches on the less-specific profile/year/record-location key, giving 45 represented rows. The remaining 42 rows have no corresponding current map row. They are mostly documentary or working-attachment rows (including undated/estimated years and reference-only locations); because this export has no archival source title, URL, or stable record ID, the unmatched rows are not recoverable evidence by themselves. They should be treated as superseded/intermediate regional export material unless the underlying source is located.
- `glasgow_death_records_estimated_birth_year(1).csv` (241 rows): only 1 registration ID appears in current map source text, and 2 additional rows have a name/year row-level match; 3 rows are therefore already represented at best. The other 238 rows are unmatched. They contain registration IDs and parsed/estimated dates but no source URL or image reference, so they are useful as a lookup queue for an official civil-registration source, not publishable evidence. No rows were added to the site.

These counts use normalized comparisons and deliberately do not treat name/year similarity as identity proof.

## Coordinator integration

The death CSV was subsequently preserved as an explicitly unverified lookup
list in the existing Ireland account. Comparison with `Pasted text(118).txt`
supports 100 rows; 141 are CSV-only, including two malformed rows on HOLD.
See `findings.md` for the authoritative outcome and maintained input paths.
The map comparison above is not a count of records new to the whole project.
