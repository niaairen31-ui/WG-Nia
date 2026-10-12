"""Author CRUD — the event journal (TICKET-0022; rewritten by TICKET-0114,
BRIEF-0114-C): no-delete-ever history rows.

An event is one happening of one of the world's event types: its title and
description, its place, its quantity when its type counts, its participants
by role (an entity or a sorte, each entity keeping it secret or not, X1),
and who learns it besides them (its fact's scopes, the type's by default,
W1). `POST /api/events` writes one, `PUT /api/events/{id}` corrects one --
its type stays and no participant is taken away -- both through
`writes.events`; every refusal is a 422. Since TICKET-0119 (BRIEF-0119-C,
M-c) a new event carries its `state_changes` -- what it changes in the
world, written with it, all or none; a correction carries none. `POST
/api/events/changes` is the shared event editor's read (BRIEF-0119-D): the
changes a type's effects pre-fill on given participants, each with its
French line, and the French of the changes a card already holds.

`_event_dict` is what the journal shows: the participants with their role
and their secret (read from their own knowledge row), the scopes with what
they name.
"""

from __future__ import annotations

from typing import Optional, Union

from fastapi import Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session as DbSession, select

from ...db import get_session
from ...event_changes import change_line, type_changes
from ...event_vocab import DOMAIN_LABELS_FR, type_view
from ...models import Entity, Event, EventParticipant, EventSorte, FactDefault, Knowledge
from ...writes.events import (
    EventScopeSpec,
    EventSpec,
    ParticipantSpec,
    StateChangeSpec,
    event_fact,
    write_event,
    write_event_update,
)

from ._router import router
from ._shared import EVENT_FIELDS, _iso, _world_id

CHANGED_BY = "creator_crud"


def _name(db: DbSession, entity_id: Optional[str]) -> Optional[str]:
    entity = db.get(Entity, entity_id) if entity_id else None
    return entity.name if entity is not None else None


def _participants(db: DbSession, event: Event, fact_id: Optional[str], roles: dict) -> list[dict]:
    rows = db.exec(select(EventParticipant).where(EventParticipant.event_id == event.id)
                   .order_by(EventParticipant.position, EventParticipant.id)).all()
    out = []
    for row in rows:
        secret = None
        if row.entity_id and fact_id:
            known = db.exec(select(Knowledge).where(Knowledge.entity_id == row.entity_id,
                                                    Knowledge.fact_id == fact_id)).first()
            secret = known.is_secret if known is not None else None
        sorte = db.get(EventSorte, row.sorte_id) if row.sorte_id else None
        out.append({"role_id": row.role_id, "role_name": roles.get(row.role_id), "entity_id": row.entity_id,
                    "sorte_id": row.sorte_id, "name": sorte.name if sorte else _name(db, row.entity_id),
                    "secret": secret})
    return out


def _event_dict(event: Event, db: DbSession) -> dict:
    view = type_view(db, event.type_id)
    fact = event_fact(db, event.id)
    scopes = db.exec(select(FactDefault).where(FactDefault.fact_id == fact.id)).all() if fact else []
    return {
        "id": event.id,
        "title": event.title,
        "description": event.description,
        "type_id": event.type_id,
        "type_name": view.name if view else None,
        "type_label": f"{view.name} ({DOMAIN_LABELS_FR[view.domain]})" if view else None,
        "quantity": event.quantity,
        "location_id": event.location_id,
        "location_name": _name(db, event.location_id),
        "participants": _participants(db, event, fact.id if fact else None,
                                      {r.id: r.name for r in view.roles} if view else {}),
        "scopes": [{"scope_type": s.scope_type, "scope_id": s.scope_id, "scope_name": _name(db, s.scope_id),
                    "level": s.level} for s in scopes],
        "fact_id": fact.id if fact else None,
        "session_id": event.session_id,
        "batch_id": event.batch_id,
        "recorded_at": _iso(event.recorded_at),
    }


class ParticipantBody(BaseModel):
    role_id: str
    entity_id: Optional[str] = None
    sorte_id: Optional[str] = None
    secret: Optional[bool] = None


class EventScopeBody(BaseModel):
    scope_type: str
    scope_id: Optional[str] = None
    level: str = "knows"


class StateChangeBody(BaseModel):
    """One change of a new event (M-c): `value` a choice key, an integer,
    an entity id, or None."""
    entity_id: str
    attribute: str
    mode: str = "set"
    value: Optional[Union[int, str]] = None


class EventBody(BaseModel):
    title: str
    description: Optional[str] = None
    type_id: str
    location_id: Optional[str] = None
    quantity: Optional[int] = None
    participants: list[ParticipantBody] = Field(default_factory=list)
    # None: the type's scopes (W1); a list, even empty: exactly these.
    scopes: Optional[list[EventScopeBody]] = None
    state_changes: list[StateChangeBody] = Field(default_factory=list)


class ChangesBody(BaseModel):
    """The editor's question: a type and its participants (role id, entity
    id), and the changes it already holds."""
    type_id: Optional[str] = None
    participants: list[ParticipantBody] = Field(default_factory=list)
    changes: list[StateChangeBody] = Field(default_factory=list)


def event_spec(body: EventBody) -> EventSpec:
    return EventSpec(
        type_id=body.type_id, title=body.title, description=body.description, location_id=body.location_id,
        quantity=body.quantity,
        participants=tuple(ParticipantSpec(p.role_id, p.entity_id, p.sorte_id, p.secret) for p in body.participants),
        scopes=None if body.scopes is None else tuple(EventScopeSpec(s.scope_type, s.scope_id, s.level)
                                                       for s in body.scopes),
        changes=tuple(StateChangeSpec(c.entity_id, c.attribute, c.value, c.mode) for c in body.state_changes),
    )


def _event(db: DbSession, event_id: str) -> Event:
    event = db.get(Event, event_id)
    if event is None or event.world_id != _world_id(db):
        raise HTTPException(404, f"Event {event_id!r} not found")
    return event


@router.get("/events")
def list_events(db: DbSession = Depends(get_session)) -> list[dict]:
    world_id = _world_id(db)
    events = db.exec(
        select(Event).where(Event.world_id == world_id).order_by(Event.recorded_at.desc())
    ).all()
    return [_event_dict(e, db) for e in events]


@router.get("/events/{event_id}")
def get_event(event_id: str, db: DbSession = Depends(get_session)) -> dict:
    return _event_dict(_event(db, event_id), db)


@router.post("/events/changes")
def event_changes(body: ChangesBody, db: DbSession = Depends(get_session)) -> dict:
    """`prefilled`: the changes the type's effects make on the participants
    (none without a type); `described`: the changes given, each with its
    French `line` (None when it names nothing of this world). Reads only."""
    world_id = _world_id(db)
    view = type_view(db, body.type_id) if body.type_id else None
    if view is not None and view.world_id != world_id:
        raise HTTPException(404, f"Event type {body.type_id!r} not found")
    prefilled = type_changes(db, world_id, view, [(p.role_id, p.entity_id) for p in body.participants])
    given = [c.model_dump() for c in body.changes]
    return {"prefilled": [dict(c, line=change_line(db, world_id, c)) for c in prefilled],
            "described": [dict(c, line=change_line(db, world_id, c)) for c in given]}


@router.post("/events", status_code=201)
def create_event(body: EventBody, db: DbSession = Depends(get_session)) -> dict:
    try:
        event = write_event(db, world_id=_world_id(db), spec=event_spec(body), created_by=CHANGED_BY)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(422, str(exc)) from exc
    db.commit()
    db.refresh(event)
    return _event_dict(event, db)


@router.put("/events/{event_id}")
def update_event(event_id: str, body: EventBody, db: DbSession = Depends(get_session)) -> dict:
    event = _event(db, event_id)
    try:
        write_event_update(db, event=event, spec=event_spec(body), changed_by=CHANGED_BY)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(422, str(exc)) from exc
    db.commit()
    db.refresh(event)
    return _event_dict(event, db)


__all__ = ["EVENT_FIELDS", "EventBody", "_event_dict", "create_event", "event_changes", "get_event", "list_events",
           "update_event"]
