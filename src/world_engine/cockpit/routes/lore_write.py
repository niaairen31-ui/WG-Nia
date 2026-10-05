"""The Lore shell's writing panel routes (TICKET-0098, BRIEF-0098-E).

A second bounded reopening of the Lore shell's read-only lock (the Q17d
precedent): the creator writes lore in prose, answers at most one round of
clarification questions (J3), corrects the draft, and commits it. Every
model call lives in `lore_write_draft.py`, every write in
`lore_write_apply.apply_proposal`, every history read in
`lore_write_read.py`; this module orchestrates, runs no query and no model
call, and commits once per commit request. The consultation pipeline is
untouched: this module imports none of `lore_selectors`, `lore_query`,
`lore_plan`, `lore_render`, `lore_prompt` (`lore_isolation.py` R17). Every
POST passes the origin guard first (BRIEF-0098-A).

Ollama down answers 503 with `lore_write_draft.WRITE_UNAVAILABLE_MESSAGE`
(K1); no canon row is written by a draft route, ever.

Every step that reaches the model or the apply step is journaled through
`lore_usage` (TICKET-0103, BRIEF-0103-C), under the panel's `attempt_id`:
a draft step in its own transaction (`record`), a successful commit in the
commit's own transaction (`stage`), a refused commit after its rollback.
"""

from __future__ import annotations

import copy
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session

from ... import lore_mentions_read as _world
from ... import lore_usage as _usage
from ... import lore_write_apply as _apply
from ... import lore_write_draft as _draft
from ... import lore_write_read as _read
from ... import model_exchange
from ...db import get_session
from ...llm_parse import LlmParseError
from ...ollama_client import OllamaError
from .. import crud as _crud

router = APIRouter()


class StatementBody(BaseModel):
    statement: str
    answers: Optional[str] = None
    attempt_id: Optional[str] = None


class CommitBody(BaseModel):
    proposal: dict[str, Any]
    attempt_id: Optional[str] = None


def _world_id(db: Session) -> str:
    world_id = _world.active_world_id(db)
    if world_id is None:
        raise HTTPException(status_code=400, detail="No active world. Activate a world before proceeding.")
    return world_id


def _statement(body: StatementBody) -> str:
    if not body.statement.strip():
        raise HTTPException(status_code=422, detail="Le texte est vide.")
    return body.statement


def _journal_failure(db: Session, attempt: str, world_id: str, step: str, outcome: str,
                     payload: dict, exchanges: list, exc: Exception, detail: str) -> None:
    model_exchange.fail(exchanges, exc)
    _usage.record(db, attempt=attempt, world_id=world_id, kind="write", step=step,
                  outcome=outcome, payload=dict(payload, error=detail), exchanges=exchanges)


@router.post("/api/lore/write/questions")
def write_questions(body: StatementBody, db: Session = Depends(get_session)) -> dict:
    world_id = _world_id(db)
    statement = _statement(body)
    attempt = _usage.attempt_id(body.attempt_id)
    payload = {"statement": statement, "questions": None}
    exchanges: list = []
    try:
        questions = _draft.draft_questions(db, world_id, statement, exchanges)
    except OllamaError as exc:
        _journal_failure(db, attempt, world_id, "questions", "unavailable", payload, exchanges,
                         exc, _draft.WRITE_UNAVAILABLE_MESSAGE)
        raise HTTPException(status_code=503, detail=_draft.WRITE_UNAVAILABLE_MESSAGE) from exc
    except LlmParseError as exc:
        detail = f"lore questions drafting failed: {exc}"
        _journal_failure(db, attempt, world_id, "questions", "parse_error", payload, exchanges,
                         exc, detail)
        raise HTTPException(status_code=502, detail=detail) from exc
    _usage.record(db, attempt=attempt, world_id=world_id, kind="write", step="questions",
                  outcome="ok", payload=dict(payload, questions=questions, error=None),
                  exchanges=exchanges)
    return {"questions": questions}


@router.post("/api/lore/write/draft")
def write_draft(body: StatementBody, db: Session = Depends(get_session)) -> dict:
    world_id = _world_id(db)
    statement = _statement(body)
    attempt = _usage.attempt_id(body.attempt_id)
    payload = {"statement": statement, "answers": body.answers or None, "draft": None}
    exchanges: list = []
    try:
        draft = _draft.draft_proposal(db, world_id, statement, body.answers or "", exchanges)
    except OllamaError as exc:
        _journal_failure(db, attempt, world_id, "draft", "unavailable", payload, exchanges,
                         exc, _draft.WRITE_UNAVAILABLE_MESSAGE)
        raise HTTPException(status_code=503, detail=_draft.WRITE_UNAVAILABLE_MESSAGE) from exc
    except LlmParseError as exc:
        detail = f"lore proposal drafting failed: {exc}"
        _journal_failure(db, attempt, world_id, "draft", "parse_error", payload, exchanges,
                         exc, detail)
        raise HTTPException(status_code=502, detail=detail) from exc
    _usage.record(db, attempt=attempt, world_id=world_id, kind="write", step="draft",
                  outcome="ok", payload=dict(payload, draft=draft, error=None), exchanges=exchanges)
    return draft


def _entity_creator(db: Session):
    """C1: a minimal fiche through the creator CRUD's commit-free core; a
    character is born an NPC."""
    def create(name: str, entity_type: str):
        extension = {"character_type": "npc"} if entity_type == "character" else {}
        body = _crud.EntityWriteBody(entity={"type": entity_type, "name": name}, extension=extension)
        return _crud._create_entity_core(body, db)
    return create


def _refuse_commit(db: Session, attempt: str, world_id: str, proposal: dict, detail: str) -> None:
    db.rollback()
    _usage.record(db, attempt=attempt, world_id=world_id, kind="write", step="commit",
                  outcome="refused", payload={"proposal": proposal, "result": None, "error": detail})


@router.post("/api/lore/write/commit")
def write_commit(body: CommitBody, db: Session = Depends(get_session)) -> dict:
    world_id = _world_id(db)
    attempt = _usage.attempt_id(body.attempt_id)
    # `apply_proposal` annotates the dict it validates (`_type` on each
    # entity); the journal keeps the proposal as the panel sent it.
    received = copy.deepcopy(body.proposal)
    try:
        result = _apply.apply_proposal(db, world_id, body.proposal, _entity_creator(db))
    except _apply.ProposalError as exc:
        _refuse_commit(db, attempt, world_id, received, str(exc))
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except HTTPException as exc:
        _refuse_commit(db, attempt, world_id, received, str(exc.detail))
        raise
    answer = {"entry_id": result.entry_id, "written": result.written, "skipped": result.skipped}
    _usage.stage(db, attempt=attempt, world_id=world_id, kind="write", step="commit",
                 outcome="ok", payload={"proposal": received, "result": answer, "error": None},
                 lore_entry_ref=result.entry_id)
    db.commit()
    return {"ok": True, **answer}


@router.get("/api/lore/write/entries")
def write_entries(db: Session = Depends(get_session)) -> dict:
    return {"entries": _read.list_entries(db, _world_id(db))}
