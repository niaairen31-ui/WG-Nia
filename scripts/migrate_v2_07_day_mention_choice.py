"""Migration v2.07 — `day_mention_choice`, the H2 choice record
(TICKET-0094, BRIEF-0094-A).

Creates the `day_mention_choice` table (`id, world_id, pass_play_id,
category, surface_form, trigger, candidate_ids, evidence_fact_ids, verdict,
chosen_entity_id, excerpt, reason, verdict_detail, attempts, created_at`)
with its CHECKs (category, trigger, verdict, attempts, and the shape CHECK:
`accepted` carries `chosen_entity_id`, `declined`/`failed` never do) and its
two indexes (`idx_day_mention_choice_pass`,
`idx_day_mention_choice_world_verdict`).

Purely additive, zero rows created: this table starts empty and is filled
only by live day declarations going forward (one row per model choice call).

Idempotent, per object independently (`migrate_v2_01_skill_system.py` rule):
table existence is checked before creating it, so a partially applied prior
run completes only the missing parts rather than skipping wholesale.

Post-check, before commit: `day_mention_choice` row count is 0.

Run from the project root:

    python scripts/migrate_v2_07_day_mention_choice.py
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
        "migrate_v2_07_day_mention_choice.py refuses to run without WORLD_ENGINE_ENV "
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


def _create_day_mention_choice_table() -> None:
    with engine.begin() as conn:
        conn.execute(text(
            """
CREATE TABLE day_mention_choice (
  id                 TEXT PRIMARY KEY,
  world_id           TEXT NOT NULL REFERENCES world(id),
  pass_play_id       TEXT NOT NULL REFERENCES pass_play(id),
  category           TEXT NOT NULL CHECK (category IN ('place','person','faction')),
  surface_form       TEXT NOT NULL,
  trigger            TEXT NOT NULL CHECK (trigger IN ('ambiguous','near')),
  candidate_ids      TEXT NOT NULL,   -- JSON array, display order
  evidence_fact_ids  TEXT NOT NULL,   -- JSON array, facts shown to the model
  verdict            TEXT NOT NULL CHECK (verdict IN ('accepted','rejected','declined','failed')),
  chosen_entity_id   TEXT REFERENCES entity(id),
  excerpt            TEXT,
  reason             TEXT,
  verdict_detail     TEXT,
  attempts           INTEGER NOT NULL CHECK (attempts IN (1, 2)),
  created_at         DATETIME DEFAULT CURRENT_TIMESTAMP,
  CHECK (
    (verdict <> 'accepted' OR chosen_entity_id IS NOT NULL)
    AND (verdict NOT IN ('declined','failed') OR chosen_entity_id IS NULL)
  )
)
"""
        ))
        conn.execute(text(
            "CREATE INDEX idx_day_mention_choice_pass ON day_mention_choice(pass_play_id)"
        ))
        conn.execute(text(
            "CREATE INDEX idx_day_mention_choice_world_verdict ON day_mention_choice(world_id, verdict)"
        ))


def _apply_ddl() -> list[str]:
    inspector = inspect(engine)
    applied: list[str] = []

    if "day_mention_choice" not in inspector.get_table_names():
        _create_day_mention_choice_table()
        applied.append("day_mention_choice table + its two indexes")
    else:
        print("Table 'day_mention_choice' already exists — nothing to do.")

    return applied


def _post_checks() -> None:
    with engine.connect() as conn:
        row_count = conn.execute(text("SELECT COUNT(*) FROM day_mention_choice")).scalar()

    if row_count != 0:
        raise SystemExit(
            f"Migration v2.07 aborted, post-check failed: day_mention_choice row count "
            f"is {row_count}, expected 0 — this migration must create zero rows."
        )

    print(f"Post-check: day_mention_choice row count = {row_count} (expected 0).")


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
    print("Migration v2.07 — day_mention_choice")

    applied = _apply_ddl()
    if applied:
        print("Applied: " + ", ".join(applied) + ".")
    else:
        print("Migration v2.07 already fully applied — zero writes.")

    _post_checks()
    _converge_schema_meta()
    print("\nMigration v2.07 applied.")


if __name__ == "__main__":
    main()
