"""G1 gate for the `goal_prerequisite` table's real shape.

TICKET-0025/BRIEF-0025-c relationalized `npc_goal.prerequisites` (a JSON
column) into `goal_prerequisite` (`canon.py:636-651`) — schema v1.79.
No schema check was ever written for the new table's shape; `prereq_judge.py`
covers only the `goal_change complete` judge's *behavior*, not the schema.
Added by TICKET-0043/BRIEF-0043-b to close that gap.

Builds tables from a fresh temp-file SQLite DB (WORLD_ENGINE_DATABASE_URL
set before any world_engine import) so this check never touches Nia's real
DB. Asserts column presence AND both CHECK constraints' DDL text (K1,
closed vocabulary) — a column-presence check alone would still pass if the
CHECK itself were dropped, the exact vacuous-pass failure mode this check
exists to avoid.
"""
import os
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _fresh_engine():
    tmp_dir = tempfile.mkdtemp()
    db_path = pathlib.Path(tmp_dir) / "check.db"
    os.environ["WORLD_ENGINE_DATABASE_URL"] = f"sqlite:///{db_path}"
    for name in list(sys.modules):
        if name == "world_engine" or name.startswith("world_engine."):
            del sys.modules[name]

    from world_engine.db import create_db_and_tables, engine

    create_db_and_tables()
    return engine


def check_goal_prerequisite_schema(engine) -> None:
    from sqlalchemy import inspect, text

    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    if "goal_prerequisite" not in tables:
        fail("goal_prerequisite table does not exist")
        return

    columns = {c["name"] for c in inspector.get_columns("goal_prerequisite")}
    for col in ("id", "world_id", "goal_id", "type", "target_entity_id", "threshold"):
        if col not in columns:
            fail(f"goal_prerequisite missing column {col!r}")

    with engine.connect() as conn:
        table_ddl = conn.execute(text(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='goal_prerequisite'"
        )).scalar()

    if not table_ddl:
        fail("could not read goal_prerequisite table DDL from sqlite_master")
    else:
        if "ck_goal_prerequisite_type" not in table_ddl:
            fail("ck_goal_prerequisite_type CHECK constraint not found in goal_prerequisite DDL")
        # K1 closed vocabulary: v1 accepts ONLY 'relation_gte'. A future
        # migration adding a second prerequisite type will require updating
        # this expected literal alongside the migration.
        elif "relation_gte" not in table_ddl:
            fail("ck_goal_prerequisite_type's DDL does not contain 'relation_gte'")

        if "ck_goal_prerequisite_threshold" not in table_ddl:
            fail("ck_goal_prerequisite_threshold CHECK constraint not found in goal_prerequisite DDL")
        elif "1" not in table_ddl or "100" not in table_ddl:
            fail("ck_goal_prerequisite_threshold's DDL does not contain the 1/100 bound")

    indexes = inspector.get_indexes("goal_prerequisite")
    unique_idx = next(
        (idx for idx in indexes if idx["name"] == "idx_goal_prerequisite_unique"),
        None,
    )
    if unique_idx is None:
        fail("idx_goal_prerequisite_unique index not found")
    else:
        if not unique_idx["unique"]:
            fail("idx_goal_prerequisite_unique is not a UNIQUE index")
        if unique_idx["column_names"] != ["goal_id", "type", "target_entity_id"]:
            fail(
                "idx_goal_prerequisite_unique does not cover exactly "
                f"(goal_id, type, target_entity_id): got {unique_idx['column_names']!r}"
            )


def main() -> None:
    engine = _fresh_engine()
    check_goal_prerequisite_schema(engine)

    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        sys.exit(1)

    print(
        "PASS: goal_prerequisite columns present; ck_goal_prerequisite_type "
        "and ck_goal_prerequisite_threshold CHECK constraints present with "
        "expected DDL text; idx_goal_prerequisite_unique is a UNIQUE index "
        "on (goal_id, type, target_entity_id)"
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
