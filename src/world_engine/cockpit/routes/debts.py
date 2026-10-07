"""Debt routes (TICKET-0110, BRIEF-0110-B, contract C-07).

The creator's ledger of debts (Création › Dettes) -- creator CRUD, a
sanctioned canon-write path:
    GET  /api/debts                 every debt of the active world
    POST /api/debts                 write one by hand (origin `creator`)
    POST /api/debts/{id}/repay      the debtor repays it, all at once (D1)
    POST /api/debts/{id}/forgive    the creditor lets it go, with a note

The player's side (Journée):
    GET  /api/journee/debts         what he owes and what is owed to him
    POST /api/services              ask a character a service (S2)

Every rule lives in `writes/debts.py` and `writes/debt_sources.py`; what is
shown, in `debt_reads.py`. This module parses, maps a refusal to its status
code (422 a request that cannot be written, 409 a debt that cannot be
repaid or forgiven now), and commits.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session

from ... import debt_reads
from ...db import get_session
from ...models import Debt
from ...writes import DebtTermSpec, create_debt, forgive_debt, request_service, settle_debt
from .. import crud as _crud
from .day import _resolve_player_character
from .quests import TermBody, _term

router = APIRouter()


class DebtTermBody(BaseModel):
    currency: str
    item_id: Optional[str] = None
    fact_id: Optional[str] = None
    skill_key: Optional[str] = None
    amount: Optional[int] = None


class DebtBody(BaseModel):
    debtor_entity_id: str
    creditor_entity_id: str
    contact_entity_id: Optional[str] = None
    reason: Optional[str] = None
    is_secret: bool = False
    terms: list[DebtTermBody] = Field(default_factory=list)


class ForgiveBody(BaseModel):
    note: Optional[str] = None


class ServiceBody(BaseModel):
    provider_entity_id: str
    on_behalf_of_id: Optional[str] = None
    terms: list[TermBody] = Field(default_factory=list)
    owed: list[DebtTermBody] = Field(default_factory=list)
    reason: Optional[str] = None
    is_secret: bool = False


def _owed(terms: list[DebtTermBody]) -> list[DebtTermSpec]:
    return [DebtTermSpec(**{name: (value if value != "" else None) for name, value in t.model_dump().items()})
            for t in terms]


def _world_debt(debt_id: str, db: Session) -> Debt:
    debt = db.get(Debt, debt_id)
    if debt is None or debt.world_id != _crud._world_id(db):
        raise HTTPException(status_code=404, detail=f"debt {debt_id!r} not found")
    return debt


@router.get("/api/debts")
def list_debts(db: Session = Depends(get_session)) -> list[dict]:
    return debt_reads.world_debts(_crud._world_id(db), db)


@router.post("/api/debts", status_code=201)
def write_debt_by_hand(body: DebtBody, db: Session = Depends(get_session)) -> dict:
    try:
        debt = create_debt(db, world_id=_crud._world_id(db), debtor_id=body.debtor_entity_id,
                           creditor_id=body.creditor_entity_id, contact_id=body.contact_entity_id or None,
                           origin="creator", reason=body.reason, is_secret=body.is_secret, terms=_owed(body.terms),
                           changed_by="creator_crud")
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    db.commit()
    return debt_reads.debt_dict(debt, db)


@router.post("/api/debts/{debt_id}/repay")
def repay(debt_id: str, db: Session = Depends(get_session)) -> dict:
    debt = _world_debt(debt_id, db)
    try:
        settle_debt(db, debt=debt, changed_by="creator_crud")
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    db.commit()
    return debt_reads.debt_dict(debt, db)


@router.post("/api/debts/{debt_id}/forgive")
def forgive(debt_id: str, body: ForgiveBody, db: Session = Depends(get_session)) -> dict:
    debt = _world_debt(debt_id, db)
    try:
        forgive_debt(db, debt=debt, note=body.note, changed_by="creator_crud")
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    db.commit()
    return debt_reads.debt_dict(debt, db)


@router.get("/api/journee/debts")
def journee_debts(db: Session = Depends(get_session)) -> dict:
    character = _resolve_player_character(_crud._world_id(db), db)
    return debt_reads.player_debts(character, db)


@router.post("/api/services", status_code=201)
def ask_service(body: ServiceBody, db: Session = Depends(get_session)) -> dict:
    character = _resolve_player_character(_crud._world_id(db), db)
    try:
        request_service(db, character=character, provider_id=body.provider_entity_id,
                        on_behalf_of_id=body.on_behalf_of_id or None, terms=[_term(t) for t in body.terms],
                        owed=_owed(body.owed), reason=body.reason, is_secret=body.is_secret)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    db.commit()
    return debt_reads.player_debts(character, db)
