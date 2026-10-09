"""Migration v2.21 — `condition_draft`, the condition interpreter's journal
(TICKET-0112, BRIEF-0112-B, decision IH1).

Creates `condition_draft` (`id, attempt_id, world_ref, world_name, role,
instruction, outcome, retried, offer_ref, saved_as_proposed, payload,
model_calls, created_at, decided_at`, CHECKs `ck_condition_draft_role`,
`ck_condition_draft_outcome`, `ck_condition_draft_saved`, indexes
`idx_condition_draft_attempt` and `idx_condition_draft_world`). No
`world_id` column and no FK to `world` or `quest_offer`: the journal
outlives a deleted world or offer.

Purely additive, zero rows created: the table starts empty and is filled
only by the interpreter's routes going forward. Nothing is backfilled.

Refuses to run on a database whose `schema_meta.static_version` is older
than v2.20 (the migrations are sequential).

Idempotent: the table's existence is checked before creating it.

Post-check, before commit: the table exists and holds zero rows.

Run from the project root:

    python scripts/migrate_v2_21_condition_draft.py
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
        "migrate_v2_21_condition_draft.py refuses to run without WORLD_ENGINE_ENV "
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

_PREVIOUS_VERSION = "v2.20"
_TABLE = "condition_draft"


def _version_key(version: str) -> tuple[int, int]:
    major, minor = version.lstrip("v").split(".")
    return int(major), int(minor)


def _refuse_if_behind() -> None:
    with engine.connect() as conn:
        row = conn.execute(text("SELECT static_version FROM schema_meta WHERE id = 1")).first()
    if row is None or _version_key(row[0]) < _version_key(_PREVIOUS_VERSION):
        found = row[0] if row is not None else "no schema_meta row"
        raise SystemExit(
            f"Migration v2.21 refused: the database is at {found!r}; run the migrations "
            f"up to {_PREVIOUS_VERSION} first."
        )


def _create_table() -> None:
    with engine.begin() as conn:
        conn.execute(text(
            """
CREATE TABLE condition_draft (
  id                 TEXT PRIMARY KEY NOT NULL,
  attempt_id         TEXT NOT NULL,
  world_ref          TEXT NOT NULL,
  world_name         TEXT NOT NULL,
  role               TEXT NOT NULL,
  instruction        TEXT NOT NULL,
  outcome            TEXT NOT NULL,
  retried            BOOLEAN NOT NULL DEFAULT 0,
  offer_ref          TEXT,
  saved_as_proposed  BOOLEAN,
  payload            JSON NOT NULL,
  model_calls        JSON NOT NULL DEFAULT '[]',
  created_at         DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  decided_at         DATETIME,
  CONSTRAINT ck_condition_draft_role CHECK (
    role IN ('eligibility','prerequisite','completion')),
  CONSTRAINT ck_condition_draft_outcome CHECK (
    outcome IN ('proposed','needs_choice','refused','unavailable','parse_error',
                'inserted','discarded','saved')),
  CONSTRAINT ck_condition_draft_saved CHECK (
    (offer_ref IS NOT NULL) = (outcome = 'saved')
    AND (saved_as_proposed IS NOT NULL) = (outcome = 'saved'))
)
"""
        ))
        conn.execute(text(
            "CREATE INDEX idx_condition_draft_attempt ON condition_draft(attempt_id, created_at)"
        ))
        conn.execute(text(
            "CREATE INDEX idx_condition_draft_world ON condition_draft(world_ref, created_at)"
        ))


def _apply_ddl() -> list[str]:
    if _TABLE in set(inspect(engine).get_table_names()):
        print(f"Table {_TABLE!r} already exists — nothing to do.")
        return []
    _create_table()
    return [f"{_TABLE} table + idx_condition_draft_attempt + idx_condition_draft_world"]


def _post_checks() -> None:
    if _TABLE not in set(inspect(engine).get_table_names()):
        raise SystemExit(f"Migration v2.21 aborted, post-check failed: {_TABLE} is missing.")
    with engine.connect() as conn:
        count = conn.execute(text(f"SELECT COUNT(*) FROM {_TABLE}")).scalar()
    if count != 0:
        raise SystemExit(
            f"Migration v2.21 aborted, post-check failed: {_TABLE} holds {count} row(s), "
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
    print("Migration v2.21 — condition_draft")
    _refuse_if_behind()
    applied = _apply_ddl()
    if applied:
        print("Applied: " + ", ".join(applied) + ".")
    else:
        print("Migration v2.21 already fully applied — zero writes.")
    _post_checks()
    _converge_schema_meta()
    print("\nMigration v2.21 applied.")


if __name__ == "__main__":
    main()
