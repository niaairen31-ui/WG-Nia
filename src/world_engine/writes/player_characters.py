"""The one writer of a new player character (TICKET-0129, BRIEF-0129-A):
the entity, its `character` row, its base-domain and open skills, its facets
and its knowledge, in the caller's transaction.

Moved verbatim out of `cockpit/routes/creator.py::create_player_character`
(pure move). Adds and flushes; never commits (INV-18) and never validates
the place -- its callers do.

`ranks` and `teachers` (TICKET-0129, BRIEF-0129-E): the approval writes the
player's ranks, and each skill that requires a master with its teacher; the
route passes neither. `write_master_rank` sets a master's skill to Maître.
"""

from __future__ import annotations

from typing import Mapping, Optional

from sqlmodel import Session, select

from ..models import BASE_SKILL_DOMAINS, Character, Entity, Skill, SkillDefinition
from ..skill_ranks import DEFAULT_RANK, MAX_RANK
from .characters import write_skill_rank, write_skill_row
from .facets import write_entity_facets
from .knowledge import KNOWLEDGE_LEVELS, write_knowledge


def _pc_custom_skill_defs(world_id: str, db: Session) -> list[SkillDefinition]:
    """The skills a new PC holds: every definition open to all -- a
    `requires_master` one is held only once taught (TICKET-0107, A2)."""
    return db.exec(
        select(SkillDefinition).where(
            SkillDefinition.world_id == world_id,
            SkillDefinition.requires_master == False,  # noqa: E712
        )
    ).all()


def _write_pc_knowledge(entity_id: str, knowledge_items: Optional[list], db: Session) -> None:
    """BRIEF-52 (E1): PC creation assistant draft knowledge, written
    `is_secret=False` through `write_knowledge` — never through
    `POST /api/entities/{id}/knowledge`, which 422s on a bad level instead
    of defaulting to "rumor"."""
    for item in (knowledge_items or []):
        level = item.level if item.level in KNOWLEDGE_LEVELS else "rumor"
        write_knowledge(
            db,
            entity_id=entity_id,
            level=level,
            content=item.content,
            source="pc_creation",
            is_incorrect=False,
            is_secret=False,
            share_threshold=50,
            session_id=None,
        )


def write_player_character(db: Session, *, world_id: str, user_id: str, name: str,
                           current_location_id: str, facets: Optional[dict],
                           knowledge: Optional[list], ranks: Optional[Mapping[str, int]] = None,
                           teachers: Optional[Mapping[str, str]] = None) -> Entity:
    """Write a new PC's entity, `character` row, skills, facets and
    knowledge; return the flushed entity. `knowledge` items carry `.level`
    and `.content`. `ranks` maps a base domain or a definition id of the
    world to a rank (default `DEFAULT_RANK`); a definition that requires a
    master is written only at rank >= 1, taught by `teachers[definition.id]`.
    `ValueError` before any write on an unknown `ranks` key."""
    ranks = ranks or {}
    teachers = teachers or {}
    taught = db.exec(
        select(SkillDefinition).where(
            SkillDefinition.world_id == world_id,
            SkillDefinition.requires_master == True,  # noqa: E712
        ).order_by(SkillDefinition.name, SkillDefinition.id)
    ).all()
    open_defs = _pc_custom_skill_defs(world_id, db)
    known = set(BASE_SKILL_DOMAINS) | {d.id for d in open_defs} | {d.id for d in taught}
    unknown = sorted(key for key in ranks if key not in known)
    if unknown:
        raise ValueError(f"write_player_character: unknown skill keys {unknown!r}")
    entity = Entity(
        world_id=world_id,
        type="character",
        name=name,
    )
    db.add(entity)
    db.flush()
    character = Character(
        id=entity.id,
        world_id=world_id,
        character_type="player",
        user_id=user_id,
        current_location_id=current_location_id,
    )
    db.add(character)
    db.flush()
    write_entity_facets(db, entity_id=entity.id, facets=facets or {}, created_by="creator_crud")
    for domain in BASE_SKILL_DOMAINS:
        db.add(Skill(character_id=entity.id, domain=domain, rank=ranks.get(domain, DEFAULT_RANK)))
    # B1 (schema v1.63): flat default-rank seed for every custom skill of the
    # PC's world — never proposed by a model, set here after the draft
    # is accepted.
    for definition in open_defs:
        db.add(Skill(
            character_id=entity.id,
            domain=definition.base_domain,
            skill_definition_id=definition.id,
            rank=ranks.get(definition.id, DEFAULT_RANK),
        ))
    for definition in taught:
        rank = ranks.get(definition.id, 0)
        if rank < 1:
            continue
        if definition.id not in teachers:
            raise ValueError(f"« {name} » : il manque le maître de « {definition.name} ».")
        write_skill_row(db, character_id=entity.id, rank=rank, skill_definition_id=definition.id,
                        taught_by_id=teachers[definition.id])
    _write_pc_knowledge(entity.id, knowledge, db)
    return entity


def write_master_rank(db: Session, *, character_id: str, skill_key: str) -> Skill:
    """Set `character_id`'s skill `skill_key` (a base domain, else a
    definition id) to `MAX_RANK`: the held row through `write_skill_rank`,
    else a new row through `write_skill_row`. Never commits."""
    if skill_key in BASE_SKILL_DOMAINS:
        held = select(Skill).where(Skill.character_id == character_id, Skill.domain == skill_key,
                                   Skill.skill_definition_id.is_(None))
    else:
        held = select(Skill).where(Skill.character_id == character_id,
                                   Skill.skill_definition_id == skill_key)
    row = db.exec(held).first()
    if row is None:
        if skill_key in BASE_SKILL_DOMAINS:
            return write_skill_row(db, character_id=character_id, rank=MAX_RANK, domain=skill_key)
        return write_skill_row(db, character_id=character_id, rank=MAX_RANK, skill_definition_id=skill_key)
    skill = write_skill_rank(db, skill_id=row.id, rank=MAX_RANK, changed_by="creator")
    db.add(skill)
    return skill
