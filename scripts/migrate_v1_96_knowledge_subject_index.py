"""Migration v1.96 — `idx_knowledge_subject` (TICKET-0078, BRIEF-0078-a — the
requirement-anchoring step).

Index-only: `knowledge` gains an index on `subject`, the column
`day_plan._anchorable_subjects`/`_held_subjects` now query by. No table
rebuild — adding an index needs none (`migrate_v1_94_agenda_step_plan.py`
precedent for index-only additions to an existing table; the
`migrate_v1_8_gatherings.py` rebuild dance does not apply here).

Also converges `schema_meta.static_version` to `EXPECTED_STATIC_SCHEMA_VERSION`
(`migrate_v1_86_schema_meta.py`'s converge-if-different idiom), inside the
same `engine.begin()` as the index creation.

Idempotent: safe to run if the index or the schema_meta row are already
converged.

Run from the project root:

    python scripts/migrate_v1_96_knowledge_subject_index.py
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
        "migrate_v1_96_knowledge_subject_index.py refuses to run without "
        "WORLD_ENGINE_ENV or WORLD_ENGINE_DATABASE_URL set (fail-closed, "
        f"TICKET-0049) — got: {_env or 'unset'}.",
        file=sys.stderr,
    )
    sys.exit(1)

from sqlalchemy import text  # noqa: E402
from sqlmodel import Session  # noqa: E402

from world_engine.db import engine  # noqa: E402
from world_engine.models import SchemaMeta  # noqa: E402
from world_engine.schema_version import EXPECTED_STATIC_SCHEMA_VERSION  # noqa: E402


def main() -> None:
    print("Migration v1.96 — idx_knowledge_subject")

    with engine.begin() as conn:
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_knowledge_subject ON knowledge(subject)"))

        session = Session(bind=conn)
        row = session.get(SchemaMeta, 1)
        if row is None:
            session.add(SchemaMeta(id=1, static_version=EXPECTED_STATIC_SCHEMA_VERSION))
            print(f"Row: seeded schema_meta.id=1 at {EXPECTED_STATIC_SCHEMA_VERSION!r}")
        elif row.static_version != EXPECTED_STATIC_SCHEMA_VERSION:
            previous = row.static_version
            row.static_version = EXPECTED_STATIC_SCHEMA_VERSION
            row.updated_at = datetime.now(UTC)
            session.add(row)
            print(f"Row: updated schema_meta.id=1: {previous!r} -> {EXPECTED_STATIC_SCHEMA_VERSION!r}")
        else:
            print(f"Row: schema_meta.id=1 already at {EXPECTED_STATIC_SCHEMA_VERSION!r} — nothing to do")
        session.flush()

    print("Schema: idx_knowledge_subject present on knowledge(subject).")
    print("\nMigration v1.96 applied.")


if __name__ == "__main__":
    main()
