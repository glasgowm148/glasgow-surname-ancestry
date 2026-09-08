#!/usr/bin/env python3
"""Export WikiTree family evidence for iterative genealogy research.

Given a WikiTree ID or profile URL, this script exports:
- the subject
- parents
- siblings
- spouses
- children
- raw WikiTree biography/source text for every returned profile
- optional FamilySearch source-page text when explicitly requested

WikiTree-only operation is the default and does not start a browser. FamilySearch
browser support is an optional extension with separate dependencies.

Outputs:
- <WikiTree-ID>_ai_export.md — one self-contained file for pasting into AI
- optional raw JSON when --write-json is supplied
- optional FamilySearch page snapshots under artifacts/profile-exports/familysearch_pages/

Examples:
    python src/wikitree_family_export.py Glasgow-1538

    python src/wikitree_family_export.py Glasgow-3905 \
        --research-dir research/Glasgow-3905 \
        --descendant-depth 2

    python src/wikitree_family_export.py Glasgow-1538 \
        --familysearch-browser

    python src/wikitree_family_export.py Glasgow-1538 \
        --familysearch-browser \
        --familysearch-map Glasgow-1538=9QMG-R4T

    python src/wikitree_family_export.py Glasgow-1538 \
        --familysearch-browser \
        --familysearch-profile .cache/familysearch-browser \
        --output-dir artifacts/profile-exports
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import unquote, urlparse

import requests

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None


WIKITREE_API_URL = "https://api.wikitree.com/api.php"
REQUEST_TIMEOUT_SECONDS = 45
BATCH_SIZE = 100
WIKITREE_REQUEST_HEADERS = {
    # WikiTree's AWS WAF currently challenges generic script user agents before
    # the request reaches api.php. These are ordinary same-site browser headers;
    # no cookies, login details, or challenge-bypass tokens are used.
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/142.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json,text/plain,*/*",
    "Accept-Language": "en-GB,en;q=0.9",
    "Origin": "https://www.wikitree.com",
    "Referer": "https://www.wikitree.com/",
}
WIKITREE_APP_ID = os.environ.get("WIKITREE_APP_ID", "GlasgowSurnameResearch")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXPORT_DIR = PROJECT_ROOT / "artifacts" / "profile-exports"
DEFAULT_FS_PROFILE_DIR = ".cache/familysearch-browser"
DEFAULT_FS_TIMEOUT_MS = 60_000
DEFAULT_FS_SETTLE_SECONDS = 3.0
DEFAULT_FS_MAX_SCROLLS = 20
DEFAULT_FS_CDP_URL = "http://127.0.0.1:9222"
DEFAULT_FS_EXPAND_PASSES = 12
DEFAULT_FS_EXPAND_WAIT_SECONDS = 1.0

RESEARCH_SCHEMA_VERSION = 1
RESEARCH_STATE_FILE = "research_state.json"
RESEARCH_PLAN_FILE = "research_plan.json"
RESEARCH_INDEX_FILE = "evidence_index.json"
RESEARCH_BRIEF_FILE = "research_brief.md"
RESEARCH_FINDINGS_FILE = "findings.md"


def research_profile_notes_file(wikitree_id: str) -> str:
    """Return the manual-review WikiTree delta filename."""
    return f"{wikitree_id}.md"


def render_profile_notes_scaffold(wikitree_id: str) -> str:
    """Create the durable queue for facts absent from the current WikiTree page."""
    subject = (
        f"[Name not captured ({wikitree_id}), birth unknown, birthplace unknown]"
        f"(https://www.wikitree.com/wiki/{wikitree_id})"
    )
    return "\n".join(
        [
            f"# WikiTree update notes: {subject}",
            "",
            "Record only sourced facts and corrections missing from the current WikiTree",
            "profile. Keep same-name identities and inferred relationships explicitly",
            "unproved.",
            "",
            "## Suggested additions",
            "",
            "| Fact missing from profile | Source | Confidence |",
            "| --- | --- | --- |",
            "",
            "## Suggested corrections",
            "",
            "## Do not add as fact",
            "",
        ]
    )

FIELDS = [
    "Id",
    "PageId",
    "Name",
    "FirstName",
    "MiddleName",
    "MiddleInitial",
    "LastNameAtBirth",
    "LastNameCurrent",
    "LastNameOther",
    "Nicknames",
    "RealName",
    "ShortName",
    "LongName",
    "BirthName",
    "Prefix",
    "Suffix",
    "Gender",
    "BirthDate",
    "BirthLocation",
    "DeathDate",
    "DeathLocation",
    "Father",
    "Mother",
    "DataStatus",
    "Privacy",
    "Connected",
    "Created",
    "Touched",
    "Categories",
    "Templates",
    "Bio",
]

RELATION_NAMES = ("Parents", "Children", "Siblings", "Spouses")

FAMILYSEARCH_PID_PATTERNS = [
    re.compile(
        r"https?://(?:www\.|beta\.)?familysearch\.org/"
        r"tree/person/(?:details/|sources/)?([A-Z0-9]{4}-[A-Z0-9]{3})",
        re.IGNORECASE,
    ),
    re.compile(
        r"https?://(?:www\.|beta\.)?familysearch\.org/"
        r"ark:/61903/4:1:([A-Z0-9]{4}-[A-Z0-9]{3})",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bPID\s*[:=]?\s*([A-Z0-9]{4}-[A-Z0-9]{3})\b",
        re.IGNORECASE,
    ),
]


class ExportError(RuntimeError):
    """Raised when an API or browser export cannot be completed."""


def load_environment() -> None:
    """Load .env when python-dotenv is installed."""
    if load_dotenv is not None:
        load_dotenv()


def env_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default

    return value.strip().lower() in {"1", "true", "yes", "on"}


def normalise_wikitree_id(value: str) -> str:
    """Accept a WikiTree ID or profile URL and return a WikiTree ID."""
    value = value.strip()
    if not value:
        raise ValueError("WikiTree ID cannot be empty.")

    if "://" in value:
        parsed = urlparse(value)
        if "wikitree.com" not in parsed.netloc.lower():
            raise ValueError("The URL is not a WikiTree URL.")

        match = re.search(r"/wiki/([^/?#]+)", parsed.path)
        if not match:
            raise ValueError("Could not find a WikiTree ID in the URL.")

        value = unquote(match.group(1))

    value = value.replace(" ", "_")

    if not re.fullmatch(r"[^\s/]+-\d+", value):
        raise ValueError(
            f"'{value}' does not look like a WikiTree ID such as Glasgow-1538."
        )

    return value


def normalise_familysearch_pid(value: str) -> str:
    """Validate a FamilySearch Family Tree person ID."""
    value = value.strip().upper()

    if not re.fullmatch(r"[A-Z0-9]{4}-[A-Z0-9]{3}", value):
        raise ValueError(
            f"'{value}' does not look like a FamilySearch PID such as 9QMG-R4T."
        )

    return value


def post_wikitree(payload: dict[str, str]) -> dict[str, Any]:
    """POST to the WikiTree API and validate its usual response envelope."""
    payload = dict(payload)
    payload.setdefault("appId", WIKITREE_APP_ID)
    response = None
    for attempt in range(5):
        try:
            response = requests.post(
                WIKITREE_API_URL,
                data=payload,
                timeout=REQUEST_TIMEOUT_SECONDS,
                headers=WIKITREE_REQUEST_HEADERS,
            )
        except requests.RequestException as exc:
            if attempt == 4:
                raise ExportError(
                    f"WikiTree API request failed after five attempts: {exc}"
                ) from exc
            time.sleep(min(2.0 ** (attempt + 1), 60.0))
            continue

        if response.headers.get("x-amzn-waf-action", "").lower() == "challenge":
            raise ExportError(
                "WikiTree's AWS WAF challenged the API request before it "
                "reached api.php (HTTP 202). Retry later or use the public "
                "profile-page capture fallback."
            )

        retryable = response.status_code == 429 or response.status_code >= 500
        if retryable and attempt < 4:
            retry_after = response.headers.get("Retry-After")
            try:
                delay = (
                    max(0.0, float(retry_after))
                    if retry_after
                    else 2.0 ** (attempt + 1)
                )
            except (TypeError, ValueError):
                delay = 2.0 ** (attempt + 1)
            time.sleep(min(delay, 60.0))
            continue

        try:
            response.raise_for_status()
        except requests.RequestException as exc:
            qualifier = " after five attempts" if retryable else ""
            raise ExportError(f"WikiTree API request failed{qualifier}: {exc}") from exc
        break

    if response is None:
        raise ExportError("WikiTree API request produced no response.")

    try:
        data = response.json()
    except ValueError as exc:
        preview = response.text[:500].replace("\n", " ")
        raise ExportError(
            f"WikiTree returned non-JSON content: {preview}"
        ) from exc

    if not isinstance(data, list) or not data:
        raise ExportError("Unexpected empty response from WikiTree.")

    envelope = data[0]
    if not isinstance(envelope, dict):
        raise ExportError("Unexpected WikiTree response structure.")

    status = envelope.get("status")
    if status not in (0, "0", "", None):
        raise ExportError(f"WikiTree API returned status: {status!r}")

    return envelope


def get_relatives(wikitree_id: str) -> dict[str, Any]:
    """
    Discover immediate relatives.

    getRelatives is used for relationship discovery only. Nested profiles can
    be partial stubs, so their full biographies are fetched with getPeople.
    """
    envelope = post_wikitree(
        {
            "action": "getRelatives",
            "keys": wikitree_id,
            "fields": "Id,PageId,Name,Father,Mother",
            "getParents": "1",
            "getChildren": "1",
            "getSiblings": "1",
            "getSpouses": "1",
        }
    )

    items = envelope.get("items")
    if not isinstance(items, list) or not items:
        raise ExportError(
            "No profile was returned. Check the WikiTree ID and privacy."
        )

    item = items[0]
    if not isinstance(item, dict) or not isinstance(item.get("person"), dict):
        raise ExportError("The response did not contain a subject profile.")

    return envelope


def resolve_wikitree_redirect(wikitree_id: str) -> tuple[str, int | None]:
    """Resolve a merged-away WikiTree ID before collecting its family."""
    envelope = post_wikitree(
        {
            "action": "getProfile",
            "key": wikitree_id,
            "fields": "Name,Id,PageId,Touched",
            "resolveRedirect": "1",
        }
    )
    profile = envelope.get("profile")
    if not isinstance(profile, dict) or not profile.get("Name"):
        raise ExportError("WikiTree did not return a resolvable profile identity.")

    redirected_from = profile.get("redirectedFrom")
    return str(profile["Name"]), (
        int(redirected_from) if redirected_from is not None else None
    )


def iter_relation_stubs(person: dict[str, Any]) -> Iterable[dict[str, Any]]:
    """Yield every profile stub from the immediate relationship collections."""
    for relation in RELATION_NAMES:
        raw = person.get(relation, {})

        if isinstance(raw, dict):
            values = raw.values()
        elif isinstance(raw, list):
            values = raw
        else:
            values = []

        for value in values:
            if isinstance(value, dict):
                yield value


def collect_profile_names(
    relatives_envelope: dict[str, Any],
    requested_id: str,
) -> list[str]:
    """Collect the subject and immediate-relative WikiTree IDs."""
    item = relatives_envelope["items"][0]
    person = item["person"]

    names: set[str] = {requested_id}

    subject_name = person.get("Name") or item.get("user_name")
    if subject_name:
        names.add(str(subject_name))

    for profile in iter_relation_stubs(person):
        name = profile.get("Name")
        if name:
            names.add(str(name))

    return sorted(names)


def get_people(wikitree_ids: list[str]) -> dict[str, dict[str, Any]]:
    """Fetch complete profiles, explicitly including raw WikiTree biography."""
    people_by_name: dict[str, dict[str, Any]] = {}

    for start in range(0, len(wikitree_ids), BATCH_SIZE):
        batch = wikitree_ids[start : start + BATCH_SIZE]

        envelope = post_wikitree(
            {
                "action": "getPeople",
                "keys": ",".join(batch),
                "fields": ",".join(FIELDS),
                "bioFormat": "wiki",
            }
        )

        raw_people = envelope.get("people")
        if not isinstance(raw_people, dict):
            raise ExportError(
                "The getPeople response did not contain a people collection."
            )

        for profile in raw_people.values():
            if not isinstance(profile, dict):
                continue

            name = profile.get("Name")
            if name:
                people_by_name[str(name)] = profile

    return people_by_name


def merge_profile(
    stub: dict[str, Any],
    full_profiles: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Replace a relationship stub with a full getPeople profile."""
    name = stub.get("Name")
    if not name or str(name) not in full_profiles:
        return dict(stub)

    merged = dict(full_profiles[str(name)])

    # Marriage metadata comes from getRelatives.
    for key, value in stub.items():
        if key.startswith("marriage_") or key == "do_not_display":
            merged[key] = value

    return merged


def hydrate_family(
    relatives_envelope: dict[str, Any],
    full_profiles: dict[str, dict[str, Any]],
    requested_id: str,
) -> dict[str, Any]:
    """Hydrate the subject and all immediate relatives."""
    item = relatives_envelope["items"][0]
    stub_subject = item["person"]

    subject_name = (
        stub_subject.get("Name")
        or item.get("user_name")
        or requested_id
    )

    subject = dict(full_profiles.get(str(subject_name), stub_subject))

    for relation in RELATION_NAMES:
        raw = stub_subject.get(relation, {})

        if isinstance(raw, dict):
            hydrated: dict[str, dict[str, Any]] = {}

            for relation_id, stub in raw.items():
                if isinstance(stub, dict):
                    hydrated[str(relation_id)] = merge_profile(
                        stub,
                        full_profiles,
                    )

            subject[relation] = hydrated

        elif isinstance(raw, list):
            subject[relation] = [
                merge_profile(stub, full_profiles)
                for stub in raw
                if isinstance(stub, dict)
            ]

        else:
            subject[relation] = {}

    item["person"] = subject
    return relatives_envelope


def fetch_family(wikitree_id: str) -> dict[str, Any]:
    """Discover immediate family and hydrate every returned profile."""
    resolved_id, redirected_from = resolve_wikitree_redirect(wikitree_id)
    relatives = get_relatives(resolved_id)
    names = collect_profile_names(relatives, resolved_id)
    full_profiles = get_people(names)
    hydrated = hydrate_family(relatives, full_profiles, resolved_id)
    hydrated["redirect"] = {
        "requested": wikitree_id,
        "resolved": resolved_id,
        "redirected_from_person_id": redirected_from,
    }
    return hydrated


def extract_bio(profile: dict[str, Any]) -> str | None:
    """Read the biography regardless of Bio/bio casing or format."""
    bio = profile.get("Bio")
    if bio is None:
        bio = profile.get("bio")

    if isinstance(bio, str):
        return bio.strip() or None

    if isinstance(bio, dict):
        for key in ("wiki", "Wiki", "bio", "html"):
            value = bio.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

        return json.dumps(
            bio,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )

    return None


def extract_familysearch_pids(profile: dict[str, Any]) -> list[str]:
    """Extract PID references; a biography may mention other people too."""
    bio = extract_bio(profile) or ""
    pids: set[str] = set()

    for pattern in FAMILYSEARCH_PID_PATTERNS:
        for match in pattern.finditer(bio):
            pids.add(match.group(1).upper())

    return sorted(pids)


def parse_familysearch_mappings(
    values: list[str] | None,
) -> dict[str, list[str]]:
    """Parse repeated WikiTree-ID=FamilySearch-PID arguments."""
    mappings: dict[str, list[str]] = {}

    for raw in values or []:
        if "=" not in raw:
            raise ValueError(
                f"Invalid FamilySearch mapping '{raw}'. "
                "Use WikiTree-ID=FamilySearch-PID."
            )

        wt_raw, pid_raw = raw.split("=", 1)
        wt_id = normalise_wikitree_id(wt_raw)
        pid = normalise_familysearch_pid(pid_raw)

        mappings.setdefault(wt_id, [])
        if pid not in mappings[wt_id]:
            mappings[wt_id].append(pid)

    return mappings


def iter_all_profiles(person: dict[str, Any]) -> Iterable[dict[str, Any]]:
    """Yield the subject and all immediate relatives."""
    yield person

    for relation in RELATION_NAMES:
        raw = person.get(relation, {})

        if isinstance(raw, dict):
            values = raw.values()
        elif isinstance(raw, list):
            values = raw
        else:
            values = []

        for profile in values:
            if isinstance(profile, dict):
                yield profile


def attach_familysearch_pids(
    envelope: dict[str, Any],
    manual_mappings: dict[str, list[str]],
) -> dict[str, Any]:
    """Attach discovered and manually supplied FamilySearch PIDs."""
    person = envelope["items"][0].get("person")
    if not isinstance(person, dict):
        raise ExportError("The response did not include the subject profile.")

    for profile in iter_all_profiles(person):
        wt_id = str(profile.get("Name") or "")
        pids = set(extract_familysearch_pids(profile))
        pids.update(manual_mappings.get(wt_id, []))

        profile["FamilySearchPIDs"] = sorted(pids)
        profile.setdefault("FamilySearchBrowserSources", {})

    return envelope


def looks_like_familysearch_login(page: Any) -> bool:
    """Best-effort detection of a FamilySearch login screen."""
    url = page.url.lower()

    if any(
        fragment in url
        for fragment in (
            "/auth/",
            "/identity/",
            "signin",
            "login",
            "oauth2",
        )
    ):
        return True

    try:
        body = page.locator("body").inner_text(timeout=5_000).lower()
    except Exception:
        return False

    login_markers = (
        "sign in with church account",
        "familysearch sign in",
        "username",
        "forgot username",
        "forgot password",
    )

    return sum(marker in body for marker in login_markers) >= 2


def wait_for_manual_familysearch_login(page: Any, target_url: str) -> None:
    """
    Pause while the user logs into FamilySearch in the opened browser.

    This function never reads login fields or credentials.
    """
    print()
    print("FamilySearch login is required.")
    print("Log in manually in the browser window.")
    print("Complete any MFA/CAPTCHA yourself.")
    input("When the FamilySearch site is fully logged in, press Enter here: ")

    page.goto(
        target_url,
        wait_until="domcontentloaded",
        timeout=DEFAULT_FS_TIMEOUT_MS,
    )



def locator_is_visible(locator: Any) -> bool:
    try:
        return locator.is_visible()
    except Exception:
        return False


def click_first_visible(locators: list[Any], timeout_ms: int = 5_000) -> bool:
    for locator in locators:
        try:
            count = locator.count()
        except Exception:
            continue

        for index in range(count):
            candidate = locator.nth(index)

            if not locator_is_visible(candidate):
                continue

            try:
                candidate.scroll_into_view_if_needed(timeout=timeout_ms)
                candidate.click(timeout=timeout_ms)
                return True
            except Exception:
                continue

    return False


def switch_familysearch_to_detail_view(page: Any) -> bool:
    """Switch the FamilySearch Sources page to Detail View."""
    main = page.locator("main")
    scope = main if main.count() else page.locator("body")

    candidates = [
        scope.get_by_role(
            "button",
            name=re.compile(r"^\s*Detail View\s*$", re.IGNORECASE),
        ),
        scope.get_by_role(
            "tab",
            name=re.compile(r"^\s*Detail View\s*$", re.IGNORECASE),
        ),
        scope.get_by_text(
            re.compile(r"^\s*Detail View\s*$", re.IGNORECASE),
            exact=True,
        ),
        scope.locator(
            '[aria-label*="Detail View" i], '
            '[title*="Detail View" i], '
            '[data-testid*="detail" i]'
        ),
    ]

    clicked = click_first_visible(candidates)

    if clicked:
        try:
            page.wait_for_load_state("networkidle", timeout=8_000)
        except Exception:
            pass

        time.sleep(1.5)

    return clicked


def count_familysearch_detail_markers(page: Any) -> int:
    """Count fields that appear in FamilySearch Detail View source cards."""
    try:
        text = page.locator("main").inner_text(timeout=5_000)
    except Exception:
        try:
            text = page.locator("body").inner_text(timeout=5_000)
        except Exception:
            return 0

    markers = (
        "Source Date",
        "Web Page (Link to the Record)",
        "Where The Record Is Found",
        "Describe The Record",
        "Indexed Information",
        "Reason This Source Is Attached",
        "Source Modified",
    )

    return sum(text.count(marker) for marker in markers)


def get_familysearch_source_count(page: Any) -> int:
    """Read the source count from the page tab/header."""
    try:
        text = page.locator("body").inner_text(timeout=5_000)
    except Exception:
        return 0

    matches = re.findall(r"Sources\s*\((\d+)\)", text, re.IGNORECASE)

    if not matches:
        return 0

    return max(int(value) for value in matches)


def wait_for_familysearch_detail_view(
    page: Any,
    source_count: int,
    timeout_seconds: float = 30.0,
) -> dict[str, Any]:
    """
    Wait until FamilySearch Detail View has rendered.

    No source rows or VIEW buttons are clicked. Detail View itself already
    renders the full source cards.
    """
    deadline = time.time() + timeout_seconds
    marker_count = count_familysearch_detail_markers(page)

    while time.time() < deadline:
        if source_count == 0:
            break

        if marker_count > 0:
            break

        time.sleep(1.0)
        marker_count = count_familysearch_detail_markers(page)

    return {
        "source_count": source_count,
        "detail_marker_count": marker_count,
        "detail_view_ready": source_count == 0 or marker_count > 0,
    }


def expand_all_familysearch_sources(
    page: Any,
    passes: int,
    wait_seconds: float,
) -> dict[str, Any]:
    """
    Select Detail View once, wait for the full page to render, then stop.

    The parameters are retained for CLI compatibility but no source-card
    clicking is performed.
    """
    detail_view_clicked = switch_familysearch_to_detail_view(page)

    source_count = get_familysearch_source_count(page)

    readiness = wait_for_familysearch_detail_view(
        page=page,
        source_count=source_count,
        timeout_seconds=max(15.0, passes * wait_seconds),
    )

    return {
        "detail_view_clicked": detail_view_clicked,
        "source_count": source_count,
        "detail_marker_count": readiness["detail_marker_count"],
        "detail_view_ready": readiness["detail_view_ready"],
        "source_title_count": source_count,
        "expanded_disclosures": 0,
        "clicked_unverified": 0,
        "expanded_view_buttons": 0,
        "expanded_source_rows": 0,
        "source_results": [],
    }


def scroll_familysearch_page(
    page: Any,
    max_scrolls: int,
    settle_seconds: float,
) -> None:
    """Scroll repeatedly to trigger lazy-loaded source cards."""
    previous_height = 0
    unchanged = 0

    for _ in range(max_scrolls):
        try:
            current_height = page.evaluate(
                "() => Math.max("
                "document.body.scrollHeight,"
                "document.documentElement.scrollHeight"
                ")"
            )
        except Exception:
            break

        page.evaluate(
            "() => window.scrollTo(0, "
            "Math.max(document.body.scrollHeight, "
            "document.documentElement.scrollHeight))"
        )
        time.sleep(settle_seconds)

        if current_height == previous_height:
            unchanged += 1
        else:
            unchanged = 0

        previous_height = current_height

        if unchanged >= 2:
            break

    page.evaluate("() => window.scrollTo(0, 0)")


def clean_page_text(text: str) -> str:
    """Normalise whitespace without destroying source-page line structure."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in text.splitlines()]

    output: list[str] = []
    blank = False

    for line in lines:
        stripped = line.strip()

        if not stripped:
            if not blank:
                output.append("")
            blank = True
            continue

        output.append(stripped)
        blank = False

    return "\n".join(output).strip()


def extract_page_links(page: Any) -> list[dict[str, str]]:
    """Extract visible links from the FamilySearch source page."""
    try:
        raw_links = page.locator("a[href]").evaluate_all(
            """
            elements => elements.map(element => ({
                text: (element.innerText || element.textContent || "").trim(),
                href: element.href || ""
            }))
            """
        )
    except Exception:
        return []

    links: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()

    for item in raw_links:
        if not isinstance(item, dict):
            continue

        href = str(item.get("href") or "").strip()
        text = re.sub(r"\s+", " ", str(item.get("text") or "").strip())

        if not href:
            continue

        # Keep FamilySearch links and direct record/image URLs. Drop nav noise.
        if "familysearch.org" not in href:
            continue

        key = (text, href)
        if key in seen:
            continue

        seen.add(key)
        links.append({"text": text, "href": href})

    return links


def save_familysearch_page_snapshot(
    page: Any,
    pid: str,
    output_dir: Path,
) -> dict[str, str]:
    """Save HTML and a full-page screenshot for later manual checking."""
    output_dir.mkdir(parents=True, exist_ok=True)

    html_path = output_dir / f"{pid}_sources.html"
    screenshot_path = output_dir / f"{pid}_sources.png"

    html_path.write_text(page.content(), encoding="utf-8")

    screenshot_error = ""
    try:
        page.screenshot(path=str(screenshot_path), full_page=True)
    except Exception as exc:
        screenshot_error = str(exc)

    result = {
        "html_path": str(html_path),
    }

    if not screenshot_error:
        result["screenshot_path"] = str(screenshot_path)
    else:
        result["screenshot_error"] = screenshot_error

    return result


def scrape_familysearch_pid(
    page: Any,
    pid: str,
    snapshot_dir: Path,
    max_scrolls: int,
    settle_seconds: float,
    expand_passes: int,
    expand_wait_seconds: float,
) -> dict[str, Any]:
    """Open one FamilySearch person Sources page and export visible data."""
    source_url = f"https://www.familysearch.org/tree/person/sources/{pid}"

    page.goto(
        source_url,
        wait_until="domcontentloaded",
        timeout=DEFAULT_FS_TIMEOUT_MS,
    )

    if looks_like_familysearch_login(page):
        wait_for_manual_familysearch_login(page, source_url)

    try:
        page.wait_for_load_state(
            "networkidle",
            timeout=15_000,
        )
    except Exception:
        # FamilySearch may keep background requests open.
        pass

    time.sleep(settle_seconds)

    # Scroll first so all lazy-loaded source rows are present, then expand
    # each source title exactly once. A second pass could collapse open cards.
    scroll_familysearch_page(page, max_scrolls, settle_seconds)

    expansion = expand_all_familysearch_sources(
        page=page,
        passes=expand_passes,
        wait_seconds=expand_wait_seconds,
    )

    if looks_like_familysearch_login(page):
        raise ExportError(
            f"FamilySearch still appears to be on a login page for {pid}."
        )

    body_text = clean_page_text(
        page.locator("body").inner_text(timeout=20_000)
    )
    links = extract_page_links(page)
    snapshots = save_familysearch_page_snapshot(
        page,
        pid,
        snapshot_dir,
    )

    return {
        "status": "ok",
        "pid": pid,
        "requested_url": source_url,
        "final_url": page.url,
        "page_title": page.title(),
        "visible_text": body_text,
        "links": links,
        "expansion": expansion,
        "snapshots": snapshots,
    }



def scrape_familysearch_sources_via_cdp(
    envelope: dict[str, Any],
    cdp_url: str,
    output_dir: Path,
    max_scrolls: int,
    settle_seconds: float,
    expand_passes: int,
    expand_wait_seconds: float,
) -> dict[str, Any]:
    """
    Attach to normal Chrome over CDP and process each unique PID once.

    A fresh temporary tab is created for each PID and closed afterwards.
    Popups opened by that temporary tab are closed immediately. Existing user
    tabs and the Chrome process itself are left untouched.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise ExportError(
            "Playwright is not installed. Run:\n"
            "  python -m pip install playwright python-dotenv\n"
            "No Playwright browser install is required for CDP mode."
        ) from exc

    person = envelope["items"][0].get("person")
    if not isinstance(person, dict):
        raise ExportError("The response did not include the subject profile.")

    # Build a global PID list first. This avoids duplicate work and makes it
    # obvious in the terminal how many FamilySearch pages will be processed.
    all_pids: list[str] = sorted(
        {
            pid
            for profile in iter_all_profiles(person)
            for pid in profile.get("FamilySearchPIDs", [])
        }
    )

    print(
        f"Detected {len(all_pids)} unique FamilySearch PID(s): "
        + (", ".join(all_pids) if all_pids else "none")
    )

    pid_cache: dict[str, dict[str, Any]] = {}
    snapshot_dir = output_dir / "familysearch_pages"

    with sync_playwright() as playwright:
        try:
            browser = playwright.chromium.connect_over_cdp(cdp_url)
        except Exception as exc:
            raise ExportError(
                f"Could not attach to Chrome at {cdp_url}: {exc}\n\n"
                "Launch normal Chrome with remote debugging enabled first."
            ) from exc

        contexts = browser.contexts
        if not contexts:
            raise ExportError(
                "Chrome was reached, but no browser context was available."
            )

        context = contexts[0]

        for position, pid in enumerate(all_pids, start=1):
            print(
                f"[{position}/{len(all_pids)}] "
                f"Fetching FamilySearch sources for {pid}..."
            )

            page = None

            try:
                page = context.new_page()

                # Only close popups created by this temporary page.
                def close_popup(popup: Any) -> None:
                    try:
                        popup.close()
                    except Exception:
                        pass

                page.on("popup", close_popup)

                pid_cache[pid] = scrape_familysearch_pid(
                    page=page,
                    pid=pid,
                    snapshot_dir=snapshot_dir,
                    max_scrolls=max_scrolls,
                    settle_seconds=settle_seconds,
                    expand_passes=expand_passes,
                    expand_wait_seconds=expand_wait_seconds,
                )

                print(f"[{position}/{len(all_pids)}] Completed {pid}")

            except Exception as exc:
                pid_cache[pid] = {
                    "status": "error",
                    "pid": pid,
                    "error": str(exc),
                }

                print(
                    f"[{position}/{len(all_pids)}] Failed {pid}: {exc}",
                    file=sys.stderr,
                )

            finally:
                if page is not None:
                    try:
                        if not page.is_closed():
                            page.close()
                    except Exception:
                        pass

        # Do not call browser.close(). With a CDP connection that can close the
        # user's real Chrome process. Exiting sync_playwright disconnects.

    # Attach the cached result to every WikiTree profile that references it.
    for profile in iter_all_profiles(person):
        profile["FamilySearchBrowserSources"] = {
            pid: pid_cache.get(
                pid,
                {
                    "status": "error",
                    "pid": pid,
                    "error": "PID was detected but not processed.",
                },
            )
            for pid in profile.get("FamilySearchPIDs", [])
        }

    return envelope


def scrape_familysearch_sources(
    envelope: dict[str, Any],
    profile_dir: Path,
    output_dir: Path,
    headless: bool,
    max_scrolls: int,
    settle_seconds: float,
    expand_passes: int,
    expand_wait_seconds: float,
) -> dict[str, Any]:
    """Scrape FamilySearch Sources pages for every detected PID."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise ExportError(
            "Playwright is not installed. Run:\n"
            "  python -m pip install playwright python-dotenv\n"
            "  python -m playwright install chromium"
        ) from exc

    person = envelope["items"][0].get("person")
    if not isinstance(person, dict):
        raise ExportError("The response did not include the subject profile.")

    pid_cache: dict[str, dict[str, Any]] = {}
    snapshot_dir = output_dir / "familysearch_pages"

    with sync_playwright() as playwright:
        profile_dir.mkdir(parents=True, exist_ok=True)

        context = playwright.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir.resolve()),
            headless=headless,
            viewport={"width": 1440, "height": 1000},
            accept_downloads=False,
        )

        try:
            pages = context.pages
            page = pages[0] if pages else context.new_page()

            for profile in iter_all_profiles(person):
                results: dict[str, Any] = {}

                for pid in profile.get("FamilySearchPIDs", []):
                    if pid not in pid_cache:
                        print(f"Fetching FamilySearch sources for {pid}...")

                        try:
                            pid_cache[pid] = scrape_familysearch_pid(
                                page=page,
                                pid=pid,
                                snapshot_dir=snapshot_dir,
                                max_scrolls=max_scrolls,
                                settle_seconds=settle_seconds,
                                expand_passes=expand_passes,
                                expand_wait_seconds=expand_wait_seconds,
                            )
                        except Exception as exc:
                            pid_cache[pid] = {
                                "status": "error",
                                "pid": pid,
                                "error": str(exc),
                            }

                    results[pid] = pid_cache[pid]

                profile["FamilySearchBrowserSources"] = results
        finally:
            context.close()

    return envelope


def profile_url(profile: dict[str, Any]) -> str:
    name = profile.get("Name")
    return f"https://www.wikitree.com/wiki/{name}" if name else ""


def display_name(profile: dict[str, Any]) -> str:
    parts = [
        profile.get("Prefix"),
        profile.get("FirstName") or profile.get("RealName"),
        profile.get("MiddleName"),
        profile.get("LastNameCurrent") or profile.get("LastNameAtBirth"),
        profile.get("Suffix"),
    ]

    value = " ".join(str(part).strip() for part in parts if part)
    return value or str(profile.get("Name") or "Unknown profile")


def profile_identity_label(profile: dict[str, Any]) -> str:
    """Return the required human-facing identity context for a profile."""
    wt_id = str(profile.get("Name") or profile.get("wikitree_id") or "unknown")
    name = str(profile.get("display_name") or display_name(profile))
    birth_date = clean_date(profile.get("BirthDate") or profile.get("birth_date"))
    birth_location = scalar(
        profile.get("BirthLocation") or profile.get("birth_location")
    )
    birth = "birth unknown" if birth_date == "unknown" else f"born {birth_date}"
    location = (
        "birthplace unknown" if birth_location == "unknown" else birth_location
    )
    return f"{name} ({wt_id}), {birth}, {location}"


def profile_markdown_link(profile: dict[str, Any]) -> str:
    """Render a WikiTree profile as a contextual, clickable Markdown label."""
    wt_id = str(profile.get("Name") or profile.get("wikitree_id") or "")
    url = f"https://www.wikitree.com/wiki/{wt_id}" if wt_id else ""
    label = profile_identity_label(profile)
    return f"[{label}]({url})" if url else label


def wikitree_id_markdown_link(
    wt_id: str,
    profiles: dict[str, dict[str, Any]],
) -> str:
    """Link an ID using captured identity context when available."""
    profile = profiles.get(wt_id)
    if isinstance(profile, dict):
        return profile_markdown_link(profile)
    url = f"https://www.wikitree.com/wiki/{wt_id}"
    return (
        f"[Name not captured ({wt_id}), birth unknown, birthplace unknown]"
        f"({url})"
    )


def terminal_profile_link(profile: dict[str, Any]) -> str:
    """Render an OSC 8 terminal link, retaining a visible URL off-terminal."""
    label = profile_identity_label(profile)
    wt_id = str(profile.get("Name") or profile.get("wikitree_id") or "")
    url = f"https://www.wikitree.com/wiki/{wt_id}" if wt_id else ""
    if url and sys.stdout.isatty() and os.environ.get("TERM") != "dumb":
        return f"\033]8;;{url}\033\\{label}\033]8;;\033\\"
    return f"{label} - {url}" if url else label


def terminal_wikitree_id_link(
    wt_id: str,
    profiles: dict[str, dict[str, Any]],
) -> str:
    """Render a terminal link, explicitly retaining missing identity fields."""
    profile = profiles.get(wt_id)
    if not isinstance(profile, dict):
        profile = {
            "wikitree_id": wt_id,
            "display_name": "Name not captured",
        }
    return terminal_profile_link(profile)


def clean_date(value: Any) -> str:
    if not value:
        return "unknown"

    text = str(value)

    if re.fullmatch(r"\d{4}-00-00", text):
        return text[:4]

    if re.fullmatch(r"\d{4}-\d{2}-00", text):
        return text[:7]

    return text


def scalar(value: Any) -> str:
    if value is None or value == "":
        return "unknown"

    if isinstance(value, (dict, list)):
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
        )

    return str(value)


def relation_profiles(
    person: dict[str, Any],
    relation: str,
) -> list[dict[str, Any]]:
    raw = person.get(relation, {})

    if isinstance(raw, dict):
        profiles = [
            value
            for value in raw.values()
            if isinstance(value, dict)
        ]
    elif isinstance(raw, list):
        profiles = [
            value
            for value in raw
            if isinstance(value, dict)
        ]
    else:
        profiles = []

    return sorted(
        profiles,
        key=lambda profile: (
            clean_date(profile.get("BirthDate")),
            str(profile.get("LastNameAtBirth") or ""),
            str(profile.get("FirstName") or ""),
            str(profile.get("Name") or ""),
        ),
    )


def format_marriage_metadata(profile: dict[str, Any]) -> list[str]:
    lines: list[str] = []

    marriage_date = profile.get("marriage_date")
    marriage_location = profile.get("marriage_location")
    marriage_end_date = profile.get("marriage_end_date")

    if marriage_date and marriage_date != "0000-00-00":
        line = f"- Marriage date: {clean_date(marriage_date)}"
        if marriage_location:
            line += f" — {marriage_location}"
        lines.append(line)
    elif marriage_location:
        lines.append(f"- Marriage location: {marriage_location}")

    if marriage_end_date and marriage_end_date != "0000-00-00":
        lines.append(
            f"- Marriage end date: {clean_date(marriage_end_date)}"
        )

    return lines


def familysearch_markdown(
    profile: dict[str, Any],
    heading_level: int,
) -> str:
    """Render scraped FamilySearch source-page material."""
    heading = "#" * heading_level
    pids = profile.get("FamilySearchPIDs", [])
    results = profile.get("FamilySearchBrowserSources", {})

    lines = [
        f"{heading} FamilySearch",
        "",
    ]

    if not pids:
        lines.extend(
            [
                "_No FamilySearch PID reference was found in the WikiTree biography "
                "or supplied manually._",
                "",
            ]
        )
        return "\n".join(lines)

    for pid in pids:
        lines.append(
            f"- FamilySearch PID reference ({pid}): "
            f"https://www.familysearch.org/tree/person/details/{pid}"
        )
        lines.append(
            f"- FamilySearch sources: "
            f"https://www.familysearch.org/tree/person/sources/{pid}"
        )

        result = results.get(pid)

        if not isinstance(result, dict):
            lines.append(
                "  - Sources were not scraped. Run with "
                "`--familysearch-browser`."
            )
            continue

        if result.get("status") != "ok":
            lines.append(
                f"  - Scrape error: {result.get('error', 'unknown error')}"
            )
            continue

        lines.extend(
            [
                f"  - Final URL: {result.get('final_url', '')}",
                f"  - Page title: {result.get('page_title', '')}",
            ]
        )

        expansion = result.get("expansion")
        if isinstance(expansion, dict):
            lines.append(
                "  - Detail View: "
                f"clicked={expansion.get('detail_view_clicked', False)}, "
                f"sources={expansion.get('source_count', 0)}, "
                f"ready={expansion.get('detail_view_ready', False)}, "
                f"detail markers={expansion.get('detail_marker_count', 0)}"
            )

        snapshots = result.get("snapshots", {})
        if isinstance(snapshots, dict):
            if snapshots.get("html_path"):
                lines.append(
                    f"  - Saved HTML: {snapshots['html_path']}"
                )
            if snapshots.get("screenshot_path"):
                lines.append(
                    f"  - Saved screenshot: {snapshots['screenshot_path']}"
                )

        links = result.get("links", [])
        if isinstance(links, list) and links:
            lines.extend(
                [
                    "",
                    f"{heading}# Extracted FamilySearch links",
                    "",
                ]
            )

            for link in links:
                if not isinstance(link, dict):
                    continue

                text = str(link.get("text") or "").strip()
                href = str(link.get("href") or "").strip()
                label = text or href

                lines.append(f"- [{label}]({href})")

        visible_text = result.get("visible_text")
        if visible_text:
            lines.extend(
                [
                    "",
                    f"{heading}# Visible FamilySearch source-page text",
                    "",
                    "```text",
                    str(visible_text),
                    "```",
                ]
            )

    lines.append("")
    return "\n".join(lines)


def profile_markdown(
    profile: dict[str, Any],
    heading_level: int = 3,
) -> str:
    heading = "#" * heading_level
    wt_id = str(profile.get("Name") or "unknown")
    title = profile_markdown_link(profile)
    url = profile_url(profile)

    lines = [
        f"{heading} {title}",
        "",
    ]

    if url:
        lines.append(f"- WikiTree: {url}")

    lines.extend(
        [
            f"- Sex: {scalar(profile.get('Gender'))}",
            (
                f"- Born: {clean_date(profile.get('BirthDate'))}"
                f" — {scalar(profile.get('BirthLocation'))}"
            ),
            (
                f"- Died: {clean_date(profile.get('DeathDate'))}"
                f" — {scalar(profile.get('DeathLocation'))}"
            ),
            f"- Father person ID: {scalar(profile.get('Father'))}",
            f"- Mother person ID: {scalar(profile.get('Mother'))}",
            f"- Privacy level: {scalar(profile.get('Privacy'))}",
            f"- Connected: {scalar(profile.get('Connected'))}",
            f"- Profile created: {scalar(profile.get('Created'))}",
            f"- Last touched: {scalar(profile.get('Touched'))}",
        ]
    )

    lines.extend(format_marriage_metadata(profile))

    categories = profile.get("Categories")
    if categories:
        lines.append(f"- Categories: {scalar(categories)}")

    lines.extend(
        [
            "",
            f"{heading}# WikiTree biography/source text",
            "",
        ]
    )

    bio = extract_bio(profile)

    if bio:
        lines.extend(
            [
                "```text",
                bio,
                "```",
            ]
        )
    else:
        lines.append(
            "_No biography text was returned by WikiTree getPeople._"
        )

    lines.extend(
        [
            "",
            familysearch_markdown(profile, heading_level + 1),
        ]
    )

    return "\n".join(lines)


def make_markdown(
    envelope: dict[str, Any],
    requested_id: str,
) -> str:
    item = envelope["items"][0]
    person = item.get("person")

    if not isinstance(person, dict):
        raise ExportError("The response did not include the subject profile.")

    lines = [
        f"# WikiTree immediate-family export: {requested_id}",
        "",
        (
            "> Generated from WikiTree and, where requested, visible "
            "FamilySearch pages. Linked relationships and user-contributed "
            "biographies are not proof. Verify claims against original records."
        ),
        "",
        "## Subject",
        "",
        profile_markdown(person, 3),
    ]

    sections = [
        ("Parents", "Parents"),
        ("Siblings", "Siblings"),
        ("Spouses", "Spouses"),
        ("Children", "Children"),
    ]

    for title, relation_key in sections:
        relatives = relation_profiles(person, relation_key)

        lines.extend(
            [
                f"## {title}",
                "",
            ]
        )

        if not relatives:
            lines.extend(
                [
                    (
                        "_No profiles returned. This may mean none are linked, "
                        "or the relationship/profile is access-restricted._"
                    ),
                    "",
                ]
            )
            continue

        for relative in relatives:
            lines.append(profile_markdown(relative, 3))

    lines.extend(
        [
            "## Raw structured export",
            "",
            (
                "The JSON below is the complete hydrated WikiTree and "
                "FamilySearch browser result used to build this dossier."
            ),
            "",
            "```json",
            json.dumps(
                envelope,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            ),
            "```",
            "",
        ]
    )

    lines.extend(
        [
            "## Suggested AI review questions",
            "",
            (
                "1. Which claims are supported by original or indexed records, "
                "and which merely come from tree structure?"
            ),
            (
                "2. Do dates, locations, occupations, spouses and children conflict?"
            ),
            (
                "3. Are parents, spouses or children attached without records "
                "explicitly naming the relationship?"
            ),
            (
                "4. Do FamilySearch source pages contain records absent from "
                "the WikiTree biography?"
            ),
            (
                "5. Are there likely conflations between people with the same name?"
            ),
            "6. Which original record images should be checked next?",
            "",
        ]
    )

    return "\n".join(lines)


def utc_now() -> str:
    """Return a filesystem-friendly UTC timestamp."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def write_json_file(path: Path, value: Any) -> None:
    """Write JSON atomically so an interrupted run does not corrupt a case."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def read_json_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ExportError(f"Could not read JSON from {path}: {exc}") from exc

    if not isinstance(value, dict):
        raise ExportError(f"Expected a JSON object in {path}.")

    return value


def default_research_plan(wikitree_id: str) -> dict[str, Any]:
    """Create the AI-editable half of a research case."""
    return {
        "schema_version": RESEARCH_SCHEMA_VERSION,
        "case_id": wikitree_id,
        "objective": (
            f"Establish the identity and documented family of {wikitree_id}, "
            "separating sourced facts from tree assertions."
        ),
        "questions": [
            {
                "id": "identity",
                "question": "Which records prove the subject's identity across events?",
                "status": "open",
                "answer": "",
            },
            {
                "id": "parents",
                "question": "Which original or indexed records identify the parents?",
                "status": "open",
                "answer": "",
            },
            {
                "id": "family",
                "question": "Which spouses and children are directly supported by records?",
                "status": "open",
                "answer": "",
            },
            {
                "id": "conflicts",
                "question": "What conflicts or same-name conflations must be resolved?",
                "status": "open",
                "answer": "",
            },
        ],
        "web_searches": [],
        "targets": [
            {
                "kind": "wikitree",
                "id": wikitree_id,
                "generation": 0,
                "reason": "Initial subject and immediate family capture.",
                "status": "pending",
            }
        ],
        "findings": [],
    }


def load_research_case(
    case_dir: Path,
    wikitree_id: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Create or load the internal state and editable plan for a case."""
    case_dir.mkdir(parents=True, exist_ok=True)
    state_path = case_dir / RESEARCH_STATE_FILE
    plan_path = case_dir / RESEARCH_PLAN_FILE
    findings_path = case_dir / RESEARCH_FINDINGS_FILE
    profile_notes_path = case_dir / research_profile_notes_file(wikitree_id)

    if not findings_path.exists():
        subject = wikitree_id_markdown_link(wikitree_id, {})
        findings_path.write_text(
            "\n".join(
                [
                    f"# Findings: {subject}",
                    "",
                    "Record every useful result and negative search here as it is found.",
                    "Do not treat an unsourced tree or naming pattern as proof.",
                    "",
                    "## Current conclusion",
                    "",
                    "No sourced conclusion recorded yet.",
                    "",
                    "## Source findings",
                    "",
                    "| Source | Finding | Assessment |",
                    "| --- | --- | --- |",
                    "| _Add a URL, archive reference, or local artifact_ | "
                    "_State exactly what the source establishes_ | "
                    "_Direct, indirect, negative, or exclusionary evidence_ |",
                    "",
                ]
            ),
            encoding="utf-8",
        )

    if not profile_notes_path.exists():
        profile_notes_path.write_text(
            render_profile_notes_scaffold(wikitree_id),
            encoding="utf-8",
        )

    if state_path.exists():
        state = read_json_object(state_path)
    else:
        now = utc_now()
        state = {
            "schema_version": RESEARCH_SCHEMA_VERSION,
            "root_wikitree_id": wikitree_id,
            "created_at": now,
            "updated_at": now,
            "captures": [],
            "errors": [],
        }

    root_id = state.get("root_wikitree_id")
    if root_id != wikitree_id:
        raise ExportError(
            f"Research case {case_dir} belongs to {root_id}, not {wikitree_id}."
        )

    if plan_path.exists():
        plan = read_json_object(plan_path)
    else:
        plan = default_research_plan(wikitree_id)

    if plan.get("case_id") != wikitree_id:
        raise ExportError(
            f"Research plan {plan_path} belongs to "
            f"{plan.get('case_id')}, not {wikitree_id}."
        )

    for key in ("questions", "web_searches", "targets", "findings"):
        if not isinstance(plan.get(key), list):
            raise ExportError(f"'{key}' must be a list in {plan_path}.")

    write_json_file(state_path, state)
    write_json_file(plan_path, plan)
    return state, plan


def add_research_target(
    plan: dict[str, Any],
    kind: str,
    target_id: str,
    reason: str,
    profile_id: str | None = None,
    generation: int | None = None,
) -> None:
    """Add a target unless the same target is already present."""
    if kind not in {"wikitree", "familysearch"}:
        raise ValueError(f"Unsupported research target kind: {kind}")

    targets = plan.setdefault("targets", [])
    for target in targets:
        if not isinstance(target, dict):
            continue
        if target.get("kind") != kind or target.get("id") != target_id:
            continue
        if kind == "wikitree" or target.get("profile_id") == profile_id:
            return

    target: dict[str, Any] = {
        "kind": kind,
        "id": target_id,
        "reason": reason,
        "status": "pending",
    }
    if profile_id:
        target["profile_id"] = profile_id
    if generation is not None:
        target["generation"] = generation
    targets.append(target)


def research_target_generation(
    plan: dict[str, Any],
    wikitree_id: str,
) -> int | None:
    for target in plan.get("targets", []):
        if not isinstance(target, dict):
            continue
        if target.get("kind") != "wikitree" or target.get("id") != wikitree_id:
            continue
        generation = target.get("generation")
        if isinstance(generation, int) and generation >= 0:
            return generation
    return None


def queue_descendant_targets(
    plan: dict[str, Any],
    envelope: dict[str, Any],
    subject_generation: int | None,
    descendant_depth: int,
) -> int:
    """Queue children whose captures are needed to hydrate the next generation."""
    if subject_generation is None or subject_generation + 1 >= descendant_depth:
        return 0

    person = envelope["items"][0].get("person")
    if not isinstance(person, dict):
        return 0

    before = len(plan.get("targets", []))
    child_generation = subject_generation + 1
    for child in relation_profiles(person, "Children"):
        child_id = child.get("Name")
        if not child_id:
            continue
        add_research_target(
            plan,
            "wikitree",
            str(child_id),
            (
                f"Automatic generation {child_generation} descendant capture; "
                "hydrates the following generation."
            ),
            generation=child_generation,
        )

    return len(plan.get("targets", [])) - before


def set_research_target_status(
    plan: dict[str, Any],
    kind: str,
    target_id: str,
    status: str,
    note: str = "",
    profile_id: str | None = None,
) -> None:
    for target in plan.get("targets", []):
        if not isinstance(target, dict):
            continue
        if target.get("kind") != kind or target.get("id") != target_id:
            continue
        if kind == "familysearch" and target.get("profile_id") != profile_id:
            continue
        target["status"] = status
        target["updated_at"] = utc_now()
        if note:
            target["note"] = note


def research_familysearch_mappings(
    plan: dict[str, Any],
) -> dict[str, list[str]]:
    mappings: dict[str, list[str]] = {}
    for target in plan.get("targets", []):
        if not isinstance(target, dict) or target.get("kind") != "familysearch":
            continue
        if target.get("status") == "complete":
            continue

        wt_id = target.get("profile_id")
        pid = target.get("id")
        if not isinstance(wt_id, str) or not isinstance(pid, str):
            continue

        wt_id = normalise_wikitree_id(wt_id)
        pid = normalise_familysearch_pid(pid)
        mappings.setdefault(wt_id, [])
        if pid not in mappings[wt_id]:
            mappings[wt_id].append(pid)

    return mappings


def merge_familysearch_mappings(
    *mapping_sets: dict[str, list[str]],
) -> dict[str, list[str]]:
    merged: dict[str, list[str]] = {}
    for mappings in mapping_sets:
        for wt_id, pids in mappings.items():
            merged.setdefault(wt_id, [])
            for pid in pids:
                if pid not in merged[wt_id]:
                    merged[wt_id].append(pid)
    return merged


def extract_envelope_from_ai_export(path: Path) -> dict[str, Any]:
    """Recover the embedded raw JSON from an existing AI Markdown export."""
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ExportError(f"Could not read AI export {path}: {exc}") from exc

    marker = "## Raw structured export"
    marker_at = content.find(marker)
    if marker_at < 0:
        raise ExportError(f"No '{marker}' section was found in {path}.")

    match = re.search(r"```json\s*\n(.*?)\n```", content[marker_at:], re.DOTALL)
    if not match:
        raise ExportError(f"No JSON code block was found after '{marker}' in {path}.")

    try:
        value = json.loads(match.group(1))
    except ValueError as exc:
        raise ExportError(f"Embedded JSON in {path} is invalid: {exc}") from exc

    if not isinstance(value, dict):
        raise ExportError(f"Embedded JSON in {path} is not an object.")
    return value


def envelope_subject_id(envelope: dict[str, Any]) -> str:
    try:
        person = envelope["items"][0]["person"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ExportError("Capture does not contain a subject profile.") from exc

    if not isinstance(person, dict) or not person.get("Name"):
        raise ExportError("Capture subject does not have a WikiTree ID.")
    return str(person["Name"])


def store_research_capture(
    case_dir: Path,
    state: dict[str, Any],
    envelope: dict[str, Any],
    requested_id: str,
    source: str,
) -> str:
    """Store an immutable raw capture and register it in case state."""
    captures_dir = case_dir / "captures"
    captures_dir.mkdir(parents=True, exist_ok=True)
    captured_at = utc_now()
    stamp = captured_at.replace(":", "").replace("-", "")
    base = f"{stamp}_{safe_stem(requested_id)}"
    capture_path = captures_dir / f"{base}.json"
    suffix = 2
    while capture_path.exists():
        capture_path = captures_dir / f"{base}_{suffix}.json"
        suffix += 1

    write_json_file(capture_path, envelope)
    relative_path = capture_path.relative_to(case_dir).as_posix()
    person = envelope["items"][0].get("person", {})
    profile_count = sum(1 for _ in iter_all_profiles(person)) if isinstance(person, dict) else 0

    state.setdefault("captures", []).append(
        {
            "captured_at": captured_at,
            "requested_wikitree_id": requested_id,
            "subject_wikitree_id": envelope_subject_id(envelope),
            "source": source,
            "path": relative_path,
            "profile_count": profile_count,
        }
    )
    state["updated_at"] = captured_at
    return relative_path


def extract_external_urls(profile: dict[str, Any]) -> list[str]:
    """Collect useful evidence URLs without retaining browser navigation links."""
    urls = set(re.findall(r"https?://[^\s<>{}\[\]|\"']+", extract_bio(profile) or ""))
    browser_sources = profile.get("FamilySearchBrowserSources", {})
    if isinstance(browser_sources, dict):
        for result in browser_sources.values():
            if not isinstance(result, dict):
                continue
            for link in result.get("links", []):
                if not isinstance(link, dict):
                    continue
                href = str(link.get("href") or "")
                if "/ark:/" in href or "/record/" in href:
                    urls.add(href)

    return sorted(url.rstrip(".,;:)]}") for url in urls)


def relation_ids(profile: dict[str, Any], relation: str) -> list[str]:
    return sorted(
        str(relative.get("Name"))
        for relative in relation_profiles(profile, relation)
        if relative.get("Name")
    )


def summarise_profile(
    profile: dict[str, Any],
    capture_path: str,
) -> dict[str, Any]:
    pids = profile.get("FamilySearchPIDs", [])
    familysearch: dict[str, Any] = {}
    raw_results = profile.get("FamilySearchBrowserSources", {})
    if isinstance(raw_results, dict):
        for pid, result in raw_results.items():
            if not isinstance(result, dict):
                continue
            record_links = []
            for link in result.get("links", []):
                if not isinstance(link, dict):
                    continue
                href = str(link.get("href") or "")
                if "/ark:/" in href or "/record/" in href:
                    record_links.append(href)
            familysearch[str(pid)] = {
                "status": result.get("status"),
                "page_title": result.get("page_title"),
                "final_url": result.get("final_url"),
                "record_links": sorted(set(record_links)),
                "snapshots": result.get("snapshots", {}),
            }

    return {
        "wikitree_id": str(profile.get("Name") or ""),
        "display_name": display_name(profile),
        "gender": profile.get("Gender"),
        "birth_date": profile.get("BirthDate"),
        "birth_location": profile.get("BirthLocation"),
        "death_date": profile.get("DeathDate"),
        "death_location": profile.get("DeathLocation"),
        "father_person_id": profile.get("Father"),
        "mother_person_id": profile.get("Mother"),
        "relations": {
            relation.lower(): relation_ids(profile, relation)
            for relation in RELATION_NAMES
        },
        "familysearch_pids": sorted(str(pid) for pid in pids),
        "familysearch": familysearch,
        "evidence_urls": extract_external_urls(profile),
        "biography": extract_bio(profile) or "",
        "capture_paths": [capture_path],
    }


def merge_profile_summary(
    existing: dict[str, Any],
    incoming: dict[str, Any],
) -> dict[str, Any]:
    """Prefer the latest facts while retaining union-valued evidence."""
    merged = dict(existing)
    for key, value in incoming.items():
        if key in {"relations", "familysearch", "evidence_urls", "familysearch_pids", "capture_paths"}:
            continue
        if value not in (None, "", [], {}):
            merged[key] = value

    merged["evidence_urls"] = sorted(
        set(existing.get("evidence_urls", [])) | set(incoming.get("evidence_urls", []))
    )
    merged["familysearch_pids"] = sorted(
        set(existing.get("familysearch_pids", []))
        | set(incoming.get("familysearch_pids", []))
    )
    merged["capture_paths"] = list(
        dict.fromkeys(existing.get("capture_paths", []) + incoming.get("capture_paths", []))
    )

    relationships: dict[str, list[str]] = {}
    for relation in (name.lower() for name in RELATION_NAMES):
        relationships[relation] = sorted(
            set(existing.get("relations", {}).get(relation, []))
            | set(incoming.get("relations", {}).get(relation, []))
        )
    merged["relations"] = relationships
    merged["familysearch"] = {
        **existing.get("familysearch", {}),
        **incoming.get("familysearch", {}),
    }
    return merged


def build_evidence_index(
    case_dir: Path,
    state: dict[str, Any],
) -> dict[str, Any]:
    """Build a compact, deduplicated view over all immutable captures."""
    profiles: dict[str, dict[str, Any]] = {}
    for capture in state.get("captures", []):
        if not isinstance(capture, dict) or not isinstance(capture.get("path"), str):
            continue
        capture_path = capture["path"]
        envelope = read_json_object(case_dir / capture_path)
        person = envelope["items"][0].get("person")
        if not isinstance(person, dict):
            continue

        for profile in iter_all_profiles(person):
            wt_id = str(profile.get("Name") or "")
            if not wt_id:
                continue
            summary = summarise_profile(profile, capture_path)
            if wt_id in profiles:
                profiles[wt_id] = merge_profile_summary(profiles[wt_id], summary)
            else:
                profiles[wt_id] = summary

    return {
        "schema_version": RESEARCH_SCHEMA_VERSION,
        "root_wikitree_id": state["root_wikitree_id"],
        "generated_at": utc_now(),
        "capture_count": len(state.get("captures", [])),
        "profiles": dict(sorted(profiles.items())),
    }


def render_research_brief(
    plan: dict[str, Any],
    state: dict[str, Any],
    index: dict[str, Any],
) -> str:
    """Render the compact dossier that an AI should analyse each iteration."""
    profiles = index.get("profiles", {})
    root_id = str(state["root_wikitree_id"])
    root_link = wikitree_id_markdown_link(root_id, profiles)
    lines = [
        f"# Genealogy research case: {root_link}",
        "",
        "> Treat trees and user biographies as clues, not proof. Cite each finding "
        "to a record or reliable page, distinguish index from original image, and "
        "record negative searches as well as positive results.",
        "",
        "## Objective",
        "",
        str(plan.get("objective") or "No objective recorded."),
        "",
        "## Loop status",
        "",
        f"- Captures: {len(state.get('captures', []))}",
        f"- Deduplicated profiles: {len(index.get('profiles', {}))}",
        f"- Plan: `{RESEARCH_PLAN_FILE}`",
        f"- Source findings: `{RESEARCH_FINDINGS_FILE}`",
        f"- WikiTree fact/correction review queue: "
        f"`{research_profile_notes_file(state['root_wikitree_id'])}`",
        f"- Evidence index: `{RESEARCH_INDEX_FILE}`",
        f"- Raw evidence: `captures/`",
        "",
        "The analysis step should record source-to-finding results in `findings.md` "
        "and `research_plan.json`, then add sourced facts and corrections absent from "
        "the current profile to `<WikiTree-ID>.md` for manual review. Queue only the "
        "additional WikiTree or FamilySearch targets needed "
        "to answer an open question, then rerun the exporter to rebuild this brief.",
        "",
        "## Research questions",
        "",
    ]

    questions = plan.get("questions", [])
    if not questions:
        lines.extend(["_No questions recorded._", ""])
    for question in questions:
        if not isinstance(question, dict):
            continue
        lines.append(
            f"- [{question.get('status', 'open')}] {question.get('id', 'question')}: "
            f"{question.get('question', '')}"
        )
        if question.get("answer"):
            lines.append(f"  Answer: {question['answer']}")
    lines.extend(["", "## Web-search queue", ""])

    searches = plan.get("web_searches", [])
    if not searches:
        lines.append("_No searches queued. The analysing AI should add focused queries._")
    for search in searches:
        if not isinstance(search, dict):
            continue
        lines.append(
            f"- [{search.get('status', 'pending')}] {search.get('id', 'search')}: "
            f"`{search.get('query', '')}`"
        )
        if search.get("purpose"):
            lines.append(f"  Purpose: {search['purpose']}")
        if search.get("result_summary"):
            lines.append(f"  Result: {search['result_summary']}")

    lines.extend(["", "## Additional scrape targets", ""])
    targets = plan.get("targets", [])
    if not targets:
        lines.append("_No targets recorded._")
    for target in targets:
        if not isinstance(target, dict):
            continue
        owner = (
            " for "
            + wikitree_id_markdown_link(str(target["profile_id"]), profiles)
            if target.get("profile_id")
            else ""
        )
        generation = (
            f" generation={target['generation']}"
            if isinstance(target.get("generation"), int)
            else ""
        )
        target_id = str(target.get("id", ""))
        if target.get("kind") == "wikitree" and target_id:
            target_label = wikitree_id_markdown_link(target_id, profiles)
        else:
            target_label = target_id
        lines.append(
            f"- [{target.get('status', 'pending')}] {target.get('kind', 'unknown')}: "
            f"{target_label}{owner}{generation} - {target.get('reason', '')}"
        )
        if target.get("note"):
            lines.append(f"  Note: {target['note']}")

    lines.extend(["", "## Findings", ""])
    findings = plan.get("findings", [])
    if not findings:
        lines.append("_No analysed findings recorded yet._")
    for finding in findings:
        if not isinstance(finding, dict):
            continue
        lines.append(
            f"- [{finding.get('confidence', 'unrated')}] "
            f"{finding.get('claim', '')}"
        )
        if finding.get("reasoning"):
            lines.append(f"  Reasoning: {finding['reasoning']}")
        sources = finding.get("sources", [])
        if isinstance(sources, list) and sources:
            lines.append("  Sources: " + ", ".join(str(source) for source in sources))

    lines.extend(["", "## Evidence summaries", ""])
    for wt_id, profile in profiles.items():
        lines.extend(
            [
                f"### {profile_markdown_link(profile)}",
                "",
                f"- Born: {clean_date(profile.get('birth_date'))} - "
                f"{scalar(profile.get('birth_location'))}",
                f"- Died: {clean_date(profile.get('death_date'))} - "
                f"{scalar(profile.get('death_location'))}",
            ]
        )
        for relation, ids in profile.get("relations", {}).items():
            if ids:
                lines.append(
                    f"- {relation.title()}: "
                    + ", ".join(
                        wikitree_id_markdown_link(str(relation_id), profiles)
                        for relation_id in ids
                    )
                )
        if profile.get("familysearch_pids"):
            lines.append(
                "- FamilySearch PID references: "
                + ", ".join(profile["familysearch_pids"])
            )
        if profile.get("evidence_urls"):
            lines.append("- Evidence URLs:")
            lines.extend(f"  - {url}" for url in profile["evidence_urls"])
        lines.append("- Raw captures: " + ", ".join(profile.get("capture_paths", [])))

        biography = profile.get("biography")
        if biography:
            lines.extend(
                [
                    "",
                    "<details>",
                    "<summary>WikiTree biography and source text</summary>",
                    "",
                    "```text",
                    str(biography).replace("```", "` ` `"),
                    "```",
                    "</details>",
                ]
            )
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def update_research_outputs(
    case_dir: Path,
    state: dict[str, Any],
    plan: dict[str, Any],
) -> None:
    state["updated_at"] = utc_now()
    index = build_evidence_index(case_dir, state)
    root_id = str(state["root_wikitree_id"])
    root_profile = index.get("profiles", {}).get(root_id)
    if isinstance(root_profile, dict):
        contextual_link = profile_markdown_link(root_profile)
        unknown_link = wikitree_id_markdown_link(root_id, {})
        headings = (
            (
                case_dir / RESEARCH_FINDINGS_FILE,
                f"# Findings: {unknown_link}",
                f"# Findings: {contextual_link}",
            ),
            (
                case_dir / research_profile_notes_file(root_id),
                f"# WikiTree update notes: {unknown_link}",
                f"# WikiTree update notes: {contextual_link}",
            ),
        )
        for path, old_heading, new_heading in headings:
            content = path.read_text(encoding="utf-8")
            if content.startswith(old_heading + "\n"):
                path.write_text(
                    new_heading + content[len(old_heading) :],
                    encoding="utf-8",
                )
    write_json_file(case_dir / RESEARCH_STATE_FILE, state)
    write_json_file(case_dir / RESEARCH_PLAN_FILE, plan)
    write_json_file(case_dir / RESEARCH_INDEX_FILE, index)
    (case_dir / RESEARCH_BRIEF_FILE).write_text(
        render_research_brief(plan, state, index),
        encoding="utf-8",
    )


def safe_stem(wikitree_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", wikitree_id)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Export a WikiTree profile, immediate family, biographies, and "
            "optional FamilySearch source-page text."
        )
    )

    parser.add_argument(
        "wikitree_id",
        help=(
            "WikiTree ID such as Glasgow-1538, "
            "or a full WikiTree profile URL."
        ),
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_EXPORT_DIR,
        help=(
            "Directory for Markdown, JSON and browser snapshots "
            f"(default: {DEFAULT_EXPORT_DIR})."
        ),
    )

    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Also print the Markdown export to standard output.",
    )

    parser.add_argument(
        "--familysearch-cdp",
        nargs="?",
        const=DEFAULT_FS_CDP_URL,
        default=os.environ.get("FAMILYSEARCH_CDP_URL"),
        metavar="URL",
        help=(
            "Attach to an existing normal Chrome session over CDP. "
            f"Default when flag is used without a URL: {DEFAULT_FS_CDP_URL}. "
            "This is preferred when FamilySearch blocks Playwright Chromium."
        ),
    )

    parser.add_argument(
        "--familysearch-browser",
        action="store_true",
        default=env_bool("FAMILYSEARCH_BROWSER", False),
        help=(
            "Launch Playwright Chromium and scrape visible FamilySearch "
            "Sources pages for PIDs found in WikiTree biographies."
        ),
    )

    parser.add_argument(
        "--familysearch-profile",
        type=Path,
        default=Path(
            os.environ.get(
                "FAMILYSEARCH_BROWSER_PROFILE",
                DEFAULT_FS_PROFILE_DIR,
            )
        ),
        help=(
            "Persistent Playwright browser-profile directory "
            f"(default: {DEFAULT_FS_PROFILE_DIR})."
        ),
    )

    parser.add_argument(
        "--familysearch-headless",
        action="store_true",
        default=env_bool("FAMILYSEARCH_HEADLESS", False),
        help=(
            "Run the FamilySearch browser headlessly. Do not use this on the "
            "first run because manual login may be required."
        ),
    )

    parser.add_argument(
        "--familysearch-map",
        action="append",
        default=[],
        metavar="WIKITREE_ID=FAMILYSEARCH_PID",
        help=(
            "Manually associate a WikiTree profile with a FamilySearch PID. "
            "May be repeated. Normally unnecessary when the PID appears in "
            "the WikiTree biography."
        ),
    )

    parser.add_argument(
        "--familysearch-max-scrolls",
        type=int,
        default=DEFAULT_FS_MAX_SCROLLS,
        help=(
            "Maximum scroll passes used to load lazy FamilySearch source cards "
            f"(default: {DEFAULT_FS_MAX_SCROLLS})."
        ),
    )

    parser.add_argument(
        "--familysearch-settle-seconds",
        type=float,
        default=DEFAULT_FS_SETTLE_SECONDS,
        help=(
            "Delay after page loads and scrolls "
            f"(default: {DEFAULT_FS_SETTLE_SECONDS})."
        ),
    )

    parser.add_argument(
        "--familysearch-expand-passes",
        type=int,
        default=DEFAULT_FS_EXPAND_PASSES,
        help=(
            "Maximum passes used to expand FamilySearch source details "
            f"(default: {DEFAULT_FS_EXPAND_PASSES})."
        ),
    )

    parser.add_argument(
        "--familysearch-expand-wait-seconds",
        type=float,
        default=DEFAULT_FS_EXPAND_WAIT_SECONDS,
        help=(
            "Delay after expanding each FamilySearch source control "
            f"(default: {DEFAULT_FS_EXPAND_WAIT_SECONDS})."
        ),
    )

    parser.add_argument(
        "--write-json",
        action="store_true",
        help=(
            "Also write a separate raw JSON file. By default everything is "
            "embedded in the single Markdown export."
        ),
    )

    parser.add_argument(
        "--research-dir",
        type=Path,
        help=(
            "Create or resume an iterative research case in this directory. "
            "Pending targets in research_plan.json are scraped, merged and "
            "rendered to research_brief.md."
        ),
    )

    parser.add_argument(
        "--import-ai-export",
        type=Path,
        metavar="MARKDOWN",
        help=(
            "Seed --research-dir from the raw JSON embedded in an existing "
            "*_ai_export.md without making a WikiTree request."
        ),
    )

    parser.add_argument(
        "--research-refresh",
        action="store_true",
        help=(
            "In --research-dir mode, scrape the root WikiTree profile again "
            "even if its initial target is complete."
        ),
    )

    parser.add_argument(
        "--descendant-depth",
        type=int,
        default=0,
        metavar="GENERATIONS",
        help=(
            "In --research-dir mode, automatically capture descendants to "
            "this depth. Depth 2 captures the root and each child, which "
            "hydrates all child and grandchild profiles (default: 0)."
        ),
    )

    return parser.parse_args()


def scrape_target(
    wikitree_id: str,
    args: argparse.Namespace,
    manual_mappings: dict[str, list[str]],
    output_dir: Path,
) -> dict[str, Any]:
    envelope = fetch_family(wikitree_id)
    envelope = attach_familysearch_pids(envelope, manual_mappings)

    if args.familysearch_cdp:
        return scrape_familysearch_sources_via_cdp(
            envelope=envelope,
            cdp_url=args.familysearch_cdp,
            output_dir=output_dir,
            max_scrolls=args.familysearch_max_scrolls,
            settle_seconds=args.familysearch_settle_seconds,
            expand_passes=args.familysearch_expand_passes,
            expand_wait_seconds=args.familysearch_expand_wait_seconds,
        )
    if args.familysearch_browser:
        return scrape_familysearch_sources(
            envelope=envelope,
            profile_dir=args.familysearch_profile,
            output_dir=output_dir,
            headless=args.familysearch_headless,
            max_scrolls=args.familysearch_max_scrolls,
            settle_seconds=args.familysearch_settle_seconds,
            expand_passes=args.familysearch_expand_passes,
            expand_wait_seconds=args.familysearch_expand_wait_seconds,
        )
    return envelope


def update_familysearch_target_outcomes(
    plan: dict[str, Any],
    envelope: dict[str, Any],
    browser_used: bool,
) -> None:
    person = envelope["items"][0].get("person")
    if not isinstance(person, dict):
        return

    profiles = {
        str(profile.get("Name")): profile
        for profile in iter_all_profiles(person)
        if profile.get("Name")
    }
    for target in plan.get("targets", []):
        if not isinstance(target, dict) or target.get("kind") != "familysearch":
            continue
        if target.get("status") == "complete":
            continue

        wt_id = target.get("profile_id")
        pid = target.get("id")
        if wt_id not in profiles or not isinstance(pid, str):
            continue

        if not browser_used:
            set_research_target_status(
                plan,
                "familysearch",
                pid,
                "needs_browser",
                "Rerun with --familysearch-cdp or --familysearch-browser.",
                str(wt_id),
            )
            continue

        result = profiles[str(wt_id)].get("FamilySearchBrowserSources", {}).get(pid)
        if isinstance(result, dict) and result.get("status") == "ok":
            set_research_target_status(
                plan,
                "familysearch",
                pid,
                "complete",
                "FamilySearch source page captured.",
                str(wt_id),
            )
        elif isinstance(result, dict):
            set_research_target_status(
                plan,
                "familysearch",
                pid,
                "error",
                str(result.get("error") or "FamilySearch scrape failed."),
                str(wt_id),
            )


def pending_research_wikitree_ids(
    plan: dict[str, Any],
    browser_used: bool,
) -> list[str]:
    ids: list[str] = []
    for target in plan.get("targets", []):
        if not isinstance(target, dict):
            continue
        if target.get("kind") == "wikitree" and target.get("status") in {
            "pending",
            "error",
        }:
            ids.append(normalise_wikitree_id(str(target.get("id") or "")))
        elif (
            browser_used
            and target.get("kind") == "familysearch"
            and target.get("status") != "complete"
            and target.get("profile_id")
        ):
            ids.append(normalise_wikitree_id(str(target["profile_id"])))
    return list(dict.fromkeys(ids))


def run_research_mode(
    args: argparse.Namespace,
    wikitree_id: str,
    cli_mappings: dict[str, list[str]],
) -> int:
    if args.research_dir is None:
        raise ExportError("Internal error: research directory is missing.")

    state, plan = load_research_case(args.research_dir, wikitree_id)
    if args.descendant_depth < 0:
        raise ValueError("--descendant-depth cannot be negative.")

    for target in plan.get("targets", []):
        if (
            isinstance(target, dict)
            and target.get("kind") == "wikitree"
            and target.get("id") == wikitree_id
        ):
            target.setdefault("generation", 0)
    for wt_id, pids in cli_mappings.items():
        for pid in pids:
            add_research_target(
                plan,
                "familysearch",
                pid,
                "Manually supplied FamilySearch association.",
                wt_id,
            )

    if args.research_refresh:
        set_research_target_status(
            plan,
            "wikitree",
            wikitree_id,
            "pending",
            "Explicit refresh requested.",
        )

    browser_used = bool(args.familysearch_cdp or args.familysearch_browser)
    plan_mappings = research_familysearch_mappings(plan)
    mappings = merge_familysearch_mappings(cli_mappings, plan_mappings)
    failures = 0

    if args.import_ai_export:
        envelope = extract_envelope_from_ai_export(args.import_ai_export)
        subject_id = envelope_subject_id(envelope)
        if subject_id != wikitree_id:
            raise ExportError(
                f"Imported export is for {subject_id}, not {wikitree_id}."
            )
        store_research_capture(
            args.research_dir,
            state,
            envelope,
            wikitree_id,
            f"import:{args.import_ai_export}",
        )
        set_research_target_status(
            plan,
            "wikitree",
            wikitree_id,
            "complete",
            "Imported from existing AI export.",
        )
        update_familysearch_target_outcomes(plan, envelope, browser_used=True)
        queue_descendant_targets(
            plan,
            envelope,
            research_target_generation(plan, wikitree_id),
            args.descendant_depth,
        )
    else:
        attempted: set[str] = set()
        while True:
            target_ids = [
                target_id
                for target_id in pending_research_wikitree_ids(plan, browser_used)
                if target_id not in attempted
            ]
            if not target_ids:
                break

            target_id = target_ids[0]
            attempted.add(target_id)
            try:
                envelope = scrape_target(
                    target_id,
                    args,
                    mappings,
                    args.research_dir,
                )
                store_research_capture(
                    args.research_dir,
                    state,
                    envelope,
                    target_id,
                    "live",
                )
                set_research_target_status(
                    plan,
                    "wikitree",
                    target_id,
                    "complete",
                    "WikiTree subject and immediate family captured.",
                )
                update_familysearch_target_outcomes(plan, envelope, browser_used)
                queue_descendant_targets(
                    plan,
                    envelope,
                    research_target_generation(plan, target_id),
                    args.descendant_depth,
                )
            except (ValueError, ExportError) as exc:
                failures += 1
                message = str(exc)
                state.setdefault("errors", []).append(
                    {
                        "at": utc_now(),
                        "wikitree_id": target_id,
                        "error": message,
                    }
                )
                set_research_target_status(
                    plan,
                    "wikitree",
                    target_id,
                    "error",
                    message,
                )
                print(
                    "Error scraping "
                    f"{terminal_wikitree_id_link(target_id, {})}: {message}",
                    file=sys.stderr,
                )

    update_research_outputs(args.research_dir, state, plan)
    case_index = read_json_object(args.research_dir / RESEARCH_INDEX_FILE)
    profiles = case_index.get("profiles", {})
    if not isinstance(profiles, dict):
        profiles = {}

    surname_outputs: list[Path] = []
    workspace_root = PROJECT_ROOT
    try:
        args.research_dir.resolve().relative_to(
            (workspace_root / "research").resolve()
        )
    except ValueError:
        pass
    else:
        try:
            from surname_research_index import rebuild_surname_indexes

            surname_outputs = rebuild_surname_indexes(workspace_root)
        except (ImportError, KeyError, OSError, ValueError) as exc:
            print(
                f"Warning: surname indexes were not rebuilt: {exc}",
                file=sys.stderr,
            )

    print(
        "WikiTree subject: "
        f"{terminal_wikitree_id_link(wikitree_id, profiles)}"
    )
    print(f"Research case: {args.research_dir}")
    print(f"AI research brief: {args.research_dir / RESEARCH_BRIEF_FILE}")
    print(f"Source findings: {args.research_dir / RESEARCH_FINDINGS_FILE}")
    print(
        "WikiTree review queue: "
        f"{args.research_dir / research_profile_notes_file(wikitree_id)}"
    )
    print(f"Editable research plan: {args.research_dir / RESEARCH_PLAN_FILE}")
    if surname_outputs:
        print(f"Surname profile index: {surname_outputs[1]}")
    return 1 if failures else 0


def main() -> int:
    load_environment()
    args = parse_args()

    try:
        wikitree_id = normalise_wikitree_id(args.wikitree_id)
        manual_mappings = parse_familysearch_mappings(
            args.familysearch_map
        )

        if args.import_ai_export and not args.research_dir:
            raise ValueError("--import-ai-export requires --research-dir.")
        if args.research_refresh and not args.research_dir:
            raise ValueError("--research-refresh requires --research-dir.")
        if args.descendant_depth and not args.research_dir:
            raise ValueError("--descendant-depth requires --research-dir.")
        if args.research_dir:
            return run_research_mode(
                args,
                wikitree_id,
                manual_mappings,
            )

        envelope = scrape_target(
            wikitree_id,
            args,
            manual_mappings,
            args.output_dir,
        )

        markdown = make_markdown(envelope, wikitree_id)

    except (ValueError, ExportError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nCancelled.", file=sys.stderr)
        return 130

    args.output_dir.mkdir(parents=True, exist_ok=True)

    stem = safe_stem(wikitree_id)
    markdown_path = args.output_dir / f"{stem}_ai_export.md"

    markdown_path.write_text(markdown, encoding="utf-8")
    person = envelope["items"][0].get("person", {})
    if isinstance(person, dict):
        print(f"WikiTree subject: {terminal_profile_link(person)}")
    print(f"Wrote single AI export: {markdown_path}")

    if args.write_json:
        json_path = args.output_dir / f"{stem}_family_export.json"
        json_path.write_text(
            json.dumps(
                envelope,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        print(f"Wrote optional JSON: {json_path}")

    if args.familysearch_browser or args.familysearch_cdp:
        print(
            "FamilySearch page snapshots: "
            f"{args.output_dir / 'familysearch_pages'}"
        )

    if args.stdout:
        print()
        print(markdown)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
