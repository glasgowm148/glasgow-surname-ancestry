#!/usr/bin/env python3
"""Preserve approved curated Y-DNA research and withhold other tester assets."""
from __future__ import annotations

import argparse
from datetime import date
import json
from pathlib import Path
import re
from shutil import copy2

try:
    from tools.site_sources.ydna_story import build as ydna_build
    from tools.public_ydna_research import study_is_approved, restore_lines, audit_approved_research, approved_document
    from tools.approved_restorations import restore_atlas as restore_approved_atlas, entries as restoration_entries, source as restoration_source
except ModuleNotFoundError:  # Direct execution from tools/.
    from site_sources.ydna_story import build as ydna_build
    from public_ydna_research import study_is_approved, restore_lines, audit_approved_research, approved_document
    from approved_restorations import restore_atlas as restore_approved_atlas, entries as restoration_entries, source as restoration_source


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "www"
PRIVATE_ROOT = ROOT / "data/private/withheld-public-assets"
PRIVATE_STUDY_INPUT = PRIVATE_ROOT / "ydna/glasgow-ydna-story-source/data.json"
WITHHELD_ASSETS = (
    "ydna/glasgow-ydna-story-source/NARRATIVE_NOTES.md",
    "ydna/glasgow-ydna-story-source/README.md",
    "ydna/glasgow-ydna-story-source/ANALYSIS.md",
    "ydna/glasgow-ydna-story-source/data.json",
    "ydna/glasgow-ydna-story-source/data-integrity-report.json",
    "ydna/glasgow-ydna-story-source/matrix-audit.json",
    "ydna/glasgow-ydna-story-source/previews-story/alternatives-desktop.png",
    "ydna/glasgow-ydna-story-source/previews-story/dates-desktop.png",
    "ydna/glasgow-ydna-story-source/previews-story/fork-desktop.png",
    "ydna/glasgow-ydna-story-source/previews-story/inheritance-desktop.png",
    "ydna/glasgow-ydna-story-source/previews-story/inheritance-mobile.png",
    "ydna/glasgow-ydna-story-source/previews-story/story-dark.png",
    "ydna/glasgow-ydna-story-source/previews-story/story-desktop.png",
    "ydna/glasgow-ydna-story-source/previews-story/story-mobile.png",
    "ydna/glasgow-ydna-story-source/story-test-report.json",
    "ydna/glasgow-ydna-story-source/source/app.js",
    "ydna/glasgow-ydna-story-source/source/template.html",
    "assets/research/glasgow-951-dna-matrix.json",
    "assets/research/glasgow-951-dna-matrix.csv",
)
DNA_INDEX = "assets/research/dna-index.json"
DNA_COVERAGE = (
    "Individual Y-DNA annotations are withheld pending publication approval. "
    "See the public Y-DNA summary."
)
ATLAS_MODELS = (
    "assets/research/atlas-model.json",
    "assets/research/atlas-import.json",
    "onetree/glasgow-one-tree-polished-3/model.json",
)
ATLAS_RENDERERS = (
    "assets/research/atlas.js",
    "assets/research/atlas-standalone.html",
    "assets/unified/atlas-standalone.html",
    "onetree/glasgow-one-tree-polished-3/template.html",
    "onetree/index.html",
    "assets/repair/atlas.js",
)
ATLAS_HTML_RENDERERS = tuple(relative for relative in ATLAS_RENDERERS if relative.endswith(".html"))
PUBLIC_DNA_SUMMARY_CSS = ROOT / "tools/atlas-public-summary.css"
SAFE_PAGES = (
    "ydna/index.html",
    "ydna/glasgow-ydna-story-source/index.html",
)

SAFE_DNA_RENDERER = '''function renderDNA(){
 $('#dna-view').innerHTML=`<div class="content-head"><div><div class="eyebrow">Y-DNA RESEARCH</div><h2>Historical branch summary</h2><p>Individual test results and tester-level relationships are withheld pending publication approval.</p></div></div><div class="note-box"><p>Read the public summary for the current aggregate historical interpretation and its qualifications.</p><p><a class="tool-btn" href="/ydna/">Open the Y-DNA summary ↗</a></p></div>`;
}
'''


def _preserve(public: Path, private: Path) -> bool:
    if not public.exists() or private.exists():
        return False
    private.parent.mkdir(parents=True, exist_ok=True)
    copy2(public, private)
    return True


def _sanitise_model(model: dict[str, object]) -> dict[str, object]:
    """Remove tester-level rows while retaining the public genealogy model."""
    prior_dna = model.get("dna", [])
    prior_ids = {
        item.get("id") for item in prior_dna
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    } if isinstance(prior_dna, list) else set()
    model["dna"] = []
    meta = model.setdefault("meta", {})
    if not isinstance(meta, dict):
        raise ValueError("Atlas model metadata must be an object.")
    meta["dnaCoverage"] = DNA_COVERAGE
    landmarks = model.get("landmarks")
    if isinstance(landmarks, list):
        model["landmarks"] = [item for item in landmarks if item not in prior_ids]
    return model


def _replace_render_dna(page: str) -> str:
    """Replace the detailed DNA view using its stable next-function boundary."""
    revised, count = re.subn(
        r"(?:/\* Genetic overview.*?\*/\s*)?function renderDNA\(\)\{.*?(?=\n(?:/\*.*?\*/\s*)?let searchItems=)",
        SAFE_DNA_RENDERER,
        page,
        count=1,
        flags=re.DOTALL,
    )
    if count != 1:
        raise ValueError("Expected one renderDNA function.")
    return revised


def _replace_tree_data(page: str) -> str:
    """Sanitise a standalone model embedded in its tree-data script tag."""
    def replace(match: re.Match[str]) -> str:
        model = _sanitise_model(json.loads(match.group(2)))
        payload = json.dumps(model, ensure_ascii=False, separators=(",", ":")).replace("<", r"\u003c")
        return match.group(1) + payload + match.group(3)

    revised, count = re.subn(
        r'(<script id="tree-data" type="application/json">)(.*?)(</script>)',
        replace,
        page,
        count=1,
        flags=re.DOTALL,
    )
    if count != 1:
        raise ValueError("Expected one embedded atlas model.")
    return revised


def _remove_tester_panel(page: str) -> str:
    """Remove the separate OneTree tester UI and pins control."""
    page, _ = re.subn(
        r'<aside[^>]*id="repair-tester-panel".*?</aside>', "", page,
        count=1, flags=re.DOTALL,
    )
    page = re.sub(r'<button[^>]*id="repair-testers-toggle"[^>]*>.*?</button>', "", page, count=1)
    page = re.sub(r'<button[^>]*id="dna-toggle"[^>]*>.*?</button>', "", page, count=1)
    page = re.sub(r"\s*\$\('#dna-toggle'\)\.hidden=.*?;", "", page, count=1)
    # The markup control is removed above, so its UI-state updates must go too.
    # Keeping either call aborts Atlas startup before it names #visible-records.
    page = re.sub(
        r"\$\('#dna-toggle'\)\.classList\.toggle\(.*?;\$\('#dna-toggle'\)\.setAttribute\(.*?;",
        "", page, count=1,
    )
    page = re.sub(r"\$\('#dna-toggle'\)\.onclick=\(\)=>\{.*?\};", "", page, count=1)
    # Repair the tail left by an older version of this helper, without restoring
    # the withdrawn control or changing any surrounding atlas handlers.
    page = page.replace("if(!state.pins)state.dnaFocus=false;syncUI();invalidate()};", "")
    page = page.replace("syncUI();invalidate()};$('#minus')", "$('#minus')")
    # The aggregate summary has no pin count or marker legend.
    page = re.sub(r'<div><strong id="dna-total">.*?</div>', "", page, count=1)
    page = re.sub(r"\$\('#dna-total'\)\.textContent=.*?;", "", page, count=1)
    page = re.sub(r'<span class="repair-dna-legend">.*?</span>', "", page, count=1)
    page = re.sub(r"\.repair-dna-legend[^{}]*\{[^{}]*\}", "", page)
    # Older standalone exports carried an appended tester-panel initializer.
    page = re.sub(
        r"</script><script>/\* Testers are represented.*?</script>",
        "</script>", page, count=1, flags=re.DOTALL,
    )
    # Remove only CSS rules that style the now-absent panel; no public layout
    # depends on these rules.
    page = re.sub(r"[^{}]*\.repair-tester[^{}]*\{[^{}]*\}", "", page)
    return page


def _sanitise_renderer(relative: str, page: str) -> str:
    if relative.endswith("atlas.js") and relative == "assets/repair/atlas.js":
        return "/* Tester-level Y-DNA controls are withheld pending publication approval. */\n"
    if "function renderDNA()" in page:
        page = _replace_render_dna(page)
    if '<script id="tree-data" type="application/json">' in page and "__MODEL__" not in page:
        page = _replace_tree_data(page)
    page = _remove_tester_panel(page)
    # These helpers are unreachable with dna=[], but removing them prevents a
    # future renderer from treating a manually-added annotation as publishable.
    page = re.sub(r"function dnaCallout\(d\)\{.*?\}\n(?=function renderDetail)", "", page, count=1, flags=re.DOTALL)
    page = re.sub(r"\s*if\(d\)body\+=dnaCallout\(d\);", "", page)
    page = re.sub(r"function dnaBadge\(d\)\{.*?\}\n(?=function renderDetail|function renderDNA)", "", page, count=1, flags=re.DOTALL)
    page = re.sub(r"dnaMarkers:\(\)=>[^\n]*,familyAudit", "dnaMarkers:()=>[],familyAudit", page, count=1)
    if relative in ATLAS_HTML_RENDERERS:
        page = _inject_public_dna_summary_css(page)
    return page


def _inject_public_dna_summary_css(page: str) -> str:
    """Embed the maintained contrast rules in each self-contained Atlas HTML."""
    css = PUBLIC_DNA_SUMMARY_CSS.read_text(encoding="utf-8")
    style = f'<style data-public-dna-summary>\n{css}</style>'
    page = re.sub(r'<style data-public-dna-summary>.*?</style>', "", page, count=1, flags=re.DOTALL)
    return page.replace("</head>", style + "</head>", 1)


def _repair_atlas_assets(web: Path, private_root: Path) -> tuple[int, int]:
    """Archive then sanitise public models and every maintained renderer copy."""
    restored = restore_approved_atlas(web, private_root)
    if restored is not None:
        return restored[:2]
    models_changed = renderers_changed = 0
    for relative in ATLAS_MODELS:
        public, private = web / relative, private_root / relative
        if not public.exists():
            raise FileNotFoundError(f"missing atlas model: {public}")
        archived = _preserve(public, private)
        model = _sanitise_model(json.loads(public.read_text(encoding="utf-8")))
        rendered = json.dumps(model, ensure_ascii=False, separators=(",", ":")) + "\n"
        if archived or public.read_text(encoding="utf-8") != rendered:
            public.write_text(rendered, encoding="utf-8")
            models_changed += 1
    for relative in ATLAS_RENDERERS:
        public, private = web / relative, private_root / relative
        if not public.exists():
            raise FileNotFoundError(f"missing atlas renderer: {public}")
        archived = _preserve(public, private)
        rendered = _sanitise_renderer(relative, public.read_text(encoding="utf-8"))
        if archived or public.read_text(encoding="utf-8") != rendered:
            public.write_text(rendered, encoding="utf-8")
            renderers_changed += 1
    return models_changed, renderers_changed


def _repair_onetree_snapshot_badge(web: Path) -> int:
    """State the Atlas import date without presenting it as catalogue freshness."""
    model = json.loads((web / "assets/research/atlas-model.json").read_text(encoding="utf-8"))
    raw_date = str(model.get("meta", {}).get("catalogueGenerated", ""))[:10]
    imported = date.fromisoformat(raw_date)
    label = f"Atlas · {imported.day} {imported.strftime('%b')} {imported.year}"
    title = (
        f"Atlas imported catalogue snapshot: {imported.day} {imported.strftime('%B')} "
        f"{imported.year}; current catalogue has separate updates."
    )
    path = web / "onetree/index.html"
    page = path.read_text(encoding="utf-8")

    def replace(match: re.Match[str]) -> str:
        anchor = re.sub(r'title="[^"]*"', f'title="{title}"', match.group(), count=1)
        return re.sub(r">.*?</a>$", f">{label}</a>", anchor, count=1, flags=re.DOTALL)

    revised, count = re.subn(
        r'<a(?=[^>]*class="[^"]*\bg-snapshot-link\b[^"]*")[^>]*>.*?</a>',
        replace, page, count=1, flags=re.DOTALL,
    )
    if count != 1:
        raise ValueError("Expected one OneTree Atlas snapshot badge.")
    if revised == page:
        return 0
    path.write_text(revised, encoding="utf-8")
    return 1


def private_tester_ids(private_root: Path = PRIVATE_ROOT) -> frozenset[str]:
    """Return tester identifiers from retained private inputs without emitting them.

    The packaging layer uses this to remove exact identifiers from generated
    public JSON, free text and URLs. It deliberately reads only preserved
    publication inputs and never treats their presence as publication approval.
    """
    identifiers: set[str] = set()
    study = private_root / "ydna/glasgow-ydna-story-source/data.json"
    if study.exists():
        data = json.loads(study.read_text(encoding="utf-8"))
        metadata = data.get("metadata", {})
        if isinstance(metadata, dict) and isinstance(metadata.get("referenceKit"), str):
            identifiers.add(metadata["referenceKit"])
        for kit in data.get("kits", []):
            if isinstance(kit, dict) and isinstance(kit.get("id"), str):
                identifiers.add(kit["id"])
        for root in data.get("roots", []):
            if isinstance(root, dict):
                identifiers.update(value for value in root.get("kitIds", []) if isinstance(value, str))
        for pair in data.get("pairs", {}):
            if isinstance(pair, str):
                identifiers.update(part for part in pair.split("|") if part)
        audit = data.get("audit", {})
        if isinstance(audit, dict):
            identifiers.update(value for value in audit.get("ids", []) if isinstance(value, str))
    index = private_root / "assets/research/dna-index.json"
    if index.exists():
        for row in json.loads(index.read_text(encoding="utf-8")):
            if isinstance(row, dict):
                identifiers.update(value for value in row.get("kits", []) if isinstance(value, str))
    return frozenset(identifiers)


def _preserve_then_withhold(web: Path, private_root: Path) -> int:
    changed = 0
    for relative in WITHHELD_ASSETS:
        public = web / relative
        private = private_root / relative
        if public.exists() and approved_document(relative, public.read_text(), private_root):
            continue
        if public.exists() and not private.exists():
            private.parent.mkdir(parents=True, exist_ok=True)
            copy2(public, private)
            changed += 1
        if public.exists():
            public.unlink()
            changed += 1
    return changed


def _preserve_pages(web: Path, private_root: Path) -> int:
    """Keep the previous public explorer pages as private source records."""
    changed = 0
    for relative in SAFE_PAGES:
        public = web / relative
        private = private_root / relative
        if public.exists() and not private.exists():
            private.parent.mkdir(parents=True, exist_ok=True)
            copy2(public, private)
            changed += 1
    return changed


def _preserve_dna_index(web: Path, private_root: Path) -> tuple[int, int]:
    """Archive the old index and leave an empty JSON array for Atlas fetches."""
    public = web / DNA_INDEX
    private = private_root / DNA_INDEX
    preserved = 0
    if public.exists() and not private.exists():
        private.parent.mkdir(parents=True, exist_ok=True)
        copy2(public, private)
        preserved = 1
    if not private.exists():
        raise FileNotFoundError(f"missing preserved DNA index: {private}")
    approval = restoration_entries(private_root).get(DNA_INDEX)
    if approval:
        rendered = restoration_source(approval)
        written = int(not public.exists() or public.read_text() != rendered)
        if written:
            public.write_text(rendered)
        return preserved, written
    safe = "[]\n"
    written = 0
    if not public.exists() or public.read_text(encoding="utf-8") != safe:
        public.parent.mkdir(parents=True, exist_ok=True)
        public.write_text(safe, encoding="utf-8")
        written = 1
    return preserved, written


def repair(web: Path = WEB, private_root: Path = PRIVATE_ROOT) -> dict[str, int]:
    """Archive tester-level assets before withdrawing their public copies."""
    changed = {
        "withheld_assets": _preserve_then_withhold(web, private_root),
        "preserved_pages": _preserve_pages(web, private_root),
        "preserved_dna_index": 0,
        "safe_dna_index": 0,
        "safe_pages": 0,
        "approved_lines": 0,
        "atlas_models": 0,
        "atlas_renderers": 0,
        "onetree_snapshot": 0,
    }
    changed["preserved_dna_index"], changed["safe_dna_index"] = _preserve_dna_index(web, private_root)
    source_page = web / "ydna/glasgow-ydna-story-source/index.html"
    public_page = web / "ydna/index.html"
    study = private_root / "ydna/glasgow-ydna-story-source/data.json"
    if not study.exists():
        raise FileNotFoundError(f"missing preserved Y-DNA study input: {study}")
    data = json.loads(study.read_text(encoding="utf-8"))
    changed["approved_lines"] = restore_lines(web, private_root)
    for page, noindex in ((source_page, True), (public_page, False)):
        rendered = ydna_build.render(
            data,
            canonical="https://glasgow.phenotype.dev/ydna/",
            noindex=noindex,
        )
        if not page.exists() or page.read_text(encoding="utf-8") != rendered:
            page.parent.mkdir(parents=True, exist_ok=True)
            page.write_text(rendered, encoding="utf-8")
            changed["safe_pages"] += 1
    changed["atlas_models"], changed["atlas_renderers"] = _repair_atlas_assets(web, private_root)
    changed["onetree_snapshot"] = _repair_onetree_snapshot_badge(web)
    return changed


def audit(web: Path = WEB, private_root: Path = PRIVATE_ROOT) -> list[str]:
    """Report publication-policy drift without reading or printing source values."""
    failures: list[str] = []
    study = private_root / "ydna/glasgow-ydna-story-source/data.json"
    curated = study.exists() and study_is_approved(json.loads(study.read_text(encoding="utf-8")), private_root)
    if curated:
        failures.extend(audit_approved_research(web, private_root))
    if restoration_entries(private_root):
        return failures
    identifiers = private_tester_ids(private_root)
    for relative in WITHHELD_ASSETS:
        if (web / relative).exists():
            failures.append(relative)
        if not (private_root / relative).exists():
            failures.append(f"private archive: {relative}")
    index = web / DNA_INDEX
    if not (private_root / DNA_INDEX).exists():
        failures.append(f"private archive: {DNA_INDEX}")
    if not index.exists() or index.read_text(encoding="utf-8") != "[]\n":
        failures.append(f"unsafe DNA index: {DNA_INDEX}")
    for relative in SAFE_PAGES:
        if not (private_root / relative).exists():
            failures.append(f"private archive: {relative}")
        path = web / relative
        if not path.exists():
            failures.append(relative)
            continue
        page = path.read_text(encoding="utf-8")
        if not curated and "tester-level genetic data" not in page:
            failures.append(f"unsafe summary: {relative}")
        if not curated and any(identifier in page for identifier in identifiers):
            failures.append(f"tester identifier in {relative}")
    for relative in ATLAS_MODELS:
        path = web / relative
        if not (private_root / relative).exists():
            failures.append(f"private archive: {relative}")
        if not path.exists():
            failures.append(relative)
            continue
        try:
            model = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            failures.append(f"invalid atlas model: {relative}")
            continue
        if model.get("dna") != [] or model.get("meta", {}).get("dnaCoverage") != DNA_COVERAGE:
            failures.append(f"unsafe atlas model: {relative}")
    for relative in ATLAS_RENDERERS:
        path = web / relative
        if not (private_root / relative).exists():
            failures.append(f"private archive: {relative}")
        if not path.exists():
            failures.append(relative)
            continue
        page = path.read_text(encoding="utf-8")
        if any(token in page for token in (
            "repair-tester-panel", "repair-tester-row", "data-dna-search", "d.kits",
            "$('#dna-toggle').classList", "$('#dna-toggle').setAttribute",
            "id=\"dna-total\"", "Y-DNA pins", "Numbered Y-DNA ancestor markers",
        )):
            failures.append(f"tester detail in {relative}")
        if relative not in {"assets/repair/atlas.js", "onetree/index.html"} and "Individual test results and tester-level relationships" not in page:
            failures.append(f"unsafe atlas renderer: {relative}")
        if relative in ATLAS_HTML_RENDERERS:
            css = PUBLIC_DNA_SUMMARY_CSS.read_text(encoding="utf-8")
            if f'<style data-public-dna-summary>\n{css}</style>' not in page:
                failures.append(f"missing public DNA contrast CSS: {relative}")
    model = json.loads((web / "assets/research/atlas-model.json").read_text(encoding="utf-8"))
    imported = date.fromisoformat(str(model.get("meta", {}).get("catalogueGenerated", ""))[:10])
    badge = f"Atlas · {imported.day} {imported.strftime('%b')} {imported.year}"
    title = (
        f"Atlas imported catalogue snapshot: {imported.day} {imported.strftime('%B')} "
        f"{imported.year}; current catalogue has separate updates."
    )
    onetree = (web / "onetree/index.html").read_text(encoding="utf-8")
    if badge not in onetree or title not in onetree:
        failures.append("unsafe OneTree snapshot badge")
    return failures


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Check policy artifacts without changing them")
    args = parser.parse_args()
    if args.check:
        failures = audit()
        print(f"Public DNA policy: {len(failures)} failures")
        for failure in failures:
            print(f"FAIL {failure}")
        raise SystemExit(bool(failures))
    print(repair())
