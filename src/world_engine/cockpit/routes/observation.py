"""Observation-run routes (TICKET-0051, BRIEF-0051-e/f).

Four write-side routes over `observation_runner.py` (start / step / stop /
inject-event) — parameter validation and a call into the runner, no business
logic here. Per the mini-RECON's process-model finding: a bounded run can be
~150 model calls (5 NPCs x 30 beats), too long for one synchronous HTTP
request, so there is no "run to completion" route. `start` only creates the
run; the client (the Observation cockpit surface, BRIEF-0051-f, or a script)
drives it forward by calling `step` repeatedly. `run_bounded` stays a
Python-level entry point for scripts and the verify check.

Read-side routes (list/detail/proposals) call into `observation_reads.py`
only — never an `Observation*` model class directly (BRIEF-0051-f), so this
module needs no entry in `observation_socle.py`'s model-identifier allowlist.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session

from ... import observation_reads as _reads
from ... import observation_runner as _runner
from ... import ollama_client
from ...db import get_session
from .. import crud as _crud

router = APIRouter()


class ObservationStartBody(BaseModel):
    world_id: str
    location_id: str
    max_beats: int = 30
    quiescence_limit: int = 5
    mj_narration: bool = False
    cooldown_beats: int = 2
    debt_weight: float = 1.0
    propensity_mode: str = "flat"
    model: str = ollama_client.DEFAULT_MODEL
    player_presence: str = "absent"
    gathering_id: Optional[str] = None


@router.post("/api/observation/runs")
def start_observation_run(body: ObservationStartBody, db: Session = Depends(get_session)) -> dict:
    run, failures = _runner.start_run(
        body.world_id, body.location_id, db,
        max_beats=body.max_beats, quiescence_limit=body.quiescence_limit,
        mj_narration=body.mj_narration, cooldown_beats=body.cooldown_beats,
        debt_weight=body.debt_weight, propensity_mode=body.propensity_mode,
        model=body.model, player_presence=body.player_presence, gathering_id=body.gathering_id,
    )
    if run is None:
        raise HTTPException(status_code=422, detail={"failures": failures})
    return {"id": run.id, "status": run.status}


@router.post("/api/observation/runs/{run_id}/step")
def step_observation_run(run_id: str, db: Session = Depends(get_session)) -> dict:
    try:
        beat, run = _runner.step_run(run_id, db)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {
        "beat": {
            "id": beat.id, "beat_index": beat.beat_index, "outcome": beat.outcome,
            "actor_id": beat.actor_id, "line": beat.line, "mj_narration": beat.mj_narration,
        },
        "run": {"id": run.id, "status": run.status, "stop_reason": run.stop_reason},
    }


@router.post("/api/observation/runs/{run_id}/stop")
def stop_observation_run(run_id: str, db: Session = Depends(get_session)) -> dict:
    try:
        run = _runner.stop_run(run_id, db)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"id": run.id, "status": run.status, "stop_reason": run.stop_reason}


class ObservationEventBody(BaseModel):
    text: str


@router.post("/api/observation/runs/{run_id}/events")
def inject_observation_event(
    run_id: str, body: ObservationEventBody, db: Session = Depends(get_session),
) -> dict:
    try:
        beat = _runner.inject_event(run_id, body.text, db)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"id": beat.id, "beat_index": beat.beat_index, "outcome": beat.outcome, "line": beat.line}


# ── Read routes (BRIEF-0051-f) ───────────────────────────────────────────


@router.get("/api/observation/locations/{location_id}/present-npcs")
def list_observation_present_npcs(location_id: str, db: Session = Depends(get_session)) -> list[dict]:
    return _reads.list_present_npcs(location_id, db)


@router.get("/api/observation/runs")
def list_observation_runs(db: Session = Depends(get_session)) -> list[dict]:
    return _reads.list_runs(_crud._world_id(db), db)


@router.get("/api/observation/runs/{run_id}")
def get_observation_run(run_id: str, db: Session = Depends(get_session)) -> dict:
    detail = _reads.get_run_detail(run_id, db)
    if detail is None:
        raise HTTPException(status_code=404, detail=f"observation_run {run_id!r} not found")
    return detail


@router.get("/api/observation/runs/{run_id}/proposals")
def get_observation_run_proposals(run_id: str, db: Session = Depends(get_session)) -> list[dict]:
    return _reads.get_run_proposals(run_id, db)
