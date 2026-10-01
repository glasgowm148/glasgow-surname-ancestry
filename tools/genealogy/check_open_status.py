#!/usr/bin/env python3
"""Explicit, anonymous WikiTree privacy/living-status check; no biographies."""
from datetime import datetime, timezone
import json
import re
import time
import urllib.parse
import urllib.request
from open_profiles import metadata, RUNTIME, STATUS, atomic_text


def main():
    rows, _ = metadata()
    ids = sorted(ident for ident, row in rows.items() if str(row.get('Privacy')) == '60')
    output = {}
    for start in range(0, len(ids), 500):
        params = {'action': 'getPeople', 'keys': ','.join(ids[start:start + 500]),
                  'fields': 'Name,Privacy,IsLiving', 'appId': 'WikitreeGenealogyLocalIndex'}
        request = urllib.request.Request('https://api.wikitree.com/api.php',
                                        data=urllib.parse.urlencode(params).encode())
        data = json.load(urllib.request.urlopen(request, timeout=45))[0]
        if data.get('status'):
            raise RuntimeError('WikiTree privacy check failed; prior snapshot preserved')
        people = data.get('people', {})
        for ident in ids[start:start + 500]:
            result = data.get('resultByKey', {}).get(ident, {})
            redirected = re.match(r'Redirected to (\d+)/', str(result.get('status', '')))
            current_id = redirected[1] if redirected else str(result.get('Id'))
            row = people.get(current_id, {})
            if row:
                output[ident] = {key: row[key] for key in ('Privacy', 'IsLiving') if key in row}
                if row.get('Name') != ident:
                    output[ident]['canonical_name'] = row.get('Name')
        time.sleep(1)
    # Missing records fail closed rather than silently retaining old eligibility.
    for ident in ids:
        output.setdefault(ident, {'Privacy': None})
    RUNTIME.mkdir(parents=True, exist_ok=True)
    payload = {'checked_at': datetime.now(timezone.utc).isoformat(),
               'fields': ['Privacy', 'IsLiving'], 'profiles': output}
    atomic_text(STATUS, json.dumps(payload, sort_keys=True) + '\n')
    print(json.dumps({'checked': len(output), 'open_nonliving': sum(
        str(row.get('Privacy')) == '60' and str(row.get('IsLiving')) == '0' for row in output.values())}))


if __name__ == '__main__':
    main()
