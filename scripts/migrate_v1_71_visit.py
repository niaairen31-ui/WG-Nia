"""Migration v1.71 — `visit` table (return-visit delta, TICKET-0016/BRIEF-0016-a).

Adds `visit` (+ `idx_visit_player_location`). Purely additive: no data
movement, no backfill — the table is born empty, so every location counts as
a first visit once (by design, G2's no-backfill drafting decision).

Idempotent: safe to run if the table already exists.

Run from the project root:

    python scripts/migrate_v1_71_visit.py
"""

from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

from sqlalchemy import inspect  # noqa: E402

from world_engine import models  # noqa: E402
from world_engine.db import engine  # noqa: E402


def main() -> None:
    inspector = inspect(engine)
    existing = set(inspector.get_table_names())

    if models.Visit.__tablename__ not in existing:
        models.Visit.__table__.create(engine)
        print(f"Created table: {models.Visit.__tablename__}")
    else:
        print("`visit` already present — nothing to do.")

    inspector = inspect(engine)
    indexes = {ix["name"] for ix in inspector.get_indexes("visit")}
    if "idx_visit_player_location" not in indexes:
        raise SystemExit("Post-check failed: idx_visit_player_location missing after create.")

    print("Migration v1.71 applied.")


if __name__ == "__main__":
    main()
