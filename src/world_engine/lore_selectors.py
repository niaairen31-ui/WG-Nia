"""Selector whitelist for the lore consultation surface (TICKET-0085,
BRIEF-0085-b).

The model names a selector; it never writes a query. Every selector is a
code-owned function with a declared row cap, reached only through
`SELECTOR_LOOKUPS`. A plan naming anything outside `SELECTORS` is rejected
before a single row is read. Coverage grows by adding a selector, never by
adding a question type.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from sqlmodel import Session, func, select

from .context import read_public_memberships
from .facet_reads import creator_only_fact_ids, facts_of, joined
from .facets import DESCRIPTIVE_FACETS, FACETS
from .models import Character, Entity, FactParticipant, Faction, Knowledge, NpcGoal, Relation
from .prose_render import knowledge_texts
from .writes.knowledge import knowledge_level_rank


@dataclass(frozen=True)
class SelectorSpec:
    fn: Callable[..., list[dict]]
    arity: int
    row_cap: int
    arg_kinds: tuple[str, ...]
    # Section names whose rows prove only that the entity exists, never that
    # canon holds something ON it (RECON finding at BRIEF-0085-b execution:
    # `entity_dossier`'s `identity` row is unconditional once a mention
    # resolves, so counting it toward "answered" would make `silent_canon`
    # unreachable). `execute_plan` excludes these sections when deciding
    # `answered` vs `silent_canon`; it still returns them in `rows` — the
    # deterministic renderer needs the entity's name even when canon is
    # silent on the actual question. Defaults to substantive (empty tuple)
    # on purpose: an author who forgets this field gets an under-firing
    # `silent_canon` (a thin answer), never an over-firing one that asserts
    # canon is silent when it is not.
    context_sections: tuple[str, ...] = ()


def world_factions(world_id: str, db: Session) -> list[dict]:
    """One row per active faction in the world, each carrying `"section":
    "factions"` (BRIEF-0085-d item 3: the section contract applies to every
    selector, not just `entity_dossier`). Joined `entity` -> `faction` on
    `faction.id == entity.id`, world-scoped and status-scoped at
    construction."""
    rows = db.exec(
        select(Entity, Faction).join(Faction, Faction.id == Entity.id).where(
            Entity.world_id == world_id,
            Entity.status == "active",
        )
    ).all()
    def facet(entity_id: str, name: str) -> str | None:
        return joined(facts_of(db, entity_id=entity_id, facets=(name,)))

    return [
        {
            "section": "factions",
            "entity_id": entity.id,
            "name": entity.name,
            "description": facet(entity.id, "description"),
            "faction_type": faction.faction_type,
            "philosophy": facet(entity.id, "doctrine"),
            "internal_structure": facet(entity.id, "organisation"),
            "internal_tensions": facet(entity.id, "tension"),
            "magic_knowledge_level": faction.magic_knowledge_level,
        }
        for entity, faction in rows
    ]


def _identity_rows(entity_id: str, world_id: str, db: Session) -> list[dict]:
    entity = db.exec(
        select(Entity).where(Entity.id == entity_id, Entity.world_id == world_id)
    ).first()
    if entity is None:
        return []
    row = {
        "section": "identity",
        "entity_id": entity.id,
        "name": entity.name,
        "type": entity.type,
        "status": entity.status,
        "is_public": entity.is_public,
        "internal_name": entity.internal_name,
    }
    if entity.type == "character":
        character = db.get(Character, entity_id)
        if character is not None:
            row.update(
                character_type=character.character_type,
                current_location_id=character.current_location_id,
                vital_status=character.vital_status,
                physical_tier=character.physical_tier,
            )
    return [row]


def _facet_rows(entity_id: str, world_id: str, db: Session) -> list[dict]:
    """One `facets` row per descriptive fact of the entity, in registry
    order (TICKET-0091, BRIEF-0091-H). The creator's dossier is the ONLY
    legal `include_creator_only=True` call site (AMENDMENT-0091-01): the
    creator sees the note, tagged `secret`, and nothing here reaches Play.
    World-scoped: an entity of another world yields no row."""
    entity = db.exec(
        select(Entity).where(Entity.id == entity_id, Entity.world_id == world_id)
    ).first()
    if entity is None:
        return []
    facets = tuple(name for name in FACETS if name in DESCRIPTIVE_FACETS)
    rows = facts_of(db, entity_id=entity_id, facets=facets, include_creator_only=True)
    secret_ids = creator_only_fact_ids(db, [row.fact_id for row in rows])
    return [
        {
            "section": "facets",
            "facet": row.facet,
            "label": FACETS[row.facet].label,
            "aspect": row.aspect,
            "content": row.content,
            "secret": row.fact_id in secret_ids,
        }
        for row in rows
    ]


def _relation_rows(entity_id: str, world_id: str, db: Session) -> list[dict]:
    # `connects_to` is location map topology, never a social signal, and its
    # intensity=50 is meaningless (CLAUDE.md invariant) -- any new
    # world-wide relation scan must exclude it, on pain of presenting map
    # adjacency as if it were a narrative relation in the dossier.
    rows = db.exec(
        select(Relation).where(
            Relation.world_id == world_id,
            (Relation.entity_a_id == entity_id) | (Relation.entity_b_id == entity_id),
            Relation.type != "connects_to",
        )
    ).all()
    other_ids = {r.entity_b_id if r.entity_a_id == entity_id else r.entity_a_id for r in rows}
    names = {
        e.id: e.name
        for e in db.exec(
            select(Entity).where(Entity.id.in_(other_ids), Entity.world_id == world_id)
        ).all()
    } if other_ids else {}
    subject = db.get(Entity, entity_id)
    subject_name = subject.name if subject is not None else entity_id
    result = []
    for r in rows:
        subject_side = "a" if r.entity_a_id == entity_id else "b"
        other_id = r.entity_b_id if subject_side == "a" else r.entity_a_id
        result.append(
            {
                "section": "relations",
                "subject_side": subject_side,
                "subject_name": subject_name,
                "type": r.type,
                "direction": r.direction,
                "intensity": r.intensity,
                "notes": r.notes,
                "other_entity_id": other_id,
                "other_entity_name": names.get(other_id),
            }
        )
    return result


def _knowledge_rows(entity_id: str, world_id: str, db: Session) -> list[dict]:
    rows = db.exec(
        select(Knowledge).join(Entity, Entity.id == Knowledge.entity_id).where(
            Knowledge.entity_id == entity_id,
            Entity.world_id == world_id,
        )
    ).all()
    return [
        {
            "section": "knowledge",
            "subject": k.subject,
            "level": k.level,
            "content": text,
            "source": k.source,
            "is_incorrect": k.is_incorrect,
            "is_secret": k.is_secret,
        }
        for k, text in zip(rows, knowledge_texts(db, rows))
    ]


def _membership_rows(entity_id: str, db: Session) -> list[dict]:
    return [
        {"section": "memberships", "faction_name": faction_name, "role": role}
        for faction_name, role in read_public_memberships(entity_id, db)
    ]


def _goal_rows(entity_id: str, world_id: str, db: Session) -> list[dict]:
    rows = db.exec(
        select(NpcGoal).where(NpcGoal.world_id == world_id, NpcGoal.npc_id == entity_id)
    ).all()
    return [
        {
            "section": "goals",
            "description": g.description,
            "status": g.status,
            "horizon": g.horizon,
            "kind": g.kind,
        }
        for g in rows
    ]


def entity_dossier(entity_id: str, world_id: str, db: Session) -> list[dict]:
    """Flat list of row dicts across six sections — identity, facets,
    relations, knowledge, memberships, goals — each carrying a `"section"`
    key. No
    `traits` section: `entity_trait` is keyed by `entity_type_id` (a
    runtime-custom-entity-type projection, TICKET-0045), never by
    `entity_id`, so it cannot serve as a per-entity dossier section — see
    ARCHITECTURE_DECISIONS.md."""
    return (
        _identity_rows(entity_id, world_id, db)
        + _facet_rows(entity_id, world_id, db)
        + _relation_rows(entity_id, world_id, db)
        + _knowledge_rows(entity_id, world_id, db)
        + _membership_rows(entity_id, db)
        + _goal_rows(entity_id, world_id, db)
    )


def who_knows_about(entity_id: str, world_id: str, db: Session) -> list[dict]:
    """Who, in this world, holds knowledge about ONE entity (TICKET-0087,
    BRIEF-0087-e, C-04). One `coverage` row first, always -- first so the
    tail truncation at `row_cap` in `execute_plan` can never drop it -- then
    one `knowers` row per `knowledge` row whose fact carries a
    `fact_participant` for the asked entity, with no role filter (J2).
    Secrets and false beliefs are returned and marked by the renderer
    (F1b, F2); ordered by level rank descending, then knower name (F3)."""
    subject = db.exec(
        select(Entity).where(Entity.id == entity_id, Entity.world_id == world_id)
    ).first()
    subject_name = subject.name if subject is not None else None
    pairs = db.exec(
        select(Knowledge, Entity)
        .join(Entity, Entity.id == Knowledge.entity_id)
        .join(FactParticipant, FactParticipant.fact_id == Knowledge.fact_id)
        .where(Entity.world_id == world_id, FactParticipant.entity_id == entity_id)
    ).all()
    uncounted = db.exec(
        select(func.count(Knowledge.id))
        .join(Entity, Entity.id == Knowledge.entity_id)
        .outerjoin(FactParticipant, FactParticipant.fact_id == Knowledge.fact_id)
        .where(Entity.world_id == world_id, FactParticipant.id.is_(None))
    ).one()
    knowers = [
        {
            "section": "knowers",
            "knower_entity_id": knower.id,
            "knower_name": knower.name,
            "level": k.level,
            "content": text,
            "source": k.source,
            "is_incorrect": k.is_incorrect,
            "is_secret": k.is_secret,
            "subject_name": subject_name,
        }
        for (k, knower), text in zip(pairs, knowledge_texts(db, [k for k, _ in pairs]))
    ]
    knowers.sort(key=lambda r: (-knowledge_level_rank(r["level"]), r["knower_name"] or ""))
    coverage = {
        "section": "coverage",
        "subject_name": subject_name,
        "counted_rows": len(knowers),
        "uncounted_rows": uncounted,
    }
    return [coverage] + knowers


SELECTORS: tuple[str, ...] = ("entity_dossier", "world_factions", "who_knows_about")

_SELECTOR_LOOKUPS: dict[str, SelectorSpec] = {
    "entity_dossier": SelectorSpec(
        fn=entity_dossier, arity=2, row_cap=400, arg_kinds=("entity_id", "world_id"),
        context_sections=("identity",),
    ),
    "world_factions": SelectorSpec(
        fn=world_factions, arity=1, row_cap=200, arg_kinds=("world_id",),
    ),
    "who_knows_about": SelectorSpec(
        fn=who_knows_about, arity=2, row_cap=200,
        arg_kinds=("entity_id", "world_id"), context_sections=("coverage",),
    ),
}
