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

from html import unescape
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
    "resolve": "What would resolve this",
    "record": "Record to request or inspect",
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
    "Research clusters, households and study groups organise related records and hypotheses. "
    "Being placed in the same cluster does not prove that people were related."
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
