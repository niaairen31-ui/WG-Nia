"""Author CRUD — descriptive facts of an entity (TICKET-0091, BRIEF-0091-E,
contract C-12).

The sheet lists, adds, edits and removes the descriptive facts of an entity
here. Every write goes through `writes/facets.py` (C-05) — never a `db.add`
of this module's own — and each route commits once. A `ValueError` from the
writer is a 422; an unknown entity or fact is a 404.
"""

from __future__ import annotations

from typing import Optional

from fastapi import Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session as DbSession, select

from ...db import get_session
from ...facets import DESCRIPTIVE_FACETS, FACETS
from ...models import Fact, FactDefault, FactParticipant
from ...writes import ScopeChoice, add_entity_fact, edit_entity_fact, remove_entity_fact

from ._router import router
from ._shared import _get_entity, _iso

CREATED_BY = "creator_crud"


class FactScopeBody(BaseModel):
    scope_type: str
    scope_id: Optional[str] = None


class EntityFactCreateBody(BaseModel):
    facet: str
    content: str
    aspect: Optional[str] = None
    scope: Optional[FactScopeBody] = None


class FactContentBody(BaseModel):
    content: str


def _fact_dict(fact: Fact, db: DbSession) -> dict:
    defaults = db.exec(
        select(FactDefault).where(FactDefault.fact_id == fact.id).order_by(FactDefault.created_at)
    ).all()
    return {
        "fact_id": fact.id,
        "facet": fact.facet,
        "aspect": fact.aspect,
        "content": fact.content,
        "scopes": [
            {"scope_type": d.scope_type, "scope_id": d.scope_id, "level": d.level} for d in defaults
        ],
        "created_at": _iso(fact.created_at),
    }


def _get_fact(db: DbSession, fact_id: str) -> Fact:
    fact = db.get(Fact, fact_id)
    if fact is None:
        raise HTTPException(status_code=404, detail=f"Fact {fact_id!r} not found")
    return fact


@router.get("/facets")
def list_facets() -> dict:
    """The descriptive facet vocabulary, registry order."""
    return {"facets": [
        {
            "name": spec.name, "label": spec.label, "family": spec.family,
            "granularity": spec.granularity, "preset": spec.preset,
            "aspects": list(spec.aspects),
        }
        for spec in FACETS.values() if spec.name in DESCRIPTIVE_FACETS
    ]}


@router.get("/entities/{entity_id}/facts")
def list_entity_facts(entity_id: str, db: DbSession = Depends(get_session)) -> dict:
    """The descriptive facts whose participant is `entity_id`, oldest first."""
    _get_entity(db, entity_id)
    facts = db.exec(
        select(Fact)
        .join(FactParticipant, FactParticipant.fact_id == Fact.id)
        .where(FactParticipant.entity_id == entity_id, Fact.facet.in_(DESCRIPTIVE_FACETS))
        .order_by(Fact.created_at, Fact.id)
    ).all()
    return {"entity_id": entity_id, "facts": [_fact_dict(f, db) for f in facts]}


@router.post("/entities/{entity_id}/facts", status_code=201)
def create_entity_fact(
    entity_id: str, body: EntityFactCreateBody, db: DbSession = Depends(get_session)
) -> dict:
    _get_entity(db, entity_id)
    scope = ScopeChoice(body.scope.scope_type, body.scope.scope_id) if body.scope else None
    try:
        fact = add_entity_fact(
            db, entity_id=entity_id, facet=body.facet, content=body.content,
            created_by=CREATED_BY, aspect=body.aspect, scope=scope,
        )
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc))
    db.commit()
    db.refresh(fact)
    return _fact_dict(fact, db)


@router.put("/facts/{fact_id}/content")
def update_entity_fact_content(
    fact_id: str, body: FactContentBody, db: DbSession = Depends(get_session)
) -> dict:
    _get_fact(db, fact_id)
    try:
        fact = edit_entity_fact(db, fact_id=fact_id, content=body.content, changed_by=CREATED_BY)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc))
    db.commit()
    db.refresh(fact)
    return _fact_dict(fact, db)


@router.delete("/facts/{fact_id}")
def delete_entity_fact(fact_id: str, db: DbSession = Depends(get_session)) -> dict:
    _get_fact(db, fact_id)
    try:
        remove_entity_fact(db, fact_id=fact_id)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc))
    db.commit()
    return {"ok": True}
