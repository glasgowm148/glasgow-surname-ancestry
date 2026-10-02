"""Remove prose-inferred assessment dates from public derived interfaces.

The dated assertions and source text remain intact. Previous generated dates
are retained with an explicit correction reason, never promoted to event dates.
"""
from collections import Counter
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from tools.catalogue_machine_data import _year
PROVENANCE = 'surname-research/indexes/relationship-hypotheses.md'
REASON = 'No structured event date was supplied; numbers in assessment prose are not event dates.'


def assessment_ids(value):
    result = set()
    if isinstance(value, dict):
        if value.get('provenance') == PROVENANCE and str(value.get('id', '')).startswith('E-'):
            result.add(value['id'])
        for child in value.values():
            result.update(assessment_ids(child))
    elif isinstance(value, list):
        for child in value:
            result.update(assessment_ids(child))
    return result


def correct(value, targets):
    count = 0
    if isinstance(value, dict):
        key = value.get('evidence_id') or value.get('id')
        if (key in targets and value.get('basis') != 'reviewed_event_role'
                and 'date_correction' not in value and any(value.get(k) is not None for k in ('date', 'raw_date', 'year'))):
            previous = {k: value[k] for k in ('date', 'raw_date', 'year') if k in value}
            for field in previous:
                value[field] = None
            value['date_correction'] = {'previous': previous, 'reason': REASON}
            count += 1
        for field, child in value.items():
            if field != 'date_correction':
                count += correct(child, targets)
    elif isinstance(value, list):
        count += sum(correct(child, targets) for child in value)
    return count


def write_json(path, value):
    text = json.dumps(value, ensure_ascii=False, separators=(',', ':')) + '\n'
    if not path.exists() or path.read_text() != text:
        path.write_text(text)
        return 1
    return 0


def repair(web=ROOT / 'www'):
    from tools.repair_sources_page import source_row, repair as repair_sources
    from tools.publish_static_sources import START, END, block
    web = Path(web)
    counts = Counter()
    targets = set()
    for path in (web / 'people').glob('*.json'):
        if not path.name.endswith('.network.json'):
            targets.update(assessment_ids(json.loads(path.read_text())))
    # Explicit dates, when introduced into the maintained assessment model,
    # remain authoritative. The legacy extraction never supplied this marker.
    from tools.catalogue_machine_data import _assessment_claim, _relationship_assessments
    for assessment in _relationship_assessments():
        if assessment.get('event_date'):
            targets.discard(_assessment_claim(assessment, {})[1]['id'])
    paths = set((web / 'people').glob('*.json'))
    for folder in ('assets/research/people', 'assets/research/evidence',
                   'assets/v3/events', 'assets/v3/sources'):
        paths.update((web / folder).glob('*.json'))
    paths.add(web / 'assets/research/event-index.json')
    for path in sorted(paths):
        if not path.exists():
            continue
        data = json.loads(path.read_text())
        changed = correct(data, targets)
        if changed:
            counts['date_corrections'] += changed
            counts['json_files'] += write_json(path, data)
        # The reader has a no-JavaScript citation mirror as well as its JSON.
        # Refresh only the generated evidence block; preserve the shell and
        # all narrative numbers (profile IDs, archive references, real years).
        if path.parent == web / 'assets/v3/sources' and any(
                c.get('date_correction') for key in ('citations', 'events') for c in data.get(key, [])):
            reader = web / 'sources' / path.stem / 'index.html'
            if reader.exists():
                page = reader.read_text()
                replacement = block(data)
                if START in page and END in page:
                    before, rest = page.split(START, 1)
                    _, after = rest.split(END, 1)
                    updated = before + replacement + after
                else:
                    updated = page.replace('<div id="v3-reader"', replacement + '\n<div id="v3-reader"', 1)
                    if updated == page:
                        raise ValueError(f'Source reader evidence marker missing: {reader}')
                if updated != page:
                    reader.write_text(updated)
                    counts['source_readers'] += 1
    index_path = web / 'assets/v3/source-index.json'
    if not index_path.exists():
        return dict(counts)
    rows = json.loads(index_path.read_text())
    for row in rows:
        path = web / 'assets/v3/sources' / (row['id'] + '.json')
        if not path.exists():
            continue
        document = json.loads(path.read_text())
        if not any(c.get('date_correction') for key in ('citations', 'events') for c in document.get(key, [])):
            continue
        entries = [*document.get('citations', []), *document.get('events', []), *document.get('records', [])]
        if row.get('date_basis') == 'reviewed event date':
            entries = [e for e in entries if e.get('basis') == 'reviewed_event_role']
        years = [year for entry in entries if (year := _year(str(entry.get('date') or ''))) is not None]
        row['from'], row['to'] = (min(years), max(years)) if years else (None, None)
    counts['source_indexes'] += write_json(index_path, rows)
    if (web / 'sources/index.html').exists():
        counts.update(repair_sources(web))
    # Re-sort the complete no-script index as well as the interactive index.
    ordered = sorted(rows, key=lambda row: (row.get('from') if row.get('from') is not None else 9999, row['title'].casefold()))
    for path in (web / 'sources/browse').glob('*.html'):
        match = re.fullmatch(r'page-(\d+)\.html', path.name)
        if path.name != 'index.html' and not match:
            continue
        number = 1 if path.name == 'index.html' else int(match[1])
        page = path.read_text()
        expected = ordered[(number-1)*100:number*100]
        pattern = r'<article\b[^>]*class="[^"]*\bv3-source-row\b[^"]*"[^>]*>.*?</article>'
        existing = len(re.findall(pattern, page, flags=re.S))
        if existing != len(expected):
            raise ValueError(f'Complete source browse row count mismatch in {path}: {existing} rows, expected {len(expected)}')
        rendered = iter(source_row(row) for row in expected)
        updated = re.sub(pattern,
                         lambda _: next(rendered), page, flags=re.S)
        if updated != page:
            path.write_text(updated)
            counts['source_browse_pages'] += 1
    return dict(counts)


if __name__ == '__main__':
    print(repair())
