"""Migration v1.86 — `schema_meta` (static-plane schema version + fail-closed
boot guard, C2 two-plane governance plane 1, TICKET-0044, BRIEF-0044-a).

Two independent guards (table existence, singleton row existence — v1.77/
v1.84 lesson): a partially applied prior run completes only the missing
part on re-run, never skips wholesale. A migration is the ONLY writer of
the `schema_meta` row: on a second run it converges `static_version` (and
`updated_at`) to the CURRENT code version rather than skipping — the row
must always end up describing "what this migration run believes is true",
never a stale value from an older run.

Run from the project root:
    python scripts/migrate_v1_86_schema_meta.py
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

from sqlalchemy import inspect  # noqa: E402
from sqlmodel import Session  # noqa: E402

from world_engine.models import SchemaMeta  # noqa: E402
from world_engine.db import engine  # noqa: E402
from world_engine.schema_version import EXPECTED_STATIC_SCHEMA_VERSION  # noqa: E402


def _ensure_table() -> bool:
    inspector = inspect(engine)
    if SchemaMeta.__tablename__ in inspector.get_table_names():
        return False
    SchemaMeta.__table__.create(engine)
    return True


def _seed_or_update_row(session: Session) -> str:
    row = session.get(SchemaMeta, 1)
    if row is None:
        session.add(SchemaMeta(id=1, static_version=EXPECTED_STATIC_SCHEMA_VERSION))
        return f"seeded schema_meta.id=1 at {EXPECTED_STATIC_SCHEMA_VERSION!r}"
    if row.static_version == EXPECTED_STATIC_SCHEMA_VERSION:
        return f"already present at {EXPECTED_STATIC_SCHEMA_VERSION!r} — nothing to do"
    previous = row.static_version
    row.static_version = EXPECTED_STATIC_SCHEMA_VERSION
    row.updated_at = datetime.now(UTC)
    session.add(row)
    return f"updated schema_meta.id=1: {previous!r} -> {EXPECTED_STATIC_SCHEMA_VERSION!r}"


def main() -> None:
    print("Migration v1.86 — schema_meta")

    created = _ensure_table()
    print(f"Schema: {'created table `schema_meta`' if created else '`schema_meta` table already present'}")

    try:
        with Session(engine) as session:
            action = _seed_or_update_row(session)
            session.commit()
            print(f"Row: {action}")
    except Exception:
        print("\nERROR — transaction rolled back.", file=sys.stderr)
        raise

    print("\nMigration v1.86 applied.")


if __name__ == "__main__":
    main()
