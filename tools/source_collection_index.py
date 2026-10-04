"""Build a bounded, public source collection index without writing files."""

from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urlparse

_YEAR = re.compile(r"(?<!\d)(1[0-9]{3}|20[0-9]{2})(?!\d)")
_URL = re.compile(r"^https?://", re.I)
_SIGNED = re.compile(r"(?:token|signature|sig|expires|secur|download|auth|credential|jwt)=", re.I)

_CATEGORIES = {
    "newspapers": r"\bnewspaper\b|\bgazette\b|\bsentinel\b|\bherald\b|\bchronicle\b|\badvertiser\b|\bjournal\b|\btimes\b",
    "census": r"\bcensus\b|enumeration",
    "births": r"birth|baptis|christen",
    "marriages": r"marriage|married|banns|wedding",
    "deaths": r"death|burial|obituar|grave|cemeter|memorial",
    "wills-probate": r"\bwill\b|testament|probate|dative",
    "land-tax": r"\bland\b|\bdeed\b|\bestate\b|\bvaluation\b|\btax\b|rent roll",
    "church": r"parish|church|register",
    "military": r"military|army|navy|regiment|service record|war",
    "directories": r"directory|directories",
    "education": r"school|college|university|student",
    "histories": r"\bhistory\b|\bhistorical\b|\bbiograph(?:y|ies)\b",
    "pedigrees": r"wikitree|profile export|family tree|\bgenealog(?:y|ical)\b|\bpedigree\b",
}
_COUNTRIES = {
    "Scotland": r"\bscotland\b|\bscottish\b|\blanarkshire\b|\bedinburgh\b|\bayrshire\b|\bwest lothian\b|\bmidlothian\b|\bscotland['’]?s people\b|\bnrs\b",
    "Ireland": r"\bireland\b|\birish\b|\bantrim\b|\btyrone\b|\blondonderry\b|\bderry\b|\bcork\b|\bdublin\b",
    "England": r"\bengland\b|\benglish\b|\blondon\b|\byorkshire\b|\blancashire\b",
    "United States": r"\bunited states\b|\bu\.s\.?a?\.?\b|\bpennsylvania\b|\bohio\b|\bvirginia\b|\balabama\b|\btennessee\b|\btexas\b|\bnorth carolina\b|\bnew york\b",
    "Canada": r"\bcanada\b|\bontario\b|\bnova scotia\b|\bnew brunswick\b",
    "New Zealand": r"\bnew zealand\b",
    "Australia": r"\baustralia\b|\bnew south wales\b|\bvictoria\b",
}


def _text(doc: dict) -> str:
    bits = [str(doc.get("title") or ""), str(doc.get("url") or "")]
    for key in ("citations", "records", "events"):
        rows = doc.get(key) or []
        if not isinstance(rows, list):
            continue
        for row in rows:
            bits.append(" ".join(str(row.get(k) or "") for k in ("type", "source", "reference", "title", "label", "association", "place", "date")))
    return " ".join(bits)


def _classification_text(doc: dict) -> str:
    """Text naming the source, excluding facts merely recorded in events."""
    bits = [str(doc.get("title") or ""), str(doc.get("url") or "")]
    for key in ("citations", "records"):
        rows = doc.get(key) or []
        if not isinstance(rows, list):
            continue
        for row in rows:
            bits.append(" ".join(str(row.get(k) or "") for k in ("source", "reference", "title", "label")))
    return " ".join(bits)


def _safe_url(value: object) -> str | None:
    url = str(value or "")
    parsed = urlparse(url)
    if not _URL.match(url) or parsed.username or parsed.password or _SIGNED.search(parsed.query):
        return None
    return url


_DATE_TYPES = {
    "census": r"census|enumeration",
    "births": r"birth|baptis|christen",
    "marriages": r"marriage|married|banns|wedding",
    "deaths": r"death|burial|obituar|grave|cemeter|memorial",
    "wills-probate": r"will|testament|probate|dative",
}


def _years(doc: dict, text: str, categories: list[str]) -> tuple[int | None, str]:
    if re.search(r"\bwikitree\b|profile export|tree-only|family tree", _classification_text(doc), re.I):
        return None, "unknown"
    title = re.sub(r"\b[A-Za-z][A-Za-z'-]*-\d+\b", "", str(doc.get("title") or ""))
    title_years = [int(x) for x in _YEAR.findall(title)]
    if len(set(title_years)) == 1:
        return title_years[0], "source title"
    if title_years:
        return None, "unknown"
    dated = []
    patterns = [re.compile(_DATE_TYPES[category], re.I) for category in categories if category in _DATE_TYPES]
    if not patterns:
        return None, "unknown"
    for key in ("records", "citations", "events"):
        rows = doc.get(key) or []
        if not isinstance(rows, list):
            continue
        for row in rows:
            row_text = " ".join(str(row.get(k) or "") for k in ("type", "source", "reference", "title", "label", "association"))
            if any(pattern.search(row_text) for pattern in patterns):
                dated.extend(int(x) for x in _YEAR.findall(str(row.get("date") or "")))
    if len(set(dated)) == 1:
        return dated[0], "record dates"
    return None, "unknown"


def _classify(doc: dict) -> list[str]:
    text = _classification_text(doc).lower()
    profile = bool(re.search(r"\bwikitree\b|profile export|tree-only|family tree", text))
    found = [name for name, pattern in _CATEGORIES.items() if re.search(pattern, text, re.I)]
    # Biography mentions of BMD facts must not turn a profile wrapper into a BMD source.
    if profile:
        found = [x for x in found if x == "pedigrees"]
        if "pedigrees" not in found:
            found.append("pedigrees")
    return found or ["other"]


def _values(doc: dict, field: str) -> list[str]:
    out = []
    for key in ("citations", "records", "events"):
        rows = doc.get(key) or []
        if not isinstance(rows, list):
            continue
        for row in rows:
            value = row.get(field)
            if value and str(value) not in out:
                out.append(str(value))
    return out


def build_index(web: Path) -> list[dict]:
    """Return normalized public source items from the generated public assets."""
    root = Path(web)
    rows = json.loads((root / "assets/v3/source-index.json").read_text(encoding="utf-8"))
    result = []
    for row in rows:
        detail = root / "assets/v3/sources" / (row["id"] + ".json")
        doc = json.loads(detail.read_text(encoding="utf-8")) if detail.exists() else dict(row)
        text = _text(doc)
        original_url = _safe_url(doc.get("url"))
        categories = _classify(doc)
        profile = "pedigrees" in categories and len(categories) == 1
        places = _values(doc, "place")[:8]
        jurisdiction_text = " ".join([str(doc.get("title") or ""), *places, *_values(doc, "source"), *_values(doc, "reference"), str(doc.get("url") or "")])
        countries = [name for name, pattern in _COUNTRIES.items() if re.search(pattern, jurisdiction_text, re.I)]
        if any(re.search(r"^glasgow(?:,|\s|$)", place, re.I) for place in places) and "Scotland" not in countries:
            countries.append("Scotland")
        year, year_basis = _years(doc, text, categories)
        result.append({
            "id": row["id"], "title": row.get("title") or doc.get("title") or "",
            "categories": categories, "year": year, "year_basis": year_basis,
            "countries": countries, "places": places, "members": row.get("members") or [],
            "records": row.get("records") or 0, "citations": row.get("citations") or 0,
            "image": bool(row.get("image") or doc.get("image")),
            "transcription": bool(row.get("transcription") or doc.get("transcription")),
            "original_url": original_url,
            "original_kind": "profile" if profile else ("record or provider" if original_url else "none"),
        })
    return result
