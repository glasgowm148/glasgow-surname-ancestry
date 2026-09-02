#!/usr/bin/env python3
"""Rank person-level evidence in saved WikiTree free-space pages.

The audit compares passages around linked WikiTree profiles with the current
profile-evidence capture.  It prioritises direct source URLs, event language and
dates that do not already appear in the live biography capture.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit


PROFILE_RE = re.compile(r"\[\[([A-Za-z][A-Za-z]+-\d+)(?:\||\]\])")
URL_RE = re.compile(r"https?://[^\s\]\|<>{}\"']+")
YEAR_RE = re.compile(r"\b(?:1[1-9]\d{2}|20\d{2})\b")
CLAIM_RE = re.compile(
    r"\b(?:born|birth|baptis|married|marriage|wife|husband|son|daughter|"
    r"father|mother|brother|sister|died|death|buried|burial|will|testament|"
    r"probate|census|tenant|occup|land|property|charter|protocol|witness|"
    r"burgess|merchant|minister|farmer|resided|lived|heir|executor)\w*\b",
    re.I,
)
LOW_VALUE_FILE_RE = re.compile(
    r"(?:using-ai|personal-genetic|glasgow-dna|ancient-ydna|r-(?:by|ft|fta|p|s|z))",
    re.I,
)


def normalise_url(url: str) -> str:
    url = url.rstrip(".,;:)")
    parts = urlsplit(url)
    host = parts.netloc.lower().removeprefix("www.")
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower(), host, path, parts.query, ""))


def clean_markup(text: str) -> str:
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.S)
    text = re.sub(r"<ref[^>]*>|</ref>", " ", text, flags=re.I)
    text = re.sub(r"\{\{.*?\}\}", " ", text, flags=re.S)
    text = re.sub(r"\[\[([^]|]+)\|([^]]+)\]\]", r"\2", text)
    text = re.sub(r"\[\[([^]]+)\]\]", r"\1", text)
    text = re.sub(r"\[(https?://\S+)\s+([^]]+)\]", r"\2", text)
    text = re.sub(r"'{2,}", "", text)
    return " ".join(text.split())


def passages(text: str) -> list[str]:
    # Blank-line blocks retain prose and citation context.  Long tables are
    # also split row-by-row so one linked person does not inherit every row.
    blocks: list[str] = []
    for block in re.split(r"\n\s*\n", text):
        block = block.strip()
        if not block:
            continue
        list_starts = re.findall(r"(?m)^(?=[*#]+\s)", block)
        if len(list_starts) >= 2:
            items = re.split(r"(?m)^(?=[*#]+\s)", block)
            blocks.extend(item.strip() for item in items if item.strip())
            continue
        if block.count("\n|-") >= 2 or block.count("\n|") >= 6:
            rows = re.split(r"\n\|-\s*\n", block)
            blocks.extend(row.strip() for row in rows if row.strip())
        else:
            blocks.append(block)
    return blocks


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--limit", type=int, default=250)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    root = args.root.resolve()
    corpus = root / "research/free-space-pages"
    index = json.loads((corpus / "index.json").read_text())
    evidence = json.loads((root / "data/wikitree/profile-evidence.json").read_text())["profiles"]
    metadata = {Path(p["localFile"]).name: p for p in index["pages"]}

    candidates: list[dict] = []
    linked_ids: set[str] = set()
    seen: set[tuple[str, str]] = set()
    per_page_ids: dict[str, set[str]] = defaultdict(set)

    for path in sorted((corpus / "pages").glob("*.wiki")):
        raw = path.read_text(errors="replace")
        meta = metadata.get(path.name, {})
        for block in passages(raw):
            ids = set(PROFILE_RE.findall(block))
            if not ids:
                continue
            linked_ids.update(ids)
            per_page_ids[path.name].update(ids)
            urls = {normalise_url(url) for url in URL_RE.findall(block)}
            external = {url for url in urls if "wikitree.com" not in urlsplit(url).netloc.lower()}
            plain = clean_markup(block)
            if len(plain) < 35:
                continue
            claim_hits = len(CLAIM_RE.findall(plain))
            years = set(YEAR_RE.findall(plain))
            for pid in ids:
                profile = evidence.get(pid)
                if not profile:
                    continue
                bio = profile.get("biography_wikitext") or ""
                live_urls = {normalise_url(url) for url in profile.get("external_urls") or []}
                new_urls = sorted(external - live_urls)
                missing_years = sorted(year for year in years if year not in bio)
                key = (pid, re.sub(r"\W+", " ", plain.lower())[:500])
                if key in seen:
                    continue
                seen.add(key)

                score = min(24, len(new_urls) * 6)
                score += min(12, claim_hits * 2)
                score += min(9, len(missing_years) * 3)
                score += 4 if "<ref" in block.lower() else 0
                score += 3 if meta.get("editDate", "").endswith("2026") else 0
                score += 2 if 90 <= len(plain) <= 900 else 0
                if LOW_VALUE_FILE_RE.search(path.name):
                    score -= 12
                if re.search(r"\b(?:hypothesis|speculat|possible|perhaps|unproven)\b", plain, re.I):
                    score -= 2
                if not new_urls and not missing_years:
                    score -= 8
                if score < 8:
                    continue
                candidates.append(
                    {
                        "score": score,
                        "profile": pid,
                        "page": meta.get("title", path.stem),
                        "page_url": meta.get("viewUrl", ""),
                        "file": str(path.relative_to(root)),
                        "new_urls": new_urls,
                        "missing_years": missing_years,
                        "passage": plain[:1400],
                    }
                )

    candidates.sort(key=lambda item: (-item["score"], item["profile"], item["file"]))
    unlinked_profiles = sorted(pid for pid in linked_ids if pid not in evidence)
    subject_pages = []
    for name, meta in metadata.items():
        if not per_page_ids.get(name) and meta.get("sourceLength", 0) > 500:
            subject_pages.append((meta.get("title", name), meta.get("viewUrl", ""), name))

    lines = [
        "# Deep free-space evidence audit",
        "",
        f"Pages audited: **{len(metadata)}**",
        f"Linked profiles seen: **{len(linked_ids)}**",
        f"Ranked person-passages: **{len(candidates)}**",
        "",
        "## Ranked evidence passages",
        "",
    ]
    for item in candidates[: args.limit]:
        lines.extend(
            [
                f"### {item['profile']} — score {item['score']}",
                "",
                f"- Free-space page: [{item['page']}]({item['page_url']})",
                f"- Local capture: `{item['file']}`",
                f"- Direct source URLs absent from captured live biography: {len(item['new_urls'])}",
                f"- Years absent from captured live biography: {', '.join(item['missing_years']) or 'none'}",
            ]
        )
        for url in item["new_urls"][:8]:
            lines.append(f"  - {url}")
        lines.extend(["", item["passage"], ""])

    lines.extend(["## Linked WikiTree IDs not in the local evidence capture", ""])
    lines.append(" · ".join(unlinked_profiles) if unlinked_profiles else "None.")
    lines.extend(["", "## Substantive pages with no linked WikiTree profile", ""])
    for title, url, name in subject_pages:
        lines.append(f"- [{title}]({url}) — `{name}`")
    lines.append("")

    output = args.output or corpus / "deep-evidence-audit.md"
    output.write_text("\n".join(lines))
    try:
        display_output = output.relative_to(root)
    except ValueError:
        display_output = output
    print(f"Wrote {display_output}")
    print(f"Candidates: {len(candidates)}; linked IDs: {len(linked_ids)}; uncaptured IDs: {len(unlinked_profiles)}")


if __name__ == "__main__":
    main()
