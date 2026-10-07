"""Quest routes (TICKET-0108, BRIEF-0108-B, contracts C-03 to C-05).

The creator's offers (E1) -- creator CRUD, a sanctioned canon-write path:
    GET  /api/quest-offers           every offer of the active world
    GET  /api/quest-offers/choices   what the editor's pickers list
    POST /api/quest-offers           create one offer
    PUT  /api/quest-offers/{id}      save one offer (steps replaced whole)

The player's quests (Journée):
    GET  /api/quests                     the offers he may accept, his quests
    POST /api/quests/accept              accept one offer (B1, A1)
    POST /api/quests/{quest_id}/abandon  abandon one quest (N1)

Every rule lives in `writes/quests.py` (what may be written) and
`quest_reads.py` (what is shown); this module parses, maps a refusal to its
status code, and commits. No response carries an agenda or step id.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session

from ... import quest_reads
from ...day_plan import PlanStep, RequirementSpec
from ...db import get_session
from ...models import Quest, QuestOffer
from ...writes import abandon_quest, accept_quest, write_quest_offer
from .. import crud as _crud
from .day import _resolve_player_character

router = APIRouter()


class RequirementBody(BaseModel):
    type: str
    target_entity_id: Optional[str] = None
    target_key: Optional[str] = None
    threshold: Optional[int] = None


class OfferStepBody(BaseModel):
    objective: str
    cost: int
    domain: Optional[str] = None
    requirements: list[RequirementBody] = Field(default_factory=list)


class OfferBody(BaseModel):
    giver_entity_id: str
    title: str
    summary: Optional[str] = None
    repeatable: bool = False
    status: str = "open"
    eligibility: list[RequirementBody] = Field(default_factory=list)
    steps: list[OfferStepBody] = Field(default_factory=list)


class AcceptBody(BaseModel):
    offer_id: str


def _spec(req: RequirementBody) -> RequirementSpec:
    return RequirementSpec(type=req.type, target_entity_id=req.target_entity_id or None,
                           target_key=req.target_key or None, threshold=req.threshold)


def _save_offer(body: OfferBody, offer: Optional[QuestOffer], world_id: str, db: Session) -> dict:
    steps = [PlanStep(objective=s.objective, cost=s.cost, domain=s.domain or None,
                      requirements=tuple(_spec(r) for r in s.requirements)) for s in body.steps]
    try:
        offer = write_quest_offer(
            db, world_id=world_id, offer=offer, giver_entity_id=body.giver_entity_id, title=body.title,
            summary=body.summary, repeatable=body.repeatable, status=body.status,
            eligibility=[_spec(r) for r in body.eligibility], steps=steps,
        )
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    db.commit()
    db.refresh(offer)
    return quest_reads.offer_dict(offer, db)


@router.get("/api/quest-offers")
def list_offers(db: Session = Depends(get_session)) -> list[dict]:
    world_id = _crud._world_id(db)
    return [quest_reads.offer_dict(o, db) for o in quest_reads.world_offers(world_id, db)]


@router.get("/api/quest-offers/choices")
def offer_choices(db: Session = Depends(get_session)) -> dict:
    return quest_reads.editor_choices(_crud._world_id(db), db)


@router.post("/api/quest-offers", status_code=201)
def create_offer(body: OfferBody, db: Session = Depends(get_session)) -> dict:
    return _save_offer(body, None, _crud._world_id(db), db)


@router.put("/api/quest-offers/{offer_id}")
def save_offer(offer_id: str, body: OfferBody, db: Session = Depends(get_session)) -> dict:
    world_id = _crud._world_id(db)
    offer = db.get(QuestOffer, offer_id)
    if offer is None or offer.world_id != world_id:
        raise HTTPException(status_code=404, detail=f"quest offer {offer_id!r} not found")
    return _save_offer(body, offer, world_id, db)


@router.get("/api/quests")
def journee_quests(db: Session = Depends(get_session)) -> dict:
    character = _resolve_player_character(_crud._world_id(db), db)
    return quest_reads.journee_payload(character, db)


@router.post("/api/quests/accept", status_code=201)
def accept(body: AcceptBody, db: Session = Depends(get_session)) -> dict:
    world_id = _crud._world_id(db)
    character = _resolve_player_character(world_id, db)
    offer = db.get(QuestOffer, body.offer_id)
    if offer is None or offer.world_id != world_id:
        raise HTTPException(status_code=404, detail=f"quest offer {body.offer_id!r} not found")
    try:
        accept_quest(db, offer=offer, character=character)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    db.commit()
    return quest_reads.journee_payload(character, db)


@router.post("/api/quests/{quest_id}/abandon")
def abandon(quest_id: str, db: Session = Depends(get_session)) -> dict:
    world_id = _crud._world_id(db)
    character = _resolve_player_character(world_id, db)
    quest = db.get(Quest, quest_id)
    if quest is None or quest.character_id != character.id:
        raise HTTPException(status_code=404, detail=f"quest {quest_id!r} not found")
    try:
        abandon_quest(db, quest=quest)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    db.commit()
    return quest_reads.journee_payload(character, db)
