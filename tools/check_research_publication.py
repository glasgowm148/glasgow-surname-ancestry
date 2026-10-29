#!/usr/bin/env python3
"""Check that research written in the maintained inputs reaches the site.

Every ``research/<ID>/findings.md`` file, the WikiTree work register
(``surname-research/to-update.md``), the update queue
(``data/wikitree/profile-update-queue.json``) and the authored overviews are
compared with what the builders will publish.  The check calls the builders'
own functions (``findings_section_category``, ``_findings_section_body``,
``_load_research_findings``, ``_load_profile_updates`` and
``dossier_resolution.resolve_presentation``), so it cannot drift from them.
It is read-only.

    .venv/bin/python tools/check_research_publication.py
    .venv/bin/python tools/check_research_publication.py --id Glasgow-951 Glasgow-438
    .venv/bin/python tools/check_research_publication.py --baseline data/site/research-publication-baseline.json
    .venv/bin/python tools/check_research_publication.py --json report.json
    .venv/bin/python tools/check_research_publication.py --baseline FILE --update-baseline [--accept-new]

Each item has a level: ``fail`` (research would not reach a reader),
``warn`` (needs a look) or ``info`` (listed for awareness).  ``--rules``
prints every rule with its plain explanation and fix.

Baseline (a ratchet): ``--baseline FILE`` tolerates the failing items listed
in FILE and fails only on new ones.  ``--update-baseline`` rewrites FILE
keeping only the listed items that still fail, so the baseline can only
shrink; add ``--accept-new`` to record new failing items on purpose (say why
in the commit message).

Exit codes:
  0  no failing item outside the baseline (no baseline given: no failing item)
  1  at least one new failing item
  2  the check could not run (bad arguments or a missing input)
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from dataclasses import asdict, dataclass
import datetime
from hashlib import sha1
import inspect
import json
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import build_research_catalog as catalog  # noqa: E402
from tools import dossier_resolution  # noqa: E402
from tools.dossier_resolution import _is_canonical_conclusion, resolve_presentation  # noqa: E402

DEFAULT_BASELINE = "data/site/research-publication-baseline.json"
SUPERSEDED_READINGS = "data/site/superseded-readings.json"
MANIFEST = "data/wikitree/research-catalogue-cases.json"

# code: (level, short title, plain explanation with the fix)
RULES = {
    "PREAMBLE_NOT_PUBLISHED": (
        "fail", "Text above the first heading",
        "Text above the first '## ' heading of findings.md is never published. Move it under a heading "
        "(for example '## Source findings') or delete it if it only repeats the template."),
    "SOURCE_ONLY_IN_INTERNAL_SECTION": (
        "fail", "Source cited only in an unpublished section",
        "A source link appears only in a section kept off the site as an editing log, so readers never see "
        "that record. Cite it in a published section (for example '## Source findings') or rename the section."),
    "INTERNAL_SECTION": (
        "info", "Section kept off the site",
        "The heading matches FINDINGS_INTERNAL_HEADINGS (an editing log), so the section is not published. "
        "Check the heading: rename the section if it holds research a reader needs."),
    "NOTES_HEADING": (
        "info", "Published under general notes",
        "The heading is not one the site recognises, so the section is published as general notes. "
        "Nothing is lost; consider a clearer heading."),
    "TEMPLATE_HIDES_CONTENT": (
        "fail", "Template filter empties a section with real rows",
        "The template filter removed every line of a section that still has real rows. Delete the template "
        "row by hand and report the builder fault."),
    "NO_PAGE_UNDECIDED": (
        "fail", "Findings with no page and no decision",
        "The profile has publishable research but no person page and no entry in "
        "data/wikitree/research-catalogue-cases.json. Record a decision: include, pending (with a reason), "
        "covered, internal or withheld."),
    "NO_PAGE_INCLUDED": (
        "fail", "Included but no page built",
        "The decision is 'include' but no person page exists. Run the targeted sync for this profile."),
    "NO_PAGE_PENDING": (
        "warn", "Findings waiting for a page",
        "The profile has publishable research and a decision that keeps it off the site for now. "
        "Review the decision."),
    "FOLDER_NOT_READ": (
        "fail", "Research folder that no builder reads",
        "This folder is not a profile folder and no tool reads it, so its findings.md never reaches the site. "
        "Move each finding into the findings of the people it concerns, route the folder to a page, or mark it "
        "'internal' in research-catalogue-cases.json."),
    "OPENING_FALLBACK": (
        "fail", "Page would open with a fall-back sentence",
        "The file has published research but no single overall '## Current conclusion', so the person page "
        "opens with a stock sentence instead of a summary. Write one overall conclusion; dated or topic "
        "conclusions are additions to it."),
    "CONCLUSION_CONFLICT": (
        "fail", "Two overall conclusions",
        "More than one undated overall conclusion, so the page says the assessments conflict. Merge them into "
        "one '## Current conclusion', or give the later one a date or topic so it reads as an addition."),
    "REGISTER_ENTRY_DROPPED": (
        "fail", "Open register entry that reaches no page",
        "An entry in surname-research/to-update.md looks open but the parser drops it, so no page lists the "
        "WikiTree change. Use the table form (| [Name](https://www.wikitree.com/wiki/ID) | OPEN | change |) "
        "or '- [[ID]] — change' under a dated section, or mark it DONE."),
    "QUEUE_ENTRY_DROPPED": (
        "fail", "Queue entry that reaches no page",
        "An entry in data/wikitree/profile-update-queue.json is dropped by the loader. Reopen the profile "
        "(reopened_completed_profiles), date the entry, or remove it if the work is done."),
    "QUEUE_ENTRY_CLOSED": (
        "info", "Queue entry kept as history",
        "The profile was completed live and the entry is not dated after the completion (or the amendment is "
        "already in the captured biography), so it is kept as history. If it is new work, give it a "
        "'queued_at' date after the completion or reopen the profile."),
    "CONCLUSION_OLDER_THAN_CORRECTION": (
        "warn", "Conclusion older than a later correction",
        "A dated section with correction wording is later than the overall conclusion, so the conclusion may "
        "be stale. Re-read the conclusion and update it (add 'Reviewed: YYYY-MM-DD' under it)."),
    "CORRECTION_NOT_IN_RECORDS": (
        "fail", "Correction not carried into a maintained record input",
        "A reading corrected in findings (listed in data/site/superseded-readings.json) still appears in a "
        "maintained input such as research/canonical_records.json. Correct that row too."),
    "CORRECTION_NOT_IN_BUILT_RECORDS": (
        "warn", "Built record data still shows a corrected reading",
        "A built file (records index, records.csv or the person's page data) still shows a reading that "
        "findings have corrected. It clears when that output is rebuilt; check it after the build."),
    "OVERVIEW_OLDER_THAN_FINDINGS": (
        "warn", "Authored overview older than its findings",
        "A presentation.json summary or a study story was last changed before the findings it summarises. "
        "Re-read it against the findings and update it or its assessment_date."),
    "PAGE_NOT_RESYNCED": (
        "fail", "Person page not re-synchronised",
        "The sections the builder would publish from findings.md differ from those stored for the built page, "
        "so the page was not re-synchronised after the file changed. Run the targeted sync for the profile."),
    "COVERED_FILE_SOURCES_MISSING": (
        "warn", "Merged file cites sources its target lacks",
        "The file is marked 'covered' by another profile, so it is not published, but it cites sources the "
        "target's findings do not. Copy them into the target's findings."),
}
LEVEL_ORDER = {"fail": 0, "warn": 1, "info": 2}
# Stock sentences the resolver writes when it has no summary to show.
STOCK_OPENINGS = frozenset(getattr(dossier_resolution, "GENERATED_ANSWERS", ())) | {
    "Research is present, but no maintained conclusion has yet been resolved for publication.",
    "No maintained assessment is recorded.",
    "Maintained assessments conflict and require editorial reconciliation.",
}

URL_RX = re.compile(r"https?://[^\s)\]>|\"'`]+")
SECTION_SPLIT = re.compile(r"^##\s+", re.M)  # the split rule of _load_research_findings
TEMPLATE_PREAMBLE = (  # boilerplate written by src/wikitree_family_export.py
    "record every useful result and negative search here as it is found.",
    "do not treat an unsourced tree or naming pattern as proof.",
)
CORRECTION_RX = re.compile(
    r"\b(supersed\w*|withdrawn|withdraw|retract\w*|correct(?:ed|ion|s)\b|no longer|overturn\w*|in error|"
    r"mistaken|not supported|rejected|downgrad\w*)", re.I)
MONTHS = ("january", "february", "march", "april", "may", "june", "july", "august", "september", "october",
          "november", "december")
_MONTH_RX = "|".join(m[:3] + r"\w*" for m in MONTHS)
DATE_PATTERNS = (
    (re.compile(r"\b(20\d\d)-(\d\d)-(\d\d)\b"), lambda m: (int(m[1]), int(m[2]), int(m[3]))),
    (re.compile(rf"\b(\d{{1,2}})\s+({_MONTH_RX})\.?\s+(20\d\d)\b", re.I),
     lambda m: (int(m[3]), MONTHS.index(next(x for x in MONTHS if m[2].casefold().startswith(x[:3]))) + 1,
                int(m[1]))),
)
REVIEWED_RX = re.compile(r"^\W*(?:Reviewed|Last reviewed|Conclusion reviewed)\W*\s*(20\d\d-\d\d-\d\d)", re.I | re.M)
OPEN_WORD = re.compile(r"\b(OPEN|REOPEN(?:ED)?)\b")
DONE_WORD = re.compile(r"\b(DONE|APPLIED LIVE|VERIFIED LIVE|RESOLVED|CREATED|RETIRED|SUPERSEDED|WITHDRAWN|"
                       r"NO ACTION|COMPLETED?)\b")
PROFILE_REF = re.compile(r"wikitree\.com/wiki/([A-Za-z][A-Za-z_'’-]*-\d+)|\[\[([A-Za-z][A-Za-z_'’-]*-\d+)(?:\|[^\]]*)?\]\]")


@dataclass
class Item:
    code: str
    subject: str
    key: str
    message: str
    level: str = ""

    def __post_init__(self):
        self.level = self.level or RULES[self.code][0]

    @property
    def baseline_key(self) -> str:
        return f"{self.subject}|{self.key}"


def _digest(value) -> str:
    return sha1(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:10]


def _norm_url(url: str) -> str:
    url = re.sub(r"^https?://(www\.)?", "", url.rstrip(".,;:*_")).rstrip("/")
    return url.casefold()


def _external_urls(text: str) -> set[str]:
    return {_norm_url(u) for u in URL_RX.findall(text or "")
            if not re.search(r"wikitree\.com|phenotype\.dev|localhost", u, re.I)}


def _latest_date(text: str) -> datetime.date | None:
    found = []
    for rx, convert in DATE_PATTERNS:
        for match in rx.finditer(text or ""):
            try:
                found.append(datetime.date(*convert(match)))
            except (ValueError, StopIteration):
                pass
    return max(found) if found else None


def is_profile_id(name: str) -> bool:
    """A WikiTree profile folder; ``opr-births-to-1700`` and similar are not."""
    return bool(catalog.WIKITREE_ID.fullmatch(name)) and name[:1].isupper()


def raw_sections(text: str) -> tuple[str, list[tuple[str, str]]]:
    blocks = SECTION_SPLIT.split(text)
    sections = []
    for block in blocks[1:]:
        title, _, body = block.partition("\n")
        sections.append((title.strip(), body.strip()))
    return blocks[0], sections


def _preamble_content(preamble: str) -> str:
    text = re.sub(r"<!--.*?-->", " ", preamble, flags=re.S)
    kept = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("# ") or re.match(r"^(Last updated|Updated|Status):", stripped, re.I):
            continue
        if stripped.casefold() in TEMPLATE_PREAMBLE or re.fullmatch(r"[-*_=\s]+", stripped):
            continue
        kept.append(stripped)
    return " ".join(kept)


def _template_hides_rows(body: str) -> bool:
    """True when the builder's filter empties a section that has real rows."""
    if not catalog.FINDINGS_TEMPLATE_MARKER.search(body) or catalog._findings_section_body(body):
        return False
    lines = [line for line in re.sub(r"<!--.*?-->", "", body, flags=re.S).splitlines() if line.strip()]
    real = 0
    for index, line in enumerate(lines):
        following = lines[index + 1] if index + 1 < len(lines) else ""
        if catalog.FINDINGS_TEMPLATE_MARKER.search(line) or catalog._TABLE_RULE.fullmatch(line):
            continue
        if line.lstrip().startswith("|") and catalog._TABLE_RULE.fullmatch(following) and "-" in following:
            continue  # table header
        real += 1
    return real > 0


@contextmanager
def builder_paths(root: Path):
    """Point the builder module at ``root`` (used by the tests' fixture trees)."""
    root = Path(root).resolve()
    names = {
        "PROJECT_ROOT": root,
        "RESEARCH_DIR": root / "research",
        "PROFILE_UPDATE_QUEUE": root / "data/wikitree/profile-update-queue.json",
        "PROFILE_UPDATE_REGISTER": root / "surname-research/to-update.md",
    }
    if root == Path(catalog.PROJECT_ROOT).resolve():
        yield
        return
    saved = {name: getattr(catalog, name) for name in names}
    try:
        for name, value in names.items():
            setattr(catalog, name, value)
        yield
    finally:
        for name, value in saved.items():
            setattr(catalog, name, value)


def _git_dates(root: Path, pathspecs: list[str]) -> dict[str, str]:
    """Last change date (YYYY-MM-DD) per path: git history, uncommitted = today."""
    dates: dict[str, str] = {}
    if not (root / ".git").exists():
        return dates
    try:
        log = subprocess.run(["git", "-C", str(root), "log", "--format=@%cs", "--name-only", "--", *pathspecs],
                             capture_output=True, text=True, check=True).stdout
        status = subprocess.run(["git", "-C", str(root), "status", "--porcelain", "--", *pathspecs],
                                capture_output=True, text=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        return dates
    current = None
    for line in log.splitlines():
        if line.startswith("@"):
            current = line[1:]
        elif line.strip() and line not in dates:
            dates[line] = current
    today = datetime.date.today().isoformat()
    for line in status.splitlines():
        dates[line[3:].strip().strip('"')] = today
    return dates


def _file_date(root: Path, relative: str, git_dates: dict[str, str]) -> str | None:
    if relative in git_dates:
        return git_dates[relative]
    path = root / relative
    if path.exists():
        return datetime.date.fromtimestamp(path.stat().st_mtime).isoformat()
    return None


def _load_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


class Checker:
    def __init__(self, root: Path = ROOT, ids: list[str] | None = None, site: bool = True,
                 wikitree_evidence: dict | None = None,
                 profile_updates: dict | None = None,
                 profile_update_report: list[dict] | None = None):
        self.root = Path(root).resolve()
        self.research = self.root / "research"
        self.web = self.root / "www"
        self.items: list[Item] = []
        self.manifest = _load_json(self.root / MANIFEST, {}).get("cases", {})
        self.requested = list(dict.fromkeys(ids or []))
        self.scope: set[str] | None = None
        if ids:
            aliases = {key for key, entry in self.manifest.items()
                       if entry.get("profile_id") in ids and key not in ids}
            self.scope = set(ids) | aliases
        self.wikitree_evidence = wikitree_evidence
        self.profile_updates = profile_updates
        self.profile_update_report = profile_update_report
        index_path = self.web / "data/people-index.json"
        self.site = bool(site and index_path.exists())
        self.slug_for: dict[str, str] = {}
        if self.site:
            rows = _load_json(index_path, [])
            # A person's own page first; a page that only lists the ID as an
            # alternate (a comparison page, for example) never takes its place.
            for row in rows:
                self.slug_for.setdefault(row["id"], row.get("catalogue_id") or row["id"].lower())
            for row in rows:
                slug = row.get("catalogue_id") or row["id"].lower()
                for pid in row.get("alternate_ids") or []:
                    self.slug_for.setdefault(pid, slug)
        self.internal_counts: dict[str, int] = {}
        self.files_checked = 0

    # -- helpers ---------------------------------------------------------
    def add(self, code: str, subject: str, key: str, message: str, level: str = "") -> None:
        if self.scope is not None and subject not in self.scope:
            return
        self.items.append(Item(code, subject, key, message, level))

    def in_scope(self, subject: str) -> bool:
        return self.scope is None or subject in self.scope

    def status(self, ident: str) -> str | None:
        return (self.manifest.get(ident) or {}).get("status")

    def page_slug(self, ident: str) -> str:
        return self.slug_for.get(ident, ident.lower())

    def page_json(self, ident: str) -> dict | None:
        path = self.web / "people" / f"{self.page_slug(ident)}.json"
        return _load_json(path, None) if path.exists() else None

    def has_page(self, ident: str) -> bool:
        return (self.web / "people" / f"{self.page_slug(ident)}.html").exists()

    # -- findings files --------------------------------------------------
    def findings_ids(self) -> list[str]:
        folders = sorted(p.parent.name for p in self.research.glob("*/findings.md"))
        return [name for name in folders if self.in_scope(name)]

    def check_findings(self) -> None:
        tool_text = None
        for ident in self.findings_ids():
            self.files_checked += 1
            text = (self.research / ident / "findings.md").read_text(encoding="utf-8")
            preamble, sections = raw_sections(text)
            status = self.status(ident)
            loaded = catalog._load_research_findings([ident])
            own = next((f for f in loaded if f.get("source_path") == f"research/{ident}/findings.md"), None)
            published = own["sections"] if own else []

            content = _preamble_content(preamble)
            if len(content.split()) >= 8:
                self.add("PREAMBLE_NOT_PUBLISHED", ident, _digest(content),
                         f"{len(content.split())} words above the first heading: \"{content[:110]}\"")

            published_urls = set().union(*(_external_urls(s["markdown"]) for s in published)) if published else set()
            internal = 0
            for title, body in sections:
                category = catalog.findings_section_category(title)
                if category == "internal" and body:
                    internal += 1
                    self.add("INTERNAL_SECTION", ident, title, f"'{title[:90]}'")
                    if status != "covered":
                        orphaned = sorted(_external_urls(body) - published_urls - self.captured_urls(ident))
                        if orphaned:
                            self.add("SOURCE_ONLY_IN_INTERNAL_SECTION", ident, title,
                                     f"'{title[:70]}' cites {len(orphaned)} source(s) found in no published "
                                     f"section, e.g. {orphaned[0][:90]}")
                elif category != "internal" and body and _template_hides_rows(body):
                    self.add("TEMPLATE_HIDES_CONTENT", ident, title, f"'{title[:90]}'")
            if internal:
                self.internal_counts[ident] = internal
            for section in published:
                if section.get("category") == "notes":
                    self.add("NOTES_HEADING", ident, section["title"], f"'{section['title'][:90]}'")

            if status == "covered":
                self.check_covered(ident, text)
                continue
            target = (self.manifest.get(ident) or {}).get("profile_id") if status == "include_record" else ident
            target = target or ident
            page = self.site and self.has_page(target)
            if not is_profile_id(ident) and not page:
                # A record subject or study folder: published only if a page or a tool reads it.
                if self.site and published and status not in {"internal", "withheld"}:
                    if tool_text is None:
                        tool_text = self.tool_sources()
                    if not folder_is_read(ident, tool_text):
                        self.add("FOLDER_NOT_READ", ident, "folder",
                                 f"{len(published)} publishable section(s); no page and no tool reads research/{ident}/")
                continue
            if status in {"internal", "withheld"} or not published:
                self.check_staleness(ident, sections)
                continue
            if self.site and not page:
                if status is None:
                    self.add("NO_PAGE_UNDECIDED", ident, "page", "no person page and no catalogue decision")
                elif status == "include":
                    self.add("NO_PAGE_INCLUDED", ident, "page", "decision 'include' but no page has been built")
                else:
                    reason = (self.manifest.get(ident) or {}).get("reason") or ""
                    self.add("NO_PAGE_PENDING", ident, "page", f"decision '{status}' {reason[:90]}".strip())
            if status != "include_record" and (page or not self.site):
                self.check_opening(ident, loaded, sections)
            self.check_staleness(ident, sections)
            if self.site:
                self.check_page_sync(ident, target, published)

    @property
    def evidence(self) -> dict:
        if self.wikitree_evidence is None:
            self.wikitree_evidence = catalog._load_wikitree_evidence()
        return self.wikitree_evidence

    def captured_urls(self, ident: str) -> set[str]:
        """Sources the live WikiTree profile already cites (shown in the page's WikiTree snapshot)."""
        capture = (self.evidence.get("profiles") or {}).get(ident) or {}
        urls = set(capture.get("external_urls") or [])
        return {_norm_url(u) for u in urls} | _external_urls(capture.get("biography_wikitext") or "")

    def tool_sources(self) -> str:
        parts = []
        for pattern in ("tools/**/*.py", "tools/**/*.json", "src/**/*.py"):
            for path in self.root.glob(pattern):
                if path.name == Path(__file__).name or "__pycache__" in path.parts:
                    continue
                try:
                    parts.append(path.read_text(encoding="utf-8", errors="ignore"))
                except OSError:
                    pass
        return "\n".join(parts)

    def check_covered(self, ident: str, text: str) -> None:
        target = (self.manifest.get(ident) or {}).get("profile_id")
        if not target or target == ident:
            return
        target_path = self.research / target / "findings.md"
        target_urls = _external_urls(target_path.read_text(encoding="utf-8")) if target_path.exists() else set()
        missing = sorted(_external_urls(text) - target_urls)
        if missing:
            self.add("COVERED_FILE_SOURCES_MISSING", ident, target,
                     f"covered by {target}; {len(missing)} source(s) absent from its findings, e.g. {missing[0][:80]}")

    def check_opening(self, ident: str, loaded: list[dict], sections: list[tuple[str, str]]) -> None:
        if not loaded:
            return
        page = self.page_json(ident) if self.site else None
        dossier = {"research_findings": loaded,
                   "research_assessments": (page or {}).get("research_assessments") or []}
        authored = _load_json(self.research / ident / "presentation.json", {})
        if authored.get("resolution_state"):
            return  # an editor set the state on purpose
        resolution = resolve_presentation(ident, dossier, {}, authored)
        state = resolution["resolution"]["state"]
        if state == "conflict":
            titles = [title for title, _ in sections
                      if catalog.findings_section_category(title) == "conclusion" and _is_canonical_conclusion(title)]
            self.add("CONCLUSION_CONFLICT", ident, "conflict", f"{len(titles)} overall conclusions: {titles[:3]}")
        elif state in {"unmapped", "none"} and (
                not ((resolution.get("position") or {}).get("answer") or "").strip()
                or ((resolution.get("position") or {}).get("answer") or "").strip() in STOCK_OPENINGS):
            conclusions = [(title, body) for title, body in sections
                           if catalog.findings_section_category(title) == "conclusion"]
            additions = resolution["resolution"].get("additions") or []
            if len(additions) > 1:
                kind, detail = "additions", f"{len(additions)} dated additions and no overall conclusion"
            elif conclusions and not any(catalog._findings_section_body(body) for _, body in conclusions):
                kind, detail = "placeholder", "the conclusion is still the template text or empty"
            else:
                kind, detail = "missing", "no '## Current conclusion' section"
            self.add("OPENING_FALLBACK", ident, kind, detail)

    def check_staleness(self, ident: str, sections: list[tuple[str, str]]) -> None:
        canonical = [(i, title, body) for i, (title, body) in enumerate(sections)
                     if catalog.findings_section_category(title) == "conclusion" and _is_canonical_conclusion(title)]
        if not canonical:
            return
        index, title, body = canonical[0]
        reviewed = REVIEWED_RX.search(body)
        concluded = datetime.date.fromisoformat(reviewed[1]) if reviewed else _latest_date(title + "\n" + body)
        later = []
        for other_index, (other_title, other_body) in enumerate(sections):
            if other_index == index or catalog.findings_section_category(other_title) == "internal":
                continue
            dated = _latest_date(other_title + "\n" + other_body[:400])
            if dated and (concluded is None or dated > concluded) and CORRECTION_RX.search(other_body):
                later.append((dated, other_title))
        if later:
            dated, other_title = max(later)
            since = concluded.isoformat() if concluded else "an undated conclusion"
            self.add("CONCLUSION_OLDER_THAN_CORRECTION", ident, other_title,
                     f"'{other_title[:70]}' ({dated}) corrects something after {since}; {len(later)} such section(s)")

    def check_page_sync(self, ident: str, target: str, published: list[dict]) -> None:
        page = self.page_json(target)
        if page is None:
            return
        source_path = f"research/{ident}/findings.md"
        built = [s for f in page.get("research_findings") or [] if f.get("source_path") == source_path
                 for s in f.get("sections") or []]
        expected_titles = [s["title"] for s in published]
        built_titles = [s.get("title") for s in built]
        if expected_titles == built_titles:
            return
        added = [t for t in expected_titles if t not in built_titles]
        removed = [t for t in built_titles if t not in expected_titles]
        detail = f"page has {len(built_titles)} section(s), the file now gives {len(expected_titles)}"
        if added:
            detail += f"; not on the page: {added[0][:60]!r}" + (f" and {len(added) - 1} more" if len(added) > 1 else "")
        if removed:
            detail += f"; only on the page: {removed[0][:60]!r}"
        self.add("PAGE_NOT_RESYNCED", ident, _digest(expected_titles), detail)

    # -- authored overviews ---------------------------------------------
    def check_overviews(self) -> None:
        dates = _git_dates(self.root, [":(glob)research/*/findings.md", ":(glob)research/*/presentation.json",
                                       "tools/study_stories"])
        for path in sorted(self.research.glob("*/presentation.json")):
            ident = path.parent.name
            if not self.in_scope(ident) or not (path.parent / "findings.md").exists():
                continue
            authored = _load_json(path, {})
            if not (authored.get("position") or authored.get("opening")
                    or (authored.get("reading_guide") or {}).get("current_answer")):
                continue
            written = _file_date(self.root, f"research/{ident}/presentation.json", dates)
            findings = _file_date(self.root, f"research/{ident}/findings.md", dates)
            if written and findings and findings > written:
                self.add("OVERVIEW_OLDER_THAN_FINDINGS", ident, "presentation.json",
                         f"presentation.json summary {written}; findings.md changed {findings}")
        branches = {b.get("id"): b for b in _load_json(self.web / "assets/research/branches.json", [])}
        id_for_slug = {slug: pid for pid, slug in self.slug_for.items()}
        id_rx = re.compile(r"\b([A-Z][A-Za-z_'’-]*-\d+)\b")
        for path in sorted((self.root / "tools/study_stories").glob("*.json")):
            story = _load_json(path, {})
            members = set(id_rx.findall(json.dumps(story, ensure_ascii=False)))
            members |= {id_for_slug.get(slug, slug) for slug in (branches.get(story.get("id")) or {}).get("members", [])}
            if self.scope is not None and not members & self.scope:
                continue
            written = _file_date(self.root, str(path.relative_to(self.root)), dates)
            newer = sorted(pid for pid in members
                           if (self.research / pid / "findings.md").exists()
                           and (_file_date(self.root, f"research/{pid}/findings.md", dates) or "") > (written or "9"))
            if newer:
                self.items.append(Item("OVERVIEW_OLDER_THAN_FINDINGS", f"story:{path.stem}", "story",
                                       f"story {written}; {len(newer)} member findings changed since, e.g. {newer[:3]}"))

    # -- corrected readings ---------------------------------------------
    def check_superseded_readings(self) -> None:
        registry = _load_json(self.root / SUPERSEDED_READINGS, {}).get("readings", [])
        if not registry:
            return
        maintained = [self.root / "research/canonical_records.json", self.root / "research/latest-findings.json",
                      self.root / "tools/repair_research_questions.py",
                      *sorted(self.research.glob("*/presentation.json")),
                      *sorted(self.research.glob("*/records_mentions.json")),
                      *sorted((self.root / "tools/study_stories").glob("*.json"))]
        built = [self.web / "data/records-index.json", self.web / "map/data/records.csv"]
        cache: dict[Path, str] = {}

        def text_of(path: Path) -> str:
            if path not in cache:
                cache[path] = path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""
            return cache[path]

        for reading in registry:
            subject = reading.get("profile") or reading["id"]
            if not self.in_scope(subject):
                continue
            pattern = re.compile(reading["superseded"] if reading.get("regex") else re.escape(reading["superseded"]))
            allowed = re.compile(reading.get("allowed_context") or r"(?!x)x", re.I)
            pages = []
            if reading.get("profile") and self.site:
                pages.append(self.web / "people" / f"{self.page_slug(reading['profile'])}.json")
            for group, paths in (("maintained", maintained), ("built", built + pages)):
                for path in paths:
                    text = text_of(path)
                    hits = [m for m in pattern.finditer(text) if not allowed.search(_context(text, m))]
                    if not hits:
                        continue
                    code = "CORRECTION_NOT_IN_RECORDS" if group == "maintained" else "CORRECTION_NOT_IN_BUILT_RECORDS"
                    relative = str(path.relative_to(self.root))
                    self.add(code, subject, f"{reading['id']}|{relative}",
                             f"{relative} still reads '{reading['superseded'][:50]}' ({len(hits)}x); "
                             f"corrected: {reading.get('corrected', '')[:90]} [{reading.get('recorded_in', '')}]")

    # -- register and queue ---------------------------------------------
    def check_register_and_queue(self) -> None:
        register = self.root / "surname-research/to-update.md"
        if not register.exists():
            return
        evidence = self.evidence
        report: list[dict] = []
        preloaded = self.profile_updates is not None and self.profile_update_report is not None
        supports_report = preloaded or "report" in inspect.signature(catalog._load_profile_updates).parameters
        if preloaded:
            updates = self.profile_updates
            report = self.profile_update_report
        else:
            try:
                parameters = inspect.signature(catalog._load_profile_updates).parameters
                kwargs = {"report": report} if supports_report else {}
                if self.scope is not None and "profile_ids" in parameters:
                    kwargs["profile_ids"] = self.scope
                updates = catalog._load_profile_updates(evidence, **kwargs)
            except ValueError as error:
                self.items.append(Item("QUEUE_ENTRY_DROPPED", "queue", _digest(str(error)),
                                       f"the update loader stopped: {error}"))
                updates = {}
        accounted_lines = set()
        for entry in report:
            if entry.get("line"):
                accounted_lines.add(entry["line"])
            if entry.get("accepted"):
                continue
            kind = entry.get("kind") or "dropped"
            if kind in {"completed", "applied"}:
                self.add("QUEUE_ENTRY_CLOSED", entry["profile_id"], kind,
                         f"{entry['reason']}: {entry.get('summary', '')[:90]}")
            elif entry.get("source") == "register":
                # A register-derived fallback can be rejected while a reviewed
                # complete replacement is successfully loaded for this person.
                # That entry reaches the site through the reviewed amendment;
                # it is not a dropped publication. The loader has already
                # validated its preservation review and source retention.
                replacement = updates.get(entry["profile_id"], {})
                if replacement.get("draft_path") and replacement.get("preservation_review_path"):
                    continue
                where = f"to-update.md:{entry['line']} " if entry.get("line") else ""
                self.add("REGISTER_ENTRY_DROPPED", entry["profile_id"],
                         _digest(entry.get("text", "")) if entry.get("text") else kind,
                         f"{where}{entry['reason']}: {(entry.get('text') or entry.get('summary') or '')[:100]}")
            else:
                self.add("QUEUE_ENTRY_DROPPED", entry["profile_id"], kind,
                         f"{entry['reason']}: {entry.get('summary', '')[:100]}")
        lines = register.read_text(encoding="utf-8").splitlines()
        heading = ""
        for number, line in enumerate(lines, 1):
            if line.startswith("#"):
                heading = line.lstrip("#").strip()
                continue
            refs = [a or b for a, b in PROFILE_REF.findall(line)]
            if not refs or number in accounted_lines:
                continue
            if not register_line_looks_open(line, heading):
                continue
            if refs[0] in updates and not supports_report:
                continue
            self.add("REGISTER_ENTRY_DROPPED", refs[0], _digest(line.strip()),
                     f"to-update.md:{number} the parser does not read this entry: {line.strip()[:100]}")
        if not supports_report:
            queue = _load_json(self.root / "data/wikitree/profile-update-queue.json", {})
            for profile_id, entry in (queue.get("entries") or {}).items():
                if profile_id not in updates:
                    self.add("QUEUE_ENTRY_DROPPED", profile_id, "dropped",
                             f"not loaded: {(entry.get('summary') or '')[:100]}")

    def run(self) -> "Checker":
        self.check_findings()
        self.check_overviews()
        self.check_superseded_readings()
        self.check_register_and_queue()
        self.items.sort(key=lambda i: (LEVEL_ORDER[i.level], i.code, i.subject, i.key))
        return self


def _context(text: str, match: re.Match) -> str:
    """The wording around a match, kept inside one quoted value or line and 120 characters."""
    before = max(text.rfind('"', 0, match.start()), text.rfind("\n", 0, match.start()), match.start() - 121) + 1
    ends = [i for i in (text.find('"', match.end()), text.find("\n", match.end())) if i != -1]
    after = min([*ends, match.end() + 120])
    return text[before:after]


def folder_is_read(folder: str, tool_text: str) -> bool:
    """True when some tool opens research/<folder>/ (a bare id or HTML anchor does not count)."""
    name = re.escape(folder)
    return bool(re.search(
        rf"(?<![\w-])research/{name}\b|RESEARCH(?:_DIR)?\s*/\s*[\"']{name}[\"']|[\"']research[\"']\s*/\s*[\"']{name}[\"']",
        tool_text))


def register_line_looks_open(line: str, heading: str) -> bool:
    """A register line that a reader of the file would take as open work."""
    stripped = line.strip()
    if re.search(r"\b(completed|resolved|applied|checked and not counted|drafts?|new-person|created)\b",
                 heading, re.I):
        return False
    status_text = stripped
    if stripped.startswith("|"):
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        status_text = " ".join(cells[1:3]) if len(cells) > 1 else stripped
    if DONE_WORD.search(status_text.replace("**", "")) and not OPEN_WORD.search(status_text):
        return False
    if OPEN_WORD.search(status_text):
        return True
    return bool(re.match(r"^[-*]\s+(\[\[[^\]]+\]\]|\[[^\]]+\]\(https?://www\.wikitree\.com/wiki/[^)]+\))\s*[—–:-]", stripped))


# -- baseline and output ---------------------------------------------------

def load_baseline(path: Path) -> dict[str, set[str]]:
    data = _load_json(path, None)
    if data is None:
        return {}
    return {code: set(keys) for code, keys in (data.get("items") or {}).items()}


def write_baseline(path: Path, entries: dict[str, set[str]]) -> None:
    payload = {
        "schema_version": 1,
        "generated": datetime.date.today().isoformat(),
        "about": ("Failing items of tools/check_research_publication.py tolerated for now. This list should only "
                  "shrink: fix an item and run --update-baseline. Keys are 'subject|key'."),
        "counts": {code: len(keys) for code, keys in sorted(entries.items()) if keys},
        "items": {code: sorted(keys) for code, keys in sorted(entries.items()) if keys},
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def compare_with_baseline(items: list[Item], baseline: dict[str, set[str]] | None) -> tuple[list[Item], dict[str, set[str]]]:
    fails = [i for i in items if i.level == "fail"]
    if baseline is None:
        return fails, {}
    new = [i for i in fails if i.baseline_key not in baseline.get(i.code, set())]
    current: dict[str, set[str]] = {}
    for item in fails:
        current.setdefault(item.code, set()).add(item.baseline_key)
    resolved = {code: keys - current.get(code, set()) for code, keys in baseline.items()}
    return new, {code: keys for code, keys in resolved.items() if keys}


def summary_text(checker: Checker, new: list[Item], resolved: dict[str, set[str]], baseline_used: bool,
                 examples: int, elapsed: float) -> str:
    out = [f"Research publication check: {checker.files_checked} findings file(s)"
           f"{' (' + ', '.join(checker.requested) + ')' if checker.requested else ''}; "
           f"built site {'checked' if checker.site else 'not checked'}; {elapsed:.1f} s"]
    by_code: dict[str, list[Item]] = {}
    for item in checker.items:
        by_code.setdefault(item.code, []).append(item)
    new_keys = {(i.code, i.baseline_key) for i in new}
    for code in sorted(by_code, key=lambda c: (LEVEL_ORDER[RULES[c][0]], c)):
        found = by_code[code]
        level, title, _ = RULES[code]
        fresh = [i for i in found if (i.code, i.baseline_key) in new_keys]
        extra = f", {len(fresh)} new" if baseline_used and level == "fail" else ""
        out.append(f"{level.upper():4}  {code:34} {len(found):5}{extra}  {title}")
        for item in (fresh or found)[:examples]:
            out.append(f"        {item.subject}: {item.message[:150]}")
    if not checker.items:
        out.append("No problems found.")
    if baseline_used:
        out.append(f"New failing items (not in the baseline): {len(new)}")
        gone = sum(len(keys) for keys in resolved.values())
        if gone and not checker.requested:
            out.append(f"Baseline items now fixed: {gone}. Run with --update-baseline to shrink the baseline.")
    else:
        out.append(f"Failing items: {len(new)} (no baseline given)")
    return "\n".join(out)


def run(root: Path = ROOT, ids: list[str] | None = None, site: bool = True,
        wikitree_evidence: dict | None = None,
        profile_updates: dict | None = None,
        profile_update_report: list[dict] | None = None) -> Checker:
    with builder_paths(root):
        return Checker(root, ids, site, wikitree_evidence,
                       profile_updates, profile_update_report).run()


def main(argv: list[str] | None = None, *, wikitree_evidence: dict | None = None,
         profile_updates: dict | None = None,
         profile_update_report: list[dict] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--id", nargs="+", dest="ids", metavar="ID", help="check only these profiles or folders")
    parser.add_argument("--json", metavar="FILE", help="write the full report as JSON ('-' for stdout)")
    parser.add_argument("--baseline", metavar="FILE", help=f"tolerate the failing items listed here ({DEFAULT_BASELINE})")
    parser.add_argument("--update-baseline", action="store_true", help="rewrite --baseline, keeping items that still fail")
    parser.add_argument("--accept-new", action="store_true", help="with --update-baseline: also record new failing items")
    parser.add_argument("--no-site", action="store_true", help="skip the checks that read the built site in www/")
    parser.add_argument("--examples", type=int, default=3, help="examples printed per rule (default 3)")
    parser.add_argument("--rules", action="store_true", help="print every rule with its explanation and exit")
    parser.add_argument("--root", default=str(ROOT), help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.rules:
        for code, (level, title, explanation) in RULES.items():
            print(f"{code} [{level}] {title}\n    {explanation}")
        return 0
    if args.update_baseline and (not args.baseline or args.ids):
        print("--update-baseline needs --baseline and a whole-repository run (no --id).", file=sys.stderr)
        return 2
    root = Path(args.root).resolve()
    if not (root / "research").is_dir():
        print(f"No research/ folder under {root}.", file=sys.stderr)
        return 2
    started = time.monotonic()
    checker = run(root, args.ids, site=not args.no_site,
                  wikitree_evidence=wikitree_evidence,
                  profile_updates=profile_updates,
                  profile_update_report=profile_update_report)
    elapsed = time.monotonic() - started
    baseline_path = Path(args.baseline) if args.baseline else None
    if baseline_path and not baseline_path.is_absolute():
        baseline_path = root / baseline_path
    baseline = None
    if baseline_path:
        if baseline_path.exists():
            baseline = load_baseline(baseline_path)
        elif not args.update_baseline:
            print(f"Baseline {baseline_path} not found.", file=sys.stderr)
            return 2
    new, resolved = compare_with_baseline(checker.items, baseline)
    if args.update_baseline:
        current: dict[str, set[str]] = {}
        for item in checker.items:
            if item.level == "fail":
                current.setdefault(item.code, set()).add(item.baseline_key)
        if baseline is None or args.accept_new:
            entries = current
        else:
            entries = {code: keys & baseline.get(code, set()) for code, keys in current.items()}
        write_baseline(baseline_path, entries)
        kept = sum(len(v) for v in entries.values())
        print(f"Baseline written: {baseline_path} ({kept} item(s)).")
        if baseline is not None and not args.accept_new:
            new, _ = compare_with_baseline(checker.items, entries)
        else:
            new = []
    report = {
        "generated": datetime.datetime.now().isoformat(timespec="seconds"),
        "scope": checker.requested or "all",
        "findings_files": checker.files_checked,
        "site_checked": checker.site,
        "elapsed_seconds": round(elapsed, 1),
        "counts": {code: sum(1 for i in checker.items if i.code == code) for code in RULES
                   if any(i.code == code for i in checker.items)},
        "new_failures": [asdict(i) for i in new],
        "baseline_items_fixed": {code: sorted(keys) for code, keys in resolved.items()},
        "internal_sections_per_file": checker.internal_counts,
        "rules": {code: {"level": level, "title": title, "explanation": text} for code, (level, title, text) in RULES.items()},
        "items": [asdict(i) for i in checker.items],
    }
    if args.json == "-":
        print(json.dumps(report, ensure_ascii=False, indent=1))
    else:
        if args.json:
            Path(args.json).write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(summary_text(checker, new, resolved, baseline is not None or args.update_baseline, args.examples, elapsed))
    return 1 if new else 0


if __name__ == "__main__":
    sys.exit(main())
