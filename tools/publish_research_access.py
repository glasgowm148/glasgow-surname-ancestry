#!/usr/bin/env python3
"""Publish small, fingerprinted indexes and HTML routes without rebuilding research."""
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
from html import escape
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / 'www'
CHUNK_SIZE = 100


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(value, ensure_ascii=False, separators=(',', ':')) + '\n' if not isinstance(value, str) else value
    if not path.exists() or path.read_text() != text:
        path.write_text(text)


def block(path, name, content):
    text = path.read_text()
    pattern = rf'<!-- {name}:start -->.*?<!-- {name}:end -->'
    replacement = f'<!-- {name}:start -->{content}<!-- {name}:end -->'
    if re.search(pattern, text, re.S):
        text = re.sub(pattern, lambda _: replacement, text, flags=re.S)
    else:
        text = re.sub(r'(<main\b[^>]*>)', lambda m: m[1] + replacement, text, count=1)
    write(path, text)


def page(template, title, body, url):
    text = re.sub(r'<title>.*?</title>', '<title>' + escape(title) + ' · Glasgow surname archive</title>', template, count=1)
    text = re.sub(r'<main\b[^>]*>.*?</main>', lambda _: '<main id="main"><h1>' + escape(title) + '</h1>' + body + '</main>', text, count=1, flags=re.S)
    text = re.sub(r'<script data-clean-index-redirect>.*?</script>', '', text, flags=re.S)
    text = re.sub(r'<link rel="canonical"[^>]*>', f'<link rel="canonical" href="https://glasgow.phenotype.dev{url}">', text)
    # Browse pages are written at several depths (/catalogue/browse/page-N.html,
    # /branches/browse/); the data/ template's ../-relative asset and nav links
    # only resolve from /data/, so hoist local refs to root-relative.
    text = re.sub(r'((?:href|src)=["\'])(?:\.\./)+', r'\1/', text)
    return text


def repair():
    template = (WEB / 'data/index.html').read_text()
    people = json.loads((WEB / 'data/people-index.json').read_text())
    records = json.loads((WEB / 'data/records-index.json').read_text())
    branches = json.loads((WEB / 'assets/research/branches.json').read_text())
    datasets = []
    for name, rows, scope in [
        ('people', people, 'Public historical-person discovery index; follow json_url for the resolved dossier and field provenance.'),
        ('records', records, 'Public record associations, including qualified and unresolved leads; these are not unique historical events.'),
        ('families', branches, 'Maintained family studies and imported tree groups; membership does not establish kinship.'),
    ]:
        chunks = []
        for start in range(0, len(rows), CHUNK_SIZE):
            number = start // CHUNK_SIZE + 1
            path = WEB / f'data/chunks/{name}-{number:04d}.json'
            write(path, {'schema_version': '1.0', 'scope': scope, 'offset': start, 'count': len(rows[start:start + CHUNK_SIZE]), 'items': rows[start:start + CHUNK_SIZE]})
            raw = path.read_bytes()
            chunks.append({'url': '/' + str(path.relative_to(WEB)), 'count': len(rows[start:start + CHUNK_SIZE]), 'bytes': len(raw), 'sha256': sha256(raw).hexdigest()})
        datasets.append({'name': name, 'scope': scope, 'count': len(rows), 'chunks': chunks})
    dates = []
    dossier_hash = sha256()
    dossier_count = 0
    for path in sorted((WEB / 'people').glob('*.json')):
        if path.name.endswith('.network.json'):
            continue
        data = json.loads(path.read_text())
        if 'vitals' not in data:
            continue
        dossier_count += 1
        dossier_hash.update(path.name.encode() + b'\0' + path.read_bytes())
        dates.extend(f['updated'] for f in data.get('research_findings', []) if re.fullmatch(r'\d{4}-\d{2}-\d{2}', f.get('updated') or ''))
    assessments = json.loads((WEB / 'assets/research/assessments.json').read_text())
    dates.extend(a['reviewed'] for a in assessments.get('assessments', []) if a.get('reviewed'))
    releases = []
    for relative, scope in [
        ('data/people.json', 'Imported people and records; not the resolved reviewed dossier interface.'),
        ('data/people-index.json', 'Discovery index; use the linked resolved person dossiers for conclusions.'),
        ('data/records.csv.txt', 'Public record-association bulk text export; interpretation and source-status fields must be retained.'),
        ('assets/research/assessments.json', 'Published review register; approved structured assessments are applied to the resolved dossiers.'),
        ('data/schema/person.schema.json', 'Resolved person dossier schema.'),
        ('assets/research/free-space-index.json', 'External-study directory, availability and links to dated public summaries; not full external page contents.'),
    ]:
        raw = (WEB / relative).read_bytes()
        releases.append({'url': '/' + relative, 'scope': scope, 'bytes': len(raw), 'sha256': sha256(raw).hexdigest()})
    manifest = {'schema_version': '1.0', 'scope': 'Published public research only. Local notes, staged decisions, private originals and external full studies are not included unless explicitly linked as published content.',
                'latest_research_update': max(dates) if dates else None,
                'research_date_basis': 'Latest explicit research_findings.updated or assessment.reviewed date in the published dossiers/register; not a rebuild date or a claim every page was reviewed then.',
                'datasets': datasets, 'bulk_exports': releases,
                'resolved_dossiers': {'count': dossier_count, 'sha256': dossier_hash.hexdigest(), 'fingerprint_basis': 'Sorted dossier filenames, NUL separator, then exact file bytes.', 'url_template': '/people/{catalogue_id}.json', 'scope': 'Current reviewed structured values where an approved assessment exists; otherwise imported evidence with its existing uncertainty. Original values remain under imported.'}}
    build_id = sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()[:20]
    old_path = WEB / 'data/manifest.json'
    old = json.loads(old_path.read_text()) if old_path.exists() else {}
    manifest.update(build_id=build_id, generated_at=old.get('generated_at') if old.get('build_id') == build_id else datetime.now(timezone.utc).isoformat(timespec='seconds'))
    write(old_path, manifest)
    chunk_links = ''.join(f'<li>{escape(d["name"].title())}: {d["count"]:,} entries — ' + ' · '.join(f'<a href="{c["url"]}">{i + 1}</a>' for i, c in enumerate(d['chunks'])) + '</li>' for d in datasets)
    body = f'<section class="data-access" aria-labelledby="access-title"><div class="data-section-head"><span class="r-kicker">Current release</span><h2 id="access-title">Current data and small downloads.</h2></div><p><a href="/data/manifest.json"><strong>Build manifest (JSON)</strong></a> · Build <code>{build_id}</code> · Assembled {escape(manifest["generated_at"])}. Latest dated person research or review: {escape(manifest["latest_research_update"] or "not recorded")}.</p><p>Start with the small indexes below, then follow each person’s JSON link for the current resolved dossier. Approved reviews override imported fields; <code>imported</code> preserves the original values and provenance. Unreviewed fields retain their existing qualifications. The bulk <code>people.json</code> export is an imported research snapshot, not the reviewed interface.</p><p>The manifest records dataset scopes, entry counts, byte sizes and SHA-256 hashes. Re-fetch it when resuming research; a changed build identifier means the listed data changed. Build time is separate from research dates.</p><details class="data-chunks"><summary>Browse small JSON chunks</summary><ul>{chunk_links}</ul></details><p class="data-browse-links"><a href="/catalogue/browse/">Browse all people without JavaScript</a> · <a href="/branches/browse/">Browse all family groups without JavaScript</a></p></section>'
    block(WEB / 'data/index.html', 'research-access', body)
    llms_path = WEB / 'llms.txt'
    if llms_path.exists():
        text = llms_path.read_text()
        intro = ('<!-- research-access:start -->\n'
                 '## Current research interface\n\n'
                 '- Start at https://glasgow.phenotype.dev/data/manifest.json for the current content fingerprint, separate research dates, scopes, counts and small index chunks.\n'
                 '- Follow person json_url links for resolved dossiers: approved reviews override imported fields, with originals under imported and provenance preserved. Bulk people.json is an imported snapshot.\n'
                 '- Static browse routes: https://glasgow.phenotype.dev/catalogue/browse/ and https://glasgow.phenotype.dev/branches/browse/. Source pages include published evidence without JavaScript.\n'
                 '- External studies and private originals are not included in full. Dated safe study summaries: https://glasgow.phenotype.dev/free-space/. Browser-local decisions are unpublished until exported and deployed.\n'
                 '<!-- research-access:end -->\n\n')
        text = re.sub(r'<!-- research-access:start -->.*?<!-- research-access:end -->\s*', '', text, flags=re.S)
        write(llms_path, intro + text)
    for name, rows in [('catalogue', people), ('branches', branches)]:
        count = (len(rows) + CHUNK_SIZE - 1) // CHUNK_SIZE
        for i in range(count):
            url = f'/{name}/browse/' + (f'page-{i + 1}.html' if i else '')
            links = []
            for row in rows[i * CHUNK_SIZE:(i + 1) * CHUNK_SIZE]:
                label = row.get('name') or row.get('label')
                target = row.get('html_url') or row.get('url')
                detail = (' · '.join(str(v) for v in [row.get('id'), row.get('birth_year'), row.get('death_year')] if v)) if name == 'catalogue' else (row.get('description') or 'Imported tree group; relationships require independent evidence.')
                links.append(f'<li><a href="{escape(target, quote=True)}">{escape(label)}</a> — {escape(detail)}</li>')
            nav = ' · '.join(f'<a href="/{name}/browse/{"" if n == 0 else f"page-{n + 1}.html"}">{n + 1}</a>' for n in range(count))
            content = f'<p>{len(rows):,} entries. Page {i + 1} of {count}. These links work without JavaScript; search filters remain available on the <a href="/{name}/">interactive page</a>.</p><nav aria-label="Index pages" style="overflow-wrap:anywhere;line-height:2">{nav}</nav><ul>{"".join(links)}</ul>'
            destination = WEB / url.lstrip('/') / 'index.html' if url.endswith('/') else WEB / url.lstrip('/')
            write(destination, page(template, 'Browse people' if name == 'catalogue' else 'Browse family groups', content, url))
        block(WEB / name / 'index.html', 'static-browse', f'<p><a href="/{name}/browse/">Browse all {"people" if name == "catalogue" else "family groups"} without JavaScript</a> · <a href="/data/">Small data downloads and freshness manifest</a></p>')
    return Counter(research_access=1, index_chunks=sum(len(d['chunks']) for d in datasets))


if __name__ == '__main__':
    print(dict(repair()))
