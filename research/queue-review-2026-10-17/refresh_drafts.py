"""Refresh source-draft dispositions and the maintained creation register."""
from collections import defaultdict
from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parents[2]
subjects = json.loads((ROOT / 'research/latest-findings-subjects/subjects.json').read_text())
reviews = json.loads((ROOT / 'research/research-queue-matches.json').read_text())['reviews']
updates = defaultdict(list)
suggestions = []
for group in subjects['groups']:
    for person in group['people']:
        ident = 'subject-' + group['slug'] + '-' + person['anchor']
        review = reviews.get(ident, {})
        if review.get('reviewed_on') != '2026-10-17':
            continue
        url = '/research/subjects/' + group['slug'] + '/#' + person['anchor']
        for path in person.get('draft_sources', []):
            if path.startswith('surname-research/new-people/') and (ROOT / path).exists():
                updates[path].append((person['name'], review, url))
        if review['status'] == 'no_compatible_profile':
            suggestions.append((person['name'], review.get('draft_path', person['draft_sources'][0])))

for path, items in updates.items():
    text = (ROOT / path).read_text()
    start, end = '<!-- identity-review-2026-10-17 -->', '<!-- identity-review-2026-10-17:end -->'
    block = start + '\n## Current identity disposition — 17 October 2026\n\n'
    for name, review, url in items:
        ids = review.get('profile_ids', [])
        label = ('Compatible existing profile(s): ' + ', '.join('[[' + pid + ']]' for pid in ids) if ids else
                 'Suggested new profile; complete sourced draft retained' if review['status'] == 'no_compatible_profile' else
                 'Record retained without a separate profile-creation recommendation')
        block += '**' + name + ': ' + label + '.** [Current evidence and complete draft](' + url + '). ' + review['assessment'] + '\n\n'
    block += end + '\n'
    if start in text:
        text = re.sub(re.escape(start) + '.*?' + re.escape(end) + '\n?', lambda _: block, text, flags=re.S)
    else:
        first, _, rest = text.partition('\n')
        text = first + '\n\n' + block + '\n' + rest.lstrip('\n')
    if any(r.get('profile_ids') for _, r, _ in items):
        text = re.sub(r'^READY TO CREATE[^\n]*', 'HOLD — compatible existing-profile candidate(s); the current assessment above controls the earlier draft.', text, flags=re.M, count=1)
    (ROOT / path).write_text(text)

path = ROOT / 'surname-research/to-update.md'
text = path.read_text()
start, end = '<!-- queue-new-profile-suggestions-2026-10-17:start -->', '<!-- queue-new-profile-suggestions-2026-10-17:end -->'
block = start + '\n## Suggested new profiles — reviewed 17 October 2026\n\n'
block += 'Existing-profile searches and their limits are recorded in each complete sourced draft. These are local suggestions; no live creation has been performed. Preserve the stated source-reading, family and chronology qualifications.\n\n'
block += '| Person | Status | Complete sourced draft |\n| --- | --- | --- |\n'
for name, draft in suggestions:
    block += '| ' + name.replace('|', '/') + ' | SUGGESTED NEW | [Draft](../' + draft + ') |\n'
block += '\n' + end + '\n'
text = re.sub(re.escape(start) + '.*?' + re.escape(end) + '\n?', lambda _: block, text, flags=re.S) if start in text else text.rstrip() + '\n\n' + block
path.write_text(text)
print(dict(source_drafts_refreshed=len(updates), suggested_new_profiles=len(suggestions)))
