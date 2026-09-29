#!/usr/bin/env python3
"""Attach reviewed exact-date GRONI death index rows to existing WikiTree profiles."""
import json
import os
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
from src.wikitree_family_export import post_wikitree

work = json.loads(Path(sys.argv[1]).read_text())
log_path = Path(sys.argv[2])
try:
    log = json.loads(log_path.read_text())
except FileNotFoundError:
    log = {"saved": [], "skipped": [], "failed": []}
done = {x["registration"] for x in log["saved"] + log["skipped"]}
tab = os.environ["WT_EDIT_TABID"]


def persist():
    log_path.write_text(json.dumps(log, indent=2) + "\n")


for row in work:
    reg = row["registration"]
    if reg in done:
        continue
    wid = row["profile_id"]
    try:
        profile = post_wikitree({"action": "getProfile", "key": wid,
                                 "fields": "Name,Id,Bio,DeathDate,DeathLocation"})["profile"]
        body = profile.get("bio") or profile.get("Bio") or ""
        if profile.get("DeathDate") != row["death_date"]:
            raise ValueError(f"exact death date mismatch: {profile.get('DeathDate')} != {row['death_date']}")
        if reg in body:
            log["skipped"].append({"registration": reg, "profile_id": wid, "reason": "already cited"})
            persist()
            print("SKIP", wid, reg, flush=True)
            continue
        natural = date.fromisoformat(row["death_date"]).strftime("%-d %B %Y")
        age = f", aged {row['age']}" if row.get("age") else ""
        sentence = (f"The death of {row['forename']} Glasgow was registered on {natural} "
                    f"in {row['district']}{age}.<ref>[https://geni.nidirect.gov.uk/search/death "
                    f"GRONI civil death index], {row['forename']} Glasgow, {natural}{age}, "
                    f"{row['district']} registration district, {reg}.</ref>")
        source_heading = re.search(r"^==\s*Sources\s*==", body, re.I | re.M)
        if source_heading:
            marker = source_heading.start()
            new_body = body[:marker].rstrip() + "\n\n" + sentence + "\n\n" + body[marker:]
        else:
            new_body = body.rstrip() + "\n\n" + sentence + "\n\n== Sources ==\n<references />\n"
        set_fields = {}
        status = {}
        if not profile.get("DeathLocation"):
            set_fields["mDeathLocation"] = row["district"] + ", Ireland"
            status["DeathLocation"] = "guess"
        patch = {"u": int(profile["Id"]), "text": new_body,
                 "summary": f"Add GRONI death index citation {reg}",
                 "sugid": "summarySuggestion-sources", "set": set_fields, "status": status}
        patch_path = Path(f"/tmp/groni-exact-death-{os.getpid()}.json")
        patch_path.write_text(json.dumps(patch))
        env = {**os.environ, "TABID": tab, "WT_PARALLEL": "1"}
        result = subprocess.run(["node", "tools/wikitree/wt_apply.mjs", str(patch_path)],
                                cwd=root, env=env, capture_output=True, text=True, timeout=600)
        output = result.stdout + result.stderr
        if result.returncode or '"saved":true' not in output.replace(" ", ""):
            raise RuntimeError(output[-1000:])
        check = post_wikitree({"action": "getProfile", "key": wid, "fields": "Name,Bio,DeathLocation"})["profile"]
        if reg not in (check.get("bio") or check.get("Bio") or ""):
            raise RuntimeError("saved URL returned but citation absent on API readback")
        log["saved"].append({"registration": reg, "profile_id": wid,
                             "death_location": check.get("DeathLocation")})
        persist()
        print("SAVED", wid, reg, flush=True)
    except Exception as error:
        log["failed"].append({"registration": reg, "profile_id": wid, "error": str(error)})
        persist()
        print("FAIL", wid, reg, str(error)[-450:], flush=True)
        break
