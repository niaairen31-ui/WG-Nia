"""The state of the world's routes (TICKET-0113, BRIEF-0113-C; decisions
WA3, WB2, WD1, WI1, WJ2 and WK2 of the conditions series) -- creator CRUD, a
sanctioned canon-write path:

    GET  /api/attributes                     every attribute of the active
                                             world (system ones first, the
                                             retired included) and the types
                                             a definition may name
    POST /api/attributes                     define one
    PUT  /api/attributes/{id}                save one
    POST /api/attributes/{id}/status         retire or restore one
    GET  /api/entities/{id}/states           what the entity's sheet shows
    PUT  /api/entities/{id}/states/{key}     set its value, `correction` or
                                             `changement` (WD1)

A name near another attribute's (`attributes.near_attributes`) is not
written until the creator confirms it (`confirm_near`): the answer is
`{"saved": false, "near": [...]}` and she picks the existing one or creates
anyway -- never a duplicate « Maudit » / « maudite » unseen (WK2). A system
attribute is never written here: its field on the sheet keeps it.

Every rule lives in `writes/attributes.py`; what is shown, in
`attributes.py`. This module parses, maps a refusal to 422, and commits once.
"""

from __future__ import annotations

from typing import Optional, Union

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from ...attributes import (
    ATTRIBUTE_FORM,
    AttributeView,
    attribute_view,
    entity_states,
    near_attributes,
    system_attribute,
    world_attributes,
    world_entity_type_labels,
)
from ...db import get_session
from ...models import AttributeDefinition, ConditionNode, Entity
from ...writes.attributes import (
    ChoiceSpec,
    DefinitionSpec,
    set_attribute_status,
    write_attribute_definition,
    write_attribute_value,
)
from .. import crud as _crud

router = APIRouter()

CHANGED_BY = "creator_crud"
SYSTEM_READ_ONLY = "Un état système se modifie dans les champs de la fiche."


class ChoiceBody(BaseModel):
    label: str
    id: Optional[str] = None


class DefinitionBody(BaseModel):
    name: str
    kind: str
    holder_types: list[str] = Field(default_factory=list)
    value_types: list[str] = Field(default_factory=list)
    choices: list[ChoiceBody] = Field(default_factory=list)
    default: Union[int, str, None] = None
    is_hidden: bool = False
    confirm_near: bool = False


class StatusBody(BaseModel):
    status: str


class ValueBody(BaseModel):
    value: Union[int, str, None] = None
    kind: str


def definition_spec(body: DefinitionBody) -> DefinitionSpec:
    """The writer's spec of a request body (shared with BRIEF-0113-E's
    offer save)."""
    return DefinitionSpec(
        name=body.name, kind=body.kind, holder_types=tuple(body.holder_types),
        value_types=tuple(body.value_types), choices=tuple(ChoiceSpec(c.label, c.id) for c in body.choices),
        default=body.default, is_hidden=body.is_hidden,
    )


def _in_use(db: Session, key: str) -> bool:
    return db.exec(select(ConditionNode.id).where(
        ConditionNode.form == ATTRIBUTE_FORM, ConditionNode.target_key == key)).first() is not None


def attribute_dict(db: Session, view: AttributeView) -> dict:
    return {
        "key": view.key, "name": view.name, "kind": view.kind, "system": view.system, "hidden": view.hidden,
        "status": view.status,
        "holder_types": list(view.holder_types) if view.holder_types is not None else None,
        "value_types": list(view.value_types),
        "choices": [{"value": key, "label": label} for key, label in view.choices],
        "default": view.default, "in_condition": _in_use(db, view.key),
    }


def _near(db: Session, world_id: str, name: str, exclude: Optional[str]) -> list[dict]:
    return [{"key": n.key, "name": n.name, "system": n.system, "score": n.score}
            for n in near_attributes(db, world_id, name, exclude_key=exclude)]


@router.get("/api/attributes")
def list_attributes(db: Session = Depends(get_session)) -> dict:
    world_id = _crud._world_id(db)
    return {
        "attributes": [attribute_dict(db, v) for v in world_attributes(db, world_id, include_retired=True)],
        "entity_types": world_entity_type_labels(db, world_id),
    }


def _save(body: DefinitionBody, definition_id: Optional[str], db: Session) -> dict:
    world_id = _crud._world_id(db)
    if not body.confirm_near:
        near = _near(db, world_id, body.name, definition_id)
        renamed = definition_id is None or db.get(AttributeDefinition, definition_id).name != body.name
        if near and renamed:
            return {"saved": False, "near": near}
    try:
        definition = write_attribute_definition(db, world_id=world_id, spec=definition_spec(body),
                                                definition_id=definition_id)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    db.commit()
    return {"saved": True, "attribute": attribute_dict(db, attribute_view(db, world_id, definition.id))}


@router.post("/api/attributes")
def create_attribute(body: DefinitionBody, db: Session = Depends(get_session)) -> dict:
    return _save(body, None, db)


@router.put("/api/attributes/{definition_id}")
def save_attribute(definition_id: str, body: DefinitionBody, db: Session = Depends(get_session)) -> dict:
    definition = db.get(AttributeDefinition, definition_id)
    if definition is None or definition.world_id != _crud._world_id(db):
        raise HTTPException(status_code=404, detail=f"attribute {definition_id!r} not found")
    return _save(body, definition_id, db)


@router.post("/api/attributes/{definition_id}/status")
def attribute_status(definition_id: str, body: StatusBody, db: Session = Depends(get_session)) -> dict:
    world_id = _crud._world_id(db)
    try:
        set_attribute_status(db, world_id=world_id, definition_id=definition_id, status=body.status)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    db.commit()
    return attribute_dict(db, attribute_view(db, world_id, definition_id))


def _entity(db: Session, entity_id: str) -> Entity:
    entity = db.get(Entity, entity_id)
    if entity is None or entity.world_id != _crud._world_id(db):
        raise HTTPException(status_code=404, detail=f"entity {entity_id!r} not found")
    return entity


@router.get("/api/entities/{entity_id}/states")
def get_states(entity_id: str, db: Session = Depends(get_session)) -> list[dict]:
    entity = _entity(db, entity_id)
    return entity_states(db, entity.world_id, entity)


@router.put("/api/entities/{entity_id}/states/{key}")
def set_state(entity_id: str, key: str, body: ValueBody, db: Session = Depends(get_session)) -> list[dict]:
    entity = _entity(db, entity_id)
    if system_attribute(key) is not None:
        raise HTTPException(status_code=422, detail=SYSTEM_READ_ONLY)
    try:
        write_attribute_value(db, world_id=entity.world_id, definition_id=key, entity_id=entity.id,
                              value=body.value, kind=body.kind, changed_by=CHANGED_BY)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    db.commit()
    return entity_states(db, entity.world_id, entity)
