"""Migration v2.13 — `lore_usage_event`, the Lore shell's usage journal
(TICKET-0103, BRIEF-0103-A, decisions A2 + B1 + C1 + D1 + F2 + I1).

Creates `lore_usage_event` (`id, attempt_id, world_ref, world_name, kind,
step, outcome, payload, model_calls, lore_entry_ref, created_at`, CHECKs
`ck_lore_usage_event_step`, `ck_lore_usage_event_outcome`,
`ck_lore_usage_event_entry`, indexes `idx_lore_usage_event_attempt` and
`idx_lore_usage_event_world`). No `world_id` column and no FK to `world` or
`lore_entry` (I1): the journal outlives a deleted world.

Purely additive, zero rows created: the table starts empty and is filled
only by the Lore shell's routes going forward. Nothing is backfilled.

Refuses to run on a database whose `schema_meta.static_version` is older
than v2.12 (the migrations are sequential).

Idempotent: the table's existence is checked before creating it.

Post-check, before commit: the table exists and holds zero rows.

Run from the project root:

    python scripts/migrate_v2_13_lore_usage.py
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
        "migrate_v2_13_lore_usage.py refuses to run without WORLD_ENGINE_ENV "
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

_PREVIOUS_VERSION = "v2.12"
_TABLE = "lore_usage_event"


def _version_key(version: str) -> tuple[int, int]:
    major, minor = version.lstrip("v").split(".")
    return int(major), int(minor)


def _refuse_if_behind() -> None:
    with engine.connect() as conn:
        row = conn.execute(text("SELECT static_version FROM schema_meta WHERE id = 1")).first()
    if row is None or _version_key(row[0]) < _version_key(_PREVIOUS_VERSION):
        found = row[0] if row is not None else "no schema_meta row"
        raise SystemExit(
            f"Migration v2.13 refused: the database is at {found!r}; run the migrations "
            f"up to {_PREVIOUS_VERSION} first."
        )


def _create_table() -> None:
    with engine.begin() as conn:
        conn.execute(text(
            """
CREATE TABLE lore_usage_event (
  id              TEXT PRIMARY KEY NOT NULL,
  attempt_id      TEXT NOT NULL,
  world_ref       TEXT NOT NULL,
  world_name      TEXT NOT NULL,
  kind            TEXT NOT NULL,
  step            TEXT NOT NULL,
  outcome         TEXT NOT NULL,
  payload         JSON NOT NULL,
  model_calls     JSON NOT NULL DEFAULT '[]',
  lore_entry_ref  TEXT,
  created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT ck_lore_usage_event_step CHECK (
    (kind = 'write' AND step IN ('questions','draft','commit'))
    OR (kind = 'consult' AND step IN ('ask','resolve'))),
  CONSTRAINT ck_lore_usage_event_outcome CHECK (
    outcome IN ('ok','unavailable','parse_error','refused')),
  CONSTRAINT ck_lore_usage_event_entry CHECK (
    (lore_entry_ref IS NOT NULL) = (step = 'commit' AND outcome = 'ok'))
)
"""
        ))
        conn.execute(text(
            "CREATE INDEX idx_lore_usage_event_attempt ON lore_usage_event(attempt_id, created_at)"
        ))
        conn.execute(text(
            "CREATE INDEX idx_lore_usage_event_world ON lore_usage_event(world_ref, created_at)"
        ))


def _apply_ddl() -> list[str]:
    if _TABLE in set(inspect(engine).get_table_names()):
        print(f"Table {_TABLE!r} already exists — nothing to do.")
        return []
    _create_table()
    return [f"{_TABLE} table + idx_lore_usage_event_attempt + idx_lore_usage_event_world"]


def _post_checks() -> None:
    if _TABLE not in set(inspect(engine).get_table_names()):
        raise SystemExit(f"Migration v2.13 aborted, post-check failed: {_TABLE} is missing.")
    with engine.connect() as conn:
        count = conn.execute(text(f"SELECT COUNT(*) FROM {_TABLE}")).scalar()
    if count != 0:
        raise SystemExit(
            f"Migration v2.13 aborted, post-check failed: {_TABLE} holds {count} row(s), "
            "expected 0 — this migration creates zero rows."
        )
    print(f"Post-check: {_TABLE} row count = 0 (expected 0).")


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
    print("Migration v2.13 — lore_usage_event")
    _refuse_if_behind()
    applied = _apply_ddl()
    if applied:
        print("Applied: " + ", ".join(applied) + ".")
    else:
        print("Migration v2.13 already fully applied — zero writes.")
    _post_checks()
    _converge_schema_meta()
    print("\nMigration v2.13 applied.")


if __name__ == "__main__":
    main()
