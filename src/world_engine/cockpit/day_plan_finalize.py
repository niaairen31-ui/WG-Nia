"""Plan finalizers, relocated from `cockpit/routes/day.py` for
module-budget headroom (TICKET-0121, BRIEF-0121-D) -- the
`day_reconcile_apply.py` precedent. Byte-identical otherwise:
`_feasibility_dict`, `_plan_step_dict`, `_finalize_plan`, in that order;
`_inquiry_cut` and `_open_step_requests` (AMENDMENT-0121-02) are the two
blocks of `_finalize_plan` the inquiry band added, extracted unchanged.
`finalize_inquiry_day` (TICKET-0121, BRIEF-0121-D, K1) follows them: the day
of a declaration that seeks what a day cannot give is a one-step search;
`close_inquiry_steps` (T1) closes its step when the day resolves.
"""

from __future__ import annotations

from typing import Optional

from fastapi import HTTPException
from sqlmodel import Session, select

from ..conditions import Bindings
from ..day_feasibility import veto as feasibility_veto
from ..day_plan import (
    DAY_BUDGET_SLOTS,
    EvaluatedStep,
    PlanStep,
    anchor_requirements,
    budget_cut,
    evaluate_requirements,
)
from ..day_resolve import INQUIRY_BAND
from ..models import Agenda, AgendaStep, Character, PassPlay
from ..writes import write_agenda_status, write_agenda_step_status, write_day_feasibility, write_day_plan
from ..writes.quest_requests import open_request


def _feasibility_dict(
    python_retained: int, veto_retained: int, reason: str, cited_objective: Optional[str], outcome: str,
) -> dict:
    """Player-facing shape (BRIEF-0075-g, Wiring): counts, the reason, the
    cited step's OBJECTIVE (never its order/id -- ticket-wide Scope OUT),
    and the honoured/clamped/unavailable flag. Shared by the `/plan`
    response (built from the fresh `VetoVerdict`) and `GET /api/day/{id}`
    (built from the persisted `pass_play.history` entry via `read_latest_
    feasibility` -- never `.history` itself, `pipeline_wiring.py`'s R5)."""
    return {
        "python_retained": python_retained,
        "veto_retained": veto_retained,
        "reason": reason,
        "cited_objective": cited_objective,
        "outcome": outcome,
    }


def _plan_step_dict(evaluated: EvaluatedStep, status: str) -> dict:
    return {
        "objective": evaluated.step.objective,
        "cost": evaluated.step.cost,
        "domain": evaluated.step.domain,
        "status": status,
        "requirements": [
            {"met": v.met, "current": v.current, "required": v.required, "reason": v.reason}
            for v in evaluated.verdicts
        ],
    }


def _inquiry_cut(anchored_steps: list, dropped_report: list) -> tuple[list, Optional[int], int]:
    """R1 (TICKET-0121): the first step with a knowledge the planner cannot
    anchor becomes the day's inquiry step and the plan stops there -- the
    steps after it are never written (`inquiry_cut`). Its own requirements
    stand as anchored; the dropped leaf is what the request will settle.
    Returns the steps kept, the inquiry step's index and the count cut."""
    inquiry_index: Optional[int] = None
    inquiry_cut = 0
    if dropped_report:
        inquiry_index = min(d["step_index"] for d in dropped_report)
        inquiry_cut = len(anchored_steps) - (inquiry_index + 1)
        anchored_steps = anchored_steps[: inquiry_index + 1]
    return anchored_steps, inquiry_index, inquiry_cut


def _open_step_requests(
    db: Session, world_id: str, character: Character, pass_play: PassPlay, agenda: Agenda,
    inquiry_index: Optional[int], blocked_index: Optional[int],
) -> None:
    """K1b / R1 (TICKET-0121): the requests are born on the written rows. The
    inquiry step first -- one request per step, and it is the one that
    decides the inquiry band; a blocked step that is also the inquiry step
    keeps its `dropped` request (`open_request` is idempotent per step)."""
    if inquiry_index is not None or blocked_index is not None:
        written = db.exec(
            select(AgendaStep).where(AgendaStep.agenda_id == agenda.id).order_by(AgendaStep.step_order)
        ).all()
        for index, trigger in ((inquiry_index, "dropped"), (blocked_index, "blocked")):
            if index is not None:
                open_request(
                    db, world_id=world_id, character_id=character.id, pass_play_id=pass_play.id,
                    trigger=trigger, declaration=written[index].objective, agenda_step_id=written[index].id,
                )


def _finalize_plan(
    world_id: str, character: Character, pass_play: PassPlay, raw_steps: list, db: Session,
) -> dict:
    # BRIEF-0078-a, Scope IN item 7: anchoring runs BEFORE evaluate_requirements
    # so a dropped requirement never reaches evaluate_requirements or
    # the step's stored condition (E2 — reporting, never refusing: /plan still
    # returns 200 and writes the plan exactly as it does today).
    anchored_steps, dropped_report = anchor_requirements(raw_steps, character, db)
    # R1 (TICKET-0121): the inquiry step ends the plan (`_inquiry_cut`).
    anchored_steps, inquiry_index, inquiry_cut = _inquiry_cut(anchored_steps, dropped_report)
    bindings = Bindings(doer=character)
    evaluated_steps = [
        EvaluatedStep(step=step, verdict=evaluate_requirements(step, bindings, db))
        for step in anchored_steps
    ]
    budget_result = budget_cut(evaluated_steps, DAY_BUDGET_SLOTS)
    # BRIEF-0075-g, Y1: the veto runs AFTER budget_cut, on an already-legal
    # plan (R4) — its own output can only narrow `budget_result.included`
    # further, never widen it (day_feasibility.clamp_verdict, R1/R2).
    verdict = feasibility_veto(budget_result, character, pass_play.declared_action, db)
    active_step_index = 0 if verdict.veto_retained > 0 else None

    # E2: reporting, never refusing — a budget-only cut is not a block.
    blocked_index: Optional[int] = None
    blocked_text: Optional[str] = None
    if budget_result.first_excluded_index is not None:
        excluded = evaluated_steps[budget_result.first_excluded_index]
        if not excluded.met:
            blocked_index = budget_result.first_excluded_index
            blocked_text = "; ".join(v.reason for v in excluded.verdicts if not v.met)

    title = pass_play.declared_action.strip().splitlines()[0][:200]
    try:
        agenda = write_day_plan(
            db,
            world_id=world_id,
            owner_entity_id=character.id,
            title=title,
            steps=[evaluated.step for evaluated in evaluated_steps],
            active_step_index=active_step_index,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    # K1b / R1 (TICKET-0121): the requests are born on the written rows.
    _open_step_requests(db, world_id, character, pass_play, agenda, inquiry_index, blocked_index)

    # Germs (already staged by `_extract_and_concord`) commit in the same
    # transaction as the plan (Scope IN item 4, all-or-nothing) — never
    # added inside day_concordance.py itself (R1). The feasibility verdict
    # (item 4, observability) is recorded in the SAME transaction, exactly
    # once per pass_play, BEFORE the status move to 'resolving'.
    write_day_feasibility(db, pass_play=pass_play, verdict=verdict)
    pass_play.status = "resolving"
    pass_play.agenda_id = agenda.id  # BRIEF-0077-a: which plan this day advanced
    db.add(pass_play)
    db.commit()

    return {
        "steps": [
            _plan_step_dict(evaluated, "active" if idx == active_step_index else "pending")
            for idx, evaluated in enumerate(evaluated_steps)
        ],
        "slots_consumed": budget_result.slots_consumed,
        "slots_budget": budget_result.slots_budget,
        "first_excluded_index": budget_result.first_excluded_index,
        "feasibility": _feasibility_dict(
            verdict.python_retained, verdict.veto_retained, verdict.reason,
            verdict.cited_objective, verdict.outcome,
        ),
        "anchoring": {"dropped": dropped_report},
        "blocked_at_index": blocked_index,
        "blocked_reason": blocked_text,
        "inquiry_cut": inquiry_cut,
    }


INQUIRY_OBJECTIVE_PREFIX = "Se renseigner : "


def finalize_inquiry_day(
    world_id: str, character: Character, pass_play: PassPlay, rendered: str, db: Session,
) -> dict:
    """K1 (TICKET-0121): a declaration that seeks what a day cannot give is
    spent searching. One agenda of one step (`Se renseigner : <declaration>`,
    cost 1, no domain -- no dice -- and no prerequisite), a `route` quest
    request born on that step, no veto and no feasibility entry. Commits:
    the plan, the request and the status move are one transaction. The
    objective is the player's own declaration (J2-a1): nothing about the
    request reaches the response or the narrator."""
    first_line = (rendered.strip() or pass_play.declared_action.strip()).splitlines()[0]
    step = PlanStep(
        objective=INQUIRY_OBJECTIVE_PREFIX + first_line[:180], cost=1, domain=None, prerequisite=None,
    )
    title = pass_play.declared_action.strip().splitlines()[0][:200]
    try:
        agenda = write_day_plan(
            db, world_id=world_id, owner_entity_id=character.id, title=title,
            steps=[step], active_step_index=0,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    db.flush()
    written = db.exec(
        select(AgendaStep).where(AgendaStep.agenda_id == agenda.id).order_by(AgendaStep.step_order)
    ).first()
    open_request(
        db, world_id=world_id, character_id=character.id, pass_play_id=pass_play.id,
        trigger="route", declaration=rendered.strip() or pass_play.declared_action,
        agenda_step_id=written.id,
    )
    pass_play.status = "resolving"
    pass_play.agenda_id = agenda.id
    db.add(pass_play)
    db.commit()

    evaluated = EvaluatedStep(step=step, verdict=evaluate_requirements(step, Bindings(doer=character), db))
    return {
        "steps": [_plan_step_dict(evaluated, "active")],
        "slots_consumed": 1,
        "slots_budget": DAY_BUDGET_SLOTS,
        "first_excluded_index": None,
        "feasibility": None,
        "anchoring": {"dropped": []},
        "blocked_at_index": None,
        "blocked_reason": None,
        "inquiry_cut": 0,
        "inquiry": True,
    }


def close_inquiry_steps(outcomes: list, agenda: Agenda, db: Session) -> None:
    """T1 (TICKET-0121): an `inquiry` outcome's step is closed directly --
    `completed`, outcome `inquiry` -- and the agenda `completed` when no
    `pending`/`active` step is left. A decision of 0121, not a proposal
    (the one exception to V1 of 0075): nothing was achieved, so nothing is
    proposed, and the day must not leave an active step the next day would
    walk again. Direct writes in the resolution's transaction; the caller
    commits. A replay never reaches here with the step open again
    (`_load_evaluated_steps` excludes terminal steps)."""
    closed = False
    for outcome in outcomes:
        if outcome.band != INQUIRY_BAND:
            continue
        step = db.get(AgendaStep, outcome.agenda_step_id)
        if step is None or step.status in ("completed", "failed"):
            continue
        write_agenda_step_status(db, step=step, status="completed", outcome="inquiry")
        closed = True
    if not closed:
        return
    db.flush()
    still_open = db.exec(
        select(AgendaStep.id).where(
            AgendaStep.agenda_id == agenda.id, AgendaStep.status.in_(("pending", "active")),
        )
    ).first()
    if still_open is None:
        write_agenda_status(db, agenda=agenda, status="completed")
