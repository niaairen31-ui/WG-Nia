"""Migration to schema v1.82 — NPC link agent staging substrate (TICKET-0036,
BRIEF-0036-a).

First step of the NPC link agent workstream: ephemeral staging tables for
batch relation/knowledge authoring, no LLM call and no canon write yet
(0036-b/c). Purely additive, no data copy, no seed rows, no validation pass:
  a. Create `link_batch` table.
  b. Create `link_batch_row` table.
  c. Create index `idx_link_batch_row_batch` on `link_batch_row(batch_id)`.

Guards check table existence and index existence INDEPENDENTLY — a
partially applied prior run completes only the missing part, never skips
wholesale (CLAUDE.md: migration guards by column/index existence, not table
existence; v1.77 lesson, v1.81's own guard shape). Idempotent: a fully
applied run reports "already applied", zero writes.

Run from the project root:
    python scripts/migrate_v1_82_link_batch.py
"""

from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

from sqlalchemy import inspect, text  # noqa: E402

from world_engine.db import engine  # noqa: E402


def _create_link_batch_table(conn) -> None:
    conn.execute(text("""
        CREATE TABLE link_batch (
          id               TEXT PRIMARY KEY,
          world_id         TEXT NOT NULL REFERENCES world(id),
          status           TEXT NOT NULL DEFAULT 'open',
          scope            JSON NOT NULL,
          pairs_total      INTEGER NOT NULL DEFAULT 0,
          pairs_done       INTEGER NOT NULL DEFAULT 0,
          coherence_status TEXT,
          coherence_findings JSON DEFAULT '[]',
          created_at       DATETIME DEFAULT CURRENT_TIMESTAMP,
          closed_at        DATETIME
        )
    """))


def _create_link_batch_row_table(conn) -> None:
    conn.execute(text("""
        CREATE TABLE link_batch_row (
          id          TEXT PRIMARY KEY,
          batch_id    TEXT NOT NULL REFERENCES link_batch(id),
          pair_a_id   TEXT NOT NULL REFERENCES entity(id),
          pair_b_id   TEXT NOT NULL REFERENCES entity(id),
          kind        TEXT NOT NULL,
          payload     JSON NOT NULL,
          row_status  TEXT NOT NULL DEFAULT 'proposed',
          created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
          updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """))


def _create_link_batch_row_index(conn) -> None:
    conn.execute(text(
        "CREATE INDEX idx_link_batch_row_batch ON link_batch_row(batch_id)"
    ))


def main() -> None:
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    has_link_batch = "link_batch" in tables
    has_link_batch_row = "link_batch_row" in tables
    has_index = has_link_batch_row and any(
        idx["name"] == "idx_link_batch_row_batch"
        for idx in inspector.get_indexes("link_batch_row")
    )

    if has_link_batch and has_link_batch_row and has_index:
        print("Migration v1.82 already applied — link_batch, link_batch_row "
              "and idx_link_batch_row_batch all present, zero writes.")
        return

    applied = []
    with engine.begin() as conn:
        if not has_link_batch:
            _create_link_batch_table(conn)
            applied.append("link_batch table")
        if not has_link_batch_row:
            _create_link_batch_row_table(conn)
            applied.append("link_batch_row table")
            has_index = False  # freshly created table never has the index yet
        if not has_index:
            _create_link_batch_row_index(conn)
            applied.append("idx_link_batch_row_batch index")

    print("Migration v1.82 applied: " + ", ".join(applied) + ".")


if __name__ == "__main__":
    main()
