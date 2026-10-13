"""Migration v2.28 — a quest request is a row (TICKET-0121, BRIEF-0121-B;
decision L1 of the Journée quest designer).

Schema, additive only; no data is written:

- creates `quest_request` (one row per agenda step the creator is asked to
  design a quest for: its trigger, declaration, status, the existence
  answer, and the rows it led to) with its three CHECKs and its two
  indexes, exactly as the model declares them.

Refuses to run on a database whose `schema_meta.static_version` is older
than v2.27. Idempotent: the table is checked before it is created. One raw
transaction (`foreign_keys` set before it).

Post-check, before `schema_meta` moves: the table exists, with its CHECKs
and indexes; `PRAGMA foreign_key_check(quest_request)` is empty (a dangling
row elsewhere is a note, never a failure -- AMENDMENT-0107-01).
`schema_meta` then moves to v2.28.

Run from the project root:

    python scripts/migrate_v2_28_quest_requests.py
"""

from __future__ import annotations

import os
import sys
from datetime import UTC, datetime
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

_env = os.environ.get("WORLD_ENGINE_ENV")
if not _env and not os.environ.get("WORLD_ENGINE_DATABASE_URL"):
    print(
        "migrate_v2_28_quest_requests.py refuses to run without WORLD_ENGINE_ENV "
        "or WORLD_ENGINE_DATABASE_URL set (fail-closed, TICKET-0049) — got: "
        f"{_env or 'unset'}.",
        file=sys.stderr,
    )
    sys.exit(1)

from sqlalchemy import inspect, text  # noqa: E402
from sqlalchemy.schema import CreateIndex, CreateTable  # noqa: E402
from sqlmodel import Session  # noqa: E402

from world_engine import models  # noqa: E402
from world_engine.db import engine  # noqa: E402

_PREVIOUS_VERSION = "v2.27"
_THIS_VERSION = "v2.28"
_TABLE = "quest_request"
_CHECKS = ("ck_quest_request_trigger", "ck_quest_request_status", "ck_quest_request_answer")
_INDEXES = ("idx_quest_request_world", "idx_quest_request_step")


def _version_key(version: str) -> tuple[int, int]:
    major, minor = version.lstrip("v").split(".")
    return int(major), int(minor)


def _refuse() -> None:
    with engine.connect() as conn:
        row = conn.execute(text("SELECT static_version FROM schema_meta WHERE id = 1")).first()
    if row is None or _version_key(row[0]) < _version_key(_PREVIOUS_VERSION):
        found = row[0] if row is not None else "no schema_meta row"
        raise SystemExit(
            f"Migration v2.28 refused: the database is at {found!r}; run the migrations "
            f"up to {_PREVIOUS_VERSION} first."
        )


def _apply() -> list[str]:
    """One raw transaction (`migrate_v1_95_parked_plans.py`'s docstring: the
    PRAGMAs must land before any transaction exists)."""
    applied: list[str] = []
    existing = set(inspect(engine).get_table_names())
    raw = engine.raw_connection()
    try:
        cursor = raw.cursor()
        cursor.execute("PRAGMA foreign_keys=OFF")
        cursor.execute("BEGIN")
        table = models.QuestRequest.__table__
        if _TABLE not in existing:
            cursor.execute(str(CreateTable(table).compile(dialect=engine.dialect)))
            applied.append(f"{_TABLE} created")
        have = {i["name"] for i in inspect(engine).get_indexes(_TABLE)} if _TABLE in existing else set()
        for index in table.indexes:
            if index.name not in have:
                cursor.execute(str(CreateIndex(index).compile(dialect=engine.dialect)))
                applied.append(f"{index.name} created")
        cursor.execute("COMMIT")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    except Exception:
        raw.rollback()
        raise
    finally:
        raw.close()
    return applied


def _post_checks() -> None:
    problems = []
    if _TABLE not in set(inspect(engine).get_table_names()):
        raise SystemExit(f"Migration v2.28 aborted, post-check failed: {_TABLE} was not created.")
    with engine.connect() as conn:
        ddl = conn.execute(text("SELECT sql FROM sqlite_master WHERE type='table' AND name=:n"),
                           {"n": _TABLE}).scalar_one()
        dangling = conn.execute(text(f"PRAGMA foreign_key_check({_TABLE})")).fetchall()
        elsewhere = [row for row in conn.execute(text("PRAGMA foreign_key_check")).fetchall()
                     if row[0] != _TABLE]
    for name in _CHECKS:
        if name not in ddl:
            problems.append(f"CHECK {name} is missing")
    have = {i["name"] for i in inspect(engine).get_indexes(_TABLE)}
    for name in _INDEXES:
        if name not in have:
            problems.append(f"index {name} is missing")
    if dangling:
        problems.append(f"foreign_key_check {dangling}")
    if problems:
        raise SystemExit("Migration v2.28 aborted, post-check failed: " + "; ".join(problems) + ".")
    for table, rowid, parent, _fk in elsewhere:
        print(f"  Note: {table} rowid {rowid} points to a missing {parent} row (not written by this migration).")
    print(f"Post-check: {_TABLE} in place with its CHECKs and indexes; foreign_key_check empty.")


def _converge_schema_meta() -> None:
    with Session(engine) as session:
        row = session.get(models.SchemaMeta, 1)
        if row is None:
            session.add(models.SchemaMeta(id=1, static_version=_THIS_VERSION))
            print(f"Row: seeded schema_meta.id=1 at {_THIS_VERSION!r}")
        elif _version_key(row.static_version) < _version_key(_THIS_VERSION):
            previous = row.static_version
            row.static_version = _THIS_VERSION
            row.updated_at = datetime.now(UTC)
            session.add(row)
            print(f"Row: updated schema_meta.id=1: {previous!r} -> {_THIS_VERSION!r}")
        else:
            print(f"Row: schema_meta.id=1 already at {row.static_version!r} — nothing to do")
        session.commit()


def main() -> None:
    print("Migration v2.28 — a quest request is a row")
    _refuse()
    applied = _apply()
    print("Applied: " + ", ".join(applied) + "." if applied else "Migration v2.28 already fully applied.")
    _post_checks()
    _converge_schema_meta()
    print("\nMigration v2.28 applied.")


if __name__ == "__main__":
    main()
