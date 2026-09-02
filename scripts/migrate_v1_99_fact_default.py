"""Migration v1.99 — `fact_default` (TICKET-0082, BRIEF-0082-c: scoped
default knowledge levels, G2a).

Ships the one table + its indexes only. Ships EMPTY — no seed row (BRIEF-
0082-c Scope OUT); the creator surface (`cockpit/crud/knowledge.py`) is its
first writer. CHECK constraints are part of the table's own `__table_args__`
(SQLModel/SQLAlchemy emits them with `Table.create`) — nothing extra to add
here beyond the table + index shapes (`migrate_v1_97_day_rewrite.py`
precedent for a from-scratch table, `migrate_v1_96_knowledge_subject_
index.py` precedent for converging `schema_meta` in the same transaction).

Two independent guards (table existence, index existence): a partially
applied prior run completes only the missing part on re-run, never skips
wholesale.

Run from the project root:

    python scripts/migrate_v1_99_fact_default.py
"""

from __future__ import annotations

import os
import sys
from datetime import UTC, datetime
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

_env = os.environ.get("WORLD_ENGINE_ENV")
if not _env and not os.environ.get("WORLD_ENGINE_DATABASE_URL"):
    print(
        "migrate_v1_99_fact_default.py refuses to run without WORLD_ENGINE_ENV "
        "or WORLD_ENGINE_DATABASE_URL set (fail-closed, TICKET-0049) — got: "
        f"{_env or 'unset'}.",
        file=sys.stderr,
    )
    sys.exit(1)

from sqlalchemy import inspect  # noqa: E402
from sqlmodel import Session  # noqa: E402

from world_engine import models  # noqa: E402
from world_engine.db import engine  # noqa: E402
from world_engine.schema_version import EXPECTED_STATIC_SCHEMA_VERSION  # noqa: E402


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
    print("Migration v1.99 — fact_default")

    created = _ensure_table(models.FactDefault)
    print(
        f"Schema: {'created table' if created else 'table already present'} "
        f"`{models.FactDefault.__tablename__}`"
    )
    applied = _ensure_indexes(models.FactDefault)
    if applied:
        print(f"Schema: created index(es) on `{models.FactDefault.__tablename__}`: {', '.join(applied)}")
    else:
        print(f"Schema: indexes on `{models.FactDefault.__tablename__}` already present — nothing to do.")

    with Session(engine) as session:
        row = session.get(models.SchemaMeta, 1)
        if row is None:
            session.add(models.SchemaMeta(id=1, static_version=EXPECTED_STATIC_SCHEMA_VERSION))
            print(f"Row: seeded schema_meta.id=1 at {EXPECTED_STATIC_SCHEMA_VERSION!r}")
        elif row.static_version != EXPECTED_STATIC_SCHEMA_VERSION:
            previous = row.static_version
            row.static_version = EXPECTED_STATIC_SCHEMA_VERSION
            row.updated_at = datetime.now(UTC)
            session.add(row)
            print(f"Row: updated schema_meta.id=1: {previous!r} -> {EXPECTED_STATIC_SCHEMA_VERSION!r}")
        else:
            print(f"Row: schema_meta.id=1 already at {EXPECTED_STATIC_SCHEMA_VERSION!r} — nothing to do")
        session.commit()

    print("\nMigration v1.99 applied.")


if __name__ == "__main__":
    main()
