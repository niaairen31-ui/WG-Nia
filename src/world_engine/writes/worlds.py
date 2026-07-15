"""`world` cascade-delete chokepoint (TICKET-0028, BRIEF-0028-b —
decomposed from `writes.py`).

DOCUMENTED EXCEPTION to "History is sacred": `delete_world_cascade` is the
only helper in the codebase that hard-deletes canon. It exists solely for
whole-world block deletion (creator authority, irreversible). No other
delete-side helper may be added here; History is sacred holds everywhere
else. `canon_write_policy.txt` wildcards this one function (`*`) — every
write inside it is sanctioned, which is why `_SUBQUERY_SCOPED_DELETES`
(pure data, not a write) is the only extraction taken from it: every
`db.execute` stays textually inside `delete_world_cascade` itself so the
wildcard entry keeps covering the whole function, unchanged.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlmodel import Session

# Subquery-scoped deletes (child_table, child_fk_column, parent_table) — run
# BEFORE their parent table is cleared (see delete_world_cascade's
# docstring on ordering). Order matches the pre-BRIEF-0028-b statement
# sequence exactly — mechanical data, not a logic change.
_SUBQUERY_SCOPED_DELETES: tuple[tuple[str, str, str], ...] = (
    ("conversation_message", "conversation_id", "conversation"),
    ("gathering_member", "gathering_id", "gathering"),
    ("batch", "session_id", "session"),
    ("pass_play", "session_id", "session"),
    ("knowledge", "entity_id", "entity"),
    ("skill", "character_id", "entity"),
    ("location", "id", "entity"),
    ("faction", "id", "entity"),
    ("artifact", "id", "entity"),
    ("item", "id", "entity"),
)

# Direct world_id-scoped deletes — order free under the FK deferral.
# `skill_definition` (BRIEF-55, schema v1.63) must still come after the
# subquery-based `skill` delete above so no `skill.skill_definition_id`
# is left pointing at a missing row by commit time (RESTRICT, deferred).
_DIRECT_WORLD_SCOPED_DELETES: tuple[str, ...] = (
    "faction_membership", "relation", "character", "discoverable_detail",
    "proposed_mutation", "ledger", "event", "gathering", "conversation",
    "session", "skill_definition", "entity",
)


def delete_world_cascade(world_id: str, db: Session) -> None:
    """Hard-delete every row scoped to `world_id`, including the `world` row
    itself. Caller owns the transaction and the commit (BRIEF-54).

    Sets `PRAGMA defer_foreign_keys = ON` on the session connection before
    any DELETE, so the self-referential columns
    (`location.parent_location_id`, `faction.parent_faction_id`,
    `character.current_location_id`) resolve without nulling — the deferral
    is per-transaction and resets after commit/rollback.

    Statement order below is NOT arbitrary despite the FK deferral: several
    deletes are correlated subqueries against `entity`/`conversation`/
    `gathering`/`session` (e.g. `knowledge` via `entity_id IN (SELECT id FROM
    entity WHERE world_id = :wid)`) — those must run while the referenced
    parent rows still exist, or the subquery returns nothing and orphans get
    left behind. So every subquery-based delete (`_SUBQUERY_SCOPED_DELETES`)
    runs before its parent table is cleared; only the direct
    `world_id`-scoped deletes (`_DIRECT_WORLD_SCOPED_DELETES`, no subquery)
    are free to run in any order relative to each other, per the FK deferral.

    Never touches `prompt_template` rows with `world_id IS NULL` (the global
    seeds shared by every world) or the `user` table (global accounts, no
    world scope).
    """
    db.execute(text("PRAGMA defer_foreign_keys = ON"))
    params = {"wid": world_id}

    for child_table, fk_column, parent_table in _SUBQUERY_SCOPED_DELETES:
        db.execute(
            text(
                f"DELETE FROM {child_table} WHERE {fk_column} IN "
                f"(SELECT id FROM {parent_table} WHERE world_id = :wid)"
            ),
            params,
        )

    for table in _DIRECT_WORLD_SCOPED_DELETES:
        db.execute(text(f"DELETE FROM {table} WHERE world_id = :wid"), params)

    # Global prompt-template seeds (world_id IS NULL) are never touched.
    db.execute(text("DELETE FROM prompt_template WHERE world_id = :wid"), params)

    # The world row itself, last.
    db.execute(text("DELETE FROM world WHERE id = :wid"), params)
