"""Conservative region candidates from an existing record_location only.

No source titles, person names, family links or coordinates are consulted.
Unresolved labels return an empty string; these are reviewable claim candidates,
not evidence that an event or residence actually occurred at the named place.
"""
from __future__ import annotations

import csv
from collections import defaultdict
from functools import lru_cache
from pathlib import Path
import re

try:
    from tools.place_gazetteer import load, key, IRISH_COUNTY_NAMES
except ModuleNotFoundError:
    from place_gazetteer import load, key, IRISH_COUNTY_NAMES

ROOT = Path(__file__).resolve().parents[1]


@lru_cache(maxsize=1)
def _gazetteer():
    return load().get("entries", {})


@lru_cache(maxsize=1)
def _held_labels():
    """Reuse exact geographic labels already assigned in the maintained map."""
    known = defaultdict(set)
    path = ROOT / "www/map/data/records.csv"
    if not path.exists():
        return known
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            loc = (row.get("record_location") or "").strip()
            region = (row.get("region") or "").strip()
            if region and region not in {"Unspecified", "At Sea", "Scotland / England", "United Kingdom"} and not re.search(
                r"holding|non.geographic|not evidence", row.get("record_precision", "") + " " + row.get("location_basis", ""), re.I
            ):
                known[key(loc)].add(region)
    return known


countries={'ireland':'Ireland','northern ireland':'Ireland','republic of ireland':'Ireland','scotland':'Scotland','england':'England','wales':'Wales','united states':'United States','united states of america':'United States','usa':'United States','us america':'United States','canada':'Canada','australia':'Australia','new zealand':'New Zealand','nz':'New Zealand','india':'India','italy':'Italy','deutschland':'Germany','isle of man':'Isle of Man'}
scottish='Aberdeenshire|Angus|Argyll|Ayrshire|Banffshire|Berwickshire|Caithness|Clackmannanshire|Dumfriesshire|Dunbartonshire|East Lothian|Fife|Inverness-shire|Kincardineshire|Kinross-shire|Lanarkshire|Midlothian|Morayshire|Orkney|Peeblesshire|Perthshire|Renfrewshire|Roxburghshire|Selkirkshire|Shetland|Stirlingshire|Sutherland|West Lothian|Wigtownshire'
english='Buckinghamshire|Cornwall|Cumberland|Derbyshire|Devon|Dorset|Durham|Essex|Gloucestershire|Hampshire|Herefordshire|Hertfordshire|Kent|Lancashire|Leicestershire|Lincolnshire|Middlesex|Norfolk|Northumberland|Nottinghamshire|Shropshire|Somerset|Staffordshire|Suffolk|Surrey|Sussex|Warwickshire|Westmorland|Wiltshire|Worcestershire|Yorkshire|Oxfordshire|Bedfordshire|Cheshire'
welsh='Anglesey|Breconshire|Caernarfonshire|Cardiganshire|Carmarthenshire|Denbighshire|Flintshire|Glamorgan|Glamorganshire|Merionethshire|Monmouthshire|Montgomeryshire|Pembrokeshire|Radnorshire'
county_groups={**{key(v):'Ireland' for v in IRISH_COUNTY_NAMES},**{key(v):'Scotland' for v in scottish.split('|')},**{key(v):'England' for v in english.split('|')},**{key(v):'Wales' for v in welsh.split('|')}}
# No bare ambiguous county/locality words: comma components, explicit County/Co.,
# and long distinctive county names are the only county matching routes.
def classify_location(loc: str) -> tuple[str | None, str]:
    """Return a conservative region and an auditable basis, or an unresolved reason."""
    loc = str(loc or "")
    gaz = _gazetteer()
    normalized=key(loc)
    if not normalized or re.search(r'holding point|location not supplied|not recorded|not specified|unknown|unspecified',normalized):
        return None,'placeholder'
    if re.search(r'church of ireland|\bcensus\b|\bcollection\b|\bregisters?\b|\brecords?\b|\bindex\b',normalized):
        return None,'collection or denomination, not an explicit geographic place'
    parts=[key(x) for x in loc.split(',') if key(x)]
    explicit={countries[p] for p in parts if p in countries}
    county_matches={county_groups[p] for p in parts if p in county_groups}
    if explicit:
        if len(explicit)!=1 or (county_matches and not county_matches<=explicit):
            return None,'conflicting country/county geography'
        country=next(iter(explicit))
        return country,'Explicit geographic country component in exact record_location'
    if normalized in {'bath', 'lee'}:
        return None, 'ambiguous locality name requires subject-specific country context'
    # Existing exact-label placement; no profile name, title, kin or coordinates consulted.
    k=_held_labels().get(normalized,set())
    if len(k)==1:
        return next(iter(k)),'Exact geographic record_location label matches a consistent held map hierarchy region'
    if len(k)>1:
        return None,'same exact label has conflicting held hierarchy regions'
    if len(county_matches)==1:
        return next(iter(county_matches)),'Exact comma-separated historic county component in record_location'
    if len(county_matches)>1:
        return None,'conflicting county components'
    # Only whole components, never substring Glasgow in names or street text.
    matches=[gaz[p] for p in parts if p in gaz]
    gs={g['country'] for g in matches}
    if len(gs)==1:
        return next(iter(gs)),'Exact comma-separated locality component matches maintained place-gazetteer.json: '+', '.join(g['name']+' / '+g['county']+' / '+g['country']+' ('+g['provenance']+')' for g in matches)
    # Long county names and explicit County X are precise hierarchy labels in addresses.
    m=[(c,r) for c,r in county_groups.items() if (len(c)>=8 or re.search(r'\bco(?:unty)?\s+'+re.escape(c)+r'\b',normalized)) and re.search(r'\b'+re.escape(c)+r'\b',normalized)]
    rs={r for _,r in m}
    if len(rs)==1:
        return next(iter(rs)),'Explicit historic county phrase in exact record_location: '+', '.join(c for c,_ in m)
    # Owner-reviewed distinctive town/county phrases, including street addresses.
    # Do not treat a town word naming a street as that street's geographic town.
    reviewed = {
        "England": (
            "london", "bolton", "lancs", "bucks", "salford", "newcastle on tyne",
            "newcastle upon tyne", "gateshead", "essex", "birmingham", "manchester",
            "woolwich", "sunderland", "barrow in furness", "blackpool", "cheltenham",
            "portsmouth", "haggerston", "kilburn", "tottenham", "islington", "hendon",
            "willesden", "fulham", "east dulwich", "wembley", "st pancras", "bethnal green",
            "marylebone", "tooting", "west hampstead", "cricklewood", "chelsea", "battersea",
            "clapham common", "dalston", "vauxhall", "stockwell", "wandsworth", "putney",
            "ealing", "southall", "uxbridge", "childs hill", "clapton park", "durham",
            "staffs", "wilts", "hants", "berks", "middx", "middlesbrough", "middlesbro",
            "southsea", "tunbridge wells", "southend on sea", "hertford", "dover", "hindhead",
            "tipton", "lyme regis", "sheerness", "morpeth", "sheffield", "liskeard",
            "carlisle", "market harborough", "southport", "brighton", "monkwearmouth",
            "ebchester", "small heath", "birkenhead", "smethwick", "monkseaton",
            "southampton", "deptford", "arnside", "elephant castle", "manor park e", "clapton n e",
            "walker on tyne", "homerton", "dunston", "bham", "b ham", "bromley",
        ),
        "Scotland": ("stirling", "leith", "prestonpans", "glasgow", "leadhills", "haddington", "lanark"),
        "Wales": ("rhayader", "pontardawe"),
        "Ireland": ("newry", "derryloran", "stewartstown", "drum cookstown", "ogonaloe", "tyanee"),
        "United States": ("ohio", "jacksonville fla", "henderson ky", "weakley co tn", "new orleans"),
    }
    hits = []
    for region, terms in reviewed.items():
        for term in terms:
            if term == "glasgow" and not (re.search(r"\d|,", loc) or normalized == "glasgow"):
                continue
            if re.search(r"\b" + re.escape(term) + r"\b(?!\s+(?:road|rd|street|st|avenue|ave|terrace|terr)\b)", normalized):
                hits.append((term, region))
    regions = {region for _, region in hits}
    if len(regions) == 1:
        return next(iter(regions)), "Owner-reviewed distinctive geographic town/county phrase in exact record_location: " + ", ".join(term for term, _ in hits)
    if len(regions) > 1:
        return None, "conflicting reviewed geographic town/county phrases"
    return None,'No unambiguous exact geographic hierarchy match'


def region_for_location(location: str) -> str:
    """Return a conservative broad region for an exact held location, else ''."""
    return classify_location(location)[0] or ""
