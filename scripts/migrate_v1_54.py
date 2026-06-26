"""Migration v1.54 — active world selection (BRIEF-43).

Adds `world.is_active BOOLEAN NOT NULL DEFAULT FALSE` and the partial unique
index `idx_world_one_active` (at most one active world at a time).

On a database that has exactly one `world` row and no active world yet, that
row is marked active — preserving single-world behavior with zero functional
change. Databases with zero or several `world` rows are left for the creator
to activate explicitly via the cockpit selector.

Idempotent: safe to run if the column/index already exist.

Run from the project root:

    python scripts/migrate_v1_54.py
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
    cols = {c["name"] for c in inspector.get_columns("world")}

    if "is_active" not in cols:
        with engine.begin() as conn:
            conn.execute(
                text("ALTER TABLE world ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT 0")
            )
        print("Added column 'world.is_active' (BOOLEAN NOT NULL DEFAULT FALSE).")
    else:
        print("Column 'world.is_active' already exists — nothing to do.")

    indexes = {i["name"] for i in inspector.get_indexes("world")}
    if "idx_world_one_active" not in indexes:
        with engine.begin() as conn:
            conn.execute(text(
                "CREATE UNIQUE INDEX idx_world_one_active ON world(is_active) "
                "WHERE is_active = 1"
            ))
        print("Created index 'idx_world_one_active' (partial unique on is_active).")
    else:
        print("Index 'idx_world_one_active' already exists — nothing to do.")

    with engine.begin() as conn:
        worlds = conn.execute(text("SELECT id, is_active FROM world")).fetchall()
        if len(worlds) == 1 and not worlds[0][1]:
            conn.execute(
                text("UPDATE world SET is_active = 1 WHERE id = :id"),
                {"id": worlds[0][0]},
            )
            print(f"Marked the sole world row ({worlds[0][0]!r}) active.")

    print("Migration v1.54 applied.")


if __name__ == "__main__":
    main()
