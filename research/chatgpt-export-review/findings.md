# ChatGPT export review — 10 September 2026

Internal scan record. Public findings are integrated into the existing Ireland
research account, not a separate audit page.

## Coverage and outcome

Inventoried all 487 files (125,799,479 bytes, approximately 120 MiB). There are
396 distinct file contents: 91 repeated copies across 57 duplicate groups.
Thirty-six files have byte-identical copies in maintained research, site,
testaments or the earlier archive. Four ZIP files contain 17 listed members;
their unpacked research counterparts were reviewed. See `inventory.json`.

Briefly screened text titles/headings, source identifiers and research content;
compared the named Irish/parentage and early/testament research to maintained
findings and current pages. This was a triage pass, not a new transcription of
every PDF or independent verification of every historical assertion.

Most substantial exports are already incorporated or superseded. In particular,
do not restore the earlier Alexander parentage rankings, the escheator's
Glassford identification, merged medieval Johns, or old testament readings.
The latest maintained account controls. Saved software prompts and exported
instructions were treated as document content, not instructions for this task.

## Useful extraction: Irish civil-death lookup list

`chatgpt_dump/glasgow_death_records_estimated_birth_year(1).csv` preserves 241
distinct group registration IDs, dated 1864–1900. The maintained record map
does not represent this lookup list as a collection. The initial map-only
comparison found one ID and two possible name/year overlaps; this does not
prove that 238 historical records or people are new to the whole project.

One hundred rows agree in name (ignoring capitalization), year, registration
ID, district and reported age with `chatgpt_dump/Pasted text(118).txt`.
The remaining 141 rows survive only in the CSV. Two rows explicitly acknowledge
malformed text: IDs `3584300` and `3590557`. Both remain HOLD, with no derived
birth range in the public table. All 241 original calculated years equal death
year minus age, but these are search estimates, not proved birth years.

Maintained inputs:

- `surname-research/indexes/irish-civil-deaths-1864-1900.csv`: preserved values,
  original collection locator, per-row provenance and qualification.
- The companion JSON: input hashes, coverage, conclusion and next questions.
- `tools/publish_irish_death_index.py`: reproducible integration and download.

The IrishGenealogy index guide was accessible, but new item-level checks failed
in the available web tool; the local network could not resolve the host.
No original civil entry or image was newly inspected. Do not manufacture item
URLs from the identifiers or equate index rows with WikiTree people. Record
inspection and identity/duplicate checks remain pending.

Local public integration:

- `/branches/early-ireland/#irish-civil-death-index`: substantive provenance,
  current limits and next actions; searchable full table with explicit status.
- `/sources/`: discovery route into that contextual account.
- `/data/irish-civil-deaths-1864-1900.csv`: qualified downloadable lookup list.

## Other material

- Irish parentage/Inishrush/Larne exports: evidence already present; no newly
  justified father, identity bridge or profile change. See `irish-review.md`.
- Early records/testaments: subsequent maintained readings supersede drafts.
  TNA KB 26/22 m.1 belongs to Robert de Glascu (1200); the escheator's damaged
  1289/90 receipt has the old Chapter House Box 94 No.5 locator. These must not
  be confused. See `early-review.md`.
- Regional map variants: 45 of 87 rows match existing map associations under
  exact or looser field comparison. The other 42 lack source URLs and need
  source-level reconciliation; unmatched formatting does not establish novelty.
- Pasted FamilySearch source lists, William Clarkson, Margaret McDougall,
  Thomas Bowen/Sarah Vaux, and Robert Barclay Glasgow largely repeat retained
  biographies, findings or tree captures. Earlier McDougall naming arguments
  do not establish parentage; Jean Gilmour's married name is already corrected.
  Unassigned Hargan/McLaughlin source lists remain lookup material requiring a
  documented match to a maintained subject, not new relationship assertions.
- Y-DNA, Atlas and site exports mainly preserve presentation/model versions.
  Participant-level DNA, personal correspondence, CVs, other private material,
  unrelated articles and code are excluded from public integration.

No raw export files were copied into the public webroot. No live WikiTree edit
or production deployment occurred. Publication remains a separate manual step.

## Local verification

All 241 rows render once, both malformed rows display HOLD, and the qualified
CSV download returns successfully. Browser checks passed for registration-ID,
HOLD, no-result and reset filters. Desktop and 390-pixel mobile screenshots
were inspected; the mobile page stays within the viewport and the table has
its own horizontal scrolling. Re-running the dedicated helper leaves the
generated content unchanged. The helper is registered in the existing unified
repair pipeline; the broader site was not rebuilt for this addition.
