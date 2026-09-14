"""Write a compact QA report for maintained dossier assessment coverage."""
from __future__ import annotations

import json
from pathlib import Path

try:
    from dossier_resolution import assessment_coverage, resolve_presentation
except ModuleNotFoundError:
    from tools.dossier_resolution import assessment_coverage, resolve_presentation

ROOT = Path(__file__).resolve().parents[1]
PROFILE_IDS = ["Glasgow-951", "Glasgow-3167", "Glasgow-987", "Glasgow-1367", "Glasgow-3939", "McCaughan-222"]


def load(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def build() -> dict:
    rows = []
    for profile_id in PROFILE_IDS:
        dossier = load(ROOT / "www/people" / f"{profile_id.casefold()}.json", {})
        model = load(ROOT / "www/assets/research/people" / f"{profile_id.casefold()}.json", {})
        authored = load(ROOT / "research" / profile_id / "presentation.json", {})
        presentation = resolve_presentation(profile_id, dossier, model, authored)
        row = assessment_coverage(profile_id, dossier, presentation)
        row["current_conclusion_findings"] = [
            {"source": source, "date": updated}
            for finding in dossier.get("research_findings") or []
            for source, updated in [(finding.get("source_path"), finding.get("updated"))]
            if source
        ]
        rows.append(row)
    return {"generated_by": "tools/build_dossier_coverage_report.py", "profiles": rows}


if __name__ == "__main__":
    output = ROOT / "artifacts/dossier-assessment-coverage.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(build(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(output)
