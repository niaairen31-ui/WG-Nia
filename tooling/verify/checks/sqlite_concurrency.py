"""G1 check: SQLite concurrency posture (TICKET-0072, BRIEF-0072-a).

BRIEF-0044-f made every transaction explicit on `db.py`'s connect listener
(`isolation_level = None` plus an explicit `BEGIN`) so DDL could not escape a
rollback. Under the default rollback journal that also turned every SELECT
into a `SHARED` lock held for the life of its transaction -- and a request
session bound for the whole life of a `StreamingResponse` (the Play stream)
holds that lock for an entire turn, so a second `Session(engine)` opened
inside the stream can INSERT but cannot COMMIT: promotion to `EXCLUSIVE`
waits on the reader, exhausts the busy timeout, and SQLite raises "database
is locked". `db.py` now declares `_SQLITE_JOURNAL_MODE = "WAL"` and an
explicit `_SQLITE_BUSY_TIMEOUT_MS`, asserted on every connect, fail-closed on
an unexpected mode. This check proves the posture is both DECLARED and
EFFECTIVE, and that it actually closes the reader-blocks-writer gap it
exists to close -- not just that the PRAGMAs were issued.

No DB import happens until AFTER `WORLD_ENGINE_DATABASE_URL` is pointed at a
scratch file under `tempfile.gettempdir()`, exactly as
`scripts/test_ddl_atomicity.py` does -- this check can never touch the prod
or test carrier. Both scratch files (and their `-wal`/`-shm` sidecars) are
deleted at start and at end.

Four rules, each vacuous-proof (a missing constant, an unparseable file, or a
guard that finds nothing to guard is a FAILURE, never a pass):

  1. **Declared.** AST-parse `db.py` (never regex). `_SQLITE_JOURNAL_MODE`,
     `_SQLITE_BUSY_TIMEOUT_MS` and `_SQLITE_JOURNAL_MODES_OK` must exist as
     module-level literal assignments; `_SQLITE_JOURNAL_MODE.lower()` must be
     `"wal"`; `_SQLITE_BUSY_TIMEOUT_MS` must be a plain `int` greater than
     zero; and the body of `_enable_sqlite_foreign_keys` must reference both
     of the first two names.
  2. **Effective.** Open a connection from the imported engine and read
     `PRAGMA journal_mode` / `PRAGMA busy_timeout` back from the driver.
     Rule 1 proves the posture is written; this proves it arrived.
  3. **A reader does not block a writer.** Session A: INSERT, commit, then
     SELECT (reproducing `play.py:136` then `play.py:143`). Vacuity guard,
     first: assert A is genuinely inside an open transaction, both at the
     SQLAlchemy level (`A.connection().in_transaction()`) and at the driver
     level (`.connection.dbapi_connection.in_transaction`) -- if either is
     `False` the reader holds nothing and the rest of the rule proves
     nothing. Then, with A still open, session B INSERTs and commits; the
     commit must succeed in under one second (a pass that consumed the busy
     timeout won a race, it did not avoid a conflict).
  4. **The instrument can see red.** The same shape, on a second scratch file
     left in the default rollback journal, using raw `sqlite3` connections
     with `timeout=0.2` so the failure is fast and the engine's own
     configuration is untouched. The nested COMMIT must raise
     `sqlite3.OperationalError`. If it does not, this check cannot detect the
     defect TICKET-0072 exists to close, and the whole instrument is
     vacuous.

One implementation per rule: this check does not re-assert transactional DDL
(`scripts/test_ddl_atomicity.py` owns that, run unmodified alongside it) and
does not re-assert foreign-key enforcement (already covered elsewhere).
"""
from __future__ import annotations

import ast
import os
import sqlite3
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
DB_PY = SRC / "world_engine" / "db.py"

_DECLARED_NAMES = ("_SQLITE_JOURNAL_MODE", "_SQLITE_BUSY_TIMEOUT_MS", "_SQLITE_JOURNAL_MODES_OK")

SCRATCH_DB = Path(tempfile.gettempdir()) / "world_engine_concurrency_scratch.db"
SCRATCH_DB2 = Path(tempfile.gettempdir()) / "world_engine_concurrency_scratch_rollback.db"

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _report_and_exit(counts: dict | None = None) -> None:
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        sys.exit(1)
    print(
        f"PASS: sqlite_concurrency — journal_mode=wal, "
        f"busy_timeout={counts['timeout_ms']}ms declared and effective, "
        f"nested commit under an open read in {counts['commit_ms']:.1f}ms, "
        f"counterfactual red"
    )
    sys.exit(0)


def _cleanup_sidecars(db_path: Path) -> None:
    for suffix in ("", "-wal", "-shm"):
        p = Path(str(db_path) + suffix)
        if p.exists():
            p.unlink()


def _check_rule1_declared() -> dict | None:
    """AST-parse db.py. Returns {'mode': str, 'timeout': int} or None on failure."""
    if not DB_PY.is_file():
        fail(f"{DB_PY} does not exist")
        return None
    try:
        tree = ast.parse(DB_PY.read_text(encoding="utf-8"), filename=str(DB_PY))
    except SyntaxError as exc:
        fail(f"{DB_PY}: cannot parse ({exc})")
        return None

    literals: dict[str, object] = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Name) or target.id not in _DECLARED_NAMES:
            continue
        try:
            literals[target.id] = ast.literal_eval(node.value)
        except (ValueError, TypeError):
            fail(f"{DB_PY}: {target.id} is not a literal assignment")

    missing = [name for name in _DECLARED_NAMES if name not in literals]
    if missing:
        fail(f"{DB_PY}: missing module-level literal constant(s): {', '.join(missing)}")
        return None

    mode = literals["_SQLITE_JOURNAL_MODE"]
    timeout = literals["_SQLITE_BUSY_TIMEOUT_MS"]
    if not isinstance(mode, str) or mode.lower() != "wal":
        fail(f"{DB_PY}: _SQLITE_JOURNAL_MODE is {mode!r}, expected 'WAL' (case-insensitive)")
        return None
    if type(timeout) is not int or timeout <= 0:
        fail(f"{DB_PY}: _SQLITE_BUSY_TIMEOUT_MS is {timeout!r}, expected an int > 0")
        return None

    listener = None
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "_enable_sqlite_foreign_keys":
            listener = node
            break
    if listener is None:
        fail(f"{DB_PY}: no top-level function _enable_sqlite_foreign_keys")
        return None

    referenced = {n.id for n in ast.walk(listener) if isinstance(n, ast.Name)}
    unreferenced = {"_SQLITE_JOURNAL_MODE", "_SQLITE_BUSY_TIMEOUT_MS"} - referenced
    if unreferenced:
        fail(
            f"{DB_PY}: _enable_sqlite_foreign_keys does not reference {sorted(unreferenced)}"
        )
        return None

    return {"mode": mode.lower(), "timeout": timeout}


def _check_rule2_effective(engine, declared: dict) -> bool:
    with engine.connect() as conn:
        mode = conn.exec_driver_sql("PRAGMA journal_mode").scalar()
        timeout = conn.exec_driver_sql("PRAGMA busy_timeout").scalar()
    ok = True
    if str(mode).lower() != "wal":
        fail(f"PRAGMA journal_mode returned {mode!r}, expected 'wal'")
        ok = False
    if int(timeout) != declared["timeout"]:
        fail(f"PRAGMA busy_timeout returned {timeout!r}, expected {declared['timeout']}")
        ok = False
    return ok


def _check_rule3_reader_does_not_block_writer(engine) -> float | None:
    from sqlalchemy import text
    from sqlmodel import Session

    with engine.begin() as conn:
        conn.exec_driver_sql(
            "CREATE TABLE _concurrency_probe (id INTEGER PRIMARY KEY, val TEXT)"
        )

    session_a = Session(engine)
    session_b = Session(engine)
    try:
        session_a.exec(text("INSERT INTO _concurrency_probe (val) VALUES ('a')"))
        session_a.commit()
        session_a.exec(text("SELECT val FROM _concurrency_probe")).all()

        conn_a = session_a.connection()
        sa_in_tx = conn_a.in_transaction()
        driver_in_tx = conn_a.connection.dbapi_connection.in_transaction
        if not sa_in_tx or not driver_in_tx:
            fail(
                "rule3 vacuity guard: reader session A is not genuinely inside an "
                f"open transaction (SQLAlchemy in_transaction={sa_in_tx}, "
                f"driver in_transaction={driver_in_tx}) -- the rest of the rule "
                "would prove nothing"
            )
            return None

        start = time.monotonic()
        try:
            session_b.exec(text("INSERT INTO _concurrency_probe (val) VALUES ('b')"))
            session_b.commit()
        except Exception as exc:  # noqa: BLE001 -- report the driver's own message
            fail(f"rule3: nested commit under an open read failed: {exc!r}")
            return None
        elapsed = time.monotonic() - start
    finally:
        session_a.close()
        session_b.close()

    if elapsed >= 1.0:
        fail(
            f"rule3: nested commit took {elapsed:.3f}s (>= 1s budget) -- a pass "
            "here would have won a race against the busy timeout rather than "
            "avoided the conflict"
        )
        return None
    return elapsed


def _check_rule4_instrument_sees_red() -> bool:
    _cleanup_sidecars(SCRATCH_DB2)
    conn_a = sqlite3.connect(str(SCRATCH_DB2), timeout=0.2, isolation_level=None)
    conn_b = sqlite3.connect(str(SCRATCH_DB2), timeout=0.2, isolation_level=None)
    try:
        conn_a.execute("PRAGMA journal_mode=DELETE")
        conn_a.execute("CREATE TABLE _concurrency_probe (id INTEGER PRIMARY KEY, val TEXT)")
        conn_a.execute("BEGIN")
        conn_a.execute("INSERT INTO _concurrency_probe (val) VALUES ('a')")
        conn_a.execute("COMMIT")
        # Reproduce play.py:136 -> play.py:143: commit, then a read that opens
        # a fresh transaction and holds it open.
        conn_a.execute("BEGIN")
        conn_a.execute("SELECT val FROM _concurrency_probe")

        raised = False
        try:
            conn_b.execute("BEGIN")
            conn_b.execute("INSERT INTO _concurrency_probe (val) VALUES ('b')")
            conn_b.execute("COMMIT")
        except sqlite3.OperationalError:
            raised = True
    finally:
        conn_a.close()
        conn_b.close()
        _cleanup_sidecars(SCRATCH_DB2)

    if not raised:
        fail(
            "rule4: the counterfactual (rollback journal) nested COMMIT did NOT "
            "raise sqlite3.OperationalError -- this check cannot see the defect "
            "TICKET-0072 exists to close, and is vacuous"
        )
        return False
    return True


def main() -> None:
    _cleanup_sidecars(SCRATCH_DB)
    _cleanup_sidecars(SCRATCH_DB2)

    declared = _check_rule1_declared()
    if declared is None:
        _cleanup_sidecars(SCRATCH_DB)
        _cleanup_sidecars(SCRATCH_DB2)
        _report_and_exit()
        return

    if SCRATCH_DB.exists():
        SCRATCH_DB.unlink()
    os.environ["WORLD_ENGINE_DATABASE_URL"] = f"sqlite:///{SCRATCH_DB}"
    sys.path.insert(0, str(SRC))

    from world_engine.db import engine

    rule2_ok = _check_rule2_effective(engine, declared)
    rule3_elapsed = _check_rule3_reader_does_not_block_writer(engine) if rule2_ok else None
    rule4_ok = _check_rule4_instrument_sees_red()

    engine.dispose()
    _cleanup_sidecars(SCRATCH_DB)
    _cleanup_sidecars(SCRATCH_DB2)

    if FAILURES or not rule2_ok or rule3_elapsed is None or not rule4_ok:
        _report_and_exit()
        return

    _report_and_exit(
        {
            "timeout_ms": declared["timeout"],
            "commit_ms": rule3_elapsed * 1000,
        }
    )


if __name__ == "__main__":
    main()
