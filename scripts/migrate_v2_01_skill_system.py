"""Migration v2.01 — `skill_system`, the world-authored body of skill rules
(TICKET-0084, BRIEF-0084-a).

Creates the `skill_system` table (`id, world_id, name, description,
created_at, updated_at`; `UNIQUE(world_id, name)`) and adds
`skill_definition.system_id`, a nullable FK to `skill_system(id)` with
`ON DELETE RESTRICT` — NULL for every existing row (unaffiliated), set only
by creator CRUD (`POST`/`PUT /api/skill-definitions`) from here on.

Purely additive, zero rows created: no world gets a default system, not
even the pilot, and no existing `skill_definition` row is backfilled.

Idempotent, per object independently (`migrate_v1_80_obstacle_geometry.py`
rule): table existence and column existence are checked separately, so a
partially applied prior run completes only the missing parts rather than
skipping wholesale.

Post-checks, before commit: `skill_system` row count is 0; the count of
`skill_definition` rows is identical before and after; every existing
`skill_definition.system_id` is NULL.

Run from the project root:

    python scripts/migrate_v2_01_skill_system.py
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
        "migrate_v2_01_skill_system.py refuses to run without WORLD_ENGINE_ENV "
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


def _create_skill_system_table() -> None:
    with engine.begin() as conn:
        conn.execute(text(
            "CREATE TABLE skill_system ("
            "  id           TEXT PRIMARY KEY,"
            "  world_id     TEXT NOT NULL REFERENCES world(id),"
            "  name         TEXT NOT NULL,"
            "  description  TEXT,"
            "  created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,"
            "  updated_at   DATETIME DEFAULT CURRENT_TIMESTAMP"
            ")"
        ))
        conn.execute(text(
            "CREATE UNIQUE INDEX idx_skill_system_world_name "
            "ON skill_system(world_id, name)"
        ))
        conn.execute(text(
            "CREATE INDEX idx_skill_system_world ON skill_system(world_id)"
        ))


def _add_system_id_column() -> None:
    with engine.begin() as conn:
        conn.execute(text(
            "ALTER TABLE skill_definition ADD COLUMN system_id TEXT "
            "REFERENCES skill_system(id) ON DELETE RESTRICT"
        ))
        conn.execute(text(
            "CREATE INDEX idx_skill_definition_system ON skill_definition(system_id)"
        ))


def _apply_ddl() -> list[str]:
    inspector = inspect(engine)
    applied: list[str] = []

    if "skill_system" not in inspector.get_table_names():
        _create_skill_system_table()
        applied.append("skill_system table + its two indexes")
    else:
        print("Table 'skill_system' already exists — nothing to do.")

    inspector = inspect(engine)
    cols = {c["name"] for c in inspector.get_columns("skill_definition")}
    if "system_id" not in cols:
        _add_system_id_column()
        applied.append("skill_definition.system_id column + idx_skill_definition_system")
    else:
        print("Column 'skill_definition.system_id' already exists — nothing to do.")

    return applied


def _post_checks(before_definition_count: int) -> None:
    with engine.connect() as conn:
        system_count = conn.execute(text("SELECT COUNT(*) FROM skill_system")).scalar()
        after_definition_count = conn.execute(text("SELECT COUNT(*) FROM skill_definition")).scalar()
        non_null_system_id = conn.execute(
            text("SELECT COUNT(*) FROM skill_definition WHERE system_id IS NOT NULL")
        ).scalar()

    if system_count != 0:
        raise SystemExit(
            f"Migration v2.01 aborted, post-check failed: skill_system row count "
            f"is {system_count}, expected 0 — this migration must create zero rows."
        )
    if after_definition_count != before_definition_count:
        raise SystemExit(
            "Migration v2.01 aborted, post-check failed: skill_definition row count "
            f"changed ({before_definition_count} -> {after_definition_count}) — "
            "history is sacred, this migration must not touch existing rows."
        )
    if non_null_system_id != 0:
        raise SystemExit(
            f"Migration v2.01 aborted, post-check failed: {non_null_system_id} "
            "skill_definition row(s) carry a non-NULL system_id — every existing "
            "row must stay unaffiliated until Nia attaches it by hand."
        )

    print(f"Post-check: skill_system row count = {system_count} (expected 0).")
    print(
        f"Post-check: skill_definition row count unchanged at {after_definition_count}, "
        f"{non_null_system_id} with non-NULL system_id (expected 0)."
    )


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
    print("Migration v2.01 — skill_system")

    with engine.connect() as conn:
        before_definition_count = conn.execute(text("SELECT COUNT(*) FROM skill_definition")).scalar()

    applied = _apply_ddl()
    if applied:
        print("Applied: " + ", ".join(applied) + ".")
    else:
        print("Migration v2.01 already fully applied — zero writes.")

    _post_checks(before_definition_count)
    _converge_schema_meta()
    print("\nMigration v2.01 applied.")


if __name__ == "__main__":
    main()
