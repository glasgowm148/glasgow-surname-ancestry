"""Load reviewed, complete profile replacements from the maintained queue batch.

The public integration manifest is durable; the private capture/update caches
remain the source of current WikiTree text and completion history.
"""
import json
from html import escape
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


def public_additive_update(update):
    """Expose safe additions without exposing a private captured biography."""
    return {key: update[key] for key in ('profile_id', 'profile_url', 'significance', 'pending') if key in update} | {
        'summary': 'Add the cited historical record account, retaining its identity qualifications.',
        'comparison_withheld': True, 'manual_update': True,
        'public_addition_wikitext': update['public_addition_wikitext'],
        'remote_wikitext': '', 'proposed_wikitext': '', 'draft_wikitext': '',
    }


def additive_update_panel(update):
    """Label an additive patch honestly; it is not a full public replacement."""
    return '<section id="wikitree-update" class="profile-update-panel"><h2>Historical additions for WikiTree</h2>' + (
        '<p>The complete current biography and proposed replacement contain private family details and remain in the local research files. '
        'The sourced historical additions below are public. Integrate these passages into the existing biography; preserve its other text and citations.</p>'
        '<details><summary>Sourced additions only</summary><textarea class="profile-draft" readonly rows="24">'
        + escape(update['public_addition_wikitext']) + '</textarea></details></section>')
