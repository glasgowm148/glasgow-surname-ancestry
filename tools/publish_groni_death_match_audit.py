#!/usr/bin/env python3
"""Publish the supplied GRONI death-index match review in the Ireland account."""

from __future__ import annotations

import csv
import html
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "surname-research/indexes/groni-death-match-audit-2026-09-23.csv"
META = SOURCE.with_suffix(".json")
PRIORITIES = ROOT / "surname-research/indexes/groni-full-record-priorities-2026-09-23.json"
WEB = ROOT / "www"
IRELAND = WEB / "branches/early-ireland/index.html"
SOURCES = WEB / "sources/index.html"
PUBLIC = WEB / "data/groni-death-match-audit-2026-09-23.csv"
CROSSWALK = ROOT / "surname-research/indexes/groni-birth-marriage-crosswalk-clean-2026-09-23.json"
PUBLIC_CROSSWALK = WEB / "data/groni-birth-marriage-crosswalk-2026-09-23.json"
LIVE_LEDGER = ROOT / "surname-research/indexes/groni-live-registration-ledger-2026-09-23.json"
CREATION_LOG = ROOT / "surname-research/indexes/groni-live-creation-log-2026-09-23.json"
START = "<!-- BEGIN GRONI-DEATH-MATCH -->"
END = "<!-- END GRONI-DEATH-MATCH -->"
LINK_START = "<!-- BEGIN GRONI-DEATH-MATCH-LINK -->"
LINK_END = "<!-- END GRONI-DEATH-MATCH-LINK -->"


def esc(value: object) -> str:
    return html.escape(str(value or ""), quote=True)


def clear(text: str, start: str, end: str) -> str:
    return re.sub(re.escape(start) + r".*?" + re.escape(end), "", text, flags=re.S)


def publish() -> dict[str, int]:
    with SOURCE.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    meta = json.loads(META.read_text(encoding="utf-8"))
    priorities = json.loads(PRIORITIES.read_text(encoding="utf-8"))["ranked"]
    if len(rows) != meta["row_count"]:
        raise ValueError("GRONI audit count differs from provenance")
    live_rows = {
        row["registration_number"]: row
        for row in json.loads(LIVE_LEDGER.read_text(encoding="utf-8"))["rows"]
        if row["record_type"] == "death" and row["status"] == "verified"
    }
    created_refs = {
        row["registration"]
        for row in json.loads(CREATION_LOG.read_text(encoding="utf-8"))["created"]
    }

    labels = {
        "existing_profile": "Existing profile",
        "existing_profile_update": "Existing profile · action pending",
        "new_profile_created": "New profile created",
        "lead_attached": "Lead attached",
        "possible_profile": "Possible profile · review",
        "no_catalogue_match": "No suitable WikiTree fit found",
        "unnamed_hold": "Unnamed · hold",
    }
    body = []
    for row in rows:
        status = row["assessment"]
        if status == "deferred_robert":
            continue
        verified = live_rows.get(row["registration_number"])
        ids = verified["live_matches"] if verified else [part for part in row["candidate_wikitree_ids"].split(";") if part]
        links = ", ".join(
            f'<a href="https://www.wikitree.com/wiki/{esc(pid)}">{esc(pid)}</a>'
            for pid in ids
        ) or "—"
        body.append(
            "<tr><td>{name}</td><td>{date}</td><td>{district}</td><td>{age}</td>"
            "<td>{links}</td><td>{status}</td></tr>".format(
                name=esc(row["forename_as_supplied"] + " Glasgow"),
                date=esc(row["death_date"]),
                district=esc(row["district"]),
                age=esc(row["age_at_death"]),
                links=links,
                status=esc(("New profile; index cited" if row["registration_number"] in created_refs else "Cited research lead" if status == "lead_attached" else "Index and death details on profile") if verified else labels[status]),
            )
        )
    created = len(set(live_rows) & created_refs)
    assigned = sum(row['assessment'] == 'existing_profile' for row in rows)
    leads = sum(row['assessment'] == 'lead_attached' for row in rows)
    matched = assigned + leads
    if len(live_rows) != len(rows) - 5:
        raise ValueError("Not all non-Robert death entries were verified live")
    priority_rows = []
    by_registration = {row["registration_number"]: row for row in rows}
    for priority in priorities:
        row = by_registration[priority["registration_id"]]
        candidate_ids = re.findall(r"[A-Za-z][A-Za-z'-]*-\d+", priority["candidate"])
        links = ", ".join(
            f'<a href="https://www.wikitree.com/wiki/{esc(pid)}">{esc(pid)}</a>'
            for pid in dict.fromkeys(candidate_ids)
        )
        priority_rows.append(
            f'<tr><td>{priority["rank"]}</td><td>{esc(row["forename_as_supplied"])} Glasgow, '
            f'{esc(row["death_date"])}<br><small>{esc(priority["registration_id"])}</small></td>'
            f'<td>{links}</td><td>{esc(priority["question"])}</td></tr>'
        )
    section = f'''{START}
<section id="groni-death-matches" class="groni-death-matches" aria-labelledby="groni-death-title">
<style>
#groni-death-matches {{ margin:2.5rem 0; padding:1.5rem; border:1px solid var(--g-line,#d8ddd4); border-radius:12px; background:var(--g-surface,#fff); }}
#groni-death-matches .groni-scroll {{ max-width:100%; overflow-x:auto; }}
#groni-death-matches table {{ border-collapse:collapse; min-width:700px; width:100%; font-size:.9rem; }}
#groni-death-matches th,#groni-death-matches td {{ padding:.6rem; border-bottom:1px solid var(--g-line,#d8ddd4); text-align:left; vertical-align:top; }}
</style>
<span class="r-kicker">Civil-death index match review</span>
<h2 id="groni-death-title">Northern Ireland Glasgow death entries</h2>
<p>A user-supplied transcription of <a href="https://geni.nidirect.gov.uk/search/death">GRONI death-search results</a> records 152 distinct entries. All 147 non-Robert references have been verified in live WikiTree biographies: {assigned} matched to existing profiles, {leads} cited as research leads on existing profiles, and {created} on newly created profiles. The five Robert death entries are handled separately.</p>
<p>The review cross-references 307 supplied births and 102 marriages. Fifteen newly profiled children have matching birth entries, including <a href="https://www.wikitree.com/wiki/Glasgow-4192">George Glasgow of Cookstown</a> and <a href="https://www.wikitree.com/wiki/Glasgow-4193">Mary Glasgow of Belfast</a>; their profiles use the indexed birth dates. The three Armagh children whose birth entries name Hewitt as their mother's maiden surname are linked to <a href="https://www.wikitree.com/wiki/Hewitt-8271">Helen (Hewitt) Glasgow</a>, spouse of <a href="https://www.wikitree.com/wiki/Glasgow-3157">William Glasgow</a>. This supersedes the former Unknown mother placeholder, Hewitt-9718, which was merged into Hewitt-8271.</p>
<p>In Belfast, <a href="https://www.wikitree.com/wiki/Glasgow-4208">Sarah born in 1889</a> and <a href="https://www.wikitree.com/wiki/Glasgow-4195">Sarah born in 1891</a> are linked to their <a href="https://www.wikitree.com/wiki/Mitchell-58907">Mitchell mother</a>. Their births share the mother's maiden surname and district; the later Sarah was born after the first died. <a href="https://www.wikitree.com/wiki/Glasgow-4186">Adam</a> and <a href="https://www.wikitree.com/wiki/Glasgow-4200">Samuel</a> are linked to their <a href="https://www.wikitree.com/wiki/Moore-107968">Moore mother</a> on the same birth-index evidence.</p>
<p>The stated death dates and ages are index details; age-derived birth years are approximate. A registration district does not establish an exact death address. Paid certificates were not consulted. When multiple death entries compete for one identity, the biography cites them without assigning both as that person's death.</p>
<p><a href="https://www.wikitree.com/wiki/Glasgow-1390">William Glasgow</a>, <a href="https://www.wikitree.com/wiki/Glasgow-1802">David Glasgow</a> and <a href="https://www.wikitree.com/wiki/Glasgow-3140">John Glasgow</a> each have two cited death-index leads that cannot both be their death. Their structured death fields remain open. The William and David returns rank among the most useful full records to view because an informant, occupation or precise address could separate the same-name men.</p>
<p>Ann Glasgow's 14 March 1877 entry is cited on <a href="/people/cushnehan-1.html">Anne (Cushnehan) Glasgow</a>. The 1890 Rosetta entry is cited on <a href="/people/glasgow-1422.html">Rose Ann Glasgow</a> as a possible identity, and the 1867 Margaret entry is cited on <a href="https://www.wikitree.com/wiki/Unknown-766238">Margaret's profile</a> while preserving its more specific place evidence.</p>
<p><a href="/data/groni-death-match-audit-2026-09-23.csv" download>Download all 152 entries with registration numbers and match reasoning (CSV)</a>, <a href="/data/groni-birth-marriage-crosswalk-2026-09-23.json" download>the dated birth and marriage leads (JSON)</a>, or <a href="/data/glasgow_civil_records_master.csv" download>the full combined 561-row birth, death and marriage coverage (CSV)</a>. Jane of Larne is linked to <a href="/people/glasgow-4013.html">Glasgow-4013</a> through her compatible birth bound and Larne locality; her live profile now has the 4 September 1873 death date.</p>
<h3>Full-record research priorities</h3><p>These {len(priority_rows)} registrations may distinguish same-name people or test specific family links. The full returns have not been viewed; an informant, occupation or precise address may settle the question.</p>
<div class="groni-scroll" tabindex="0" role="region" aria-label="Priority death registrations"><table><thead><tr><th>Rank</th><th>Registration</th><th>Possible profile</th><th>Question to resolve</th></tr></thead><tbody>{''.join(priority_rows)}</tbody></table></div>
<details><summary>Browse {len(body)} reviewed entries</summary><div class="groni-scroll" tabindex="0" role="region" aria-label="GRONI death match table"><table><thead><tr><th>Name</th><th>Death date</th><th>Registration district</th><th>Age</th><th>WikiTree candidate</th><th>Assessment</th></tr></thead><tbody>{''.join(body)}</tbody></table></div></details>
</section>
{END}'''

    page = clear(IRELAND.read_text(encoding="utf-8"), START, END)
    if "</main>" not in page:
        raise ValueError("Ireland page lacks main close")
    IRELAND.write_text(page.replace("</main>", section + "</main>", 1), encoding="utf-8")
    discovery = (
        LINK_START
        + '<aside class="repair-static-note" aria-label="Northern Ireland death matches"><p>'
        + '<strong>Northern Ireland death matches:</strong> <a href="/branches/early-ireland/#groni-death-matches">'
        + f'{assigned} existing matches, {leads} research leads and {created} new profiles; all 147 non-Robert death references verified live'
        + "</a> from the supplied GRONI death-search list.</p></aside>"
        + LINK_END
    )
    page = clear(SOURCES.read_text(encoding="utf-8"), LINK_START, LINK_END)
    if "</h1>" not in page:
        raise ValueError("Sources page lacks heading")
    SOURCES.write_text(page.replace("</h1>", "</h1>" + discovery, 1), encoding="utf-8")
    PUBLIC.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(SOURCE, PUBLIC)
    shutil.copyfile(CROSSWALK, PUBLIC_CROSSWALK)
    return {"rows": len(rows), "public_rows": len(body), "matched": matched}


if __name__ == "__main__":
    print(publish())
