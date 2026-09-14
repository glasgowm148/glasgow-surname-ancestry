"""Ensure an upload tar contains the verified HTML, JSON and stylesheet."""
import hashlib
import json
from pathlib import Path
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[1]


def verify(path):
    with tarfile.open(path, "r:gz") as archive:
        members = {member.name.removeprefix("./"): member for member in archive.getmembers()}
        assert not any(name.endswith(".tar.gz") for name in members), "Nested upload archive"
        manifest = json.load(archive.extractfile(members["dossier-release.json"]))
        expected = {**manifest["files"], **manifest.get("additional_files", {})}
        files = list(dict.fromkeys([*expected, *[name.replace(".html", ".json") for name in manifest["files"]], "assets/repair/person-hierarchy.css", "dossier-release.json"]))
        for name in files:
            packed = archive.extractfile(members[name]).read()
            local = (ROOT / "www" / name).read_bytes()
            assert packed == local, f"Packed file differs from verified build: {name}"
            if name in expected:
                assert hashlib.sha256(packed).hexdigest() == expected[name], name
        print(f"Verified {len(files)} release files byte-for-byte; no nested tar archives.")
    with open(path, "rb") as handle:
        checksum = hashlib.file_digest(handle, "sha256").hexdigest()
    print(checksum, path)


if __name__ == "__main__":
    verify(Path(sys.argv[1]))
