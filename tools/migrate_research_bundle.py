"""Offline, explicit migration from one legacy research directory to one bundle.

This command does not discover cases, contact services, refresh research, or
rebuild any catalogue.  It delegates conversion and same-directory protection
to the established Glasgow research-toolkit bridge.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from glasgow_research_toolkit import write_toolkit_research_bundle


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        prog="migrate_research_bundle.py",
        description="Convert one explicit legacy research directory into a private toolkit bundle offline."
    )
    result.add_argument("--research-dir", type=Path, required=True, help="existing legacy research directory")
    result.add_argument("--bundle-dir", type=Path, required=True, help="new private toolkit bundle directory")
    return result


def main(argv: list[str] | None = None) -> int:
    command = parser()
    args = command.parse_args(argv)
    try:
        paths = write_toolkit_research_bundle(args.research_dir, args.bundle_dir)
    except ValueError as error:
        command.error(str(error))
    print(f"Wrote private toolkit research bundle to {args.bundle_dir}")
    print(f"Toolkit bundle manifest: {paths['bundle-manifest.json']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
