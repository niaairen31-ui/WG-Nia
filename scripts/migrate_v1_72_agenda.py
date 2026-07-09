"""Migration v1.72 — `agenda` + `agenda_step` tables (structured faction
intrigues, TICKET-0018/BRIEF-0018-a).

Adds `agenda` (+ `ck_agenda_status`, `idx_agenda_owner_status`) and
`agenda_step` (+ `ck_agenda_step_status`, `idx_agenda_step_agenda`, and the
partial unique `idx_agenda_step_one_active` — at most one ACTIVE step per
agenda). Purely additive: no data movement, no backfill.

Idempotent: safe to run if the tables already exist.

Run from the project root:

    python scripts/migrate_v1_72_agenda.py
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

    if models.Agenda.__tablename__ not in existing:
        models.Agenda.__table__.create(engine)
        print(f"Created table: {models.Agenda.__tablename__}")
    else:
        print("`agenda` already present — nothing to do.")

    inspector = inspect(engine)
    existing = set(inspector.get_table_names())

    if models.AgendaStep.__tablename__ not in existing:
        models.AgendaStep.__table__.create(engine)
        print(f"Created table: {models.AgendaStep.__tablename__}")
    else:
        print("`agenda_step` already present — nothing to do.")

    inspector = inspect(engine)

    agenda_indexes = {ix["name"] for ix in inspector.get_indexes("agenda")}
    if "idx_agenda_owner_status" not in agenda_indexes:
        raise SystemExit("Post-check failed: idx_agenda_owner_status missing after create.")

    agenda_checks = {ck["name"] for ck in inspector.get_check_constraints("agenda")}
    if "ck_agenda_status" not in agenda_checks:
        raise SystemExit("Post-check failed: ck_agenda_status missing after create.")

    step_indexes = {ix["name"] for ix in inspector.get_indexes("agenda_step")}
    for name in ("idx_agenda_step_agenda", "idx_agenda_step_one_active"):
        if name not in step_indexes:
            raise SystemExit(f"Post-check failed: {name} missing after create.")

    step_checks = {ck["name"] for ck in inspector.get_check_constraints("agenda_step")}
    if "ck_agenda_step_status" not in step_checks:
        raise SystemExit("Post-check failed: ck_agenda_step_status missing after create.")

    print("Migration v1.72 applied.")


if __name__ == "__main__":
    main()
