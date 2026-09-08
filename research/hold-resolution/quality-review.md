# HOLD-resolution quality review

Reviewed 8 September 2026. This is an independent defect review of the
early-Scotland verdicts and the Ballybogy, Oritor, Drumragh, Killycurragh,
Prescott and Cape drafts. No live WikiTree edits or catalogue rebuild were
performed.

## Corrected defects

1. **Cape Alexander had an empty creation birthplace and unsupported context.**
   The two NAAIRS index titles do not establish that Maria Welch was Maria
   Lacey Welch, that Gerhard Myburgh was a Cape Town merchant, or that Alexander
   belonged to a Cape Town property network. Those claims and the proposed
   occupation/residence context were removed. Cape Colony, South Africa, is now
   supplied only as an uncertain birth-location field inferred from Alexander's
   own first documented adult legal appearance. The draft expressly says that
   neither Cape Town residence nor birthplace is proved. The known Lisnagaver
   Thomas is now linked as [[Glasgow-987]].
2. **The Prescott will was treated as an unverified supplied reading.** The
   registered copy was inspected directly on FamilySearch, film 008200419,
   image 35. It names Robert's brothers Daniel, Samuel, John and Thomas, the
   children of deceased brother James, and sister Mary, then appoints “my said
   brother Samuel Glasgow” executor. The Robert and Samuel drafts and
   `research/Glasgow-4010/findings.md` now cite the inspected image rather than
   asking for an image recheck.
3. **Robert's creation birthplace was blank despite usable immediate-family
   context.** Robert's proved brother [[Glasgow-4010|Samuel]] was recorded as
   Irish-born in the original 1851 Prescott census. Robert's creation field now
   uses Ireland as uncertain, explicitly as sibling-derived context rather than
   a found birthplace. The Samuel replacement also now links every already
   created household profile: [[Unknown-764031]], [[Glasgow-4016]],
   [[Glasgow-4017]], [[Glasgow-4019]] and [[Glasgow-4021]].
4. **The Killycurragh/Oritor exclusion of [[Glasgow-1165]] relied on a probate
   chronology fallacy.** A death in 1823 cannot alone exclude a delayed 1826 or
   1836 probate entry. The exclusion is now based on the incompatible
   relationship-defined family: Glasgow-1165 is a son of John Glasgow and Mary
   Arthur, whereas T1959/3 places the Oritor and Killycurragh men in two other
   named families. The draft and findings retain the probate-date caution.
5. **The Killycurragh draft omitted the strongest existing sibling lead.**
   [[Glasgow-1698|Samuel Glasgow]], born about 1800 and reported dead at
   Killycurragh in 1857, is now recorded as the leading candidate for the
   letter's Samuel who remained in the parental house, not as a proved sibling.
   [[Glasgow-1675|William Glasgow]] is excluded from the letter's physician
   William by his documented elder/emigration/Ohio life. Both profile findings
   files now preserve those conclusions.
6. **The Saltcoats daughter drafts retained stale HOLD wording after the John
   decision.** Agnes and Katherine now direct the editor to create the distinct
   Saltcoats John first and attach him as certain father. They no longer present
   [[Glasgow-1030]] as the unresolved father candidate; Isobell Gray's maternity
   remains correctly unproved.

## Central-data defects for the root workflow

- `www/map/data/records.csv` rows for the 1893 and 1898 Cape cases still repeat
  the unsupported Maria Lacey/mortgage and Cape Town commercial-context claims
  and leave Alexander's creation birth location blank. They should match the
  corrected draft: Cape Colony/South Africa uncertain, with no Cape Town
  residence or occupation assertion.
- The Prescott Robert row still has no birth location and cites the later
  property history as its principal source. It should carry uncertain Ireland
  from Samuel's original census and preserve the directly inspected
  FamilySearch will as a separate original-record citation/provenance item.
- The Killycurragh row uses `before 1802`, which is not established merely
  because the letter writer was born in 1801. The defensible direct boundary is
  before about 1815 from adult status at the 1836 probate event, matching the
  draft.
- The saved audit and `to-update.md` still contain the old HOLD state and the
  deleted Ballybogy-junior draft path. These require the root's planned central
  remapping and regeneration, not edits in this review.

## No defect found

The seven verdicts in `early-scotland.md` are evidence-calibrated. All seven
corresponding creation drafts, plus the already-ready Saltcoats Agnes draft,
contain creation fields, native WikiTree biography/Research Notes/Sources
markup, citations, duplicate reasoning and uncertain household-derived birth
locations. The corrected Ballybogy, Oritor, Drumragh and Killycurragh drafts
are also structurally complete. The Ballybogy unsuffixed man remains safely
distinct even though the separate junior entry is only probably assigned to
[[Glasgow-2981]].

## Residual HOLD audit

### Resolved: Maria Glasgow duplicate

[[Glasgow-3928]] and [[Glasgow-2137]] should no longer remain on HOLD. The
Hiltner database assigns one person (`I370`) both to John Glasgow and Mary
Arthur's family and to Alexander Wallace. This is explicit descendant
identification, not an automated same-name score. The Bible proves Maria's 22
September 1800 birth in the natal family; the Wallace identification remains
derivative because Robert Glasgow's cited 2018 report is not publicly attached
and the Bible does not mention the marriage.

The remaining evidence converges without a substantive conflict: the 1822 date
on Glasgow-2137 is an uncited estimate; Maria born in 1800 was 39–41 at the two
known births; the Wallace family lived at Rasharkin in the same Bann Valley
setting as the Inishrush Glasgows; daughters Mary and Lavinia repeat the names
of Maria's mother and uncommon-named sister; and the refreshed live WikiTree
search found no third compatible Irish Maria Glasgow. This supports a
**probable merge into Glasgow-3928**, with the missing original bridge stated
plainly rather than treating the spouse identity as direct proof. A complete
post-merge profile is ready at `research/Glasgow-3928/Glasgow-3928.md`.
Glasgow-2137 is managed by [[McMeekan-55]], so this is ready to submit as a
merge proposal but may require that manager's approval before completion.

[[Unknown-764460|Mary (Unknown) Glasgow]] also contained stale “creation remains
on hold” wording in its resolved evidence handoff. The workhouse record defines
a publishable profile even though it does not prove her husband or the
consecutive children's maternity. The handoff now distinguishes a resolved
profile from the still-open relationship question; only those attachments must
wait for the original register or another explicit kinship record.

### Genuine active HOLD: Elizat Stevinsoun

[[Stevenson-7398]] is excluded as Robert Blaikstone's Yorkshire wife.
[[Stevinsoune-1|Bessie Stevinsoune]] cannot yet be excluded or identified. The
Findmypast transcript `R_695585805/2` and the published Dunfermline parish
register show that Bessie married George Lugtoun on 25 February 1606 and that
they baptised John on 3 February 1607 and Annas on 27 June 1609. The source
gives no parents, earlier residence or prior marital status. Because Andrew
Glasgow died in 1597/8, the chronology permits Elizat to have remarried; because
no record joins Bessie to Corsoun, Andrew, Robert or the landholding, a merge is
equally unsafe. This is an evidence gap, not an unreviewed candidate score.

The Elizat creation handoff and Andrew's findings now contain the full
Dunfermline evidence and the exact resolution test. Publication can proceed for
Andrew and the four proved Glasgow children without creating or attaching
Elizat; Andrew's biography can name her directly from his testament while the
structured spouse link remains unchanged and uncertain.

### Exact `to-update.md` corrections

The following line numbers refer to the file before the root workflow's central
rewrite:

- **Line 19:** retain as the one genuine active identity HOLD, but replace
  “compatible Stevinsoune profile remains under review” with the specific
  Bessie/George Lugtoun 1606–1609 evidence and resolution test above.
- **Line 478:** stale. Replace the Maria HOLD with **READY — PROBABLE MERGE
  Glasgow-2137 INTO Glasgow-3928**, linking the complete post-merge draft and
  both findings files.
- **Lines 23–24, 46–47, 154–155, 444 and 719:** stale Saltcoats HOLD state. The
  distinct John and Katherine decisions supersede the Glasgow-1030/3942
  hypotheses; these lines must not reopen them.
- **Lines 293–299:** stale Cape HOLD narrative. The corrected Alexander draft
  now treats the two actions conservatively and is creation-ready.
- **Line 305:** stale Prescott HOLD. Robert's inspected will directly names
  Samuel and the other siblings; the record-defined Robert is creation-ready.
- **Lines 479–486:** these are live Ireland identity decisions owned by the
  Ireland HOLD audit, except that the deleted Ballybogy-junior path at line 482
  is already known stale and must not survive the central rewrite.

Lines 415–416 are not queue-state defects: they accurately record separate
historical merge questions for the James 3077/3337 and Hew 1067/3109 pairs.
Fan-chart root HOLDs and dated audit prose describing an earlier state may also
remain when clearly labelled as history rather than current work.
