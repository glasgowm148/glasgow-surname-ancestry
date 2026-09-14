# Source recovery continuation, 10 September 2026

## Useful results

- Recovered Renwick's actual protocol volume II: Internet Archive
  [abstractsprotoc04robegoog](https://archive.org/details/abstractsprotoc04robegoog).
  The title identifies William Hegait's Protocols, 1555-60 (1896).
- Examined protocol 307, printed p. 15 (6 August 1556), and 402, printed p. 41
  (22 November 1557). Both give John Glesgw as an eastern property boundary.
  Neither gives a Glasgow kinship relationship. The explicit father-son
  succession in 402 belongs to Thomas and John Bargilly.
- Do not treat a historical boundary description as proof that its named
  owner was alive or present. Existing probable Glasgow ties remain probable.
- Retrieved four dated Leith child-record leads and the reported 1646 marriage
  reference from public WikiTree biographies. Full handoff:
  `research/Glasgow-3078/parish-register-targets-2026-09-10.md`.
- Corrected a contradictory automatic identity assignment in
  `research/Glasgow-3938/findings.md`, source `fmp-glasgow-937fb03a9d56`.
  The 1666 cordiner Robert Glasgow-Euphame Lorimer household is not thereby
  proved to be the Robert who married Jonet Thomsone in 1652.

## Rechecked, not newly discovered

The Edinburgh burgess roll was retrieved from Internet Archive item
`scottishrecordso46scotuoft`. Printed p. 208 contains James Glasgow's
20 June 1649 admission, repeating his apprenticeship date 16 June 1641 and
master William Sclaitter. This was already documented under Glasgow-1150;
do not present it as a new bridge to Andrew of Corstoun's son Robert.

The same page's Robert Glasgow-Euphame Lorimer entry, 4 July 1666, was already
discussed under Glasgow-3938, Glasgow-1149 and Glasgow-1078. A shared cordiner
trade does not connect Robert to either Leith Archibald.

## Testament originals still outstanding

| Target | Established finding-aid information | Volume status |
| --- | --- | --- |
| Margaret Smith, spouse of James Glasgow, Brekpleughe, Steinstoune | Confirmation 21 February 1632; printed Glasgow testament calendar p. 460; series CC9/7 | Exact volume/image not established. Another person's October 1632 entry in CC9/7/25 cannot fix this February entry's volume. |
| Agnes Glasgow, spouse of John Logane, trumpmaker, Stevenston | Confirmation 4 March 1628; printed calendar p. 195; series CC9/7 | CC9/7/22 is cited in the current Glasgow-3178 biography, but her original entry or full volume date coverage has not been checked. Treat as a candidate, not newly confirmed. |
| John Mathie of Ibert, Kilmaronock | Confirmation 9 November 1607; Glasgow commissary series CC9/7 | Exact volume/image not established. Another early-1607 record in CC9/7/5 cannot fix the November entry's volume. |

The public Smith-374110 biography repeats the calendar date but provides no
original-image reference. The public Glasgow-3178 biography cites CC9/7/22;
repetition of that citation does not independently verify the reference or
the manuscript's contents. No original for these three targets was located
in the bounded local filename and public-access searches. This is not a claim
that none exists or that it is unavailable to an authenticated researcher.

The [NRS commissary court guide](https://www.nrscotland.gov.uk/learning-and-events/research-guides/commissary-court-records/)
identifies Scotland'sPeople as the wills index route. No credits were spent,
no restricted access bypassed, and no purported transcription produced from
an unread original. Chrome could be listed by the computer-use tool, but
attachment timed out; no purchased-image account was inspected.

## Retrieval notes for the next pass

- `getProfiles` was rejected by this API endpoint. Public `getRelatives` POST
  succeeded with `fields=Name,Bio` and `bioFormat=wiki`; returned biography
  key is lower-case `bio`.
- `getRelatives` for Glasgow-2714 with `getSiblings=1` supplied the four public
  child profiles and their citations. Their shared attachment is not a source
  independent of WikiTree's existing family reconstruction.
- FamilySearch FQMH-CXH returned an internal error through the web tool.
  Avoid repeating broad exact-name searches in place of obtaining the images.
- Public report data: `followup-2026-09-10/protocol-volume-two-recovery.json`
  and `followup-2026-09-10/leith-parish-targets.json`.

No relationships, dates or locations were detached, blanked or changed on
WikiTree in this pass. No code tests or browser-validation cycle was run.
