"""Migration v2.03 — drop `world.magic_status` (TICKET-0084, BRIEF-0084-e).

`world.magic_status` was a world-scale magical era
(`dormant | awakening | active | suppressed`) with no reader, no creator
surface, and one writer in the whole repo (`scripts/seed_pilot.py`). Its two
siblings were already dealt with: `location.magic_status` was unplugged from
every prompt surface by decision D3, and `faction.magic_knowledge_level` is
named as `fact_default`'s direct ancestor. With `skill_system` now answering
"does magic exist here" by row presence (B3, TICKET-0084), a world-level
magic column would offer a second, conflicting answer to the same question.
This is the only destructive step of TICKET-0084 — its own migration, its
own commit.

`location.magic_status` is NOT touched by this migration, in any way.

SQLite mechanics: `ALTER TABLE ... DROP COLUMN` (supported since SQLite
3.35, confirmed present here at 3.50.4), same technique as
`migrate_v1_40_drop_character_faction_id.py`. `world` carries no index on
`magic_status`, so no blocking-index drop is needed first.

Idempotent: safe to re-run — reports "already absent" and exits 0 if the
column is gone.

History is sacred: every world's prior `magic_status` value is printed
before the column is dropped, so the destroyed values are visible in the
run log. Post-checks before commit: `world` row count identical before and
after; `id`, `name`, `is_active`, `current_phase` values identical before
and after (checksummed); the column is gone. A checksum mismatch aborts
before commit — this migration never repairs, only refuses.

Run from the project root:

    python scripts/migrate_v2_03_drop_world_magic_status.py
"""

from __future__ import annotations

import hashlib
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

_env = os.environ.get("WORLD_ENGINE_ENV")
if not _env and not os.environ.get("WORLD_ENGINE_DATABASE_URL"):
    print(
        "migrate_v2_03_drop_world_magic_status.py refuses to run without "
        "WORLD_ENGINE_ENV or WORLD_ENGINE_DATABASE_URL set (fail-closed, "
        f"TICKET-0049) — got: {_env or 'unset'}.",
        file=sys.stderr,
    )
    sys.exit(1)

from sqlalchemy import inspect, text  # noqa: E402
from sqlmodel import Session  # noqa: E402

from world_engine import models  # noqa: E402
from world_engine.db import engine  # noqa: E402
from world_engine.schema_version import EXPECTED_STATIC_SCHEMA_VERSION  # noqa: E402


def _checksum_rows() -> tuple[int, str]:
    """Return (row_count, checksum) over id/name/is_active/current_phase,
    ordered by id so the checksum is stable across a rebuild."""
    with engine.connect() as conn:
        rows = conn.execute(text(
            "SELECT id, name, is_active, current_phase FROM world ORDER BY id"
        )).fetchall()
    digest = hashlib.sha256()
    for row in rows:
        digest.update("|".join(str(v) for v in row).encode("utf-8"))
    return len(rows), digest.hexdigest()


def _print_destroyed_values() -> None:
    with engine.connect() as conn:
        rows = conn.execute(text(
            "SELECT id, name, magic_status FROM world ORDER BY id"
        )).fetchall()
    print(f"Destroyed values ({len(rows)} world row(s)), world.id | name | magic_status:")
    for row in rows:
        print(f"  {row[0]} | {row[1]} | {row[2]}")


def _drop_column() -> None:
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE world DROP COLUMN magic_status"))


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
    print("Migration v2.03 — drop world.magic_status")

    inspector = inspect(engine)
    columns = {c["name"] for c in inspector.get_columns("world")}
    if "magic_status" not in columns:
        print("Column 'world.magic_status' already absent — skipping.")
        return

    _print_destroyed_values()

    before_count, before_checksum = _checksum_rows()

    _drop_column()

    inspector = inspect(engine)
    columns_after = {c["name"] for c in inspector.get_columns("world")}
    if "magic_status" in columns_after:
        raise SystemExit(
            "Migration v2.03 aborted, post-check failed: world.magic_status "
            "is still present after DROP COLUMN."
        )

    after_count, after_checksum = _checksum_rows()
    if after_count != before_count:
        raise SystemExit(
            f"Migration v2.03 aborted, post-check failed: world row count "
            f"changed ({before_count} -> {after_count}) — history is sacred, "
            "this migration must not add or remove rows."
        )
    if after_checksum != before_checksum:
        raise SystemExit(
            "Migration v2.03 aborted, post-check failed: checksum over "
            "id/name/is_active/current_phase changed — a remaining column's "
            "value was altered by the drop. This migration never repairs, "
            "only refuses."
        )

    print(f"Post-check: world row count unchanged at {after_count}.")
    print("Post-check: id/name/is_active/current_phase checksum unchanged.")

    _converge_schema_meta()
    print("\nMigration v2.03 applied: world.magic_status column dropped.")


if __name__ == "__main__":
    main()
