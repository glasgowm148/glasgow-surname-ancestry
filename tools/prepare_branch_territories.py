#!/usr/bin/env python3
"""Prepare the small boundary files behind the Families & places study map.

Only the most-researched study areas get a selectable territory; every
other boundary is non-interactive context.  Territories are drawn from
civil-parish outlines as *representative study areas*: they show where a
study's records sit, not a proved extent of any family's land.

Raw inputs (not committed; fetched once into data/reference/boundaries/raw/):
- counties.geojson — all-island Irish counties, townlands.ie (OSM, ODbL)
  https://www.townlands.ie/static/downloads/counties.geojson.zip
- hcbp/UKDefinitionA.shp — Historic County Borders Project, simplified WGS84
  https://www.county-borders.co.uk/UKDefinitionA_WG84_Simplified.zip
- sct_cp_{0,400,800}.geojson — NRS civil parishes (1930), OGL, via
  https://maps.gov.scot/server/rest/services/NRS/NRS/MapServer/0/query
- ie_study_parishes.geojson — named Irish civil parishes from OpenStreetMap
  (ODbL) via Overpass, converted with osmtogeojson.

Outputs (committed, small): tools/branch_territories/{counties,territories}.geojson
Requires `npx mapshaper` (fetched on demand by npx).
"""
from pathlib import Path
import json
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/reference/boundaries/raw"
OUT = ROOT / "tools/branch_territories"
CLIP = "-7.7,54.4,-2.5,56.2"  # north-east Ulster to the Lothians: every priority area

# Candidate study areas.  Their order on the page is not fixed here:
# tools/build_branches_directory.py ranks them by measured research (research
# dossier depth, sourced records and documented people located in each area)
# every time the site is built.  An area is only drawn when it has a study to
# open; the first study listed is the one a click opens.  The areas were chosen
# from a 12 × 14 km grid audit of all located records in Ireland and Scotland
# (24 Sep 2026): each is a high-scoring cell with a maintained study.
TERRITORIES = [
    dict(id="larne", label="Larne & Kilwaughter", country="ie",
         parishes=["Larne", "Kilwaughter"],
         studies=["larne-kilwaughter", "research-irish-east-antrim"],
         why="The proposed Larne origin and the South Carolina migration may join the Irish and American branches."),
    dict(id="lisnagaver", label="Lisnagaver, Rasharkin & Kilrea", country="ie",
         parishes=["Rasharkin", "Kilrea", "Desertoghill"],
         studies=["lisnagaver-rasharkin", "research-irish-bann-valley-killoquin", "research-irish-desertoghill-garvagh"],
         why="Alexander of Lisnagaver’s parents are the project’s first open question; Daniel and Thomas are proved brothers nearby."),
    dict(id="dunaghy", label="Dunaghy & Glenleslie", country="ie",
         parishes=["Dunaghy"],
         studies=["research-irish-inishrush-collateral"],
         why="Family-register, census and tithe clues for the collateral households, and the proposed John of Glenleslie link."),
    dict(id="inishrush", label="Inishrush & Tamlaght O'Crilly", country="ie",
         parishes=["Tamlaght O'Crilly"],
         studies=["research-irish-tamlaght", "research-irish-inishrush-collateral"],
         why="John of Inishrush and the two 1740 Hugh households are the next generation back."),
    dict(id="cookstown", label="Cookstown, Killycurragh & Moneymore", country="ie",
         parishes=["Derryloran (Derry portion)", "Derryloran (Upper Dungannon portion)", "Kildress", "Lissan (Derry portion)", "Lissan (Dungannon Upper portion)", "Artrea", "Artrea (Tyrone portion)", "Desertlyn"],
         studies=["research-irish-derryloran", "research-irish-cross-derry", "research-irish-moneymore"],
         why="The largest cluster of Glasgow profiles in Ireland, around Killycurragh and Cookstown; most still await record review."),
    dict(id="glasgow-burgh", label="Glasgow burgh", country="sct",
         parishes=["Glasgow"],
         studies=["research-saltmarket-succession", "research-glasgow-fishers", "early-scottish-records"],
         why="The earliest documented Glasgow bearers and the Saltmarket succession."),
    dict(id="north-ayrshire", label="Stevenston, Kilwinning & Kilbirnie", country="sct",
         parishes=["Stevenston", "Kilwinning", "Kilbirnie"],
         studies=["research-corsankell-household", "research-stevenston-estate-network", "research-kilbirnie-minister"],
         why="The Corsankell households and the possible burgh-to-Ayrshire bridge."),
    dict(id="calder", label="Calder & Inveresk", country="sct",
         parishes=["Mid Calder", "Kirknewton", "Inveresk"],
         studies=["research-hirmenschelis-household", "research-calder-testament-household", "research-calder-inveresk-james"],
         why="Testament households at Hirmenschelis and Caldercleir, and the two-place James."),
]

def mapshaper(*args):
    subprocess.run(["npx", "-y", "mapshaper", *args, "-quiet"], check=True, cwd=ROOT)


def features(path):
    return json.loads(Path(path).read_text())["features"]


def main():
    OUT.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        # Context counties: all-island Irish counties plus Great Britain's
        # historic counties (the HCBP Ulster counties are replaced by Irish ones).
        mapshaper(str(RAW / "counties.geojson"), "-each", "name=NAME_EN||NAME_TAG, country='ie'",
                  "-filter-fields", "name,country", "-clip", f"bbox={CLIP}", "-simplify", "interval=250", "keep-shapes",
                  "-o", str(tmp / "ie.geojson"), "format=geojson")
        mapshaper(str(RAW / "hcbp/UKDefinitionA.shp"), "-filter", "COUNTY.indexOf('Antrim')<0 && ['Armagh','Down','Fermanagh','Londonderry','Tyrone'].indexOf(COUNTY)<0",
                  "-each", "name=NAME, country='gb'", "-filter-fields", "name,country",
                  "-clip", f"bbox={CLIP}", "-simplify", "interval=250", "keep-shapes", "-o", str(tmp / "gb.geojson"), "format=geojson")
        counties = features(tmp / "ie.geojson") + features(tmp / "gb.geojson")
        (OUT / "counties.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": counties}, separators=(",", ":")))

        wanted = {}
        for territory in TERRITORIES:
            for parish in territory["parishes"]:
                wanted[(territory["country"], parish)] = territory["id"]
        parts = []
        sct = [f for o in (0, 400, 800) for f in features(RAW / f"sct_cp_{o}.geojson")]
        for feature in sct:
            key = ("sct", feature["properties"]["name"])
            if key in wanted:
                parts.append({"type": "Feature", "geometry": feature["geometry"], "properties": {"territory": wanted[key], "parish": key[1]}})
        for feature in features(RAW / "ie_study_parishes.geojson"):
            props = feature["properties"]
            key = ("ie", props.get("name"))
            if props.get("boundary") == "civil_parish" and key in wanted:
                parts.append({"type": "Feature", "geometry": feature["geometry"], "properties": {"territory": wanted[key], "parish": key[1]}})
        found = {(("sct" if p["properties"]["territory"] in {"glasgow-burgh", "north-ayrshire", "calder"} else "ie"), p["properties"]["parish"]) for p in parts}
        missing = sorted(set(wanted) - found)
        if missing:
            raise SystemExit(f"missing parish outlines: {missing}")
        (tmp / "parts.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": parts}))
        mapshaper(str(tmp / "parts.geojson"), "-dissolve2", "territory", "copy-fields=", "-simplify", "interval=60", "keep-shapes",
                  "-o", str(tmp / "territories.geojson"), "format=geojson")
        meta = {t["id"]: t for t in TERRITORIES}
        out = []
        for feature in features(tmp / "territories.geojson"):
            t = meta[feature["properties"]["territory"]]
            feature["properties"] = {"id": t["id"], "label": t["label"], "country": t["country"],
                                     "parishes": t["parishes"], "studies": t["studies"], "why": t["why"]}
            out.append(feature)
        (OUT / "territories.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": out}, ensure_ascii=False, separators=(",", ":")))
    print({"counties": len(counties), "territories": len(out)})


if __name__ == "__main__":
    main()
