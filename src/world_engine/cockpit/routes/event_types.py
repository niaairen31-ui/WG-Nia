"""The event journal's vocabulary routes (TICKET-0114, BRIEF-0114-B;
decisions B1, C1, D1, T3 and W1 of the conditions series) -- creator CRUD, a
sanctioned canon-write path:

    GET  /api/event-vocabulary            the active world's event types
                                          (the retired included), its sortes,
                                          and what a type may name: entity
                                          types, domains, scope kinds, levels
    POST /api/event-types                 define one type
    PUT  /api/event-types/{id}            save one
    POST /api/event-types/{id}/status     retire or restore one
    POST /api/event-sortes                add one sorte
    PUT  /api/event-sortes/{id}           rename one
    POST /api/event-sortes/{id}/status    retire or restore one

A name near another type's or sorte's (`event_vocab.near_event_types`,
`near_sortes`) is not written until the creator confirms it
(`confirm_near`): the answer is `{"saved": false, "near": [...]}` and she
opens the existing one or creates anyway -- never « Tuer » twice unseen
(the WK2 rule of TICKET-0113).

Every rule lives in `writes/event_types.py`; what is shown, in
`event_vocab.py`. This module parses, maps a refusal to 422, and commits once.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session, func, select

from ...attributes import world_entity_type_labels
from ...db import get_session
from ...event_vocab import (
    DOMAIN_LABELS_FR,
    EVENT_FORM,
    EventTypeView,
    near_event_types,
    near_sortes,
    type_view,
    world_event_types,
    world_sortes,
)
from ...models import EVENT_DOMAINS, EVENT_SCOPE_KINDS, ConditionNode, Event, EventSorte, EventType
from ...writes.event_types import (
    EventTypeSpec,
    RoleSpec,
    ScopeSpec,
    set_event_type_status,
    set_sorte_status,
    write_event_type,
    write_sorte,
)
from .. import crud as _crud

router = APIRouter()

# W1: the scope kinds and the levels a scope may give, in French, in order.
SCOPE_LABELS_FR: dict[str, str] = {
    "location": "ceux qui passent au lieu de l'événement", "world": "tout le monde",
    "rencontre": "ceux qui ont rencontré", "faction": "les membres de la faction",
}
LEVEL_LABELS_FR: dict[str, str] = {
    "rumor": "une rumeur", "suspicious": "un soupçon", "partial": "en partie", "knows": "le savent",
    "fully_understands": "le comprennent pleinement",
}


class RoleBody(BaseModel):
    name: str
    entity_types: list[str] = Field(default_factory=list)
    accepts_sorte: bool = False
    id: Optional[str] = None


class ScopeBody(BaseModel):
    kind: str
    role: Optional[str] = None
    level: str = "knows"


class EventTypeBody(BaseModel):
    name: str
    domain: str = "other"
    roles: list[RoleBody] = Field(default_factory=list)
    counts_quantity: bool = False
    in_chronicle: bool = True
    participants_secret: bool = False
    scopes: list[ScopeBody] = Field(default_factory=list)
    confirm_near: bool = False


class SorteBody(BaseModel):
    name: str
    confirm_near: bool = False


class StatusBody(BaseModel):
    status: str


def event_type_spec(body: EventTypeBody) -> EventTypeSpec:
    """The writer's spec of a request body (shared with the interpreter's
    and the analyzer's proposals, BRIEF-0114-G/H)."""
    return EventTypeSpec(
        name=body.name, domain=body.domain,
        roles=tuple(RoleSpec(r.name, tuple(r.entity_types), r.accepts_sorte, r.id) for r in body.roles),
        counts_quantity=body.counts_quantity, in_chronicle=body.in_chronicle,
        participants_secret=body.participants_secret,
        scopes=tuple(ScopeSpec(s.kind, s.role, s.level) for s in body.scopes),
    )


def _in_condition(db: Session, type_id: str) -> bool:
    return db.exec(select(ConditionNode.id).where(
        ConditionNode.form == EVENT_FORM, ConditionNode.target_key == type_id)).first() is not None


def type_dict(db: Session, view: EventTypeView) -> dict:
    """One type as the « Vocabulaire du monde » tab and the journal show it."""
    names = {r.id: r.name for r in view.roles}
    events = db.exec(select(func.count()).select_from(Event).where(Event.type_id == view.id)).one()
    return {
        "id": view.id, "name": view.name, "domain": view.domain, "domain_label": DOMAIN_LABELS_FR[view.domain],
        "counts_quantity": view.counts_quantity, "in_chronicle": view.in_chronicle,
        "participants_secret": view.participants_secret, "status": view.status,
        "roles": [{"id": r.id, "name": r.name, "entity_types": list(r.entity_types),
                   "accepts_sorte": r.accepts_sorte, "status": r.status} for r in view.roles],
        "scopes": [{"kind": s.kind, "role": names.get(s.role_id), "level": s.level} for s in view.scopes],
        "in_condition": _in_condition(db, view.id), "events": events,
    }


def sorte_dict(sorte: EventSorte) -> dict:
    return {"id": sorte.id, "name": sorte.name, "status": sorte.status}


def _near(found) -> list[dict]:
    return [{"id": n.id, "name": n.name, "score": n.score} for n in found]


@router.get("/api/event-vocabulary")
def event_vocabulary(db: Session = Depends(get_session)) -> dict:
    world_id = _crud._world_id(db)
    return {
        "types": [type_dict(db, v) for v in world_event_types(db, world_id, include_retired=True)],
        "sortes": [sorte_dict(s) for s in world_sortes(db, world_id, include_retired=True)],
        "entity_types": world_entity_type_labels(db, world_id),
        "domains": [{"value": d, "label": DOMAIN_LABELS_FR[d]} for d in EVENT_DOMAINS],
        "scope_kinds": [{"value": k, "label": SCOPE_LABELS_FR[k]} for k in EVENT_SCOPE_KINDS],
        "levels": [{"value": v, "label": label} for v, label in LEVEL_LABELS_FR.items()],
    }


def _save_type(body: EventTypeBody, type_id: Optional[str], db: Session) -> dict:
    world_id = _crud._world_id(db)
    if not body.confirm_near:
        near = _near(near_event_types(db, world_id, body.name, exclude_id=type_id))
        renamed = type_id is None or db.get(EventType, type_id).name != body.name
        if near and renamed:
            return {"saved": False, "near": near}
    try:
        row = write_event_type(db, world_id=world_id, spec=event_type_spec(body), type_id=type_id)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    db.commit()
    return {"saved": True, "type": type_dict(db, type_view(db, row.id))}


def _type(db: Session, type_id: str) -> EventType:
    row = db.get(EventType, type_id)
    if row is None or row.world_id != _crud._world_id(db):
        raise HTTPException(status_code=404, detail=f"event type {type_id!r} not found")
    return row


@router.post("/api/event-types")
def create_event_type(body: EventTypeBody, db: Session = Depends(get_session)) -> dict:
    return _save_type(body, None, db)


@router.put("/api/event-types/{type_id}")
def save_event_type(type_id: str, body: EventTypeBody, db: Session = Depends(get_session)) -> dict:
    _type(db, type_id)
    return _save_type(body, type_id, db)


@router.post("/api/event-types/{type_id}/status")
def event_type_status(type_id: str, body: StatusBody, db: Session = Depends(get_session)) -> dict:
    row = _type(db, type_id)
    try:
        set_event_type_status(db, world_id=row.world_id, type_id=type_id, status=body.status)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    db.commit()
    return type_dict(db, type_view(db, type_id))


def _save_sorte(body: SorteBody, sorte_id: Optional[str], db: Session) -> dict:
    world_id = _crud._world_id(db)
    if not body.confirm_near:
        near = _near(near_sortes(db, world_id, body.name, exclude_id=sorte_id))
        renamed = sorte_id is None or db.get(EventSorte, sorte_id).name != body.name
        if near and renamed:
            return {"saved": False, "near": near}
    try:
        row = write_sorte(db, world_id=world_id, name=body.name, sorte_id=sorte_id)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    db.commit()
    return {"saved": True, "sorte": sorte_dict(row)}


def _sorte(db: Session, sorte_id: str) -> EventSorte:
    row = db.get(EventSorte, sorte_id)
    if row is None or row.world_id != _crud._world_id(db):
        raise HTTPException(status_code=404, detail=f"sorte {sorte_id!r} not found")
    return row


@router.post("/api/event-sortes")
def create_sorte(body: SorteBody, db: Session = Depends(get_session)) -> dict:
    return _save_sorte(body, None, db)


@router.put("/api/event-sortes/{sorte_id}")
def save_sorte(sorte_id: str, body: SorteBody, db: Session = Depends(get_session)) -> dict:
    _sorte(db, sorte_id)
    return _save_sorte(body, sorte_id, db)


@router.post("/api/event-sortes/{sorte_id}/status")
def sorte_status(sorte_id: str, body: StatusBody, db: Session = Depends(get_session)) -> dict:
    row = _sorte(db, sorte_id)
    try:
        set_sorte_status(db, world_id=row.world_id, sorte_id=sorte_id, status=body.status)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    db.commit()
    return sorte_dict(db.get(EventSorte, sorte_id))
