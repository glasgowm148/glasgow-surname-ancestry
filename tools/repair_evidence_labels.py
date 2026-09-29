#!/usr/bin/env python3
"""Apply the shared evidence vocabulary to already-published pages.

A targeted, idempotent repair; it never rebuilds a page. It only:

* rewrites dossier relationship labels (``.status-label`` inside a
  ``tr[data-state]`` row) from the recorded state, via
  ``evidence_labels.normalise_status_label``;
* adds the "How to read the evidence" link beside dossier family labels,
  research priorities and the dossier header's assessment line;
* re-renders only the "Active research priorities" block of dossiers that
  publish research tasks, so open questions show their status, what would
  resolve them and the record to inspect (or "Not yet identified");
* adds ``/assets/research/evidence.css`` to pages it changes;
* maps Atlas relationship marks to the canonical tree labels and adds the
  guide link to the Atlas person drawer.

Navigation rails and every other part of a page are left byte-for-byte intact.
"""
from __future__ import annotations

from collections import Counter
from html import escape
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import evidence_labels as ev  # noqa: E402

WEB = ROOT / "www"
CSS_HREF = f"/assets/research/evidence.css?v={ev.VERSION}"
CSS_LINK = f'<link href="{CSS_HREF}" rel="stylesheet"/>'
GUIDE = (f'<p class="evidence-guide-link"><a href="{ev.GUIDE_URL}">{ev.GUIDE_LABEL}</a>'
         '<span> What “Documented”, “Probable”, “Possible” and “Unassessed tree link” mean.</span></p>')

ROW_LABEL = re.compile(
    r'(<tr\b[^>]*\bdata-state="(?P<state>[^"]*)"[^>]*>(?:(?!</tr>).)*?<span class="status-label status-[^"]*">)'
    r'(?P<text>[^<]*)(</span>)',
    re.S,
)
RESEARCH_BLOCK = re.compile(
    r'<h3>Active research priorities</h3>(?:<p class="evidence-guide-link">.*?</p>)?'
    r'(?:<ol class="task-list">.*?</ol>|<p class="dossier-empty">No active task is recorded\.</p>)'
    r'(?:<h3>Completed searches and review log</h3>(?:<div class="table-wrap">.*?</table></div>|<p class="dossier-empty">[^<]*</p>))?',
    re.S,
)


def _html_text(value: str) -> str:
    """Escape like the BeautifulSoup serializer used for dossier pages."""
    return escape(value, quote=False)


def relabel(text: str) -> tuple[str, int]:
    count = 0

    def replace(match: re.Match) -> str:
        nonlocal count
        new = _html_text(ev.normalise_status_label(match["state"], match["text"]))
        if new == match["text"]:
            return match[0]
        count += 1
        return match[1] + new + match[4]

    return ROW_LABEL.sub(replace, text), count


def add_family_guide(text: str) -> str:
    start = text.find('id="family"')
    if start < 0:
        return text
    end = text.find("</section>", start)
    section = text[start:end]
    if "evidence-guide-link" in section or '<details class="relation-group">' not in section:
        return text
    at = start + section.index('<details class="relation-group">')
    return text[:at] + GUIDE + text[at:]


META_LINK = (f'<a class="dossier-evidence-guide" href="{ev.GUIDE_URL}">{ev.GUIDE_LABEL}</a>')
META_BLOCK = re.compile(r'(<div class="dossier-meta">)((?:(?!</div>).)*?)(</div>)', re.S)


def add_meta_guide(text: str) -> str:
    """Show the guide in the dossier header, beside the assessment date."""
    if 'class="dossier-evidence-guide"' in text:
        return text
    return META_BLOCK.sub(lambda m: m[1] + m[2] + META_LINK + m[3], text, count=1)


def _soup_fragment(markup: str) -> str:
    from bs4 import BeautifulSoup
    return str(BeautifulSoup(markup, "html.parser"))


def rerender_research(text: str, profile_id: str) -> str:
    if "Question tested" not in text:
        return text
    import repair_person_hierarchy as dossiers
    fresh = _soup_fragment(dossiers._research_html(dossiers._editorial(profile_id)))
    return RESEARCH_BLOCK.sub(lambda _: fresh, text, count=1)


def add_css(text: str) -> str:
    if "/assets/research/evidence.css" in text:
        return re.sub(r"/assets/research/evidence\.css\?v=\w+", CSS_HREF, text)
    return text.replace("</head>", CSS_LINK + "</head>", 1)


def repair_people(counts: Counter, only: set[str] | None = None) -> None:
    for path in sorted((WEB / "people").glob("*.html")):
        if only and path.stem not in only:
            continue
        before = path.read_text(encoding="utf-8")
        if ('class="status-label' not in before and "Active research priorities" not in before
                and 'class="dossier-meta"' not in before):
            continue
        text, relabelled = relabel(before)
        text = add_family_guide(text)
        text = add_meta_guide(text)
        match = re.search(r'data-r-person=["\']([^"\']+)', text)
        if match:
            text = rerender_research(text, match[1])
        if text != before:
            text = add_css(text)
            path.write_text(text, encoding="utf-8")
            counts["person_pages"] += 1
            counts["relationship_labels"] += relabelled


# Atlas: one small relation-mark mapper and a guide link in the Family tab.
ATLAS_MARKS = {
    "DNA-confirmed": ev.label("dna_confirmed"), "confident": ev.label("confident"),
    "uncertain": ev.label("uncertain"), "non-biological": ev.label("non_biological"),
    "unmarked": ev.label("unmarked"),
}
ATLAS_OLD = "const detail=[r.role,r.status&&r.status!=='unmarked'?r.status:null,"
ATLAS_NEW = ("const detail=[r.role,r.status?(EVIDENCE_MARKS[r.status]||r.status):null,")
ATLAS_DEF = "const EVIDENCE_MARKS=" + json.dumps(ATLAS_MARKS, ensure_ascii=False, separators=(",", ":")) + ";"
ATLAS_FAMILY_OLD = ("rels.length?rels.map(relationHTML).join(''):'<p>None named in this snapshot.</p>'}</section>`;\n"
                    " }else{")
ATLAS_GUIDE = (f"body+=`<p class=\"evidence-guide-link\"><a href=\"{ev.GUIDE_URL}\">{ev.GUIDE_LABEL}</a> "
               "Tree marks are the contributor’s, not this project’s assessment.</p>`;")
ATLAS_FAMILY_NEW = ("rels.length?rels.map(relationHTML).join(''):'<p>None named in this snapshot.</p>'}</section>`;\n"
                    "  " + ATLAS_GUIDE + "\n }else{")


def patch_atlas_script(text: str) -> str:
    text = re.sub(r"const EVIDENCE_MARKS=\{[^}]*\};", lambda _: ATLAS_DEF, text)
    if ATLAS_OLD in text:
        text = text.replace("function relationHTML(r){", ATLAS_DEF + "\nfunction relationHTML(r){", 1)
        text = text.replace(ATLAS_OLD, ATLAS_NEW, 1)
    if "evidence-guide-link" not in text and ATLAS_FAMILY_OLD in text:
        text = text.replace(ATLAS_FAMILY_OLD, ATLAS_FAMILY_NEW, 1)
    return text


def repair_atlas(counts: Counter) -> None:
    for relative in ("assets/research/atlas.js", "assets/research/atlas-standalone.html"):
        path = WEB / relative
        before = path.read_text(encoding="utf-8")
        text = patch_atlas_script(before)
        if relative.endswith(".html"):
            text = add_css(text) if text != before else text
        if text != before:
            path.write_text(text, encoding="utf-8")
            counts["atlas_files"] += 1
    boot = WEB / "assets/research/atlas-boot.js"
    before = boot.read_text(encoding="utf-8")
    text = before.replace("/assets/research/atlas.js?v=3.3-canopy-1'", "/assets/research/atlas.js?v=3.3-canopy-1-ev1'")
    if text != before:
        boot.write_text(text, encoding="utf-8")
        counts["atlas_files"] += 1
    page = WEB / "onetree/index.html"
    before = page.read_text(encoding="utf-8")
    text = add_css(before)
    if text != before:
        page.write_text(text, encoding="utf-8")
        counts["atlas_pages"] += 1


def repair_research_page(counts: Counter) -> None:
    path = WEB / "research/index.html"
    before = path.read_text(encoding="utf-8")
    text = add_css(before)
    if text != before:
        path.write_text(text, encoding="utf-8")
        counts["research_page"] += 1


def repair(profile_ids=None) -> dict:
    counts: Counter = Counter()
    ev.write_json()
    only = {value.casefold() for value in profile_ids} if profile_ids else None
    repair_people(counts, only)
    if not only:
        repair_atlas(counts)
        repair_research_page(counts)
    return dict(counts)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profiles", nargs="*", help="Optional WikiTree IDs")
    print(json.dumps(repair(parser.parse_args().profiles), sort_keys=True))
