"""Project cached HTML, CSV and data scripts through the public privacy policy."""
import csv
from copy import copy
from io import StringIO
import json
import re

from bs4 import BeautifulSoup

try:
    from tools.public_ydna_research import approved_document
except ModuleNotFoundError:
    from public_ydna_research import approved_document

NOTICE = "Private family or tester details withheld."


def capture_data(raw):
    return any('"' + key + '"' in raw for key in ("profile_id", "biography_text", "biography_wikitext", "record_passages"))


def project_html(raw, policy):
    soup = BeautifulSoup(raw, "html.parser")
    for script in soup.select('script[type="application/json"], script[type="application/ld+json"]'):
        if script.string and (policy.contains_private_id(script.string) or capture_data(script.string)):
            value = policy.project(json.loads(script.string))
            script.string = json.dumps(value, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    for pre in soup.find_all("pre"):
        if policy.contains_private_id(pre.get_text()) or capture_data(pre.get_text()):
            try:
                pre.string = json.dumps(policy.project(json.loads(pre.get_text())), ensure_ascii=False, indent=2)
            except json.JSONDecodeError:
                pre.string = NOTICE
    # Remove the whole containing prose/row, including names printed beside
    # the identifier. Merely blanking an href leaves that independent leak.
    for tag in list(soup.find_all(["tr", "p", "li", "a", "h1", "h2", "h3", "h4", "title", "dt", "dd", "span", "option"])):
        if tag.parent and policy.contains_private_id(str(tag)):
            tag.clear()
            tag.append(NOTICE)
            for attribute, value in list(tag.attrs.items()):
                if policy.contains_private_id(value):
                    tag.attrs.pop(attribute, None)
    for tag in soup.find_all(["meta", "img", "input"]):
        for attribute, value in list(tag.attrs.items()):
            if policy.contains_private_id(value):
                tag.attrs.pop(attribute, None)
    for script in soup.find_all("script"):
        if script.string and (policy.contains_private_id(script.string) or capture_data(script.string)):
            script.string = project_script(script.string, policy)
    for comment in soup.find_all(string=lambda value: isinstance(value, str)):
        # Source comments/attribute values can independently retain identifiers.
        # Scripts and prose above have already undergone structured projection.
        if comment.parent and comment.parent.name not in {"script", "pre"} and policy.contains_private_id(comment):
            comment.replace_with(NOTICE)
    return str(soup)


def project_csv(raw, policy):
    reader = csv.DictReader(StringIO(raw.lstrip("\ufeff")))
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=reader.fieldnames, lineterminator="\n")
    writer.writeheader()
    for row in reader:
        if any(policy.contains_private_id(row.get(key) or "") for key in ("profile_ids", "profile_id", "catalogue_id", "id")):
            continue
        writer.writerow({key: NOTICE if policy.contains_private_id(value) else value for key, value in row.items()})
    return ("\ufeff" if raw.startswith("\ufeff") else "") + output.getvalue()


def project_script(raw, policy):
    # Data-only scripts are legacy mirrors of the JSON indexes, not executable
    # transforms. Decode each assignment while preserving its variable name.
    pattern = re.compile(r"(?:window\.)?[A-Za-z_$][\w$]*\s*=\s*(?=[\[{])")
    changes = []
    decoder = json.JSONDecoder()
    for match in pattern.finditer(raw):
        try:
            value, end = decoder.raw_decode(raw, match.end())
        except json.JSONDecodeError:
            continue
        text = raw[match.end():end]
        if policy.contains_private_id(text) or capture_data(text):
            changes.append((match.end(), end, json.dumps(policy.project(value), ensure_ascii=False, separators=(",", ":"))))
    for start, end, value in reversed(changes):
        raw = raw[:start] + value + raw[end:]
    if policy.tester_ids:
        raw = re.sub(r'(["\'])([^"\'\n]*)\1',
                     lambda match: match[1] + NOTICE + match[1] if policy.contains_private_id(match[2]) else match[0], raw)
    return raw


def repair(web, policy, *, paths=None):
    changed = 0
    for path in web.rglob("*") if paths is None else paths:
        if path.suffix.lower() not in {".html", ".js", ".csv", ".txt", ".md"} or not path.is_file():
            continue
        raw = path.read_text(encoding="utf-8")
        page_policy = policy
        if approved_document(path.relative_to(web).as_posix(), raw):
            # Publication permission covers this exact study only. Keep the
            # ordinary living-profile and restricted-capture checks in force.
            page_policy = copy(policy)
            page_policy.tester_ids = frozenset()
            page_policy.tester_pattern = re.compile(r"(?!)")
            page_policy.allow_approved_dna = True
        if not page_policy.contains_private_id(raw) and not capture_data(raw):
            continue
        if path.suffix == ".html":
            updated = project_html(raw, page_policy)
        elif path.suffix == ".js":
            updated = project_script(raw, page_policy)
        elif path.suffix == ".csv" or path.name.endswith(".csv.txt"):
            updated = project_csv(raw, page_policy)
        else:
            updated = page_policy.project(raw)
        if updated != raw:
            path.write_text(updated, encoding="utf-8")
            changed += 1
    return changed
