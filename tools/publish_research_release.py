#!/usr/bin/env python3
"""Refresh research-access interfaces after targeted or full site generation."""
from pathlib import Path
import runpy

ROOT = Path(__file__).resolve().parents[1]


def publish():
    runpy.run_path(str(ROOT / 'tools/publish_resolved_dossiers.py'))['publish']()
    runpy.run_path(str(ROOT / 'tools/publish_static_sources.py'))['main']()
    runpy.run_path(str(ROOT / 'tools/publish_research_access.py'))['repair']()


if __name__ == '__main__':
    publish()
