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
from pydantic import BaseModel, Field
from sqlalchemy import func
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
    NpcPrice,
    PromptTemplate,
    PromptVariable,
    ProposedMutation,
    Relation,
    Skill,
    SkillDefinition,
    SkillResolution,
    SkillSystem,
    World,
)
from ...prompt_registry import PROMPT_REGISTRY, effective_model
from ...prompt_store import current_prompt, get_version, list_versions
from ...skill_ranks import DEFAULT_RANK, MAX_RANK, RANK_POINTS_COLUMNS, RANKS, RankStep, points_to_next, skill_owners, world_ladder
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
    write_membership,
    write_npc_goal,
    write_npc_goal_prerequisites,
    write_npc_goal_status,
    write_npc_prices,
    write_prompt_version,
    write_relation,
    upsert_skill_rank,
    write_skill_rank,
    write_skill_row,
)

from ._router import router
from ._shared import _get_entity, _iso, _world_id


SKILL_DOMAINS = BASE_SKILL_DOMAINS


def _skill_dict(
    s: Skill, ladder: tuple[RankStep, ...], definition: SkillDefinition | None = None,
    system: SkillSystem | None = None,
) -> dict:
    return {
        "id": s.id,
        "character_id": s.character_id,
        "domain": s.domain,
        "skill_definition_id": s.skill_definition_id,
        "definition_name": definition.name if definition else None,
        "rank": s.rank,
        "rank_label": ladder[s.rank].label,
        "xp": s.xp,
        "points_to_next": points_to_next(s.rank, ladder, system=system, definition=definition),
        "requires_master": bool(definition.requires_master) if definition else False,
        "taught_by_id": s.taught_by_id,
        "change_history": s.change_history,
        "updated_at": _iso(s.updated_at),
    }


def _rank_step_dict(step: RankStep) -> dict:
    return {"rank": step.rank, "label": step.label, "points_to_next": step.points_to_next}


@router.get("/skill-ranks")
def list_skill_ranks(db: DbSession = Depends(get_session)) -> list[dict]:
    """The active world's six ranks, index = rank (`skill_ranks.world_ladder`:
    its `skill_rank` rows over the engine defaults). Read-only."""
    return [_rank_step_dict(step) for step in world_ladder(db, _world_id(db))]


class SkillRankStepBody(BaseModel):
    rank: int
    label: str
    points_to_next: Optional[int] = None


class SkillRanksBody(BaseModel):
    ranks: list[SkillRankStepBody]


@router.put("/skill-ranks")
def update_skill_ranks(body: SkillRanksBody, db: DbSession = Depends(get_session)) -> list[dict]:
    """Creator edit of the active world's ladder (TICKET-0106, BRIEF-0106-C,
    P2/O1): all six ranks at once, each a name and, below Maître, the points
    to leave it. Upserts the six `skill_rank` rows in one transaction; 422 on
    any invalid step, before any write."""
    world_id = _world_id(db)
    if sorted(step.rank for step in body.ranks) != list(RANKS):
        raise HTTPException(422, f"ranks must list each of {RANKS} exactly once")
    try:
        for step in body.ranks:
            upsert_skill_rank(db, world_id=world_id, rank=step.rank, label=step.label,
                              points_to_next=step.points_to_next)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(422, str(exc))
    db.commit()
    return [_rank_step_dict(step) for step in world_ladder(db, world_id)]


@router.get("/skills/player-characters")
def list_skill_player_characters(
    character_type: str = Query("player"), db: DbSession = Depends(get_session),
) -> list[dict]:
    """The active world's characters of one type (`player` by default, or
    `npc` since TICKET-0107), for the Fiche selector."""
    if character_type not in ("player", "npc"):
        raise HTTPException(422, "character_type must be 'player' or 'npc'")
    rows = db.exec(
        select(Entity, Character)
        .join(Character, Character.id == Entity.id)
        .where(Character.character_type == character_type)
        .where(Character.world_id == _world_id(db))
        .order_by(Entity.name)
    ).all()
    return [{"id": e.id, "name": e.name} for e, _ in rows]


def _masters(db: DbSession, world_id: str, *, definition_id: Optional[str], domain: Optional[str]) -> list[dict]:
    """The characters of the world at Maître in one skill (C1)."""
    stmt = (
        select(Entity)
        .join(Skill, Skill.character_id == Entity.id)
        .where(Entity.world_id == world_id, Skill.rank == MAX_RANK)
    )
    if definition_id is not None:
        stmt = stmt.where(Skill.skill_definition_id == definition_id)
    else:
        stmt = stmt.where(Skill.domain == domain, Skill.skill_definition_id.is_(None))
    return [{"id": e.id, "name": e.name} for e in db.exec(stmt.order_by(Entity.name)).all()]


@router.get("/skills/learnable")
def list_learnable_skills(character_id: str = Query(...), db: DbSession = Depends(get_session)) -> list[dict]:
    """The skills a character does not hold and may be given (TICKET-0107):
    for a player, the `requires_master` skills he was never taught (every
    open skill is held already); for an NPC, every base domain and every
    definition it holds no row for. Each with the masters who could teach
    it."""
    entity = _get_entity(db, character_id)
    character = db.get(Character, character_id)
    if character is None:
        raise HTTPException(422, f"{character_id!r} is not a character")
    held = db.exec(select(Skill).where(Skill.character_id == character_id)).all()
    held_definitions = {r.skill_definition_id for r in held if r.skill_definition_id}
    held_domains = {r.domain for r in held if r.skill_definition_id is None}
    out: list[dict] = []
    if character.character_type != "player":
        for domain in SKILL_DOMAINS:
            if domain not in held_domains:
                out.append({"domain": domain, "skill_definition_id": None, "name": domain, "requires_master": False,
                            "masters": _masters(db, entity.world_id, definition_id=None, domain=domain)})
    for definition in db.exec(select(SkillDefinition).where(SkillDefinition.world_id == entity.world_id)
                              .order_by(SkillDefinition.name)).all():
        if definition.id in held_definitions:
            continue
        if character.character_type == "player" and not definition.requires_master:
            continue
        out.append({"domain": definition.base_domain, "skill_definition_id": definition.id, "name": definition.name,
                    "requires_master": definition.requires_master,
                    "masters": _masters(db, entity.world_id, definition_id=definition.id, domain=None)})
    return out


class SkillGrantBody(BaseModel):
    character_id: str
    skill_definition_id: Optional[str] = None
    domain: Optional[str] = None
    rank: int = 0
    taught_by_id: Optional[str] = None


@router.post("/skills", status_code=201)
def grant_skill(body: SkillGrantBody, db: DbSession = Depends(get_session)) -> dict:
    """Creator grant of one skill row (TICKET-0107, C1): a skill learned, or
    an NPC's skill. `taught_by_id`, when given, must be another character of
    the world at Maître in that skill (422 otherwise); none = granted without
    a master, the creator's bypass. 409 when the character holds it already."""
    world_id = _world_id(db)
    entity = _get_entity(db, body.character_id)
    if entity.world_id != world_id or db.get(Character, body.character_id) is None:
        raise HTTPException(422, "character_id must be a character of the active world")
    if body.skill_definition_id is not None:
        definition = db.get(SkillDefinition, body.skill_definition_id)
        if definition is None or definition.world_id != world_id:
            raise HTTPException(422, "skill_definition_id must be a skill of the active world")
    if body.taught_by_id is not None:
        masters = _masters(db, world_id, definition_id=body.skill_definition_id, domain=body.domain)
        if body.taught_by_id == body.character_id or body.taught_by_id not in {m["id"] for m in masters}:
            raise HTTPException(422, "taught_by_id must be another character at Maître in this skill")
    held = select(Skill).where(Skill.character_id == body.character_id)
    held = (held.where(Skill.skill_definition_id == body.skill_definition_id) if body.skill_definition_id
            else held.where(Skill.domain == body.domain, Skill.skill_definition_id.is_(None)))
    if db.exec(held).first() is not None:
        raise HTTPException(409, "This character already holds this skill")
    try:
        row = write_skill_row(db, character_id=body.character_id, rank=body.rank, domain=body.domain,
                              skill_definition_id=body.skill_definition_id, taught_by_id=body.taught_by_id)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    db.commit()
    db.refresh(row)
    system, definition = skill_owners(db, row.skill_definition_id)
    return _skill_dict(row, world_ladder(db, world_id), definition, system)


@router.get("/skills")
def list_skills(character_id: str = Query(...), db: DbSession = Depends(get_session)) -> list[dict]:
    """A character's skill sheet (a player's, or an NPC's since TICKET-0107),
    in fixed domain order, each row with its rank's name and the points it
    needs to leave that rank."""
    entity = _get_entity(db, character_id)
    ladder = world_ladder(db, entity.world_id)
    rows = db.exec(
        select(Skill, SkillDefinition, SkillSystem)
        .outerjoin(SkillDefinition, Skill.skill_definition_id == SkillDefinition.id)
        .outerjoin(SkillSystem, SkillDefinition.system_id == SkillSystem.id)
        .where(Skill.character_id == character_id)
    ).all()
    order = {domain: i for i, domain in enumerate(SKILL_DOMAINS)}
    rows.sort(key=lambda r: order.get(r[0].domain, len(SKILL_DOMAINS)))
    return [_skill_dict(s, ladder, d, sys) for s, d, sys in rows]


class SkillRankBody(BaseModel):
    rank: int


@router.patch("/skills/{skill_id}")
def update_skill_rank(skill_id: str, body: SkillRankBody, db: DbSession = Depends(get_session)) -> dict:
    """Creator edit: set a skill's rank directly (canon write, no checkpoint).

    Archives the previous rank and points into `change_history`, restarts the
    points at 0 (U2) and bumps `updated_at` — but only on an actual change,
    so resubmitting the same rank is a no-op.
    """
    skill = db.get(Skill, skill_id)
    if skill is None:
        raise HTTPException(404, f"Skill {skill_id!r} not found")
    if body.rank not in RANKS:
        raise HTTPException(422, f"rank must be one of {RANKS}")

    if body.rank != skill.rank:
        write_skill_rank(db, skill_id=skill_id, rank=body.rank, changed_by="creator")
        db.commit()
        db.refresh(skill)

    entity = _get_entity(db, skill.character_id)
    system, definition = skill_owners(db, skill.skill_definition_id)
    return _skill_dict(skill, world_ladder(db, entity.world_id), definition, system)


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
        **_rank_points(s),
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


class RankPointsBody(BaseModel):
    """The five optional rank thresholds of a system or a skill (TICKET-0106,
    BRIEF-0106-C, O1): a positive count, or None to inherit. A PUT replaces
    all five, like every other field of its body."""
    points_to_rank_1: Optional[int] = Field(default=None, ge=1)
    points_to_rank_2: Optional[int] = Field(default=None, ge=1)
    points_to_rank_3: Optional[int] = Field(default=None, ge=1)
    points_to_rank_4: Optional[int] = Field(default=None, ge=1)
    points_to_rank_5: Optional[int] = Field(default=None, ge=1)


def _rank_points(row: Any) -> dict:
    return {column: getattr(row, column) for column in RANK_POINTS_COLUMNS}


def _set_rank_points(row: Any, body: RankPointsBody) -> None:
    for column in RANK_POINTS_COLUMNS:
        setattr(row, column, getattr(body, column))


class SkillSystemWriteBody(RankPointsBody):
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
    _set_rank_points(system, body)
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
    _set_rank_points(system, body)
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


# The two arbiter-failure sentinels `skill_lexicon.judge` records verdict=
# 'unmatched' for (see play_physical.py::_arbitrate/_parse_arbitrate_response).
# Ollama being unwell is not a hole in the world -- excluded from `gaps`,
# counted separately in `arbiter_failures` (BRIEF-0084-d).
_ARBITER_FAILURE_FORMS = {"__arbiter_error__": "error", "__arbiter_empty__": "empty"}


@router.get("/skill-gaps")
def list_skill_gaps(db: DbSession = Depends(get_session)) -> dict:
    """Distinct unmatched surface forms for the active world (BRIEF-0084-d).

    Read-only: performs no write of any kind. One entry per distinct
    `surface_form` among `verdict='unmatched'` rows, most frequent first —
    these are the terms the arbiter named that the world's catalogue does
    not cover. The two arbiter-failure sentinels are excluded from `gaps`
    and reported separately in `arbiter_failures`.
    """
    world_id = _world_id(db)
    rows = db.exec(
        select(
            SkillResolution.surface_form,
            func.count(SkillResolution.id),
            func.max(SkillResolution.created_at),
        )
        .where(SkillResolution.world_id == world_id)
        .where(SkillResolution.verdict == "unmatched")
        .group_by(SkillResolution.surface_form)
        .order_by(func.count(SkillResolution.id).desc(), func.max(SkillResolution.created_at).desc())
    ).all()

    gaps: list[dict] = []
    arbiter_failures = {"error": 0, "empty": 0}
    for surface_form, count, last_seen in rows:
        failure_key = _ARBITER_FAILURE_FORMS.get(surface_form)
        if failure_key is not None:
            arbiter_failures[failure_key] = count
            continue
        gaps.append({"surface_form": surface_form, "count": count, "last_seen": _iso(last_seen)})

    return {"gaps": gaps, "arbiter_failures": arbiter_failures}


def _skill_definition_dict(d: SkillDefinition) -> dict:
    return {
        "id": d.id,
        "world_id": d.world_id,
        "name": d.name,
        "base_domain": d.base_domain,
        "system_id": d.system_id,
        "description": d.description,
        "requires_master": d.requires_master,
        **_rank_points(d),
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


class SkillDefinitionWriteBody(RankPointsBody):
    name: str
    base_domain: str
    system_id: Optional[str] = None
    description: Optional[str] = None
    # TICKET-0107 (A2): learned only from a master -- no player character
    # holds a row for it until taught.
    requires_master: bool = False


def _backfill_open_skill(db: DbSession, definition: SkillDefinition) -> None:
    """A skill open to all (`requires_master` false): every player character
    of its world that lacks a row for it gets one at `DEFAULT_RANK`, through
    `write_skill_row` -- the catalogue<->PC alignment of open skills."""
    holders = set(db.exec(select(Skill.character_id).where(Skill.skill_definition_id == definition.id)).all())
    for character_id in db.exec(
        select(Character.id)
        .where(Character.world_id == definition.world_id)
        .where(Character.character_type == "player")
    ).all():
        if character_id not in holders:
            write_skill_row(db, character_id=character_id, skill_definition_id=definition.id, rank=DEFAULT_RANK)


@router.post("/skill-definitions", status_code=201)
def create_skill_definition(
    body: SkillDefinitionWriteBody, db: DbSession = Depends(get_session)
) -> dict:
    """Add a custom skill to the active world's catalogue (D2-backfill-yes).

    Backfills, for a skill open to all, a `skill` row at `DEFAULT_RANK`
    (Initié) onto every existing player character of the world, in the SAME
    transaction (`_backfill_open_skill`): every PC always holds every open
    skill. A `requires_master` skill backfills nothing -- it is held only
    once taught (TICKET-0107, A2).
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
        requires_master=body.requires_master,
    )
    _set_rank_points(definition, body)
    db.add(definition)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, f"A skill named {name!r} already exists in this world")

    if not definition.requires_master:
        _backfill_open_skill(db, definition)

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
    Turning `requires_master` off backfills the open skill onto every PC
    lacking it; turning it on keeps every row already held (TICKET-0107).
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
    opened = definition.requires_master and not body.requires_master
    definition.requires_master = body.requires_master
    definition.name = name
    definition.base_domain = body.base_domain
    definition.system_id = body.system_id
    definition.description = body.description
    _set_rank_points(definition, body)
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
    if opened:
        db.flush()
        _backfill_open_skill(db, definition)

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
