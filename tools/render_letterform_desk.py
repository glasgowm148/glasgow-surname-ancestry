"""Progressively disclosed, source-preserving manuscript reading desk."""
from html import escape
from functools import lru_cache
import json
from pathlib import Path
import re


def e(value):
    return escape(str(value or ""), quote=True)


@lru_cache(maxsize=None)
def load_community_reading(ident):
    path = Path(__file__).resolve().parents[1] / "research" / "transcriptions" / "community-readings" / f"{ident}.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def community_reading_markup(ident, study=None):
    data = load_community_reading(ident)
    if not data:
        return ""
    target = data.get("study_nav_label")
    if target and (study or {}).get("nav_label") != target:
        return ""
    if study is not None and not target:
        return ""
    conclusions = "".join(f'<div><dt>{e(item["label"])}</dt><dd>{e(item["text"])}</dd></div>' for item in data.get("assessment", []))
    return (
        '<section class="tx-community-reading" id="human-contributor-reading" aria-labelledby="human-reading-title">'
        '<p class="tx-community-kicker">Community transcription / human reading</p>'
        f'<h3 id="human-reading-title">{e(data["title"])}</h3>'
        f'<p class="tx-community-byline">{e(data["attribution"])}</p>'
        '<blockquote class="tx-community-quote">'
        f'<p>{e(data["surname_quote"])}</p></blockquote>'
        f'<dl class="tx-community-assessment">{conclusions}</dl>'
        '<details class="tx-community-details"><summary>Read the contributor\'s full transcription and discussion</summary>'
        f'<p>{e(data["modernization"])}</p><pre class="tx-community-transcript">{e(data["transcript"])}</pre>'
        '<h4>The project owner\'s Hutcheson connection</h4>'
        f'<blockquote><p>{e(data["owner_reply"])}</p><cite>project owner, original poster</cite></blockquote>'
        '<h4>Marjory or Marion?</h4>'
        f'<blockquote><p>{e(data["owner_name_question"])}</p><cite>project owner, original poster</cite></blockquote>'
        f'<blockquote><p>{e(data["name_reply"])}</p><cite>Double_Show_9316</cite></blockquote>'
        f'<p class="tx-community-provenance">{e(data["source_note"])}</p></details></section>'
    )


def confidence_badge(study):
    assessment = str(study.get("confidence") or "").strip()
    levels = {
        "high": ("High confidence", 3),
        "moderate": ("Moderate confidence", 2),
        "low": ("Low confidence", 1),
        "qualified": ("Qualified reading", 0),
        "unassessed": ("Not yet graded", 0),
    }
    level = study.get("confidence_grade")
    if level not in levels:
        # Summarise maintained qualitative assessments, not invented percentages.
        text = re.sub(r"\bstrong\b", "high", assessment.casefold())
        text = re.sub(r"\bmedium\b", "moderate", text)
        grades = set(re.findall(r"\b(high|moderate|low)\b", text))
        leading = re.match(r"^(high|moderate|low)\b", text)
        level = (leading.group(1) if leading and len(grades) == 1 else
                 "qualified" if assessment else "unassessed")
    label, strength = levels[level]
    if strength:
        drawing = "".join(
            f'<rect x="{2 + i * 5}" y="{11 - i * 4}" width="3" height="{4 + i * 4}" rx="1" opacity="{1 if i < strength else .22}"/>'
            for i in range(3)
        )
    else:
        drawing = '<circle cx="8" cy="8" r="6" fill="none" stroke="currentColor" stroke-width="1.5"/><path d="M8 4.5v4M8 11v.5" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>'
    return (f'<span class="lf-confidence lf-confidence-{level}" title="{e(assessment or label)}">'
            f'<svg viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">{drawing}</svg>'
            f'<span>{label}</span></span>')


def source_svg(image, width, height, region, label, locator=False):
    x, y, w, h = region
    box = f'0 0 {width} {height}' if locator else f'{x} {y} {w} {h}'
    mark = (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" '
            'class="lf-source-box" vector-effect="non-scaling-stroke"/>') if locator else ""
    return (f'<svg viewBox="{box}" role="img" aria-label="{e(label)}" '
            f'xmlns="http://www.w3.org/2000/svg"><image href="{e(image)}" '
            f'width="{width}" height="{height}"/>{mark}</svg>')


def render_letterform_desk(ident, data):
    if not data or not data.get("studies"):
        return ""
    studies = []
    palette = ["#a04431", "#176f78", "#626727", "#83512c", "#355caf", "#874c75"]
    for number, study in enumerate(data["studies"], 1):
        image = study.get("image", "")
        region = study.get("region")
        if not image.startswith("/assets/research/") or not region:
            continue
        width, height = study["image_width"], study["image_height"]
        sid = f'tx-letterform-{ident}-{study["id"]}'
        letters = study.get("letters", []) if study.get("review_status") == "source-aligned" else []
        words = study.get("words") or [{"text": study.get("comparison_text", study.get("reading", "")), "region": region}]
        for word in words:
            word.setdefault("region", region)
        first = words[0]
        config = {"image": image, "width": width, "height": height, "words": words,
                  "letters": [{"id": l.get("id", str(i)), "glyph": l.get("glyph", "?"),
                               "region": l.get("region"), "color": palette[i % len(palette)]}
                              for i, l in enumerate(letters)]}
        tabs = "".join(f'<button type="button" data-lf-word="{i}" aria-pressed="{str(i == 0).lower()}">{e(w.get("label", w["text"]))}</button>' for i, w in enumerate(words))
        chips, panels = [], []
        for i, letter in enumerate(letters):
            lid = letter.get("id", str(i))
            glyph = letter.get("glyph", "?")
            color = palette[i % len(palette)]
            chips.append(f'<button type="button" data-lf-letter="{e(lid)}" aria-pressed="false" '
                         f'aria-controls="{sid}-group-{i}" style="--group-ink:{color}">'
                         f'<span aria-hidden="true">{i + 1:02}</span> {e(glyph)}</button>')
            crop = source_svg(image, width, height, letter.get("region", region), f'Original source group: {glyph}')
            observations = "".join(f'<dt>{label}</dt><dd>{e(letter.get(key))}</dd>' for key, label in (
                ("observed", "What is visible"), ("matches", "Why this reading"),
                ("differs", "Where it differs"), ("caution", "What remains uncertain")) if letter.get(key))
            panels.append(f'<section class="lf-group-panel" id="{sid}-group-{i}" data-lf-panel="{e(lid)}" hidden>'
                          f'<h5>{e(letter.get("label", glyph))}</h5><div class="lf-group-grid">'
                          f'<figure>{crop}<figcaption>Untouched source detail. Neighbouring ink is retained.</figcaption></figure>'
                          f'<dl>{observations}</dl></div></section>')
        steps = []
        for i, step in enumerate(study.get("reading_steps", [])):
            crop = source_svg(image, width, height, step.get("region", region), step.get("title", "Reading step"))
            steps.append(f'<li data-lf-step="{i}"><figure>{crop}<figcaption>Original source detail</figcaption></figure>'
                         f'<div><p class="lf-eyebrow">Step {i + 1:02}</p><h5>{e(step.get("title"))}</h5><p>{e(step.get("text"))}</p></div></li>')
        reasoning = (f'<details class="lf-drawer lf-reasoning"><summary>Walk through the reading <span>{len(steps)} steps</span></summary>'
                     '<div class="lf-step-controls" hidden><button type="button" data-lf-prev>Previous</button>'
                     '<output data-lf-progress></output><button type="button" data-lf-next>Next step</button></div>'
                     f'<ol class="lf-steps">{"".join(steps)}</ol></details>') if steps else ""
        comparisons = []
        for comparison in study.get("same_hand_comparisons", []):
            ci = comparison.get("image", image)
            if not ci.startswith("/assets/research/"):
                continue
            crop = source_svg(ci, comparison.get("image_width", width), comparison.get("image_height", height),
                              comparison.get("region", region), comparison.get("reading", "Same-hand comparison"))
            comparisons.append(f'<figure>{crop}<figcaption><strong>{e(comparison.get("reading"))}</strong>'
                               f'<p>{e(comparison.get("explanation"))}</p></figcaption></figure>')
        comparison_markup = ('<details class="lf-drawer"><summary>Compare the same clerk\'s writing '
                             f'<span>{len(comparisons)} source examples</span></summary><div class="lf-same-hand">'
                             + "".join(comparisons) + '</div></details>') if comparisons else ""
        raw = source_svg(image, width, height, first["region"], "Untouched manuscript word")
        locator = source_svg(image, width, height, first["region"], "Word located in the original passage", True)
        font_word = first.get("text", "")
        unknown = first.get("unresolved", False) or len(font_word) > 65
        font_markup = ('<p class="lf-no-reading">No settled reading.<br>A font would supply letters the manuscript has not established.</p>' if unknown else
                       f'<span class="lf-font-word">{e(font_word)}</span><span class="lf-font-unavailable">Loading the secretary-hand teaching font...</span>')
        study_html = [
            f'<details class="lf-study" id="{sid}" name="letterform-{e(ident)}">',
            f'<summary class="lf-study-summary"><span class="lf-study-number">{number:02}</span>',
            f'<span><span class="lf-study-title"><strong>{e(study.get("nav_label", study.get("title")))}</strong>{confidence_badge(study)}</span>',
            f'<small>{e(study.get("title"))}</small></span><span class="lf-open-label">Inspect reading</span></summary>',
            '<div class="lf-study-body">',
            f'<p class="lf-reading"><span>Proposed reading</span><strong>{e(study.get("reading"))}</strong></p>',
            f'<p class="lf-context">{e(study.get("context"))}</p>',
            f'<div class="lf-word-tabs" role="group" aria-label="Choose a whole word">{tabs}</div>',
            '<div class="lf-word-grid">',
            f'<figure class="lf-word-source"><figcaption><span>01</span> Original word <small>Untouched manuscript</small></figcaption><div class="lf-word-image">{raw}</div></figure>',
            '<figure class="lf-word-ink"><figcaption><span>02</span> Ink on white <small>Derived from the original pixels</small></figcaption>',
            '<div class="lf-word-image"><canvas data-lf-ink role="img" aria-label="Processed ink from the selected original word"></canvas><p class="lf-ink-fallback">Open the original above if this browser cannot process the image.</p></div></figure>',
            '<figure class="lf-word-model"><figcaption><span>03</span> Same spelling, another hand <small>Joscelyn teaching font</small></figcaption>',
            f'<div class="lf-word-image lf-model-image">{font_markup}</div><p class="lf-model-spelling">{e(font_word) if not unknown else "Unresolved"}</p></figure>',
            '</div>',
            '<div class="lf-ink-controls"><div role="group" aria-label="Derived ink display"><button type="button" data-lf-ink-mode="black" aria-pressed="true">Clean ink</button>',
            '<button type="button" data-lf-ink-mode="colour" aria-pressed="false">Colour letter groups</button></div>',
            f'<label for="{sid}-strength">Retain faint ink <input id="{sid}-strength" data-lf-strength type="range" min="20" max="80" value="52"></label></div>',
            ('<div class="lf-inline-key"><span>Colour key: proposed letter groups</span>'
             f'<div class="lf-letter-controls" role="group" aria-label="Source letter groups">{"".join(chips)}</div></div>') if chips else '',
            '<p class="lf-processing-note">The white-background view suppresses paper colour; reviewed focus boundaries exclude separable neighbouring fragments where available. It does not restore missing strokes. Colour follows retained source pixels inside proposed letter groups, not a reconstructed pen path. Ambiguous crossings remain neutral where reviewed; other crossing ink may still belong to another line.</p>',
            '<p class="lf-model-note">The teaching word colours complete characters using the same key as the proposed manuscript groups; it does not use width-based colour strips. Cross-letter ligatures are disabled in both modes so each character can keep its own colour. Unmapped characters stay neutral. This font shows the proposed spelling in another hand, not proof of the reading.</p>',
            f'<details class="lf-drawer lf-locator"><summary>Locate the word in its passage <span>Original context</span></summary><figure>{locator}<figcaption>{e(study.get("locator_note", study.get("context")))}</figcaption></figure></details>',
        ]
        if chips:
            study_html.extend([
                '<div class="lf-letter-section">',
                f'<details class="lf-drawer lf-group-detail"><summary>Selected letter-group evidence</summary>{"".join(panels)}</details></div>',
            ])
        study_html.extend([
            community_reading_markup(ident, study),
            reasoning, comparison_markup,
            '<details class="lf-drawer lf-assessment"><summary>Reading, meaning and uncertainty</summary>',
            f'<p><strong>Expansion:</strong> {e(study.get("expansion"))}</p><p><strong>Confidence:</strong> {e(study.get("confidence"))}</p>',
            f'<p class="lf-conclusion"><strong>Evidence boundary:</strong> {e(study.get("conclusion"))}</p></details>',
            f'<script type="application/json" class="lf-config">{json.dumps(config, ensure_ascii=True).replace("<", chr(92) + "u003c")}</script>',
            '</div></details>',
        ])
        studies.append("".join(study_html))
    return ( '<link rel="stylesheet" href="/assets/research/letterform-workbench.css?v=8">'
            + community_reading_markup(ident)
            + '<section class="lf-workbench" id="reading-desk" aria-labelledby="tx-letterform-title">'
            '<header class="lf-heading"><p class="lf-eyebrow">The reading desk</p>'
            '<h3 id="tx-letterform-title">One name. Three ways to look.</h3>'
            '<p>Choose a name or relationship below. Compare the original ink, a paper-free view and the same spelling in a secretary-hand teaching font. Open the reasoning only when you need it.</p>'
            '<p class="lf-confidence-note">Badges summarise reading confidence, not proof of family identity. A qualified reading has mixed or unresolved details; the full assessment is inside.</p></header>'
            + "".join(studies)
            + '<p class="lf-font-credit">Teaching typeface: <a href="https://github.com/psb1558/Joscelyn-font">Joscelyn by Peter S. Baker</a>, based on a different Renaissance secretary hand. '
              '<a href="/assets/research/fonts/Joscelyn-OFL.txt">SIL Open Font License</a>. Source images remain separate and unchanged.</p>'
              '</section><script src="/assets/research/letterform-workbench.js?v=7" defer></script>')
