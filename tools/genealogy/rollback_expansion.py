#!/usr/bin/env python3
"""Restore the preceding three-case corpus and 15-minute schedule, retaining edits."""
import argparse
from datetime import datetime
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
RUNTIME = Path.home() / 'Library/Application Support/genealogy-tools'
BACKUP = RUNTIME / 'backups/open-profile-expansion'
LABEL = 'com.wikitree.genealogy-index-refresh'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    if not (BACKUP / 'launchagent.plist').is_file():
        raise SystemExit('Expansion backups missing; refusing rollback')
    if not args.apply:
        print('Will restore pre-expansion files, corpus/config and refresh schedule; retain current versions. Add --apply to execute.')
        return
    subprocess.run(['launchctl', 'bootout', f'gui/{os.getuid()}/{LABEL}'], capture_output=True)
    saved = RUNTIME / ('expansion-rollback-current-' + datetime.now().strftime('%Y%m%d-%H%M%S'))
    saved.mkdir()
    def retain(path, relative):
        if path.exists():
            target = saved / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(path), str(target))
    for directory in ('tools', 'skills', 'docs', 'src'):
        for original in (BACKUP / directory).rglob('*'):
            if original.is_file():
                relative = original.relative_to(BACKUP)
                retain(ROOT / relative, relative)
                shutil.copy2(original, ROOT / relative)
    retain(ROOT / 'AGENTS.md', 'AGENTS.md')
    shutil.copy2(BACKUP / 'AGENTS.md', ROOT / 'AGENTS.md')
    config = RUNTIME / 'qmd/index.yml'
    retain(config, 'runtime/qmd-index.yml')
    shutil.copy2(BACKUP / 'qmd-index.yml', config)
    plist = Path.home() / 'Library/LaunchAgents' / (LABEL + '.plist')
    retain(plist, 'launchagent.plist')
    shutil.copy2(BACKUP / 'launchagent.plist', plist)
    for name in ('open-profile-status.json', 'open-profile-sources.json'):
        retain(RUNTIME / name, 'runtime/' + name)
    retain(RUNTIME / 'corpus/notes/open-profiles', 'runtime/open-profiles')
    for name in ('open_profiles.py', 'check_open_status.py', 'batch_complete.py', 'test_expansion.py', 'rollback_expansion.py'):
        retain(ROOT / 'tools/genealogy' / name, 'tools/genealogy/' + name)
    subprocess.run([sys.executable, str(ROOT / 'tools/genealogy/refresh.py'), '--refresh'], check=True)
    subprocess.run(['launchctl', 'bootstrap', f'gui/{os.getuid()}', str(plist)], check=True)
    print('Expansion rolled back; current edits retained at:', saved)
    print('Restart the project MCP sessions/new Codex chat.')


if __name__ == '__main__':
    main()
