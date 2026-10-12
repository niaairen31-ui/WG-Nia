"""Migration v2.26 — what an event does to the state of the world
(TICKET-0119, BRIEF-0119-A; decisions M-c, C1, D3, E1 and U1 of the
conditions series).

Schema, additive except one rebuild; no data is written:

- creates `event_type_effect` (an event type's effects: the role whose
  entity changes, the state, the value -- a choice, an integer set or
  added, or the entity of another role), exactly as the model declares it;
- adds `attribute_change.event_id` (the event that made a change, M-c) and
  its index `idx_attribute_change_event`;
- rebuilds `lore_entry_row` (its `row_table` CHECK gains `event`,
  `event_participant`, `attribute_value` and `attribute_change`: an event
  Lore declares is recorded with everything it wrote, U1), every row
  copied.

Refuses to run on a database whose `schema_meta.static_version` is older
than v2.25. Idempotent: each step checks what is already there. One raw
transaction (`foreign_keys` and `legacy_alter_table` set before it).

Post-check, before `schema_meta` moves: `lore_entry_row` and
`attribute_change` kept their row counts; the new table, column and CHECK
are in place; `PRAGMA foreign_key_check` on the tables this migration
writes is empty (a dangling row elsewhere is a note, never a failure --
AMENDMENT-0107-01). `schema_meta` then moves to v2.26.

Run from the project root:

    python scripts/migrate_v2_26_event_effects.py
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
        "migrate_v2_26_event_effects.py refuses to run without WORLD_ENGINE_ENV "
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

_PREVIOUS_VERSION = "v2.25"
_THIS_VERSION = "v2.26"
_LORE_ROW_COLUMNS = "id, entry_id, row_table, row_id, action"
_EVENT_INDEX = "idx_attribute_change_event"
# The tables this migration writes: the only ones its foreign-key post-check judges.
_TOUCHED_TABLES = ("event_type_effect", "attribute_change", "lore_entry_row")


def _version_key(version: str) -> tuple[int, int]:
    major, minor = version.lstrip("v").split(".")
    return int(major), int(minor)


def _refuse() -> None:
    with engine.connect() as conn:
        row = conn.execute(text("SELECT static_version FROM schema_meta WHERE id = 1")).first()
    if row is None or _version_key(row[0]) < _version_key(_PREVIOUS_VERSION):
        found = row[0] if row is not None else "no schema_meta row"
        raise SystemExit(
            f"Migration v2.26 refused: the database is at {found!r}; run the migrations "
            f"up to {_PREVIOUS_VERSION} first."
        )


def _table_sql(table: str) -> str:
    with engine.connect() as conn:
        row = conn.execute(text("SELECT sql FROM sqlite_master WHERE type='table' AND name=:t"), {"t": table}).first()
    return row[0] if row is not None else ""


def _columns(table: str) -> set[str]:
    return {column["name"] for column in inspect(engine).get_columns(table)}


def _indexes(table: str) -> set[str]:
    return {index["name"] for index in inspect(engine).get_indexes(table)}


def _count(conn, table: str) -> int:
    return conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one()


def _create_from_model(cursor, model) -> None:
    cursor.execute(str(CreateTable(model.__table__).compile(dialect=engine.dialect)))
    for index in model.__table__.indexes:
        cursor.execute(str(CreateIndex(index).compile(dialect=engine.dialect)))


def _rebuild(cursor, table: str, model, columns: str) -> None:
    for (index_name,) in cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name=? AND sql IS NOT NULL", (table,)
    ).fetchall():
        cursor.execute(f"DROP INDEX {index_name}")
    cursor.execute(f"ALTER TABLE {table} RENAME TO {table}_old")
    _create_from_model(cursor, model)
    cursor.execute(f"INSERT INTO {table} ({columns}) SELECT {columns} FROM {table}_old")
    cursor.execute(f"DROP TABLE {table}_old")


def _plan() -> dict:
    existing = set(inspect(engine).get_table_names())
    return {
        "effect": "event_type_effect" not in existing,
        "event_id": "event_id" not in _columns("attribute_change"),
        "event_index": _EVENT_INDEX not in _indexes("attribute_change"),
        "lore_entry_row": "'attribute_change'" not in _table_sql("lore_entry_row"),
    }


def _apply(plan: dict) -> list[str]:
    """One raw transaction (`migrate_v1_95_parked_plans.py`'s docstring: the
    PRAGMAs must land before any transaction exists)."""
    applied: list[str] = []
    raw = engine.raw_connection()
    try:
        cursor = raw.cursor()
        cursor.execute("PRAGMA foreign_keys=OFF")
        cursor.execute("PRAGMA legacy_alter_table=ON")
        cursor.execute("BEGIN")
        if plan["effect"]:
            _create_from_model(cursor, models.EventTypeEffect)
            applied.append("event_type_effect created")
        if plan["event_id"]:
            cursor.execute("ALTER TABLE attribute_change ADD COLUMN event_id VARCHAR REFERENCES event (id)")
            applied.append("attribute_change.event_id added")
        if plan["event_index"]:
            cursor.execute(f"CREATE INDEX {_EVENT_INDEX} ON attribute_change (event_id)")
            applied.append(f"{_EVENT_INDEX} created")
        if plan["lore_entry_row"]:
            _rebuild(cursor, "lore_entry_row", models.LoreEntryRow, _LORE_ROW_COLUMNS)
            applied.append("lore_entry_row rebuilt")
        cursor.execute("COMMIT")
        cursor.execute("PRAGMA legacy_alter_table=OFF")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    except Exception:
        raw.rollback()
        raise
    finally:
        raw.close()
    return applied


def _post_checks(before: dict[str, int]) -> None:
    with engine.connect() as conn:
        after = {t: _count(conn, t) for t in before}
        dangling = [row for table in _TOUCHED_TABLES
                    for row in conn.execute(text(f"PRAGMA foreign_key_check({table})")).fetchall()]
        elsewhere = [row for row in conn.execute(text("PRAGMA foreign_key_check")).fetchall()
                     if row[0] not in _TOUCHED_TABLES]
    problems = []
    if after != before:
        problems.append(f"row counts changed {before} -> {after}")
    if "event_type_effect" not in set(inspect(engine).get_table_names()):
        problems.append("event_type_effect was not created")
    if "event_id" not in _columns("attribute_change") or _EVENT_INDEX not in _indexes("attribute_change"):
        problems.append("attribute_change.event_id or its index is missing")
    if "'attribute_change'" not in _table_sql("lore_entry_row"):
        problems.append("lore_entry_row was not rebuilt")
    if dangling:
        problems.append(f"foreign_key_check {dangling}")
    if problems:
        raise SystemExit("Migration v2.26 aborted, post-check failed: " + "; ".join(problems) + ".")
    for table, rowid, parent, _fk in elsewhere:
        print(f"  Note: {table} rowid {rowid} points to a missing {parent} row (not written by this migration).")
    print(f"Post-check: event_type_effect, attribute_change.event_id and lore_entry_row in place; "
          f"counts kept {after}.")


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
    print("Migration v2.26 — what an event does to the state of the world")
    _refuse()
    with engine.connect() as conn:
        before = {t: _count(conn, t) for t in ("lore_entry_row", "attribute_change")}
    applied = _apply(_plan())
    print("Applied: " + ", ".join(applied) + "." if applied else "Migration v2.26 already fully applied.")
    _post_checks(before)
    _converge_schema_meta()
    print("\nMigration v2.26 applied.")


if __name__ == "__main__":
    main()
