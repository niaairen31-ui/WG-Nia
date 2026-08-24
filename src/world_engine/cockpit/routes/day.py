"""Day declaration routes (TICKET-0075, BRIEF-0075-a — the declaration
socle: plumbing only). A player declares a day; the declaration is stored,
listed and read back. No resolution, no plan emission, no model call of any
kind appears anywhere in this module.

`_get_or_open_session` deliberately duplicates the M5 idiom from
`cockpit/play.py` (`_get_or_open_session`) rather than importing it: Play is
a sealed module (TICKET-0069 is its own migration), and this surface must
not couple to it.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from ...db import get_session
from ...models import Batch, Character, PassPlay
from ...models import Session as GameSession
from ...writes import MAX_DECLARATION_CHARS, write_batch, write_pass_play
from .. import crud as _crud

router = APIRouter()


def _get_or_open_session(world_id: str, db: Session) -> GameSession:
    """Return the world's open session, creating one if none exists (same
    idiom as `cockpit/play.py::_get_or_open_session`, duplicated on
    purpose — see module docstring)."""
    existing = db.exec(
        select(GameSession)
        .where(GameSession.world_id == world_id, GameSession.status == "open")
        .order_by(GameSession.number.desc())
    ).first()
    if existing is not None:
        return existing
    numbers = db.exec(
        select(GameSession.number).where(GameSession.world_id == world_id)
    ).all()
    number = (max(numbers) if numbers else 0) + 1
    sess = GameSession(
        world_id=world_id,
        number=number,
        title="Live play session",
        status="open",
        started_at=datetime.now(UTC),
    )
    db.add(sess)
    db.commit()
    db.refresh(sess)
    return sess


def _resolve_player_character(world_id: str, db: Session) -> Character:
    rows = db.exec(
        select(Character).where(
            Character.world_id == world_id, Character.character_type == "player",
        )
    ).all()
    if len(rows) != 1:
        raise HTTPException(
            status_code=400,
            detail=(
                f"expected exactly one player character for this world, found {len(rows)}"
            ),
        )
    return rows[0]


def _day_dict(batch: Batch, pass_play: PassPlay) -> dict:
    # `status` is the pass_play lifecycle (PASS_PLAY_STATUSES) -- the
    # player's own declaration, not `batch.status` (a separate, larger
    # vocabulary belonging to the legacy Claude-checkpoint pipeline).
    return {
        "id": batch.id,
        "day_number": batch.day_number,
        "status": pass_play.status,
        "declared_action": pass_play.declared_action,
        "created_at": batch.created_at.isoformat() if batch.created_at else None,
    }


class DayDeclareBody(BaseModel):
    # Bound read from writes/pipeline.py rather than restated as a literal
    # (R4) -- this is a fast client-facing 422, write_pass_play's own check
    # is the structural guarantee.
    declared_action: str = Field(max_length=MAX_DECLARATION_CHARS)


@router.post("/api/day/declare")
def declare_day(body: DayDeclareBody, db: Session = Depends(get_session)) -> dict:
    world_id = _crud._world_id(db)
    game_session = _get_or_open_session(world_id, db)
    character = _resolve_player_character(world_id, db)

    batch = write_batch(db, session_id=game_session.id, changed_by="player")
    try:
        pass_play = write_pass_play(
            db,
            batch_id=batch.id,
            session_id=game_session.id,
            character_id=character.id,
            declared_action=body.declared_action,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    db.add(batch)
    db.add(pass_play)
    db.commit()
    db.refresh(batch)
    db.refresh(pass_play)
    return _day_dict(batch, pass_play)


@router.get("/api/days")
def list_days(db: Session = Depends(get_session)) -> list[dict]:
    world_id = _crud._world_id(db)
    rows = db.exec(
        select(Batch, PassPlay)
        .join(GameSession, GameSession.id == Batch.session_id)
        .join(PassPlay, PassPlay.batch_id == Batch.id)
        .where(GameSession.world_id == world_id)
        .order_by(Batch.day_number.desc())
    ).all()
    return [_day_dict(batch, pass_play) for batch, pass_play in rows]


@router.get("/api/day/{batch_id}")
def get_day(batch_id: str, db: Session = Depends(get_session)) -> dict:
    world_id = _crud._world_id(db)
    row = db.exec(
        select(Batch, PassPlay)
        .join(GameSession, GameSession.id == Batch.session_id)
        .join(PassPlay, PassPlay.batch_id == Batch.id)
        .where(Batch.id == batch_id, GameSession.world_id == world_id)
    ).first()
    if row is None:
        raise HTTPException(status_code=404, detail=f"day {batch_id!r} not found")
    batch, pass_play = row
    return _day_dict(batch, pass_play)
