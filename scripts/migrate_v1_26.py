"""Migration to schema v1.26 — add discoverable_detail table.

New table: discoverable_detail
  - Stores pre-seeded hidden content per location for explicit search reveals.
  - NEVER read by any context assembler; content reaches prompts only via
    post-selection injection on a partial/success perception search.
  - access_level: 'hidden' (requires roll) | 'ambient' (passive, DORMANT).
  - discovery_threshold: DORMANT this migration — not yet compared against rolls.
  - discovered: flipped TRUE by _apply_mutation when the engine-proposed
    new_knowledge mutation is approved by the creator.

Idempotent: safe to run if the table already exists.

Run from the project root:
    python scripts/migrate_v1_26.py
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
    tables = inspector.get_table_names()

    if "discoverable_detail" in tables:
        print("Table 'discoverable_detail' already exists — nothing to do.")
        return

    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE discoverable_detail (
                id                  TEXT PRIMARY KEY,
                world_id            TEXT NOT NULL REFERENCES world(id),
                location_id         TEXT NOT NULL REFERENCES entity(id),
                subject             TEXT NOT NULL,
                content             TEXT NOT NULL,
                access_level        TEXT NOT NULL DEFAULT 'hidden',
                discovery_threshold INTEGER NOT NULL DEFAULT 0
                    CHECK (discovery_threshold BETWEEN 0 AND 12),
                discovered          BOOLEAN NOT NULL DEFAULT FALSE,
                created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at          DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conn.execute(text(
            "CREATE INDEX idx_discoverable_location ON discoverable_detail(location_id)"
        ))
        conn.execute(text(
            "CREATE INDEX idx_discoverable_world ON discoverable_detail(world_id)"
        ))

    print("Migration v1.26 applied: discoverable_detail table and indexes created.")


if __name__ == "__main__":
    main()
