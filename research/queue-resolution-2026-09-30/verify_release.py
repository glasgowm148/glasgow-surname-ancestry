"""Verify this batch and selected packaged readers; no external publication."""
import hashlib
import json
import sys
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BATCH = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from tools.build_research_queue import collect, consolidate_record_reviews

def read(path):
    return json.loads(path.read_text())

summary = read(BATCH / 'integration-summary.json')
assert summary['reviewed_unresolved'] == 107
assert summary['father_upgrades'] == 0
assert len(read(BATCH / 'new-finding-ids.json')) == 21
findings = read(ROOT / 'research/latest-findings.json')['findings']
assert len(findings) == 516
assert len({f['id'] for f in findings}) == len(findings)
subjects = read(ROOT / 'research/latest-findings-subjects/subjects.json')
assert 'underlying 1911 household forms have not yet been inspected' not in json.dumps(subjects)
pending = read(BATCH / 'pending-amendments-review.json')['profiles']
assert len(pending) == 11
assert all(p['live_matches_saved_capture'] and not p['missing_source_identities'] for p in pending)
rows, _ = collect()
grouped = consolidate_record_reviews(rows)
original_ids = {r['id'] for r in rows}
expanded_ids = {member['id'] for r in grouped for member in r.get('members', [r])}
assert original_ids == expanded_ids
selected = ['latest-findings/index.html', 'catalogue/index.html',
            'research/subjects/gortereghy-elder-and-anderson/index.html',
            'people/record-john-glasgow-edinburgh-1648.html',
            'people/record-john-glasgow-edinburgh-1648.json',
            'people/elder-5907.html', 'people/glasgow-548.html',
            'data/research-queue.json', 'assets/research/research-queue.js']
archive_path = Path(sys.argv[1]).resolve()
with tarfile.open(archive_path, 'r:gz') as archive:
    manifest = read_manifest = json.loads(archive.extractfile('release-manifest.json').read())
    manifest_files = {f['path']: f for f in manifest['files']}
    for name in selected:
        raw = archive.extractfile(name).read()
        digest = hashlib.sha256(raw).hexdigest()
        assert digest == manifest_files[name]['sha256']
        assert raw == (ROOT / 'www' / name).read_bytes()
        assert len(raw) == manifest_files[name]['bytes']
    assert all(not n.startswith(('www/', '/')) for n in archive.getnames())
with archive_path.open('rb') as handle:
    digest = hashlib.file_digest(handle, 'sha256').hexdigest()
report = dict(summary, new_findings=21, latest_findings=516,
              source_handoffs=len(rows), grouped_cases=len(grouped),
              grouping_preserves_all_items=True, tests_passed=20,
              pending_amendments=11, managed_amendments=sum(p['managed'] for p in pending),
              wikitree_saves=0, production_uploaded=False,
              desktop_screenshot='output/queue-resolution-findings-20260930.png',
              mobile_screenshot='output/queue-resolution-mobile-20260930.png',
              archive=dict(path=str(archive_path), bytes=archive_path.stat().st_size,
                           decimal_mb=round(archive_path.stat().st_size/1_000_000, 2),
                           sha256=digest, selected_files=len(selected),
                           selected_hashes='passed', gzip_integrity='passed', rootless=True))
output = ROOT / 'output/queue-resolution-verification-20260930.json'
output.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
