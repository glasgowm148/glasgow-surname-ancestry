"""Install both shared search implementations from one public route registry."""
from __future__ import annotations

from collections import Counter
from html import unescape
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
MARKER = "/* PUBLIC_SEARCH_ROUTES */[]"

# Current navigation names, with former names retained as search aliases.
# This registry contains only intentionally published reader routes.
PUBLIC_ROUTES = (
    ("Home", "/", "home", "The Glasgow surname archive", "Overview"),
    ("People", "/catalogue/", "people", "Search people, relatives, dates and places", "People Catalogue Catalogue"),
    ("Families & places", "/branches/", "people", "Named family and locality pages", "Families and places Branch cards"),
    ("Family tree", "/onetree/", "tree", "Public profiles, branches and Y-DNA tester markers", "Family Atlas Whole tree"),
    ("Y-DNA", "/ydna/", "dna", "Testers, haplogroups and the genetic explorer", "Y DNA"),
    ("Records & sources", "/sources/", "records", "Search source references and read linked evidence", "Records Source library Source references"),
    ("Research", "/research/", "desk", "Findings, unresolved links and comparison tools", "Research questions"),
    ("Latest findings", "/latest-findings/", "desk", "Dated discoveries, corrections and relationship findings", "Latest research Recent findings"),
    ("Research library", "/free-space/", "desk", "Complete research studies, sources and WikiTree comparisons", "Free-space Library Free space WikiTree study pages"),
    ("Explore the archive", "/explore/", "desk", "Ways to explore people, places and research", "Explore"),
    ("Map", "/map/", "map", "Mapped records and places", "Family map"),
    ("Places", "/places/", "pin", "Browse places linked to people and records", "Localities"),
    ("Records by person", "/records/", "records", "People mentioned in records", "Record associations"),
    ("Life events", "/events/", "timeline", "Personal events, mentions and family evidence", "Events"),
    ("Timeline", "/timeline/", "timeline", "The historical and genetic timeline", "Historical timeline"),
    ("DNA story", "/dna/", "dna", "The genetic branches in historical context", "DNA connections"),
    ("Connection finder", "/connections/", "connections", "A relationship chain between two people", "Find a connection"),
    ("Compare two people", "/compare/", "people", "Compare the records behind a possible identity match", "Compare people Comparison"),
    ("Early records", "/early-records/", "timeline", "The earliest surname entries", "Early bearers"),
    ("Research review", "/research/review/", "edit", "Conflicting imported values and maintained conclusions", "Review decisions"),
    ("Research queue", "/research/queue/", "desk", "Outstanding research and WikiTree amendments", "Work queue"),
    ("Wills & transcriptions", "/research/transcriptions/", "records", "Read transcribed historical records", "Transcriptions Wills and transcriptions"),
    ("Statistics", "/statistics/", "people", "Catalogue totals and evidence coverage", "Complete statistics"),
    ("About", "/about/", "edit", "About the Glasgow surname project", "About this project"),
    ("Resources", "/resources/", "desk", "Community links and research resources", "Community"),
    ("Coverage & method", "/coverage/", "edit", "Publication scope, evidence and limitations", "Coverage and method"),
    ("How to read the evidence", "/evidence/", "edit", "Evidence quality and confidence labels", "Evidence labels"),
    ("Data & downloads", "/data/", "records", "Public historical datasets and their provenance", "Data and downloads"),
    ("Change log", "/changes/", "edit", "Website and research release changes", "Changes"),
    ("Suggest a correction", "/feedback/", "edit", "Send feedback about the archive", "Feedback"),
    ("Catalogue status", "/status/", "edit", "Source snapshots and publication status", "Status"),
    ("Privacy", "/privacy/", "edit", "Publication and browser storage policy", "Privacy policy"),
    ("Candidate matches", "/candidate-matches/", "people", "Compare possible historical identities", "Identity candidates"),
)


def search_routes():
    return [dict(name=name, url=url, icon=icon, meta=meta, search=aliases)
            for name, url, icon, meta, aliases in PUBLIC_ROUTES]


def render_search(source: str) -> str:
    if source.count(MARKER) != 1:
        raise ValueError("Search template must contain exactly one route marker")
    return source.replace(MARKER, json.dumps(search_routes(), ensure_ascii=False, separators=(",", ":")))


# ---------------------------------------------------------------------------
# Section index: families and studies, research questions, record studies,
# transcriptions and latest findings (S1-08), plus a current place index.
# ---------------------------------------------------------------------------
SECTION_INDEX = "assets/v3/search-sections.json"
PLACE_INDEXES = ("assets/v3/search-places.json", "assets/unified/search-places.json")
SECTION_FIELDS = ["id", "name", "url", "sub", "search", "type"]
STUDY_TYPES = {"family": "Family group", "research": "Research study", "region": "Regional guide", "place": "Local study"}
MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December")


def _text(value) -> str:
    return " ".join(unescape(re.sub(r"<[^>]+>", " ", str(value or ""))).split())


def _snippet(value, limit: int = 140) -> str:
    """The first sentence, cut at a word boundary when it is long."""
    text = _text(value)
    sentence = re.split(r"(?<=[.!?])\s+(?=[A-Z“\"(])", text, maxsplit=1)[0]
    if len(sentence) <= limit:
        return sentence
    cut = sentence[:limit].rsplit(" ", 1)[0].rstrip(",;:–— ")
    return cut + "…"


def _long_date(iso: str) -> str:
    match = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", str(iso or ""))
    return f"{int(match[3])} {MONTHS[int(match[2]) - 1]} {match[1]}" if match else str(iso or "")


def _read_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def _study_rows(site_root: Path) -> list[list[str]]:
    rows = []
    for study in _read_json(site_root / "assets/research/branches.json", []):
        url = study.get("url") or ""
        if not url.startswith("/branches/") or not (site_root / url.strip("/") / "index.html").exists():
            continue
        kind = STUDY_TYPES.get(study.get("kind"), "Family study")
        count = study.get("count") or len(study.get("members") or [])
        years = "–".join(str(int(y)) for y in (study.get("from"), study.get("to")) if isinstance(y, (int, float)))
        facts = " · ".join(x for x in (f"{count:,} {'person' if count == 1 else 'people'}" if count else "", years) if x)
        sub = " · ".join(x for x in (kind, facts, _snippet(study.get("description"), 110)) if x)
        topics = "" if study.get("kind") == "family" else " ".join(study.get("topic_ids") or [])
        search = " ".join(str(x) for x in (study.get("rootId"), topics, "family study") if x)
        rows.append(["study-" + str(study.get("id")), _text(study.get("label")), url, sub, search, kind])
    return rows


def _question_rows(site_root: Path) -> list[list[str]]:
    """Research questions from the maintained list behind /research/#open-questions."""
    if not (site_root / "research/index.html").exists():
        return []
    try:
        from tools import repair_research_questions as questions
    except Exception:  # pragma: no cover - the maintained list is optional for the index
        try:
            import repair_research_questions as questions  # type: ignore
        except Exception:
            return []
    rows = []
    for slug, name, date, question, answer in questions.QUESTIONS:
        rows.append([f"question-{slug}", _text(question), f"/people/{slug}.html",
                     f"Research question · {name} ({date}) · {_snippet(answer, 100)}", f"{name} {slug} open question", "Research question"])
    for index, (study, subject, question, answer, url) in enumerate(questions.ADDITIONAL_QUESTIONS):
        local = url if str(url).startswith("/") else "/research/#open-questions"
        rows.append([f"question-{index + 1}", _text(question), local,
                     f"Research question · {study} · {_text(subject)}", f"{study} {_snippet(answer, 100)} open question", "Research question"])
    return rows


def _research_page_rows(site_root: Path) -> list[list[str]]:
    rows = []
    for path in sorted((site_root / "research/subjects").glob("*/subjects.json")):
        data = _read_json(path, {})
        if not (path.parent / "index.html").exists() or not data.get("title"):
            continue
        names = list(dict.fromkeys(_text(p.get("name")) for p in data.get("people") or [] if p.get("name")))
        sub = "Record study · " + (", ".join(names[:4]) + (" and others" if len(names) > 4 else "") if names else "people named in the records")
        rows.append([f"subject-{path.parent.name}", _text(data["title"]), f"/research/subjects/{path.parent.name}/", sub,
                     " ".join(names[4:]), "Record study"])
    for path in sorted((site_root / "research/transcriptions").glob("*/index.html")):
        page = path.read_text(encoding="utf-8", errors="ignore")
        heading = re.search(r"<h1\b[^>]*>(.*?)</h1>", page, re.S)
        if not heading:
            continue
        year = re.search(r"(1[0-9]{3})$", path.parent.name)
        rows.append([f"transcription-{path.parent.name}", _text(heading[1]), f"/research/transcriptions/{path.parent.name}/",
                     "Wills & transcriptions" + (f" · {year[1]}" if year else ""), path.parent.name.replace("-", " "),
                     "Wills & transcriptions"])
    return rows


def _finding_rows(site_root: Path, findings_path: Path) -> list[list[str]]:
    """Latest findings, each linking to its dated row on /latest-findings/."""
    pages = {row.get("id"): row.get("url") for row in _read_json(site_root / "data/latest-findings-index.json", [])}
    rows = []
    for finding in _read_json(findings_path, {}).get("findings", []):
        anchor = f"finding-{finding.get('id')}"
        page = pages.get(anchor)
        if not page:
            continue
        people = [p for p in finding.get("people") or [] if p.get("name")]
        names = ", ".join(_text(p["name"]) for p in people[:3]) + (" and others" if len(people) > 3 else "")
        sub = " · ".join(x for x in (f"Latest finding · {_long_date(finding.get('found_on'))}", names) if x)
        # Names already appear in ``sub``; the search field adds IDs and any further names.
        search = " ".join([*(str(p.get("id") or "") for p in people), *(_text(p["name"]) for p in people[3:])]).strip()
        rows.append([anchor, _snippet(finding.get("finding"), 120), f"{page}#{anchor}", sub, search, "Latest finding"])
    return rows


def section_rows(site_root=ROOT / "www", findings_path: Path | None = None) -> list[list[str]]:
    site_root = Path(site_root)
    findings_path = findings_path or ROOT / "research/latest-findings.json"
    rows = [*_study_rows(site_root), *_question_rows(site_root), *_research_page_rows(site_root),
            *_finding_rows(site_root, findings_path)]
    seen, unique = set(), []
    for row in rows:
        if (row[1], row[2]) not in seen:
            seen.add((row[1], row[2])); unique.append(row)
    return unique


def place_rows(site_root=ROOT / "www") -> list[list[str]]:
    """Every published place page, from the maintained place index."""
    site_root = Path(site_root)
    rows = []
    for place in _read_json(site_root / "data/places-index.json", []):
        url = place.get("url") or ""
        if not url.startswith("/places/") or not (site_root / url.lstrip("/")).exists():
            continue
        people, records = place.get("people") or 0, place.get("records") or 0
        years = "–".join(dict.fromkeys(str(y) for y in (place.get("year_from"), place.get("year_to")) if y))
        sub = " · ".join(x for x in (place.get("region"), f"{people:,} {'person' if people == 1 else 'people'}" if people else "",
                                     f"{records:,} {'record' if records == 1 else 'records'}" if records else "", years) if x)
        rows.append([place.get("slug") or place.get("id"), _text(place.get("name")), url, sub,
                     " ".join([place.get("region") or "", *(place.get("surnames") or [])]).strip()])
    return rows


def _write_json(path: Path, payload) -> bool:
    content = json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n"
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def build_search_indexes(site_root=ROOT / "www", findings_path: Path | None = None) -> dict[str, int]:
    """Write the section index and refresh the place index from built data.

    Only files that already exist in ``site_root`` are read; an empty site
    produces no index files. Returns counts of rows and files written.
    """
    site_root = Path(site_root)
    counts = Counter()
    sections = section_rows(site_root, findings_path)
    if sections:
        counts["search_section_rows"] = len(sections)
        if _write_json(site_root / SECTION_INDEX, {"schema_version": 1, "fields": SECTION_FIELDS, "rows": sections}):
            counts["search_indexes"] += 1
    places = place_rows(site_root)
    if places:
        counts["search_place_rows"] = len(places)
        # The worker reads compact rows; the no-worker fallback in site.js reads objects.
        unified = [dict(name=name, url=url, meta=sub, search=f"{name} {search}".strip()) for _id, name, url, sub, search in places]
        for relative, payload in zip(PLACE_INDEXES, (places, unified)):
            if _write_json(site_root / relative, payload):
                counts["search_indexes"] += 1
    return dict(counts)


def install_search(site_root=ROOT / "www") -> dict[str, int]:
    """Write the worker, shared UI and search indexes; the release finalizer stamps versions."""
    counts = Counter(build_search_indexes(site_root))
    counts.pop("search_section_rows", None); counts.pop("search_place_rows", None)
    for filename, destination in (("search-worker.js", "assets/research/search-worker.js"),
                                  ("site.js", "assets/unified/site.js")):
        content = render_search((ROOT / "tools/site_sources/performance" / filename).read_text())
        path = Path(site_root) / destination
        if not path.exists() or path.read_text() != content:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
            counts["shared_search_assets"] += 1
    return dict(counts)


if __name__ == "__main__":
    print(install_search())
