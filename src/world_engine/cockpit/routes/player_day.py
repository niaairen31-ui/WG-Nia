"""The player's days (TICKET-0128, BRIEF-0128-G; G1, D1, E1): he declares, the worker runs, the creator publishes, he reads the published narrative only.

Keyed on the world and the profile given, never on the active world; the
guards are the player door's own (`routes/player.py`). Nothing else of a
day reaches the player: not the narrator's text, a failure, a proposal,
the account nor the feasibility (INV-66).
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from ...day_run_reads import unpublished_day
from ...db import get_session
from ...models import Batch, Character, PassPlay
from ...perspective_view import player_character_of
from ...writes import MAX_DECLARATION_CHARS
from ..day_declare import declare
from .player import CHARACTER_NOT_FOUND, _open_world, _player_profile

router = APIRouter()


class DayDeclareBody(BaseModel):
    profile_id: str
    world_id: str
    declared_action: str = Field(max_length=MAX_DECLARATION_CHARS)


def _state(pass_play: PassPlay) -> str:
    if pass_play.published_at is not None:
        return "publiee"
    if pass_play.status == "abandoned":
        return "abandonnee"
    if pass_play.status in ("submitted", "resolving"):
        return "en_cours"
    return "en_attente"


def _journee(character_id: Optional[str], db: Session) -> dict:
    if character_id is None:
        return {"character_id": None, "can_declare": False, "days": []}
    rows = db.exec(
        select(Batch.day_number, PassPlay)
        .join(PassPlay, PassPlay.batch_id == Batch.id)
        .where(PassPlay.character_id == character_id)
        .order_by(PassPlay.submitted_at.desc(), PassPlay.id.desc())
    ).all()
    days = []
    for day_number, pass_play in rows:
        state = _state(pass_play)
        days.append({
            "day_number": day_number,
            "declared_action": pass_play.declared_action,
            "state": state,
            "text": pass_play.published_text if state == "publiee" else None,
        })
    return {"character_id": character_id, "can_declare": unpublished_day(db, character_id) is None,
            "days": days}


def _own(profile_id: str, world_id: str, db: Session) -> Optional[str]:
    _open_world(world_id, db)
    _player_profile(profile_id, db)
    own = player_character_of(db, world_id, profile_id)
    return own[0] if own is not None else None


@router.get("/api/joueur/journee")
def player_days(profile_id: str, world_id: str, db: Session = Depends(get_session)) -> dict:
    return _journee(_own(profile_id, world_id, db), db)


@router.post("/api/joueur/journee/declarer", status_code=201)
def player_declare(body: DayDeclareBody, db: Session = Depends(get_session)) -> dict:
    character_id = _own(body.profile_id, body.world_id, db)
    if character_id is None:
        raise HTTPException(status_code=404, detail=CHARACTER_NOT_FOUND)
    declare(db, world_id=body.world_id, character=db.get(Character, character_id),
            declared_action=body.declared_action, quest_id=None, changed_by="player")
    return _journee(character_id, db)
