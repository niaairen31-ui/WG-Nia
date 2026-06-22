"""Migration v1.38 — faction structure & resources (BRIEF-26).

Adds three nullable columns to `faction`, all DORMANT (placed-but-unread,
same posture as `equipped` / `connects_to`):

  parent_faction_id TEXT REFERENCES entity(id)  -- containment tree, mirror
                      of location.parent_location_id. NULL = root faction.
  scope             TEXT  -- descriptive scale label (global | national |
                      regional | local | other), NOT derived from tree depth.
  goals             TEXT  -- prose: what the faction is trying to do.

Plus the traversal index `idx_faction_parent` (unused today — no assembler
or guard reads `parent_faction_id` yet; the index exists for the deferred
consumer, the membership/C1 follow-up).

No CHECK constraint on any of the three columns. Creator-CRUD only.

Idempotent: checks for the columns first, safe to re-run.

Run from the project root:

    python scripts/migrate_v1_38_faction_structure.py
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
    cols = {c["name"] for c in inspector.get_columns("faction")}

    if {"parent_faction_id", "scope", "goals"} <= cols:
        print("Columns already exist on 'faction' — nothing to do.")
        return

    with engine.begin() as conn:
        if "parent_faction_id" not in cols:
            conn.execute(text("ALTER TABLE faction ADD COLUMN parent_faction_id TEXT REFERENCES entity(id)"))
        if "scope" not in cols:
            conn.execute(text("ALTER TABLE faction ADD COLUMN scope TEXT"))
        if "goals" not in cols:
            conn.execute(text("ALTER TABLE faction ADD COLUMN goals TEXT"))
        existing_indexes = {i["name"] for i in inspector.get_indexes("faction")}
        if "idx_faction_parent" not in existing_indexes:
            conn.execute(text("CREATE INDEX idx_faction_parent ON faction(parent_faction_id)"))

    print("Migration v1.38 applied: faction.parent_faction_id/scope/goals + idx_faction_parent created.")


if __name__ == "__main__":
    main()
