"""Migration v2.31 — a world opens to players; the Lore journal admits the perspective kind (TICKET-0125, BRIEF-0125-B; decisions C1, H1-c).

Schema only; the one data write is the journal's copy:

- adds `world.open_to_players` (BOOLEAN NOT NULL DEFAULT 0: the creator's
  « Ouvert aux joueurs », read by the player shell);
- rebuilds `lore_usage_event` so its step CHECK admits `kind = 'perspective'`
  with steps `perspective_ask` and `perspective_resolve`. Every row is copied
  unchanged.

Refuses to run on a database whose `schema_meta.static_version` is older
than v2.30. Idempotent: each step runs only while still needed (the column
is absent; the stored table SQL lacks `'perspective'`). One raw transaction
(`foreign_keys` and `legacy_alter_table` set before it).

Post-checks, before `schema_meta` moves: `world` holds `open_to_players`;
the stored `lore_usage_event` SQL holds `'perspective_ask'`; the journal's
row count is unchanged. `schema_meta` then moves to v2.31.

Run from the project root:

    python scripts/migrate_v2_31_player_entry.py
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
        "migrate_v2_31_player_entry.py refuses to run without WORLD_ENGINE_ENV "
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

_PREVIOUS_VERSION = "v2.30"
_THIS_VERSION = "v2.31"
_JOURNAL_COLUMNS = (
    "id, attempt_id, world_ref, world_name, kind, step, outcome, payload, "
    "model_calls, lore_entry_ref, created_at"
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
            f"Migration v2.31 refused: the database is at {found!r}; run the migrations "
            f"up to {_PREVIOUS_VERSION} first."
        )


def _has_open_to_players() -> bool:
    return "open_to_players" in {c["name"] for c in inspect(engine).get_columns("world")}


def _journal_sql() -> str:
    with engine.connect() as conn:
        return conn.execute(text("SELECT sql FROM sqlite_master WHERE type='table' AND name=:n"),
                            {"n": "lore_usage_event"}).scalar_one()


def _journal_count() -> int:
    with engine.connect() as conn:
        return conn.execute(text("SELECT COUNT(*) FROM lore_usage_event")).scalar_one()


def _create_from_model(cursor, model) -> None:
    cursor.execute(str(CreateTable(model.__table__).compile(dialect=engine.dialect)))
    for index in model.__table__.indexes:
        cursor.execute(str(CreateIndex(index).compile(dialect=engine.dialect)))


def _rebuild(cursor, model, columns: str) -> None:
    table = model.__tablename__
    for (index_name,) in cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name=? AND sql IS NOT NULL",
        (table,),
    ).fetchall():
        cursor.execute(f"DROP INDEX {index_name}")
    cursor.execute(f"ALTER TABLE {table} RENAME TO {table}_old")
    _create_from_model(cursor, model)
    cursor.execute(f"INSERT INTO {table} ({columns}) SELECT {columns} FROM {table}_old")
    cursor.execute(f"DROP TABLE {table}_old")


def _plan() -> tuple[list[str], list[tuple]]:
    """(ADD COLUMN statements, (model, copied columns) rebuilds) still to apply."""
    adds: list[str] = []
    if not _has_open_to_players():
        adds.append("ALTER TABLE world ADD COLUMN open_to_players BOOLEAN NOT NULL DEFAULT 0")
    rebuilds: list[tuple] = []
    if "'perspective'" not in _journal_sql():
        rebuilds.append((models.LoreUsageEvent, _JOURNAL_COLUMNS))
    return adds, rebuilds


def _apply() -> list[str]:
    """One raw transaction (`migrate_v1_95_parked_plans.py`'s docstring: the
    PRAGMAs must land before any transaction exists)."""
    adds, rebuilds = _plan()
    if not adds and not rebuilds:
        return []
    raw = engine.raw_connection()
    try:
        cursor = raw.cursor()
        cursor.execute("PRAGMA foreign_keys=OFF")
        cursor.execute("PRAGMA legacy_alter_table=ON")
        cursor.execute("BEGIN")
        for statement in adds:
            cursor.execute(statement)
        for model, columns in rebuilds:
            _rebuild(cursor, model, columns)
        cursor.execute("COMMIT")
        cursor.execute("PRAGMA legacy_alter_table=OFF")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    except Exception:
        raw.rollback()
        raise
    finally:
        raw.close()
    added = ["world.open_to_players added"] if adds else []
    return added + [f"{model.__tablename__} rebuilt" for model, _ in rebuilds]


def _post_checks(journal_before: int) -> None:
    problems: list[str] = []
    if not _has_open_to_players():
        problems.append("world lacks open_to_players")
    if "'perspective_ask'" not in _journal_sql():
        problems.append("lore_usage_event's step CHECK lacks 'perspective_ask'")
    journal_after = _journal_count()
    if journal_after != journal_before:
        problems.append(f"lore_usage_event row count {journal_before} -> {journal_after}")
    if problems:
        raise SystemExit("Migration v2.31 aborted, post-check failed: " + "; ".join(problems) + ".")
    print(f"Post-check: world.open_to_players in place; lore_usage_event admits the perspective "
          f"kind; {journal_after} journal row(s) kept.")


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
    print("Migration v2.31 — a world opens to players; the Lore journal admits the perspective kind")
    _refuse()
    journal_before = _journal_count()
    applied = _apply()
    print("Applied: " + ", ".join(applied) + "." if applied else "Migration v2.31 already fully applied.")
    _post_checks(journal_before)
    _converge_schema_meta()
    print("\nMigration v2.31 applied.")


if __name__ == "__main__":
    main()
