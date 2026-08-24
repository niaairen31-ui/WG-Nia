"""Migration v1.93 — `batch.day_number` (TICKET-0075, BRIEF-0075-a).

Adds `batch.day_number` (INTEGER NOT NULL DEFAULT 0 — SQLite requires a
default on `ADD COLUMN ... NOT NULL`) and a unique index on
`(session_id, day_number)`: the day IS the batch ordinal (decision L1),
scoped to its session (decision U1).

Backfill (only runs if `batch` is non-empty): per `session_id`, order
existing rows by `created_at` ascending and assign `1..n` — the column
default of `0` would otherwise collide across every batch in a session
once the unique index is created.

Idempotent: safe to run if the column/index already exist.

Run from the project root:

    python scripts/migrate_v1_93_batch_day_number.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

_env = os.environ.get("WORLD_ENGINE_ENV")
if not _env and not os.environ.get("WORLD_ENGINE_DATABASE_URL"):
    print(
        "migrate_v1_93_batch_day_number.py refuses to run without "
        "WORLD_ENGINE_ENV or WORLD_ENGINE_DATABASE_URL set (fail-closed, "
        f"TICKET-0049) — got: {_env or 'unset'}.",
        file=sys.stderr,
    )
    sys.exit(1)

from sqlalchemy import inspect, text  # noqa: E402

from world_engine.db import engine  # noqa: E402


def _has_day_number_column() -> bool:
    inspector = inspect(engine)
    columns = {c["name"] for c in inspector.get_columns("batch")}
    return "day_number" in columns


def _has_unique_index() -> bool:
    inspector = inspect(engine)
    for idx in inspector.get_indexes("batch"):
        if idx["name"] == "idx_batch_session_day":
            return True
    return False


def main() -> None:
    print("Migration v1.93 — batch.day_number")

    if _has_day_number_column():
        print("`batch.day_number` already present — nothing to do.")
    else:
        with engine.begin() as conn:
            conn.execute(text(
                "ALTER TABLE batch ADD COLUMN day_number INTEGER NOT NULL DEFAULT 0"
            ))
        print("Schema: added column `batch.day_number`.")

    if not _has_day_number_column():
        raise SystemExit("Post-check failed: batch.day_number still missing after ALTER TABLE.")

    with engine.begin() as conn:
        session_ids = [
            row[0] for row in conn.execute(
                text("SELECT DISTINCT session_id FROM batch")
            ).all()
        ]
        touched = 0
        for session_id in session_ids:
            rows = conn.execute(
                text(
                    "SELECT id FROM batch WHERE session_id = :session_id "
                    "ORDER BY created_at ASC"
                ),
                {"session_id": session_id},
            ).all()
            for position, row in enumerate(rows, start=1):
                conn.execute(
                    text("UPDATE batch SET day_number = :day_number WHERE id = :id"),
                    {"day_number": position, "id": row[0]},
                )
                touched += 1
        if touched:
            print(f"Backfill: assigned day_number for {touched} existing batch row(s).")
        else:
            print("Backfill: no existing batch rows — nothing to assign.")

    if _has_unique_index():
        print("`idx_batch_session_day` already present — nothing to do.")
    else:
        with engine.begin() as conn:
            conn.execute(text(
                "CREATE UNIQUE INDEX idx_batch_session_day ON batch (session_id, day_number)"
            ))
        print("Schema: added unique index `idx_batch_session_day`.")

    if not _has_unique_index():
        raise SystemExit("Post-check failed: idx_batch_session_day still missing after CREATE INDEX.")

    print("\nMigration v1.93 applied.")


if __name__ == "__main__":
    main()
