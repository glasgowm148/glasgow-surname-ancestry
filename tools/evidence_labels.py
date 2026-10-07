#!/usr/bin/env python3
"""The one public vocabulary for evidence and confidence states.

Internal keys are unchanged; only the words readers see are defined here.
Every surface (catalogue, dossiers, study pages, Atlas, evidence guide) takes
its labels from this module or from its JSON mirror,
``www/assets/research/evidence-labels.json``.

Rules the vocabulary follows:

* A label never claims more than its evidence. "Documented" is reserved for a
  relationship or fact stated by a cited record (key ``proved``).
* Marks copied from a family tree say so ("Tree-marked …"); this project has
  not independently assessed them.
* An unmarked tree link is called unassessed.
* Text is always shown, so no state depends on colour alone.

Run this file to rewrite the JSON mirror (idempotent).
"""
from __future__ import annotations

from html import escape, unescape
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
JSON_PATH = ROOT / "www/assets/research/evidence-labels.json"
GUIDE_URL = "/evidence/"
GUIDE_LABEL = "How to read the evidence"
VERSION = "1"

# Relationship and claim states. ``family`` groups states for styling only;
# ``glyph`` is a redundant, non-colour cue shown beside the text label.
STATES: dict[str, dict[str, str]] = {
    "proved": dict(
        label="Documented", family="documented", glyph="✓", source="research",
        meaning="A cited record states this directly, and the research has checked that the record belongs to this person.",
    ),
    "strongly_supported": dict(
        label="Strongly supported", family="supported", glyph="✓", source="research",
        meaning="Several independent, consistent records point to this, but no single record states it outright.",
    ),
    "probable": dict(
        label="Probable", family="probable", glyph="~", source="research",
        meaning="The evidence favours this over the alternatives, but it is not proved and could still change.",
    ),
    "possible": dict(
        label="Possible", family="possible", glyph="?", source="research",
        meaning="Consistent with the evidence so far. A lead to test, not a conclusion.",
    ),
    "uncertain": dict(
        label="Uncertain", family="possible", glyph="?", source="research or tree",
        meaning="Flagged as uncertain, either by this research or by the tree contributor. Treat as unresolved.",
    ),
    "disputed": dict(
        label="Disputed", family="conflict", glyph="!", source="research",
        meaning="Records or researchers disagree, and the conflict is not resolved.",
    ),
    "contradicted": dict(
        label="Contradicted", family="conflict", glyph="✕", source="research",
        meaning="The available records argue against this link. It is shown only so that readers can see why it was rejected.",
    ),
    "superseded": dict(
        label="Superseded", family="conflict", glyph="↺", source="research",
        meaning="An earlier proposal that later research has replaced. Kept for the audit trail.",
    ),
    "dna_confirmed": dict(
        label="Tree-marked DNA confirmed", family="tree", glyph="◇", source="tree",
        meaning="The WikiTree contributor marked this link as confirmed with DNA. This project has not independently checked that DNA reasoning.",
    ),
    "confident": dict(
        label="Tree-marked confident", family="tree", glyph="◇", source="tree",
        meaning="The WikiTree contributor marked this link as confident. It is the contributor’s judgement, not an assessment by this project.",
    ),
    "non_biological": dict(
        label="Tree-marked non-biological", family="tree", glyph="◇", source="tree",
        meaning="The tree marks an adoptive, step or other non-biological relationship.",
    ),
    "unmarked": dict(
        label="Unassessed tree link", family="unassessed", glyph="○", source="tree",
        meaning="Copied from the family tree with no certainty mark. It has not been assessed against records.",
    ),
}

# Legacy or surface-specific spellings of the same states.
ALIASES = {
    "documented": "proved", "strongly-supported": "strongly_supported", "supported": "strongly_supported",
    "dna-confirmed": "dna_confirmed", "non-biological": "non_biological",
    "unknown": "unmarked", "unassessed": "unmarked", "": "unmarked",
}

# Values of WikiTree's parent ``data_status`` field.
TREE_DATA_STATUS = {"5": "non_biological", "10": "uncertain", "20": "confident", "30": "dna_confirmed"}

# The catalogue's source-quality classes (``source_quality`` values).
RECORD_QUALITY: dict[str, dict[str, str]] = {
    "original": dict(label="Original record", meaning="An image or original register, return, will or deed that has been inspected."),
    "derivative": dict(label="Index or transcription", meaning="An index, abstract, calendar or transcription of an original. Useful for finding the original, but open to copying errors and omissions."),
    "secondary": dict(label="Secondary source", meaning="A published history, family account or later compilation. Its claims need their own sources."),
    "tree_only": dict(label="Tree/profile only", meaning="Known only from a family-tree profile. A lead to look for records, not evidence in itself."),
    "unknown": dict(label="Unclassified", meaning="The source has not yet been classified. Do not assume it is an original."),
}

# Record-association evidence terms used by catalogue rows and the records search.
RECORD_EVIDENCE: dict[str, str] = {
    "Documented": "A cited record places this person in this event.",
    "Probable": "The record probably concerns this person, but the identification is not proved.",
    "Profile lead": "Reported on a tree profile; inspect its sources before relying on it.",
    "Kin-inferred profile lead": "Placed through a relative’s tree profile, not through a record naming this person.",
    "Traditional": "A family tradition or later account without a contemporary record.",
    "Estimated": "A date or place inferred from other evidence, such as an age at death or a later census.",
}

# The four-step scale used on family and locality study pages.
STUDY_TONES: dict[str, dict[str, str]] = {
    "proved": dict(label="Documented", state="proved", meaning="A cited record states the link."),
    "supported": dict(label="Strongly supported", state="strongly_supported", meaning="Consistent records support it; none states it outright."),
    "hypothesis": dict(label="Working hypothesis", state="possible", meaning="A proposal the study is testing; not a conclusion."),
    "unresolved": dict(label="Unresolved", state="unmarked", meaning="Not yet assessed, or the records do not decide it."),
}

# Research-question statuses and the prompts every published question shows.
QUESTION_STATUS = {
    "open": "Open",
    "partly_answered": "Partly answered",
    "answered": "Answered",
}
QUESTION_FIELDS = {
    "resolve": "What evidence would answer this?",
    "record": "Next record to check",
}
NOT_YET_IDENTIFIED = "Not yet identified"

DATE_PLACE_NOTES = (
    ("Exact", "A day, month and year taken from a record."),
    ("c. / about", "An approximate date, usually calculated from an age or a nearby event."),
    ("before / after", "A limit only: the event happened before or after this date."),
    ("Estimated", "A date or place inferred from other evidence. It is a working value, not a recorded fact."),
    ("Place not established", "No reviewed record gives the place; a tree value may be shown separately as a lead."),
)

CLUSTER_NOTE = (
    "People are grouped by household, place or related records to help investigate possible family connections. "
    "Being in the same group does not prove that people were related."
)

ROLE_NOUNS = {"father", "mother", "parent", "son", "daughter", "child", "spouse", "partner", "sibling", "brother", "sister"}
_GRADED = {"proved", "strongly_supported", "probable", "possible"}
_LEGACY_ROLE = re.compile(
    r"^(?:Documented|Strongly identified|Strongly supported|Probable|Possible|Unassessed|Disputed|Contradicted|Uncertain|"
    r"Tree-marked (?:DNA confirmed|confident|non-biological))\s+(" + "|".join(sorted(ROLE_NOUNS)) + r")(?: link)?$",
    re.I,
)


def canonical_key(value) -> str:
    """Map any surface spelling of a state to its canonical key."""
    key = str(value if value is not None else "").strip()
    if key in TREE_DATA_STATUS:
        return TREE_DATA_STATUS[key]
    lowered = key.casefold().replace(" ", "_")
    if lowered in STATES:
        return lowered
    return ALIASES.get(lowered, ALIASES.get(lowered.replace("_", "-"), "unmarked"))


def label(value) -> str:
    return STATES[canonical_key(value)]["label"]


def meaning(value) -> str:
    return STATES[canonical_key(value)]["meaning"]


def css_class(value) -> str:
    return "evidence-" + canonical_key(value).replace("_", "-")


def quality_label(value) -> str:
    return RECORD_QUALITY.get(str(value or "unknown"), RECORD_QUALITY["unknown"])["label"]


def study_label(tone: str) -> str:
    return STUDY_TONES.get(tone, STUDY_TONES["unresolved"])["label"]


def relationship_label(state, role: str) -> str:
    """Label a relationship from the opened person's perspective."""
    key = canonical_key(state)
    role = (role or "relationship").strip().casefold()
    if role == "partner":
        role = "spouse"
    if key in _GRADED:
        return f"{STATES[key]['label']} {role}"
    if key == "superseded":
        return "Superseded proposal"
    if key == "unmarked":
        return f"Unassessed {'partner' if role == 'spouse' else role} link"
    return f"{STATES[key]['label']} {role} link"


def normalise_status_label(state, text: str) -> str:
    """Bring an existing dossier label into the canonical vocabulary.

    Generic role labels are rebuilt from the recorded state. A curated,
    qualified label (for example "Probable; 1892 next-of-kin citation") is
    kept and only prefixed with the canonical term when it does not already
    begin with it. Idempotent.
    """
    key = canonical_key(state)
    text = " ".join(unescape(str(text or "")).split())
    if key == "superseded" and text in {"", "Superseded proposal"}:
        return "Superseded proposal"
    legacy = _LEGACY_ROLE.match(text)
    if legacy:
        return relationship_label(key, legacy.group(1))
    if text in {"Tree relationship", "Relationship not assessed", "WikiTree tree relationship"}:
        return relationship_label(key, "spouse" if text == "Tree relationship" else "relationship")
    if not text:
        return STATES[key]["label"]
    term = STATES[key]["label"]
    if text.casefold().startswith(term.casefold()):
        return text
    if key == "unmarked":
        return text if text.casefold().startswith("unassessed") else f"Unassessed · {text}"
    return f"{term} · {text}"


# ---------------------------------------------------------------------------
# Reader labels: one entry point for every printed label
# ---------------------------------------------------------------------------
#
# ``describe(value)`` turns any stored value (a state key, a tree status code, a
# source-quality key, a record-link term or a curated badge text) into the
# words a reader sees, a one-line meaning and the anchor of that label's entry
# in the guide. ``label_html(value)`` prints it as a linked badge. Wording and
# links only: the stored value and its grade are never changed.

# What kind of record each label usually rests on, shown in the guide.
STATE_BASIS: dict[str, str] = {
    "proved": "A record that names both people and the relationship, such as a baptism naming the father, a marriage naming the bride’s father, or a will naming a son.",
    "strongly_supported": "Two or more independent records that agree, for example a burgess roll and a testament that together place someone in a family, with no record naming the link itself.",
    "probable": "Indirect records that fit better than any alternative: shared places, witnesses, estate parties or naming patterns.",
    "possible": "Fit in time, place and names, with no record yet tying the people together.",
    "uncertain": "Usually a tree link flagged as uncertain by its contributor, or a research link that the records do not settle.",
    "disputed": "Records that disagree with each other, or researchers who read the same records differently.",
    "contradicted": "A record that rules the link out, such as an estate list that leaves the person out or dates that cannot fit.",
    "superseded": "Earlier research notes. The record that replaced the proposal is named with the current conclusion.",
    "unmarked": "A family-tree profile only. No record has been checked for this link yet.",
    "confident": "The tree contributor’s own judgement on WikiTree.",
    "dna_confirmed": "The tree contributor’s DNA reasoning on WikiTree.",
    "non_biological": "The tree contributor’s note that the parent is adoptive, a step-parent or similar.",
}

# One real example from the site for each label. ``None`` means the label is
# part of the scale but no published page currently uses it.
GUIDE_EXAMPLES: dict[str, tuple[str, str] | None] = {
    "state-proved": ("James Glasgow (baptised 1731) and his father Robert: an original memorial states the father–son relationship.", "/people/glasgow-1144.html"),
    "state-strongly-supported": ("Ann Taggard Glasgow (born 1733) and her father Robert: supported by a direct register transcription rather than the original register.", "/people/glasgow-1500.html"),
    "state-probable": ("Robert Glasgow (about 1800) and his father Wilson Crossier Glasgow: a reconstruction of the parties to Wilson’s estate favours the link, but no record states it.", "/people/glasgow-2298.html"),
    "state-possible": ("Hugh Glasgow (about 1770) as a son of James Glasgow (1748–1812): the generation and names fit, but no inspected record names Hugh as James’s son.", "/people/glasgow-4180.html"),
    "state-uncertain": ("Adam Glasgow (born before 1794) and his father Adam: the WikiTree contributor marks this parent link as uncertain.", "/people/glasgow-1622.html"),
    "state-disputed": None,
    "state-contradicted": ("James J Glasgow (about 1810) and Wilson Crossier Glasgow: Wilson’s estate records list seven children and leave James out, so the father link is shown as contradicted.", "/people/glasgow-2738.html"),
    "state-superseded": None,
    "state-unmarked": ("Abraham Glasgow (baptised 1719) and his father Thomas: copied from the family tree with no certainty mark and not yet checked against records.", "/people/glasgow-1227.html"),
    "state-confident": ("Abraham Glasgow (baptised before 1745) and his father Abraham: the WikiTree contributor marks the parent link as confident.", "/people/glasgow-1235.html"),
    "state-dna-confirmed": ("Joseph Dorris Glasgow (1820–1862) and his father Isaac Wesley Glasgow: the WikiTree contributor marks the link as confirmed with DNA.", "/people/glasgow-121.html"),
    "state-non-biological": ("Bessie Glasgow (born 1891) and Mary Louisa (Schenck) Jones: the WikiTree contributor marks the mother link as non-biological.", "/people/glasgow-3683.html"),
    "quality-original": ("Adam Glasgow, listed as a son aged 4 in an 1851 household at Cloghgaldanagh.", "/places/cloghgaldanagh.html"),
    "quality-derivative": ("Ann Taggard Glasgow’s parents come from a transcription of the register, not an image of the original page.", "/people/glasgow-1500.html"),
    "quality-secondary": ("William Glasgow Harkness, son of James Harkness and Margaret Glasgow, is identified from a published family history.", "/places/jacksonville-illinois.html"),
    "quality-tree-only": ("John Glasgow, elder present at Drimbolg in 1827: the place rests on a tree profile so far.", "/places/drimbolg.html"),
    "quality-unknown": ("Geillis Glasgow’s 1603 testament at Ardrossan is documented, but its source has not yet been classed.", "/places/ardrossan.html"),
    "link-profile-lead": ("Amelia Glasgow: a family-tree profile gives Ardrossan as her place of death.", "/places/ardrossan.html"),
    "link-kin-inferred-profile-lead": ("Mary J (Sinclair) Glasgow is placed at Cookstown only through her husband’s birthplace on the tree.", "/places/cookstown.html"),
    "link-traditional": ("John Glasgow (about 1735), by tradition a son of Hugh Glasgow.", "/places/county-londonderry-general.html"),
    "link-estimated": ("Hugh Glasgow’s family farm, described only as “not far from” Portglenone.", "/places/portglenone-reference.html"),
}

RECORD_LINK_ANCHORS = {term: "link-" + re.sub(r"[^a-z0-9]+", "-", term.casefold()).strip("-") for term in RECORD_EVIDENCE}
OTHER_WORDING_ANCHOR = "other-wording"
OTHER_WORDING_MEANING = ("The researcher’s own description of this record. It has not yet been matched to one of the "
                         "standard labels, so read it alongside the guide.")

# Curated badge texts used on place pages (record ``evidence`` values and
# source-quality values), mapped onto the guide. Each value is
# ``(guide anchor, text shown)``; a shown text of ``None`` keeps the stored
# text when it already begins with the standard label, and otherwise prefixes
# the label ("Probable · Highly probable same Irish cleric"). The stored
# values are never changed. Texts that do not map cleanly are in
# ``UNMAPPED_BADGE_TEXTS`` and are shown as written, linked to the guide's
# "Other wording" entry.
BADGE_TEXT_MAP: dict[str, tuple[str, str | None]] = {
    # Tree-profile leads
    "One-Tree profile lead": ("link-profile-lead", "Profile lead · One-Tree"),
    "Kin-inferred One-Tree profile lead": ("link-kin-inferred-profile-lead", "Kin-inferred profile lead · One-Tree"),
    "Recent WikiTree profile lead": ("link-profile-lead", "Profile lead · recent WikiTree profile"),
    "Profile location lead": ("link-profile-lead", "Profile lead · place only"),
    "Conflicted profile location lead": ("link-profile-lead", "Profile lead · place only, conflicting"),
    "One-Tree relational context": ("link-profile-lead", "Profile lead · One-Tree relationship context"),
    "Unsourced profile family": ("link-profile-lead", "Profile lead · unsourced profile family"),
    "Traditional / profile lead": ("link-traditional", "Traditional · also a profile lead"),
    "Contradicted profile lead": ("state-contradicted", "Contradicted · profile lead"),
    # Documented (key ``proved``): the stored text already starts with the term.
    **{text: ("state-proved", None) for text in (
        "Documented", "Documented occurrence", "Documented household", "Documented derivative register",
        "Documented occurrence / candidate cluster link", "Documented marriage", "Documented individual occurrence",
        "Documented church-office occurrence", "Documented associated person", "Documented parent",
        "Documented occurrence / probable repeated identity", "Documented baptism", "Documented death",
        "Documented grandchild", "Documented infant death", "Documented occurrence; surname identity unresolved",
        "Documented occurrence / identity unproved", "Documented later biographical locality",
        "Documented catalogue occurrence", "Documented witness", "Documented repeated occurrence / candidate cluster link",
        "Documented burgess-family context", "Documented marital boundary", "Documented testament",
        "Documented nuclear family", "Documented associated-lives record",
        "Documented parent-child record / candidate cluster link", "Documented marriage locality",
    )},
    # "Proved" is printed as the guide's word for the same grade.
    "Proved son": ("state-proved", "Documented son"),
    "Proved sibling": ("state-proved", "Documented sibling"),
    "Proved parent-child link": ("state-proved", "Documented parent-child link"),
    "Proved relationship": ("state-proved", "Documented relationship"),
    # Probable
    **{text: ("state-probable", None) for text in (
        "Probable", "Probable same Irish cleric", "Probable repeated identity", "Probable child",
        "Probable locality match", "Probable probate-profile match", "Probable profile match",
        "Probable repeated identity / candidate cluster link", "Probable duplicate probate index entry",
        "Highly probable same Irish cleric",
    )},
    # Possible
    **{text: ("state-possible", None) for text in (
        "Possible later-life identity", "Possible duplicate", "Possible namesake occurrence", "Possible identity",
        "Possible collateral",
    )},
    "Candidate identity": ("state-possible", "Possible · candidate identity"),
    "Candidate probate identification": ("state-possible", "Possible · candidate probate identification"),
    "Candidate paternal genetic relative": ("state-possible", "Possible · candidate paternal genetic relative"),
    # Working hypotheses (study scale)
    "Working household": ("tone-hypothesis", "Working hypothesis · household"),
    "Working adult": ("tone-hypothesis", "Working hypothesis · adult"),
    "Working offshoot": ("tone-hypothesis", "Working hypothesis · offshoot"),
    "Genetic placement hypothesis": ("tone-hypothesis", "Working hypothesis · genetic placement"),
    "Unresolved namesake": ("tone-unresolved", "Unresolved · namesake"),
    # Estimates
    "Approximate location": ("link-estimated", "Estimated · approximate location"),
    "Derived age evidence": ("link-estimated", "Estimated · derived from a stated age"),
    "Derived age and birthplace evidence": ("link-estimated", "Estimated · derived from a stated age and birthplace"),
}

# Place-page badge texts that describe the record or a stage of the work rather
# than a grade, or that mix two grades. Shown as written; listed for the owner.
UNMAPPED_BADGE_TEXTS = frozenset({
    "Probate index", "Undated probate index", "Unassigned same-name probate index", "Primary family record",
    "Primary record", "Contemporary Synod record", "Original valuation revision book", "Will and probate",
    "Derivative family record", "Original will and local history", "Later congregational history",
    "Published family identification", "Child's civil birth", "Court defendant", "Archive research lead",
    "Paternal genetic relatives", "Paternal genetic cluster report", "Paternal genetic identity lead",
    "Genetic collateral evidence", "Memorial-supported family", "Record-supported later profile",
    "Catalogue-only occurrence", "Strong probate-profile match", "Reconstructed parent generation",
    "Unproved profile reconstruction", "Unproved migration claim", "Documented with conflict",
    "Documented/working spouse", "Conflicted locality / candidate cluster link", "Unresolved / separate",
})


def anchor_for_state(key: str) -> str:
    return "state-" + canonical_key(key).replace("_", "-")


def guide_entries() -> dict[str, dict[str, str]]:
    """Every labelled entry of the guide, keyed by its anchor id."""
    entries = {anchor_for_state(key): dict(label=value["label"], meaning=value["meaning"]) for key, value in STATES.items()}
    entries.update({"quality-" + key.replace("_", "-"): dict(label=value["label"], meaning=value["meaning"])
                    for key, value in RECORD_QUALITY.items()})
    entries.update({RECORD_LINK_ANCHORS[term]: dict(label=term, meaning=text) for term, text in RECORD_EVIDENCE.items()})
    entries.update({"tone-" + key: dict(label=value["label"], meaning=value["meaning"]) for key, value in STUDY_TONES.items()})
    entries[OTHER_WORDING_ANCHOR] = dict(label="Other wording", meaning=OTHER_WORDING_MEANING)
    return entries


def _clean(value) -> str:
    return " ".join(unescape(str(value if value is not None else "")).split())


def _result(anchor: str, text: str, mapped: bool = True) -> dict[str, str | bool]:
    entry = guide_entries()[anchor]
    return dict(anchor=anchor, url=f"{GUIDE_URL}#{anchor}", label=entry["label"], meaning=entry["meaning"],
                text=text or entry["label"], mapped=mapped)


def _qualified(anchor: str, stored: str) -> str:
    term = guide_entries()[anchor]["label"]
    if not stored or stored.casefold() == term.casefold():
        return term
    if stored.casefold().startswith(term.casefold()):
        return stored
    return f"{term} · {stored}"


_PREFIXES = (
    ("documented", "state-proved"), ("strongly supported", "state-strongly-supported"), ("probable", "state-probable"),
    ("possible", "state-possible"), ("uncertain", "state-uncertain"), ("disputed", "state-disputed"),
    ("contradicted", "state-contradicted"), ("superseded", "state-superseded"), ("unassessed", "state-unmarked"),
    ("tree-marked dna confirmed", "state-dna-confirmed"), ("tree-marked confident", "state-confident"),
    ("tree-marked non-biological", "state-non-biological"),
)


def describe(value, kind: str | None = None) -> dict[str, str | bool]:
    """The reader's label for any stored evidence value.

    ``kind`` narrows the lookup: ``"state"`` (relationship and claim states,
    aliases and WikiTree status codes), ``"quality"`` (``source_quality``),
    ``"tone"`` (study-page scale) or ``None`` to accept any of them and the
    curated place-page badge texts. Returns ``anchor`` (id in the guide),
    ``url`` (guide link), ``label`` (the standard label), ``text`` (what to
    print: the standard label, with the curated qualifier when there is one),
    ``meaning`` (one line) and ``mapped`` (False for wording outside the scale).
    The stored value is never changed and its grade is never raised.
    """
    raw = _clean(value)
    folded = raw.casefold()
    snake = folded.replace(" ", "_")
    if kind == "tone":
        tone = STUDY_TONES.get(snake, STUDY_TONES["unresolved"])
        return _result("tone-" + (snake if snake in STUDY_TONES else "unresolved"), tone["label"])
    if kind in (None, "quality"):
        if raw in RECORD_QUALITY or (kind == "quality" and not raw):
            key = raw or "unknown"
            return _result("quality-" + key.replace("_", "-"), RECORD_QUALITY[key]["label"])
        for key, item in RECORD_QUALITY.items():
            if folded == item["label"].casefold():
                return _result("quality-" + key.replace("_", "-"), item["label"])
    if kind in (None, "state"):
        if raw in TREE_DATA_STATUS or snake in STATES or folded in ALIASES or folded.replace("_", "-") in ALIASES \
                or (kind == "state" and not raw):
            key = canonical_key(raw)
            return _result(anchor_for_state(key), STATES[key]["label"])
        if kind == "state":
            key = canonical_key(raw)
            return _result(anchor_for_state(key), STATES[key]["label"])
    for term, anchor in RECORD_LINK_ANCHORS.items():
        if folded == term.casefold():
            return _result(anchor, term)
    mapped = BADGE_TEXT_MAP.get(raw) or next((v for k, v in BADGE_TEXT_MAP.items() if k.casefold() == folded), None)
    if mapped:
        anchor, shown = mapped
        return _result(anchor, shown or _qualified(anchor, raw))
    if raw in UNMAPPED_BADGE_TEXTS or not raw:
        return _result(OTHER_WORDING_ANCHOR, raw or "Unclassified", mapped=False)
    if folded.startswith("proved "):
        return _result("state-proved", "Documented " + raw[len("proved "):])
    for prefix, anchor in _PREFIXES:
        if folded == prefix or folded.startswith(prefix + " ") or folded.startswith(prefix + ";") \
                or folded.startswith(prefix + " ·"):
            return _result(anchor, raw)
    return _result(OTHER_WORDING_ANCHOR, raw, mapped=False)


def _slug(value) -> str:
    return re.sub(r"[^a-z0-9]+", "-", _clean(value or "unknown").casefold()).strip("-") or "unknown"


def label_html(value, kind: str | None = None, *, css: str = "evidence-badge", text: str | None = None) -> str:
    """A printed label: the reader's words, linked to the label's guide entry.

    The outer element keeps the classes used today (``evidence-badge
    evidence-<stored value>``) so existing styles still apply; the meaning is
    the link's tooltip. ``text`` overrides the printed words only.
    """
    info = describe(value, kind)
    shown = text or str(info["text"])
    return (f'<span class="{escape(css, quote=True)} evidence-{escape(_slug(value), quote=True)}">'
            f'<a class="ev-label-link" href="{escape(str(info["url"]), quote=True)}" '
            f'title="{escape(str(info["meaning"]), quote=True)}">{escape(shown)}</a></span>')


GUIDE_LINK_TEXT = "How to read the labels"


def guide_link_html(text: str = GUIDE_LINK_TEXT, anchor: str = "") -> str:
    """A short "How to read the labels" link for any block of labels."""
    href = GUIDE_URL + (f"#{anchor}" if anchor else "")
    return f'<p class="evidence-guide-link"><a href="{escape(href, quote=True)}">{escape(text)}</a></p>'


def as_json() -> dict:
    return {
        "version": VERSION,
        "guide": {"url": GUIDE_URL, "label": GUIDE_LABEL},
        "states": STATES,
        "aliases": ALIASES,
        "tree_data_status": TREE_DATA_STATUS,
        "record_quality": RECORD_QUALITY,
        "record_evidence": RECORD_EVIDENCE,
        "study_tones": STUDY_TONES,
        "question_status": QUESTION_STATUS,
        "question_fields": QUESTION_FIELDS,
        "not_yet_identified": NOT_YET_IDENTIFIED,
        "cluster_note": CLUSTER_NOTE,
        "guide_entries": guide_entries(),
        "badge_text_map": {text: dict(anchor=anchor, text=shown) for text, (anchor, shown) in BADGE_TEXT_MAP.items()},
        "unmapped_badge_texts": sorted(UNMAPPED_BADGE_TEXTS),
    }


def json_text() -> str:
    return json.dumps(as_json(), ensure_ascii=False, indent=1, sort_keys=False) + "\n"


def write_json(path: Path = JSON_PATH) -> bool:
    text = json_text()
    if path.exists() and path.read_text(encoding="utf-8") == text:
        return False
    path.write_text(text, encoding="utf-8")
    return True


if __name__ == "__main__":
    print(json.dumps({"evidence_labels_json_written": write_json()}))
