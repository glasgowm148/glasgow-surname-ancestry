# Recovered-file review — 10 September 2026

## Handoff note

Internal inventory and handoff. The current research account is on the existing
person and family pages; no standalone public audit page is maintained.

## Coverage

- Inventoried and SHA-256 hashed every file under `dump/`: **1,493 files**, about
  1.07 GB, **1,299 distinct contents**, **194 repeated copies**. The manifest is
  `inventory.json`; file counts are not counts of historical records.
- Classified 281 system/metadata files, 718 legacy software/export files,
  489 research candidates and five generated artworks. These are triage groups,
  not measures of evidential quality.
- Found 79 file copies with exact matches in maintained assets, testaments,
  data or research. All 41 substantive files in `Wills & Testaments` match the
  maintained `testaments/` collection; 28 additional files there are metadata.
- Screened the narrative notes and derivative tree/spreadsheet exports; extracted
  text from 77 historical/Misc/Antrim PDFs. Visually checked 45 selected historical
  image captures and the loose non-generated images. See the scoped handoffs for
  actual coverage rather than assuming that every page was transcribed.
- Root `WikiTree_Media-2.pdf` is an 18-page markup manual, not genealogical evidence.
  Root `george_.pdf` was rendered and inspected: it is the Mid Calder baptism
  page headed 17 February 1605, already represented by the George-1605 reading
  in `research/transcriptions/originals-2026-09-09/` (find the current dated
  originals directory if that revision changes).
- Root portraits, group photographs, the Pixelmator project preview and generated
  artwork supply no new verified historical identity. Personal images and social
  screenshots are retained privately. The loose manuscript crops lack adequate
  independent attribution for a new fact.

## Incorporated finding

**Robert Glasgow of Montgreenan — correction to the written account.**
`dump/TheGlasgows.md:11486–11509` preserves the UCL research on the 1803 trust.
The official UCL mirror was inspected at
<https://wwwdepts-live.ucl.ac.uk/lbs/person/view/2146643739> and
<https://wwwdepts-live.ucl.ac.uk/lbs/person/view/27300>.
It contradicts the categorical statement that Robert died without issue by
reporting children John and Emilia and identifying Anne in the succession.
The original trust and register images have not been inspected in this review.
This is recovered evidence missing from the site's current conclusion, not a
claim that the children were previously absent from WikiTree.

Maintained account and evidence limits: `research/Glasgow-1076/findings.md`.
The profile already displays child references, so no new people or relationship
changes were made. A complete replacement narrative is saved beside the findings
for later review; it has not been submitted to WikiTree.

Synchronized locally:

- `www/people/glasgow-1076.html` and `.json`: current conclusion, sources,
  household identity assessment and next records, derived from the findings.
- `www/branches/scottish-families/`: Montgreenan and St Vincent family account,
  maintained by `tools/repair_family_browsing.py::repair_montgreenan`.
- Name Study row in `surname-research/free-space-pages/Glasgow_Name_Study_Astra_reviewed.md`
  and `research/free-space-pages/pages/021-glasgow-name-study.wiki`.
- The relevant main research question and latest-research feed, maintained by
  their existing repair/build helpers.

## Material not promoted to fact

- The Jeremiah frontier biography has incomplete/unrecoverable citations. The
  current Timeline already labels his place in Henry's reported pedigree as a
  proposed extension; no extra public audit panel or pedigree change is needed.
- Older alias-Smith, Gamelin, Cunninghame-alliance, Tyrone-migration, Cameron and
  ancient-DNA narratives are superseded, already qualified, or unsupported.
- Eight Antrim census PDFs, several image-only census forms, the family Bible
  photograph and poorly attributed historical screenshots remain pending
  reliable reading/provenance checks. Their filenames do not prove identities.
- Raw genetic data, living-person records, personal photographs and software
  configuration were excluded from public integration.

## Handoffs and reproducibility

- `notes-findings.md`: narrative comparisons and superseded accounts.
- `historical-findings.md`: text and image coverage, known records, unreadable leads.
- `structured-findings.md`: export coverage, format limitations and stale claims.
- `.cache/dump-historical/coverage.json`: detailed image-review limits.
- `.cache/dump-audit/sync_person.py`: targeted refresh of this dossier using the
  existing catalogue findings loader/renderer. A future catalogue build reads
  the same maintained `findings.md`; no full catalogue regeneration was needed.

Local synchronization only. No deployment or live WikiTree edit occurred.

## Verification

Focused content, local-link and dossier-JSON checks passed. The Scottish-family
and main-question helpers were rerun with no additional change. Browser checks
confirmed readable person/family accounts at desktop and 390-pixel mobile widths.
The generated standalone audit route and its discovery panels were removed at
the user’s request; inventories remain internal.
