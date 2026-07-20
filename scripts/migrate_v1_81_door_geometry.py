"""Migration to schema v1.81 — inter-location door geometry (TICKET-0034,
BRIEF-0034-a).

Fifth step of the spatial / Play mode workstream (0029 geometry -> 0030
collision -> 0031 presence/proximity -> 0032 canvas/WASD -> 0034 doors).
Adds persistent door-point storage the server can resolve arrival against
(BRIEF-0034-b) and the client can draw (BRIEF-0034-d) — nothing that
resolves, judges or moves ships here.

Purely additive, no data copy, no seed rows, no validation pass (nothing to
transform):
  a. Create `door` table.
  b. Create unique index `idx_door_target` on `(location_id,
     target_location_id)`.

Guards check table existence and index existence INDEPENDENTLY — a
partially applied prior run completes only the missing part, never skips
wholesale (CLAUDE.md: migration guards by column/index existence, not table
existence; v1.77 lesson, v1.80's own guard shape). Idempotent: a fully
applied run reports "already applied", zero writes.

Run from the project root:
    python scripts/migrate_v1_81_door_geometry.py
"""

from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

from sqlalchemy import inspect, text  # noqa: E402

from world_engine.db import engine  # noqa: E402


def _create_door_table(conn) -> None:
    conn.execute(text("""
        CREATE TABLE door (
          id                 TEXT PRIMARY KEY,
          world_id           TEXT NOT NULL REFERENCES world(id),
          location_id        TEXT NOT NULL REFERENCES entity(id),
          target_location_id TEXT NOT NULL REFERENCES entity(id),
          x                  REAL NOT NULL,
          y                  REAL NOT NULL,
          created_at         DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """))


def _create_door_target_index(conn) -> None:
    conn.execute(text(
        "CREATE UNIQUE INDEX idx_door_target "
        "ON door(location_id, target_location_id)"
    ))


def main() -> None:
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    has_door = "door" in tables
    has_index = has_door and any(
        idx["name"] == "idx_door_target" for idx in inspector.get_indexes("door")
    )

    if has_door and has_index:
        print("Migration v1.81 already applied — door table and idx_door_target "
              "index both present, zero writes.")
        return

    applied = []
    with engine.begin() as conn:
        if not has_door:
            _create_door_table(conn)
            applied.append("door table")
        if not has_index:
            _create_door_target_index(conn)
            applied.append("idx_door_target index")

    print("Migration v1.81 applied: " + ", ".join(applied) + ".")


if __name__ == "__main__":
    main()
