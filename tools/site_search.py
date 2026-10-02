"""Install both shared search implementations from one public route registry."""
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path

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


def install_search(site_root=ROOT / "www") -> dict[str, int]:
    """Write only the worker and shared UI; the release finalizer stamps versions."""
    counts = Counter()
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
