#!/usr/bin/env python3
"""Package or deploy the public www/ site with rsync over SSH."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import io
import json
import os
import shlex
import subprocess
import sys
import tarfile
from pathlib import Path


EXCLUDE_PATTERNS = (
    "glasgow-site-*.tar.gz", ".DS_Store", "._*", ".env", ".env.*",
    "*.py", "*.pyc", "*.pyo", "*.pem", "*.key", "*.p12", "*.pfx",
    "__pycache__/",
)
PRIVATE_DIR_NAMES = {
    "private", "private-research", "secrets", "raw", "source", "__pycache__",
}
PRIVATE_SUFFIXES = {".py", ".pyc", ".pyo", ".pem", ".key", ".p12", ".pfx"}


def prepare_release(site_root: Path, write: bool = True) -> None:
    """Stamp asset versions with content hashes before anything is packaged or uploaded.

    Page builders and tests can reset ``?v=`` values, so every release refreshes
    them here and refuses to continue if any reference is still stale.
    """
    tools = Path(__file__).parent
    sys.path.insert(0, str(tools))
    from stamp_asset_versions import stamp
    from finalize_site import finalize
    if write: finalize(site_root)

    if write:
        # Scripts that load other versioned assets change hash when stamped,
        # so repeat until references settle.
        for _ in range(4):
            changed, references = stamp(site_root, write=True)
            print(f"asset versions: updated {changed} files, {references} references")
            if not references:
                break
    # Refuse to release pages that disagree on totals or link to missing dossiers.
    for check in (["check_release_consistency.py"], ["repair_atlas_destinations.py", "--check"], ["check_publication_boundary.py"]):
        if subprocess.run([sys.executable, str(tools / check[0]), *check[1:]]).returncode:
            raise SystemExit(f"{check[0]} failed; not releasing")
    _, stale = stamp(site_root, write=False)
    if stale:
        raise SystemExit(f"asset versions: {stale} stale references remain; not releasing")


def is_excluded(relative: Path) -> bool:
    return (
        any(part in PRIVATE_DIR_NAMES for part in relative.parts)
        or relative.name == ".DS_Store"
        or relative.name.startswith("._")
        or relative.name == ".env"
        or relative.name.startswith(".env.")
        or relative.suffix.casefold() in PRIVATE_SUFFIXES
        or relative.match("glasgow-site-*.tar.gz")
    )


def validate_release_tree(site_root: Path) -> None:
    """Reject links that would point a static release outside its source tree."""
    root = site_root.resolve()
    for path in site_root.rglob("*"):
        if not path.is_symlink():
            continue
        try:
            path.resolve(strict=False).relative_to(root)
        except ValueError as error:
            raise ValueError(f"refusing escaped symlink in release tree: {path}") from error


def bundle_name(now: dt.datetime | None = None) -> str:
    now = now or dt.datetime.now()
    return f"glasgow-site-{now.strftime('%Y%m%d-%H%M%S')}.tar.gz"


def make_bundle(site_root: Path, now: dt.datetime | None = None) -> Path:
    """Create a verified, rootless tarball outside www before moving it in."""
    validate_release_tree(site_root)
    destination = site_root / bundle_name(now)
    temporary = site_root.parent / f".{destination.name}.tmp"
    with tarfile.open(temporary, "w:gz") as archive:
        manifest = []
        for path in sorted(site_root.rglob("*")):
            relative = path.relative_to(site_root)
            if is_excluded(relative) or relative.as_posix() == "release-manifest.json" or path.is_symlink() or not path.is_file():
                continue
            with path.open("rb") as handle:
                digest = hashlib.file_digest(handle, "sha256").hexdigest()
            manifest.append({"path": relative.as_posix(), "bytes": path.stat().st_size, "sha256": digest})
            archive.add(path, arcname=relative.as_posix(), recursive=False)
        content = (json.dumps({"schema_version": 1, "files": manifest}, separators=(",", ":")) + "\n").encode()
        info = tarfile.TarInfo("release-manifest.json")
        info.size = len(content)
        info.mode = 0o644
        archive.addfile(info, io.BytesIO(content))
    subprocess.run(["gzip", "-t", str(temporary)], check=True)
    temporary.replace(destination)
    return destination


def target_parts(target: str) -> tuple[str, str]:
    if ":" not in target:
        raise ValueError("target must be user@host:/absolute/document-root")
    host, path = target.split(":", 1)
    if not host or not path.startswith("/"):
        raise ValueError("target must be user@host:/absolute/document-root")
    return host, path.rstrip("/")


def rsync_command(site_root: Path, target: str, dry_run: bool = True) -> list[str]:
    validate_release_tree(site_root)
    # Excluded files must also disappear from the public destination. Ordinary
    # --delete protects excluded old archives/raw assets on the receiver.
    # Mac user/group IDs must not replace the serving host's ownership.
    command = ["rsync", "-az", "--no-owner", "--no-group", "--delete", "--delete-excluded", "--itemize-changes", "--safe-links"]
    if dry_run:
        command.append("--dry-run")
    for pattern in EXCLUDE_PATTERNS:
        command.extend(("--exclude", pattern))
    for directory in sorted(PRIVATE_DIR_NAMES):
        command.extend(("--exclude", f"{directory}/"))
    return [*command, f"{site_root.resolve()}/", target.rstrip("/") + "/"]


def release_target(target: str, release: str) -> str:
    host, path = target_parts(target)
    return f"{host}:{path}.releases/{release}/"


def atomic_switch_command(target: str, release: str) -> list[str]:
    host, path = target_parts(target)
    releases = f"{path}.releases"
    destination = shlex.quote(path)
    source = shlex.quote(releases + '/' + release)
    command = f"mkdir -p {shlex.quote(releases)} && test -d {source} && {{ test ! -e {destination} || test -L {destination}; }} && ln -sfn {source} {destination}"
    return ["ssh", host, command]


def rollback_command(target: str) -> list[str]:
    host, path = target_parts(target)
    releases = f"{path}.releases"
    command = (
        f"previous=$(ls -1dt {shlex.quote(releases)}/* | sed -n '2p'); "
        f"test -n \"$previous\" && test -L {shlex.quote(path)} && ln -sfn \"$previous\" {shlex.quote(path)}"
    )
    return ["ssh", host, command]


def run(command: list[str]) -> None:
    print("+", shlex.join(command))
    subprocess.run(command, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", help="user@host:/absolute/document-root")
    parser.add_argument("--execute", action="store_true", help="perform upload (default is dry-run)")
    parser.add_argument("--atomic", action="store_true", help="release directory plus symlink switch; host document root must support symlinks")
    parser.add_argument("--rollback", action="store_true", help="switch an atomic deployment back to its prior release")
    parser.add_argument("--bundle", action="store_true", help="create www/glasgow-site-YYYYMMDD-HHMMSS.tar.gz")
    parser.add_argument("--no-stamp", action="store_true", help="skip content-hash asset stamping (not recommended)")
    parser.add_argument("--base-url", default="https://glasgow.phenotype.dev", help="URL passed to smoke test after upload")
    args = parser.parse_args()
    site_root = Path(__file__).parents[1] / "www"
    if args.bundle:
        prepare_release(site_root, write=not args.no_stamp)
        archive = make_bundle(site_root)
        size = archive.stat().st_size
        print(f"bundle: {archive} ({size} bytes, {size / 1_000_000:.2f} MB, {size / 1024**2:.2f} MiB)")
        return 0
    target = args.target or os.environ.get("GLASGOW_DEPLOY_TARGET")
    if not target:
        parser.error("--target or GLASGOW_DEPLOY_TARGET is required unless using --bundle")
    try:
        target_parts(target)
    except ValueError as error:
        parser.error(str(error))
    if args.rollback:
        command = rollback_command(target)
        if args.execute:
            run(command)
            run([sys.executable, str(Path(__file__).with_name("smoke_test_site.py")), args.base_url])
        else:
            print("dry-run rollback:", shlex.join(command))
        return 0
    release = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    destination = release_target(target, release) if args.atomic else target
    command = rsync_command(site_root, destination, dry_run=not args.execute)
    if args.execute:
        prepare_release(site_root, write=not args.no_stamp)
        if args.atomic:
            host, path = target_parts(target)
            run(["ssh", host, f"mkdir -p {shlex.quote(path + '.releases')}"])
        run(command)
        if args.atomic:
            run(atomic_switch_command(target, release))
        run([sys.executable, str(Path(__file__).with_name("smoke_test_site.py")), args.base_url])
    else:
        run(command)
        if args.atomic:
            print("then:", shlex.join(atomic_switch_command(target, release)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
