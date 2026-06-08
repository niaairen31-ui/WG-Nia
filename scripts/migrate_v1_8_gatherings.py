"""Migrate the live database to schema v1.8 — multi-NPC gatherings (Tier 1).

Adds the `gathering` and `gathering_member` tables, relaxes
`conversation.npc_id` to nullable (a seed/focus NPC is now optional —
participants derive from the gathering roster), and adds
`conversation.gathering_id`. Idempotent — safe to run more than once.

Run from the project root:

    python scripts/migrate_v1_8_gatherings.py
"""

from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

from sqlalchemy import inspect, text  # noqa: E402

from world_engine import models  # noqa: E402
from world_engine.db import engine  # noqa: E402

CONVERSATION_COLUMNS = (
    "id, world_id, session_id, location_id, player_id, npc_id, "
    "status, injected_context, started_at, ended_at"
)


def _npc_id_is_nullable() -> bool:
    for col in inspect(engine).get_columns("conversation"):
        if col["name"] == "npc_id":
            return bool(col["nullable"])
    raise RuntimeError("conversation.npc_id column not found")


def _rebuild_conversation_table() -> None:
    """Recreate `conversation` with npc_id nullable + gathering_id, preserving rows.

    SQLite has no ALTER COLUMN; relaxing a NOT NULL constraint requires a full
    table rebuild (rename, recreate from the model, copy, drop). The existing
    `idx_conversation_world` index is dropped first so the rebuilt table's
    `__table_args__` can recreate it under the same name without a clash.

    `legacy_alter_table=ON` is mandatory here: by default SQLite 3.25+ rewrites
    the FK clauses of *other* tables (`conversation_message`, `proposed_mutation`)
    to follow a renamed table, leaving them pointing at the soon-to-be-dropped
    `conversation_old` once the rebuilt table reclaims the `conversation` name.
    """
    with engine.begin() as conn:
        conn.execute(text("PRAGMA foreign_keys=OFF"))
        conn.execute(text("PRAGMA legacy_alter_table=ON"))
        conn.execute(text("DROP INDEX IF EXISTS idx_conversation_world"))
        conn.execute(text("ALTER TABLE conversation RENAME TO conversation_old"))

        models.Conversation.__table__.create(conn)

        conn.execute(text(
            f"INSERT INTO conversation ({CONVERSATION_COLUMNS}, gathering_id) "
            f"SELECT {CONVERSATION_COLUMNS}, NULL FROM conversation_old"
        ))
        conn.execute(text("DROP TABLE conversation_old"))
        conn.execute(text("PRAGMA legacy_alter_table=OFF"))
        conn.execute(text("PRAGMA foreign_keys=ON"))


def main() -> None:
    inspector = inspect(engine)
    existing = set(inspector.get_table_names())

    created = []
    for table in (models.Gathering, models.GatheringMember):
        if table.__tablename__ not in existing:
            table.__table__.create(engine)
            created.append(table.__tablename__)

    if created:
        print(f"Created tables: {', '.join(created)}")
    else:
        print("`gathering` / `gathering_member` already present.")

    if _npc_id_is_nullable():
        print("`conversation` already migrated — npc_id nullable, gathering_id present.")
    else:
        _rebuild_conversation_table()
        print("Rebuilt `conversation`: npc_id is now nullable, gathering_id added.")


if __name__ == "__main__":
    main()
