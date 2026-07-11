"""Migration to schema v1.74 — add `faction.role_capacities` and
`npc_goal.prerequisites` (TICKET-0024, BRIEF-0024-a).

Both columns are DORMANT this step: stored and creator-editable via this
brief's editors, but read by no AI-path code yet (BRIEF-0024-b reads
`prerequisites`; BRIEF-0024-c reads `role_capacities`'s AI-path).

- `faction.role_capacities` — JSON, nullable, default NULL.
- `npc_goal.prerequisites`  — JSON, nullable, default NULL.

Idempotent: safe to re-run — skips a table's ALTER if the column already
exists on it.

Run from the project root:
    python scripts/migrate_v1_74_completion_mechanics.py
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

    columns_by_table = {
        "faction": "role_capacities",
        "npc_goal": "prerequisites",
    }
    for table, column in columns_by_table.items():
        columns = {c["name"] for c in inspector.get_columns(table)}
        if column in columns:
            print(f"Column '{table}.{column}' already present — skipping.")
            continue
        with engine.begin() as conn:
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} JSON"))
        print(f"Migration v1.74 applied: {table}.{column} column added.")


if __name__ == "__main__":
    main()
