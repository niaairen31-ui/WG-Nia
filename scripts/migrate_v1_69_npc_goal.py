"""Migration v1.69 — `npc_goal` table (NPC interiority, TICKET-0013/BRIEF-0013-a).

Adds `npc_goal` (+ `ck_npc_goal_horizon`, `ck_npc_goal_status`,
`idx_npc_goal_npc_status`). Purely additive: no data movement, no backfill.

Idempotent: safe to run if the table already exists.

Run from the project root:

    python scripts/migrate_v1_69_npc_goal.py
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

    if models.NpcGoal.__tablename__ not in existing:
        models.NpcGoal.__table__.create(engine)
        print(f"Created table: {models.NpcGoal.__tablename__}")
    else:
        print("`npc_goal` already present — nothing to do.")

    inspector = inspect(engine)
    indexes = {ix["name"] for ix in inspector.get_indexes("npc_goal")}
    if "idx_npc_goal_npc_status" not in indexes:
        raise SystemExit("Post-check failed: idx_npc_goal_npc_status missing after create.")

    checks = {ck["name"] for ck in inspector.get_check_constraints("npc_goal")}
    for name in ("ck_npc_goal_horizon", "ck_npc_goal_status"):
        if name not in checks:
            raise SystemExit(f"Post-check failed: {name} missing after create.")

    print("Migration v1.69 applied.")


if __name__ == "__main__":
    main()
