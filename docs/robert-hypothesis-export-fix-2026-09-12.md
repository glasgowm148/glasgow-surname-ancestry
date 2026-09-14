# Robert–Alexander hypothesis export correction

The v18 comparison already distinguished the Lisnagaver occupier, Glenleslie
Robert and the retired Robert/Catherine proposal. The remaining defect was
the publishing path: HTML resolved the shared relationship assessment, but
default dossier and network relationships used the older approved/tree rows.

## One current assertion, preserved history

The existing shared assessment now defines
`C-robert-alexander-father-hypothesis`: possible, open and unproved. It is
resolved into both people's default relationships, claims, presentation and
network endpoints. All carry the same reason, tithe record reference,
identity limitation and direct analysis links.

Historical assertions remain, with their original IDs and text:

- `C-b48375a01529`: earlier Alexander → Robert pedigree attachment.
- `C-ad51f3d1462c`: reciprocal reconstructed son attachment.
- `C-d7cae2ea03a1`: earlier supporting interpretation conflating the
  Glenleslie chronology with the Coltrim household. That interpretation is
  retired, not the independently stated open father hypothesis.

These claims have `lifecycle: historical`, a scoped supersession explanation
and a `superseded_by` link. The new assertion has `lifecycle: current` and
references its predecessors. Earlier relationship rows are in
`relationship_history`; original imported sections remain intact.
The source is published at `/assets/research/relationship-assessments.json`.
Source IDs refer to canonical records also mapped in the dossier's
`presentation.record_associations`; direct analysis links work without a
separate catalogue lookup.

The active Lisnagaver candidate's verdict, limitation and source IDs resolve
from this same assertion. Its links lead to Robert's identity and fatherhood
questions and the specific tithe row, not merely the general archive.

## Unchanged historical questions

Fatherhood is not established. Lisnagaver and Glenleslie are not merged.
Robert's dates and birthplace remain identity-dependent in the maintained
presentation. Catherine remains an unassessed alternative/imported mother
attachment, not an active mother hypothesis. No original research note,
prepared WikiTree text or private material was removed or newly disclosed.
The layout, stylesheet and dossier presentation version remain v18.

## Checks and deployment boundary

- 41 regression tests passed: current/historical claim semantics across
  HTML/dossier/network, reciprocal wording/references, scoped supersession,
  idempotence, no global status replacement, candidate comparison, identity
  qualifications, chronology, existing child assessments and retained exports.
- Re-running the publisher changed zero dossiers; both targeted pages rebuilt.
- Screenshots inspected at 1440px and 390px for both affected family rows:
  correct perspective labels, readable links and no horizontal overflow.
- Fresh HTML equals saved local HTML for all seven acceptance dossiers.
- Live check at **2026-09-12 09:29:06 UTC**: both dossier and network URLs
  returned the older semantics (Alexander → Robert superseded; reciprocal
  unknown), without the new assertion. Initial JSON requests returned 403;
  retrying with the working HTML client headers succeeded, as did the normal
  URLs without cache-busting parameters. This was not a broken-endpoint finding.

Local checks: **Pass locally**. Live current-hypothesis availability:
**Still failing publicly / awaiting upload**. No deployment was performed.
Full hashes and response headers are in
`artifacts/dossier-delivery/20260912T092906Z/report.json`.
The new archive's release manifest covers the affected network exports as well
as HTML, dossier JSON and the shared assertion source. Base catalogue data
build identity is kept separate from this narrowly scoped derived-data release.
