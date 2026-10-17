"""Refresh reviewed queue panels and indexes after the substantive case sync.

This bounded pass preserves person-page research and avoids another full tree
render when only the complete amendment panel or its queue summary changes.
"""
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
BATCH = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'tools'))
from bs4 import BeautifulSoup
import build_research_catalog as catalogue
import sync_catalogue_research as sync
from queue_profile_amendments import public_additive_update
from repair_person_hierarchy import _profile_update_panel
from catalogue_search_index import refresh

spec = importlib.util.spec_from_file_location('queue_assembly', BATCH / 'assemble_amendments.py')
assembly = importlib.util.module_from_spec(spec)
spec.loader.exec_module(assembly)


def read(path):
    return json.loads(path.read_text())


def main():
    path = BATCH / 'catalogue-integration.json'
    manifest = read(path)
    baseline = ROOT / 'tmp/catalogue-integration-2026-10-17/before/www/data/catalogue-search-index.json'
    prior = {r['id']: r.get('wikitree_update_summary') or '' for r in read(baseline)
             if r.get('needs_wikitree_update')} if baseline.exists() else {}
    report_path = BATCH / 'amendment-integration.json'
    report = read(report_path)
    for ident, entry in manifest['profile_updates'].items():
        headings = [assembly.passage_label(h) for h in report['profiles'][ident]['headings']]
        summary = 'Add the cited record account' + ('s' if len(headings) > 1 else '') + ': ' + '; '.join(headings[:3])
        if len(headings) > 3:
            summary += f'; and {len(headings)-3} other record accounts'
        summary += '. Retain the stated identity and relationship limits.'
        previous = entry.get('prior_work_summary', prior.get(ident.casefold(), ''))
        entry['prior_work_summary'] = previous
        entry['summary'] = entry['work_queue_summary'] = previous + '\n\n' + summary if previous else summary
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n')
    evidence = catalogue._load_wikitree_evidence()
    policy = sync.from_sources(evidence)
    updates = catalogue._load_profile_updates(evidence)
    rows = read(ROOT / 'www/data/catalogue-search-index.json')
    by_slug = {r['id']: r for r in rows}
    for ident, entry in manifest['profile_updates'].items():
        update = updates[ident]
        complete = update['proposed_wikitext'].strip()
        (ROOT / entry['draft_path']).write_text(complete + '\n')
        if entry.get('private_comparison'):
            update = public_additive_update(update)
        assert not policy.contains_private_id(json.dumps(sync.update_data(update), ensure_ascii=False)), ident
        slug = ident.casefold()
        dossier_path = ROOT / f'www/people/{slug}.json'
        dossier = read(dossier_path)
        dossier['wikitree_update'] = sync.update_data(update)
        dossier['research_findings'] = sync.public_findings([ident], policy)
        sync.write_json(dossier_path, dossier)
        html_path = dossier_path.with_suffix('.html')
        soup = BeautifulSoup(html_path.read_text(), 'html.parser')
        previous_panel = soup.select_one('#wikitree-update')
        assert previous_panel is not None, ident
        previous_panel.replace_with(BeautifulSoup(_profile_update_panel(update), 'html.parser'))
        html_path.write_text(str(soup))
        by_slug[slug].update(needs_wikitree_update=True,
                            wikitree_update_summary=update['summary'],
                            wikitree_update_significance=update['significance'],
                            wikitree_update_relationship_changes=update.get('relationship_changes') or [])
        report['profiles'][ident]['final_replacement_sha256'] = sha256(complete.encode()).hexdigest()
        report['profiles'][ident]['final_replacement_characters'] = len(complete)
    sync.write_json(ROOT / 'www/data/catalogue-search-index.json', rows)
    (ROOT / 'www/data/people-index.js').write_text('window.glasgowPeopleIndex=' + json.dumps(rows, ensure_ascii=False, separators=(',', ':')) + ';\n')
    sync.refresh_catalogue_summaries(rows)
    refresh(ROOT / 'www')
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'amended_profiles': len(manifest['profile_updates']),
                      'missing_profile': sum(bool(r.get('missing_profile')) for r in rows),
                      'needs_update': sum(bool(r.get('needs_wikitree_update')) for r in rows)}))


if __name__ == '__main__':
    main()
