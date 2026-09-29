#!/usr/bin/env python3
"""WCAG 2.1 A/AA accessibility regression check for public site routes."""

import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import Page, sync_playwright


BASE = os.environ.get("CATALOGUE_TEST_BASE", "http://127.0.0.1:8765").rstrip("/")
ROOT = Path(__file__).resolve().parents[1]
AXE = ROOT / "tests/vendor/axe-core-4.x/axe.min.js"
BASELINE = ROOT / "tests/accessibility-baseline.json"
REPORT = ROOT / "artifacts/accessibility-report.json"
LOCAL_CHROME = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
VIEWPORTS = {"desktop": {"width": 1440, "height": 1000}, "mobile": {"width": 390, "height": 844}}
TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]
TARGETS = [
    ("/", "/"),
    ("/catalogue/", "/catalogue/"),
    ("/catalogue/?q=Alexander", "/catalogue/?q=Alexander"),
    ("/catalogue/?q=Alexander [Name filter open]", "/catalogue/?q=Alexander", "#catalogue-filter-toggle-name"),
    ("/onetree/", "/onetree/"),
    ("/map/", "/map/"),
    ("/branches/", "/branches/"),
    ("/ydna/", "/ydna/"),
    ("/timeline/", "/timeline/"),
    ("/research/", "/research/"),
    ("/about/", "/about/"),
    ("/people/glasgow-951.html", "/people/glasgow-951.html"),
]


def scan(page: Page, target: tuple[str, ...], viewport: str) -> list[dict]:
    label, route, *open_selector = target
    page.goto(f"{BASE}{route}", wait_until="networkidle", timeout=60_000)
    if open_selector:
        page.locator(open_selector[0]).click()
        page.locator(open_selector[0]).wait_for(state="visible")
    page.add_script_tag(path=str(AXE))
    result = page.evaluate(
        """async (tags) => axe.run(document, {
            runOnly: {type: 'tag', values: tags}
        })""",
        TAGS,
    )
    findings = []
    for violation in result["violations"]:
        findings.append(
            {
                "rule": violation["id"],
                "impact": violation.get("impact") or "unknown",
                "page": label,
                "viewport": viewport,
                "count": len(violation["nodes"]),
                "sample_selectors": [node["target"] for node in violation["nodes"][:5]],
                "help": violation["help"],
                "help_url": violation["helpUrl"],
            }
        )
    return findings


def grouped(findings: list[dict]) -> dict:
    output: dict = {}
    for finding in findings:
        rule = output.setdefault(finding["rule"], {"impact": finding["impact"], "pages": {}})
        rule["pages"][f"{finding['page']} [{finding['viewport']}]"] = {
            "count": finding["count"],
            "sample_selectors": finding["sample_selectors"],
            "help": finding["help"],
            "help_url": finding["help_url"],
        }
    return output


def count_index(findings: list[dict]) -> dict[str, int]:
    return {f"{item['page']} [{item['viewport']}]::{item['rule']}": item["count"] for item in findings}


def load_baseline() -> dict[str, int]:
    if not BASELINE.exists():
        return {}
    return json.loads(BASELINE.read_text())["counts"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-baseline", action="store_true", help="replace the committed baseline with current counts")
    args = parser.parse_args()
    assert AXE.exists(), f"Missing vendored axe-core: {AXE}"

    findings: list[dict] = []
    with sync_playwright() as playwright:
        options = {"executable_path": str(LOCAL_CHROME)} if LOCAL_CHROME.exists() else {}
        browser = playwright.chromium.launch(headless=True, **options)
        for viewport, size in VIEWPORTS.items():
            page = browser.new_page(viewport=size)
            for target in TARGETS:
                findings.extend(scan(page, target, viewport))
            page.close()
        browser.close()

    counts = count_index(findings)
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "base_url": BASE,
        "axe_core_version": "4.11.1",
        "standards": "WCAG 2.1 A/AA",
        "viewports": VIEWPORTS,
        "violations": grouped(findings),
        "counts": counts,
        "summary": {
            "rules": len({item["rule"] for item in findings}),
            "instances": sum(item["count"] for item in findings),
            "critical_or_serious_instances": sum(
                item["count"] for item in findings if item["impact"] in {"critical", "serious"}
            ),
        },
    }
    REPORT.parent.mkdir(exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2) + "\n")

    if args.write_baseline:
        BASELINE.write_text(
            json.dumps({"axe_core_version": "4.11.1", "counts": counts}, indent=2) + "\n"
        )
        print(f"Wrote baseline with {len(counts)} page/rule counts")
        return

    baseline = load_baseline()
    regressions = [
        (key, count, baseline.get(key, 0))
        for key, count in counts.items()
        if count > baseline.get(key, 0)
        and next(item for item in findings if f"{item['page']} [{item['viewport']}]::{item['rule']}" == key)["impact"]
        in {"critical", "serious"}
    ]
    if regressions:
        print("New critical/serious accessibility violations:", file=sys.stderr)
        for key, count, allowed in regressions:
            print(f"  {key}: {count} (baseline {allowed})", file=sys.stderr)
        raise SystemExit(1)
    print(f"Accessibility check passed ({report['summary']['instances']} current violation instances; no new critical/serious findings)")


if __name__ == "__main__":
    main()
