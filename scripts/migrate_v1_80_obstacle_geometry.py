"""Migration to schema v1.80 — intra-location obstacle geometry
(TICKET-0029, BRIEF-0029-a).

First step of the spatial / Play mode workstream (0029 -> 0030 -> 0031 ->
0032). Adds persistent wall geometry storage the server can judge movement
against (collision endpoint, ticket 0030) and the client can draw (canvas
renderer, ticket 0032) — nothing that moves ships here.

Purely additive, no data copy, no seed rows, no validation pass (nothing to
transform):
  a. Create `obstacle` + `obstacle_vertex` tables and both indexes
     (`idx_obstacle_location`, unique `idx_obstacle_vertex_order`).
  b. `ALTER TABLE location ADD COLUMN bounds_width REAL` and
     `bounds_height REAL` (nullable, no default). NULL = no spatial mode.

Guards check column existence on `location` and table existence for the two
new tables INDEPENDENTLY — a partially applied prior run completes only the
missing parts, never skips wholesale (CLAUDE.md: migration guards by column
existence, not table existence). Idempotent: a fully applied run reports
"already applied", zero writes.

Run from the project root:
    python scripts/migrate_v1_80_obstacle_geometry.py
"""

from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

from sqlalchemy import inspect, text  # noqa: E402

from world_engine.db import engine  # noqa: E402


def _create_obstacle_table(conn) -> None:
    conn.execute(text("""
        CREATE TABLE obstacle (
          id          TEXT PRIMARY KEY,
          world_id    TEXT NOT NULL REFERENCES world(id),
          location_id TEXT NOT NULL REFERENCES entity(id),
          created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """))
    conn.execute(text(
        "CREATE INDEX idx_obstacle_location ON obstacle(location_id)"
    ))


def _create_obstacle_vertex_table(conn) -> None:
    conn.execute(text("""
        CREATE TABLE obstacle_vertex (
          id            TEXT PRIMARY KEY,
          obstacle_id   TEXT NOT NULL REFERENCES obstacle(id),
          vertex_order  INTEGER NOT NULL,
          x             REAL NOT NULL,
          y             REAL NOT NULL
        )
    """))
    conn.execute(text(
        "CREATE UNIQUE INDEX idx_obstacle_vertex_order "
        "ON obstacle_vertex(obstacle_id, vertex_order)"
    ))


def main() -> None:
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    location_columns = {c["name"] for c in inspector.get_columns("location")}

    has_obstacle = "obstacle" in tables
    has_obstacle_vertex = "obstacle_vertex" in tables
    has_bounds_width = "bounds_width" in location_columns
    has_bounds_height = "bounds_height" in location_columns

    if has_obstacle and has_obstacle_vertex and has_bounds_width and has_bounds_height:
        print("Migration v1.80 already applied — obstacle/obstacle_vertex tables and "
              "location bounds_width/bounds_height columns all present, zero writes.")
        return

    applied = []
    with engine.begin() as conn:
        if not has_obstacle:
            _create_obstacle_table(conn)
            applied.append("obstacle table + idx_obstacle_location")
        if not has_obstacle_vertex:
            _create_obstacle_vertex_table(conn)
            applied.append("obstacle_vertex table + idx_obstacle_vertex_order")
        if not has_bounds_width:
            conn.execute(text("ALTER TABLE location ADD COLUMN bounds_width REAL"))
            applied.append("location.bounds_width column")
        if not has_bounds_height:
            conn.execute(text("ALTER TABLE location ADD COLUMN bounds_height REAL"))
            applied.append("location.bounds_height column")

    print("Migration v1.80 applied: " + ", ".join(applied) + ".")


if __name__ == "__main__":
    main()
