"""Migration v1.73 — `goal_agenda_link` table (goal <-> agenda many-to-many,
TICKET-0020/BRIEF-0020-a).

Adds `goal_agenda_link` (+ `idx_goal_agenda_link_goal`,
`idx_goal_agenda_link_agenda`, and the partial unique
`idx_goal_agenda_link_active` — at most one ACTIVE link per goal/agenda
pair). Purely additive: no data movement, no backfill.

Idempotent: safe to run if the table already exists.

Run from the project root:

    python scripts/migrate_v1_73_goal_agenda_link.py
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

    if models.GoalAgendaLink.__tablename__ not in existing:
        models.GoalAgendaLink.__table__.create(engine)
        print(f"Created table: {models.GoalAgendaLink.__tablename__}")
    else:
        print("`goal_agenda_link` already present — nothing to do.")

    inspector = inspect(engine)
    link_indexes = {ix["name"] for ix in inspector.get_indexes("goal_agenda_link")}
    for name in (
        "idx_goal_agenda_link_goal",
        "idx_goal_agenda_link_agenda",
        "idx_goal_agenda_link_active",
    ):
        if name not in link_indexes:
            raise SystemExit(f"Post-check failed: {name} missing after create.")

    print("Migration v1.73 applied.")


if __name__ == "__main__":
    main()
