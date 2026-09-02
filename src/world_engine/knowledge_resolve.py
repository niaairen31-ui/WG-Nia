"""Scoped default knowledge-level resolution (TICKET-0082, BRIEF-0082-c,
G2a).

`resolve_knowledge_level` is the single resolution authority for "what level
does this entity hold on this fact", total over the six-value ladder
(`writes/knowledge.py::KNOWLEDGE_LEVEL_LADDER`) — precedence, most specific
first:

1. a stored `knowledge` row for `(entity_id, fact_id)` — wins outright,
   including when it is `'unaware'`;
2. a `fact_default` at `scope_type='location'` for the entity's current
   location or any ancestor via `location.parent_location_id` — nearest
   ancestor wins;
3. a `fact_default` at `scope_type='faction'` for any faction the entity
   holds an ACTIVE membership in (`left_at IS NULL`) — the HIGHEST level
   across several such memberships wins;
4. a `fact_default` at `scope_type='world'`;
5. `fact.default_level` — always present (NOT NULL), so this tier never
   fails to produce a value.

`resolve_levels_for_entity` is the batch companion: one pass over every
fact in the entity's world, returning only the facts resolving above
`'unaware'`, so a context assembler calls it once per assembly rather than
once per fact.

# A resolved default never carries is_secret. Secrecy is a property of a
# stored knowledge row, structurally excluded at query level by the
# existing readers. A default that could mint secret knowledge would put
# a second, weaker authority behind that exclusion.

Resolution is a read: no function here ever calls `db.add`, and no default
is ever written back as a `knowledge` row.
"""

from __future__ import annotations

from typing import Optional

from sqlmodel import Session, select

from .models import Character, Entity, Fact, FactDefault, FactionMembership, Knowledge, Location
from .writes.knowledge import KNOWLEDGE_LEVEL_LADDER

DEFAULT_SHARE_THRESHOLD = 50


def _location_ancestor_chain(db: Session, entity_id: str) -> list[str]:
    """The entity's current location, then each ancestor up
    `parent_location_id`, nearest first. Empty when the entity has no
    `Character` row or no current location. Cycle-safe (stops on repeat)."""
    character = db.get(Character, entity_id)
    if character is None or not character.current_location_id:
        return []
    chain: list[str] = []
    seen: set[str] = set()
    current_id: Optional[str] = character.current_location_id
    while current_id and current_id not in seen:
        chain.append(current_id)
        seen.add(current_id)
        location = db.get(Location, current_id)
        current_id = location.parent_location_id if location else None
    return chain


def _active_faction_ids(db: Session, entity_id: str) -> list[str]:
    rows = db.exec(
        select(FactionMembership).where(
            FactionMembership.entity_id == entity_id,
            FactionMembership.left_at.is_(None),
        )
    ).all()
    return [row.faction_id for row in rows]


def _highest_level(levels: list[str]) -> str:
    return max(levels, key=KNOWLEDGE_LEVEL_LADDER.index)


def _resolve_tiers(
    *,
    stored_level: Optional[str],
    location_chain: list[str],
    location_defaults: dict[str, str],
    faction_ids: list[str],
    faction_defaults: dict[str, str],
    world_default: Optional[str],
    fallback_level: str,
) -> str:
    """Pure precedence resolution over already-fetched context (item 2/G2a).
    Shared by the single-fact and batch entry points so both apply the
    identical rule."""
    if stored_level is not None:
        return stored_level
    for location_id in location_chain:
        if location_id in location_defaults:
            return location_defaults[location_id]
    faction_levels = [
        faction_defaults[faction_id]
        for faction_id in faction_ids
        if faction_id in faction_defaults
    ]
    if faction_levels:
        return _highest_level(faction_levels)
    if world_default is not None:
        return world_default
    return fallback_level


def resolve_knowledge_level(db: Session, entity_id: str, fact_id: str) -> str:
    """Total: always returns one of the six `KNOWLEDGE_LEVEL_LADDER` values,
    never `None` — tier 5 (`fact.default_level`) is NOT NULL by schema."""
    stored = db.exec(
        select(Knowledge).where(
            Knowledge.entity_id == entity_id, Knowledge.fact_id == fact_id,
        )
    ).first()
    stored_level = stored.level if stored is not None else None

    location_chain = _location_ancestor_chain(db, entity_id)
    location_defaults: dict[str, str] = {}
    if location_chain:
        rows = db.exec(
            select(FactDefault).where(
                FactDefault.fact_id == fact_id,
                FactDefault.scope_type == "location",
                FactDefault.scope_id.in_(location_chain),
            )
        ).all()
        location_defaults = {row.scope_id: row.level for row in rows}

    faction_ids = _active_faction_ids(db, entity_id)
    faction_defaults: dict[str, str] = {}
    if faction_ids:
        rows = db.exec(
            select(FactDefault).where(
                FactDefault.fact_id == fact_id,
                FactDefault.scope_type == "faction",
                FactDefault.scope_id.in_(faction_ids),
            )
        ).all()
        faction_defaults = {row.scope_id: row.level for row in rows}

    world_row = db.exec(
        select(FactDefault).where(
            FactDefault.fact_id == fact_id, FactDefault.scope_type == "world",
        )
    ).first()
    world_default = world_row.level if world_row is not None else None

    fact = db.get(Fact, fact_id)
    fallback_level = fact.default_level if fact is not None else "unaware"

    return _resolve_tiers(
        stored_level=stored_level,
        location_chain=location_chain,
        location_defaults=location_defaults,
        faction_ids=faction_ids,
        faction_defaults=faction_defaults,
        world_default=world_default,
        fallback_level=fallback_level,
    )


def resolve_levels_for_entity(db: Session, entity_id: str) -> dict[str, str]:
    """`fact_id -> level` for every fact in the entity's world resolving
    above `'unaware'`. One pass: stored rows, location chain, faction
    memberships and every `fact_default` for the world are each fetched
    once, then every fact is resolved against that shared context — never
    one query per fact."""
    entity = db.get(Entity, entity_id)
    if entity is None:
        return {}

    facts = db.exec(select(Fact).where(Fact.world_id == entity.world_id)).all()
    if not facts:
        return {}

    stored_rows = db.exec(select(Knowledge).where(Knowledge.entity_id == entity_id)).all()
    stored_by_fact = {row.fact_id: row.level for row in stored_rows}

    location_chain = _location_ancestor_chain(db, entity_id)
    faction_ids = _active_faction_ids(db, entity_id)

    fact_ids = [fact.id for fact in facts]
    defaults = db.exec(select(FactDefault).where(FactDefault.fact_id.in_(fact_ids))).all()

    location_defaults_by_fact: dict[str, dict[str, str]] = {}
    faction_defaults_by_fact: dict[str, dict[str, str]] = {}
    world_default_by_fact: dict[str, str] = {}
    for row in defaults:
        if row.scope_type == "location":
            location_defaults_by_fact.setdefault(row.fact_id, {})[row.scope_id] = row.level
        elif row.scope_type == "faction":
            faction_defaults_by_fact.setdefault(row.fact_id, {})[row.scope_id] = row.level
        elif row.scope_type == "world":
            world_default_by_fact[row.fact_id] = row.level

    resolved: dict[str, str] = {}
    for fact in facts:
        level = _resolve_tiers(
            stored_level=stored_by_fact.get(fact.id),
            location_chain=location_chain,
            location_defaults=location_defaults_by_fact.get(fact.id, {}),
            faction_ids=faction_ids,
            faction_defaults=faction_defaults_by_fact.get(fact.id, {}),
            world_default=world_default_by_fact.get(fact.id),
            fallback_level=fact.default_level,
        )
        if level != "unaware":
            resolved[fact.id] = level
    return resolved


def resolve_default_rows(
    db: Session, entity_id: str, exclude_fact_ids: set[str],
) -> list[Knowledge]:
    """Transient (never `db.add`-ed, never persisted) `Knowledge` instances
    for every fact `entity_id` resolves above `'unaware'` via
    `resolve_levels_for_entity`, skipping any `fact_id` already in
    `exclude_fact_ids` (a stored row for that fact already renders on its
    own). Each row carries `is_secret=False` and
    `share_threshold=DEFAULT_SHARE_THRESHOLD` (item 5 — see module
    docstring) so it renders through the exact `_knowledge_line` shape the
    three readers already use for a stored row."""
    levels = resolve_levels_for_entity(db, entity_id)
    rows: list[Knowledge] = []
    for fact_id, level in levels.items():
        if fact_id in exclude_fact_ids:
            continue
        fact = db.get(Fact, fact_id)
        if fact is None:
            continue
        rows.append(
            Knowledge(
                entity_id=entity_id, fact_id=fact_id, subject=fact.content,
                level=level, content=fact.content, is_secret=False,
                share_threshold=DEFAULT_SHARE_THRESHOLD,
            )
        )
    return rows
