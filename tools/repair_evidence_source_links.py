"""Apply explicit citation corrections while retaining the original import URL."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def repair(web=ROOT / "www"):
    corrections = json.loads((ROOT / "research/evidence_source_corrections.json").read_text())
    records = {row["record_id"]: row for row in json.loads((ROOT / "research/canonical_records.json").read_text())}
    count = 0
    for correction in corrections:
        record = records[correction["canonical_record_id"]]
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
