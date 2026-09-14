# ChatGPT export inventory (read-only scan)

Scanned `chatgpt_dump/` recursively on 2026-09-10. This is an inventory only; no research conclusions were assessed and no `www/` or research files were edited.

## Counts

- 487 files, 125,799,479 bytes (~120 MiB)
- 416 text, 24 code, 22 image/other assets, 14 documents, 7 other, 4 archives
- 36 files have an exact SHA-256 match in existing `research/`, `surname-research/`, `testaments/`, `www/`, or `archive/dump/`
- 57 internal duplicate-hash groups (148 files); many are copied/revised export variants
- Archives were listed without extraction: 4 archives, 17 members total

The machine-readable per-file record, hashes, archive member counts/samples, and existing-path matches are in `inventory.json`.

## Archive listings

- `Robert_Glasgow_Larne_research_bundle-1.zip` (5 members)
- `glasgow_pre1450_research_bundle.zip` (2 members)
- `Glasgow_parentage_backtests_2026-09-05.zip` (7 members)
- `Inishrush_identity_tests_2026-09-05.zip` (3 members)

## Promising unmatched export titles, grouped for later review

These are filename/title leads only, not validated findings.

### Parentage and identity testing

- `Glasgow_parentage_master_findings_2026-09-05(2).md`
- `Glasgow_joint_hypotheses_2026-09-05.md`
- `Alexander_Glasgow_hypothesis_tests_2026-09-05.md`
- `Alexander_Glasgow_record_brief_2026-09-04.md`
- `Glasgow_parentage_backtests_2026-09-05.zip`
- `Inishrush_identity_tests_2026-09-05.zip`

### Early and medieval bearers

- `Glasgow_Branches_and_Clusters_in_Early_Ireland_full_rewrite_2026-07-17.txt`
- `Early_Glasgow_Branches_updated(1).txt`
- `Glasgow_medieval_surname_page_updated(1).txt`
- `Glasgow_medieval_page_revised_2026-08-03(1).txt`
- `Glasgow_surname_medieval_bearers_updated_WikiTree_page.wiki`
- `Glasgow_pre1400_research_patch_2026-08-03.txt`
- `glasgow_pre1450_research_bundle.zip`

### Ireland, Londonderry and Antrim records/maps

- `glasgow_londonderry_and_antrim_records.csv`
- `Glasgow_Families_County_Londonderry_UPDATED_2026-07-21(1).wikitext`
- `Glasgow_Families_County_Londonderry_UPDATE_DIFF_2026-07-21.txt`
- `glasgow_family_records_with_filter_years.csv`
- `glasgow_family_records_year_slider.csv`
- `glasgow_people_by_family_group.csv`
- `glasgow_londonderry_and_antrim_family_map.html`

### Testaments and record transcriptions

- `Glasgow_testaments_working_transcription.md`
- `Glasgow_testaments_evidence_notebook.html`
- `1577_John_working_transcription.txt`
- `James_Glasgow_Innisrush_death_1878_transcription.txt` (duplicate copy also present)
- `glasgow_testament_workbench/glasgow_testament_workbench.html`

### Research handoffs and audits

- `Robert_Glasgow_Larne_research_handoff/04_RESEARCH_HANDOFF.md` (also duplicated at export root)
- `Robert_Glasgow_Larne_research_handoff/03_Master_professional_genealogy_research_prompt.md`
- `Roger_de_Glasgu_research_audit.md`
- `Glasgow_de_Glasgu_research_audit.md`

## Deduplication notes

Exact matches should be treated as copies of maintained material where the matching path is recorded in `inventory.json`. Near-duplicates are common among numbered `Pasted text/markdown` files and versioned HTML/CSV exports; this scan did not infer equivalence from content similarity. `archive/dump/` matches are retained as matches and should not be confused with the earlier archive/dump audit. Any later integration should compare the candidate against maintained source inputs and the public-safe website surfaces before deciding whether it adds new evidence.

