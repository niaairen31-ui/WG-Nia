"""Migration v1.87 — `entity_type` + `entity_type_history` (per-world
runtime-type registry + append-only DDL-event log, TICKET-0044, BRIEF-0044-b).

Socle of the governed runtime-DDL constructor (A1, Dgov1) — plane 2 of the
C2 two-plane governance design (v1.86 shipped plane 1, `schema_meta`), a
separate concern with no write path to `schema_meta`. Ships the two static
tables ONLY: no writer, no DDL emission, no seeding — no runtime types exist
yet.

Two independent guards per table (table existence, index existence — v1.77
lesson, v1.80/v1.81/v1.84 guard shape): a partially applied prior run
completes only the missing part on re-run, never skips wholesale.

Run from the project root:
    python scripts/migrate_v1_87_entity_type.py
"""

from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

from sqlalchemy import inspect  # noqa: E402

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


def main() -> None:
    print("Migration v1.87 — entity_type + entity_type_history")

    for model in (models.EntityType, models.EntityTypeHistory):
        created = _ensure_table(model)
        print(
            f"Schema: {'created table' if created else 'table already present'} "
            f"`{model.__tablename__}`"
        )
        applied = _ensure_indexes(model)
        if applied:
            print(f"Schema: created index(es) on `{model.__tablename__}`: {', '.join(applied)}")
        else:
            print(f"Schema: indexes on `{model.__tablename__}` already present — nothing to do.")

    print("\nMigration v1.87 applied.")


if __name__ == "__main__":
    main()
