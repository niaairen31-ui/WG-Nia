"""Migration v1.57 — one player character per user per world (BRIEF-46).

Adds `character.world_id TEXT NOT NULL REFERENCES world(id)`, denormalized
from `entity.world_id` (same pattern as `relation.world_id` — needed because
SQLite indexes can't reach across a join to `entity`). Backfills every
existing `character` row from its `entity.world_id`. Adds `idx_character_world`
and the partial unique index `idx_character_one_pc_per_user_world`
(`character(world_id, user_id) WHERE character_type = 'player'`), enforcing
at most one player character per (world, user) — multiplayer-safe, since the
index is scoped per world, not world-wide.

Idempotent: safe to run if the column/indexes already exist.

Run from the project root:

    python scripts/migrate_v1_57.py
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
    cols = {c["name"] for c in inspector.get_columns("character")}

    if "world_id" not in cols:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE character ADD COLUMN world_id TEXT REFERENCES world(id)"))
            conn.execute(text(
                "UPDATE character SET world_id = ("
                "  SELECT entity.world_id FROM entity WHERE entity.id = character.id"
                ")"
            ))
        print("Added column 'character.world_id' and backfilled it from entity.world_id.")
    else:
        print("Column 'character.world_id' already exists — nothing to do.")

    indexes = {i["name"] for i in inspector.get_indexes("character")}

    if "idx_character_world" not in indexes:
        with engine.begin() as conn:
            conn.execute(text("CREATE INDEX idx_character_world ON character(world_id)"))
        print("Created index 'idx_character_world'.")
    else:
        print("Index 'idx_character_world' already exists — nothing to do.")

    if "idx_character_one_pc_per_user_world" not in indexes:
        with engine.begin() as conn:
            conn.execute(text(
                "CREATE UNIQUE INDEX idx_character_one_pc_per_user_world "
                "ON character(world_id, user_id) WHERE character_type = 'player'"
            ))
        print("Created index 'idx_character_one_pc_per_user_world' (partial unique).")
    else:
        print("Index 'idx_character_one_pc_per_user_world' already exists — nothing to do.")

    print("Migration v1.57 applied.")


if __name__ == "__main__":
    main()
