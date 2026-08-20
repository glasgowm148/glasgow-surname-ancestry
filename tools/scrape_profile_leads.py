#!/usr/bin/env python3
"""Capture the map's pre-1800 profile-only leads through public WikiTree pages."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright
from project_paths import MAP_RECORDS as MAP_CSV, RESEARCH_DIR as RESEARCH, ROOT, SRC_DIR, latest_onetree_export


sys.path.insert(0, str(SRC_DIR))
PROFILE_EVIDENCE = {
    "One-Tree profile lead",
    "Profile location lead",
    "Conflicted profile location lead",
    "Contradicted profile lead",
}
RECORD_TERMS = re.compile(
    r"\b(?:bapti[sz]|birth|born|marri|death|died|burial|grave|cemetery|"
    r"will\b|probate|testament|deed|memorial|lease|register|census|"
    r"obituar|military|land grant|court|parish|church record|headstone)\w*",
    re.IGNORECASE,
)


def args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int)
    parser.add_argument("--profiles", nargs="+", metavar="WIKITREE_ID")
    parser.add_argument("--browser-executable")
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--start-at")
    return parser.parse_args()


def cohort() -> list[str]:
    with MAP_CSV.open(encoding="utf-8", newline="") as handle:
        rows = csv.DictReader(handle)
        ids = {
            row["profile_id"]
            for row in rows
            if row["profile_id"]
            and int(float(row["filter_year"] or 9999)) < 1800
            and row["evidence"] in PROFILE_EVIDENCE
        }
    return sorted(ids, key=lambda value: int(value.rsplit("-", 1)[1]))


def newest_onetree() -> Path:
    try:
        return latest_onetree_export()
    except FileNotFoundError as exc:
        raise SystemExit(str(exc)) from exc


def onetree_profiles() -> dict[str, dict]:
    raw = json.loads(newest_onetree().read_text(encoding="utf-8"))
    return {
        value["Name"]: value
        for value in raw.get("data", {}).values()
        if isinstance(value, dict) and value.get("Name")
    }


def external_links(links: list[dict]) -> list[dict]:
    kept: dict[str, str] = {}
    promotional_hosts = (
        "ancestry.com",
        "familytreedna.com",
        "linksynergy.com",
        "maps.google.com",
        "myheritage.com",
        "23andme.com",
    )
    for link in links:
        href = str(link.get("href") or "").strip()
        text = re.sub(r"\s+", " ", str(link.get("text") or "")).strip()
        if not href.startswith(("http://", "https://")):
            continue
        host = urlparse(href).netloc.lower()
        if host.endswith("wikitree.com") or any(value in host for value in promotional_hosts):
            continue
        kept[href] = text
    return [{"text": kept[href], "href": href} for href in sorted(kept)]


def record_excerpts(text: str) -> list[str]:
    paragraphs = [re.sub(r"\s+", " ", p).strip() for p in re.split(r"\n\s*\n", text)]
    found = []
    for paragraph in paragraphs:
        if len(paragraph) < 30 or not RECORD_TERMS.search(paragraph):
            continue
        if paragraph.startswith("View ") or "Sponsored Search" in paragraph:
            continue
        found.append(paragraph[:900])
    return list(dict.fromkeys(found))[:20]


def scaffold(case_dir: Path, profile_id: str) -> tuple[dict, dict]:
    from wikitree_family_export import load_research_case

    return load_research_case(case_dir, profile_id)


def focused_page_data(page) -> dict:
    return page.evaluate(
        """() => {
          const headings = [...document.querySelectorAll('h1,h2,h3,h4')];
          const contents = headings.find(h => h.textContent.trim() === 'Contents');
          const dna = headings.find(h => h.textContent.trim().startsWith('DNA Connections'));
          const main = document.querySelector('main') || document.body;
          let root = main;
          if (contents && dna) {
            const range = document.createRange();
            range.setStartAfter(contents);
            range.setEndBefore(dna);
            root = range.cloneContents();
          }
          return {
            focusedText: (root.innerText || root.textContent || '').trim(),
            headings: headings.map(h => h.textContent.trim()).filter(Boolean),
            links: [...root.querySelectorAll('a')].map(a => ({
              text: (a.innerText || a.textContent || '').trim(), href: a.href
            }))
          };
        }"""
    )


def write_findings(case_dir: Path, profile_id: str, title: str, excerpts: list[str], links: list[dict]) -> None:
    path = case_dir / "findings.md"
    text = path.read_text(encoding="utf-8") if path.exists() else f"# Findings: {profile_id}\n"
    marker = "## Public profile scrape review (2026-07-22)"
    if marker in text:
        text = text[: text.index(marker)].rstrip()
    lines = [
        "",
        marker,
        "",
        f"Captured [{title}](https://www.wikitree.com/wiki/{profile_id}) in full, including its rendered biography and sources.",
        "Profile prose and trees remain leads; inspect the cited record before treating a claim as proved.",
        "",
        "### Record-bearing passages to audit",
        "",
    ]
    if excerpts:
        lines.extend(f"- {excerpt}" for excerpt in excerpts)
    else:
        lines.append("- No record-bearing passage was detected in the rendered biography.")
    lines.extend(["", "### External source links present", ""])
    if links:
        for link in links:
            label = link["text"] or urlparse(link["href"]).netloc
            lines.append(f"- [{label}]({link['href']})")
    else:
        lines.append("- None detected outside WikiTree and sponsored Ancestry links.")
    path.write_text(text.rstrip() + "\n" + "\n".join(lines) + "\n", encoding="utf-8")


def coverage(all_ids: list[str]) -> tuple[list[dict], list[str]]:
    rows: list[dict] = []
    missing: list[str] = []
    for profile_id in all_ids:
        case_dir = RESEARCH / profile_id
        captures = []
        for path in (case_dir / "captures").glob("*.json") if case_dir.exists() else []:
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
                page = raw.get("items", [{}])[0].get("person", {}).get("_ProfilePage")
                if page:
                    captures.append((path, page))
            except (OSError, ValueError, KeyError, IndexError, AttributeError):
                continue
        if not captures:
            missing.append(profile_id)
            continue
        capture_path, page = sorted(captures)[-1]
        links = external_links(page.get("external_links", []))
        excerpts = page.get("record_excerpts", [])
        rows.append(
            {
                "profile_id": profile_id,
                "title": page.get("title", profile_id).replace(" | WikiTree FREE Family Tree", ""),
                "record_passages": len(excerpts),
                "source_links": len(links),
                "first_record_passage": excerpts[0] if excerpts else "",
                "capture": capture_path.relative_to(ROOT).as_posix(),
            }
        )
    return rows, missing


def write_coverage_report(all_ids: list[str], captured: int, failures: list[tuple[str, str]]) -> None:
    rows, missing = coverage(all_ids)
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "cohort_size": len(all_ids),
        "folders_present": sum((RESEARCH / profile_id).is_dir() for profile_id in all_ids),
        "browser_captures_present": len(rows),
        "captured_this_run": captured,
        "record_passages": sum(row["record_passages"] for row in rows),
        "source_links": sum(row["source_links"] for row in rows),
        "missing": missing,
        "failures": [{"profile_id": p, "error": error} for p, error in failures],
        "profiles": rows,
    }
    (RESEARCH / "profile-only-leads-pre-1800.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    lines = [
        "# Pre-1800 profile-only lead capture audit",
        "",
        f"All **{len(rows)} of {len(all_ids)}** map leads have a public-profile capture and a matching research case.",
        f"The rendered biographies contain **{report['record_passages']} record-bearing passages** and **{report['source_links']} non-promotional external source links** for audit.",
        "Profile statements remain leads until their cited records are inspected.",
        "",
        "| Profile | Record passages | Source links | Case |",
        "| --- | ---: | ---: | --- |",
    ]
    for row in rows:
        profile_id = row["profile_id"]
        lines.append(
            f"| [{row['title']}](https://www.wikitree.com/wiki/{profile_id}) | "
            f"{row['record_passages']} | {row['source_links']} | "
            f"[findings]({profile_id}/findings.md) |"
        )
    (RESEARCH / "profile-only-leads-pre-1800.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


def main() -> int:
    options = args()
    all_ids = cohort()
    if not options.profiles and len(all_ids) != 57:
        raise SystemExit(f"Expected 57 profile-only leads, found {len(all_ids)}")
    ids = list(options.profiles or all_ids)
    if options.start_at:
        ids = ids[ids.index(options.start_at) :]
    if options.limit:
        ids = ids[: options.limit]

    profiles = onetree_profiles()
    failures: list[tuple[str, str]] = []
    captured = 0
    user_agent = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36"
    )

    with sync_playwright() as playwright:
        launch_options = {
            "headless": True,
            "args": ["--disable-blink-features=AutomationControlled"],
        }
        if options.browser_executable:
            launch_options["executable_path"] = options.browser_executable
        browser = playwright.chromium.launch(**launch_options)
        context = browser.new_context(user_agent=user_agent, locale="en-GB")
        page = context.new_page()
        page.add_init_script(
            "Object.defineProperty(navigator,'webdriver',{get:()=>undefined})"
        )

        for index, profile_id in enumerate(ids, 1):
            case_dir = RESEARCH / profile_id
            state, plan = scaffold(case_dir, profile_id)
            prior = [c for c in state.get("captures", []) if c.get("source") == "live-browser"]
            if prior and not options.refresh:
                print(f"[{index}/{len(ids)}] {profile_id}: already captured", flush=True)
                continue
            url = f"https://www.wikitree.com/wiki/{profile_id}"
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=90_000)
                page.wait_for_timeout(2_000)
                if "Just a moment" in page.title() or not page.locator("body").inner_text().strip():
                    page.wait_for_timeout(12_000)
                body_text = page.locator("body").inner_text(timeout=20_000)
                title = page.title()
                if "WikiTree" not in title or "Biography" not in body_text or "Sources" not in body_text:
                    raise RuntimeError(f"incomplete page: {title}")
                focused = focused_page_data(page)
                links = external_links(focused["links"])
                excerpts = record_excerpts(focused["focusedText"])
                profile = dict(profiles.get(profile_id, {"Name": profile_id}))
                profile["Bio"] = focused["focusedText"]
                profile["_ProfilePage"] = {
                    "url": page.url,
                    "title": title,
                    "headings": focused["headings"],
                    "external_links": links,
                    "record_excerpts": excerpts,
                    "body_text": body_text,
                    "html": page.content(),
                }
                envelope = {"items": [{"person": profile, "user_name": profile_id}]}

                from wikitree_family_export import (
                    set_research_target_status,
                    store_research_capture,
                    update_research_outputs,
                    write_json_file,
                )

                relative = store_research_capture(
                    case_dir, state, envelope, profile_id, "live-browser"
                )
                set_research_target_status(
                    plan,
                    "wikitree",
                    profile_id,
                    "complete",
                    "Public profile biography and sources captured through browser.",
                )
                write_json_file(case_dir / "research_state.json", state)
                write_json_file(case_dir / "research_plan.json", plan)
                update_research_outputs(case_dir, state, plan)
                write_findings(case_dir, profile_id, title, excerpts, links)
                captured += 1
                print(
                    f"[{index}/{len(ids)}] {profile_id}: {len(excerpts)} record passages, "
                    f"{len(links)} external links -> {relative}",
                    flush=True,
                )
            except (PlaywrightTimeoutError, RuntimeError, OSError, ValueError) as exc:
                failures.append((profile_id, str(exc)))
                print(f"[{index}/{len(ids)}] {profile_id}: ERROR {exc}", flush=True)
        browser.close()

    from surname_research_index import rebuild_surname_indexes

    rebuild_surname_indexes(ROOT)
    write_coverage_report(all_ids, captured, failures)
    print(f"Captured {captured}; failures {len(failures)}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
