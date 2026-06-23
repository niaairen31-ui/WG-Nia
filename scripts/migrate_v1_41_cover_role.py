"""Migration to schema v1.41 — add `faction_membership.cover_role` (BRIEF-30).

Cas 3 (double agent): a character can be a PUBLICLY-known member of a
faction (`is_secret = FALSE`) while presenting a false role. The true
`role` ("espion") stays creator-only; `cover_role` ("membre") is the
prompt-facing façade every reader sees. `read_public_memberships`
(`src/world_engine/context.py`) resolves `cover_role ?? role` so the true
role never crosses the accessor boundary when a cover is set.

No backfill: the new column defaults NULL, so `NULL ?? role = role` and
every existing membership renders exactly as before.

Idempotent: safe to re-run — skips straight to "already present" if the
column already exists.

Run from the project root:
    python scripts/migrate_v1_41_cover_role.py
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
    columns = {c["name"] for c in inspector.get_columns("faction_membership")}

    if "cover_role" in columns:
        print("Column 'faction_membership.cover_role' already present — skipping.")
        return

    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE faction_membership ADD COLUMN cover_role TEXT"))

    print("Migration v1.41 applied: faction_membership.cover_role column added.")


if __name__ == "__main__":
    main()
