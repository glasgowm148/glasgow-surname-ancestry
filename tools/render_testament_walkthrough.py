"""Render source-image reading trails; never manufacture manuscript imagery."""

from functools import lru_cache
from html import escape
from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "research/transcriptions/walkthroughs"
LETTERFORM_DATA = ROOT / "research/transcriptions/letterforms"
STATUSES = {"explicit": "Stated in the record", "uncertain": "Reading uncertain", "comparison": "Identity comparison"}


def e(value):
    return escape(str(value), quote=True)


@lru_cache(maxsize=None)
def load_walkthrough(ident):
    if not re.fullmatch(r"[a-z0-9-]+", ident):
        raise ValueError("Invalid testament identifier")
    path = DATA / f"{ident}.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


@lru_cache(maxsize=None)
def load_letterforms(ident):
    if not re.fullmatch(r"[a-z0-9-]+", ident):
        raise ValueError("Invalid testament identifier")
    path = LETTERFORM_DATA / f"{ident}.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


@lru_cache(maxsize=1)
def load_letterform_reference():
    path = LETTERFORM_DATA / "reference.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def image_url(step):
    url = step["image"]
    if not re.fullmatch(r"/assets/research/testament-crops/[A-Za-z0-9_.-]+\.(?:jpg|jpeg|png|webp)", url):
        raise ValueError("A reading trail must use a local manuscript crop")
    return url


def letterform_image_url(url):
    if not isinstance(url, str) or not re.fullmatch(r"/assets/research/[A-Za-z0-9_./-]+\.(?:jpg|jpeg|png|webp)", url):
        raise ValueError("A letterform study must use a local research image")
    return url


def svg_path(path):
    # Permit only ordinary SVG path commands and numeric coordinate syntax.
    if not isinstance(path, str) or len(path) > 4000 or not re.fullmatch(r"[MmLlHhVvCcSsQqTtAaZz0-9 ,.\-+Ee]+", path):
        raise ValueError("Invalid letterform SVG path")
    return path


def number(value, fallback=0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def study_region(region, width, height):
    if not isinstance(region, list) or len(region) != 4:
        raise ValueError("A letterform region requires four coordinates")
    x, y, w, h = (number(value) for value in region)
    x, y = max(0, x), max(0, y)
    w, h = min(w, width - x), min(h, height - y)
    if w <= 0 or h <= 0:
        raise ValueError("Invalid letterform crop region")
    return x, y, w, h


def safe_reference_url(url):
    return url if isinstance(url, str) and re.fullmatch(r"https://[^\s<>\"]+", url) else ""


def letterform_studies_markup(ident):
    try:
        from tools.render_letterform_desk import render_letterform_desk
    except ModuleNotFoundError:
        from render_letterform_desk import render_letterform_desk
    return render_letterform_desk(ident, load_letterforms(ident))


def step_id(step, number):
    ident = str(step.get("id", ""))
    return ident if re.fullmatch(r"[a-z0-9-]+", ident) else f"passage-{number}"


def preview_walkthrough(ident, original=None):
    data = load_walkthrough(ident)
    if not data or not data.get("steps"):
        if original:
            return (f'<a class="tx-preview" href="/research/transcriptions/{e(ident)}/" tabindex="-1" aria-hidden="true">'
                    f'<img src="{e(image_url(original))}" alt="" loading="lazy" decoding="async">'
                    '<span>Original supplied; fresh reading pending</span></a>')
        return '<div class="tx-preview-missing">Illustrated walkthrough not yet prepared</div>'
    first = data["steps"][0]
    return (f'<a class="tx-preview" href="/research/transcriptions/{e(ident)}/" tabindex="-1" aria-hidden="true">'
            f'<img src="{e(image_url(first))}" alt="" loading="lazy" decoding="async">'
            f'<span>{len(data["steps"])} illustrated passages</span></a>')


def render_supplied_original(item, sources):
    original = item.get("original_preview")
    figure = ""
    if original:
        url = image_url(original)
        caption = original.get("page_label", item.get("record", "Supplied original"))
        figure = (f'<figure class="tx-evidence-figure"><a href="{e(url)}" '
                  'aria-label="Enlarge supplied original page">'
                  f'<div class="tx-image-frame"><img src="{e(url)}" '
                  f'alt="{e(original.get("alt", caption))}" loading="lazy" decoding="async"></div></a>'
                  f'<figcaption>{e(caption)}. Click to enlarge. '
                  '&copy; Crown copyright, National Records of Scotland / ScotlandsPeople. '
                  'Unannotated source preview, not a completed transcription.</figcaption></figure>')
    files = "".join(f'<li><code>{e(path)}</code></li>' for path in sources)
    return ('<section class="tx-image-pending"><p class="r-kicker">Original supplied</p>'
            '<h2>The manuscript is available.</h2>'
            '<p>The original PDF has been matched to this record. A fresh transcription and '
            'word-by-word illustrated reading remain to be prepared; the earlier assessment '
            'below is preserved, not presented as newly verified.</p>' + figure
            + '<h3>Supplied local source file</h3><ul>' + files + '</ul>'
            '<p>The full PDF remains in the local research archive.</p></section>')


def marks_markup(marks):
    rects, key = [], []
    for number, mark in enumerate(marks, 1):
        kind = mark.get("kind", "name")
        if kind not in {"name", "relationship", "uncertain"}:
            kind = "name"
        x = max(0, min(100, float(mark["x"])))
        y = max(0, min(100, float(mark["y"])))
        w = max(0, min(100 - x, float(mark["w"])))
        h = max(0, min(100 - y, float(mark["h"])))
        selected = " is-selected" if number == 1 else ""
        rects.append(f'<rect class="tx-mark-{kind}{selected}" data-tx-mark="{number}" x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" '
                     'rx="0.3" vector-effect="non-scaling-stroke"/>')
        pressed = "true" if number == 1 else "false"
        key.append(f'<li><button type="button" data-tx-focus="{number}" aria-pressed="{pressed}">'
                   f'<span class="tx-key-number tx-mark-{kind}">{number}</span><span>{e(mark["label"])}</span></button></li>')
    overlay = ('<svg class="tx-highlight-layer" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">'
               + "".join(rects) + '</svg>')
    legend = ('<p class="tx-outline-help">Choose a phrase to locate it in the manuscript. '
              'Only its outline is shown, so overlapping strokes stay readable.</p>'
              '<ol class="tx-crop-key" aria-label="Choose the outlined phrase">' + "".join(key) + '</ol>') if marks else ""
    return overlay, legend


def word_studies_markup(step):
    studies = [(number, mark) for number, mark in enumerate(step.get("marks", []), 1)]
    studies += [(None, word) for word in step.get("word_studies", [])]
    cards = []
    width = float(step.get("image_width", 100))
    height = float(step.get("image_height", 100))
    for number, word in studies:
        analysis = word.get("analysis", {})
        if not analysis:
            continue
        x = max(0, min(100, float(word["x"]))) * width / 100
        y = max(0, min(100, float(word["y"]))) * height / 100
        w = max(0, min(width - x, float(word["w"]) * width / 100))
        h = max(0, min(height - y, float(word["h"]) * height / 100))
        if w <= 0 or h <= 0:
            continue
        reading = analysis.get("reading", word.get("label", "Unresolved detail"))
        label = f"Phrase {number:02}" if number is not None else "Unresolved detail"
        features = "".join(f'<li>{e(feature)}</li>' for feature in analysis.get("features", []))
        comparison = (f'<p class="tx-word-comparison"><strong>Compare in this hand:</strong> '
                      f'{e(analysis["comparison"])}</p>') if analysis.get("comparison") else ""
        uncertainty = (f'<p class="tx-word-caution"><strong>Reading limits:</strong> '
                       f'{e(analysis["uncertainty"])}</p>') if analysis.get("uncertainty") else ""
        locate = (f'<button type="button" class="tx-word-locate" data-tx-focus="{number}" '
                  f'aria-pressed="{"true" if number == 1 else "false"}">Show in the passage</button>') if number is not None else ""
        cards.append('<article class="tx-word-card"><header>'
                     f'<p class="r-kicker">{label}</p><h4>{e(reading)}</h4>'
                     f'<p class="tx-word-expansion">{e(analysis.get("expansion", ""))}</p></header>'
                     '<div class="tx-word-detail"><figure class="tx-word-sample">'
                     f'<svg class="tx-word-image" viewBox="{x:g} {y:g} {w:g} {h:g}" role="img" '
                     f'aria-label="Enlarged original handwriting: {e(reading)}">'
                     f'<image href="{e(image_url(step))}" width="{width:g}" height="{height:g}" preserveAspectRatio="none"/>'
                     '</svg><figcaption>Magnified from the same manuscript image. No letters have been redrawn.</figcaption>'
                     + locate + '</figure><div class="tx-letterforms"><h5>Look at the strokes</h5><ol>'
                     + features + '</ol>' + comparison + uncertainty + '</div></div></article>')
    if not cards:
        return ""
    return ('<section class="tx-word-studies"><div class="tx-word-studies-heading">'
            '<p class="r-kicker">Slow reading</p><h3>Inspect the words, not just the conclusion.</h3>'
            '<p>Compare the original strokes with the proposed reading. Tall or trailing strokes from neighbouring '
            'lines may enter a sample; the notes distinguish what is visible from what remains uncertain.</p>'
            '</div>' + "".join(cards) + '</section>')


def render_walkthrough(review):
    data = load_walkthrough(review["id"])
    if not data or not data.get("steps"):
        return ('<section class="tx-image-pending"><p class="r-kicker">Image coverage</p>'
                '<h2>No illustrated reading is available for this source yet.</h2>'
                '<p>The saved text remains below. Missing manuscript evidence is not replaced with a reconstructed image.</p></section>')
    steps = data["steps"]
    ids = {step.get("id"): step_id(step, n) for n, step in enumerate(steps, 1)}
    people = []
    for person in data.get("people", []):
        status = person.get("status", "uncertain")
        if status not in STATUSES:
            status = "uncertain"
        anchor = ids.get(person.get("evidence_step"), step_id(steps[0], 1))
        profile = str(person.get("profile_id") or "")
        wiki = (f'<a class="tx-person-profile" href="https://www.wikitree.com/wiki/{e(profile)}">'
                f'{e(profile)} on WikiTree &nearr;</a>') if re.fullmatch(r"[A-Za-z]+-\d+", profile) else ""
        evidence_study = str(person.get("evidence_study", ""))
        target = f'tx-letterform-{review["id"]}-{evidence_study}' if re.fullmatch(r"[a-z0-9-]+", evidence_study) else f'passage-{anchor}'
        people.append(f'<li class="tx-named-person tx-person-{status}"><a href="#{e(target)}">'
                      f'<strong>{e(person["name"])}</strong><span>{e(person.get("role", ""))}</span>'
                      f'<small>{STATUSES[status]} <span aria-hidden="true">&darr;</span></small></a>{wiki}</li>')
    nav = "".join(f'<a href="#passage-{e(step_id(step, n))}" data-tx-step="passage-{e(step_id(step, n))}">'
                  f'<span>{n:02}</span>{e(step["title"])}</a>' for n, step in enumerate(steps, 1))
    passages = []
    for number, step in enumerate(steps, 1):
        ident = step_id(step, number)
        url = image_url(step)
        overlay, key = marks_markup(step.get("marks", []))
        caption = step.get("page_label", review["record"])
        passages.append(
            f'<article class="tx-passage" id="passage-{e(ident)}" aria-labelledby="heading-{e(ident)}">'
            '<header class="tx-passage-head">'
            f'<span class="tx-passage-number" aria-hidden="true">{number:02}</span><div>'
            f'<p class="r-kicker">{e(caption)}</p><h2 id="heading-{e(ident)}">{e(step["title"])}</h2></div></header>'
            '<div class="tx-passage-grid"><figure class="tx-evidence-figure">'
            f'<a class="tx-image-link" href="{e(url)}" data-tx-zoom data-tx-caption="{e(caption)}" '
            f'aria-label="Enlarge manuscript crop: {e(step["title"])}">'
            f'<div class="tx-image-frame"><img src="{e(url)}" alt="{e(step.get("alt", step["original"]))}" '
            f'loading="lazy" decoding="async">{overlay}</div></a>'
            '<div class="tx-image-tools"><span>Click the manuscript to enlarge</span>'
            '<button type="button" data-tx-toggle aria-pressed="true">Highlights on</button></div>'
            + key + f'<figcaption>{e(caption)}. Cropped from the supplied original; '
            '&copy; Crown copyright, National Records of Scotland / ScotlandsPeople. '
            'Coloured boxes are reading aids, not part of the manuscript.</figcaption></figure>'
            '<div class="tx-reading-guide"><p class="tx-guide-label">On the page</p>'
            f'<blockquote class="tx-literal">{e(step["original"])}</blockquote>'
            '<p class="tx-guide-label">In modern English</p>'
            f'<p class="tx-modern">{e(step["reading"])}</p>'
            '<div class="tx-how"><h3>How to read it</h3>'
            f'<p>{e(step["explanation"])}</p></div>'
            '<div class="tx-proof"><h3>What this establishes</h3>'
            f'<p>{e(step["proves"])}</p></div>'
            '<div class="tx-not-proof"><h3>What it does not establish</h3>'
            f'<p>{e(step["does_not_prove"])}</p></div>'
            f'<p class="tx-reading-confidence">{e(step.get("confidence", "Uncertain readings stay bracketed."))}</p>'
            '</div></div>' + ('' if step.get("word_studies_replaced") else word_studies_markup(step)) + '</article>')
    return (
        '<section class="tx-walkthrough" id="guided-reading" aria-labelledby="tx-walkthrough-title">'
        '<div class="tx-walkthrough-heading"><div><p class="r-kicker">Follow the handwriting</p>'
        '<h2 id="tx-walkthrough-title">The people behind the words.</h2>'
        f'<p>{e(data.get("intro", "Follow the numbered passages from the manuscript to the family evidence."))}</p></div>'
        '<div class="tx-colour-key" aria-label="Highlight colours"><span class="tx-legend-name">Name</span>'
        '<span class="tx-legend-relationship">Relationship / role</span><span class="tx-legend-uncertain">Uncertain</span></div></div>'
        '<details class="tx-handbook"><summary>New to secretary hand? Start with the shapes.</summary>'
        '<div class="tx-handbook-grid"><p><strong>Follow the writing line.</strong> Ascenders rise above small letters; '
        'descenders fall below them. A neighbouring line can cross the word you are reading.</p>'
        '<p><strong>Count the short strokes.</strong> These are called minims. Joined i, m, n and u shapes '
        'can be ambiguous; compare a clear repeated word by the same clerk rather than guessing from a modern alphabet.</p>'
        '<p><strong>Separate reading from expansion.</strong> A contraction is not a fully written modern word. '
        'Square brackets retain doubtful letters or editorial additions. A familiar legal formula is a clue, not permission to fill a gap.</p>'
        '<p><strong>Then assess the relationship.</strong> Reading a name securely is not the same as proving kinship. '
        'Look for the actual role words and who they refer to.</p></div>'
        '<p class="tx-handbook-links">Learn with the archive: '
        '<a href="https://www.scotlandspeople.gov.uk/scottish-handwriting/tutorials/1-hour-basic-tutorial">Secretary-hand tutorial</a> '
        '&middot; <a href="https://www.scotlandspeople.gov.uk/scottish-handwriting/tutorials/testaments-tutorial/introduction-testaments-dative-vocabulary">Testament vocabulary</a>.</p></details>'
        + '<section class="tx-people" aria-labelledby="tx-people-title"><h3 id="tx-people-title">Who appears in these passages?</h3>'
        '<p>Select a name to jump to its manuscript evidence.</p><ul class="tx-people-grid">' + "".join(people) + '</ul></section>'
        + letterform_studies_markup(review["id"])
        + '<nav class="tx-reading-nav" aria-label="Manuscript reading steps">' + nav + '</nav>'
        + "".join(passages) + '</section>'
        '<dialog class="tx-image-dialog" id="tx-image-dialog" aria-labelledby="tx-image-dialog-title">'
        '<div class="tx-image-dialog-bar"><h2 id="tx-image-dialog-title">Manuscript detail</h2>'
        '<button type="button" data-tx-native aria-pressed="false">Actual size</button>'
        '<button type="button" data-tx-close aria-label="Close enlarged manuscript">Close &times;</button></div>'
        '<div class="tx-zoom-canvas"></div><p class="tx-zoom-caption"></p></dialog>'
    )
