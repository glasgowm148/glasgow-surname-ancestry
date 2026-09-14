# Maintained testament readings

The public collection is `/research/transcriptions/`. Full original files in
`testaments/` remain local. User-requested focused crops are published under
`www/assets/research/testament-crops/` for illustrated reading and commentary,
with archive attribution. No synthetic manuscript imagery is used.

- `index.json` preserves the earlier saved attempts and their source excerpts.
  Its `source_files` and `original_preview` fields also identify supplied PDFs
  awaiting a fresh reading. Source availability is independent of review or
  illustrated-walkthrough completion.
- `originals-YYYY-MM-DD/*.json` holds dated fresh image reviews. Folder dates
  identify a batch; `reviewed_at` records the actual review date.
- `tools/build_transcriptions.py` publishes the ledger, individual cases,
  downloadable working text and links from associated person pages through
  `tools/publish_testament_reviews.py`. The regular site repair pipeline calls it.
- Later reviewed records supersede earlier reports with the same `id`.
- `walkthroughs/<case-id>.json` maintains numbered manuscript passages, named
  people, literal/modern readings, reading explanations and evidential limits.
  Image-overlay coordinates are percentages of the unaltered exported crop;
  `kind` distinguishes `name`, `relationship` and `uncertain`. The renderer
  provides switchable highlights and enlargement without baking annotation
  into the source image. Keep the guided reading before technical case notes.
- Every retained mark carries `analysis`: `reading`, `expansion`, observed
  `features`, optional same-hand `comparison`, and `uncertainty`. Its full-stroke
  bounds also drive an unaltered magnified word sample. Store actual
  `image_width` / `image_height` on each step. Unresolved, unmarked details may
  use `word_studies` with the same bounds and analysis without implying an
  identified person. Include ascenders, descenders and flourishes with a small
  margin; never crop to the body of the letters. Only the selected outline is
  displayed, with numbered controls outside the manuscript.
- `coverage: full` means the supplied record image span was examined. It does
  NOT mean every word was deciphered or that the transcription is complete.
- List missing pages explicitly. Keep earlier readings of absent pages as
  earlier assessments, not fresh confirmations.
- Distinguish uncertain letters, editorial expansion, omitted text and missing
  images. Never supply a legal formula simply because it is expected.
- Separate verbatim working passages, modern interpretation, evidence-led
  conclusions, revision history, source files, associated profiles and gaps.
- Profile associations may be rejected identities or comparisons. Preserve the
  qualification in the label; do not generate parent/child edges from these links.

## Batch corrections, 10 September 2026

Annotation placement must be measured on the exact exported JPEG/PNG, not an
earlier source crop or whole-page rendering. Record actual dimensions, locate
the labelled words, and convert pixel bounds to percentages. Split wrapped
phrases into separate boxes. Inspect each passage's overlay proof against
the handwriting; a rectangle being inside the image is not evidence that
it covers the right word. An excerpt missing its claimed text must be
replaced or its unsupported callout removed. Local audit proofs belong in
`tmp/pdfs/annotation-audit/`, not in the public original-image directory.

Katherine's image 7 reads "the nynt day of may 1605": 9 May, superseding the
older uncertain 26 May reading. Archibald's 1662 record says Leith and places
his January will before his February death. The Jonet Meik February 1606 date
belongs to making the testament, not an independently established death date.

The two Jonet PDFs are one record (CC9/7/5, images 82-83). The William 1673
PDF in the Edinburgh folder and root CC14/5/9 PDF are the same Lanark record
(images 24-26); the publisher merges the alias `william-lanark-1673` into
`william-1673`. George1605 is a Mid Calder baptism, not a testament, and is
published separately from testament totals.

John1577 image277 is supplied within the nested three-page John PDF; its third
page is a separate Andrew Hutcheson screenshot and must not be assigned to John
merely because of its reused header. Andrew1598 also has a local page-two
capture. Earlier opening-only reviews do not constitute fresh transcriptions
of these continuations. John1650 opening image65 is supplied in the nested 1650_Glasgow.pdf and 1650_John_p1.png; its debts continue onto image66.
The originals for Geillis1603 and Quothquan1685 are supplied:
`testaments/Glasgow/1603_GIllis/1603_Gillis.pdf` (CC9/7/3, images113-114) and
`testaments/Glasgow/Lanark/1685_John_Lanark.pdf` (CC14/5/12, images67-68).
Fresh reviews and illustrated readings belong to their canonical case IDs
`geillis-1603` and `quothquan-1685`, published from the latest dated review
files. Source availability and transcription completeness remain separate.
