"""Build a prepared, column-packed search index and demand-loaded result details.

Preparation and worker matching are extracted from the maintained catalogue JS,
so the compact index shares its surname and filter semantics with the legacy data.
Only approved public website data is read here.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def build(site_root=ROOT / 'www'):
    source = (ROOT / 'tools/catalogue_search.js').read_text()
    normalizers = source[source.index('  const normaliseLiteral='):source.index('  const esc=')]
    prepare = source[source.index('  function prepare('):source.index('  function loadPeople(')]
    sorter = source[source.index('  function relationSurname('):source.index('  function comparePeople(')]
    script = normalizers + prepare + sorter + '''
const fs=require('node:fs');
const rows=prepare(JSON.parse(fs.readFileSync(process.argv[1],'utf8')));
for(const p of rows){
 p._search=[...new Set(p._search.split(' '))].join(' ');
 p._sortValues=Object.fromEntries(['name','birth','death','birthLocation','deathLocation','spouse','father','mother','recorded','cluster','profile','significance','fatherConfidence','changeConfidence'].map(k=>[k,sortValue(p,k)]));
 p._identityExactTokens=[...p._identityExactTokens];
}
process.stdout.write(JSON.stringify(rows));
'''
    full_path = site_root / 'data/catalogue-search-index.json'
    rows = json.loads(subprocess.run(['node', '-e', script, str(full_path)], check=True, capture_output=True, text=True).stdout)
    # Detail shards follow display-name order, keeping ordinary first-page hydration small.
    details = site_root / 'data/catalogue-details'
    details.mkdir(parents=True, exist_ok=True)
    sorted_rows = sorted(rows, key=lambda p: (p['_name'], p['id']))
    for start in range(0, len(sorted_rows), 50):
        chunk = sorted_rows[start:start + 50]
        raw = [{k: v for k, v in p.items() if not k.startswith('_') and k not in {'evidence_terms', 'biography_text'}} for p in chunk]
        content = json.dumps(raw, ensure_ascii=False, separators=(',', ':')) + '\n'
        name = hashlib.sha256(content.encode()).hexdigest()[:16] + '.json'
        target = details / name
        if not target.exists() or target.read_text() != content:
            target.write_text(content)
        for p in chunk:
            p['_detailShard'] = '/data/catalogue-details/' + name
    keep = {'id','name','profile_ids','birth','death','date_years','birth_year','death_year','gender','record_count','has_original_record','has_profile','wikitree_update_significance','wikitree_update_relationship_changes','missing_father','missing_mother','missing_profile','needs_wikitree_update','descendants','woman_married_glasgow','has_suffix'}
    compact = [{k:v for k,v in p.items() if k.startswith('_') or k in keep} for p in rows]
    search, location_search = {}, {}
    advanced = []
    sort_keys = ['name','birth','death','birthLocation','deathLocation','spouse','father','mother','recorded','cluster','profile','significance','fatherConfidence','changeConfidence']
    for i, person in enumerate(compact):
        for word in dict.fromkeys(person.pop('_search').split()): search.setdefault(word, []).append(i)
        for word in dict.fromkeys(person['_location'].split()): location_search.setdefault(word, []).append(i)
        advanced.append({k:person.pop(k) for k in ['_location','_siblings','_biography','_recordLocation']})
        person['_sortValues'] = [person['_sortValues'][k] for k in sort_keys]
    for posting_index in [search, location_search]:
        for word, ids in posting_index.items():
            posting_index[word] = [ids[0]] + [ids[i]-ids[i-1] for i in range(1,len(ids))]
    advanced_path = site_root / 'data/catalogue-search-advanced.json'
    advanced_path.write_text(json.dumps(advanced, ensure_ascii=False, separators=(',', ':'))+'\n')
    fields = sorted(set().union(*(p.keys() for p in compact)))
    strings, string_ids = [], {}
    def pack(value):
        if isinstance(value, str):
            if value not in string_ids:
                string_ids[value] = len(strings); strings.append(value)
            return -string_ids[value] - 1
        if isinstance(value, list): return [pack(x) for x in value]
        if isinstance(value, dict): return {k:pack(v) for k,v in value.items()}
        if isinstance(value, (int,float)) and value < 0: return {'number':value}
        return value
    packed_rows = [[pack(p.get(k)) for k in fields] for p in compact]
    payload = {'schema_version':1,'fields':fields,'strings':strings,'rows':packed_rows,'sort_keys':sort_keys,'search':search,'location_search':location_search}
    target = site_root / 'data/catalogue-search-fast.json'
    content = json.dumps(payload, ensure_ascii=False, separators=(',', ':')) + '\n'
    if not target.exists() or target.read_text() != content:
        target.write_text(content)
    predicate = source[source.index('  function matches('):source.index('  function relevance(')]
    predicate = predicate.replace('selectedGender()', 'filters.gender')
    import re
    predicate = re.sub(r'controls\.(\w+)\.checked', r'filters.flags.\1', predicate)
    ranking = source[source.index('  function relevance('):source.index('  function relationSurname(')].replace('person._location.includes(term)', 'queryLocationMatches.get(term)?.has(person.id)')
    compare = source[source.index('  function comparePeople('):source.index('  function sortOptions(')]
    worker_source = normalizers + sorter + ranking + compare + (ROOT / 'tools/catalogue_search_worker.js').read_text().replace('/* MATCH_PREDICATE */', predicate)
    worker = site_root / 'people/catalogue-worker.js'
    worker.parent.mkdir(parents=True, exist_ok=True)
    if not worker.exists() or worker.read_text() != worker_source:
        worker.write_text(worker_source)
    return {'catalogue_fast_bytes':target.stat().st_size,'catalogue_full_bytes':full_path.stat().st_size,'catalogue_people':len(rows)}


def refresh(site_root=ROOT / 'www'):
    """Refresh browser indexes, detail shards and content-versioned URLs."""
    from tools.catalogue_search_markup import PAGES
    from tools.stamp_asset_versions import VERSIONED_ASSET, asset_path, content_hash
    result = build(site_root)
    paths = [site_root / 'people/search.js', site_root / 'people/catalogue-worker.js',
             *(site_root / relative for relative in PAGES)]
    changed = 0
    for path in paths:
        if not path.exists() and path != site_root / 'people/search.js':
            continue
        def version(match):
            target = asset_path(site_root, path, match['url'])
            return match[0] if target is None or not target.is_file() else (
                match['quote'] + match['url'] + '?v=' + content_hash(target) + match['quote'])
        before = path.read_text() if path.exists() else ''
        authored = (ROOT / 'tools/catalogue_search.js').read_text() if path == site_root / 'people/search.js' else before
        after = VERSIONED_ASSET.sub(version, authored)
        if after != before:
            path.write_text(after)
            changed += 1
    return {**result, 'catalogue_versioned_files': changed}


if __name__ == '__main__':
    print(refresh())
