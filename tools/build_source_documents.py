#!/usr/bin/env python3
"""Produce the source library documents (``www/assets/v3/sources/``) from the dossiers.

Each source document groups the citations that cite one source: by its URL, or,
for a citation without a URL, by its text within one person's dossier. Its
citations are the dossiers' own evidence entries (``www/people/<id>.json``,
written by the catalogue from the WikiTree captures), so they are produced
here rather than carried forward from an earlier build:

* every existing document keeps its id, title, reference, repository and record
  entries; new sources get ``s-`` plus the first 16 hex digits of the SHA-256 of
  their grouping key;
* dossier citations (``E-`` plus 12 hex digits) are rebuilt from the dossiers,
  and those no dossier has any more are dropped;
* citations the canonical-record ingest adds (``E-`` plus 16 hex digits) are
  kept as they are; the ingest maintains them;
* no document is deleted, and the source index (``source-index.json``) is
  updated to match;
* a dossier the privacy policy withholds (using every export) contributes no
  citations.

New sources get their page from the ingest's standard page shell. Run with
``--check`` to report what would change.

    .venv/bin/python tools/build_source_documents.py [--check]
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from hashlib import sha256
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
DOSSIER_EVIDENCE = re.compile(r"E-[0-9a-f]{12}")
YEAR = re.compile(r"(?<!\d)(1[0-9]{3}|20[0-9]{2})(?!\d)")
BASIS_URL, BASIS_TEXT = "exact source URL", "citation text within this dossier"
DATE_BASIS = "dates associated with this source, not necessarily the document date"


def citation(person: str, name: str, evidence: dict, claims: dict[str, dict]) -> dict:
    return {"person": person, "name": name, "evidence_id": evidence.get("id"), "type": evidence.get("record_type"),
            "date": evidence.get("date"), "place": evidence.get("place"), "assertion": evidence.get("assertion"),
            "status": evidence.get("evidence_status"), "quality": evidence.get("source_quality"),
            "independence_group": evidence.get("independence_group"), "source": evidence.get("source"),
            "claims": [claims[i] for i in evidence.get("claim_ids") or [] if i in claims]}


def carry_date_correction(fresh: dict, old: dict | None) -> dict:
    """Keep a correction ``repair_assessment_dates`` made while the dossier still has the corrected date."""
    correction = (old or {}).get("date_correction")
    if correction and all(fresh.get(k) == v for k, v in correction.get("previous", {}).items() if k in fresh):
        fresh = {**fresh, **{k: None for k in correction.get("previous", {}) if k in fresh}, "date_correction": correction}
    return fresh


def group_key(source: dict, person: str) -> tuple:
    url = (source or {}).get("url")
    return ("url", url) if url else ("text", person, (source or {}).get("title") or "")


def document_key(doc: dict) -> tuple | None:
    cited = [c for c in doc.get("citations", []) if DOSSIER_EVIDENCE.fullmatch(str(c.get("evidence_id")))]
    if doc.get("grouping_basis") == BASIS_URL and doc.get("url"):
        return ("url", doc["url"])
    if doc.get("grouping_basis") == BASIS_TEXT and cited:
        return group_key(cited[0].get("source"), cited[0].get("person"))
    return None


def privacy_policy():
    try:
        from public_privacy import from_sources
    except ModuleNotFoundError:
        from tools.public_privacy import from_sources
    return from_sources(all_exports=True) if (ROOT / "data").is_dir() else None


def dossier_citations(web: Path, policy=None) -> dict[tuple, list[dict]]:
    """Citations from every dossier, leaving out anyone the privacy policy withholds."""
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for path in sorted((web / "people").glob("*.json")):
        if path.name.endswith(".network.json"):
            continue
        try:
            dossier = json.loads(path.read_text(encoding="utf-8"))
        except ValueError:
            continue
        if not isinstance(dossier, dict):
            continue
        person = path.stem
        if dossier.get("likely_living") or dossier.get("withheld") or (policy and person in policy.blocked):
            continue
        claims = {claim.get("id"): claim for claim in dossier.get("claims") or [] if isinstance(claim, dict)}
        for evidence in dossier.get("evidence") or []:
            if DOSSIER_EVIDENCE.fullmatch(str(evidence.get("id"))):
                groups[group_key(evidence.get("source"), person)].append(
                    citation(person, dossier.get("name"), evidence, claims))
    return groups


def _years(doc: dict) -> list[int]:
    values = [c.get("date") for c in doc.get("citations", [])]
    values += [r.get("year") if isinstance(r.get("year"), int) else r.get("date") for r in doc.get("records", [])
               if isinstance(r, dict)]
    years = []
    for value in values:
        if isinstance(value, int):
            years.append(value)
        elif value:
            found = YEAR.search(str(value))
            if found:
                years.append(int(found[1]))
    return years


def index_row(doc: dict, previous: dict | None, changed: bool) -> dict:
    years = _years(doc)
    span = (min(years), max(years)) if years else (None, None)
    if previous and not changed:
        span = (previous.get("from"), previous.get("to"))
    return {"id": doc["id"], "title": doc.get("display_title") or doc.get("title"), "members": doc.get("members", []),
            "records": len(doc.get("records", [])), "citations": len(doc.get("citations", [])),
            "from": span[0], "to": span[1], "image": bool(doc.get("image")),
            "transcription": doc.get("transcription") not in (None, "", "[]"),
            "basis": doc.get("grouping_basis"), "date_basis": doc.get("date_basis") or DATE_BASIS}


def build(web: Path, policy=None) -> tuple[dict[str, dict], list[dict], Counter]:
    """Return (documents to write, the new index, counts); writes nothing."""
    sources = web / "assets/v3/sources"
    index = json.loads((web / "assets/v3/source-index.json").read_text(encoding="utf-8"))
    previous = {row["id"]: row for row in index}
    docs = {path.stem: json.loads(path.read_text(encoding="utf-8")) for path in sorted(sources.glob("s-*.json"))}
    by_key = {key: sid for sid, doc in docs.items() if (key := document_key(doc))}
    current = dossier_citations(web, policy)
    counts: Counter = Counter()
    changed: dict[str, dict] = {}
    for key, cited in current.items():
        sid = by_key.get(key)
        if sid is None:
            sid = "s-" + sha256(json.dumps(key, ensure_ascii=False).encode()).hexdigest()[:16]
            if sid in docs:
                raise ValueError(f"source id collision for {key!r}")
            source = cited[0].get("source") or {}
            title = " ".join(str(source.get("title") or "Source item").split())
            docs[sid] = {"id": sid, "title": title, "display_title": title, "url": source.get("url") or "",
                         "reference": source.get("reference") or "", "repository": source.get("repository") or "",
                         "grouping_basis": BASIS_URL if key[0] == "url" else BASIS_TEXT, "members": [],
                         "citations": [], "records": [], "events": [], "annotations": {},
                         "annotation_status": "No line-to-image annotation supplied", "date_basis": DATE_BASIS,
                         "image": None, "transcription": "[]", "is_collection": False}
            by_key[key] = sid
            counts["new sources"] += 1
    wanted = {sid: current.get(key, []) for key, sid in by_key.items()}
    for sid, doc in docs.items():
        kept = [c for c in doc.get("citations", []) if not DOSSIER_EVIDENCE.fullmatch(str(c.get("evidence_id")))]
        fresh = wanted.get(sid, [])
        old = {(c.get("person"), c.get("evidence_id")): c for c in doc.get("citations", [])
               if DOSSIER_EVIDENCE.fullmatch(str(c.get("evidence_id")))}
        order = [k for k in old if k in {(c["person"], c["evidence_id"]) for c in fresh}]
        order += [(c["person"], c["evidence_id"]) for c in fresh if (c["person"], c["evidence_id"]) not in old]
        by_id = {(c["person"], c["evidence_id"]): carry_date_correction(c, old.get((c["person"], c["evidence_id"])))
                 for c in fresh}
        citations = [by_id[k] for k in order] + kept
        if citations == doc.get("citations", []):
            continue
        dropped = len(old) - len(set(old) & set(by_id))
        counts["stale dossier citations dropped"] += dropped
        members = [m for m in doc.get("members", []) if m in {c.get("person") for c in citations}
                   or m in {r.get("person_id") or r.get("catalogue_id") for r in doc.get("records", []) if isinstance(r, dict)}]
        members += [c["person"] for c in citations if c.get("person") and c["person"] not in members]
        updated = {**doc, "citations": citations, "members": members, "citation_count": len(citations),
                   "record_count": len(doc.get("records", []))}
        changed[sid] = updated
        counts["documents updated"] += 1
    rows = [index_row(changed.get(row["id"], docs[row["id"]]), row, row["id"] in changed) for row in index
            if row["id"] in docs]
    rows += [index_row(changed[sid], None, True) for sid in changed if sid not in previous]
    return changed, rows, counts


def write(web: Path, changed: dict[str, dict], rows: list[dict]) -> list[str]:
    """Write the documents, the index and a standard page for each new source."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from ingest_canonical_records import packed_source_index, source_browse_pages, source_page  # noqa: E402
    template = next(iter(sorted((web / "sources").glob("s-*/index.html"))), None)
    pages = []
    for sid, doc in changed.items():
        (web / "assets/v3/sources" / f"{sid}.json").write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
        page = web / "sources" / sid / "index.html"
        if not page.exists() and template is not None:
            page.parent.mkdir(parents=True, exist_ok=True)
            page.write_text(source_page(template.read_text(encoding="utf-8"), doc, site_root=web), encoding="utf-8")
            pages.append(page.relative_to(web).as_posix())
    (web / "assets/v3/source-index.json").write_text(json.dumps(rows, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    # The packed index and the complete no-script browse pages follow the index, as after an ingest.
    (web / "assets/v3/source-index-packed.json").write_text(
        json.dumps(packed_source_index(rows), ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    for path, text in source_browse_pages(web, rows).items():
        if not path.exists() or path.read_text(encoding="utf-8") != text:
            path.write_text(text, encoding="utf-8")
    return pages


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--web", type=Path, default=ROOT / "www")
    parser.add_argument("--check", action="store_true", help="report what would change; write nothing")
    args = parser.parse_args(argv)
    changed, rows, counts = build(args.web, privacy_policy())
    if not args.check and changed:
        counts["source pages created"] = len(write(args.web, changed, rows))
    print(json.dumps({"written": not args.check, **dict(sorted(counts.items())), "index rows": len(rows)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
