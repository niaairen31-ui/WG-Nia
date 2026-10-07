"""`world` cascade-delete chokepoint (TICKET-0028, BRIEF-0028-b —
decomposed from `writes.py`).

DOCUMENTED EXCEPTION to "History is sacred": `delete_world_cascade` is the
only helper in the codebase that hard-deletes canon. It exists solely for
whole-world block deletion (creator authority, irreversible). No other
delete-side helper may be added here; History is sacred holds everywhere
else. `canon_write_policy.txt` wildcards this one function (`*`) — every
write inside it is sanctioned, which is why `_SUBQUERY_SCOPED_DELETES`
(pure data, not a write) is the only extraction taken from it: every
`db.execute` that writes stays textually inside `delete_world_cascade`
itself so the wildcard entry keeps covering the whole function, unchanged.

The exception covers the world's append-only tables too (`ledger`,
`rencontre`, `skill_resolution`, the day-chain tables): a deleted world
leaves no reader for its history (TICKET-0096, C1). It never covers a
table in `_REFUSING_TABLES`: a world holding such a row is refused before
any delete (TICKET-0096, D1 and E1).

`tooling/verify/checks/world_cascade.py` keeps these three lists equal to
the world-reaching tables of the schema — a new world-scoped table is a red
gate until it is named here.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlmodel import Session


class WorldDeleteRefused(ValueError):
    """The world holds a row the cascade must never delete; nothing was
    deleted. The message is shown to the creator as is."""


# Subquery-scoped deletes (child_table, child_fk_column, parent_table) — run
# BEFORE their parent table is cleared (see delete_world_cascade's
# docstring on ordering). Every parent is a direct table below.
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
    ("agenda_step", "agenda_id", "agenda"),
    ("event_entity", "event_id", "event"),
    ("obstacle_vertex", "obstacle_id", "obstacle"),
    ("observation_beat", "run_id", "observation_run"),
    ("observation_intent", "run_id", "observation_run"),
    ("observation_mutation_link", "run_id", "observation_run"),
    ("observation_run_template", "run_id", "observation_run"),
    ("day_mention_choice_candidate", "choice_id", "day_mention_choice"),
    ("day_mention_choice_evidence", "choice_id", "day_mention_choice"),
    ("lore_entry_row", "entry_id", "lore_entry"),
)

# Direct world_id-scoped deletes — order free under the FK deferral.
# `skill_definition` (BRIEF-55, schema v1.63) must still come after the
# subquery-based `skill` delete above so no `skill.skill_definition_id`
# is left pointing at a missing row by commit time (RESTRICT, deferred).
_DIRECT_WORLD_SCOPED_DELETES: tuple[str, ...] = (
    "faction_membership", "relation", "character", "discoverable_detail",
    "proposed_mutation", "ledger", "event", "gathering", "conversation",
    "session", "skill_definition", "entity",
    "agenda", "agenda_step_requirement", "conversation_window_config",
    "day_mention_choice", "day_mention_resolution", "day_mention_review",
    "day_rewrite", "door", "fact", "fact_default", "fact_participant",
    "faction_role", "goal_agenda_link", "goal_prerequisite",
    "location_type_catalog", "lore_entry", "npc_goal", "npc_price",
    "npc_schedule", "observation_run", "obstacle", "passage", "rencontre",
    "skill_rank", "skill_resolution", "skill_system", "unresolved_mention", "visit",
    "world_law", "quest", "quest_offer", "quest_offer_requirement", "quest_offer_step",
    "item_holding", "quest_offer_term", "quest_term", "quest_economy",
    "debt", "debt_term",
)

# Refusing tables (root_table, label_column, guarded_children, message) —
# a world holding a root row is never deleted: `delete_world_cascade`
# raises `WorldDeleteRefused` before any DELETE. The guarded children hang
# off a root row and are never deleted here either. `entity_type`: its
# `ext_*` table can never be dropped (Ddrop1). `prompt_template`: its
# versions are append-only with no exception. `{labels}` is the sorted,
# comma-separated `label_column` values of the world's root rows.
_REFUSING_TABLES: tuple[tuple[str, str, tuple[str, ...], str], ...] = (
    (
        "entity_type", "name", ("entity_trait", "entity_type_history"),
        "Suppression refusée : ce monde porte des types d'entité personnalisés "
        "({labels}). Leur suppression n'est pas encore prise en charge.",
    ),
    (
        "prompt_template", "id", ("prompt_version", "prompt_variable"),
        "Suppression refusée : ce monde possède des gabarits de prompt propres "
        "({labels}), dont les versions ne sont jamais effacées.",
    ),
)


def _refusal(world_id: str, db: Session) -> str | None:
    """The message of the first refusing table holding a row of `world_id`,
    or None. Reads only."""
    for root, label, _children, message in _REFUSING_TABLES:
        labels = db.execute(
            text(f"SELECT {label} FROM {root} WHERE world_id = :wid"),
            {"wid": world_id},
        ).scalars().all()
        if labels:
            return message.format(labels=", ".join(sorted(labels)))
    return None


def delete_world_cascade(world_id: str, db: Session) -> None:
    """Hard-delete every row scoped to `world_id`, including the `world` row
    itself. Caller owns the transaction and the commit (BRIEF-54).

    Raises `WorldDeleteRefused` before any DELETE when the world holds a row
    of a refusing table (`_REFUSING_TABLES`); nothing is deleted then.

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

    Never touches the `user` table (global accounts, no world scope) nor any
    `prompt_template` row: a world owning one is refused above, and the
    global seeds (`world_id IS NULL`) are shared by every world.
    """
    refusal = _refusal(world_id, db)
    if refusal is not None:
        raise WorldDeleteRefused(refusal)

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

    # The world row itself, last.
    db.execute(text("DELETE FROM world WHERE id = :wid"), params)
