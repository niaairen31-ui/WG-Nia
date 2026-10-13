"""Plan finalizers, relocated from `cockpit/routes/day.py` for
module-budget headroom (TICKET-0121, BRIEF-0121-D) -- the
`day_reconcile_apply.py` precedent. Byte-identical otherwise:
`_feasibility_dict`, `_plan_step_dict`, `_finalize_plan`, in that order.
"""

from __future__ import annotations

from typing import Optional

from fastapi import HTTPException
from sqlmodel import Session

from ..conditions import Bindings
from ..day_feasibility import veto as feasibility_veto
from ..day_plan import (
    DAY_BUDGET_SLOTS,
    EvaluatedStep,
    anchor_requirements,
    budget_cut,
    evaluate_requirements,
)
from ..models import Character, PassPlay
from ..writes import write_day_feasibility, write_day_plan


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


def _finalize_plan(
    world_id: str, character: Character, pass_play: PassPlay, raw_steps: list, db: Session,
) -> dict:
    # BRIEF-0078-a, Scope IN item 7: anchoring runs BEFORE evaluate_requirements
    # so a dropped requirement never reaches evaluate_requirements or
    # the step's stored condition (E2 — reporting, never refusing: /plan still
    # returns 200 and writes the plan exactly as it does today).
    anchored_steps, dropped_report = anchor_requirements(raw_steps, character, db)
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
    }
