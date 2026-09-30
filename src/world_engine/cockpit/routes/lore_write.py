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
(K1); nothing is written by a draft route, ever.
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session

from ... import lore_mentions_read as _world
from ... import lore_write_apply as _apply
from ... import lore_write_draft as _draft
from ... import lore_write_read as _read
from ...db import get_session
from ...llm_parse import LlmParseError
from ...ollama_client import OllamaError
from .. import crud as _crud

router = APIRouter()


class StatementBody(BaseModel):
    statement: str
    answers: Optional[str] = None


class CommitBody(BaseModel):
    proposal: dict[str, Any]


def _world_id(db: Session) -> str:
    world_id = _world.active_world_id(db)
    if world_id is None:
        raise HTTPException(status_code=400, detail="No active world. Activate a world before proceeding.")
    return world_id


def _statement(body: StatementBody) -> str:
    if not body.statement.strip():
        raise HTTPException(status_code=422, detail="Le texte est vide.")
    return body.statement


@router.post("/api/lore/write/questions")
def write_questions(body: StatementBody, db: Session = Depends(get_session)) -> dict:
    world_id = _world_id(db)
    try:
        questions = _draft.draft_questions(db, world_id, _statement(body))
    except OllamaError as exc:
        raise HTTPException(status_code=503, detail=_draft.WRITE_UNAVAILABLE_MESSAGE) from exc
    except LlmParseError as exc:
        raise HTTPException(status_code=502, detail=f"lore questions drafting failed: {exc}") from exc
    return {"questions": questions}


@router.post("/api/lore/write/draft")
def write_draft(body: StatementBody, db: Session = Depends(get_session)) -> dict:
    world_id = _world_id(db)
    try:
        return _draft.draft_proposal(db, world_id, _statement(body), body.answers or "")
    except OllamaError as exc:
        raise HTTPException(status_code=503, detail=_draft.WRITE_UNAVAILABLE_MESSAGE) from exc
    except LlmParseError as exc:
        raise HTTPException(status_code=502, detail=f"lore proposal drafting failed: {exc}") from exc


def _entity_creator(db: Session):
    """C1: a minimal fiche through the creator CRUD's commit-free core; a
    character is born an NPC."""
    def create(name: str, entity_type: str):
        extension = {"character_type": "npc"} if entity_type == "character" else {}
        body = _crud.EntityWriteBody(entity={"type": entity_type, "name": name}, extension=extension)
        return _crud._create_entity_core(body, db)
    return create


@router.post("/api/lore/write/commit")
def write_commit(body: CommitBody, db: Session = Depends(get_session)) -> dict:
    world_id = _world_id(db)
    try:
        result = _apply.apply_proposal(db, world_id, body.proposal, _entity_creator(db))
    except _apply.ProposalError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except HTTPException:
        db.rollback()
        raise
    db.commit()
    return {"ok": True, "entry_id": result.entry_id, "written": result.written,
            "skipped": result.skipped}


@router.get("/api/lore/write/entries")
def write_entries(db: Session = Depends(get_session)) -> dict:
    return {"entries": _read.list_entries(db, _world_id(db))}
