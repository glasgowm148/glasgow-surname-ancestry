#!/usr/bin/env python3
"""Build /evidence/ ("How to read the evidence") from the shared vocabulary.

The page shell, including the unchanged ``<nav class="g-nav">`` rail, is copied
from ``www/about/index.html``; only the title, description, breadcrumb, body
path and ``<main>`` content are replaced. The vocabulary JSON mirror is
refreshed at the same time. Re-running produces identical output.
"""
from __future__ import annotations

from html import escape
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import evidence_labels as ev  # noqa: E402
from repair_primary_navigation import render_breadcrumbs  # noqa: E402
from site_identity import SITE_NAME, page_title  # noqa: E402

WEB = ROOT / "www"
TEMPLATE = WEB / "about/index.html"
OUTPUT = WEB / "evidence/index.html"
TITLE = page_title(ev.GUIDE_LABEL)
DESCRIPTION = (f"What the evidence and confidence labels on the {SITE_NAME} site mean: documented, "
               "supported, probable and possible links, tree marks, record quality, estimates and possible groups.")
CSS = f'<link rel="stylesheet" href="/assets/research/evidence.css?v={ev.VERSION}">'
CSS_SOURCE = ROOT / "tools/evidence.css"
CSS_TARGET = WEB / "assets/research/evidence.css"

STATE_ORDER = ("proved", "strongly_supported", "probable", "possible", "uncertain", "disputed", "contradicted",
               "superseded", "unmarked", "confident", "dna_confirmed", "non_biological")


RECORD_LINK_BASIS = {
    "Documented": "A record that names the person at this event, checked as belonging to them.",
    "Probable": "A record whose name, place and date fit this person better than anyone else known.",
    "Profile lead": "A place or date given on a family-tree profile, not yet matched to a record.",
    "Kin-inferred profile lead": "A relative’s tree profile, such as a child’s birthplace used to place a parent.",
    "Traditional": "A family story or a later written account, with no contemporary record found.",
    "Estimated": "Arithmetic from other records, such as an age at death or a census age, or a description such as “near” a town.",
}


def _label_chip(key: str) -> str:
    state = ev.STATES[key]
    return (f'<span class="ev-label ev-family-{state["family"]}"><b aria-hidden="true">{escape(state["glyph"])}</b>'
            f'{escape(state["label"])}</span>')


def _example(anchor: str) -> str:
    example = ev.GUIDE_EXAMPLES.get(anchor)
    if not example:
        return '<dt>Example</dt><dd class="ev-no-example">Not used on any published page at present.</dd>'
    text, url = example
    return f'<dt>Example</dt><dd>{escape(text)} <a href="{escape(url, quote=True)}">See the page</a></dd>'


def _entry(anchor: str, chip: str, meaning: str, basis: str = "", key: str = "") -> str:
    """One label in the guide: the label, its meaning, what it rests on and a real example.

    Internal keys stay out of the visible text; they are kept as ``data-key``.
    """
    data_key = f' data-key="{escape(key, quote=True)}"' if key else ""
    basis_html = f'<dt>Usually rests on</dt><dd>{escape(basis)}</dd>' if basis else ""
    return (f'<article class="ev-entry" id="{anchor}"{data_key}><h3>{chip}</h3>'
            f'<p class="ev-meaning">{escape(meaning)}</p><dl class="ev-facts">{basis_html}{_example(anchor)}</dl></article>')


def _state_entries(keys) -> str:
    return "".join(
        _entry(ev.anchor_for_state(key), _label_chip(key), ev.STATES[key]["meaning"], ev.STATE_BASIS.get(key, ""), key)
        for key in keys
    )


def _ladder(keys) -> str:
    items = "".join(
        f'<li><a href="#{ev.anchor_for_state(key)}">{escape(ev.STATES[key]["label"])}</a></li>' for key in keys
    )
    return f'<ol class="ev-ladder" aria-label="From strongest to weakest">{items}</ol>'


def _other_wording_rows() -> str:
    entries = ev.guide_entries()
    rows = "".join(
        f'<tr><td>{escape(text)}</td><td><a href="#{anchor}">{escape(entries[anchor]["label"])}</a></td></tr>'
        for text, (anchor, _shown) in sorted(ev.BADGE_TEXT_MAP.items(), key=lambda item: item[0].casefold())
        if text.casefold() != entries[anchor]["label"].casefold()
    )
    return rows


def _tone_state(key: str) -> str:
    return "uncertain" if key == "unresolved" else ev.STUDY_TONES[key]["state"]


def main_html() -> str:
    research = [k for k in STATE_ORDER if ev.STATES[k]["source"] != "tree"]
    tree = [k for k in STATE_ORDER if ev.STATES[k]["source"] == "tree"]
    quality = "".join(
        _entry("quality-" + key.replace("_", "-"), f'<span class="ev-label">{escape(value["label"])}</span>', value["meaning"], key=key)
        for key, value in ev.RECORD_QUALITY.items()
    )
    record_terms = "".join(
        _entry(ev.RECORD_LINK_ANCHORS[term], f'<span class="ev-label">{escape(term)}</span>', text, RECORD_LINK_BASIS.get(term, ""))
        for term, text in ev.RECORD_EVIDENCE.items()
    )
    dates = "".join(f'<dt>{escape(term)}</dt><dd>{escape(text)}</dd>' for term, text in ev.DATE_PLACE_NOTES)
    tones = "".join(
        f'<dt id="tone-{escape(key, quote=True)}">{escape(value["label"])}</dt><dd>{escape(value["meaning"])} '
        f'Read it as <a href="#{ev.anchor_for_state(_tone_state(key))}">{escape(ev.STATES[_tone_state(key)]["label"])}</a>.</dd>'
        for key, value in ev.STUDY_TONES.items()
    )
    questions = "".join(
        f'<dt>{escape(label)}</dt><dd>{escape(text)}</dd>' for label, text in (
            (ev.QUESTION_STATUS["open"], "Still being researched. The question shows what would resolve it and which record to request or inspect."),
            (ev.QUESTION_STATUS["partly_answered"], "Part of the question is settled; the remaining part stays open."),
            (ev.QUESTION_STATUS["answered"], "Settled by the records named in the task. Kept so that the reasoning stays visible."),
            (ev.QUESTION_FIELDS["resolve"], "The finding that would settle the question, as stated in the research."),
            (ev.QUESTION_FIELDS["record"], "The particular register, file or index entry to consult next."),
            (ev.NOT_YET_IDENTIFIED, "The research has not yet named a deciding finding or record. The site does not fill the gap with a guess."),
        )
    )
    return (
        '<main class="ev-page">'
        '<header class="g-editorial-hero"><p class="g-eyebrow">Evidence and confidence</p>'
        f'<h1>{escape(ev.GUIDE_LABEL)}</h1>'
        '<p class="ev-intro">Every relationship, date and place on this site carries a label saying how well the records support it. '
        'The same words are used on person pages, family studies, place pages and the people catalogue. '
        'Select any label on the site to come back to its entry here. '
        'The labels describe evidence; they are not a verdict on anyone’s family tradition.</p></header>'
        '<nav class="ev-section ev-contents" aria-labelledby="ev-glance-title"><h2 id="ev-glance-title">The labels at a glance</h2>'
        '<p>From strongest to weakest, then conflicts:</p>'
        f'{_ladder(research)}'
        '<p>Marks copied from the family tree: '
        + " · ".join(f'<a href="#{ev.anchor_for_state(k)}">{escape(ev.STATES[k]["label"])}</a>' for k in tree)
        + '. Also: <a href="#record-links">how a record is linked to a person</a>, <a href="#record-quality">record quality</a>, '
        '<a href="#dates-and-places">estimated dates and places</a> and <a href="#other-wording">other wording</a>.</p></nav>'
        '<section class="ev-section" id="relationship-labels" aria-labelledby="relationship-labels-title">'
        '<h2 id="relationship-labels-title">Labels for facts and relationships</h2>'
        '<h3 id="relationship-probability">Father–child probability estimates</h3>'
        '<p>Confident: 90–99%; probable: 60–89%; possible: 30–59%; speculative or uncertain: 1–29%. '
        'Each reviewed father link has an individual percentage estimate, based on its evidence, identity match and alternatives. '
        'The categories are guides; the percentage is a judgment of belief, not a measured frequency. '
        'Unassessed and conflicting links remain unrated. No relationship is assigned 100%. '
        'A documented relationship can apply only to the person in a particular record: a separate uncertain identity stays uncertain. '
        'WikiTree contributor marks alone do not receive a percentage. '
        'The individual estimate and its reasoning are retained with the relationship data.</p>'
        '<p>These labels come from this project’s own review of the records. '
        '“Documented” is used only when a cited record states the relationship or fact directly.</p>'
        f'<div class="ev-entries">{_state_entries(research)}</div></section>'
        '<section class="ev-section" id="tree-marks" aria-labelledby="tree-marks-title">'
        '<h2 id="tree-marks-title">Marks copied from the family tree</h2>'
        '<p>Many links come from WikiTree profiles. When a contributor has marked a parent link, the mark is shown with the word “Tree” so that it is not mistaken for this project’s assessment. '
        'A link with no mark is called unassessed.</p>'
        f'<div class="ev-entries">{_state_entries(tree)}</div></section>'
        '<section class="ev-section" id="record-links" aria-labelledby="record-links-title">'
        '<h2 id="record-links-title">How a record is linked to a person</h2>'
        '<p>Place pages, record lists and the catalogue show how sure the research is that a record concerns this person. '
        'Rows marked Possible or Contradicted use the meanings <a href="#state-possible">above</a>.</p>'
        f'<div class="ev-entries">{record_terms}</div></section>'
        '<section class="ev-section" id="record-quality" aria-labelledby="record-quality-title">'
        '<h2 id="record-quality-title">Record quality</h2>'
        '<p>Each source is classed by how close it is to the original event. The class describes the source, not the conclusion drawn from it: '
        'a documented fact can rest on a source that has not yet been classed.</p>'
        f'<div class="ev-entries">{quality}</div></section>'
        '<section class="ev-section" id="dates-and-places" aria-labelledby="dates-title">'
        '<h2 id="dates-title">Estimated dates and places</h2>'
        '<p>A date or place without a record behind it is marked as an estimate or a limit. An estimate is a working value; it can move when a record is found.</p>'
        f'<dl class="ev-dl">{dates}</dl></section>'
        '<section class="ev-section" id="clusters" aria-labelledby="clusters-title">'
        '<h2 id="clusters-title">Being in the same study does not prove a family relationship</h2>'
        f'<p class="ev-note">{escape(ev.CLUSTER_NOTE)} The tree layout alone does not establish a shared ancestor.</p>'
        '<h3 id="study-scale">Labels used in family studies</h3><p>Family and locality studies use a shorter four-step scale for the relationships being investigated.</p>'
        f'<dl class="ev-dl">{tones}</dl></section>'
        f'<section class="ev-section" id="{ev.OTHER_WORDING_ANCHOR}" aria-labelledby="other-wording-title">'
        '<h2 id="other-wording-title">Other wording</h2>'
        '<p>Some record rows keep the researcher’s own description, such as “Probate index” or “Court defendant”. '
        'These describe the record or the stage of the work. They have not yet been matched to one of the standard labels, '
        'so read them alongside the entries above.</p>'
        '<details class="ev-wording"><summary>Wordings you may see, and the standard label each one is filed under</summary>'
        '<div class="ev-table-wrap"><table class="ev-table"><thead><tr><th scope="col">Wording on the page</th><th scope="col">Standard label</th></tr></thead>'
        f'<tbody>{_other_wording_rows()}</tbody></table></div></details></section>'
        '<section class="ev-section" id="open-questions-guide" aria-labelledby="questions-title">'
        '<h2 id="questions-title">Open research questions</h2>'
        '<p>Open questions on the <a href="/research/#open-questions">research page</a> and in person pages use these fields.</p>'
        f'<dl class="ev-dl">{questions}</dl></section>'
        '<section class="ev-section" id="corrections" aria-labelledby="corrections-title">'
        '<h2 id="corrections-title">If a label looks wrong</h2>'
        '<p>Send the profile, the detail to correct and the record that bears on it through the <a href="/feedback/">correction form</a>. '
        'A label changes only when the evidence does.</p>'
        f'<p>Machine-readable vocabulary: <a href="/assets/research/evidence-labels.json">evidence-labels.json</a>.</p></section>'
        '</main>'
    )


def render(template: str) -> str:
    page = template
    page = re.sub(r"<title>.*?</title>", lambda _: f"<title>{escape(TITLE)}</title>", page, count=1, flags=re.S)
    page = re.sub(r'<meta name="description" content="[^"]*">',
                  lambda _: f'<meta name="description" content="{escape(DESCRIPTION, quote=True)}">', page, count=1)
    page = page.replace('data-g-path="/about/index.html"', 'data-g-path="/evidence/index.html"', 1)
    page = page.replace("g-kind-about", "g-kind-evidence", 1)
    # One breadcrumb (Home / About / How to read the evidence), whatever root
    # label the About template carries (an older site name before the identity
    # pass, "Home" after it).
    page = re.sub(r'<div class="g-crumbs">.*?</div>',
                  lambda _: render_breadcrumbs(Path("evidence/index.html"), escape(ev.GUIDE_LABEL)), page, count=1, flags=re.S)
    page = re.sub(r"<main\b[^>]*>.*?</main>", lambda _: main_html(), page, count=1, flags=re.S)
    if "/assets/research/evidence.css" not in page:
        page = page.replace("</head>", CSS + "</head>", 1)
    return page


def nav_rail(page: str) -> str:
    match = re.search(r'<nav class="g-nav".*?</nav>', page, flags=re.S)
    return match[0] if match else ""


def build() -> dict:
    template = TEMPLATE.read_text(encoding="utf-8")
    page = render(template)
    if nav_rail(page) != nav_rail(template):
        raise ValueError("The copied navigation rail changed")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    changed = not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != page
    if changed:
        OUTPUT.write_text(page, encoding="utf-8")
    return {"evidence_page_written": changed, "evidence_labels_json_written": ev.write_json(),
            "evidence_css_written": install_css()}


def install_css(target: Path = CSS_TARGET) -> bool:
    """Copy the maintained stylesheet ``tools/evidence.css`` into the site."""
    text = CSS_SOURCE.read_text(encoding="utf-8")
    if target.exists() and target.read_text(encoding="utf-8") == text:
        return False
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    return True


if __name__ == "__main__":
    print(json.dumps(build()))
