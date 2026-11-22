#!/usr/bin/env python3
"""Prepare, extract and review bounded evidence packets. Application is disabled.

No command imports a workbench writer or executes proposed operations. Run artifacts
are an operational spool, never an authoritative research registry.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import datetime, timezone
from functools import partial
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
from threading import Event
import time

try:
    from tools.project_paths import atomic_write_text
    from tools.research_batch_contract import (EXTRACTION_PROMPT, REVIEW_PROMPT, digest, parse_json,
                                               check_preconditions, review_proposal, validate_extraction, validate_packet)
except ModuleNotFoundError:
    from project_paths import atomic_write_text
    from research_batch_contract import (EXTRACTION_PROMPT, REVIEW_PROMPT, digest, parse_json,
                                         check_preconditions, review_proposal, validate_extraction, validate_packet)

PROJECT = Path(__file__).resolve().parents[1]
ROUTES = {"deepseek": "opencode-go/deepseek-v4.1-flash", "sol": "openai/gpt-6.1-sol"}
MAX_PACKET_BYTES = 64000


def _read(path):
    return parse_json(Path(path).read_text(encoding="utf-8"))


def _write(path, value):
    atomic_write_text(Path(path), json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    Path(path).chmod(0o600)


def _safe_output(path):
    path = Path(path).absolute()
    if any(probe.is_symlink() for probe in (path, *path.parents)):
        raise ValueError("Run output cannot traverse symlinks")
    path = path.resolve()
    if path == PROJECT or PROJECT in path.parents:
        relative = path.relative_to(PROJECT)
        if not relative.parts or relative.parts[0] not in {".cache", "artifacts", "tmp", "test-results"}:
            raise ValueError("Operational output cannot overwrite research, database, website or source directories")
    return path


@contextmanager
def _lock(folder):
    lock = folder / ".controller.lock"
    if lock.is_symlink():
        raise ValueError("Run lock cannot be a symlink")
    with lock.open("a") as stream:
        lock.chmod(0o600)
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise ValueError("Another controller owns this run") from error
        try:
            yield
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)


def prepare(packet_path, output, *, route="deepseek"):
    raw = Path(packet_path).read_bytes()
    if len(raw) > MAX_PACKET_BYTES:
        raise ValueError("Packet exceeds the 64000-byte bound; retrieve a bounded dossier")
    packet = validate_packet(parse_json(raw.decode("utf-8")))
    if route not in ROUTES:
        raise ValueError("Unknown extraction route")
    output = _safe_output(output)
    try:
        output.mkdir(parents=True, mode=0o700)
    except FileExistsError as error:
        raise ValueError("Prepare needs a new empty run directory; do not overwrite earlier receipts") from error
    output.chmod(0o700)
    _write(output / "packet.json", packet)
    manifest = {"format": "research-batch-run", "format_version": 1, "task_id": packet["task_id"],
                "packet_sha256": digest(packet), "extraction_model": ROUTES[route],
                "review_model": ROUTES["sol"], "created_at": datetime.now(timezone.utc).isoformat(),
                "preconditions": check_preconditions(packet),
                "application_enabled": False}
    _write(output / "manifest.json", manifest)
    return manifest


def _state(folder):
    folder = _safe_output(folder)
    manifest, packet = _read(folder / "manifest.json"), validate_packet(_read(folder / "packet.json"))
    if (manifest.get("format") != "research-batch-run" or manifest.get("format_version") != 1
            or manifest.get("application_enabled") is not False
            or manifest.get("task_id") != packet["task_id"] or manifest.get("packet_sha256") != digest(packet)
            or manifest.get("extraction_model") not in ROUTES.values() or manifest.get("review_model") != ROUTES["sol"]):
        raise ValueError("Run manifest or frozen evidence packet changed")
    return folder, manifest, packet


def _opencode(command, *, cwd, env, timeout, cancelled=None):
    """Bound a CLI process group, including cleanup on interruption/timeout."""
    if cancelled is not None and cancelled.is_set():
        raise InterruptedError("Research batch interrupted")
    process = subprocess.Popen(command, cwd=cwd, env=env, text=True, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, start_new_session=True)
    try:
        if cancelled is None:
            stdout, stderr = process.communicate(timeout=timeout)
            return process.returncode, stdout, stderr
        deadline = time.monotonic() + timeout
        while not cancelled.is_set():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise subprocess.TimeoutExpired(command, timeout)
            try:
                stdout, stderr = process.communicate(timeout=min(0.1, remaining))
            except subprocess.TimeoutExpired:
                continue
            return process.returncode, stdout, stderr
        raise InterruptedError("Research batch interrupted")
    except BaseException:
        try:
            os.killpg(process.pid, signal.SIGTERM)
            process.communicate(timeout=5)
        except (ProcessLookupError, subprocess.TimeoutExpired):
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.communicate()
        raise


def _events(stdout):
    result = []
    for line in stdout.splitlines():
        try:
            event = parse_json(line)
            if isinstance(event, dict):
                result.append(event)
        except ValueError:
            pass  # CLI/plugin diagnostics are retained in the raw log.
    return result


def _call(folder, stage, model, payload, prompt, *, timeout=180, runner=None):
    request = {"model": model, "agent": "batch-packet", "prompt": prompt, "payload": payload}
    request_hash = digest(request)
    receipt_path = folder / (stage + "-receipt.json")
    response_path = folder / (stage + "-response.json")
    if receipt_path.exists():
        receipt = _read(receipt_path)
        if receipt.get("request_sha256") != request_hash:
            raise ValueError("Existing stage receipt belongs to different evidence/model/instructions")
        if receipt.get("status") != "completed" or not response_path.exists():
            raise ValueError("Previous stage failed; inspect it and prepare a new run, do not replay silently")
        response = _read(response_path)
        if digest(response) != receipt.get("response_sha256"):
            raise ValueError("Saved model response changed after its receipt")
        return response
    marker = folder / (stage + "-started.json")
    if marker.exists():
        raise ValueError("Prior stage outcome is uncertain; inspect it before preparing another run")
    started = time.monotonic()
    task_id = payload["task_id"] if "task_id" in payload else payload["evidence_packet"]["task_id"]
    receipt = {"task_id": task_id,
               "stage": stage, "model": model, "request_sha256": request_hash,
               "started_at": datetime.now(timezone.utc).isoformat(), "application_enabled": False}
    _write(marker, receipt)
    _write(folder / (stage + "-request.json"), request)
    env = os.environ.copy()
    env.pop("OPENCODE_CONFIG", None)
    env.update({"OPENCODE_DISABLE_PROJECT_CONFIG": "1", "OPENCODE_DISABLE_EXTERNAL_SKILLS": "1",
                "OPENCODE_DISABLE_CLAUDE_CODE_SKILLS": "1", "OPENCODE_PURE": "1",
                "OPENCODE_CONFIG_CONTENT": json.dumps({
                    "mcp": {"mac-mcp": {"enabled": False}}, "share": "disabled",
                    "agent": {"batch-packet": {"mode": "primary", "model": model, "steps": 2,
                        "permission": {"*": "deny"}, "prompt": prompt,
                        "description": "Tool-free documentary extraction or review; proposals only."}}})})
    try:
        # An isolated directory prevents accidental injection of the checkout's
        # enormous ambient instructions. Authentication remains the normal
        # OpenCode subscription/provider route, not a new paid API client.
        with tempfile.TemporaryDirectory(prefix="research-batch-") as execution:
            attachment = Path(execution) / "evidence.json"
            _write(attachment, payload)
            binary = shutil.which("opencode")
            if not binary:
                raise ValueError("OpenCode CLI is not available")
            command = [binary, "run", "Process the attached packet using your exact JSON contract. No tools or writes.",
                       "--agent", "batch-packet", "--file", str(attachment), "--format", "json",
                       "--title", f"research-batch:{receipt['task_id']}:{stage}:{model}"]
            code, stdout, stderr = (runner or _opencode)(command, cwd=execution, env=env, timeout=timeout)
        atomic_write_text(folder / (stage + "-events.jsonl"), stdout)
        atomic_write_text(folder / (stage + "-stderr.log"), stderr)
        events = _events(stdout)
        receipt.update(returncode=code, session_ids=sorted({e["sessionID"] for e in events if e.get("sessionID")}),
                       step_metrics=[e.get("part", {}) for e in events if e.get("type") == "step_finish"])
        if code != 0 or any(e.get("type") in {"error", "tool_use"} for e in events):
            raise ValueError("Model execution failed or attempted tools; inspect the event log")
        text = "\n".join(e.get("part", {}).get("text", "") for e in events if e.get("type") == "text")
        response = parse_json(text)
        if not isinstance(response, dict) or response.get("task_id") != receipt["task_id"]:
            raise ValueError("Response is not a task-matching JSON object")
        _write(response_path, response)
        receipt.update(status="completed", response_sha256=digest(response))
    except Exception as error:
        receipt.update(status="failed", error=type(error).__name__ + ": " + str(error))
        raise
    finally:
        receipt["wall_seconds"] = round(time.monotonic() - started, 3)
        _write(receipt_path, receipt)
    return response


def extract(folder, *, runner=None, timeout=180):
    folder, manifest, packet = _state(folder)
    with _lock(folder):
        preconditions = check_preconditions(packet)
        if not preconditions["passed"]:
            result = {"status": "blocked_preconditions", "preconditions": preconditions, "application_enabled": False}
            _write(folder / "field-checks.json", result)
            return result
        response = _call(folder, "extract", manifest["extraction_model"], packet,
                         EXTRACTION_PROMPT, timeout=timeout, runner=runner)
        try:
            checks = validate_extraction(packet, response)
        except ValueError as error:
            _write(folder / "field-checks.json", {"status": "blocked_protocol", "error": str(error),
                                                "application_enabled": False})
            raise
        _write(folder / "field-checks.json", checks)
        return checks


def review(folder, *, runner=None, timeout=180):
    folder, manifest, packet = _state(folder)
    with _lock(folder):
        if not check_preconditions(packet)["passed"]:
            raise ValueError("Frozen integrity preconditions failed; review cannot override them")
        extraction = _read(folder / "extract-response.json")
        receipt = _read(folder / "extract-receipt.json")
        expected = digest({"model": manifest["extraction_model"], "agent": "batch-packet",
                           "prompt": EXTRACTION_PROMPT, "payload": packet})
        if (receipt.get("status") != "completed" or receipt.get("response_sha256") != digest(extraction)
                or receipt.get("request_sha256") != expected):
            raise ValueError("Extraction receipt does not match this run")
        checks = validate_extraction(packet, extraction)
        payload = {"evidence_packet": packet, "extraction": extraction, "field_checks": checks}
        response = _call(folder, "review", manifest["review_model"], payload,
                         REVIEW_PROMPT, timeout=timeout, runner=runner)
        proposal = review_proposal(packet, extraction, response)
        _write(folder / "proposal.json", proposal)
        return proposal


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare", help="freeze a bounded curated packet; no model call")
    prep.add_argument("packet", type=Path)
    prep.add_argument("--output", type=Path, required=True)
    prep.add_argument("--route", choices=ROUTES, default="deepseek")
    for stage in ("extract", "review", "status", "apply"):
        child = sub.add_parser(stage)
        child.add_argument("run", type=Path)
        if stage in {"extract", "review"}:
            child.add_argument("--timeout", type=int, default=180, choices=range(1, 301), metavar="1..300")
    batch = sub.add_parser("batch", help="execute prepared runs; model calls, no application")
    batch.add_argument("runs", type=Path, nargs="+")
    batch.add_argument("--workers", type=int, choices=(1, 2), default=2)
    batch.add_argument("--review", action="store_true", help="also spend a SOL review call per run")
    args = parser.parse_args(argv)
    try:
        if args.command == "apply":
            raise ValueError("Database application is disabled; these are source-scoped proposals only")
        if args.command == "prepare":
            result = prepare(args.packet, args.output, route=args.route)
        elif args.command in {"extract", "review"}:
            result = globals()[args.command](args.run, timeout=args.timeout)
        elif args.command == "batch":
            runs = [_safe_output(path) for path in args.runs]
            if len(runs) != len(set(runs)):
                raise ValueError("Duplicate run directories would repeat work")
            cancelled = Event()
            runner = partial(_opencode, cancelled=cancelled)

            def execute(path):
                result = extract(path, runner=runner)
                if args.review and not cancelled.is_set() and result.get("status") != "blocked_preconditions":
                    return review(path, runner=runner)
                return result

            with ThreadPoolExecutor(max_workers=args.workers) as workers:
                try:
                    result = list(workers.map(execute, runs))
                except KeyboardInterrupt:
                    # The main thread receives Ctrl-C. Signal active subprocesses
                    # before the executor waits for worker cleanup.
                    cancelled.set()
                    raise
        else:
            folder, manifest, _ = _state(args.run)
            result = {"manifest": manifest, "stages": {
                stage: _read(folder / (stage + "-receipt.json")) if (folder / (stage + "-receipt.json")).exists() else None
                for stage in ("extract", "review")},
                "field_checks": _read(folder / "field-checks.json") if (folder / "field-checks.json").exists() else None,
                "proposal_status": _read(folder / "proposal.json").get("status") if (folder / "proposal.json").exists() else None,
                "application_enabled": False}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        results = result if isinstance(result, list) else [result]
        return 2 if any(row.get("status", "").startswith("blocked_") for row in results) else 0
    except KeyboardInterrupt:
        print("Research batch interrupted", file=sys.stderr)
        return 130
    except (ValueError, OSError, subprocess.TimeoutExpired) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
