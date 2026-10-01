"""Refresh local search after a successful approved website research batch."""
from pathlib import Path
import subprocess
import sys


def refresh_after_batch():
    runtime = Path.home() / 'Library/Application Support/genealogy-tools'
    if not (runtime / 'mcp-policy.json').is_file():
        return 0  # Optional local tooling on other machines.
    result = subprocess.run([sys.executable, str(Path(__file__).with_name('refresh.py')), '--refresh'],
                            capture_output=True, text=True)
    if result.returncode:
        print('Local genealogy index refresh needs attention: ' + result.stdout.strip()[-2000:], file=sys.stderr)
    else:
        print('Local genealogy index refreshed after approved research batch.', file=sys.stderr)
    return result.returncode
