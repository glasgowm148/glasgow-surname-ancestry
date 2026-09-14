# Site experience checks

File preservation is not sufficient evidence of a complete migration. Keep
these three layers distinct; a source-contract pass is not a browser pass.

## Generated-content contracts

```sh
.venv/bin/python tools/audit_site_experience.py
.venv/bin/python -m unittest discover -s tests -p 'test_site_experience.py'
```

Checks cover prominent community links, confirmed WikiTree actions, access to
Latest research, complete statistics, preserved family anchors and source-dated
feed entries. The isolated generator test supplies different full and compact
identity datasets so the wrong-data-source regression cannot silently return.
Closed disclosures and explicit hidden attributes do not count as prominence.
CSS and JavaScript visibility still require the browser check below.

The full read-only migration audit includes these generated-content contracts:

```sh
.venv/bin/python tools/repair_unified_site.py --check
```

## Real-browser contracts

With a local preview already running and Playwright CLI installed:

```sh
playwright-cli -s=site-experience open http://127.0.0.1:8080/ --headed
playwright-cli -s=site-experience run-code "$(cat tools/check_site_experience.js)"
playwright-cli -s=site-experience close
```

The script uses the currently open local origin. It checks desktop and mobile
visibility, person-page actions, exposed statistics and research-feed cards,
family sections, and preservation of specialist Map bookmark queries/hashes.
It does not submit forms, change research or visit external community sites.

These checks are a focused regression set, not an exhaustive genealogy audit,
accessibility audit, source-verification exercise or check of every browser flow.
Report generated-contract and browser results separately, including checks not
run. Do not infer working buttons from generated-file counts.
