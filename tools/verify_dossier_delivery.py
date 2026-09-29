"""Compare a freshly rendered dossier with saved local and fetched public HTML.

Read-only against production. Captures public responses and hashes for upload QA;
the catalogue data build identifier is not a frontend deployment identifier.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

try:
    from repair_person_hierarchy import PRESENTATION_VERSION, _replace_main
except ModuleNotFoundError:
    from tools.repair_person_hierarchy import PRESENTATION_VERSION, _replace_main

ROOT = Path(__file__).resolve().parents[1]
IDS = ["Glasgow-951", "Glasgow-987", "Glasgow-1367", "Glasgow-3939", "Glasgow-3167", "McCaughan-222", "Glasgow-3940"]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def checks(html, profile):
    soup = BeautifulSoup(html, "html.parser")
    main = soup.select_one("main")
    result = {}
    if main is None:
        return {"dossier": False}
    text = main.get_text(" ", strip=True)
    article = main.select_one("[data-dossier-presentation]")
    result["frontend_version"] = bool(article and article.get("data-dossier-presentation") == PRESENTATION_VERSION)
    result["header_css_loaded"] = bool(soup.select_one(f'link[href="/assets/repair/person-hierarchy.css?v={PRESENTATION_VERSION}"]'))
    if profile == "Glasgow-951":
        result["single_thomas_proof"] = not main.select("#question-parents tr[id^='record-will-daniel'], #question-parents tr[id^='record-marriage-daniel']") and len(main.select("#question-thomas-network tr[id^='record-will-daniel'], #question-thomas-network tr[id^='record-marriage-daniel']")) == 2
        result["letter_possession"] = "inspected with the letter" in text and not re.search(
            r"\b(?:obtain|acquire)\b.{0,120}\b(?:letter|20 March 1847)\b", text
        )
        result["death_qualified"] = "leading identification" in main.select_one(".dossier-life").get_text()
    if profile == "Glasgow-1367":
        overview = main.select_one("#overview").get_text(" ", strip=True)
        result["identity_scope_conflict"] = all(value in overview for value in ("No record yet bridges", "County Antrim", "imported profile", "father candidate"))
    if profile == "Glasgow-3939":
        result["child_adults_death_separate"] = all(main.select_one(value) for value in ("#question-identity", "#question-parents", "#question-death-boundary"))
        result["birth_baptism_distinct"] = "17 January 1837" in text and "baptised 9 February 1837" in text
    if profile == "Glasgow-987":
        ids = [row.get("id") for row in main.select("#timeline .timeline-row")]
        expected = ["timeline-census-thomas-1851", "timeline-probate-index-thomas-1870", "timeline-marriage-sarah-1885"]
        result["chronology"] = all(value in ids for value in expected) and [ids.index(value) for value in expected] == sorted(ids.index(value) for value in expected)
    if profile == "McCaughan-222":
        row = main.select_one("#timeline-death-mary-1892 .timeline-role")
        result["own_death_subject"] = bool(row and row.get_text(strip=True) == "Subject")
    if profile == "Glasgow-3167":
        result["samuel_recorded_forms"] = "Samuel Glasgow Elder birth index entry" in text and "separate recorded forms" in text
    return result


def main():
    now = datetime.now(timezone.utc)
    output = ROOT / "artifacts/dossier-delivery" / now.strftime("%Y%m%dT%H%M%SZ")
    output.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((ROOT / "www/data/manifest.json").read_text())
    report = {"fetched_at": now.isoformat(), "commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(), "working_tree": "uncommitted local changes; commit alone does not identify this build", "frontend_presentation_version": PRESENTATION_VERSION, "data_build_id": manifest["build_id"], "pages": []}
    for route in ('data/manifest.json', 'dossier-release.json'):
        try:
            request = Request(f"https://glasgow.phenotype.dev/{route}?verify={now.strftime('%Y%m%dT%H%M%SZ')}", headers={"Cache-Control": "no-cache", "User-Agent": "GlasgowArchive-DeliveryCheck/1"})
            with urlopen(request, timeout=30) as response:
                raw = response.read()
            report[route] = {"sha256": digest(raw), "payload": json.loads(raw)}
        except Exception as error:
            report[route] = {"error": str(error)}
    for profile in IDS:
        slug = profile.casefold()
        local = (ROOT / "www/people" / f"{slug}.html").read_bytes()
        fresh = _replace_main(local.decode(), profile).encode()
        row = {"profile": profile, "local_sha256": digest(local), "fresh_sha256": digest(fresh), "source_matches_saved_html": local == fresh, "local_checks": checks(local, profile)}
        request = Request(f"https://glasgow.phenotype.dev/people/{slug}.html?verify={now.strftime('%Y%m%dT%H%M%SZ')}", headers={"Cache-Control": "no-cache", "User-Agent": "GlasgowArchive-DeliveryCheck/1"})
        try:
            with urlopen(request, timeout=30) as response:
                public = response.read()
                row.update({"http_status": response.status, "response_headers": dict(response.headers), "public_sha256": digest(public), "public_matches_local": public == local, "public_checks": checks(public, profile)})
            (output / f"{slug}.public.html").write_bytes(public)
        except Exception as error:
            row["public_error"] = str(error)
        dossier = json.loads((ROOT / "www/people" / f"{slug}.json").read_text())
        assertion_ids = set(dossier.get("shared_relationship_assertions", []))
        if assertion_ids:
            row["structured_exports"] = []
            for suffix in (".json", ".network.json"):
                local_json = (ROOT / "www/people" / f"{slug}{suffix}").read_bytes()
                item = {"path": f"/people/{slug}{suffix}", "local_sha256": digest(local_json)}
                def assertions(payload):
                    claims = [c for c in payload.get("claims", []) if c.get("id") in assertion_ids or c.get("superseded_by") in assertion_ids]
                    relationships = payload.get("relationships", [])
                    if isinstance(relationships, dict):
                        relationships = [r for rows in relationships.values() for r in rows]
                    return {"claims": claims, "relationships": [r for r in relationships if r.get("claim_id") in assertion_ids], "history": payload.get("relationship_history", []), "vitals": payload.get("vitals")}
                item["local_assertions"] = assertions(json.loads(local_json))
                try:
                    request = Request(f"https://glasgow.phenotype.dev/people/{slug}{suffix}?verify={now.strftime('%Y%m%dT%H%M%SZ')}", headers={"Cache-Control": "no-cache", "User-Agent": "GlasgowArchive-DeliveryCheck/1"})
                    with urlopen(request, timeout=30) as response:
                        raw = response.read()
                        item.update(http_status=response.status, response_headers=dict(response.headers), public_sha256=digest(raw))
                    public_data = json.loads(raw)
                    item["public_assertions"] = assertions(public_data)
                    item["assertions_match"] = item["public_assertions"] == item["local_assertions"]
                    (output / f"{slug}.public{suffix}").write_bytes(raw)
                except Exception as error:
                    item["public_error"] = str(error)
                row["structured_exports"].append(item)
        report["pages"].append(row)
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(output / "report.json")
    for row in report["pages"]:
        print(row["profile"], "source/local", row["source_matches_saved_html"], "local", row["local_checks"], "public", row.get("public_checks", row.get("public_error")))
        for item in row.get("structured_exports", []):
            print(item["path"], "live assertions match:", item.get("assertions_match", item.get("public_error")))


if __name__ == "__main__":
    main()
