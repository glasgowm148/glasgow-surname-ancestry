"""Keep the public Early Records index aligned with the medieval register."""

from collections import Counter
import json
from pathlib import Path


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
)


def repair():
    changed = Counter()
    entries = json.loads(ENTRIES.read_text(encoding="utf-8"))
    present = {entry["id"] for entry in entries}
    for record_id, year, name, place, life, anchor in MEDIEVAL_OCCURRENCES:
        if record_id in present:
            continue
        entries.append({
            "id": record_id,
            "year": year,
            "name": name,
            "slug": "",
            "place": place,
            "life": life,
            "basis": "family" if record_id.endswith("father-alexander") else "mention",
            "sources": [],
            "atlas": False,
            "country": "ireland" if place.startswith("Dublin") else "england" if "England" in place or place.startswith("Kippax") else "scotland",
            "url": f"{REGISTER}#{anchor}",
        })
        changed["medieval_register_entries"] += 1
    if changed:
        entries.sort(key=lambda entry: (entry["year"], entry["name"], entry["id"]))
        ENTRIES.write_text(json.dumps(entries, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    return changed


if __name__ == "__main__":
    print(dict(repair()))
