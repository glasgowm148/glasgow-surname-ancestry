#!/usr/bin/env python3
"""Reversibly undo this local installation; --apply is required."""
import argparse
from datetime import datetime
from pathlib import Path
import shutil
import subprocess
import os

root = Path(__file__).resolve().parents[2]
runtime = Path.home() / 'Library/Application Support/genealogy-tools'
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--apply', action='store_true')
args = parser.parse_args()
required = [runtime / 'backups/AGENTS.md.before', runtime / 'backups/skill-before/SKILL.md']
if not all(p.is_file() for p in required):
    raise SystemExit('Original backups are missing; refusing rollback')
label = 'com.wikitree.genealogy-index-refresh'
destination = runtime.with_name('genealogy-tools.rollback-' + datetime.now().strftime('%Y%m%d-%H%M%S'))
if not args.apply:
    print('Will stop the refresh LaunchAgent, restore backed-up AGENTS.md and skill,')
    print('and move newly installed files/runtime aside. No originals, auth or provider settings change.')
    print('Run this same command with --apply to execute.')
    raise SystemExit(0)
subprocess.run(['launchctl', 'bootout', f'gui/{os.getuid()}/{label}'], capture_output=True)
saved = runtime / 'rollback-project-current'
saved.mkdir(parents=True, exist_ok=False)


def retain(path, relative):
    if path.exists():
        target = saved / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(path), str(target))


retain(root / 'AGENTS.md', 'AGENTS.md')
retain(root / 'skills/wikitree-research/SKILL.md', 'skills/wikitree-research/SKILL.md')
shutil.copy2(required[0], root / 'AGENTS.md')
shutil.copy2(required[1], root / 'skills/wikitree-research/SKILL.md')
# These files existed before tooling; remove only our batch/metadata additions
# by restoring their preserved, already-dirty pre-expansion copies.
for relative in ('tools/sync_catalogue_research.py', 'tools/publish_research_release.py',
                 'tools/sync_wikitree_profile_evidence.py', 'src/wikitree_family_export.py'):
    original = runtime / 'backups/open-profile-expansion' / relative
    if original.is_file():
        retain(root / relative, relative)
        shutil.copy2(original, root / relative)
for name in ('identity-and-evidence.md', 'profile-workflows.md', 'catalogue-and-site.md', 'transcription.md'):
    retain(root / 'skills/wikitree-research/references' / name, Path('skills/wikitree-research/references') / name)
retain(root / '.codex/config.toml', '.codex/config.toml')
old_config = runtime / 'backups/config.toml.before'
if old_config.exists():
    shutil.copy2(old_config, root / '.codex/config.toml')
retain(root / 'docs/genealogy-tooling.md', 'docs/genealogy-tooling.md')
plist = Path.home() / 'Library/LaunchAgents' / (label + '.plist')
retain(plist, Path('launchagent') / plist.name)
old_plist = runtime / 'backups/launchagent.before.plist'
if old_plist.exists():
    shutil.copy2(old_plist, plist)
    subprocess.run(['launchctl', 'bootstrap', f'gui/{os.getuid()}', str(plist)], capture_output=True)
retain(root / 'tools/genealogy', 'tools/genealogy')
shutil.move(str(runtime), str(destination))
print('Rollback complete. Installed files and current edits retained at:', destination)
print('Restart Codex; global mac-mcp/Caveman skills, authentication and original trees are unchanged.')
