"""The condition interpreter's routes (TICKET-0112, BRIEF-0112-D; decisions
IB1, IG1, IH1, IJ1).

The offer editor asks for a condition in French and gets a proposal back;
nothing here touches an offer -- the creator inserts the proposal into her
draft and her « Enregistrer » writes it (`routes/quests.py`), A1 of the
conditions series:
    POST /api/conditions/interpret                    a sentence -> a proposal
    POST /api/conditions/drafts/{draft_id}/resolve    the names she picked
    POST /api/conditions/drafts/{draft_id}/decision   inserted | discarded

Every model call lives in `condition_interpreter`, every journal write in
`writes/condition_drafts.py`; this module parses, maps a refusal to its
status code, and commits once per request. Every proposal that reached the
model is journaled, the unavailable and the unparsable included (IH1, D1);
a request refused before the model (no active world, an empty sentence, an
unknown role, a current tree that does not hold) is not. Every POST passes
the origin guard (`cockpit/origin_guard.py`, mounted on the app).
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session

from ... import condition_interpreter as _interpreter
from ... import model_exchange
from ...conditions import node_from_dict
from ...db import get_session
from ...llm_parse import LlmParseError
from ...lore_usage import attempt_id as _attempt_id
from ...models import CONDITION_ROLES, ConditionDraft
from ...ollama_client import OllamaError
from ...quest_reads import condition_view
from ...writes.conditions import clean_condition
from ...writes.condition_drafts import move_condition_draft, write_condition_draft
from .. import crud as _crud

router = APIRouter()

PARSE_ERROR_MESSAGE = (
    "Le modèle a répondu dans une forme illisible : aucune condition n'a été proposée "
    "et rien n'a changé dans l'offre. Relance, ou reformule ta phrase."
)
DECISIONS: tuple[str, ...] = ("inserted", "discarded")


class InterpretBody(BaseModel):
    instruction: str
    role: str
    # The condition being edited (IC1), in the dict form of
    # `conditions.node_to_dict`; null when the creator starts from nothing.
    current: Optional[dict] = None
    attempt_id: Optional[str] = None


class ResolveBody(BaseModel):
    bindings: dict[str, str] = Field(default_factory=dict)


class DecisionBody(BaseModel):
    decision: str


def _current(body: InterpretBody, world_id: str, db: Session):
    if not body.instruction.strip():
        raise HTTPException(status_code=422, detail="Écris d'abord la condition en une phrase.")
    if body.role not in CONDITION_ROLES:
        raise HTTPException(status_code=422, detail=f"unknown condition role {body.role!r}")
    try:
        return clean_condition(db, world_id, node_from_dict(body.current), where="current: ")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"La condition actuelle ne tient pas : {exc}") from exc


def _answer(draft: ConditionDraft, result: Optional[_interpreter.Interpretation], db: Session) -> dict:
    """C-06: what the editor shows."""
    if result is None:
        return {"draft_id": draft.id, "outcome": draft.outcome, "view": None, "mentions": [], "notes": [],
                "errors": []}
    return {
        "draft_id": draft.id, "outcome": result.outcome,
        "view": condition_view(db, result.tree) if result.tree is not None else None,
        "mentions": [m for m in result.mentions if m["status"] != "matched" and m["choices"]],
        "notes": result.notes, "errors": result.errors,
    }


def _failed(db: Session, body: InterpretBody, world_id: str, current, outcome: str,
            exchanges: list, exc: Exception) -> None:
    model_exchange.fail(exchanges, exc)
    empty = _interpreter.Interpretation(outcome, None, None, [], [], [])
    write_condition_draft(
        db, attempt_id=_attempt_id(body.attempt_id), world_id=world_id, role=body.role,
        instruction=body.instruction, outcome=outcome, payload=empty.payload(current),
        model_calls=[e.to_record() for e in exchanges],
    )
    db.commit()


@router.post("/api/conditions/interpret")
def interpret(body: InterpretBody, db: Session = Depends(get_session)) -> dict:
    world_id = _crud._world_id(db)
    current = _current(body, world_id, db)
    exchanges: list[model_exchange.ModelExchange] = []
    try:
        result = _interpreter.interpret(db, world_id, body.role, body.instruction, current, exchanges)
    except OllamaError as exc:
        _failed(db, body, world_id, current, "unavailable", exchanges, exc)
        raise HTTPException(status_code=503, detail=_interpreter.INTERPRET_UNAVAILABLE_MESSAGE) from exc
    except LlmParseError as exc:
        _failed(db, body, world_id, current, "parse_error", exchanges, exc)
        raise HTTPException(status_code=502, detail=PARSE_ERROR_MESSAGE) from exc
    draft = write_condition_draft(
        db, attempt_id=_attempt_id(body.attempt_id), world_id=world_id, role=body.role,
        instruction=body.instruction, outcome=result.outcome, retried=result.retried,
        payload=result.payload(current), model_calls=[e.to_record() for e in exchanges],
    )
    db.commit()
    return _answer(draft, result, db)


def _draft(db: Session, draft_id: str) -> ConditionDraft:
    world_id = _crud._world_id(db)
    draft = db.get(ConditionDraft, draft_id)
    if draft is None or draft.world_ref != world_id:
        raise HTTPException(status_code=404, detail=f"condition draft {draft_id!r} not found")
    return draft


@router.post("/api/conditions/drafts/{draft_id}/resolve")
def resolve(draft_id: str, body: ResolveBody, db: Session = Depends(get_session)) -> dict:
    draft = _draft(db, draft_id)
    if draft.outcome != "needs_choice":
        raise HTTPException(status_code=409, detail=f"a {draft.outcome!r} proposal has no name to pick")
    stored = draft.payload
    try:
        result = _interpreter.resolve(db, draft.world_ref, stored["pending"], stored["mentions"],
                                      stored["notes"], body.bindings)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    move_condition_draft(db, draft, result.outcome,
                         result.payload(node_from_dict(stored["current"]), body.bindings))
    db.commit()
    return _answer(draft, result, db)


@router.post("/api/conditions/drafts/{draft_id}/decision")
def decide(draft_id: str, body: DecisionBody, db: Session = Depends(get_session)) -> dict:
    draft = _draft(db, draft_id)
    if body.decision not in DECISIONS:
        raise HTTPException(status_code=422, detail=f"unknown decision {body.decision!r}")
    try:
        move_condition_draft(db, draft, body.decision)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    db.commit()
    return _answer(draft, None, db)
