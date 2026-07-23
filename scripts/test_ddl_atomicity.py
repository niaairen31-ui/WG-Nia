"""Engine-level proof that DDL is transactional on SQLite (BRIEF-0044-f).

Against a scratch DB (never the real world-engine database):

- open a transaction, CREATE TABLE, then fail before commit — the table
  must NOT exist afterwards (rollback took the DDL with it);
- open a transaction, CREATE TABLE, commit — the table MUST exist.

This is the engine-level proof only. The higher-level proof (3-write
atomicity through create_entity_type) is BRIEF-0044-c's own test, not this
one.

No model call.

    python scripts/test_ddl_atomicity.py
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

_SCRATCH_DB = Path(tempfile.gettempdir()) / "world_engine_ddl_atomicity_scratch.db"
if _SCRATCH_DB.exists():
    _SCRATCH_DB.unlink()
os.environ["WORLD_ENGINE_DATABASE_URL"] = f"sqlite:///{_SCRATCH_DB}"

from sqlalchemy import text  # noqa: E402

from world_engine.db import engine  # noqa: E402


def _table_exists(name: str) -> bool:
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name=:n"),
            {"n": name},
        ).fetchone()
        return row is not None


def main() -> None:
    results: list[tuple[bool, str]] = []

    # 1. Rollback case: CREATE TABLE before a forced failure must not persist.
    try:
        with engine.begin() as conn:
            conn.exec_driver_sql("CREATE TABLE ext_attest (id TEXT PRIMARY KEY)")
            raise RuntimeError("forced failure before commit")
    except RuntimeError:
        pass

    results.append(
        (
            not _table_exists("ext_attest"),
            "CREATE TABLE rolled back with the failed transaction",
        )
    )

    # 2. Commit case: CREATE TABLE inside a committed transaction must persist.
    with engine.begin() as conn:
        conn.exec_driver_sql("CREATE TABLE ext_attest (id TEXT PRIMARY KEY)")

    results.append(
        (
            _table_exists("ext_attest"),
            "CREATE TABLE persisted after commit",
        )
    )

    # 3. FK enforcement still active on a fresh connection.
    with engine.connect() as conn:
        fk_on = conn.exec_driver_sql("PRAGMA foreign_keys").scalar() == 1
    results.append((fk_on, "PRAGMA foreign_keys=ON still active"))

    for ok, label in results:
        print(f"  [{'PASS' if ok else 'FAIL'}] {label}")

    passed = sum(1 for ok, _ in results if ok)
    print(f"\n{passed}/{len(results)} checks passed.")

    engine.dispose()
    if _SCRATCH_DB.exists():
        _SCRATCH_DB.unlink()

    if passed != len(results):
        sys.exit(1)


if __name__ == "__main__":
    main()
