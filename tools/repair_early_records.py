"""Keep the public Early Records index aligned with the medieval register."""

from collections import Counter
import hashlib
import json
import re
from urllib.parse import quote
from pathlib import Path


try:
    from tools.project_paths import normalized_profile_redirects
except ModuleNotFoundError:
    from project_paths import normalized_profile_redirects


ROOT = Path(__file__).resolve().parents[1]
ENTRIES = ROOT / "www/assets/v3/early-entries.json"
REGISTER = (
    "https://www.wikitree.com/wiki/Space:Bearers_of_the_%27%27de_Glasgu%27%27_"
    "Name_and_the_Emergence_of_the_Glasgow_Surname%2C_c.1175%E2%80%931500"
)

MEDIEVAL_OCCURRENCES = (
    ("record-medieval-1175-roger-de-glasgu", 1175, "Roger de Glasgu", "Glasgow, Scotland", "Witness to a Glasgow burgh and Clyde fishery charter; earliest secure direct bearer.", "roger"),
    ("record-medieval-1180-richard-de-glasgu-dublin", 1180, "Richard de Glasgu", "Dublin, Ireland", "Dublin guild merchant admission; paid eight shillings.", "richard_dublin"),
    ("record-medieval-1180-robert-de-glasgu-dublin", 1180, "Robert de Glasgu", "Dublin, Ireland", "Dublin guild merchant admission immediately after Richard; their relationship is unproved.", "robert_dublin"),
    ("record-medieval-1200-robert-de-glascu-dadinton", 1200, "Robert de Glascu", "England — Dadinton unidentified", "Named in an English royal plea-roll notice concerning men said to have been present at a robbery; identity with the Dublin Robert is unproved.", "robert_1200"),
    ("record-medieval-1222-gilbert-de-glascu-dublin", 1222, "Gilbert or Gilibertus de Glascu", "Dublin, Ireland", "Dublin guild merchant admission; paid eight shillings.", "gilbert_dublin"),
    ("record-medieval-1229-robert-de-glasgu-dunkeld", 1229, "Robert de Glasgu", "Dunkeld, Scotland", "Clerk in the household of Gilbert, bishop of Dunkeld; identity with other Roberts is unproved.", "robert_dunkeld"),
    ("record-medieval-1238-robert-de-glascu-father-alexander", 1238, "Robert de Glascu, father of Alexander", "Dublin, Ireland", "Relationship-only guild record: Glasgow attaches to Robert, not Alexander. This Robert may overlap another early Robert.", "alexander_son_robert"),
    ("record-medieval-1248-robert-de-glascu-kippax", 1248, "Robert de Glascu", "Kippax, England", "Witness to a Durham episcopal ordinance issued at Kippax; office not stated.", "robert_durham"),
    ("record-medieval-1259-john-de-glasgu-gamelin", 1259, "John de Glasgu", "St Andrews, Scotland", "Chaplain of Bishop Gamelin of St Andrews; probably also a Dunipace witness.", "john_gamelin"),
    # Register bearers c.1283–1475 not otherwise represented by an Early Records
    # entry (added 6 Oct 2026). The 1283 Alexanders, the 1289/90 escheator,
    # Alan Glasgw (Glasgow-3023) and John alias Smith already have catalogue entries.
    ("record-medieval-1283-hugh-de-glasgw", 1283, "Hugh de Glasgw", "Rottenrow, Glasgow, Scotland", "Witness to a Rottenrow quitclaim in the Paisley register; date assigned c.1283.", "Space:Hugh de Glasgw"),
    ("record-medieval-1291-master-walter-de-glasgu", 1291, "Master Walter de Glasgu", "Melrose, Scotland", "Educated witness in Melrose charter material, c.1291.", "Space:Master Walter de Glasgu"),
    ("record-medieval-1299-john-of-glasgow-holyrood", 1299, "John of Glasgow", "Holyrood, Edinburgh, Scotland", "Member of the Holyrood community swearing fealty to Edward I, 7 January 1299; identity with Gamelin's chaplain unproved.", "Space:John of Glasgow (Holyrood)"),
    ("record-medieval-1312-richard-of-glasgow-arbroath", 1312, "Richard of Glasgow", "Arbroath, Scotland", "Monk of Arbroath, 3 July 1312.", "Space:Richard of Glasgow (Arbroath)"),
    ("record-medieval-1315-william-de-glascou-corbridge", 1315, "William de Glasgow / de Glascou", "Corbridge, Northumberland, England", "Priest instituted vicar of Corbridge in 1315 and a deed witness in 1322; repeated personal byname.", "Space:William de Glasgow (fl. 1315–1322, Durham)", "england"),
    ("record-medieval-1350-adam-de-glasgeu-berwick", 1350, "Adam de Glasgeu", "Berwick-upon-Tweed", "Burgess of Berwick granting land at Hiddeslaw in Bondington; probably fourteenth century, date broad and assigned.", "Space:Adam de Glasgu", "scotland"),
    ("record-medieval-1343-john-de-glasgu", 1343, "John de Glasgu", "Scotland", "Paid 7s. 6d. for the board of royal servants in the Exchequer accounts, 1343; office unknown.", "Space:John de Glasgu (royal account 1343)"),
    ("record-medieval-1377-master-john-de-glasgow", 1377, "Master John de Glasgow", "Dunkeld and Glasgow, Scotland", "Chancellor of Dunkeld, cleric and legal proctor, 1377 to before 1419.", "Space:Master John de Glasgow (~1340 – 1419)"),
    ("record-medieval-1384-matthew-de-glasgu", 1384, "Matthew de Glasgu", "Kelso, Scotland (benefice petition)", "Papal petitioner for a benefice in the gift of Kelso Abbey, 20 December 1384 roll.", "Space:Matthew de Glasgu (fl. 1394)"),
    ("record-medieval-1394-william-de-glasgu-priest", 1394, "William de Glasgu, priest", "Kelso / Kilwinning, Scotland (benefice petitions)", "Two 1394 papal petitions for benefices in the gifts of Kelso and Kilwinning abbeys; separate from the physician.", "Space:William de Glasgu (fl. 1394)"),
    ("record-medieval-1394-john-de-glasgu-father-malcolm", 1394, "John de Glasgu, father of Malcolm", "Perth, Scotland (account)", "Named as Malcolm's father in an Exchequer payment of the king's debt; family-identifying use.", "Space:John de Glasgu (father of Malcolm)", "scotland", "family"),
    ("record-medieval-1395-william-physician-de-glasgu", 1395, "William, physician de Glasgu", "Linlithgow, Scotland (customs account)", "Royal customs remission on two sacks of wool and a later royal gift, 1395–1397.", "Space:William physician de Glasgu"),
    ("record-medieval-1447-john-de-glasgu-burgess", 1447, "John de Glasgu", "Glasgow, Scotland", "Glasgow burgess and witness in burgh property acts of 21 June 1447 and 10 April 1455.", "Space:John Glasgow-1"),
    ("record-medieval-1475-john-glasgw-stirling", 1475, "John Glasgw", "Stirling, Scotland", "Witness to Stirling property and endowment acts, 11 April 1475 and 2 March 1479/80; plausible but unproved father of John Glasgow of Saltmarket.", "Space:John Glasgw of Stirling"),
)


def repair():
    changed = Counter()
    entries = json.loads(ENTRIES.read_text(encoding="utf-8"))
    present = {entry["id"] for entry in entries}
    for record_id, year, name, place, life, anchor, *extra in MEDIEVAL_OCCURRENCES:
        if record_id in present:
            continue
        country_override = extra[0] if extra else None
        basis_override = extra[1] if len(extra) > 1 else None
        entries.append({
            "id": record_id,
            "year": year,
            "name": name,
            "slug": "",
            "place": place,
            "life": life,
            "basis": basis_override or ("family" if record_id.endswith("father-alexander") else "mention"),
            "sources": [],
            "atlas": False,
            "country": country_override or ("ireland" if place.startswith("Dublin") else "england" if "England" in place or place.startswith("Kippax") else "scotland"),
            "url": (
                "https://www.wikitree.com/wiki/" + quote(anchor.replace(" ", "_"), safe=":_()~-.,'")
                if anchor.startswith("Space:") else f"{REGISTER}#{anchor}"
            ),
        })
        changed["medieval_register_entries"] += 1
    site = ROOT / "www"
    catalogue = json.loads((site / "data/catalogue-search-index.json").read_text())
    people = {row["id"]: row for row in catalogue}
    links = json.loads((ROOT / "data/wikitree/catalogue-profile-links.json").read_text())["entries"]
    overrides = json.loads((ROOT / "data/wikitree/live-profile-overrides.json").read_text())
    redirects = normalized_profile_redirects(overrides["redirects"])
    register_ids = {occurrence[0] for occurrence in MEDIEVAL_OCCURRENCES}
    records = json.loads((site / "assets/research/record-index.json").read_text())
    person_records = {}
    for record in records:
        if record.get("p") in register_ids and record.get("document_id"):
            person_records.setdefault(record["p"], []).append(record)
    for entry in entries:
        ident = entry["id"]
        person = links.get(ident, {}).get("profile_id") or ident
        slug = redirects.get(person, person).lower()
        if slug not in people:
            continue
        updates = {"slug": slug}
        if ident in person_records:
            mentions = person_records[ident]
            updates["date_label"] = mentions[0]["year"]
            updates["sources"] = list(dict.fromkeys(item["document_id"] for item in mentions))
        if entry.get("atlas"):
            updates["atlas_id"] = people[slug]["map_key"]
        if not ident.startswith("record-medieval-"):
            updates["name"] = people[slug]["name"]
        if ident.startswith("record-corsoun-1598-"):
            updates.update(year=1598, basis="family", life="Named in Andrew Glasgow’s testament, made 6 February 1597/8 and confirmed 10 July 1598.")
        elif ident == "record-edinburgh-1577-andrew-glasgow":
            updates.update(life="Named with Katherine as a lawful child of John Glasgow in his testament.")
        if any(entry.get(key) != value for key, value in updates.items()):
            entry.update(updates)
            changed["catalogue_links"] += 1
    if changed:
        entries.sort(key=lambda entry: (entry["year"], entry["name"], entry["id"]))
        ENTRIES.write_text(json.dumps(entries, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    script = (ROOT / "tools/early_records.js").read_bytes()
    asset = site / "assets/v3/early.js"
    if not asset.exists() or asset.read_bytes() != script:
        asset.write_bytes(script)
        changed["early_script"] += 1
    page = site / "early-records/index.html"
    content = page.read_text()
    version = hashlib.sha256(script).hexdigest()[:10]
    updated = re.sub(r'/assets/v3/early\.js(?:\?v=[a-z0-9]+)?', f'/assets/v3/early.js?v={version}', content)
    if updated != content:
        page.write_text(updated)
        changed["early_page"] += 1
    early_count = sum(any(year <= 1699 for year in row.get("date_years", [])) for row in catalogue)
    card = re.compile(r'(<a class="browse-card" href=")[^"]*("><strong>Before 1700</strong><span>)[\d,]+')
    for route in ("catalogue.html", "catalogue/index.html", "catalogue/advanced.html", "people/index.html"):
        path = site / route
        content = path.read_text()
        updated = card.sub(lambda match: f"{match[1]}/catalogue/?to=1699#catalogue-filters{match[2]}{early_count:,}", content)
        if updated != content:
            path.write_text(updated)
            changed["catalogue_shortcut"] += 1
    return changed


if __name__ == "__main__":
    print(dict(repair()))
