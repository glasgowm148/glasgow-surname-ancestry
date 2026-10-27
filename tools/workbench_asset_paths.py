"""Small, audited helpers for relocating repository research assets."""

from __future__ import annotations

from pathlib import Path


def _research_path(value: str) -> Path:
    path = Path(value)
    if (path.is_absolute() or ".." in path.parts or len(path.parts) != 2
            or path.parts[0] != "research"):
        raise ValueError(f"asset path must be a research/<case> directory: {value}")
    return path


def relocate_research_assets(project, tx, old_directory: str, new_directory: str) -> dict:
    """Move all repository asset versions from one research directory to another.

    The caller moves files first.  Old paths must be absent and destination
    files must exist; database rows are then updated with revision guards.
    """
    old = _research_path(old_directory)
    new = _research_path(new_directory)
    if old == new:
        raise ValueError("old and new research directories must differ")
    prefix = old.as_posix().rstrip("/") + "/"
    escaped = prefix.replace("%", "\\%").replace("_", "\\_")
    rows = tx.store.all("SELECT * FROM asset WHERE root='repository' AND path LIKE ? ESCAPE '\\' ORDER BY path, revision",
                        (escaped + "%",))
    if not rows:
        raise ValueError(f"no repository assets under {old_directory}")
    moved = []
    destinations = {row["path"] for row in tx.store.all("SELECT path FROM asset WHERE root='repository'")}
    moved_destinations = set()
    source_root = project.root("repository")
    for row in rows:
        old_path = Path(row["path"])
        new_path = (new / old_path.relative_to(old)).as_posix()
        if (source_root / old_path).is_file():
            raise ValueError(f"old asset path still exists: {row['path']}")
        if not (source_root / new_path).is_file():
            raise ValueError(f"destination asset path is missing: {new_path}")
        if new_path in destinations and new_path not in moved_destinations and new_path != row["path"]:
            raise ValueError(f"destination asset path already registered: {new_path}")
        moved_destinations.add(new_path)
        tx.update("asset", row["id"], {"path": new_path}, expected_revision=row["revision"])
        moved.append({"id": row["id"], "old_path": row["path"], "path": new_path,
                      "sha256": row["sha256"], "revision": row["revision"]})
    return {"moved": moved, "count": len(moved), "old_directory": old.as_posix(), "new_directory": new.as_posix()}
