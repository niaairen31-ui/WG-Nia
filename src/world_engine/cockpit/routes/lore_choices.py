"""Model-choice review routes (TICKET-0095, K1, C-07).

Nia agrees or disagrees with one H2 choice; every write goes through the
creator path (B1): `writes/facets.record_appellation` for an optional
appellation, `writes.write_day_mention_review` for the verdict, one commit
per request. One review per choice (J1); the past day, its rewrite and its
resolutions are never touched. Reads live in `lore_choices_read.py`.
Isolated from the consultation pipeline (`lore_isolation.py` R17). Guarded
exactly as the names panel (no route authentication).
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session

from ... import lore_choices_read as _read
from ...db import get_session
from ...lore_mentions_read import active_world_id
from ...lore_resolve import validate_binding
from ...writes import write_day_mention_review
from ...writes.facets import record_appellation

router = APIRouter()

_CHANGED_BY = "creator_crud"


class ChoiceReviewBody(BaseModel):
    verdict: str
    entity_id: Optional[str] = None
    record_appellation: bool = False
    scope_type: str = "rencontre"


def _world_id(db: Session) -> str:
    world_id = active_world_id(db)
    if world_id is None:
        raise HTTPException(status_code=400, detail="No active world. Activate a world before proceeding.")
    return world_id


def _effective_entity(db: Session, choice, body: ChoiceReviewBody, world_id: str) -> Optional[str]:
    """C-07 steps 4-7: the entity the review names, or a 422."""
    if body.verdict not in ("agreed", "disagreed"):
        raise HTTPException(status_code=422, detail="verdict must be 'agreed' or 'disagreed'")
    if body.verdict == "agreed":
        if body.entity_id is not None and body.entity_id != choice.chosen_entity_id:
            raise HTTPException(status_code=422,
                                detail="agreed: entity_id must be omitted or equal the model's choice")
        effective = choice.chosen_entity_id
    else:
        if body.entity_id is None and body.record_appellation:
            raise HTTPException(status_code=422,
                                detail="disagreed without an entity cannot record an appellation")
        if body.entity_id == choice.chosen_entity_id:
            raise HTTPException(status_code=422, detail="disagreed: entity_id equals the model's choice")
        effective = body.entity_id
    if effective is not None and not validate_binding(effective, choice.category, world_id, db):
        raise HTTPException(status_code=422,
                            detail="entity_id is not an active entity of this category in the world")
    return effective


@router.get("/api/lore/choices")
def list_choices(db: Session = Depends(get_session)) -> dict:
    return {"choices": _read.list_pending_choices(db, _world_id(db))}


@router.post("/api/lore/choices/{choice_id}/review")
def review_choice_route(choice_id: str, body: ChoiceReviewBody, db: Session = Depends(get_session)) -> dict:
    world_id = _world_id(db)
    choice = _read.reviewable_choice(db, choice_id, world_id)
    if choice is None:
        raise HTTPException(status_code=404, detail=f"reviewable choice {choice_id!r} not found")
    if _read.is_reviewed(db, choice_id):
        raise HTTPException(status_code=409, detail=f"choice {choice_id!r} is already reviewed")
    effective = _effective_entity(db, choice, body, world_id)
    try:
        fact = None
        if body.record_appellation:
            fact = record_appellation(db, entity_id=effective, surface=choice.surface_form,
                                      scope_type=body.scope_type, created_by=_CHANGED_BY)
        write_day_mention_review(
            db, world_id=world_id, choice_id=choice.id, verdict=body.verdict, entity_id=effective,
            appellation_fact_id=fact.id if fact else None,
            appellation_scope=body.scope_type if fact else None,
        )
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    db.commit()
    return {"ok": True, "id": choice_id, "appellation_written": fact is not None}
