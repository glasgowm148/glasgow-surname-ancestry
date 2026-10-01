#!/usr/bin/env python3
"""Safely stage the reviewed genealogy corpus and optionally refresh QMD.

The manifest is the allowlist. A source is staged only while it remains a
regular file below the project root with the recorded SHA256. The staging lock
and atomic state write keep readers from observing a half-refresh.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = Path(__file__).with_name("collections.json")
RUNTIME = Path.home() / "Library/Application Support/genealogy-tools"
CORPUS = RUNTIME / "corpus"
NOTES = CORPUS / "notes"
PDFS = CORPUS / "pdf"
STATE = RUNTIME / "genealogy-refresh-state.json"
LOCK = RUNTIME / "genealogy-refresh.lock"
FRONTMATTER_LINES = 6


@contextmanager
def refresh_lock():
    RUNTIME.mkdir(parents=True, exist_ok=True)
    handle = LOCK.open("a+")
    try:
        import fcntl

        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        yield
    finally:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        finally:
            handle.close()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def safe_source(relative: str, expected: str) -> tuple[Path | None, str | None]:
    raw = ROOT / relative
    if raw.is_symlink() or raw.absolute() != raw.resolve(strict=False):
        return None, "symlinked"
    candidate = raw.resolve(strict=False)
    try:
        candidate.relative_to(ROOT)
    except ValueError:
        return None, "outside project root"
    if not candidate.is_file():
        return None, "missing or non-regular"
    actual = sha256(candidate)
    if actual != expected:
        return None, "SHA256 changed"
    return candidate, None


def clean_stage(directory: Path, allowed: set[str]) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for child in directory.iterdir():
        if child.name not in allowed:
            if child.is_dir() and not child.is_symlink():
                shutil.rmtree(child)
            else:
                child.unlink()


def stage_note(source: Path, entry: dict, destination: Path) -> None:
    original = source.read_text(encoding="utf-8")
    metadata = (
        "---\n"
        f"source_path: {entry['source']}\n"
        f"source_sha256: {entry['sha256']}\n"
        f"review_reason: {entry['review_reason']}\n"
        f"source_mapping_offset: {FRONTMATTER_LINES}\n"
        "---\n"
    )
    temporary = destination.with_suffix('.tmp')
    temporary.write_text(metadata + original, encoding="utf-8")
    os.replace(temporary, destination)


def stage_pdf(source: Path, destination: Path) -> None:
    if destination.is_file() and sha256(destination) == sha256(source):
        return
    temporary = destination.with_suffix('.tmp')
    shutil.copyfile(source, temporary)
    os.replace(temporary, destination)


def write_state(state: dict) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    temporary = STATE.with_suffix(".tmp")
    temporary.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, STATE)


def run_qmd() -> dict:
    qmd = RUNTIME / "node" / "node_modules" / ".bin" / "qmd"
    if not qmd.is_file():
        return {"qmd": "unavailable", "unfinished": ["qmd_not_installed"]}
    env = {
        "PATH": "/opt/homebrew/bin:/usr/bin:/bin",
        "HOME": str(RUNTIME / "qmd-home"),
        "QMD_CONFIG_DIR": str(RUNTIME / "qmd"),
        "INDEX_PATH": str(RUNTIME / "qmd" / "index.sqlite"),
    }
    env["QMD_CONFIG_DIR"] = str(RUNTIME / "qmd")
    result = subprocess.run([str(qmd), "update"], cwd=ROOT, env=env, check=False)
    return {"qmd": "updated" if result.returncode == 0 else "failed", "qmd_exit": result.returncode,
            "unfinished": [] if result.returncode == 0 else ["qmd_update_failed"]}


def run_pdf() -> dict:
    env = {"PATH": "/opt/homebrew/bin:/usr/bin:/bin",
           "HOME": str(RUNTIME / 'pdf-home'),
           "PDF_MCP_CACHE_DIR": str(RUNTIME / 'pdf-cache'),
           "PDF_MCP_MAX_WORKERS": "2", "HF_HUB_OFFLINE": "1",
           "HF_HUB_DISABLE_TELEMETRY": "1", "DO_NOT_TRACK": "1"}
    code = '''import json,sys
from pdf_mcp.tools.corpus_tools import pdf_corpus_warm
result=pdf_corpus_warm(sys.argv[1],budget_seconds=45,embeddings=False)
print(json.dumps(result))
'''
    result = subprocess.run([str(RUNTIME / 'pdf-venv/bin/python'), '-c', code, str(PDFS)],
                            env=env, capture_output=True, text=True, timeout=120)
    if result.returncode:
        return {"pdf": "failed", "pages": 0, "unfinished": ["pdf_warm_failed"]}
    try:
        data = json.loads(result.stdout.strip().splitlines()[-1])
    except (IndexError, ValueError):
        return {"pdf": "failed", "pages": 0, "unfinished": ["pdf_warm_response_invalid"]}
    (RUNTIME / 'pdf-warm-state.json').write_text(json.dumps(data, indent=2) + '\n')
    remaining = data.get('unprocessed', [])
    return {"pdf": "pending" if remaining else "warmed", "pages": sum(d.get('pages', 0) for d in data.get('docs', [])),
            "unfinished": ["pdf_more_pages_pending"] if remaining else []}


def refresh(stage_only: bool) -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    entries = manifest["collections"]
    reviewed = withheld = 0
    unfinished: list[str] = []
    allowed_notes = {e["staged_name"] for e in entries if e["kind"] == "note"}
    allowed_pdfs = {e["staged_name"] for e in entries if e["kind"] == "pdf"}
    with refresh_lock():
        clean_stage(NOTES, allowed_notes | {'open-profiles'})
        clean_stage(PDFS, allowed_pdfs)
        for entry in entries:
            source, reason = safe_source(entry["source"], entry["sha256"])
            if source is None:
                withheld += 1
                unfinished.append(f"withheld:{entry['source']}:{reason}")
                stale = (NOTES if entry['kind'] == 'note' else PDFS) / entry['staged_name']
                stale.unlink(missing_ok=True)
                continue
            destination = (NOTES if entry["kind"] == "note" else PDFS) / entry["staged_name"]
            if entry["kind"] == "note":
                stage_note(source, entry, destination)
            else:
                stage_pdf(source, destination)
            reviewed += 1
        from open_profiles import stage as stage_open_profiles
        profile_result = stage_open_profiles(NOTES / 'open-profiles')
        result = {"qmd": "skipped", "pdf": "skipped", "pages": 0}
        if not stage_only:
            result = run_qmd()
            unfinished.extend(result.pop("unfinished", []))
            pdf_result = run_pdf()
            unfinished.extend(pdf_result.pop('unfinished', []))
            result.update(pdf_result)
        state = {
            "reviewed": reviewed,
            "withheld": withheld,
            "unfinished": sorted(set(unfinished)),
            **profile_result,
            **result,
        }
        write_state(state)
    print(json.dumps(state, sort_keys=True))
    return 0 if not withheld and not any(k in state["unfinished"] for k in ("qmd_update_failed", "pdf_warm_failed", "pdf_warm_response_invalid")) else 1


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--stage-only", action="store_true", help="stage reviewed sources without updating QMD (default)")
    mode.add_argument("--refresh", action="store_true", help="stage sources and run the installed QMD update")
    args = parser.parse_args(argv)
    return refresh(stage_only=not args.refresh)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
