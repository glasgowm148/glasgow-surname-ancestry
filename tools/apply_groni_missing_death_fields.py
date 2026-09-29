#!/usr/bin/env python3
"""Set death date/place for reviewed GRONI matches already cited on WikiTree."""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from wikitree_family_export import post_wikitree

MATCHES = {
    'Glasgow-1363': 'D/1897/20/1004/20/403',
    'Glasgow-1368': 'D/1881/50/1007/41/66',
    'Glasgow-1387': 'D/1874/49/1007/17/123',
    'Glasgow-1389': 'D/1870/50/1007/17/273',
    'Glasgow-1401': 'D/1900/23/1004/12/293',
    'Glasgow-1403': 'D/1874/52/1007/12/431',
    'Glasgow-1790': 'D/1875/99/1009/6/45',
    'Glasgow-1798': 'D/1900/48/1007/54/58',
    'Glasgow-2011': 'D/1890/27/1005/13/100',
    'Glasgow-2885': 'D/1884/183/1022/7/459',
    'Glasgow-2975': 'D/1890/23/1004/9/446',
    'Glasgow-2981': 'D/1865/99/1009/1/329',
    'Glasgow-3196': 'D/1875/98/1009/2/344',
    'Glasgow-3438': 'D/1887/100/1009/8/224',
    'Glasgow-3955': 'D/1879/191/1023/9/27',
    'Glasgow-3988': 'D/1865/24/1004/1/118',
}
LEDGER = ROOT / 'surname-research/indexes/groni-live-registration-ledger-2026-09-23.json'
LOG = Path('/tmp/groni-missing-death-fields-live-log.json')
rows = {r['registration_number']: r for r in json.loads(LEDGER.read_text())['rows']}
log = json.loads(LOG.read_text()) if LOG.exists() else {'saved': [], 'failed': []}
done = {x['id'] for x in log['saved']}
tab = os.environ['WT_EDIT_TABID']

def profile(wid):
    return post_wikitree({'action': 'getProfile', 'key': wid,
                          'fields': 'Name,Id,Bio,DeathDate,DeathLocation'})['profile']

for wid, reg in MATCHES.items():
    if wid in done:
        continue
    try:
        row = rows[reg]
        date = row['event_date_iso']
        place = row['district'] + ', Ireland'
        p = profile(wid)
        bio = p.get('bio') or p.get('Bio') or ''
        if reg not in bio:
            raise ValueError('Registration is not cited in live biography')
        if p.get('DeathDate') not in ('0000-00-00', '1851-00-00' if wid == 'Glasgow-3955' else '0000-00-00'):
            raise ValueError('Unexpected existing death date: ' + str(p.get('DeathDate')))
        if p.get('DeathLocation'):
            raise ValueError('Unexpected existing death location: ' + p['DeathLocation'])
        patch = {'u': int(p['Id']), 'summary': f'Set cited GRONI death date and place {reg}',
                 'sugid': 'summarySuggestion-bio',
                 'set': {'mDeathDate': date, 'mDeathLocation': place},
                 'status': {'DeathDate': 'guess', 'DeathLocation': 'guess'}}
        patchfile = Path(f'/tmp/groni-death-fields-{wid}.json')
        patchfile.write_text(json.dumps(patch) + '\n')
        result = subprocess.run(['node', 'tools/wikitree/wt_apply.mjs', str(patchfile)],
                                cwd=ROOT, env={**os.environ, 'TABID': tab, 'WT_PARALLEL': '1'},
                                capture_output=True, text=True, timeout=300)
        if result.returncode:
            raise RuntimeError((result.stdout + result.stderr)[-600:])
        check = profile(wid)
        if check.get('DeathDate') != date or check.get('DeathLocation') != place:
            raise RuntimeError('Live readback did not show requested date/place: ' + json.dumps({'date': check.get('DeathDate'), 'place': check.get('DeathLocation')}))
        log['saved'].append({'id': wid, 'registration': reg, 'death_date': date, 'death_location': place})
        LOG.write_text(json.dumps(log, indent=2) + '\n')
        print('SAVED', wid, reg, date, place, flush=True)
    except Exception as exc:
        log['failed'].append({'id': wid, 'registration': reg, 'error': str(exc)})
        LOG.write_text(json.dumps(log, indent=2) + '\n')
        print('FAIL', wid, reg, exc, flush=True)
        break
