"""Migration v1.92 — `npc_schedule` table + `world.current_phase` column
(TICKET-0074, BRIEF-0074-a).

Two independent pieces, both purely additive:

- `npc_schedule` — a brand-new table (`_ensure_table`/`_ensure_indexes`,
  `migrate_v1_89_conversation_window_config.py` precedent): its CHECK
  constraint rides on `CREATE TABLE` via the model's own `__table_args__`,
  so a fresh `create_all` and this migration produce identical DDL.
- `world.current_phase` — a new column on an EXISTING table
  (`migrate_v1_91_npc_goal_kind.py` precedent): SQLite has no
  `ADD CONSTRAINT`, so the CHECK rides on the `ALTER TABLE ... ADD COLUMN`
  statement itself — the same asymmetry v1.91 documents.

No seeding, no backfill (B1: the schedule table is sparse by decision).
Idempotent: safe to run if either piece is already applied.

Run from the project root:

    python scripts/migrate_v1_92_npc_schedule.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

_env = os.environ.get("WORLD_ENGINE_ENV")
if not _env and not os.environ.get("WORLD_ENGINE_DATABASE_URL"):
    print(
        "migrate_v1_92_npc_schedule.py refuses to run without "
        "WORLD_ENGINE_ENV or WORLD_ENGINE_DATABASE_URL set (fail-closed, "
        f"TICKET-0049) — got: {_env or 'unset'}.",
        file=sys.stderr,
    )
    sys.exit(1)

from sqlalchemy import inspect, text  # noqa: E402

from world_engine import models  # noqa: E402
from world_engine.db import engine  # noqa: E402
from world_engine.models.schedule import SCHEDULE_PHASES  # noqa: E402


def _ensure_table(model: type) -> bool:
    inspector = inspect(engine)
    if model.__tablename__ in inspector.get_table_names():
        return False
    model.__table__.create(engine)
    return True


def _index_names(tablename: str) -> set[str]:
    inspector = inspect(engine)
    return {ix["name"] for ix in inspector.get_indexes(tablename)}


def _ensure_indexes(model: type) -> list[str]:
    applied: list[str] = []
    existing = _index_names(model.__tablename__)
    for index in model.__table__.indexes:
        if index.name not in existing:
            index.create(engine)
            applied.append(index.name)
    return applied


def _has_current_phase_column() -> bool:
    inspector = inspect(engine)
    columns = {c["name"] for c in inspector.get_columns("world")}
    return "current_phase" in columns


def main() -> None:
    print("Migration v1.92 — npc_schedule, world.current_phase")

    created = _ensure_table(models.NpcSchedule)
    print(f"Schema: {'created table' if created else 'table already present'} `npc_schedule`")
    applied = _ensure_indexes(models.NpcSchedule)
    if applied:
        print(f"Schema: created index(es) on `npc_schedule`: {', '.join(applied)}")
    else:
        print("Schema: indexes on `npc_schedule` already present — nothing to do.")

    phase_list = ",".join(f"'{p}'" for p in SCHEDULE_PHASES)
    if _has_current_phase_column():
        print("`world.current_phase` already present — nothing to do.")
    else:
        with engine.begin() as conn:
            conn.execute(text(
                "ALTER TABLE world ADD COLUMN current_phase TEXT NOT NULL DEFAULT 'matin' "
                f"CHECK (current_phase IN ({phase_list}))"
            ))
        print("Schema: added column `world.current_phase`.")

    if not _has_current_phase_column():
        raise SystemExit("Post-check failed: world.current_phase still missing after ALTER TABLE.")

    with engine.connect() as conn:
        bad_phase = conn.execute(text(
            f"SELECT COUNT(*) FROM world WHERE current_phase NOT IN ({phase_list})"
        )).scalar_one()
        if bad_phase != 0:
            raise SystemExit(
                f"Post-check failed: {bad_phase} world row(s) hold a current_phase outside {SCHEDULE_PHASES}."
            )

        bad_schedule_phase = conn.execute(text(
            f"SELECT COUNT(*) FROM npc_schedule WHERE phase NOT IN ({phase_list})"
        )).scalar_one()
        if bad_schedule_phase != 0:
            raise SystemExit(
                f"Post-check failed: {bad_schedule_phase} npc_schedule row(s) hold a "
                f"phase outside {SCHEDULE_PHASES}."
            )

    print("\nMigration v1.92 applied.")


if __name__ == "__main__":
    main()
