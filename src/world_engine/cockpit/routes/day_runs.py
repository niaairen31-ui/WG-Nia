"""The creator's view of the day worker: failed days, relaunch, abandon, what runs now (TICKET-0128, M1, Z1, Y1).

The creator also publishes a resolved day there, once its proposals are
reviewed (C1, C′2).

Every route acts for the active world; a batch outside it is « Journée
introuvable. ». The worker's state covers every world: there is one worker.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from ...day_run_reads import PENDING_REVIEW, days_to_publish, failed_days, pending_proposals
from ...db import get_session
from ...models import Batch, Entity, PassPlay, World
from ...models import Session as GameSession
from ...writes.day_runs import EMPTY_NARRATIVE, abandon_day, publish_day, reopen_day
from .. import crud as _crud
from ..day_runner import enqueue_day, queued_count, running_day

router = APIRouter()

DAY_NOT_FOUND = "Journée introuvable."


def _active_world_day(batch_id: str, db: Session) -> PassPlay:
    world_id = _crud._world_id(db)
    pass_play = db.exec(
        select(PassPlay)
        .join(Batch, Batch.id == PassPlay.batch_id)
        .join(GameSession, GameSession.id == Batch.session_id)
        .where(Batch.id == batch_id, GameSession.world_id == world_id)
    ).first()
    if pass_play is None:
        raise HTTPException(status_code=404, detail=DAY_NOT_FOUND)
    return pass_play


@router.get("/api/day-runs/echecs")
def list_failures(db: Session = Depends(get_session)) -> list[dict]:
    return failed_days(db, _crud._world_id(db))


@router.post("/api/day-runs/{batch_id}/relancer")
def relaunch_day(batch_id: str, db: Session = Depends(get_session)) -> dict:
    pass_play = _active_world_day(batch_id, db)
    try:
        stage = reopen_day(db, pass_play=pass_play)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    db.commit()
    enqueue_day(batch_id)
    return {"ok": True, "stage": stage}


@router.post("/api/day-runs/{batch_id}/abandonner")
def give_up_day(batch_id: str, db: Session = Depends(get_session)) -> dict:
    pass_play = _active_world_day(batch_id, db)
    try:
        abandon_day(db, pass_play=pass_play)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    db.commit()
    return {"ok": True}


@router.get("/api/day-runs/etat")
def worker_state(db: Session = Depends(get_session)) -> dict:
    running = None
    batch_id = running_day()
    if batch_id is not None:
        row = db.exec(
            select(Batch.day_number, Entity.name, World.name)
            .join(PassPlay, PassPlay.batch_id == Batch.id)
            .join(Entity, Entity.id == PassPlay.character_id)
            .join(GameSession, GameSession.id == Batch.session_id)
            .join(World, World.id == GameSession.world_id)
            .where(Batch.id == batch_id)
        ).first()
        if row is not None:
            running = {"batch_id": batch_id, "day_number": row[0], "character_name": row[1], "world_name": row[2]}
    return {"running": running, "queued": queued_count()}


class PublishBody(BaseModel):
    text: Optional[str] = None  # None: the narrator's text as is


@router.get("/api/day-runs/a-publier")
def list_to_publish(db: Session = Depends(get_session)) -> list[dict]:
    return days_to_publish(db, _crud._world_id(db))


@router.post("/api/day-runs/{batch_id}/publier")
def publish(batch_id: str, body: PublishBody, db: Session = Depends(get_session)) -> dict:
    pass_play = _active_world_day(batch_id, db)
    if pending_proposals(db, pass_play.id) > 0:
        raise HTTPException(status_code=409, detail=PENDING_REVIEW)
    batch = db.get(Batch, batch_id)
    text_ = body.text if body.text is not None else (batch.final_result or "")
    try:
        publish_day(db, pass_play=pass_play, text=text_)
    except ValueError as exc:
        raise HTTPException(status_code=422 if str(exc) == EMPTY_NARRATIVE else 409, detail=str(exc)) from exc
    db.commit()
    return {"ok": True, "published_at": pass_play.published_at.isoformat()}
