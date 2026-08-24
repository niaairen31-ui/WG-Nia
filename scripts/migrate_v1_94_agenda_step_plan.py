"""Migration v1.94 — `agenda_step.cost`/`domain` + `agenda_step_requirement`
(TICKET-0075, BRIEF-0075-b — the plan-emission-and-budget step).

Two independent, purely additive pieces:

- `agenda_step.cost`/`agenda_step.domain` — two new nullable columns on an
  EXISTING table (`migrate_v1_91_npc_goal_kind.py` precedent): SQLite has no
  `ADD CONSTRAINT`, so `cost`'s CHECK rides on the `ALTER TABLE ... ADD
  COLUMN` statement itself. NULL for every pre-existing (NPC) step — no
  backfill.
- `agenda_step_requirement` — a brand-new table
  (`migrate_v1_92_npc_schedule.py` precedent): both CHECKs and the unique
  index ride on `CREATE TABLE` via the model's own `__table_args__`, so a
  fresh `create_all` and this migration produce identical DDL.

Idempotent: safe to run if either piece is already applied.

Run from the project root:

    python scripts/migrate_v1_94_agenda_step_plan.py
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
        "migrate_v1_94_agenda_step_plan.py refuses to run without "
        "WORLD_ENGINE_ENV or WORLD_ENGINE_DATABASE_URL set (fail-closed, "
        f"TICKET-0049) — got: {_env or 'unset'}.",
        file=sys.stderr,
    )
    sys.exit(1)

from sqlalchemy import inspect, text  # noqa: E402

from world_engine import models  # noqa: E402
from world_engine.db import engine  # noqa: E402


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


def _agenda_step_columns() -> set[str]:
    inspector = inspect(engine)
    return {c["name"] for c in inspector.get_columns("agenda_step")}


def main() -> None:
    print("Migration v1.94 — agenda_step.cost/domain, agenda_step_requirement")

    columns = _agenda_step_columns()
    if "cost" in columns:
        print("`agenda_step.cost` already present — nothing to do.")
    else:
        with engine.begin() as conn:
            conn.execute(text(
                "ALTER TABLE agenda_step ADD COLUMN cost INTEGER "
                "CHECK (cost IS NULL OR cost BETWEEN 1 AND 4)"
            ))
        print("Schema: added column `agenda_step.cost`.")

    if "domain" in columns:
        print("`agenda_step.domain` already present — nothing to do.")
    else:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE agenda_step ADD COLUMN domain TEXT"))
        print("Schema: added column `agenda_step.domain`.")

    post_columns = _agenda_step_columns()
    if "cost" not in post_columns or "domain" not in post_columns:
        raise SystemExit(
            "Post-check failed: agenda_step.cost/domain still missing after ALTER TABLE."
        )

    created = _ensure_table(models.AgendaStepRequirement)
    print(
        f"Schema: {'created table' if created else 'table already present'} "
        "`agenda_step_requirement`"
    )
    applied = _ensure_indexes(models.AgendaStepRequirement)
    if applied:
        print(f"Schema: created index(es) on `agenda_step_requirement`: {', '.join(applied)}")
    else:
        print("Schema: indexes on `agenda_step_requirement` already present — nothing to do.")

    with engine.connect() as conn:
        bad_cost = conn.execute(text(
            "SELECT COUNT(*) FROM agenda_step WHERE cost IS NOT NULL AND (cost < 1 OR cost > 4)"
        )).scalar_one()
        if bad_cost != 0:
            raise SystemExit(
                f"Post-check failed: {bad_cost} agenda_step row(s) hold a cost outside 1..4."
            )

    print("\nMigration v1.94 applied.")


if __name__ == "__main__":
    main()
