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

WEB = ROOT / "www"
TEMPLATE = WEB / "about/index.html"
OUTPUT = WEB / "evidence/index.html"
TITLE = f"{ev.GUIDE_LABEL} · Glasgow surname archive"
DESCRIPTION = ("What the evidence and confidence labels on the Glasgow surname archive mean: documented, "
               "supported, probable and possible links, tree marks, record quality, estimates and research clusters.")
CSS = f'<link rel="stylesheet" href="/assets/research/evidence.css?v={ev.VERSION}">'

STATE_ORDER = ("proved", "strongly_supported", "probable", "possible", "uncertain", "disputed", "contradicted",
               "superseded", "unmarked", "confident", "dna_confirmed", "non_biological")


def _label_chip(key: str) -> str:
    state = ev.STATES[key]
    return (f'<span class="ev-label ev-family-{state["family"]}"><b aria-hidden="true">{escape(state["glyph"])}</b>'
            f'{escape(state["label"])}</span>')


def _state_rows(keys) -> str:
    return "".join(
        f'<tr id="state-{key.replace("_", "-")}"><td>{_label_chip(key)}<span class="ev-key">{escape(key)}</span></td>'
        f'<td>{escape(ev.STATES[key]["meaning"])}</td></tr>'
        for key in keys
    )


def main_html() -> str:
    research = [k for k in STATE_ORDER if ev.STATES[k]["source"] != "tree"]
    tree = [k for k in STATE_ORDER if ev.STATES[k]["source"] == "tree"]
    table_head = '<thead><tr><th scope="col">Label</th><th scope="col">What it means</th></tr></thead>'
    quality = "".join(
        f'<tr id="quality-{key.replace("_", "-")}"><td><span class="ev-label">{escape(value["label"])}</span></td><td>{escape(value["meaning"])}</td></tr>'
        for key, value in ev.RECORD_QUALITY.items()
    )
    record_terms = "".join(f'<dt>{escape(term)}</dt><dd>{escape(text)}</dd>' for term, text in ev.RECORD_EVIDENCE.items())
    dates = "".join(f'<dt>{escape(term)}</dt><dd>{escape(text)}</dd>' for term, text in ev.DATE_PLACE_NOTES)
    tones = "".join(
        f'<dt>{escape(value["label"])}</dt><dd>{escape(value["meaning"])}</dd>' for value in ev.STUDY_TONES.values()
    )
    questions = "".join(
        f'<dt>{escape(label)}</dt><dd>{escape(text)}</dd>' for label, text in (
            (ev.QUESTION_STATUS["open"], "Still being researched. The question shows what would resolve it and which record to request or inspect."),
            (ev.QUESTION_STATUS["partly_answered"], "Part of the question is settled; the remaining part stays open."),
            (ev.QUESTION_STATUS["answered"], "Settled by the records named in the task. Kept so that the reasoning stays visible."),
            (ev.QUESTION_FIELDS["resolve"], "The finding that would settle the question, as stated in the maintained research."),
            (ev.QUESTION_FIELDS["record"], "The particular register, file or index entry to consult next."),
            (ev.NOT_YET_IDENTIFIED, "The research has not yet named a deciding finding or record. The site does not fill the gap with a guess."),
        )
    )
    return (
        '<main class="ev-page">'
        '<header class="g-editorial-hero"><p class="g-eyebrow">Evidence and confidence</p>'
        f'<h1>{escape(ev.GUIDE_LABEL)}</h1>'
        '<p class="ev-intro">Every relationship, date and place on this site carries a label saying how well the records support it. '
        'The same words are used in the catalogue, the person dossiers, the family atlas and the study pages. '
        'The label is always written out, so no state depends on colour alone. The labels describe evidence; '
        'they are not a verdict on anyone’s family tradition.</p></header>'
        '<section class="ev-section" id="relationship-labels" aria-labelledby="relationship-labels-title">'
        '<h2 id="relationship-labels-title">Relationship and claim labels</h2>'
        '<p>These labels come from this project’s own review of the records. They run from strongest to weakest, followed by conflicts. '
        '“Documented” is used only when a cited record states the relationship or fact directly.</p>'
        f'<div class="ev-table-wrap"><table class="ev-table">{table_head}<tbody>{_state_rows(research)}</tbody></table></div></section>'
        '<section class="ev-section" id="tree-marks" aria-labelledby="tree-marks-title">'
        '<h2 id="tree-marks-title">Marks copied from the family tree</h2>'
        '<p>Many links come from WikiTree profiles. When a contributor has marked a parent link, the mark is shown with the word “Tree” so that it is not mistaken for this project’s assessment. '
        'A link with no mark is called unassessed.</p>'
        f'<div class="ev-table-wrap"><table class="ev-table">{table_head}<tbody>{_state_rows(tree)}</tbody></table></div></section>'
        '<section class="ev-section" id="record-quality" aria-labelledby="record-quality-title">'
        '<h2 id="record-quality-title">Record quality</h2>'
        '<p>Each source is classed by how close it is to the original event. The class describes the source, not the conclusion drawn from it.</p>'
        f'<div class="ev-table-wrap"><table class="ev-table"><thead><tr><th scope="col">Class</th><th scope="col">What it means</th></tr></thead><tbody>{quality}</tbody></table></div>'
        '<h3>Record associations</h3><p>Catalogue record rows use these terms for the link between a person and a record.</p>'
        f'<dl class="ev-dl">{record_terms}</dl></section>'
        '<section class="ev-section" id="dates-and-places" aria-labelledby="dates-title">'
        '<h2 id="dates-title">Estimated dates and places</h2>'
        '<p>A date or place without a record behind it is marked as an estimate or a limit. An estimate is a working value; it can move when a record is found.</p>'
        f'<dl class="ev-dl">{dates}</dl></section>'
        '<section class="ev-section" id="clusters" aria-labelledby="clusters-title">'
        '<h2 id="clusters-title">Research clusters are not proof of kinship</h2>'
        f'<p class="ev-note">{escape(ev.CLUSTER_NOTE)} A family atlas branch or a visual root is a layout choice, not a shared ancestor.</p>'
        '<h3>Study page scale</h3><p>Family and locality studies use a shorter four-step scale for their clusters and links.</p>'
        f'<dl class="ev-dl">{tones}</dl></section>'
        '<section class="ev-section" id="open-questions-guide" aria-labelledby="questions-title">'
        '<h2 id="questions-title">Open research questions</h2>'
        '<p>Open questions on the <a href="/research/#open-questions">research page</a> and in person dossiers use these fields.</p>'
        f'<dl class="ev-dl">{questions}</dl></section>'
        '<section class="ev-section" id="corrections" aria-labelledby="corrections-title">'
        '<h2 id="corrections-title">If a label looks wrong</h2>'
        '<p>Send the profile, the exact claim and the record that bears on it through the <a href="/feedback/">correction form</a>. '
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
    page = re.sub(r'(<div class="g-crumbs"><a href="/">Glasgow archive</a><i>/</i><strong>).*?(</strong>)',
                  lambda m: m[1] + escape(ev.GUIDE_LABEL) + m[2], page, count=1, flags=re.S)
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
    return {"evidence_page_written": changed, "evidence_labels_json_written": ev.write_json()}


if __name__ == "__main__":
    print(json.dumps(build()))
