"""Timestamped, rotated backup of the live world-engine database.

Run this BEFORE every play / seed / migration session. It:
  - backs up the exact file the app and every script use (resolved from the
    shared engine, never a stray copy);
  - writes the backup OUTSIDE the git working tree, so `git clean -fdx` or an
    IDE "clean workspace" cannot take the backups along with the .db;
  - keeps the 2 most recent backups and prunes the rest;
  - uses SQLite's online backup API (a consistent snapshot, WAL-safe, even if
    the database is open);
  - refuses to back up a missing or empty file, and prints what it is backing
    up (entity / location counts) so a hollow seed-only DB is caught on sight.

Usage:
    python scripts/backup.py
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from pathlib import Path

# Import the SAME engine the app and every script use, so we always back up the
# file actually in play. IMPORTANT: match this import to how seed_pilot.py
# imports `engine` (e.g. `from world_engine.db import engine`); adjust if the
# package path differs.
from world_engine.db import engine

# How many recent backups to retain.
KEEP = 2

# Where backups live. MUST be outside the git working tree. Defaults to the same
# out-of-tree home directory recommended for the database itself, so data and
# its backups sit together, away from anything `git clean` touches. Override
# with WORLD_ENGINE_BACKUP_DIR.
DEFAULT_BACKUP_DIR = Path.home() / ".world_engine" / "backups"
BACKUP_DIR = Path(os.environ.get("WORLD_ENGINE_BACKUP_DIR", str(DEFAULT_BACKUP_DIR)))


def _sqlite_path_from_engine() -> Path:
    """The absolute path of the SQLite file the engine is bound to."""
    url = engine.url
    if url.get_backend_name() != "sqlite":
        raise SystemExit(f"Refusing to back up a non-sqlite database: {url}")
    if not url.database or url.database == ":memory:":
        raise SystemExit("Engine has no on-disk database file (in-memory?). Aborting.")
    return Path(url.database).resolve()


def _sanity_counts(src: Path) -> tuple[int, int]:
    """Read-only peek so a hollow / wrong DB is obvious before we trust it."""
    with sqlite3.connect(f"file:{src}?mode=ro", uri=True) as ro:
        entities = ro.execute("SELECT count(*) FROM entity").fetchone()[0]
        locations = ro.execute(
            "SELECT count(*) FROM entity WHERE type='location'"
        ).fetchone()[0]
    return entities, locations


def main() -> None:
    src = _sqlite_path_from_engine()
    if not src.exists():
        raise SystemExit(
            f"Database file does not exist: {src}\n"
            "Refusing to write an empty backup. Is the path right / the world seeded?"
        )

    entities, locations = _sanity_counts(src)
    print(f"Backing up: {src}")
    print(f"  entities={entities}  locations={locations}")
    if entities == 0:
        raise SystemExit("Database has zero entities — refusing to back up an empty world.")

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = BACKUP_DIR / f"world_engine_{stamp}.db"
    tmp = dest.parent / (dest.name + ".tmp")

    if tmp.exists():
        tmp.unlink()

    # Online backup into a temp file, then atomic rename, so a crash mid-copy
    # never leaves a half-written backup that rotation might keep. Connections
    # are closed explicitly (not just via `with`) because on Windows the file
    # handle must be released before os.replace can rename it.
    source = sqlite3.connect(src)
    target = sqlite3.connect(tmp)
    try:
        source.backup(target)
    finally:
        source.close()
        target.close()

    try:
        os.replace(tmp, dest)
    except OSError:
        if tmp.exists():
            tmp.unlink()
        raise
    print(f"Wrote backup: {dest}")

    # Rotation: keep the KEEP most recent, prune older ones.
    backups = sorted(
        BACKUP_DIR.glob("world_engine_*.db"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for old in backups[KEEP:]:
        old.unlink()
        print(f"Pruned old backup: {old}")


if __name__ == "__main__":
    main()
