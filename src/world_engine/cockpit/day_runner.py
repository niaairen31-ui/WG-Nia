"""One background worker plans then resolves each declared day, one at a time, in arrival order; a failure is written, never silent (TICKET-0128, B2, K1, S1, R1, L1).

A day module (INV-71): the world and the character come from the day.
`cockpit/routes/day.py` is imported only inside `run_day`, never at module
level (the routes import this module's `enqueue_day` through
`day_declare`). Checks drive `run_day` synchronously and never start the
thread.
"""

from __future__ import annotations

import logging
import queue
import threading
from typing import Optional

from fastapi import HTTPException
from sqlmodel import Session, select

from ..db import engine
from ..models import Batch, PassPlay
from ..models import Session as GameSession
from ..writes.day_runs import write_day_run_failure

_log = logging.getLogger(__name__)

INTERRUPTED_REASON = "Interrompue : le serveur s'est arrêté pendant la journée."

_QUEUE: "queue.Queue[str]" = queue.Queue()
_STATE: dict = {"running": None, "thread": None}
_START_LOCK = threading.Lock()


def failure_of(exc: BaseException) -> tuple[str, str]:
    """The failure code and reason an exception of the chain gives."""
    if isinstance(exc, HTTPException):
        status = exc.status_code
        if status == 502:
            code = "model_failed"
        elif status == 409:
            code = "blocked"
        elif status == 422:
            code = "rejected"
        elif 400 <= status < 500:
            code = "refused"
        else:
            code = "crashed"
        detail = exc.detail
        if isinstance(detail, str):
            reason = detail
        elif isinstance(detail, dict) and "message" in detail:
            reason = str(detail["message"])
        else:
            reason = str(detail)
        return code, reason
    return "crashed", str(exc) or type(exc).__name__


def _world_of_day(db: Session, batch_id: str) -> Optional[str]:
    return db.exec(
        select(GameSession.world_id).join(Batch, Batch.session_id == GameSession.id).where(Batch.id == batch_id)
    ).first()


def _record_failure(batch_id: str, stage: str, exc: BaseException) -> str:
    code, reason = failure_of(exc)
    with Session(engine) as db:
        pass_play = db.exec(select(PassPlay).where(PassPlay.batch_id == batch_id)).first()
        world_id = _world_of_day(db, batch_id)
        if pass_play is None or world_id is None:
            _log.error("day_runner: day %s vanished before its failure could be written", batch_id)
            return code
        write_day_run_failure(db, pass_play=pass_play, world_id=world_id, stage=stage, code=code, reason=reason)
        db.commit()
    return code


def run_day(batch_id: str) -> Optional[str]:
    """Plan then resolve one day; the failure code, or None on success or
    when there is nothing to run."""
    from .routes import day as _day

    _STATE["running"] = batch_id
    stage = "plan"
    try:
        with Session(engine) as db:
            pass_play = db.exec(select(PassPlay).where(PassPlay.batch_id == batch_id)).first()
            if pass_play is None or pass_play.status not in ("submitted", "resolving"):
                return None
            try:
                if pass_play.status == "submitted":
                    stage = "plan"
                    _day.plan_day(batch_id, db)
                    db.expire_all()
                    pass_play = db.exec(select(PassPlay).where(PassPlay.batch_id == batch_id)).first()
                if pass_play is not None and pass_play.status == "resolving":
                    stage = "resolve"
                    _day.resolve_day(batch_id, db)
            except Exception as exc:  # noqa: BLE001 -- B2: every failure is written
                db.rollback()
                _log.warning("day_runner: day %s failed at %s: %s", batch_id, stage, exc)
                return _record_failure(batch_id, stage, exc)
        return None
    finally:
        _STATE["running"] = None


def enqueue_day(batch_id: str) -> None:
    """Hand a declared day to the worker (arrival order)."""
    _QUEUE.put(batch_id)


def queued_count() -> int:
    return _QUEUE.qsize()


def running_day() -> Optional[str]:
    """The batch id the worker is running now, or None."""
    return _STATE["running"]


def interrupt_stale_days() -> int:
    """R1: at startup, every day left `submitted` or `resolving` by a
    stopped server gets an `interrupted` failure; one commit."""
    count = 0
    with Session(engine) as db:
        rows = db.exec(
            select(PassPlay, GameSession.world_id)
            .join(Batch, Batch.id == PassPlay.batch_id)
            .join(GameSession, GameSession.id == Batch.session_id)
            .where(PassPlay.status.in_(("submitted", "resolving")))
        ).all()
        for pass_play, world_id in rows:
            stage = "resolve" if pass_play.status == "resolving" else "plan"
            write_day_run_failure(db, pass_play=pass_play, world_id=world_id, stage=stage,
                                  code="interrupted", reason=INTERRUPTED_REASON)
            count += 1
        db.commit()
    return count


def _loop() -> None:
    while True:
        batch_id = _QUEUE.get()
        try:
            run_day(batch_id)
        except Exception:  # noqa: BLE001 -- the worker never dies on one day
            _log.exception("day_runner: unexpected error on day %s", batch_id)
        finally:
            _QUEUE.task_done()


def start_day_runner() -> None:
    """Start the one worker thread; idempotent."""
    with _START_LOCK:
        thread = _STATE["thread"]
        if thread is not None and thread.is_alive():
            return
        thread = threading.Thread(target=_loop, name="day-runner", daemon=True)
        _STATE["thread"] = thread
        thread.start()
