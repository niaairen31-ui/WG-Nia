"""Migration v2.34 — the active player character, the day's pin, publication and failures (TICKET-0128, BRIEF-0128-A).

Schema, plus one data step (W1):

- adds `world.active_pc_id` (FK `character`, ON DELETE SET NULL), the
  creator's « PJ actif »;
- adds `pass_play.quest_id` (FK `quest`), `pass_play.published_text` and
  `pass_play.published_at`;
- creates the table `day_run_failure` (two CHECKs) and its indexes
  `idx_day_run_failure_pass_play`, `idx_day_run_failure_world`;
- W1: the days already resolved are published with the narrator's text,
  once: only in the run that adds `pass_play.published_at`
  (`published_text` = the batch's `final_result`, `published_at` = its
  `processed_at`, else the day's `submitted_at`). Neither
  `batch.final_result` nor `pass_play.history` is touched.

Refuses to run on a database whose `schema_meta.static_version` is older
than v2.33. Idempotent: each step runs only while still needed (the column
or the table is absent; W1 only while `published_at` is). One raw
transaction (`foreign_keys` and `legacy_alter_table` set before it).

Post-checks, before `schema_meta` moves: the four columns, the table and
both indexes exist; the `pass_play` row count is unchanged; when W1 ran, no
`resolved` day is left unpublished. `schema_meta` then moves to v2.34.

Run from the project root:

    python scripts/migrate_v2_34_player_day.py
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
        "migrate_v2_34_player_day.py refuses to run without WORLD_ENGINE_ENV "
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

_PREVIOUS_VERSION = "v2.33"
_THIS_VERSION = "v2.34"
_NEW_COLUMNS = (
    ("world", "active_pc_id", "VARCHAR REFERENCES character (id) ON DELETE SET NULL"),
    ("pass_play", "quest_id", "VARCHAR REFERENCES quest (id)"),
    ("pass_play", "published_text", "VARCHAR"),
    ("pass_play", "published_at", "DATETIME"),
)
_FAILURE_TABLE = "day_run_failure"
_FAILURE_INDEXES = ("idx_day_run_failure_pass_play", "idx_day_run_failure_world")
_W1_BACKFILL = (
    "UPDATE pass_play SET "
    "published_at = COALESCE((SELECT processed_at FROM batch WHERE batch.id = pass_play.batch_id), "
    "submitted_at), "
    "published_text = (SELECT final_result FROM batch WHERE batch.id = pass_play.batch_id) "
    "WHERE status = 'resolved' AND published_at IS NULL"
)


def _version_key(version: str) -> tuple[int, int]:
    major, minor = version.lstrip("v").split(".")
    return int(major), int(minor)


def _refuse() -> None:
    with engine.connect() as conn:
        row = conn.execute(text("SELECT static_version FROM schema_meta WHERE id = 1")).first()
    if row is None or _version_key(row[0]) < _version_key(_PREVIOUS_VERSION):
        found = row[0] if row is not None else "no schema_meta row"
        raise SystemExit(
            f"Migration v2.34 refused: the database is at {found!r}; run the migrations "
            f"up to {_PREVIOUS_VERSION} first."
        )


def _tables() -> set[str]:
    return set(inspect(engine).get_table_names())


def _columns(table: str) -> set[str]:
    return {c["name"] for c in inspect(engine).get_columns(table)}


def _indexes() -> set[str]:
    with engine.connect() as conn:
        return {name for (name,) in conn.execute(text("SELECT name FROM sqlite_master WHERE type='index'"))}


def _pass_play_count() -> int:
    with engine.connect() as conn:
        return conn.execute(text("SELECT COUNT(*) FROM pass_play")).scalar_one()


def _create_from_model(cursor, model) -> None:
    cursor.execute(str(CreateTable(model.__table__).compile(dialect=engine.dialect)))
    for index in model.__table__.indexes:
        cursor.execute(str(CreateIndex(index).compile(dialect=engine.dialect)))


def _plan() -> tuple[list, list[str], bool]:
    """(models to create, ALTER statements, whether W1 runs) still to apply."""
    creates = [] if _FAILURE_TABLE in _tables() else [models.DayRunFailure]
    adds = [
        f"ALTER TABLE {table} ADD COLUMN {column} {sql_type}"
        for table, column, sql_type in _NEW_COLUMNS
        if column not in _columns(table)
    ]
    backfill = "published_at" not in _columns("pass_play")
    return creates, adds, backfill


def _apply() -> tuple[list[str], int | None]:
    """One raw transaction (`migrate_v1_95_parked_plans.py`'s docstring: the
    PRAGMAs must land before any transaction exists). Returns what was
    applied and the number of days W1 published (None when it did not run)."""
    creates, adds, backfill = _plan()
    if not creates and not adds and not backfill:
        return [], None
    published: int | None = None
    raw = engine.raw_connection()
    try:
        cursor = raw.cursor()
        cursor.execute("PRAGMA foreign_keys=OFF")
        cursor.execute("PRAGMA legacy_alter_table=ON")
        cursor.execute("BEGIN")
        for model in creates:
            _create_from_model(cursor, model)
        for statement in adds:
            cursor.execute(statement)
        if backfill:
            cursor.execute(_W1_BACKFILL)
            published = cursor.rowcount
        cursor.execute("COMMIT")
        cursor.execute("PRAGMA legacy_alter_table=OFF")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    except Exception:
        raw.rollback()
        raise
    finally:
        raw.close()
    created = [f"{model.__tablename__} created" for model in creates]
    added = [f"{statement.split()[2]}.{statement.split()[5]} added" for statement in adds]
    filled = ["W1 backfill run"] if backfill else []
    return created + added + filled, published


def _post_checks(days_before: int, published: int | None) -> None:
    problems: list[str] = []
    for table, column, _ in _NEW_COLUMNS:
        if column not in _columns(table):
            problems.append(f"{table} lacks {column}")
    if _FAILURE_TABLE not in _tables():
        problems.append(f"{_FAILURE_TABLE} is missing")
    indexes = _indexes()
    for name in _FAILURE_INDEXES:
        if name not in indexes:
            problems.append(f"{name} is missing")
    days_after = _pass_play_count()
    if days_after != days_before:
        problems.append(f"pass_play row count {days_before} -> {days_after}")
    if published is not None:
        with engine.connect() as conn:
            left = conn.execute(text(
                "SELECT COUNT(*) FROM pass_play WHERE status = 'resolved' AND published_at IS NULL"
            )).scalar_one()
        if left:
            problems.append(f"{left} resolved day(s) left unpublished by W1")
    if problems:
        raise SystemExit("Migration v2.34 aborted, post-check failed: " + "; ".join(problems) + ".")
    print(f"Post-check: {len(_NEW_COLUMNS)} columns, {_FAILURE_TABLE} and its "
          f"{len(_FAILURE_INDEXES)} indexes in place; {days_after} day(s) kept.")
    if published is not None:
        print(f"W1: {published} day(s) published.")


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
    print("Migration v2.34 — the active player character, the day's pin, publication and failures")
    _refuse()
    days_before = _pass_play_count()
    applied, published = _apply()
    print("Applied: " + ", ".join(applied) + "." if applied else "Nothing to do.")
    _post_checks(days_before, published)
    _converge_schema_meta()
    print("\nMigration v2.34 applied.")


if __name__ == "__main__":
    main()
