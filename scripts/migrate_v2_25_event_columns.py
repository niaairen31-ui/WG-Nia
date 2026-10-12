"""Migration v2.25 — the journal drops what it no longer reads (TICKET-0114,
BRIEF-0114-D; decisions L1, N1, O1 and V1 of the conditions series).

Rebuilds `event` without `type` (a type's `domain` now), `knowledge_status`
(who knows an event is its fact's knowledge and scopes since v2.24),
`has_magic_impact`, `consequences` and `occurred_at` (no reader, no value:
the four production events carry the JSON `null` in `consequences`, never
a magic impact nor an `occurred_at`), with `type_id` required and a
`quantity` CHECK (1 or more); every row copied. Drops `event_entity`, whose
rows v2.24 copied into `event_participant`.

Before anything, the v2.24 data step is made complete: an event written
between v2.24 and this code is typed, given its participants and its fact
exactly as v2.24 did (`migrate_v2_24_event_journal._backfill`, imported,
never copied), so no event loses what the dropped columns said.

Refuses to run on a database whose `schema_meta.static_version` is older
than v2.24, or when an `event_entity` row has no `event_participant`
twin. Idempotent: a database already at the new shape is left as it is.
One raw transaction (`foreign_keys` and `legacy_alter_table` set before it).

Post-check, before `schema_meta` moves: `event` holds as many rows as
before, none without a type; `event_entity` is gone; the dropped columns
are gone; `PRAGMA foreign_key_check` on `event`, `event_participant` and
`fact` is empty (a dangling row elsewhere is a note, AMENDMENT-0107-01).

Run from the project root:

    python scripts/migrate_v2_25_event_columns.py
"""

from __future__ import annotations

import os
import sys
from datetime import UTC, datetime
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(Path(__file__).resolve().parent))

_env = os.environ.get("WORLD_ENGINE_ENV")
if not _env and not os.environ.get("WORLD_ENGINE_DATABASE_URL"):
    print(
        "migrate_v2_25_event_columns.py refuses to run without WORLD_ENGINE_ENV "
        "or WORLD_ENGINE_DATABASE_URL set (fail-closed, TICKET-0049) — got: "
        f"{_env or 'unset'}.",
        file=sys.stderr,
    )
    sys.exit(1)

from sqlalchemy import inspect, text  # noqa: E402
from sqlalchemy.schema import CreateIndex, CreateTable  # noqa: E402
from sqlmodel import Session  # noqa: E402

from migrate_v2_24_event_journal import _backfill  # noqa: E402
from world_engine import models  # noqa: E402
from world_engine.db import engine  # noqa: E402
from world_engine.schema_version import EXPECTED_STATIC_SCHEMA_VERSION  # noqa: E402

_PREVIOUS_VERSION = "v2.24"
_KEPT_COLUMNS = "id, world_id, session_id, batch_id, type_id, title, description, location_id, quantity, recorded_at"
_DROPPED = ("type", "knowledge_status", "has_magic_impact", "consequences", "occurred_at")
_TOUCHED_TABLES = ("event", "event_participant", "fact", "fact_default", "event_type", "event_type_role",
                   "event_type_role_type")


def _version_key(version: str) -> tuple[int, int]:
    major, minor = version.lstrip("v").split(".")
    return int(major), int(minor)


def _tables() -> set[str]:
    return set(inspect(engine).get_table_names())


def _columns(table: str) -> set[str]:
    return {column["name"] for column in inspect(engine).get_columns(table)}


def _refuse() -> None:
    with engine.connect() as conn:
        row = conn.execute(text("SELECT static_version FROM schema_meta WHERE id = 1")).first()
        if row is None or _version_key(row[0]) < _version_key(_PREVIOUS_VERSION):
            found = row[0] if row is not None else "no schema_meta row"
            raise SystemExit(
                f"Migration v2.25 refused: the database is at {found!r}; run the migrations "
                f"up to {_PREVIOUS_VERSION} first."
            )
        if "event_entity" in _tables():
            orphans = conn.execute(text(
                "SELECT COUNT(*) FROM event_entity l JOIN event e ON e.id = l.event_id WHERE e.type_id IS NOT NULL "
                "AND NOT EXISTS (SELECT 1 FROM event_participant p WHERE p.event_id = l.event_id "
                "AND p.entity_id = l.entity_id)")).scalar_one()
            if orphans:
                raise SystemExit(
                    f"Migration v2.25 refused: {orphans} event_entity row(s) have no event_participant twin; "
                    "dropping them would lose who took part."
                )


def _create_from_model(cursor, model) -> None:
    cursor.execute(str(CreateTable(model.__table__).compile(dialect=engine.dialect)))
    for index in model.__table__.indexes:
        cursor.execute(str(CreateIndex(index).compile(dialect=engine.dialect)))


def _apply() -> list[str]:
    needed = bool(set(_DROPPED) & _columns("event")) or "event_entity" in _tables()
    if not needed:
        return []
    applied: list[str] = []
    raw = engine.raw_connection()
    try:
        cursor = raw.cursor()
        cursor.execute("PRAGMA foreign_keys=OFF")
        cursor.execute("PRAGMA legacy_alter_table=ON")
        cursor.execute("BEGIN")
        typed = _backfill(cursor)
        if typed:
            applied.append(f"{len(typed)} event(s) typed first, as v2.24 does")
        if set(_DROPPED) & _columns("event"):
            for (index_name,) in cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='event' AND sql IS NOT NULL"
            ).fetchall():
                cursor.execute(f"DROP INDEX {index_name}")
            cursor.execute("ALTER TABLE event RENAME TO event_old")
            _create_from_model(cursor, models.Event)
            cursor.execute(f"INSERT INTO event ({_KEPT_COLUMNS}) SELECT {_KEPT_COLUMNS} FROM event_old")
            cursor.execute("DROP TABLE event_old")
            applied.append("event rebuilt without " + ", ".join(_DROPPED))
        if "event_entity" in _tables():
            cursor.execute("DROP TABLE event_entity")
            applied.append("event_entity dropped")
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


def _post_checks(before: int) -> None:
    problems = []
    with engine.connect() as conn:
        after = conn.execute(text("SELECT COUNT(*) FROM event")).scalar_one()
        untyped = conn.execute(text("SELECT COUNT(*) FROM event WHERE type_id IS NULL")).scalar_one()
        dangling = [row for table in _TOUCHED_TABLES
                    for row in conn.execute(text(f"PRAGMA foreign_key_check({table})")).fetchall()]
        elsewhere = [row for row in conn.execute(text("PRAGMA foreign_key_check")).fetchall()
                     if row[0] not in _TOUCHED_TABLES]
    if after != before:
        problems.append(f"event holds {after} row(s), {before} before")
    if untyped:
        problems.append(f"{untyped} event(s) without a type")
    if "event_entity" in _tables():
        problems.append("event_entity is still there")
    left = sorted(set(_DROPPED) & _columns("event"))
    if left:
        problems.append(f"event still has {left}")
    if dangling:
        problems.append(f"foreign_key_check {dangling}")
    if problems:
        raise SystemExit("Migration v2.25 aborted, post-check failed: " + "; ".join(problems) + ".")
    for table, rowid, parent, _fk in elsewhere:
        print(f"  Note: {table} rowid {rowid} points to a missing {parent} row (not written by this migration).")
    print(f"Post-check: {after} event(s) kept, each typed; the dropped columns and event_entity are gone.")


def _converge_schema_meta() -> None:
    with Session(engine) as session:
        row = session.get(models.SchemaMeta, 1)
        if row is None:
            session.add(models.SchemaMeta(id=1, static_version=EXPECTED_STATIC_SCHEMA_VERSION))
            print(f"Row: seeded schema_meta.id=1 at {EXPECTED_STATIC_SCHEMA_VERSION!r}")
        elif _version_key(row.static_version) < _version_key(EXPECTED_STATIC_SCHEMA_VERSION):
            previous = row.static_version
            row.static_version = EXPECTED_STATIC_SCHEMA_VERSION
            row.updated_at = datetime.now(UTC)
            session.add(row)
            print(f"Row: updated schema_meta.id=1: {previous!r} -> {EXPECTED_STATIC_SCHEMA_VERSION!r}")
        else:
            print(f"Row: schema_meta.id=1 already at {row.static_version!r} — nothing to do")
        session.commit()


def main() -> None:
    print("Migration v2.25 — the journal drops what it no longer reads")
    _refuse()
    with engine.connect() as conn:
        before = conn.execute(text("SELECT COUNT(*) FROM event")).scalar_one()
    applied = _apply()
    print("Applied: " + ", ".join(applied) + "." if applied else "Migration v2.25 already fully applied.")
    _post_checks(before)
    _converge_schema_meta()
    print("\nMigration v2.25 applied.")


if __name__ == "__main__":
    main()
