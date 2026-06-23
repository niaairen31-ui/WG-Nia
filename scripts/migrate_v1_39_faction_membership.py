"""Migration to schema v1.39 — add the faction_membership table (BRIEF-27).

New table: faction_membership
  - Durable member <-> faction roster. Durable counterpart to
    `gathering_member` (session-ephemeral): no `session_id`, membership
    persists across sessions.
  - Roster predicate, single source: a membership is ACTIVE iff
    `left_at IS NULL`. Rows are append/close only — never updated in place
    or hard-deleted. A role/primary change is close + reopen (a new row),
    so the closed rows ARE the history (no `change_history` column here).
  - `role` / `is_secret` are DORMANT this step: stored, creator-editable via
    the cockpit, read by no assembler. The first reader (and the structural
    is_secret=FALSE exclusion it requires) is the next brief.
  - Two structural guards, partial unique indexes (enforced by construction,
    not by instruction):
      idx_membership_one_primary    — at most one ACTIVE primary per member.
      idx_membership_unique_active  — no duplicate ACTIVE membership of the
                                       same member in the same faction.

Backfill: for every `character` row with a non-NULL `faction_id`, insert one
membership row (is_primary=TRUE, is_secret=FALSE, role=NULL, left_at=NULL),
joined_at = the member entity's created_at (fallback CURRENT_TIMESTAMP).
Idempotent — re-running inserts no duplicate active rows (checks for an
existing active row per (entity_id, faction_id) before inserting; the
partial unique index also backs this).

`character.faction_id` itself is NOT dropped by this script — that drop is
grep-gated (BRIEF-27 Scope IN #6) and, if any consumer beyond the cockpit
editor / idx_character_faction is found, is deferred to a follow-up.

Idempotent: safe to re-run.

Run from the project root:
    python scripts/migrate_v1_39_faction_membership.py
"""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

from sqlalchemy import inspect, text  # noqa: E402

from world_engine.db import engine  # noqa: E402


def _create_table(conn) -> None:
    conn.execute(text("""
        CREATE TABLE faction_membership (
          id          TEXT PRIMARY KEY,
          world_id    TEXT NOT NULL REFERENCES world(id),
          entity_id   TEXT NOT NULL REFERENCES entity(id),
          faction_id  TEXT NOT NULL REFERENCES entity(id),
          role        TEXT,
          is_primary  BOOLEAN DEFAULT FALSE,
          is_secret   BOOLEAN DEFAULT FALSE,
          joined_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
          left_at     DATETIME
        )
    """))
    conn.execute(text(
        "CREATE INDEX idx_faction_membership_entity ON faction_membership(entity_id)"
    ))
    conn.execute(text(
        "CREATE INDEX idx_faction_membership_faction ON faction_membership(faction_id)"
    ))
    conn.execute(text(
        "CREATE UNIQUE INDEX idx_membership_one_primary "
        "ON faction_membership(entity_id) WHERE is_primary = 1 AND left_at IS NULL"
    ))
    conn.execute(text(
        "CREATE UNIQUE INDEX idx_membership_unique_active "
        "ON faction_membership(entity_id, faction_id) WHERE left_at IS NULL"
    ))


def _backfill(conn) -> tuple[int, int]:
    """Insert one active primary membership per character.faction_id.

    Returns (candidates, inserted).
    """
    candidates = conn.execute(text(
        "SELECT c.id AS entity_id, c.faction_id AS faction_id, e.created_at AS created_at "
        "FROM character c JOIN entity e ON e.id = c.id "
        "WHERE c.faction_id IS NOT NULL"
    )).mappings().all()

    inserted = 0
    for row in candidates:
        existing = conn.execute(text(
            "SELECT 1 FROM faction_membership "
            "WHERE entity_id = :entity_id AND faction_id = :faction_id AND left_at IS NULL"
        ), {"entity_id": row["entity_id"], "faction_id": row["faction_id"]}).first()
        if existing is not None:
            continue

        world_id = conn.execute(text(
            "SELECT world_id FROM entity WHERE id = :entity_id"
        ), {"entity_id": row["entity_id"]}).scalar_one()

        conn.execute(text(
            "INSERT INTO faction_membership "
            "(id, world_id, entity_id, faction_id, role, is_primary, is_secret, joined_at, left_at) "
            "VALUES (:id, :world_id, :entity_id, :faction_id, NULL, 1, 0, "
            "COALESCE(:joined_at, CURRENT_TIMESTAMP), NULL)"
        ), {
            "id": str(uuid.uuid4()),
            "world_id": world_id,
            "entity_id": row["entity_id"],
            "faction_id": row["faction_id"],
            "joined_at": row["created_at"],
        })
        inserted += 1

    return len(candidates), inserted


def main() -> None:
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    if "faction_membership" not in tables:
        with engine.begin() as conn:
            _create_table(conn)
        print("Migration v1.39 applied: faction_membership table and four indexes created.")
    else:
        print("Table 'faction_membership' already exists — skipping table/index creation.")

    with engine.begin() as conn:
        candidates, inserted = _backfill(conn)

    print(f"Backfill: {candidates} character(s) with faction_id, {inserted} membership row(s) inserted.")


if __name__ == "__main__":
    main()
