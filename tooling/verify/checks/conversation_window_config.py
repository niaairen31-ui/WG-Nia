"""G1 check for TICKET-0050 (BRIEF-0050-a) — `conversation_window_config`
table shape, on the schema_0025.py / location_type_classified.py FAILURES
idiom (zero parsed criteria is never a vacuous pass).

DB-backed, self-contained fresh temp-file SQLite fixture (WORLD_ENGINE_
DATABASE_URL set BEFORE any world_engine import) — same idiom as
location_type_classified.py / spatial_door_travel.py, so this check never
touches Nia's real DB.

Assertion, against `sqlite_master` DDL text (not column-presence-only): the
table exists; `world_id`, `word_budget`, `verbatim_turns`, `summary_enabled`
columns exist; `word_budget` DEFAULT 1200; `verbatim_turns` DEFAULT 6;
`summary_enabled` DEFAULT 1; the unique index on `world_id` exists.
Vacuous-proof: an empty/missing DDL text read is itself a FAILURE, never a
silent pass.
"""
from __future__ import annotations

import os
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src"

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _report_and_exit() -> None:
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        sys.exit(1)
    print(
        "PASS: conversation_window_config — table, columns, defaults "
        "(word_budget=1200, verbatim_turns=6, summary_enabled=1) and the "
        "unique index on world_id are all present in DDL"
    )
    sys.exit(0)


def _fresh_engine():
    tmp_dir = tempfile.mkdtemp()
    db_path = pathlib.Path(tmp_dir) / "check.db"
    os.environ["WORLD_ENGINE_DATABASE_URL"] = f"sqlite:///{db_path}"
    sys.path.insert(0, str(SRC))
    for name in list(sys.modules):
        if name == "world_engine" or name.startswith("world_engine."):
            del sys.modules[name]

    from world_engine.db import create_db_and_tables, engine

    create_db_and_tables()
    return engine


def check_schema(engine) -> None:
    from sqlalchemy import inspect, text

    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    if "conversation_window_config" not in tables:
        fail("conversation_window_config table does not exist")
        return

    columns = {c["name"] for c in inspector.get_columns("conversation_window_config")}
    for col in ("id", "world_id", "word_budget", "verbatim_turns", "summary_enabled", "updated_at"):
        if col not in columns:
            fail(f"conversation_window_config missing column {col!r}")

    with engine.connect() as conn:
        table_ddl = conn.execute(text(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='conversation_window_config'"
        )).scalar()

    if not table_ddl:
        fail("vacuous-proof: could not read conversation_window_config table DDL from sqlite_master")
    else:
        if "word_budget" not in table_ddl or "1200" not in table_ddl:
            fail("word_budget DEFAULT 1200 not found in conversation_window_config DDL")
        if "verbatim_turns" not in table_ddl:
            fail("verbatim_turns column not found in conversation_window_config DDL")
        # DEFAULT 6 for verbatim_turns — checked narrowly (the literal '6'
        # alone is too common in DDL text) by scanning the column's own
        # definition line.
        verbatim_line = next(
            (line for line in table_ddl.splitlines() if "verbatim_turns" in line), ""
        )
        if "6" not in verbatim_line:
            fail(f"verbatim_turns DEFAULT 6 not found in its DDL line: {verbatim_line!r}")
        if "summary_enabled" not in table_ddl:
            fail("summary_enabled column not found in conversation_window_config DDL")
        summary_line = next(
            (line for line in table_ddl.splitlines() if "summary_enabled" in line), ""
        )
        if "1" not in summary_line:
            fail(f"summary_enabled DEFAULT 1 not found in its DDL line: {summary_line!r}")

    indexes = inspector.get_indexes("conversation_window_config")
    unique_idx = next(
        (idx for idx in indexes if idx["name"] == "idx_conversation_window_config_world"),
        None,
    )
    if unique_idx is None:
        fail("idx_conversation_window_config_world index not found")
    else:
        if not unique_idx["unique"]:
            fail("idx_conversation_window_config_world is not a UNIQUE index")
        if unique_idx["column_names"] != ["world_id"]:
            fail(
                "idx_conversation_window_config_world does not cover exactly "
                f"(world_id): got {unique_idx['column_names']!r}"
            )


def check_missing_table_fails() -> None:
    """Vacuous-proof, negative direction: a DB missing the table must FAIL,
    never silently pass — proves the check is wired to real DDL, not a
    hardcoded green."""
    tmp_dir = tempfile.mkdtemp()
    db_path = pathlib.Path(tmp_dir) / "empty.db"
    os.environ["WORLD_ENGINE_DATABASE_URL"] = f"sqlite:///{db_path}"
    for name in list(sys.modules):
        if name == "world_engine" or name.startswith("world_engine."):
            del sys.modules[name]

    from sqlalchemy import create_engine

    empty_engine = create_engine(f"sqlite:///{db_path}")

    local_failures: list[str] = []
    real_failures = FAILURES[:]
    FAILURES.clear()
    check_schema(empty_engine)
    local_failures = FAILURES[:]
    FAILURES.clear()
    FAILURES.extend(real_failures)

    if not local_failures:
        fail("vacuous-proof: a DB missing conversation_window_config passed the check")


def main() -> None:
    engine = _fresh_engine()
    check_schema(engine)
    check_missing_table_fails()
    _report_and_exit()


if __name__ == "__main__":
    main()
