"""Migration v1.70 — `proposed_mutation.tick_id` (TICKET-0014/BRIEF-0014-b).

Adds `proposed_mutation.tick_id TEXT NULL` + `idx_mutation_tick` on it.
World-tick proposals (`source_type="world_tick"`) carry a shared `tick_id`
per invocation (one UUID per `run_world_tick` call) with BOTH FKs
(`pass_play_id`, `conversation_id`) NULL — `tick_id` is that source's
anchor, read by the duplicate-application guard's tick branch and the
queue's `TICK ·xxxx` badge. Purely additive: no backfill, existing rows are
born NULL.

Idempotent: safe to run if the column/index already exist.

Run from the project root:

    python scripts/migrate_v1_70_tick_id.py
"""

from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

from sqlalchemy import inspect, text  # noqa: E402

from world_engine.db import engine  # noqa: E402


def main() -> None:
    inspector = inspect(engine)
    cols = {c["name"] for c in inspector.get_columns("proposed_mutation")}

    if "tick_id" not in cols:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE proposed_mutation ADD COLUMN tick_id TEXT"))
        print("Added column 'proposed_mutation.tick_id' (TEXT NULL).")
    else:
        print("Column 'proposed_mutation.tick_id' already exists — nothing to do.")

    indexes = {i["name"] for i in inspector.get_indexes("proposed_mutation")}
    if "idx_mutation_tick" not in indexes:
        with engine.begin() as conn:
            conn.execute(text("CREATE INDEX idx_mutation_tick ON proposed_mutation(tick_id)"))
        print("Created index 'idx_mutation_tick'.")
    else:
        print("Index 'idx_mutation_tick' already exists — nothing to do.")

    print("Migration v1.70 applied.")


if __name__ == "__main__":
    main()
