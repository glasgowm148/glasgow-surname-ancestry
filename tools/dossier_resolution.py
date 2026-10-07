"""Resolve maintained person research before the shared dossier renderer.

This is deliberately conservative: an explicit authored presentation or an
approved structured assessment wins.  A canonical ``Current conclusion``
finding is publishable research, but it is recorded as finding-backed rather
than silently promoted to a structured relationship decision.
"""
from __future__ import annotations

from copy import deepcopy
import re


def _plain(markdown: str) -> str:
    text = re.sub(r"!?(\[)([^\]]+)(\])\([^)]*\)", r"\2", markdown or "")
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"[`*_#]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _summary(markdown: str) -> str:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", markdown or "") if p.strip()]
    if not paragraphs:
        return ""
    return _plain(paragraphs[0])


def current_findings(dossier: dict) -> list[dict]:
    found = []
    for finding in dossier.get("research_findings") or []:
        for section in finding.get("sections") or []:
            title = str(section.get("title") or "").strip().casefold()
            category = str(section.get("category") or "").strip().casefold()
            if title == "current conclusion" or category == "conclusion":
                found.append({**section, "canonical": _is_canonical_conclusion(title),
                              "finding_updated": finding.get("updated"), "source_path": finding.get("source_path")})
    return found


def _is_canonical_conclusion(title: str) -> bool:
    """True for the one overall conclusion of a file.

    ``Current conclusion — newspaper identity review, 6 October 2026`` and
    similar dated or topic headings are additions made by a later review.
    They add to the overall conclusion; they do not compete with it.
    """
    title = re.sub(r"\s+", " ", title or "").strip().casefold()
    if title in {"current conclusion", "conclusion", "current answer"}:
        return True
    return title.startswith("current conclusion") and not re.search(r"[—–:,-]|\d{4}", title)


def resolve_presentation(profile_id: str, dossier: dict, model: dict, authored: dict | None = None) -> dict:
    """Return presentation data plus a non-ambiguous assessment resolution.

    ``state`` is one of ``none``, ``resolved``, ``conflict`` or ``unmapped``.
    The latter means research exists but no maintained presentation has yet
    mapped it into claims; it must never render as no assessment exists.
    """
    authored = deepcopy(authored or {})
    approved = [a for a in dossier.get("research_assessments") or []
                if str(a.get("subject") or profile_id).casefold() == profile_id.casefold()
                and a.get("status") == "approved"]
    findings = current_findings(dossier)
    issues = []
    state = "none"
    basis = []
    summary = ""
    assessment_date = authored.get("assessment_date") or ""

    if len(approved) > 1:
        summaries = {str(a.get("summary") or "").strip() for a in approved}
        if len(summaries) > 1:
            state = "conflict"
            issues.append("More than one approved assessment has a different summary; editorial reconciliation is required.")
        else:
            state = "resolved"
    elif approved:
        state = "resolved"
    elif findings:
        # This is an explicit maintained heading from the research catalogue,
        # not an inference from the newest arbitrary note.
        canonical = [f for f in findings if f.get("canonical")]
        addenda = [f for f in findings if not f.get("canonical")]
        if len(canonical) > 1:
            state = "conflict"
            issues.append("More than one canonical current-conclusion finding is available; the page must identify which scope controls.")
        elif canonical or len(addenda) == 1:
            # One overall conclusion, with any dated topic reviews as additions.
            state = "resolved"
            primary = (canonical or addenda)[0]
            findings = [primary] + [f for f in findings if f is not primary]
        else:
            # Several dated topic reviews and no overall conclusion: research
            # exists, but nobody has written the summary yet. Not a conflict.
            state = "unmapped"
            issues.append("Dated topic conclusions are recorded, but no overall conclusion has been written.")

    if approved:
        basis.append("approved structured assessment")
        summary = str(approved[-1].get("summary") or "").strip()
        assessment_date = assessment_date or str(approved[-1].get("reviewed") or "")
    elif findings and state == "resolved":
        basis.append("maintained Current conclusion finding")
        summary = _summary(findings[0].get("markdown") or "")
        assessment_date = assessment_date or str(findings[0].get("finding_updated") or "")
    elif findings and state == "conflict":
        basis.append("conflicting Current conclusion findings")
    elif findings:
        basis.append("dated topic conclusions without an overall conclusion")

    if not authored and not approved and not findings:
        if dossier.get("research_leads") or dossier.get("evidence") or dossier.get("open_questions"):
            state = "unmapped"
            basis.append("research or leads exist, but no maintained presentation is mapped")
            issues.append("Research is present in the dossier but has not been mapped into a publication-safe maintained presentation.")

    authored_has_mapping = any(
        authored.get(key)
        for key in (
            "position",
            "opening",
            "evidence_questions",
            "record_evidence",
            "family_display",
            "research_tasks",
            "completed_searches",
        )
    )

    if authored:
        result = authored
        # Authored presentation is the deliberate publication mapping.  It
        # may still expose a conflict explicitly rather than hiding it.
        if authored.get("resolution_state"):
            state = authored["resolution_state"]
        if authored.get("resolution_issue"):
            issues.append(str(authored["resolution_issue"]))
        # Older presentation files used ``unmapped`` as a placeholder even
        # after their current position and evidence questions had been
        # written.  That is not an unresolved historical assessment: the
        # publication layer is already mapped.  Keep genuinely unmapped
        # research distinct when no authored claim exists.
        if authored_has_mapping and state == "unmapped":
            state = "resolved"
            basis.append("authored publication mapping")
    else:
        result = {}

    if state == "conflict" and not result.get("position"):
        result["position"] = {"answer": "Maintained assessments conflict and require editorial reconciliation.", "points": []}
    elif not result.get("position") and summary:
        result["position"] = {"answer": summary, "points": []}
    elif state == "unmapped" and not result.get("position"):
        result["position"] = {"answer": "Research is present, but no maintained conclusion has yet been resolved for publication.", "points": []}
    elif state == "none" and not result.get("position"):
        result["position"] = {"answer": "No maintained assessment is recorded.", "points": []}

    if not result.get("opening") and summary:
        result["opening"] = summary
    if not assessment_date and result.get("assessment_date"):
        assessment_date = str(result["assessment_date"])
    result["assessment_date"] = assessment_date
    result["resolution"] = {
        "state": state,
        "basis": basis,
        "issues": issues,
        "source_ids": [str(a.get("id")) for a in approved if a.get("id")]
                      + [str(f.get("source_path")) for f in findings if f.get("source_path")],
        "additions": [str(f.get("title")) for f in findings if not f.get("canonical") and f.get("title")],
    }
    return result


def assessment_coverage(profile_id: str, dossier: dict, presentation: dict) -> dict:
    resolution = presentation.get("resolution") or {}
    displayed = []
    if presentation.get("position"):
        displayed.append("overview/current-position")
    for question in presentation.get("evidence_questions") or []:
        displayed.append(f"evidence/question-{question.get('id')}")
    return {
        "profile_id": profile_id,
        "state": resolution.get("state", "none"),
        "assessment_sources": resolution.get("source_ids", []),
        "displayed_sections": displayed,
        "superseded": presentation.get("superseded_interpretations", []),
        "deliberate_exclusions": presentation.get("deliberate_exclusions", []),
        "issues": resolution.get("issues", []),
    }
