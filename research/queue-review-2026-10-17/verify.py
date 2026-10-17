"""Verify the frozen worklist, public dispositions and actual draft contents."""
from collections import Counter
from pathlib import Path
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.publish_newspaper_review import build_public_data


def read(path):
    return json.loads((ROOT / path).read_text())


baseline = read('research/queue-review-2026-10-17/baseline.json')['rows']
progress = read('research/queue-review-2026-10-17/progress.json')
queue = read('www/data/research-queue.json')
registry = read('research/research-queue-matches.json')['reviews']
suggestions = read('www/data/wikitree-new-profile-suggestions.json')['people']
assert len(baseline) == len({r['id'] for r in baseline}) == 511
assert {r['id'] for r in baseline} == set(progress['baseline_results'])
assert all(r['disposition'] in {'existing_profile', 'new_profile', 'disregarded', 'study'}
           for r in progress['baseline_results'].values())
assert progress['remaining_items'] == queue['review_progress']['remaining_items'] == 0
assert all(r.get('identity_review', {}).get('complete') and r.get('match_review') for r in queue['rows'])
assert len({p['id'] for p in suggestions}) == len(suggestions)
for person in suggestions:
    review = registry[person['id']]
    assert review['status'] == 'no_compatible_profile' and not review.get('profile_ids')
    assert all(s in person['draft_wikitext'] for s in ('== Biography ==', '== Sources ==', '<references />', '<ref'))
    assert re.search(r'https?://', person['draft_wikitext'])
    path = ROOT / 'www' / person['url'].split('#')[0].lstrip('/') / 'index.html'
    assert path.is_file() and 'id="' + person['url'].split('#')[1] + '"' in path.read_text()
    assert person['name'] in (ROOT / 'surname-research/to-update.md').read_text()
for row in progress['baseline_results'].values():
    if row['disposition'] == 'existing_profile':
        assert row.get('profile_ids')
    if row['disposition'] == 'new_profile':
        assert row.get('suggested_people')
        assert all((ROOT / p['draft_path']).is_file() for p in row['suggested_people'])
expected = build_public_data(read('surname-research/indexes/glasgow-newspaper-review.json'))
assert read('www/data/glasgow-newspaper-review.json') == expected
full = read('www/data/catalogue-search-index.json')
packed = read('www/data/catalogue-search-fast.json')
def unpack(v):
    if isinstance(v, int) and not isinstance(v, bool) and v < 0:
        return packed['strings'][-v-1]
    return v
fast = [dict(zip(packed['fields'], map(unpack, values))) for values in packed['rows']]
assert {r['id'] for r in full if r.get('needs_wikitree_update')} == {
    r['id'] for r in fast if r.get('needs_wikitree_update')}
print(json.dumps(dict(reviewed=511, remaining=0, public_rows=len(queue['rows']),
                      suggested_new_people=len(suggestions),
                      baseline_dispositions=dict(Counter(r['disposition'] for r in progress['baseline_results'].values())),
                      existing_profile_amendments=sum(bool(r.get('needs_wikitree_update')) for r in full)), indent=2))
