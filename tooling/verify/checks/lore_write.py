"""G1 check for TICKET-0098 -- the lore writing path.

The lot adds its modules brief by brief; this check grows with it. Each
brief adds its files to `_LORE_WRITE_FILES` and its rules below in the same
commit (the `knowledge_identity.py` K3 census precedent, TICKET-0097).

L0 -- census. The files of the lore writing path that exist under
   `src/world_engine` (the glob `_CENSUS_GLOBS`) equal `_LORE_WRITE_FILES`
   exactly: a new module is red until a brief names it, a named module that
   is missing is red.
W1 -- schema (BRIEF-0098-B, v2.11). `lore_entry` declares `world_id` (FK to
   `world`) and the index `idx_lore_entry_world (world_id, created_at)`;
   `lore_entry_row` declares `entry_id` (FK to `lore_entry`), the UNIQUE
   index `idx_lore_entry_row_entry (entry_id, row_table, row_id)`, and CHECKs
   whose literals equal `LORE_ENTRY_ROW_TABLES` and `LORE_ENTRY_ROW_ACTIONS`.
W2 -- migration `scripts/migrate_v2_11_lore_entry.py`, on a v2.10-shaped
   database (the current schema minus both tables, `schema_meta` at v2.10):
   a. at v2.09 it refuses (non-zero exit) and creates nothing;
   b. at v2.10 it creates both tables, empty, and moves `schema_meta` to
      v2.11;
   c. a second run changes nothing and exits zero.

Fresh temp-file SQLite database for any fixture rule
(`WORLD_ENGINE_DATABASE_URL` set before any world_engine import) -- never
Nia's DB.
"""
from __future__ import annotations

import os
import pathlib
import re
import sqlite3
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src" / "world_engine"
MIGRATION = ROOT / "scripts" / "migrate_v2_11_lore_entry.py"

FAILURES: list[str] = []

_CENSUS_GLOBS = ("lore_write*.py", "writes/lore_entries.py", "cockpit/routes/lore_write*.py")
_LORE_WRITE_FILES: frozenset[str] = frozenset()


def fail(msg: str) -> None:
    FAILURES.append(msg)


def check_l0() -> None:
    found = {
        path.relative_to(SRC).as_posix()
        for pattern in _CENSUS_GLOBS for path in SRC.glob(pattern)
    }
    for extra in sorted(found - _LORE_WRITE_FILES):
        fail(f"L0: {extra} exists but no brief named it in _LORE_WRITE_FILES")
    for missing in sorted(_LORE_WRITE_FILES - found):
        fail(f"L0: {missing} is named in _LORE_WRITE_FILES but does not exist")


def _check_literals(table, name: str, expected: tuple[str, ...]) -> None:
    sql = next((str(c.sqltext) for c in table.constraints if getattr(c, "name", None) == name), None)
    if sql is None:
        fail(f"W1: {table.name} has no CHECK {name}")
        return
    got = tuple(re.findall(r"'([a-z_]+)'", sql))
    if got != expected:
        fail(f"W1: {name} lists {got}, expected {expected}")


def _index(table, name: str):
    return next((i for i in table.indexes if i.name == name), None)


def check_w1() -> None:
    from world_engine.models import LoreEntry, LoreEntryRow
    from world_engine.models.pipeline import LORE_ENTRY_ROW_ACTIONS, LORE_ENTRY_ROW_TABLES

    entry, row = LoreEntry.__table__, LoreEntryRow.__table__
    if {fk.target_fullname for fk in entry.c.world_id.foreign_keys} != {"world.id"}:
        fail("W1: lore_entry.world_id is not a FK to world.id")
    idx = _index(entry, "idx_lore_entry_world")
    if idx is None or [c.name for c in idx.columns] != ["world_id", "created_at"]:
        fail("W1: idx_lore_entry_world is not (world_id, created_at)")
    if {fk.target_fullname for fk in row.c.entry_id.foreign_keys} != {"lore_entry.id"}:
        fail("W1: lore_entry_row.entry_id is not a FK to lore_entry.id")
    idx = _index(row, "idx_lore_entry_row_entry")
    if idx is None or not idx.unique or [c.name for c in idx.columns] != ["entry_id", "row_table", "row_id"]:
        fail("W1: idx_lore_entry_row_entry is not UNIQUE (entry_id, row_table, row_id)")
    _check_literals(row, "ck_lore_entry_row_table", LORE_ENTRY_ROW_TABLES)
    _check_literals(row, "ck_lore_entry_row_action", LORE_ENTRY_ROW_ACTIONS)


def _run_migration(db_path: str) -> subprocess.CompletedProcess:
    env = dict(os.environ, WORLD_ENGINE_DATABASE_URL=f"sqlite:///{db_path}", WORLD_ENGINE_ENV="test")
    return subprocess.run([sys.executable, str(MIGRATION)], env=env, capture_output=True,
                          text=True, cwd=str(ROOT), timeout=120)


def _tables(db_path: str) -> set[str]:
    with sqlite3.connect(db_path) as conn:
        return {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def _set_version(db_path: str, version: str) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute("DROP TABLE IF EXISTS lore_entry_row")
        conn.execute("DROP TABLE IF EXISTS lore_entry")
        conn.execute("UPDATE schema_meta SET static_version = ? WHERE id = 1", (version,))


def check_w2(db_path: str) -> None:
    from sqlmodel import Session

    from world_engine.db import create_db_and_tables, engine
    from world_engine.models import SchemaMeta

    create_db_and_tables()
    with Session(engine) as session:
        if session.get(SchemaMeta, 1) is None:
            session.add(SchemaMeta(id=1, static_version="v2.10"))
            session.commit()
    engine.dispose()
    _set_version(db_path, "v2.09")
    result = _run_migration(db_path)
    if result.returncode == 0 or {"lore_entry", "lore_entry_row"} & _tables(db_path):
        fail(f"W2a: v2.09 was not refused (exit {result.returncode})")
    _set_version(db_path, "v2.10")
    result = _run_migration(db_path)
    with sqlite3.connect(db_path) as conn:
        version = conn.execute("SELECT static_version FROM schema_meta WHERE id = 1").fetchone()[0]
        counts = [conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                  for t in ("lore_entry", "lore_entry_row")] if result.returncode == 0 else None
    if result.returncode != 0 or counts != [0, 0] or version != "v2.11":
        fail(f"W2b: first run exit {result.returncode}, counts {counts}, version {version!r}: "
             f"{result.stderr.strip()[-200:]}")
    again = _run_migration(db_path)
    if again.returncode != 0 or "nothing to do" not in again.stdout:
        fail(f"W2c: second run exit {again.returncode}: {again.stdout.strip()[-200:]}")


def main() -> int:
    tmp = tempfile.mkdtemp(prefix="lore_write_")
    db_path = f"{tmp}/w.db"
    os.environ["WORLD_ENGINE_DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ.setdefault("WORLD_ENGINE_ENV", "test")
    sys.path.insert(0, str(ROOT / "src"))
    check_l0()
    check_w1()
    check_w2(db_path)
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print(f"PASS: lore_write -- census of {len(_LORE_WRITE_FILES)} module(s) holds; "
          "v2.11 declares the source record and migrates from v2.10 only")
    return 0


if __name__ == "__main__":
    sys.exit(main())
