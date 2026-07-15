"""Author CRUD — events (TICKET-0022): no-delete-ever history rows.

Split out of `cockpit/crud.py` (TICKET-0027, BRIEF-0027-d) — pure move,
no logic change.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Optional

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
from ._shared import (
    EVENT_FIELDS,
    EVENT_KNOWLEDGE_STATUSES,
    EVENT_TYPE_LABELS_FR,
    _iso,
    _world_id,
)


def _event_dict(event: Event, db: DbSession) -> dict:
    location = db.get(Entity, event.location_id) if event.location_id else None
    involved = []
    links = db.exec(select(EventEntity).where(EventEntity.event_id == event.id)).all()
    for link in links:
        target = db.get(Entity, link.entity_id)
        involved.append({"id": link.entity_id, "name": target.name if target is not None else None})
    return {
        "id": event.id,
        "title": event.title,
        "description": event.description,
        "type": event.type,
        "type_label": EVENT_TYPE_LABELS_FR.get(event.type, event.type),
        "knowledge_status": event.knowledge_status,
        "location_id": event.location_id,
        "location_name": location.name if location is not None else None,
        "involved_entities": involved,
        "recorded_at": _iso(event.recorded_at),
    }


def _validate_event_location(db: DbSession, world_id: str, location_id: Optional[str]) -> Optional[str]:
    """Reuses the exact predicate at app.py:1575-1583 (event_creation branch)
    — active `location` entity in the active world. 422 on anything else:
    the creator's picker cannot produce a bad id, so a bad id is a bug, not
    a typo."""
    if not location_id:
        return None
    target = db.get(Entity, location_id)
    if (
        target is None
        or target.type != "location"
        or target.status != "active"
        or target.world_id != world_id
    ):
        raise HTTPException(422, f"location_id {location_id!r} is not an active location in this world")
    return location_id


def _validate_event_involved(db: DbSession, world_id: str, ids: Optional[list]) -> Optional[list]:
    if not ids:
        return None
    out = []
    for entity_id in ids:
        target = db.get(Entity, entity_id)
        if target is None or target.world_id != world_id:
            raise HTTPException(422, f"involved_entities: {entity_id!r} is not a valid entity id in this world")
        out.append(entity_id)
    return out


class EventCreateBody(BaseModel):
    title: str
    description: Optional[str] = None
    type: Optional[str] = None
    knowledge_status: str = "secret"
    location_id: Optional[str] = None
    involved_entities: Optional[list[str]] = None


class EventUpdateBody(BaseModel):
    title: str
    description: Optional[str] = None
    type: Optional[str] = None
    knowledge_status: str
    location_id: Optional[str] = None
    involved_entities: Optional[list[str]] = None


@router.get("/events")
def list_events(db: DbSession = Depends(get_session)) -> list[dict]:
    world_id = _world_id(db)
    events = db.exec(
        select(Event).where(Event.world_id == world_id).order_by(Event.recorded_at.desc())
    ).all()
    return [_event_dict(e, db) for e in events]


@router.get("/events/{event_id}")
def get_event(event_id: str, db: DbSession = Depends(get_session)) -> dict:
    event = db.get(Event, event_id)
    if event is None or event.world_id != _world_id(db):
        raise HTTPException(404, f"Event {event_id!r} not found")
    return _event_dict(event, db)


@router.post("/events", status_code=201)
def create_event(body: EventCreateBody, db: DbSession = Depends(get_session)) -> dict:
    world_id = _world_id(db)
    if not body.title or not body.title.strip():
        raise HTTPException(422, "title is required")
    if body.knowledge_status not in EVENT_KNOWLEDGE_STATUSES:
        raise HTTPException(422, f"knowledge_status must be one of {EVENT_KNOWLEDGE_STATUSES}")
    location_id = _validate_event_location(db, world_id, body.location_id)
    involved = _validate_event_involved(db, world_id, body.involved_entities)

    event = write_event(
        db,
        world_id=world_id,
        title=body.title.strip(),
        description=body.description,
        type=body.type,
        knowledge_status=body.knowledge_status,
        involved_entities=involved,
        location_id=location_id,
    )
    db.commit()
    db.refresh(event)
    return _event_dict(event, db)


@router.put("/events/{event_id}")
def update_event(event_id: str, body: EventUpdateBody, db: DbSession = Depends(get_session)) -> dict:
    event = db.get(Event, event_id)
    if event is None or event.world_id != _world_id(db):
        raise HTTPException(404, f"Event {event_id!r} not found")
    world_id = _world_id(db)
    if not body.title or not body.title.strip():
        raise HTTPException(422, "title is required")
    if body.knowledge_status not in EVENT_KNOWLEDGE_STATUSES:
        raise HTTPException(422, f"knowledge_status must be one of {EVENT_KNOWLEDGE_STATUSES}")
    location_id = _validate_event_location(db, world_id, body.location_id)
    involved = _validate_event_involved(db, world_id, body.involved_entities)

    event = write_event_update(
        db,
        event=event,
        title=body.title.strip(),
        description=body.description,
        type=body.type,
        knowledge_status=body.knowledge_status,
        involved_entities=involved,
        location_id=location_id,
    )
    db.commit()
    db.refresh(event)
    return _event_dict(event, db)
