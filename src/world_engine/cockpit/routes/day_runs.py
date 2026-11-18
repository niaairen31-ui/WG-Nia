"""The creator's view of the day worker: failed days, relaunch, abandon, what runs now (TICKET-0128, M1, Z1, Y1).

Every route acts for the active world; a batch outside it is « Journée
introuvable. ». The worker's state covers every world: there is one worker.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ...day_run_reads import failed_days
from ...db import get_session
from ...models import Batch, Entity, PassPlay, World
from ...models import Session as GameSession
from ...writes.day_runs import abandon_day, reopen_day
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
