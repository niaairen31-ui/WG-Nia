"""The creator's perspective routes: Lore as everybody or as any character (TICKET-0125, BRIEF-0125-E, C-10; TICKET-0127, C-13).

Lore « as the public » or « as X »: Nia asks what everybody -- or any one
character, at the creator's door (his own secrets shown, marked) -- knows
and sees, beside the answer, the rows it was built from and the audit of
what was withheld.
Thin orchestration only -- no `chat(`, no `select(` here (as
`routes/lore.py`): the flow lives in `cockpit/perspective_flow.py`, shared
with the player's door. An unknown perspective is refused before anything
is journaled; the characters she may ask as come from
`perspective_view.world_characters`.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session

from ... import lore_usage as _usage
from ...db import get_session
from ...perspective_view import world_characters
from .. import perspective_flow as _flow

router = APIRouter()

UNKNOWN_PERSPECTIVE_MESSAGE = "Perspective inconnue."
ASKED_BY = "creator"


class PerspectiveAskBody(BaseModel):
    question: str
    world_id: str
    perspective: str
    character_id: Optional[str] = None
    attempt_id: Optional[str] = None


class PerspectiveResolveBody(BaseModel):
    plan: dict
    bindings: dict[str, str]
    world_id: str
    question: str
    perspective: str
    character_id: Optional[str] = None
    attempt_id: Optional[str] = None


def _check_perspective(perspective: str, character_id: Optional[str]) -> None:
    """Only `("public", None)` and `("character", <id>)`; 422 before any journal row."""
    if perspective == "public" and character_id is None:
        return
    if perspective == "character" and character_id:
        return
    raise HTTPException(status_code=422, detail=UNKNOWN_PERSPECTIVE_MESSAGE)


@router.get("/api/lore/perspective/characters")
def list_perspective_characters(world_id: str, db: Session = Depends(get_session)) -> list[dict]:
    return world_characters(db, world_id)


@router.post("/api/lore/perspective/ask")
def ask_perspective(body: PerspectiveAskBody, db: Session = Depends(get_session)) -> dict:
    _check_perspective(body.perspective, body.character_id)
    return _flow.ask_flow(db, question=body.question, world_id=body.world_id, asked_by=ASKED_BY,
                          attempt=_usage.attempt_id(body.attempt_id),
                          character_id=body.character_id, door="creator")


@router.post("/api/lore/perspective/resolve")
def resolve_perspective(body: PerspectiveResolveBody, db: Session = Depends(get_session)) -> dict:
    _check_perspective(body.perspective, body.character_id)
    return _flow.resolve_flow(db, plan_raw=body.plan, bindings=body.bindings, question=body.question,
                              world_id=body.world_id, asked_by=ASKED_BY,
                              attempt=_usage.attempt_id(body.attempt_id),
                              character_id=body.character_id, door="creator")
