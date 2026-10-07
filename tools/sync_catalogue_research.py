"""Check or refresh existing person research without rebuilding the whole site.

Only reviewed findings sections and the maintained WikiTree update queue are
published. This does not infer amendments, create people, or change tree data.
"""
import argparse
import contextlib
import json
import re
import sys
from html import escape
from pathlib import Path

from bs4 import BeautifulSoup

try:
    import build_research_catalog as catalogue
    from public_privacy import from_sources, public_capture
    from site_html import read_html
    from repair_person_hierarchy import _profile_update_panel, _replace_main, revise, render_person_dossier
except ModuleNotFoundError:
    from tools import build_research_catalog as catalogue
    from tools.public_privacy import from_sources, public_capture
    from tools.site_html import read_html
    from tools.repair_person_hierarchy import _profile_update_panel, _replace_main, revise, render_person_dossier

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "www"


def public_findings(identifiers, policy):
    """Apply the public boundary to maintained notes before dossier rendering."""
    return policy.project(catalogue._load_research_findings(identifiers))

CATEGORIES = {
    "conclusion": ("research-update", "Current research conclusion"),
    "sources": ("research-findings", "Case-file source findings"),
    "assessment": ("evidence", "Identity and relationship assessments"),
    "actions": ("questions", "Unresolved questions and next steps"),
    "notes": ("research-notes", "Other research notes"),
}


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")


def update_data(update):
    if not update:
        return None
    draft = update.get("proposed_wikitext") or update.get("draft_wikitext") or ""
    return {
        "profile_id": update["profile_id"],
        "significance": int(update.get("significance") or 0),
        "summary": update.get("summary") or "",
        "remote_captured_at": update.get("remote_captured_at") or "",
        "remote_revision": update.get("remote_revision") or "",
        "remote_wikitext": update.get("remote_wikitext") or "",
        "draft_wikitext": draft,
        "manual_update": bool(update.get("manual_update")),
        "pending": bool(update.get("pending", True)),
        **({"application_review": {key: update["application_review"][key]
                                   for key in ("reviewed_on", "status", "assessment")
                                   if key in update["application_review"]}}
           if update.get("application_review") else {}),
    }


def completed_comparisons(evidence, queue_payload, policy=None):
    """Materialise a read-only current-vs-draft comparison for completed work."""
    policy = policy or from_sources(evidence)
    profiles = evidence.get("profiles", {})
    reopened = set(queue_payload.get("reopened_completed_profiles", []))
    entries = queue_payload.get("entries", {})
    completed = set(queue_payload.get("completed_live_profiles", [])) - reopened
    comparisons = {}
    for profile_id in sorted(completed):
        capture = profiles.get(profile_id) or {}
        if profile_id.casefold() in policy.blocked or not public_capture(capture):
            continue
        current = str(capture.get("biography_wikitext") or "").strip()
        if not current:
            continue
        spec = entries.get(profile_id) or {}
        revision = capture.get("last_updated") or ""
        try:
            revision = catalogue._format_profile_timestamp(revision)
        except (AttributeError, TypeError, ValueError):
            revision = str(revision)
        comparisons[profile_id] = policy.project({
            "profile_id": profile_id,
            "remote_wikitext": current,
            "draft_wikitext": current,
            "remote_captured_at": capture.get("captured_at") or "",
            "remote_revision": revision,
            "summary": "The prepared amendment is already on WikiTree; no pending biography change.",
            "pending": False,
            "significance": int(spec.get("significance") or 0),
            "profile_url": capture.get("profile_url") or f"https://www.wikitree.com/wiki/{profile_id}",
        })
    return comparisons


def article_html(finding, section, links):
    meta = escape(finding["profile_id"])
    if finding.get("updated"):
        meta += " · updated " + escape(finding["updated"])
    return (f'<article class="research-finding"><h3>{escape(section["title"])}</h3>'
            f'<p class="finding-meta">{meta}</p>'
            + catalogue._render_findings_markdown(section["markdown"], links) + "</article>")


def plain(node):
    return " ".join(node.get_text(" ", strip=True).split())


def discrepancies(dossier, soup, findings, update, row, links, comparison=None):
    issues = []
    new_layout = bool(soup.select_one(".person-dossier-readable"))
    if dossier.get("research_findings", []) != findings:
        issues.append("findings data")
    if new_layout:
        # The shared presentation reads the refreshed dossier model and keeps
        # the full finding text in Archive and tools; the old per-category
        # disclosure checks no longer describe the primary reading view.
        desired = update_data(update)
        if dossier.get("wikitree_update") != desired:
            issues.append("update data")
        if comparison and dossier.get("wikitree_comparison") != comparison:
            issues.append("comparison data")
        display = update or comparison
        panel = soup.select_one("#wikitree-update")
        if bool(panel) != bool(display):
            issues.append("update panel")
        elif display:
            expected_draft = display.get("proposed_wikitext") or display.get("draft_wikitext") or ""
            draft = panel.select_one("#profile-update-draft")
            if not draft or draft.get_text() != expected_draft:
                issues.append("visible draft")
            if display.get("remote_wikitext") and not panel.select_one("#profile-update-current"):
                issues.append("visible current capture")
        if bool(row.get("needs_wikitree_update")) != bool(update):
            issues.append("update flag")
        if row.get("wikitree_update_summary", "") != (update["summary"] if update else ""):
            issues.append("search update summary")
        if int(row.get("wikitree_update_significance") or 0) != (int(update["significance"]) if update else 0):
            issues.append("search update significance")
        return issues
    for finding in findings:
        for section in finding["sections"]:
            target = soup.find(id=CATEGORIES[section["category"]][0])
            expected = plain(BeautifulSoup(article_html(finding, section, links), "html.parser"))
            if not target or re.sub(r"\s+", "", expected) not in re.sub(r"\s+", "", plain(target)):
                issues.append("visible finding: " + section["title"])
    desired = update_data(update)
    actual = dossier.get("wikitree_update")
    if actual != desired:
        issues.append("update data")
    if comparison and dossier.get("wikitree_comparison") != comparison:
        issues.append("comparison data")
    panel = soup.select_one("#wikitree-update")
    display = update or comparison
    if bool(panel) != bool(display):
        issues.append("update panel")
    elif display:
        draft = panel.select_one("#profile-update-draft")
        summary = panel.select_one(".lede")
        expected_draft = display.get("proposed_wikitext") or display.get("draft_wikitext") or ""
        if not draft or draft.get_text() != expected_draft:
            issues.append("visible draft")
        if not summary or plain(summary) != " ".join(display.get("summary", "").split()):
            issues.append("visible update summary")
        if display.get("remote_wikitext") and not panel.select_one("#profile-update-current"):
            issues.append("visible current capture")
    if bool(row.get("needs_wikitree_update")) != bool(update):
        issues.append("update flag")
    if row.get("wikitree_update_summary", "") != (update["summary"] if update else ""):
        issues.append("search update summary")
    if int(row.get("wikitree_update_significance") or 0) != (int(update["significance"]) if update else 0):
        issues.append("search update significance")
    return issues


def refresh_person(soup, findings, update, links):
    research = soup.select_one("#research, #research-stack")
    if not research:
        raise ValueError("Existing dossier has no research container")
    for category, (identifier, title) in CATEGORIES.items():
        sections = [(f, s) for f in findings for s in f["sections"] if s["category"] == category]
        target = soup.find(id=identifier)
        if not target and sections:
            target = soup.new_tag("details", id=identifier, attrs={"class": "r-disclosure r-original-research"})
            summary = soup.new_tag("summary"); summary.string = title; target.append(summary)
            target.append(soup.new_tag("div", attrs={"class": "disclosure-body"}))
            research.append(target)
        if not target:
            continue
        body = target.select_one(".disclosure-body") or target.select_one(".research-section-body")
        if body is None and target.name == "section" and identifier == "research-update":
            for placeholder in target.select(".r-caption"):
                if plain(placeholder).startswith("No separately maintained research assessment"):
                    placeholder.decompose()
            body = soup.new_tag("div", attrs={"class": "disclosure-body"})
            target.append(body)
        if body is None:
            raise ValueError(f"Unknown research section layout: {identifier}")
        for old in body.select(".research-finding"):
            old.decompose()
        for finding, section in sections:
            body.append(BeautifulSoup(article_html(finding, section, links), "html.parser"))
        if sections:
            for p in body.find_all("p", recursive=False):
                if plain(p).startswith("No formal open question"):
                    p.decompose()
    for old in soup.select("#wikitree-update"):
        parent = old.parent
        heading = parent.find("summary", recursive=False)
        if parent.name == "details" and heading and "Prepared WikiTree updates" in plain(heading):
            parent.decompose()
        else:
            old.decompose()
    for link in soup.select('.v3-inline-links a[href="#wikitree-update"]'):
        link.decompose()
    if update:
        tools = soup.select_one("#research-tools")
        if tools is None:
            tools = soup.new_tag("div", id="research-tools")
            research.append(tools)
        wrapper = soup.new_tag("details", attrs={"class": "r-disclosure"})
        heading = soup.new_tag("summary"); heading.string = "Prepared WikiTree comparison" if not update.get("pending", True) else "Prepared WikiTree updates — Needs updated on WikiTree"
        wrapper.append(heading)
        wrapper.append(BeautifulSoup(_profile_update_panel(update), "html.parser"))
        tools.insert(1, wrapper)
        inline = soup.select_one(".v3-inline-links")
        if inline is not None:
            link = soup.new_tag("a", href="#wikitree-update"); link.string = "WikiTree comparison →" if not update.get("pending", True) else "Needs updated on WikiTree →"; inline.append(link)
        if not any("profile-update.js" in script.get("src", "") for script in soup.select("script[src]")):
            soup.body.append(soup.new_tag("script", src=f"/people/profile-update.js?v={catalogue.CATALOGUE_ASSET_VERSION}", defer=True))
    return revise(str(soup))[0]


def refresh_catalogue_summaries(rows):
    pending = sorted((r for r in rows if r.get("needs_wikitree_update")),
                     key=lambda r: (-r["wikitree_update_significance"], r["name"].casefold()))
    for relative in ("catalogue.html", "catalogue/index.html", "catalogue/advanced.html"):
        path = WEB / relative
        old = path.read_text(encoding="utf-8")
        soup = BeautifulSoup(old, "html.parser")
        hero = soup.select_one(".catalogue-hero .lede")
        if hero:
            hero.string = f"Search {len(rows):,} historical people connected with the Glasgow surname."
        for statistic in soup.select(".statistics-summary > div"):
            label = statistic.find("span")
            if label and plain(label) == "Historical people":
                statistic.find("strong").string = f"{len(rows):,}"
        for link in soup.select('a[href*="needsUpdate"]'):
            label, count = link.find("strong"), link.find("span")
            if label and count and plain(label) == "Needs updated on WikiTree":
                count.string = f"{len(pending):,} profiles ranked by significance, with paste-ready or exact manual corrections"
        preview = soup.select_one(".wikitree-update-preview")
        if preview:
            description = preview.find("p", recursive=False)
            if description:
                description.string = f"{len(pending):,} source-backed corrections remain on WikiTree. The highest-significance updates are previewed here; the filter opens the complete queue. Each page provides either paste-ready text or the exact manual relationship, confidence or vital-field action."
            grid = preview.select_one(".wikitree-update-grid")
            if grid:
                grid.clear()
                for row in pending[:8]:
                    ident = read_json(WEB / "people" / (row["id"] + ".json"))["wikitree_update"]["profile_id"]
                    grid.append(BeautifulSoup(
                        f'<article><div><p class="kicker">Significance {row["wikitree_update_significance"]}/100</p>'
                        f'<h3><a href="/people/{row["id"]}.html#wikitree-update">{escape(row["name"])}</a></h3>'
                        f'<p><a href="https://www.wikitree.com/wiki/{ident}">{ident}</a></p></div>'
                        f'<p>{escape(row["wikitree_update_summary"])}</p></article>', "html.parser"))
        if str(soup) != old:
            path.write_text(str(soup), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profiles", nargs="*", help="Profile IDs; default: every case with findings or an update")
    parser.add_argument("--write", action="store_true", help="Refresh reviewed existing dossiers and queue presentation")
    args = parser.parse_args()
    evidence = catalogue._load_wikitree_evidence()
    policy = from_sources(evidence)
    updates = catalogue._load_profile_updates(evidence)
    queue_payload = read_json(catalogue.PROFILE_UPDATE_QUEUE)
    comparisons = completed_comparisons(evidence, queue_payload)
    rows = read_json(WEB / "data/catalogue-search-index.json")
    by_slug = {r["id"]: r for r in rows}
    links = {p["id"]: p.get("slug", p["id"].lower()) for p in read_json(WEB / "data/people-index.json")}
    requested = set(args.profiles) or ({p.parent.name for p in (ROOT / "research").glob("*/findings.md")} | set(updates) | set(comparisons))
    manifest_path = ROOT / "data/wikitree/research-catalogue-cases.json"
    cases = read_json(manifest_path).get("cases", {}) if manifest_path.exists() else {}
    report, missing, checked, refreshed_profiles = {}, [], 0, []
    for ident in sorted(requested):
        decision = cases.get(ident, {})
        if decision.get("status") in {"internal", "withheld"}:
            continue
        if decision.get("status") == "covered":
            target = WEB / "people" / (decision["profile_id"].lower() + ".html")
            if not target.exists():
                missing.append(ident)
            continue
        if decision.get("status") == "include_record":
            ident = decision["profile_id"]
        slug = links.get(ident, ident.lower())
        path = WEB / "people" / (slug + ".json")
        if not path.exists() or slug not in by_slug:
            if catalogue._load_research_findings([ident]) or ident in updates:
                missing.append(ident)
            continue
        dossier = read_json(path)
        identifiers = list(dict.fromkeys([dossier["id"], *by_slug[slug].get("profile_ids", [])]))
        findings = public_findings(identifiers, policy)
        update = updates.get(ident)
        html_path = path.with_suffix(".html")
        soup = BeautifulSoup(read_html(html_path, site_root=WEB), "html.parser")
        comparison = comparisons.get(ident)
        issues = discrepancies(dossier, soup, findings, update, by_slug[slug], links, comparison)
        checked += 1
        if not issues:
            continue
        report[ident] = issues
        if not args.write:
            continue
        display_update = update or comparison
        rendered = None if soup.select_one(".person-dossier-readable") else refresh_person(soup, findings, display_update, links)
        dossier["research_findings"] = findings
        if update:
            dossier["wikitree_update"] = update_data(update)
        else:
            dossier.pop("wikitree_update", None)
        if comparison:
            dossier["wikitree_comparison"] = comparison
        else:
            dossier.pop("wikitree_comparison", None)
        by_slug[slug].update(needs_wikitree_update=bool(update),
                            wikitree_update_summary=update["summary"] if update else "",
                            wikitree_update_significance=int(update["significance"]) if update else 0)
        write_json(path, dossier)
        if soup.select_one(".person-dossier-readable"):
            html_path.write_text(_replace_main(html_path.read_text(encoding="utf-8"), dossier["id"]), encoding="utf-8")
        else:
            html_path.write_text(rendered, encoding="utf-8")
        refreshed_profiles.append(dossier["id"])
    if args.write and report:
        write_json(WEB / "data/catalogue-search-index.json", rows)
        (WEB / "data/people-index.js").write_text("window.glasgowPeopleIndex=" + json.dumps(rows, ensure_ascii=False, separators=(",", ":")) + ";\n", encoding="utf-8")
        # The hierarchy pass writes the approved presentation fields, then
        # refreshes the derived Bio/Marriage catalogue search fields.
        from repair_person_hierarchy import repair as repair_person_hierarchy
        repair_person_hierarchy(refreshed_profiles)
        refresh_catalogue_summaries(rows)
    index_exit = 0
    if args.write and not missing:
        try:
            from genealogy.batch_complete import refresh_after_batch
        except ModuleNotFoundError:
            from tools.genealogy.batch_complete import refresh_after_batch
        index_exit = refresh_after_batch()
    print(json.dumps({"checked": checked, "refreshed" if args.write else "stale": report,
                      "missing_public_cases": missing}, indent=2))
    # What the builders will still not publish for these profiles (text above
    # the first heading, sources only in editing logs, no overall conclusion,
    # register or queue entries dropped). Printed on stderr so the JSON above
    # stays machine-readable.
    try:
        from check_research_publication import main as check_publication
    except ModuleNotFoundError:
        from tools.check_research_publication import main as check_publication
    check_args = ["--baseline", str(ROOT / "data/site/research-publication-baseline.json")]
    if args.profiles:
        check_args += ["--id", *args.profiles]
    with contextlib.redirect_stdout(sys.stderr):
        publication_exit = check_publication(check_args)
    return int(bool(missing or (report and not args.write) or index_exit or publication_exit))


if __name__ == "__main__":
    raise SystemExit(main())
