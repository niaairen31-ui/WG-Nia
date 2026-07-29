"""Migration v1.89 — `conversation_window_config` (creator-tunable NPC
dialogue context window, TICKET-0050, BRIEF-0050-a).

Ships the table + unique index only: no seeding, no rows. Absence of a row
is legal and handled by the reader's in-memory defaults
(`context_window.load_conversation_window_config`) — "no structure
without a reader" holds: the reader ships in this same brief.

Two independent guards (table existence, index existence — v1.77 lesson,
v1.80/v1.81/v1.84/v1.87/v1.88 guard shape): a partially applied prior run
completes only the missing part on re-run, never skips wholesale.

Run from the project root:
    python scripts/migrate_v1_89_conversation_window_config.py
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
        "migrate_v1_89_conversation_window_config.py refuses to run without "
        "WORLD_ENGINE_ENV or WORLD_ENGINE_DATABASE_URL set (fail-closed, "
        f"TICKET-0049) — got: {_env or 'unset'}.",
        file=sys.stderr,
    )
    sys.exit(1)

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
    print("Migration v1.89 — conversation_window_config")

    for model in (models.ConversationWindowConfig,):
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

    print("\nMigration v1.89 applied.")


if __name__ == "__main__":
    main()
