"""Migration to schema v1.83 — NPC group agent staging substrate (TICKET-0037,
BRIEF-0037-a).

First step of the NPC group generation agent workstream: ephemeral staging
tables for batch NPC drafting, no LLM call and no canon write yet
(0037-b/c). Purely additive, no data copy, no seed rows, no validation pass:
  a. Create `npc_batch` table.
  b. Create `npc_batch_row` table.
  c. Create index `idx_npc_batch_row_batch` on `npc_batch_row(batch_id)`.

Guards check table existence and index existence INDEPENDENTLY — a
partially applied prior run completes only the missing part, never skips
wholesale (CLAUDE.md: migration guards by column/index existence, not table
existence; v1.77 lesson, v1.81/v1.82's own guard shape). Idempotent: a fully
applied run reports "already applied", zero writes.

Run from the project root:
    python scripts/migrate_v1_83_npc_batch.py
"""

from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

from sqlalchemy import inspect, text  # noqa: E402

from world_engine.db import engine  # noqa: E402


def _create_npc_batch_table(conn) -> None:
    conn.execute(text("""
        CREATE TABLE npc_batch (
          id          TEXT PRIMARY KEY,
          world_id    TEXT NOT NULL REFERENCES world(id),
          status      TEXT NOT NULL DEFAULT 'open',
          scope       JSON NOT NULL,
          npcs_total  INTEGER NOT NULL DEFAULT 0,
          npcs_done   INTEGER NOT NULL DEFAULT 0,
          created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
          closed_at   DATETIME
        )
    """))


def _create_npc_batch_row_table(conn) -> None:
    conn.execute(text("""
        CREATE TABLE npc_batch_row (
          id          TEXT PRIMARY KEY,
          batch_id    TEXT NOT NULL REFERENCES npc_batch(id),
          line_index  INTEGER NOT NULL,
          kind        TEXT NOT NULL,
          payload     JSON NOT NULL,
          row_status  TEXT NOT NULL DEFAULT 'proposed',
          created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
          updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """))


def _create_npc_batch_row_index(conn) -> None:
    conn.execute(text(
        "CREATE INDEX idx_npc_batch_row_batch ON npc_batch_row(batch_id)"
    ))


def main() -> None:
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    has_npc_batch = "npc_batch" in tables
    has_npc_batch_row = "npc_batch_row" in tables
    has_index = has_npc_batch_row and any(
        idx["name"] == "idx_npc_batch_row_batch"
        for idx in inspector.get_indexes("npc_batch_row")
    )

    if has_npc_batch and has_npc_batch_row and has_index:
        print("Migration v1.83 already applied — npc_batch, npc_batch_row "
              "and idx_npc_batch_row_batch all present, zero writes.")
        return

    applied = []
    with engine.begin() as conn:
        if not has_npc_batch:
            _create_npc_batch_table(conn)
            applied.append("npc_batch table")
        if not has_npc_batch_row:
            _create_npc_batch_row_table(conn)
            applied.append("npc_batch_row table")
            has_index = False  # freshly created table never has the index yet
        if not has_index:
            _create_npc_batch_row_index(conn)
            applied.append("idx_npc_batch_row_batch index")

    print("Migration v1.83 applied: " + ", ".join(applied) + ".")


if __name__ == "__main__":
    main()
