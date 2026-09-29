#!/usr/bin/env python3
"""Restore and verify explicitly approved historical transcription assets."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "www"
PRIVATE = ROOT / "data" / "private" / "withheld-public-assets"
APPROVALS = ROOT / "research" / "transcriptions" / "public-preview-approvals.json"
APPROVED_DIRECTORIES = (
    Path("assets/research/testament-crops"),
    Path("assets/research/testament-originals"),
    Path("assets/research/record-excerpts"),
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _relative_url(url: str) -> Path | None:
    if not isinstance(url, str) or not url.startswith("/") or "?" in url or "#" in url:
        return None
    relative = Path(url[1:])
    if relative.is_absolute() or ".." in relative.parts or relative.as_posix() != url[1:]:
        return None
    if not any(relative.is_relative_to(directory) for directory in APPROVED_DIRECTORIES):
        return None
    return relative


def approvals(manifest: Path = APPROVALS) -> dict[str, str]:
    """Return exact approved URL-to-digest mappings from the maintained manifest."""
    data = json.loads(manifest.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1 or not isinstance(data.get("approved_assets"), list):
        raise ValueError("invalid public manuscript preview approval manifest")
    result: dict[str, str] = {}
    for asset in data["approved_assets"]:
        if not isinstance(asset, dict):
            raise ValueError("invalid public manuscript preview approval entry")
        url, sha256 = asset.get("url"), asset.get("sha256")
        if _relative_url(url) is None or not isinstance(sha256, str) or len(sha256) != 64:
            raise ValueError("invalid public manuscript preview approval entry")
        if url in result or any(character not in "0123456789abcdef" for character in sha256):
            raise ValueError("duplicate or invalid public manuscript preview approval entry")
        result[url] = sha256
    return result


def approved_preview(
    url: str, web: Path = WEB, private: Path = PRIVATE, manifest: Path = APPROVALS
) -> bool:
    """Whether an exact public asset is approved and matches its private original."""
    relative = _relative_url(url)
    if relative is None:
        return False
    approved = approvals(manifest).get(url)
    public, source = web / relative, private / relative
    return bool(approved and public.is_file() and source.is_file()
                and digest(public) == approved == digest(source))


approved_transcription_asset = approved_preview


def restore_approved_previews(
    web: Path = WEB, private: Path = PRIVATE, manifest: Path = APPROVALS
) -> int:
    """Copy only hash-approved historical transcription material to the public site."""
    restored = 0
    for url, approved in approvals(manifest).items():
        relative = _relative_url(url)
        assert relative is not None
        source, destination = private / relative, web / relative
        if not source.is_file():
            continue
        if digest(source) != approved:
            raise ValueError(f"approved private asset differs from manifest: {relative}")
        if destination.is_file() and digest(destination) == approved:
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        restored += 1
    return restored


def audit_approved_previews(
    web: Path = WEB, private: Path = PRIVATE, manifest: Path = APPROVALS
) -> list[str]:
    """Reject public transcription assets that lack approval or hash verification."""
    approved = approvals(manifest)
    failures: list[str] = []
    for directory in APPROVED_DIRECTORIES:
        public_directory = web / directory
        if not public_directory.exists():
            continue
        for path in sorted(public_directory.rglob("*")):
            if not path.is_file():
                continue
            url = "/" + path.relative_to(web).as_posix()
            expected = approved.get(url)
            private_path = private / path.relative_to(web)
            if expected is None:
                failures.append(f"Unapproved historical transcription asset remains: {path.relative_to(web)}")
            elif not private_path.is_file() or digest(path) != expected or digest(private_path) != expected:
                failures.append(f"Tampered historical transcription asset remains: {path.relative_to(web)}")
    return failures
