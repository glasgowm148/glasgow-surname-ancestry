"""Fail a release containing withheld identities, raw captures or tracking."""
from pathlib import Path
from html import unescape
import json
import re

try:
    from public_privacy import from_sources, public_capture
    from site_analytics import audit as analytics_audit
    from repair_public_dna import WITHHELD_ASSETS, ATLAS_MODELS, DNA_INDEX
    from public_manuscript_previews import audit_approved_previews
    from public_ydna_research import audit_approved_research, approved_document
except ModuleNotFoundError:
    from tools.public_privacy import from_sources, public_capture
    from tools.site_analytics import audit as analytics_audit
    from tools.repair_public_dna import WITHHELD_ASSETS, ATLAS_MODELS, DNA_INDEX
    from tools.public_manuscript_previews import audit_approved_previews
    from tools.public_ydna_research import audit_approved_research, approved_document

ROOT = Path(__file__).resolve().parents[1]


def capture_issues(value):
    issues = set()
    if isinstance(value, dict):
        if "profile_id" in value:
            if any(key in value for key in ("biography_text", "biography_wikitext", "record_passages")):
                issues.add("Raw capture")
            if not public_capture(value):
                issues.add("Restricted capture")
        for child in value.values():
            issues.update(capture_issues(child))
    elif isinstance(value, list):
        for child in value:
            issues.update(capture_issues(child))
    return issues


def embedded_json(text):
    """Inspect JSON objects in cached HTML/data scripts without executing code."""
    decoder, end = json.JSONDecoder(), 0
    for match in re.finditer(r"[\[{]", text):
        if match.start() < end:
            continue
        try:
            value, end = decoder.raw_decode(text, match.start())
        except json.JSONDecodeError:
            continue
        yield value


def audit(web=ROOT / "www", policy=None):
    policy = policy or from_sources()
    failures = []
    for relative in WITHHELD_ASSETS:
        if (web / relative).exists():
            path = web / relative
            if not approved_document(str(relative), path.read_text()):
                failures.append(f"Withheld asset remains: {relative}")
    failures.extend(audit_approved_previews(web))
    failures.extend(audit_approved_research(web))
    for relative in ATLAS_MODELS:
        path = web / relative
        if path.exists() and json.loads(path.read_text()).get("dna") and not approved_document(relative, path.read_text()):
            failures.append(f"Individual DNA annotations remain: {relative}")
    dna_index = web / DNA_INDEX
    if dna_index.exists() and json.loads(dna_index.read_text()) != [] and not approved_document(DNA_INDEX, dna_index.read_text()):
        failures.append(f"Individual DNA index remains: {DNA_INDEX}")
    for path in web.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {".html", ".json", ".js", ".csv", ".txt", ".md"}:
            continue
        text = path.read_text(encoding="utf-8")
        approved = approved_document(path.relative_to(web).as_posix(), text)
        if policy.contains_private_id(text, include_testers=not approved):
            failures.append(f"Withheld identifier remains: {path.relative_to(web)}")
        if path.suffix == ".html" and re.search(r'<article\b[^>]*\brepair-tester-row\b', text) and not approved:
            failures.append(f"Individual DNA panel remains: {path.relative_to(web)}")
        decoded = unescape(text) if path.suffix == ".html" and "profile_id" in text else text
        values = [json.loads(text)] if path.suffix == ".json" else embedded_json(decoded) if '"profile_id"' in decoded else []
        issues = set().union(*(capture_issues(value) for value in values))
        failures.extend(f"{issue} remains: {path.relative_to(web)}" for issue in sorted(issues))
    _, analytics_failures = analytics_audit(web)
    failures.extend(f"Missing or duplicate analytics tag: {path}" for path in analytics_failures)
    return failures


if __name__ == "__main__":
    failures = audit()
    print(f"Publication boundary: {len(failures)} failures")
    for failure in failures:
        print(failure)
    raise SystemExit(bool(failures))
