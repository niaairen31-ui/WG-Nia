"""The quest requests' routes (TICKET-0121, BRIEF-0121-E, C-12).

A request is what the planner opened when a declared day could not be anchored in the lore
(`writes/quest_requests.py`). The creator's panel lists them and moves each one:
    GET  /api/quest-requests                    the active world's requests, newest first
    POST /api/quest-requests/{id}/design        « Concevoir » -- the designer's run (C-11)
    POST /api/quest-requests/{id}/answer        the existence question's answer
    POST /api/quest-requests/{id}/drop          « Mettre de côté »

Every rule of what a status allows is the case table of the lot (C-02); every model call lives in
`quest_designer`, every write in `writes/quest_requests`; this module parses, maps a refusal to its
status code and commits once per request. Every POST passes the origin guard. Nothing here reaches a
player surface: no response carries an agenda or step id.
"""

from __future__ import annotations

from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session

from ... import quest_designer
from ...db import get_session
from ...llm_parse import LlmParseError
from ...models import Entity, ProposedMutation, QuestRequest
from ...ollama_client import OllamaError
from ...quest_requests import request_dict, world_requests
from ...writes.quest_requests import move_request
from .. import crud as _crud

router = APIRouter()

PARSE_ERROR_MESSAGE = (
    "Le modèle a répondu dans une forme illisible : la demande n'a pas été conçue et rien n'a changé. "
    "Relance."
)
PENDING_PROPOSAL = ("proposed", "approved")


class AnswerBody(BaseModel):
    answer: Literal["exists", "absent", "already"]
    text: str = ""
    entity_id: Optional[str] = None


def _request(db: Session, request_id: str) -> QuestRequest:
    request = db.get(QuestRequest, request_id)
    if request is None or request.world_id != _crud._world_id(db):
        raise HTTPException(status_code=404, detail=f"quest request {request_id!r} not found")
    return request


def _proposal_status(db: Session, request: QuestRequest) -> Optional[str]:
    proposal = db.get(ProposedMutation, request.mutation_id) if request.mutation_id else None
    return proposal.status if proposal is not None else None


def _may_design(db: Session, request: QuestRequest) -> bool:
    """C-02: from `new`, `covered`, and `proposed` when its proposal was rejected."""
    if request.status in ("new", "covered"):
        return True
    return request.status == "proposed" and _proposal_status(db, request) == "rejected"


@router.get("/api/quest-requests")
def list_requests(db: Session = Depends(get_session)) -> list[dict]:
    return [request_dict(r, db) for r in world_requests(db, _crud._world_id(db))]


@router.post("/api/quest-requests/{request_id}/design")
def design(request_id: str, db: Session = Depends(get_session)) -> dict:
    request = _request(db, request_id)
    if not _may_design(db, request):
        raise HTTPException(status_code=409, detail=f"a {request.status!r} request cannot be designed now")
    try:
        result = quest_designer.design(db, request, [])
    except OllamaError as exc:
        db.rollback()
        raise HTTPException(status_code=503, detail=quest_designer.DESIGNER_UNAVAILABLE_MESSAGE) from exc
    except LlmParseError as exc:
        db.rollback()
        raise HTTPException(status_code=502, detail=PARSE_ERROR_MESSAGE) from exc
    db.commit()
    db.refresh(request)
    return {**request_dict(request, db), "outcome": result.outcome, "notes": result.notes}


@router.post("/api/quest-requests/{request_id}/answer")
def answer(request_id: str, body: AnswerBody, db: Session = Depends(get_session)) -> dict:
    request = _request(db, request_id)
    if request.status != "asking":
        raise HTTPException(status_code=409, detail=f"a {request.status!r} request asks nothing")
    subject = request.subject or request.declaration
    if body.answer == "already":
        entity = db.get(Entity, body.entity_id) if body.entity_id else None
        if entity is None or entity.world_id != request.world_id:
            raise HTTPException(status_code=422, detail="Choisis l'entité du monde qui le contient déjà.")
        move_request(db, request, "new", existence_answer="already", existing_entity_id=entity.id)
        statement = None
    else:
        text = body.text.strip()
        move_request(db, request, "writing_lore", existence_answer=body.answer, creator_text=text)
        statement = f"{subject} : {text}" if body.answer == "exists" else \
            f"{subject} n'existe pas dans ce monde. {text}".strip()
    db.commit()
    db.refresh(request)
    return {"request": request_dict(request, db), "statement": statement}


@router.post("/api/quest-requests/{request_id}/drop")
def drop(request_id: str, db: Session = Depends(get_session)) -> dict:
    request = _request(db, request_id)
    if request.status == "dropped" or (
            request.status == "proposed" and _proposal_status(db, request) in PENDING_PROPOSAL):
        raise HTTPException(status_code=409, detail=f"a {request.status!r} request cannot be set aside now")
    move_request(db, request, "dropped")
    db.commit()
    db.refresh(request)
    return request_dict(request, db)
