"""Author CRUD — faction roles and faction membership.

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
from ._shared import _get_entity, _iso


class FactionRoleCreateBody(BaseModel):
    name: str
    description: Optional[str] = None
    max_holders: Optional[int] = None


class FactionRoleUpdateBody(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    max_holders: Optional[int] = None


class FactionRoleReorderBody(BaseModel):
    role_ids: list[str] = []


class MembershipOpenBody(BaseModel):
    faction_id: str
    role: Optional[str] = None
    cover_role: Optional[str] = None
    is_primary: bool = False
    is_secret: bool = False


def _membership_dict(m: FactionMembership, db: DbSession) -> dict:
    member = db.get(Entity, m.entity_id)
    faction = db.get(Entity, m.faction_id)
    return {
        "id": m.id,
        "entity_id": m.entity_id,
        "entity_name": member.name if member else m.entity_id,
        "faction_id": m.faction_id,
        "faction_name": faction.name if faction else m.faction_id,
        "role": m.role,
        "cover_role": m.cover_role,
        "is_primary": m.is_primary,
        "is_secret": m.is_secret,
        "joined_at": _iso(m.joined_at),
        "left_at": _iso(m.left_at),
    }


@router.get("/entities/{faction_id}/roles")
def list_faction_roles(faction_id: str, db: DbSession = Depends(get_session)) -> list[dict]:
    """Curated, ordered role vocabulary for a faction — membership role
    select contract (names-only, order = rank). Reads the `faction_role`
    table (TICKET-0024, BRIEF-0024-d — corrective, replaces
    `entity.metadata['roles']`). Public org vocabulary — no secret
    filtering applies.
    """
    faction = _get_entity(db, faction_id)
    if faction.type != "faction":
        raise HTTPException(422, f"{faction_id!r} is not a faction entity")
    roles = db.exec(
        select(FactionRole)
        .where(FactionRole.faction_id == faction_id)
        .order_by(FactionRole.position)
    ).all()
    return [{"name": r.name, "description": r.description} for r in roles]


def _active_role_counts(db: DbSession, faction_id: str) -> dict[str, int]:
    """Casefold -> count of ACTIVE memberships bearing that true `role`."""
    holder_roles = db.exec(
        select(FactionMembership.role)
        .where(FactionMembership.faction_id == faction_id, FactionMembership.left_at.is_(None))
    ).all()
    counts: dict[str, int] = {}
    for role_name in holder_roles:
        if role_name:
            folded = role_name.casefold()
            counts[folded] = counts.get(folded, 0) + 1
    return counts


def _faction_role_dict(role: FactionRole, active_holder_count: int) -> dict:
    return {
        "id": role.id,
        "faction_id": role.faction_id,
        "name": role.name,
        "description": role.description,
        "max_holders": role.max_holders,
        "position": role.position,
        "active_holder_count": active_holder_count,
    }


@router.get("/factions/{faction_id}/roles")
def list_faction_role_rows(faction_id: str, db: DbSession = Depends(get_session)) -> dict:
    """Faction sheet's ROLES editor: full `faction_role` rows ordered by
    `position`, plus the DISTINCT true `role` values on ACTIVE memberships
    that match NO declared row (casefold) — the undeclared-borne-roles
    adoption hint source (TICKET-0024, BRIEF-0024-d)."""
    entity = _get_entity(db, faction_id)
    if entity.type != "faction":
        raise HTTPException(422, f"{faction_id!r} is not a faction entity")
    roles = db.exec(
        select(FactionRole)
        .where(FactionRole.faction_id == faction_id)
        .order_by(FactionRole.position)
    ).all()
    counts = _active_role_counts(db, faction_id)
    declared_casefold = {r.name.casefold() for r in roles}
    active_role_names = db.exec(
        select(FactionMembership.role)
        .where(FactionMembership.faction_id == faction_id, FactionMembership.left_at.is_(None))
        .distinct()
    ).all()
    undeclared = sorted({
        name for name in active_role_names
        if name and name.casefold() not in declared_casefold
    })
    return {
        "roles": [_faction_role_dict(r, counts.get(r.name.casefold(), 0)) for r in roles],
        "undeclared_active_roles": undeclared,
    }


@router.post("/factions/{faction_id}/roles", status_code=201)
def create_faction_role(
    faction_id: str, body: FactionRoleCreateBody, db: DbSession = Depends(get_session)
) -> dict:
    entity = _get_entity(db, faction_id)
    if entity.type != "faction":
        raise HTTPException(422, f"{faction_id!r} is not a faction entity")
    try:
        role = write_faction_role(
            db, mode="create", world_id=entity.world_id, faction_id=faction_id,
            name=body.name, description=body.description, max_holders=body.max_holders,
            changed_by="creator",
        )
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(422, str(exc))
    db.refresh(role)
    return _faction_role_dict(role, _active_role_counts(db, faction_id).get(role.name.casefold(), 0))


@router.patch("/factions/{faction_id}/roles/reorder")
def reorder_faction_roles(
    faction_id: str, body: FactionRoleReorderBody, db: DbSession = Depends(get_session)
) -> dict:
    """Full ordered id list — `position` is rewritten 0..n-1 to match."""
    entity = _get_entity(db, faction_id)
    if entity.type != "faction":
        raise HTTPException(422, f"{faction_id!r} is not a faction entity")
    roles = {
        r.id: r for r in db.exec(
            select(FactionRole).where(FactionRole.faction_id == faction_id)
        ).all()
    }
    if set(body.role_ids) != set(roles.keys()):
        raise HTTPException(422, "reorder: role_ids must be exactly this faction's role ids, no more, no less")
    for position, role_id in enumerate(body.role_ids):
        write_faction_role(
            db, mode="update", role_id=role_id,
            description=roles[role_id].description, max_holders=roles[role_id].max_holders,
            position=position,
        )
    db.commit()
    return list_faction_role_rows(faction_id, db)


@router.patch("/factions/{faction_id}/roles/{role_id}")
def update_faction_role(
    faction_id: str, role_id: str, body: FactionRoleUpdateBody, db: DbSession = Depends(get_session)
) -> dict:
    """Field edit and/or rename in one call — a `name` differing from the
    stored value triggers `mode="rename"` (T1: realigns active memberships
    holding the old name) before `description`/`max_holders` are applied."""
    role = db.get(FactionRole, role_id)
    if role is None or role.faction_id != faction_id:
        raise HTTPException(404, f"faction_role {role_id!r} not found")
    try:
        if body.name is not None and body.name.strip() and body.name.strip() != role.name:
            role = write_faction_role(db, mode="rename", role_id=role_id, name=body.name)
        role = write_faction_role(
            db, mode="update", role_id=role_id,
            description=body.description, max_holders=body.max_holders,
        )
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(422, str(exc))
    db.refresh(role)
    return _faction_role_dict(role, _active_role_counts(db, faction_id).get(role.name.casefold(), 0))


@router.delete("/factions/{faction_id}/roles/{role_id}")
def delete_faction_role(faction_id: str, role_id: str, db: DbSession = Depends(get_session)) -> dict:
    role = db.get(FactionRole, role_id)
    if role is None or role.faction_id != faction_id:
        raise HTTPException(404, f"faction_role {role_id!r} not found")
    try:
        write_faction_role(db, mode="delete", role_id=role_id)
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(422, str(exc))
    return {"deleted": True}


@router.get("/entities/{entity_id}/memberships")
def list_entity_memberships(entity_id: str, db: DbSession = Depends(get_session)) -> list[dict]:
    """Active memberships for a member (character sheet "Appartenances" list)."""
    _get_entity(db, entity_id)
    rows = db.exec(
        select(FactionMembership)
        .where(FactionMembership.entity_id == entity_id, FactionMembership.left_at.is_(None))
    ).all()
    return [_membership_dict(m, db) for m in rows]


def _open_membership_core(
    entity_id: str, body: MembershipOpenBody, db: DbSession
) -> FactionMembership:
    """Commit-free core of `open_entity_membership` (BRIEF-35).

    Flushes (not commits) so the partial-unique-index `IntegrityError`
    surfaces deterministically at the core call site, catchable by either
    caller (this route's wrapper or a future batch caller).
    """
    entity = _get_entity(db, entity_id)
    faction = db.get(Entity, body.faction_id)
    if faction is None or faction.type != "faction":
        raise HTTPException(422, f"{body.faction_id!r} is not a valid faction entity id")

    membership = write_membership(
        db,
        mode="open",
        world_id=entity.world_id,
        entity_id=entity_id,
        faction_id=body.faction_id,
        role=body.role,
        cover_role=body.cover_role,
        is_primary=body.is_primary,
        is_secret=body.is_secret,
    )
    db.flush()
    return membership


@router.post("/entities/{entity_id}/memberships", status_code=201)
def open_entity_membership(
    entity_id: str, body: MembershipOpenBody, db: DbSession = Depends(get_session)
) -> dict:
    try:
        membership = _open_membership_core(entity_id, body, db)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            409,
            "Membership conflicts with an existing active row — at most one "
            "active primary per member, and no duplicate active membership "
            "in the same faction. Close the existing membership first.",
        )
    db.refresh(membership)
    return _membership_dict(membership, db)


@router.post("/memberships/{membership_id}/close")
def close_entity_membership(membership_id: str, db: DbSession = Depends(get_session)) -> dict:
    try:
        membership = write_membership(db, mode="close", membership_id=membership_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc))
    db.commit()
    db.refresh(membership)
    return _membership_dict(membership, db)


@router.get("/entities/{entity_id}/faction-roster")
def get_faction_roster(entity_id: str, db: DbSession = Depends(get_session)) -> list[dict]:
    """Active members of a faction (faction sheet read-only roster).

    Secret members ARE included, with their `is_secret` badge — the creator
    sees everything; the structural exclusion belongs to the future
    player-facing reader, which does not exist yet (Scope OUT, BRIEF-27).
    """
    _get_entity(db, entity_id)
    rows = db.exec(
        select(FactionMembership)
        .where(FactionMembership.faction_id == entity_id, FactionMembership.left_at.is_(None))
    ).all()
    return [_membership_dict(m, db) for m in rows]
