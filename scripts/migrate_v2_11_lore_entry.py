"""Migration v2.11 — `lore_entry` and `lore_entry_row`, the lore writing
path's source record (TICKET-0098, BRIEF-0098-B, decisions B2 + M1).

Creates `lore_entry` (`id, world_id, statement, questions, answers,
created_at`, index `idx_lore_entry_world`) and `lore_entry_row` (`id,
entry_id, row_table, row_id, action`, CHECKs on `row_table` and `action`,
UNIQUE index `idx_lore_entry_row_entry` on `(entry_id, row_table, row_id)`).

Purely additive, zero rows created: both tables start empty and are filled
only by commits from the Lore shell's writing panel going forward.

Refuses to run on a database whose `schema_meta.static_version` is older
than v2.10 (the migrations are sequential).

Idempotent, per object independently (`migrate_v2_01_skill_system.py` rule):
each table's existence is checked before creating it.

Post-check, before commit: both tables exist and hold zero rows.

Run from the project root:

    python scripts/migrate_v2_11_lore_entry.py
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
        "migrate_v2_11_lore_entry.py refuses to run without WORLD_ENGINE_ENV "
        "or WORLD_ENGINE_DATABASE_URL set (fail-closed, TICKET-0049) — got: "
        f"{_env or 'unset'}.",
        file=sys.stderr,
    )
    sys.exit(1)

from sqlalchemy import inspect, text  # noqa: E402
from sqlmodel import Session  # noqa: E402

from world_engine import models  # noqa: E402
from world_engine.db import engine  # noqa: E402
from world_engine.schema_version import EXPECTED_STATIC_SCHEMA_VERSION  # noqa: E402

_PREVIOUS_VERSION = "v2.10"
_TABLES = ("lore_entry", "lore_entry_row")


def _version_key(version: str) -> tuple[int, int]:
    major, minor = version.lstrip("v").split(".")
    return int(major), int(minor)


def _refuse_if_behind() -> None:
    with engine.connect() as conn:
        row = conn.execute(text("SELECT static_version FROM schema_meta WHERE id = 1")).first()
    if row is None or _version_key(row[0]) < _version_key(_PREVIOUS_VERSION):
        found = row[0] if row is not None else "no schema_meta row"
        raise SystemExit(
            f"Migration v2.11 refused: the database is at {found!r}; run the migrations "
            f"up to {_PREVIOUS_VERSION} first."
        )


def _create_lore_entry() -> None:
    with engine.begin() as conn:
        conn.execute(text(
            """
CREATE TABLE lore_entry (
  id          TEXT PRIMARY KEY,
  world_id    TEXT NOT NULL REFERENCES world(id),
  statement   TEXT NOT NULL,
  questions   TEXT,
  answers     TEXT,
  created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
)
"""
        ))
        conn.execute(text(
            "CREATE INDEX idx_lore_entry_world ON lore_entry(world_id, created_at)"
        ))


def _create_lore_entry_row() -> None:
    with engine.begin() as conn:
        conn.execute(text(
            """
CREATE TABLE lore_entry_row (
  id         TEXT PRIMARY KEY,
  entry_id   TEXT NOT NULL REFERENCES lore_entry(id),
  row_table  TEXT NOT NULL CHECK (row_table IN ('entity','fact','fact_participant',
               'fact_default','knowledge','relation','faction_membership')),
  row_id     TEXT NOT NULL,
  action     TEXT NOT NULL CHECK (action IN ('created','updated'))
)
"""
        ))
        conn.execute(text(
            "CREATE UNIQUE INDEX idx_lore_entry_row_entry "
            "ON lore_entry_row(entry_id, row_table, row_id)"
        ))


def _apply_ddl() -> list[str]:
    existing = set(inspect(engine).get_table_names())
    applied: list[str] = []
    if "lore_entry" not in existing:
        _create_lore_entry()
        applied.append("lore_entry table + idx_lore_entry_world")
    else:
        print("Table 'lore_entry' already exists — nothing to do.")
    if "lore_entry_row" not in existing:
        _create_lore_entry_row()
        applied.append("lore_entry_row table + idx_lore_entry_row_entry")
    else:
        print("Table 'lore_entry_row' already exists — nothing to do.")
    return applied


def _post_checks() -> None:
    missing = [t for t in _TABLES if t not in set(inspect(engine).get_table_names())]
    if missing:
        raise SystemExit(f"Migration v2.11 aborted, post-check failed: missing {missing}.")
    with engine.connect() as conn:
        for table in _TABLES:
            count = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
            if count != 0:
                raise SystemExit(
                    f"Migration v2.11 aborted, post-check failed: {table} holds {count} "
                    "row(s), expected 0 — this migration creates zero rows."
                )
            print(f"Post-check: {table} row count = 0 (expected 0).")


def _converge_schema_meta() -> None:
    with Session(engine) as session:
        row = session.get(models.SchemaMeta, 1)
        if row is None:
            session.add(models.SchemaMeta(id=1, static_version=EXPECTED_STATIC_SCHEMA_VERSION))
            print(f"Row: seeded schema_meta.id=1 at {EXPECTED_STATIC_SCHEMA_VERSION!r}")
        elif row.static_version != EXPECTED_STATIC_SCHEMA_VERSION:
            previous = row.static_version
            row.static_version = EXPECTED_STATIC_SCHEMA_VERSION
            row.updated_at = datetime.now(UTC)
            session.add(row)
            print(f"Row: updated schema_meta.id=1: {previous!r} -> {EXPECTED_STATIC_SCHEMA_VERSION!r}")
        else:
            print(f"Row: schema_meta.id=1 already at {EXPECTED_STATIC_SCHEMA_VERSION!r} — nothing to do")
        session.commit()


def main() -> None:
    print("Migration v2.11 — lore_entry, lore_entry_row")
    _refuse_if_behind()
    applied = _apply_ddl()
    if applied:
        print("Applied: " + ", ".join(applied) + ".")
    else:
        print("Migration v2.11 already fully applied — zero writes.")
    _post_checks()
    _converge_schema_meta()
    print("\nMigration v2.11 applied.")


if __name__ == "__main__":
    main()
