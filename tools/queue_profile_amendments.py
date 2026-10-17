"""Load reviewed, complete profile replacements from the maintained queue batch.

The public integration manifest is durable; the private capture/update caches
remain the source of current WikiTree text and completion history.
"""
import json
from pathlib import Path

RELATIVE_MANIFEST = Path('research/queue-review-2026-10-17/catalogue-integration.json')


def reviewed_amendments(root):
    path = Path(root) / RELATIVE_MANIFEST
    if not path.exists():
        return {}
    entries = json.loads(path.read_text()).get('profile_updates', {})
    for ident, entry in entries.items():
        draft = Path(root) / entry['draft_path']
        if not draft.is_file():
            raise ValueError(f'Missing reviewed replacement for {ident}: {draft}')
    return entries


def merge_amendments(specifications, amendments, captures, report=None):
    """Replace superseded patch instructions while retaining structured actions."""
    reopened = set()
    for ident, amendment in amendments.items():
        if ident not in captures:
            if report is not None:
                report.append({'source': 'reviewed-queue', 'profile_id': ident,
                               'kind': 'no_capture', 'reason': 'reviewed replacement needs a public capture'})
            continue
        previous = specifications.get(ident, {})
        # The saved replacement already includes the effective prior draft.
        # Reapplying its old patches would duplicate or invalidate the work.
        entry = {key: value for key, value in previous.items() if key not in {
            'replacements', 'post_merge_replacements', 'addition_wikitext',
            'preservation_review_path', 'preserve_captured_detail',
            'reviewed_narrative_reduction', 'manual_update', 'registered_update',
            'work_queue_summary', 'draft_path',
        }}
        entry.update(amendment)
        entry.update(registered_update=False, manual_update=False)
        specifications[ident] = entry
        reopened.add(ident)
    return reopened
