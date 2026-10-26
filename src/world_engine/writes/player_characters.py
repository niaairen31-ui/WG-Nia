"""The one writer of a new player character (TICKET-0129, BRIEF-0129-A):
the entity, its `character` row, its base-domain and open skills, its facets
and its knowledge, in the caller's transaction.

Moved verbatim out of `cockpit/routes/creator.py::create_player_character`
(pure move). Adds and flushes; never commits (INV-18) and never validates
the place -- its callers do.
"""

from __future__ import annotations

from typing import Optional

from sqlmodel import Session, select

from ..models import BASE_SKILL_DOMAINS, Character, Entity, Skill, SkillDefinition
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
                           knowledge: Optional[list]) -> Entity:
    """Write a new PC's entity, `character` row, skills, facets and
    knowledge; return the flushed entity. `knowledge` items carry `.level`
    and `.content`."""
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
        db.add(Skill(character_id=entity.id, domain=domain))
    # B1 (schema v1.63): flat default-rank seed for every custom skill of the
    # PC's world — never proposed by a model, set here after the draft
    # is accepted.
    for definition in _pc_custom_skill_defs(world_id, db):
        db.add(Skill(
            character_id=entity.id,
            domain=definition.base_domain,
            skill_definition_id=definition.id,
        ))
    _write_pc_knowledge(entity.id, knowledge, db)
    return entity
