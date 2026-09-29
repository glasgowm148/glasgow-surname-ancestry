"""Exact publication approval for the previously curated Y-DNA study.

This exception covers the retained study. Additional restored publications
have their own exact source approvals; raw sequences remain private.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / "data/private/withheld-public-assets"
APPROVAL = ROOT / "research/ydna-publication-approval.json"
STUDY = "ydna/glasgow-ydna-story-source/data.json"
LINES = "assets/research/dna-index.json"
PAGES = ("ydna/index.html", "ydna/glasgow-ydna-story-source/index.html")


def approved_inputs(private: Path = PRIVATE) -> dict[str, object] | None:
    """Validate the approved original bytes; never expand to other private inputs."""
    if not APPROVAL.exists():
        return None
    approval = json.loads(APPROVAL.read_text(encoding="utf-8"))
    if approval.get("schema_version") != 1 or approval.get("scope") != "previous-curated-ydna-study":
        raise ValueError("invalid curated Y-DNA publication approval")
    entries = {item["path"]: item["sha256"] for item in approval["inputs"]}
    if set(entries) != {STUDY, LINES} or approval.get("public_pages") != list(PAGES):
        raise ValueError("curated Y-DNA approval has unexpected scope")
    if approval.get("public_assets") != [{"path": "ydna/lines.json", "source": LINES}]:
        raise ValueError("curated Y-DNA approval has unexpected asset scope")
    # Temporary fixtures and other repositories have no approval for their data.
    if private.resolve() != PRIVATE.resolve():
        return None
    values = {}
    for relative, digest in entries.items():
        content = (private / relative).read_bytes()
        if hashlib.sha256(content).hexdigest() != digest:
            raise ValueError(f"approved Y-DNA input changed: {relative}")
        values[relative] = json.loads(content)
    return values


def study_is_approved(data: dict[str, object], private: Path = PRIVATE) -> bool:
    inputs = approved_inputs(private)
    return inputs is not None and inputs[STUDY] == data


def approved_document(relative: str, content: str, private: Path = PRIVATE) -> bool:
    """Scope the tester exception to the exact approved payload and destinations."""
    if relative not in {*PAGES, "ydna/lines.json"}:
        try:
            from tools.approved_restorations import approved_document as restored_document
        except ModuleNotFoundError:
            from approved_restorations import approved_document as restored_document
        return restored_document(relative, content, private)
    inputs = approved_inputs(private)
    if inputs is None:
        return False
    try:
        if relative == "ydna/lines.json":
            return json.loads(content) == inputs[LINES]
        match = re.search(r'<script\b[^>]*\bid="research-data"[^>]*>([\s\S]*?)</script>', content)
        return bool(match) and json.loads(match[1]) == inputs[STUDY]
    except ValueError:
        return False


def restore_lines(web: Path, private: Path = PRIVATE) -> int:
    inputs = approved_inputs(private)
    if inputs is None:
        return 0
    target = web / "ydna/lines.json"
    content = (private / LINES).read_bytes()
    if target.exists() and target.read_bytes() == content:
        return 0
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)
    return 1


def audit_approved_research(web: Path, private: Path = PRIVATE) -> list[str]:
    try:
        inputs = approved_inputs(private)
    except (OSError, ValueError, KeyError) as error:
        return [f"Y-DNA approval: {error}"]
    if inputs is None:
        return []
    failures = []
    for relative in PAGES:
        path = web / relative
        page = path.read_text(encoding="utf-8") if path.exists() else ""
        match = re.search(r'<script\b[^>]*\bid="research-data"[^>]*>([\s\S]*?)</script>', page)
        try:
            actual = json.loads(match[1]) if match else None
        except ValueError:
            actual = None
        if actual != inputs[STUDY]:
            failures.append(f"approved Y-DNA study missing or changed: {relative}")
    path = web / "ydna/lines.json"
    if not path.exists() or path.read_bytes() != (private / LINES).read_bytes():
        failures.append("approved Y-DNA documentary lines missing or changed")
    try:
        from tools.approved_restorations import audit as audit_restorations
    except ModuleNotFoundError:
        from approved_restorations import audit as audit_restorations
    failures.extend(audit_restorations(web, private))
    return failures
