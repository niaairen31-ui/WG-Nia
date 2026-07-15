"""Author CRUD — discoverable details, the location map graph, and
location hierarchy browse.

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
from ._shared import _get_entity, _iso, _world_id


ACCESS_LEVELS = ("hidden", "ambient")


def _detail_dict(d: DiscoverableDetail) -> dict:
    return {
        "id": d.id,
        "world_id": d.world_id,
        "location_id": d.location_id,
        "subject": d.subject,
        "content": d.content,
        "access_level": d.access_level,
        "discovery_threshold": d.discovery_threshold,
        "discovered": d.discovered,
        "signpost_group": d.signpost_group,
        "created_at": _iso(d.created_at),
        "updated_at": _iso(d.updated_at),
    }


@router.get("/locations/{location_id}/discoverable-details")
def list_discoverable_details(
    location_id: str, db: DbSession = Depends(get_session)
) -> list[dict]:
    """List all discoverable details for a location (creator view)."""
    _get_entity(db, location_id)
    rows = db.exec(
        select(DiscoverableDetail)
        .where(DiscoverableDetail.location_id == location_id)
        .order_by(DiscoverableDetail.created_at, DiscoverableDetail.id)
    ).all()
    return [_detail_dict(d) for d in rows]


class DiscoverableDetailBody(BaseModel):
    world_id: str
    subject: str
    content: str
    access_level: str = "hidden"
    discovery_threshold: int = 0
    signpost_group: Optional[str] = None


@router.post("/locations/{location_id}/discoverable-details")
def create_discoverable_detail(
    location_id: str,
    body: DiscoverableDetailBody,
    db: DbSession = Depends(get_session),
) -> dict:
    """Seed a new discoverable detail on a location (creator direct write)."""
    _get_entity(db, location_id)
    if body.access_level not in ACCESS_LEVELS:
        raise HTTPException(422, f"access_level must be one of {ACCESS_LEVELS}")
    if not (0 <= body.discovery_threshold <= 12):
        raise HTTPException(422, "discovery_threshold must be between 0 and 12")
    detail = DiscoverableDetail(
        world_id=body.world_id,
        location_id=location_id,
        subject=body.subject,
        content=body.content,
        access_level=body.access_level,
        discovery_threshold=body.discovery_threshold,
        signpost_group=body.signpost_group,
    )
    db.add(detail)
    db.commit()
    db.refresh(detail)
    return _detail_dict(detail)


class DiscoverableDetailPatchBody(BaseModel):
    subject: Optional[str] = None
    content: Optional[str] = None
    access_level: Optional[str] = None
    discovery_threshold: Optional[int] = None
    discovered: Optional[bool] = None
    signpost_group: Optional[str] = None
    clear_signpost_group: bool = False  # explicit flag — signpost_group=None alone means "no change"


@router.put("/discoverable-details/{detail_id}")
def update_discoverable_detail(
    detail_id: str,
    body: DiscoverableDetailPatchBody,
    db: DbSession = Depends(get_session),
) -> dict:
    """Edit a discoverable detail (creator direct write).

    `discovered` is normally read-only (flipped by _apply_mutation on approve),
    but the creator can reset it to False to re-enable re-discovery.
    """
    detail = db.get(DiscoverableDetail, detail_id)
    if detail is None:
        raise HTTPException(404, f"DiscoverableDetail {detail_id!r} not found")
    if body.access_level is not None and body.access_level not in ACCESS_LEVELS:
        raise HTTPException(422, f"access_level must be one of {ACCESS_LEVELS}")
    if body.discovery_threshold is not None and not (0 <= body.discovery_threshold <= 12):
        raise HTTPException(422, "discovery_threshold must be between 0 and 12")
    if body.subject is not None:
        detail.subject = body.subject
    if body.content is not None:
        detail.content = body.content
    if body.access_level is not None:
        detail.access_level = body.access_level
    if body.discovery_threshold is not None:
        detail.discovery_threshold = body.discovery_threshold
    if body.discovered is not None:
        detail.discovered = body.discovered
    if body.clear_signpost_group:
        detail.signpost_group = None
    elif body.signpost_group is not None:
        detail.signpost_group = body.signpost_group
    detail.updated_at = datetime.now(UTC)
    db.add(detail)
    db.commit()
    db.refresh(detail)
    return _detail_dict(detail)


@router.delete("/discoverable-details/{detail_id}")
def delete_discoverable_detail(
    detail_id: str, db: DbSession = Depends(get_session)
) -> dict:
    """Delete a discoverable detail (creator direct write — hard delete)."""
    detail = db.get(DiscoverableDetail, detail_id)
    if detail is None:
        raise HTTPException(404, f"DiscoverableDetail {detail_id!r} not found")
    db.delete(detail)
    db.commit()
    return {"deleted": detail_id}


@router.get("/locations/graph")
def get_locations_graph(db: DbSession = Depends(get_session)) -> dict:
    """Active location nodes + connects_to edges — read-only, creator surface.

    nodes: all active location entities joined to their extension (for
    coord_x/coord_y). edges: connects_to relations whose both endpoints are
    in nodes (dangling edges from soft-deleted locations are filtered out
    server-side).
    """
    world_id = _world_id(db)

    rows = db.exec(
        select(Entity, Location)
        .join(Location, Location.id == Entity.id)
        .where(Entity.type == "location")
        .where(Entity.world_id == world_id)
        .where(Entity.status == "active")
        .order_by(Entity.name)
    ).all()

    active_ids = {e.id for e, _ in rows}
    nodes = [
        {"id": e.id, "name": e.name, "coord_x": loc.coord_x, "coord_y": loc.coord_y}
        for e, loc in rows
    ]

    rels = db.exec(
        select(Relation)
        .where(Relation.world_id == world_id)
        .where(Relation.type == "connects_to")
    ).all()
    edges = [
        {
            "id": r.id,
            "entity_a_id": r.entity_a_id,
            "entity_b_id": r.entity_b_id,
            "direction": r.direction,
        }
        for r in rels
        if r.entity_a_id in active_ids and r.entity_b_id in active_ids
    ]

    return {"nodes": nodes, "edges": edges}


@router.get("/locations")
def list_locations(db: DbSession = Depends(get_session)) -> list[dict]:
    """All locations (every status) with hierarchy fields — read-only, creator browse."""
    world_id = _world_id(db)
    rows = db.exec(
        select(Entity, Location)
        .join(Location, Location.id == Entity.id)
        .where(Entity.type == "location")
        .where(Entity.world_id == world_id)
        .order_by(Entity.name)
    ).all()
    return [
        {
            "id": e.id,
            "name": e.name,
            "parent_location_id": loc.parent_location_id,
            "location_type": loc.location_type,
            "status": e.status,
        }
        for e, loc in rows
    ]
