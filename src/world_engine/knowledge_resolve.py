"""Scoped default knowledge-level resolution (TICKET-0082, BRIEF-0082-c,
G2a), dated by contact (TICKET-0105, BRIEF-0105-D, B5).

`resolve_knowledge` is the single resolution authority for "what does this
entity hold of this fact": a `Known(level, as_of)`, total over the six-value
ladder (`writes/knowledge.py::KNOWLEDGE_LEVEL_LADDER`). Precedence, most
specific first:

1. a stored `knowledge` row for `(entity_id, fact_id)` -- wins outright,
   including when it is `'unaware'`;
2. self: the entity is a `fact_participant` of the fact AND the fact's
   facet is in `facets.DESCRIPTIVE_FACETS` -- `'knows'` (TICKET-0091, Q6a,
   Q18a);
3. rencontre: a `fact_default` at `scope_type='rencontre'` whose `scope_id`
   the entity met (`rencontre.last_at`) AT OR AFTER the default was written,
   or is in contact with right now -- the HIGHEST level wins;
4. location: a `fact_default` at `scope_type='location'` whose place, or a
   place inside it, the entity was in (`passage.last_at`) at or after the
   default was written, or is in right now -- the HIGHEST level wins (C1);
5. faction: a `fact_default` at `scope_type='faction'` for a faction the
   entity belongs to, or belonged to at or after the default was written
   (J2) -- the HIGHEST level wins;
6. a `fact_default` at `scope_type='world'`;
7. `fact.default_level` -- always present (NOT NULL).

A fact once learned stays learned: tiers 3-5 read the LAST contact, so
leaving a place, a group or a person forgets nothing.

Contact "right now" (no date to compare, always in contact): being in a
place or a place inside it (`current_location_id` and its ancestors), a
place one's schedule names, an entity at the same exact current location
(O1) or sharing one of one's schedule slots (L1), an active membership.

`as_of` is when the entity last saw the fact as it is (N1): the latest
contact with any of the fact's anchors -- its participants and the
entities its non-world defaults name -- or, for a stored row, that or the
row's `updated_at`, whichever is later. It is `None` (always current) for
a fact with a `world` default, for one's own facts (tier 2), and at tiers
6-7. `fact_versions.version_text` turns it into the text the entity knows.

`resolve_known_for_entity` is the batch companion: every fact of the
entity's world resolving above `'unaware'`, each context query run once.
`resolve_knowledge_level` and `resolve_levels_for_entity` return the level
alone.

# A resolved default never carries is_secret. Secrecy is a property of a
# stored knowledge row, structurally excluded at query level by the
# existing readers. A default that could mint secret knowledge would put
# a second, weaker authority behind that exclusion.

Resolution is a read: no function here ever calls `db.add`, and no default
is ever written back as a `knowledge` row.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Iterable, Optional

from sqlmodel import Session, select

from .fact_versions import utc
from .facets import DESCRIPTIVE_FACETS
from .models import (
    Character, Entity, Fact, FactDefault, FactionMembership, FactParticipant, Knowledge, Location,
    NpcSchedule, Passage, Rencontre,
)
from .writes.knowledge import KNOWLEDGE_LEVEL_LADDER

DEFAULT_SHARE_THRESHOLD = 50

# `partial` is the floor at which an edge becomes traversable: the first
# level on the ladder at which the knower can be said to know where the way
# goes. One constant, shared by the character path and the public path — a
# second floor would drift. (TICKET-0082, BRIEF-0082-d amendment 1, I1.)
KNOWN_EDGE_FLOOR = "partial"


@dataclass(frozen=True)
class Known:
    """What an entity holds of a fact: its level, and when it last saw the
    fact as it is (`None`: always current)."""
    level: str
    as_of: Optional[datetime]


def meets_floor(level: str, floor: str) -> bool:
    """True iff `level` is at or above `floor` on `KNOWLEDGE_LEVEL_LADDER`.
    The one place a floor comparison indexes the ladder — callers (e.g.
    `tick_context._reachable_locations`) compare through this, never by
    indexing `KNOWLEDGE_LEVEL_LADDER` themselves."""
    return KNOWLEDGE_LEVEL_LADDER.index(level) >= KNOWLEDGE_LEVEL_LADDER.index(floor)


def _highest_level(levels: list[str]) -> str:
    return max(levels, key=KNOWLEDGE_LEVEL_LADDER.index)


def _later(a: Optional[datetime], b: Optional[datetime]) -> Optional[datetime]:
    if a is None:
        return b
    if b is None:
        return a
    return max(a, b)


@dataclass
class _Contacts:
    """The perceiver's dated contacts, fetched once. Each map holds the last
    contact per entity id; `now` stands for contact right now."""
    now: datetime
    met: dict[str, datetime] = field(default_factory=dict)
    places: dict[str, datetime] = field(default_factory=dict)
    factions: dict[str, datetime] = field(default_factory=dict)

    def any(self, entity_id: str) -> Optional[datetime]:
        """The last contact with `entity_id` through any registry."""
        return _later(_later(self.met.get(entity_id), self.places.get(entity_id)),
                      self.factions.get(entity_id))


def _keep(target: dict[str, datetime], key: str, at: datetime) -> None:
    if key not in target or target[key] < at:
        target[key] = at


def _ancestors(db: Session, location_id: str, memo: dict[str, list[str]]) -> list[str]:
    """`location_id` then each ancestor up `parent_location_id`; cycle-safe."""
    if location_id in memo:
        return memo[location_id]
    chain: list[str] = []
    current: Optional[str] = location_id
    while current and current not in chain:
        chain.append(current)
        row = db.get(Location, current)
        current = row.parent_location_id if row else None
    memo[location_id] = chain
    return chain


def _place_contacts(db: Session, entity_id: str, char: Optional[Character],
                    schedule: list[NpcSchedule], ctx: _Contacts) -> None:
    memo: dict[str, list[str]] = {}
    for row in db.exec(select(Passage).where(Passage.entity_id == entity_id)).all():
        for place in _ancestors(db, row.location_id, memo):
            _keep(ctx.places, place, utc(row.last_at))
    now_places = [s.location_id for s in schedule]
    if char is not None and char.current_location_id:
        now_places.append(char.current_location_id)
    for location_id in now_places:
        for place in _ancestors(db, location_id, memo):
            ctx.places[place] = ctx.now


def _met_contacts(db: Session, entity_id: str, char: Optional[Character],
                  schedule: list[NpcSchedule], ctx: _Contacts) -> None:
    for row in db.exec(select(Rencontre).where(
            (Rencontre.entity_lo_id == entity_id) | (Rencontre.entity_hi_id == entity_id))).all():
        other = row.entity_hi_id if row.entity_lo_id == entity_id else row.entity_lo_id
        _keep(ctx.met, other, utc(row.last_at or row.first_at))
    present: set[str] = set()
    if char is not None and char.current_location_id:
        present.update(db.exec(select(Character.id).where(
            Character.current_location_id == char.current_location_id)).all())
    for slot in schedule:
        present.update(db.exec(select(NpcSchedule.npc_id).where(
            NpcSchedule.location_id == slot.location_id, NpcSchedule.phase == slot.phase)).all())
    present.discard(entity_id)
    for other in present:
        ctx.met[other] = ctx.now


def _contacts(db: Session, entity_id: str) -> _Contacts:
    ctx = _Contacts(now=datetime.now(UTC))
    char = db.get(Character, entity_id)
    schedule = list(db.exec(select(NpcSchedule).where(NpcSchedule.npc_id == entity_id)).all())
    _place_contacts(db, entity_id, char, schedule, ctx)
    _met_contacts(db, entity_id, char, schedule, ctx)
    for row in db.exec(select(FactionMembership).where(
            FactionMembership.entity_id == entity_id)).all():
        _keep(ctx.factions, row.faction_id, ctx.now if row.left_at is None else utc(row.left_at))
    return ctx


_SCOPE_CONTACTS = {"rencontre": "met", "location": "places", "faction": "factions"}


def _tier_level(ctx: _Contacts, defaults: list[FactDefault], scope_type: str) -> Optional[str]:
    """The highest level among `scope_type` defaults whose scope the entity
    was in contact with at or after the default was written."""
    contacts = getattr(ctx, _SCOPE_CONTACTS[scope_type])
    levels = []
    for row in defaults:
        if row.scope_type != scope_type:
            continue
        seen = contacts.get(row.scope_id)
        if seen is not None and seen >= utc(row.created_at):
            levels.append(row.level)
    return _highest_level(levels) if levels else None


def _as_of(ctx: _Contacts, defaults: list[FactDefault], participants: Iterable[str],
           stored: Optional[Knowledge]) -> Optional[datetime]:
    """When the entity last saw the fact as it is (N1); `None`: current."""
    if any(row.scope_type == "world" for row in defaults):
        return None
    anchors = set(participants) | {row.scope_id for row in defaults if row.scope_id}
    seen: Optional[datetime] = None
    for anchor in anchors:
        seen = _later(seen, ctx.any(anchor))
    if stored is not None and stored.updated_at is not None:
        seen = _later(seen, utc(stored.updated_at))
    return seen


def _resolve_fact(ctx: _Contacts, entity_id: str, fact: Fact, defaults: list[FactDefault],
                  participants: set[str], stored: Optional[Knowledge]) -> Known:
    """Tiers 1-7 for one fact over already-fetched context (module docstring)."""
    if stored is not None:
        return Known(stored.level, _as_of(ctx, defaults, participants, stored))
    if entity_id in participants and fact.facet in DESCRIPTIVE_FACETS:
        return Known("knows", None)
    for scope_type in ("rencontre", "location", "faction"):
        level = _tier_level(ctx, defaults, scope_type)
        if level is not None:
            return Known(level, _as_of(ctx, defaults, participants, None))
    world = [row.level for row in defaults if row.scope_type == "world"]
    if world:
        return Known(world[0], None)
    return Known(fact.default_level, None)


def resolve_knowledge(db: Session, entity_id: str, fact_id: str) -> Known:
    """Total: one of the six `KNOWLEDGE_LEVEL_LADDER` values, never `None`;
    `Known("unaware", None)` for an unknown fact id."""
    fact = db.get(Fact, fact_id)
    if fact is None:
        return Known("unaware", None)
    stored = db.exec(select(Knowledge).where(
        Knowledge.entity_id == entity_id, Knowledge.fact_id == fact_id)).first()
    defaults = list(db.exec(select(FactDefault).where(FactDefault.fact_id == fact_id)).all())
    participants = set(db.exec(select(FactParticipant.entity_id).where(
        FactParticipant.fact_id == fact_id)).all())
    return _resolve_fact(_contacts(db, entity_id), entity_id, fact, defaults, participants, stored)


def resolve_knowledge_level(db: Session, entity_id: str, fact_id: str) -> str:
    """The level of `resolve_knowledge`."""
    return resolve_knowledge(db, entity_id, fact_id).level


def resolve_known_for_entity(db: Session, entity_id: str) -> dict[str, Known]:
    """`fact_id -> Known` for every fact in the entity's world resolving
    above `'unaware'`. One pass: stored rows, participants, defaults and the
    entity's contacts are each fetched once."""
    entity = db.get(Entity, entity_id)
    if entity is None:
        return {}
    facts = db.exec(select(Fact).where(Fact.world_id == entity.world_id)).all()
    if not facts:
        return {}
    fact_ids = [fact.id for fact in facts]
    stored = {row.fact_id: row for row in db.exec(
        select(Knowledge).where(Knowledge.entity_id == entity_id)).all()}
    defaults: dict[str, list[FactDefault]] = {}
    for row in db.exec(select(FactDefault).where(FactDefault.fact_id.in_(fact_ids))).all():
        defaults.setdefault(row.fact_id, []).append(row)
    participants: dict[str, set[str]] = {}
    for fact_id, member in db.exec(select(FactParticipant.fact_id, FactParticipant.entity_id).where(
            FactParticipant.fact_id.in_(fact_ids))).all():
        participants.setdefault(fact_id, set()).add(member)
    ctx = _contacts(db, entity_id)
    resolved: dict[str, Known] = {}
    for fact in facts:
        known = _resolve_fact(ctx, entity_id, fact, defaults.get(fact.id, []),
                              participants.get(fact.id, set()), stored.get(fact.id))
        if known.level != "unaware":
            resolved[fact.id] = known
    return resolved


def resolve_levels_for_entity(db: Session, entity_id: str) -> dict[str, str]:
    """`fact_id -> level` of `resolve_known_for_entity`."""
    return {fact_id: known.level for fact_id, known in resolve_known_for_entity(db, entity_id).items()}


def _public_tier(world_default: Optional[str], fallback_level: str) -> str:
    """Tiers 6-7 alone: the public floor has no entity, so no stored row,
    no self, no contact."""
    return world_default if world_default is not None else fallback_level


def resolve_public_level(db: Session, fact_id: str) -> str:
    """Public-floor resolution (TICKET-0082, BRIEF-0082-d amendment 1, H3):
    the same tiered authority as `resolve_knowledge_level`, entered at its
    world tier, with NO entity — tiers 1-5 (stored row, self, rencontre,
    location chain, faction memberships) are skipped because each requires one. For a
    reader whose prompt no single character governs (classified `public`,
    never `deliberation` — a `public` site never passes an entity_id)."""
    world_row = db.exec(
        select(FactDefault).where(
            FactDefault.fact_id == fact_id, FactDefault.scope_type == "world",
        )
    ).first()
    world_default = world_row.level if world_row is not None else None
    fact = db.get(Fact, fact_id)
    fallback_level = fact.default_level if fact is not None else "unaware"
    return _public_tier(world_default, fallback_level)


def resolve_public_levels(db: Session, world_id: str) -> dict[str, str]:
    """Batch companion to `resolve_public_level`, in the shape of
    `resolve_levels_for_entity`: `fact_id -> level` for every fact in
    `world_id`, each resolved at the public floor (no entity). Unlike the
    per-entity batch helper, this includes every fact regardless of level —
    a `public` caller's floor comparison needs the full set, not one
    pre-filtered by a per-entity notion of "resolves above unaware"."""
    facts = db.exec(select(Fact).where(Fact.world_id == world_id)).all()
    if not facts:
        return {}
    fact_ids = [fact.id for fact in facts]
    world_rows = db.exec(
        select(FactDefault).where(
            FactDefault.fact_id.in_(fact_ids), FactDefault.scope_type == "world",
        )
    ).all()
    world_default_by_fact = {row.fact_id: row.level for row in world_rows}
    return {
        fact.id: _public_tier(world_default_by_fact.get(fact.id), fact.default_level)
        for fact in facts
    }


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
    three readers already use for a stored row. A fact whose facet is in
    `DESCRIPTIVE_FACETS` is skipped: what is said of an entity is read
    through `facet_reads`, never as speakable knowledge, so the three
    readers' knowledge section is unchanged (TICKET-0091, Q13a)."""
    levels = resolve_levels_for_entity(db, entity_id)
    rows: list[Knowledge] = []
    for fact_id, level in levels.items():
        if fact_id in exclude_fact_ids:
            continue
        fact = db.get(Fact, fact_id)
        if fact is None or fact.facet in DESCRIPTIVE_FACETS:
            continue
        rows.append(
            Knowledge(
                entity_id=entity_id, fact_id=fact_id,
                level=level, content_raw=fact.content_raw, is_secret=False,
                share_threshold=DEFAULT_SHARE_THRESHOLD,
            )
        )
    return rows
