"""Migration v2.02 — `skill_resolution`, the action lexicon's audit trail
(TICKET-0084, BRIEF-0084-c).

Creates the `skill_resolution` table (`id, world_id, conversation_id,
surface_form, verdict, base_domain, skill_definition_id, created_at`) with
its shape CHECK (`base` carries `base_domain` only, `matched` carries
`skill_definition_id` only, `unmatched` carries neither) and its two
indexes (`idx_skill_resolution_world_verdict`,
`idx_skill_resolution_conversation`).

Purely additive, zero rows created: this table starts empty and is filled
only by live Play turns going forward (`skill_lexicon.record`).

Idempotent, per object independently (`migrate_v2_01_skill_system.py` rule):
table existence is checked before creating it, so a partially applied prior
run completes only the missing parts rather than skipping wholesale.

Post-check, before commit: `skill_resolution` row count is 0.

Run from the project root:

    python scripts/migrate_v2_02_skill_resolution.py
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
        "migrate_v2_02_skill_resolution.py refuses to run without WORLD_ENGINE_ENV "
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


def _create_skill_resolution_table() -> None:
    with engine.begin() as conn:
        conn.execute(text(
            "CREATE TABLE skill_resolution ("
            "  id                   TEXT PRIMARY KEY,"
            "  world_id             TEXT NOT NULL REFERENCES world(id),"
            "  conversation_id      TEXT NOT NULL REFERENCES conversation(id),"
            "  surface_form         TEXT NOT NULL,"
            "  verdict              TEXT NOT NULL"
            "    CHECK (verdict IN ('base','matched','unmatched')),"
            "  base_domain          TEXT,"
            "  skill_definition_id  TEXT REFERENCES skill_definition(id),"
            "  created_at           DATETIME DEFAULT CURRENT_TIMESTAMP,"
            "  CHECK ("
            "    (verdict <> 'base' OR (base_domain IS NOT NULL AND skill_definition_id IS NULL))"
            "    AND (verdict <> 'matched' OR (skill_definition_id IS NOT NULL AND base_domain IS NULL))"
            "    AND (verdict <> 'unmatched' OR (skill_definition_id IS NULL AND base_domain IS NULL))"
            "  )"
            ")"
        ))
        conn.execute(text(
            "CREATE INDEX idx_skill_resolution_world_verdict "
            "ON skill_resolution(world_id, verdict)"
        ))
        conn.execute(text(
            "CREATE INDEX idx_skill_resolution_conversation "
            "ON skill_resolution(conversation_id)"
        ))


def _apply_ddl() -> list[str]:
    inspector = inspect(engine)
    applied: list[str] = []

    if "skill_resolution" not in inspector.get_table_names():
        _create_skill_resolution_table()
        applied.append("skill_resolution table + its two indexes")
    else:
        print("Table 'skill_resolution' already exists — nothing to do.")

    return applied


def _post_checks() -> None:
    with engine.connect() as conn:
        row_count = conn.execute(text("SELECT COUNT(*) FROM skill_resolution")).scalar()

    if row_count != 0:
        raise SystemExit(
            f"Migration v2.02 aborted, post-check failed: skill_resolution row count "
            f"is {row_count}, expected 0 — this migration must create zero rows."
        )

    print(f"Post-check: skill_resolution row count = {row_count} (expected 0).")


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
    print("Migration v2.02 — skill_resolution")

    applied = _apply_ddl()
    if applied:
        print("Applied: " + ", ".join(applied) + ".")
    else:
        print("Migration v2.02 already fully applied — zero writes.")

    _post_checks()
    _converge_schema_meta()
    print("\nMigration v2.02 applied.")


if __name__ == "__main__":
    main()
