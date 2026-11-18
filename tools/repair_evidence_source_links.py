"""Project reviewed citation corrections while preserving historical captures."""
import csv
from html import escape
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


TITLE_FIELDS = {"title", "display_title", "source_title", "supporting_source_title"}
CAPTURE_FIELDS = {"imported", "superseded_source", "wikitree_update", "wikitree_comparison"}


def _project_title(value, prior, reviewed):
    if isinstance(value, list):
        return sum(_project_title(item, prior, reviewed) for item in value)
    if not isinstance(value, dict):
        return 0
    count = 0
    for field, current in value.items():
        if field in CAPTURE_FIELDS:
            continue
        if field in TITLE_FIELDS and isinstance(current, str) and " ".join(current.split()) == prior:
            value[field] = reviewed
            count += 1
        else:
            count += _project_title(current, prior, reviewed)
    return count


def _repair_source_readers(web, prior, reviewed):
    from bs4 import BeautifulSoup
    try:
        from tools.ingest_canonical_records import packed_source_index
        from tools.project_paths import atomic_write_text
    except ModuleNotFoundError:
        from ingest_canonical_records import packed_source_index
        from project_paths import atomic_write_text

    index = web / "assets/v3/source-index.json"
    if not index.is_file():
        return 0
    rows = json.loads(index.read_text())
    changed = {row["id"] for row in rows if _project_title(row, prior, reviewed)}
    if not changed:
        return 0
    updates = {index: rows, index.with_name("source-index-packed.json"): packed_source_index(rows)}
    for ident in changed:
        path = web / "assets/v3/sources" / f"{ident}.json"
        doc = json.loads(path.read_text())
        _project_title(doc, prior, reviewed)
        updates[path] = doc
    for path, value in updates.items():
        atomic_write_text(path, json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n")
    count = len(updates)
    for ident in changed:
        path = web / "sources" / ident / "index.html"
        if not path.is_file():
            continue
        original = path.read_text()
        soup = BeautifulSoup(original, "html.parser")
        for node in soup.select("title, h1, noscript p"):
            text = " ".join(node.get_text().split())
            if prior in text:
                # No-script prose already appends a full stop to the caption.
                term = prior + "." if reviewed.endswith(".") and prior + "." in text else prior
                node.string = text.replace(term, reviewed, 1)
        revised = str(soup)
        if revised != original:
            atomic_write_text(path, revised)
            count += 1
    urls = {f"/sources/{ident}/" for ident in changed}
    for path in sorted((web / "sources/browse").glob("*.html")):
        original = path.read_text()
        if escape(prior) not in original or not any(url in original for url in urls):
            continue
        soup = BeautifulSoup(original, "html.parser")
        matching = [link for link in soup.select("a[href]") if link["href"] in urls
                    and " ".join(link.get_text().split()) == prior]
        if not matching:
            continue
        for link in matching:
            link.string = reviewed
        atomic_write_text(path, str(soup))
        count += 1
    return count


def repair_source_title(web, correction, record):
    try:
        from tools.project_paths import atomic_write_csv, atomic_write_text
    except ModuleNotFoundError:
        from project_paths import atomic_write_csv, atomic_write_text

    prior = " ".join(correction["previous_source_title"].split())
    prefix = correction.get("preserved_title_prefix", "")
    reviewed = prefix + record["source_title"] if record.get("source_title") else ""
    if (not prior or not reviewed or not prior.startswith(prefix)
            or " ".join(reviewed.split()) == prior or not correction.get("reason")):
        raise ValueError(f"{record['record_id']}: title projection requires a distinct reviewed title and reason")
    slugs = [ident.casefold() for ident in correction.get("profile_ids", [])]
    paths = [web / "data/records-index.json"]
    for slug in slugs:
        paths.extend([web / "people" / f"{slug}.json", web / "people" / f"{slug}.network.json",
                      web / "assets/research/people" / f"{slug}.json"])
    paths.extend(web / "assets/research/records" / f"{ident}.json"
                 for ident in correction.get("record_ids", []))
    paths.extend(sorted((web / "data/chunks").glob("records-*.json")))
    changed = 0
    for path in paths:
        if not path.is_file():
            continue
        value = json.loads(path.read_text())
        if _project_title(value, prior, reviewed):
            atomic_write_text(path, json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n")
            changed += 1

    for name in ("records.csv", "source-gaps.csv", "source-review.csv"):
        path = web / "data" / name
        if not path.is_file():
            continue
        with path.open(encoding="utf-8-sig", newline="") as handle:
            inputs = csv.DictReader(handle)
            rows = list(inputs)
        if not _project_title(rows, prior, reviewed):
            continue
        atomic_write_csv(path, inputs.fieldnames, rows)
        mirror = path.with_suffix(".csv.txt")
        if mirror.exists():
            with path.open(encoding="utf-8-sig", newline="") as handle:
                atomic_write_text(mirror, handle.read(), encoding="utf-8-sig")
            changed += 1
        changed += 1
    return changed + _repair_source_readers(web, prior, reviewed)


def repair(web=ROOT / "www", *, titles=True, urls=True):
    corrections = json.loads((ROOT / "research/evidence_source_corrections.json").read_text())
    try:
        import research_data
    except ModuleNotFoundError:
        from tools import research_data
    records = {row["record_id"]: row for row in research_data.canonical_records(ROOT)}
    count = 0
    for correction in corrections:
        record = records[correction["canonical_record_id"]]
        if "previous_source_title" in correction:
            if titles:
                count += repair_source_title(web, correction, record)
            continue
        if not urls:
            continue
        for path in (web / "people" / (correction["profile_id"].lower() + ".json"),
                     web / "assets/research/evidence" / (correction["evidence_id"] + ".json")):
            if not path.exists():
                continue
            data = json.loads(path.read_text())
            evidence = data.get("evidence", [data])
            changed = False
            for item in evidence:
                if item.get("id") != correction["evidence_id"]:
                    continue
                source = item.setdefault("source", {})
                if source.get("url") != record["source_url"]:
                    item.setdefault("superseded_source", dict(source))
                    source["url"] = record["source_url"]
                    item["source_correction"] = correction
                    changed = True
            if changed:
                path.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n")
                count += 1
    return {"source_correction_files": count}


if __name__ == "__main__":
    print(repair())
