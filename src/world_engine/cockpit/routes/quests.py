"""Quest routes (TICKET-0108, BRIEF-0108-B, contracts C-03 to C-05).

The creator's offers (E1) -- creator CRUD, a sanctioned canon-write path:
    GET  /api/quest-offers           every offer of the active world
    GET  /api/quest-offers/choices   what the editor's pickers list
    POST /api/quest-offers           create one offer
    PUT  /api/quest-offers/{id}      save one offer (steps replaced whole)
    POST /api/quest-offers/value     the indicative value of draft terms
    GET  /api/quest-economy          the world's rates (TICKET-0109, E1)
    PUT  /api/quest-economy          set them (None = the code's default)

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
from sqlmodel import Session, select

from ... import quest_reads
from ...day_plan import PlanStep, RequirementSpec
from ...db import get_session
from ...models import Quest, QuestEconomy, QuestOffer
from ...quest_value import DEFAULT_RATES, offer_value, value_dict, world_rates
from ...writes import TermSpec, abandon_quest, accept_quest, upsert_quest_economy, write_quest_offer
from ...writes.quest_terms import ECONOMY_COLUMNS
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


class TermBody(BaseModel):
    direction: str
    currency: str
    counterparty_entity_id: Optional[str] = None
    item_id: Optional[str] = None
    fact_id: Optional[str] = None
    skill_key: Optional[str] = None
    amount: Optional[int] = None
    level: Optional[str] = None


class OfferBody(BaseModel):
    giver_entity_id: str
    title: str
    summary: Optional[str] = None
    repeatable: bool = False
    status: str = "open"
    eligibility: list[RequirementBody] = Field(default_factory=list)
    steps: list[OfferStepBody] = Field(default_factory=list)
    # TICKET-0109 (B1): the offer's costs and rewards, replaced whole; absent
    # (None) keeps the stored ones.
    terms: Optional[list[TermBody]] = None


class ValueBody(BaseModel):
    terms: list[TermBody] = Field(default_factory=list)


class EconomyBody(BaseModel):
    rate_money: Optional[int] = None
    rate_relation: Optional[int] = None
    rate_fact: Optional[int] = None
    rate_skill: Optional[int] = None
    band_low_pct: Optional[int] = None
    band_high_pct: Optional[int] = None


def _term(term: TermBody) -> TermSpec:
    return TermSpec(**{name: (value if value != "" else None) for name, value in term.model_dump().items()})


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
            terms=None if body.terms is None else [_term(t) for t in body.terms],
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


@router.post("/api/quest-offers/value")
def preview_value(body: ValueBody, db: Session = Depends(get_session)) -> dict:
    """The editor's live total (C1): no validation, nothing written."""
    return value_dict(offer_value(db, _crud._world_id(db), [_term(t) for t in body.terms]))


@router.get("/api/quest-economy")
def get_economy(db: Session = Depends(get_session)) -> dict:
    world_id = _crud._world_id(db)
    row = db.exec(select(QuestEconomy).where(QuestEconomy.world_id == world_id)).first()
    stored = {name: getattr(row, name) if row is not None else None for name in ECONOMY_COLUMNS}
    return {"stored": stored, "effective": world_rates(db, world_id), "defaults": DEFAULT_RATES}


@router.put("/api/quest-economy")
def set_economy(body: EconomyBody, db: Session = Depends(get_session)) -> dict:
    try:
        upsert_quest_economy(db, world_id=_crud._world_id(db), values=body.model_dump())
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    db.commit()
    return get_economy(db=db)


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
