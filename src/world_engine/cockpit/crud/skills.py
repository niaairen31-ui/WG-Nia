"""Author CRUD — PC skill sheet and the world-scoped custom skill
catalogue (skill_definition).

Split out of `cockpit/crud.py` (TICKET-0027, BRIEF-0027-d) — pure move,
no logic change.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session as DbSession, select

from ...db import get_session
from ...entity_author import generate_npc_goals
from ...gathering import close_open_memberships
from ...ledger import get_balance, list_entries
from ...ollama_client import OllamaError, ping
from ...models import (
    Agenda,
    AgendaStep,
    BASE_SKILL_DOMAINS,
    Character,
    DiscoverableDetail,
    Entity,
    Event,
    EventEntity,
    Faction,
    FactionMembership,
    FactionRole,
    GoalAgendaLink,
    GoalPrerequisite,
    Item,
    Knowledge,
    Ledger,
    Location,
    LocationSubculture,
    NpcPrice,
    PromptTemplate,
    PromptVariable,
    ProposedMutation,
    Relation,
    Skill,
    SkillDefinition,
    SkillSystem,
    World,
)
from ...prompt_registry import PROMPT_REGISTRY, effective_model
from ...prompt_store import current_prompt, get_version, list_versions
from ...tick_normalize import _EVENT_TYPES
from ...writes import (
    KNOWLEDGE_LEVELS,
    NPC_GOAL_HORIZONS,
    NPC_GOAL_PREREQUISITE_TYPES,
    PromptValidationError,
    detach_goal_agenda_link,
    write_agenda,
    write_agenda_status,
    write_agenda_step,
    write_agenda_step_status,
    write_event,
    write_event_update,
    write_faction_role,
    write_goal_agenda_link,
    write_knowledge,
    write_ledger_entry,
    write_location_subculture,
    write_membership,
    write_npc_goal,
    write_npc_goal_prerequisites,
    write_npc_goal_status,
    write_npc_prices,
    write_prompt_version,
    write_relation,
    write_skill_tier,
)

from ._router import router
from ._shared import _get_entity, _iso, _world_id


SKILL_DOMAINS = BASE_SKILL_DOMAINS


SKILL_TIERS = (-1, 0, 1, 2)


def _skill_dict(s: Skill, definition_name: str | None = None) -> dict:
    return {
        "id": s.id,
        "character_id": s.character_id,
        "domain": s.domain,
        "skill_definition_id": s.skill_definition_id,
        "definition_name": definition_name,
        "tier": s.tier,
        "change_history": s.change_history,
        "updated_at": _iso(s.updated_at),
    }


@router.get("/skills/player-characters")
def list_skill_player_characters(db: DbSession = Depends(get_session)) -> list[dict]:
    """Player characters (`character_type = 'player'`), for the Fiche selector."""
    rows = db.exec(
        select(Entity, Character)
        .join(Character, Character.id == Entity.id)
        .where(Character.character_type == "player")
        .where(Character.world_id == _world_id(db))
        .order_by(Entity.name)
    ).all()
    return [{"id": e.id, "name": e.name} for e, _ in rows]


@router.get("/skills")
def list_skills(character_id: str = Query(...), db: DbSession = Depends(get_session)) -> list[dict]:
    """A player character's skill sheet, in fixed domain order."""
    _get_entity(db, character_id)
    pairs = db.exec(
        select(Skill, SkillDefinition)
        .outerjoin(SkillDefinition, Skill.skill_definition_id == SkillDefinition.id)
        .where(Skill.character_id == character_id)
    ).all()
    order = {domain: i for i, domain in enumerate(SKILL_DOMAINS)}
    pairs.sort(key=lambda p: order.get(p[0].domain, len(SKILL_DOMAINS)))
    return [_skill_dict(s, d.name if d else None) for s, d in pairs]


class SkillTierBody(BaseModel):
    tier: int


@router.patch("/skills/{skill_id}")
def update_skill_tier(skill_id: str, body: SkillTierBody, db: DbSession = Depends(get_session)) -> dict:
    """Creator edit: set a skill's tier directly (canon write, no checkpoint).

    Archives the previous tier into `change_history` and bumps `updated_at`
    — but only on an actual change, so resubmitting the same tier is a no-op.
    """
    skill = db.get(Skill, skill_id)
    if skill is None:
        raise HTTPException(404, f"Skill {skill_id!r} not found")
    if body.tier not in SKILL_TIERS:
        raise HTTPException(422, f"tier must be one of {SKILL_TIERS}")

    if body.tier != skill.tier:
        write_skill_tier(db, skill_id=skill_id, tier=body.tier, changed_by="creator")
        db.commit()
        db.refresh(skill)

    return _skill_dict(skill)


def _skill_system_dict(s: SkillSystem, db: DbSession) -> dict:
    skill_count = len(db.exec(
        select(SkillDefinition.id).where(SkillDefinition.system_id == s.id)
    ).all())
    return {
        "id": s.id,
        "world_id": s.world_id,
        "name": s.name,
        "description": s.description,
        "skill_count": skill_count,
        "updated_at": _iso(s.updated_at),
    }


@router.get("/skill-systems")
def list_skill_systems(db: DbSession = Depends(get_session)) -> list[dict]:
    """The active world's skill systems (magic, technology, ritual, ...)."""
    rows = db.exec(
        select(SkillSystem)
        .where(SkillSystem.world_id == _world_id(db))
        .order_by(SkillSystem.name)
    ).all()
    return [_skill_system_dict(s, db) for s in rows]


class SkillSystemWriteBody(BaseModel):
    name: str
    description: Optional[str] = None


@router.post("/skill-systems", status_code=201)
def create_skill_system(
    body: SkillSystemWriteBody, db: DbSession = Depends(get_session)
) -> dict:
    """Add a skill system to the active world.

    No backfill of any kind: creating a system never touches `skill` or
    `skill_definition` — unlike `POST /skill-definitions`.
    """
    world_id = _world_id(db)
    name = body.name.strip()
    if not name:
        raise HTTPException(422, "name is required")

    system = SkillSystem(world_id=world_id, name=name, description=body.description)
    db.add(system)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, f"A skill system named {name!r} already exists in this world")
    db.refresh(system)
    return _skill_system_dict(system, db)


@router.put("/skill-systems/{system_id}")
def update_skill_system(
    system_id: str, body: SkillSystemWriteBody, db: DbSession = Depends(get_session)
) -> dict:
    """Rename / re-word a skill system."""
    system = db.get(SkillSystem, system_id)
    if system is None or system.world_id != _world_id(db):
        raise HTTPException(404, f"SkillSystem {system_id!r} not found")
    name = body.name.strip()
    if not name:
        raise HTTPException(422, "name is required")

    system.name = name
    system.description = body.description
    system.updated_at = datetime.now(UTC)
    db.add(system)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, f"A skill system named {name!r} already exists in this world")
    db.refresh(system)
    return _skill_system_dict(system, db)


@router.delete("/skill-systems/{system_id}")
def delete_skill_system(system_id: str, db: DbSession = Depends(get_session)) -> dict:
    """Delete a skill system (D2b-delete-refuse).

    Fail-closed, unlike `DELETE /skill-definitions` above: refuses while any
    `skill_definition` still carries this `system_id`. A system is a
    container the creator authored — silently orphaning her catalogue is
    worse than making her say it twice. Returns before any `db.delete` on
    every refusal path.
    """
    system = db.get(SkillSystem, system_id)
    if system is None or system.world_id != _world_id(db):
        raise HTTPException(404, f"SkillSystem {system_id!r} not found")

    attached = db.exec(
        select(SkillDefinition.id).where(SkillDefinition.system_id == system.id)
    ).all()
    if attached:
        raise HTTPException(
            409,
            "Cannot delete a skill system that still has skills attached — "
            "detach or delete them first.",
        )

    db.delete(system)
    db.commit()
    return {"deleted": system_id}


def _skill_definition_dict(d: SkillDefinition) -> dict:
    return {
        "id": d.id,
        "world_id": d.world_id,
        "name": d.name,
        "base_domain": d.base_domain,
        "system_id": d.system_id,
        "description": d.description,
        "updated_at": _iso(d.updated_at),
    }


@router.get("/skill-definitions")
def list_skill_definitions(db: DbSession = Depends(get_session)) -> list[dict]:
    """The active world's custom skill catalogue."""
    rows = db.exec(
        select(SkillDefinition)
        .where(SkillDefinition.world_id == _world_id(db))
        .order_by(SkillDefinition.name)
    ).all()
    return [_skill_definition_dict(d) for d in rows]


class SkillDefinitionWriteBody(BaseModel):
    name: str
    base_domain: str
    system_id: Optional[str] = None
    description: Optional[str] = None


@router.post("/skill-definitions", status_code=201)
def create_skill_definition(
    body: SkillDefinitionWriteBody, db: DbSession = Depends(get_session)
) -> dict:
    """Add a custom skill to the active world's catalogue (D2-backfill-yes).

    Backfills: inserts a tier-0 `skill` row for this definition onto every
    existing player character of the world, in the SAME transaction, so the
    catalogue<->PC alignment that makes the arbiter lookup total never
    lapses (BRIEF-55's invariant — every PC always has every world skill).
    """
    world_id = _world_id(db)
    name = body.name.strip()
    if not name:
        raise HTTPException(422, "name is required")
    if name.lower() in BASE_SKILL_DOMAINS:
        raise HTTPException(422, "name must not be a base domain literal")
    if body.base_domain not in BASE_SKILL_DOMAINS:
        raise HTTPException(422, f"base_domain must be one of {BASE_SKILL_DOMAINS}")
    if body.system_id is not None:
        system = db.get(SkillSystem, body.system_id)
        if system is None or system.world_id != world_id:
            raise HTTPException(422, "system_id must reference a skill system of the active world")

    definition = SkillDefinition(
        world_id=world_id,
        name=name,
        base_domain=body.base_domain,
        system_id=body.system_id,
        description=body.description,
    )
    db.add(definition)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, f"A skill named {name!r} already exists in this world")

    pc_ids = db.exec(
        select(Character.id)
        .where(Character.world_id == world_id)
        .where(Character.character_type == "player")
    ).all()
    for character_id in pc_ids:
        db.add(Skill(
            character_id=character_id,
            domain=definition.base_domain,
            tier=0,
            skill_definition_id=definition.id,
        ))

    db.commit()
    db.refresh(definition)
    return _skill_definition_dict(definition)


@router.put("/skill-definitions/{definition_id}")
def update_skill_definition(
    definition_id: str,
    body: SkillDefinitionWriteBody,
    db: DbSession = Depends(get_session),
) -> dict:
    """Rename / re-base / re-word a custom skill.

    Rename is safe by construction (every reader joins by id, never copies
    the name onto a `skill` row). Changing `base_domain` re-points
    resolution for every existing PC `skill` row referencing this
    definition — also updates their `domain` column so the 2d6 bands and
    the base-domain CHECK stay consistent (mirrors the create-time seed).
    """
    definition = db.get(SkillDefinition, definition_id)
    if definition is None or definition.world_id != _world_id(db):
        raise HTTPException(404, f"SkillDefinition {definition_id!r} not found")
    name = body.name.strip()
    if not name:
        raise HTTPException(422, "name is required")
    if name.lower() in BASE_SKILL_DOMAINS:
        raise HTTPException(422, "name must not be a base domain literal")
    if body.base_domain not in BASE_SKILL_DOMAINS:
        raise HTTPException(422, f"base_domain must be one of {BASE_SKILL_DOMAINS}")
    if body.system_id is not None:
        system = db.get(SkillSystem, body.system_id)
        if system is None or system.world_id != definition.world_id:
            raise HTTPException(422, "system_id must reference a skill system of the active world")

    domain_changed = body.base_domain != definition.base_domain
    definition.name = name
    definition.base_domain = body.base_domain
    definition.system_id = body.system_id
    definition.description = body.description
    definition.updated_at = datetime.now(UTC)
    db.add(definition)

    if domain_changed:
        dependent = db.exec(
            select(Skill).where(Skill.skill_definition_id == definition.id)
        ).all()
        for skill in dependent:
            skill.domain = body.base_domain
            skill.updated_at = datetime.now(UTC)
            db.add(skill)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, f"A skill named {name!r} already exists in this world")
    db.refresh(definition)
    return _skill_definition_dict(definition)


@router.delete("/skill-definitions/{definition_id}")
def delete_skill_definition(
    definition_id: str, db: DbSession = Depends(get_session)
) -> dict:
    """Delete a custom skill definition (D2-delete-cascade).

    Always possible — never blocked by the structural `ON DELETE RESTRICT`
    floor. Deletes every dependent PC `skill` row first, then the
    definition, in one transaction. Per the locked decision, this cascade
    carries no separate history snapshot — the creator-side confirmation
    (type "Oui") is the safeguard, the same idiom as world block deletion.
    """
    definition = db.get(SkillDefinition, definition_id)
    if definition is None or definition.world_id != _world_id(db):
        raise HTTPException(404, f"SkillDefinition {definition_id!r} not found")

    dependent = db.exec(
        select(Skill).where(Skill.skill_definition_id == definition.id)
    ).all()
    for skill in dependent:
        db.delete(skill)
    db.delete(definition)
    db.commit()
    return {"deleted": definition_id, "skills_removed": len(dependent)}
